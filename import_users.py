#!/usr/bin/env python
"""
SIMPLE CSV IMPORT - Creates users with matching IDs
"""
import os
import sys
import django
import csv
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from website.models import UserProfile, UserProfileImage, UserIdMapping

User = get_user_model()

csv_path = '/Users/carlsng/Desktop/synergy/data/Master_user_sheet.csv'

print("📥 Importing users from CSV...")

success_count = 0

with open(csv_path, 'r', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    
    for row in reader:
        try:
            csv_user_id = int(row['user_id'])
            username = row['username'].strip()
            email = row['email'].strip()
            
            print(f"Importing ID {csv_user_id}: {username}")
            
            # Check if user already exists
            try:
                user = User.objects.get(id=csv_user_id)
                print(f"  User {csv_user_id} already exists, updating...")
                user.username = username
                user.email = email
                user.save()
            except User.DoesNotExist:
                # Create new user with required fields
                user = User.objects.create_user(
                    id=csv_user_id,  # Set custom ID
                    username=username,
                    email=email,
                    password='temporary_password_123',  # Users will reset
                    first_name='',  # Empty string (not NULL)
                    last_name='',   # Empty string (not NULL)
                    is_active=True
                )
                print(f"  ✓ Created user {csv_user_id}")
            
            success_count += 1
            
            # Create/update ID mapping
            UserIdMapping.objects.update_or_create(
                external_profile_id=csv_user_id,
                defaults={
                    'external_user_id': csv_user_id,
                    'django_user_id': csv_user_id,
                    'username': username
                }
            )
            
            # Parse date
            dob_str = row.get('date_of_birth', '').strip()
            dob = None
            if dob_str:
                try:
                    dob = datetime.strptime(dob_str, '%d-%m-%Y').date()
                except:
                    pass
            
            # Create/update profile
            profile, created = UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    'profile_name': row.get('profile_name', '').strip() or username,
                    'date_of_birth': dob,
                    'relationship_status': row.get('relationship_status', 'single').lower(),
                    'body_type': row.get('body_type', 'average').lower(),
                    'has_children': bool(row.get('children', '').strip()),
                    'is_smoker': row.get('smoker', 'No').strip().lower() == 'yes',
                    'location': row.get('location', 'Unknown').strip(),
                    'story': row.get('my_story', '').strip(),
                    'profile_image_url': row.get('profile_image', '').strip(),
                    'gender': row.get('gender', '').strip().title(),
                    'looking_for': row.get('looking_for', '').strip(),
                    'communication_style': row.get('communication_style', 'Friendly').strip(),
                }
            )
            
            # Add profile image
            profile_image_url = row.get('profile_image', '').strip()
            if profile_image_url:
                UserProfileImage.objects.get_or_create(
                    user_profile=profile,
                    image_url=profile_image_url,
                    image_type='additional',
                    position=0
                )
            
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            continue

print(f"\n✅ IMPORT COMPLETE!")
print(f"Successfully imported: {success_count} users")
print(f"Total users in database: {User.objects.count()}")
print(f"Total profiles: {UserProfile.objects.count()}")

print("\n🔐 Default password for all users: 'temporary_password_123'")
print("   Users should reset password on first login.")
print("\n👑 Create admin: python manage.py createsuperuser")
print("🚀 Test: python manage.py runserver")
