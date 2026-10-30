"""Unit tests for the document processor."""

import os
import tempfile
import pytest
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.document_processor import DocumentProcessor


class TestDocumentProcessor:
    """Test cases for DocumentProcessor class."""

    def test_supported_formats(self):
        """Test getting supported formats."""
        processor = DocumentProcessor()
        formats = processor.get_supported_formats()
        assert ".docx" in formats
        assert ".pdf" in formats

    def test_clean_text_removes_whitespace(self):
        """Test text cleaning removes excessive whitespace."""
        processor = DocumentProcessor()
        text = "This  is   a    test\n\n\n\nwith   spaces"
        cleaned = processor.clean_text(text)
        assert cleaned == "This is a test\n\nwith spaces"

    def test_clean_text_preserves_paragraph_breaks(self):
        """Test cleaning preserves paragraph structure and normalizes line endings."""
        processor = DocumentProcessor()
        text = "First   paragraph.\r\n \t\r\nSecond\tparagraph.\nThird paragraph."
        assert processor.clean_text(text) == (
            "First paragraph.\n\nSecond paragraph.\nThird paragraph."
        )

    def test_clean_text_removes_control_characters(self):
        """Test text cleaning removes control characters."""
        processor = DocumentProcessor()
        text = "Test\x00text\x01with\x02control"
        cleaned = processor.clean_text(text)
        assert "\x00" not in cleaned
        assert "\x01" not in cleaned
        assert "\x02" not in cleaned

    def test_validate_document_nonexistent(self):
        """Test validation fails for non-existent file."""
        processor = DocumentProcessor()
        is_valid, error = processor.validate_document("/nonexistent/file.docx")
        assert not is_valid
        assert "not found" in error.lower()

    def test_validate_document_unsupported_format(self):
        """Test validation fails for unsupported format."""
        processor = DocumentProcessor()
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            temp_path = f.name

        try:
            is_valid, error = processor.validate_document(temp_path)
            assert not is_valid
            assert "unsupported" in error.lower()
        finally:
            os.unlink(temp_path)

    def test_validate_document_empty_file(self):
        """Test validation fails for empty file."""
        processor = DocumentProcessor()
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            temp_path = f.name

        try:
            is_valid, error = processor.validate_document(temp_path)
            assert not is_valid
            assert "empty" in error.lower()
        finally:
            os.unlink(temp_path)
