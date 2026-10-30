> [!WARNING] 
> This was a mostly vibe coded project in VS with Claude Sonnet 4.5 through [OpenRouter](https://openrouter.ai/). This is the ["alpha-slop" version.](https://simonwillison.net/2026/Jan/11/answers/)

# Quiz Generator

A local LLM-powered quiz generation tool that creates multiple-choice quizzes from student assignments and documents. Everything runs locally in-process via [`llama-cpp-python`](https://github.com/abetlen/llama-cpp-python) — no cloud API or background inference daemon required. There are [examples](/example/) if you are interested in what the results look like.

It uses grammar-constrained JSON output (`QuizResponse` / `Question` Pydantic schemas), preflight context-budget checks so long papers are never silently truncated, quality validation checks, and Python-side option shuffling (without shuffling, the model puts nearly every answer at B).

## Why?

There are two related purposes to this idea:

1) A student who has spent time working and writing a paper ought to be able to easily answer questions about that paper. Yes, this was partially created out of a concern over AI use.  

2) I am a firm believer that the purpose of writing is to learn, I hope that this quiz demonstrates to students what they learned through their own research.

## Installation

### Prerequisites

- Python 3.12 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- C/C++ build toolchain (Xcode Command Line Tools on macOS) for building `llama-cpp-python`
- A local `.gguf` chat model (tested with `Qwen3.5-27B` Q4_K_M)

### Setup

```bash
# Clone or navigate to the project directory
cd quiz_maker

# Install dependencies (on macOS with Apple Silicon, disable OpenMP if clang lacks libomp)
CMAKE_ARGS="-DGGML_OPENMP=OFF" uv sync

# Place your GGUF model at the configured path (default: ./models/model.gguf)
mkdir -p models
cp /path/to/your-model.gguf ./models/model.gguf
```

### Downloading a model

Download a GGUF instruct/chat model from [Hugging Face](https://huggingface.co/models?library=gguf) into the `models` directory. For example, to download a smaller Q4_K_M model:

```bash
uvx --from huggingface_hub hf download \
  bartowski/Qwen2.5-14B-Instruct-GGUF \
  --include "*Q4_K_M.gguf" \
  --local-dir models
```

The `models` directory is gitignored, so downloaded model files will not be committed. To try a new model without changing the default configuration, pass its path with `--model`:

```bash
uv run python quiz_maker.py \
  --input example/example_doc1.docx \
  --model models/Qwen2.5-14B-Instruct-Q4_K_M.gguf
```

To make it the default, update `llm.model_path` in `config.yaml` instead. Q4_K_M is a good starting point for balancing quality, file size, and speed. Choose an instruct/chat GGUF with a chat template and a context length that supports the configured `n_ctx`; smaller models generally use less memory and run faster, but may produce lower-quality quizzes.

## Usage

### Command-Line Interface

The quiz maker loads the GGUF model once at startup, processes all requested documents, and exits.

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

# Use a different GGUF model file
uv run python quiz_maker.py --input essay.docx --model ./models/other-model.gguf

# Generate quiz without answer key
uv run python quiz_maker.py --input essay.docx --no-answer-key

# Generate answer key without explanations
uv run python quiz_maker.py --input essay.docx --no-explanations
```

#### Multiple Files

```bash
# Process multiple files (loads the GGUF model once)
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
| `--model`, `--model-path` | `-m` | Path to GGUF model file | From config |
| `--config` | `-c` | Path to configuration file | `config.yaml` |
| `--no-answer-key` | | Skip answer key generation | Generate key |
| `--no-explanations` | | Exclude explanations from answer key | Include them |
| `--verbose` | `-v` | Enable verbose output (INFO level) | WARNING level |
| `--debug` | `-d` | Enable debug output (DEBUG level) | WARNING level |
| `--version` | | Show version information | |
| `--help` | `-h` | Show help message | |

## Configuration

The application uses [`config.yaml`](config.yaml) for configuration:

```yaml
llm:
  model_path: "./models/model.gguf"
  n_ctx: 32768
  n_gpu_layers: -1
  temperature: 0.7
  max_tokens: 5000

quiz:
  default_questions: 5
  num_options: 4

output:
  formats: ["docx", "html"]
  quiz_dir: "./output/quizzes"
  answer_key_dir: "./output/answer_keys"
  include_explanations: true
```

### Memory and Context Window Notes

- `n_ctx` sets the total token budget (`prompt tokens + max_tokens`). Before calling the model, Quiz Maker tokenizes the prompt with the loaded GGUF tokenizer and raises an explicit error if the essay plus `max_tokens` exceeds `n_ctx`.
- `n_gpu_layers: -1` offloads all model layers to Metal/GPU. On a 32 GB Apple Silicon Mac, a 27B Q4_K_M model with `n_ctx: 32768` uses roughly 19 GB of unified memory. If memory pressure is high, lower `n_ctx` (for example `16384` or `8192`) or use a smaller GGUF model.
