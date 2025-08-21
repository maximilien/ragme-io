# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

from unittest.mock import Mock, patch

import pytest

from src.ragme.utils.config_manager import config


class TestLanguageConfiguration:
    """Test language configuration functionality."""

    def test_llm_language_config_defaults(self):
        """Test that LLM language configuration has correct defaults."""
        llm_config = config.get_llm_config()

        # Test default values
        assert llm_config.get("language", "en") == "en"
        assert llm_config.get("force_english", True) is True

    def test_language_instruction_generation(self):
        """Test that language instructions are generated correctly."""
        from src.ragme.agents.ragme_agent import RagMeAgent

        # Mock the ragme instance
        mock_ragme = Mock()
        mock_ragme.vector_db = Mock()

        # Test with force_english=True
        with patch("src.ragme.agents.ragme_agent.config") as mock_config:
            mock_config.get_llm_config.return_value = {
                "force_english": True,
                "language": "en",
                "temperature": 0.7,
            }
            mock_config.get_agent_config.return_value = {"llm_model": "gpt-4o-mini"}

            agent = RagMeAgent(mock_ragme)
            assert agent.force_english is True
            assert agent.default_language == "en"

        # Test with force_english=False and different language
        with patch("src.ragme.agents.ragme_agent.config") as mock_config:
            mock_config.get_llm_config.return_value = {
                "force_english": False,
                "language": "fr",
                "temperature": 0.7,
            }
            mock_config.get_agent_config.return_value = {"llm_model": "gpt-4o-mini"}

            agent = RagMeAgent(mock_ragme)
            assert agent.force_english is False
            assert agent.default_language == "fr"

    def test_config_file_language_settings(self):
        """Test that language settings are properly loaded from config file."""
        # This test assumes config.yaml exists and has language settings
        try:
            llm_config = config.get_llm_config()

            # Check that language settings exist
            assert "language" in llm_config or "force_english" in llm_config

            # If force_english is set, it should be a boolean
            if "force_english" in llm_config:
                assert isinstance(llm_config["force_english"], bool)

            # If language is set, it should be a string
            if "language" in llm_config:
                assert isinstance(llm_config["language"], str)

        except FileNotFoundError:
            # Skip test if config file doesn't exist
            pytest.skip("config.yaml not found")

    def test_frontend_speech_language_config(self):
        """Test that frontend speech language configuration is accessible."""
        frontend_config = config.get_frontend_config()
        settings = frontend_config.get("settings", {})

        # Check if speech_language is configured
        if "speech_language" in settings:
            assert isinstance(settings["speech_language"], str)
            # Should be a valid language code format
            assert (
                "-" in settings["speech_language"]
                or len(settings["speech_language"]) == 2
            )


if __name__ == "__main__":
    pytest.main([__file__])
