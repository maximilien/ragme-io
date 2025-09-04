# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""
Integration tests for i18n (internationalization) functionality.

These tests verify that the LLM agents respond in the configured language
regardless of the input language.
"""

import asyncio
import locale
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.ragme.utils.config_manager import ConfigManager


class TestI18nIntegration(unittest.TestCase):
    """Integration tests for i18n functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.config_manager = ConfigManager()

    def test_ragme_agent_responds_in_configured_language(self):
        """Test that RagMeAgent responds in the configured language."""
        from src.ragme.agents.ragme_agent import RagMeAgent

        # Mock the ragme instance
        mock_ragme = Mock()
        mock_ragme.vector_db = Mock()

        # Test with French language configuration
        with patch("src.ragme.agents.ragme_agent.config") as mock_config:
            mock_config.get_agent_config.return_value = {"llm_model": "gpt-4o-mini"}
            mock_config.get_llm_config.return_value = {"temperature": 0.7}
            mock_config.get_preferred_language.return_value = "fr"
            mock_config.get_language_name.return_value = "French"

            agent = RagMeAgent(mock_ragme)

            # Verify the system prompt contains French language instruction
            system_prompt = agent.agent.system_prompt
            self.assertIn("French", system_prompt)
            self.assertIn("only responds in French", system_prompt)
            self.assertIn("MUST ALWAYS respond in French", system_prompt)

    def test_functional_agent_responds_in_configured_language(self):
        """Test that FunctionalAgent responds in the configured language."""
        from src.ragme.agents.functional_agent import FunctionalAgent

        # Mock the ragme instance
        mock_ragme = Mock()

        # Test with Spanish language configuration
        with patch("src.ragme.agents.functional_agent.config") as mock_config:
            mock_config.get_agent_config.return_value = {"llm_model": "gpt-4o-mini"}
            mock_config.get_llm_config.return_value = {"temperature": 0.7}
            mock_config.get_preferred_language.return_value = "es"
            mock_config.get_language_name.return_value = "Spanish"

            agent = FunctionalAgent(mock_ragme)

            # Verify the system prompt contains Spanish language instruction
            system_prompt = agent.agent.system_prompt
            self.assertIn("Spanish", system_prompt)
            self.assertIn("only responds in Spanish", system_prompt)
            self.assertIn("MUST ALWAYS respond in Spanish", system_prompt)

    def test_query_agent_responds_in_configured_language(self):
        """Test that QueryAgent responds in the configured language."""
        from src.ragme.agents.query_agent import QueryAgent

        # Mock the vector database
        mock_vector_db = Mock()

        # Test with German language configuration
        with patch("src.ragme.agents.query_agent.config") as mock_config:
            mock_config.get_agent_config.return_value = {"llm_model": "gpt-4o-mini"}
            mock_config.get_llm_config.return_value = {"temperature": 0.7}
            mock_config.get_query_top_k.return_value = 5
            mock_config.get_query_text_relevance_threshold.return_value = 0.4
            mock_config.get_query_image_relevance_threshold.return_value = 0.3
            mock_config.get_query_text_rerank_top_k.return_value = 3
            mock_config.get_query_text_rerank_enabled.return_value = False
            mock_config.get_query_image_rerank_top_k.return_value = 10
            mock_config.get_query_image_rerank_enabled.return_value = True
            mock_config.get_preferred_language.return_value = "de"
            mock_config.get_language_name.return_value = "German"

            agent = QueryAgent(mock_vector_db)

            # Verify the agent has German language configuration
            self.assertEqual(agent.preferred_language, "de")
            self.assertEqual(agent.language_name, "German")

    def test_language_detection_from_system_locale(self):
        """Test that language detection works from system locale."""
        from src.ragme.utils.config_manager import ConfigManager

        config_manager = ConfigManager()

        # Test with French locale
        with patch("locale.getdefaultlocale") as mock_locale:
            mock_locale.return_value = ("fr_FR", "UTF-8")

            with patch.object(config_manager, "get_i18n_config") as mock_i18n:
                mock_i18n.return_value = {"preferred_language": "default"}

                language = config_manager.get_preferred_language()
                self.assertEqual(language, "fr")

    def test_language_detection_from_environment_variables(self):
        """Test that language detection works from environment variables."""
        from src.ragme.utils.config_manager import ConfigManager

        config_manager = ConfigManager()

        # Test with Spanish environment variable
        with patch("locale.getdefaultlocale") as mock_locale:
            mock_locale.side_effect = locale.Error("No locale")

            with patch.dict(os.environ, {"LANG": "es_ES.UTF-8"}):
                with patch.object(config_manager, "get_i18n_config") as mock_i18n:
                    mock_i18n.return_value = {"preferred_language": "default"}

                    language = config_manager.get_preferred_language()
                    self.assertEqual(language, "es")

    def test_language_name_mapping(self):
        """Test that language codes are correctly mapped to language names."""
        from src.ragme.utils.config_manager import ConfigManager

        config_manager = ConfigManager()

        test_cases = [
            ("en", "English"),
            ("fr", "French"),
            ("es", "Spanish"),
            ("de", "German"),
            ("it", "Italian"),
            ("pt", "Portuguese"),
            ("ru", "Russian"),
            ("ja", "Japanese"),
            ("ko", "Korean"),
            ("zh", "Chinese"),
            ("ar", "Arabic"),
            ("hi", "Hindi"),
        ]

        for language_code, expected_name in test_cases:
            with self.subTest(language_code=language_code):
                name = config_manager.get_language_name(language_code)
                self.assertEqual(name, expected_name)

    def test_system_prompt_language_consistency(self):
        """Test that all agents use consistent language instruction format."""
        from src.ragme.agents.functional_agent import FunctionalAgent
        from src.ragme.agents.query_agent import QueryAgent
        from src.ragme.agents.ragme_agent import RagMeAgent

        # Mock instances
        mock_ragme = Mock()
        mock_ragme.vector_db = Mock()
        mock_vector_db = Mock()

        # Test with Italian language configuration
        with (
            patch("src.ragme.agents.ragme_agent.config") as mock_ragme_config,
            patch("src.ragme.agents.functional_agent.config") as mock_func_config,
            patch("src.ragme.agents.query_agent.config") as mock_query_config,
        ):
            # Configure all mocks with Italian language
            for mock_config in [mock_ragme_config, mock_func_config, mock_query_config]:
                mock_config.get_agent_config.return_value = {"llm_model": "gpt-4o-mini"}
                mock_config.get_llm_config.return_value = {"temperature": 0.7}
                mock_config.get_preferred_language.return_value = "it"
                mock_config.get_language_name.return_value = "Italian"

            # Add query-specific config
            mock_query_config.get_query_top_k.return_value = 5
            mock_query_config.get_query_text_relevance_threshold.return_value = 0.4
            mock_query_config.get_query_image_relevance_threshold.return_value = 0.3
            mock_query_config.get_query_text_rerank_top_k.return_value = 3
            mock_query_config.get_query_text_rerank_enabled.return_value = False
            mock_query_config.get_query_image_rerank_top_k.return_value = 10
            mock_query_config.get_query_image_rerank_enabled.return_value = True

            # Create agents
            ragme_agent = RagMeAgent(mock_ragme)
            functional_agent = FunctionalAgent(mock_ragme)
            query_agent = QueryAgent(mock_vector_db)

            # Verify all agents have Italian language configuration
            self.assertEqual(ragme_agent.language_name, "Italian")
            self.assertEqual(functional_agent.language_name, "Italian")
            self.assertEqual(query_agent.language_name, "Italian")

            # Verify system prompts contain Italian language instruction
            ragme_prompt = ragme_agent.agent.system_prompt
            func_prompt = functional_agent.agent.system_prompt

            self.assertIn("Italian", ragme_prompt)
            self.assertIn("Italian", func_prompt)
            self.assertIn("only responds in Italian", ragme_prompt)
            self.assertIn("only responds in Italian", func_prompt)

    def test_fallback_to_english_when_language_unknown(self):
        """Test that unknown language codes fallback to English."""
        from src.ragme.utils.config_manager import ConfigManager

        config_manager = ConfigManager()

        # Test unknown language code
        name = config_manager.get_language_name("unknown_lang")
        self.assertEqual(name, "English")

        # Test empty string
        name = config_manager.get_language_name("")
        self.assertEqual(name, "English")

        # Test None
        name = config_manager.get_language_name(None)
        # This should use the preferred language from config, which defaults to English
        self.assertEqual(name, "English")

    def test_locale_detection_consistency(self):
        """Test that locale detection is consistent with language detection."""
        from src.ragme.utils.config_manager import ConfigManager

        config_manager = ConfigManager()

        # Test with French locale
        with patch("locale.getdefaultlocale") as mock_locale:
            mock_locale.return_value = ("fr_FR", "UTF-8")

            with patch.object(config_manager, "get_i18n_config") as mock_i18n:
                mock_i18n.return_value = {
                    "preferred_language": "default",
                    "preferred_locale": "default",
                }

                language = config_manager.get_preferred_language()
                locale_code = config_manager.get_preferred_locale()

                # Language should be extracted from locale
                self.assertEqual(language, "fr")
                self.assertEqual(locale_code, "fr_FR")

    def test_environment_variable_priority(self):
        """Test that environment variables are checked in correct priority order."""
        from src.ragme.utils.config_manager import ConfigManager

        config_manager = ConfigManager()

        # Test with multiple environment variables set
        with patch("locale.getdefaultlocale") as mock_locale:
            mock_locale.side_effect = locale.Error("No locale")

            with patch.dict(
                os.environ,
                {
                    "LANG": "es_ES.UTF-8",
                    "LC_ALL": "fr_FR.UTF-8",
                    "LC_CTYPE": "de_DE.UTF-8",
                },
            ):
                with patch.object(config_manager, "get_i18n_config") as mock_i18n:
                    mock_i18n.return_value = {"preferred_language": "default"}

                    language = config_manager.get_preferred_language()
                    # Should use LANG first (es)
                    self.assertEqual(language, "es")


if __name__ == "__main__":
    unittest.main()
