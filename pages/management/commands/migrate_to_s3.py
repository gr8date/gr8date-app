import os
import boto3
from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path

class Command(BaseCommand):
    help = 'Migrate local media files to S3 - USING DIRECT S3 API'
    
    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)
        s3 = boto3.client('s3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        
        # Count files
        all_files = []
        for root, dirs, files in os.walk(media_root):
            for file in files:
                full_path = Path(root) / file
                relative_path = full_path.relative_to(media_root)
                all_files.append(str(relative_path))
        
        self.stdout.write(f"Found {len(all_files)} local files")
        
        # UPLOAD USING DIRECT S3 API
        success_count = 0
        
        for file_path in all_files:
            try:
                local_path = media_root / file_path
                
                # Upload directly to S3
                with open(local_path, 'rb') as file:
                    s3.put_object(
                        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                        Key=file_path,
                        Body=file
                    )
                
                success_count += 1
                
                if success_count % 100 == 0:
                    self.stdout.write(f"Progress: {success_count}/{len(all_files)}")
                    
            except Exception as e:
                self.stdout.write(f"Failed: {file_path} - {e}")
        
        self.stdout.write(f"🎉 Migration complete: {success_count}/{len(all_files)} files uploaded")
