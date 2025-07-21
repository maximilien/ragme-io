# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import warnings

# Suppress Pydantic deprecation warnings from dependencies
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*class-based `config`.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*PydanticDeprecatedSince20.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*Support for class-based `config`.*")

# Suppress Milvus connection warnings during tests
warnings.filterwarnings("ignore", category=UserWarning, message=".*Failed to connect to Milvus.*")
warnings.filterwarnings("ignore", category=UserWarning, message=".*Milvus client is not available.*")

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock

from src.ragme.ragme import RagMe

def test_ragme_init():
    with patch('src.ragme.ragme.create_vector_database') as mock_create_db, \
         patch('llama_index.llms.openai.OpenAI') as mock_openai, \
         patch('weaviate.agents.query.QueryAgent') as mock_query_agent, \
         patch('llama_index.core.agent.workflow.FunctionAgent') as mock_function_agent, \
         patch.dict('os.environ', {'VECTOR_DB_TYPE': 'weaviate'}):
        # Setup mocks
        mock_db_instance = MagicMock()
        mock_create_db.return_value = mock_db_instance
        mock_query_agent.return_value = MagicMock()
        mock_function_agent.return_value = MagicMock()
        mock_openai.return_value = MagicMock()

        # Mock the vector database methods
        mock_db_instance.setup = MagicMock()
        mock_db_instance.create_query_agent = MagicMock(return_value=MagicMock())

        ragme = RagMe()
        assert ragme.collection_name == "RagMeDocs"
        assert ragme.vector_db is not None
        assert ragme.query_agent is not None
        assert ragme.ragme_agent is not None

def test_write_webpages_to_weaviate():
    with patch('src.ragme.ragme.SimpleWebPageReader') as mock_reader, \
         patch('src.ragme.ragme.create_vector_database') as mock_create_db, \
         patch('llama_index.llms.openai.OpenAI') as mock_openai, \
         patch('weaviate.agents.query.QueryAgent') as mock_query_agent, \
         patch('llama_index.core.agent.workflow.FunctionAgent') as mock_function_agent, \
         patch.dict('os.environ', {'VECTOR_DB_TYPE': 'weaviate'}):
        # Setup mocks
        mock_db_instance = MagicMock()
        mock_create_db.return_value = mock_db_instance
        mock_query_agent.return_value = MagicMock()
        mock_function_agent.return_value = MagicMock()
        mock_openai.return_value = MagicMock()

        # Mock the vector database methods
        mock_db_instance.setup = MagicMock()
        mock_db_instance.create_query_agent = MagicMock(return_value=MagicMock())

        # Mock the reader
        mock_instance = mock_reader.return_value
        mock_instance.load_data.return_value = [MagicMock(id_='url1', text='text1'), MagicMock(id_='url2', text='text2')]

        ragme = RagMe()
        ragme.write_webpages_to_weaviate(['http://test1', 'http://test2'])
        
        # Verify the calls
        assert mock_db_instance.write_documents.call_count == 1
        # Check that write_documents was called with the expected documents
        call_args = mock_db_instance.write_documents.call_args[0][0]
        assert len(call_args) == 2
        assert call_args[0]["url"] == "url1"
        assert call_args[0]["text"] == "text1"
        assert call_args[1]["url"] == "url2"
        assert call_args[1]["text"] == "text2" 