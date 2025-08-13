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

        text_vdb = None
        image_vdb = None

        try:
            # Test text collection
            text_vdb = create_vector_database(collection_name=self.text_collection_name)
            text_count = text_vdb.count_documents()
            results["collections"]["text"] = {
                "name": self.text_collection_name,
                "status": "healthy",
                "document_count": text_count,
            }
        except Exception as e:
            results["collections"]["text"] = {
                "name": self.text_collection_name,
                "status": "error",
                "error": str(e),
            }
            results["errors"].append(f"Text collection error: {e}")
        finally:
            # Clean up text VDB connection
            if text_vdb:
                try:
                    text_vdb.cleanup()
                except Exception:
                    pass

        try:
            # Test image collection
            image_vdb = create_vector_database(
                collection_name=self.image_collection_name
            )
            image_count = image_vdb.count_documents()
            results["collections"]["image"] = {
                "name": self.image_collection_name,
                "status": "healthy",
                "document_count": image_count,
            }
        except Exception as e:
            results["collections"]["image"] = {
                "name": self.image_collection_name,
                "status": "error",
                "error": str(e),
            }
            results["errors"].append(f"Image collection error: {e}")
        finally:
            # Clean up image VDB connection
            if image_vdb:
                try:
                    image_vdb.cleanup()
                except Exception:
                    pass

        # Overall status
        if results["errors"]:
            results["status"] = "unhealthy"
        else:
            results["status"] = "healthy"

        return results

    def list_collections(self) -> dict[str, Any]:
        """List collection names and basic info."""
        return {
            "text_collection": {"name": self.text_collection_name, "type": "text"},
            "image_collection": {"name": self.image_collection_name, "type": "image"},
        }

    def list_text_documents(self, limit: int = 50) -> dict[str, Any]:
        """List documents in the text collection."""
        text_vdb = None
        try:
            text_vdb = create_vector_database(collection_name=self.text_collection_name)
            documents = text_vdb.list_documents(limit=limit, offset=0)

            return {
                "status": "success",
                "collection": self.text_collection_name,
                "count": len(documents),
                "documents": documents,
            }
        except Exception as e:
            return {
                "status": "error",
                "collection": self.text_collection_name,
                "error": str(e),
            }
        finally:
            # Clean up VDB connection
            if text_vdb:
                try:
                    text_vdb.cleanup()
                except Exception:
                    pass

    def list_image_documents(self, limit: int = 50) -> dict[str, Any]:
        """List documents in the image collection."""
        image_vdb = None
        try:
            image_vdb = create_vector_database(
                collection_name=self.image_collection_name
            )
            documents = image_vdb.list_documents(limit=limit, offset=0)

            return {
                "status": "success",
                "collection": self.image_collection_name,
                "count": len(documents),
                "documents": documents,
            }
        except Exception as e:
            return {
                "status": "error",
                "collection": self.image_collection_name,
                "error": str(e),
            }
        finally:
            # Clean up VDB connection
            if image_vdb:
                try:
                    image_vdb.cleanup()
                except Exception:
                    pass

    def delete_text_collection_content(self) -> dict[str, Any]:
        """Delete all content from the text collection."""
        text_vdb = None
        try:
            text_vdb = create_vector_database(collection_name=self.text_collection_name)

            # Get all documents first to show what will be deleted
            all_docs = text_vdb.list_documents(limit=10000, offset=0)
            doc_count = len(all_docs)

            if doc_count == 0:
                return {
                    "status": "success",
                    "collection": self.text_collection_name,
                    "message": "Collection is already empty",
                    "deleted_count": 0,
                }

            # Delete each document
            deleted_count = 0
            for doc in all_docs:
                try:
                    text_vdb.delete_document(doc["id"])
                    deleted_count += 1
                except Exception as e:
                    print(f"Warning: Failed to delete document {doc['id']}: {e}")

            return {
                "status": "success",
                "collection": self.text_collection_name,
                "message": f"Successfully deleted {deleted_count} documents",
                "deleted_count": deleted_count,
            }
        except Exception as e:
            return {
                "status": "error",
                "collection": self.text_collection_name,
                "error": str(e),
            }
        finally:
            # Clean up VDB connection
            if text_vdb:
                try:
                    text_vdb.cleanup()
                except Exception:
                    pass

    def delete_image_collection_content(self) -> dict[str, Any]:
        """Delete all content from the image collection."""
        image_vdb = None
        try:
            image_vdb = create_vector_database(
                collection_name=self.image_collection_name
            )

            # Get all documents first to show what will be deleted
            all_docs = image_vdb.list_documents(limit=10000, offset=0)
            doc_count = len(all_docs)

            if doc_count == 0:
                return {
                    "status": "success",
                    "collection": self.image_collection_name,
                    "message": "Collection is already empty",
                    "deleted_count": 0,
                }

            # Delete each document
            deleted_count = 0
            for doc in all_docs:
                try:
                    image_vdb.delete_document(doc["id"])
                    deleted_count += 1
                except Exception as e:
                    print(f"Warning: Failed to delete document {doc['id']}: {e}")

            return {
                "status": "success",
                "collection": self.image_collection_name,
                "message": f"Successfully deleted {deleted_count} documents",
                "deleted_count": deleted_count,
            }
        except Exception as e:
            return {
                "status": "error",
                "collection": self.image_collection_name,
                "error": str(e),
            }
        finally:
            # Clean up VDB connection
            if image_vdb:
                try:
                    image_vdb.cleanup()
                except Exception:
                    pass


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
                    print_emoji_status(
                        "success",
                        f"{coll_type.title()} Collection: {coll_info['name']} ({coll_info['document_count']} documents)",
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

        elif command == "collections":
            if len(sys.argv) < 3:
                print("❌ Error: collections command requires additional arguments")
                sys.exit(1)

            subcommand = sys.argv[2]

            if subcommand == "--list":
                collections = manager.list_collections()
                print_emoji_status("list", "VDB Collections:")
                print(f"  Text: {collections['text_collection']['name']}")
                print(f"  Image: {collections['image_collection']['name']}")

            elif subcommand == "--text":
                if len(sys.argv) < 4:
                    print(
                        "❌ Error: --text requires additional argument (--list or --delete)"
                    )
                    sys.exit(1)

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
                    sys.exit(1)

                action = sys.argv[3]

                if action == "--list":
                    result = manager.list_image_documents()
                    if result["status"] == "success":
                        print_emoji_status(
                            "list",
                            f"Image Collection Documents ({result['count']} found):",
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
                sys.exit(1)
        else:
            print("❌ Error: Unknown command")
            print("Use './tools/vdb.sh help' for usage information")
            sys.exit(1)

    except Exception as e:
        print_emoji_status("error", f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
