"""
Question validation for ensuring quiz quality.

This module provides validation logic to ensure generated questions
meet quality standards and are relevant to the source material.
"""

import logging
import re
from typing import List, Dict, Any, Tuple

from .models import Question, Quiz


logger = logging.getLogger(__name__)


class QuestionValidator:
    """Validator for ensuring question quality and relevance."""

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

    def validate_question(
        self, question: Question, source_text: str = ""
    ) -> Tuple[bool, List[str]]:
        """
        Validate a single question for quality issues.

        Args:
            question: The question to validate
            source_text: Optional source text to check relevance

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

        # Check relevance to source text if provided
        if source_text:
            relevance_issues = self._check_relevance(question, source_text)
            issues.extend(relevance_issues)

        is_valid = len(issues) == 0
        return is_valid, issues

    def validate_quiz(self, quiz: Quiz, source_text: str = "") -> Dict[str, Any]:
        """
        Validate an entire quiz.

        Args:
            quiz: The quiz to validate
            source_text: Optional source text to check relevance

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
            is_valid, issues = self.validate_question(question, source_text)

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

        # Check for duplicate questions
        duplicate_issues = self._check_duplicate_questions(quiz.questions)
        if duplicate_issues:
            results["is_valid"] = False
            results["question_issues"].extend(duplicate_issues)

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

    def _check_relevance(self, question: Question, source_text: str) -> List[str]:
        """
        Check if question is relevant to source text.

        Args:
            question: The question to check
            source_text: The source text

        Returns:
            List of relevance issues
        """
        issues = []

        # Extract key terms from question
        q_words = set(re.findall(r"\b\w{4,}\b", question.question.lower()))
        source_words = set(re.findall(r"\b\w{4,}\b", source_text.lower()))

        # Check if question has some overlap with source
        overlap = q_words.intersection(source_words)

        if len(overlap) < 2:
            issues.append(
                "Question may not be relevant to source text (low keyword overlap)"
            )

        return issues

    def _check_duplicate_questions(
        self, questions: List[Question]
    ) -> List[Dict[str, Any]]:
        """
        Check for duplicate or very similar questions.

        Args:
            questions: List of questions to check

        Returns:
            List of duplicate issue dictionaries
        """
        issues = []

        for i in range(len(questions)):
            for j in range(i + 1, len(questions)):
                similarity = self._calculate_similarity(
                    questions[i].question, questions[j].question
                )

                if similarity > 0.8:
                    issues.append(
                        {
                            "question_number": f"{i + 1} and {j + 1}",
                            "question_text": "Duplicate questions detected",
                            "issues": [
                                f"Questions {i + 1} and {j + 1} are very similar (similarity: {similarity:.2f})"
                            ],
                        }
                    )

        return issues

    def filter_valid_questions(
        self, questions: List[Question], source_text: str = ""
    ) -> Tuple[List[Question], List[Dict[str, Any]]]:
        """
        Filter a list of questions, returning only valid ones.

        Args:
            questions: List of questions to filter
            source_text: Optional source text for relevance checking

        Returns:
            Tuple of (valid_questions, rejected_questions_with_reasons)
        """
        valid = []
        rejected = []

        for idx, question in enumerate(questions, 1):
            is_valid, issues = self.validate_question(question, source_text)

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
