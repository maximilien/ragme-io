# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import warnings
# Suppress Pydantic deprecation warnings from dependencies
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*PydanticDeprecatedSince20.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*class-based `config` is deprecated.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic._internal._config")

import base64
import json
import logging
import os
import requests
import tempfile

from typing import List, Dict, Any
from urllib.parse import urljoin, urlparse

from PIL import Image, ExifTags
from exif import Image as ExifImage
from bs4 import BeautifulSoup

from llama_index.core.llms import ChatMessage
from llama_index.core.tools import FunctionTool
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openai import OpenAI
from llama_index.readers.web import SimpleWebPageReader
from pydantic import BaseModel, Field
import weaviate
from weaviate.auth import Auth
from weaviate.agents.query import QueryAgent
from weaviate.classes.config import Configure, Property, DataType

from src.ragme.common import crawl_webpage

import dotenv

dotenv.load_dotenv()

# Get environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
WEAVIATE_URL = os.getenv("WEAVIATE_URL")

# Check if environment variables are set
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set")
if not WEAVIATE_API_KEY:
    raise ValueError("WEAVIATE_API_KEY is not set")
if not WEAVIATE_URL:
    raise ValueError("WEAVIATE_URL is not set")

# Filter warnings
warnings.filterwarnings("ignore")
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", category=UserWarning, module="bs4")
logging.getLogger("httpx").setLevel(logging.WARNING)

class RagMe:
    """A class for managing RAG (Retrieval-Augmented Generation) operations with web content using a Vector Database."""
    
    def __init__(self):
        self.docs_collection_name = "RagMeDocs"
        self.images_collection_name = "RagMeImages"
        self.weeviate_client, self.query_agent, self.ragme_agent = None, None, None

        self._create_weaviate_client()
        self._setup_weaviate()
        
        self.ragme_agent = self._create_ragme_agent()
    
    # private methods

    def _create_weaviate_client(self):
        if not self.weeviate_client:
            self.weeviate_client = weaviate.connect_to_weaviate_cloud(
                cluster_url=WEAVIATE_URL,
                auth_credentials=Auth.api_key(WEAVIATE_API_KEY),
            )
        return self.weeviate_client
    
    def _setup_weaviate(self):
        # Create the RagMeDocs collection
        if not self.weeviate_client.collections.exists(self.docs_collection_name):
            self.weeviate_client.collections.create(
                self.docs_collection_name,
                description="A dataset with the contents of RagMe docs and website",
                vectorizer_config=Configure.Vectorizer.text2vec_weaviate(),
                properties=[
                    Property(name="url", data_type=DataType.TEXT, description="the source URL of the webpage"),
                    Property(name="text", data_type=DataType.TEXT, description="the content of the webpage"),
                    Property(name="metadata", data_type=DataType.TEXT, description="additional metadata in JSON format"),
            ])
        # Create the RagMeImages collection
        if not self.weeviate_client.collections.exists(self.images_collection_name):
            try:
                self.weeviate_client.collections.create(
                    self.images_collection_name,
                    description="A dataset with the contents of RagMe images",
                    vectorizer_config=Configure.Vectorizer.multi2vec_google(image_fields=["image"]),
                    properties=[
                        Property(name="image", data_type=DataType.BLOB, description="the base64 encoded image"),
                        Property(name="metadata", data_type=DataType.TEXT, description="additional metadata in JSON format"),
                    ]
                )
            except Exception as e:
                print("multi2vec-google not available or not supporting images, falling back to text2vec-weaviate.")
                self.weeviate_client.collections.create(
                    self.images_collection_name,
                    description="A dataset with the contents of RagMe images",
                    vectorizer_config=Configure.Vectorizer.text2vec_weaviate(),
                    properties=[
                        Property(name="image", data_type=DataType.BLOB, description="the base64 encoded image"),
                        Property(name="metadata", data_type=DataType.TEXT, description="additional metadata in JSON format"),
                    ]
                )

    def _list_documents(self, collection_name: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List documents in the Weaviate collection.
        
        Args:
            limit (int): Maximum number of documents to return
            offset (int): Number of documents to skip
            
        Returns:
            List[Dict[str, Any]]: List of documents with their properties
        """
        collection = self.weeviate_client.collections.get(collection_name)
        
        # Query the collection
        result = collection.query.fetch_objects(
            limit=limit,
            offset=offset,
            include_vector=False  # Don't include vector data in response
        )
        
        # Process the results
        documents = []
        for obj in result.objects:
            doc = {
                "id": obj.uuid,
                "url": obj.properties.get("url", ""),
                "text": obj.properties.get("text", ""),
                "metadata": obj.properties.get("metadata", "{}")
            }
            
            # Try to parse metadata if it's a JSON string
            try:
                doc["metadata"] = json.loads(doc["metadata"])
            except json.JSONDecodeError:
                pass

            documents.append(doc)            
        return documents

    def _get_image_metadata(self, image_url: str) -> Dict[str, Any]:
        """
        Get the metadata of an image
        """
        try:
            response = requests.get(image_url)
            image = ExifImage(response.content)
            metadata = {
                "type": "image",
                "url": image_url,
                "exif": {}
            }
            for tag in image.list_all():
                try:
                    metadata["exif"][tag] = str(image.get(tag))
                except:
                    continue
            return metadata
        except Exception as e:
            print(f"Error getting image metadata: {e}")
            return {"type": "image", "url": image_url}

    def _create_query_agent(self):
        return QueryAgent(client=self.weeviate_client, collections=[self.docs_collection_name, self.images_collection_name])

    def _create_ragme_agent(self):
        llm = OpenAI(model="gpt-4o-mini")

        def find_urls_crawling_webpage(start_url: str, max_pages: int = 10) -> list[str]:
            """
            Crawl a webpage and find all web pages under it.
            Args:
                start_url (str): The URL to start crawling from
                max_pages (int): The maximum number of pages to crawl
            Returns:
                list[str]: A list of URLs found
            """
            return crawl_webpage(start_url, max_pages)
                
        def delete_ragme_collections():
            """
            Reset and delete the RagMeDocs and RagMeImages collections
            """
            self.weeviate_client.collections.delete(self.docs_collection_name)
            self.weeviate_client.collections.delete(self.images_collection_name)

        def list_ragme_collection(limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
            """
            List the contents of the RagMeDocs and RagMeImages collections
            """
            return self._list_documents(self.docs_collection_name) + self._list_documents(self.images_collection_name)

        def list_ragme_docs_collection(limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
            """
            List the contents of the RagMeDocs collection
            """
            return self._list_documents(self.docs_collection_name)

        def list_ragme_images_collection(limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
            """
            List the contents of the RagMeImages collection
            """
            return self._list_documents(self.images_collection_name)

        def write_image_to_ragme_collection(image_url=str):
            """
            Useful for writing new image URLs to the RagMeImages collection
            Args:
                image_url (str): The URL of the image to write to the RagMeImages collection
            """
            print(f"Writing image {image_url} to the RagMeImages collection")
            self.write_image_to_weaviate(image_url)

        def write_to_ragme_collection(urls=list[str]):
            """
            Useful for writing new content to the RagMeDocs collection
            Args:
                urls (list[str]): A list of URLs to write to the RagMeDocs collection
            """
            self.write_webpages_to_weaviate(urls)

        def query_agent(query: str) -> str:
            """
            Useful for asking questions about RagMe docs and website
            Args:
                query (str): The query to ask the QueryAgent
            Returns:
                str: The response from the QueryAgent
            """
            response = self.query_agent.run(query)
            return response.final_answer

        return FunctionAgent(
            tools=[write_to_ragme_collection, write_image_to_ragme_collection, delete_ragme_collections, list_ragme_collection, list_ragme_docs_collection, list_ragme_images_collection, find_urls_crawling_webpage, query_agent],
            llm=llm,
            # system_prompt="""You are a helpful assistant that can answer questions about 
            # content from the RagMeDocs collection and show images from the RagMeImages collection.
            # Forward questions to the QueryAgent if you don't have the answer.
            # QueryAgent should show images from the RagMeImages collection if the question is about images.
            # QueryAgent should provide the answer to the question using content retrieved from the RagMeDocs collection.
            # """,
            system_prompt="""You are a helpful assistant that can answer questions about 
            content from the RagMeDocs collection and show images from the RagMeImages collection.
            Forward questions to the QueryAgent if you don't have the answer.
            QueryAgent should show images from the RagMeImages collection if the question is about images.
            QueryAgent should provide the answer to the question using content retrieved from the RagMeDocs collection.
            """,
            verbose=True
        )
        
    # public methods

    def cleanup(self):
        if self.weeviate_client:
            self.weeviate_client.close()

    def write_image_to_weaviate(self, image_url: str):
        """
        Write an image (from a URL) to the RagMeImages collection in Weaviate.
        Args:
            image_url (str): The URL of the image to write to the RagMeImages collection
        """
        print(f"Writing image {image_url} to the RagMeImages collection") #DEBUG
        metadata = self._get_image_metadata(image_url)
        image_recognition = self._extract_image_recognition_info(image_url)
        image_classification = self.classify_image_with_tensorflow(image_url)
        print(f"Metadata: {metadata}") #DEBUG
        print(f"Image recognition: {image_recognition}") #DEBUG
        print(f"Image classification: {image_classification}") #DEBUG
        metadata.update(image_recognition)
        metadata.update(image_classification)
        collection = self.weeviate_client.collections.get(self.images_collection_name)
        with collection.batch.dynamic() as batch:
            response = requests.get(image_url)
            response.raise_for_status()
            image_data = response.content            
            base64_encoding = base64.b64encode(image_data).decode("utf-8")            
            data_properties = {
                "image": base64_encoding,
                "metadata": json.dumps(metadata)
            }
            try:
                batch.add_object(properties=data_properties)
            except Exception as e:
                print(f"Error writing image to Weaviate: {e}")

    def write_webpages_to_weaviate(self, urls: list[str]):
        """
        Write the contents of a list of URLs to the RagMeDocs collection in Weaviate.
        Args:
            urls (list[str]): A list of URLs to write to the RagMeDocs collection
        """
        documents = SimpleWebPageReader(html_to_text=True).load_data(urls)
        collection = self.weeviate_client.collections.get(self.docs_collection_name)
        with collection.batch.dynamic() as batch:
            for doc in documents:
                metadata_text = json.dumps({"type": "webpage", "url": doc.id_}, ensure_ascii=False)
                batch.add_object(properties={"url": doc.id_,
                                             "metadata": metadata_text,
                                             "text": doc.text})
    
    def write_json_to_weaviate(self, json_data: Dict[str, Any], metadata: Dict[str, Any] = None):
        """
        Write JSON content to the RagMeDocs collection in Weaviate.
        Args:
            json_data (Dict[str, Any]): The JSON data to write
            metadata (Dict[str, Any], optional): Additional metadata to store with the content
        """
        # Convert JSON data to string for storage
        json_text = json.dumps(json_data, ensure_ascii=False)
        
        # Convert metadata to string if provided
        metadata_text = json.dumps(metadata, ensure_ascii=False) if metadata else "{}"
        
        collection = self.weeviate_client.collections.get(self.docs_collection_name)
        with collection.batch.dynamic() as batch:
            batch.add_object(properties={
                "url": json_data.get("filename", "filename not found"),
                "text": json_text,
                "metadata": metadata_text
            })

    async def run(self, query: str):
        response = await self.ragme_agent.run(
            user_msg=query
        )
        return str(response)

    def _extract_image_recognition_info(self, image_url: str) -> Dict[str, Any]:
        """
        Extract image recognition information using Daft for multimodal data processing.
        Args:
            image_url (str): The URL of the image to analyze
        Returns:
            Dict[str, Any]: JSON containing image recognition information
        """
        try:
            import daft
            from daft import from_pydict
            
            # Download image from URL
            response = requests.get(image_url)
            response.raise_for_status()
            image_data = response.content
            
            # Create a temporary file to store the image
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                temp_file.write(image_data)
                temp_file_path = temp_file.name
            
            try:
                # Create a DataFrame with image information using from_pydict
                df = from_pydict({
                    "image_url": [image_url],
                    "image_path": [temp_file_path],
                    "image_size": [len(image_data)]
                })
                
                # Extract basic image information
                image_info = {
                    "url": image_url,
                    "type": "image",
                    "recognition_data": {
                        "format": "image",
                        "size_bytes": len(image_data),
                        "daft_processing": True,
                        "daft_dataframe_shape": df.shape if hasattr(df, 'shape') else None
                    },
                    "metadata": self.classify_image_with_tensorflow(image_url)
                }
                
                # Add Daft-specific information if available
                if hasattr(df, 'schema'):
                    image_info["recognition_data"]["schema"] = str(df.schema)
                
                # Process image with Daft's multimodal capabilities
                # Note: This is a basic implementation - Daft can do much more
                # with its unified multimodal data processing capabilities
                
                return image_info
                
            finally:
                # Clean up temporary file
                os.unlink(temp_file_path)
                
        except ImportError:
            print("Daft not installed. Install with: pip install daft")
            return {
                "url": image_url,
                "type": "image",
                "recognition_data": {
                    "error": "Daft not available",
                    "daft_processing": False
                },
                "metadata": self.classify_image_with_tensorflow(image_url)
            }
        except Exception as e:
            print(f"Error extracting image recognition info with Daft: {e}")
            return {
                "url": image_url,
                "type": "image",
                "recognition_data": {
                    "error": str(e),
                    "daft_processing": False
                },
                "metadata": self.classify_image_with_tensorflow(image_url)
            }

    def classify_image_with_tensorflow(self, image_url: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Classify an image using TensorFlow with a pre-trained model.
        Args:
            image_url (str): The URL of the image to classify
            top_k (int): Number of top predictions to return
        Returns:
            Dict[str, Any]: JSON containing image classification results
        """
        try:
            import tensorflow as tf
            from tensorflow.keras.applications import ResNet50
            from tensorflow.keras.applications.resnet50 import preprocess_input, decode_predictions
            from tensorflow.keras.preprocessing import image
            import numpy as np
            from PIL import Image
            import io
            
            # Download image from URL
            response = requests.get(image_url)
            response.raise_for_status()
            image_data = response.content
            
            # Load and preprocess the image
            img = Image.open(io.BytesIO(image_data))
            img = img.convert('RGB')  # Ensure RGB format
            img = img.resize((224, 224))  # ResNet50 expects 224x224
            
            # Convert to numpy array and preprocess
            x = image.img_to_array(img)
            x = np.expand_dims(x, axis=0)
            x = preprocess_input(x)
            
            # Load pre-trained ResNet50 model
            model = ResNet50(weights='imagenet')
            
            # Make prediction
            preds = model.predict(x)
            
            # Decode predictions
            results = decode_predictions(preds, top=top_k)[0]
            
            # Format results
            classifications = []
            for i, (imagenet_id, label, score) in enumerate(results):
                classifications.append({
                    "rank": i + 1,
                    "label": label,
                    "confidence": float(score),
                    "imagenet_id": imagenet_id
                })
            
            # Create classification info
            classification_info = {
                "url": image_url,
                "type": "image_classification",
                "model": "ResNet50",
                "dataset": "ImageNet",
                "top_k": top_k,
                "classifications": classifications,
                "top_prediction": classifications[0] if classifications else None,
                "tensorflow_processing": True
            }
            
            return classification_info
            
        except ImportError:
            print("TensorFlow not installed. Install with: pip install tensorflow")
            return {
                "url": image_url,
                "type": "image_classification",
                "error": "TensorFlow not available",
                "tensorflow_processing": False
            }
        except Exception as e:
            print(f"Error classifying image with TensorFlow: {e}")
            return {
                "url": image_url,
                "type": "image_classification",
                "error": str(e),
                "tensorflow_processing": False
            }

if __name__ == "__main__":
    ragme = RagMe()
    try:
        print("Give me a one URL or a list of URLs to save (separated by commas):")
        urls = input()
        if ',' in urls:
            urls = urls.split(',')
        else:
            url = urls
            search_term = input("Give me a search term to find all post URLs: ")
            prefix = '/'.join(url.split('/')[:-1])
            urls = ragme.find_all_post_urls(url, search_term)
            urls = [prefix + '/' + url for url in urls]
            urls = list(set(urls))
            print(f"Found the following post URLs: {urls}")
            if input(f"Do you want to proceed and process these {len(urls)} URLs? (y/n)") == 'n':
                print("Quitting...")
                exit()
        print(f"Processing {len(urls)} URLs")
        urls = [url.strip() for url in urls]
        ragme.write_webpages_to_weaviate(urls)
        print("Done writing to Weaviate")
        
        while True:
            print("What questions do you have about the URLs just saved?")
            query = input()
            if query.lower() == 'q' or query.lower() == 'quit':
                print("Quitting...")
                break
            else:
                answer = asyncio.run(ragme.run(query))
                print("Answer:")
                print(answer + "\n")
    except KeyboardInterrupt:
        print("\nInterrupted by user. Cleaning up...")
    finally:
        ragme.cleanup()
