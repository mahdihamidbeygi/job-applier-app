import requests
import json
import re
from django.conf import settings

class OllamaClient:
    """Client for interacting with Ollama API."""
    def __init__(self, model:str="phi4:latest", temperature:float=settings.TEMPERATURE):
        self.model = model
        self.temperature = temperature
        self.base_url = "http://localhost:11434/api/generate"

    def generate(self, prompt: str, resp_in_json:bool=False) -> str:
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
                        "temperature": self.temperature,
                        "num_predict": 2048,
                        "top_k": 40,
                        "top_p": 0.9,
                        "repeat_penalty": 1.1,
                        "num_ctx": 4096
                    }
                },
                timeout=120
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

class GrokClient:
    """Client for interacting with Grok API."""
    def __init__(self, model:str="grok-2-1212", temperature:float=settings.TEMPERATURE):
        self.model = model
        self.temperature = temperature
        self.base_url = "https://api.x.ai/v1/chat/completions"
        self.api_key = settings.GROK_API_KEY

    def generate(self, prompt: str) -> str:
        """Generate text using Grok API."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
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
                    "presence_penalty": 0.1
                },
                timeout=120
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
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            # Validate the JSON structure
            try:
                json.loads(response_text)  # Test if it's valid JSON
            except json.JSONDecodeError as e:
                print(f"Invalid JSON after cleaning: {response_text}")
                raise Exception(f"Failed to clean JSON string: {str(e)}")
            
            return response_text
        except requests.exceptions.Timeout:
            raise Exception("Request to Grok API timed out. The model might be too large or the input too long. Try using a smaller model or reducing the input size.")
        except requests.exceptions.ConnectionError:
            raise Exception("Could not connect to Grok API. Please check your internet connection and API key.")
        except Exception as e:
            raise Exception(f"Error calling Grok API: {str(e)}")

