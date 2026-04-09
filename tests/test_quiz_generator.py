"""
Unit tests for the quiz generator module.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from src.quiz_generator import QuizGenerator, QuizGenerationError, create_quiz_generator
from src.config_manager import ConfigManager
from src.document_processor import DocumentProcessor
from src.llm_interface import LLMInterface
from src.question_validator import QuestionValidator
from src.models import Quiz, Question, QuizResponse


@pytest.fixture
def mock_config():
    """Create a mock configuration manager."""
    config = Mock(spec=ConfigManager)
    config.config = {
        'llm': {
            'model': 'test-model',
            'temperature': 0.7,
            'max_tokens': 2000
        },
        'quiz': {
            'default_questions': 7,
            'num_options': 4
        },
        'output': {
            'formats': ['docx', 'html'],
            'quiz_dir': './output/quizzes',
            'answer_key_dir': './output/answer_keys',
            'include_explanations': True
        },
        'processing': {
            'batch_size': 5,
            'timeout_seconds': 120
        }
    }
    config.get = lambda key, default=None: _get_nested_value(config.config, key, default)
    return config


def _get_nested_value(d, key_path, default=None):
    """Helper to get nested dictionary values using dot notation."""
    keys = key_path.split('.')
    value = d
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
            if value is None:
                return default
        else:
            return default
    return value if value is not None else default


@pytest.fixture
def mock_document_processor():
    """Create a mock document processor."""
    processor = Mock(spec=DocumentProcessor)
    processor.process_document.return_value = {
        'text': 'This is a sample document about Python programming. ' * 20,
        'filename': 'test.docx',
        'file_type': '.docx',
        'word_count': 100,
        'char_count': 500
    }
    return processor


@pytest.fixture
def mock_llm_interface():
    """Create a mock LLM interface."""
    llm = Mock(spec=LLMInterface)
    llm.model = 'test-model'
    llm.temperature = 0.7
    
    # Create sample questions
    sample_questions = [
        Question(
            question="What is Python?",
            options={
                "A": "A programming language",
                "B": "A snake",
                "C": "A framework",
                "D": "A database"
            },
            correct_answer="A",
            explanation="Python is a high-level programming language."
        ),
        Question(
            question="What is a variable?",
            options={
                "A": "A constant value",
                "B": "A storage location",
                "C": "A function",
                "D": "A class"
            },
            correct_answer="B",
            explanation="A variable is a storage location for data."
        )
    ]
    
    llm.generate_quiz.return_value = QuizResponse(questions=sample_questions)
    
    # Mock generate_single_question for regeneration scenarios
    llm.generate_single_question.return_value = Question(
        question="What is a function?",
        options={
            "A": "A reusable block of code",
            "B": "A variable",
            "C": "A class",
            "D": "A module"
        },
        correct_answer="A",
        explanation="A function is a reusable block of code."
    )
    
    return llm


@pytest.fixture
def mock_validator():
    """Create a mock question validator."""
    validator = Mock(spec=QuestionValidator)
    validator.validate_question.return_value = (True, [])
    validator.validate_quiz.return_value = {
        'is_valid': True,
        'total_questions': 2,
        'valid_questions': 2,
        'invalid_questions': 0,
        'question_issues': []
    }
    return validator


@pytest.fixture
def quiz_generator(mock_config, mock_document_processor, mock_llm_interface, mock_validator):
    """Create a quiz generator with mocked dependencies."""
    return QuizGenerator(
        config=mock_config,
        document_processor=mock_document_processor,
        llm_interface=mock_llm_interface,
        validator=mock_validator
    )


class TestQuizGeneratorInit:
    """Tests for QuizGenerator initialization."""
    
    def test_init_with_all_dependencies(self, mock_config, mock_document_processor, 
                                       mock_llm_interface, mock_validator):
        """Test initialization with all dependencies provided."""
        generator = QuizGenerator(
            config=mock_config,
            document_processor=mock_document_processor,
            llm_interface=mock_llm_interface,
            validator=mock_validator
        )
        
        assert generator.config == mock_config
        assert generator.document_processor == mock_document_processor
        assert generator.llm_interface == mock_llm_interface
        assert generator.validator == mock_validator
    
    def test_init_with_defaults(self):
        """Test initialization with default dependencies."""
        with patch('src.quiz_generator.ConfigManager') as mock_config_cls, \
             patch('src.quiz_generator.DocumentProcessor') as mock_proc_cls, \
             patch('src.quiz_generator.create_llm_interface') as mock_llm_fn, \
             patch('src.quiz_generator.create_validator') as mock_val_fn:
            
            generator = QuizGenerator()
            
            # Verify default instances were created
            mock_config_cls.assert_called_once()
            mock_proc_cls.assert_called_once()
            mock_llm_fn.assert_called_once()
            mock_val_fn.assert_called_once()


class TestGenerateQuizFromDocument:
    """Tests for generate_quiz_from_document method."""
    
    def test_successful_generation(self, quiz_generator, mock_document_processor,
                                   mock_llm_interface):
        """Test successful quiz generation."""
        quiz = quiz_generator.generate_quiz_from_document('test.docx', num_questions=2)
        
        # Verify document was processed
        mock_document_processor.process_document.assert_called_once_with('test.docx')
        
        # Verify LLM was called
        mock_llm_interface.generate_quiz.assert_called_once()
        
        # Verify quiz structure
        assert isinstance(quiz, Quiz)
        assert quiz.num_questions == 2
        assert quiz.source_document == 'test.docx'
        assert 'generated_at' in quiz.metadata
        assert 'source_filename' in quiz.metadata
    
    def test_generation_with_custom_num_questions(self, quiz_generator, mock_llm_interface):
        """Test generation with custom number of questions."""
        quiz = quiz_generator.generate_quiz_from_document('test.docx', num_questions=5)
        
        # Verify LLM was called with correct number
        call_args = mock_llm_interface.generate_quiz.call_args
        assert call_args[1]['num_questions'] == 5
    
    def test_generation_uses_default_num_questions(self, quiz_generator, mock_llm_interface):
        """Test that default number of questions is used when not specified."""
        quiz = quiz_generator.generate_quiz_from_document('test.docx')
        
        # Verify LLM was called with default (7)
        call_args = mock_llm_interface.generate_quiz.call_args
        assert call_args[1]['num_questions'] == 7
    
    def test_generation_with_validation_disabled(self, quiz_generator, mock_validator):
        """Test generation with validation disabled."""
        quiz = quiz_generator.generate_quiz_from_document(
            'test.docx',
            validate_questions=False
        )
        
        # Validator should not be called for individual questions
        mock_validator.validate_question.assert_not_called()
        assert isinstance(quiz, Quiz)
    
    def test_generation_with_validation_enabled(self, quiz_generator, mock_validator):
        """Test generation with validation enabled."""
        quiz = quiz_generator.generate_quiz_from_document(
            'test.docx',
            num_questions=2,
            validate_questions=True
        )
        
        # Validator should be called for each question
        assert mock_validator.validate_question.call_count == 2
        assert isinstance(quiz, Quiz)
    
    def test_document_not_found(self, quiz_generator, mock_document_processor):
        """Test handling of missing document."""
        mock_document_processor.process_document.side_effect = FileNotFoundError(
            "File not found: missing.docx"
        )
        
        with pytest.raises(FileNotFoundError):
            quiz_generator.generate_quiz_from_document('missing.docx')
    
    def test_document_too_short(self, quiz_generator, mock_document_processor):
        """Test handling of document with insufficient content."""
        mock_document_processor.process_document.return_value = {
            'text': 'Too short',
            'filename': 'short.docx',
            'file_type': '.docx',
            'word_count': 2,
            'char_count': 9
        }
        
        with pytest.raises(QuizGenerationError) as exc_info:
            quiz_generator.generate_quiz_from_document('short.docx')
        
        assert "too short" in str(exc_info.value).lower()
    
    def test_llm_generation_failure(self, quiz_generator, mock_llm_interface):
        """Test handling of LLM generation failure."""
        mock_llm_interface.generate_quiz.side_effect = RuntimeError("LLM error")
        
        with pytest.raises(QuizGenerationError) as exc_info:
            quiz_generator.generate_quiz_from_document('test.docx')
        
        assert "Failed to generate quiz" in str(exc_info.value)
    
    def test_all_questions_fail_validation(self, quiz_generator, mock_validator):
        """Test handling when all questions fail validation."""
        mock_validator.validate_question.return_value = (False, ["Invalid question"])
        
        with pytest.raises(QuizGenerationError) as exc_info:
            quiz_generator.generate_quiz_from_document('test.docx', validate_questions=True)
        
        assert "failed validation" in str(exc_info.value).lower()
    
    def test_metadata_added_to_quiz(self, quiz_generator):
        """Test that metadata is properly added to generated quiz."""
        quiz = quiz_generator.generate_quiz_from_document('test.docx')
        
        # Check required metadata fields
        assert 'generated_at' in quiz.metadata
        assert 'source_filename' in quiz.metadata
        assert 'source_file_type' in quiz.metadata
        assert 'source_word_count' in quiz.metadata
        assert 'source_char_count' in quiz.metadata
        assert 'llm_model' in quiz.metadata
        assert 'llm_temperature' in quiz.metadata
        
        # Check values
        assert quiz.metadata['source_filename'] == 'test.docx'
        assert quiz.metadata['source_file_type'] == '.docx'
        assert quiz.metadata['source_word_count'] == 100
        assert quiz.metadata['llm_model'] == 'test-model'


class TestValidateQuizQuality:
    """Tests for validate_quiz_quality method."""
    
    def test_validate_quiz_quality(self, quiz_generator, mock_validator):
        """Test quiz quality validation."""
        quiz = Quiz(
            questions=[
                Question(
                    question="Test question?",
                    options={"A": "Option 1", "B": "Option 2", "C": "Option 3", "D": "Option 4"},
                    correct_answer="A",
                    explanation="Test explanation"
                )
            ],
            source_document="test.docx"
        )
        
        result = quiz_generator.validate_quiz_quality(quiz, "source text")
        
        # Verify validator was called
        mock_validator.validate_quiz.assert_called_once_with(quiz, "source text")
        
        # Check result structure matches actual validator output
        assert 'is_valid' in result
        assert 'total_questions' in result
        assert 'valid_questions' in result
        assert 'invalid_questions' in result


class TestGenerateBatch:
    """Tests for batch generation."""
    
    def test_batch_generation_all_successful(self, quiz_generator):
        """Test batch generation with all documents succeeding."""
        doc_paths = ['doc1.docx', 'doc2.docx', 'doc3.docx']
        
        results = quiz_generator.generate_batch(doc_paths)
        
        assert results['total'] == 3
        assert results['success_count'] == 3
        assert results['failure_count'] == 0
        assert len(results['successful']) == 3
        assert len(results['failed']) == 0
    
    def test_batch_generation_with_failures(self, quiz_generator, mock_document_processor):
        """Test batch generation with some failures."""
        doc_paths = ['doc1.docx', 'doc2.docx', 'doc3.docx']
        
        # Make second document fail
        def side_effect(path):
            if 'doc2' in path:
                raise FileNotFoundError(f"File not found: {path}")
            return {
                'text': 'Sample text ' * 20,
                'filename': Path(path).name,
                'file_type': '.docx',
                'word_count': 100,
                'char_count': 500
            }
        
        mock_document_processor.process_document.side_effect = side_effect
        
        results = quiz_generator.generate_batch(doc_paths)
        
        assert results['total'] == 3
        assert results['success_count'] == 2
        assert results['failure_count'] == 1
        assert len(results['successful']) == 2
        assert len(results['failed']) == 1
        
        # Check failed entry
        failed_doc, error = results['failed'][0]
        assert 'doc2' in failed_doc
        assert 'not found' in error.lower()
    
    def test_batch_generation_empty_list(self, quiz_generator):
        """Test batch generation with empty document list."""
        results = quiz_generator.generate_batch([])
        
        assert results['total'] == 0
        assert results['success_count'] == 0
        assert results['failure_count'] == 0
    
    def test_batch_generation_with_custom_num_questions(self, quiz_generator, mock_llm_interface):
        """Test batch generation with custom number of questions."""
        doc_paths = ['doc1.docx', 'doc2.docx']
        
        results = quiz_generator.generate_batch(doc_paths, num_questions=8)
        
        # Verify all LLM calls used the custom number
        for call in mock_llm_interface.generate_quiz.call_args_list:
            assert call[1]['num_questions'] == 8


class TestAddMetadata:
    """Tests for add_metadata method."""
    
    def test_add_metadata(self, quiz_generator):
        """Test adding metadata to a quiz."""
        quiz = Quiz(
            questions=[
                Question(
                    question="What is a test question?",
                    options={"A": "Option 1", "B": "Option 2", "C": "Option 3", "D": "Option 4"},
                    correct_answer="A",
                    explanation="This is a test explanation."
                )
            ],
            source_document="test.docx",
            metadata={'existing': 'value'}
        )
        
        additional = {
            'custom_field': 'custom_value',
            'another_field': 123
        }
        
        updated_quiz = quiz_generator.add_metadata(quiz, additional)
        
        # Check metadata was added
        assert updated_quiz.metadata['existing'] == 'value'
        assert updated_quiz.metadata['custom_field'] == 'custom_value'
        assert updated_quiz.metadata['another_field'] == 123
        
        # Verify it's the same object (modified in place)
        assert updated_quiz is quiz


class TestCreateQuizGenerator:
    """Tests for the factory function."""
    
    def test_create_with_config_path(self):
        """Test creating generator with config path."""
        with patch('src.quiz_generator.ConfigManager') as mock_config_cls:
            mock_config_cls.return_value = Mock(spec=ConfigManager)
            mock_config_cls.return_value.config = {'llm': {}, 'quiz': {}}
            
            generator = create_quiz_generator(config_path='test_config.yaml')
            
            mock_config_cls.assert_called_once_with('test_config.yaml')
            assert isinstance(generator, QuizGenerator)
    
    def test_create_with_config_instance(self, mock_config):
        """Test creating generator with config instance."""
        generator = create_quiz_generator(config=mock_config)
        
        assert generator.config == mock_config
        assert isinstance(generator, QuizGenerator)
    
    def test_create_with_no_args(self):
        """Test creating generator with no arguments."""
        with patch('src.quiz_generator.ConfigManager') as mock_config_cls:
            mock_config_cls.return_value = Mock(spec=ConfigManager)
            mock_config_cls.return_value.config = {'llm': {}, 'quiz': {}}
            
            generator = create_quiz_generator()
            
            mock_config_cls.assert_called_once_with(None)
            assert isinstance(generator, QuizGenerator)


class TestValidateAndRegenerateQuestions:
    """Tests for _validate_and_regenerate_questions method."""
    
    def test_all_questions_valid(self, quiz_generator, mock_validator):
        """Test when all questions are valid."""
        questions = [
            Question(
                question="What is question one?",
                options={"A": "Option 1", "B": "Option 2", "C": "Option 3", "D": "Option 4"},
                correct_answer="A",
                explanation="This is explanation one."
            ),
            Question(
                question="What is question two?",
                options={"A": "Option 1", "B": "Option 2", "C": "Option 3", "D": "Option 4"},
                correct_answer="B",
                explanation="This is explanation two."
            )
        ]
        
        mock_validator.validate_question.return_value = (True, [])
        
        valid = quiz_generator._validate_and_regenerate_questions(
            questions, "source text", target_count=2, num_options=4
        )
        
        assert len(valid) == 2
        assert valid == questions
    
    def test_some_questions_invalid(self, quiz_generator, mock_validator, mock_llm_interface):
        """Test when some questions are invalid and regeneration is needed."""
        questions = [
            Question(
                question="What is question one?",
                options={"A": "Option 1", "B": "Option 2", "C": "Option 3", "D": "Option 4"},
                correct_answer="A",
                explanation="This is explanation one."
            ),
            Question(
                question="What is question two?",
                options={"A": "Option 1", "B": "Option 2", "C": "Option 3", "D": "Option 4"},
                correct_answer="B",
                explanation="This is explanation two."
            )
        ]
        
        # First valid, second invalid, then regenerated question is valid
        mock_validator.validate_question.side_effect = [
            (True, []),
            (False, ["Invalid question"]),
            (True, [])  # For regenerated question
        ]
        
        valid = quiz_generator._validate_and_regenerate_questions(
            questions, "source text", target_count=2, num_options=4
        )
        
        assert len(valid) == 2
        assert valid[0] == questions[0]
    
    def test_all_questions_invalid(self, quiz_generator, mock_validator, mock_llm_interface):
        """Test when all questions are invalid and regeneration is attempted."""
        questions = [
            Question(
                question="What is question one?",
                options={"A": "Option 1", "B": "Option 2", "C": "Option 3", "D": "Option 4"},
                correct_answer="A",
                explanation="This is explanation one."
            )
        ]
        
        # All questions invalid, including regenerated ones
        mock_validator.validate_question.return_value = (False, ["Invalid"])
        
        valid = quiz_generator._validate_and_regenerate_questions(
            questions, "source text", target_count=1, num_options=4, max_retries=1
        )
        
        # Should return empty list since all are invalid
        assert len(valid) == 0


class TestCreateQuizWithMetadata:
    """Tests for _create_quiz_with_metadata method."""
    
    def test_creates_quiz_with_metadata(self, quiz_generator):
        """Test that quiz is created with proper metadata."""
        questions = [
            Question(
                question="What is a test question?",
                options={"A": "Option 1", "B": "Option 2", "C": "Option 3", "D": "Option 4"},
                correct_answer="A",
                explanation="This is a test explanation."
            )
        ]
        
        doc_info = {
            'text': 'Sample text',
            'filename': 'test.docx',
            'file_type': '.docx',
            'word_count': 100,
            'char_count': 500
        }
        
        quiz = quiz_generator._create_quiz_with_metadata(
            questions,
            'path/to/test.docx',
            doc_info
        )
        
        assert isinstance(quiz, Quiz)
        assert quiz.num_questions == 1
        assert quiz.source_document == 'path/to/test.docx'
        
        # Check metadata
        assert quiz.metadata['source_filename'] == 'test.docx'
        assert quiz.metadata['source_file_type'] == '.docx'
        assert quiz.metadata['source_word_count'] == 100
        assert quiz.metadata['source_char_count'] == 500
        assert quiz.metadata['llm_model'] == 'test-model'
        assert quiz.metadata['llm_temperature'] == 0.7
        assert 'generated_at' in quiz.metadata


class TestIntegrationScenarios:
    """Integration-style tests for complete workflows."""
    
    def test_end_to_end_quiz_generation(self, quiz_generator):
        """Test complete quiz generation workflow."""
        quiz = quiz_generator.generate_quiz_from_document(
            'test.docx',
            num_questions=7,
            validate_questions=True
        )
        
        # Verify complete quiz
        assert isinstance(quiz, Quiz)
        assert quiz.num_questions > 0
        assert quiz.source_document == 'test.docx'
        assert len(quiz.metadata) > 0
        
        # Verify questions structure
        for question in quiz.questions:
            assert isinstance(question, Question)
            assert len(question.question) > 0
            assert len(question.options) == 4
            assert question.correct_answer in question.options
            assert len(question.explanation) > 0
    
    def test_batch_processing_workflow(self, quiz_generator):
        """Test batch processing workflow."""
        doc_paths = ['doc1.docx', 'doc2.docx']
        
        results = quiz_generator.generate_batch(
            doc_paths,
            num_questions=5,
            validate_questions=True
        )
        
        assert results['total'] == 2
        assert results['success_count'] == 2
        
        # Verify each quiz
        for doc_path, quiz in results['successful']:
            assert isinstance(quiz, Quiz)
            assert quiz.num_questions > 0
            assert quiz.source_document == doc_path
