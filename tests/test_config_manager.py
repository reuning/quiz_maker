"""Unit tests for the configuration manager."""

import os
import tempfile
import pytest
import yaml
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config_manager import ConfigManager


class TestConfigManager:
    """Test cases for ConfigManager class."""
    
    def test_default_config_loads(self):
        """Test that default configuration loads correctly."""
        config = ConfigManager()
        assert config.get('llm.model') == 'llama3.1:8b'
        assert config.get('quiz.default_questions') == 7
        assert config.get('output.formats') == ['docx', 'html']
    
    def test_get_with_dot_notation(self):
        """Test getting config values with dot notation."""
        config = ConfigManager()
        assert config.get('llm.temperature') == 0.7
        assert config.get('quiz.num_options') == 4
        assert config.get('processing.timeout_seconds') == 120
    
    def test_get_with_default(self):
        """Test getting non-existent keys returns default."""
        config = ConfigManager()
        assert config.get('nonexistent.key', 'default') == 'default'
        assert config.get('llm.nonexistent', None) is None
    
    def test_set_config_value(self):
        """Test setting configuration values."""
        config = ConfigManager()
        config.set('llm.model', 'mistral:7b')
        assert config.get('llm.model') == 'mistral:7b'
        
        config.set('quiz.default_questions', 10)
        assert config.get('quiz.default_questions') == 10
    
    def test_load_custom_config(self):
        """Test loading configuration from a custom file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            custom_config = {
                'llm': {'model': 'custom-model'},
                'quiz': {
                    'default_questions': 8
                }
            }
            yaml.dump(custom_config, f)
            temp_path = f.name
        
        try:
            config = ConfigManager(config_path=temp_path)
            assert config.get('llm.model') == 'custom-model'
            assert config.get('quiz.default_questions') == 8
            # Should still have defaults for unspecified values
            assert config.get('quiz.num_options') == 4
        finally:
            os.unlink(temp_path)
    
    def test_save_config(self):
        """Test saving configuration to file."""
        config = ConfigManager()
        config.set('llm.model', 'test-model')
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = f.name
        
        try:
            config.save(temp_path)
            
            # Load the saved config
            with open(temp_path, 'r') as f:
                saved_config = yaml.safe_load(f)
            
            assert saved_config['llm']['model'] == 'test-model'
        finally:
            os.unlink(temp_path)
    
    def test_get_all(self):
        """Test getting entire configuration."""
        config = ConfigManager()
        all_config = config.get_all()
        
        assert 'llm' in all_config
        assert 'quiz' in all_config
        assert 'output' in all_config
        assert 'processing' in all_config
