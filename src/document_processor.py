"""Document processing module for extracting text from various file formats."""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional
import docx
import pdfplumber


class DocumentProcessor:
    """Handles extraction and processing of text from documents."""
    
    SUPPORTED_FORMATS = ['.docx', '.pdf']
    
    def __init__(self):
        """Initialize the document processor."""
        pass
    
    def process_document(self, file_path: str) -> Dict[str, Any]:
        """
        Process a document and extract its text content.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Dictionary containing:
                - text: Extracted and cleaned text
                - filename: Original filename
                - file_type: File extension
                - word_count: Number of words in the document
                - char_count: Number of characters in the document
                
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file format is not supported
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        path_obj = Path(file_path)
        file_ext = path_obj.suffix.lower()
        
        if file_ext not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported file format: {file_ext}. "
                f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
            )
        
        # Extract text based on file type
        if file_ext == '.docx':
            raw_text = self.extract_text_from_docx(file_path)
        elif file_ext == '.pdf':
            raw_text = self.extract_text_from_pdf(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
        
        # Clean the extracted text
        cleaned_text = self.clean_text(raw_text)
        
        # Calculate statistics
        word_count = len(cleaned_text.split())
        char_count = len(cleaned_text)
        
        return {
            'text': cleaned_text,
            'filename': path_obj.name,
            'file_type': file_ext,
            'word_count': word_count,
            'char_count': char_count,
        }
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """
        Extract text from a Word document (.docx).
        
        Args:
            file_path: Path to the .docx file
            
        Returns:
            Extracted text as a string
            
        Raises:
            Exception: If the document cannot be read
        """
        try:
            doc = docx.Document(file_path)
            text_parts = []
            
            # Extract text from paragraphs
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)
            
            # Extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            text_parts.append(cell.text)
            
            return '\n'.join(text_parts)
        
        except Exception as e:
            raise Exception(f"Failed to extract text from Word document: {e}")
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extract text from a PDF document.
        
        Args:
            file_path: Path to the .pdf file
            
        Returns:
            Extracted text as a string
            
        Raises:
            Exception: If the PDF cannot be read
        """
        try:
            text_parts = []
            
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            
            return '\n'.join(text_parts)
        
        except Exception as e:
            raise Exception(f"Failed to extract text from PDF: {e}")
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove multiple consecutive newlines
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Remove common artifacts from PDF extraction
        text = re.sub(r'\x00', '', text)  # Null bytes
        text = re.sub(r'[\x01-\x08\x0b-\x0c\x0e-\x1f]', '', text)  # Control characters
        
        return text
    
    def validate_document(self, file_path: str) -> tuple[bool, Optional[str]]:
        """
        Validate if a document can be processed.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if file exists
        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}"
        
        # Check if file is readable
        if not os.access(file_path, os.R_OK):
            return False, f"File is not readable: {file_path}"
        
        # Check file extension
        file_ext = Path(file_path).suffix.lower()
        if file_ext not in self.SUPPORTED_FORMATS:
            return False, (
                f"Unsupported file format: {file_ext}. "
                f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
            )
        
        # Check file size (warn if too large, e.g., > 10MB)
        file_size = os.path.getsize(file_path)
        max_size = 10 * 1024 * 1024  # 10MB
        if file_size > max_size:
            return False, f"File too large: {file_size / (1024*1024):.2f}MB (max: 10MB)"
        
        # Check if file is empty
        if file_size == 0:
            return False, "File is empty"
        
        return True, None
    
    def get_supported_formats(self) -> list[str]:
        """
        Get list of supported file formats.
        
        Returns:
            List of supported file extensions
        """
        return self.SUPPORTED_FORMATS.copy()
    
    def chunk_text(self, text: str, max_chunk_size: int = 4000, overlap: int = 200) -> list[str]:
        """
        Split text into chunks for processing large documents.
        
        Args:
            text: Text to chunk
            max_chunk_size: Maximum characters per chunk
            overlap: Number of characters to overlap between chunks
            
        Returns:
            List of text chunks
        """
        if len(text) <= max_chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + max_chunk_size
            
            # If not the last chunk, try to break at a sentence or paragraph
            if end < len(text):
                # Look for paragraph break
                paragraph_break = text.rfind('\n\n', start, end)
                if paragraph_break > start:
                    end = paragraph_break
                else:
                    # Look for sentence break
                    sentence_break = max(
                        text.rfind('. ', start, end),
                        text.rfind('! ', start, end),
                        text.rfind('? ', start, end)
                    )
                    if sentence_break > start:
                        end = sentence_break + 1
            
            chunks.append(text[start:end].strip())
            start = end - overlap if end < len(text) else end
        
        return chunks


def create_processor() -> DocumentProcessor:
    """
    Factory function to create a DocumentProcessor instance.
    
    Returns:
        DocumentProcessor instance
    """
    return DocumentProcessor()
