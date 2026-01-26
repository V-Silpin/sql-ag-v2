"""
MinIO Storage Manager
"""
import os
from typing import Optional
from datetime import timedelta
from minio import Minio
from minio.error import S3Error
from io import BytesIO


class StorageManager:
    """Manages MinIO object storage operations"""
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        secure: bool = False
    ):
        """
        Initialize MinIO storage manager
        
        Args:
            endpoint: MinIO endpoint (e.g., 'localhost:9000')
            access_key: MinIO access key
            secret_key: MinIO secret key
            secure: Whether to use HTTPS
        """
        self.endpoint = endpoint or os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.access_key = access_key or os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = secret_key or os.getenv("MINIO_SECRET_KEY", "minioadmin123")
        self.secure = secure if secure is not None else os.getenv("MINIO_SECURE", "false").lower() == "true"
        
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )
    
    def create_bucket(self, bucket_name: str) -> bool:
        """Create a bucket if it doesn't exist"""
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
                print(f"Bucket '{bucket_name}' created successfully")
            else:
                print(f"Bucket '{bucket_name}' already exists")
            return True
        except S3Error as e:
            print(f"Error creating bucket: {e}")
            return False
    
    def upload_file(self, bucket_name: str, object_name: str, data: bytes, content_type: str = "application/octet-stream") -> bool:
        """Upload a file to MinIO"""
        try:
            self.client.put_object(
                bucket_name,
                object_name,
                BytesIO(data),
                length=len(data),
                content_type=content_type
            )
            print(f"Uploaded '{object_name}' to bucket '{bucket_name}'")
            return True
        except S3Error as e:
            print(f"Error uploading file: {e}")
            return False
    
    def download_file(self, bucket_name: str, object_name: str) -> Optional[bytes]:
        """Download a file from MinIO"""
        try:
            response = self.client.get_object(bucket_name, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            print(f"Error downloading file: {e}")
            return None
    
    def list_files(self, bucket_name: str, prefix: str = "") -> list:
        """List files in a bucket"""
        try:
            objects = self.client.list_objects(bucket_name, prefix=prefix, recursive=True)
            return [obj.object_name for obj in objects]
        except S3Error as e:
            print(f"Error listing files: {e}")
            return []
    
    def delete_file(self, bucket_name: str, object_name: str) -> bool:
        """Delete a file from MinIO"""
        try:
            self.client.remove_object(bucket_name, object_name)
            print(f"Deleted '{object_name}' from bucket '{bucket_name}'")
            return True
        except S3Error as e:
            print(f"Error deleting file: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test MinIO connection"""
        try:
            self.client.list_buckets()
            return True
        except S3Error as e:
            print(f"MinIO connection failed: {e}")
            return False
    
    def get_presigned_url(self, bucket_name: str, object_name: str, expires: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for downloading a file
        
        Args:
            bucket_name: Name of the bucket
            object_name: Name of the object
            expires: Expiration time in seconds (default: 1 hour)
            
        Returns:
            Presigned URL or None on error
        """
        try:
            url = self.client.presigned_get_object(
                bucket_name,
                object_name,
                expires=timedelta(seconds=expires)
            )
            return url
        except S3Error as e:
            print(f"Error generating presigned URL: {e}")
            return None


# Global storage manager instance
_storage_manager: Optional[StorageManager] = None


def get_storage_manager() -> StorageManager:
    """Get global storage manager instance"""
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = StorageManager()
    return _storage_manager
