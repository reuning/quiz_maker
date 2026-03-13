# Quiz Generator

A local LLM-powered quiz generation tool that creates multiple-choice quizzes from student assignments and documents.

## Project Status

**Phase 1: Foundation (Core Infrastructure) - ✅ COMPLETED**
**Phase 2: LLM Integration - ✅ COMPLETED**

### Implemented Components

#### Phase 1: Foundation
1. **Project Structure**
   - Created modular directory structure
   - Initialized Python package with proper `__init__.py` files
   - Set up output directories for quizzes and answer keys

2. **Configuration System** ([`src/config_manager.py`](src/config_manager.py))
   - Flexible YAML-based configuration
   - Default configuration with sensible values
   - Configuration validation and merging
   - Dot-notation access to config values
   - Automatic directory creation

3. **Document Processing** ([`src/document_processor.py`](src/document_processor.py))
   - Support for Word documents (.docx)
   - Support for PDF documents (.pdf)
   - Text extraction and cleaning
   - Document validation
   - Text chunking for large documents
   - Comprehensive error handling

#### Phase 2: LLM Integration
4. **Data Models** ([`src/models.py`](src/models.py))
   - Pydantic models for type safety and validation
   - Question, Quiz, QuizResponse models
   - ValidationResult and DocumentInfo models
   - Automatic validation of question structure

5. **Prompt Templates** ([`src/prompts.py`](src/prompts.py))
   - Structured prompts for quiz generation
   - Question improvement prompts
   - Validation prompts
   - System prompts for LLM behavior

6. **LLM Interface** ([`src/llm_interface.py`](src/llm_interface.py))
   - Integration with Ollama for local LLM inference
   - Automatic retry logic for failed generations
   - JSON response parsing with error handling
   - Question improvement functionality
   - Connection verification

7. **Question Validator** ([`src/question_validator.py`](src/question_validator.py))
   - Quality checks for generated questions
   - Duplicate detection
   - Relevance checking
   - Option validation
   - Quiz-level validation

## Installation

### Prerequisites

- Python 3.12 or higher
- **UV package manager (REQUIRED for this project)**
- Ollama (for LLM functionality)

### Setup

**Note: This project uses UV for dependency management. All commands should use `uv run` prefix.**

```bash
# Clone or navigate to the project directory
cd quiz_maker

# Install dependencies (UV will create a virtual environment automatically)
uv sync

# Install Ollama (for LLM functionality)
# macOS/Linux:
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a recommended model
ollama pull llama3.1:8b
```

### Running Tests

**Important: Use `uv run` for all Python commands in this project.**

```bash
# Run all tests
uv run pytest -v

# Run specific test file
uv run pytest tests/test_models.py -v

# Run Phase 1 tests
uv run pytest tests/test_config_manager.py tests/test_document_processor.py -v

# Run Phase 2 tests
uv run pytest tests/test_models.py tests/test_question_validator.py tests/test_llm_interface.py -v
```

## Configuration

The application uses [`config.yaml`](config.yaml) for configuration. Default settings:

```yaml
llm:
  model: "llama3.1:8b"
  temperature: 0.7
  max_tokens: 2000

quiz:
  default_questions: 7
  min_questions: 5
  max_questions: 10
  num_options: 4

output:
  formats: ["docx", "html"]
  quiz_dir: "./output/quizzes"
  answer_key_dir: "./output/answer_keys"
  include_explanations: true

processing:
  batch_size: 5
  timeout_seconds: 120
```

## Testing

### Run All Tests

```bash
# With UV
uv run pytest tests/ -v

# With pip
pytest tests/ -v
```

### Run Integration Tests

```bash
# With UV
uv run python tests/test_integration.py

# With pip
python tests/test_integration.py
```

## Project Structure

```
quiz_maker/
├── config.yaml              # Configuration file
├── requirements.txt         # Python dependencies
├── pyproject.toml          # UV project configuration
├── README.md               # This file
├── src/                    # Source code
│   ├── __init__.py
│   ├── config_manager.py   # Configuration management
│   └── document_processor.py # Document text extraction
├── tests/                  # Test suite
│   ├── __init__.py
│   ├── test_config_manager.py
│   ├── test_document_processor.py
│   ├── test_integration.py
│   ├── test_document_1.docx  # Sample Word document
│   └── test_document_2.pdf   # Sample PDF document
├── output/                 # Generated output
│   ├── quizzes/           # Generated quiz files
│   └── answer_keys/       # Generated answer keys
└── plans/                  # Project planning documents
    ├── architecture.md
    └── implementation_guide.md
```

## Phase 1 Features

### Configuration Manager

- Load configuration from YAML files
- Merge custom configs with defaults
- Validate configuration values
- Get/set config values using dot notation
- Save configuration to file

### Document Processor

- Extract text from Word documents (.docx)
- Extract text from PDF documents (.pdf)
- Clean and normalize extracted text
- Validate documents before processing
- Chunk large documents for processing
- Calculate document statistics (word count, character count)

## Next Steps

**Phase 2: LLM Integration** (Coming Next)
- Implement LLM interface for Ollama
- Create structured prompts for quiz generation
- Add question validation
- Test with local LLM models

## Development

### Code Quality

```bash
# Format code with Black
uv run black src/ tests/

# Lint code with Flake8
uv run flake8 src/ tests/
```

### Adding New Features

Follow the implementation guide in [`plans/implementation_guide.md`](plans/implementation_guide.md) for the recommended order of implementation.

## License

This project is for educational purposes.

## Privacy & Security

- All processing happens locally on your machine
- No data is sent to external services
- Documents are not stored after processing
- You control all output locations
