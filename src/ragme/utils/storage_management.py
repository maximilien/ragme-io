#!/usr/bin/env python3
"""
Storage Management CLI for RAGme.io
Provides commands to manage storage content with proper confirmations
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    from ragme.utils.config_manager import ConfigManager
    from ragme.utils.storage import StorageService
except ImportError:
    print(
        "❌ Error: Could not import required modules. Make sure you're running from the project root."
    )
    sys.exit(1)


class StorageManager:
    """CLI interface for storage management"""

    def __init__(self):
        """Initialize storage manager"""
        try:
            self.config = ConfigManager()
            self.storage = StorageService(self.config)
            self.storage_config = self.config.get("storage", {})
            self.storage_type = self.storage_config.get("type", "minio")
        except Exception as e:
            print(f"❌ Error initializing storage service: {e}")
            print("💡 Make sure your storage service is configured and running")
            sys.exit(1)

    def check_storage_health(self) -> bool:
        """Check if storage service is accessible"""
        try:
            # Try to list files to test connectivity
            self.storage.list_files(prefix="", recursive=False)
            return True
        except Exception as e:
            print(f"❌ Storage service not accessible: {e}")
            return False

    def list_buckets(self, show_details: bool = False):
        """List all available buckets"""
        try:
            buckets = self.storage.list_buckets()

            if not buckets:
                print("📦 No buckets found")
                return

            print(f"📦 Found {len(buckets)} bucket(s):")
            print()

            for bucket_info in buckets:
                name = bucket_info["name"]
                size = bucket_info.get("size", 0)
                creation_date = bucket_info.get("creation_date")

                # Format size
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"

                # Format date
                if isinstance(creation_date, datetime):
                    date_str = creation_date.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    date_str = str(creation_date) if creation_date else "Unknown"

                if show_details:
                    print(f"  📦 {name}")
                    print(f"     Size: {size_str}")
                    print(f"     Created: {date_str}")
                    print()
                else:
                    print(f"  📦 {name} ({size_str}, {date_str})")

        except Exception as e:
            print(f"❌ Error listing buckets: {e}")
            sys.exit(1)

    def list_files(
        self,
        prefix: str = "",
        recursive: bool = True,
        show_details: bool = False,
        bucket_name: str | None = None,
        all_buckets: bool = False,
    ):
        """List files in storage"""
        try:
            if all_buckets:
                # List files from all buckets
                buckets = self.storage.list_buckets()
                if not buckets:
                    print("📁 No buckets found")
                    return

                total_files = 0
                for bucket_info in buckets:
                    bucket_name = bucket_info["name"]
                    print(f"📦 Bucket: {bucket_name}")
                    print("-" * (len(bucket_name) + 8))

                    try:
                        files = self.storage.list_files_in_bucket(
                            bucket_name, prefix=prefix, recursive=recursive
                        )
                        if files:
                            for file_info in files:
                                total_files += 1
                                name = file_info["name"]
                                size = file_info["size"]
                                last_modified = file_info["last_modified"]

                                # Format size
                                if size < 1024:
                                    size_str = f"{size} B"
                                elif size < 1024 * 1024:
                                    size_str = f"{size / 1024:.1f} KB"
                                else:
                                    size_str = f"{size / (1024 * 1024):.1f} MB"

                                # Format date
                                if isinstance(last_modified, datetime):
                                    date_str = last_modified.strftime(
                                        "%Y-%m-%d %H:%M:%S"
                                    )
                                else:
                                    date_str = str(last_modified)

                                if show_details:
                                    print(f"  📄 {name}")
                                    print(f"     Size: {size_str}")
                                    print(f"     Modified: {date_str}")
                                    print()
                                else:
                                    print(f"  📄 {name} ({size_str}, {date_str})")
                        else:
                            print("  📁 No files found")
                        print()
                    except Exception as e:
                        print(f"  ❌ Error accessing bucket {bucket_name}: {e}")
                        print()

                print(f"📁 Total files across all buckets: {total_files}")

            elif bucket_name:
                # List files from specific bucket
                if not self.storage.bucket_exists(bucket_name):
                    print(f"❌ Bucket not found: {bucket_name}")
                    return

                files = self.storage.list_files_in_bucket(
                    bucket_name, prefix=prefix, recursive=recursive
                )
                if not files:
                    print(f"📁 No files found in bucket '{bucket_name}'")
                    return

                print(f"📁 Found {len(files)} file(s) in bucket '{bucket_name}':")
                print()

                for file_info in files:
                    name = file_info["name"]
                    size = file_info["size"]
                    last_modified = file_info["last_modified"]

                    # Format size
                    if size < 1024:
                        size_str = f"{size} B"
                    elif size < 1024 * 1024:
                        size_str = f"{size / 1024:.1f} KB"
                    else:
                        size_str = f"{size / (1024 * 1024):.1f} MB"

                    # Format date
                    if isinstance(last_modified, datetime):
                        date_str = last_modified.strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        date_str = str(last_modified)

                    if show_details:
                        print(f"  📄 {name}")
                        print(f"     Size: {size_str}")
                        print(f"     Modified: {date_str}")
                        print()
                    else:
                        print(f"  📄 {name} ({size_str}, {date_str})")

            else:
                # List files from default bucket (existing behavior)
                files = self.storage.list_files(prefix=prefix, recursive=recursive)

                if not files:
                    print("📁 No files found in storage")
                    return

                print(f"📁 Found {len(files)} file(s) in storage:")
                print()

                for file_info in files:
                    name = file_info["name"]
                    size = file_info["size"]
                    last_modified = file_info["last_modified"]

                    # Format size
                    if size < 1024:
                        size_str = f"{size} B"
                    elif size < 1024 * 1024:
                        size_str = f"{size / 1024:.1f} KB"
                    else:
                        size_str = f"{size / (1024 * 1024):.1f} MB"

                    # Format date
                    if isinstance(last_modified, datetime):
                        date_str = last_modified.strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        date_str = str(last_modified)

                    if show_details:
                        print(f"  📄 {name}")
                        print(f"     Size: {size_str}")
                        print(f"     Modified: {date_str}")
                        print()
                    else:
                        print(f"  📄 {name} ({size_str}, {date_str})")

        except Exception as e:
            print(f"❌ Error listing files: {e}")
            sys.exit(1)

    def show_links(self, object_name: str | None = None, expires_in: int = 3600):
        """Show download links for files"""
        try:
            if object_name:
                # Show link for specific file
                if not self.storage.file_exists(object_name):
                    print(f"❌ File not found: {object_name}")
                    return

                url = self.storage.get_file_url(object_name, expires_in)
                print(f"🔗 Download link for '{object_name}':")
                print(f"   {url}")
                print(f"   Expires in: {expires_in} seconds")
            else:
                # Show links for all files
                files = self.storage.list_files(prefix="", recursive=True)

                if not files:
                    print("📁 No files found in storage")
                    return

                print(f"🔗 Download links for {len(files)} file(s):")
                print()

                for file_info in files:
                    name = file_info["name"]
                    url = self.storage.get_file_url(name, expires_in)
                    print(f"  📄 {name}")
                    print(f"     {url}")
                    print()

        except Exception as e:
            print(f"❌ Error generating links: {e}")
            sys.exit(1)

    def delete_file(
        self, object_name: str, force: bool = False, bucket_name: str | None = None
    ):
        """Delete a single file from storage"""
        try:
            if bucket_name:
                # Delete from specific bucket
                if not self.storage.bucket_exists(bucket_name):
                    print(f"❌ Bucket not found: {bucket_name}")
                    return

                # Check if file exists in bucket
                files = self.storage.list_files_in_bucket(
                    bucket_name, prefix=object_name, recursive=False
                )
                file_exists = any(f["name"] == object_name for f in files)

                if not file_exists:
                    print(f"❌ File not found: {object_name} in bucket {bucket_name}")
                    return

                if not force:
                    print(
                        f"🗑️  About to delete: {object_name} from bucket {bucket_name}"
                    )
                    confirm = input("   Are you sure? (yes/no): ").strip().lower()
                    if confirm not in ["yes", "y"]:
                        print("❌ Deletion cancelled")
                        return

                success = self.storage.delete_file_from_bucket(bucket_name, object_name)
                if success:
                    print(f"✅ Deleted: {object_name} from bucket {bucket_name}")
                else:
                    print(
                        f"❌ Failed to delete: {object_name} from bucket {bucket_name}"
                    )

            else:
                # Delete from default bucket (existing behavior)
                if not self.storage.file_exists(object_name):
                    print(f"❌ File not found: {object_name}")
                    return

                if not force:
                    # Get file info for confirmation
                    file_info = self.storage.get_file_info(object_name)
                    size = file_info["size"]

                    if size < 1024:
                        size_str = f"{size} B"
                    elif size < 1024 * 1024:
                        size_str = f"{size / 1024:.1f} KB"
                    else:
                        size_str = f"{size / (1024 * 1024):.1f} MB"

                    print(f"🗑️  About to delete: {object_name}")
                    print(f"   Size: {size_str}")
                    print(f"   Type: {file_info.get('content_type', 'Unknown')}")

                    confirm = input("   Are you sure? (yes/no): ").strip().lower()
                    if confirm not in ["yes", "y"]:
                        print("❌ Deletion cancelled")
                        return

                self.storage.delete_file(object_name)
                print(f"✅ Deleted: {object_name}")

        except Exception as e:
            print(f"❌ Error deleting file: {e}")
            sys.exit(1)

    def delete_all_files(
        self,
        force: bool = False,
        prefix: str = "",
        bucket_name: str | None = None,
        all_buckets: bool = False,
    ):
        """Delete all files from storage"""
        try:
            if all_buckets:
                # Delete from all buckets
                buckets = self.storage.list_buckets()
                if not buckets:
                    print("📁 No buckets found")
                    return

                total_files = 0
                total_size = 0
                all_files = []

                for bucket_info in buckets:
                    bucket_name = bucket_info["name"]
                    try:
                        files = self.storage.list_files_in_bucket(
                            bucket_name, prefix=prefix, recursive=True
                        )
                        for file_info in files:
                            file_info["bucket"] = bucket_name
                            all_files.append(file_info)
                            total_files += 1
                            total_size += file_info["size"]
                    except Exception as e:
                        print(f"⚠️  Could not access bucket {bucket_name}: {e}")

                if not all_files:
                    print("📁 No files found to delete")
                    return

                if total_size < 1024:
                    size_str = f"{total_size} B"
                elif total_size < 1024 * 1024:
                    size_str = f"{total_size / 1024:.1f} KB"
                else:
                    size_str = f"{total_size / (1024 * 1024):.1f} MB"

                if not force:
                    print(
                        f"🗑️  About to delete {total_files} file(s) from {len(buckets)} bucket(s)"
                    )
                    print(f"   Total size: {size_str}")
                    if prefix:
                        print(f"   Prefix filter: {prefix}")

                    confirm = (
                        input(
                            "   Are you sure? This action cannot be undone! (yes/no): "
                        )
                        .strip()
                        .lower()
                    )
                    if confirm not in ["yes", "y"]:
                        print("❌ Deletion cancelled")
                        return

                deleted_count = 0
                for file_info in all_files:
                    try:
                        success = self.storage.delete_file_from_bucket(
                            file_info["bucket"], file_info["name"]
                        )
                        if success:
                            deleted_count += 1
                            print(
                                f"   ✅ Deleted: {file_info['name']} from {file_info['bucket']}"
                            )
                        else:
                            print(
                                f"   ❌ Failed to delete {file_info['name']} from {file_info['bucket']}"
                            )
                    except Exception as e:
                        print(
                            f"   ❌ Failed to delete {file_info['name']} from {file_info['bucket']}: {e}"
                        )

                print(
                    f"✅ Successfully deleted {deleted_count}/{total_files} files from {len(buckets)} bucket(s)"
                )

            elif bucket_name:
                # Delete from specific bucket
                if not self.storage.bucket_exists(bucket_name):
                    print(f"❌ Bucket not found: {bucket_name}")
                    return

                files = self.storage.list_files_in_bucket(
                    bucket_name, prefix=prefix, recursive=True
                )

                if not files:
                    print(f"📁 No files found to delete in bucket '{bucket_name}'")
                    return

                total_size = sum(f["size"] for f in files)
                if total_size < 1024:
                    size_str = f"{total_size} B"
                elif total_size < 1024 * 1024:
                    size_str = f"{total_size / 1024:.1f} KB"
                else:
                    size_str = f"{total_size / (1024 * 1024):.1f} MB"

                if not force:
                    print(
                        f"🗑️  About to delete {len(files)} file(s) from bucket '{bucket_name}'"
                    )
                    print(f"   Total size: {size_str}")
                    if prefix:
                        print(f"   Prefix filter: {prefix}")

                    confirm = (
                        input(
                            "   Are you sure? This action cannot be undone! (yes/no): "
                        )
                        .strip()
                        .lower()
                    )
                    if confirm not in ["yes", "y"]:
                        print("❌ Deletion cancelled")
                        return

                deleted_count = 0
                for file_info in files:
                    try:
                        success = self.storage.delete_file_from_bucket(
                            bucket_name, file_info["name"]
                        )
                        if success:
                            deleted_count += 1
                            print(f"   ✅ Deleted: {file_info['name']}")
                        else:
                            print(f"   ❌ Failed to delete {file_info['name']}")
                    except Exception as e:
                        print(f"   ❌ Failed to delete {file_info['name']}: {e}")

                print(
                    f"✅ Successfully deleted {deleted_count}/{len(files)} files from bucket '{bucket_name}'"
                )

            else:
                # Delete from default bucket (existing behavior)
                files = self.storage.list_files(prefix=prefix, recursive=True)

                if not files:
                    print("📁 No files found to delete")
                    return

                total_size = sum(f["size"] for f in files)
                if total_size < 1024:
                    size_str = f"{total_size} B"
                elif total_size < 1024 * 1024:
                    size_str = f"{total_size / 1024:.1f} KB"
                else:
                    size_str = f"{total_size / (1024 * 1024):.1f} MB"

                if not force:
                    print(f"🗑️  About to delete {len(files)} file(s) from storage")
                    print(f"   Total size: {size_str}")
                    if prefix:
                        print(f"   Prefix filter: {prefix}")

                    confirm = (
                        input(
                            "   Are you sure? This action cannot be undone! (yes/no): "
                        )
                        .strip()
                        .lower()
                    )
                    if confirm not in ["yes", "y"]:
                        print("❌ Deletion cancelled")
                        return

                deleted_count = 0
                for file_info in files:
                    try:
                        self.storage.delete_file(file_info["name"])
                        deleted_count += 1
                        print(f"   ✅ Deleted: {file_info['name']}")
                    except Exception as e:
                        print(f"   ❌ Failed to delete {file_info['name']}: {e}")

                print(f"✅ Successfully deleted {deleted_count}/{len(files)} files")

        except Exception as e:
            print(f"❌ Error deleting files: {e}")
            sys.exit(1)

    def show_info(self):
        """Show storage configuration and status"""
        try:
            print("📊 Storage Information")
            print("=====================")
            print(f"Type: {self.storage_type}")

            if self.storage_type == "minio":
                minio_config = self.storage_config.get("minio", {})
                print(f"Endpoint: {minio_config.get('endpoint', 'N/A')}")
                print(f"Bucket: {minio_config.get('bucket_name', 'N/A')}")
                print(f"Secure: {minio_config.get('secure', False)}")
            elif self.storage_type == "s3":
                s3_config = self.storage_config.get("s3", {})
                print(f"Endpoint: {s3_config.get('endpoint', 'N/A')}")
                print(f"Bucket: {s3_config.get('bucket_name', 'N/A')}")
                print(f"Region: {s3_config.get('region', 'N/A')}")
            elif self.storage_type == "local":
                local_config = self.storage_config.get("local", {})
                print(f"Path: {local_config.get('path', 'N/A')}")

            print()

            # Test connectivity
            if self.check_storage_health():
                print("✅ Storage service is accessible")

                # Get file count
                files = self.storage.list_files(prefix="", recursive=True)
                total_size = sum(f["size"] for f in files)

                if total_size < 1024:
                    size_str = f"{total_size} B"
                elif total_size < 1024 * 1024:
                    size_str = f"{total_size / 1024:.1f} KB"
                else:
                    size_str = f"{total_size / (1024 * 1024):.1f} MB"

                print(f"📁 Total files: {len(files)}")
                print(f"💾 Total size: {size_str}")
            else:
                print("❌ Storage service is not accessible")

        except Exception as e:
            print(f"❌ Error getting storage info: {e}")
            sys.exit(1)

    def check_health(self, verbose: bool = False):
        """Check storage service health and connectivity"""
        try:
            print("🏥 Storage Health Check")
            print("======================")

            # Check configuration
            print("📋 Configuration:")
            print(f"   Type: {self.storage_type}")

            if self.storage_type == "minio":
                minio_config = self.storage_config.get("minio", {})
                endpoint = minio_config.get("endpoint", "N/A")
                bucket = minio_config.get("bucket_name", "N/A")
                secure = minio_config.get("secure", False)
                print(f"   Endpoint: {endpoint}")
                print(f"   Bucket: {bucket}")
                print(f"   Secure: {secure}")
            elif self.storage_type == "s3":
                s3_config = self.storage_config.get("s3", {})
                endpoint = s3_config.get("endpoint", "N/A")
                bucket = s3_config.get("bucket_name", "N/A")
                region = s3_config.get("region", "N/A")
                print(f"   Endpoint: {endpoint}")
                print(f"   Bucket: {bucket}")
                print(f"   Region: {region}")
            elif self.storage_type == "local":
                local_config = self.storage_config.get("local", {})
                path = local_config.get("path", "N/A")
                print(f"   Path: {path}")

            print()

            # Test connectivity
            print("🔌 Connectivity Test:")
            if self.check_storage_health():
                print("   ✅ Storage service is accessible")

                # Test basic operations
                print("   🔄 Testing basic operations...")

                # Test list operation
                try:
                    files = self.storage.list_files(prefix="", recursive=False)
                    print("   ✅ List operation: OK")
                    if verbose:
                        print(f"      Found {len(files)} files")
                except Exception as e:
                    print(f"   ❌ List operation: FAILED - {e}")

                # Test bucket/container access
                try:
                    if self.storage_type == "minio":
                        # For MinIO, check if bucket exists
                        if self.storage.client.bucket_exists(self.storage.bucket_name):
                            print("   ✅ Bucket access: OK")
                        else:
                            print(
                                "   ⚠️  Bucket access: WARNING - Bucket does not exist"
                            )
                    elif self.storage_type == "s3":
                        # For S3, try to list objects
                        self.storage.client.list_objects_v2(
                            Bucket=self.storage.bucket_name, MaxKeys=1
                        )
                        print("   ✅ Bucket access: OK")
                    elif self.storage_type == "local":
                        # For local, check if directory exists
                        if self.storage.storage_path.exists():
                            print("   ✅ Directory access: OK")
                        else:
                            print(
                                "   ⚠️  Directory access: WARNING - Directory does not exist"
                            )
                except Exception as e:
                    print(f"   ❌ Bucket access: FAILED - {e}")

                # Show available buckets
                try:
                    buckets = self.storage.list_buckets()
                    if buckets:
                        print("   📦 Available buckets:")
                        for bucket_info in buckets:
                            name = bucket_info["name"]
                            size = bucket_info.get("size", 0)
                            if size < 1024:
                                size_str = f"{size} B"
                            elif size < 1024 * 1024:
                                size_str = f"{size / 1024:.1f} KB"
                            else:
                                size_str = f"{size / (1024 * 1024):.1f} MB"
                            print(f"      - {name} ({size_str})")
                    else:
                        print("   📦 No buckets found")
                except Exception as e:
                    print(f"   ❌ Bucket listing: FAILED - {e}")

                # Test URL generation (if supported)
                try:
                    if self.storage_type in ["minio", "s3"]:
                        # Try to generate a test URL
                        test_url = self.storage.get_file_url(
                            "test-health-check", expires_in=60
                        )
                        print("   ✅ URL generation: OK")
                        if verbose:
                            print(f"      Test URL: {test_url}")
                    elif self.storage_type == "local":
                        # Test URL generation for local storage
                        test_url = self.storage.get_file_url(
                            "test-health-check", expires_in=60
                        )
                        print("   ✅ URL generation: OK")
                        if verbose:
                            print(f"      Test URL: {test_url}")
                    else:
                        print(
                            "   ⏭️  URL generation: SKIPPED (not supported for this storage type)"
                        )
                except Exception as e:
                    print(f"   ❌ URL generation: FAILED - {e}")

                print()
                print("🎉 Health check completed successfully!")
                print("   Storage service is healthy and ready for use.")

            else:
                print("   ❌ Storage service is not accessible")
                print()
                print("💡 Troubleshooting tips:")
                print("   - Check if your storage service (MinIO/S3) is running")
                print("   - Verify your configuration in config.yaml")
                print("   - Check network connectivity to the storage endpoint")
                print("   - Ensure credentials are correct")
                if self.storage_type == "minio":
                    print("   - For MinIO, try: docker ps | grep minio")
                elif self.storage_type == "s3":
                    print(
                        "   - For S3, check your AWS credentials and bucket permissions"
                    )

        except Exception as e:
            print(f"❌ Error during health check: {e}")
            sys.exit(1)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="RAGme Storage Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s info                           # Show storage configuration and status
  %(prog)s health                         # Check storage service health and connectivity
  %(prog)s health --verbose               # Check health with verbose output
  %(prog)s list                           # List all files in storage
  %(prog)s list --details                 # List files with detailed information
  %(prog)s list --prefix "documents/"     # List files with specific prefix
  %(prog)s links                          # Show download links for all files
  %(prog)s links document.pdf             # Show download link for specific file
  %(prog)s delete document.pdf            # Delete specific file (with confirmation)
  %(prog)s delete document.pdf --force    # Delete specific file without confirmation
  %(prog)s delete-all                     # Delete all files (with confirmation)
  %(prog)s delete-all --force             # Delete all files without confirmation
  %(prog)s delete-all --prefix "temp/"    # Delete files with specific prefix
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Info command
    subparsers.add_parser("info", help="Show storage configuration and status")

    # Health command
    health_parser = subparsers.add_parser(
        "health", help="Check storage service health and connectivity"
    )
    health_parser.add_argument(
        "--verbose", action="store_true", help="Show verbose output"
    )

    # Buckets command
    buckets_parser = subparsers.add_parser("buckets", help="List all available buckets")
    buckets_parser.add_argument(
        "--details", action="store_true", help="Show detailed bucket information"
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List files in storage")
    list_parser.add_argument(
        "--details", action="store_true", help="Show detailed file information"
    )
    list_parser.add_argument("--prefix", default="", help="Filter files by prefix")
    list_parser.add_argument(
        "--no-recursive", action="store_true", help="Don't list recursively"
    )
    list_parser.add_argument("--bucket", help="List files from specific bucket")
    list_parser.add_argument(
        "--all", action="store_true", help="List files from all buckets"
    )

    # Links command
    links_parser = subparsers.add_parser("links", help="Show download links for files")
    links_parser.add_argument(
        "object_name", nargs="?", help="Specific file name (optional)"
    )
    links_parser.add_argument(
        "--expires",
        type=int,
        default=3600,
        help="Link expiration time in seconds (default: 3600)",
    )

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a specific file")
    delete_parser.add_argument("object_name", help="Name of the file to delete")
    delete_parser.add_argument("--force", action="store_true", help="Skip confirmation")
    delete_parser.add_argument("--bucket", help="Delete from specific bucket")

    # Delete all command
    delete_all_parser = subparsers.add_parser("delete-all", help="Delete all files")
    delete_all_parser.add_argument(
        "--force", action="store_true", help="Skip confirmation"
    )
    delete_all_parser.add_argument(
        "--prefix", default="", help="Only delete files with specific prefix"
    )
    delete_all_parser.add_argument("--bucket", help="Delete from specific bucket")
    delete_all_parser.add_argument(
        "--all", action="store_true", help="Delete from all buckets"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize storage manager
    manager = StorageManager()

    # Execute command
    if args.command == "info":
        manager.show_info()
    elif args.command == "health":
        manager.check_health(args.verbose)
    elif args.command == "buckets":
        manager.list_buckets(args.details)
    elif args.command == "list":
        manager.list_files(
            prefix=args.prefix,
            recursive=not args.no_recursive,
            show_details=args.details,
            bucket_name=args.bucket,
            all_buckets=args.all,
        )
    elif args.command == "links":
        manager.show_links(args.object_name, args.expires)
    elif args.command == "delete":
        manager.delete_file(args.object_name, args.force, args.bucket)
    elif args.command == "delete-all":
        manager.delete_all_files(args.force, args.prefix, args.bucket, args.all)


if __name__ == "__main__":
    main()
