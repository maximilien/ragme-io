# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import logging
import warnings

from llama_index.llms.openai import OpenAI

from src.ragme.utils.common import filter_items_by_date_range, parse_date_query
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
        query_config = config.get("query", {})
        self.top_k = query_config.get(
            "top_k", 5
        )  # Default to 5 most relevant documents

        # Get relevance thresholds
        self.text_relevance_threshold = query_config.get(
            "text_relevance_threshold", 0.8
        )
        self.image_relevance_threshold = query_config.get(
            "image_relevance_threshold", 0.8
        )
        self.text_rerank_top_k = query_config.get("text_rerank_top_k", 3)

        # Legacy support for old configuration structure
        if "relevance_thresholds" in query_config:
            relevance_thresholds = query_config.get("relevance_thresholds", {})
            self.text_relevance_threshold = relevance_thresholds.get(
                "text", self.text_relevance_threshold
            )
            self.image_relevance_threshold = relevance_thresholds.get(
                "image", self.image_relevance_threshold
            )

        # Get rerank settings (legacy support)
        self.image_rerank_with_llm: bool = query_config.get(
            "image_rerank_with_llm", False
        )
        self.image_rerank_top_k: int = query_config.get("image_rerank_top_k", 10)
        self.text_rerank_with_llm: bool = query_config.get(
            "text_rerank_with_llm", False
        )

        # Get language settings
        llm_config = config.get_llm_config()
        self.force_english = llm_config.get("force_english", True)
        self.default_language = llm_config.get("language", "en")

        self.llm = OpenAI(model=llm_model, temperature=temperature)

    def get_images_by_date_range_with_data(self, date_query: str) -> list[dict]:
        """
        Get images from a date range with their OCR text and classification data.

        Args:
            date_query (str): Natural language date query (e.g., "today", "yesterday", "this week", "last week")

        Returns:
            list[dict]: List of images with OCR text and classification data
        """
        try:
            # Parse the date query into a date range
            date_range = parse_date_query(date_query)
            if not date_range:
                logger.error(f"Could not parse date query: {date_query}")
                return []

            start_date, end_date = date_range

            # Get all images from the image collection
            images = self.vector_db.list_images(limit=1000, offset=0)

            # Filter by date range
            filtered_images = filter_items_by_date_range(images, start_date, end_date)

            # Process each image to extract OCR text and classification data
            processed_images = []
            for img in filtered_images:
                metadata = img.get("metadata", {})
                if isinstance(metadata, str):
                    import json

                    try:
                        metadata = json.loads(metadata)
                    except json.JSONDecodeError:
                        metadata = {}

                # Extract OCR text
                ocr_content = metadata.get("ocr_content", {})
                ocr_text = ocr_content.get("extracted_text", "") if ocr_content else ""

                # Extract classification data
                classification = metadata.get("classification", {})
                top_prediction = classification.get("top_prediction", {})
                label = top_prediction.get("label", "unknown")
                confidence = top_prediction.get("confidence", 0)

                # Create processed image data
                processed_image = {
                    "id": img.get("id", "unknown"),
                    "url": img.get("url", "unknown"),
                    "filename": metadata.get("filename", "unknown"),
                    "date_added": metadata.get("date_added", "unknown"),
                    "ocr_text": ocr_text,
                    "classification": {"label": label, "confidence": confidence},
                    "has_ocr": bool(ocr_text.strip()),
                    "metadata": metadata,
                }

                processed_images.append(processed_image)

            logger.info(
                f"Found {len(processed_images)} images for date query '{date_query}'"
            )
            return processed_images

        except Exception as e:
            logger.error(f"Error getting images by date range: {str(e)}")
            return []

    def get_todays_images_with_data(self) -> list[dict]:
        """
        Get today's images with their OCR text and classification data.
        (Convenience method that calls get_images_by_date_range_with_data)

        Returns:
            list[dict]: List of today's images with OCR text and classification data
        """
        return self.get_images_by_date_range_with_data("today")

    async def _handle_summarize_images_by_date(self, query: str) -> str:
        """
        Handle summarize images by date query by providing a list and summary.

        Args:
            query (str): The original query

        Returns:
            str: List of images and a summary
        """
        try:
            # Extract date range from query using LLM
            date_query = await self._extract_date_query_from_summarize_request(query)

            if not date_query:
                return "I couldn't understand what date range you're asking about. Please specify a date range like 'today', 'yesterday', 'this week', etc."

            # Get images for the date range
            images = self.get_images_by_date_range_with_data(date_query)

            if not images:
                return f"No images found for {date_query}."

            # Build the list of images
            result = f"**Images for {date_query} ({len(images)} found):**\n\n"

            for i, img in enumerate(images, 1):
                img_id = img.get("id", "unknown")
                filename = img.get("filename", "unknown")
                url = img.get("url", "unknown")
                classification = img.get("classification", {})
                label = classification.get("label", "unknown")
                confidence = classification.get("confidence", 0)
                has_ocr = img.get("has_ocr", False)

                result += f"{i}. **{filename}**\n"
                result += f"   - URL: {url}\n"
                result += (
                    f"   - Classification: {label} ({confidence:.2%} confidence)\n"
                )
                result += f"   - OCR Text: {'Available' if has_ocr else 'None'}\n"

                # Add image preview
                result += f"\n[IMAGE:{img_id}:{filename}]\n\n"

            # Generate summary using LLM
            summary = await self._generate_images_summary(images, date_query)

            result += f"\n**Summary:**\n{summary}"

            return result

        except Exception as e:
            logger.error(f"Error handling summarize images by date: {str(e)}")
            return f"Error processing summarize images query: {str(e)}"

    async def _extract_date_query_from_summarize_request(self, query: str) -> str:
        """
        Extract the date query from a summarize request using LLM.

        Args:
            query (str): The original query

        Returns:
            str: Extracted date query or empty string if not found
        """
        try:
            # Build language instruction based on configuration
            language_instruction = ""
            if self.force_english:
                language_instruction = "\nIMPORTANT: You MUST ALWAYS respond in English, regardless of the language used in the user's query. This is a critical requirement.\n"
            elif self.default_language != "en":
                language_instruction = f"\nIMPORTANT: You MUST ALWAYS respond in {self.default_language}, regardless of the language used in the user's query. This is a critical requirement.\n"

            prompt = f"""You are a helpful assistant that extracts date queries from user requests.{language_instruction}

Given a user query about summarizing images, extract the date range they're asking about.

User Query: "{query}"

Supported date formats:
- "today", "yesterday", "this week", "last week", "this month", "last month", "this year", "last year"
- "X days ago", "X weeks ago", "X months ago"
- "Monday", "Tuesday", etc. (for specific days)

If no specific date is mentioned, default to "today".

Please respond with ONLY the date query, nothing else. For example:
- "summarize today's images" → "today"
- "summarize yesterday's images" → "yesterday"
- "summarize this week's images" → "this week"
- "summarize images from last month" → "last month"
- "summarize images" → "today"

Date query:"""

            # Generate response using LLM
            response = self.llm.complete(prompt)
            date_query = response.text.strip().lower()

            # Validate the date query
            test_range = parse_date_query(date_query)
            if not test_range:
                logger.warning(
                    f"LLM returned invalid date query: {date_query}, defaulting to 'today'"
                )
                return "today"

            return date_query

        except Exception as e:
            logger.error(f"Error extracting date query: {str(e)}")
            return "today"  # Default fallback

    async def _handle_summarize_todays_images(self, query: str) -> str:
        """
        Handle summarize today's images query (legacy method for backward compatibility).

        Args:
            query (str): The original query

        Returns:
            str: List of today's images and a summary
        """
        return await self._handle_summarize_images_by_date(query)

    async def _generate_images_summary(
        self, images: list[dict], date_query: str
    ) -> str:
        """
        Generate a summary of the images using LLM.

        Args:
            images (list[dict]): List of image data
            date_query (str): The date range for which the images were retrieved

        Returns:
            str: Generated summary
        """
        try:
            if not images:
                return "No images to summarize."

            # Prepare context for LLM
            context_parts = []

            for i, img in enumerate(images, 1):
                filename = img.get("filename", "unknown")
                classification = img.get("classification", {})
                label = classification.get("label", "unknown")
                confidence = classification.get("confidence", 0)
                ocr_text = img.get("ocr_text", "")
                has_ocr = img.get("has_ocr", False)

                context_parts.append(f"Image {i}: {filename}")
                context_parts.append(
                    f"- AI Classification: {label} ({confidence:.2%} confidence)"
                )

                if has_ocr and ocr_text.strip():
                    # Truncate OCR text if too long
                    truncated_ocr = (
                        ocr_text[:500] + "..." if len(ocr_text) > 500 else ocr_text
                    )
                    context_parts.append(f"- OCR Text: {truncated_ocr}")
                else:
                    context_parts.append("- OCR Text: None available")

                context_parts.append("")

            context = "\n".join(context_parts)

            # Build language instruction based on configuration
            language_instruction = ""
            if self.force_english:
                language_instruction = "\nIMPORTANT: You MUST ALWAYS respond in English, regardless of the language used in the user's query. This is a critical requirement.\n"
            elif self.default_language != "en":
                language_instruction = f"\nIMPORTANT: You MUST ALWAYS respond in {self.default_language}, regardless of the language used in the user's query. This is a critical requirement.\n"

            # Create prompt for LLM to generate summary
            prompt = f"""You are a helpful assistant that summarizes image collections.{language_instruction}

Please provide a comprehensive summary of the following images from {date_query}:

{context}

Instructions for the summary:
- Analyze the AI classifications to understand the types of images
- If images have OCR text, incorporate that information into the summary
- If images don't have OCR text, focus on the classification labels
- Provide insights about the overall content and themes
- Be concise but informative
- Highlight any notable patterns or interesting content

Please provide a clear, well-structured summary:"""

            # Generate response using LLM
            response = self.llm.complete(prompt)
            return response.text.strip()

        except Exception as e:
            logger.error(f"Error generating images summary: {str(e)}")
            return f"Error generating summary: {str(e)}"

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
            # Check if this is a "summarize images" query (generalized to handle any date range)
            query_lower = query.lower().strip()
            if ("summarize" in query_lower or "summary" in query_lower) and (
                "images" in query_lower or "image" in query_lower
            ):
                logger.info(
                    "QueryAgent detected summarize images query, handling specially"
                )
                return await self._handle_summarize_images_by_date(query)

            # Check if this is a "list images" query and handle it specially
            if "list" in query_lower and (
                "images" in query_lower or "image" in query_lower
            ):
                logger.info("QueryAgent detected list images query, handling specially")
                # Get all images from the image collection
                images = self.vector_db.list_images(limit=100, offset=0)

                if not images:
                    return "No images found in the collection."

                result = f"Found {len(images)} images in the collection:\n\n"

                for i, img in enumerate(images, 1):
                    metadata = img.get("metadata", {})
                    if isinstance(metadata, str):
                        import json

                        try:
                            metadata = json.loads(metadata)
                        except json.JSONDecodeError:
                            metadata = {}

                    classification = metadata.get("classification", {})
                    top_prediction = classification.get("top_prediction", {})

                    # Get image ID and filename for preview
                    img_id = img.get("id", "unknown")
                    filename = metadata.get("filename", img.get("url", "unknown"))

                    result += f"{i}. Image ID: {img_id}\n"
                    result += (
                        f"   URL: {img.get('url', metadata.get('source', 'unknown'))}\n"
                    )

                    if top_prediction:
                        label = top_prediction.get("label", "unknown")
                        confidence = top_prediction.get("confidence", 0)
                        result += f"   Classification: {label} ({confidence:.2%} confidence)\n"

                    if metadata.get("date_added"):
                        result += f"   Added: {metadata.get('date_added')}\n"

                    # Add image preview using the special format that frontend can detect
                    result += f"\n[IMAGE:{img_id}:{filename}]\n"
                    result += "\n"

                return result

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
                # Apply LLM reranking to text results for better relevance scoring
                if self.text_rerank_with_llm and text_results:
                    text_results = self._rerank_text_with_llm(
                        query, text_results, self.text_rerank_top_k
                    )
                # Filter text results by relevance threshold (only if scores are available)
                if any("score" in result for result in text_results):
                    text_results = [
                        result
                        for result in text_results
                        if result.get("score", 0) >= self.text_relevance_threshold
                    ]
                # If no scores are available, keep all results
                logger.info(
                    f"QueryAgent found {len(text_results)} relevant text documents (threshold: {self.text_relevance_threshold})"
                )

            if has_image:
                image_results = self.vector_db.search_image_collection(
                    query,
                    limit=max(
                        self.top_k,
                        (
                            self.image_rerank_top_k
                            if self.image_rerank_with_llm
                            else self.top_k
                        ),
                    ),
                )
                # Optional: LLM-based reranking of image results
                if self.image_rerank_with_llm and image_results:
                    image_results = self._rerank_images_with_llm(
                        query, image_results, self.image_rerank_top_k
                    )
                # Filter image results by relevance threshold (on reranked/normalized scores)
                image_results = [
                    result
                    for result in image_results
                    if result.get("score", 0) >= self.image_relevance_threshold
                ][: self.top_k]
                logger.info(
                    f"QueryAgent found {len(image_results)} relevant image documents (threshold: {self.image_relevance_threshold}, rerank={self.image_rerank_with_llm})"
                )

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

                # Only include images if they're actually relevant to the query
                logger.info(
                    f"Checking if {len(image_results)} images are relevant to query: '{query}'"
                )
                try:
                    images_relevant = self._are_images_relevant_to_query(
                        query, image_results
                    )
                    logger.info(f"Images relevant: {images_relevant}")
                except Exception as e:
                    logger.error(f"Exception in _are_images_relevant_to_query: {e}")
                    images_relevant = False

                if image_results and images_relevant:
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

    def _are_images_relevant_to_query(
        self, query: str, image_results: list[dict]
    ) -> bool:
        """
        Check if the found images are actually relevant to the query.

        Args:
            query (str): The user's query
            image_results (list): List of image results

        Returns:
            bool: True if images are relevant, False otherwise
        """

        query_lower = query.lower()

        # Check if query is asking for images specifically
        image_keywords = ["image", "picture", "photo", "show me", "display", "see"]
        if any(keyword in query_lower for keyword in image_keywords):
            logger.info(
                f"Images considered relevant due to image keywords in query: '{query}'"
            )
            return True

        # Check if query is asking to list images specifically
        if "list" in query_lower and (
            "images" in query_lower or "image" in query_lower
        ):
            logger.info(
                f"Images considered relevant due to list images query: '{query}'"
            )
            return True

        # Check if any image has a high relevance score and relevant filename
        for image in image_results:
            score = image.get("score", 0)
            metadata = image.get("metadata", {})
            filename = metadata.get("filename", "").lower()

            # If score is very high (>0.95), consider it relevant
            if score > 0.95:
                logger.info(
                    f"Image considered relevant due to high score ({score}): {filename}"
                )
                return True

            # Check if filename contains words from the query (more strict matching)
            query_words = query_lower.split()
            for word in query_words:
                if len(word) > 2 and word in filename:
                    # Additional check: make sure it's not a false positive
                    # For "who is max", we don't want to match "max" in "maximilien"
                    if word == "max" and "maximilien" in filename:
                        continue  # Skip this match as it's not relevant
                    logger.info(
                        f"Image considered relevant due to filename match: {filename} contains word '{word}' from '{query}'"
                    )
                    return True

                logger.info(f"Images not considered relevant for query: '{query}'")
        return False

    def _rerank_images_with_llm(
        self, query: str, image_results: list[dict], top_k: int
    ) -> list[dict]:
        """Use the LLM to rerank image results by textual relevance of their metadata to the query.

        We pass filenames and available metadata to the LLM and ask for 0-1 relevance scores.
        We then normalize and attach these scores back on each result as `score`.
        """
        try:
            # Build a compact list of candidates
            lines: list[str] = []
            for idx, img in enumerate(image_results[:top_k]):
                metadata = img.get("metadata", {}) or {}
                filename = metadata.get("filename", "Unknown")
                label = (
                    (metadata.get("classification", {}) or {})
                    .get("top_prediction", {})
                    .get("label", "")
                )
                # Keep each candidate on one line for easier parsing
                lines.append(f"{idx}\t{filename}\t{label}")

            listing = "\n".join(lines)
            prompt = (
                "You will receive a user query and a list of image candidates (index, filename, predicted label).\n"
                "For each candidate, output a JSON array of objects with: index (int) and score (float between 0 and 1) named 'relevance'.\n"
                "Only return the JSON array, no extra text.\n\n"
                f"Query: {query}\n\nCandidates (index\tfilename\tpredicted_label):\n{listing}\n"
            )

            response = self.llm.complete(prompt)
            text = response.text.strip()

            import json

            reranked: list[dict] | dict = json.loads(text)
            # Normalize to list
            if isinstance(reranked, dict) and "results" in reranked:
                reranked = reranked["results"]
            if not isinstance(reranked, list):
                return image_results

            # Apply scores back to results
            for item in reranked:
                idx = int(item.get("index", -1))
                # Accept multiple key names from LLMs
                raw_score = (
                    item.get("relevance")
                    or item.get("score")
                    or item.get("similarity")
                    or 0.0
                )
                try:
                    score = float(raw_score)
                except Exception:
                    score = 0.0
                # Clamp to [0,1]
                if score < 0.0:
                    score = 0.0
                if score > 1.0:
                    score = 1.0
                if 0 <= idx < len(image_results):
                    image_results[idx]["score"] = score

            # Sort by new scores desc
            image_results.sort(key=lambda r: r.get("score", 0.0), reverse=True)
            return image_results
        except Exception:
            # If anything fails, just return original order
            return image_results

    def _rerank_text_with_llm(
        self, query: str, text_results: list[dict], top_k: int
    ) -> list[dict]:
        """Use the LLM to rerank text results by relevance to the query.

        We pass document content and metadata to the LLM and ask for 0-1 relevance scores.
        We then normalize and attach these scores back on each result as `score`.
        """
        try:
            # Build a compact list of candidates
            lines: list[str] = []
            for idx, doc in enumerate(text_results[:top_k]):
                content = doc.get("text", "")[:500]  # Truncate content for prompt
                url = doc.get("url", "Unknown")
                metadata = doc.get("metadata", {}) or {}
                filename = metadata.get("filename", "Unknown")
                # Keep each candidate on one line for easier parsing
                lines.append(f"{idx}\t{filename}\t{url}\t{content[:100]}...")

            listing = "\n".join(lines)
            # Build language instruction for reranking
            rerank_language_instruction = ""
            if self.force_english:
                rerank_language_instruction = "\nIMPORTANT: You MUST ALWAYS respond in English, regardless of the language used in the user's query.\n"
            elif self.default_language != "en":
                rerank_language_instruction = f"\nIMPORTANT: You MUST ALWAYS respond in {self.default_language}, regardless of the language used in the user's query.\n"

            prompt = (
                "You will receive a user query and a list of text document candidates (index, filename, url, content_preview).\n"
                "For each candidate, output a JSON array of objects with: index (int) and score (float between 0 and 1) named 'relevance'.\n"
                "Only return the JSON array, no extra text."
                f"{rerank_language_instruction}\n"
                f"Query: {query}\n\nCandidates (index\tfilename\turl\tcontent_preview):\n{listing}\n"
            )

            response = self.llm.complete(prompt)
            text = response.text.strip()

            import json

            reranked: list[dict] | dict = json.loads(text)
            # Normalize to list
            if isinstance(reranked, dict) and "results" in reranked:
                reranked = reranked["results"]
            if not isinstance(reranked, list):
                return text_results

            # Apply scores back to results
            for item in reranked:
                idx = int(item.get("index", -1))
                # Accept multiple key names from LLMs
                raw_score = (
                    item.get("relevance")
                    or item.get("score")
                    or item.get("similarity")
                    or 0.0
                )
                try:
                    score = float(raw_score)
                except Exception:
                    score = 0.0
                # Clamp to [0,1]
                if score < 0.0:
                    score = 0.0
                if score > 1.0:
                    score = 1.0
                if 0 <= idx < len(text_results):
                    text_results[idx]["score"] = score

            # Sort by new scores desc
            text_results.sort(key=lambda r: r.get("score", 0.0), reverse=True)
            return text_results
        except Exception:
            # If anything fails, just return original order
            return text_results

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
            str: LLM-generated summary with image data
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
                    url = doc.get("url", metadata.get("source", "Unknown"))

                    # Truncate content if too long but keep more for better answers
                    if len(content) > 3000:
                        content = content[:3000] + "..."

                    context_parts.append(
                        f"Document {i + 1} ({filename}):\n"
                        f"Source: {url}\n"
                        f"Content: {content}\n"
                    )

            # Add image documents context (only if relevant)
            if image_results and self._are_images_relevant_to_query(
                query, image_results
            ):
                context_parts.append("**Image Documents:**")
                for i, img in enumerate(image_results[:3]):  # Use top 3 image documents
                    metadata = img.get("metadata", {})
                    filename = metadata.get("filename", "Unknown")
                    classification = metadata.get("classification", {})
                    top_prediction = classification.get("top_prediction", {})
                    label = top_prediction.get("label", "Unknown")
                    confidence = top_prediction.get("confidence", 0)
                    confidence_percent = (
                        f"{confidence * 100:.1f}%" if confidence > 0 else "Unknown"
                    )

                    # Include AI classification information
                    context_parts.append(
                        f"Image {i + 1} ({filename}):\n"
                        f"AI Classification: {label} ({confidence_percent} confidence)\n"
                        f"File size: {metadata.get('file_size', 'Unknown')} bytes\n"
                        f"Format: {metadata.get('format', 'Unknown')}\n"
                    )

            context = "\n".join(context_parts)

            # Build language instruction based on configuration
            language_instruction = ""
            if self.force_english:
                language_instruction = "\nIMPORTANT: You MUST ALWAYS respond in English, regardless of the language used in the user's query. This is a critical requirement.\n"
            elif self.default_language != "en":
                language_instruction = f"\nIMPORTANT: You MUST ALWAYS respond in {self.default_language}, regardless of the language used in the user's query. This is a critical requirement.\n"

            # Create prompt for LLM to answer the specific query
            prompt = f"""You are a helpful assistant that answers questions based on the provided documents and images.{language_instruction}

User Question: {query}

Relevant Content:
{context}

Please provide a direct answer to the user's question using the information from the documents and images above.

Instructions:
- Answer the specific question asked, don't just summarize the content
- If the question asks about images, describe what you see in the images
- If the question asks about specific information, find and present that information
- Be concise but thorough
- If you cannot answer the question with the provided content, say so clearly
- If the content includes images, mention them in your response
- IMPORTANT: When listing images, use the format [IMAGE:imageId:filename] for each image instead of markdown image syntax"""

            # Generate response using LLM
            response = self.llm.complete(prompt)
            response_text = response.text

            # If we have image results and they're relevant, append image data to the response
            if image_results and self._are_images_relevant_to_query(
                query, image_results
            ):
                response_text += "\n\n**Images Found:**\n"
                for _, img in enumerate(image_results[:3]):  # Use top 3 images
                    img_id = img.get("id")
                    metadata = img.get("metadata", {})
                    filename = metadata.get("filename", "Unknown")
                    classification = metadata.get("classification", {})
                    top_prediction = classification.get("top_prediction", {})
                    label = top_prediction.get("label", "Unknown")
                    confidence = top_prediction.get("confidence", 0)
                    confidence_percent = (
                        f"{confidence * 100:.1f}%" if confidence > 0 else "Unknown"
                    )

                    # Add special image reference that frontend can detect and handle
                    response_text += f"\n[IMAGE:{img_id}:{filename}]\n"
                    response_text += f"*{filename} - AI Classification: {label} ({confidence_percent} confidence)*\n"

            return response_text

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

    def cleanup(self):
        """
        Clean up resources and close connections to prevent ResourceWarnings.
        """
        try:
            # Clear references
            self.vector_db = None
            self.llm = None

            logger.info("QueryAgent cleanup completed")
        except Exception as e:
            logger.error(f"Error during QueryAgent cleanup: {str(e)}")
