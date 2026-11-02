"""
Tests for question validator.
"""

from src.models import Question, Quiz
from src.question_validator import QuestionValidator


class TestQuestionValidator:
    """Tests for QuestionValidator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = QuestionValidator()
        self.valid_question = Question(
            question="What is the primary function of mitochondria in cells?",
            options={
                "A": "Protein synthesis",
                "B": "Energy production through ATP",
                "C": "DNA replication",
                "D": "Waste removal",
            },
            correct_answer="B",
            explanation="Mitochondria are known as the powerhouse of the cell, producing ATP.",
        )

    def test_validate_valid_question(self):
        """Test validation of a valid question."""
        is_valid, issues = self.validator.validate_question(self.valid_question)

        assert is_valid is True
        assert len(issues) == 0

    def test_validate_question_without_question_mark(self):
        """Test that questions without question marks are flagged."""
        question = Question(
            question="What is the capital of France",  # No question mark
            options={"A": "London", "B": "Paris", "C": "Berlin", "D": "Madrid"},
            correct_answer="B",
            explanation="Paris is the capital of France.",
        )

        is_valid, issues = self.validator.validate_question(question)

        assert is_valid is False
        assert any("question mark" in issue.lower() for issue in issues)

    def test_validate_question_too_short(self):
        """Test that very short questions are flagged."""
        # Use model_construct to bypass Pydantic validation for testing
        question = Question.model_construct(
            question="Capital?",
            options={"A": "London", "B": "Paris", "C": "Berlin", "D": "Madrid"},
            correct_answer="B",
            explanation="Paris is the capital.",
        )

        is_valid, issues = self.validator.validate_question(question)

        assert is_valid is False
        assert any("short" in issue.lower() for issue in issues)

    def test_validate_duplicate_options(self):
        """Test that duplicate options are detected."""
        question = Question(
            question="What is the capital of France?",
            options={
                "A": "Paris",
                "B": "Paris",  # Duplicate
                "C": "Berlin",
                "D": "Madrid",
            },
            correct_answer="A",
            explanation="Paris is the capital.",
        )

        is_valid, issues = self.validator.validate_question(question)

        assert is_valid is False
        assert any("duplicate" in issue.lower() for issue in issues)

    def test_validate_conspicuously_long_correct_answer(self):
        """Test that a much longer correct answer is flagged as a giveaway."""
        question = Question(
            question="In your paper, which conclusion did you draw about reform?",
            options={
                "A": "It failed",
                "B": "It stalled",
                "C": "It reversed",
                "D": "It gradually succeeded because local organizers built durable coalitions",
            },
            correct_answer="D",
            explanation="The paper connects gradual reform to durable local coalitions.",
        )

        is_valid, issues = self.validator.validate_question(question)

        assert is_valid is False
        assert any("conspicuously longer" in issue for issue in issues)

    def test_validate_allows_balanced_option_lengths(self):
        """Test that ordinary length differences do not reject a question."""
        is_valid, issues = self.validator.validate_question(self.valid_question)

        assert is_valid is True
        assert not any("conspicuously longer" in issue for issue in issues)

    def test_validate_quiz(self):
        """Test validation of an entire quiz."""
        quiz = Quiz(
            questions=[
                self.valid_question,
                Question(
                    question="What is the process by which plants convert light energy?",
                    options={
                        "A": "Process of making food",
                        "B": "Conversion of light energy",
                        "C": "Process of respiration",
                        "D": "Process of cell division",
                    },
                    correct_answer="B",
                    explanation="Photosynthesis converts light energy to chemical energy.",
                ),
            ],
            source_document="test.docx",
        )

        results = self.validator.validate_quiz(quiz)

        assert results["is_valid"] is True
        assert results["total_questions"] == 2
        assert results["valid_questions"] == 2
        assert results["invalid_questions"] == 0

    def test_validate_quiz_with_invalid_questions(self):
        """Test validation of quiz with some invalid questions."""
        # Use model_construct to bypass Pydantic validation
        invalid_question = Question.model_construct(
            question="Short?",  # Invalid
            options={"A": "Yes", "B": "No", "C": "Maybe", "D": "Unknown"},
            correct_answer="A",
            explanation="Test",
        )

        quiz = Quiz(
            questions=[self.valid_question, invalid_question],
            source_document="test.docx",
        )

        results = self.validator.validate_quiz(quiz)

        assert results["is_valid"] is False
        assert results["total_questions"] == 2
        assert results["valid_questions"] == 1
        assert results["invalid_questions"] == 1
        assert len(results["question_issues"]) > 0

    def test_calculate_similarity(self):
        """Test similarity calculation."""
        text1 = "The quick brown fox"
        text2 = "The quick brown dog"

        similarity = self.validator._calculate_similarity(text1, text2)

        assert 0.0 <= similarity <= 1.0
        assert similarity > 0.5  # Should be fairly similar
