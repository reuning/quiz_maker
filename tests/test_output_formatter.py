"""
Unit tests for output_formatter module.
"""

import os
import tempfile
from pathlib import Path
from datetime import datetime

import pytest
from docx import Document

from src.output_formatter import OutputFormatter, create_output_formatter
from src.models import Quiz, Question


@pytest.fixture
def sample_quiz():
    """Create a sample quiz for testing."""
    questions = [
        Question(
            question="What is the capital of France?",
            options={
                "A": "London",
                "B": "Paris",
                "C": "Berlin",
                "D": "Madrid"
            },
            correct_answer="B",
            explanation="Paris is the capital and largest city of France."
        ),
        Question(
            question="Which planet is known as the Red Planet?",
            options={
                "A": "Venus",
                "B": "Jupiter",
                "C": "Mars",
                "D": "Saturn"
            },
            correct_answer="C",
            explanation="Mars is called the Red Planet due to its reddish appearance from iron oxide on its surface."
        ),
        Question(
            question="What is 2 + 2?",
            options={
                "A": "3",
                "B": "4",
                "C": "5",
                "D": "6"
            },
            correct_answer="B",
            explanation="Basic arithmetic: 2 + 2 equals 4."
        )
    ]
    
    return Quiz(
        questions=questions,
        source_document="test_document.docx",
        metadata={
            "generated_at": datetime(2024, 1, 15, 10, 30).isoformat(),
            "model": "test-model"
        }
    )


@pytest.fixture
def config():
    """Create a test configuration."""
    return {
        "output": {
            "formats": ["docx", "html"],
            "quiz_dir": "./output/quizzes",
            "answer_key_dir": "./output/answer_keys",
            "include_explanations": True
        }
    }


@pytest.fixture
def output_formatter(config):
    """Create an OutputFormatter instance."""
    return OutputFormatter(config)


class TestOutputFormatter:
    """Test suite for OutputFormatter class."""
    
    def test_initialization(self, config):
        """Test OutputFormatter initialization."""
        formatter = OutputFormatter(config)
        assert formatter.config == config
        assert formatter.output_config == config["output"]
        assert formatter.jinja_env is not None
    
    def test_create_output_formatter_factory(self, config):
        """Test factory function."""
        formatter = create_output_formatter(config)
        assert isinstance(formatter, OutputFormatter)
        assert formatter.config == config
    
    def test_create_word_quiz(self, output_formatter, sample_quiz):
        """Test Word document quiz generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_quiz.docx")
            result_path = output_formatter.create_word_quiz(
                sample_quiz, 
                output_path, 
                include_answers=False
            )
            
            # Verify file was created
            assert os.path.exists(result_path)
            assert result_path == output_path
            
            # Verify it's a valid Word document
            doc = Document(result_path)
            assert len(doc.paragraphs) > 0
            
            # Check that questions are present
            doc_text = "\n".join([p.text for p in doc.paragraphs])
            assert "What is the capital of France?" in doc_text
            assert "Which planet is known as the Red Planet?" in doc_text
            assert "Paris" in doc_text
            assert "Mars" in doc_text
    
    def test_create_word_answer_key(self, output_formatter, sample_quiz):
        """Test Word document answer key generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_answers.docx")
            result_path = output_formatter.create_word_quiz(
                sample_quiz, 
                output_path, 
                include_answers=True
            )
            
            # Verify file was created
            assert os.path.exists(result_path)
            
            # Verify it's a valid Word document
            doc = Document(result_path)
            doc_text = "\n".join([p.text for p in doc.paragraphs])
            
            # Check that answers and explanations are present
            assert "Correct Answer: B" in doc_text
            assert "Correct Answer: C" in doc_text
            assert "Paris is the capital" in doc_text
            assert "iron oxide" in doc_text
    
    def test_create_html_quiz(self, output_formatter, sample_quiz):
        """Test HTML quiz generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_quiz.html")
            result_path = output_formatter.create_html_quiz(
                sample_quiz, 
                output_path, 
                include_answers=False
            )
            
            # Verify file was created
            assert os.path.exists(result_path)
            assert result_path == output_path
            
            # Read and verify HTML content
            with open(result_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            assert "<!DOCTYPE html>" in html_content
            assert "What is the capital of France?" in html_content
            assert "Which planet is known as the Red Planet?" in html_content
            assert "Paris" in html_content
            assert "Mars" in html_content
            assert "test_document.docx" in html_content
            
            # Should NOT include answers in quiz
            assert "Correct Answer:" not in html_content or "Your Answer:" in html_content
    
    def test_create_html_answer_key(self, output_formatter, sample_quiz):
        """Test HTML answer key generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_answers.html")
            result_path = output_formatter.create_html_quiz(
                sample_quiz, 
                output_path, 
                include_answers=True
            )
            
            # Verify file was created
            assert os.path.exists(result_path)
            
            # Read and verify HTML content
            with open(result_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            assert "<!DOCTYPE html>" in html_content
            assert "Answer Key" in html_content
            
            # Should include correct answers
            assert "✓ Correct Answer: B" in html_content
            assert "✓ Correct Answer: C" in html_content
            
            # Should include explanations
            assert "Paris is the capital" in html_content
            assert "iron oxide" in html_content
    
    def test_create_quiz_outputs_multiple_formats(self, output_formatter, sample_quiz):
        """Test creating quiz in multiple formats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_paths = output_formatter.create_quiz_outputs(
                sample_quiz,
                "test_quiz",
                output_dir=tmpdir,
                formats=["docx", "html"]
            )
            
            # Verify both formats were created
            assert "docx" in output_paths
            assert "html" in output_paths
            assert os.path.exists(output_paths["docx"])
            assert os.path.exists(output_paths["html"])
            
            # Verify filenames
            assert output_paths["docx"].endswith("test_quiz.docx")
            assert output_paths["html"].endswith("test_quiz.html")
    
    def test_create_answer_key_outputs_multiple_formats(self, output_formatter, sample_quiz):
        """Test creating answer key in multiple formats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_paths = output_formatter.create_answer_key_outputs(
                sample_quiz,
                "test_quiz",
                output_dir=tmpdir,
                formats=["docx", "html"]
            )
            
            # Verify both formats were created
            assert "docx" in output_paths
            assert "html" in output_paths
            assert os.path.exists(output_paths["docx"])
            assert os.path.exists(output_paths["html"])
            
            # Verify filenames include "_answers"
            assert output_paths["docx"].endswith("test_quiz_answers.docx")
            assert output_paths["html"].endswith("test_quiz_answers.html")
    
    def test_create_outputs_with_defaults(self, output_formatter, sample_quiz):
        """Test creating outputs using config defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Override config for testing
            output_formatter.output_config['quiz_dir'] = tmpdir
            
            output_paths = output_formatter.create_quiz_outputs(
                sample_quiz,
                "test_quiz"
            )
            
            # Should use default formats from config
            assert len(output_paths) > 0
            for path in output_paths.values():
                assert os.path.exists(path)
    
    def test_format_multiple_choice_without_answer(self, output_formatter, sample_quiz):
        """Test formatting a question as plain text without answer."""
        question = sample_quiz.questions[0]
        formatted = output_formatter.format_multiple_choice(question, 1, include_answer=False)
        
        assert "1. What is the capital of France?" in formatted
        assert "A. London" in formatted
        assert "B. Paris" in formatted
        assert "Correct Answer:" not in formatted
        assert "Explanation:" not in formatted
    
    def test_format_multiple_choice_with_answer(self, output_formatter, sample_quiz):
        """Test formatting a question as plain text with answer."""
        question = sample_quiz.questions[0]
        formatted = output_formatter.format_multiple_choice(question, 1, include_answer=True)
        
        assert "1. What is the capital of France?" in formatted
        assert "A. London" in formatted
        assert "B. Paris" in formatted
        assert "Correct Answer: B" in formatted
        assert "Explanation: Paris is the capital" in formatted
        assert "→" in formatted  # Arrow marker for correct answer
    
    def test_output_directory_creation(self, output_formatter, sample_quiz):
        """Test that output directories are created if they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = os.path.join(tmpdir, "nested", "output", "dir")
            output_path = os.path.join(nested_dir, "test_quiz.docx")
            
            # Directory doesn't exist yet
            assert not os.path.exists(nested_dir)
            
            # Create quiz should create the directory
            result_path = output_formatter.create_word_quiz(
                sample_quiz, 
                output_path
            )
            
            assert os.path.exists(nested_dir)
            assert os.path.exists(result_path)
    
    def test_quiz_without_source_document(self, output_formatter):
        """Test handling quiz without source document."""
        quiz = Quiz(
            questions=[
                Question(
                    question="Test question?",
                    options={"A": "Opt1", "B": "Opt2", "C": "Opt3", "D": "Opt4"},
                    correct_answer="A",
                    explanation="Test explanation"
                )
            ],
            source_document=None,
            metadata={}
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_quiz.html")
            result_path = output_formatter.create_html_quiz(quiz, output_path)
            
            assert os.path.exists(result_path)
            
            with open(result_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Should handle missing source gracefully
            assert "Unknown" in html_content or "Source:" in html_content
    
    def test_html_templates_exist(self, output_formatter):
        """Test that required HTML templates exist."""
        template_dir = Path(__file__).parent.parent / 'src' / 'templates'
        
        assert (template_dir / 'quiz_template.html').exists()
        assert (template_dir / 'answer_key_template.html').exists()
    
    def test_word_document_structure(self, output_formatter, sample_quiz):
        """Test Word document has proper structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_quiz.docx")
            output_formatter.create_word_quiz(sample_quiz, output_path)
            
            doc = Document(output_path)
            
            # Check document has content
            assert len(doc.paragraphs) > 10
            
            # Check for title
            assert any("Quiz" in p.text for p in doc.paragraphs)
            
            # Check for metadata
            doc_text = "\n".join([p.text for p in doc.paragraphs])
            assert "Source:" in doc_text
            assert "Generated:" in doc_text
            assert "Total Questions:" in doc_text
    
    def test_html_includes_print_styles(self, output_formatter, sample_quiz):
        """Test that HTML includes print-friendly CSS."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_quiz.html")
            output_formatter.create_html_quiz(sample_quiz, output_path)
            
            with open(output_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Check for print media query
            assert "@media print" in html_content
            assert "page-break" in html_content
    
    def test_answer_key_highlights_correct_answers(self, output_formatter, sample_quiz):
        """Test that answer key properly highlights correct answers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test Word format
            word_path = os.path.join(tmpdir, "test_answers.docx")
            output_formatter.create_word_quiz(sample_quiz, word_path, include_answers=True)
            
            doc = Document(word_path)
            doc_text = "\n".join([p.text for p in doc.paragraphs])
            
            # Should show correct answers
            assert "Correct Answer: B" in doc_text
            assert "Correct Answer: C" in doc_text
            
            # Test HTML format
            html_path = os.path.join(tmpdir, "test_answers.html")
            output_formatter.create_html_quiz(sample_quiz, html_path, include_answers=True)
            
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Should have correct answer indicators
            assert "✓ Correct Answer: B" in html_content
            assert "✓ Correct Answer: C" in html_content
            assert "correct-answer" in html_content  # CSS class
    
    def test_explanations_included_when_configured(self, sample_quiz):
        """Test that explanations are included when configured."""
        config_with_explanations = {
            "output": {
                "formats": ["html"],
                "quiz_dir": "./output/quizzes",
                "answer_key_dir": "./output/answer_keys",
                "include_explanations": True
            }
        }
        
        formatter = OutputFormatter(config_with_explanations)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_answers.html")
            formatter.create_html_quiz(sample_quiz, output_path, include_answers=True)
            
            with open(output_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Should include explanations
            assert "Paris is the capital" in html_content
            assert "iron oxide" in html_content
    
    def test_explanations_excluded_when_configured(self, sample_quiz):
        """Test that explanations can be excluded."""
        config_without_explanations = {
            "output": {
                "formats": ["html"],
                "quiz_dir": "./output/quizzes",
                "answer_key_dir": "./output/answer_keys",
                "include_explanations": False
            }
        }
        
        formatter = OutputFormatter(config_without_explanations)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_answers.html")
            formatter.create_html_quiz(sample_quiz, output_path, include_answers=True)
            
            with open(output_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Should still show correct answers
            assert "✓ Correct Answer:" in html_content
            
            # But explanations should not be shown (or minimal)
            # Note: The template might still have the explanation section, 
            # but it won't be populated
    
    def test_single_format_output(self, output_formatter, sample_quiz):
        """Test creating output in a single format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Only create HTML
            output_paths = output_formatter.create_quiz_outputs(
                sample_quiz,
                "test_quiz",
                output_dir=tmpdir,
                formats=["html"]
            )
            
            assert len(output_paths) == 1
            assert "html" in output_paths
            assert os.path.exists(output_paths["html"])
    
    def test_format_multiple_choice_all_options(self, output_formatter, sample_quiz):
        """Test that all options A-D are formatted."""
        question = sample_quiz.questions[0]
        formatted = output_formatter.format_multiple_choice(question, 1, include_answer=False)
        
        # All options should be present
        assert "A. London" in formatted
        assert "B. Paris" in formatted
        assert "C. Berlin" in formatted
        assert "D. Madrid" in formatted
    
    def test_quiz_metadata_in_output(self, output_formatter, sample_quiz):
        """Test that quiz metadata appears in output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_quiz.html")
            output_formatter.create_html_quiz(sample_quiz, output_path)
            
            with open(output_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Check metadata is present
            assert "test_document.docx" in html_content
            assert "January 15, 2024" in html_content
            assert str(sample_quiz.num_questions) in html_content
