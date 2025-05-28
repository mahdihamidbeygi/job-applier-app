"""
Local LLM clients for text generation.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict

import httpx
import requests
from django.conf import settings
from google import genai
from google.api_core import retry
from google.genai import types

logger = logging.getLogger(__name__)


class BaseLLMClient:
    """Base class for local LLM clients."""

    def __init__(self, **kwargs) -> None:
        self.model: str = kwargs.get("model", "gemini-2.5-flash-preview-04-17")
        self.temperature: float = kwargs.get("temperature", settings.TEMPERATURE)
        self.api_key: str | None = kwargs.get("api_key", None)
        self.max_tokens: int = kwargs.get("max_tokens", 4096)
        self.temperature: float | None = kwargs.get("temperature", 0.2)
        self.top_k: int = kwargs.get("top_k", 40)
        self.top_p: float = kwargs.get("top_p", 0.95)


class OllamaClient(BaseLLMClient):
    """Client for interacting with Ollama API."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.base_url = "http://localhost:11434/api/generate"

    def generate(self, prompt: str, resp_in_json: bool = False) -> str:
        """Generate text using Ollama API."""
        try:
            # First, check if the model is available
            response = requests.get("http://localhost:11434/api/tags")
            response.raise_for_status()
            available_models = [model["name"] for model in response.json()["models"]]

            if self.model not in available_models:
                raise Exception(
                    f"Model {self.model} is not available. Available models: {', '.join(available_models)}"
                )

            # Make the generate request with optimized parameters
            response = requests.post(
                self.base_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens,
                        "top_k": self.top_k,
                        "top_p": self.top_p,
                        "repeat_penalty": 1.1,
                        "num_ctx": 4096,
                    },
                },
                timeout=120,
            )

            if response.status_code != 200:
                error_msg = f"Ollama API returned status code {response.status_code}"
                try:
                    error_details = response.json()
                    error_msg += f": {error_details.get('error', 'Unknown error')}"
                except:
                    error_msg += f": {response.text}"
                raise Exception(error_msg)

            result = response.json()
            if "error" in result:
                raise Exception(f"Ollama API error: {result['error']}")

            response_text = result["response"]
            if resp_in_json:
                # Remove any markdown code block markers and clean the response
                response_text = response_text.replace("```json", "").replace("```", "").strip()

                # Remove any explanatory text before the JSON
                if "Here is the response in the required format:" in response_text:
                    response_text = response_text.split(
                        "Here is the response in the required format:"
                    )[1].strip()

                # Try to find the first occurrence of { or [ and the last occurrence of } or ]
                start_idx = min(response_text.find("{"), response_text.find("["))
                end_idx = max(response_text.rfind("}"), response_text.rfind("]"))

                if start_idx != -1 and end_idx != -1:
                    response_text = response_text[start_idx : end_idx + 1]
                else:
                    # If no JSON structure found, try to clean the response as a simple array
                    response_text = response_text.strip()
                    if response_text.startswith("["):
                        response_text = response_text[: response_text.rfind("]") + 1]
                    elif response_text.startswith("{"):
                        response_text = response_text[: response_text.rfind("}") + 1]

                # Validate the JSON structure
                try:
                    json.loads(response_text)  # Test if it's valid JSON
                except json.JSONDecodeError as e:
                    print(f"Invalid JSON after cleaning: {response_text}")
                    raise Exception(f"Failed to clean JSON string: {str(e)}")

            return response_text

        except requests.exceptions.Timeout:
            raise Exception(
                "Request to Ollama API timed out. The model might be too large or the input too long. Try using a smaller model or reducing the input size."
            )
        except requests.exceptions.ConnectionError:
            raise Exception("Could not connect to Ollama API. Make sure Ollama is running.")
        except Exception as e:
            raise Exception(f"Error calling Ollama API: {str(e)}")

    def generate_structured_output(self, prompt: str, output_schema: Dict[str, Any]):
        """Generate structured output in JSON format based on the provided schema.

        Args:
            prompt (str): The prompt to send to the model
            output_schema (Dict[str, Any]): The JSON schema for the expected output

        Returns:
            Dict: Parsed JSON response that matches the output schema
        """
        # Add schema requirements to the prompt
        enhanced_prompt = f"{prompt}\n\nPlease format your response as a JSON object with the following schema:\n{json.dumps(output_schema, indent=2)}"

        # Get response with JSON processing enabled
        response_text = self.generate(enhanced_prompt, resp_in_json=True)

        # Parse and return the JSON
        return json.loads(response_text)


class GrokClient(BaseLLMClient):
    """Client for interacting with Grok API."""

    name: str = "grok"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.base_url = "https://api.x.ai/v1/chat/completions"
        self.api_key = kwargs.get("api_key", settings.GROK_API_KEY)

    def generate(self, prompt: str) -> str:
        """Generate text using Grok API."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            # Make the generate request with optimized parameters
            response = requests.post(
                self.base_url,
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                    "top_p": self.top_p,
                    "frequency_penalty": 0.1,
                    "presence_penalty": 0.1,
                },
                timeout=120,
            )

            if response.status_code != 200:
                error_msg = f"Grok API returned status code {response.status_code}"
                try:
                    error_details = response.json()
                    error_msg += f": {error_details.get('error', 'Unknown error')}"
                except:
                    error_msg += f": {response.text}"
                raise Exception(error_msg)

            result = response.json()
            if "error" in result:
                raise Exception(f"Grok API error: {result['error']}")

            # Extract the response text
            response_text = result["choices"][0]["message"]["content"]

            # Clean the response to ensure it's valid JSON
            response_text = response_text.replace("```json", "").replace("```", "").strip()

            # Validate the JSON structure
            try:
                json.loads(response_text)  # Test if it's valid JSON
            except json.JSONDecodeError as e:
                print(f"Invalid JSON after cleaning: {response_text}")
                raise Exception(f"Failed to clean JSON string: {str(e)}")

            return response_text
        except requests.exceptions.Timeout:
            raise Exception(
                "Request to Grok API timed out. The model might be too large or the input too long. Try using a smaller model or reducing the input size."
            )
        except requests.exceptions.ConnectionError:
            raise Exception(
                "Could not connect to Grok API. Please check your internet connection and API key."
            )
        except Exception as e:
            raise Exception(f"Error calling Grok API: {str(e)}")

    def generate_structured_output(self, prompt: str, output_schema: Dict[str, Any]):
        """Generate structured output in JSON format based on the provided schema.

        Args:
            prompt (str): The prompt to send to the model
            output_schema (Dict[str, Any]): The JSON schema for the expected output

        Returns:
            Dict: Parsed JSON response that matches the output schema
        """
        # Add schema requirements to the prompt
        enhanced_prompt = f"{prompt}\n\nPlease format your response as a JSON object with the following schema:\n{json.dumps(output_schema, indent=2)}"

        # Generate response
        response_text = self.generate(enhanced_prompt)

        # Clean the response to extract JSON
        response_text = response_text.replace("```json", "").replace("```", "").strip()

        # Extract JSON portion
        start_idx = response_text.find("{")
        end_idx = response_text.rfind("}")

        if start_idx != -1 and end_idx != -1:
            json_text = response_text[start_idx : end_idx + 1]
            return json.loads(json_text)
        else:
            raise Exception("Failed to extract valid JSON from response")

    def query_with_grounding(self, prompt: str):
        """Generate text with factual information.

        Note: As of implementation, Grok doesn't have an official API for web search grounding.
        This method adds a prompt instruction to use factual information.

        Args:
            prompt (str): The prompt to send to the model

        Returns:
            str: The model's response
        """
        enhanced_prompt = f"{prompt}\n\nPlease ensure your response is factual and up-to-date."
        return self.generate(enhanced_prompt)


class GoogleClient(BaseLLMClient):
    """
    Client for Google's LLM API.

    This client handles text generation requests to Google's language models.
    """

    name: str = "google"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.api_key: str | None = kwargs.get("api_key", os.environ.get("GOOGLE_API_KEY"))

        if not self.api_key:
            logger.warning("No Google API key provided. Using mock responses.")
            return

        is_retriable = lambda e: (isinstance(e, genai.errors.APIError) and e.code in {429, 503})

        # Configure the API
        self.client = genai.Client(api_key=self.api_key)
        is_retriable = lambda e: (isinstance(e, genai.errors.APIError) and e.code in {429, 503})

        if not hasattr(genai.models.Models.generate_content, "__wrapped__"):
            genai.models.Models.generate_content = retry.Retry(predicate=is_retriable)(
                genai.models.Models.generate_content
            )

        self.config = types.GenerationConfig(
            temperature=self.temperature,
            top_k=self.top_k,
            top_p=self.top_p,
            max_output_tokens=self.max_tokens,
        )
        # # Create model with grounding (with proper parameters for the API)
        # self.model_instance = genai.GenerativeModel(
        #     model_name=self.model,
        #     generation_config=self.config,
        #     tools=[genai.web.WebSearchTool()],
        # )

    def generate_text(
        self,
        prompt: str | list,
        **kwargs,
    ) -> str:
        """
        Generate text using Google's LLM.

        Args:
            prompt: The prompt to generate text from
            max_tokens: Maximum number of tokens to generate
            temperature: Temperature for generation (higher = more random)
            top_k: Top-k sampling parameter
            top_p: Top-p sampling parameter
            **kwargs: Additional parameters for the generation

        Returns:
            Generated text as a string
        """
        try:
            # it seems like it caused issue with pydantic validation
            # GenerateContentConfig doesn't "have max_tokens"
            if "max_tokens" in kwargs:
                kwargs["max_output_tokens"] = kwargs.pop("max_tokens")

            # Set up generation config (with proper parameters for the API)
            self.config_with_search = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                **kwargs,
            )

            # Generate response
            response: types.GenerateContentResponse = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=self.config_with_search,
            )

            # Return the text response
            if response and hasattr(response, "text"):
                return response.text
            return "No response generated"

        except Exception as e:
            logger.error(f"Error generating text: {str(e)}")
            raise Exception(f"Error generating text: {str(e)}")

    def generate_structured_output(self, prompt: str, output_schema: Dict[str, Any], **kwargs):
        """Generate structured output in JSON format based on the provided schema.

        Args:
            prompt (str): The prompt to send to the model
            output_schema (Dict[str, Any]): The JSON schema for the expected output
            model (str, optional): Model to use, defaults to the instance's model

        Returns:
            Dict: Parsed JSON response that matches the output schema
        """

        # Add schema requirements to the prompt
        enhanced_prompt: str = (
            f"{prompt}\n\nPlease format your response as a JSON object with the following schema:\n{json.dumps(output_schema, indent=2)}"
        )

        # it seems like it caused issue with pydantic validation
        # GenerateContentConfig doesn't "have max_tokens"
        if "max_tokens" in kwargs:
            kwargs["max_output_tokens"] = kwargs.pop("max_tokens")

        self.config_with_search = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            **kwargs,
        )

        response: types.GenerateContentResponse = self.client.models.generate_content(
            model=self.model,
            contents=enhanced_prompt,
            config=self.config_with_search,
        )

        # Extract and clean the JSON response
        response_text: str | None = response.text
        response_text = response_text.replace("```json", "").replace("```", "").strip()

        # Extract JSON portion
        start_idx: int = response_text.find("{")
        end_idx: int = response_text.rfind("}")

        if start_idx != -1 and end_idx != -1:
            json_text: str = response_text[start_idx : end_idx + 1]
            return json.loads(json_text)
        else:
            raise Exception("Failed to extract valid JSON from response")

    def upload_file(self, file_path: str | Path):
        """
        Upload a file to the Google API.

        Args:
            file_path: Path to the file to upload

        Returns:
            The uploaded file object
        """
        try:
            file_path = Path(file_path)

            response = types.Part.from_bytes(
                data=file_path.read_bytes(),
                mime_type="application/pdf",
            )

            return response
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            raise Exception(f"Error uploading file: {str(e)}")


class OpenAIClient(BaseLLMClient):
    """
    Client for OpenAI's API.

    This client handles text generation requests to OpenAI's language models.
    """

    name: str = "openai"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.api_key = kwargs.get("api_key", os.environ.get("OPENAI_API_KEY"))
        self.model = kwargs.get("model", "gpt-3.5-turbo")
        self.client_loaded = False
        self.client = None

        """
        Initialize the OpenAI client.

        Args:
            api_key: Optional API key (defaults to environment variable OPENAI_API_KEY)
            model: Model to use for text generation
        """

        if not self.api_key:
            logger.warning("No OpenAI API key provided. Using mock responses.")
            return

        # Only import if API key is available
        from openai import OpenAI

        self.client = OpenAI(api_key=self.api_key)
        self.client_loaded = True

    def generate_text(
        self,
        prompt: str,
        **kwargs,
    ) -> str:
        """
        Generate text using OpenAI's API.

        Args:
            prompt: The prompt to generate text from
            max_tokens: Maximum number of tokens to generate
            temperature: Temperature for generation (higher = more random)
            top_p: Top-p sampling parameter
            **kwargs: Additional parameters for the generation

        Returns:
            Generated text as a string
        """
        try:
            # Generate response
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                top_p=kwargs.get("top_p", self.top_p),
                **kwargs,
            )

            # Return the text response
            if hasattr(response, "choices") and response.choices:
                return response.choices[0].message.content or ""
            return "No response generated"
        except Exception as e:
            logger.error(f"Error generating text: {str(e)}")
            raise Exception(f"Error generating text: {str(e)}")
