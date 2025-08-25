"""
Storage service for RAGme.io
Provides S3-compatible file storage functionality using MinIO
"""

import logging
import mimetypes
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError
from minio import Minio
from minio.error import S3Error

from .config_manager import ConfigManager

logger = logging.getLogger(__name__)


class StorageService:
    """S3-compatible storage service using MinIO"""

    def __init__(self, config: ConfigManager | None = None):
        """Initialize storage service with configuration"""
        self.config = config or ConfigManager()
        self.storage_config = self.config.get("storage", {})
        self.storage_type = self.storage_config.get("type", "minio")

        if self.storage_type == "minio":
            self._init_minio_client()
        elif self.storage_type == "s3":
            self._init_s3_client()
        elif self.storage_type == "local":
            self._init_local_storage()
        else:
            raise ValueError(f"Unsupported storage type: {self.storage_type}")

    def _init_minio_client(self):
        """Initialize MinIO client"""
        minio_config = self.storage_config.get("minio", {})
        self.client = Minio(
            endpoint=minio_config.get("endpoint", "localhost:9000"),
            access_key=minio_config.get("access_key", "minioadmin"),
            secret_key=minio_config.get("secret_key", "minioadmin"),
            secure=minio_config.get("secure", False),
            region=minio_config.get("region", "us-east-1"),
        )
        self.bucket_name = minio_config.get("bucket_name", "ragme-storage")
        self._ensure_bucket_exists()

    def _init_s3_client(self):
        """Initialize S3 client"""
        s3_config = self.storage_config.get("s3", {})
        self.client = boto3.client(
            "s3",
            endpoint_url=s3_config.get("endpoint"),
            aws_access_key_id=s3_config.get("access_key"),
            aws_secret_access_key=s3_config.get("secret_key"),
            region_name=s3_config.get("region", "us-east-1"),
            use_ssl=s3_config.get("secure", True),
        )
        self.bucket_name = s3_config.get("bucket_name")
        if not self.bucket_name:
            raise ValueError("S3 bucket name is required")

    def _init_local_storage(self):
        """Initialize local storage"""
        local_config = self.storage_config.get("local", {})
        self.storage_path = Path(local_config.get("path", "local_storage/"))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.client = None
        self.bucket_name = None

    def _ensure_bucket_exists(self):
        """Ensure the bucket exists (for MinIO)"""
        if self.storage_type == "minio":
            try:
                if not self.client.bucket_exists(self.bucket_name):
                    self.client.make_bucket(self.bucket_name)
                    logger.info(f"Created bucket: {self.bucket_name}")
            except S3Error as e:
                logger.error(f"Error ensuring bucket exists: {e}")
                raise

    def upload_file(
        self,
        file_path: str,
        object_name: str | None = None,
        content_type: str | None = None,
    ) -> str:
        """
        Upload a file to storage

        Args:
            file_path: Path to the file to upload
            object_name: Name for the object in storage (defaults to filename)
            content_type: MIME type of the file

        Returns:
            Object key/name in storage
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        if object_name is None:
            object_name = os.path.basename(file_path)

        if content_type is None:
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type is None:
                content_type = "application/octet-stream"

        try:
            if self.storage_type == "minio":
                return self._upload_file_minio(file_path, object_name, content_type)
            elif self.storage_type == "s3":
                return self._upload_file_s3(file_path, object_name, content_type)
            elif self.storage_type == "local":
                return self._upload_file_local(file_path, object_name)
        except Exception as e:
            logger.error(f"Error uploading file {file_path}: {e}")
            raise

    def _upload_file_minio(
        self, file_path: str, object_name: str, content_type: str
    ) -> str:
        """Upload file using MinIO client"""
        file_size = os.path.getsize(file_path)
        with open(file_path, "rb") as file_data:
            self.client.put_object(
                self.bucket_name,
                object_name,
                file_data,
                file_size,
                content_type=content_type,
            )
        logger.info(f"Uploaded {file_path} to {object_name}")
        return object_name

    def _upload_file_s3(
        self, file_path: str, object_name: str, content_type: str
    ) -> str:
        """Upload file using S3 client"""
        self.client.upload_file(
            file_path,
            self.bucket_name,
            object_name,
            ExtraArgs={"ContentType": content_type},
        )
        logger.info(f"Uploaded {file_path} to {object_name}")
        return object_name

    def _upload_file_local(self, file_path: str, object_name: str) -> str:
        """Upload file to local storage"""
        dest_path = self.storage_path / object_name
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        import shutil

        shutil.copy2(file_path, dest_path)
        logger.info(f"Copied {file_path} to {dest_path}")
        return object_name

    def upload_data(
        self, data: bytes, object_name: str, content_type: str | None = None
    ) -> str:
        """
        Upload binary data to storage

        Args:
            data: Binary data to upload
            object_name: Name for the object in storage
            content_type: MIME type of the data

        Returns:
            Object key/name in storage
        """
        if content_type is None:
            content_type = "application/octet-stream"

        try:
            if self.storage_type == "minio":
                return self._upload_data_minio(data, object_name, content_type)
            elif self.storage_type == "s3":
                return self._upload_data_s3(data, object_name, content_type)
            elif self.storage_type == "local":
                return self._upload_data_local(data, object_name)
        except Exception as e:
            logger.error(f"Error uploading data to {object_name}: {e}")
            raise

    def _upload_data_minio(
        self, data: bytes, object_name: str, content_type: str
    ) -> str:
        """Upload data using MinIO client"""
        from io import BytesIO

        data_stream = BytesIO(data)
        self.client.put_object(
            self.bucket_name,
            object_name,
            data_stream,
            len(data),
            content_type=content_type,
        )
        logger.info(f"Uploaded data to {object_name}")
        return object_name

    def _upload_data_s3(self, data: bytes, object_name: str, content_type: str) -> str:
        """Upload data using S3 client"""
        self.client.put_object(
            Bucket=self.bucket_name,
            Key=object_name,
            Body=data,
            ContentType=content_type,
        )
        logger.info(f"Uploaded data to {object_name}")
        return object_name

    def _upload_data_local(self, data: bytes, object_name: str) -> str:
        """Upload data to local storage"""
        dest_path = self.storage_path / object_name
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        with open(dest_path, "wb") as f:
            f.write(data)
        logger.info(f"Saved data to {dest_path}")
        return object_name

    def download_file(self, object_name: str, file_path: str) -> bool:
        """
        Download a file from storage

        Args:
            object_name: Name of the object in storage
            file_path: Local path to save the file

        Returns:
            True if successful
        """
        try:
            if self.storage_type == "minio":
                return self._download_file_minio(object_name, file_path)
            elif self.storage_type == "s3":
                return self._download_file_s3(object_name, file_path)
            elif self.storage_type == "local":
                return self._download_file_local(object_name, file_path)
        except Exception as e:
            logger.error(f"Error downloading {object_name}: {e}")
            raise

    def _download_file_minio(self, object_name: str, file_path: str) -> bool:
        """Download file using MinIO client"""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        self.client.fget_object(self.bucket_name, object_name, file_path)
        logger.info(f"Downloaded {object_name} to {file_path}")
        return True

    def _download_file_s3(self, object_name: str, file_path: str) -> bool:
        """Download file using S3 client"""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        self.client.download_file(self.bucket_name, object_name, file_path)
        logger.info(f"Downloaded {object_name} to {file_path}")
        return True

    def _download_file_local(self, object_name: str, file_path: str) -> bool:
        """Download file from local storage"""
        src_path = self.storage_path / object_name
        if not src_path.exists():
            raise FileNotFoundError(f"Object not found: {object_name}")

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        import shutil

        shutil.copy2(src_path, file_path)
        logger.info(f"Copied {src_path} to {file_path}")
        return True

    def get_file(self, object_name: str) -> bytes:
        """
        Get file data from storage

        Args:
            object_name: Name of the object in storage

        Returns:
            File data as bytes
        """
        try:
            if self.storage_type == "minio":
                return self._get_file_minio(object_name)
            elif self.storage_type == "s3":
                return self._get_file_s3(object_name)
            elif self.storage_type == "local":
                return self._get_file_local(object_name)
        except Exception as e:
            logger.error(f"Error getting file {object_name}: {e}")
            raise

    def _get_file_minio(self, object_name: str) -> bytes:
        """Get file data using MinIO client"""
        response = self.client.get_object(self.bucket_name, object_name)
        data = response.read()
        response.close()
        response.release_conn()
        return data

    def _get_file_s3(self, object_name: str) -> bytes:
        """Get file data using S3 client"""
        response = self.client.get_object(Bucket=self.bucket_name, Key=object_name)
        return response["Body"].read()

    def _get_file_local(self, object_name: str) -> bytes:
        """Get file data from local storage"""
        file_path = self.storage_path / object_name
        if not file_path.exists():
            raise FileNotFoundError(f"Object not found: {object_name}")

        with open(file_path, "rb") as f:
            return f.read()

    def list_files(
        self, prefix: str = "", recursive: bool = True
    ) -> list[dict[str, Any]]:
        """
        List files in storage

        Args:
            prefix: Prefix to filter objects
            recursive: Whether to list recursively

        Returns:
            List of file information dictionaries
        """
        try:
            if self.storage_type == "minio":
                return self._list_files_minio(prefix, recursive)
            elif self.storage_type == "s3":
                return self._list_files_s3(prefix, recursive)
            elif self.storage_type == "local":
                return self._list_files_local(prefix, recursive)
        except Exception as e:
            logger.error(f"Error listing files with prefix {prefix}: {e}")
            raise

    def _list_files_minio(self, prefix: str, recursive: bool) -> list[dict[str, Any]]:
        """List files using MinIO client"""
        objects = self.client.list_objects(
            self.bucket_name, prefix=prefix, recursive=recursive
        )
        files = []
        for obj in objects:
            files.append(
                {
                    "name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": obj.etag,
                }
            )
        return files

    def _list_files_s3(self, prefix: str, recursive: bool) -> list[dict[str, Any]]:
        """List files using S3 client"""
        paginator = self.client.get_paginator("list_objects_v2")
        page_iterator = paginator.paginate(
            Bucket=self.bucket_name, Prefix=prefix, Delimiter="" if recursive else "/"
        )

        files = []
        for page in page_iterator:
            if "Contents" in page:
                for obj in page["Contents"]:
                    files.append(
                        {
                            "name": obj["Key"],
                            "size": obj["Size"],
                            "last_modified": obj["LastModified"],
                            "etag": obj["ETag"],
                        }
                    )
        return files

    def _list_files_local(self, prefix: str, recursive: bool) -> list[dict[str, Any]]:
        """List files in local storage"""
        prefix_path = self.storage_path / prefix
        files = []

        if recursive:
            pattern = "**/*"
        else:
            pattern = "*"

        for file_path in prefix_path.glob(pattern):
            if file_path.is_file():
                stat = file_path.stat()
                files.append(
                    {
                        "name": str(file_path.relative_to(self.storage_path)),
                        "size": stat.st_size,
                        "last_modified": datetime.fromtimestamp(stat.st_mtime),
                        "etag": str(stat.st_mtime),  # Use modification time as ETag
                    }
                )

        return files

    def delete_file(self, object_name: str) -> bool:
        """
        Delete a file from storage

        Args:
            object_name: Name of the object to delete

        Returns:
            True if successful
        """
        try:
            if self.storage_type == "minio":
                return self._delete_file_minio(object_name)
            elif self.storage_type == "s3":
                return self._delete_file_s3(object_name)
            elif self.storage_type == "local":
                return self._delete_file_local(object_name)
        except Exception as e:
            logger.error(f"Error deleting {object_name}: {e}")
            raise

    def _delete_file_minio(self, object_name: str) -> bool:
        """Delete file using MinIO client"""
        self.client.remove_object(self.bucket_name, object_name)
        logger.info(f"Deleted {object_name}")
        return True

    def _delete_file_s3(self, object_name: str) -> bool:
        """Delete file using S3 client"""
        self.client.delete_object(Bucket=self.bucket_name, Key=object_name)
        logger.info(f"Deleted {object_name}")
        return True

    def _delete_file_local(self, object_name: str) -> bool:
        """Delete file from local storage"""
        file_path = self.storage_path / object_name
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted {file_path}")
            return True
        else:
            logger.warning(f"File not found: {file_path}")
            return False

    def file_exists(self, object_name: str) -> bool:
        """
        Check if a file exists in storage

        Args:
            object_name: Name of the object to check

        Returns:
            True if file exists
        """
        try:
            if self.storage_type == "minio":
                return self._file_exists_minio(object_name)
            elif self.storage_type == "s3":
                return self._file_exists_s3(object_name)
            elif self.storage_type == "local":
                return self._file_exists_local(object_name)
        except Exception as e:
            logger.error(f"Error checking if {object_name} exists: {e}")
            return False

    def _file_exists_minio(self, object_name: str) -> bool:
        """Check if file exists using MinIO client"""
        try:
            self.client.stat_object(self.bucket_name, object_name)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            raise

    def _file_exists_s3(self, object_name: str) -> bool:
        """Check if file exists using S3 client"""
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=object_name)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise

    def _file_exists_local(self, object_name: str) -> bool:
        """Check if file exists in local storage"""
        file_path = self.storage_path / object_name
        return file_path.exists()

    def get_file_url(self, object_name: str, expires_in: int = 3600) -> str:
        """
        Get a presigned URL for file access

        Args:
            object_name: Name of the object
            expires_in: URL expiration time in seconds

        Returns:
            Presigned URL
        """
        try:
            if self.storage_type == "minio":
                return self._get_file_url_minio(object_name, expires_in)
            elif self.storage_type == "s3":
                return self._get_file_url_s3(object_name, expires_in)
            elif self.storage_type == "local":
                return self._get_file_url_local(object_name)
        except Exception as e:
            logger.error(f"Error generating URL for {object_name}: {e}")
            raise

    def _get_file_url_minio(self, object_name: str, expires_in: int) -> str:
        """Get presigned URL using MinIO client"""
        from datetime import timedelta

        return self.client.presigned_get_object(
            self.bucket_name, object_name, expires=timedelta(seconds=expires_in)
        )

    def _get_file_url_s3(self, object_name: str, expires_in: int) -> str:
        """Get presigned URL using S3 client"""
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": object_name},
            ExpiresIn=expires_in,
        )

    def _get_file_url_local(self, object_name: str) -> str:
        """Get local file URL (for development)"""
        # For local storage, construct a proper URL using the API server
        try:
            # Get the API URL from configuration
            api_url = (
                self.config.get("network", {})
                .get("frontend", {})
                .get("api_url", "http://localhost:8021")
            )
            # Remove trailing slash if present
            api_url = api_url.rstrip("/")
            return f"{api_url}/storage/{object_name}"
        except Exception:
            # Fallback to relative path if configuration is not available
            return f"/storage/{object_name}"

    def get_file_info(self, object_name: str) -> dict[str, Any]:
        """
        Get file information

        Args:
            object_name: Name of the object

        Returns:
            File information dictionary
        """
        try:
            if self.storage_type == "minio":
                return self._get_file_info_minio(object_name)
            elif self.storage_type == "s3":
                return self._get_file_info_s3(object_name)
            elif self.storage_type == "local":
                return self._get_file_info_local(object_name)
        except Exception as e:
            logger.error(f"Error getting info for {object_name}: {e}")
            raise

    def _get_file_info_minio(self, object_name: str) -> dict[str, Any]:
        """Get file info using MinIO client"""
        stat = self.client.stat_object(self.bucket_name, object_name)
        return {
            "name": object_name,
            "size": stat.size,
            "last_modified": stat.last_modified,
            "etag": stat.etag,
            "content_type": stat.content_type,
        }

    def _get_file_info_s3(self, object_name: str) -> dict[str, Any]:
        """Get file info using S3 client"""
        response = self.client.head_object(Bucket=self.bucket_name, Key=object_name)
        return {
            "name": object_name,
            "size": response["ContentLength"],
            "last_modified": response["LastModified"],
            "etag": response["ETag"],
            "content_type": response.get("ContentType", "application/octet-stream"),
        }

    def _get_file_info_local(self, object_name: str) -> dict[str, Any]:
        """Get file info from local storage"""
        file_path = self.storage_path / object_name
        if not file_path.exists():
            raise FileNotFoundError(f"Object not found: {object_name}")

        stat = file_path.stat()
        return {
            "name": object_name,
            "size": stat.st_size,
            "last_modified": datetime.fromtimestamp(stat.st_mtime),
            "etag": str(stat.st_mtime),
            "content_type": mimetypes.guess_type(str(file_path))[0]
            or "application/octet-stream",
        }

    def list_buckets(self) -> list[dict[str, Any]]:
        """
        List all available buckets

        Returns:
            List of bucket information dictionaries
        """
        try:
            if self.storage_type == "minio":
                return self._list_buckets_minio()
            elif self.storage_type == "s3":
                return self._list_buckets_s3()
            elif self.storage_type == "local":
                return self._list_buckets_local()
        except Exception as e:
            logger.error(f"Error listing buckets: {e}")
            raise

    def _list_buckets_minio(self) -> list[dict[str, Any]]:
        """List buckets using MinIO client"""
        buckets = []
        for bucket in self.client.list_buckets():
            buckets.append(
                {
                    "name": bucket.name,
                    "creation_date": bucket.creation_date,
                    "size": 0,  # MinIO doesn't provide bucket size directly
                }
            )
        return buckets

    def _list_buckets_s3(self) -> list[dict[str, Any]]:
        """List buckets using S3 client"""
        response = self.client.list_buckets()
        buckets = []
        for bucket in response["Buckets"]:
            # Get bucket size by listing objects
            try:
                size = 0
                paginator = self.client.get_paginator("list_objects_v2")
                for page in paginator.paginate(Bucket=bucket["Name"]):
                    if "Contents" in page:
                        size += sum(obj["Size"] for obj in page["Contents"])
                buckets.append(
                    {
                        "name": bucket["Name"],
                        "creation_date": bucket["CreationDate"],
                        "size": size,
                    }
                )
            except Exception as e:
                logger.warning(f"Could not get size for bucket {bucket['Name']}: {e}")
                buckets.append(
                    {
                        "name": bucket["Name"],
                        "creation_date": bucket["CreationDate"],
                        "size": 0,
                    }
                )
        return buckets

    def _list_buckets_local(self) -> list[dict[str, Any]]:
        """List buckets for local storage (directories)"""
        buckets = []
        if self.storage_path.exists():
            for item in self.storage_path.iterdir():
                if item.is_dir():
                    # Calculate directory size
                    size = 0
                    try:
                        for file_path in item.rglob("*"):
                            if file_path.is_file():
                                size += file_path.stat().st_size
                    except Exception:
                        size = 0

                    buckets.append(
                        {
                            "name": item.name,
                            "creation_date": datetime.fromtimestamp(
                                item.stat().st_ctime
                            ),
                            "size": size,
                        }
                    )
        return buckets

    def bucket_exists(self, bucket_name: str) -> bool:
        """
        Check if a bucket exists

        Args:
            bucket_name: Name of the bucket to check

        Returns:
            True if bucket exists, False otherwise
        """
        try:
            if self.storage_type == "minio":
                return self.client.bucket_exists(bucket_name)
            elif self.storage_type == "s3":
                try:
                    self.client.head_bucket(Bucket=bucket_name)
                    return True
                except ClientError as e:
                    if e.response["Error"]["Code"] == "404":
                        return False
                    raise
            elif self.storage_type == "local":
                bucket_path = self.storage_path / bucket_name
                return bucket_path.exists() and bucket_path.is_dir()
        except Exception as e:
            logger.error(f"Error checking bucket existence: {e}")
            return False

    def list_files_in_bucket(
        self, bucket_name: str, prefix: str = "", recursive: bool = True
    ) -> list[dict[str, Any]]:
        """
        List files in a specific bucket

        Args:
            bucket_name: Name of the bucket
            prefix: Prefix to filter files
            recursive: Whether to list recursively

        Returns:
            List of file information dictionaries
        """
        try:
            if self.storage_type == "minio":
                return self._list_files_in_bucket_minio(bucket_name, prefix, recursive)
            elif self.storage_type == "s3":
                return self._list_files_in_bucket_s3(bucket_name, prefix, recursive)
            elif self.storage_type == "local":
                return self._list_files_in_bucket_local(bucket_name, prefix, recursive)
        except Exception as e:
            logger.error(f"Error listing files in bucket {bucket_name}: {e}")
            raise

    def _list_files_in_bucket_minio(
        self, bucket_name: str, prefix: str = "", recursive: bool = True
    ) -> list[dict[str, Any]]:
        """List files in bucket using MinIO client"""
        files = []
        try:
            objects = self.client.list_objects(
                bucket_name, prefix=prefix, recursive=recursive
            )
            for obj in objects:
                files.append(
                    {
                        "name": obj.object_name,
                        "size": obj.size,
                        "last_modified": obj.last_modified,
                        "etag": obj.etag,
                    }
                )
        except S3Error as e:
            if e.code == "NoSuchBucket":
                return []
            raise
        return files

    def _list_files_in_bucket_s3(
        self, bucket_name: str, prefix: str = "", recursive: bool = True
    ) -> list[dict[str, Any]]:
        """List files in bucket using S3 client"""
        files = []
        try:
            paginator = self.client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
                if "Contents" in page:
                    for obj in page["Contents"]:
                        files.append(
                            {
                                "name": obj["Key"],
                                "size": obj["Size"],
                                "last_modified": obj["LastModified"],
                                "etag": obj["ETag"],
                            }
                        )
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchBucket":
                return []
            raise
        return files

    def _list_files_in_bucket_local(
        self, bucket_name: str, prefix: str = "", recursive: bool = True
    ) -> list[dict[str, Any]]:
        """List files in bucket for local storage"""
        files = []
        bucket_path = self.storage_path / bucket_name
        if not bucket_path.exists() or not bucket_path.is_dir():
            return files

        try:
            if recursive:
                file_paths = bucket_path.rglob("*")
            else:
                file_paths = bucket_path.glob("*")

            for file_path in file_paths:
                if file_path.is_file():
                    # Check if file matches prefix
                    relative_path = file_path.relative_to(bucket_path)
                    if not prefix or str(relative_path).startswith(prefix):
                        stat = file_path.stat()
                        files.append(
                            {
                                "name": str(relative_path),
                                "size": stat.st_size,
                                "last_modified": datetime.fromtimestamp(stat.st_mtime),
                                "etag": str(stat.st_mtime),
                            }
                        )
        except Exception as e:
            logger.error(f"Error listing files in local bucket {bucket_name}: {e}")
            raise

        return files

    def delete_file_from_bucket(self, bucket_name: str, object_name: str) -> bool:
        """
        Delete a file from a specific bucket

        Args:
            bucket_name: Name of the bucket
            object_name: Name of the object to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.storage_type == "minio":
                self.client.remove_object(bucket_name, object_name)
                return True
            elif self.storage_type == "s3":
                self.client.delete_object(Bucket=bucket_name, Key=object_name)
                return True
            elif self.storage_type == "local":
                file_path = self.storage_path / bucket_name / object_name
                if file_path.exists():
                    file_path.unlink()
                    return True
                return False
        except Exception as e:
            logger.error(
                f"Error deleting file {object_name} from bucket {bucket_name}: {e}"
            )
            return False
