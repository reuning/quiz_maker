"""
Tests for data models.
"""

import pytest
from pydantic import ValidationError

from src.models import Question, QuizResponse, Quiz, ValidationResult


class TestQuestion:
    """Tests for Question model."""

    def test_valid_question(self):
        """Test creating a valid question."""
        question = Question(
            question="What is the capital of France?",
            options={"A": "London", "B": "Paris", "C": "Berlin", "D": "Madrid"},
            correct_answer="B",
            explanation="Paris is the capital and largest city of France.",
        )

        assert question.question == "What is the capital of France?"
        assert question.correct_answer == "B"
        assert len(question.options) == 4

    def test_question_missing_option(self):
        """Test that question requires all 4 options."""
        with pytest.raises(ValidationError):
            Question(
                question="What is the capital of France?",
                options={
                    "A": "London",
                    "B": "Paris",
                    "C": "Berlin",
                    # Missing D
                },
                correct_answer="B",
                explanation="Paris is the capital.",
            )

    def test_question_invalid_correct_answer(self):
        """Test that correct_answer must be A-D."""
        with pytest.raises(ValidationError):
            Question(
                question="What is the capital of France?",
                options={"A": "London", "B": "Paris", "C": "Berlin", "D": "Madrid"},
                correct_answer="E",  # Invalid
                explanation="Paris is the capital.",
            )

    def test_question_short_text(self):
        """Test that question text has minimum length."""
        with pytest.raises(ValidationError):
            Question(
                question="What?",  # Too short
                options={"A": "London", "B": "Paris", "C": "Berlin", "D": "Madrid"},
                correct_answer="B",
                explanation="Paris is the capital.",
            )


class TestQuizResponse:
    """Tests for QuizResponse model."""

    def test_valid_quiz_response(self):
        """Test creating a valid quiz response."""
        response = QuizResponse(
            questions=[
                Question(
                    question="What is the capital of France?",
                    options={"A": "London", "B": "Paris", "C": "Berlin", "D": "Madrid"},
                    correct_answer="B",
                    explanation="Paris is the capital.",
                )
            ]
        )

        assert len(response.questions) == 1
        assert response.questions[0].correct_answer == "B"

    def test_empty_quiz_response(self):
        """Test that quiz response requires at least one question."""
        with pytest.raises(ValidationError):
            QuizResponse(questions=[])


class TestQuiz:
    """Tests for Quiz model."""

    def test_valid_quiz(self):
        """Test creating a valid quiz."""
        quiz = Quiz(
            questions=[
                Question(
                    question="What is the capital of France?",
                    options={"A": "London", "B": "Paris", "C": "Berlin", "D": "Madrid"},
                    correct_answer="B",
                    explanation="Paris is the capital.",
                )
            ],
            source_document="test.docx",
            metadata={"author": "test"},
        )

        assert quiz.num_questions == 1
        assert quiz.source_document == "test.docx"
        assert quiz.metadata["author"] == "test"

    def test_quiz_to_dict(self):
        """Test converting quiz to dictionary."""
        quiz = Quiz(
            questions=[
                Question(
                    question="What is the capital of France?",
                    options={"A": "London", "B": "Paris", "C": "Berlin", "D": "Madrid"},
                    correct_answer="B",
                    explanation="Paris is the capital.",
                )
            ],
            source_document=None,
        )

        quiz_dict = quiz.to_dict()
        assert "questions" in quiz_dict
        assert "num_questions" in quiz_dict
        assert quiz_dict["num_questions"] == 1


class TestValidationResult:
    """Tests for ValidationResult model."""

    def test_valid_validation_result(self):
        """Test creating a valid validation result."""
        result = ValidationResult(
            is_relevant=True,
            confidence=0.95,
            reason="Question directly addresses main topic",
        )

        assert result.is_relevant is True
        assert result.confidence == 0.95

    def test_confidence_bounds(self):
        """Test that confidence must be between 0 and 1."""
        with pytest.raises(ValidationError):
            ValidationResult(
                is_relevant=True,
                confidence=1.5,  # Invalid
                reason="Test",
            )
