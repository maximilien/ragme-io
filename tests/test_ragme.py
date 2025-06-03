import pytest
from unittest.mock import patch, MagicMock
from ragme import RagMe

def test_ragme_init():
    with patch('ragme.weaviate.connect_to_weaviate_cloud') as mock_connect, \
         patch('ragme.weaviate.auth.Auth.api_key') as mock_api_key, \
         patch('ragme.weaviate') as mock_weaviate, \
         patch('ragme.OpenAI') as mock_openai, \
         patch('ragme.QueryAgent') as mock_query_agent, \
         patch('ragme.FunctionAgent') as mock_function_agent:
        # Setup mocks
        mock_client = MagicMock()
        mock_connect.return_value = mock_client
        mock_client.collections.exists.return_value = True
        mock_query_agent.return_value = MagicMock()
        mock_function_agent.return_value = MagicMock()
        mock_openai.return_value = MagicMock()
        mock_api_key.return_value = 'fake-key'

        ragme = RagMe()
        assert ragme.collection_name == "RagMeDocs"
        assert ragme.weeviate_client is not None
        assert ragme.query_agent is not None
        assert ragme.ragme_agent is not None

def test_write_webpages_to_weaviate():
    with patch('ragme.SimpleWebPageReader') as mock_reader, \
         patch('weaviate.connect_to_weaviate_cloud') as mock_connect, \
         patch('weaviate.auth.Auth.api_key') as mock_api_key, \
         patch('ragme.OpenAI') as mock_openai, \
         patch('ragme.QueryAgent') as mock_query_agent, \
         patch('ragme.FunctionAgent') as mock_function_agent:
        # Setup mocks
        mock_client = MagicMock()
        mock_connect.return_value = mock_client
        mock_client.collections.exists.return_value = True
        mock_query_agent.return_value = MagicMock()
        mock_function_agent.return_value = MagicMock()
        mock_openai.return_value = MagicMock()
        mock_api_key.return_value = 'fake-key'

        # Mock the reader
        mock_instance = mock_reader.return_value
        mock_instance.load_data.return_value = [MagicMock(id_='url1', text='text1'), MagicMock(id_='url2', text='text2')]
        
        # Mock collection and batch
        mock_collection = MagicMock()
        mock_client.collections.get.return_value = mock_collection
        mock_batch = MagicMock()
        mock_batch_context = MagicMock()
        mock_batch_context.__enter__.return_value = mock_batch
        mock_collection.batch.dynamic.return_value = mock_batch_context

        ragme = RagMe()
        ragme.write_webpages_to_weaviate(['http://test1', 'http://test2'])
        
        # Verify the calls
        assert mock_batch.add_object.call_count == 2
        mock_batch.add_object.assert_any_call(properties={"url": "url1", "text": "text1"})
        mock_batch.add_object.assert_any_call(properties={"url": "url2", "text": "text2"}) 