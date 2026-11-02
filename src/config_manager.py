"""Configuration management for the quiz generator."""

import os
import copy
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigManager:
    """Manages application configuration from YAML files."""

    DEFAULT_CONFIG = {
        "llm": {
            "model_path": "./models/model.gguf",
            "n_ctx": 32768,
            "n_gpu_layers": -1,
            "temperature": 0.7,
            "max_tokens": 2000,
        },
        "quiz": {
            "default_questions": 7,
        },
        "output": {
            "formats": ["docx", "html"],
            "quiz_dir": "./output/quizzes",
            "answer_key_dir": "./output/answer_keys",
            "include_explanations": True,
        },
    }

    def __init__(
        self,
        config_path: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the configuration manager.

        Args:
            config_path: Path to the configuration YAML file. If None, uses default config.
            overrides: Optional dictionary of configuration overrides applied before validation.
        """
        self.config_path = config_path
        self.config = self._load_config()
        if overrides:
            self.config = self._merge_configs(self.config, overrides)
        self._validate_config()
        self._ensure_directories()

    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file or use defaults.

        Returns:
            Configuration dictionary
        """
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    user_config = yaml.safe_load(f)
                    # Merge user config with defaults (use deep copy to avoid mutation)
                    return self._merge_configs(
                        copy.deepcopy(self.DEFAULT_CONFIG), user_config
                    )
            except Exception as e:
                print(f"Warning: Failed to load config from {self.config_path}: {e}")
                print("Using default configuration.")
                return copy.deepcopy(self.DEFAULT_CONFIG)
        else:
            return copy.deepcopy(self.DEFAULT_CONFIG)

    def _merge_configs(self, base: Dict, override: Dict) -> Dict:
        """
        Recursively merge override config into base config.

        Args:
            base: Base configuration dictionary
            override: Override configuration dictionary

        Returns:
            Merged configuration dictionary
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                base[key] = self._merge_configs(base[key], value)
            else:
                base[key] = value
        return base

    def _validate_config(self) -> None:
        """Validate configuration values."""
        llm = self.config.get("llm", {})
        model_path = llm.get("model_path")
        if not isinstance(model_path, str) or not model_path.strip():
            raise ValueError("llm.model_path must be configured")

        path = Path(model_path).expanduser()
        if path.suffix.lower() != ".gguf":
            raise ValueError("llm.model_path must point to a .gguf file")
        if not path.is_file() or not os.access(path, os.R_OK):
            raise ValueError(f"llm.model_path is not a readable file: {model_path}")

        for key in ("n_ctx", "max_tokens"):
            value = llm.get(key)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"llm.{key} must be a positive integer")

        n_gpu_layers = llm.get("n_gpu_layers")
        if isinstance(n_gpu_layers, bool) or not isinstance(n_gpu_layers, int):
            raise ValueError("llm.n_gpu_layers must be an integer")

        # Validate output formats
        output = self.config.get("output", {})
        valid_formats = ["docx", "html"]
        for fmt in output.get("formats", []):
            if fmt not in valid_formats:
                raise ValueError(
                    f"Invalid output format: {fmt}. Must be one of {valid_formats}"
                )

    def _ensure_directories(self) -> None:
        """Create output directories if they don't exist."""
        output = self.config.get("output", {})
        quiz_dir = output.get("quiz_dir")
        answer_key_dir = output.get("answer_key_dir")

        if quiz_dir:
            Path(quiz_dir).mkdir(parents=True, exist_ok=True)

        if answer_key_dir:
            Path(answer_key_dir).mkdir(parents=True, exist_ok=True)

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.

        Args:
            key_path: Dot-separated path to the config value (e.g., 'llm.model_path')
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            >>> config.get('llm.model_path')
            './models/model.gguf'
        """
        keys = key_path.split(".")
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any) -> None:
        """
        Set a configuration value using dot notation.

        Args:
            key_path: Dot-separated path to the config value (e.g., 'llm.model_path')
            value: Value to set

        Example:
            >>> config.set('llm.model_path', './models/model.gguf')
        """
        keys = key_path.split(".")
        target = self.config

        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]

        target[keys[-1]] = value

    def save(self, output_path: Optional[str] = None) -> None:
        """
        Save current configuration to a YAML file.

        Args:
            output_path: Path to save the config. If None, uses self.config_path
        """
        save_path = output_path or self.config_path

        if not save_path:
            raise ValueError("No output path specified for saving configuration")

        with open(save_path, "w") as f:
            yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)

    def get_all(self) -> Dict[str, Any]:
        """
        Get the entire configuration dictionary.

        Returns:
            Complete configuration dictionary
        """
        return self.config.copy()

    def __repr__(self) -> str:
        """String representation of the configuration."""
        return f"ConfigManager(config_path={self.config_path})"
