# core/storage_backends.py
from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings
import os

class MediaS3Storage(S3Boto3Storage):
    """
    Custom S3 storage backend that uses MEDIA_URL for URLs
    instead of direct S3 URLs. This enables hybrid local/S3 serving.
    """
    
    def url(self, name):
        # Use MEDIA_URL + filename instead of direct S3 URL
        if hasattr(settings, 'MEDIA_URL') and settings.MEDIA_URL:
            # Ensure proper URL joining
            base_url = settings.MEDIA_URL.rstrip('/')
            filename = name.lstrip('/')
            return f"{base_url}/{filename}"
        # Fallback to default S3 URL if no MEDIA_URL
        return super().url(name)

    def exists(self, name):
        """
        Check if file exists either locally or in S3
        """
        # First check local filesystem
        local_path = os.path.join(settings.MEDIA_ROOT, name)
        if os.path.exists(local_path):
            return True
        # Then check S3
        return super().exists(name)
