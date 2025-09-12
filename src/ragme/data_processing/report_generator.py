# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class ReportGenerator:
    """
    Report generator for the RAGme data processing pipeline.
    Creates CSV summaries and individual .processed files for each document.
    """

    def __init__(self, output_directory: str):
        """
        Initialize the report generator.

        Args:
            output_directory: Directory where reports will be generated
        """
        self.output_directory = Path(output_directory)

    def create_processed_file(self, file_path: str, results: Dict[str, Any]):
        """
        Create a .processed file for a single document with human-readable summary.

        Args:
            file_path: Original file path
            results: Processing results dictionary
        """
        processed_file_path = Path(file_path).with_suffix(Path(file_path).suffix + ".processed")
        
        try:
            summary = self._generate_human_readable_summary(results)
            
            with open(processed_file_path, 'w', encoding='utf-8') as f:
                f.write(summary)
                
        except Exception as e:
            print(f"Error creating .processed file for {file_path}: {e}")

    def _generate_human_readable_summary(self, results: Dict[str, Any]) -> str:
        """Generate a human-readable summary of processing results."""
        lines = []
        
        # Header
        lines.append("=" * 60)
        lines.append("RAGme Document Processing Pipeline - Processing Summary")
        lines.append("=" * 60)
        lines.append("")
        
        # File Information
        lines.append("📄 FILE INFORMATION")
        lines.append("-" * 20)
        lines.append(f"File Name: {results.get('file_name', 'Unknown')}")
        lines.append(f"File Size: {results.get('file_size_kb', 0):.2f} KB")
        lines.append(f"File Type: {results.get('file_type', 'Unknown')}")
        if results.get('document_type'):
            lines.append(f"Document Type: {results.get('document_type').upper()}")
        lines.append(f"Processing Date: {results.get('processing_start_time', 'Unknown')}")
        lines.append("")
        
        # Processing Results
        lines.append("⚡ PROCESSING RESULTS")
        lines.append("-" * 23)
        success = results.get('success', False)
        lines.append(f"Status: {'✅ SUCCESS' if success else '❌ FAILED'}")
        
        if results.get('retry_count', 0) > 0:
            lines.append(f"Retry Attempts: {results.get('retry_count', 0)}")
        
        # Document-specific results
        if results.get('file_type') == 'document':
            lines.append(f"Text Chunks: {results.get('chunk_count', 0)}")
            lines.append(f"Average Chunk Size: {results.get('average_chunk_size_kb', 0):.2f} KB")
            
            if results.get('metadata', {}).get('page_count'):
                lines.append(f"Pages: {results['metadata']['page_count']}")
            
            extracted_images = results.get('extracted_images', [])
            lines.append(f"Images Extracted: {len(extracted_images)}")
            
            # Image processing summary
            if extracted_images:
                lines.append("")
                lines.append("🖼️  EXTRACTED IMAGES PROCESSING")
                lines.append("-" * 32)
                
                for i, img in enumerate(extracted_images):
                    lines.append(f"  Image {i+1}:")
                    lines.append(f"    Size: {img.get('file_size_kb', 0):.2f} KB")
                    lines.append(f"    EXIF Extracted: {'✅' if img.get('exif_extracted', False) else '❌'}")
                    lines.append(f"    AI Classifications: {img.get('ai_classification_features', 0)}")
                    lines.append(f"    OCR Success: {'✅' if img.get('ocr_success', False) else '❌'}")
                    if img.get('ocr_text_length', 0) > 0:
                        lines.append(f"    OCR Text Length: {img.get('ocr_text_length', 0)} chars")
                    if img.get('errors'):
                        lines.append(f"    Errors: {len(img['errors'])}")
                    lines.append("")
        
        # Image-specific results
        elif results.get('file_type') == 'image':
            lines.append("")
            lines.append("🖼️  IMAGE PROCESSING")
            lines.append("-" * 20)
            lines.append(f"EXIF Extracted: {'✅' if results.get('exif_extracted', False) else '❌'}")
            lines.append(f"AI Classifications: {results.get('ai_classification_features', 0)}")
            lines.append(f"OCR Success: {'✅' if results.get('ocr_success', False) else '❌'}")
            if results.get('ocr_text_length', 0) > 0:
                lines.append(f"OCR Text Length: {results.get('ocr_text_length', 0)} chars")
            
            if results.get('is_extracted'):
                lines.append(f"Extracted from: {results.get('source_document', 'Unknown document')}")
        
        lines.append("")
        
        # Timing Information
        timing = results.get('timing', {})
        if timing:
            lines.append("⏱️  TIMING BREAKDOWN")
            lines.append("-" * 19)
            
            if 'text_extraction' in timing:
                lines.append(f"Text Extraction: {timing['text_extraction']:.3f}s")
            if 'chunking' in timing:
                lines.append(f"Text Chunking: {timing['chunking']:.3f}s")
            if 'image_processing' in timing:
                lines.append(f"Image Processing: {timing['image_processing']:.3f}s")
            if 'vdb_storage' in timing:
                lines.append(f"VDB Storage: {timing['vdb_storage']:.3f}s")
            
            lines.append(f"Total Time: {timing.get('total', 0):.3f}s")
            lines.append("")
        
        # Errors
        errors = results.get('errors', [])
        if errors:
            lines.append("❌ ERRORS ENCOUNTERED")
            lines.append("-" * 21)
            for i, error in enumerate(errors, 1):
                lines.append(f"{i}. {error}")
            lines.append("")
        
        # Metadata Summary (for documents)
        metadata = results.get('metadata', {})
        if metadata and results.get('file_type') == 'document':
            lines.append("📋 DOCUMENT METADATA")
            lines.append("-" * 21)
            
            if metadata.get('author'):
                lines.append(f"Author: {metadata['author']}")
            if metadata.get('title'):
                lines.append(f"Title: {metadata['title']}")
            if metadata.get('subject'):
                lines.append(f"Subject: {metadata['subject']}")
            if metadata.get('created'):
                lines.append(f"Created: {metadata['created']}")
            if metadata.get('modified'):
                lines.append(f"Modified: {metadata['modified']}")
            
            lines.append("")
        
        # Footer
        lines.append("=" * 60)
        lines.append(f"Generated on: {datetime.now().isoformat()}")
        lines.append("Processed by: RAGme Document Processing Pipeline")
        lines.append("=" * 60)
        
        return "\n".join(lines)

    def aggregate_results(self, results_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate results from multiple file processing operations.

        Args:
            results_list: List of individual file processing results

        Returns:
            Aggregated statistics dictionary
        """
        stats = {
            "total_files": len(results_list),
            "successful_files": 0,
            "failed_files": 0,
            "total_documents": 0,
            "total_images": 0,
            "total_chunks": 0,
            "total_extracted_images": 0,
            "total_errors": 0,
            "processing_times": [],
            "document_times": [],
            "image_times": [],
            "file_sizes": [],
            "retry_counts": [],
        }
        
        for result in results_list:
            # Success/failure counting
            if result.get('success', False):
                stats["successful_files"] += 1
            else:
                stats["failed_files"] += 1
            
            # File type counting
            file_type = result.get('file_type')
            if file_type == 'document':
                stats["total_documents"] += 1
                stats["total_chunks"] += result.get('chunk_count', 0)
                stats["total_extracted_images"] += len(result.get('extracted_images', []))
                
                # Document processing times
                total_time = result.get('timing', {}).get('total', 0)
                if total_time > 0:
                    stats["document_times"].append(total_time)
                    
            elif file_type == 'image':
                stats["total_images"] += 1
                
                # Image processing times
                total_time = result.get('timing', {}).get('total', 0)
                if total_time > 0:
                    stats["image_times"].append(total_time)
            
            # Error counting
            stats["total_errors"] += len(result.get('errors', []))
            
            # Timing and size tracking
            total_time = result.get('timing', {}).get('total', 0)
            if total_time > 0:
                stats["processing_times"].append(total_time)
            
            file_size = result.get('file_size_kb', 0)
            if file_size > 0:
                stats["file_sizes"].append(file_size)
            
            retry_count = result.get('retry_count', 0)
            stats["retry_counts"].append(retry_count)
        
        # Calculate averages
        if stats["processing_times"]:
            stats["avg_processing_time"] = sum(stats["processing_times"]) / len(stats["processing_times"])
            stats["total_processing_time"] = sum(stats["processing_times"])
        else:
            stats["avg_processing_time"] = 0
            stats["total_processing_time"] = 0
        
        if stats["document_times"]:
            stats["avg_document_time"] = sum(stats["document_times"]) / len(stats["document_times"])
        else:
            stats["avg_document_time"] = 0
        
        if stats["image_times"]:
            stats["avg_image_time"] = sum(stats["image_times"]) / len(stats["image_times"])
        else:
            stats["avg_image_time"] = 0
        
        if stats["file_sizes"]:
            stats["avg_file_size_kb"] = sum(stats["file_sizes"]) / len(stats["file_sizes"])
        else:
            stats["avg_file_size_kb"] = 0
        
        return stats

    def create_csv_report(self, results_list: List[Dict[str, Any]], filename: str = "processing_results.csv"):
        """
        Create a CSV report from processing results.

        Args:
            results_list: List of individual file processing results
            filename: Name of the CSV file to create
        """
        csv_path = self.output_directory / filename
        
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'file_name', 'file_size_kb', 'file_type', 'document_type',
                    'chunk_count', 'avg_chunk_size_kb', 'extracted_images_count',
                    'total_errors', 'exif_extracted', 'ai_classification_features',
                    'ocr_success', 'ocr_text_length', 'processing_time_seconds',
                    'retry_count', 'success', 'processing_date'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for result in results_list:
                    # Calculate extracted images count
                    extracted_images_count = len(result.get('extracted_images', []))
                    
                    # For images, get values directly; for documents, aggregate from extracted images
                    if result.get('file_type') == 'image':
                        exif_extracted = result.get('exif_extracted', False)
                        ai_classification_features = result.get('ai_classification_features', 0)
                        ocr_success = result.get('ocr_success', False)
                        ocr_text_length = result.get('ocr_text_length', 0)
                    else:
                        # For documents, summarize extracted images
                        extracted_images = result.get('extracted_images', [])
                        if extracted_images:
                            exif_extracted = any(img.get('exif_extracted', False) for img in extracted_images)
                            ai_classification_features = sum(img.get('ai_classification_features', 0) for img in extracted_images)
                            ocr_success = any(img.get('ocr_success', False) for img in extracted_images)
                            ocr_text_length = sum(img.get('ocr_text_length', 0) for img in extracted_images)
                        else:
                            exif_extracted = False
                            ai_classification_features = 0
                            ocr_success = False
                            ocr_text_length = 0
                    
                    writer.writerow({
                        'file_name': result.get('file_name', ''),
                        'file_size_kb': round(result.get('file_size_kb', 0), 2),
                        'file_type': result.get('file_type', ''),
                        'document_type': result.get('document_type', ''),
                        'chunk_count': result.get('chunk_count', 0 if result.get('file_type') == 'document' else ''),
                        'avg_chunk_size_kb': round(result.get('average_chunk_size_kb', 0), 2) if result.get('file_type') == 'document' else '',
                        'extracted_images_count': extracted_images_count if result.get('file_type') == 'document' else '',
                        'total_errors': len(result.get('errors', [])),
                        'exif_extracted': exif_extracted,
                        'ai_classification_features': ai_classification_features,
                        'ocr_success': ocr_success,
                        'ocr_text_length': ocr_text_length,
                        'processing_time_seconds': round(result.get('timing', {}).get('total', 0), 3),
                        'retry_count': result.get('retry_count', 0),
                        'success': result.get('success', False),
                        'processing_date': result.get('processing_start_time', ''),
                    })
                    
        except Exception as e:
            print(f"Error creating CSV report: {e}")

    def print_summary(self, results_list: List[Dict[str, Any]], verbose: bool = False):
        """
        Print a console summary of processing results.

        Args:
            results_list: List of individual file processing results
            verbose: Whether to show detailed per-file status
        """
        stats = self.aggregate_results(results_list)
        
        print("\n" + "="*60)
        print("🚀 RAGme Document Processing Pipeline - Summary Report")
        print("="*60)
        
        # Overall statistics
        print(f"\n📊 OVERALL STATISTICS")
        print("-" * 22)
        print(f"Total files processed: {stats['total_files']}")
        print(f"✅ Successful: {stats['successful_files']}")
        print(f"❌ Failed: {stats['failed_files']}")
        print(f"📄 Documents: {stats['total_documents']}")
        print(f"🖼️  Images: {stats['total_images']}")
        
        # Processing results
        print(f"\n📈 PROCESSING RESULTS")
        print("-" * 21)
        print(f"Total chunks created: {stats['total_chunks']:,}")
        print(f"Images extracted from docs: {stats['total_extracted_images']}")
        print(f"Total errors encountered: {stats['total_errors']}")
        
        # Timing statistics
        print(f"\n⏱️  TIMING STATISTICS")
        print("-" * 20)
        print(f"Total processing time: {stats['total_processing_time']:.2f}s")
        print(f"Average processing time: {stats['avg_processing_time']:.3f}s")
        if stats['avg_document_time'] > 0:
            print(f"Average document time: {stats['avg_document_time']:.3f}s")
        if stats['avg_image_time'] > 0:
            print(f"Average image time: {stats['avg_image_time']:.3f}s")
        
        # File size statistics
        if stats['avg_file_size_kb'] > 0:
            print(f"\n📏 FILE SIZE STATISTICS")
            print("-" * 23)
            print(f"Average file size: {stats['avg_file_size_kb']:.2f} KB")
            print(f"Total data processed: {sum(stats['file_sizes']):.2f} KB")
        
        # Retry statistics
        total_retries = sum(stats['retry_counts'])
        if total_retries > 0:
            print(f"\n🔄 RETRY STATISTICS")
            print("-" * 18)
            print(f"Total retry attempts: {total_retries}")
            print(f"Files requiring retries: {sum(1 for r in stats['retry_counts'] if r > 0)}")
        
        if verbose and results_list:
            print(f"\n📋 DETAILED FILE STATUS")
            print("-" * 23)
            
            for result in results_list:
                status_emoji = "✅" if result.get('success', False) else "❌"
                file_type_emoji = "📄" if result.get('file_type') == 'document' else "🖼️"
                
                print(f"{status_emoji} {file_type_emoji} {result.get('file_name', 'Unknown')}")
                
                if result.get('file_type') == 'document':
                    print(f"   Chunks: {result.get('chunk_count', 0)}, "
                          f"Extracted Images: {len(result.get('extracted_images', []))}")
                
                if result.get('errors'):
                    print(f"   Errors: {len(result['errors'])}")
                
                timing = result.get('timing', {})
                if timing.get('total'):
                    print(f"   Time: {timing['total']:.3f}s")
                
                print()
        
        print("="*60)
        print("📝 Reports saved to:", self.output_directory)
        print("="*60)

    def load_processed_files_results(self) -> List[str]:
        """
        Load list of already processed files by scanning for .processed files.

        Returns:
            List of file paths that have already been processed
        """
        processed_files = []
        
        for file_path in self.output_directory.glob("*.processed"):
            # Remove the .processed extension to get original file name
            original_file = str(file_path)[:-10]  # Remove '.processed'
            processed_files.append(original_file)
        
        return processed_files