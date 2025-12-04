#!/usr/bin/env python
"""
COMPLETE IMAGE IMPORT - Imports ALL images from CSV
"""
import os
import sys
import django
import csv

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from website.models import UserProfile, UserProfileImage

User = get_user_model()
csv_path = '/Users/carlsng/Desktop/synergy/data/Master_user_sheet.csv'

print("🖼️  Importing ALL images from CSV...")

with open(csv_path, 'r', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    
    for row in reader:
        try:
            csv_user_id = int(row['user_id'])
            username = row['username'].strip()
            
            print(f"Processing images for {csv_user_id}: {username}")
            
            # Get user and profile
            user = User.objects.get(id=csv_user_id)
            profile = UserProfile.objects.get(user=user)
            
            # Clear existing images
            UserProfileImage.objects.filter(user_profile=profile).delete()
            
            # Import main profile image (position 0)
            profile_image_url = row.get('profile_image', '').strip()
            if profile_image_url:
                UserProfileImage.objects.create(
                    user_profile=profile,
                    image_url=profile_image_url,
                    image_type='additional',
                    position=0
                )
                print(f"  ✓ Main profile image")
            
            # Import additional images (positions 1-4)
            for i in range(1, 5):
                img_url = row.get(f'additional_image_{i}', '').strip()
                if img_url:
                    UserProfileImage.objects.create(
                        user_profile=profile,
                        image_url=img_url,
                        image_type='additional',
                        position=i
                    )
                    print(f"  ✓ Additional image {i}")
            
            # Import private images (positions 1-5)
            for i in range(1, 6):
                img_url = row.get(f'private_image_{i}', '').strip()
                if img_url:
                    UserProfileImage.objects.create(
                        user_profile=profile,
                        image_url=img_url,
                        image_type='private',
                        position=i
                    )
                    print(f"  ✓ Private image {i}")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            continue

print(f"\n✅ Image import complete!")
print(f"Total images imported: {UserProfileImage.objects.count()}")
