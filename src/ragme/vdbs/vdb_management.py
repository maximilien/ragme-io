#!/usr/bin/env python3
"""
RAGme VDB Management Tool

Direct management of vector database collections using the existing VDB abstractions.
This tool allows administrators to manage text and image collections independently
of the RAGme UI, APIs, and MCP services.
"""

import os
import sys
from pathlib import Path
from typing import Any

# Handle both direct execution and module import
try:
    from ..utils.config_manager import config
    from .vector_db_factory import create_vector_database
except ImportError:
    # When running as script, use absolute imports
    import sys
    from pathlib import Path

    # Add the src directory to the Python path
    current_file = Path(__file__)
    src_path = current_file.parent.parent.parent
    sys.path.insert(0, str(src_path))
    from ragme.utils.config_manager import config
    from ragme.vdbs.vector_db_factory import create_vector_database


class VDBManager:
    """Vector Database Manager for direct collection operations."""

    def __init__(self):
        """Initialize the VDB manager with current configuration."""
        self.config_manager = config
        self.vdb_type = os.getenv("VECTOR_DB_TYPE") or self.config_manager.get(
            "vector_databases", {}
        ).get("default", "weaviate-cloud")
        self.text_collection_name = self.config_manager.get_text_collection_name()
        self.image_collection_name = self.config_manager.get_image_collection_name()
        self.vdb = None

    def _get_vdb(self):
        """Get or create VDB instance."""
        if self.vdb is None:
            self.vdb = create_vector_database()
        return self.vdb

    def cleanup(self):
        """Clean up VDB resources."""
        if self.vdb is not None:
            try:
                self.vdb.cleanup()
            except Exception:
                pass  # Ignore cleanup errors
            self.vdb = None

    def show_config(self) -> dict[str, Any]:
        """Show currently configured VDB information."""
        return {
            "vdb_type": self.vdb_type,
            "text_collection": self.text_collection_name,
            "image_collection": self.image_collection_name,
            "config_source": "config.yaml + .env",
        }

    def check_health(self) -> dict[str, Any]:
        """Check VDB health and connectivity."""
        results = {
            "vdb_type": self.vdb_type,
            "status": "unknown",
            "collections": {},
            "errors": [],
        }

        try:
            # Get VDB instance
            vdb = self._get_vdb()

            # Test text collection if available
            if vdb.has_text_collection():
                try:
                    text_count = vdb.count_documents()
                    results["collections"]["text"] = {
                        "name": vdb.get_text_collection_name(),
                        "status": "healthy",
                        "document_count": text_count,
                        "item_type": "documents",
                    }
                except Exception as e:
                    results["collections"]["text"] = {
                        "name": vdb.get_text_collection_name(),
                        "status": "error",
                        "error": str(e),
                        "item_type": "documents",
                    }
                    results["errors"].append(f"Text collection error: {e}")
            else:
                results["collections"]["text"] = {
                    "name": "not configured",
                    "status": "not available",
                    "document_count": 0,
                    "item_type": "documents",
                }

            # Test image collection if available
            if vdb.has_image_collection():
                try:
                    image_count = vdb.count_images()
                    results["collections"]["image"] = {
                        "name": vdb.get_image_collection_name(),
                        "status": "healthy",
                        "document_count": image_count,
                        "item_type": "images",
                    }
                except Exception as e:
                    results["collections"]["image"] = {
                        "name": vdb.get_image_collection_name(),
                        "status": "error",
                        "error": str(e),
                        "item_type": "images",
                    }
                    results["errors"].append(f"Image collection error: {e}")
            else:
                results["collections"]["image"] = {
                    "name": "not configured",
                    "status": "not available",
                    "document_count": 0,
                    "item_type": "images",
                }

        except Exception as e:
            results["status"] = "error"
            results["errors"].append(f"VDB connection error: {e}")
            return results

        # Overall status
        if results["errors"]:
            results["status"] = "unhealthy"
        else:
            results["status"] = "healthy"

        return results

    def list_collections(self) -> dict[str, Any]:
        """List collection names and basic info."""
        try:
            vdb = self._get_vdb()
            collections = {}

            if vdb.has_text_collection():
                collections["text_collection"] = {
                    "name": vdb.get_text_collection_name(),
                    "type": "text",
                }

            if vdb.has_image_collection():
                collections["image_collection"] = {
                    "name": vdb.get_image_collection_name(),
                    "type": "image",
                }

            return collections
        except Exception:
            return {
                "text_collection": {"name": self.text_collection_name, "type": "text"},
                "image_collection": {
                    "name": self.image_collection_name,
                    "type": "image",
                },
            }

    def list_text_documents(self, limit: int = 50) -> dict[str, Any]:
        """List documents in the text collection."""
        try:
            vdb = self._get_vdb()

            if not vdb.has_text_collection():
                return {
                    "status": "error",
                    "collection": "text",
                    "error": "Text collection not configured",
                }

            documents = vdb.list_documents(limit=limit, offset=0)

            return {
                "status": "success",
                "collection": vdb.get_text_collection_name(),
                "count": len(documents),
                "documents": documents,
            }
        except Exception as e:
            return {
                "status": "error",
                "collection": "text",
                "error": str(e),
            }

    def list_image_documents(self, limit: int = 50) -> dict[str, Any]:
        """List documents in the image collection."""
        try:
            vdb = self._get_vdb()

            if not vdb.has_image_collection():
                return {
                    "status": "error",
                    "collection": "image",
                    "error": "Image collection not configured",
                }

            # Use list_images method to get images from the image collection
            images = vdb.list_images(limit=limit, offset=0)

            return {
                "status": "success",
                "collection": vdb.get_image_collection_name(),
                "count": len(images),
                "documents": images,
            }
        except Exception as e:
            return {
                "status": "error",
                "collection": "image",
                "error": str(e),
            }

    def delete_text_collection_content(self) -> dict[str, Any]:
        """Delete all content from the text collection."""
        try:
            vdb = self._get_vdb()

            if not vdb.has_text_collection():
                return {
                    "status": "error",
                    "collection": "text",
                    "error": "Text collection not configured",
                }

            # Get all documents first to show what will be deleted
            all_docs = vdb.list_documents(limit=10000, offset=0)
            doc_count = len(all_docs)

            if doc_count == 0:
                return {
                    "status": "success",
                    "collection": vdb.get_text_collection_name(),
                    "message": "Collection is already empty",
                    "deleted_count": 0,
                }

            # Delete each document
            deleted_count = 0
            storage_deleted_count = 0
            for doc in all_docs:
                try:
                    # Check if document has a storage path and delete from storage if it exists
                    storage_path = doc.get("metadata", {}).get("storage_path")
                    if storage_path:
                        try:
                            from ..utils.config_manager import config
                            from ..utils.storage import StorageService

                            storage_service = StorageService(config)
                            storage_deleted = storage_service.delete_file(storage_path)
                            if storage_deleted:
                                print(f"Deleted document from storage: {storage_path}")
                                storage_deleted_count += 1
                            else:
                                print(
                                    f"Failed to delete document from storage: {storage_path}"
                                )
                        except Exception as storage_error:
                            print(
                                f"Error deleting document from storage {storage_path}: {storage_error}"
                            )
                            # Continue with vector database deletion even if storage deletion fails

                    # Delete from vector database
                    vdb.delete_document(doc["id"])
                    deleted_count += 1
                except Exception as e:
                    print(f"Warning: Failed to delete document {doc['id']}: {e}")

            message = f"Successfully deleted {deleted_count} documents"
            if storage_deleted_count > 0:
                message += f" (also deleted {storage_deleted_count} files from storage)"

            return {
                "status": "success",
                "collection": vdb.get_text_collection_name(),
                "message": message,
                "deleted_count": deleted_count,
            }
        except Exception as e:
            return {
                "status": "error",
                "collection": "text",
                "error": str(e),
            }

    def delete_image_collection_content(self) -> dict[str, Any]:
        """Delete all content from the image collection."""
        try:
            vdb = self._get_vdb()

            if not vdb.has_image_collection():
                return {
                    "status": "error",
                    "collection": "image",
                    "error": "Image collection not configured",
                }

            # Get all images first to show what will be deleted
            all_images = vdb.list_images(limit=10000, offset=0)
            image_count = len(all_images)

            if image_count == 0:
                return {
                    "status": "success",
                    "collection": vdb.get_image_collection_name(),
                    "message": "Collection is already empty",
                    "deleted_count": 0,
                }

            # Delete each image
            deleted_count = 0
            storage_deleted_count = 0
            for image in all_images:
                try:
                    # Check if image has a storage path and delete from storage if it exists
                    storage_path = image.get("metadata", {}).get("storage_path")
                    if storage_path:
                        try:
                            from ..utils.config_manager import config
                            from ..utils.storage import StorageService

                            storage_service = StorageService(config)
                            storage_deleted = storage_service.delete_file(storage_path)
                            if storage_deleted:
                                print(f"Deleted image from storage: {storage_path}")
                                storage_deleted_count += 1
                            else:
                                print(
                                    f"Failed to delete image from storage: {storage_path}"
                                )
                        except Exception as storage_error:
                            print(
                                f"Error deleting image from storage {storage_path}: {storage_error}"
                            )
                            # Continue with vector database deletion even if storage deletion fails

                    # Delete from vector database
                    vdb.delete_image(image["id"])
                    deleted_count += 1
                except Exception as e:
                    print(f"Warning: Failed to delete image {image['id']}: {e}")

            message = f"Successfully deleted {deleted_count} images"
            if storage_deleted_count > 0:
                message += f" (also deleted {storage_deleted_count} files from storage)"

            return {
                "status": "success",
                "collection": vdb.get_image_collection_name(),
                "message": message,
                "deleted_count": deleted_count,
            }
        except Exception as e:
            return {
                "status": "error",
                "collection": "image",
                "error": str(e),
            }

    def get_virtual_structure_stats(self) -> dict[str, Any]:
        """Get virtual structure statistics showing chunks, grouped images, documents, and individual images."""
        try:
            vdb = self._get_vdb()
            stats = {
                "total_chunks": 0,
                "grouped_images": 0,
                "individual_documents": 0,
                "individual_images": 0,
                "document_groups": 0,
                "image_groups": 0,
                "collections": {},
            }

            # Get text collection stats
            if vdb.has_text_collection():
                try:
                    documents = vdb.list_documents(limit=10000, offset=0)
                    stats["total_chunks"] = len(documents)

                    # Group documents to count individual documents vs chunks
                    doc_groups = {}
                    for doc in documents:
                        metadata = doc.get("metadata", {})

                        # Check if this is a chunked document
                        if (
                            metadata.get("is_chunk") and metadata.get("total_chunks")
                        ) or (
                            metadata.get("is_chunked") and metadata.get("total_chunks")
                        ):
                            # Extract base URL for grouping
                            url = doc.get("url", "")
                            base_url = url.split("#")[0] if "#" in url else url
                            if base_url not in doc_groups:
                                doc_groups[base_url] = {
                                    "total_chunks": metadata.get("total_chunks", 0),
                                    "chunks": [],
                                }
                            doc_groups[base_url]["chunks"].append(doc)
                        else:
                            # Individual document
                            stats["individual_documents"] += 1

                    stats["document_groups"] = len(doc_groups)

                    # Count total individual documents (groups + individual)
                    stats["individual_documents"] += stats["document_groups"]

                    stats["collections"]["text"] = {
                        "name": vdb.get_text_collection_name(),
                        "status": "healthy",
                        "total_chunks": stats["total_chunks"],
                        "document_groups": stats["document_groups"],
                        "individual_documents": stats["individual_documents"],
                    }
                except Exception as e:
                    stats["collections"]["text"] = {
                        "name": vdb.get_text_collection_name(),
                        "status": "error",
                        "error": str(e),
                    }
            else:
                stats["collections"]["text"] = {
                    "name": "not configured",
                    "status": "not available",
                }

            # Get image collection stats
            if vdb.has_image_collection():
                try:
                    images = vdb.list_images(limit=10000, offset=0)

                    # Group images by source PDF
                    image_groups = {}
                    individual_images = 0

                    for img in images:
                        metadata = img.get("metadata", {})

                        # Check if this is a PDF-extracted image
                        if metadata.get(
                            "source_type"
                        ) == "pdf_extracted_image" and metadata.get("pdf_filename"):
                            pdf_filename = metadata["pdf_filename"]
                            if pdf_filename not in image_groups:
                                image_groups[pdf_filename] = {
                                    "total_images": 0,
                                    "images": [],
                                }
                            image_groups[pdf_filename]["images"].append(img)
                            image_groups[pdf_filename]["total_images"] += 1
                        else:
                            # Individual uploaded image
                            individual_images += 1

                    stats["grouped_images"] = sum(
                        group["total_images"] for group in image_groups.values()
                    )
                    stats["individual_images"] = individual_images
                    stats["image_groups"] = len(image_groups)

                    stats["collections"]["image"] = {
                        "name": vdb.get_image_collection_name(),
                        "status": "healthy",
                        "grouped_images": stats["grouped_images"],
                        "individual_images": stats["individual_images"],
                        "image_groups": stats["image_groups"],
                    }
                except Exception as e:
                    stats["collections"]["image"] = {
                        "name": vdb.get_image_collection_name(),
                        "status": "error",
                        "error": str(e),
                    }
            else:
                stats["collections"]["image"] = {
                    "name": "not configured",
                    "status": "not available",
                }

            return stats
        except Exception as e:
            return {
                "error": str(e),
                "total_chunks": 0,
                "grouped_images": 0,
                "individual_documents": 0,
                "individual_images": 0,
                "document_groups": 0,
                "image_groups": 0,
                "collections": {},
            }

    def list_document_groups(self, limit: int = 50) -> dict[str, Any]:
        """List document groups showing how chunks are organized."""
        try:
            vdb = self._get_vdb()

            if not vdb.has_text_collection():
                return {
                    "status": "error",
                    "collection": "text",
                    "error": "Text collection not configured",
                }

            documents = vdb.list_documents(limit=10000, offset=0)

            # Group documents
            doc_groups = {}
            individual_docs = []

            for doc in documents:
                metadata = doc.get("metadata", {})

                # Check if this is a chunked document
                if (metadata.get("is_chunk") and metadata.get("total_chunks")) or (
                    metadata.get("is_chunked") and metadata.get("total_chunks")
                ):
                    # Extract base URL for grouping
                    url = doc.get("url", "")
                    base_url = url.split("#")[0] if "#" in url else url

                    if base_url not in doc_groups:
                        doc_groups[base_url] = {
                            "base_url": base_url,
                            "original_filename": metadata.get("filename", "Unknown"),
                            "total_chunks": metadata.get("total_chunks", 0),
                            "chunks": [],
                            "metadata": metadata,
                        }
                    doc_groups[base_url]["chunks"].append(doc)
                else:
                    # Individual document
                    individual_docs.append(doc)

            # Sort groups by filename and limit results
            sorted_groups = sorted(
                doc_groups.values(), key=lambda x: x["original_filename"]
            )
            limited_groups = sorted_groups[:limit]

            return {
                "status": "success",
                "collection": vdb.get_text_collection_name(),
                "document_groups": len(doc_groups),
                "individual_documents": len(individual_docs),
                "total_chunks": len(documents),
                "groups": limited_groups,
                "individual_docs": individual_docs[:limit],
            }
        except Exception as e:
            return {
                "status": "error",
                "collection": "text",
                "error": str(e),
            }

    def list_image_groups(self, limit: int = 50) -> dict[str, Any]:
        """List image groups showing how images are organized by source PDF."""
        try:
            vdb = self._get_vdb()

            if not vdb.has_image_collection():
                return {
                    "status": "error",
                    "collection": "image",
                    "error": "Image collection not configured",
                }

            images = vdb.list_images(limit=10000, offset=0)

            # Group images by source PDF
            image_groups = {}
            individual_images = []

            for img in images:
                metadata = img.get("metadata", {})

                # Check if this is a PDF-extracted image
                if metadata.get(
                    "source_type"
                ) == "pdf_extracted_image" and metadata.get("pdf_filename"):
                    pdf_filename = metadata["pdf_filename"]

                    if pdf_filename not in image_groups:
                        image_groups[pdf_filename] = {
                            "pdf_filename": pdf_filename,
                            "total_images": 0,
                            "images": [],
                            "metadata": metadata,
                        }
                    image_groups[pdf_filename]["images"].append(img)
                    image_groups[pdf_filename]["total_images"] += 1
                else:
                    # Individual uploaded image
                    individual_images.append(img)

            # Sort groups by filename and limit results
            sorted_groups = sorted(
                image_groups.values(), key=lambda x: x["pdf_filename"]
            )
            limited_groups = sorted_groups[:limit]

            return {
                "status": "success",
                "collection": vdb.get_image_collection_name(),
                "image_groups": len(image_groups),
                "individual_images": len(individual_images),
                "grouped_images": sum(
                    group["total_images"] for group in image_groups.values()
                ),
                "groups": limited_groups,
                "individual_images_list": individual_images[:limit],
            }
        except Exception as e:
            return {
                "status": "error",
                "collection": "image",
                "error": str(e),
            }

    def delete_document_by_filename(self, filename: str) -> dict[str, Any]:
        """Delete an individual document by filename, including all its chunks and grouped images."""
        try:
            vdb = self._get_vdb()

            # Get all documents and images
            documents = vdb.list_documents(limit=10000, offset=0)
            images = vdb.list_images(limit=10000, offset=0)

            # Find documents that match the filename
            matching_docs = []
            for doc in documents:
                metadata = doc.get("metadata", {})
                doc_filename = metadata.get("filename", "")
                if doc_filename == filename:
                    matching_docs.append(doc)

            if not matching_docs:
                return {
                    "status": "error",
                    "message": f"No documents found with filename: {filename}",
                    "deleted_docs": 0,
                    "deleted_images": 0,
                }

            # Find images that were extracted from this document
            matching_images = []
            for img in images:
                metadata = img.get("metadata", {})
                pdf_filename = metadata.get("pdf_filename", "")
                if pdf_filename == filename:
                    matching_images.append(img)

            # Delete all matching documents
            deleted_docs = 0
            storage_deleted_count = 0
            for doc in matching_docs:
                try:
                    # Check if document has a storage path and delete from storage if it exists
                    storage_path = doc.get("metadata", {}).get("storage_path")
                    if storage_path:
                        try:
                            from ..utils.config_manager import config
                            from ..utils.storage import StorageService

                            storage_service = StorageService(config)
                            storage_deleted = storage_service.delete_file(storage_path)
                            if storage_deleted:
                                print(f"Deleted document from storage: {storage_path}")
                                storage_deleted_count += 1
                            else:
                                print(
                                    f"Failed to delete document from storage: {storage_path}"
                                )
                        except Exception as storage_error:
                            print(
                                f"Error deleting document from storage {storage_path}: {storage_error}"
                            )
                            # Continue with vector database deletion even if storage deletion fails

                    # Delete from vector database
                    vdb.delete_document(doc["id"])
                    deleted_docs += 1
                except Exception as e:
                    print(f"Warning: Failed to delete document {doc['id']}: {e}")

            # Delete all matching images
            deleted_images = 0
            for img in matching_images:
                try:
                    # Check if image has a storage path and delete from storage if it exists
                    storage_path = img.get("metadata", {}).get("storage_path")
                    if storage_path:
                        try:
                            from ..utils.config_manager import config
                            from ..utils.storage import StorageService

                            storage_service = StorageService(config)
                            storage_deleted = storage_service.delete_file(storage_path)
                            if storage_deleted:
                                print(f"Deleted image from storage: {storage_path}")
                            else:
                                print(
                                    f"Failed to delete image from storage: {storage_path}"
                                )
                        except Exception as storage_error:
                            print(
                                f"Error deleting image from storage {storage_path}: {storage_error}"
                            )
                            # Continue with vector database deletion even if storage deletion fails

                    # Delete from vector database
                    vdb.delete_image(img["id"])
                    deleted_images += 1
                except Exception as e:
                    print(f"Warning: Failed to delete image {img['id']}: {e}")

            # Prepare message
            message = f"Successfully deleted document '{filename}'"
            if deleted_docs > 0:
                message += f" ({deleted_docs} chunks)"
            if deleted_images > 0:
                message += f" and {deleted_images} extracted images"
            if storage_deleted_count > 0:
                message += f" (also deleted {storage_deleted_count} files from storage)"

            return {
                "status": "success",
                "message": message,
                "filename": filename,
                "deleted_docs": deleted_docs,
                "deleted_images": deleted_images,
                "storage_deleted": storage_deleted_count,
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error deleting document '{filename}': {str(e)}",
                "deleted_docs": 0,
                "deleted_images": 0,
            }


def print_emoji_status(status: str, message: str):
    """Print status with emoji."""
    emojis = {
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
        "info": "ℹ️",
        "health": "🏥",
        "config": "⚙️",
        "list": "📋",
        "delete": "🗑️",
    }
    emoji = emojis.get(status, "ℹ️")
    print(f"{emoji} {message}")


def cleanup_and_exit(manager: VDBManager, exit_code: int = 0):
    """Clean up resources and exit."""
    try:
        manager.cleanup()
    except Exception:
        pass  # Ignore cleanup errors
    sys.exit(exit_code)


def main():
    """Main entry point for the VDB management tool."""
    if len(sys.argv) < 2:
        print("❌ Error: No command specified")
        print("Use './tools/vdb.sh help' for usage information")
        sys.exit(1)

    command = sys.argv[1]
    manager = VDBManager()

    try:
        if command == "help":
            print("RAGme VDB Management Tool")
            print("=" * 40)
            print("USAGE:")
            print(
                "./tools/vdb.sh help                         # shows help for this script"
            )
            print(
                "./tools/vdb.sh --show                       # shows currently configured VDB"
            )
            print(
                "./tools/vdb.sh health                       # attempts to connect to VDB and collections"
            )
            print(
                "./tools/vdb.sh virtual-structure            # shows virtual structure (chunks, grouped images, documents, individual images)"
            )
            print(
                "./tools/vdb.sh document-groups              # shows how documents are grouped into chunks"
            )
            print(
                "./tools/vdb.sh image-groups                 # shows how images are grouped by PDF source"
            )
            print(
                "./tools/vdb.sh delete-document <filename>   # delete document and all its chunks and extracted images"
            )
            print(
                "./tools/vdb.sh collections --list           # shows collection names"
            )
            print(
                "./tools/vdb.sh collections --text --list    # list docs in text collection (shows source, type, text preview)"
            )
            print(
                "./tools/vdb.sh collections --image --list   # list docs in image collection (shows source, classification, image data)"
            )
            print(
                "./tools/vdb.sh collections --text --delete  # delete the text collection content"
            )
            print(
                "./tools/vdb.sh collections --image --delete # delete the image collection content"
            )

        elif command == "--show":
            config_info = manager.show_config()
            print_emoji_status("config", "VDB Configuration:")
            print(f"  Type: {config_info['vdb_type']}")
            print(f"  Text Collection: {config_info['text_collection']}")
            print(f"  Image Collection: {config_info['image_collection']}")
            print(f"  Config Source: {config_info['config_source']}")

        elif command == "health":
            health_info = manager.check_health()
            if health_info["status"] == "healthy":
                print_emoji_status("health", "VDB Health Check: HEALTHY")
            else:
                print_emoji_status("error", "VDB Health Check: UNHEALTHY")

            for coll_type, coll_info in health_info["collections"].items():
                if coll_info["status"] == "healthy":
                    item_type = coll_info.get("item_type", "documents")
                    print_emoji_status(
                        "success",
                        f"{coll_type.title()} Collection: {coll_info['name']} ({coll_info['document_count']} {item_type})",
                    )
                else:
                    print_emoji_status(
                        "error",
                        f"{coll_type.title()} Collection: {coll_info['name']} - ERROR: {coll_info['error']}",
                    )

            if health_info["errors"]:
                print_emoji_status("warning", "Errors encountered:")
                for error in health_info["errors"]:
                    print(f"  - {error}")

            # Show virtual structure summary
            print()
            print_emoji_status("info", "Virtual Structure Summary:")
            try:
                stats = manager.get_virtual_structure_stats()
                if "error" not in stats:
                    print(f"  📄 Total Chunks: {stats['total_chunks']}")
                    print(f"  🖼️  Grouped Images: {stats['grouped_images']}")
                    print(f"  📁 Individual Documents: {stats['individual_documents']}")
                    print(f"  🖼️  Individual Images: {stats['individual_images']}")
                else:
                    print(
                        f"  ⚠️  Could not retrieve virtual structure: {stats['error']}"
                    )
            except Exception as e:
                print(f"  ⚠️  Could not retrieve virtual structure: {e}")

        elif command == "virtual-structure":
            stats = manager.get_virtual_structure_stats()
            if "error" in stats:
                print_emoji_status(
                    "error", f"Failed to get virtual structure: {stats['error']}"
                )
                cleanup_and_exit(manager, 1)

            print_emoji_status("info", "Virtual Structure Overview:")
            print(f"  📄 Total Chunks: {stats['total_chunks']}")
            print(f"  🖼️  Grouped Images: {stats['grouped_images']}")
            print(f"  📁 Individual Documents: {stats['individual_documents']}")
            print(f"  🖼️  Individual Images: {stats['individual_images']}")
            print(f"  📂 Document Groups: {stats['document_groups']}")
            print(f"  🗂️  Image Groups: {stats['image_groups']}")
            print()

            # Show collection details
            for coll_type, coll_info in stats["collections"].items():
                if coll_info["status"] == "healthy":
                    if coll_type == "text":
                        print_emoji_status(
                            "success", f"Text Collection: {coll_info['name']}"
                        )
                        print(f"    - Total Chunks: {coll_info['total_chunks']}")
                        print(f"    - Document Groups: {coll_info['document_groups']}")
                        print(
                            f"    - Individual Documents: {coll_info['individual_documents']}"
                        )
                    elif coll_type == "image":
                        print_emoji_status(
                            "success", f"Image Collection: {coll_info['name']}"
                        )
                        print(f"    - Grouped Images: {coll_info['grouped_images']}")
                        print(
                            f"    - Individual Images: {coll_info['individual_images']}"
                        )
                        print(f"    - Image Groups: {coll_info['image_groups']}")
                else:
                    print_emoji_status(
                        "error",
                        f"{coll_type.title()} Collection: {coll_info['name']} - {coll_info.get('error', 'Not available')}",
                    )

        elif command == "document-groups":
            result = manager.list_document_groups()
            if result["status"] == "success":
                print_emoji_status(
                    "list",
                    f"Document Groups ({result['document_groups']} groups, {result['individual_documents']} individual docs):",
                )
                print(f"  Total Chunks: {result['total_chunks']}")
                print()

                # Show document groups
                if result["groups"]:
                    print_emoji_status("info", "Document Groups:")
                    for i, group in enumerate(result["groups"], 1):
                        print(f"  {i}. {group['original_filename']}")
                        print(f"     Base URL: {group['base_url']}")
                        print(f"     Total Chunks: {group['total_chunks']}")
                        print(f"     Chunks in Group: {len(group['chunks'])}")
                        print()

                # Show individual documents
                if result["individual_docs"]:
                    print_emoji_status("info", "Individual Documents:")
                    for i, doc in enumerate(result["individual_docs"], 1):
                        metadata = doc.get("metadata", {})
                        filename = metadata.get("filename", "Unknown")
                        source = metadata.get("source", "")
                        print(f"  {i}. {filename}")
                        if source:
                            print(f"     Source: {source}")
                        print()
            else:
                print_emoji_status(
                    "error", f"Failed to list document groups: {result['error']}"
                )

        elif command == "image-groups":
            result = manager.list_image_groups()
            if result["status"] == "success":
                print_emoji_status(
                    "list",
                    f"Image Groups ({result['image_groups']} groups, {result['individual_images']} individual images):",
                )
                print(f"  Grouped Images: {result['grouped_images']}")
                print()

                # Show image groups
                if result["groups"]:
                    print_emoji_status("info", "Image Groups (by PDF source):")
                    for i, group in enumerate(result["groups"], 1):
                        print(f"  {i}. {group['pdf_filename']}")
                        print(f"     Total Images: {group['total_images']}")
                        print(f"     Images in Group: {len(group['images'])}")
                        print()

                # Show individual images
                if result["individual_images_list"]:
                    print_emoji_status("info", "Individual Images:")
                    for i, img in enumerate(result["individual_images_list"], 1):
                        metadata = img.get("metadata", {})
                        filename = metadata.get("filename", "Unknown")
                        source = metadata.get("source", "")
                        print(f"  {i}. {filename}")
                        if source:
                            print(f"     Source: {source}")
                        print()
            else:
                print_emoji_status(
                    "error", f"Failed to list image groups: {result['error']}"
                )

        elif command == "delete-document":
            if len(sys.argv) < 3:
                print("❌ Error: delete-document command requires a filename")
                print("Usage: ./tools/vdb.sh delete-document <filename>")
                cleanup_and_exit(manager, 1)

            filename = sys.argv[2]
            print_emoji_status(
                "warning",
                f"This will delete document '{filename}' and ALL its chunks and extracted images!",
            )

            # Show what will be deleted
            try:
                stats = manager.get_virtual_structure_stats()
                if "error" not in stats:
                    # Find the specific document in the groups
                    doc_groups_result = manager.list_document_groups()
                    if doc_groups_result["status"] == "success":
                        matching_group = None
                        for group in doc_groups_result["groups"]:
                            if group["original_filename"] == filename:
                                matching_group = group
                                break

                        if matching_group:
                            print(f"Document: {filename}")
                            print(
                                f"  - Chunks to delete: {len(matching_group['chunks'])}"
                            )

                            # Check for extracted images
                            image_groups_result = manager.list_image_groups()
                            if image_groups_result["status"] == "success":
                                matching_image_group = None
                                for group in image_groups_result["groups"]:
                                    if group["pdf_filename"] == filename:
                                        matching_image_group = group
                                        break

                                if matching_image_group:
                                    print(
                                        f"  - Extracted images to delete: {len(matching_image_group['images'])}"
                                    )
                                else:
                                    print("  - Extracted images to delete: 0")
                            else:
                                print("  - Extracted images to delete: unknown")
                        else:
                            print(f"Document '{filename}' not found in document groups")
                    else:
                        print(
                            f"Could not retrieve document groups: {doc_groups_result['error']}"
                        )
                else:
                    print(f"Could not retrieve virtual structure: {stats['error']}")
            except Exception as e:
                print(f"Could not preview deletion: {e}")

            confirm = input("Are you sure you want to continue? (yes/no): ")
            if confirm.lower() in ["yes", "y"]:
                result = manager.delete_document_by_filename(filename)
                if result["status"] == "success":
                    print_emoji_status("delete", result["message"])
                    print(f"  - Deleted documents/chunks: {result['deleted_docs']}")
                    print(f"  - Deleted images: {result['deleted_images']}")
                    if result.get("storage_deleted", 0) > 0:
                        print(f"  - Deleted from storage: {result['storage_deleted']}")
                else:
                    print_emoji_status("error", result["message"])
            else:
                print_emoji_status("info", "Operation cancelled")

        elif command == "collections":
            if len(sys.argv) < 3:
                print("❌ Error: collections command requires additional arguments")
                cleanup_and_exit(manager, 1)

            subcommand = sys.argv[2]

            if subcommand == "--list":
                collections = manager.list_collections()
                print_emoji_status("list", "VDB Collections:")
                print(f"  Text: {collections['text_collection']['name']}")
                print(f"  Image: {collections['image_collection']['name']}")

                # Show virtual structure summary
                print()
                print_emoji_status("info", "Virtual Structure Summary:")
                try:
                    stats = manager.get_virtual_structure_stats()
                    if "error" not in stats:
                        print(f"  📄 Total Chunks: {stats['total_chunks']}")
                        print(f"  🖼️  Grouped Images: {stats['grouped_images']}")
                        print(
                            f"  📁 Individual Documents: {stats['individual_documents']}"
                        )
                        print(f"  🖼️  Individual Images: {stats['individual_images']}")
                    else:
                        print(
                            f"  ⚠️  Could not retrieve virtual structure: {stats['error']}"
                        )
                except Exception as e:
                    print(f"  ⚠️  Could not retrieve virtual structure: {e}")

            elif subcommand == "--text":
                if len(sys.argv) < 4:
                    print(
                        "❌ Error: --text requires additional argument (--list or --delete)"
                    )
                    cleanup_and_exit(manager, 1)

                action = sys.argv[3]

                if action == "--list":
                    result = manager.list_text_documents()
                    if result["status"] == "success":
                        print_emoji_status(
                            "list",
                            f"Text Collection Documents ({result['count']} found):",
                        )
                        for i, doc in enumerate(
                            result["documents"][:10], 1
                        ):  # Show first 10
                            print(f"  {i}. ID: {doc['id']}")

                            # Show better source information from metadata
                            metadata = doc.get("metadata", {})
                            source = metadata.get("source", "")
                            filename = metadata.get("filename", "")

                            if source:
                                print(f"     Source: {source}")
                            elif filename:
                                print(f"     Filename: {filename}")
                            elif doc.get("url"):
                                print(f"     URL: {doc.get('url')}")
                            else:
                                print("     Source: N/A")

                            # Show document type if available
                            doc_type = metadata.get("type", "")
                            if doc_type:
                                print(f"     Type: {doc_type}")

                            # Show text preview
                            text = doc.get("text", "")
                            if text:
                                print(f"     Text: {text[:100]}...")

                            print()
                        if result["count"] > 10:
                            print(f"  ... and {result['count'] - 10} more documents")
                    else:
                        print_emoji_status(
                            "error", f"Failed to list text documents: {result['error']}"
                        )

                elif action == "--delete":
                    print_emoji_status(
                        "warning",
                        "This will delete ALL documents in the text collection!",
                    )
                    print(f"Collection: {manager.text_collection_name}")

                    # Get current count
                    count_result = manager.list_text_documents(limit=1)
                    if count_result["status"] == "success":
                        print(f"Current document count: {count_result['count']}")

                    confirm = input("Are you sure you want to continue? (yes/no): ")
                    if confirm.lower() in ["yes", "y"]:
                        result = manager.delete_text_collection_content()
                        if result["status"] == "success":
                            print_emoji_status("delete", result["message"])
                        else:
                            print_emoji_status(
                                "error",
                                f"Failed to delete text collection: {result['error']}",
                            )
                    else:
                        print_emoji_status("info", "Operation cancelled")

            elif subcommand == "--image":
                if len(sys.argv) < 4:
                    print(
                        "❌ Error: --image requires additional argument (--list or --delete)"
                    )
                    cleanup_and_exit(manager, 1)

                action = sys.argv[3]

                if action == "--list":
                    result = manager.list_image_documents()
                    if result["status"] == "success":
                        print_emoji_status(
                            "list",
                            f"Image Collection Images ({result['count']} found):",
                        )
                        for i, doc in enumerate(
                            result["documents"][:10], 1
                        ):  # Show first 10
                            print(f"  {i}. ID: {doc['id']}")

                            # Show better source information from metadata
                            metadata = doc.get("metadata", {})
                            source = metadata.get("source", "")
                            filename = metadata.get("filename", "")

                            if source:
                                print(f"     Source: {source}")
                            elif filename:
                                print(f"     Filename: {filename}")
                            elif doc.get("url"):
                                print(f"     URL: {doc.get('url')}")
                            else:
                                print("     Source: N/A")

                            # Show image classification if available
                            classification = metadata.get("classification", {})
                            if classification and not classification.get("error"):
                                top_prediction = classification.get(
                                    "top_prediction", {}
                                )
                                if top_prediction:
                                    label = top_prediction.get("label", "Unknown")
                                    confidence = top_prediction.get("confidence", 0)
                                    print(
                                        f"     Classification: {label} ({confidence:.2%})"
                                    )

                            # Show image data status
                            print(
                                f"     Has Image Data: {'Yes' if doc.get('image_data') else 'No'}"
                            )

                            print()
                        if result["count"] > 10:
                            print(f"  ... and {result['count'] - 10} more documents")
                    else:
                        print_emoji_status(
                            "error",
                            f"Failed to list image documents: {result['error']}",
                        )

                elif action == "--delete":
                    print_emoji_status(
                        "warning",
                        "This will delete ALL documents in the image collection!",
                    )
                    print(f"Collection: {manager.image_collection_name}")

                    # Get current count
                    count_result = manager.list_image_documents(limit=1)
                    if count_result["status"] == "success":
                        print(f"Current document count: {count_result['count']}")

                    confirm = input("Are you sure you want to continue? (yes/no): ")
                    if confirm.lower() in ["yes", "y"]:
                        result = manager.delete_image_collection_content()
                        if result["status"] == "success":
                            print_emoji_status("delete", result["message"])
                        else:
                            print_emoji_status(
                                "error",
                                f"Failed to delete image collection: {result['error']}",
                            )
                    else:
                        print_emoji_status("info", "Operation cancelled")
            else:
                print("❌ Error: Unknown collections subcommand")
                cleanup_and_exit(manager, 1)
        else:
            print("❌ Error: Unknown command")
            print("Use './tools/vdb.sh help' for usage information")
            cleanup_and_exit(manager, 1)

    except Exception as e:
        print_emoji_status("error", f"Unexpected error: {e}")
        cleanup_and_exit(manager, 1)
    finally:
        # Ensure cleanup happens even if there's an exception
        try:
            manager.cleanup()
        except Exception:
            pass  # Ignore cleanup errors


if __name__ == "__main__":
    main()
