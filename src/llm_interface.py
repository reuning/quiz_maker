"""
LLM interface for quiz generation using Ollama.

This module handles communication with local LLM models via Ollama,
including prompt formatting, response parsing, and error handling.
"""

import json
import logging
import time
from typing import Dict, List, Optional, Any
from pydantic import ValidationError

try:
    import ollama
except ImportError:
    ollama = None

from .models import Question, QuizResponse
from .prompts import PromptTemplates


logger = logging.getLogger(__name__)


class LLMInterface:
    """Interface for interacting with Ollama LLM models."""
    
    def __init__(self, model: str = "llama3.1:8b", temperature: float = 0.7, max_tokens: int = 4000):
        """
        Initialize the LLM interface.
        
        Args:
            model: Name of the Ollama model to use
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response
            
        Raises:
            RuntimeError: If Ollama is not installed or not running
        """
        if ollama is None:
            raise RuntimeError(
                "Ollama package not installed. Install with: pip install ollama"
            )
        
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.prompts = PromptTemplates()
        
        # Verify Ollama is running and model is available
        self._verify_ollama_connection()
    
    def _verify_ollama_connection(self) -> None:
        """
        Verify that Ollama is running and the model is available.
        
        Raises:
            RuntimeError: If Ollama is not running or model is not available
        """
        try:
            # List available models
            models_response = ollama.list()
            # Access the models attribute and get the model name from each Model object
            model_names = [m.model for m in models_response.models] if hasattr(models_response, 'models') else []
            
            # Check if our model is available
            if not any(self.model in name for name in model_names):
                logger.warning(f"Model {self.model} not found. Available models: {model_names}")
                logger.info(f"Attempting to pull model {self.model}...")
                # Note: In production, we might want to pull automatically
                # For now, we'll just warn and try to use it anyway
        except Exception as e:
            raise RuntimeError(
                f"Failed to connect to Ollama. Is it running? Error: {str(e)}\n"
                "Start Ollama with: ollama serve"
            )
    
    def generate_quiz(
        self, 
        text: str, 
        num_questions: int = 7, 
        num_options: int = 4,
        max_retries: int = 3
    ) -> QuizResponse:
        """
        Generate a quiz from the provided text.
        
        Args:
            text: Source text to generate questions from
            num_questions: Number of questions to generate
            num_options: Number of answer options per question
            max_retries: Maximum number of retry attempts
            
        Returns:
            QuizResponse containing the generated questions
            
        Raises:
            RuntimeError: If quiz generation fails after all retries
            ValidationError: If LLM response doesn't match expected schema
        """
        prompt = self.prompts.get_quiz_generation_prompt(text, num_questions, num_options)
        system_prompt = self.prompts.get_system_prompt()
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Generating quiz (attempt {attempt + 1}/{max_retries})...")
                
                response = self._call_ollama(prompt, system_prompt)
                quiz_response = self._parse_quiz_response(response)
                
                # Validate we got the requested number of questions
                if len(quiz_response.questions) < num_questions:
                    logger.warning(
                        f"Got {len(quiz_response.questions)} questions, expected {num_questions}"
                    )
                
                logger.info(f"Successfully generated {len(quiz_response.questions)} questions")
                return quiz_response
                
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise RuntimeError(
                        f"Failed to generate valid quiz after {max_retries} attempts. "
                        f"Last error: {str(e)}"
                    )
                time.sleep(1)  # Brief pause before retry
            except Exception as e:
                logger.error(f"Unexpected error during quiz generation: {str(e)}")
                raise RuntimeError(f"Quiz generation failed: {str(e)}")
        
        raise RuntimeError("Quiz generation failed after all retries")
    
    def _call_ollama(self, prompt: str, system_prompt: str) -> str:
        """
        Make a call to Ollama API.
        
        Args:
            prompt: The user prompt
            system_prompt: The system prompt
            
        Returns:
            Raw response text from the LLM
            
        Raises:
            RuntimeError: If the API call fails
        """
        try:
            logger.debug(f"Calling Ollama with model: {self.model}")
            logger.debug(f"System prompt (first 200 chars): {system_prompt[:200]}...")
            logger.debug(f"User prompt (first 200 chars): {prompt[:200]}...")
            
            response = ollama.chat(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': prompt}
                ],
                options={
                    'temperature': self.temperature,
                    'num_predict': self.max_tokens,
                }
            )
            
            logger.debug(f"Response type: {type(response)}")
            logger.debug(f"Response: {response}")
            
            # Handle both dict and object responses
            if isinstance(response, dict):
                logger.debug(f"Response is dict with keys: {response.keys()}")
                content = response['message']['content']
            else:
                # ChatResponse object - access via attributes
                logger.debug(f"Response is ChatResponse object")
                if hasattr(response, 'message'):
                    logger.debug(f"Message: {response.message}")
                    content = response.message.content
                    
                    # Check if content is empty but thinking field exists
                    if not content and hasattr(response.message, 'thinking') and response.message.thinking:
                        logger.error(f"Content is empty but thinking field has {len(response.message.thinking)} chars")
                        logger.error(f"Model used all tokens for reasoning (done_reason: {response.done_reason})")
                        logger.error(f"Increase max_tokens in config.yaml (current: {self.max_tokens})")
                        raise RuntimeError(
                            f"Model returned empty content. All {self.max_tokens} tokens were used for internal reasoning. "
                            f"Increase max_tokens in config.yaml to at least 6000."
                        )
                else:
                    logger.warning(f"Response has no message attribute, converting to string")
                    content = str(response)
            
            logger.debug(f"Content length: {len(content) if content else 0}")
            if content:
                logger.debug(f"Content (first 500 chars): {content[:500]}")
            else:
                logger.error(f"Content is empty!")
                raise RuntimeError("LLM returned empty content")
            
            return content
            
        except Exception as e:
            logger.error(f"Ollama API call failed: {str(e)}", exc_info=True)
            raise RuntimeError(f"Ollama API call failed: {str(e)}")
    
    def _parse_quiz_response(self, response: str) -> QuizResponse:
        """
        Parse LLM response into structured QuizResponse.
        
        Args:
            response: Raw JSON response from LLM
            
        Returns:
            Validated QuizResponse object
            
        Raises:
            json.JSONDecodeError: If response is not valid JSON
            ValidationError: If response doesn't match schema
        """
        # Try to extract JSON from response (LLM might add extra text)
        response = response.strip()
        
        # DEBUG: Log the response for troubleshooting
        logger.debug(f"Raw LLM response (first 500 chars): {response[:500]}")
        
        # Find JSON object in response
        start_idx = response.find('{')
        end_idx = response.rfind('}')
        
        if start_idx == -1 or end_idx == -1:
            logger.error(f"No JSON found in response. Response length: {len(response)}, First 200 chars: {response[:200]}")
            raise json.JSONDecodeError("No JSON object found in response", response, 0)
        
        json_str = response[start_idx:end_idx + 1]
        data = json.loads(json_str)
        
        # Validate using Pydantic model
        return QuizResponse(**data)
    
    def improve_question(
        self, 
        question: Question, 
        issue: str,
        max_retries: int = 2
    ) -> Question:
        """
        Improve a specific question based on identified issues.
        
        Args:
            question: The question to improve
            issue: Description of what needs improvement
            max_retries: Maximum number of retry attempts
            
        Returns:
            Improved Question object
            
        Raises:
            RuntimeError: If improvement fails after all retries
        """
        prompt = self.prompts.get_question_improvement_prompt(
            question.model_dump(), 
            issue
        )
        system_prompt = self.prompts.get_system_prompt()
        
        for attempt in range(max_retries):
            try:
                response = self._call_ollama(prompt, system_prompt)
                
                # Parse response
                response = response.strip()
                start_idx = response.find('{')
                end_idx = response.rfind('}')
                
                if start_idx == -1 or end_idx == -1:
                    raise json.JSONDecodeError("No JSON object found", response, 0)
                
                json_str = response[start_idx:end_idx + 1]
                data = json.loads(json_str)
                
                return Question(**data)
                
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning(f"Question improvement attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Failed to improve question: {str(e)}")
                time.sleep(1)
        
        raise RuntimeError("Question improvement failed after all retries")
    
    def generate_single_question(
        self,
        text: str,
        num_options: int = 4,
        existing_questions: Optional[List[str]] = None,
        max_retries: int = 3
    ) -> Question:
        """
        Generate a single question from the provided text.
        
        Args:
            text: Source text to generate a question from
            num_options: Number of answer options
            existing_questions: List of existing question texts to avoid duplicates
            max_retries: Maximum number of retry attempts
            
        Returns:
            Generated Question object
            
        Raises:
            RuntimeError: If question generation fails after all retries
        """
        prompt = self.prompts.get_single_question_prompt(text, num_options, existing_questions)
        system_prompt = self.prompts.get_system_prompt()
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"Generating single question (attempt {attempt + 1}/{max_retries})...")
                
                response = self._call_ollama(prompt, system_prompt)
                
                # Parse response
                response = response.strip()
                start_idx = response.find('{')
                end_idx = response.rfind('}')
                
                if start_idx == -1 or end_idx == -1:
                    raise json.JSONDecodeError("No JSON object found", response, 0)
                
                json_str = response[start_idx:end_idx + 1]
                data = json.loads(json_str)
                
                question = Question(**data)
                logger.debug(f"Successfully generated single question")
                return question
                
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning(f"Single question generation attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Failed to generate single question: {str(e)}")
                time.sleep(1)
        
        raise RuntimeError("Single question generation failed after all retries")
    
    def validate_question_relevance(
        self, 
        question: Question, 
        source_text: str
    ) -> Dict[str, Any]:
        """
        Validate if a question is relevant to the source text.
        
        Args:
            question: The question to validate
            source_text: The original source text
            
        Returns:
            Dictionary with validation results
        """
        prompt = self.prompts.get_validation_prompt(question.model_dump(), source_text)
        system_prompt = self.prompts.get_system_prompt()
        
        try:
            response = self._call_ollama(prompt, system_prompt)
            
            # Parse response
            response = response.strip()
            start_idx = response.find('{')
            end_idx = response.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx + 1]
                return json.loads(json_str)
            
            # If parsing fails, return default
            return {
                "is_relevant": True,
                "confidence": 0.5,
                "reason": "Could not validate relevance"
            }
            
        except Exception as e:
            logger.warning(f"Question validation failed: {str(e)}")
            return {
                "is_relevant": True,
                "confidence": 0.5,
                "reason": f"Validation error: {str(e)}"
            }


def create_llm_interface(config: Dict[str, Any]) -> LLMInterface:
    """
    Factory function to create an LLM interface from configuration.
    
    Args:
        config: Configuration dictionary with LLM settings
        
    Returns:
        Configured LLMInterface instance
    """
    llm_config = config.get('llm', {})
    
    return LLMInterface(
        model=llm_config.get('model', 'llama3.1:8b'),
        temperature=llm_config.get('temperature', 0.7),
        max_tokens=llm_config.get('max_tokens', 2000)
    )
