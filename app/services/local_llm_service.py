"""
Local LLM Service for AI Assistant.

This module provides integration with local LLM services like Ollama,
allowing the AI assistant to use external LLM models for enhanced responses.
"""

import logging
import requests
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class LocalLLMService:
    """Service for interacting with local LLM providers like Ollama."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the local LLM service.
        
        Args:
            config: Local LLM configuration dictionary
        """
        self.config = config
        self.provider = config.get('provider', 'ollama')
        self.base_url = config.get('base_url', 'http://localhost:11434')
        self.api_key = config.get('api_key', '')
        self.model = config.get('model', 'llama2')
        self.timeout = config.get('timeout', 60)
        self.max_tokens = config.get('max_tokens', 2048)
        self.temperature = config.get('temperature', 0.7)
        self.available_models = config.get('available_models', [])
        
        # Ensure base URL doesn't end with slash
        if self.base_url.endswith('/'):
            self.base_url = self.base_url[:-1]
    
    def is_available(self) -> bool:
        """Check if the local LLM service is available."""
        try:
            if self.provider == 'ollama':
                return self._check_ollama_availability()
            else:
                logger.warning(f"Unknown LLM provider: {self.provider}")
                return False
        except Exception as e:
            logger.error(f"Error checking LLM availability: {e}")
            return False
    
    def _check_ollama_availability(self) -> bool:
        """Check if Ollama is available and running."""
        try:
            response = requests.get(f"{self.base_url}/api/version", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Ollama availability check failed: {e}")
            return False
    
    def get_available_models(self) -> List[str]:
        """Get list of available models from the LLM service."""
        try:
            if self.provider == 'ollama':
                return self._get_ollama_models()
            else:
                logger.warning(f"Model listing not supported for provider: {self.provider}")
                return []
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return []
    
    def _get_ollama_models(self) -> List[str]:
        """Get list of available models from Ollama."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                data = response.json()
                models = []
                for model in data.get('models', []):
                    model_name = model.get('name', '')
                    if model_name:
                        # Remove the tag part (e.g., 'llama2:latest' -> 'llama2')
                        base_name = model_name.split(':')[0]
                        if base_name not in models:
                            models.append(base_name)
                return sorted(models)
            else:
                logger.error(f"Failed to get Ollama models: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting Ollama models: {e}")
            return []
    
    def generate_response(self, prompt: str, context: Optional[str] = None, 
                         model: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a response using the local LLM.
        
        Args:
            prompt: The user's prompt/question
            context: Optional context from RAG system
            model: Optional model to use (overrides default)
            
        Returns:
            Dictionary with response data
        """
        try:
            if not self.is_available():
                return {
                    'success': False,
                    'error': 'Local LLM service is not available',
                    'response': 'Local LLM service is currently unavailable. Please check your configuration.',
                    'confidence': 0.0,
                    'method': 'local_llm_error'
                }
            
            model_to_use = model or self.model
            
            if self.provider == 'ollama':
                return self._generate_ollama_response(prompt, context, model_to_use)
            else:
                return {
                    'success': False,
                    'error': f'Unsupported provider: {self.provider}',
                    'response': 'The configured LLM provider is not supported.',
                    'confidence': 0.0,
                    'method': 'local_llm_error'
                }
                
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': 'An error occurred while generating the response.',
                'confidence': 0.0,
                'method': 'local_llm_error'
            }
    
    def _generate_ollama_response(self, prompt: str, context: Optional[str] = None, 
                                 model: Optional[str] = None) -> Dict[str, Any]:
        """Generate response using Ollama API."""
        try:
            # Prepare the full prompt
            full_prompt = self._prepare_prompt(prompt, context)
            
            # Prepare the request payload
            payload = {
                'model': model or self.model,
                'prompt': full_prompt,
                'stream': False,
                'options': {
                    'temperature': self.temperature,
                    'num_predict': self.max_tokens
                }
            }
            
            # Make the request
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                llm_response = data.get('response', '').strip()
                
                if llm_response:
                    return {
                        'success': True,
                        'response': {
                            'diagnosis': self._extract_diagnosis(llm_response),
                            'solution': self._extract_solution(llm_response),
                            'confidence': 0.8,  # LLM responses are generally confident
                            'raw_response': llm_response
                        },
                        'confidence': 0.8,
                        'method': 'local_llm',
                        'model': model or self.model,
                        'provider': self.provider,
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Empty response from LLM',
                        'response': 'The LLM returned an empty response.',
                        'confidence': 0.0,
                        'method': 'local_llm_error'
                    }
            else:
                error_msg = f"LLM API error: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', error_msg)
                except:
                    pass
                
                return {
                    'success': False,
                    'error': error_msg,
                    'response': 'Failed to get response from the LLM service.',
                    'confidence': 0.0,
                    'method': 'local_llm_error'
                }
                
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'Request timeout',
                'response': 'The LLM request timed out. Please try again.',
                'confidence': 0.0,
                'method': 'local_llm_error'
            }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'error': 'Connection error',
                'response': 'Cannot connect to the LLM service. Please check if it is running.',
                'confidence': 0.0,
                'method': 'local_llm_error'
            }
        except Exception as e:
            logger.error(f"Error in Ollama response generation: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': 'An unexpected error occurred while communicating with the LLM.',
                'confidence': 0.0,
                'method': 'local_llm_error'
            }
    
    def _prepare_prompt(self, prompt: str, context: Optional[str] = None) -> str:
        """Prepare the full prompt for the LLM."""
        system_prompt = """You are an AI assistant for a MicroK8s Cluster Orchestrator. You help users with Kubernetes cluster management, troubleshooting, and system administration tasks.

Your responses should be:
- Technical and accurate
- Helpful and actionable
- Focused on MicroK8s and Kubernetes topics
- Clear and concise

Format your responses as:
Diagnosis: [Your analysis of the issue]
Solution: [Step-by-step solution or recommendations]

If you're unsure about something, say so and suggest where to find more information."""

        full_prompt = system_prompt
        
        if context:
            full_prompt += f"\n\nContext from system knowledge base:\n{context}\n"
        
        full_prompt += f"\n\nUser question: {prompt}\n\nPlease provide a helpful response:"
        
        return full_prompt
    
    def _extract_diagnosis(self, response: str) -> str:
        """Extract diagnosis from LLM response."""
        lines = response.split('\n')
        diagnosis_lines = []
        in_diagnosis = False
        
        for line in lines:
            line = line.strip()
            if line.lower().startswith('diagnosis:'):
                in_diagnosis = True
                diagnosis_lines.append(line[10:].strip())  # Remove 'Diagnosis:' prefix
            elif line.lower().startswith('solution:'):
                break
            elif in_diagnosis and line:
                diagnosis_lines.append(line)
        
        return ' '.join(diagnosis_lines) if diagnosis_lines else response[:200] + '...'
    
    def _extract_solution(self, response: str) -> str:
        """Extract solution from LLM response."""
        lines = response.split('\n')
        solution_lines = []
        in_solution = False
        
        for line in lines:
            line = line.strip()
            if line.lower().startswith('solution:'):
                in_solution = True
                solution_lines.append(line[9:].strip())  # Remove 'Solution:' prefix
            elif in_solution and line:
                solution_lines.append(line)
        
        return ' '.join(solution_lines) if solution_lines else response
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the connection to the local LLM service."""
        try:
            if not self.is_available():
                return {
                    'success': False,
                    'error': 'Service is not available',
                    'details': 'Cannot connect to the local LLM service'
                }
            
            # Try a simple test request
            test_response = self.generate_response("Hello, can you respond with 'Test successful'?")
            
            if test_response.get('success'):
                return {
                    'success': True,
                    'message': 'Connection test successful',
                    'model': self.model,
                    'provider': self.provider,
                    'base_url': self.base_url
                }
            else:
                return {
                    'success': False,
                    'error': test_response.get('error', 'Unknown error'),
                    'details': 'Test request failed'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'details': 'Exception during connection test'
            }

# Global instance
_local_llm_service = None

def get_local_llm_service() -> Optional[LocalLLMService]:
    """Get the global local LLM service instance."""
    global _local_llm_service
    if _local_llm_service is None:
        try:
            from ..utils.ai_config import get_ai_config
            ai_config = get_ai_config()
            
            if ai_config.is_local_llm_enabled():
                llm_config = ai_config.get_local_llm_config()
                _local_llm_service = LocalLLMService(llm_config)
            else:
                logger.info("Local LLM service is disabled in configuration")
                
        except Exception as e:
            logger.error(f"Error initializing local LLM service: {e}")
    
    return _local_llm_service
