import json
import re
from typing import Any, Dict, Optional, Union

import google.generativeai as genai
import requests
from django.conf import settings
from google.api_core import retry
from google.generativeai import types


class OllamaClient:
    """Client for interacting with Ollama API."""

    def __init__(self, model: str = "phi4:latest", temperature: float = settings.TEMPERATURE):
        self.model = model
        self.temperature = temperature
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
                        "num_predict": 2048,
                        "top_k": 40,
                        "top_p": 0.9,
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


class GrokClient:
    """Client for interacting with Grok API."""

    def __init__(self, model: str = "grok-2-1212", temperature: float = settings.TEMPERATURE):
        self.model = model
        self.temperature = temperature
        self.base_url = "https://api.x.ai/v1/chat/completions"
        self.api_key = settings.GROK_API_KEY

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
                    "max_tokens": 2048,
                    "top_p": 0.9,
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


class GoogleClient:
    """Client for interacting with Google's Gemini API using the official google-generativeai library."""

    def __init__(
        self, model: str = settings.GOOGLE_MODEL, temperature: float = settings.TEMPERATURE
    ):
        self.model = model
        self.temperature = temperature
        # Configure the API key
        genai.configure(api_key=settings.GOOGLE_API_KEY)

        # Define a retry policy for API errors
        # This predicate checks if the error is retriable (429 or 503)
        def is_retriable(e):
            return (
                hasattr(e, "code")
                and e.code in {429, 503}
                or (isinstance(e, Exception) and any(code in str(e) for code in ["429", "503"]))
            )

        # Apply retry policy to the GenerativeModel class
        if not hasattr(genai.GenerativeModel.generate_content, "__wrapped__"):
            genai.GenerativeModel.generate_content = retry.Retry(
                predicate=is_retriable, initial=1.0, maximum=60.0, multiplier=2.0
            )(genai.GenerativeModel.generate_content)

    def generate(
        self,
        prompt: str,
        resp_in_json: bool = False,
        response_schema: Optional[Union[Dict[str, Any], Dict[str, type]]] = None,
    ) -> str:
        """Generate text using Google's Gemini API.

        Args:
            prompt (str): The prompt to send to the model
            resp_in_json (bool): Whether to expect and validate JSON response
            response_schema (Optional[Union[Dict[str, Any], Dict[str, type]]]): Optional schema to enforce response structure
        """
        try:
            # Get the model
            model = genai.GenerativeModel(model_name=self.model)

            # If response_schema is provided, add it to the prompt
            if response_schema:
                schema_prompt = f"\nPlease respond in the following JSON schema format:\n{json.dumps(response_schema, indent=2)}"
                prompt = prompt + schema_prompt
                resp_in_json = True  # Force JSON response when schema is provided

            # Generate the response with retry capability built in at the class level
            generation_config = {
                "temperature": self.temperature,
                "top_k": 40,
                "top_p": 0.9,
                "max_output_tokens": 2048,
            }

            response = model.generate_content(prompt, generation_config=generation_config)

            # Extract the response text
            response_text = response.text

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
                    parsed_json = json.loads(response_text)  # Test if it's valid JSON

                    # If schema is provided, validate against it
                    if response_schema:
                        # Basic schema validation
                        if isinstance(response_schema, dict) and isinstance(parsed_json, dict):
                            for key, value_type in response_schema.items():
                                if key not in parsed_json:
                                    raise ValueError(f"Missing required field: {key}")
                                if not isinstance(parsed_json[key], value_type):
                                    raise ValueError(
                                        f"Field {key} has incorrect type. Expected {value_type}, got {type(parsed_json[key])}"
                                    )
                except json.JSONDecodeError as e:
                    print(f"Invalid JSON after cleaning: {response_text}")
                    raise Exception(f"Failed to clean JSON string: {str(e)}")

            return response_text

        except Exception as e:
            if "blocked" in str(e).lower():
                raise Exception(f"Prompt was blocked by Google's safety filters: {str(e)}")
            raise Exception(f"Error calling Google Gemini API: {str(e)}")

    def query_with_grounding(self, prompt: str, model: str = "gemini-2.0-flash"):
        """Generate text with web search grounding enabled.

        Args:
            prompt (str): The prompt to send to the model
            model (str): The model to use, defaults to gemini-2.0-flash

        Returns:
            The response from the model with web search capability
        """
        # Create a model instance with web search capability
        model_instance = genai.GenerativeModel(model_name=model)

        # Call the model with web search enabled
        # The 'tools' parameter enables web search
        try:
            response = model_instance.generate_content(contents=prompt, tools=["web_search"])
            return response
        except Exception as e:
            print(f"Error with web search: {str(e)}")
            # Fall back to regular generation without web search
            return self.generate(prompt)

    def search_grounding_example(self):
        """Example of how to implement web search grounding as per user's request.

        This is a reference implementation showing the exact code pattern
        requested by the user.
        """
        # Example usage of query_with_grounding
        return self.query_with_grounding("When and where is Billie Eilish's next concert?")

    def get_search_grounded_response(self, prompt: str):
        """Get a response with web search grounding."""
        return self.query_with_grounding(prompt)

    def generate_structured_output(
        self, prompt: str, output_schema: Dict[str, Any], model: str = None
    ):
        """Generate structured output in JSON format based on the provided schema.

        Args:
            prompt (str): The prompt to send to the model
            output_schema (Dict[str, Any]): The JSON schema for the expected output
            model (str, optional): Model to use, defaults to the instance's model

        Returns:
            Dict: Parsed JSON response that matches the output schema
        """
        if model is None:
            model = self.model

        model_instance = genai.GenerativeModel(model_name=model)

        # Add schema requirements to the prompt
        enhanced_prompt = f"{prompt}\n\nPlease format your response as a JSON object with the following schema:\n{json.dumps(output_schema, indent=2)}"

        # Generate the response
        generation_config = types.GenerationConfig(
            temperature=self.temperature,
            top_k=40,
            top_p=0.9,
            max_output_tokens=2048,
        )

        response = model_instance.generate_content(
            contents=enhanced_prompt, generation_config=generation_config
        )

        # Extract and clean the JSON response
        response_text = response.text
        response_text = response_text.replace("```json", "").replace("```", "").strip()

        # Extract JSON portion
        start_idx = response_text.find("{")
        end_idx = response_text.rfind("}")

        if start_idx != -1 and end_idx != -1:
            json_text = response_text[start_idx : end_idx + 1]
            return json.loads(json_text)
        else:
            raise Exception("Failed to extract valid JSON from response")
