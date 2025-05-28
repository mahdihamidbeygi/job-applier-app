from typing import Any, Dict, List
import os

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings


class JobKnowledgeBase:
    def __init__(self, persist_directory: str = "./job_vectors"):
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-004",
            google_api_key=os.environ.get("GOOGLE_API_KEY"),
        )
        self.vectorstore = Chroma(
            persist_directory=persist_directory,
            embedding_function=self.embeddings,
            collection_name="job_knowledge",
        )
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

    def add_job_posting(self, job_posting: Dict[str, Any]):
        """Add a job posting to the knowledge base"""
        # Convert job posting to text format
        job_text = f"""
        Title: {job_posting.get('title', '')}
        Company: {job_posting.get('company', '')}
        Description: {job_posting.get('description', '')}
        Required Skills: {', '.join(job_posting.get('required_skills', []))}
        Preferred Skills: {', '.join(job_posting.get('preferred_skills', []))}
        Experience Level: {job_posting.get('experience_level', '')}
        """

        # Split and add to vector store
        texts = self.text_splitter.split_text(job_text)
        self.vectorstore.add_texts(
            texts=texts,
            metadatas=[{"source": "job_posting", "job_id": job_posting.get("id")} for _ in texts],
        )

    def add_company_info(self, company_info: Dict[str, Any]):
        """Add company information to the knowledge base"""
        company_text = f"""
        Company: {company_info.get('name', '')}
        Industry: {company_info.get('industry', '')}
        Culture: {company_info.get('culture', '')}
        Tech Stack: {', '.join(company_info.get('tech_stack', []))}
        """

        texts = self.text_splitter.split_text(company_text)
        self.vectorstore.add_texts(
            texts=texts,
            metadatas=[
                {"source": "company_info", "company_id": company_info.get("id")} for _ in texts
            ],
        )

    def add_interview_questions(self, questions: List[Dict[str, Any]]):
        """Add interview questions and answers to the knowledge base"""
        for q in questions:
            q_text = f"""
            Question: {q.get('question', '')}
            Category: {q.get('category', '')}
            Difficulty: {q.get('difficulty', '')}
            Sample Answer: {q.get('sample_answer', '')}
            """

            texts = self.text_splitter.split_text(q_text)
            self.vectorstore.add_texts(
                texts=texts,
                metadatas=[
                    {"source": "interview_question", "question_id": q.get("id")} for _ in texts
                ],
            )

    def search_similar_jobs(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar jobs based on query"""
        results = self.vectorstore.similarity_search(query, k=k, filter={"source": "job_posting"})
        return [doc.metadata for doc in results]

    def get_company_context(self, company_name: str) -> str:
        """Get relevant company information"""
        results = self.vectorstore.similarity_search(
            company_name, k=3, filter={"source": "company_info"}
        )
        return "\n".join([doc.page_content for doc in results])

    def get_relevant_interview_questions(self, job_title: str, k: int = 5) -> List[Dict[str, Any]]:
        """Get relevant interview questions for a job title"""
        results = self.vectorstore.similarity_search(
            job_title, k=k, filter={"source": "interview_question"}
        )
        return [doc.metadata for doc in results]
