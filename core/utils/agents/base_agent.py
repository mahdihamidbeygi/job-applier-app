from dataclasses import dataclass
from typing import Any, Dict, List

from langchain.memory import ConversationBufferMemory
from langchain_core.memory import BaseMemory

from core.utils.local_llms import OllamaClient


@dataclass
class AgentState:
    memory: BaseMemory
    llm: OllamaClient
    user_id: int


class BaseAgent:
    def __init__(self, user_id: int, model: str = "phi4:latest"):
        self.user_id = user_id
        self.llm = OllamaClient(model=model, temperature=0.0)
        # Initialize memory with basic configuration
        self.memory = ConversationBufferMemory(
            return_messages=True,
            memory_key="chat_history",
            input_key="input",
            output_key="output"
        )
        self.state = AgentState(memory=self.memory, llm=self.llm, user_id=user_id)

    def save_context(self, input_text: str, output_text: str):
        """Save interaction to memory"""
        try:
            # Truncate input and output if they're too long
            input_text = input_text[:500] if len(input_text) > 500 else input_text
            output_text = output_text[:500] if len(output_text) > 500 else output_text
            self.memory.save_context({"input": input_text}, {"output": output_text})
        except Exception as e:
            # If saving fails, clear memory and try again
            self.memory.clear()
            self.memory.save_context({"input": input_text}, {"output": output_text})

    def get_memory(self) -> str:
        """Get formatted memory history"""
        try:
            return self.memory.load_memory_variables({})["chat_history"]
        except Exception:
            return ""

    def clear_memory(self):
        """Clear agent's memory"""
        self.memory.clear()
