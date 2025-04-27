import json
import logging
import os
from typing import Any, Dict, Optional, Sequence

from django.conf import settings
from django.db.models.manager import BaseManager
from django.shortcuts import get_object_or_404  # Import for safe DB lookups
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.memory import ConversationBufferWindowMemory

# Agent related imports
from langchain.tools import StructuredTool  # <-- Import StructuredTool if needed later
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.messages.base import BaseMessage
from langchain_core.prompt_values import PromptValue
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.base import Runnable
from langchain_core.vectorstores.base import VectorStoreRetriever
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

# Existing imports
from langchain_openai import OpenAIEmbeddings
from pydantic import BaseModel, Field  # <-- Import Pydantic

from core.models import (  # Add models needed for tools
    Certification,
    ChatConversation,
    Education,
    JobListing,
    Project,
    Publication,
    Skill,
    UserProfile,
    WorkExperience,
)
from core.models.chat import ChatMessage
from core.utils.agents.application_agent import ApplicationAgent
from core.utils.agents.job_agent import JobAgent
from core.utils.agents.personal_agent import PersonalAgent
from core.utils.db_utils import safe_get_or_none

logger = logging.getLogger(__name__)


class SearchUserContextInput(BaseModel):
    query: str = Field(
        description="Specific question or topic to search for within the user's data."
    )


class GetWorkExperienceInput(BaseModel):
    experience_id: int = Field(description="The integer ID of the specific work experience entry.")


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


class AgenticRAGProcessor:
    """
    Agentic Retrieval Augmented Generation (RAG) processor.

    Uses an LLM agent to decide when and how to retrieve context
    and potentially use other tools to answer user queries.
    """

    def __init__(self, user_id: int, conversation_id: Optional[int] = None):
        """
        Initialize the Agentic RAG processor.
        """
        self.user_id: int = user_id
        self.conversation_id: int | None = conversation_id
        self.persist_directory: str = os.path.join(settings.BASE_DIR, "job_vectors")

        # --- Initialization Steps ---
        self.embeddings: GoogleGenerativeAIEmbeddings | OpenAIEmbeddings = (
            self._initialize_embeddings()
        )
        self.llm: ChatGoogleGenerativeAI = (
            self._initialize_llm()
        )  # Ensure this LLM supports tool calling
        self.vectorstore: Chroma | None = self._initialize_vectorstore(
            exclude_conversations=True
        )  # Exclude convos from vector store
        self.retriever: VectorStoreRetriever | None = self._create_retriever()
        self.tools: list[StructuredTool] = self._initialize_tools()
        self.memory: ConversationBufferWindowMemory = self._initialize_memory()
        self.agent_executor: AgentExecutor = self._initialize_agent()
        # --- End Initialization ---

    def _initialize_embeddings(self):
        """Initialize the embedding model."""
        try:
            if os.environ.get("GOOGLE_API_KEY"):
                embeddings = GoogleGenerativeAIEmbeddings(
                    model="models/embedding-001",
                    google_api_key=os.environ.get("GOOGLE_API_KEY"),
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

    def _initialize_llm(self):
        """Initialize the LLM for generation and agent control."""
        try:
            # Use Google Gemini LLM - Ensure it's a version supporting tool calling
            # Models like 'gemini-1.5-flash-latest' or 'gemini-1.5-pro-latest' are good choices
            llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-pro-latest",  # Or another tool-calling capable model
                google_api_key=os.environ.get("GOOGLE_API_KEY"),
                temperature=0.1,
                convert_system_message_to_human=True,  # Often needed for Gemini function calling
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
            search_kwargs={"k": 5, "filter": {"user_id": self.user_id}}
        )

    def _populate_vectorstore(self, vectorstore, exclude_conversations: bool = False) -> None:
        """Populate the vector store with user data."""
        # This is largely the same as your RAGProcessor.populate_vectorstore,
        # but we add the 'exclude_conversations' logic.
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
            # Don't raise here, allow agent to potentially function without full context initially

    # --- Tool Definitions ---
    # Use the @tool decorator for functions the agent can call

    def search_user_context(self, query: str) -> str:
        """
        Searches the user's profile, resume, work history, projects, skills,
        and past job applications to find relevant information to answer the user's question.
        Use this tool to find context about the user's background.
        Input should be a specific question or topic to search for within the user's data.
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
            profile: UserProfile = UserProfile.objects.get(user_id=self.user_id)
            experience: WorkExperience | None = safe_get_or_none(
                WorkExperience, id=experience_id, profile=profile
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

    def save_job_description(self, job_description_text: str) -> str:
        """
        Parses and saves a job description provided as text to the database.
        Use this tool when the user pastes or provides the full text of a job description
        and wants to save it for later use (like generating documents).
        Input MUST be the full text of the job description.
        Returns a confirmation message with the new Job ID if successful, or an error message.
        """

        # job_description_text: str = args.j / ob_description_text  # Access arg via model instance
        logger.info(f"Agent Tool: save_job_description called for user {self.user_id}")
        if not job_description_text or len(job_description_text) < 50:  # Basic validation
            return "Please provide the full job description text for me to save."
        try:
            # Instantiate JobAgent with the text. This triggers parsing and saving.
            # The user_id is taken from self.user_id of the AgenticRAGProcessor instance.
            job_agent = JobAgent(user_id=self.user_id, text=job_description_text)

            # Check if the job_record was successfully created
            if job_agent.job_record and job_agent.job_record.id:
                new_job_id: int = job_agent.job_record.id
                job_title: str = job_agent.job_record.title
                company: str = job_agent.job_record.company
                logger.info(
                    f"Successfully saved job description as Job ID: {new_job_id} for user {self.user_id}"
                )
                # Return a helpful message including the ID, prompting the next action
                return (
                    f"OK. I've saved the job description for '{job_title}' at '{company}' as Job ID: {new_job_id}. "
                    f"Would you like me to generate a resume or cover letter for this job now?"
                )
            else:
                logger.error(
                    f"JobAgent failed to create a job record from text for user {self.user_id}"
                )
                return "Sorry, I encountered an issue while trying to parse and save the job description. Please ensure the text is a valid job description."

        except ValueError as ve:  # Catch potential errors during JobAgent init or parsing
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
        # job_id: int = args.job_id  # Access arg via model instance
        logger.info(
            f"Agent Tool: generate_tailored_resume called for job ID: {job_id} for user {self.user_id}"
        )
        try:
            # Verify the job exists and belongs to the user
            job_listing = get_object_or_404(JobListing, id=job_id, user_id=self.user_id)

            # Initialize necessary agents for ApplicationAgent
            personal_agent = PersonalAgent(user_id=self.user_id)
            # Use the modified JobAgent constructor to load by ID
            job_agent = JobAgent(user_id=self.user_id, job_id=job_id)

            # Initialize ApplicationAgent
            application_agent = ApplicationAgent(
                user_id=self.user_id,
                personal_agent=personal_agent,
                job_agent=job_agent,
            )

            # Call the generation method within ApplicationAgent
            # Assuming generate_resume() saves the file and returns the URL
            resume_url = application_agent.generate_resume()

            if resume_url:
                logger.info(f"Successfully generated resume for job {job_id}. URL: {resume_url}")
                # Provide a user-friendly confirmation message
                return f"OK. I have generated your tailored resume for the '{job_listing.title}' position at '{job_listing.company}'. You can access it here: {resume_url}"
            else:
                logger.error(f"ApplicationAgent failed to generate resume URL for job {job_id}")
                return "Sorry, I encountered an issue while generating the resume file."

        except JobListing.DoesNotExist:
            logger.warning(
                f"generate_tailored_resume tool: JobListing ID {job_id} not found for user {self.user_id}"
            )
            return f"I couldn't find a job with ID {job_id} associated with your account. Please double-check the ID."
        except json.JSONDecodeError as json_err:  # <-- CATCH JSONDecodeError FIRST
            logger.error(
                f"generate_tailored_resume tool: Failed to parse LLM response during resume generation for job {job_id}: {json_err}"
            )
            # Optionally log the raw response that failed to parse if possible
            return f"Sorry, I encountered an issue processing the data to generate the resume for job {job_id}. The internal language model might have returned an unexpected format. Please try again."
        except (
            ValueError
        ) as ve:  # Catch other ValueErrors (like from JobAgent init if it truly fails there)
            logger.warning(
                f"generate_tailored_resume tool: Value error during processing for job ID {job_id}: {ve}"
            )
            # Keep the original message here ONLY if the error truly comes from JobAgent init
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
        # job_id: int = args.job_id  # Access arg via model instance
        logger.info(
            f"Agent Tool: generate_tailored_cover_letter called for job ID: {job_id} for user {self.user_id}"
        )
        try:
            # Verify the job exists and belongs to the user
            job_listing: JobListing = get_object_or_404(JobListing, id=job_id, user_id=self.user_id)

            # Initialize necessary agents for ApplicationAgent
            personal_agent = PersonalAgent(user_id=self.user_id)
            # Use the modified JobAgent constructor to load by ID
            job_agent = JobAgent(user_id=self.user_id, job_id=job_id)

            # Initialize ApplicationAgent
            application_agent = ApplicationAgent(
                user_id=self.user_id,
                personal_agent=personal_agent,
                job_agent=job_agent,
            )

            # Call the generation method within ApplicationAgent
            # Assuming generate_cover_letter() saves the file and returns the URL
            cover_letter_url = application_agent.generate_cover_letter()

            if cover_letter_url:
                logger.info(
                    f"Successfully generated cover letter for job {job_id}. URL: {cover_letter_url}"
                )
                # Provide a user-friendly confirmation message
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
        except ValueError as ve:  # Catch error from JobAgent init if job not found
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
            # Alternatively, construct the string manually:
            # details = (
            #     f"Job Details (ID: {job_listing.id}):\n"
            #     f"Title: {job_listing.title}\n"
            #     f"Company: {job_listing.company}\n"
            #     f"Location: {job_listing.location}\n"
            #     f"Posted Date: {job_listing.posted_date}\n"
            #     f"Source: {job_listing.source}\n"
            #     f"URL: {job_listing.source_url}\n\n"
            #     f"Description:\n{job_listing.description}\n\n"
            #     f"Requirements:\n{job_listing.requirements}\n\n"
            #     # Add other relevant fields like salary, benefits if available
            # )
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
        """
        Analyzes provided text (like interview questions or a job description snippet)
        in the context of the user's background to answer a specific user query.
        Use this when the user provides context directly in the chat and asks a question about it
        that requires knowledge of their profile (skills, experience).

        Args:
            context_text: The text provided by the user (e.g., interview questions, job snippet).
            user_query: The specific question the user wants answered based on the context_text and their background.
        """
        logger.info(
            f"Agent Tool: analyze_text_with_background called for user {self.user_id}. Query: '{user_query}'"
        )
        try:
            # 1. Get User Background (using PersonalAgent is direct)
            # Ensure PersonalAgent is initialized correctly if needed, or retrieve from vector store
            personal_agent = PersonalAgent(
                user_id=self.user_id
            )  # Assumes PersonalAgent can be initialized here
            background_summary = (
                personal_agent.get_formatted_background()
            )  # Or use get_background_str()

            # 2. Construct a prompt for the LLM combining background, context_text, and query
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

            # 3. Call the LLM (using the agent's LLM instance)
            response: str = self.llm.generate_text(
                prompt, temperature=0.1, max_tokens=1000
            )  # Adjust max_tokens as needed

            logger.info("Successfully generated analysis using text and background.")
            return response

        except Exception as e:
            logger.exception(
                f"Error in analyze_text_with_background tool for user {self.user_id}: {str(e)}"
            )
            return f"An unexpected error occurred during analysis: {str(e)}"

    def get_profile_summary(self) -> str:
        """
        Retrieves a formatted summary of the user's profile, including work experience,
        education, skills, and projects directly from their saved profile data.
        Use this as a quick way to get the user's overall background if vector search fails or is too slow.
        """
        logger.info(f"Agent Tool: get_profile_summary called for user {self.user_id}")
        try:
            personal_agent = PersonalAgent(user_id=self.user_id)
            # Use the method that returns a dictionary or well-formatted string
            summary_data = personal_agent.get_formatted_background()
            # Convert dict to string if necessary for the agent
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

    # Add more tools as needed (e.g., get_profile_summary, search_web, trigger_document_generation)

    def _initialize_tools(self) -> list[StructuredTool]:
        """Gather all defined tools for the agent using StructuredTool."""
        tools: list[StructuredTool] = [
            StructuredTool.from_function(
                func=self.search_user_context,  # Pass the bound method
                name="search_user_context",
                description=self.search_user_context.__doc__,  # Use docstring
                args_schema=SearchUserContextInput,
            ),
            StructuredTool.from_function(
                func=self.get_specific_work_experience,  # Pass the bound method
                name="get_specific_work_experience",
                description=self.get_specific_work_experience.__doc__,  # Use docstring
                args_schema=GetWorkExperienceInput,
            ),
            StructuredTool.from_function(
                func=self.save_job_description,  # Pass the bound method
                name="save_job_description",
                description=self.save_job_description.__doc__,  # Use docstring
                args_schema=SaveJobDescriptionInput,
            ),
            StructuredTool.from_function(
                func=self.generate_tailored_resume,  # Pass the bound method
                name="generate_tailored_resume",
                description=self.generate_tailored_resume.__doc__,  # Use docstring
                args_schema=GenerateDocumentInput,
            ),
            StructuredTool.from_function(
                func=self.generate_tailored_cover_letter,  # Pass the bound method
                name="generate_tailored_cover_letter",
                description=self.generate_tailored_cover_letter.__doc__,  # Use docstring
                args_schema=GenerateDocumentInput,
            ),
            StructuredTool.from_function(
                func=self.get_job_details,
                name="get_job_details",
                description=self.get_job_details.__doc__,
                args_schema=GetJobDetailsInput,  # Use the new schema
            ),
            StructuredTool.from_function(
                func=self.analyze_text_with_background,
                name="analyze_text_with_background",
                description=self.analyze_text_with_background.__doc__,
                args_schema=AnalyzeTextWithBackgroundInput,  # Use the new schema
            ),
            StructuredTool.from_function(
                func=self.get_profile_summary,
                name="get_profile_summary",
                description=self.get_profile_summary.__doc__,
                # No args_schema needed as it takes no arguments
            ),
        ]
        return tools

    def _initialize_memory(self) -> ConversationBufferWindowMemory:
        """Initialize conversation memory, loading from DB if conversation_id exists."""
        memory = ConversationBufferWindowMemory(
            k=10,  # Number of past interactions to keep
            memory_key="chat_history",
            input_key="input",  # Key for user input in agent chain
            output_key="output",  # Key for agent output in agent chain
            return_messages=True,  # Return Message objects
        )

        # Load existing messages if conversation_id is provided
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
                            memory.chat_memory.add_user_message(msg.content)
                        elif msg.role == "assistant":
                            memory.chat_memory.add_ai_message(msg.content)
                    logger.info(
                        f"Loaded {messages.count()} messages into memory for conversation {self.conversation_id}"
                    )
            except Exception as e:
                logger.error(
                    f"Error loading chat history for conversation {self.conversation_id}: {str(e)}"
                )

        return memory

    def _initialize_agent(self) -> AgentExecutor:
        """Create the agent and agent executor using Tool Calling."""

        # 1. Define Custom Instructions (Similar to before, but adapted)
        #    Focus on clear instructions about tool usage and priorities.
        #    No need for ReAct formatting instructions.
        custom_instructions: str = f"""
        **AGENT BEHAVIOR RULES (User ID: {self.user_id}):**

        You are a helpful job application assistant for User ID {self.user_id}.
        Your goal is to assist the user with their job search and application process using the available tools and context.

        **CONTEXT AND TOOL USAGE GUIDELINES:**

        **VERY IMPORTANT RULE FOR BACKGROUND QUESTIONS:**
        - When the user asks questions like "What do you know about my background?", "What are my skills?", "Tell me about my experience", or any question asking about *their own profile information*, you **MUST** use the `search_user_context` tool first.
        - If `search_user_context` fails or returns insufficient information, you MAY then use the `get_profile_summary` tool as a fallback.
        - **DO NOT** answer questions about the user's background based on general knowledge, assumptions, or by inferring from job listings mentioned in the chat. Only use information retrieved via the specified tools (`search_user_context`, `get_profile_summary`).

        **OTHER TOOL USAGE GUIDELINES:**

        1.  **CHECK CHAT HISTORY:** Before using any tool, review the recent `chat_history`. If the user recently provided specific text (like interview answers, job description snippets) and asks a question *about that text*, prioritize using `analyze_text_with_background` or incorporate the chat context directly in your reasoning if appropriate.
        2.  **USE `search_user_context` for GENERAL BACKGROUND:** For general questions about the user's background, skills, experience, education, projects, or suitability for a role (when specific text isn't provided in chat), **ALWAYS** use the `search_user_context` tool first. If the tool returns no relevant info, state that clearly.
        3.  **USE `get_profile_summary` as FALLBACK:** Only use `get_profile_summary` if `search_user_context` fails or is insufficient for a background query.
        4.  **USE `analyze_text_with_background` for SPECIFIC TEXT + BACKGROUND:** When the user provides specific text (e.g., interview questions/answers) in the chat and asks how it relates to their background or how to improve it, use the `analyze_text_with_background` tool. Provide both the text and the user's query to the tool.
        5.  **USE `get_job_details` for SAVED JOBS:** If the user asks about a specific job previously saved (mentioning its ID), use the `get_job_details` tool with the `job_id`.
        6.  **USE `save_job_description` for SAVING:** When the user provides the *full text* of a job description and asks to save it, use the `save_job_description` tool. Confirm the action by stating the Job ID.
        7.  **CHECK IDs for GENERATION:** Before using `generate_tailored_resume` or `generate_tailored_cover_letter`, check `chat_history` or `input` for a specific Job ID. If unclear, ASK the user for the ID. DO NOT GUESS.
        8.  **Report Tool Results:** Clearly state the outcome of tool actions. Report errors clearly.
        9.  **General Conversation:** If no specific tool or context is relevant, engage in helpful conversation based on history and general knowledge, but remember the **VERY IMPORTANT RULE** about background questions.
        """
        # 2. Create the ChatPromptTemplate for Tool Calling
        #    Note the placeholders: input, chat_history, agent_scratchpad
        prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages(
            [
                ("system", custom_instructions),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),  # Crucial placeholder
            ]
        )

        # 3. Bind Tools to LLM (Optional but Recommended for some models/versions)
        #    This explicitly tells the LLM which tools it can call.
        #    Depending on the LangChain version and Gemini model, this might be
        #    handled automatically by create_tool_calling_agent, but being explicit can help.
        llm_with_tools: Runnable[
            PromptValue
            | str
            | Sequence[BaseMessage | list[str] | tuple[str, str] | str | dict[str, Any]],
            BaseMessage,
        ] = self.llm.bind_tools(
            self.tools
        )  # Uncomment if needed

        # 4. Create the Tool Calling Agent
        #    Pass the LLM (potentially llm_with_tools), tools, and prompt.
        agent = create_tool_calling_agent(
            # self.llm, # Use this if not using bind_tools explicitly
            llm=llm_with_tools,  # Or use llm_with_tools if you uncommented above
            tools=self.tools,
            prompt=prompt,
        )

        # 5. Create the AgentExecutor (Configuration is similar)
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,  # Keep verbose=True for debugging tool calls
            handle_parsing_errors=True,  # Still useful for unexpected issues
            max_iterations=8,  # Can likely reduce this significantly from ReAct's needs
            metadata={"user_id": self.user_id},
            # return_intermediate_steps=True, # Less critical for debugging tool calling vs ReAct, but can keep
        )
        return agent_executor

    def run(self, user_input: str) -> str:
        """
        Run the agentic RAG process for a given user input.

        Args:
            user_input: The query text from the user

        Returns:
            The agent's final response string
        """
        try:
            logger.info(
                f"Running Agentic RAG for user {self.user_id}, conversation {self.conversation_id}"
            )
            # --- Add Memory Logging ---
            try:
                memory_vars: dict[str, Any] = self.memory.load_memory_variables({})
                logger.debug(f"Memory variables before invoke: {memory_vars}")
            except Exception as mem_err:
                logger.error(f"Could not load memory variables for logging: {mem_err}")
            # --- End Memory Logging ---

            # Invoke the agent executor. It handles the LLM calls, tool execution, and memory updates.
            response: Dict[str, Any] = self.agent_executor.invoke(
                {
                    "input": user_input,
                },
                # Add config here to use langsmith.
                config={"metadata": {"user_id": self.user_id}},
            )

            # The actual response is typically in the 'output' key
            agent_response = response.get(
                "output", "Sorry, I encountered an issue processing your request."
            )

            # --- Persist Memory Changes (Optional but Recommended) ---
            # If the memory isn't automatically saving, you might need to manually
            # extract the latest AI message from memory and save it to ChatMessage
            # This depends heavily on how you integrate memory persistence.
            # For now, we assume the view will save user/assistant messages.

            return agent_response

        except Exception as e:
            logger.exception(
                f"Error during Agentic RAG execution for user {self.user_id}: {str(e)}"
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
