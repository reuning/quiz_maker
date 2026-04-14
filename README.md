> [!WARNING] 
> This was a mostly vibe coded project as I wanted to port the latex exam class to Typst because of PDF accessibility issues (also Typst seems less frustrating?). I used [Roo Code](https://roocode.com/) in VS with Claude Sonnet 4.5 through [OpenRouter](https://openrouter.ai/). This is the ["alpha-slop" version.](https://simonwillison.net/2026/Jan/11/answers/)

# Quiz Generator

A local LLM-powered quiz generation tool that creates multiple-choice quizzes from student assignments and documents. There are [examples](/example/) if you are interested in what the results looks like. 

Currently it uses a local LLM through [Ollama](https://ollama.com/). There are validation checks to make sure it produces the right number of questions, and options. I also have set it up to use randomization via python on the answers (when I initially ran it without that almost every anser was B). I personally had good luck with [Qwen 3.5](https://ollama.com/library/qwen3.5/tags). 

## Installation

### Prerequisites

- Python 3.12 or higher
- UV package manager
- Ollama (for LLM functionality)

### Setup

```bash
# Clone or navigate to the project directory
cd quiz_maker

# Install dependencies (UV will create a virtual environment automatically)
uv sync

# Install Ollama (for LLM functionality)
# macOS/Linux:
curl -fsSL https://ollama.com/install.sh | sh

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

#### Multiple Files

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


## Configuration

The application uses [`config.yaml`](config.yaml) for configuration. Default settings:

```yaml
llm:
  model: "qwen3.5:27b-q4_K_M"
  temperature: 0.7
  max_tokens: 2000

quiz:
  default_questions: 5
  num_options: 4

output:
  formats: ["docx", "html"]
  quiz_dir: "./output/quizzes"
  answer_key_dir: "./output/answer_keys"
  include_explanations: true

processing:
  timeout_seconds: 120
```
