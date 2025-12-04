# website/management/commands/migrate_local_images.py
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from website.models import UserProfile, UserProfileImage

class Command(BaseCommand):
    help = 'Migrate local profile images to database without affecting user accounts'

    def handle(self, *args, **options):
        images_dir = '/Users/carlsng/Desktop/synergy/media/profile_images'
        
        if not os.path.exists(images_dir):
            self.stdout.write(self.style.ERROR(f"Images directory not found: {images_dir}"))
            return

        migrated_count = 0
        
        for user in User.objects.all():
            try:
                profile = UserProfile.objects.get(user=user)
                user_migrated = self.migrate_user_images(profile, images_dir)
                
                if user_migrated:
                    migrated_count += 1
                    self.stdout.write(self.style.SUCCESS(f"Migrated images for user {user.username} (ID: {user.id})"))
                else:
                    self.stdout.write(self.style.WARNING(f"No images found for user {user.username} (ID: {user.id})"))
                    
            except UserProfile.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"No profile found for user {user.username}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error migrating {user.username}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f"Image migration completed: {migrated_count} users updated"))

    def migrate_user_images(self, profile, images_dir):
        """Migrate images for a single user without affecting other data"""
        user_id = profile.user.id
        migrated = False
        
        # Look for profile image
        profile_image_patterns = [
            f"user_{user_id}_profile_image.jpg",
            f"user_{user_id}_profile_image.jpeg", 
            f"user_{user_id}_profile_image.png"
        ]
        
        for pattern in profile_image_patterns:
            profile_image_path = os.path.join(images_dir, pattern)
            if os.path.exists(profile_image_path):
                with open(profile_image_path, 'rb') as img_file:
                    profile.profile_photo.save(pattern, img_file, save=True)
                migrated = True
                break

        # Look for additional images (1-4)
        for i in range(1, 5):
            additional_patterns = [
                f"user_{user_id}_additional_image_{i}.jpg",
                f"user_{user_id}_additional_image_{i}.jpeg",
                f"user_{user_id}_additional_image_{i}.png"
            ]
            
            for pattern in additional_patterns:
                image_path = os.path.join(images_dir, pattern)
                if os.path.exists(image_path):
                    # Check if image already exists to avoid duplicates
                    if not UserProfileImage.objects.filter(
                        user_profile=profile, 
                        image_type='additional', 
                        position=i
                    ).exists():
                        with open(image_path, 'rb') as img_file:
                            UserProfileImage.objects.create(
                                user_profile=profile,
                                image=img_file,
                                image_type='additional',
                                position=i
                            )
                        migrated = True

        # Look for private images (1-5)
        for i in range(1, 6):
            private_patterns = [
                f"user_{user_id}_private_image_{i}.jpg",
                f"user_{user_id}_private_image_{i}.jpeg", 
                f"user_{user_id}_private_image_{i}.png"
            ]
            
            for pattern in private_patterns:
                image_path = os.path.join(images_dir, pattern)
                if os.path.exists(image_path):
                    # Check if image already exists to avoid duplicates
                    if not UserProfileImage.objects.filter(
                        user_profile=profile, 
                        image_type='private', 
                        position=i
                    ).exists():
                        with open(image_path, 'rb') as img_file:
                            UserProfileImage.objects.create(
                                user_profile=profile,
                                image=img_file,
                                image_type='private',
                                position=i
                            )
                        migrated = True

        return migrated
