# 🤖 RAGme.io Assistant Frontend

A modern, responsive web interface for the RAGme.io Assistant, built with TypeScript, Express, Socket.IO, and D3.js.

## Features

- **Three-pane layout** with resizable and collapsible sidebars
- **Real-time chat** with markdown support and copy functionality
- **Document management** with visual D3.js charts
- **Content addition** via URLs or JSON data
- **Modern UI** with smooth animations and responsive design
- **WebSocket communication** for real-time updates

## Architecture

- **Backend**: Express.js server with Socket.IO for real-time communication
- **Frontend**: Vanilla JavaScript with modern ES6+ features
- **Styling**: CSS3 with gradients, animations, and responsive design
- **Visualization**: D3.js for document charts and analytics
- **Markdown**: Marked.js for parsing and DOMPurify for sanitization

## Setup

### Prerequisites

- Node.js 18+ 
- npm or yarn
- RAGme.io backend running on port 8021

### Installation

1. Install dependencies:
```bash
npm install
```

2. Build the TypeScript code:
```bash
npm run build
```

3. Start the development server:
```bash
npm run dev
```

4. For production:
```bash
npm run build
npm start
```

## Development

### Available Scripts

- `npm run dev` - Start development server with hot reload
- `npm run build` - Build TypeScript to JavaScript
- `npm run watch` - Watch for changes and rebuild
- `npm run lint` - Run ESLint
- `npm run format` - Format code with Prettier

### Project Structure

```
frontend/
├── src/
│   └── index.ts          # Main server file
├── public/
│   ├── index.html        # Main HTML file
│   ├── styles.css        # CSS styles
│   └── app.js           # Frontend JavaScript
├── package.json
├── tsconfig.json
└── README.md
```

## API Integration

The frontend communicates with the RAGme.io backend API via WebSocket events:

### Chat Events
- `chat_message` - Send user message
- `chat_response` - Receive AI response

### Document Events
- `list_documents` - Request document list
- `documents_listed` - Receive document list

### Content Events
- `add_urls` - Add URLs to knowledge base
- `add_json` - Add JSON data to knowledge base
- `urls_added` / `json_added` - Confirmation of content addition

## UI Components

### Three-Pane Layout
1. **Left Sidebar**: Chat history (collapsible)
2. **Center**: Main chat area with input
3. **Right Sidebar**: Recent documents with visualization (resizable)

### Key Features
- **Responsive design** that works on desktop and mobile
- **Resizable dividers** for customizing layout
- **Collapsible sidebars** for more screen space
- **Real-time updates** via WebSocket
- **Markdown rendering** with syntax highlighting
- **Copy functionality** for AI responses
- **Document visualization** with D3.js charts

## Configuration

The frontend runs on port 3020 by default and connects to the RAGme.io API on `http://localhost:8021` by default. To change these, set the `RAGME_FRONTEND_PORT` and `RAGME_API_URL` environment variables, or modify the constants in `src/index.ts`.

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License - see the main project LICENSE file for details. 