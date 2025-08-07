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

    def __init__(self, ragme_instance):
        """
        Initialize the QueryAgent with a reference to the main RagMe instance.

        Args:
            ragme_instance: The RagMe instance that provides access to vector database and methods
        """
        self.ragme = ragme_instance

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

        # Get citation configuration
        self.include_citations = config.get(
            "query.include_citations", False
        )  # Default to False - only include citations for detailed queries

        self.llm = OpenAI(model=llm_model, temperature=temperature)

    async def run(self, query: str, is_detailed: bool = None):
        """
        Run a query to answer questions about document content.

        Args:
            query (str): The query to process
            is_detailed (bool, optional): Whether this is a detailed query.
                                        If None, will be determined automatically.

        Returns:
            str: The response with relevant document content
        """
        logger.info(f"QueryAgent received query: '{query}'")

        try:
            logger.info(
                f"QueryAgent searching vector database with query: '{query}' (top_k={self.top_k})"
            )
            # Use vector similarity search to find relevant documents
            documents = self.ragme.vector_db.search(query, limit=self.top_k)
            logger.info(f"QueryAgent found {len(documents)} documents")

            if documents:
                # Get the most relevant documents
                most_relevant = documents[0]
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
                answer = self._answer_query_with_chunks(query, documents)

                # Format URL as a proper markdown link
                url_link = f"[{url}]({url})" if url else "No URL available"

                result = f"**Based on the stored documents, here's what I found:**\n\n**URL:** {url_link}{chunk_info}{score_info}\n\n**Answer:** {answer}"

                # Determine if we should add citations
                # Use the passed is_detailed parameter, or determine automatically if not provided
                if is_detailed is None:
                    is_detailed = self._is_detailed_query(query)

                # Add citations based on configuration and query type
                # If include_citations is True, always include citations
                # If include_citations is False, only include for detailed queries or multiple documents
                should_include_citations = (
                    self.include_citations or is_detailed or len(documents) > 1
                )

                if should_include_citations:
                    citations = self._generate_citations(documents[:3])
                    result += f"\n\n**Citations:**\n{citations}"

                logger.info(f"QueryAgent returning result for query: '{query}'")
                return result
            else:
                logger.info(f"QueryAgent found no documents for query: '{query}'")
                return f"I couldn't find any relevant information about '{query}' in the stored documents."

        except Exception as e:
            logger.error(f"QueryAgent error: {str(e)}")
            return f"Error searching documents: {str(e)}"

    def _answer_query_with_chunks(self, query: str, documents: list[dict]) -> str:
        """
        Use LLM to summarize relevant chunks in the context of the query.

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

Please provide a clear, well-structured answer that directly addresses the user's question. Use information from the documents to support your response. If the documents don't contain enough information to fully answer the question, acknowledge this and provide what information is available.

Answer:"""

            # Use the LLM to generate the summary
            response = self.llm.complete(prompt)
            return response.text.strip()

        except Exception:
            # Fallback to simple text extraction if LLM summarization fails
            most_relevant = documents[0]
            content = most_relevant.get("text", "")

            # Truncate content if too long
            if len(content) > 1500:
                content = content[:1500] + "..."

            return f"Content: {content}"

    def _generate_citations(self, documents: list[dict]) -> str:
        """
        Generate citations for the top documents used in the response.

        Args:
            documents (list): List of documents to cite

        Returns:
            str: Formatted citations
        """
        citations = []
        for i, doc in enumerate(documents, 1):
            url = doc.get("url", "")
            metadata = doc.get("metadata", {})
            filename = metadata.get("filename", "Unknown Document")

            # Format URL as markdown link
            if url:
                url_link = f"[{url}]({url})"
            else:
                url_link = "No URL available"

            # Add similarity score if available
            score_info = ""
            if "score" in doc:
                score_info = f" (Similarity: {doc['score']:.3f})"

            citations.append(f"{i}. **{filename}** - {url_link}{score_info}")

        return "\n".join(citations)

    def _is_detailed_query(self, query: str) -> bool:
        """
        Use LLM to determine if a query is asking for a detailed response or report.

        Args:
            query (str): The user query

        Returns:
            bool: True if the query is asking for a detailed response
        """
        try:
            # Create a prompt for the LLM to determine if this is a detailed query
            prompt = f"""Analyze the following user query and determine if it's asking for detailed information, a comprehensive response, or a report.

User Query: "{query}"

Consider the following:
- Is the user asking for a detailed explanation, analysis, or overview?
- Is the user requesting a comprehensive response or report?
- Is the user asking "what", "how", "why", "when", "where", "who", "which" questions?
- Is the user asking for explanations, descriptions, or detailed information?
- Is this a functional query (like "list", "add", "delete") or an informational query?

Respond with ONLY "YES" if the query is asking for detailed information, or "NO" if it's a simple functional query.

Response:"""

            # Use the LLM to determine if this is a detailed query
            response = self.llm.complete(prompt)
            result = response.text.strip().upper()

            # Return True if LLM says YES, False otherwise
            return result == "YES"

        except Exception as e:
            # Fallback to keyword-based detection if LLM fails
            logger.warning(
                f"LLM-based detailed query detection failed, falling back to keyword detection: {e}"
            )
            return self._fallback_detailed_query_detection(query)

    def _fallback_detailed_query_detection(self, query: str) -> bool:
        """
        Fallback keyword-based detection for detailed queries.

        Args:
            query (str): The user query

        Returns:
            bool: True if the query is asking for a detailed response
        """
        query_lower = query.lower()

        # Keywords that indicate a request for detailed information
        detailed_keywords = [
            "report",
            "detailed",
            "comprehensive",
            "complete",
            "full",
            "thorough",
            "analysis",
            "overview",
            "summary",
            "explain",
            "describe",
            "tell me about",
            "what is",
            "how does",
            "why",
            "when",
            "where",
            "who",
            "which",
            "compare",
            "contrast",
            "evaluate",
            "assess",
            "review",
            "examine",
            "investigate",
            "explore",
            "discuss",
            "elaborate",
            "expand",
            "provide",
            "give me",
            "show me",
            "help me understand",
            "break down",
            "outline",
        ]

        # Check if any detailed keywords are present
        for keyword in detailed_keywords:
            if keyword in query_lower:
                return True

        # Check for question words that typically indicate detailed responses
        question_words = ["what", "how", "why", "when", "where", "who", "which"]
        if any(word in query_lower for word in question_words):
            return True

        return False

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
