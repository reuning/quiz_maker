"""Unit tests for the configuration manager."""

import os
import sys

import pytest
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config_manager import ConfigManager


@pytest.fixture
def config_factory(tmp_path):
    model_path = tmp_path / "model.gguf"
    model_path.touch()

    def create_config(llm_overrides=None):
        llm_config = {"model_path": str(model_path)}
        if llm_overrides:
            llm_config.update(llm_overrides)
        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.safe_dump({"llm": llm_config}))
        return ConfigManager(config_path=str(config_path))

    return create_config


@pytest.fixture
def config(config_factory):
    return config_factory()


class TestConfigManager:
    def test_get_with_dot_notation(self, config):
        assert config.get("llm.model_path").endswith("model.gguf")
        assert config.get("llm.n_ctx") == 32768

    def test_get_with_default(self, config):
        assert config.get("nonexistent.key", "default") == "default"
        assert config.get("llm.nonexistent", None) is None

    def test_set_config_value(self, config):
        config.set("llm.n_ctx", 16384)
        assert config.get("llm.n_ctx") == 16384

        config.set("quiz.default_questions", 10)
        assert config.get("quiz.default_questions") == 10

    def test_load_custom_config(self, config_factory):
        config = config_factory(
            {"n_ctx": 16384, "n_gpu_layers": 20, "max_tokens": 4000}
        )
        assert config.get("llm.n_ctx") == 16384
        assert config.get("llm.n_gpu_layers") == 20
        assert config.get("llm.max_tokens") == 4000

    def test_cli_overrides_apply_before_validation(self, tmp_path):
        override_model = tmp_path / "override.gguf"
        override_model.touch()
        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            yaml.safe_dump({"llm": {"model_path": str(tmp_path / "missing.gguf")}})
        )

        config = ConfigManager(
            config_path=str(config_path),
            overrides={"llm": {"model_path": str(override_model)}},
        )
        assert config.get("llm.model_path") == str(override_model)

    @pytest.mark.parametrize("model_path", [None, "", "missing.gguf", "model.bin"])
    def test_invalid_model_path(self, config_factory, model_path):
        with pytest.raises(ValueError, match="llm.model_path"):
            config_factory({"model_path": model_path})

    @pytest.mark.parametrize("key", ["n_ctx", "max_tokens"])
    @pytest.mark.parametrize("value", [0, -1, 1.5, "32768", True])
    def test_invalid_token_limits(self, config_factory, key, value):
        with pytest.raises(ValueError, match=f"llm.{key}"):
            config_factory({key: value})

    @pytest.mark.parametrize("value", [1.5, "all", True])
    def test_invalid_gpu_layers(self, config_factory, value):
        with pytest.raises(ValueError, match="llm.n_gpu_layers"):
            config_factory({"n_gpu_layers": value})
