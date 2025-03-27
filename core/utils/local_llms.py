import requests
import json
import re
from django.conf import settings

class OllamaClient:
    """Client for interacting with Ollama API."""
    def __init__(self, model="phi4:latest"):
        self.model = model
        self.base_url = "http://localhost:11434/api/generate"

    def generate(self, prompt: str) -> str:
        """Generate text using Ollama API."""
        try:
            # First, check if the model is available
            response = requests.get("http://localhost:11434/api/tags")
            response.raise_for_status()
            available_models = [model["name"] for model in response.json()["models"]]
            
            if self.model not in available_models:
                raise Exception(f"Model {self.model} is not available. Available models: {', '.join(available_models)}")

            # Make the generate request with optimized parameters
            response = requests.post(
                self.base_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": settings.temperature,  # Lower temperature for more focused output
                        "num_predict": 2048,  # Increased token limit
                        "top_k": 40,  # Limit token selection
                        "top_p": 0.9,  # Nucleus sampling
                        "repeat_penalty": 1.1,  # Prevent repetition
                        "num_ctx": 4096  # Increased context window size
                    }
                },
                timeout=120  # Increased timeout to 120 seconds
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
                
            # Clean the response to ensure it's valid JSON
            response_text = result["response"]
            # Remove any markdown code block markers
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            # Validate the JSON structure
            try:
                json.loads(response_text)  # Test if it's valid JSON
            except json.JSONDecodeError as e:
                print(f"Invalid JSON after cleaning: {response_text}")
                raise Exception(f"Failed to clean JSON string: {str(e)}")
            
            return response_text
        except requests.exceptions.Timeout:
            raise Exception("Request to Ollama API timed out. The model might be too large or the input too long. Try using a smaller model or reducing the input size.")
        except requests.exceptions.ConnectionError:
            raise Exception("Could not connect to Ollama API. Make sure Ollama is running.")
        except Exception as e:
            raise Exception(f"Error calling Ollama API: {str(e)}")

