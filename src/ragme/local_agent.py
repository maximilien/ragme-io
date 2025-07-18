# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import json
import logging
import os
import time
import traceback
from pathlib import Path
from typing import Optional, Callable

import dotenv
import requests
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Load environment variables
dotenv.load_dotenv()

# Get MCP server URL from environment variables
RAGME_API_URL = os.getenv('RAGME_API_URL')
RAGME_MCP_URL = os.getenv('RAGME_MCP_URL')

class FileHandler(FileSystemEventHandler):
    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback
        self.supported_extensions = {'.pdf', '.docx'}

    def on_created(self, event):
        if not event.is_directory:
            file_path = Path(event.src_path)
            if file_path.suffix.lower() in self.supported_extensions:
                logging.info(f"New file detected: {file_path}")
                if self.callback:
                    self.callback(file_path)

    def on_modified(self, event):
        if not event.is_directory:
            file_path = Path(event.src_path)
            if file_path.suffix.lower() in self.supported_extensions:
                logging.info(f"File modified: {file_path}")
                if self.callback:
                    self.callback(file_path)

class DirectoryMonitor:
    def __init__(self, directory: str, callback: Optional[Callable] = None):
        self.directory = Path(directory)
        self.observer = Observer()
        self.handler = FileHandler(callback)

    def start(self):
        """Start monitoring the directory"""
        if not self.directory.exists():
            logging.error(f"Directory does not exist: {self.directory}")
            return

        logging.info(f"Starting to monitor directory: {self.directory}")
        self.observer.schedule(self.handler, str(self.directory), recursive=False)
        self.observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stop monitoring the directory"""
        self.observer.stop()
        self.observer.join()
        logging.info("Stopped monitoring directory")

class RagMeLocalAgent:
    """Local agent for processing files and adding them to RAG system"""
    
    def __init__(self, api_url: Optional[str] = None, mcp_url: Optional[str] = None):
        self.api_url = api_url or RAGME_API_URL
        self.mcp_url = mcp_url or RAGME_MCP_URL
        
        if not self.api_url:
            raise ValueError("RAGME_API_URL environment variable is required")
        if not self.mcp_url:
            raise ValueError("RAGME_MCP_URL environment variable is required")

    # private methods

    def _process_pdf_file(self, file_path: Path) -> bool:
        """Process a PDF file using the MCP server"""
        try:
            # Check if file exists and is a PDF
            if not file_path.exists() or file_path.suffix.lower() != '.pdf':
                logging.error(f"Invalid PDF file: {file_path}")
                return False

            # Prepare the file for upload
            with open(file_path, 'rb') as pdf_file:
                files = {'file': (file_path.name, pdf_file, 'application/pdf')}
                
                # Call the MCP server
                response = requests.post(
                    f'{self.mcp_url}/tool/process_pdf',
                    files=files
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(json.dumps(result, indent=2)) #DEBUG
                    if result['success']:
                        data = result['data']['data']
                        logging.info(f"Successfully processed PDF: {file_path}")
                        logging.info(f"Extracted {len(data['text'])} characters of text")
                        # Add to RAG
                        self.add_to_rag({"data": data, "metadata": result['data']['metadata']})
                        return True
                    else:
                        logging.error(f"Error processing PDF: {result.get('error', 'Unknown error')}")
                else:
                    logging.error(f"Server error: {response.status_code} - {response.text}")
                
                return False

        except Exception as e:
            print("Full traceback:")
            print(traceback.format_exc())
            logging.error(f"Error processing PDF file {file_path}: {str(e)}")
            return False

    def _process_docx_file(self, file_path: Path) -> bool:
        """Process a DOCX file using the MCP server"""
        try:
            # Check if file exists and is a DOCX
            if not file_path.exists() or file_path.suffix.lower() != '.docx':
                logging.error(f"Invalid DOCX file: {file_path}")
                return False

            # Prepare the file for upload
            with open(file_path, 'rb') as docx_file:
                files = {'file': (file_path.name, docx_file, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
                
                # Call the MCP server
                response = requests.post(
                    f'{self.mcp_url}/tool/process_docx',
                    files=files
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(json.dumps(result, indent=2)) #DEBUG
                    if result['success']:
                        data = result['data']['data']
                        logging.info(f"Successfully processed DOCX: {file_path}")
                        logging.info(f"Extracted {len(data['text'])} characters of text")
                        logging.info(f"Found {data['table_count']} tables")
                        # Add to RAG
                        self.add_to_rag({"data": data, "metadata": result['data']['metadata']})
                        return True
                    else:
                        logging.error(f"Error processing DOCX: {result.get('error', 'Unknown error')}")
                else:
                    logging.error(f"Server error: {response.status_code} - {response.text}")
                
                return False

        except Exception as e:
            print("Full traceback:")
            print(traceback.format_exc())
            logging.error(f"Error processing DOCX file {file_path}: {str(e)}")
            return False

    # public methods

    def process_file(self, file_path: Path):
        """Process detected files based on their type"""
        if file_path.suffix.lower() == '.pdf':
            self._process_pdf_file(file_path)
        elif file_path.suffix.lower() == '.docx':
            self._process_docx_file(file_path)
        else:
            logging.warning(f"Unsupported file type: {file_path}")
    
    def add_to_rag(self, data: dict) -> bool:
        """Add processed data to RAG system"""
        try:
            print(f"Adding to RAG: {json.dumps(data, indent=2)}")  # Pretty print error response
            # Wrap the data in a 'data' field as expected by the API
            response = requests.post(
                f'{self.api_url}/add-json',
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                print(json.dumps(result, indent=2)) #DEBUG
                if result.get('status') == 'success':
                    logging.info("Successfully added data to RAG")
                    return True
                else:
                    logging.error(f"Error adding to RAG: {result.get('error', 'Unknown error')}")
            else:
                logging.error(f"RAG server error: {response.status_code}")
                print(json.dumps(response.json(), indent=2))  # Pretty print error response
            
            return False
        except Exception as e:
            print("Full traceback:")
            print(traceback.format_exc())
            logging.error(f"Error adding to RAG: {str(e)}")
            return False

if __name__ == "__main__":
    # Example usage
    local_agent = RagMeLocalAgent()
    monitor = DirectoryMonitor(
        directory="./watch_directory",  # Directory to monitor
        callback=local_agent.process_file
    )
    monitor.start() 