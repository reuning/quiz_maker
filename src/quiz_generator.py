"""
Quiz generation orchestration module.

This module coordinates document processing, LLM interaction, and question
validation to generate complete quizzes from source documents.
"""

import logging
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config_manager import ConfigManager
from .document_processor import DocumentProcessor
from .llm_interface import LLMInterface, create_llm_interface
from .question_validator import QuestionValidator, create_validator
from .models import Quiz, Question, DocumentInfo


logger = logging.getLogger(__name__)


class QuizGenerationError(Exception):
    """Exception raised when quiz generation fails."""
    pass


class QuizGenerator:
    """Orchestrates the quiz generation process."""
    
    def __init__(
        self,
        config: Optional[ConfigManager] = None,
        document_processor: Optional[DocumentProcessor] = None,
        llm_interface: Optional[LLMInterface] = None,
        validator: Optional[QuestionValidator] = None
    ):
        """
        Initialize the quiz generator.
        
        Args:
            config: Configuration manager instance (creates default if None)
            document_processor: Document processor instance (creates default if None)
            llm_interface: LLM interface instance (creates from config if None)
            validator: Question validator instance (creates default if None)
        """
        self.config = config or ConfigManager()
        self.document_processor = document_processor or DocumentProcessor()
        self.llm_interface = llm_interface or create_llm_interface(self.config.config)
        self.validator = validator or create_validator(self.config.config)
        
        logger.info("QuizGenerator initialized")
    
    def generate_quiz_from_document(
        self,
        doc_path: str,
        num_questions: Optional[int] = None,
        validate_questions: bool = True,
        max_retries: int = 3
    ) -> Quiz:
        """
        Generate a quiz from a document.
        
        Args:
            doc_path: Path to the source document
            num_questions: Number of questions to generate (uses config default if None)
            validate_questions: Whether to validate question quality
            max_retries: Maximum number of retry attempts for generation
            
        Returns:
            Generated Quiz object
            
        Raises:
            QuizGenerationError: If quiz generation fails
            FileNotFoundError: If document doesn't exist
            ValueError: If document format is unsupported
        """
        logger.info(f"Starting quiz generation from document: {doc_path}")
        
        # Use default from config if not specified
        if num_questions is None:
            num_questions = self.config.get('quiz.default_questions', 7)
        
        # Ensure we have a valid integer
        num_questions = int(num_questions)
        
        try:
            # Step 1: Process document
            logger.info("Processing document...")
            doc_info = self.document_processor.process_document(doc_path)
            logger.info(
                f"Document processed: {doc_info['word_count']} words, "
                f"{doc_info['char_count']} characters"
            )
            
            # Check if document has sufficient content
            if doc_info['word_count'] < 50:
                raise QuizGenerationError(
                    f"Document too short ({doc_info['word_count']} words). "
                    "Need at least 50 words to generate meaningful questions."
                )
            
            # Step 2: Generate questions using LLM
            logger.info(f"Generating {num_questions} questions...")
            num_options = self.config.get('quiz.num_options', 4)
            
            # Ensure num_questions is an int (should always be at this point)
            assert num_questions is not None, "num_questions should not be None at this point"
            
            quiz_response = self.llm_interface.generate_quiz(
                text=doc_info['text'],
                num_questions=num_questions,
                num_options=num_options,
                max_retries=max_retries
            )
            
            logger.info(f"Generated {len(quiz_response.questions)} questions")
            
            # Step 3: Validate questions if requested
            if validate_questions:
                logger.info("Validating questions...")
                validated_questions = self._validate_and_regenerate_questions(
                    quiz_response.questions,
                    doc_info['text'],
                    num_questions,
                    num_options,
                    max_retries
                )
                
                if not validated_questions:
                    raise QuizGenerationError(
                        "All generated questions failed validation. "
                        "Try adjusting the source document or generation parameters."
                    )
                
                logger.info(
                    f"Validation complete: {len(validated_questions)}/{num_questions} "
                    "questions ready"
                )
            else:
                validated_questions = quiz_response.questions
            
            # Step 3.5: Randomize answer positions to avoid bias
            logger.info("Randomizing answer positions...")
            validated_questions = self._randomize_answer_positions(validated_questions)
            
            # Step 4: Create quiz with metadata
            quiz = self._create_quiz_with_metadata(
                validated_questions,
                doc_path,
                doc_info
            )
            
            logger.info(f"Quiz generation complete: {quiz.num_questions} questions")
            return quiz
            
        except FileNotFoundError as e:
            logger.error(f"Document not found: {e}")
            raise
        except ValueError as e:
            logger.error(f"Invalid document or parameters: {e}")
            raise QuizGenerationError(f"Invalid input: {e}")
        except Exception as e:
            logger.error(f"Quiz generation failed: {e}", exc_info=True)
            raise QuizGenerationError(f"Failed to generate quiz: {e}")
    
    def _validate_and_regenerate_questions(
        self,
        questions: List[Question],
        source_text: str,
        target_count: int,
        num_options: int,
        max_retries: int = 3
    ) -> List[Question]:
        """
        Validate questions and regenerate invalid ones to reach target count.
        
        Args:
            questions: List of questions to validate
            source_text: Source text for relevance checking
            target_count: Target number of valid questions
            num_options: Number of options per question
            max_retries: Maximum retries per failed question
            
        Returns:
            List of valid questions (up to target_count)
        """
        valid_questions = []
        
        # First pass: validate all questions
        for i, question in enumerate(questions, 1):
            is_valid, issues = self.validator.validate_question(question, source_text)
            
            if is_valid:
                valid_questions.append(question)
                logger.debug(f"Question {i}: ✓ Valid")
            else:
                logger.warning(f"Question {i}: ✗ Invalid - {'; '.join(issues)}")
        
        # If we have enough valid questions, return them
        if len(valid_questions) >= target_count:
            return valid_questions[:target_count]
        
        # Otherwise, regenerate questions to reach target count
        num_needed = target_count - len(valid_questions)
        logger.info(f"Need to regenerate {num_needed} question(s) to reach target of {target_count}")
        
        # Get existing question texts to avoid duplicates
        existing_question_texts = [q.question for q in valid_questions]
        
        regeneration_attempts = 0
        max_total_attempts = num_needed * max_retries
        
        while len(valid_questions) < target_count and regeneration_attempts < max_total_attempts:
            regeneration_attempts += 1
            logger.info(f"Regeneration attempt {regeneration_attempts}/{max_total_attempts}")
            
            try:
                # Generate a single new question
                new_question = self.llm_interface.generate_single_question(
                    text=source_text,
                    num_options=num_options,
                    existing_questions=existing_question_texts,
                    max_retries=2
                )
                
                # Validate the new question
                is_valid, issues = self.validator.validate_question(new_question, source_text)
                
                if is_valid:
                    valid_questions.append(new_question)
                    existing_question_texts.append(new_question.question)
                    logger.info(f"✓ Successfully regenerated question {len(valid_questions)}/{target_count}")
                else:
                    logger.warning(f"✗ Regenerated question invalid - {'; '.join(issues)}")
                    
            except Exception as e:
                logger.warning(f"Failed to regenerate question: {e}")
        
        if len(valid_questions) < target_count:
            logger.warning(
                f"Could only generate {len(valid_questions)}/{target_count} valid questions "
                f"after {regeneration_attempts} attempts"
            )
        
        return valid_questions
    
    def _randomize_answer_positions(self, questions: List[Question]) -> List[Question]:
        """
        Randomize the position of correct answers across all questions.
        
        This method shuffles the answer options for each question to ensure
        the correct answer is not always in the same position (e.g., always B).
        This prevents patterns that students might exploit and ensures a more
        balanced distribution of correct answers across A, B, C, and D.
        
        Args:
            questions: List of questions to randomize
            
        Returns:
            List of questions with randomized answer positions
        """
        randomized_questions = []
        
        for question in questions:
            # Get current options and correct answer text
            options = question.options.copy()
            correct_text = options[question.correct_answer]
            
            # Create list of all option texts
            option_texts = list(options.values())
            
            # Shuffle the option texts using Python's random module
            random.shuffle(option_texts)
            
            # Reassign shuffled texts to A, B, C, D
            new_options = {
                'A': option_texts[0],
                'B': option_texts[1],
                'C': option_texts[2],
                'D': option_texts[3]
            }
            
            # Find new position of correct answer
            new_correct_answer = None
            for key, text in new_options.items():
                if text == correct_text:
                    new_correct_answer = key
                    break
            
            # Safety check: this should never happen, but handle it gracefully
            if new_correct_answer is None:
                logger.error(f"Failed to find correct answer after shuffling: {correct_text}")
                # Fall back to original question if shuffling fails
                randomized_questions.append(question)
                continue
            
            # Create new question with shuffled options
            randomized_question = Question(
                question=question.question,
                options=new_options,
                correct_answer=new_correct_answer,
                explanation=question.explanation
            )
            randomized_questions.append(randomized_question)
            
            logger.debug(
                f"Randomized question: '{question.question[:50]}...' - "
                f"Correct answer moved from {question.correct_answer} to {new_correct_answer}"
            )
        
        return randomized_questions
    
    def _create_quiz_with_metadata(
        self,
        questions: List[Question],
        doc_path: str,
        doc_info: Dict[str, Any]
    ) -> Quiz:
        """
        Create a Quiz object with metadata.
        
        Args:
            questions: List of validated questions
            doc_path: Path to source document
            doc_info: Document processing information
            
        Returns:
            Quiz object with metadata
        """
        metadata = {
            'generated_at': datetime.now().isoformat(),
            'source_filename': doc_info['filename'],
            'source_file_type': doc_info['file_type'],
            'source_word_count': doc_info['word_count'],
            'source_char_count': doc_info['char_count'],
            'llm_model': self.llm_interface.model,
            'llm_temperature': self.llm_interface.temperature,
        }
        
        quiz = Quiz(
            questions=questions,
            source_document=doc_path,
            metadata=metadata
        )
        
        return quiz
    
    def validate_quiz_quality(self, quiz: Quiz, source_text: str = "") -> Dict[str, Any]:
        """
        Validate the overall quality of a quiz.
        
        Args:
            quiz: The quiz to validate
            source_text: Optional source text for relevance checking
            
        Returns:
            Dictionary with validation results including:
                - is_valid: Overall validity
                - num_questions: Number of questions
                - num_valid: Number of valid questions
                - num_invalid: Number of invalid questions
                - issues: List of issues found
                - quality_score: Overall quality score (0-1)
        """
        return self.validator.validate_quiz(quiz, source_text)
    
    def add_metadata(self, quiz: Quiz, additional_metadata: Dict[str, Any]) -> Quiz:
        """
        Add additional metadata to a quiz.
        
        Args:
            quiz: The quiz to update
            additional_metadata: Dictionary of metadata to add
            
        Returns:
            Updated quiz (note: modifies in place and returns)
        """
        quiz.metadata.update(additional_metadata)
        logger.debug(f"Added metadata to quiz: {list(additional_metadata.keys())}")
        return quiz


def create_quiz_generator(
    config_path: Optional[str] = None,
    config: Optional[ConfigManager] = None
) -> QuizGenerator:
    """
    Factory function to create a quiz generator.
    
    Args:
        config_path: Path to configuration file
        config: Pre-configured ConfigManager instance (takes precedence over config_path)
        
    Returns:
        Configured QuizGenerator instance
    """
    if config is None:
        config = ConfigManager(config_path)
    
    return QuizGenerator(config=config)
