from dataclasses import dataclass
from langchain.memory import ConversationBufferMemory
from core.utils.local_llms import OllamaClient


@dataclass
class AgentState:
    memory: ConversationBufferMemory
    llm: OllamaClient
    user_id: int


class BaseAgent:
    def __init__(self, user_id: int, model: str = "phi4:latest"):
        self.user_id = user_id
        self.llm = OllamaClient(model=model, temperature=0.0)
        self.memory = ConversationBufferMemory(
            memory_key="chat_history", return_messages=True, output_key="output"
        )
        self.state = AgentState(memory=self.memory, llm=self.llm, user_id=user_id)

    def save_context(self, input_text: str, output_text: str):
        """Save interaction to memory"""
        self.memory.save_context({"input": input_text}, {"output": output_text})

    def get_memory(self) -> str:
        """Get formatted memory history"""
        return self.memory.load_memory_variables({})["chat_history"]

    def clear_memory(self):
        """Clear agent's memory"""
        self.memory.clear()
