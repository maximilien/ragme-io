# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import locale
import os
import unittest
from unittest.mock import Mock, patch

import pytest

from src.ragme.utils.config_manager import ConfigManager


class TestI18nConfiguration(unittest.TestCase):
    """Test internationalization configuration functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.config_manager = ConfigManager()

    def test_get_i18n_config_default(self):
        """Test that i18n configuration returns default values when not configured."""
        with patch.object(self.config_manager, "get") as mock_get:
            mock_get.return_value = {}

            i18n_config = self.config_manager.get_i18n_config()
            self.assertEqual(i18n_config, {})

    def test_get_i18n_config_with_values(self):
        """Test that i18n configuration returns configured values."""
        test_config = {"preferred_language": "fr", "preferred_locale": "fr_FR"}

        with patch.object(self.config_manager, "get") as mock_get:
            mock_get.return_value = test_config

            i18n_config = self.config_manager.get_i18n_config()
            self.assertEqual(i18n_config, test_config)

    def test_get_preferred_language_default(self):
        """Test that preferred language returns default when set to 'default'."""
        with patch.object(self.config_manager, "get_i18n_config") as mock_i18n:
            mock_i18n.return_value = {"preferred_language": "default"}

            with patch.object(
                self.config_manager, "_detect_system_language"
            ) as mock_detect:
                mock_detect.return_value = "en"

                language = self.config_manager.get_preferred_language()
                self.assertEqual(language, "en")
                mock_detect.assert_called_once()

    def test_get_preferred_language_configured(self):
        """Test that preferred language returns configured value."""
        with patch.object(self.config_manager, "get_i18n_config") as mock_i18n:
            mock_i18n.return_value = {"preferred_language": "fr"}

            language = self.config_manager.get_preferred_language()
            self.assertEqual(language, "fr")

    def test_get_preferred_language_fallback(self):
        """Test that preferred language falls back to 'en' when not configured."""
        with patch.object(self.config_manager, "get_i18n_config") as mock_i18n:
            mock_i18n.return_value = {}

            with patch.object(
                self.config_manager, "_detect_system_language"
            ) as mock_detect:
                mock_detect.return_value = "en"

                language = self.config_manager.get_preferred_language()
                self.assertEqual(language, "en")

    def test_get_preferred_locale_default(self):
        """Test that preferred locale returns default when set to 'default'."""
        with patch.object(self.config_manager, "get_i18n_config") as mock_i18n:
            mock_i18n.return_value = {"preferred_locale": "default"}

            with patch.object(
                self.config_manager, "_detect_system_locale"
            ) as mock_detect:
                mock_detect.return_value = "en_US"

                locale_code = self.config_manager.get_preferred_locale()
                self.assertEqual(locale_code, "en_US")
                mock_detect.assert_called_once()

    def test_get_preferred_locale_configured(self):
        """Test that preferred locale returns configured value."""
        with patch.object(self.config_manager, "get_i18n_config") as mock_i18n:
            mock_i18n.return_value = {"preferred_locale": "fr_FR"}

            locale_code = self.config_manager.get_preferred_locale()
            self.assertEqual(locale_code, "fr_FR")

    def test_get_preferred_locale_fallback(self):
        """Test that preferred locale falls back to 'en_US' when not configured."""
        with patch.object(self.config_manager, "get_i18n_config") as mock_i18n:
            mock_i18n.return_value = {}

            with patch.object(
                self.config_manager, "_detect_system_locale"
            ) as mock_detect:
                mock_detect.return_value = "en_US"

                locale_code = self.config_manager.get_preferred_locale()
                self.assertEqual(locale_code, "en_US")

    def test_get_language_name_common_languages(self):
        """Test that language names are returned correctly for common languages."""
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
                name = self.config_manager.get_language_name(language_code)
                self.assertEqual(name, expected_name)

    def test_get_language_name_unknown_language(self):
        """Test that unknown language codes return 'English' as fallback."""
        name = self.config_manager.get_language_name("unknown")
        self.assertEqual(name, "English")

    def test_get_language_name_none_uses_preferred(self):
        """Test that passing None uses the preferred language from config."""
        with patch.object(
            self.config_manager, "get_preferred_language"
        ) as mock_preferred:
            mock_preferred.return_value = "fr"

            name = self.config_manager.get_language_name(None)
            self.assertEqual(name, "French")
            mock_preferred.assert_called_once()

    def test_detect_system_language_from_locale(self):
        """Test system language detection from locale."""
        with patch("locale.getdefaultlocale") as mock_locale:
            mock_locale.return_value = ("fr_FR", "UTF-8")

            language = self.config_manager._detect_system_language()
            self.assertEqual(language, "fr")

    def test_detect_system_language_from_env_vars(self):
        """Test system language detection from environment variables."""
        with patch("locale.getdefaultlocale") as mock_locale:
            mock_locale.side_effect = locale.Error("No locale")

            with patch.dict(os.environ, {"LANG": "es_ES.UTF-8"}):
                language = self.config_manager._detect_system_language()
                self.assertEqual(language, "es")

    def test_detect_system_language_fallback(self):
        """Test system language detection fallback to English."""
        with patch("locale.getdefaultlocale") as mock_locale:
            mock_locale.side_effect = locale.Error("No locale")

            with patch.dict(os.environ, {}, clear=True):
                language = self.config_manager._detect_system_language()
                self.assertEqual(language, "en")

    def test_detect_system_locale_from_locale(self):
        """Test system locale detection from locale."""
        with patch("locale.getdefaultlocale") as mock_locale:
            mock_locale.return_value = ("fr_FR", "UTF-8")

            locale_code = self.config_manager._detect_system_locale()
            self.assertEqual(locale_code, "fr_FR")

    def test_detect_system_locale_from_env_vars(self):
        """Test system locale detection from environment variables."""
        with patch("locale.getdefaultlocale") as mock_locale:
            mock_locale.side_effect = locale.Error("No locale")

            with patch.dict(os.environ, {"LANG": "es_ES.UTF-8"}):
                locale_code = self.config_manager._detect_system_locale()
                self.assertEqual(locale_code, "es_ES")

    def test_detect_system_locale_fallback(self):
        """Test system locale detection fallback to en_US."""
        with patch("locale.getdefaultlocale") as mock_locale:
            mock_locale.side_effect = locale.Error("No locale")

            with patch.dict(os.environ, {}, clear=True):
                locale_code = self.config_manager._detect_system_locale()
                self.assertEqual(locale_code, "en_US")

    def test_language_detection_edge_cases(self):
        """Test language detection with edge cases."""
        test_cases = [
            ("en_US.UTF-8", "en"),
            ("fr_FR", "fr"),
            ("zh_CN.UTF-8", "zh"),
            ("invalid_format", "en"),  # Should fallback
        ]

        for env_value, expected_language in test_cases:
            with self.subTest(env_value=env_value):
                with patch("locale.getdefaultlocale") as mock_locale:
                    mock_locale.side_effect = locale.Error("No locale")

                    with patch.dict(os.environ, {"LANG": env_value}):
                        language = self.config_manager._detect_system_language()
                        self.assertEqual(language, expected_language)

    def test_locale_detection_edge_cases(self):
        """Test locale detection with edge cases."""
        test_cases = [
            ("en_US.UTF-8", "en_US"),
            ("fr_FR", "fr_FR"),
            ("zh_CN.UTF-8", "zh_CN"),
            ("invalid_format", "en_US"),  # Should fallback
        ]

        for env_value, expected_locale in test_cases:
            with self.subTest(env_value=env_value):
                with patch("locale.getdefaultlocale") as mock_locale:
                    mock_locale.side_effect = locale.Error("No locale")

                    with patch.dict(os.environ, {"LANG": env_value}):
                        locale_code = self.config_manager._detect_system_locale()
                        self.assertEqual(locale_code, expected_locale)


class TestI18nAgentIntegration(unittest.TestCase):
    """Test i18n integration with agents."""

    def test_ragme_agent_language_configuration(self):
        """Test that RagMeAgent uses i18n configuration correctly."""
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

            self.assertEqual(agent.preferred_language, "fr")
            self.assertEqual(agent.language_name, "French")

            # Verify that the language instruction is included in the system prompt
            system_prompt = agent.agent.system_prompt
            self.assertIn("French", system_prompt)
            self.assertIn("only responds in French", system_prompt)

    def test_functional_agent_language_configuration(self):
        """Test that FunctionalAgent uses i18n configuration correctly."""
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

            self.assertEqual(agent.preferred_language, "es")
            self.assertEqual(agent.language_name, "Spanish")

            # Verify that the language instruction is included in the system prompt
            system_prompt = agent.agent.system_prompt
            self.assertIn("Spanish", system_prompt)
            self.assertIn("only responds in Spanish", system_prompt)

    def test_query_agent_language_configuration(self):
        """Test that QueryAgent uses i18n configuration correctly."""
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

            self.assertEqual(agent.preferred_language, "de")
            self.assertEqual(agent.language_name, "German")


if __name__ == "__main__":
    unittest.main()
