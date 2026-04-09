"""
Tests for LLM interface.

Note: These tests mock Ollama responses to avoid requiring a running Ollama instance.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from src.llm_interface import LLMInterface, create_llm_interface
from src.models import Question, QuizResponse
from pydantic import ValidationError


class TestLLMInterface:
    """Tests for LLMInterface class."""
    
    @patch('src.llm_interface.ollama')
    def test_init_success(self, mock_ollama):
        """Test successful initialization."""
        mock_ollama.list.return_value = {
            'models': [{'name': 'llama3.1:8b'}]
        }
        
        llm = LLMInterface(model="llama3.1:8b")
        
        assert llm.model == "llama3.1:8b"
        assert llm.temperature == 0.7
        assert llm.max_tokens == 4000
    
    @patch('src.llm_interface.ollama')
    def test_init_ollama_not_running(self, mock_ollama):
        """Test initialization when Ollama is not running."""
        mock_ollama.list.side_effect = Exception("Connection refused")
        
        with pytest.raises(RuntimeError, match="Failed to connect to Ollama"):
            LLMInterface()
    
    @patch('src.llm_interface.ollama')
    def test_generate_quiz_success(self, mock_ollama):
        """Test successful quiz generation."""
        # Mock Ollama list for initialization
        mock_ollama.list.return_value = {
            'models': [{'name': 'llama3.1:8b'}]
        }
        
        # Mock Ollama chat response
        mock_response = {
            'message': {
                'content': json.dumps({
                    "questions": [
                        {
                            "question": "What is the capital of France?",
                            "options": {
                                "A": "London",
                                "B": "Paris",
                                "C": "Berlin",
                                "D": "Madrid"
                            },
                            "correct_answer": "B",
                            "explanation": "Paris is the capital and largest city of France."
                        }
                    ]
                })
            }
        }
        mock_ollama.chat.return_value = mock_response
        
        llm = LLMInterface()
        result = llm.generate_quiz("France is a country in Europe. Paris is its capital.", num_questions=1)
        
        assert isinstance(result, QuizResponse)
        assert len(result.questions) == 1
        assert result.questions[0].correct_answer == "B"
    
    @patch('src.llm_interface.ollama')
    def test_generate_quiz_with_extra_text(self, mock_ollama):
        """Test parsing quiz when LLM adds extra text around JSON."""
        mock_ollama.list.return_value = {
            'models': [{'name': 'llama3.1:8b'}]
        }
        
        # Mock response with extra text
        mock_response = {
            'message': {
                'content': 'Here is the quiz:\n' + json.dumps({
                    "questions": [
                        {
                            "question": "What is the capital of France?",
                            "options": {
                                "A": "London",
                                "B": "Paris",
                                "C": "Berlin",
                                "D": "Madrid"
                            },
                            "correct_answer": "B",
                            "explanation": "Paris is the capital."
                        }
                    ]
                }) + '\n\nI hope this helps!'
            }
        }
        mock_ollama.chat.return_value = mock_response
        
        llm = LLMInterface()
        result = llm.generate_quiz("Test text", num_questions=1)
        
        assert isinstance(result, QuizResponse)
        assert len(result.questions) == 1
    
    @patch('src.llm_interface.ollama')
    def test_generate_quiz_invalid_json(self, mock_ollama):
        """Test handling of invalid JSON response."""
        mock_ollama.list.return_value = {
            'models': [{'name': 'llama3.1:8b'}]
        }
        
        # Mock invalid response
        mock_response = {
            'message': {
                'content': 'This is not valid JSON'
            }
        }
        mock_ollama.chat.return_value = mock_response
        
        llm = LLMInterface()
        
        with pytest.raises(RuntimeError, match="Failed to generate valid quiz"):
            llm.generate_quiz("Test text", num_questions=1, max_retries=2)
    
    @patch('src.llm_interface.ollama')
    def test_generate_quiz_retry_logic(self, mock_ollama):
        """Test that retry logic works correctly."""
        mock_ollama.list.return_value = {
            'models': [{'name': 'llama3.1:8b'}]
        }
        
        # First call fails, second succeeds
        valid_response = {
            'message': {
                'content': json.dumps({
                    "questions": [
                        {
                            "question": "What is the capital of France?",
                            "options": {
                                "A": "London",
                                "B": "Paris",
                                "C": "Berlin",
                                "D": "Madrid"
                            },
                            "correct_answer": "B",
                            "explanation": "Paris is the capital."
                        }
                    ]
                })
            }
        }
        
        mock_ollama.chat.side_effect = [
            {'message': {'content': 'Invalid'}},  # First attempt fails
            valid_response  # Second attempt succeeds
        ]
        
        llm = LLMInterface()
        result = llm.generate_quiz("Test text", num_questions=1, max_retries=3)
        
        assert isinstance(result, QuizResponse)
        assert mock_ollama.chat.call_count == 2
    
    @patch('src.llm_interface.ollama')
    def test_improve_question(self, mock_ollama):
        """Test question improvement functionality."""
        mock_ollama.list.return_value = {
            'models': [{'name': 'llama3.1:8b'}]
        }
        
        improved_response = {
            'message': {
                'content': json.dumps({
                    "question": "What is the primary function of mitochondria?",
                    "options": {
                        "A": "Protein synthesis",
                        "B": "ATP production",
                        "C": "DNA storage",
                        "D": "Waste removal"
                    },
                    "correct_answer": "B",
                    "explanation": "Mitochondria produce ATP through cellular respiration."
                })
            }
        }
        mock_ollama.chat.return_value = improved_response
        
        llm = LLMInterface()
        original = Question(
            question="What do mitochondria do",  # Missing question mark
            options={"A": "A", "B": "B", "C": "C", "D": "D"},
            correct_answer="B",
            explanation="They make energy"
        )
        
        improved = llm.improve_question(original, "Add question mark and improve clarity")
        
        assert isinstance(improved, Question)
        assert improved.question.endswith('?')


class TestCreateLLMInterface:
    """Tests for LLM interface factory function."""
    
    @patch('src.llm_interface.ollama')
    def test_create_llm_interface_default(self, mock_ollama):
        """Test creating LLM interface with default config."""
        mock_ollama.list.return_value = {
            'models': [{'name': 'llama3.1:8b'}]
        }
        
        config = {}
        llm = create_llm_interface(config)
        
        assert isinstance(llm, LLMInterface)
        assert llm.model == "llama3.1:8b"
    
    @patch('src.llm_interface.ollama')
    def test_create_llm_interface_custom(self, mock_ollama):
        """Test creating LLM interface with custom config."""
        mock_ollama.list.return_value = {
            'models': [{'name': 'mistral:7b'}]
        }
        
        config = {
            "llm": {
                "model": "mistral:7b",
                "temperature": 0.5,
                "max_tokens": 1500
            }
        }
        llm = create_llm_interface(config)
        
        assert llm.model == "mistral:7b"
        assert llm.temperature == 0.5
        assert llm.max_tokens == 1500


class TestPromptGeneration:
    """Tests for prompt generation."""
    
    @patch('src.llm_interface.ollama')
    def test_quiz_generation_prompt_format(self, mock_ollama):
        """Test that quiz generation uses proper prompt format."""
        mock_ollama.list.return_value = {
            'models': [{'name': 'llama3.1:8b'}]
        }
        
        mock_ollama.chat.return_value = {
            'message': {
                'content': json.dumps({
                    "questions": [
                        {
                            "question": "Test question?",
                            "options": {"A": "1", "B": "2", "C": "3", "D": "4"},
                            "correct_answer": "A",
                            "explanation": "Test explanation"
                        }
                    ]
                })
            }
        }
        
        llm = LLMInterface()
        llm.generate_quiz("Test text", num_questions=1)
        
        # Verify chat was called with proper structure
        assert mock_ollama.chat.called
        call_args = mock_ollama.chat.call_args
        messages = call_args[1]['messages']
        
        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert messages[1]['role'] == 'user'
        assert 'Test text' in messages[1]['content']
