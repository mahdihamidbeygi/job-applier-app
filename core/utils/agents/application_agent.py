from typing import Dict, Any, List
from core.utils.agents.base_agent import BaseAgent
from core.utils.agents.personal_agent import PersonalAgent
from core.utils.rag.job_knowledge import JobKnowledgeBase

class ApplicationAgent(BaseAgent):
    def __init__(self, user_id: int, personal_agent: PersonalAgent):
        super().__init__(user_id)
        self.personal_agent = personal_agent
        self.knowledge_base = JobKnowledgeBase()
    
    def fill_application_form(self, form_fields: List[Dict[str, Any]], job_description: str) -> Dict[str, Any]:
        """Fills out job application forms"""
        # Get company context
        company_context = self.knowledge_base.get_company_context(
            job_description.split('\n')[0]  # Assuming first line contains company name
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
            responses[field['id']] = response
            self.save_context(f"Fill field: {field['label']}", response)
        
        return responses
    
    def handle_screening_questions(self, questions: List[str], job_context: str) -> List[Dict[str, Any]]:
        """Handles pre-screening questions"""
        # Get relevant interview questions from knowledge base
        relevant_questions = self.knowledge_base.get_relevant_interview_questions(
            job_context.split('\n')[0]  # Assuming first line contains job title
        )
        
        responses = []
        for question in questions:
            # Get relevant experience for this question
            relevant_background = self.personal_agent.get_relevant_experience(question)
            
            # Find similar questions in knowledge base
            similar_questions = [
                q for q in relevant_questions 
                if q.get('question', '').lower() in question.lower()
            ]
            
            prompt = f"""
            Question: {question}
            Job Context: {job_context}
            
            Similar Questions Found:
            {similar_questions}
            
            Relevant Experience:
            {relevant_background}
            
            Provide a professional response that:
            1. Directly answers the question
            2. Demonstrates relevant experience
            3. Aligns with job requirements
            4. Maintains consistency with previous answers
            5. Incorporates insights from similar questions
            """
            
            response = self.llm.generate(prompt, resp_in_json=False)
            responses.append({
                'question': question,
                'answer': response
            })
            self.save_context(f"Answer question: {question[:50]}...", response)
        
        return responses
    
    def generate_cover_letter(self, job_description: str) -> str:
        """Generates a tailored cover letter"""
        # Get company context
        company_context = self.knowledge_base.get_company_context(
            job_description.split('\n')[0]  # Assuming first line contains company name
        )
        
        prompt = f"""
        Job Description:
        {job_description}
        
        Company Context:
        {company_context}
        
        Candidate Background:
        {self.personal_agent.get_background_summary()}
        
        Generate a compelling cover letter that:
        1. Opens with a strong hook
        2. Highlights relevant experience
        3. Demonstrates understanding of the role
        4. Shows enthusiasm for the company
        5. Closes with a call to action
        6. Reflects company culture and values
        """
        
        response = self.llm.generate(prompt, resp_in_json=False)
        self.save_context("Generate cover letter", response)
        return response
    
    def prepare_interview_responses(self, job_description: str) -> List[Dict[str, Any]]:
        """Prepares potential interview responses"""
        # Get relevant interview questions
        relevant_questions = self.knowledge_base.get_relevant_interview_questions(
            job_description.split('\n')[0]  # Assuming first line contains job title
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