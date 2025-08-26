# PDF Image Extraction Feature

## Overview

RAGme now automatically extracts and processes images from PDF documents using PyMuPDF (fitz). When a PDF is uploaded, the system not only extracts text content but also identifies and extracts embedded images, processes them with AI classification and OCR, and stores them in the image collection with rich metadata.

## Features

### 🔍 Automatic Image Extraction
- **PyMuPDF Integration**: Uses PyMuPDF (fitz) for robust image extraction, extracting 8-bit/color RGB PNG images
- **Page-Level Scanning**: Scans each page for embedded images
- **Smart Filtering**: Configurable size and format constraints
- **Metadata Preservation**: Tracks PDF source, page numbers, and extraction timestamps
- **Web-Compatible Format**: Extracts images in proper color format (no more "black rectangle" display issues)

### 🤖 AI Processing Pipeline
- **Image Classification**: Uses PyTorch ResNet50 for content classification
- **OCR Text Extraction**: Extracts text from images containing text (diagrams, charts, etc.)
- **Caption Detection**: Attempts to extract captions from OCR content
- **Rich Metadata**: Complete processing information and confidence scores

### ⚙️ Configuration Options
- **Enable/Disable**: Toggle feature on/off globally
- **Size Constraints**: Minimum and maximum image size limits
- **Format Filtering**: Support for specific image formats
- **Processing Options**: Control AI classification and OCR processing

## Configuration

### Basic Configuration

Add the following section to your `config.yaml`:

```yaml
# PDF Image Extraction Configuration
pdf_image_extraction:
  enabled: true  # Enable/disable PDF image extraction
  min_image_size_kb: 1  # Minimum image size to extract (in KB)
  max_image_size_mb: 10  # Maximum image size to extract (in MB)
  supported_formats: ["jpeg", "jpg", "png", "gif", "bmp", "tiff"]  # Supported image formats
  extract_captions: true  # Try to extract captions from OCR content
  process_with_ai: true  # Apply AI classification and OCR to extracted images
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `true` | Enable or disable PDF image extraction globally |
| `min_image_size_kb` | integer | `1` | Minimum image size in KB to extract |
| `max_image_size_mb` | integer | `10` | Maximum image size in MB to extract |
| `supported_formats` | array | `["jpeg", "jpg", "png", "gif", "bmp", "tiff"]` | List of supported image formats |
| `extract_captions` | boolean | `true` | Attempt to extract captions from OCR content |
| `process_with_ai` | boolean | `true` | Apply AI classification and OCR processing |

## Processing Pipeline

### 1. PDF Upload
When a PDF is uploaded via the frontend or local agent, the system processes it normally for text extraction.

### 2. Image Detection
PyMuPDF scans each page of the PDF for embedded images and extracts them as 8-bit/color RGB PNG with basic metadata.

### 3. Image Filtering
Images are filtered based on:
- **Size constraints**: Must be within configured min/max size limits
- **Format support**: Must be in the supported formats list
- **Quality checks**: Basic validation of image data

### 4. AI Processing
If `process_with_ai` is enabled, extracted images go through:
- **Classification**: PyTorch ResNet50 classification for content identification
- **OCR Processing**: Text extraction from images containing text
- **Metadata Enhancement**: Rich metadata with confidence scores

### 5. Storage
Processed images are stored in the image collection with:
- **Base64 encoding**: Images stored as base64 data for web compatibility
- **Rich metadata**: Complete processing information and source tracking
- **Search indexing**: Full text search capabilities

## Metadata Structure

Each extracted image includes comprehensive metadata:

```json
{
  "source_type": "pdf_extracted_image",
  "pdf_filename": "document.pdf",
  "pdf_page_number": 3,
  "pdf_image_name": "X39.png",
  "pdf_storage_path": "documents/20250826_123456_document.pdf",
  "extraction_timestamp": "2025-08-26T14:21:22",
  "extracted_caption": "Figure 1: System Architecture",
  "classification": {
    "top_prediction": {
      "label": "diagram",
      "confidence": 0.95
    }
  },
  "ocr_content": {
    "text": "System Architecture Diagram",
    "confidence": 0.88
  },
             "size": 3318,
           "format": "png",
           "mime_type": "image/png",
           "width": 800,
           "height": 600
}
```

### Metadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `source_type` | string | Always "pdf_extracted_image" |
| `pdf_filename` | string | Original PDF filename |
| `pdf_page_number` | integer | Page number where image was found |
| `pdf_image_name` | string | Internal image name in PDF |
| `pdf_storage_path` | string | Storage path of the PDF file |
| `extraction_timestamp` | string | ISO timestamp of extraction |
| `extracted_caption` | string | Caption extracted from OCR (if available) |
| `classification` | object | AI classification results |
| `ocr_content` | object | OCR text extraction results |
| `size` | integer | Image file size in bytes |
| `format` | string | Image format (jpeg, png, etc.) |
| `mime_type` | string | MIME type (image/jpeg, image/png, etc.) |
| `width` | integer | Image width in pixels |
| `height` | integer | Image height in pixels |

## Use Cases

### Technical Documentation
Extract diagrams, charts, and screenshots from technical PDFs:
- Architecture diagrams
- Flow charts and process diagrams
- Screenshots and UI mockups
- Technical illustrations

### Research Papers
Extract figures, graphs, and tables from academic papers:
- Research graphs and charts
- Data visualizations
- Experimental results
- Statistical figures

### Business Reports
Extract visualizations and charts from business reports:
- Financial charts
- Performance metrics
- Organizational charts
- Marketing materials

### Presentations
Extract slides and graphics from PDF presentations:
- Slide graphics
- Infographics
- Charts and diagrams
- Visual elements

## Search Capabilities

### By PDF Source
```
"Show me images from document.pdf"
"Find all images from the architecture document"
"Extract images from the quarterly report"
```

### By Page Number
```
"Find images from page 5 of the report"
"Show diagrams from page 3"
"Extract charts from pages 10-15"
```

### By Content Type
```
"Find diagrams or charts in my PDFs"
"Show me screenshots from technical documents"
"Extract graphs from research papers"
```

### By Extracted Text
```
"Find images containing 'API' text"
"Show diagrams with 'architecture' in the text"
"Extract charts mentioning 'performance'"
```

## Example Workflow

### Upload Technical Document
```
User: "Upload this technical document: architecture.pdf"
RAGme: 
  - Extracts text content (20 pages, 15,000 characters)
  - Extracts 8 images (diagrams, screenshots, charts)
  - Processes images with AI classification
  - Stores everything in respective collections
```

### Query Extracted Images
```
User: "Show me the diagrams from the architecture document"
RAGme: Lists 3 images classified as "diagram" from architecture.pdf

User: "Find images with 'API' in the text"
RAGme: Searches OCR content and finds 2 images containing "API" text
```

## Error Handling

### Graceful Degradation
- **PDF Processing**: If image extraction fails, PDF text processing continues normally
- **Image Processing**: If AI processing fails, images are still stored with basic metadata
- **Storage Issues**: If vector database is unavailable, images are processed but not stored

### Error Logging
- **Detailed Logs**: All extraction and processing steps are logged
- **Error Context**: Specific error messages with PDF and image context
- **Debugging Info**: Page numbers, image names, and processing stages

### Common Issues
- **Large Images**: Images exceeding size limits are skipped with debug logging
- **Unsupported Formats**: Non-supported image formats are filtered out
- **Corrupted Images**: Damaged images are handled gracefully with error reporting

## Performance Considerations

### Processing Time
- **Image Extraction**: Typically 1-5 seconds per page depending on image count
- **AI Processing**: 2-10 seconds per image depending on size and complexity
- **Storage**: 1-3 seconds per image for vector database storage

### Resource Usage
- **Memory**: Temporary storage of extracted images during processing
- **CPU**: AI classification and OCR processing
- **Storage**: Base64 encoding increases storage size by ~33%

### Optimization Tips
- **Size Limits**: Adjust `max_image_size_mb` to limit processing time
- **Format Filtering**: Restrict `supported_formats` to common formats only
- **AI Processing**: Disable `process_with_ai` for faster processing without classification

## Integration Points

### Frontend Integration
- **Upload Interface**: No changes required - works automatically with PDF uploads
- **Image Gallery**: Extracted images appear in the image collection
- **Search Interface**: Full text search includes extracted image content

### API Integration
- **PDF Processing**: Enhanced `/tool/process_pdf` and `/tool/process_pdf_base64` endpoints
- **Response Data**: Includes `extracted_images_count` in processing results
- **Error Handling**: Graceful degradation with detailed error reporting

### Agent Integration
- **Local Agent**: Automatic image extraction during watch directory processing
- **Logging**: Enhanced logging shows image extraction progress
- **Error Handling**: Robust error handling prevents processing failures

## Testing

### Unit Tests
Comprehensive test suite in `tests/test_pdf_image_extraction.py`:
- Configuration loading and validation
- Image extraction functionality
- Size and format constraint checking
- Error handling and edge cases
- Metadata creation and validation
- Vector database integration

### Integration Tests
- End-to-end PDF processing with image extraction
- Vector database storage and retrieval
- Configuration system integration
- Error handling scenarios

### Test Coverage
- ✅ Configuration validation
- ✅ Image extraction functionality
- ✅ Size and format constraints
- ✅ Error handling
- ✅ Metadata creation
- ✅ Vector database integration

## Troubleshooting

### Common Issues

#### Images Not Extracted
1. **Check Configuration**: Verify `enabled: true` in config
2. **Size Constraints**: Check if images meet size requirements
3. **Format Support**: Verify image formats are in supported list
4. **PDF Structure**: Some PDFs may not contain extractable images

#### Processing Errors
1. **Memory Issues**: Reduce `max_image_size_mb` if processing large images
2. **AI Dependencies**: Ensure PyTorch and OCR dependencies are installed
3. **Vector Database**: Check vector database connectivity and configuration

#### Performance Issues
1. **Large PDFs**: Consider processing in batches for very large documents
2. **Image Count**: PDFs with many images will take longer to process
3. **AI Processing**: Disable `process_with_ai` for faster processing

### Debug Logging
Enable debug logging to see detailed processing information:
```yaml
logging:
  level: "DEBUG"
```

### Monitoring
Monitor the following metrics:
- **Extraction Success Rate**: Percentage of PDFs with successful image extraction
- **Processing Time**: Average time per PDF and per image
- **Storage Usage**: Impact on vector database storage
- **Error Rates**: Frequency of extraction and processing errors

## Future Enhancements

### Planned Features
- **Batch Processing**: Process multiple PDFs simultaneously
- **Advanced Filtering**: Content-based image filtering
- **Custom Metadata**: User-defined metadata extraction
- **Export Options**: Export extracted images to file system

### Potential Improvements
- **Alternative Libraries**: Support for additional PDF processing libraries
- **Image Enhancement**: Automatic image quality improvement
- **Compression**: Optimize storage with image compression
- **Caching**: Cache processed images for improved performance

## Conclusion

The PDF Image Extraction feature provides a comprehensive solution for automatically extracting and processing images from PDF documents. With full AI processing integration, rich metadata preservation, and robust error handling, it enables users to leverage visual content from their PDF documents alongside text content in a unified search and retrieval system.

The feature is designed to be:
- **Automatic**: No user intervention required
- **Configurable**: Flexible settings for different use cases
- **Robust**: Graceful error handling and logging
- **Integrated**: Seamless integration with existing RAGme functionality
- **Scalable**: Efficient processing for large document collections
