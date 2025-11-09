import os
from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from django.conf import settings
from pathlib import Path

class Command(BaseCommand):
    help = 'Migrate local media files to S3 - FORCE UPLOAD'
    
    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)
        
        self.stdout.write(f"Media root: {media_root}")
        self.stdout.write(f"Storage: {default_storage.__class__.__name__}")
        
        # Count files
        all_files = []
        for root, dirs, files in os.walk(media_root):
            for file in files:
                full_path = Path(root) / file
                relative_path = full_path.relative_to(media_root)
                all_files.append(str(relative_path))
        
        self.stdout.write(f"Found {len(all_files)} files to migrate")
        
        # UPLOAD ALL FILES - NO CHECKS
        success_count = 0
        for i, file_path in enumerate(all_files):
            try:
                local_path = media_root / file_path
                
                # Debug info
                file_size = local_path.stat().st_size
                self.stdout.write(f"Uploading [{i+1}/{len(all_files)}]: {file_path} ({file_size} bytes)")
                
                # Force upload
                with open(local_path, 'rb') as file:
                    default_storage.save(file_path, file)
                
                success_count += 1
                
                # Progress every 100 files
                if success_count % 100 == 0:
                    self.stdout.write(f"✅ Progress: {success_count}/{len(all_files)}")
                    
            except Exception as e:
                self.stdout.write(f"❌ Failed: {file_path} - {str(e)}")
        
        self.stdout.write(f"🎉 Migration complete: {success_count}/{len(all_files)} files uploaded")
