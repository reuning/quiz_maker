"""
Prompt templates for LLM-based quiz generation.

This module contains structured prompts for generating multiple-choice questions
from document text using a local LLM.
"""

from typing import Dict, Any, List, Optional


class PromptTemplates:
    """Collection of prompt templates for quiz generation."""

    @staticmethod
    def get_quiz_generation_prompt(text: str, num_questions: int) -> str:
        """
        Generate a prompt for creating multiple-choice questions from text.

        Args:
            text: The source text to generate questions from
            num_questions: Number of questions to generate

        Returns:
            Formatted prompt string for the LLM
        """
        prompt = f"""You are creating a multiple-choice quiz for the student who wrote the following paper. The purpose is to test whether the author can recall the arguments, claims, evidence, and distinctions in their own writing. Generate {num_questions} high-quality questions about this specific paper.

STUDENT'S PAPER:
{text}

INSTRUCTIONS:
1. Create {num_questions} multiple-choice questions with 4 options each (A, B, C, D)
2. Address the student as the paper's author, for example: "In your paper, which argument did you use to...?" or "Which conclusion did you draw about...?"
3. Test recall of what the student actually wrote, not general knowledge or understanding of the broader subject
4. Each question must have exactly ONE correct answer supported by the paper
5. Incorrect options should be plausible but clearly inconsistent with the paper's specific claims
6. Questions should cover different arguments and parts of the paper
7. Avoid trivial questions about wording, titles, or formatting
8. Make all options similar in length and specificity; do not make the correct answer noticeably longer or more detailed than the distractors
9. Include brief explanations that refer to the student's own argument or claim

OUTPUT FORMAT:
You must respond with valid JSON in this exact format:
{{
  "questions": [
    {{
      "question": "The question text here?",
      "options": {{
        "A": "First option",
        "B": "Second option",
        "C": "Third option",
        "D": "Fourth option"
      }},
      "correct_answer": "A",
      "explanation": "Brief explanation of why this is correct"
    }}
  ]
}}

Generate the quiz now:"""
        return prompt

    @staticmethod
    def get_question_improvement_prompt(question: Dict[str, Any], issue: str) -> str:
        """
        Generate a prompt for improving a specific question.

        Args:
            question: The question dictionary to improve
            issue: Description of what needs improvement

        Returns:
            Formatted prompt string for the LLM
        """
        prompt = f"""The following multiple-choice question needs improvement:

QUESTION:
{question.get("question", "")}

OPTIONS:
{chr(10).join(f"{k}: {v}" for k, v in question.get("options", {}).items())}

CORRECT ANSWER: {question.get("correct_answer", "")}

ISSUE TO FIX:
{issue}

Please provide an improved version that addresses the issue. The question should address the student as the paper's author and test recall of their own arguments or claims. Keep every option similar in length and specificity so the correct answer is not given away. Respond with valid JSON in this format:
{{
  "question": "Improved question text?",
  "options": {{
    "A": "First option",
    "B": "Second option",
    "C": "Third option",
    "D": "Fourth option"
  }},
  "correct_answer": "A",
  "explanation": "Brief explanation"
}}"""
        return prompt

    @staticmethod
    def get_system_prompt() -> str:
        """
        Get the system prompt that sets the LLM's role and behavior.

        Returns:
            System prompt string
        """
        return """You are an expert educational content creator who quizzes college students on papers they wrote themselves. Your questions should:
- Address the student as the author (for example, "In your paper, you argued...")
- Test recall of the student's own arguments, claims, evidence, and distinctions rather than general subject knowledge
- Have clear, unambiguous wording
- Include plausible distractors that are clearly inconsistent with the student's paper
- Keep all options similar in length and specificity so the correct answer is not given away
- Cover important ideas from different parts of the student's paper
- Always respond with valid, properly formatted JSON"""

    @staticmethod
    def get_validation_prompt(question: Dict[str, Any], text: str) -> str:
        """
        Generate a prompt for validating if a question is relevant to the source text.

        Args:
            question: The question to validate
            text: The source text

        Returns:
            Formatted prompt string for validation
        """
        prompt = f"""Evaluate if this multiple-choice question is relevant to and answerable from the source text.

QUESTION:
{question.get("question", "")}

SOURCE TEXT:
{text[:1000]}...

Respond with valid JSON:
{{
  "is_relevant": true/false,
  "confidence": 0.0-1.0,
  "reason": "Brief explanation"
}}"""
        return prompt

    @staticmethod
    def get_single_question_prompt(
        text: str, existing_questions: Optional[List[str]] = None
    ) -> str:
        """
        Generate a prompt for creating a single multiple-choice question from text.

        Args:
            text: The source text to generate a question from
            existing_questions: List of existing question texts to avoid duplicates

        Returns:
            Formatted prompt string for the LLM
        """
        existing_text = ""
        if existing_questions:
            existing_text = (
                "\n\nEXISTING QUESTIONS (avoid creating similar questions):\n"
            )
            for i, q in enumerate(existing_questions, 1):
                existing_text += f"{i}. {q}\n"

        prompt = f"""You are creating a multiple-choice quiz for the student who wrote the following paper. Generate 1 high-quality question that tests whether the author can recall an argument, claim, piece of evidence, or distinction from their own writing.

STUDENT'S PAPER:
{text}
{existing_text}
INSTRUCTIONS:
1. Create 1 multiple-choice question with 4 options (A, B, C, D)
2. Address the student as the paper's author, for example: "In your paper, which argument did you use to...?"
3. Test recall of what the student actually wrote, not general knowledge or understanding of the broader subject
4. The question must have exactly ONE correct answer supported by the paper
5. Incorrect options should be plausible but clearly inconsistent with the paper's specific claims
6. The question should end with a question mark
7. Avoid trivial questions about wording, titles, or formatting
8. Include a brief explanation that refers to the student's own argument or claim
9. Make sure the options are distinct, plausible, and similar in length and specificity; do not make the correct answer noticeably longer or more detailed than the distractors

OUTPUT FORMAT:
You must respond with valid JSON in this exact format:
{{
  "question": "The question text here?",
  "options": {{
    "A": "First option",
    "B": "Second option",
    "C": "Third option",
    "D": "Fourth option"
  }},
  "correct_answer": "A",
  "explanation": "Brief explanation of why this is correct"
}}

Generate the question now:"""
        return prompt
