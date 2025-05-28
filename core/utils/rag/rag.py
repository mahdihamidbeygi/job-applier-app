"""
Retrieval Augmented Generation (RAG) utilities for enhancing LLM responses with user data.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from django.conf import settings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_openai import OpenAIEmbeddings

from core.models import ChatConversation, JobListing, UserProfile
from core.utils.llm_clients import GoogleClient

logger = logging.getLogger(__name__)


class RAGProcessor:
    """
    Retrieval Augmented Generation (RAG) processor.

    This class handles the RAG pipeline for enhancing LLM responses with relevant
    context from user data (profile, job history, etc.).
    """

    def __init__(self, user_id: int, conversation_id: Optional[int] = None):
        """
        Initialize the RAG processor.

        Args:
            user_id: The user's ID
            conversation_id: Optional ID of an existing conversation
        """
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.persist_directory = os.path.join(settings.BASE_DIR, "job_vectors")
        self.initialize_embeddings()
        self.initialize_llm()
        self.initialize_vectorstore()

    def initialize_embeddings(self):
        """Initialize the embedding model."""
        try:
            # Try to use Google embeddings if API key is available
            if os.environ.get("GOOGLE_API_KEY"):
                self.embeddings = GoogleGenerativeAIEmbeddings(
                    model="models/embedding-004",
                    google_api_key=os.environ.get("GOOGLE_API_KEY"),
                )
                logger.info("Using Google AI embeddings")
            else:
                # Fall back to OpenAI embeddings
                self.embeddings = OpenAIEmbeddings()
                logger.info("Using OpenAI embeddings")
        except Exception as e:
            logger.error(f"Error initializing embeddings: {str(e)}")
            # Fallback to OpenAI embeddings
            self.embeddings = OpenAIEmbeddings()

    def initialize_llm(self):
        """Initialize the LLM for generation."""
        try:
            # Use Google Gemini LLM
            self.llm = ChatGoogleGenerativeAI(
                model=settings.PRO_GOOGLE_MODEL,
                google_api_key=os.environ.get("GOOGLE_API_KEY"),
                temperature=0.2,
            )
            self.direct_client = GoogleClient(
                model=settings.PRO_GOOGLE_MODEL,
                temperature=0.2,
                max_tokens=1024,
            )
            logger.info("Using Google Gemini LLM")
        except Exception as e:
            logger.error(f"Error initializing LLM: {str(e)}")
            raise

    def initialize_vectorstore(self):
        """Initialize or load the vector store."""
        try:
            # Check if vector store already exists for this user
            user_persist_dir = os.path.join(self.persist_directory, f"user_{self.user_id}")
            os.makedirs(user_persist_dir, exist_ok=True)

            # Initialize vector store
            self.vectorstore = Chroma(
                persist_directory=user_persist_dir,
                embedding_function=self.embeddings,
            )

            # Check if we need to populate the vectorstore
            if not self.vectorstore._collection.count() > 0:
                self.populate_vectorstore()

            # Create a retriever from the vectorstore
            self.retriever = self.vectorstore.as_retriever(
                search_kwargs={"k": 5, "filter": {"user_id": self.user_id}}
            )
            logger.info(
                f"Vector store initialized with {self.vectorstore._collection.count()} documents"
            )

        except Exception as e:
            logger.error(f"Error initializing vector store: {str(e)}")
            raise

    def populate_vectorstore(self):
        """Populate the vector store with user data."""
        try:
            documents = []

            # Get user profile
            try:
                profile = UserProfile.objects.get(user_id=self.user_id)
                profile_data = profile.get_all_user_info()

                # Add user profile as a document
                profile_doc = Document(
                    page_content=f"User Profile: {profile.full_name}\n\n"
                    + f"Title: {profile.title}\n"
                    + f"Summary: {profile.professional_summary}\n"
                    + f"Years of Experience: {profile.years_of_experience}",
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

            # Get previous job listings
            job_listings = JobListing.objects.filter(user_id=self.user_id)
            for job in job_listings:
                job_doc = Document(
                    page_content=f"Job: {job.title} at {job.company}\n\n"
                    + f"Description: {job.description}\n"
                    + f"Requirements: {job.requirements}",
                    metadata={"type": "job_listing", "user_id": self.user_id, "id": job.id},
                )
                documents.append(job_doc)

            # Get previous conversations if they exist
            conversations = ChatConversation.objects.filter(user_id=self.user_id)
            for conv in conversations:
                # Get the latest 10 messages from this conversation
                messages = conv.messages.order_by("-created_at")[:10]
                if messages:
                    conv_text = f"Previous Conversation (ID: {conv.id}):\n\n"
                    for msg in reversed(messages):
                        conv_text += f"{msg.role.capitalize()}: {msg.content}\n\n"

                    conv_doc = Document(
                        page_content=conv_text,
                        metadata={"type": "conversation", "user_id": self.user_id, "id": conv.id},
                    )
                    documents.append(conv_doc)

            # Add documents to the vectorstore
            if documents:
                self.vectorstore.add_documents(documents)
                self.vectorstore.persist()
                logger.info(f"Added {len(documents)} documents to vector store")
            else:
                logger.warning("No documents found to add to vector store")

        except Exception as e:
            logger.error(f"Error populating vector store: {str(e)}")
            raise

    def query(self, query_text: str) -> str:
        """
        Process a query using RAG, including current conversation history.

        Args:
            query_text: The query text from the user

        Returns:
            The response from the LLM
        """
        try:
            # --- Retrieve Context Documents (Existing Logic) ---
            docs = self.retriever.get_relevant_documents(query_text)
            context = "\n\n".join([doc.page_content for doc in docs])

            # --- Retrieve Current Conversation History ---
            chat_history = []
            if self.conversation_id:
                try:
                    conversation = ChatConversation.objects.get(
                        id=self.conversation_id, user_id=self.user_id
                    )
                    # Get recent messages (e.g., last 10 messages)
                    recent_messages = conversation.messages.order_by("-created_at")[:10]
                    # Format for LangChain (needs to be in reverse order for prompt)
                    for msg in reversed(recent_messages):
                        if msg.role == "user":
                            chat_history.append(HumanMessage(content=msg.content))
                        elif msg.role == "assistant":
                            chat_history.append(AIMessage(content=msg.content))
                except ChatConversation.DoesNotExist:
                    logger.warning(
                        f"Conversation ID {self.conversation_id} not found for user {self.user_id}"
                    )
                except Exception as hist_err:
                    logger.error(
                        f"Error retrieving chat history for conv {self.conversation_id}: {hist_err}"
                    )

            # --- Create the Prompt Template (Include History) ---
            # Note: Adjust the template structure based on your LLM's preference for history placement
            template = """
            You are a helpful job application assistant. Use the following context about the user
            and the ongoing chat history to provide personalized advice and assistance.
            Maintain a friendly, professional tone.

            User Context:
            {context}

            Chat History:
            {chat_history}

            User Question: {question}

            Your response should be helpful, concise and directly address the user's needs based on
            the context and history. If you lack specific information, provide general advice but mention it.
            """
            prompt = ChatPromptTemplate.from_template(template)

            # --- Create the RAG Chain (Pass History) ---
            # We need a way to pass context, question, and history to the prompt
            def format_docs(docs):
                return "\n\n".join(doc.page_content for doc in docs)

            rag_chain = (
                {
                    "context": self.retriever | format_docs,
                    "question": RunnablePassthrough(),
                    "chat_history": lambda x: chat_history,  # Pass the retrieved history
                }
                | prompt
                | self.llm
            )

            # --- Run the Chain ---
            # Pass the user's query text. The chain handles retrieving context and adding history.
            response = rag_chain.invoke(query_text)

            if hasattr(response, "content"):
                return response.content
            return str(response)

        except Exception as e:
            logger.exception(
                f"Error in RAG query for user {self.user_id}: {str(e)}"
            )  # Use logger.exception
            # Fall back to direct LLM (as you already have)
            try:
                # Maybe add a simplified prompt for fallback
                fallback_prompt = (
                    f"User question: {query_text}\n\nProvide a general helpful response."
                )
                return self.direct_client.generate_text(fallback_prompt)
            except Exception as fallback_error:
                logger.error(f"Error in fallback query: {str(fallback_error)}")
                return "I'm sorry, I encountered an error processing your request. Please try again later."

    def refresh_vectorstore(self):
        """Refresh the vector store with updated user data."""
        try:
            # Clear existing data
            self.vectorstore.delete_collection()
            self.vectorstore = Chroma(
                persist_directory=os.path.join(self.persist_directory, f"user_{self.user_id}"),
                embedding_function=self.embeddings,
            )

            # Repopulate with fresh data
            self.populate_vectorstore()

            # Recreate retriever
            self.retriever = self.vectorstore.as_retriever(
                search_kwargs={"k": 5, "filter": {"user_id": self.user_id}}
            )

            logger.info("Vector store refreshed successfully")
            return True
        except Exception as e:
            logger.error(f"Error refreshing vector store: {str(e)}")
            return False
