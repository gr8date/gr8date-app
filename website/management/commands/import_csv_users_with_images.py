# management/commands/import_csv_users_with_images.py
import csv
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings
from your_app.models import UserProfile, UserProfileImage  # Replace 'your_app' with your app name

class Command(BaseCommand):
    help = 'Import users from CSV with image URLs support'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        
        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f"CSV file not found: {csv_file_path}"))
            return

        with open(csv_file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            users_created = 0
            users_updated = 0
            
            for row_num, row in enumerate(csv_reader, 1):
                try:
                    # Extract basic user info
                    username = row.get('username', '').strip()
                    email = row.get('email', '').strip()
                    profile_name = row.get('profile_name', '').strip()
                    
                    if not username or not email:
                        self.stdout.write(self.style.WARNING(f"Row {row_num}: Skipping - missing username or email"))
                        continue

                    # Create or update user
                    user, created = User.objects.get_or_create(
                        username=username,
                        defaults={
                            'email': email,
                            'is_active': True,
                            'password': 'pbkdf2_sha256$600000$synpass1234$default_hash'  # Use your actual hash
                        }
                    )
                    
                    if created:
                        users_created += 1
                    else:
                        users_updated += 1

                    # Create or update user profile
                    profile, profile_created = UserProfile.objects.get_or_create(
                        user=user,
                        defaults={
                            'profile_name': profile_name,
                            'location': row.get('location', 'Unknown'),
                            'gender': row.get('gender', ''),
                            'height': row.get('height', ''),
                            'looking_for': row.get('looking_for', ''),
                            'is_approved': True,
                            'is_complete': True,
                        }
                    )

                    # IMPORT IMAGE DATA FROM CSV
                    self.import_profile_images(profile, row)
                    
                    self.stdout.write(self.style.SUCCESS(
                        f"Row {row_num}: {'Created' if created else 'Updated'} user {username}"
                    ))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f"Row {row_num}: Error processing user - {str(e)}"
                    ))
                    continue

            self.stdout.write(self.style.SUCCESS(
                f"Import completed: {users_created} users created, {users_updated} users updated"
            ))

    def import_profile_images(self, profile, row):
        """Import all image URLs from CSV row"""
        
        # 1. Import profile image
        profile_image_url = row.get('profile_image', '').strip()
        if profile_image_url:
            profile.profile_image_url = profile_image_url
            profile.save()

        # 2. Import additional images (1-4)
        additional_images = []
        for i in range(1, 5):
            image_url = row.get(f'additional_image_{i}', '').strip()
            if image_url:
                additional_images.append({
                    'url': image_url,
                    'position': i,
                    'type': 'additional'
                })

        # 3. Import private images (1-5)
        private_images = []
        for i in range(1, 6):
            image_url = row.get(f'private_image_{i}', '').strip()
            if image_url:
                private_images.append({
                    'url': image_url,
                    'position': i,
                    'type': 'private'
                })

        # Save all images to database
        self.save_profile_images(profile, additional_images + private_images)

    def save_profile_images(self, profile, images_data):
        """Save profile images to UserProfileImage model"""
        for image_data in images_data:
            try:
                UserProfileImage.objects.update_or_create(
                    user_profile=profile,
                    image_type=image_data['type'],
                    position=image_data['position'],
                    defaults={
                        'image_url': image_data['url']
                    }
                )
            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f"Error saving {image_data['type']} image {image_data['position']} for {profile.profile_name}: {str(e)}"
                ))
