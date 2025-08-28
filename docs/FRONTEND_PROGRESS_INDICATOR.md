# Frontend Progress Indicator

## Overview

The RAGme frontend includes a progress indicator that provides visual feedback during long-running operations like document and image processing. This enhances the user experience by clearly showing the current status of operations that may take several seconds to complete.

## Features

### Visual Progress Indicator
- **Spinning Wheel**: Animated spinner that appears next to the "Add Content" button
- **Progress Text**: Dynamic text that updates to show the current processing stage
- **Fixed Width**: Consistent 320px width prevents layout shifts during text changes
- **Text Truncation**: Long messages are gracefully truncated with ellipsis
- **Pulsing Animation**: Subtle background animation to draw attention
- **Automatic Hiding**: Disappears when processing is complete or on error

### Multi-Stage Progress Tracking
Different operations show different progress stages:

#### Document Processing
1. **Upload**: "Uploading X document(s)..."
2. **Text Extraction**: "Extracting text from X document(s)..."
3. **AI Analysis**: "Analyzing X document(s) with AI..."
4. **Complete**: Success notification

#### Image Processing
1. **Upload**: "Uploading X image(s)..."
2. **AI Classification**: "Analyzing X image(s) with AI classification..."
3. **OCR Processing**: "Extracting text from X image(s) with OCR..."
4. **Complete**: Success notification

#### URL Processing
- **Processing**: "Processing X URL(s)..."

#### JSON Processing
- **Processing**: "Processing JSON data..."

### Enhanced User Experience
- **Button Disabling**: The "Add Content" button is disabled during processing
- **Visual Feedback**: Button becomes grayed out and shows "not-allowed" cursor
- **Automatic Re-enabling**: Button is restored when processing completes
- **Timeout Protection**: 5-minute automatic timeout prevents stuck indicators

## Technical Implementation

### CSS Components
```css
.progress-indicator {
    display: none;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    background: rgba(102, 126, 234, 0.1);
    border: 1px solid rgba(102, 126, 234, 0.2);
    border-radius: 8px;
    animation: progressPulse 2s ease-in-out infinite;
    /* Fixed width to prevent layout shifts */
    width: 320px;
    min-width: 320px;
    max-width: 320px;
}

.progress-spinner {
    width: 16px;
    height: 16px;
    border: 2px solid rgba(102, 126, 234, 0.3);
    border-top: 2px solid #667eea;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

.progress-text {
    font-weight: 500;
    color: #667eea;
    /* Ensure text fits within the fixed width */
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    flex: 1;
}
```

### JavaScript Methods
```javascript
// Show progress indicator
showProgressIndicator(operation, text = null)

// Hide progress indicator
hideProgressIndicator()

// Update progress text
updateProgressText(text)

// Get current progress status
getProgressStatus()
```

### Integration Points
- **File Uploads**: `uploadFiles()` method
- **Image Uploads**: `uploadImages()` method
- **URL Processing**: Socket event handlers
- **JSON Processing**: Socket event handlers

## Usage

The progress indicator is automatically triggered when users:
1. Upload documents via the Files tab
2. Upload images via the Images tab
3. Add URLs via the URLs tab
4. Add JSON data via the JSON tab

No user action is required - the indicator appears automatically and provides real-time feedback throughout the processing pipeline.

## Error Handling

- **Automatic Hiding**: Progress indicator hides on any error
- **Timeout Protection**: 5-minute timeout prevents stuck indicators
- **Error Notifications**: Standard error notifications still appear
- **Button Restoration**: "Add Content" button is always re-enabled

## Configuration

The progress indicator behavior is built into the frontend and doesn't require configuration. However, the timeout duration can be adjusted in the JavaScript code if needed:

```javascript
// 5-minute timeout (300000ms)
setTimeout(() => {
    if (this.progressState.isProcessing && this.progressState.currentOperation === operation) {
        console.warn('Progress indicator timeout - hiding automatically');
        this.hideProgressIndicator();
        this.showNotification('Processing timeout - please try again', 'warning');
    }
}, 300000);
```

## Benefits

1. **Better UX**: Users know their operation is being processed
2. **Reduced Confusion**: Clear indication of multi-stage processing
3. **Professional Feel**: Modern UI with smooth animations
4. **Error Prevention**: Prevents multiple simultaneous uploads
5. **Accessibility**: Visual feedback for all users
