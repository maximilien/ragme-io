# Image Summarization Feature

## Overview

The image summarization feature allows users to get a comprehensive summary of images from any date range. The system intelligently extracts date ranges from natural language queries and provides both a list of images and an AI-generated summary.

## How It Works

### 1. Query Processing
When a user asks to "summarize images", the system:
- Uses LLM to extract the date range from the query
- Supports natural language date expressions like "today", "yesterday", "this week", etc.
- Defaults to "today" if no specific date is mentioned

### 2. Image Retrieval
The system retrieves images for the specified date range and extracts:
- **OCR Text**: Extracted text from images that contain readable text
- **AI Classification**: Labels and confidence scores from image classification
- **Metadata**: File information, dates, URLs, etc.

### 3. Summary Generation
Using the retrieved data, the system generates a comprehensive summary that:
- Analyzes AI classifications to understand image types
- Incorporates OCR text when available
- Provides insights about content themes and patterns
- Highlights notable or interesting content

## Supported Date Queries

The system supports a wide range of natural language date expressions:

### Basic Time Periods
- `"today"` - Current day
- `"yesterday"` - Previous day
- `"this week"` - Current week
- `"last week"` - Previous week
- `"this month"` - Current month
- `"last month"` - Previous month
- `"this year"` - Current year
- `"last year"` - Previous year

### Relative Time
- `"X days ago"` - Specific number of days in the past
- `"X weeks ago"` - Specific number of weeks in the past
- `"X months ago"` - Specific number of months in the past

### Specific Days
- `"Monday"`, `"Tuesday"`, etc. - Specific days of the week

## Example Queries

```
User: "summarize today's images"
System: Lists today's images with AI-generated summary

User: "summarize yesterday's images"
System: Lists yesterday's images with AI-generated summary

User: "summarize this week's images"
System: Lists this week's images with AI-generated summary

User: "summarize images from last month"
System: Lists last month's images with AI-generated summary

User: "summarize images from 3 days ago"
System: Lists images from 3 days ago with AI-generated summary

User: "summarize images"
System: Lists today's images (default) with AI-generated summary
```

## Output Format

The system provides:

1. **Image List**: Each image shows:
   - Filename and URL
   - AI classification with confidence score
   - OCR text availability indicator
   - Image preview (frontend-rendered)

2. **AI Summary**: Generated summary that:
   - Analyzes image types and themes
   - Incorporates OCR text when available
   - Highlights patterns and notable content
   - Provides insights about the collection

## Technical Implementation

### QueryAgent Methods
- `get_images_by_date_range_with_data(date_query)` - Retrieves images with OCR and classification data
- `_extract_date_query_from_summarize_request(query)` - Uses LLM to extract date range
- `_handle_summarize_images_by_date(query)` - Main handler for summarize requests
- `_generate_images_summary(images, date_query)` - Generates AI summary

### Tools Integration
- `get_images_by_date_range_with_data(date_query)` - Available as a tool for other agents
- `get_todays_images_with_data()` - Convenience method for today's images

### Routing Logic
- RagMeAgent routes "summarize images" queries to QueryAgent
- QueryAgent handles the analysis and summary generation
- FunctionalAgent provides access to the underlying tools

## Configuration

The feature respects the following configuration settings:
- Language settings (force_english, default_language)
- LLM model and temperature settings
- OCR processing settings
- Image classification settings

## Error Handling

The system gracefully handles:
- Invalid date queries (defaults to "today")
- No images found for the specified date range
- OCR processing failures
- Classification failures
- LLM processing errors

## Future Enhancements

Potential improvements:
- Support for more complex date ranges
- Filtering by image type or classification
- Custom summary styles
- Export functionality
- Integration with document summarization
