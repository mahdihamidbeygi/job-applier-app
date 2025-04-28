import json
import logging
import operator
import os
from typing import Annotated, Any, Dict, Optional, TypedDict, cast

from django.conf import settings
from django.db.models.manager import BaseManager
from django.shortcuts import get_object_or_404
from IPython.display import Image

# LangChain core imports (some might be slightly different for graph nodes)
from langchain.agents import create_tool_calling_agent  # Still used for the agent node logic
from langchain.tools import StructuredTool
from langchain_community.vectorstores import Chroma
from langchain_core.agents import AgentAction
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.vectorstores.base import VectorStoreRetriever
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_openai import OpenAIEmbeddings
from langgraph.checkpoint.base import BaseCheckpointSaver  # Import base class if needed for typing

# LangGraph imports
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field

# Your existing imports
from core.models import (
    ChatConversation,
    Education,
    JobListing,
    Project,
    Skill,
    UserProfile,
    WorkExperience,
)
from core.models.chat import ChatMessage
from core.utils.agents.application_agent import ApplicationAgent
from core.utils.agents.job_agent import JobAgent
from core.utils.agents.personal_agent import PersonalAgent
from core.utils.db_utils import safe_get_or_none
from core.utils.langgraph_checkpointer import DjangoCheckpointSaver

logger = logging.getLogger(__name__)


# --- Pydantic Models for Tool Inputs (Keep these as they are) ---
class SearchUserContextInput(BaseModel):
    query: str = Field(
        description="Specific question or topic to search for within the user's data."
    )


class GetWorkExperienceInput(BaseModel):
    experience_id: int = Field(description="The integer ID of the specific work experience entry.")


class GetProjectExperienceInput(BaseModel):
    project_id: int = Field(description="The integer ID of the specific project experience entry.")


class SaveJobDescriptionInput(BaseModel):
    job_description_text: str = Field(
        description="The full text of the job description provided by the user."
    )


class GenerateDocumentInput(BaseModel):
    job_id: int = Field(description="The integer ID of the job listing saved in the system.")


class GetJobDetailsInput(BaseModel):
    job_id: int = Field(description="The integer ID of the job listing saved in the system.")


class AnalyzeTextWithBackgroundInput(BaseModel):
    context_text: str = Field(
        description="The relevant text provided by the user (e.g., interview questions, job description snippet)."
    )
    user_query: str = Field(
        description="The specific question the user wants answered based on the context_text and their background."
    )


# --- LangGraph State Definition ---
class AgentState(TypedDict):
    # Input query
    input: str
    # Conversation history (list of BaseMessage objects)
    chat_history: list[BaseMessage]
    # List of tool calls and their outputs (AgentAction, ToolMessage tuples)
    # Use Annotated and operator.add for accumulation
    intermediate_steps: Annotated[list, operator.add]
    # User and conversation context
    user_id: int
    conversation_id: Optional[int]
    job_id: Optional[int]
    # Potentially add other state variables if needed, e.g., current_job_id


# --- AgenticRAGProcessor Class (LangGraph) ---
class AgenticRAGProcessor:
    """
    Agentic Retrieval Augmented Generation (RAG) processor using LangGraph.
    """

    def __init__(self, user_id: int, conversation_id: Optional[int] = None):
        """
        Initialize the Agentic RAG processor with LangGraph.
        """
        self.user_id: int = user_id
        self.conversation_id: int | None = conversation_id
        self.persist_directory: str = os.path.join(settings.BASE_DIR, "job_vectors")

        # --- Initialization Steps (Mostly the same) ---
        self.embeddings: GoogleGenerativeAIEmbeddings | OpenAIEmbeddings = (
            self._initialize_embeddings()
        )
        self.llm: ChatGoogleGenerativeAI = self._initialize_llm()
        self.vectorstore: Chroma | None = self._initialize_vectorstore(exclude_conversations=True)
        self.retriever: VectorStoreRetriever | None = self._create_retriever()
        self.tools: list[StructuredTool] = self._initialize_tools()  # Tool functions defined below
        self.tool_map: Dict[str, StructuredTool] = {
            tool.name: tool for tool in self.tools
        }  # For easy lookup in tool node

        # --- LangGraph Setup ---
        self.graph: StateGraph = self._build_graph()
        # --- Checkpointing Setup (Django ORM) ---
        # Instantiate your custom saver
        self.memory_checkpointer: BaseCheckpointSaver = DjangoCheckpointSaver()
        logger.info("Using Django ORM checkpointer (DjangoCheckpointSaver).")
        # --- End Checkpointing Setup ---

        # Compile the graph with the custom checkpointer
        self.app: CompiledStateGraph = self.graph.compile(checkpointer=self.memory_checkpointer)
        Image(self.app.get_graph().draw_mermaid_png(), filename="agentic_rag_graph.png")
        # --- End LangGraph Setup ---

    def _initialize_embeddings(self):
        """Initialize the embedding model."""
        try:
            if settings.GOOGLE_API_KEY:
                embeddings = GoogleGenerativeAIEmbeddings(
                    model="models/text-embedding-004",
                    google_api_key=settings.GOOGLE_API_KEY,
                )
                logger.info("Using Google AI embeddings")
            else:
                embeddings = OpenAIEmbeddings()
                logger.info("Using OpenAI embeddings")
            return embeddings
        except Exception as e:
            logger.error(f"Error initializing embeddings: {str(e)}")
            logger.info("Falling back to OpenAI embeddings")
            return OpenAIEmbeddings()

    def _initialize_llm(self) -> ChatGoogleGenerativeAI:
        """Initialize the LLM for generation and agent control."""
        try:
            # # Disable LangSmith tracing to avoid connection issues
            # os.environ["LANGCHAIN_TRACING_V2"] = "false"
            # os.environ["LANGCHAIN_ENDPOINT"] = ""
            # os.environ["LANGCHAIN_API_KEY"] = ""
            # os.environ["LANGCHAIN_PROJECT"] = ""

            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                api_key=settings.GOOGLE_API_KEY,
                temperature=0.1,
                convert_system_message_to_human=True,
            )
            logger.info("Using Google Gemini LLM for Agent")
            return llm
        except Exception as e:
            logger.error(f"Error initializing LLM: {str(e)}")
            raise

    def _initialize_vectorstore(self, exclude_conversations: bool = False):
        """Initialize or load the vector store."""
        try:
            user_persist_dir: str = os.path.join(self.persist_directory, f"user_{self.user_id}")
            os.makedirs(user_persist_dir, exist_ok=True)

            vectorstore = Chroma(
                persist_directory=user_persist_dir,
                embedding_function=self.embeddings,
            )

            # Check if we need to populate the vectorstore
            # Pass exclude_conversations flag to populate method
            if not vectorstore._collection.count() > 0:
                self._populate_vectorstore(vectorstore, exclude_conversations)

            logger.info(
                f"Vector store initialized with {vectorstore._collection.count()} documents"
            )
            return vectorstore

        except Exception as e:
            logger.error(f"Error initializing vector store: {str(e)}")
            raise

    def _create_retriever(self) -> VectorStoreRetriever:
        """Create a retriever from the vectorstore."""
        if not self.vectorstore:
            raise ValueError("Vectorstore not initialized")
        return self.vectorstore.as_retriever(
            search_kwargs={"k": 10, "filter": {"user_id": self.user_id}}
        )

    def _populate_vectorstore(self, vectorstore, exclude_conversations: bool = False) -> None:
        """Populate the vector store with user data."""
        try:
            documents: list[Document] = []
            try:
                profile: UserProfile = UserProfile.objects.get(user_id=self.user_id)
                try:
                    profile_content = profile.get_all_user_info_formatted()
                except AttributeError:
                    # Fallback if the method doesn't exist
                    profile_content = (
                        f"User Profile: {profile.get_all_user_info_formatted()}\n\n"
                        + f"Title: {profile.title}\n"
                        + f"Summary: {profile.professional_summary}\n"
                        + f"Years of Experience: {profile.years_of_experience}"
                    )
                    logger.warning(
                        "UserProfile.get_all_user_info_formatted() not found, using basic profile info."
                    )

                profile_doc: Document = Document(
                    page_content=profile_content,  # Use the comprehensive content
                    metadata={"type": "profile", "user_id": self.user_id},
                )

                documents.append(profile_doc)

                # Add work experiences
                for exp in profile.work_experiences.all():
                    exp_doc = Document(
                        page_content=f"Work Experience: {exp.position} at {exp.company}\n\n"
                        + f"Duration: {exp.start_date.strftime('%b %Y')} - "
                        + f"{exp.end_date.strftime('%b %Y') if exp.end_date else 'Present'}\n"
                        + f"Description: {exp.description}\n"
                        + f"Achievements: {exp.achievements}\n"
                        + f"Technologies: {exp.technologies}",
                        metadata={"type": "work_experience", "user_id": self.user_id, "id": exp.id},
                    )
                    documents.append(exp_doc)

                # Add education
                for edu in profile.education.all():
                    edu_doc = Document(
                        page_content=f"Education: {edu.degree} in {edu.field_of_study} from {edu.institution}\n\n"
                        + f"Duration: {edu.start_date.strftime('%b %Y') if edu.start_date else ''} - "
                        + f"{edu.end_date.strftime('%b %Y') if edu.end_date else 'Present'}\n"
                        + f"Achievements: {edu.achievements}",
                        metadata={"type": "education", "user_id": self.user_id, "id": edu.id},
                    )
                    documents.append(edu_doc)

                # Add skills
                skills_text = "Skills:\n"
                for skill in profile.skills.all():
                    skills_text += (
                        f"- {skill.name} ({skill.get_category_display()}, "
                        + f"Proficiency: {skill.get_proficiency_display()})\n"
                    )
                skills_doc = Document(
                    page_content=skills_text, metadata={"type": "skills", "user_id": self.user_id}
                )
                documents.append(skills_doc)

                # Add projects
                for proj in profile.projects.all():
                    proj_doc = Document(
                        page_content=f"Project: {proj.title}\n\n"
                        + f"Duration: {proj.start_date.strftime('%b %Y')} - "
                        + f"{proj.end_date.strftime('%b %Y') if proj.end_date else 'Present'}\n"
                        + f"Description: {proj.description}\n"
                        + f"Technologies: {proj.technologies}",
                        metadata={"type": "project", "user_id": self.user_id, "id": proj.id},
                    )
                    documents.append(proj_doc)

            except UserProfile.DoesNotExist:
                logger.warning(f"User profile not found for user_id={self.user_id}")

            # --- Load Job Listings ---
            # (Copy the logic from RAGProcessor.populate_vectorstore here)
            job_listings: BaseManager[JobListing] = JobListing.objects.filter(user_id=self.user_id)
            for job in job_listings:
                job_doc = Document(
                    page_content=f"Job Listing: {job.get_formatted_info()}",
                    metadata={"type": "job_listing", "user_id": self.user_id, "id": job.id},
                )
                documents.append(job_doc)

            # --- Conditionally Load Conversations ---
            if not exclude_conversations:
                conversations: BaseManager[ChatConversation] = ChatConversation.objects.filter(
                    user_id=self.user_id
                )
                for conv in conversations:
                    messages: BaseManager[ChatMessage] = conv.messages.order_by("-created_at")[:10]
                    if messages:
                        conv_text: str = f"Previous Conversation (ID: {conv.id}):\n\n"
                        for msg in reversed(messages):
                            conv_text += f"{msg.role.capitalize()}: {msg.content}\n\n"
                        conv_doc = Document(
                            page_content=conv_text,
                            metadata={
                                "type": "conversation",
                                "user_id": self.user_id,
                                "id": conv.id,
                            },
                        )
                        documents.append(conv_doc)

            # Add documents to the vectorstore
            if documents:
                logger.info(
                    f"Attempting to add {len(documents)} documents to vector store for user {self.user_id}. First doc type: {documents[0].metadata.get('type')}"
                )
                vectorstore.add_documents(documents)
                vectorstore.persist()
                logger.info(
                    f"Successfully added {len(documents)} documents. Vector store count now: {vectorstore._collection.count()}"
                )  # Check count after adding
            else:
                logger.warning(f"No documents found to add to vector store for user {self.user_id}")

        except Exception as e:
            logger.error(f"Error populating vector store for user {self.user_id}: {str(e)}")

    # --- Tool Definitions (Keep the actual functions as they are) ---
    def search_user_context(self, query: str) -> str:
        """
        Searches the user's profile, resume, work history, projects, skills,
        and past job applications to find relevant information to answer the user's question.
        Use this tool **ONLY** when the user asks a question directly about their own background, skills, experience, or profile details (e.g., 'What are my skills?', 'Tell me about my experience'). Input is the specific question or topic to search for.
        """
        logger.info(
            f"Agent Tool: search_user_context called with query: '{query}' for user {self.user_id}"
        )
        if not self.retriever:
            return "Error: Retriever not available."
        try:
            docs: list[Document] = self.retriever.get_relevant_documents(query)
            if not docs:
                return "No specific context found in the user's profile for that query."
            context: str = "\n\n".join(
                [
                    f"Source: {doc.metadata.get('type', 'unknown')}, Content: {doc.page_content}"
                    for doc in docs
                ]
            )
            return context
        except Exception as e:
            logger.error(f"Error in search_user_context tool: {str(e)}")
            return f"Error searching user context: {str(e)}"

    def get_specific_work_experience(self, experience_id: int) -> str:
        """
        Retrieves detailed information about a specific work experience entry using its ID.
        Use this if the user asks about a particular job they held or if context search mentions a specific experience ID.
        Input must be the integer ID of the work experience.
        """
        logger.info(
            f"Agent Tool: get_specific_work_experience called with ID: {experience_id} for user {self.user_id}"
        )
        try:
            # No need to get profile first if using safe_get_or_none with user_id filter
            experience: WorkExperience | None = safe_get_or_none(
                WorkExperience,
                id=experience_id,
                profile__user_id=self.user_id,  # Filter by user_id directly
            )
            if experience:
                return (
                    f"Work Experience Details (ID: {experience.id}):\n"
                    f"Company: {experience.company}\n"
                    f"Position: {experience.position}\n"
                    f"Location: {experience.location}\n"
                    f"Duration: {experience.start_date.strftime('%b %Y')} - {experience.end_date.strftime('%b %Y') if experience.end_date else 'Present'}\n"
                    f"Description: {experience.description}\n"
                    f"Achievements: {experience.achievements}\n"
                    f"Technologies: {experience.technologies}"
                )
            else:
                return f"Work experience with ID {experience_id} not found for this user."
        except Exception as e:
            logger.error(f"Error in get_specific_work_experience tool: {str(e)}")
            return f"Error retrieving work experience: {str(e)}"

    def get_specific_project_experience(self, experience_id: int) -> str:
        """
        Retrieves detailed information about a specific Project experience entry using its ID.
        Use this if the user asks about a particular project they completed or if context search mentions a specific project ID.
        Input must be the integer ID of the project experience.
        """
        logger.info(
            f"Agent Tool: get_specific_project_experience called with ID: {experience_id} for user {self.user_id}"
        )
        try:
            # No need to get profile first if using safe_get_or_none with user_id filter
            project: Project | None = safe_get_or_none(
                Project,
                id=experience_id,
                profile__user_id=self.user_id,  # Filter by user_id directly
            )
            if project:
                return (
                    f"Project Details (ID: {project.id}):\n"
                    f"Title: {project.title}\n"
                    f"Duration: {project.start_date.strftime('%b %Y')} - {project.end_date.strftime('%b %Y') if project.end_date else 'Present'}\n"
                    f"Description: {project.description}\n"
                    f"Technologies: {project.technologies}"
                )
            else:
                return f"Project with ID {experience_id} not found for this user."
        except Exception as e:
            logger.error(f"Error in get_specific_project_experience tool: {str(e)}")
            return f"Error retrieving project experience: {str(e)}"

    def save_job_description(self, job_description_text: str) -> str:
        """
        Parses and saves a job description provided as text to the database.
        Use this tool when the user pastes or provides the full text of a job description
        and wants to save it for later use (like generating documents).
        Input MUST be the full text of the job description.
        Returns a confirmation message with the new Job ID if successful, or an error message.
        """
        logger.info(f"Agent Tool: save_job_description called for user {self.user_id}")
        if not job_description_text or len(job_description_text) < 50:  # Basic validation
            return "Please provide the full job description text for me to save."
        try:
            # Instantiate JobAgent with the text. This triggers parsing and saving.
            job_agent = JobAgent(user_id=self.user_id, text=job_description_text)

            # Check if the job_record was successfully created
            if job_agent.job_record and job_agent.job_record.id:
                new_job_id: int = job_agent.job_record.id
                job_title: str = job_agent.job_record.title
                company: str = job_agent.job_record.company
                logger.info(
                    f"Successfully saved job description as Job ID: {new_job_id} for user {self.user_id}"
                )
                return (
                    f"OK. I've saved the job description for '{job_title}' at '{company}' as Job ID: {new_job_id}. "
                    f"Would you like me to generate a resume or cover letter for this job now?"
                )
            else:
                # This case might happen if JobAgent's LLM call fails validation but doesn't raise an error
                logger.error(
                    f"JobAgent did not successfully create a job record from text for user {self.user_id}. LLM output might be invalid."
                )
                return "Sorry, I encountered an issue while trying to parse and save the job description. The format might be unexpected."

        except (
            ValueError,
            TypeError,
        ) as ve:  # Catch potential errors during JobAgent init or parsing (including JSON/Type errors from LLM)
            logger.error(f"Error in save_job_description tool for user {self.user_id}: {ve}")
            return f"Sorry, I couldn't process that text as a job description. Error: {ve}"
        except Exception as e:
            logger.exception(
                f"Unexpected error in save_job_description tool for user {self.user_id}: {str(e)}"
            )
            return (
                f"An unexpected error occurred while trying to save the job description: {str(e)}"
            )

    def generate_tailored_resume(self, job_id: int) -> str:
        """
        Generates a tailored resume PDF for the user based on a specific job listing ID.
        Use this tool ONLY when the user explicitly asks to generate a resume for a specific job ID they provide or confirm.
        Input MUST be the integer ID of the job listing saved in the system.
        Returns the URL of the generated resume PDF or an error message.
        """
        logger.info(
            f"Agent Tool: generate_tailored_resume called for job ID: {job_id} for user {self.user_id}"
        )
        try:
            # Verify the job exists and belongs to the user
            job_listing = get_object_or_404(JobListing, id=job_id, user_id=self.user_id)

            # Initialize necessary agents for ApplicationAgent
            personal_agent = PersonalAgent(user_id=self.user_id)
            job_agent = JobAgent(user_id=self.user_id, job_id=job_id)  # Load by ID

            # Initialize ApplicationAgent
            application_agent = ApplicationAgent(
                user_id=self.user_id,
                personal_agent=personal_agent,
                job_agent=job_agent,
            )

            # Call the generation method within ApplicationAgent
            resume_url = application_agent.generate_resume()

            if resume_url:
                logger.info(f"Successfully generated resume for job {job_id}. URL: {resume_url}")
                return f"OK. I have generated your tailored resume for the '{job_listing.title}' position at '{job_listing.company}'. You can access it here: {resume_url}"
            else:
                logger.error(f"ApplicationAgent failed to generate resume URL for job {job_id}")
                return "Sorry, I encountered an issue while generating the resume file."

        except JobListing.DoesNotExist:
            logger.warning(
                f"generate_tailored_resume tool: JobListing ID {job_id} not found for user {self.user_id}"
            )
            return f"I couldn't find a job with ID {job_id} associated with your account. Please double-check the ID."
        except json.JSONDecodeError as json_err:
            logger.error(
                f"generate_tailored_resume tool: Failed to parse LLM response during resume generation for job {job_id}: {json_err}"
            )
            return f"Sorry, I encountered an issue processing the data to generate the resume for job {job_id}. The internal language model might have returned an unexpected format. Please try again."
        except ValueError as ve:  # Catch error from JobAgent init if job not found by ID
            logger.warning(
                f"generate_tailored_resume tool: Value error during processing for job ID {job_id}: {ve}"
            )
            return f"I couldn't find or process the job with ID {job_id}. Please double-check the ID. Error: {ve}"
        except Exception as e:
            logger.exception(f"Error in generate_tailored_resume tool for job {job_id}: {str(e)}")
            return f"An unexpected error occurred while trying to generate the resume: {str(e)}"

    def generate_tailored_cover_letter(self, job_id: int) -> str:
        """
        Generates a tailored cover letter PDF for the user based on a specific job listing ID.
        Use this tool ONLY when the user explicitly asks to generate a cover letter for a specific job ID they provide or confirm.
        Input MUST be the integer ID of the job listing saved in the system.
        Returns the URL of the generated cover letter PDF or an error message.
        """
        logger.info(
            f"Agent Tool: generate_tailored_cover_letter called for job ID: {job_id} for user {self.user_id}"
        )
        try:
            # Verify the job exists and belongs to the user
            job_listing: JobListing = get_object_or_404(JobListing, id=job_id, user_id=self.user_id)

            # Initialize necessary agents for ApplicationAgent
            personal_agent = PersonalAgent(user_id=self.user_id)
            job_agent = JobAgent(user_id=self.user_id, job_id=job_id)  # Load by ID

            # Initialize ApplicationAgent
            application_agent = ApplicationAgent(
                user_id=self.user_id,
                personal_agent=personal_agent,
                job_agent=job_agent,
            )

            # Call the generation method within ApplicationAgent
            cover_letter_url = application_agent.generate_cover_letter()

            if cover_letter_url:
                logger.info(
                    f"Successfully generated cover letter for job {job_id}. URL: {cover_letter_url}"
                )
                return f"OK. I have generated your tailored cover letter for the '{job_listing.title}' position at '{job_listing.company}'. You can access it here: {cover_letter_url}"
            else:
                logger.error(
                    f"ApplicationAgent failed to generate cover letter URL for job {job_id}"
                )
                return "Sorry, I encountered an issue while generating the cover letter file."

        except JobListing.DoesNotExist:
            logger.warning(
                f"generate_tailored_cover_letter tool: JobListing ID {job_id} not found for user {self.user_id}"
            )
            return f"I couldn't find a job with ID {job_id} associated with your account. Please double-check the ID."
        except json.JSONDecodeError as json_err:
            logger.error(
                f"generate_tailored_cover_letter tool: Failed to parse LLM response during cover letter generation for job {job_id}: {json_err}"
            )
            return f"Sorry, I encountered an issue processing the data to generate the cover letter for job {job_id}. The internal language model might have returned an unexpected format. Please try again."
        except ValueError as ve:  # Catch error from JobAgent init if job not found by ID
            logger.warning(
                f"generate_tailored_cover_letter tool: Error initializing JobAgent for job ID {job_id}: {ve}"
            )
            return f"I couldn't find a job with ID {job_id} associated with your account. Please double-check the ID."
        except Exception as e:
            logger.exception(
                f"Error in generate_tailored_cover_letter tool for job {job_id}: {str(e)}"
            )
            return (
                f"An unexpected error occurred while trying to generate the cover letter: {str(e)}"
            )

    def get_job_details(self, job_id: int) -> str:
        """
        Retrieves the full details (title, company, description, requirements, etc.)
        of a specific job listing saved in the system using its ID.
        Use this tool when the user asks questions about a specific job identified by its ID,
        especially if the job details were saved previously using 'save_job_description'.
        Input must be the integer ID of the job listing.
        """
        logger.info(
            f"Agent Tool: get_job_details called for job ID: {job_id} for user {self.user_id}"
        )
        try:
            # Use get_object_or_404 for safety, ensuring job belongs to user
            job_listing: JobListing = get_object_or_404(JobListing, id=job_id, user_id=self.user_id)
            # Use the model's method if it provides good formatting
            details = job_listing.get_formatted_info()
            logger.info(f"Retrieved details for job ID: {job_id}")
            return details
        except JobListing.DoesNotExist:
            logger.warning(
                f"get_job_details tool: JobListing ID {job_id} not found for user {self.user_id}"
            )
            return f"Error: Job listing with ID {job_id} not found for this user."
        except Exception as e:
            logger.exception(f"Error in get_job_details tool for job {job_id}: {str(e)}")
            return f"An unexpected error occurred while retrieving job details: {str(e)}"

    def analyze_text_with_background(self, context_text: str, user_query: str) -> str:
        """Analyzes provided text in the context of the user's background."""
        try:
            personal_agent = PersonalAgent(user_id=self.user_id)
            background_summary = personal_agent.get_formatted_background()

            prompt = f"""
            You are an expert assistant helping a user answer a question based on provided text and their background.

            User's Background Summary:
            ---
            {json.dumps(background_summary, indent=2)}
            ---

            Provided Context Text:
            ---
            {context_text}
            ---

            User's Question:
            ---
            {user_query}
            ---

            Based *only* on the User's Background Summary and the Provided Context Text, answer the User's Question accurately and concisely.
            Focus on highlighting relevant skills and experiences from the background that relate to the context text and the question.
            If the background doesn't contain relevant information, state that clearly.
            """

            # Use invoke instead of generate_text
            response = self.llm.invoke(prompt)
            return str(response.content)

        except Exception as e:
            logger.exception(
                f"Error in analyze_text_with_background tool for user {self.user_id}: {str(e)}"
            )
            return f"An unexpected error occurred during analysis: {str(e)}"

    def get_profile_summary(self) -> str:
        """
        Retrieves a formatted summary of the user's profile, including work experience,
        education, skills, and projects directly from their saved profile data.
        Use this as a quick way to get the user's overall background if vector search fails or is too slow, or as a fallback if `search_user_context` fails.
        """
        logger.info(f"Agent Tool: get_profile_summary called for user {self.user_id}")
        try:
            personal_agent = PersonalAgent(user_id=self.user_id)
            # Use the method that returns a dictionary or well-formatted string
            summary_data = personal_agent.get_formatted_background()  # Returns dict
            # Convert dict to string for the agent
            summary_str = json.dumps(summary_data, indent=2)
            logger.info("Successfully retrieved profile summary.")
            return summary_str
        except UserProfile.DoesNotExist:
            logger.warning(
                f"get_profile_summary tool: UserProfile not found for user {self.user_id}"
            )
            return "Error: User profile could not be loaded."
        except Exception as e:
            logger.exception(f"Error in get_profile_summary tool for user {self.user_id}: {str(e)}")
            return f"An unexpected error occurred while retrieving the profile summary: {str(e)}"

    def _initialize_tools(self) -> list[StructuredTool]:
        """Gather all defined tools for the agent using StructuredTool."""
        # Make sure the docstrings of the tool functions are descriptive!
        tools: list[StructuredTool] = [
            StructuredTool.from_function(
                func=self.search_user_context,
                name="search_user_context",
                description=self.search_user_context.__doc__,
                args_schema=SearchUserContextInput,
            ),
            StructuredTool.from_function(
                func=self.get_specific_work_experience,
                name="get_specific_work_experience",
                description=self.get_specific_work_experience.__doc__,
                args_schema=GetWorkExperienceInput,
            ),
            StructuredTool.from_function(
                func=self.get_specific_project_experience,
                name="get_specific_project_experience",
                description=self.get_specific_project_experience.__doc__,
                args_schema=GetProjectExperienceInput,
            ),
            StructuredTool.from_function(
                func=self.save_job_description,
                name="save_job_description",
                description=self.save_job_description.__doc__,
                args_schema=SaveJobDescriptionInput,
            ),
            StructuredTool.from_function(
                func=self.generate_tailored_resume,
                name="generate_tailored_resume",
                description=self.generate_tailored_resume.__doc__,
                args_schema=GenerateDocumentInput,
            ),
            StructuredTool.from_function(
                func=self.generate_tailored_cover_letter,
                name="generate_tailored_cover_letter",
                description=self.generate_tailored_cover_letter.__doc__,
                args_schema=GenerateDocumentInput,
            ),
            StructuredTool.from_function(
                func=self.get_job_details,
                name="get_job_details",
                description=self.get_job_details.__doc__,
                args_schema=GetJobDetailsInput,
            ),
            StructuredTool.from_function(
                func=self.analyze_text_with_background,
                name="analyze_text_with_background",
                description=self.analyze_text_with_background.__doc__,
                args_schema=AnalyzeTextWithBackgroundInput,
            ),
            StructuredTool.from_function(
                func=self.get_profile_summary,
                name="get_profile_summary",
                description=self.get_profile_summary.__doc__,
                # No args_schema needed
            ),
        ]
        return tools

    # --- LangGraph Node Definitions ---

    def _agent_node(self, state: AgentState):
        """Invokes the agent model to decide the next action or respond."""
        logger.debug(f"--- Calling Agent Node ---")
        # The agent needs the specific prompt structure defined earlier
        # We need to create the agent runnable *here* or have it pre-built
        # Let's pre-build it for efficiency

        # If self.agent is not defined, build it
        if not hasattr(self, "agent"):
            custom_instructions: str = self._get_agent_instructions()
            prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages(
                [
                    ("system", custom_instructions),
                    MessagesPlaceholder(variable_name="chat_history"),
                    ("human", "{input}"),
                    MessagesPlaceholder(
                        variable_name="agent_scratchpad"
                    ),  # Use intermediate_steps directly
                ]
            )
            # Adapt create_tool_calling_agent if needed, or use a pre-built agent structure
            # The key is that it takes 'input', 'chat_history', 'intermediate_steps'
            # and returns AgentAction or AgentFinish
            llm_with_tools = self.llm.bind_tools(self.tools)
            self.agent = create_tool_calling_agent(llm_with_tools, self.tools, prompt)
            logger.info("Agent runnable created.")

        # Check if we've already generated a resume in this conversation
        for msg in state["chat_history"]:
            if (
                isinstance(msg, AIMessage)
                and "I have generated your tailored resume" in msg.content
            ):
                logger.debug("Resume already generated in this conversation.")
                return {
                    "chat_history": state["chat_history"]
                    + [
                        AIMessage(
                            content="I've already generated a resume for this job. You can find the link in the previous message."
                        )
                    ]
                }

        # Prepare input for the agent runnable
        # Format intermediate steps as tuples of (agent_action, observation)
        formatted_steps = []
        for step in state["intermediate_steps"]:
            if isinstance(step, AIMessage) and step.tool_calls:
                # Convert AIMessage with tool calls to AgentAction
                for tool_call in step.tool_calls:
                    action = AgentAction(
                        tool=tool_call["name"],
                        tool_input=tool_call["args"],
                        log=f"Calling {tool_call['name']} with args: {tool_call['args']}",
                    )
                    formatted_steps.append((action, None))
            elif isinstance(step, ToolMessage):
                # If the last step was an AgentAction, pair it with this observation
                if formatted_steps and formatted_steps[-1][1] is None:
                    formatted_steps[-1] = (formatted_steps[-1][0], step.content)
                else:
                    # If no matching action, create a dummy action
                    action = AgentAction(tool="unknown", tool_input={}, log="Unknown tool call")
                    formatted_steps.append((action, step.content))

        agent_input = {
            "input": state["input"],
            "chat_history": state["chat_history"],
            "intermediate_steps": formatted_steps,
        }
        logger.info(f"Agent Node Input: {agent_input}")

        # Invoke the agent logic
        try:
            agent_output = self.agent.invoke(agent_input)
            logger.info(f"Agent Node Output: {agent_output}")
        except Exception as e:
            logger.error(f"Error invoking agent: {str(e)}")
            return {
                "chat_history": state["chat_history"]
                + [
                    AIMessage(
                        content="I encountered an error while processing your request. Please try again."
                    )
                ]
            }

        # Handle direct response from LLM (no tool calls)
        if isinstance(agent_output, str):
            logger.debug("Agent output is a direct string response.")
            ai_message = AIMessage(content=agent_output)
            return {"chat_history": state["chat_history"] + [ai_message]}

        # Handle AIMessage with tool calls
        if isinstance(agent_output, AIMessage) and agent_output.tool_calls:
            logger.debug("Agent output is AIMessage with tool_calls.")
            # Return the AIMessage itself. operator.add will append it to the list.
            return_value = {"intermediate_steps": [agent_output]}
            logger.debug(f"Agent node returning AIMessage with tool calls: {return_value}")
            return return_value

        # Handle AIMessage without tool calls (direct response)
        elif isinstance(agent_output, AIMessage):
            logger.debug(f"Agent output is AIMessage (direct response): {agent_output}")
            return {"chat_history": state["chat_history"] + [agent_output]}

        # Check if the output is directly a list of tool actions/calls
        elif (
            isinstance(agent_output, list)
            and agent_output
            and hasattr(agent_output[0], "tool")
            and hasattr(agent_output[0], "tool_input")
        ):
            logger.debug("Agent output is a list of tool actions (e.g., ToolAgentAction).")
            # Convert to AIMessage format for consistency
            tool_calls_for_aimessage = []
            for action in agent_output:
                tool_calls_for_aimessage.append(
                    {
                        "name": action.tool,
                        "args": action.tool_input,
                        "id": getattr(action, "id", None),
                    }
                )

            ai_message_with_calls = AIMessage(content="", tool_calls=tool_calls_for_aimessage)
            return_value = {"intermediate_steps": [ai_message_with_calls]}
            logger.debug(f"Agent node converting list of actions to AIMessage: {return_value}")
            return return_value

        # Handle older AgentFinish case
        elif hasattr(agent_output, "return_values") and "output" in agent_output.return_values:
            logger.debug("Agent output is legacy AgentFinish.")
            final_output = agent_output.return_values["output"]
            return {"chat_history": state["chat_history"] + [AIMessage(content=final_output)]}

        # Handle unexpected output format
        else:
            logger.error(f"Unexpected agent output format: {agent_output}")
            error_message = AIMessage(content="Error: Unexpected agent response format.")
            return {"chat_history": state["chat_history"] + [error_message]}

    def _execute_tool_node(self, state: AgentState) -> Dict[str, list]:
        """
        Executes the tool calls requested by the agent.

        Expects the last item in intermediate_steps to be an AIMessage
        containing a list of tool_calls (dictionaries).

        Returns a dictionary with 'intermediate_steps' containing a list
        of ToolMessage objects corresponding to the results.
        """
        logger.debug(f"--- Calling Tool Node ---")
        # The last step added by _agent_node should be an AIMessage with tool_calls
        last_step = state["intermediate_steps"][-1] if state["intermediate_steps"] else None
        logger.debug(f"Tool node processing last step: {last_step} (type: {type(last_step)})")

        # Validate the expected input format
        if not isinstance(last_step, AIMessage) or not last_step.tool_calls:
            error_msg = f"Tool node expected AIMessage with tool_calls, but got {type(last_step)}. Cannot execute tools."
            logger.error(error_msg)
            # Return an empty list to append to intermediate_steps, effectively adding no tool results
            # and allowing the agent to potentially recover or report the error.
            return {"intermediate_steps": []}

        tool_calls_list = (
            last_step.tool_calls
        )  # This is a list of dicts {'name': ..., 'args': ..., 'id': ...}
        tool_messages: list[ToolMessage] = []  # This will be the list of results to return

        logger.info(f"Executing {len(tool_calls_list)} tool call(s)...")

        for tool_call in tool_calls_list:
            # Safely extract tool details from the dictionary
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("args", {})
            # Ensure tool_call_id is a string, use a default if None
            tool_call_id = str(tool_call.get("id", f"tool_{len(tool_messages)}"))

            logger.debug(
                f"Processing tool call: name='{tool_name}', id='{tool_call_id}', args={tool_args}"
            )

            if not tool_name:
                error_msg = f"Error: Tool call missing 'name'. Tool call data: {tool_call}"
                logger.error(error_msg)
                tool_messages.append(ToolMessage(content=error_msg, tool_call_id=tool_call_id))
                continue

            # Look up the tool function in the map
            if tool_name not in self.tool_map:
                error_msg = f"Error: Tool '{tool_name}' not found."
                logger.error(error_msg)
                tool_messages.append(ToolMessage(content=error_msg, tool_call_id=tool_call_id))
                continue

            tool_to_call: StructuredTool = self.tool_map[tool_name]

            # Execute the tool
            observation = None
            try:
                # Invoke the tool with the arguments dictionary
                # StructuredTool handles Pydantic model validation if args_schema is set
                logger.info(f"Invoking tool '{tool_name}' with args: {tool_args}")
                observation = tool_to_call.invoke(tool_args)
                logger.debug(f"Tool '{tool_name}' observation: {observation}")
                # Append success message
                tool_messages.append(
                    ToolMessage(content=str(observation), tool_call_id=tool_call_id)
                )

            except Exception as e:
                # Log the full exception traceback for debugging
                error_msg = f"Error executing tool '{tool_name}' with args {tool_args}: {e}"
                logger.exception(error_msg)
                # Append error message
                tool_messages.append(ToolMessage(content=error_msg, tool_call_id=tool_call_id))

        # Check if any tool messages should be shown to the user
        for tool_message in tool_messages:
            # If the tool message contains a URL or is a success message, add it to chat history
            if (
                "http" in tool_message.content
                or "OK." in tool_message.content
                or "Success" in tool_message.content
            ):
                return {
                    "chat_history": state["chat_history"]
                    + [AIMessage(content=tool_message.content)]
                }

        # Return the list of ToolMessage results.
        # operator.add in the state definition will concatenate this list
        # with the existing intermediate_steps list.
        logger.debug(f"Tool node returning {len(tool_messages)} message(s): {tool_messages}")
        return {"intermediate_steps": tool_messages}

    def _format_intermediate_steps(self, intermediate_steps):
        """Helper to format tool calls and results for the agent_scratchpad."""
        # This needs to match what create_tool_calling_agent expects
        # Typically, it's a list of AIMessage (with tool calls) and ToolMessage pairs
        log = []
        for item in intermediate_steps:
            # item could be a list of tool calls (from agent) or list of ToolMessages (from tool node)
            if isinstance(item, list):
                if item and hasattr(
                    item[0], "tool"
                ):  # Agent tool calls (might need adjustment based on actual object)
                    log.append(AIMessage(content="", tool_calls=item))
                elif item and isinstance(item[0], ToolMessage):  # Tool results
                    log.extend(item)
            # Handle older formats if necessary
            elif hasattr(item, "tool_calls"):  # AIMessage with tool calls
                log.append(item)
            elif isinstance(item, ToolMessage):  # Single ToolMessage
                log.append(item)

        logger.debug(f"Formatted Scratchpad: {log}")
        return log

    # --- LangGraph Edge Logic ---

    def _should_continue(self, state: AgentState) -> str:
        """
        Determines the next step after the agent node runs.
        Checks if the agent node's output (the last intermediate step)
        indicates a tool call request.
        """
        logger.debug(f"--- Checking should_continue ---")
        logger.debug(f"Current intermediate_steps: {state['intermediate_steps']}")
        last_intermediate_step = (
            state["intermediate_steps"][-1] if state["intermediate_steps"] else None
        )
        logger.debug(f"Last intermediate step type: {type(last_intermediate_step)}")
        if last_intermediate_step:
            logger.debug(f"Last intermediate step content: {last_intermediate_step}")

        # If there are no intermediate steps, check if we have a direct response in chat history
        if not last_intermediate_step:
            if state["chat_history"] and isinstance(state["chat_history"][-1], AIMessage):
                logger.debug("No intermediate steps, but found direct response in chat history.")
                return END
            logger.debug("No intermediate steps and no direct response found.")
            return END

        # Check for tool calls in the last step
        tool_call_detected = False

        # Case 1: AIMessage with tool_calls
        if isinstance(last_intermediate_step, AIMessage) and last_intermediate_step.tool_calls:
            tool_call_detected = True
            logger.debug("Tool call detected: AIMessage with tool_calls.")

        # Case 2: Dictionary with tool call structure
        elif isinstance(last_intermediate_step, dict):
            if "name" in last_intermediate_step and (
                "args" in last_intermediate_step or "arguments" in last_intermediate_step
            ):
                tool_call_detected = True
                logger.debug("Tool call detected: Dict with name/args structure.")

        # Case 3: Object with tool/tool_input attributes
        elif hasattr(last_intermediate_step, "tool") and hasattr(
            last_intermediate_step, "tool_input"
        ):
            tool_call_detected = True
            logger.debug("Tool call detected: Object with tool/tool_input attributes.")

        # Case 4: List of tool calls
        elif isinstance(last_intermediate_step, list) and last_intermediate_step:
            first_item = last_intermediate_step[0]
            if (
                isinstance(first_item, dict)
                and "name" in first_item
                and ("args" in first_item or "arguments" in first_item)
            ):
                tool_call_detected = True
                logger.debug("Tool call detected: List of dicts with name/args structure.")
            elif hasattr(first_item, "tool") and hasattr(first_item, "tool_input"):
                tool_call_detected = True
                logger.debug("Tool call detected: List of objects with tool/tool_input attributes.")

        # Decision Logic
        if tool_call_detected:
            logger.debug("Decision: Agent requested tool execution. Returning 'action'.")
            return "action"
        else:
            logger.debug("Decision: No tool call request detected. Returning END.")
            return END

    # --- Graph Building ---

    def _get_agent_instructions(self) -> str:
        """Returns the system prompt instructions for the agent."""
        return f"""
        **AGENT BEHAVIOR RULES (User ID: {self.user_id}):**

        You are a helpful job application assistant for User ID {self.user_id}.
        Your goal is to assist the user with their job search and application process using the available tools and context.

        **CONTEXT AND TOOL USAGE GUIDELINES:**

        **VERY IMPORTANT RULE FOR JOB DESCRIPTIONS:**
        - If the user's input is a large block of text (more than ~100 words) and appears to be a job description (containing sections like Responsibilities, Qualifications, About the Company, etc.), you **MUST** use the `save_job_description` tool to parse and save it. Do not treat it as a conversational question unless it's very short or clearly a question *about* a job description.
        - After successfully saving, confirm with the user by providing the new Job ID.

        **VERY IMPORTANT RULE FOR BACKGROUND QUESTIONS:**
        - When the user asks questions like "What do you know about my background?", "What are my skills?", "Tell me about my experience?", or any question asking about *their own profile information*, you **MUST** use the `search_user_context` tool first.
        - If `search_user_context` fails or returns insufficient information, you MAY then use the `get_profile_summary` tool as a fallback.
        - **DO NOT** answer questions about the user's background based on general knowledge, assumptions, or by inferring from job listings mentioned in the chat. Only use information retrieved via the specified tools (`search_user_context`, `get_profile_summary`).

        **OTHER TOOL USAGE GUIDELINES:**

        1.  **CHECK CHAT HISTORY:** Before using any tool, review the recent `chat_history`. If the user recently provided specific text (like interview answers, job description snippets) and asks a question *about that text*, prioritize using `analyze_text_with_background` or incorporate the chat context directly in your reasoning if appropriate.
        2.  **USE `search_user_context` for GENERAL BACKGROUND:** For general questions about the user's background, skills, experience, education, projects, or suitability for a role (when specific text isn't provided in chat), **ALWAYS** use the `search_user_context` tool first. If the tool returns no relevant info, state that clearly.
        3.  **USE `get_profile_summary` as FALLBACK:** Only use `get_profile_summary` if `search_user_context` fails or is insufficient for a background query.
        4.  **USE `analyze_text_with_background` for SPECIFIC TEXT + BACKGROUND:** When the user provides specific text (e.g., interview questions/answers) in the chat and asks how it relates to their background or how to improve it, use the `analyze_text_with_background` tool. Provide both the text and the user's query to the tool.
        5.  **USE `get_job_details` for SAVED JOBS:** If the user asks about a specific job previously saved (mentioning its ID), use the `get_job_details` tool with the `job_id`.
        6.  **CHECK IDs for GENERATION:** Before using `generate_tailored_resume` or `generate_tailored_cover_letter`, check `chat_history` or `input` for a specific Job ID. If unclear, ASK the user for the ID. DO NOT GUESS.
        7.  **REPORT TOOL RESULTS:** Clearly state the outcome of tool actions. Report errors clearly.
        8.  **GENERAL CONVERSATION:** If no specific tool or context is relevant, engage in helpful conversation based on history and general knowledge, but remember the **VERY IMPORTANT RULES** above.
        """

    def _build_graph(self) -> StateGraph:
        """Constructs the LangGraph StateGraph."""
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("agent", self._agent_node)
        graph.add_node("action", self._execute_tool_node)

        # Define edges
        graph.add_edge(START, "agent")  # Start by calling the agent

        # Conditional edge after agent decides
        graph.add_conditional_edges(
            "agent",  # Source node
            self._should_continue,  # Function to decide path
            {
                "action": "action",  # If tool call, go to action node
                END: END,  # If no tool call, end graph
            },
        )

        # Edge from action node back to agent node
        graph.add_edge("action", "agent")

        return graph

    def _load_memory(self) -> list[BaseMessage]:
        """Loads chat history from the database for the current conversation."""
        chat_history = []
        if self.conversation_id:
            try:
                conversation: ChatConversation | None = safe_get_or_none(
                    ChatConversation, id=self.conversation_id, user_id=self.user_id
                )
                if conversation:
                    messages: BaseManager[ChatMessage] = conversation.messages.order_by(
                        "created_at"
                    )
                    for msg in messages:
                        if msg.role == "user":
                            chat_history.append(HumanMessage(content=msg.content))
                        elif msg.role == "assistant":
                            # Check if message content indicates tool calls (might need parsing if stored complexly)
                            # Simple assumption: if it looks like JSON, maybe it was tool related? Needs better handling.
                            # For now, treat all assistant messages as plain AI messages for history.
                            chat_history.append(AIMessage(content=msg.content))
                        # Ignore system messages for basic history
                    logger.info(
                        f"Loaded {len(chat_history)} messages into memory for conversation {self.conversation_id}"
                    )
            except Exception as e:
                logger.error(
                    f"Error loading chat history for conversation {self.conversation_id}: {str(e)}"
                )
        return chat_history

    # --- Main Execution Method ---
    def run(self, user_input: str) -> str:
        """Run the agentic RAG process using the LangGraph application."""
        try:
            logger.info(
                f"Running Agentic RAG (LangGraph) for user {self.user_id}, conversation {self.conversation_id}"
            )

            current_chat_history = self._load_memory()
            logger.debug(f"Initial Chat History Loaded: {current_chat_history}")

            initial_state: AgentState = {
                "input": user_input,
                "chat_history": current_chat_history,
                "intermediate_steps": [],
                "user_id": self.user_id,
                "conversation_id": self.conversation_id,
                "job_id": None,
            }

            # Use proper RunnableConfig type
            config = {
                "configurable": {
                    "thread_id": str(self.conversation_id or f"user_{self.user_id}_new")
                }
            }
            final_state = self.app.invoke(initial_state, config=cast(Any, config))

            if final_state and final_state.get("chat_history"):
                final_messages = [
                    msg for msg in final_state["chat_history"] if isinstance(msg, AIMessage)
                ]
                if final_messages:
                    final_message = final_messages[-1]
                    if not final_message.tool_calls:
                        return str(final_message.content)
                    else:
                        logger.error(
                            f"The last AIMessage contained tool calls, indicating abnormal termination: {final_message}"
                        )
                        return "It looks like I got stuck in a loop. Could you try rephrasing?"
                else:
                    logger.error("Final state chat history exists but contains no AIMessages.")
                    if final_state["chat_history"] and isinstance(
                        final_state["chat_history"][-1], HumanMessage
                    ):
                        logger.warning("Graph seems to have ended immediately after user input.")
                        return "I received your message, but couldn't process a response. Please try again."
                    return "Sorry, I couldn't formulate a final response."
            else:
                logger.error("Graph execution did not return a valid final state or chat history.")
                return "Sorry, I encountered an internal processing error."

        except Exception as e:
            logger.exception(
                f"Error during Agentic RAG (LangGraph) execution for user {self.user_id}: {str(e)}"
            )
            return "I'm sorry, I encountered an internal error. Please try again."

    def refresh_vectorstore(self) -> bool:
        """Refresh the vector store with updated user data."""
        # This method needs to be adapted slightly if it exists in the original RAGProcessor
        # to use the correct vectorstore instance and population method.
        try:
            # Get the user-specific directory
            user_persist_dir = os.path.join(self.persist_directory, f"user_{self.user_id}")

            # Re-initialize Chroma by deleting and recreating (or use update methods if available)
            # Note: Deleting the collection is simpler but rebuilds everything.
            temp_vectorstore = Chroma(
                persist_directory=user_persist_dir,
                embedding_function=self.embeddings,
            )
            ids_to_delete = temp_vectorstore.get().get("ids", [])
            if ids_to_delete:
                temp_vectorstore.delete(ids=ids_to_delete)
                logger.info(f"Cleared existing vector store data for user {self.user_id}")

            # Repopulate with fresh data (excluding conversations)
            self._populate_vectorstore(temp_vectorstore, exclude_conversations=True)

            # Update the instance's vectorstore and retriever
            self.vectorstore: Chroma = temp_vectorstore
            self.retriever: VectorStoreRetriever = self._create_retriever()

            logger.info(f"Vector store refreshed successfully for user {self.user_id}")
            return True
        except Exception as e:
            logger.error(f"Error refreshing vector store for user {self.user_id}: {str(e)}")
            return False
