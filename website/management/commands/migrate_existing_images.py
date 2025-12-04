# website/management/commands/migrate_existing_images.py
import csv
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from website.models import UserProfile, UserProfileImage  # Changed to 'website'

class Command(BaseCommand):
    help = 'Migrate image URLs from CSV for existing users'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        
        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f"CSV file not found: {csv_file_path}"))
            return

        # Build username to image data mapping
        image_data_map = {}
        
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            
            for row in csv_reader:
                username = row.get('username', '').strip()
                if username:
                    image_data_map[username] = row

        # Migrate images for existing users
        migrated_count = 0
        for username, row_data in image_data_map.items():
            try:
                user = User.objects.get(username=username)
                profile = UserProfile.objects.get(user=user)
                
                # Clear existing images
                UserProfileImage.objects.filter(user_profile=profile).delete()
                
                # Import new images
                self.import_profile_images(profile, row_data)
                migrated_count += 1
                
                self.stdout.write(self.style.SUCCESS(f"Migrated images for {username}"))
                
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"User not found: {username}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error migrating {username}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f"Image migration completed: {migrated_count} users updated"))

    def import_profile_images(self, profile, row):
        """Import all image URLs from CSV row"""
        
        # Import profile image
        profile_image_url = row.get('profile_image', '').strip()
        if profile_image_url:
            profile.profile_image_url = profile_image_url
            profile.save()

        # Import additional images (1-4)
        for i in range(1, 5):
            image_url = row.get(f'additional_image_{i}', '').strip()
            if image_url:
                UserProfileImage.objects.create(
                    user_profile=profile,
                    image_url=image_url,
                    image_type='additional',
                    position=i
                )

        # Import private images (1-5)
        for i in range(1, 6):
            image_url = row.get(f'private_image_{i}', '').strip()
            if image_url:
                UserProfileImage.objects.create(
                    user_profile=profile,
                    image_url=image_url,
                    image_type='private',
                    position=i
                )
