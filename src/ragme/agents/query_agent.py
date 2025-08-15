# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import logging
import warnings

from llama_index.llms.openai import OpenAI

from src.ragme.utils.config_manager import config

# Set up logging
logger = logging.getLogger(__name__)

# Suppress Pydantic deprecation warnings from dependencies
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*class-based `config`.*"
)
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*PydanticDeprecatedSince20.*"
)
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message=".*Support for class-based `config`.*",
)


class QueryAgent:
    """A query agent that answers questions about document content using vector search and LLM summarization."""

    def __init__(self, vector_db):
        """
        Initialize the QueryAgent with a reference to a vector database.

        Args:
            vector_db: The vector database instance that provides search capabilities
        """
        self.vector_db = vector_db

        # Get agent configuration
        agent_config = config.get_agent_config("query-agent")
        llm_model = (
            agent_config.get("llm_model", "gpt-4o-mini")
            if agent_config
            else "gpt-4o-mini"
        )

        # Get LLM configuration
        llm_config = config.get_llm_config()
        temperature = llm_config.get("temperature", 0.7)

        # Get query configuration
        self.top_k = config.get(
            "query.top_k", 5
        )  # Default to 5 most relevant documents

        self.llm = OpenAI(model=llm_model, temperature=temperature)

    async def run(self, query: str):
        """
        Run a query to answer questions about document content.

        Args:
            query (str): The query to process

        Returns:
            str: The response with relevant document content
        """
        logger.info(f"QueryAgent received query: '{query}'")

        try:
            logger.info(
                f"QueryAgent searching vector database with query: '{query}' (top_k={self.top_k})"
            )

            # Check what collections are available
            has_text = self.vector_db.has_text_collection()
            has_image = self.vector_db.has_image_collection()

            if not has_text and not has_image:
                return "No collections are configured for this vector database."

            # Search collections based on availability
            text_results = []
            image_results = []

            if has_text:
                text_results = self.vector_db.search_text_collection(
                    query, limit=self.top_k
                )
                logger.info(f"QueryAgent found {len(text_results)} text documents")

            if has_image:
                image_results = self.vector_db.search_image_collection(
                    query, limit=self.top_k
                )
                logger.info(f"QueryAgent found {len(image_results)} image documents")

            # Combine and sort results
            all_results = text_results + image_results
            all_results.sort(key=lambda x: x.get("score", 0), reverse=True)

            if all_results:
                # Get the most relevant result
                most_relevant = all_results[0]
                url = most_relevant.get("url", "")
                metadata = most_relevant.get("metadata", {})

                # For chunked documents, provide more context
                if metadata.get("is_chunked") or metadata.get("is_chunk"):
                    chunk_info = f" (Chunked document with {metadata.get('total_chunks', 'unknown')} chunks)"
                else:
                    chunk_info = ""

                # Include similarity score if available
                score_info = ""
                if "score" in most_relevant:
                    score_info = f" (Similarity: {most_relevant['score']:.3f})"

                logger.info(
                    f"QueryAgent generating answer with LLM for query: '{query}'"
                )

                # Use LLM to answer the query with the relevant content
                answer = self._answer_query_with_results(
                    query, text_results, image_results
                )

                # Build result message
                result_parts = [
                    "**Based on the stored documents, here's what I found:**\n"
                ]

                if text_results:
                    result_parts.append(
                        f"**Text Documents:** Found {len(text_results)} relevant text documents"
                    )

                if image_results:
                    result_parts.append(
                        f"**Images:** Found {len(image_results)} relevant images"
                    )

                result_parts.append(
                    f"\n**Most Relevant:** [{url}]({url}){chunk_info}{score_info}"
                )
                result_parts.append(f"\n**Answer:** {answer}")

                result = "\n".join(result_parts)

                logger.info(f"QueryAgent returning result for query: '{query}'")
                return result
            else:
                logger.info(f"QueryAgent found no documents for query: '{query}'")
                return f"I couldn't find any relevant information about '{query}' in the stored documents."

        except Exception as e:
            logger.error(f"QueryAgent error: {str(e)}")
            return f"Error searching documents: {str(e)}"

    def _answer_query_with_results(
        self, query: str, text_results: list[dict], image_results: list[dict]
    ) -> str:
        """
        Use LLM to summarize relevant results from both text and image collections.

        Args:
            query (str): The user's query
            text_results (list): List of relevant text documents
            image_results (list): List of relevant image documents

        Returns:
            str: LLM-generated summary
        """
        try:
            # Prepare context from the most relevant documents
            context_parts = []

            # Add text documents context
            if text_results:
                context_parts.append("**Text Documents:**")
                for i, doc in enumerate(text_results[:3]):  # Use top 3 text documents
                    content = doc.get("text", "")
                    metadata = doc.get("metadata", {})
                    filename = metadata.get("filename", "Unknown")

                    # Truncate content if too long (keep more for summarization)
                    if len(content) > 2000:
                        content = content[:2000] + "..."

                    context_parts.append(f"Document {i + 1} ({filename}):\n{content}\n")

            # Add image documents context
            if image_results:
                context_parts.append("**Image Documents:**")
                for i, img in enumerate(image_results[:3]):  # Use top 3 image documents
                    metadata = img.get("metadata", {})
                    filename = metadata.get("filename", "Unknown")
                    description = metadata.get(
                        "description", "No description available"
                    )

                    context_parts.append(
                        f"Image {i + 1} ({filename}):\nDescription: {description}\n"
                    )

            context = "\n".join(context_parts)

            # Create prompt for LLM summarization
            prompt = f"""Based on the following documents and images, please provide a comprehensive answer to the user's question.

User Question: {query}

Relevant Content:
{context}

Please provide a clear, accurate answer based on the information above. If the content includes both text documents and images, mention both types of sources in your response."""

            # Generate response using LLM
            response = self.llm.complete(prompt)
            return response.text

        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}")
            return f"Error generating response: {str(e)}"

    def _answer_query_with_chunks(self, query: str, documents: list[dict]) -> str:
        """
        Use LLM to summarize relevant chunks in the context of the query.
        (Legacy method for backward compatibility)

        Args:
            query (str): The user's query
            documents (list): List of relevant documents

        Returns:
            str: LLM-generated summary
        """
        try:
            # Prepare context from the most relevant documents
            context_parts = []
            for i, doc in enumerate(documents[:3]):  # Use top 3 documents
                content = doc.get("text", "")
                metadata = doc.get("metadata", {})
                filename = metadata.get("filename", "Unknown")

                # Truncate content if too long (keep more for summarization)
                if len(content) > 2000:
                    content = content[:2000] + "..."

                context_parts.append(f"Document {i + 1} ({filename}):\n{content}\n")

            context = "\n".join(context_parts)

            # Create prompt for LLM summarization
            prompt = f"""Based on the following documents, please provide a comprehensive answer to the user's question.

User Question: {query}

Relevant Documents:
{context}

Please provide a clear, accurate answer based on the information above."""

            # Generate response using LLM
            response = self.llm.complete(prompt)
            return response.text

        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}")
            return f"Error generating response: {str(e)}"

    def is_query_question(self, query: str) -> bool:
        """
        Determine if a query is a question about document content.

        Args:
            query (str): The user query

        Returns:
            bool: True if the query is a question, False otherwise
        """
        question_keywords = [
            "what",
            "who",
            "when",
            "where",
            "why",
            "how",
            "which",
            "whose",
            "tell me",
            "explain",
            "describe",
            "summarize",
            "find",
            "search",
            "information about",
            "details about",
            "content of",
        ]

        query_lower = query.lower()
        is_question = any(keyword in query_lower for keyword in question_keywords)
        logger.info(f"QueryAgent.is_query_question('{query}') = {is_question}")
        return is_question
