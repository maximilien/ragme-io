# AI Acceleration with FriendliAI

## Overview

RAGme now supports optional AI acceleration for image processing using FriendliAI, providing faster and more accurate image classification and OCR capabilities. This feature enhances the existing PyTorch and EasyOCR processing with cloud-based AI acceleration while maintaining full backward compatibility.

## Benefits

### ⚡ Performance Improvements
- **Parallel Processing**: Classification and OCR run simultaneously instead of sequentially
- **Faster Response Times**: Reduced processing time for complex images
- **Optimized Infrastructure**: Leverages FriendliAI's specialized hardware and models

### 🎯 Enhanced Accuracy
- **Better Classification**: More detailed and accurate image content classification
- **Improved OCR**: Enhanced text extraction from complex layouts and various fonts
- **Rich Metadata**: More comprehensive metadata with confidence scores and descriptions

### 🔧 Resource Optimization
- **Reduced Local Load**: Offloads processing to cloud infrastructure
- **Lower Memory Usage**: No need to load large models locally
- **Scalable Processing**: Handles multiple images efficiently

## Configuration

### 1. Environment Setup

Add your FriendliAI credentials to the `.env` file:

```bash
# FriendliAI Configuration (for AI acceleration)
FRIENDLI_TOKEN=your_friendli_token
FRIENDLI_TEAM_ID=your_team_id
FRIENDLI_ENDPOINT_ID=your_endpoint_id
```

### 2. Configuration File

Update your `config.yaml` to include AI acceleration settings:

```yaml
# AI Acceleration Configuration
ai_acceleration:
  enabled: false  # Enable/disable AI acceleration for image processing
  image_classification: true  # Use AI acceleration for image classification
  image_ocr: true  # Use AI acceleration for OCR text extraction
  friendli_ai:
    friendli_token: "${FRIENDLI_TOKEN}"
    friendli_team_id: "${FRIENDLI_TEAM_ID}"
    friendli_model:
      acceleration_type:
        - "image_classification"
        - "image_ocr"
      endpoint_url: "https://api.friendli.ai/dedicated"
      endpoint_id: "${FRIENDLI_ENDPOINT_ID}"
```

### 3. Frontend Settings

Enable AI acceleration through the Settings interface:

1. Open Settings (hamburger menu → Settings)
2. Navigate to the "AI Acceleration" tab
3. Enable the following options:
   - **Enable AI Acceleration**: Master toggle for the feature
   - **Enable Image Classification Acceleration**: Use AI for image classification
   - **Enable Image OCR Acceleration**: Use AI for OCR text extraction

## How It Works

### Processing Flow

1. **Image Upload**: User uploads an image through the web interface
2. **AI Acceleration Check**: System checks if AI acceleration is enabled and configured
3. **Parallel Processing**: If enabled, classification and OCR run simultaneously via FriendliAI
4. **Fallback Processing**: If AI acceleration fails, system falls back to standard PyTorch/EasyOCR
5. **Metadata Storage**: Results are stored in the vector database with enhanced metadata

### FriendliAI Integration

The system uses FriendliAI's chat completion API with structured prompts:

#### Image Classification Prompt
```
Analyze this image and provide a detailed classification.

Image filename: {filename}

Please provide the classification in the following JSON format:
{
    "classifications": [
        {
            "rank": 1,
            "label": "descriptive_label",
            "confidence": 0.95,
            "description": "brief_description"
        }
    ],
    "top_prediction": {
        "label": "best_label",
        "confidence": 0.95,
        "description": "best_description"
    },
    "content_type": "image_type",
    "contains_text": true/false,
    "text_confidence": 0.8
}

Focus on:
1. Main subject/content of the image
2. Whether the image contains readable text
3. Type of content (document, screenshot, photo, etc.)
4. Confidence levels for each classification
```

#### OCR Prompt
```
Extract all readable text from this image. Please provide the results in the following JSON format:

{
    "extracted_text": "all text found in the image",
    "text_blocks": [
        {
            "text": "text content",
            "confidence": 0.95,
            "bbox": [x1, y1, x2, y2]
        }
    ],
    "text_length": 150,
    "block_count": 5,
    "language": "en",
    "text_quality": "high/medium/low"
}

If no text is found, return:
{
    "extracted_text": "",
    "text_blocks": [],
    "text_length": 0,
    "block_count": 0,
    "language": "unknown",
    "text_quality": "none"
}

Focus on:
1. All readable text in the image
2. Text confidence levels
3. Text positioning (if possible)
4. Language detection
5. Overall text quality assessment
```

## Architecture

### Components

1. **FriendliAIClient** (`src/ragme/utils/friendli_client.py`)
   - HTTP client for FriendliAI API communication
   - Handles authentication and request formatting
   - Manages parallel processing of classification and OCR

2. **Enhanced ImageProcessor** (`src/ragme/utils/image_processor.py`)
   - Integrates FriendliAI acceleration with existing processing
   - Provides automatic fallback to standard processing
   - Maintains backward compatibility

3. **Configuration System**
   - Environment variable support for sensitive credentials
   - YAML configuration for feature flags and settings
   - Frontend integration for user control

4. **Frontend Integration**
   - Settings UI for enabling/disabling acceleration
   - Status monitoring and configuration display
   - Real-time feedback on acceleration status

### Error Handling

The system implements comprehensive error handling:

1. **Configuration Errors**: Graceful handling of missing or invalid configuration
2. **API Failures**: Automatic fallback to standard processing on API errors
3. **Timeout Handling**: Configurable timeouts with fallback processing
4. **Network Issues**: Robust handling of network connectivity problems

## Monitoring and Status

### Settings Interface

The AI Acceleration tab in Settings provides:

- **Configuration Status**: Shows whether FriendliAI is properly configured
- **Acceleration Types**: Displays enabled acceleration types
- **Endpoint Information**: Shows the configured model endpoint
- **Real-time Status**: Indicates if the service is available

### Status Indicators

- 🟢 **Configured**: All required configuration is present and valid
- 🔴 **Not Configured**: Missing required configuration parameters
- ⚠️ **Error Loading**: Unable to load configuration information

## Fallback Behavior

When AI acceleration is disabled or fails, the system automatically falls back to standard processing:

1. **PyTorch Classification**: Uses ResNet50 model for image classification
2. **EasyOCR Processing**: Uses EasyOCR or pytesseract for text extraction
3. **Metadata Preservation**: All existing metadata fields are maintained
4. **Error Transparency**: Processing errors are logged and reported

## Performance Comparison

### Standard Processing
- **Classification**: ~2-5 seconds per image
- **OCR**: ~3-8 seconds per image
- **Total Time**: ~5-13 seconds (sequential processing)
- **Resource Usage**: High local CPU/memory usage

### AI Acceleration
- **Classification**: ~1-3 seconds per image
- **OCR**: ~1-4 seconds per image
- **Total Time**: ~1-4 seconds (parallel processing)
- **Resource Usage**: Minimal local resource usage

## Troubleshooting

### Common Issues

1. **"FriendliAI not available"**
   - Check that FriendliAI client is properly imported
   - Verify Python environment and dependencies

2. **"Missing required FriendliAI configuration parameters"**
   - Ensure all environment variables are set in `.env`
   - Verify configuration in `config.yaml`

3. **"AI acceleration failed, falling back to standard processing"**
   - Check FriendliAI API credentials and endpoint
   - Verify network connectivity
   - Review API rate limits and quotas

4. **"Processing timeout"**
   - Increase timeout settings in configuration
   - Check FriendliAI service status
   - Verify endpoint URL and model availability

### Debug Mode

Enable debug logging to troubleshoot issues:

```yaml
logging:
  level: "DEBUG"
```

### API Testing

Test FriendliAI connectivity:

```python
from src.ragme.utils.friendli_client import FriendliAIClient

# Test configuration
config = {
    "friendli_token": "your_token",
    "friendli_team_id": "your_team_id",
    "friendli_model": {
        "acceleration_type": ["image_classification", "image_ocr"],
        "endpoint_url": "your_endpoint_url",
        "endpoint_id": "your_endpoint_id"
    }
}

client = FriendliAIClient(config)
# Test with sample image data
result = client.classify_image(b"sample_image_data", "test.jpg")
print(result)
```

## Security Considerations

1. **Credential Management**: Store sensitive credentials in environment variables
2. **API Security**: Use HTTPS endpoints and secure authentication
3. **Data Privacy**: Images are processed by FriendliAI - review their privacy policy
4. **Rate Limiting**: Implement appropriate rate limiting for API calls

## Future Enhancements

1. **Additional AI Providers**: Support for other AI acceleration providers
2. **Batch Processing**: Optimized batch processing for multiple images
3. **Custom Models**: Support for custom-trained models
4. **Advanced Analytics**: Detailed performance metrics and analytics
5. **Caching**: Intelligent caching of processed results

## Support

For issues with AI acceleration:

1. Check the troubleshooting section above
2. Review FriendliAI documentation and API status
3. Verify configuration and environment variables
4. Enable debug logging for detailed error information
5. Test with standard processing to isolate issues

The AI acceleration feature is designed to enhance existing functionality while maintaining full backward compatibility. If you encounter issues, the system will automatically fall back to standard processing to ensure continued operation.
