"""Focused tests for quiz generation orchestration."""

from unittest.mock import Mock

import pytest

from src.config_manager import ConfigManager
from src.document_processor import DocumentProcessor
from src.llm_interface import LLMInterface
from src.models import Question, Quiz, QuizResponse
from src.question_validator import QuestionValidator
from src.quiz_generator import QuizGenerationError, QuizGenerator


@pytest.fixture
def mock_config():
    config = Mock(spec=ConfigManager)
    config.config = {
        "llm": {"model_path": "test.gguf"},
        "quiz": {"default_questions": 5, "num_options": 4},
    }
    config.get.side_effect = lambda key, default=None: {
        "quiz.default_questions": 5,
        "quiz.num_options": 4,
    }.get(key, default)
    return config


@pytest.fixture
def mock_document_processor():
    processor = Mock(spec=DocumentProcessor)
    processor.process_document.return_value = {
        "text": "This is a sample student paper about Python programming. " * 20,
        "filename": "test.docx",
        "file_type": ".docx",
        "word_count": 100,
        "char_count": 500,
    }
    return processor


def make_question(text="What is Python?", correct_answer="A"):
    return Question(
        question=text,
        options={
            "A": "A programming language",
            "B": "A snake",
            "C": "A framework",
            "D": "A database",
        },
        correct_answer=correct_answer,
        explanation="The paper describes Python as a programming language.",
    )


@pytest.fixture
def mock_llm_interface():
    llm = Mock(spec=LLMInterface)
    llm.model = "test.gguf"
    llm.temperature = 0.7
    llm.generate_quiz.return_value = QuizResponse(
        questions=[make_question(), make_question("What is a variable?", "B")]
    )
    llm.generate_single_question.return_value = make_question("What is a function?")
    return llm


@pytest.fixture
def mock_validator():
    validator = Mock(spec=QuestionValidator)
    validator.validate_question.return_value = (True, [])
    return validator


@pytest.fixture
def quiz_generator(
    mock_config, mock_document_processor, mock_llm_interface, mock_validator
):
    return QuizGenerator(
        config=mock_config,
        document_processor=mock_document_processor,
        llm_interface=mock_llm_interface,
        validator=mock_validator,
    )


def test_generation_preserves_correct_answer_text_through_shuffle(
    quiz_generator, mock_document_processor, mock_llm_interface
):
    original_questions = mock_llm_interface.generate_quiz.return_value.questions
    original_correct_texts = [
        question.options[question.correct_answer] for question in original_questions
    ]

    quiz = quiz_generator.generate_quiz_from_document("test.docx", num_questions=2)

    mock_document_processor.process_document.assert_called_once_with("test.docx")
    mock_llm_interface.generate_quiz.assert_called_once()
    assert isinstance(quiz, Quiz)
    assert quiz.num_questions == 2
    assert quiz.source_document == "test.docx"
    assert quiz.metadata["llm_model"] == "test.gguf"
    assert [
        question.options[question.correct_answer] for question in quiz.questions
    ] == original_correct_texts


def test_generation_uses_configured_question_count(quiz_generator, mock_llm_interface):
    quiz_generator.generate_quiz_from_document("test.docx")

    assert mock_llm_interface.generate_quiz.call_args.kwargs["num_questions"] == 5


def test_validation_can_be_disabled(quiz_generator, mock_validator):
    quiz_generator.generate_quiz_from_document("test.docx", validate_questions=False)

    mock_validator.validate_question.assert_not_called()


def test_document_too_short_is_rejected(quiz_generator, mock_document_processor):
    mock_document_processor.process_document.return_value = {
        "text": "Too short",
        "filename": "short.docx",
        "file_type": ".docx",
        "word_count": 2,
        "char_count": 9,
    }

    with pytest.raises(QuizGenerationError, match="too short"):
        quiz_generator.generate_quiz_from_document("short.docx")


def test_missing_document_error_is_preserved(quiz_generator, mock_document_processor):
    mock_document_processor.process_document.side_effect = FileNotFoundError("missing")

    with pytest.raises(FileNotFoundError):
        quiz_generator.generate_quiz_from_document("missing.docx")


def test_llm_failure_has_actionable_generation_error(
    quiz_generator, mock_llm_interface
):
    mock_llm_interface.generate_quiz.side_effect = RuntimeError("LLM error")

    with pytest.raises(QuizGenerationError, match="Failed to generate quiz"):
        quiz_generator.generate_quiz_from_document("test.docx")


def test_invalid_question_is_regenerated_and_included(
    quiz_generator, mock_validator, mock_llm_interface
):
    original_questions = [make_question(), make_question("What is a variable?", "B")]
    replacement = make_question("What is a function?")
    mock_llm_interface.generate_single_question.return_value = replacement
    mock_validator.validate_question.side_effect = [
        (True, []),
        (False, ["Unbalanced options"]),
        (True, []),
    ]

    valid = quiz_generator._validate_and_regenerate_questions(
        original_questions, "source text", target_count=2, num_options=4
    )

    assert valid == [original_questions[0], replacement]
    call = mock_llm_interface.generate_single_question.call_args
    assert call.kwargs["text"] == "source text"
    assert call.kwargs["num_options"] == 4
    assert call.kwargs["existing_questions"][0] == original_questions[0].question
    assert replacement.question in call.kwargs["existing_questions"]
    assert call.kwargs["max_retries"] == 2


def test_extra_questions_are_trimmed_to_target(quiz_generator):
    questions = [make_question(f"Question {index}?") for index in range(4)]

    valid = quiz_generator._validate_and_regenerate_questions(
        questions, "source text", target_count=2, num_options=4
    )

    assert valid == questions[:2]


def test_all_invalid_questions_produce_clear_failure(quiz_generator, mock_validator):
    mock_validator.validate_question.return_value = (False, ["Invalid"])

    with pytest.raises(QuizGenerationError, match="failed validation"):
        quiz_generator.generate_quiz_from_document("test.docx", num_questions=2)
