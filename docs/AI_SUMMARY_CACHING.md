# AI Summary Caching

## Overview

The AI Summary Caching system prevents redundant AI summary generation by storing generated summaries in document metadata and retrieving them on subsequent requests. This improves performance, reduces API costs, and provides a better user experience.

## Features

### 🧠 Intelligent Caching
- **Automatic Cache Checking**: System checks for existing summaries before generating new ones
- **Metadata Storage**: Summaries stored in vector database document metadata
- **Visual Indicators**: Frontend shows "Cached Summary" badge for cached content
- **Cross-Collection Support**: Works with both document and image collections

### 🎯 Performance Benefits
- **Reduced API Calls**: Eliminates redundant OpenAI API calls for existing summaries
- **Faster Response Times**: Cached summaries load instantly
- **Cost Optimization**: Reduces AI service usage costs
- **Improved UX**: No waiting for summary regeneration

### 🔄 Force Refresh Capability
- **Manual Refresh**: Users can force regenerate summaries using the refresh button
- **Bypass Cache**: Force refresh bypasses cached summaries and generates new content
- **Visual Feedback**: Clear indication when summaries are being regenerated
- **HTTP Request Handling**: Proper handling of force refresh requests with parameter validation

## Architecture

### Backend Implementation

#### Vector Database Abstraction
The caching system extends the vector database abstraction with metadata update capabilities:

```python
# Base class methods (VectorDatabase)
@abstractmethod
def update_document_metadata(self, document_id: str, metadata: dict[str, Any]) -> bool:
    """Update metadata for a document in the text collection."""

@abstractmethod
def update_image_metadata(self, image_id: str, metadata: dict[str, Any]) -> bool:
    """Update metadata for an image in the image collection."""
```

#### Implementation Examples

**Weaviate Implementation:**
```python
def update_document_metadata(self, document_id: str, metadata: dict[str, Any]) -> bool:
    """Update metadata for a document in the text collection."""
    collection = self.client.collections.get(self.text_collection.name)
    
    # Use the correct Weaviate filter syntax to get the object by ID
    import weaviate.classes as wvc
    
    response = collection.query.fetch_objects(
        limit=1,
        include_vector=False,
        filters=wvc.query.Filter.by_id().equal(document_id),
    )
    
    if not response.objects:
        return False
    
    # Update metadata
    existing_metadata = response.objects[0].properties.get("metadata", {})
    existing_metadata.update(metadata)
    
    # Persist changes
    collection.data.update(
        uuid=document_id,
        properties={"metadata": existing_metadata}
    )
    
    return True
```

**Milvus Implementation:**
```python
def update_document_metadata(self, document_id: str, metadata: dict[str, Any]) -> bool:
    """Update metadata for a document in the text collection."""
    # Get existing document
    response = self.client.query(
        collection_name=self.text_collection.name,
        filter=f'id == "{document_id}"',
        output_fields=["id", "url", "text", "metadata"],
        limit=1,
    )
    
    if not response:
        return False
    
    # Update metadata
    existing_metadata = json.loads(response[0].get("metadata", "{}"))
    existing_metadata.update(metadata)
    
    # Persist changes
    self.client.update(
        collection_name=self.text_collection.name,
        filter=f'id == "{document_id}"',
        data={"metadata": json.dumps(existing_metadata)},
    )
    
    return True
```

### API Integration

#### Summary Generation Flow

1. **Cache Check**: API checks for existing `ai_summary` in document metadata
2. **Cached Response**: If found, returns cached summary with `cached: True` flag
3. **Generation**: If not found, generates new summary using AI
4. **Storage**: Stores generated summary in document metadata
5. **Response**: Returns summary with appropriate caching status

```python
@app.post("/summarize-document")
async def summarize_document(input_data: SummarizeInput):
    # Find document
    document = find_document_by_id(document_id)
    
    # Check for cached summary
    metadata = document.get("metadata", {})
    existing_summary = metadata.get("ai_summary")
    
    if existing_summary:
        return {
            "status": "success",
            "summary": existing_summary,
            "document_id": document_id,
            "cached": True  # Indicates cached content
        }
    
    # Generate new summary
    summary_text = await generate_ai_summary(document)
    
    # Store in metadata
    try:
        if document.get("content_type") == "image":
            image_vdb.update_image_metadata(document_id, {"ai_summary": summary_text})
        else:
            ragme.update_document_metadata(document_id, {"ai_summary": summary_text})
    except Exception as e:
        print(f"Warning: Failed to store AI summary in metadata: {e}")
    
    return {
        "status": "success",
        "summary": summary_text,
        "cached": False
    }
```

### Frontend Integration

#### Visual Indicators

The frontend displays caching status with visual indicators:

```javascript
this.socket.on('document_summarized', (result) => {
    if (result.success) {
        let summaryText = result.summary;
        if (result.cached) {
            summaryText = `<div class="cached-summary-indicator">
                <i class="fas fa-save"></i> Cached Summary
            </div>${summaryText}`;
        }
        this.updateDocumentSummary(summaryText);
    }
});
```

#### CSS Styling

```css
.cached-summary-indicator {
    background: #e0f2fe;
    color: #0277bd;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    margin-bottom: 0.5rem;
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    border: 1px solid #81c784;
}

.cached-summary-indicator i {
    font-size: 0.7rem;
}
```

## Usage

### Automatic Operation

The caching system operates automatically:

1. **First Access**: When a document is opened for the first time, AI generates a summary
2. **Storage**: Summary is automatically stored in document metadata
3. **Subsequent Access**: On future opens, cached summary is retrieved instantly
4. **Visual Feedback**: Frontend shows "Cached Summary" indicator

### Manual Cache Management

#### Clear Cache for Document

To regenerate a summary (clear cache):

```python
# Remove cached summary from metadata
ragme.update_document_metadata(document_id, {"ai_summary": None})
```

#### Check Cache Status

```python
# Check if document has cached summary
document = ragme.list_documents(limit=1, offset=0)[0]
has_cached_summary = "ai_summary" in document.get("metadata", {})
```

## Force Refresh Implementation

### Frontend Implementation

The force refresh feature is implemented in the frontend with a refresh button next to the "AI Summary" title:

```javascript
// Force refresh button in document details modal
<span class="force-refresh-icon" title="Force refresh AI summary" data-action="force-refresh-summary">
    <i class="fas fa-sync-alt"></i>
</span>
```

#### Event Handling

```javascript
// Event delegation for force refresh
document.addEventListener('click', (e) => {
    const forceRefreshIcon = e.target.closest('[data-action="force-refresh-summary"]');
    if (forceRefreshIcon) {
        e.preventDefault();
        e.stopPropagation();
        this.forceRefreshSummary();
    }
});
```

#### HTTP Request Implementation

```javascript
// Force refresh with HTTP request
async fetchDocumentSummary(doc, forceRefresh = false) {
    const response = await fetch(this.buildApiUrl('summarize-document'), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            document_id: documentIdToSend,
            forceRefresh: forceRefresh
        })
    });
}
```

### Backend Implementation

#### Pydantic Model

```python
class SummarizeInput(BaseModel):
    """Input model for document summarization."""
    document_id: str | dict
    force_refresh: bool = Field(default=False, alias="forceRefresh")
```

#### Force Refresh Logic

```python
# Check if summary already exists in metadata (unless force refresh is requested)
metadata = document.get("metadata", {})
existing_summary = metadata.get("ai_summary")

if existing_summary and not input_data.force_refresh:
    print(f"📋 RETRIEVED cached AI summary for document: {document_id}")
    return {
        "status": "success",
        "summary": existing_summary,
        "document_id": input_data.document_id,
        "cached": True,
    }

if input_data.force_refresh and existing_summary:
    print(f"🔄 FORCE REFRESH requested for document: {document_id} - regenerating AI summary")
```

### CSS Styling

```css
.force-refresh-icon {
    cursor: pointer;
    opacity: 0.6;
    transition: all 0.2s ease;
    font-size: 0.8rem;
    color: #6b7280;
    margin-left: auto;
}

.force-refresh-icon:hover {
    opacity: 1;
    color: #10b981;
    transform: scale(1.1);
}

.force-refresh-icon i {
    transition: transform 0.3s ease;
}

.force-refresh-icon:hover i {
    transform: rotate(180deg);
}
```

## Configuration

### Environment Variables

No additional configuration required - caching is enabled by default.

### Vector Database Support

Caching works with all supported vector databases:
- ✅ **Weaviate** (Cloud and Local)
- ✅ **Milvus** (Lite and Cloud)

## Performance Impact

### Benefits

- **API Cost Reduction**: Eliminates redundant AI API calls
- **Response Time**: Cached summaries load instantly (< 100ms)
- **User Experience**: No waiting for summary regeneration
- **Resource Efficiency**: Reduces AI service load

### Monitoring

Monitor caching effectiveness:

```python
# Check cache hit rate
total_requests = get_total_summary_requests()
cached_requests = get_cached_summary_requests()
cache_hit_rate = cached_requests / total_requests
```

## Troubleshooting

### Common Issues

#### Cache Not Working

1. **Check Vector Database**: Ensure VDB supports metadata updates
2. **Verify Implementation**: Confirm `update_document_metadata` method exists
3. **Check Permissions**: Ensure write access to document metadata
4. **Review Logs**: Check for metadata update errors

#### Stale Cache

1. **Manual Clear**: Remove `ai_summary` from metadata
2. **Document Update**: Regenerate summary after document changes
3. **Force Refresh**: Use cache-busting techniques if needed

### Debug Commands

```bash
# Check if document has cached summary
./tools/vdb.sh list-documents | grep -A 5 "ai_summary"

# Clear cache for specific document
# (Manual operation through API or direct VDB access)
```

## Future Enhancements

### Planned Features

- **Cache Expiration**: Automatic cache invalidation after time periods
- **Cache Statistics**: Dashboard showing cache hit rates and performance
- **Selective Caching**: User control over what gets cached
- **Cache Compression**: Compress cached summaries for storage efficiency
- **Multi-Language Support**: Cache summaries in multiple languages

### Advanced Caching

- **Version Control**: Cache different summary versions
- **User-Specific Caching**: Personalized summaries per user
- **Context-Aware Caching**: Cache based on query context
- **Intelligent Pre-caching**: Predict and cache likely-needed summaries

## Related Documentation

- **[Vector Database Abstraction](VECTOR_DB_ABSTRACTION.md)** - Vector database architecture
- **[Configuration Guide](CONFIG.md)** - System configuration options
- **[API Documentation](API.md)** - API endpoint documentation
- **[Troubleshooting](TROUBLESHOOTING.md)** - Common issues and solutions

---

*Last updated: January 2025*
