import logging
from dataclasses import dataclass
from typing import Any, Dict

from langchain.memory import ConversationBufferMemory
from langchain_core.memory import BaseMemory

from core.utils.llm_clients import GoogleClient

logger = logging.getLogger(__name__)
LLM_CLIENT = GoogleClient


@dataclass
class AgentState:
    memory: BaseMemory
    llm: LLM_CLIENT
    user_id: int


class BaseAgent:
    def __init__(
        self,
        user_id: int | None = None,
        job_id: int | None = None,
        model: str = "gemini-2.5-flash-preview-04-17",
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

    def validate_importing_data(self, data: Dict[str, Any], validation_func=None) -> Dict[str, Any]:
        """
        Generic method to update records with validation

        Args:
            data: Dictionary of fields to update
            validation_func: Optional function to validate and clean data

        Returns:
            Updated data dictionary after validation
        """
        try:
            # Validate and clean data if validation function provided
            if validation_func and callable(validation_func):
                validated_data = validation_func(data)
            else:
                validated_data = data

            return validated_data
        except Exception as e:
            logger.error(f"Error updating record: {str(e)}")
            raise ValueError(f"Failed to update record: {str(e)}")

    def update_with_form(self, instance, form_class, data, partial=False):
        """
        Update a model instance using Django ModelForm validation

        Args:
            instance: The model instance to update (or None for create)
            form_class: Django ModelForm class to use for validation
            data: Dictionary containing fields to update
            partial: Whether this is a partial update (only update specified fields)

        Returns:
            Tuple of (bool success, updated_instance or form, str error_message)
        """
        try:
            if partial and instance:
                # For partial updates, first create an empty form to get the fields
                empty_form = form_class(instance=instance)

                # Get the initial data from the instance
                initial_data = {}
                for field_name in empty_form.fields:
                    if hasattr(empty_form, "initial") and field_name in empty_form.initial:
                        initial_data[field_name] = empty_form.initial[field_name]

                # Update only the fields provided in data
                initial_data.update(data)

                # Create the form with the combined data
                form = form_class(initial_data, instance=instance)
            else:
                # For full updates, use the provided data directly
                form = form_class(data, instance=instance)

            if form.is_valid():
                updated_instance = form.save()
                logger.info(
                    f"Successfully updated {form_class.__name__} instance ID: {instance.id if instance else 'new'}"
                )
                return True, updated_instance, ""
            else:
                error_msg = f"Validation failed: {form.errors}"
                logger.warning(f"Form validation failed for {form_class.__name__}: {form.errors}")
                return False, form, error_msg

        except Exception as e:
            logger.error(f"Error updating with form: {str(e)}")
            return False, instance, f"Update failed: {str(e)}"
