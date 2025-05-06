import json
import logging
import operator
import os
import uuid
from typing import Annotated, Any, Dict, List, Optional, TypedDict, cast

from django.conf import settings
from django.db.models.manager import BaseManager
from django.shortcuts import get_object_or_404

# LangChain core imports (some might be slightly different for graph nodes)
from langchain.agents import create_tool_calling_agent  # Still used for the agent node logic
from langchain.tools import StructuredTool
from langchain_community.vectorstores import Chroma
from langchain_core.agents import AgentAction, AgentFinish
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
from core.utils.agents.job_agent import JobAgent
from core.utils.agents.personal_agent import PersonalAgent
from core.utils.agents.writer_agent import WriterAgent
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


class GenerateAnswerInput(BaseModel):
    question: str = Field(description="The job application question that needs to be answered")
    job_id: int = Field(description="The integer ID of the job listing saved in the system.")


class FormField(BaseModel):
    id: str = Field(description="Unique identifier for the form field")
    label: str = Field(description="Label or question text for the form field")
    type: str = Field(description="Type of form field (text, select, checkbox, date, etc.)")
    options: Optional[List[str]] = Field(
        None, description="Available options for select or checkbox fields"
    )


class FillFormInput(BaseModel):
    fields: List[FormField] = Field(description="List of form fields to be filled")
    job_id: int = Field(description="The integer ID of the job listing saved in the system.")


class HandleScreeningInput(BaseModel):
    questions: List[str] = Field(description="List of screening questions to answer")
    job_id: int = Field(description="The integer ID of the job listing saved in the system.")


# --- LangGraph State Definition ---
class AgentState(TypedDict):
    input: str
    chat_history: list[BaseMessage]
    intermediate_steps: Annotated[list, operator.add]
    user_id: int
    conversation_id: Optional[int]
    job_id: Optional[int]


# --- AgenticRAGProcessor Class (LangGraph) ---
class AssistantAgent:
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
        self.tool_map: Dict[str, StructuredTool] = {tool.name: tool for tool in self.tools}
        self.agent = self._create_agent_runnable()

        # --- LangGraph Setup ---
        self.graph: StateGraph = self._build_graph()
        # --- Checkpointing Setup (Django ORM) ---
        # Instantiate your custom saver
        self.memory_checkpointer: BaseCheckpointSaver = DjangoCheckpointSaver()
        # --- End Checkpointing Setup ---

        # Compile the graph with the custom checkpointer
        self.app: CompiledStateGraph = self.graph.compile(checkpointer=self.memory_checkpointer)
        # --- End LangGraph Setup ---

    def _initialize_embeddings(self):
        """Initialize the embedding model."""
        if settings.GOOGLE_API_KEY:
            embeddings = GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",
                google_api_key=settings.GOOGLE_API_KEY,
            )
        else:
            embeddings = OpenAIEmbeddings()
        return embeddings

    def _initialize_llm(self) -> ChatGoogleGenerativeAI:
        """Initialize the LLM for generation and agent control."""
        try:

            llm = ChatGoogleGenerativeAI(
                # model="gemini-2.5-flash-preview-04-17",
                # model="gemini-1.5-pro",
                model="gemini-2.5-flash-preview-04-17",
                api_key=settings.GOOGLE_API_KEY,
                temperature=0.1,
                # convert_system_message_to_human=True,
            )
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
                vectorstore.add_documents(documents)
                vectorstore.persist()
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
                return (
                    f"OK. I've saved the job description for '{job_title}' at '{company}' as Job ID: {new_job_id}. "
                    f"Would you like me to generate a resume or cover letter for this job now?"
                )
            else:
                # This case might happen if JobAgent's LLM call fails validation but doesn't raise an error
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
        try:
            # Verify the job exists and belongs to the user
            job_listing = get_object_or_404(JobListing, id=job_id, user_id=self.user_id)

            # Initialize necessary agents for ApplicationAgent
            personal_agent = PersonalAgent(user_id=self.user_id)
            job_agent = JobAgent(user_id=self.user_id, job_id=job_id)  # Load by ID

            # Initialize ApplicationAgent
            writer_agent = WriterAgent(
                user_id=self.user_id,
                personal_agent=personal_agent,
                job_agent=job_agent,
            )

            # Call the generation method within ApplicationAgent
            resume_url = writer_agent.generate_resume()

            if resume_url:
                return f"OK. I have generated your tailored resume for the '{job_listing.title}' position at '{job_listing.company}'. You can access it here: {resume_url}"
            else:
                logger.error(f"ApplicationAgent failed to generate resume URL for job {job_id}")
                return "Sorry, I encountered an issue while generating the resume file."

        except JobListing.DoesNotExist:
            return f"I couldn't find a job with ID {job_id} associated with your account. Please double-check the ID."
        except json.JSONDecodeError as json_err:
            logger.error(
                f"generate_tailored_resume tool: Failed to parse LLM response during resume generation for job {job_id}: {json_err}"
            )
            return f"Sorry, I encountered an issue processing the data to generate the resume for job {job_id}. The internal language model might have returned an unexpected format. Please try again."
        except ValueError as ve:  # Catch error from JobAgent init if job not found by ID
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
        try:
            # Verify the job exists and belongs to the user
            job_listing: JobListing = get_object_or_404(JobListing, id=job_id, user_id=self.user_id)

            # Initialize necessary agents for ApplicationAgent
            personal_agent = PersonalAgent(user_id=self.user_id)
            job_agent = JobAgent(user_id=self.user_id, job_id=job_id)  # Load by ID

            # Initialize ApplicationAgent
            writer_agent = WriterAgent(
                user_id=self.user_id,
                personal_agent=personal_agent,
                job_agent=job_agent,
            )

            # Call the generation method within ApplicationAgent
            cover_letter_url = writer_agent.generate_cover_letter()

            if cover_letter_url:
                return f"OK. I have generated your tailored cover letter for the '{job_listing.title}' position at '{job_listing.company}'. You can access it here: {cover_letter_url}"
            else:
                logger.error(
                    f"ApplicationAgent failed to generate cover letter URL for job {job_id}"
                )
                return "Sorry, I encountered an issue while generating the cover letter file."

        except JobListing.DoesNotExist:
            return f"I couldn't find a job with ID {job_id} associated with your account. Please double-check the ID."
        except json.JSONDecodeError as json_err:
            logger.error(
                f"generate_tailored_cover_letter tool: Failed to parse LLM response during cover letter generation for job {job_id}: {json_err}"
            )
            return f"Sorry, I encountered an issue processing the data to generate the cover letter for job {job_id}. The internal language model might have returned an unexpected format. Please try again."
        except ValueError as ve:  # Catch error from JobAgent init if job not found by ID
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
        try:
            # Use get_object_or_404 for safety, ensuring job belongs to user
            job_listing: JobListing = get_object_or_404(JobListing, id=job_id, user_id=self.user_id)
            # Use the model's method if it provides good formatting
            details = job_listing.get_formatted_info()
            logger.info(f"Retrieved details for job ID: {job_id}")
            return details
        except JobListing.DoesNotExist:
            return f"Error: Job listing with ID {job_id} not found for this user."
        except Exception as e:
            logger.exception(f"Error in get_job_details tool for job {job_id}: {str(e)}")
            return f"An unexpected error occurred while retrieving job details: {str(e)}"

    def analyze_text_with_background(self, context_text: str, user_query: str) -> str:
        """Analyzes provided text in the context of the user's background."""
        try:
            personal_agent = PersonalAgent(user_id=self.user_id)
            background_summary: Dict[str, Any] = personal_agent.get_formatted_background()

            prompt: str = f"""
            You are an expert assistant helping a user answer a question based on provided text and their background.

            User's Background:
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

            Based *only* on the User's Background and the Provided Context Text, answer the User's Question accurately and concisely.
            Focus on highlighting relevant skills and experiences from the background that relate to the context text and the question.
            
            """

            # Use invoke instead of generate_text
            response: BaseMessage = self.llm.invoke(prompt)
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
        try:
            personal_agent = PersonalAgent(user_id=self.user_id)
            # Use the method that returns a dictionary or well-formatted string
            summary_data: Dict[str, Any] = personal_agent.get_formatted_background()  # Returns dict
            # Convert dict to string for the agent
            summary_str: str = json.dumps(summary_data, indent=2)
            logger.info("Successfully retrieved profile summary.")
            return summary_str
        except UserProfile.DoesNotExist:
            return "Error: User profile could not be loaded."
        except Exception as e:
            logger.exception(f"Error in get_profile_summary tool for user {self.user_id}: {str(e)}")
            return f"An unexpected error occurred while retrieving the profile summary: {str(e)}"

    def fill_application_form(self, form_data: Dict[str, Any], job_id: int) -> Dict[str, Any]:
        """
        Automatically fills application form fields based on user profile and job requirements.
        Use this tool when the user needs to complete a job application form with multiple fields.
        Inputs: form field specifications and the integer ID of the job listing.
        Returns a dictionary of field IDs mapped to completed values or an error message.
        """
        try:
            # Verify the job exists and belongs to the user
            job_listing = get_object_or_404(JobListing, id=job_id, user_id=self.user_id)

            # Initialize necessary agents
            personal_agent = PersonalAgent(user_id=self.user_id)
            job_agent = JobAgent(user_id=self.user_id, job_id=job_id)

            # Initialize WriterAgent
            writer_agent = WriterAgent(
                user_id=self.user_id,
                personal_agent=personal_agent,
                job_agent=job_agent,
            )

            # Fill the form fields
            form_fields = form_data.get("fields", [])
            job_description = job_listing.description

            filled_form = writer_agent.fill_application_form(form_fields, job_description)

            if filled_form:
                return {
                    "status": "success",
                    "message": f"I've completed the application form for '{job_listing.title}' at '{job_listing.company}'.",
                    "form_data": filled_form,
                }
            else:
                logger.error(f"WriterAgent failed to fill form for job {job_id}")
                return {
                    "status": "error",
                    "message": "Sorry, I encountered an issue while filling the application form.",
                }

        except JobListing.DoesNotExist:
            return {
                "status": "error",
                "message": f"I couldn't find a job with ID {job_id} associated with your account. Please double-check the ID.",
            }
        except Exception as e:
            logger.exception(f"Error in fill_application_form tool for job {job_id}: {str(e)}")
            return {
                "status": "error",
                "message": f"An unexpected error occurred while filling the application form: {str(e)}",
            }

    def prepare_interview_responses(self, job_id: int) -> str:
        """
        Prepares potential interview questions and responses based on the job description and user profile.
        Use this tool when the user is preparing for an interview for a specific job listing.
        Input MUST be the integer ID of the job listing saved in the system.
        Returns interview preparation materials or an error message.
        """
        try:
            # Verify the job exists and belongs to the user
            job_listing = get_object_or_404(JobListing, id=job_id, user_id=self.user_id)

            # Initialize necessary agents
            personal_agent = PersonalAgent(user_id=self.user_id)
            job_agent = JobAgent(user_id=self.user_id, job_id=job_id)

            # Initialize WriterAgent
            writer_agent = WriterAgent(
                user_id=self.user_id,
                personal_agent=personal_agent,
                job_agent=job_agent,
            )

            # Generate interview responses
            interview_prep = writer_agent.prepare_interview_responses()

            if interview_prep:
                formatted_prep = self._format_interview_prep(interview_prep, job_listing)
                return formatted_prep
            else:
                logger.error(f"WriterAgent failed to generate interview prep for job {job_id}")
                return "Sorry, I encountered an issue while preparing interview materials."

        except JobListing.DoesNotExist:
            return f"I couldn't find a job with ID {job_id} associated with your account. Please double-check the ID."
        except Exception as e:
            logger.exception(
                f"Error in prepare_interview_responses tool for job {job_id}: {str(e)}"
            )
            return f"An unexpected error occurred while preparing interview materials: {str(e)}"

    def generate_answer_to_question(self, question: str, job_id: int) -> str:
        """
        Generates a professional answer to a job application question based on user profile and job details.
        Use this tool when the user needs help answering a specific job application question for a known job.
        Inputs: the question text and the integer ID of the job listing saved in the system.
        Returns: A tailored professional answer or an error message.
        """
        try:
            # Verify the job exists and belongs to the user
            job_listing = get_object_or_404(JobListing, id=job_id, user_id=self.user_id)

            # Initialize necessary agents
            personal_agent = PersonalAgent(user_id=self.user_id)
            job_agent = JobAgent(user_id=self.user_id, job_id=job_id)

            # Initialize WriterAgent
            writer_agent = WriterAgent(
                user_id=self.user_id,
                personal_agent=personal_agent,
                job_agent=job_agent,
            )

            # Generate the answer
            answer = writer_agent.generate_answer(question)

            if answer:
                return f"Here's a suggested answer for your application to '{job_listing.title}' at '{job_listing.company}':\n\n{answer}"
            else:
                logger.error(f"WriterAgent failed to generate answer for job {job_id}")
                return "Sorry, I encountered an issue while generating your answer."

        except JobListing.DoesNotExist:
            return f"I couldn't find a job with ID {job_id} associated with your account. Please double-check the ID."
        except Exception as e:
            logger.exception(
                f"Error in generate_answer_to_question tool for job {job_id}: {str(e)}"
            )
            return f"An unexpected error occurred while generating your answer: {str(e)}"

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
            StructuredTool.from_function(
                func=self.fill_application_form,
                name="fill_application_form",
                description=self.fill_application_form.__doc__,
                args_schema=FillFormInput,
            ),
            StructuredTool.from_function(
                func=self.prepare_interview_responses,
                name="prepare_interview_responses",
                description=self.prepare_interview_responses.__doc__,
                args_schema=GenerateDocumentInput,
            ),
            StructuredTool.from_function(
                func=self.generate_answer_to_question,
                name="generate_answer_to_question",
                description=self.generate_answer_to_question.__doc__,
                args_schema=GenerateAnswerInput,
            ),
        ]
        return tools

    # --- LangGraph Node Definitions ---

    def _create_agent_runnable(self):
        """Creates the agent runnable chain."""
        custom_instructions: str = self._get_agent_instructions()
        prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages(
            [
                ("system", custom_instructions),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )
        llm_with_tools = self.llm.bind_tools(self.tools)
        agent = create_tool_calling_agent(llm_with_tools, self.tools, prompt)
        return agent

    def _agent_node(self, state: AgentState):
        """Invokes the agent model to decide the next action or respond."""

        self._validate_state(state)
        # Prepare input for the agent runnable
        # Format intermediate steps as tuples of (agent_action, observation)
        formatted_steps = []
        for step in state["intermediate_steps"]:
            if isinstance(step, AgentAction):
                formatted_steps.append((step, None))
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
            "job_id": state["job_id"],
            "user_id": state["user_id"],
            "conversation_id": state["conversation_id"],
        }

        # Invoke the agent logic
        try:
            agent_output = self.agent.invoke(agent_input)
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

        if isinstance(agent_output, list) and isinstance(agent_output[0], AgentAction):
            return_value = {"intermediate_steps": agent_output}
            return return_value
        elif isinstance(agent_output, AgentFinish):
            return {
                "chat_history": state["chat_history"]
                + [AIMessage(content=agent_output.return_values["output"])]
            }
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
        self._validate_state(state)
        last_step = state["intermediate_steps"][-1] if state["intermediate_steps"] else None

        # Validate the expected input format
        if not isinstance(last_step, AgentAction):
            error_msg = f"Tool node expected AgentAction as last step, but got {type(last_step)}. Cannot execute tools."
            logger.error(error_msg)
            return {"intermediate_steps": []}

        tool_messages: list[ToolMessage] = []

        # Safely extract tool details from the dictionary
        tool_name: str = last_step.tool
        tool_args = last_step.tool_input
        tool_call_id: Any | str = getattr(last_step, "id", str(uuid.uuid4()))

        if not tool_name:
            error_msg = f"Error: Tool call missing 'name'. Tool call data: {tool_name}"
            logger.error(error_msg)
            tool_message = ToolMessage(
                content=error_msg,
                tool_call_id=tool_call_id,
                action=last_step,
            )
            tool_messages.append(tool_message)
            raise ValueError(error_msg)

        # Look up the tool function in the map
        if tool_name not in self.tool_map:
            error_msg = f"Error: Tool '{tool_name}' not found."
            logger.error(error_msg)
            tool_message = ToolMessage(
                content=error_msg,
                tool_call_id=tool_call_id,
                action=last_step,
            )
            tool_messages.append(tool_message)
            raise ValueError(error_msg)

        tool_to_call: StructuredTool = self.tool_map[tool_name]
        observation = None
        try:
            logger.info(f"Executing tool '{tool_name}' with args {tool_args}")
            observation = tool_to_call.invoke(tool_args)
            tool_message = ToolMessage(
                content=observation,
                tool_call_id=tool_call_id,
                action=last_step,
            )

            # Append success message
            tool_messages.append(tool_message)

        except Exception as e:
            # Log the full exception traceback for debugging
            error_msg: str = f"Error executing tool '{tool_name}' with args {tool_args}: {e}"
            tool_message = ToolMessage(
                content=error_msg,
                tool_call_id=tool_call_id,
                action=last_step,
            )
            tool_messages.append(tool_message)
            logger.exception(error_msg)

        # Prepare the dictionary to return, always include intermediate_steps
        return_dict: Dict[str, Any] = {"intermediate_steps": tool_messages}

        return return_dict

    # --- LangGraph Edge Logic ---

    def _should_continue(self, state: AgentState) -> str:
        """
        Determines the next step after the agent node runs.
        Checks if the agent node's output (the last intermediate step)
        indicates a tool call request.
        """
        last_intermediate_step = (
            state["intermediate_steps"][-1] if state["intermediate_steps"] else None
        )
        if not last_intermediate_step:
            return END

        # Check for tool calls in the last step
        tool_call_detected = False

        if isinstance(last_intermediate_step, AgentAction):
            tool_call_detected = True

        elif isinstance(last_intermediate_step, ToolMessage):
            tool_call_detected = False

        # Decision Logic
        if tool_call_detected:
            return "action"
        else:
            return END

    # --- Graph Building ---

    def _get_agent_instructions(self) -> str:
        """Returns the system prompt instructions for the agent."""
        return f"""
            **AGENT IDENTITY (User ID: {self.user_id}):**

        You are an excellent job applicant assistant. But to increase the quality of responses, you act as You ARE the user with ID {self.user_id} when writing documents or answering application questions.
        in that case You're not just assisting them - you ARE them in their job application process. 
        When writing resumes, cover letters, or answering screening questions, write from the FIRST PERSON perspective as if you are the actual job applicant.

            **CORE BEHAVIOR:**
            - Act as applicants when responding to writing requests, as "I" not as an assistant helping someone else
            - Use the user's background, skills, and experiences AS YOUR OWN when crafting responses
            - Generate authentic, personalized content that genuinely represents why YOU (as the user) are interested in positions
            - Show enthusiasm appropriate for a job applicant when discussing opportunities

            **TOOL USAGE GUIDELINES:**

            1. **Self-Knowledge:**
            - Use `search_user_context` and `get_profile_summary` to access YOUR background, skills, experiences, and projects
            - Always retrieve YOUR profile information before crafting personalized responses
            - NEVER invent details about yourself - only use information from your profile

            2. **Job Processing:**
            - When you encounter text appearing to be like job descriptions, use `save_job_description` to parse and save them and Job IDs
            - After saving, keep the Job IDs in the conversation, and return Job ID to screen
            - Reference the job details when discussing why YOU are interested or qualified
            
            3. **Document Generation:**
            - Generate YOUR resume and cover letter using `generate_tailored_resume` and `generate_tailored_cover_letter`
            - These documents should represent YOU applying for the position
            - These tools return url of generated documents that users need to access
            
            4. **Application Assistance:**
            - When answering application questions, use `generate_answer_to_question` to craft professional responses
            - For job application forms, use `fill_application_form` to complete multiple fields at once
            - Handle screening questions with `handle_screening_questions` tool
            - Prepare for interviews using `prepare_interview_responses` tool
            - All responses should be in YOUR voice as the applicant
            
            5. **Conversation Flow:**
            - If tools have specific returned values that users should have, return them to users
            - Maintain the perspective of being the job applicant throughout all interactions
            - If asked for clarification about your background, experience, or motivations, always retrieve this information from your profile first
            - Be proactive about next steps in YOUR application process
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

            current_chat_history: List[BaseMessage] = self._load_memory()

            initial_state: AgentState = {
                "input": user_input,
                "chat_history": current_chat_history,
                "intermediate_steps": [],
                "user_id": self.user_id,
                "conversation_id": self.conversation_id,
                "job_id": None,
            }

            # Use proper RunnableConfig type
            config: Dict[str, Dict[str, str]] = {
                "configurable": {"thread_id": str(self.conversation_id)}
            }

            final_state = self.app.invoke(initial_state, config=cast(Any, config))

            if final_state and final_state.get("chat_history"):
                final_messages: list[AIMessage] = [
                    msg for msg in final_state["chat_history"] if isinstance(msg, AIMessage)
                ]
                if final_messages:
                    final_message: AIMessage = final_messages[-1]
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

            # Repopulate with fresh data (excluding conversations)
            self._populate_vectorstore(temp_vectorstore, exclude_conversations=True)

            # Update the instance's vectorstore and retriever
            self.vectorstore: Chroma = temp_vectorstore
            self.retriever: VectorStoreRetriever = self._create_retriever()

            return True
        except Exception as e:
            logger.error(f"Error refreshing vector store for user {self.user_id}: {str(e)}")
            return False

    def _validate_state(self, state: Any) -> Dict[str, Any]:
        """Ensure state is properly formatted before checkpointing"""
        if isinstance(state, tuple):
            return {state[0]: state[1]}  # Convert (key,value) to {key:value}
        elif not isinstance(state, dict):
            raise ValueError(f"Invalid state format: {type(state)}. Expected dict")
        return state
