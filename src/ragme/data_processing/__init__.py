# SPDX-License-Identifier: MIT
# Copyright (c) 2025 dr.max

"""
RAGme Data Processing Pipeline

This module provides batch document processing capabilities for RAGme,
allowing efficient processing of PDFs, DOCX files, and images into
vector database collections with full metadata extraction.
"""

from .pipeline import DocumentProcessingPipeline
from .processor import DocumentProcessor
from .report_generator import ReportGenerator

__all__ = ["DocumentProcessingPipeline", "DocumentProcessor", "ReportGenerator"]