"""Tests for preserving answer correctness while shuffling options."""

from unittest.mock import Mock, patch

import pytest

from src.models import Question
from src.quiz_generator import QuizGenerator


@pytest.fixture
def quiz_generator():
    return QuizGenerator(
        config=Mock(config={}),
        document_processor=Mock(),
        llm_interface=Mock(),
        validator=Mock(),
    )


def test_randomization_preserves_question_and_correct_answer(quiz_generator):
    question = Question(
        question="What is the capital of France?",
        options={"A": "London", "B": "Paris", "C": "Berlin", "D": "Madrid"},
        correct_answer="B",
        explanation="Paris is the capital and largest city of France.",
    )

    with patch("src.quiz_generator.random.shuffle", side_effect=lambda items: items.reverse()):
        randomized = quiz_generator._randomize_answer_positions([question])[0]

    assert randomized.options == {
        "A": "Madrid",
        "B": "Berlin",
        "C": "Paris",
        "D": "London",
    }
    assert randomized.correct_answer == "C"
    assert randomized.options[randomized.correct_answer] == "Paris"
    assert randomized.question == question.question
    assert randomized.explanation == question.explanation


def test_randomization_handles_multiple_questions_and_empty_input(quiz_generator):
    questions = [
        Question(
            question=f"Question {index}?",
            options={"A": "One", "B": "Two", "C": "Three", "D": "Four"},
            correct_answer="B",
            explanation=f"Explanation {index}",
        )
        for index in range(3)
    ]

    randomized = quiz_generator._randomize_answer_positions(questions)

    assert quiz_generator._randomize_answer_positions([]) == []
    assert len(randomized) == len(questions)
    for original, shuffled in zip(questions, randomized):
        assert set(shuffled.options.values()) == set(original.options.values())
        assert shuffled.options[shuffled.correct_answer] == "Two"
