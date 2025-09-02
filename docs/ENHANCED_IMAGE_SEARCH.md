# Enhanced Image Search in RAGme

## Overview

This document describes the enhanced image search functionality implemented in RAGme to address the issue where queries like "show me a dog" or "display the Yorkshire terrier" were not including relevant images from the image collection.

## Problem Statement

Previously, queries requesting to "show" or "display" something were not intelligently including images, even when relevant images existed in the collection. Users had to explicitly ask for images or use specific image-related keywords.

## Solution Implemented

### 1. Intelligent Image Relevance Detection

Instead of relying on simple keyword matching, the system now uses **LLM-based intelligent determination** to decide when images would be helpful for a query.

**Key Features:**
- **LLM Analysis**: Uses the language model to analyze query intent and determine if images would enhance the response
- **Context-Aware**: Considers the available images and their metadata when making relevance decisions
- **Fallback Heuristics**: Includes fallback logic for when LLM analysis fails

**Implementation:** `_llm_determine_image_relevance()` method in `QueryAgent`

### 2. Enhanced Image Search Strategy

The image search now utilizes **comprehensive metadata** for better results:

**Metadata Fields Used:**
- **Filename**: Direct text matching
- **AI Classification**: Labels and confidence scores from image analysis
- **OCR Content**: Text extracted from images
- **EXIF Data**: Camera information, GPS coordinates, location data
- **Date/Time**: When images were taken or added

**Search Methods (in order of preference):**
1. **Multi-field BM25**: Searches across all metadata fields simultaneously
2. **Hybrid Search**: Combines vector similarity with sparse text matching
3. **General BM25**: Fallback to general metadata search
4. **Near-text**: Vector similarity as last resort

**Implementation:** Enhanced `search_image_collection()` methods in all vector database implementations

### 3. Smart Image Inclusion in Responses

When images are determined to be relevant, the system now:

**Includes Up to 3 Images:**
- Shows the most relevant images first
- Provides AI classification information and confidence scores
- Displays relevance scores for transparency
- Uses the `[IMAGE:id:filename]` format for frontend rendering

**User Experience:**
- Clear indication of how many relevant images were found
- Information about remaining images
- Guidance on how to request more images

**Implementation:** Enhanced response building in `QueryAgent.run()`

### 4. Memory for Follow-up Requests

The system now **keeps search results in memory** to handle follow-up requests:

**Memory Features:**
- Stores last search query and results
- Tracks timestamp for result freshness (10-minute expiration)
- Enables natural follow-up requests

**Follow-up Queries Supported:**
- "show more images"
- "additional images"
- "rest of the images"
- "more images please"
- "see more"

**Implementation:** `_handle_follow_up_image_request()` method in `QueryAgent`

## Configuration Updates

### Query Configuration

```yaml
query:
  top_k: 5  # Number of most relevant documents to retrieve
  text_rerank_top_k: 3  # Text results to rerank with LLM
  image_rerank_top_k: 10  # Image results to rerank with LLM
  text_rerank_with_llm: false  # Enable LLM reranking for text
  image_rerank_with_llm: true  # Enable LLM reranking for images
  relevance_thresholds:
    text: 0.4  # Text relevance threshold
    image: 0.3  # Image relevance threshold (lowered for better coverage)
```

## Vector Database Enhancements

### Weaviate (Cloud & Local)

- **Multi-field BM25**: Searches across filename, classification, OCR, EXIF
- **Enhanced logging**: Better visibility into search performance
- **Comprehensive fallbacks**: Multiple search strategies for reliability

### Milvus

- **Metadata relevance scoring**: Post-processes results using metadata
- **Score boosting**: Enhances relevance based on filename, classification, OCR matches
- **Intelligent ranking**: Combines vector similarity with metadata relevance

## Usage Examples

### Basic Image Queries

```
User: "show me a dog"
Response: [Includes up to 3 relevant dog images with classification info]

User: "display the Yorkshire terrier"
Response: [Shows Yorkshire terrier images with AI classification confidence]
```

### Follow-up Requests

```
User: "show more images"
Response: [Shows next batch of relevant images from previous search]

User: "additional images please"
Response: [Continues showing remaining relevant images]
```

## Technical Implementation Details

### Query Agent Changes

1. **Enhanced `_are_images_relevant_to_query()`**: Now uses LLM for intelligent determination
2. **New `_llm_determine_image_relevance()`**: LLM-based relevance analysis
3. **Memory storage**: `last_search_results` for follow-up requests
4. **Follow-up handling**: `_handle_follow_up_image_request()` method
5. **Enhanced response building**: Includes up to 3 images with metadata

### Vector Database Changes

1. **Multi-field search**: BM25 across comprehensive metadata
2. **Enhanced logging**: Better search result tracking
3. **Metadata utilization**: EXIF, AI classification, OCR content
4. **Fallback strategies**: Multiple search methods for reliability

## Benefits

### For Users

- **Natural Queries**: Can ask to "show me" something without specific image keywords
- **Better Results**: Images are included when they would be helpful
- **Follow-up Support**: Can request more images naturally
- **Rich Information**: See AI classification and confidence scores

### For System

- **Intelligent Routing**: LLM determines when images are relevant
- **Better Search**: Comprehensive metadata utilization
- **Memory Efficiency**: Results cached for follow-up requests
- **Scalability**: Multiple search strategies for different scenarios

## Testing

To test the enhanced functionality:

1. **Start RAGme backend** with the updated configuration
2. **Upload images** with metadata (EXIF, AI classification, OCR)
3. **Try queries** like:
   - "show me a dog"
   - "display the landscape"
   - "what does a car look like"
4. **Request more images** with follow-up queries
5. **Verify** that relevant images are included intelligently

## Future Enhancements

Potential improvements for future versions:

1. **User Preference Learning**: Remember which types of queries users prefer with images
2. **Image Result Caching**: Cache frequently requested image results
3. **Advanced Relevance Models**: More sophisticated relevance scoring algorithms
4. **Image Similarity Search**: Find visually similar images
5. **Contextual Image Selection**: Choose images based on conversation context

## Conclusion

The enhanced image search functionality transforms RAGme from a text-focused system to one that intelligently includes visual content when it enhances the user experience. By using LLM-based relevance determination and comprehensive metadata search, users can now naturally request to "show" or "display" things and receive relevant images alongside text responses.

This implementation maintains the existing functionality while significantly improving the user experience for image-related queries, making RAGme a more comprehensive and user-friendly information retrieval system.
