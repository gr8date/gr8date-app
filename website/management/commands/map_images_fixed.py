# website/management/commands/map_images_fixed.py
import csv
import os
import re
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from website.models import UserProfile, UserProfileImage

class Command(BaseCommand):
    help = 'Map local images to users using username mapping from CSV'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the original CSV file')

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        images_dir = '/Users/carlsng/Desktop/synergy/media/profile_images'
        
        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f"CSV file not found: {csv_file_path}"))
            return

        if not os.path.exists(images_dir):
            self.stdout.write(self.style.ERROR(f"Images directory not found: {images_dir}"))
            return

        # Build username to CSV user_id mapping
        username_to_csv_id = {}
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                username = row.get('username', '').strip()
                csv_user_id = row.get('user_id', '').strip()
                if username and csv_user_id:
                    username_to_csv_id[username] = csv_user_id

        migrated_count = 0
        
        for user in User.objects.all():
            try:
                profile = UserProfile.objects.get(user=user)
                
                # Get the CSV user_id for this username
                csv_user_id = username_to_csv_id.get(user.username)
                
                if csv_user_id:
                    user_migrated = self.migrate_user_images_by_csv_id(profile, csv_user_id, images_dir)
                    
                    if user_migrated:
                        migrated_count += 1
                        self.stdout.write(self.style.SUCCESS(f"Migrated images for {user.username} (CSV ID: {csv_user_id})"))
                    else:
                        self.stdout.write(self.style.WARNING(f"No images found for {user.username} (CSV ID: {csv_user_id})"))
                else:
                    self.stdout.write(self.style.WARNING(f"No CSV ID found for {user.username}"))
                    
            except UserProfile.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"No profile found for {user.username}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error migrating {user.username}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f"Image migration completed: {migrated_count} users updated"))

    def migrate_user_images_by_csv_id(self, profile, csv_user_id, images_dir):
        """Migrate images for a user using CSV user_id to find local files"""
        migrated = False
        
        # Look for profile image
        profile_patterns = [
            f"user_{csv_user_id}_profile_image.jpg",
            f"user_{csv_user_id}_profile_image.jpeg", 
            f"user_{csv_user_id}_profile_image.png"
        ]
        
        for pattern in profile_patterns:
            profile_path = os.path.join(images_dir, pattern)
            if os.path.exists(profile_path):
                with open(profile_path, 'rb') as img_file:
                    profile.profile_photo.save(pattern, img_file, save=True)
                migrated = True
                self.stdout.write(self.style.SUCCESS(f"  - Profile image: {pattern}"))
                break

        # Look for additional images (1-4)
        for i in range(1, 5):
            additional_patterns = [
                f"user_{csv_user_id}_additional_image_{i}.jpg",
                f"user_{csv_user_id}_additional_image_{i}.jpeg",
                f"user_{csv_user_id}_additional_image_{i}.png"
            ]
            
            for pattern in additional_patterns:
                additional_path = os.path.join(images_dir, pattern)
                if os.path.exists(additional_path):
                    if not UserProfileImage.objects.filter(
                        user_profile=profile, 
                        image_type='additional', 
                        position=i
                    ).exists():
                        with open(additional_path, 'rb') as img_file:
                            UserProfileImage.objects.create(
                                user_profile=profile,
                                image=img_file,
                                image_type='additional',
                                position=i
                            )
                        migrated = True
                        self.stdout.write(self.style.SUCCESS(f"  - Additional image {i}: {pattern}"))

        # Look for private images (1-5)
        for i in range(1, 6):
            private_patterns = [
                f"user_{csv_user_id}_private_image_{i}.jpg",
                f"user_{csv_user_id}_private_image_{i}.jpeg", 
                f"user_{csv_user_id}_private_image_{i}.png"
            ]
            
            for pattern in private_patterns:
                private_path = os.path.join(images_dir, pattern)
                if os.path.exists(private_path):
                    if not UserProfileImage.objects.filter(
                        user_profile=profile, 
                        image_type='private', 
                        position=i
                    ).exists():
                        with open(private_path, 'rb') as img_file:
                            UserProfileImage.objects.create(
                                user_profile=profile,
                                image=img_file,
                                image_type='private',
                                position=i
                            )
                        migrated = True
                        self.stdout.write(self.style.SUCCESS(f"  - Private image {i}: {pattern}"))

        return migrated
