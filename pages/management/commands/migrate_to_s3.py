import os
from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from django.conf import settings
from pathlib import Path

class Command(BaseCommand):
    help = 'Migrate local media files to S3'
    
    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)
        
        # Count files
        all_files = []
        for root, dirs, files in os.walk(media_root):
            for file in files:
                full_path = Path(root) / file
                relative_path = full_path.relative_to(media_root)
                all_files.append(str(relative_path))
        
        self.stdout.write(f"Found {len(all_files)} files to migrate")
        
        # Upload to S3
        success_count = 0
        for file_path in all_files:
            try:
                local_path = media_root / file_path
                with open(local_path, 'rb') as file:
                    default_storage.save(file_path, file)
                success_count += 1
                self.stdout.write(f"✅ Uploaded: {file_path}")
            except Exception as e:
                self.stdout.write(f"❌ Failed: {file_path} - {e}")
        
        self.stdout.write(f"Migration complete: {success_count}/{len(all_files)} files uploaded")
