# website/management/commands/map_images_from_csv.py
import csv
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from website.models import UserProfile, UserProfileImage

class Command(BaseCommand):
    help = 'Map local images to users using original CSV for ID mapping'

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

        # Build mapping from CSV
        csv_mapping = self.build_csv_mapping(csv_file_path)
        
        migrated_count = 0
        
        for user in User.objects.all():
            try:
                profile = UserProfile.objects.get(user=user)
                
                # Find this user in CSV mapping
                csv_user_data = None
                for csv_user in csv_mapping.values():
                    if csv_user['username'] == user.username:
                        csv_user_data = csv_user
                        break
                
                if csv_user_data:
                    user_migrated = self.migrate_user_images_from_csv(profile, csv_user_data, images_dir)
                    
                    if user_migrated:
                        migrated_count += 1
                        self.stdout.write(self.style.SUCCESS(f"Migrated images for {user.username}"))
                    else:
                        self.stdout.write(self.style.WARNING(f"No images found for {user.username}"))
                else:
                    self.stdout.write(self.style.WARNING(f"No CSV data found for {user.username}"))
                    
            except UserProfile.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"No profile found for {user.username}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error migrating {user.username}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f"Image migration completed: {migrated_count} users updated"))

    def build_csv_mapping(self, csv_file_path):
        """Build mapping from CSV data including image URLs"""
        csv_mapping = {}
        
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            
            for row in csv_reader:
                user_id = row.get('id', '').strip()
                username = row.get('username', '').strip()
                
                if user_id and username:
                    csv_mapping[user_id] = {
                        'username': username,
                        'profile_image': row.get('profile_image', '').strip(),
                        'additional_images': [
                            row.get(f'additional_image_{i}', '').strip()
                            for i in range(1, 5)
                        ],
                        'private_images': [
                            row.get(f'private_image_{i}', '').strip()
                            for i in range(1, 6)
                        ]
                    }
        
        return csv_mapping

    def migrate_user_images_from_csv(self, profile, csv_user_data, images_dir):
        """Migrate images for a user using CSV data to find local files"""
        migrated = False
        
        # Extract numeric ID from profile image URL to find local files
        profile_image_id = self.extract_image_id_from_url(csv_user_data['profile_image'])
        if profile_image_id:
            # Look for profile image with this ID
            profile_patterns = [
                f"user_{profile_image_id}_profile_image.jpg",
                f"user_{profile_image_id}_profile_image.jpeg", 
                f"user_{profile_image_id}_profile_image.png"
            ]
            
            for pattern in profile_patterns:
                profile_path = os.path.join(images_dir, pattern)
                if os.path.exists(profile_path):
                    with open(profile_path, 'rb') as img_file:
                        profile.profile_photo.save(pattern, img_file, save=True)
                    migrated = True
                    break

        # Migrate additional images
        for i, additional_url in enumerate(csv_user_data['additional_images'], 1):
            if additional_url:
                additional_id = self.extract_image_id_from_url(additional_url)
                if additional_id:
                    additional_patterns = [
                        f"user_{additional_id}_additional_image_{i}.jpg",
                        f"user_{additional_id}_additional_image_{i}.jpeg",
                        f"user_{additional_id}_additional_image_{i}.png"
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

        # Migrate private images  
        for i, private_url in enumerate(csv_user_data['private_images'], 1):
            if private_url:
                private_id = self.extract_image_id_from_url(private_url)
                if private_id:
                    private_patterns = [
                        f"user_{private_id}_private_image_{i}.jpg",
                        f"user_{private_id}_private_image_{i}.jpeg", 
                        f"user_{private_id}_private_image_{i}.png"
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

        return migrated

    def extract_image_id_from_url(self, url):
        """Extract numeric ID from image URL"""
        if not url:
            return None
            
        # Example URL: https://adultarrangements.com/wp-content/uploads/2022/07/face_ad1401841bf83439ce1fdd102e0f1cc8_df8ad39ffbe9178ad81797e228a61103.jpg
        # The unique part is the hash, but we need to map this to our local files
        # Since we have local files named with numeric IDs, we need a different approach
        
        # For now, let's try to extract any numeric patterns that might match
        import re
        # Look for patterns like user_1001 in the filename part
        filename = os.path.basename(url)
        match = re.search(r'user_(\d+)', filename)
        if match:
            return match.group(1)
            
        return None
