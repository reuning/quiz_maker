"""
Data models for quiz generation using Pydantic.

This module defines the structured data models for questions and quizzes.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class Question(BaseModel):
    """A single multiple-choice question."""

    question: str = Field(..., min_length=10, description="The question text")
    options: Dict[str, str] = Field(..., description="Answer options (A, B, C, D)")
    correct_answer: str = Field(
        ..., pattern="^[A-D]$", description="The correct answer key"
    )
    explanation: str = Field(
        ..., min_length=10, description="Explanation of the correct answer"
    )

    @field_validator("options")
    @classmethod
    def validate_options(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Ensure options has exactly 4 entries with keys A, B, C, D."""
        expected_keys = {"A", "B", "C", "D"}
        if set(v.keys()) != expected_keys:
            raise ValueError(
                f"Options must have exactly keys A, B, C, D. Got: {set(v.keys())}"
            )
        for key, value in v.items():
            if not value or not value.strip():
                raise ValueError(f"Option {key} cannot be empty")
        return v

    @field_validator("correct_answer")
    @classmethod
    def validate_correct_answer(cls, v: str, info) -> str:
        """Ensure correct_answer is one of the option keys."""
        # Note: options validation happens first, so we can rely on it
        return v.upper()


class QuizResponse(BaseModel):
    """Response from LLM containing generated questions."""

    questions: List[Question] = Field(
        ..., min_length=1, description="List of generated questions"
    )


class Quiz(BaseModel):
    """A complete quiz with metadata."""

    questions: List[Question] = Field(
        ..., min_length=1, description="List of questions in the quiz"
    )
    source_document: Optional[str] = Field(None, description="Path to source document")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    @property
    def num_questions(self) -> int:
        """Get the number of questions in the quiz."""
        return len(self.questions)

    def to_dict(self) -> Dict[str, Any]:
        """Convert quiz to dictionary format."""
        return {
            "questions": [q.model_dump() for q in self.questions],
            "source_document": self.source_document,
            "metadata": self.metadata,
            "num_questions": self.num_questions,
        }
