"""Focused tests for quiz and answer-key output behavior."""

from datetime import datetime

import pytest
from docx import Document

from src.models import Question, Quiz
from src.output_formatter import OutputFormatter


@pytest.fixture
def sample_quiz():
    return Quiz(
        questions=[
            Question(
                question="What is the capital of France?",
                options={"A": "London", "B": "Paris", "C": "Berlin", "D": "Madrid"},
                correct_answer="B",
                explanation="Paris is the capital and largest city of France.",
            ),
            Question(
                question="Which planet is known as the Red Planet?",
                options={"A": "Venus", "B": "Jupiter", "C": "Mars", "D": "Saturn"},
                correct_answer="C",
                explanation="Mars appears red because of iron oxide on its surface.",
            ),
        ],
        source_document="test_document.docx",
        metadata={"generated_at": datetime(2024, 1, 15, 10, 30).isoformat()},
    )


@pytest.fixture
def formatter():
    return OutputFormatter(
        {
            "output": {
                "formats": ["docx", "html"],
                "quiz_dir": "./output/quizzes",
                "answer_key_dir": "./output/answer_keys",
                "include_explanations": True,
            }
        }
    )


def _word_text(path):
    return "\n".join(paragraph.text for paragraph in Document(path).paragraphs)


@pytest.mark.parametrize("output_format", ["docx", "html"])
def test_student_quiz_contains_questions_but_no_answers_or_explanations(
    formatter, sample_quiz, tmp_path, output_format
):
    output_path = tmp_path / f"quiz.{output_format}"
    if output_format == "docx":
        formatter.create_word_quiz(sample_quiz, str(output_path))
        content = _word_text(output_path)
    else:
        formatter.create_html_quiz(sample_quiz, str(output_path))
        content = output_path.read_text(encoding="utf-8")

    assert "What is the capital of France?" in content
    assert "Paris" in content
    assert "Berlin" in content
    assert "test_document.docx" in content
    assert "Correct Answer" not in content
    assert "Explanation:" not in content
    assert "Paris is the capital and largest city" not in content
    assert "✓" not in content


@pytest.mark.parametrize("output_format", ["docx", "html"])
def test_answer_key_contains_answers_and_explanations(
    formatter, sample_quiz, tmp_path, output_format
):
    output_path = tmp_path / f"answers.{output_format}"
    if output_format == "docx":
        formatter.create_word_quiz(sample_quiz, str(output_path), include_answers=True)
        content = _word_text(output_path)
    else:
        formatter.create_html_quiz(sample_quiz, str(output_path), include_answers=True)
        content = output_path.read_text(encoding="utf-8")

    assert "Answer Key" in content
    assert "Correct Answer: B" in content
    assert "Correct Answer: C" in content
    assert "Paris is the capital and largest city" in content
    assert "iron oxide" in content


@pytest.mark.parametrize("include_explanations", [True, False])
def test_answer_key_explanation_setting_is_enforced(
    sample_quiz, tmp_path, include_explanations
):
    formatter = OutputFormatter(
        {"output": {"include_explanations": include_explanations}}
    )
    output_path = tmp_path / "answers.html"
    formatter.create_html_quiz(sample_quiz, str(output_path), include_answers=True)

    content = output_path.read_text(encoding="utf-8")

    assert "Correct Answer: B" in content
    assert ("Paris is the capital and largest city" in content) is include_explanations
    assert ("Explanation" in content) is include_explanations


def test_output_methods_create_expected_filenames(formatter, sample_quiz, tmp_path):
    quiz_paths = formatter.create_quiz_outputs(
        sample_quiz, "paper", output_dir=str(tmp_path), formats=["docx", "html"]
    )
    answer_paths = formatter.create_answer_key_outputs(
        sample_quiz, "paper", output_dir=str(tmp_path), formats=["docx", "html"]
    )

    assert quiz_paths == {
        "docx": str(tmp_path / "paper.docx"),
        "html": str(tmp_path / "paper.html"),
    }
    assert answer_paths == {
        "docx": str(tmp_path / "paper_answers.docx"),
        "html": str(tmp_path / "paper_answers.html"),
    }
    assert all(path.exists() for path in tmp_path.iterdir())
