"""
Tests for data models.
"""

import pytest
from pydantic import ValidationError

from src.models import Question, QuizResponse, Quiz


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
