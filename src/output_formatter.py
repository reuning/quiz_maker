"""
Output formatter for quiz generation.

This module handles the creation of quiz and answer key documents in multiple formats
(Word and HTML) using python-docx and Jinja2 templating.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .models import Quiz, Question


class OutputFormatter:
    """Handles formatting and generation of quiz output files."""
    
    def __init__(self, config: dict):
        """
        Initialize the output formatter.
        
        Args:
            config: Configuration dictionary with output settings
        """
        self.config = config
        self.output_config = config.get('output', {})
        
        # Set up Jinja2 environment for HTML templates
        template_dir = Path(__file__).parent / 'templates'
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )
    
    def create_word_quiz(self, quiz: Quiz, output_path: str, include_answers: bool = False) -> str:
        """
        Create a Word document quiz.
        
        Args:
            quiz: Quiz object containing questions
            output_path: Path where the Word document should be saved
            include_answers: Whether to include answers (for answer key)
            
        Returns:
            Path to the created document
        """
        doc = Document()
        
        # Set up document margins
        sections = doc.sections
        for section in sections:
            section.top_margin = Inches(1)
            section.bottom_margin = Inches(1)
            section.left_margin = Inches(1)
            section.right_margin = Inches(1)
        
        # Add title
        title = doc.add_heading('Quiz' if not include_answers else 'Answer Key', level=1)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Add metadata
        if quiz.source_document:
            source_name = Path(quiz.source_document).name
            doc.add_paragraph(f"Source: {source_name}")
        
        generated_date = quiz.metadata.get('generated_at', datetime.now().isoformat())
        if isinstance(generated_date, str):
            try:
                generated_date = datetime.fromisoformat(generated_date).strftime('%B %d, %Y')
            except:
                generated_date = datetime.now().strftime('%B %d, %Y')
        else:
            generated_date = generated_date.strftime('%B %d, %Y')
        
        #doc.add_paragraph(f"Generated: {generated_date}")
        #doc.add_paragraph(f"Total Questions: {quiz.num_questions}")
        
        # Add spacing
        #doc.add_paragraph()
        
        # Add instructions if not answer key
        if not include_answers:
            instructions = doc.add_paragraph()
            instructions.add_run("Instructions: ").bold = True
            instructions.add_run("Select the best answer for each question.")
            doc.add_paragraph()
        
        # Add questions
        for idx, question in enumerate(quiz.questions, 1):
            # Question text
            q_paragraph = doc.add_paragraph()
            q_run = q_paragraph.add_run(f"{idx}. {question.question}")
            q_run.bold = True
            q_run.font.size = Pt(11)
            
            # Options
            for option_key in ['A', 'B', 'C', 'D']:
                option_text = question.options.get(option_key, '')
                option_paragraph = doc.add_paragraph(style='List Bullet')
                option_paragraph.paragraph_format.left_indent = Inches(0.5)
                
                option_run = option_paragraph.add_run(f"{option_key}. {option_text}")
                
                # Highlight correct answer in answer key
                if include_answers and option_key == question.correct_answer:
                    option_run.bold = True
                    option_run.font.size = Pt(11)
            
            # Add answer and explanation for answer key
            if include_answers:
                answer_paragraph = doc.add_paragraph()
                answer_paragraph.paragraph_format.left_indent = Inches(0.5)
                answer_run = answer_paragraph.add_run(f"Correct Answer: {question.correct_answer}")
                answer_run.bold = True
                answer_run.font.size = Pt(10)
                
                if self.output_config.get('include_explanations', True):
                    explanation_paragraph = doc.add_paragraph()
                    explanation_paragraph.paragraph_format.left_indent = Inches(0.5)
                    explanation_run = explanation_paragraph.add_run(f"Explanation: {question.explanation}")
                    explanation_run.font.size = Pt(10)
            
            # Add spacing between questions
            doc.add_paragraph()
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save document
        doc.save(output_path)
        return output_path
    
    def create_html_quiz(self, quiz: Quiz, output_path: str, include_answers: bool = False) -> str:
        """
        Create an HTML quiz.
        
        Args:
            quiz: Quiz object containing questions
            output_path: Path where the HTML file should be saved
            include_answers: Whether to include answers (for answer key)
            
        Returns:
            Path to the created HTML file
        """
        # Select appropriate template
        template_name = 'answer_key_template.html' if include_answers else 'quiz_template.html'
        template = self.jinja_env.get_template(template_name)
        
        # Prepare context data
        source_name = Path(quiz.source_document).name if quiz.source_document else "Unknown"
        
        generated_date = quiz.metadata.get('generated_at', datetime.now().isoformat())
        if isinstance(generated_date, str):
            try:
                generated_date = datetime.fromisoformat(generated_date).strftime('%B %d, %Y')
            except:
                generated_date = datetime.now().strftime('%B %d, %Y')
        else:
            generated_date = generated_date.strftime('%B %d, %Y')
        
        context = {
            'quiz': quiz,
            'source_name': source_name,
            'generated_date': generated_date,
            'num_questions': quiz.num_questions,
            'include_explanations': self.output_config.get('include_explanations', True)
        }
        
        # Render template
        html_content = template.render(**context)
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Write HTML file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return output_path
    
    def create_quiz_outputs(
        self,
        quiz: Quiz,
        base_filename: str,
        output_dir: Optional[str] = None,
        formats: Optional[list[str]] = None
    ) -> dict[str, str]:
        """
        Create quiz outputs in multiple formats.
        
        Args:
            quiz: Quiz object to format
            base_filename: Base name for output files (without extension)
            output_dir: Directory for output files (uses config default if None)
            formats: List of formats to generate (uses config default if None)
            
        Returns:
            Dictionary mapping format to output file path
        """
        # Ensure we have valid values
        output_directory: str = output_dir if output_dir is not None else self.output_config.get('quiz_dir', './output/quizzes')
        format_list: list[str] = formats if formats is not None else self.output_config.get('formats', ['docx', 'html'])
        
        output_paths = {}
        
        # Create quiz files
        for fmt in format_list:
            if fmt == 'docx':
                output_path = os.path.join(output_directory, f"{base_filename}.docx")
                output_paths['docx'] = self.create_word_quiz(quiz, output_path, include_answers=False)
            elif fmt == 'html':
                output_path = os.path.join(output_directory, f"{base_filename}.html")
                output_paths['html'] = self.create_html_quiz(quiz, output_path, include_answers=False)
        
        return output_paths
    
    def create_answer_key_outputs(
        self,
        quiz: Quiz,
        base_filename: str,
        output_dir: Optional[str] = None,
        formats: Optional[list[str]] = None
    ) -> dict[str, str]:
        """
        Create answer key outputs in multiple formats.
        
        Args:
            quiz: Quiz object to format
            base_filename: Base name for output files (without extension)
            output_dir: Directory for output files (uses config default if None)
            formats: List of formats to generate (uses config default if None)
            
        Returns:
            Dictionary mapping format to output file path
        """
        # Ensure we have valid values
        output_directory: str = output_dir if output_dir is not None else self.output_config.get('answer_key_dir', './output/answer_keys')
        format_list: list[str] = formats if formats is not None else self.output_config.get('formats', ['docx', 'html'])
        
        output_paths = {}
        
        # Create answer key files
        for fmt in format_list:
            if fmt == 'docx':
                output_path = os.path.join(output_directory, f"{base_filename}_answers.docx")
                output_paths['docx'] = self.create_word_quiz(quiz, output_path, include_answers=True)
            elif fmt == 'html':
                output_path = os.path.join(output_directory, f"{base_filename}_answers.html")
                output_paths['html'] = self.create_html_quiz(quiz, output_path, include_answers=True)
        
        return output_paths
    
    def format_multiple_choice(self, question: Question, question_number: int, include_answer: bool = False) -> str:
        """
        Format a multiple choice question as plain text.
        
        Args:
            question: Question object to format
            question_number: The question number
            include_answer: Whether to include the answer
            
        Returns:
            Formatted question string
        """
        lines = [f"{question_number}. {question.question}"]
        
        for option_key in ['A', 'B', 'C', 'D']:
            option_text = question.options.get(option_key, '')
            marker = "→" if include_answer and option_key == question.correct_answer else " "
            lines.append(f"   {marker} {option_key}. {option_text}")
        
        if include_answer:
            lines.append(f"   Correct Answer: {question.correct_answer}")
            if question.explanation:
                lines.append(f"   Explanation: {question.explanation}")
        
        return "\n".join(lines)


def create_output_formatter(config: dict) -> OutputFormatter:
    """
    Factory function to create an OutputFormatter instance.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configured OutputFormatter instance
    """
    return OutputFormatter(config)
