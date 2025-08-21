# 🌍 Language Configuration

RAGme now supports configurable language settings to ensure consistent agent responses and improve user experience across different locales.

## 🎯 Problem Solved

Previously, the LLM agents could switch to different languages based on user input, which could be confusing and inconsistent. This feature ensures that:

- **Consistent Language**: Agents always respond in the configured language
- **Configurable**: Users can set their preferred language
- **Flexible**: Support for both forced English and custom language settings

## ⚙️ Configuration Options

### LLM Language Settings

Add these settings to your `config.yaml` file under the `llm` section:

```yaml
llm:
  # Default LLM settings
  default_model: "gpt-4o-mini"
  temperature: 0.7
  max_tokens: 4000
  
  # Language settings
  language: "en"  # Default language for agent responses (en, fr, es, de, etc.)
  force_english: true  # Force agents to always respond in English regardless of user's language
```

### Frontend Speech Recognition

Configure speech recognition language in the `frontend.settings` section:

```yaml
frontend:
  settings:
    max_documents: 10
    auto_refresh: true
    refresh_interval_ms: 30000
    max_tokens: 4000
    temperature: 0.7
    speech_language: "en-US"  # Language for speech recognition (en-US, fr-FR, es-ES, etc.)
```

## 🔧 How It Works

### Agent Language Control

The language configuration affects all three main agents:

1. **RagMeAgent** (Dispatcher): Routes queries and enforces language rules
2. **FunctionalAgent**: Handles operations and enforces language rules
3. **QueryAgent**: Answers content questions and enforces language rules

### Language Instruction Generation

The system automatically generates appropriate language instructions based on your configuration:

- **`force_english: true`**: Adds instruction to always respond in English
- **`force_english: false` + `language: "fr"`**: Adds instruction to always respond in French
- **`force_english: false` + `language: "en"`**: No additional language instruction (default behavior)

### Example Language Instructions

```python
# When force_english: true
language_instruction = "\nIMPORTANT: You MUST ALWAYS respond in English, regardless of the language used in the user's query. This is a critical requirement.\n"

# When force_english: false and language: "fr"
language_instruction = "\nIMPORTANT: You MUST ALWAYS respond in fr, regardless of the language used in the user's query. This is a critical requirement.\n"
```

## 🌐 Supported Languages

### Agent Response Languages

The `language` setting supports standard language codes:

- `"en"` - English (default)
- `"fr"` - French
- `"es"` - Spanish
- `"de"` - German
- `"it"` - Italian
- `"pt"` - Portuguese
- `"ja"` - Japanese
- `"ko"` - Korean
- `"zh"` - Chinese
- And any other language code supported by the LLM

### Speech Recognition Languages

The `speech_language` setting supports browser speech recognition language codes:

- `"en-US"` - English (US)
- `"en-GB"` - English (UK)
- `"fr-FR"` - French (France)
- `"es-ES"` - Spanish (Spain)
- `"de-DE"` - German (Germany)
- `"it-IT"` - Italian (Italy)
- `"pt-BR"` - Portuguese (Brazil)
- `"ja-JP"` - Japanese (Japan)
- `"ko-KR"` - Korean (Korea)
- `"zh-CN"` - Chinese (China)

## 📝 Usage Examples

### Force English Responses

```yaml
llm:
  force_english: true
  language: "en"
```

**Result**: All agents will always respond in English, regardless of user input language.

### Custom Language Responses

```yaml
llm:
  force_english: false
  language: "fr"
```

**Result**: All agents will always respond in French, regardless of user input language.

### Default Behavior (No Language Enforcement)

```yaml
llm:
  force_english: false
  language: "en"
```

**Result**: Agents may respond in the same language as the user's query.

### Speech Recognition in French

```yaml
frontend:
  settings:
    speech_language: "fr-FR"
```

**Result**: Voice input will be processed in French.

## 🧪 Testing

Run the language configuration tests:

```bash
python -m pytest tests/test_language_configuration.py -v
```

## 🔄 Migration Guide

### From Previous Versions

If you're upgrading from a previous version:

1. **No Breaking Changes**: Existing configurations will continue to work
2. **Default Behavior**: If no language settings are specified, `force_english: true` is used by default
3. **Gradual Migration**: You can add language settings at any time

### Recommended Configuration

For most users, we recommend:

```yaml
llm:
  force_english: true  # Ensures consistent English responses
  language: "en"       # Default language

frontend:
  settings:
    speech_language: "en-US"  # Match your browser's language
```

## 🐛 Troubleshooting

### Agent Still Responding in Different Languages

1. **Check Configuration**: Ensure `force_english: true` is set in your `config.yaml`
2. **Restart Services**: Restart the backend after changing configuration
3. **Clear Cache**: Clear browser cache if using the frontend

### Speech Recognition Not Working

1. **Browser Support**: Ensure your browser supports the specified language
2. **Permissions**: Check microphone permissions
3. **Language Code**: Verify the language code format (e.g., `"en-US"` not `"en"`)

### Configuration Not Loading

1. **File Location**: Ensure `config.yaml` is in the project root directory
2. **YAML Syntax**: Check for YAML syntax errors
3. **Permissions**: Ensure the file is readable by the application

## 📚 Related Documentation

- [Configuration Guide](CONFIG.md) - Complete configuration reference
- [Agent Architecture](AGENT_REFACTOR.md) - Understanding the agent system
- [Frontend Configuration](SETTINGS_UI_IMPROVEMENTS.md) - Frontend customization options
