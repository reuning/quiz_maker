"""
Prompt templates for LLM-based quiz generation.

This module contains structured prompts for generating multiple-choice questions
from document text using local LLMs via Ollama.
"""

from typing import Dict, Any


class PromptTemplates:
    """Collection of prompt templates for quiz generation."""
    
    @staticmethod
    def get_quiz_generation_prompt(text: str, num_questions: int, num_options: int = 4) -> str:
        """
        Generate a prompt for creating multiple-choice questions from text.
        
        Args:
            text: The source text to generate questions from
            num_questions: Number of questions to generate
            num_options: Number of answer options per question (default: 4)
            
        Returns:
            Formatted prompt string for the LLM
        """
        prompt = f"""You are an expert educator creating a multiple-choice quiz based on the following text. Generate {num_questions} high-quality multiple-choice questions that test understanding of the key concepts.

SOURCE TEXT:
{text}

INSTRUCTIONS:
1. Create {num_questions} multiple-choice questions with {num_options} options each (A, B, C, D)
2. Questions should test comprehension, not just memorization
3. Each question must have exactly ONE correct answer
4. Incorrect options should be plausible but clearly wrong
5. Questions should cover different parts of the text
6. Avoid trivial or overly obvious questions
7. Include brief explanations for why the correct answer is right

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
{question.get('question', '')}

OPTIONS:
{chr(10).join(f"{k}: {v}" for k, v in question.get('options', {}).items())}

CORRECT ANSWER: {question.get('correct_answer', '')}

ISSUE TO FIX:
{issue}

Please provide an improved version of this question that addresses the issue. Respond with valid JSON in this format:
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
        return """You are an expert educational content creator specializing in creating high-quality multiple-choice questions. Your questions should:
- Test deep understanding, not just recall
- Have clear, unambiguous wording
- Include plausible distractors (incorrect options)
- Be appropriate for college-level students
- Cover important concepts from the source material
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
{question.get('question', '')}

SOURCE TEXT:
{text[:1000]}...

Respond with valid JSON:
{{
  "is_relevant": true/false,
  "confidence": 0.0-1.0,
  "reason": "Brief explanation"
}}"""
        return prompt
