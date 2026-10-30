"""Tests for the llama.cpp LLM interface."""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.llm_interface import ContextBudgetError, LLMInterface, create_llm_interface
from src.models import Question, QuizResponse


def _chat_response(payload):
    content = payload if isinstance(payload, str) else json.dumps(payload)
    return {"choices": [{"message": {"content": content}}]}


@pytest.fixture
def gguf_file(tmp_path):
    path = tmp_path / "model.gguf"
    path.write_bytes(b"GGUF")
    return path


@pytest.fixture
def mock_llama():
    with patch("src.llm_interface.Llama") as llama_cls:
        client = MagicMock()
        client.tokenize.side_effect = lambda text, **_: [1] * max(1, len(text) // 4)
        llama_cls.return_value = client
        yield llama_cls, client


@pytest.fixture
def sample_question_payload():
    return {
        "question": "What is the capital of France?",
        "options": {
            "A": "London",
            "B": "Paris",
            "C": "Berlin",
            "D": "Madrid",
        },
        "correct_answer": "B",
        "explanation": "Paris is the capital and largest city of France.",
    }


class TestLLMInterface:
    """Tests for LLMInterface."""

    def test_init_loads_model_with_configured_settings(self, gguf_file, mock_llama):
        llama_cls, client = mock_llama

        llm = LLMInterface(
            model_path=str(gguf_file),
            temperature=0.5,
            max_tokens=1500,
            n_ctx=16384,
            n_gpu_layers=24,
        )

        llama_cls.assert_called_once_with(
            model_path=str(gguf_file),
            n_ctx=16384,
            n_gpu_layers=24,
        )
        assert llm._client is client
        assert llm.model == "model.gguf"

    def test_init_rejects_missing_or_non_gguf_paths(self, tmp_path, mock_llama):
        llama_cls, _ = mock_llama
        non_gguf = tmp_path / "model.bin"
        non_gguf.write_bytes(b"data")

        with pytest.raises(ValueError, match=r"\.gguf"):
            LLMInterface(model_path=str(non_gguf))

        with pytest.raises(FileNotFoundError, match="not a readable file"):
            LLMInterface(model_path=str(tmp_path / "missing.gguf"))

        llama_cls.assert_not_called()

    def test_init_wraps_model_load_failures(self, gguf_file, mock_llama):
        llama_cls, _ = mock_llama
        llama_cls.side_effect = RuntimeError("corrupt GGUF header")

        with pytest.raises(RuntimeError, match="Failed to load GGUF model"):
            LLMInterface(model_path=str(gguf_file))

    def test_generate_quiz_passes_schema_and_validates_response(
        self, gguf_file, mock_llama, sample_question_payload
    ):
        llama_cls, client = mock_llama
        client.create_chat_completion.return_value = _chat_response(
            {"questions": [sample_question_payload]}
        )

        llm = LLMInterface(
            model_path=str(gguf_file), temperature=0.6, max_tokens=1200, n_ctx=8192
        )
        result = llm.generate_quiz(
            "France is a country in Europe. Paris is its capital.", num_questions=1
        )

        assert isinstance(result, QuizResponse)
        assert len(result.questions) == 1
        assert result.questions[0].correct_answer == "B"
        llama_cls.assert_called_once()

        call_kwargs = client.create_chat_completion.call_args.kwargs
        assert call_kwargs["temperature"] == 0.6
        assert call_kwargs["max_tokens"] == 1200
        assert call_kwargs["response_format"] == {
            "type": "json_object",
            "schema": QuizResponse.model_json_schema(),
        }
        assert [m["role"] for m in call_kwargs["messages"]] == ["system", "user"]
        assert "Paris is its capital." in call_kwargs["messages"][1]["content"]

    def test_generate_single_question_uses_question_schema(
        self, gguf_file, mock_llama, sample_question_payload
    ):
        _, client = mock_llama
        client.create_chat_completion.return_value = _chat_response(
            sample_question_payload
        )

        llm = LLMInterface(model_path=str(gguf_file))
        question = llm.generate_single_question(
            "France is a country in Europe.",
            existing_questions=["Existing question?"],
        )

        assert isinstance(question, Question)
        call_kwargs = client.create_chat_completion.call_args.kwargs
        assert call_kwargs["response_format"] == {
            "type": "json_object",
            "schema": Question.model_json_schema(),
        }
        assert "Existing question?" in call_kwargs["messages"][1]["content"]

    def test_prose_wrapped_json_is_not_recovered(
        self, gguf_file, mock_llama, sample_question_payload
    ):
        _, client = mock_llama
        wrapped = (
            f"Here is the quiz:\n{json.dumps({'questions': [sample_question_payload]})}"
        )
        client.create_chat_completion.return_value = _chat_response(wrapped)

        llm = LLMInterface(model_path=str(gguf_file))

        with patch("src.llm_interface.time.sleep"):
            with pytest.raises(RuntimeError, match="Failed to generate a valid quiz"):
                llm.generate_quiz("Test text", num_questions=1, max_retries=2)

        assert client.create_chat_completion.call_count == 2

    def test_retry_recovers_from_invalid_json_and_schema_errors(
        self, gguf_file, mock_llama, sample_question_payload
    ):
        _, client = mock_llama
        invalid_schema_payload = {
            "questions": [{**sample_question_payload, "correct_answer": "E"}]
        }
        client.create_chat_completion.side_effect = [
            _chat_response("not valid json"),
            _chat_response(invalid_schema_payload),
            _chat_response({"questions": [sample_question_payload]}),
        ]

        llm = LLMInterface(model_path=str(gguf_file))
        with patch("src.llm_interface.time.sleep"):
            result = llm.generate_quiz("Test text", num_questions=1, max_retries=3)

        assert isinstance(result, QuizResponse)
        assert client.create_chat_completion.call_count == 3

    def test_over_budget_prompt_fails_before_inference_without_retrying(
        self, gguf_file, mock_llama
    ):
        _, client = mock_llama
        client.tokenize.side_effect = None
        client.tokenize.return_value = [1] * 600

        llm = LLMInterface(
            model_path=str(gguf_file),
            max_tokens=1000,
            n_ctx=2000,
        )

        with pytest.raises(ContextBudgetError, match="context budget"):
            llm.generate_quiz("Long student paper", num_questions=1, max_retries=3)

        client.create_chat_completion.assert_not_called()


class TestCreateLLMInterface:
    """Tests for the create_llm_interface factory."""

    def test_create_llm_interface_propagates_config(self, gguf_file, mock_llama):
        llama_cls, _ = mock_llama
        config = {
            "llm": {
                "model_path": str(gguf_file),
                "n_ctx": 16384,
                "n_gpu_layers": 16,
                "temperature": 0.4,
                "max_tokens": 1800,
            }
        }

        llm = create_llm_interface(config)

        llama_cls.assert_called_once_with(
            model_path=str(gguf_file),
            n_ctx=16384,
            n_gpu_layers=16,
        )
        assert llm.model == gguf_file.name
