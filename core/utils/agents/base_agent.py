from dataclasses import dataclass

from langchain.memory import ConversationBufferMemory
from langchain_core.memory import BaseMemory

from core.utils.local_llms import GoogleClient

LLM_CLIENT = GoogleClient


@dataclass
class AgentState:
    memory: BaseMemory
    llm: LLM_CLIENT
    user_id: int


class BaseAgent:
    def __init__(
        self, user_id: int | None = None, job_id: int | None = None, model: str = "gemini-2.0-flash"
    ) -> None:
        self.user_id: int | None = user_id
        self.job_id: int | None = job_id
        self.llm: LLM_CLIENT = LLM_CLIENT(model=model)
        if self.user_id is not None:
            # Initialize memory with basic configuration
            self.memory_user = ConversationBufferMemory(
                return_messages=True,
                memory_key="chat_history",
                input_key="input",
                output_key="output",
            )
            self.state_user = AgentState(memory=self.memory_user, llm=self.llm, user_id=user_id)

    def save_context(self, input_text: str, output_text: str):
        """Save interaction to memory"""
        try:
            # Truncate input and output if they're too long
            input_text = input_text[:500] if len(input_text) > 500 else input_text
            output_text = output_text[:500] if len(output_text) > 500 else output_text
            self.memory_user.save_context({"input": input_text}, {"output": output_text})
        except Exception as e:
            # If saving fails, clear memory and try again
            self.memory_user.clear()
            self.memory_user.save_context({"input": input_text}, {"output": output_text})

    def get_memory(self) -> str:
        """Get formatted memory history"""
        try:
            return self.memory_user.load_memory_variables({})["chat_history"]
        except Exception:
            return ""

    def clear_memory(self):
        """Clear agent's memory"""
        self.memory_user.clear()
