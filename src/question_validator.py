"""
Question validation for ensuring quiz quality.

This module provides validation logic to ensure generated questions
meet basic quality standards.
"""

import logging
import re
from typing import List, Dict, Any, Tuple

from .models import Question, Quiz


logger = logging.getLogger(__name__)


class QuestionValidator:
    """Validator for ensuring basic question quality."""

    def __init__(
        self,
        min_question_length: int = 10,
        min_option_length: int = 2,
        max_correct_answer_length_ratio: float = 2.0,
        max_correct_answer_extra_words: int = 4,
    ):
        """
        Initialize the question validator.

        Args:
            min_question_length: Minimum length for question text
            min_option_length: Minimum length for each option
            max_correct_answer_length_ratio: Maximum allowed ratio between the
                correct answer's word count and the mean distractor word count
            max_correct_answer_extra_words: Minimum excess over the mean
                distractor word count before the length ratio is enforced
        """
        self.min_question_length = min_question_length
        self.min_option_length = min_option_length
        self.max_correct_answer_length_ratio = max_correct_answer_length_ratio
        self.max_correct_answer_extra_words = max_correct_answer_extra_words

    def validate_question(self, question: Question) -> Tuple[bool, List[str]]:
        """
        Validate a single question for quality issues.

        Args:
            question: The question to validate

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Check question length
        if len(question.question.strip()) < self.min_question_length:
            issues.append(
                f"Question text too short (min {self.min_question_length} chars)"
            )

        # Check if question ends with question mark
        if not question.question.strip().endswith("?"):
            issues.append("Question should end with a question mark")

        # Check options
        option_texts = list(question.options.values())

        # Check option lengths
        for key, option in question.options.items():
            if len(option.strip()) < self.min_option_length:
                issues.append(f"Option {key} is too short")

        # Check for duplicate options
        if len(option_texts) != len(set(option_texts)):
            issues.append("Duplicate answer options found")

        # Check for overly similar options
        similar_pairs = self._find_similar_options(option_texts)
        if similar_pairs:
            issues.append(f"Very similar options found: {similar_pairs}")

        # Check correct answer exists in options
        if question.correct_answer not in question.options:
            issues.append(f"Correct answer '{question.correct_answer}' not in options")
        else:
            length_issue = self._check_correct_answer_length(question)
            if length_issue:
                issues.append(length_issue)

        # Check explanation
        if len(question.explanation.strip()) < 5:
            issues.append("Explanation is too short")

        # Check for common quality issues
        issues.extend(self._check_question_quality(question))

        is_valid = len(issues) == 0
        return is_valid, issues

    def validate_quiz(self, quiz: Quiz) -> Dict[str, Any]:
        """
        Validate an entire quiz.

        Args:
            quiz: The quiz to validate

        Returns:
            Dictionary with validation results
        """
        results = {
            "is_valid": True,
            "total_questions": len(quiz.questions),
            "valid_questions": 0,
            "invalid_questions": 0,
            "question_issues": [],
        }

        for idx, question in enumerate(quiz.questions, 1):
            is_valid, issues = self.validate_question(question)

            if is_valid:
                results["valid_questions"] += 1
            else:
                results["invalid_questions"] += 1
                results["is_valid"] = False
                results["question_issues"].append(
                    {
                        "question_number": idx,
                        "question_text": question.question[:50] + "...",
                        "issues": issues,
                    }
                )

        return results

    def _find_similar_options(
        self, options: List[str], threshold: float = 0.9
    ) -> List[str]:
        """
        Find pairs of very similar options.

        Args:
            options: List of option texts
            threshold: Similarity threshold (0-1)

        Returns:
            List of similar option pairs
        """
        similar_pairs = []

        for i in range(len(options)):
            for j in range(i + 1, len(options)):
                similarity = self._calculate_similarity(options[i], options[j])
                if similarity >= threshold:
                    similar_pairs.append(
                        f"'{options[i][:30]}...' and '{options[j][:30]}...'"
                    )

        return similar_pairs

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate simple similarity between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0-1)
        """
        # Simple word-based similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    def _check_correct_answer_length(self, question: Question) -> str:
        """Flag a correct answer that is conspicuously longer than distractors."""
        distractors = [
            option
            for key, option in question.options.items()
            if key != question.correct_answer
        ]
        if not distractors:
            return ""

        correct_words = len(question.options[question.correct_answer].split())
        mean_distractor_words = sum(
            len(option.split()) for option in distractors
        ) / len(distractors)
        if mean_distractor_words == 0:
            return ""

        excess_words = correct_words - mean_distractor_words
        length_ratio = correct_words / mean_distractor_words
        if (
            excess_words >= self.max_correct_answer_extra_words
            and length_ratio > self.max_correct_answer_length_ratio
        ):
            return (
                "Correct answer is conspicuously longer than the distractors "
                f"({correct_words} words vs. mean of {mean_distractor_words:.1f}); "
                "balance option lengths to avoid giving away the answer"
            )
        return ""

    def _check_question_quality(self, question: Question) -> List[str]:
        """
        Check for common quality issues in questions.

        Args:
            question: The question to check

        Returns:
            List of quality issues found
        """
        issues = []

        q_text = question.question.lower()

        # Check for vague questions
        vague_patterns = [
            r"\bwhich of the following\b",
            r"\ball of the above\b",
            r"\bnone of the above\b",
        ]

        for pattern in vague_patterns:
            if re.search(pattern, q_text):
                # This is actually common in multiple choice, so just log it
                logger.debug(f"Question uses pattern: {pattern}")

        # Check for "all of the above" in options
        for key, option in question.options.items():
            if option.lower() in ["all of the above", "none of the above"]:
                if key == question.correct_answer:
                    issues.append(f"Correct answer should not be '{option}'")

        # Check for overly short questions
        if len(question.question.split()) < 5:
            issues.append("Question is very short, may lack context")

        # Check for overly long questions
        if len(question.question.split()) > 50:
            issues.append("Question is very long, may be confusing")

        return issues

    def filter_valid_questions(
        self, questions: List[Question]
    ) -> Tuple[List[Question], List[Dict[str, Any]]]:
        """
        Filter a list of questions, returning only valid ones.

        Args:
            questions: List of questions to filter

        Returns:
            Tuple of (valid_questions, rejected_questions_with_reasons)
        """
        valid = []
        rejected = []

        for idx, question in enumerate(questions, 1):
            is_valid, issues = self.validate_question(question)

            if is_valid:
                valid.append(question)
            else:
                rejected.append(
                    {
                        "question_number": idx,
                        "question": question.model_dump(),
                        "issues": issues,
                    }
                )

        return valid, rejected


def create_validator(config: Dict[str, Any]) -> QuestionValidator:
    """
    Factory function to create a question validator from configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Configured QuestionValidator instance
    """
    validation_config = config.get("validation", {})

    return QuestionValidator(
        min_question_length=validation_config.get("min_question_length", 10),
        min_option_length=validation_config.get("min_option_length", 2),
    )
