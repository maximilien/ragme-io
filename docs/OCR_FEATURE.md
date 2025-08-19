# OCR (Optical Character Recognition) Feature

## Overview

The OCR feature automatically extracts text from images that contain text content, such as:
- Screenshots of websites
- Photos of documents
- Slides and presentations
- Charts and diagrams
- Any image containing readable text

## Configuration

The OCR feature is configured in `config.yaml`:

```yaml
# Feature Flags
features:
  ocr_processing: true   # Enable OCR for images containing text

# OCR Configuration
ocr:
  enabled: true
  engine: "easyocr"  # Options: easyocr, pytesseract
  languages: ["en"]  # Language codes for OCR processing
  confidence_threshold: 0.5  # Minimum confidence score for text detection
  preprocessing:
    enabled: true
    denoise: true
    deskew: true
    contrast_enhancement: true
  text_detection:
    enabled: true
    min_text_size: 10  # Minimum text size in pixels
    max_text_size: 1000  # Maximum text size in pixels
  content_types:
    - "website"
    - "document"
    - "slide"
    - "screenshot"
    - "text"
    - "chart"
    - "diagram"
```

## How It Works

1. **Image Classification**: When an image is uploaded, it's first classified using PyTorch/ResNet50
2. **OCR Decision**: Based on the classification results, the system determines if OCR should be applied
3. **Image Preprocessing**: If OCR is needed, the image is preprocessed for better text extraction:
   - Denoising to remove image noise
   - Deskewing to correct rotated text
   - Contrast enhancement for better readability
4. **Text Extraction**: OCR engine extracts text with confidence scores
5. **Metadata Storage**: Extracted text is stored in the `ocr_content` field of image metadata

## OCR Engines

### EasyOCR (Default)
- **Pros**: High accuracy, supports multiple languages, good at handling various text styles
- **Cons**: Slower processing, larger memory footprint
- **Best for**: Production use, multi-language support

### pytesseract
- **Pros**: Faster processing, smaller memory footprint
- **Cons**: Lower accuracy on complex layouts, limited language support
- **Best for**: Simple text extraction, resource-constrained environments

## API Endpoints

### Upload Images with OCR
```
POST /upload-images
```
Images uploaded through this endpoint automatically have OCR applied if the content type suggests text presence.

### Test OCR Functionality
```
POST /test-ocr
```
Test OCR on a single image file and get detailed results.

## Example Usage

### Python Client
```python
import requests

# Upload image with OCR
with open('screenshot.png', 'rb') as f:
    files = {'files': ('screenshot.png', f, 'image/png')}
    response = requests.post('http://localhost:8021/upload-images', files=files)
    result = response.json()
    print(f"Processed {result['files_processed']} images")

# Test OCR specifically
with open('document.png', 'rb') as f:
    files = {'file': ('document.png', f, 'image/png')}
    response = requests.post('http://localhost:8021/test-ocr', files=files)
    result = response.json()
    
    ocr_result = result['ocr_result']
    if ocr_result['ocr_processing']:
        print(f"Extracted text: {ocr_result['extracted_text']}")
        print(f"Text blocks: {ocr_result['block_count']}")
```

### cURL
```bash
# Upload image with OCR
curl -X POST http://localhost:8021/upload-images \
  -F "files=@screenshot.png"

# Test OCR
curl -X POST http://localhost:8021/test-ocr \
  -F "file=@document.png"
```

## Metadata Structure

When OCR is applied, the image metadata includes:

```json
{
  "ocr_content": {
    "type": "ocr_extraction",
    "engine": "easyocr",
    "confidence_threshold": 0.5,
    "extracted_text": "The actual text content...",
    "text_blocks": [
      {
        "text": "Text block 1",
        "confidence": 0.95,
        "bbox": [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
      }
    ],
    "text_length": 150,
    "block_count": 3,
    "ocr_processing": true
  }
}
```

## Dependencies

Install OCR dependencies:
```bash
pip install easyocr pytesseract opencv-python Pillow
```

For pytesseract, you also need to install Tesseract OCR:
- **Ubuntu/Debian**: `sudo apt-get install tesseract-ocr`
- **macOS**: `brew install tesseract`
- **Windows**: Download from https://github.com/UB-Mannheim/tesseract/wiki

## Testing

Run the OCR test script:
```bash
python test_ocr_functionality.py
```

This will test OCR functionality using the example image at `tests/fixtures/images/ragme_screen.png`.

## Troubleshooting

### OCR Not Working
1. Check if dependencies are installed: `pip list | grep -E "(easyocr|pytesseract|opencv)"`
2. Verify OCR is enabled in config: `features.ocr_processing: true`
3. Check logs for OCR-related errors

### Low OCR Accuracy
1. Adjust confidence threshold in config
2. Enable preprocessing options (denoise, deskew, contrast_enhancement)
3. Try different OCR engine (easyocr vs pytesseract)
4. Ensure image quality is sufficient

### Performance Issues
1. Use pytesseract for faster processing
2. Disable preprocessing if not needed
3. Adjust text detection size limits
4. Consider using GPU acceleration for EasyOCR

## Future Enhancements

- Support for more OCR engines (Azure Computer Vision, Google Vision API)
- Automatic language detection
- Layout analysis for complex documents
- Table structure recognition
- Handwriting recognition
- Real-time OCR for video streams
