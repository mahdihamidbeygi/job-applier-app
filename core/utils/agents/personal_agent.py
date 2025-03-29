from typing import Dict, Any, List
from core.utils.agents.base_agent import BaseAgent
from dataclasses import dataclass

@dataclass
class PersonalBackground:
    profile: Dict[str, Any]
    work_experience: List[Dict[str, Any]]
    education: List[Dict[str, Any]]
    skills: List[Dict[str, Any]]
    projects: List[Dict[str, Any]]
    github_data: Dict[str, Any]
    achievements: List[str]
    interests: List[str]

class PersonalAgent(BaseAgent):
    def __init__(self, user_id: int):
        super().__init__(user_id)
        self.background = None
    
    def load_background(self, background: PersonalBackground):
        """Load or update the agent's background knowledge"""
        self.background = background
        self._initialize_self_knowledge()
    
    def _initialize_self_knowledge(self):
        """Initialize the agent with understanding of its own background"""
        prompt = f"""
        You are now embodying a job applicant with the following background:
        
        Professional Experience:
        {self._format_experience(self.background.work_experience)}
        
        Education:
        {self._format_education(self.background.education)}
        
        Skills:
        {', '.join([skill['name'] for skill in self.background.skills])}
        
        Projects:
        {self._format_projects(self.background.projects)}
        
        GitHub Activity:
        {self._format_github_data(self.background.github_data)}
        
        Achievements:
        {', '.join(self.background.achievements)}
        
        You should respond to questions as if you are this person, maintaining consistency
        with this background while being natural and professional.
        """
        
        response = self.llm.generate(prompt, resp_in_json=False)
        self.save_context("Initialize personal background", response)
    
    def get_background_summary(self) -> str:
        """Get a concise summary of the background"""
        return f"""
        Professional Experience: {len(self.background.work_experience)} positions
        Education: {len(self.background.education)} institutions
        Skills: {len(self.background.skills)} skills
        Projects: {len(self.background.projects)} projects
        """
    
    def get_relevant_experience(self, context: str) -> str:
        """Get experience relevant to a specific context"""
        prompt = f"""
        Context: {context}
        
        Based on this background:
        {self.get_background_summary()}
        
        Provide the most relevant experience and skills for this context.
        """
        
        return self.llm.generate(prompt)
    
    def _format_experience(self, experience: List[Dict[str, Any]]) -> str:
        return "\n".join([
            f"- {exp.get('position', '')} at {exp.get('company', '')} "
            f"({exp.get('start_date', '')} - {exp.get('end_date', '')})"
            for exp in experience
        ])
    
    def _format_education(self, education: List[Dict[str, Any]]) -> str:
        return "\n".join([
            f"- {edu.get('degree', '')} from {edu.get('institution', '')} "
            f"({edu.get('start_date', '')} - {edu.get('end_date', '')})"
            for edu in education
        ])
    
    def _format_projects(self, projects: List[Dict[str, Any]]) -> str:
        return "\n".join([
            f"- {proj.get('title', '')} ({', '.join(proj.get('technologies', []))})"
            for proj in projects
        ])
    
    def _format_github_data(self, github_data: Dict[str, Any]) -> str:
        return f"""
        Repositories: {len(github_data.get('repositories', []))}
        Contributions: {github_data.get('contributions', 0)}
        Languages: {', '.join(github_data.get('languages', []))}
        """ 