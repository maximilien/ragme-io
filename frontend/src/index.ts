import express from 'express';
import { createServer } from 'http';
import { Server } from 'socket.io';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import path from 'path';
import multer from 'multer';
import FormData from 'form-data';

const app = express();
const server = createServer(app);
const io = new Server(server, {
  cors: {
    origin: '*',
    methods: ['GET', 'POST'],
  },
});

const PORT = process.env.PORT || 3020;
const RAGME_API_URL = process.env.RAGME_API_URL || 'http://localhost:8000';

// Configure multer for file uploads
const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 50 * 1024 * 1024, // 50MB limit
  },
});

// Logger function to replace console statements
const logger = {
  info: (message: string, ...args: unknown[]): void => {
    if (process.env.NODE_ENV !== 'production') {
      console.log(message, ...args);
    }
  },
  error: (message: string, ...args: unknown[]): void => {
    if (process.env.NODE_ENV !== 'production') {
      console.error(message, ...args);
    }
  },
  warn: (message: string, ...args: unknown[]): void => {
    if (process.env.NODE_ENV !== 'production') {
      console.warn(message, ...args);
    }
  },
};

// Type definitions for better type safety
interface TableData {
  headers: string[];
  rows: string[][];
  caption?: string;
}

interface DocumentMetadata {
  type: string;
  filename: string;
  date_added: string;
  page_count?: number;
  paragraph_count?: number;
  table_count?: number;
  [key: string]: unknown; // Allow additional metadata properties
}

interface MCPResponse {
  success: boolean;
  data?: {
    data: {
      filename: string;
      text: string;
      page_count?: number;
      tables?: TableData[];
      paragraph_count?: number;
      table_count?: number;
    };
    metadata?: DocumentMetadata;
  };
  error?: string;
}

// Middleware
app.use(
  helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        connectSrc: ["'self'", 'http://localhost:8021', 'ws://localhost:8021'],
        scriptSrc: ["'self'", "'unsafe-inline'"],
        styleSrc: ["'self'", "'unsafe-inline'"],
        imgSrc: ["'self'", 'data:', 'https:'],
        fontSrc: ["'self'", 'https:'],
      },
    },
  })
);
app.use(compression());
app.use(cors());
app.use(express.json());

app.use(express.static(path.join(process.cwd(), 'public')));

// Serve the main HTML file
app.get('/', (req, res) => {
  res.sendFile(path.join(process.cwd(), 'public/index.html'));
});

// Type definitions for API responses
interface Document {
  id: string;
  title: string;
  content: string;
  metadata?: DocumentMetadata;
  created_at: string;
  updated_at: string;
}

interface PaginationInfo {
  limit: number;
  offset: number;
  count: number;
}

interface APIResponse {
  status: string;
  message?: string;
  response?: string;
  summary?: string;
  document_id?: string;
  urls_processed?: number;
  files_processed?: number;
  documents?: Document[];
  pagination?: PaginationInfo;
}

// Function to call RAGme API
async function callRAGmeAPI(
  endpoint: string,
  data?: Record<string, unknown> | FormData,
  queryParams?: string,
  isFormData?: boolean,
  method?: string
): Promise<APIResponse | null> {
  try {
    let url = `${RAGME_API_URL}${endpoint}`;
    if (queryParams) {
      url += queryParams;
    }

    const options: RequestInit = {
      method: method || (data ? 'POST' : 'GET'),
    };

    if (data) {
      if (isFormData && data instanceof FormData) {
        // For FormData, don't set Content-Type header - let FormData set it with boundary
        options.body = data;
        // Set the headers from FormData
        const headers = data.getHeaders ? data.getHeaders() : {};
        options.headers = headers;
      } else {
        options.headers = {
          'Content-Type': 'application/json',
        };
        options.body = JSON.stringify(data);
      }
    }

    const response = await fetch(url, options);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result = (await response.json()) as APIResponse;
    return result;
  } catch (error) {
    logger.error(`Error calling RAGme API (${endpoint}):`, error);
    return null;
  }
}

// Function to chunk text into smaller pieces
function chunkText(text: string, maxChunkSize: number): string[] {
  const chunks: string[] = [];
  const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 0);

  let currentChunk = '';

  for (const sentence of sentences) {
    const sentenceWithPunctuation = sentence.trim() + '. ';

    if (currentChunk.length + sentenceWithPunctuation.length > maxChunkSize) {
      if (currentChunk.trim()) {
        chunks.push(currentChunk.trim());
      }
      currentChunk = sentenceWithPunctuation;
    } else {
      currentChunk += sentenceWithPunctuation;
    }
  }

  if (currentChunk.trim()) {
    chunks.push(currentChunk.trim());
  }

  // If no chunks were created (single sentence), return the original text
  if (chunks.length === 0) {
    chunks.push(text);
  }

  return chunks;
}

// File upload endpoint
app.post('/upload-files', upload.array('files'), async (req, res) => {
  try {
    const files = req.files as Express.Multer.File[];

    if (!files || files.length === 0) {
      return res.status(400).json({
        status: 'error',
        message: 'No files uploaded',
      });
    }

    // Process files directly and add to RAG system
    let processed_count = 0;

    for (const file of files) {
      try {
        // Determine file type and extract text
        const filename = file.originalname.toLowerCase();
        let text_content = '';
        let metadata = {
          type: filename.split('.').pop() || 'unknown',
          filename: file.originalname,
          date_added: new Date().toISOString(),
        };

        if (filename.endsWith('.pdf')) {
          // Use MCP server to process PDF files
          logger.info(`Sending PDF to MCP server: ${file.originalname}`);

          // Convert buffer to base64 and send as JSON
          const base64Data = file.buffer.toString('base64');
          const mcpResponse = await fetch('http://localhost:8022/tool/process_pdf_base64', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              filename: file.originalname,
              content: base64Data,
              content_type: file.mimetype,
            }),
          });

          logger.info(`MCP response status: ${mcpResponse.status}`);
          if (mcpResponse.ok) {
            const mcpResult = (await mcpResponse.json()) as MCPResponse;
            logger.info(`MCP result:`, mcpResult);
            if (mcpResult.success && mcpResult.data) {
              text_content = mcpResult.data.data.text;
              // Merge MCP metadata with our metadata
              if (mcpResult.data.metadata) {
                metadata = { ...metadata, ...mcpResult.data.metadata };
              }
            } else {
              logger.error(`MCP PDF processing failed for ${file.originalname}:`, mcpResult.error);
              continue;
            }
          } else {
            const errorText = await mcpResponse.text();
            logger.error(
              `MCP PDF processing failed for ${file.originalname}:`,
              mcpResponse.status,
              errorText
            );
            continue;
          }
        } else if (filename.endsWith('.docx')) {
          // Use MCP server to process DOCX files
          logger.info(`Sending DOCX to MCP server: ${file.originalname}`);

          // Convert buffer to base64 and send as JSON
          const base64Data = file.buffer.toString('base64');
          const mcpResponse = await fetch('http://localhost:8022/tool/process_docx_base64', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              filename: file.originalname,
              content: base64Data,
              content_type: file.mimetype,
            }),
          });

          logger.info(`MCP response status: ${mcpResponse.status}`);
          if (mcpResponse.ok) {
            const mcpResult = (await mcpResponse.json()) as MCPResponse;
            logger.info(`MCP result:`, mcpResult);
            if (mcpResult.success && mcpResult.data) {
              text_content = mcpResult.data.data.text;
              // Merge MCP metadata with our metadata
              if (mcpResult.data.metadata) {
                metadata = { ...metadata, ...mcpResult.data.metadata };
              }
            } else {
              logger.error(`MCP DOCX processing failed for ${file.originalname}:`, mcpResult.error);
              continue;
            }
          } else {
            const errorText = await mcpResponse.text();
            logger.error(
              `MCP DOCX processing failed for ${file.originalname}:`,
              mcpResponse.status,
              errorText
            );
            continue;
          }
        } else if (filename.endsWith('.txt') || filename.endsWith('.md')) {
          // Handle text files
          text_content = file.buffer.toString('utf-8');
        } else if (filename.endsWith('.json')) {
          // Handle JSON files
          const jsonData = JSON.parse(file.buffer.toString('utf-8'));
          text_content = JSON.stringify(jsonData, null, 2);
        } else if (filename.endsWith('.csv')) {
          // Handle CSV files
          text_content = file.buffer.toString('utf-8');
        } else {
          // Try to decode as text for unknown file types
          text_content = file.buffer.toString('utf-8');
        }

        if (text_content.trim()) {
          // Chunk large text content to avoid token limit issues
          const chunks = chunkText(text_content, 1000); // Much smaller chunk size to avoid token limits

          if (chunks.length === 1) {
            // Single chunk - send as regular document
            const document = {
              text: chunks[0],
              url: `file://${file.originalname}`,
              metadata: metadata,
            };

            logger.info(`Adding single document to RAG system for file: ${file.originalname}`);

            const apiResult = await callRAGmeAPI('/add-json', {
              data: {
                documents: [document],
              },
            });

            if (apiResult && apiResult.status === 'success') {
              processed_count += 1;
            }
          } else {
            // Multiple chunks - create a single document with all chunks
            const combinedText = chunks.join('\n\n--- Chunk ---\n\n');
            const chunkedMetadata = {
              ...metadata,
              total_chunks: chunks.length,
              is_chunked: true,
              chunk_sizes: chunks.map(chunk => chunk.length),
              original_filename: file.originalname,
            };

            const document = {
              text: combinedText,
              url: `file://${file.originalname}`,
              metadata: chunkedMetadata,
            };

            logger.info(
              `Adding chunked document (${chunks.length} chunks) to RAG system for file: ${file.originalname}`
            );

            const apiResult = await callRAGmeAPI('/add-json', {
              data: {
                documents: [document],
              },
            });

            if (apiResult && apiResult.status === 'success') {
              processed_count += 1; // Count as one document, not multiple chunks
            }
          }
        }
      } catch (error) {
        logger.error(`Error processing file ${file.originalname}:`, error);
        continue;
      }
    }

    if (processed_count > 0) {
      res.json({
        status: 'success',
        message: `Successfully uploaded ${processed_count} files.`,
        files_processed: processed_count,
      });
    } else {
      res.status(500).json({
        status: 'error',
        message: 'Failed to upload files',
      });
    }
  } catch (error) {
    logger.error('File upload error:', error);
    res.status(500).json({
      status: 'error',
      message: 'File upload failed',
    });
  }
});

// Delete document endpoint
app.delete('/delete-document/:documentId', async (req, res) => {
  try {
    const { documentId } = req.params;

    const apiResult = await callRAGmeAPI(
      `/delete-document/${documentId}`,
      undefined,
      undefined,
      false,
      'DELETE'
    );

    if (apiResult) {
      res.json(apiResult);
    } else {
      res.status(500).json({
        status: 'error',
        message: 'Failed to delete document',
      });
    }
  } catch (error) {
    logger.error('Delete document error:', error);
    res.status(500).json({
      status: 'error',
      message: 'Failed to delete document',
    });
  }
});

// WebSocket connection handling
io.on('connection', socket => {
  logger.info('User connected:', socket.id);

  // Handle chat messages
  socket.on('chat_message', async data => {
    logger.info('Received message:', data);

    // Call RAGme API to process the query
    const apiResult = await callRAGmeAPI('/query', { query: data.content });
    logger.info('RAGme API result:', apiResult);

    let responseContent = '';

    if (apiResult && apiResult.status === 'success') {
      responseContent = apiResult.response || 'No response content available.';
    } else {
      responseContent = 'Sorry, I encountered an error processing your request. Please try again.';
    }

    const response = {
      id: Date.now().toString(),
      type: 'ai',
      content: responseContent,
      timestamp: new Date().toISOString(),
    };

    socket.emit('chat_response', response);
  });

  // Handle URL addition
  socket.on('add_urls', async data => {
    logger.info('Adding URLs:', data);

    const apiResult = await callRAGmeAPI('/add-urls', { urls: data.urls });

    if (apiResult && apiResult.status === 'success') {
      socket.emit('urls_added', {
        success: true,
        message: apiResult.message || 'URLs added successfully',
        urls_processed: apiResult.urls_processed || 0,
      });
    } else {
      socket.emit('urls_added', {
        success: false,
        message: 'Failed to add URLs. Please try again.',
      });
    }
  });

  // Handle JSON addition
  socket.on('add_json', async data => {
    logger.info('Adding JSON:', data);

    const apiResult = await callRAGmeAPI('/add-json', {
      data: data.jsonData,
      metadata: data.metadata,
    });

    if (apiResult && apiResult.status === 'success') {
      socket.emit('json_added', {
        success: true,
        message: apiResult.message || 'JSON data added successfully',
      });
    } else {
      socket.emit('json_added', {
        success: false,
        message: 'Failed to add JSON data. Please try again.',
      });
    }
  });

  // Handle document listing
  socket.on('list_documents', async data => {
    logger.info('Listing documents:', data);

    const limit = data.limit || 10;
    const offset = data.offset || 0;
    const dateFilter = data.dateFilter || 'all';

    const apiResult = await callRAGmeAPI(
      `/list-documents?limit=${limit}&offset=${offset}&date_filter=${dateFilter}`
    );

    if (apiResult && apiResult.status === 'success') {
      socket.emit('documents_listed', {
        success: true,
        documents: apiResult.documents || [],
        pagination: apiResult.pagination || { limit: 0, offset: 0, count: 0 },
      });
    } else {
      socket.emit('documents_listed', {
        success: false,
        message: 'Failed to list documents. Please try again.',
      });
    }
  });

  // Handle vector database info request
  socket.on('get_vector_db_info', async () => {
    logger.info('Getting vector database info...');

    try {
      // Get vector DB info from environment variables or use defaults
      const vectorDbInfo = {
        dbType: process.env.VECTOR_DB_TYPE || 'weaviate-local',
        collectionName: process.env.COLLECTION_NAME || 'RagMeDocs',
      };

      socket.emit('vector_db_info', {
        success: true,
        info: vectorDbInfo,
      });
    } catch (error) {
      logger.error('Error getting vector DB info:', error);
      socket.emit('vector_db_info', {
        success: false,
        message: 'Failed to get vector database information.',
      });
    }
  });

  // Handle document summarization
  socket.on('summarize_document', async data => {
    logger.info('Summarizing document:', data);

    const apiResult = await callRAGmeAPI('/summarize-document', { document_id: data.documentId });

    if (apiResult && apiResult.status === 'success') {
      socket.emit('document_summarized', {
        success: true,
        summary: apiResult.summary,
        documentId: data.documentId,
      });
    } else {
      socket.emit('document_summarized', {
        success: false,
        message: 'Failed to summarize document. Please try again.',
      });
    }
  });

  // Handle new chat creation
  socket.on('new_chat', () => {
    logger.info('New chat requested');
    socket.emit('chat_cleared');
  });

  // Handle chat save
  socket.on('save_chat', chatData => {
    logger.info('Chat save requested:', chatData);
    // In a real app, this would save to a database
    socket.emit('chat_saved', { success: true, message: 'Chat saved successfully' });
  });

  socket.on('disconnect', () => {
    logger.info('User disconnected:', socket.id);
  });
});

server.listen(PORT, () => {
  logger.info(`🤖 RAGme.ai Assistant Frontend running on port ${PORT}`);
  logger.info(`Open http://localhost:${PORT} in your browser`);
  logger.info(`RAGme API: http://localhost:8021`);
});
