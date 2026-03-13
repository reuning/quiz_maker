"""Unit tests for the document processor."""

import os
import tempfile
import pytest
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.document_processor import DocumentProcessor, create_processor


class TestDocumentProcessor:
    """Test cases for DocumentProcessor class."""
    
    def test_create_processor(self):
        """Test factory function creates processor."""
        processor = create_processor()
        assert isinstance(processor, DocumentProcessor)
    
    def test_supported_formats(self):
        """Test getting supported formats."""
        processor = DocumentProcessor()
        formats = processor.get_supported_formats()
        assert '.docx' in formats
        assert '.pdf' in formats
    
    def test_clean_text_removes_whitespace(self):
        """Test text cleaning removes excessive whitespace."""
        processor = DocumentProcessor()
        text = "This  is   a    test\n\n\n\nwith   spaces"
        cleaned = processor.clean_text(text)
        assert "  " not in cleaned
        assert "\n\n\n" not in cleaned
    
    def test_clean_text_removes_control_characters(self):
        """Test text cleaning removes control characters."""
        processor = DocumentProcessor()
        text = "Test\x00text\x01with\x02control"
        cleaned = processor.clean_text(text)
        assert '\x00' not in cleaned
        assert '\x01' not in cleaned
        assert '\x02' not in cleaned
    
    def test_validate_document_nonexistent(self):
        """Test validation fails for non-existent file."""
        processor = DocumentProcessor()
        is_valid, error = processor.validate_document('/nonexistent/file.docx')
        assert not is_valid
        assert 'not found' in error.lower()
    
    def test_validate_document_unsupported_format(self):
        """Test validation fails for unsupported format."""
        processor = DocumentProcessor()
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            temp_path = f.name
        
        try:
            is_valid, error = processor.validate_document(temp_path)
            assert not is_valid
            assert 'unsupported' in error.lower()
        finally:
            os.unlink(temp_path)
    
    def test_validate_document_empty_file(self):
        """Test validation fails for empty file."""
        processor = DocumentProcessor()
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            temp_path = f.name
        
        try:
            is_valid, error = processor.validate_document(temp_path)
            assert not is_valid
            assert 'empty' in error.lower()
        finally:
            os.unlink(temp_path)
    
    def test_chunk_text_small_text(self):
        """Test chunking returns single chunk for small text."""
        processor = DocumentProcessor()
        text = "This is a small text."
        chunks = processor.chunk_text(text, max_chunk_size=1000)
        assert len(chunks) == 1
        assert chunks[0] == text
    
    def test_chunk_text_large_text(self):
        """Test chunking splits large text."""
        processor = DocumentProcessor()
        text = "This is a sentence. " * 500  # Create large text
        chunks = processor.chunk_text(text, max_chunk_size=500, overlap=50)
        assert len(chunks) > 1
        # Check that chunks have some overlap
        if len(chunks) > 1:
            # Last part of first chunk should appear in second chunk
            assert chunks[0][-20:] in chunks[1] or chunks[1][:20] in chunks[0]
    
    def test_chunk_text_respects_sentence_boundaries(self):
        """Test chunking tries to break at sentence boundaries."""
        processor = DocumentProcessor()
        text = "First sentence. " * 100 + "Second sentence. " * 100
        chunks = processor.chunk_text(text, max_chunk_size=500, overlap=50)
        # Each chunk should end with a period (sentence boundary)
        for chunk in chunks[:-1]:  # All but last chunk
            assert chunk.rstrip().endswith('.')
