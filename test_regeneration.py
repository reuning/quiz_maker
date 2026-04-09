"""
Test script to verify question regeneration functionality.

This script tests that when questions fail validation, the system
regenerates them instead of just using the remaining valid questions.
"""

import logging
from src.quiz_generator import QuizGenerator
from src.config_manager import ConfigManager

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

def test_regeneration():
    """Test that failed questions are regenerated."""
    
    # Use an existing test document
    test_doc_path = "tests/test_document_1.docx"
    
    try:
        logger.info("=" * 60)
        logger.info("Testing Question Regeneration Functionality")
        logger.info("=" * 60)
        
        # Initialize quiz generator
        config = ConfigManager()
        generator = QuizGenerator(config=config)
        
        # Generate quiz with 5 questions
        logger.info("\nGenerating quiz with 5 questions...")
        quiz = generator.generate_quiz_from_document(
            doc_path=test_doc_path,
            num_questions=5,
            validate_questions=True,
            max_retries=3
        )
        
        logger.info("\n" + "=" * 60)
        logger.info("RESULTS")
        logger.info("=" * 60)
        logger.info(f"Target questions: 5")
        logger.info(f"Generated questions: {len(quiz.questions)}")
        
        if len(quiz.questions) == 5:
            logger.info("✓ SUCCESS: Got exactly 5 questions as requested")
        else:
            logger.warning(f"⚠ WARNING: Got {len(quiz.questions)} questions instead of 5")
        
        logger.info("\nGenerated Questions:")
        for i, q in enumerate(quiz.questions, 1):
            logger.info(f"\n{i}. {q.question}")
            logger.info(f"   Correct Answer: {q.correct_answer}")
        
        return len(quiz.questions) == 5
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = test_regeneration()
    if success:
        print("\n✓ Test PASSED: Question regeneration is working correctly")
    else:
        print("\n✗ Test FAILED: Check logs above for details")
