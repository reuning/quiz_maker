# Quiz Generator

A local LLM-powered quiz generation tool that creates multiple-choice quizzes from student assignments and documents.

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
ollama pull qwen3.5:27b-q4_K_M 
```

## Usage

### Command-Line Interface

The quiz maker provides a comprehensive CLI for generating quizzes from documents.

#### Basic Usage

```bash
# Generate quiz from a single document
uv run python quiz_maker.py --input essay.docx

# Process a PDF document
uv run python quiz_maker.py --input assignment.pdf
```

#### Advanced Options

```bash
# Specify output directory
uv run python quiz_maker.py --input essay.docx --output ./my_quizzes

# Generate specific number of questions
uv run python quiz_maker.py --input essay.docx --questions 10

# Choose output format (docx, html, or both)
uv run python quiz_maker.py --input essay.pdf --format html

# Use a different LLM model
uv run python quiz_maker.py --input essay.docx --model mistral:7b

# Generate quiz without answer key
uv run python quiz_maker.py --input essay.docx --no-answer-key

# Generate answer key without explanations
uv run python quiz_maker.py --input essay.docx --no-explanations
```

#### Batch Processing

```bash
# Process multiple files
uv run python quiz_maker.py --input essay1.docx essay2.pdf essay3.docx --output ./batch_quizzes

# Use glob patterns
uv run python quiz_maker.py --input ./assignments/*.docx --output ./quizzes
```

#### Debugging and Verbose Output

```bash
# Verbose mode (shows progress and INFO logs)
uv run python quiz_maker.py --input essay.docx --verbose

# Debug mode (shows detailed DEBUG logs)
uv run python quiz_maker.py --input essay.docx --debug
```

#### Help and Version

```bash
# Show help with all options
uv run python quiz_maker.py --help

# Show version
uv run python quiz_maker.py --version
```

#### CLI Options Reference

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--input` | `-i` | Input document file(s) or glob pattern | Required |
| `--output` | `-o` | Output directory for generated files | `./output` |
| `--questions` | `-q` | Number of questions to generate | From config |
| `--format` | `-f` | Output format: docx, html, or both | `both` |
| `--model` | `-m` | Ollama model to use | From config |
| `--config` | `-c` | Path to configuration file | `config.yaml` |
| `--no-answer-key` | | Skip answer key generation | Generate key |
| `--no-explanations` | | Exclude explanations from answer key | Include them |
| `--verbose` | `-v` | Enable verbose output (INFO level) | WARNING level |
| `--debug` | `-d` | Enable debug output (DEBUG level) | WARNING level |
| `--version` | | Show version information | |
| `--help` | `-h` | Show help message | |

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

# Run Phase 3 tests
uv run pytest tests/test_quiz_generator.py -v
```

## Configuration

The application uses [`config.yaml`](config.yaml) for configuration. Default settings:

```yaml
llm:
  model: "qwen3.5:27b-q4_K_M"
  temperature: 0.7
  max_tokens: 2000

quiz:
  default_questions: 5
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


### Basic Quiz Generation (Phase 3)

```python
from src.quiz_generator import create_quiz_generator

# Create quiz generator with default config
generator = create_quiz_generator(config_path='config.yaml')

# Generate quiz from a document
quiz = generator.generate_quiz_from_document('essay.docx')

# Access the generated quiz
print(f"Generated {quiz.num_questions} questions")
for i, question in enumerate(quiz.questions, 1):
    print(f"\n{i}. {question.question}")
    for key, option in sorted(question.options.items()):
        marker = "✓" if key == question.correct_answer else " "
        print(f"  [{marker}] {key}. {option}")
    print(f"  Explanation: {question.explanation}")
```

### Batch Processing

```python
# Process multiple documents
results = generator.generate_batch(
    ['essay1.docx', 'essay2.pdf', 'essay3.docx'],
    num_questions=7,
    validate_questions=True
)

# Check results
print(f"Successful: {results['success_count']}/{results['total']}")
for doc_path, quiz in results['successful']:
    print(f"✓ {doc_path}: {quiz.num_questions} questions")
```

### Custom Configuration

```python
# Generate with custom parameters
quiz = generator.generate_quiz_from_document(
    doc_path='essay.docx',
    num_questions=8,           # Custom number of questions
    validate_questions=True,   # Enable validation
    max_retries=5             # More retry attempts
)

# Add custom metadata
generator.add_metadata(quiz, {
    'course': 'Political Science 101',
    'assignment': 'Essay 1'
})
```

## Next Steps

**Phase 4: Output Generation** (Coming Next)
- Implement output formatter for Word and HTML
- Create quiz and answer key templates
- Add print-friendly styling

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
