# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import os
import signal
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .processor import DocumentProcessor
from .report_generator import ReportGenerator


class DocumentProcessingPipeline:
    """
    Main document processing pipeline for RAGme.
    Orchestrates parallel processing of documents and images with progress tracking,
    error handling, and comprehensive reporting.
    """

    def __init__(self, input_directory: str, batch_size: int = 3, retry_limit: int = 3, verbose: bool = False):
        """
        Initialize the document processing pipeline.

        Args:
            input_directory: Directory containing files to process
            batch_size: Number of parallel processing workers
            retry_limit: Maximum number of retry attempts per file
            verbose: Enable verbose progress reporting
        """
        self.input_directory = Path(input_directory)
        self.batch_size = batch_size
        self.retry_limit = retry_limit
        self.verbose = verbose
        
        if not self.input_directory.exists():
            raise ValueError(f"Input directory does not exist: {input_directory}")
        
        # Initialize components
        self.processor = DocumentProcessor(batch_size=batch_size, retry_limit=retry_limit)
        self.report_generator = ReportGenerator(str(self.input_directory))
        
        # Track processing state
        self.processed_files = []
        self.failed_files = []
        self.skipped_files = []
        self.results = []
        
        # Lock files for parallel processing coordination
        self.lock_files = set()
        
        # Setup signal handlers for cleanup
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle interruption signals for cleanup."""
        print(f"\n🚨 Received signal {signum}, cleaning up...")
        self._cleanup_lock_files()
        self.processor.cleanup()
        print("✅ Cleanup completed. Exiting.")
        exit(0)

    def discover_files(self) -> Tuple[List[str], List[str]]:
        """
        Discover files to process in the input directory.

        Returns:
            Tuple of (files_to_process, already_processed_files)
        """
        all_files = []
        processed_files = []
        
        # Find all supported files
        for file_path in self.input_directory.iterdir():
            if file_path.is_file() and self.processor.is_supported_file(str(file_path)):
                file_str = str(file_path)
                processed_file_path = file_str + ".processed"
                
                if os.path.exists(processed_file_path):
                    processed_files.append(file_str)
                else:
                    all_files.append(file_str)
        
        return all_files, processed_files

    def _create_lock_file(self, file_path: str) -> bool:
        """
        Create a lock file to prevent concurrent processing.

        Args:
            file_path: Path to the file being processed

        Returns:
            True if lock was created successfully, False if already locked
        """
        lock_path = file_path + ".lock"
        
        try:
            # Try to create lock file exclusively
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"Locked at {time.time()}".encode())
            os.close(fd)
            
            self.lock_files.add(lock_path)
            return True
            
        except FileExistsError:
            return False
        except Exception as e:
            print(f"Warning: Could not create lock file for {file_path}: {e}")
            return True  # Proceed without locking

    def _remove_lock_file(self, file_path: str):
        """Remove lock file after processing."""
        lock_path = file_path + ".lock"
        
        try:
            if os.path.exists(lock_path):
                os.unlink(lock_path)
                self.lock_files.discard(lock_path)
        except Exception as e:
            print(f"Warning: Could not remove lock file {lock_path}: {e}")

    def _cleanup_lock_files(self):
        """Clean up all lock files created by this instance."""
        for lock_path in list(self.lock_files):
            try:
                if os.path.exists(lock_path):
                    os.unlink(lock_path)
            except Exception:
                pass  # Ignore cleanup errors
        self.lock_files.clear()

    def _process_single_file(self, file_path: str) -> Dict[str, Any]:
        """
        Process a single file with locking and error handling.

        Args:
            file_path: Path to the file to process

        Returns:
            Processing results dictionary
        """
        # Create lock file
        if not self._create_lock_file(file_path):
            return {
                "file_name": Path(file_path).name,
                "file_path": file_path,
                "errors": ["File is locked by another process"],
                "success": False,
                "skipped": True,
            }
        
        try:
            # Process the file
            if self.verbose:
                print(f"🔄 Processing {Path(file_path).name}...")
            
            result = self.processor.process_file_with_retry(file_path, self.retry_limit)
            
            # Create .processed file
            self.report_generator.create_processed_file(file_path, result)
            
            # Status reporting
            if self.verbose:
                if result.get('success', False):
                    file_type_emoji = "📄" if result.get('file_type') == 'document' else "🖼️"
                    processing_time = result.get('timing', {}).get('total', 0)
                    
                    if result.get('file_type') == 'document':
                        chunks = result.get('chunk_count', 0)
                        extracted_imgs = len(result.get('extracted_images', []))
                        print(f"✅ {file_type_emoji} {Path(file_path).name} - {chunks} chunks, {extracted_imgs} images ({processing_time:.2f}s)")
                    else:
                        ocr_text = result.get('ocr_text_length', 0)
                        ai_features = result.get('ai_classification_features', 0)
                        print(f"✅ {file_type_emoji} {Path(file_path).name} - {ai_features} AI features, {ocr_text} OCR chars ({processing_time:.2f}s)")
                else:
                    error_count = len(result.get('errors', []))
                    retry_count = result.get('retry_count', 0)
                    print(f"❌ {Path(file_path).name} - {error_count} errors, {retry_count} retries")
            
            return result
            
        except Exception as e:
            print(f"❌ Unexpected error processing {Path(file_path).name}: {e}")
            return {
                "file_name": Path(file_path).name,
                "file_path": file_path,
                "file_type": self.processor.get_file_type(file_path) or "unknown",
                "errors": [f"Unexpected error: {str(e)}"],
                "success": False,
                "retry_count": 0,
            }
            
        finally:
            # Always remove lock file
            self._remove_lock_file(file_path)

    def process_files_parallel(self, files_to_process: List[str]) -> List[Dict[str, Any]]:
        """
        Process files in parallel using thread pool.

        Args:
            files_to_process: List of file paths to process

        Returns:
            List of processing results
        """
        if not files_to_process:
            return []
        
        if self.verbose:
            print(f"🚀 Starting parallel processing with {self.batch_size} workers...")
        
        results = []
        
        # Use ThreadPoolExecutor for I/O bound operations
        # ProcessPoolExecutor would be better for CPU-bound, but requires more complex setup
        with ThreadPoolExecutor(max_workers=self.batch_size) as executor:
            # Submit all jobs
            future_to_file = {
                executor.submit(self._process_single_file, file_path): file_path
                for file_path in files_to_process
            }
            
            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                
                try:
                    result = future.result()
                    results.append(result)
                    completed += 1
                    
                    if not self.verbose:
                        # Show progress for non-verbose mode
                        print(f"📊 Progress: {completed}/{len(files_to_process)} files processed", end='\r')
                        
                except Exception as e:
                    print(f"❌ Error in worker processing {Path(file_path).name}: {e}")
                    results.append({
                        "file_name": Path(file_path).name,
                        "file_path": file_path,
                        "file_type": "unknown",
                        "errors": [f"Worker error: {str(e)}"],
                        "success": False,
                        "retry_count": 0,
                    })
                    completed += 1
        
        if not self.verbose:
            print()  # New line after progress indicator
        
        return results

    def optimize_processing_order(self, files_to_process: List[str]) -> List[str]:
        """
        Optimize the order of file processing for better resource utilization.
        
        Strategy:
        - Mix document and image files to balance CPU/GPU usage
        - Process larger files first to get them out of the way
        - Randomize within size groups to avoid hotspots

        Args:
            files_to_process: List of file paths

        Returns:
            Optimized list of file paths
        """
        import random
        
        # Separate files by type and get sizes
        documents = []
        images = []
        
        for file_path in files_to_process:
            try:
                file_size = os.path.getsize(file_path)
                file_info = (file_path, file_size)
                
                file_type = self.processor.get_file_type(file_path)
                if file_type == 'document':
                    documents.append(file_info)
                else:
                    images.append(file_info)
                    
            except Exception:
                # If we can't get size, treat as small file
                file_info = (file_path, 0)
                file_type = self.processor.get_file_type(file_path)
                if file_type == 'document':
                    documents.append(file_info)
                else:
                    images.append(file_info)
        
        # Sort by size (largest first) and randomize within size groups
        documents.sort(key=lambda x: x[1], reverse=True)
        images.sort(key=lambda x: x[1], reverse=True)
        
        # Interleave documents and images for better resource utilization
        optimized_order = []
        doc_idx = img_idx = 0
        
        while doc_idx < len(documents) or img_idx < len(images):
            # Add a document if available
            if doc_idx < len(documents):
                optimized_order.append(documents[doc_idx][0])
                doc_idx += 1
            
            # Add 1-2 images to balance the load
            for _ in range(min(2, len(images) - img_idx)):
                if img_idx < len(images):
                    optimized_order.append(images[img_idx][0])
                    img_idx += 1
        
        return optimized_order

    def run(self) -> Dict[str, Any]:
        """
        Run the complete document processing pipeline.

        Returns:
            Dictionary containing processing statistics and results
        """
        start_time = time.time()
        
        print("🔍 Discovering files to process...")
        files_to_process, already_processed = self.discover_files()
        
        if self.verbose:
            print(f"📁 Found {len(files_to_process)} files to process")
            print(f"✅ {len(already_processed)} files already processed (skipping)")
            
            if files_to_process:
                print("\n📋 Files to process:")
                for file_path in files_to_process:
                    file_type = self.processor.get_file_type(file_path)
                    size_kb = os.path.getsize(file_path) / 1024
                    emoji = "📄" if file_type == 'document' else "🖼️"
                    print(f"  {emoji} {Path(file_path).name} ({size_kb:.1f} KB)")
                print()
        
        if not files_to_process:
            print("✨ No files to process. All files have already been processed!")
            return {
                "total_files": len(already_processed),
                "processed_files": 0,
                "already_processed": len(already_processed),
                "processing_time": 0,
                "results": [],
            }
        
        # Optimize processing order
        if self.batch_size > 1:
            if self.verbose:
                print("🎯 Optimizing processing order for better resource utilization...")
            files_to_process = self.optimize_processing_order(files_to_process)
        
        # Process files
        if self.verbose:
            print(f"⚡ Processing {len(files_to_process)} files with {self.batch_size} workers...")
            print("-" * 60)
        
        try:
            results = self.process_files_parallel(files_to_process)
            
            # Generate reports
            if self.verbose:
                print("\n📊 Generating reports...")
            
            self.report_generator.create_csv_report(results)
            
            # Print summary
            self.report_generator.print_summary(results, verbose=self.verbose)
            
            # Calculate final statistics
            total_time = time.time() - start_time
            successful = sum(1 for r in results if r.get('success', False))
            
            final_stats = {
                "total_files": len(files_to_process) + len(already_processed),
                "processed_files": len(results),
                "successful_files": successful,
                "failed_files": len(results) - successful,
                "already_processed": len(already_processed),
                "processing_time": total_time,
                "results": results,
            }
            
            return final_stats
            
        finally:
            # Cleanup
            self._cleanup_lock_files()
            self.processor.cleanup()
            
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self._cleanup_lock_files()
        self.processor.cleanup()