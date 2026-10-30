"""LLM interface for local, schema-constrained quiz generation."""

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

from .models import Question, QuizResponse, ValidationResult
from .prompts import PromptTemplates


logger = logging.getLogger(__name__)

ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


class ContextBudgetError(ValueError):
    """Raised when a prompt and its output reserve exceed the model context."""


class LLMInterface:
    """Interface for interacting with an in-process llama.cpp model."""

    # The chat-completion API applies the model's chat template internally.
    # Reserving this many tokens conservatively accounts for its role markers,
    # generation prompt, and special tokens during preflight budget checks.
    CHAT_TEMPLATE_TOKEN_ALLOWANCE = 128

    def __init__(
        self,
        model_path: str = "./models/model.gguf",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        n_ctx: int = 32768,
        n_gpu_layers: int = -1,
    ):
        """Load a GGUF model once for reuse across generation requests.

        Raises:
            FileNotFoundError: If the GGUF file does not exist or is unreadable.
            ValueError: If the model path or context settings are invalid.
            RuntimeError: If llama-cpp-python is unavailable or model loading fails.
        """
        if Llama is None:
            raise RuntimeError(
                "llama-cpp-python is not installed. Install the project dependencies "
                "with Metal support before loading a local model."
            )

        path = Path(model_path).expanduser()
        if path.suffix.lower() != ".gguf":
            raise ValueError("Model path must point to a .gguf file")
        if not path.is_file() or not os.access(path, os.R_OK):
            raise FileNotFoundError(f"GGUF model is not a readable file: {path}")
        if isinstance(n_ctx, bool) or not isinstance(n_ctx, int) or n_ctx <= 0:
            raise ValueError("n_ctx must be a positive integer")
        if (
            isinstance(max_tokens, bool)
            or not isinstance(max_tokens, int)
            or max_tokens <= 0
        ):
            raise ValueError("max_tokens must be a positive integer")
        if isinstance(n_gpu_layers, bool) or not isinstance(n_gpu_layers, int):
            raise ValueError("n_gpu_layers must be an integer")

        self.model_path = str(path)
        self.model = path.name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.prompts = PromptTemplates()

        try:
            self._client = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_gpu_layers=self.n_gpu_layers,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load GGUF model '{self.model_path}' with llama.cpp: {exc}"
            ) from exc

    def generate_quiz(
        self,
        text: str,
        num_questions: int = 7,
        num_options: int = 4,
        max_retries: int = 3,
    ) -> QuizResponse:
        """Generate a schema-validated quiz from the provided text."""
        prompt = self.prompts.get_quiz_generation_prompt(
            text, num_questions, num_options
        )
        quiz_response = self._generate_and_validate(
            prompt=prompt,
            system_prompt=self.prompts.get_system_prompt(),
            response_model=QuizResponse,
            operation="generate a valid quiz",
            max_retries=max_retries,
        )

        if len(quiz_response.questions) < num_questions:
            logger.warning(
                "Got %d questions, expected %d",
                len(quiz_response.questions),
                num_questions,
            )
        logger.info("Successfully generated %d questions", len(quiz_response.questions))
        return quiz_response

    def _count_prompt_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Conservatively count message content and chat-template overhead."""
        content_tokens = sum(
            len(
                self._client.tokenize(
                    message["content"].encode("utf-8"),
                    add_bos=False,
                    special=True,
                )
            )
            for message in messages
        )
        return content_tokens + 1 + self.CHAT_TEMPLATE_TOKEN_ALLOWANCE

    def _check_context_budget(self, messages: List[Dict[str, str]]) -> None:
        """Reject over-budget prompts before llama.cpp can truncate them."""
        prompt_tokens = self._count_prompt_tokens(messages)
        required_tokens = prompt_tokens + self.max_tokens
        if required_tokens > self.n_ctx:
            raise ContextBudgetError(
                f"Prompt exceeds the llama.cpp context budget: {prompt_tokens} "
                f"prompt tokens (including a {self.CHAT_TEMPLATE_TOKEN_ALLOWANCE}-token "
                f"chat-template allowance) plus {self.max_tokens} output tokens "
                f"requires {required_tokens} tokens, but n_ctx is {self.n_ctx}. "
                "Shorten the source text, reduce llm.max_tokens, or increase llm.n_ctx."
            )
        logger.debug(
            "Context budget: %d prompt tokens + %d output tokens <= %d",
            prompt_tokens,
            self.max_tokens,
            self.n_ctx,
        )

    def _call_llama(
        self, prompt: str, system_prompt: str, schema: Dict[str, Any]
    ) -> str:
        """Make one schema-constrained llama.cpp chat-completion request."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        self._check_context_budget(messages)

        try:
            response = self._client.create_chat_completion(
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object", "schema": schema},
            )
            content = response["choices"][0]["message"]["content"]
        except Exception as exc:
            raise RuntimeError(f"llama.cpp chat completion failed: {exc}") from exc

        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("llama.cpp returned empty response content")
        return content

    @staticmethod
    def _parse_response(
        response: str, response_model: Type[ResponseModel]
    ) -> ResponseModel:
        """Parse strict JSON and validate it with the requested Pydantic model."""
        return response_model.model_validate(json.loads(response))

    def _generate_and_validate(
        self,
        prompt: str,
        system_prompt: str,
        response_model: Type[ResponseModel],
        operation: str,
        max_retries: int,
    ) -> ResponseModel:
        """Generate and validate a response, retrying only transient failures."""
        for attempt in range(max_retries):
            try:
                response = self._call_llama(
                    prompt, system_prompt, response_model.model_json_schema()
                )
                return self._parse_response(response, response_model)
            except ContextBudgetError:
                raise
            except (json.JSONDecodeError, ValidationError, RuntimeError) as exc:
                logger.warning(
                    "%s attempt %d/%d failed: %s",
                    operation.capitalize(),
                    attempt + 1,
                    max_retries,
                    exc,
                )
                if attempt == max_retries - 1:
                    raise RuntimeError(
                        f"Failed to {operation} after {max_retries} attempts. "
                        f"Last error: {exc}"
                    ) from exc
                time.sleep(1)

        raise RuntimeError(f"Failed to {operation}: max_retries must be positive")

    def improve_question(
        self, question: Question, issue: str, max_retries: int = 2
    ) -> Question:
        """Improve a specific question based on identified issues."""
        return self._generate_and_validate(
            prompt=self.prompts.get_question_improvement_prompt(
                question.model_dump(), issue
            ),
            system_prompt=self.prompts.get_system_prompt(),
            response_model=Question,
            operation="improve question",
            max_retries=max_retries,
        )

    def generate_single_question(
        self,
        text: str,
        num_options: int = 4,
        existing_questions: Optional[List[str]] = None,
        max_retries: int = 3,
    ) -> Question:
        """Generate one schema-validated question from the provided text."""
        return self._generate_and_validate(
            prompt=self.prompts.get_single_question_prompt(
                text, num_options, existing_questions
            ),
            system_prompt=self.prompts.get_system_prompt(),
            response_model=Question,
            operation="generate a single question",
            max_retries=max_retries,
        )

    def validate_question_relevance(
        self, question: Question, source_text: str
    ) -> Dict[str, Any]:
        """Validate question relevance, preserving the existing fallback result."""
        try:
            result = self._generate_and_validate(
                prompt=self.prompts.get_validation_prompt(
                    question.model_dump(), source_text
                ),
                system_prompt=self.prompts.get_system_prompt(),
                response_model=ValidationResult,
                operation="validate question relevance",
                max_retries=1,
            )
            return result.model_dump()
        except Exception as exc:
            logger.warning("Question validation failed: %s", exc)
            return {
                "is_relevant": True,
                "confidence": 0.5,
                "reason": f"Validation error: {exc}",
            }


def create_llm_interface(config: Dict[str, Any]) -> LLMInterface:
    """Create an LLM interface from llama.cpp configuration settings."""
    llm_config = config.get("llm", {})
    return LLMInterface(
        model_path=llm_config.get("model_path", "./models/model.gguf"),
        temperature=llm_config.get("temperature", 0.7),
        max_tokens=llm_config.get("max_tokens", 2000),
        n_ctx=llm_config.get("n_ctx", 32768),
        n_gpu_layers=llm_config.get("n_gpu_layers", -1),
    )
