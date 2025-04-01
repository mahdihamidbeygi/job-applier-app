from typing import Any, Dict, List

from core.utils.agents.base_agent import BaseAgent
from core.utils.agents.personal_agent import PersonalAgent
from core.utils.rag.job_knowledge import JobKnowledgeBase


class ApplicationAgent(BaseAgent):
    def __init__(self, user_id: int, personal_agent: PersonalAgent):
        super().__init__(user_id)
        self.personal_agent = personal_agent
        self.knowledge_base = JobKnowledgeBase()

    def fill_application_form(
        self, form_fields: List[Dict[str, Any]], job_description: str
    ) -> Dict[str, Any]:
        """Fills out job application forms"""
        # Get company context
        company_context = self.knowledge_base.get_company_context(
            job_description.split("\n")[0]  # Assuming first line contains company name
        )

        responses = {}
        for field in form_fields:
            prompt = f"""
            Field: {field['label']}
            Type: {field['type']}
            Job Context: {job_description[:100]}...
            
            Company Context:
            {company_context}
            
            Relevant Experience:
            {self.personal_agent.get_relevant_experience(field['label'])}
            
            Generate appropriate response that:
            1. Directly answers the field
            2. Demonstrates relevant experience
            3. Aligns with job requirements
            4. Maintains professional tone
            5. Reflects company culture
            """

            response = self.llm.generate(prompt, resp_in_json=False)
            responses[field["id"]] = response
            self.save_context(f"Fill field: {field['label']}", response)

        return responses

    def handle_screening_questions(
        self, questions: List[str], job_context: str
    ) -> List[Dict[str, Any]]:
        """Handles pre-screening questions"""
        # Get relevant interview questions from knowledge base
        relevant_questions = self.knowledge_base.get_relevant_interview_questions(
            job_context.split("\n")[0]  # Assuming first line contains job title
        )

        responses = []
        for question in questions:
            # Get relevant experience for this question
            relevant_background = self.personal_agent.get_relevant_experience(question)

            # Find similar questions in knowledge base
            similar_questions = [
                q for q in relevant_questions if q.get("question", "").lower() in question.lower()
            ]

            prompt = f"""
            Question: {question}
            Job Context: {job_context}
            
            Similar Questions Found:
            {similar_questions}
            
            Relevant Experience:
            {relevant_background}
            
            Provide a concise, focused response (2-3 sentences maximum) that:
            1. Directly answers the question
            2. Demonstrates relevant experience
            3. Aligns with job requirements
            4. Maintains consistency with previous answers
            5. Incorporates insights from similar questions
            """

            response = self.llm.generate(prompt, resp_in_json=False)
            responses.append({"question": question, "answer": response})
            self.save_context(f"Answer question: {question[:50]}...", response)

        return responses

    def generate_cover_letter(self, job_description: str) -> str:
        """Generates a tailored cover letter"""
        # Get company context
        company_context = self.knowledge_base.get_company_context(
            job_description.split("\n")[0]  # Assuming first line contains company name
        )

        prompt = f"""
        Job Description:
        {job_description}
        
        Company Context:
        {company_context}
        
        Candidate Background:
        {self.personal_agent.get_background_summary()}
        
        GitHub Profile:
        {self.personal_agent._format_github_data(self.personal_agent.user_profile.github_data if hasattr(self.personal_agent, 'user_profile') else {})}
        
        Generate a professional cover letter that:
        1. Opens with a strong hook
        2. Highlights relevant experience and GitHub contributions
        3. Demonstrates understanding of the role
        4. Shows enthusiasm for the company
        5. Closes with a call to action
        6. Reflects company culture and values
        7. References specific GitHub projects or contributions when relevant
        
        Format Requirements:
        1. Start with "Dear Hiring Manager," on its own line
        2. Add a blank line after the salutation
        3. Write exactly 3 paragraphs:
           - First paragraph: Introduction and hook
           - Second paragraph: Relevant experience, GitHub contributions, and skills
           - Third paragraph: Closing and call to action
        4. End with "Sincerely," followed by a blank line and the candidate's name
        5. Each paragraph must be unique - do not repeat any sentences or content
        6. Keep paragraphs focused and concise
        
        Return ONLY the formatted cover letter text, with no additional commentary.
        """

        response = self.llm.generate(prompt, resp_in_json=False)

        # Clean up formatting
        # Split into paragraphs and remove empty lines
        paragraphs = [p.strip() for p in response.split("\n") if p.strip()]

        # Remove any duplicate paragraphs while preserving order
        seen = set()
        unique_paragraphs = []
        for p in paragraphs:
            normalized_p = " ".join(p.lower().split())  # Normalize for comparison
            if normalized_p not in seen and p not in ["Dear Hiring Manager,", "Sincerely,"]:
                seen.add(normalized_p)
                unique_paragraphs.append(p)

        # Ensure proper structure
        formatted_parts = []
        formatted_parts.append("Dear Hiring Manager,")  # Salutation
        formatted_parts.extend(unique_paragraphs[:3])  # Main paragraphs (limit to 3)
        formatted_parts.append("Sincerely,")  # Closing
        formatted_parts.append(self.personal_agent.background.profile["name"])  # Name

        # Join with double line breaks
        formatted_letter = "\n\n".join(formatted_parts)

        self.save_context("Generate cover letter", formatted_letter)
        return formatted_letter

    def prepare_interview_responses(self, job_description: str) -> List[Dict[str, Any]]:
        """Prepares potential interview responses"""
        # Get relevant interview questions
        relevant_questions = self.knowledge_base.get_relevant_interview_questions(
            job_description.split("\n")[0]  # Assuming first line contains job title
        )

        prompt = f"""
        Job Description:
        {job_description}
        
        Candidate Background:
        {self.personal_agent.get_background_summary()}
        
        Relevant Interview Questions:
        {relevant_questions}
        
        Generate a JSON response with:
        1. common_questions: list of likely interview questions
        2. responses: list of prepared responses using STAR method
        3. key_points: list of key points to emphasize
        4. questions_to_ask: list of questions for the interviewer
        5. company_specific_prep: company-specific preparation tips
        """

        response = self.llm.generate(prompt, resp_in_json=True)
        self.save_context("Prepare interview responses", response)
        return response
