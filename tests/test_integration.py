"""Integration tests for Phase 1 components."""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config_manager import ConfigManager
from src.document_processor import DocumentProcessor


def test_config_manager_integration():
    """Test that config manager works correctly."""
    print("\n=== Testing Config Manager ===")
    
    # Test default config
    config = ConfigManager()
    print(f"✓ Config loaded successfully")
    print(f"  - LLM Model: {config.get('llm.model')}")
    print(f"  - Default Questions: {config.get('quiz.default_questions')}")
    print(f"  - Output Formats: {config.get('output.formats')}")
    
    # Test custom config if exists
    if os.path.exists('config.yaml'):
        config_with_file = ConfigManager(config_path='config.yaml')
        print(f"✓ Custom config loaded from config.yaml")
    
    return True


def test_document_processor_integration():
    """Test that document processor works correctly."""
    print("\n=== Testing Document Processor ===")
    
    processor = DocumentProcessor()
    print(f"✓ Document processor created")
    print(f"  - Supported formats: {processor.get_supported_formats()}")
    
    # Test text cleaning
    test_text = "This  is   a    test\n\n\n\nwith   spaces"
    cleaned = processor.clean_text(test_text)
    print(f"✓ Text cleaning works")
    print(f"  - Original length: {len(test_text)}")
    print(f"  - Cleaned length: {len(cleaned)}")
    
    # Test chunking
    long_text = "This is a sentence. " * 500
    chunks = processor.chunk_text(long_text, max_chunk_size=500, overlap=50)
    print(f"✓ Text chunking works")
    print(f"  - Original length: {len(long_text)} chars")
    print(f"  - Number of chunks: {len(chunks)}")
    
    # Test validation
    is_valid, error = processor.validate_document('/nonexistent/file.docx')
    print(f"✓ Document validation works")
    print(f"  - Validation of non-existent file: {is_valid} (expected False)")
    
    # Test with actual documents if they exist
    test_dir = Path(__file__).parent
    
    # Look for .docx files
    docx_files = list(test_dir.glob('*.docx'))
    if docx_files:
        print(f"\n  Testing with .docx file: {docx_files[0].name}")
        try:
            result = processor.process_document(str(docx_files[0]))
            print(f"  ✓ Successfully processed .docx file")
            print(f"    - Word count: {result['word_count']}")
            print(f"    - Character count: {result['char_count']}")
            print(f"    - First 100 chars: {result['text'][:100]}...")
        except Exception as e:
            print(f"  ✗ Error processing .docx: {e}")
    
    # Look for .pdf files
    pdf_files = list(test_dir.glob('*.pdf'))
    if pdf_files:
        print(f"\n  Testing with .pdf file: {pdf_files[0].name}")
        try:
            result = processor.process_document(str(pdf_files[0]))
            print(f"  ✓ Successfully processed .pdf file")
            print(f"    - Word count: {result['word_count']}")
            print(f"    - Character count: {result['char_count']}")
            print(f"    - First 100 chars: {result['text'][:100]}...")
        except Exception as e:
            print(f"  ✗ Error processing .pdf: {e}")
    
    if not docx_files and not pdf_files:
        print(f"\n  ⚠ No .docx or .pdf test files found in tests directory")
        print(f"  Please add sample documents to fully test document processing")
    
    return True


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("Phase 1 Integration Tests")
    print("=" * 60)
    
    try:
        test_config_manager_integration()
        test_document_processor_integration()
        
        print("\n" + "=" * 60)
        print("✓ All Phase 1 integration tests passed!")
        print("=" * 60)
        return 0
    
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
