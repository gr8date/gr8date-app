# website/management/commands/map_images_by_username.py
import os
import re
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from website.models import UserProfile, UserProfileImage

class Command(BaseCommand):
    help = 'Map local images to users by extracting usernames from filenames'

    def handle(self, *args, **options):
        images_dir = '/Users/carlsng/Desktop/synergy/media/profile_images'
        
        if not os.path.exists(images_dir):
            self.stdout.write(self.style.ERROR(f"Images directory not found: {images_dir}"))
            return

        # First, build a mapping of usernames to image files
        username_to_images = self.build_username_mapping(images_dir)
        
        migrated_count = 0
        
        for user in User.objects.all():
            try:
                profile = UserProfile.objects.get(user=user)
                
                if user.username in username_to_images:
                    user_migrated = self.migrate_user_images_by_username(profile, username_to_images[user.username])
                    
                    if user_migrated:
                        migrated_count += 1
                        self.stdout.write(self.style.SUCCESS(f"Migrated images for {user.username}"))
                    else:
                        self.stdout.write(self.style.WARNING(f"No matching images found for {user.username}"))
                else:
                    self.stdout.write(self.style.WARNING(f"No images mapped for {user.username}"))
                    
            except UserProfile.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"No profile found for {user.username}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error migrating {user.username}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f"Image migration completed: {migrated_count} users updated"))
        self.stdout.write(self.style.SUCCESS(f"Total users with images mapped: {len(username_to_images)}"))

    def build_username_mapping(self, images_dir):
        """Build mapping of usernames to their image files by extracting from filenames"""
        username_mapping = {}
        
        for filename in os.listdir(images_dir):
            if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                continue
                
            # Try to extract username from filename pattern
            username = self.extract_username_from_filename(filename)
            if username:
                if username not in username_mapping:
                    username_mapping[username] = {
                        'profile_images': [],
                        'additional_images': [],
                        'private_images': []
                    }
                
                # Categorize the image
                if 'profile_image' in filename.lower():
                    username_mapping[username]['profile_images'].append(filename)
                elif 'additional_image' in filename.lower():
                    username_mapping[username]['additional_images'].append(filename)
                elif 'private_image' in filename.lower():
                    username_mapping[username]['private_images'].append(filename)
        
        return username_mapping

    def extract_username_from_filename(self, filename):
        """Extract username from various filename patterns"""
        # Remove file extension
        name_without_ext = os.path.splitext(filename)[0]
        
        # Pattern 1: user_1001_profile_image.jpg -> extract numeric part
        match = re.search(r'user_(\d+)_', filename)
        if match:
            return match.group(1)  # Return the numeric ID as username
        
        # Add more patterns here if needed
        return None

    def migrate_user_images_by_username(self, profile, image_files):
        """Migrate images for a user using the filename mapping"""
        migrated = False
        images_dir = '/Users/carlsng/Desktop/synergy/media/profile_images'
        
        # Migrate profile images (take first one found)
        for profile_file in image_files['profile_images']:
            profile_path = os.path.join(images_dir, profile_file)
            if os.path.exists(profile_path):
                with open(profile_path, 'rb') as img_file:
                    profile.profile_photo.save(profile_file, img_file, save=True)
                migrated = True
                break

        # Migrate additional images
        for i, additional_file in enumerate(image_files['additional_images'][:4], 1):
            additional_path = os.path.join(images_dir, additional_file)
            if os.path.exists(additional_path):
                # Extract position from filename or use enumeration
                position = self.extract_position_from_filename(additional_file) or i
                
                if not UserProfileImage.objects.filter(
                    user_profile=profile, 
                    image_type='additional', 
                    position=position
                ).exists():
                    with open(additional_path, 'rb') as img_file:
                        UserProfileImage.objects.create(
                            user_profile=profile,
                            image=img_file,
                            image_type='additional',
                            position=position
                        )
                    migrated = True

        # Migrate private images  
        for i, private_file in enumerate(image_files['private_images'][:5], 1):
            private_path = os.path.join(images_dir, private_file)
            if os.path.exists(private_path):
                # Extract position from filename or use enumeration
                position = self.extract_position_from_filename(private_file) or i
                
                if not UserProfileImage.objects.filter(
                    user_profile=profile, 
                    image_type='private', 
                    position=position
                ).exists():
                    with open(private_path, 'rb') as img_file:
                        UserProfileImage.objects.create(
                            user_profile=profile,
                            image=img_file,
                            image_type='private',
                            position=position
                        )
                    migrated = True

        return migrated

    def extract_position_from_filename(self, filename):
        """Extract image position from filename (e.g., additional_image_2 -> 2)"""
        match = re.search(r'_image_(\d+)', filename)
        if match:
            return int(match.group(1))
        return None
