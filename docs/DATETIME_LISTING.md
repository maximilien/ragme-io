# DateTime-Based Listing for Images and Documents

This document describes the new datetime-based listing functionality that allows users to query for images and documents based on natural language date expressions.

## Overview

The functional agent now supports intelligent date-based filtering for both documents and images. Instead of listing all items in the collection, users can now specify time ranges using natural language expressions.

## New Tools

### `list_documents_by_datetime(date_query, limit, offset)`

Lists documents in the collection filtered by a natural language date query.

**Parameters:**
- `date_query` (str): Natural language date expression (e.g., "yesterday", "today", "last week")
- `limit` (int): Maximum number of documents to return (default: 10)
- `offset` (int): Number of documents to skip (default: 0)

**Returns:** Formatted string with document information

### `list_images_by_datetime(date_query, limit, offset)`

Lists images in the collection filtered by a natural language date query.

**Parameters:**
- `date_query` (str): Natural language date expression (e.g., "yesterday", "today", "last week")
- `limit` (int): Maximum number of images to return (default: 10)
- `offset` (int): Number of images to skip (default: 0)

**Returns:** Formatted string with image information including classifications and previews

## Supported Date Queries

The system supports a wide range of natural language date expressions:

### Basic Time Periods
- `"today"` - Current day (00:00:00 to 23:59:59)
- `"yesterday"` - Previous day (00:00:00 to 23:59:59)
- `"this week"` - Current week (Monday 00:00:00 to current time)
- `"last week"` - Previous week (Monday 00:00:00 to Sunday 23:59:59)
- `"this month"` - Current month (1st 00:00:00 to current time)
- `"last month"` - Previous month (1st 00:00:00 to last day 23:59:59)
- `"this year"` - Current year (January 1st 00:00:00 to current time)
- `"last year"` - Previous year (January 1st 00:00:00 to December 31st 23:59:59)

### Relative Time Expressions
- `"3 days ago"` - Specific number of days in the past
- `"2 weeks ago"` - Specific number of weeks in the past
- `"1 month ago"` - Specific number of months in the past

## Usage Examples

### User Queries
Users can now ask questions like:

- "list yesterday's images"
- "show me today's documents"
- "list documents from last week"
- "show me images from 3 days ago"
- "list yesterday's documents"
- "what images did I add this month?"

### Agent Responses
The functional agent will interpret these queries and call the appropriate tool:

```
User: "list yesterday's images"
Agent: Calls list_images_by_datetime("yesterday")

User: "show me documents from last week"
Agent: Calls list_documents_by_datetime("last week")
```

## Implementation Details

### Date Parsing
The system uses the `parse_date_query()` function in `src/ragme/utils/common.py` to convert natural language expressions into precise datetime ranges.

### Filtering Logic
The `filter_items_by_date_range()` function filters items based on their `date_added` metadata field, handling both dictionary and JSON string metadata formats.

### Integration
The new tools are automatically available to the functional agent and are included in the system prompt with clear usage instructions.

## Error Handling

If a date query is not recognized, the system returns a helpful error message listing supported formats:

```
Could not understand the date query 'invalid date'. 
Supported formats: today, yesterday, this week, last week, this month, 
last month, this year, last year, 'X days ago', 'X weeks ago', 'X months ago'
```

## Testing

The functionality is thoroughly tested with unit tests covering:
- Date query parsing for all supported formats
- Filtering logic with various metadata formats
- Tool execution with valid and invalid queries
- Edge cases and error conditions

Run tests with:
```bash
python -m pytest tests/test_datetime_listing.py -v
```

## Backward Compatibility

The new functionality is additive and doesn't break existing functionality:
- Existing `list_ragme_collection()` and `list_image_collection()` tools continue to work
- Users can still use the old tools for listing all items
- The new tools provide enhanced filtering capabilities

## Future Enhancements

Potential future improvements could include:
- Support for custom date ranges (e.g., "between January 1st and March 15th")
- Time-based expressions (e.g., "this morning", "last night")
- Relative expressions with more precision (e.g., "2 hours ago")
- Integration with the query agent for content-based date filtering
