"""
Unit tests for answer position randomization in quiz generation.
"""

import pytest
from collections import Counter
from src.models import Question
from src.quiz_generator import QuizGenerator


class TestAnswerRandomization:
    """Test suite for answer randomization functionality."""
    
    @pytest.fixture
    def quiz_generator(self):
        """Create a quiz generator instance for testing."""
        return QuizGenerator()
    
    @pytest.fixture
    def sample_question(self):
        """Create a sample question for testing."""
        return Question(
            question="What is the capital of France?",
            options={
                "A": "London",
                "B": "Paris",
                "C": "Berlin",
                "D": "Madrid"
            },
            correct_answer="B",
            explanation="Paris is the capital and largest city of France."
        )
    
    def test_randomization_preserves_correct_answer_text(self, quiz_generator, sample_question):
        """Test that randomization preserves the correct answer text."""
        original_correct_text = sample_question.options[sample_question.correct_answer]
        
        randomized = quiz_generator._randomize_answer_positions([sample_question])
        randomized_question = randomized[0]
        
        # The correct answer text should still be the same
        new_correct_text = randomized_question.options[randomized_question.correct_answer]
        assert new_correct_text == original_correct_text
        assert new_correct_text == "Paris"
    
    def test_randomization_preserves_all_options(self, quiz_generator, sample_question):
        """Test that all original options are preserved after randomization."""
        original_options = set(sample_question.options.values())
        
        randomized = quiz_generator._randomize_answer_positions([sample_question])
        randomized_question = randomized[0]
        
        new_options = set(randomized_question.options.values())
        assert new_options == original_options
    
    def test_randomization_preserves_question_text(self, quiz_generator, sample_question):
        """Test that the question text is not modified."""
        original_question_text = sample_question.question
        
        randomized = quiz_generator._randomize_answer_positions([sample_question])
        randomized_question = randomized[0]
        
        assert randomized_question.question == original_question_text
    
    def test_randomization_preserves_explanation(self, quiz_generator, sample_question):
        """Test that the explanation is not modified."""
        original_explanation = sample_question.explanation
        
        randomized = quiz_generator._randomize_answer_positions([sample_question])
        randomized_question = randomized[0]
        
        assert randomized_question.explanation == original_explanation
    
    def test_randomization_produces_varied_positions(self, quiz_generator, sample_question):
        """Test that randomization produces varied answer positions over multiple runs."""
        positions = []
        
        # Run randomization 50 times to get a good sample
        for _ in range(50):
            randomized = quiz_generator._randomize_answer_positions([sample_question])
            randomized_question = randomized[0]
            positions.append(randomized_question.correct_answer)
        
        # Count the distribution
        distribution = Counter(positions)
        
        # We should see at least 2 different positions (ideally more)
        # With 50 runs and 4 positions, we expect to see multiple positions
        unique_positions = len(distribution)
        assert unique_positions >= 2, f"Only {unique_positions} unique position(s) in 50 runs"
        
        # No single position should dominate too heavily (e.g., > 80% of the time)
        max_count = max(distribution.values())
        assert max_count < 40, f"Position appeared {max_count}/50 times (too frequent)"
    
    def test_randomization_handles_multiple_questions(self, quiz_generator):
        """Test that randomization works correctly with multiple questions."""
        questions = [
            Question(
                question="Question 1?",
                options={"A": "Opt1A", "B": "Opt1B", "C": "Opt1C", "D": "Opt1D"},
                correct_answer="A",
                explanation="Explanation 1"
            ),
            Question(
                question="Question 2?",
                options={"A": "Opt2A", "B": "Opt2B", "C": "Opt2C", "D": "Opt2D"},
                correct_answer="B",
                explanation="Explanation 2"
            ),
            Question(
                question="Question 3?",
                options={"A": "Opt3A", "B": "Opt3B", "C": "Opt3C", "D": "Opt3D"},
                correct_answer="C",
                explanation="Explanation 3"
            ),
        ]
        
        randomized = quiz_generator._randomize_answer_positions(questions)
        
        # Should return same number of questions
        assert len(randomized) == len(questions)
        
        # Each question should have its correct answer preserved
        for i, (original, randomized_q) in enumerate(zip(questions, randomized)):
            original_correct_text = original.options[original.correct_answer]
            new_correct_text = randomized_q.options[randomized_q.correct_answer]
            assert new_correct_text == original_correct_text, f"Question {i+1} correct answer changed"
    
    def test_randomization_with_empty_list(self, quiz_generator):
        """Test that randomization handles an empty list gracefully."""
        result = quiz_generator._randomize_answer_positions([])
        assert result == []
    
    def test_randomization_maintains_option_keys(self, quiz_generator, sample_question):
        """Test that randomized questions still have A, B, C, D as keys."""
        randomized = quiz_generator._randomize_answer_positions([sample_question])
        randomized_question = randomized[0]
        
        assert set(randomized_question.options.keys()) == {'A', 'B', 'C', 'D'}
    
    def test_correct_answer_is_valid_key(self, quiz_generator, sample_question):
        """Test that the correct_answer is always a valid option key."""
        randomized = quiz_generator._randomize_answer_positions([sample_question])
        randomized_question = randomized[0]
        
        assert randomized_question.correct_answer in randomized_question.options
        assert randomized_question.correct_answer in ['A', 'B', 'C', 'D']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
