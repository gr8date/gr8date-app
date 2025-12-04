#!/usr/bin/env python
"""
RESET AND REIMPORT SCRIPT - Fixes ID mismatches
Run this ONCE to reset database and import CSV with matching IDs
"""
import os
import sys
import django
import csv
from datetime import datetime

# Setup Django - CORRECT: config.settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db import connection
from website.models import UserProfile, UserProfileImage, UserIdMapping

def reset_database():
    """Clear all data and reset sequences"""
    print("⚠️  RESETTING DATABASE...")
    
    # Delete all data (in correct order to avoid foreign key issues)
    UserProfileImage.objects.all().delete()
    UserProfile.objects.all().delete()
    UserIdMapping.objects.all().delete()
    
    # Get User model and delete all users except superuser
    User = get_user_model()
    User.objects.filter(is_superuser=False).delete()
    
    print("✅ Database reset complete")

def create_user_with_custom_id(user_id, username, email):
    """Create user with specific ID by manipulating database directly"""
    from django.db import connection
    
    # Create user with raw SQL to set specific ID
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO auth_user (id, username, email, password, is_superuser, is_staff, is_active, date_joined)
            VALUES (%s, %s, %s, %s, false, false, true, %s)
        """, [
            user_id,
            username,
            email,
            'pbkdf2_sha256$260000$fakehash$fakepassword',  # Fake hash for now
            datetime.now()
        ])
    
    User = get_user_model()
    return User.objects.get(id=user_id)

def import_csv_with_matching_ids():
    """Import CSV with IDs matching the CSV user_id column"""
    csv_path = '/Users/carlsng/Desktop/synergy/data/Master_user_sheet.csv'
    
    print("📥 IMPORTING CSV WITH MATCHING IDs...")
    
    User = get_user_model()
    stats = {'users': 0, 'profiles': 0, 'images': 0}
    
    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for row in reader:
            try:
                csv_user_id = int(row['user_id'])
                username = row['username'].strip()
                email = row['email'].strip()
                
                print(f"Processing: ID {csv_user_id} - {username}")
                
                # Create user with EXACT CSV ID
                try:
                    user = User.objects.get(id=csv_user_id)
                    print(f"  User {csv_user_id} already exists, updating...")
                except User.DoesNotExist:
                    # Create with custom ID
                    user = create_user_with_custom_id(csv_user_id, username, email)
                    print(f"  ✓ Created user with ID {csv_user_id}")
                
                stats['users'] += 1
                
                # Create UserIdMapping for reference
                mapping, created = UserIdMapping.objects.get_or_create(
                    external_profile_id=csv_user_id,
                    defaults={
                        'external_user_id': csv_user_id,
                        'django_user_id': csv_user_id,  # SAME ID!
                        'username': username
                    }
                )
                
                # Parse date (dd-mm-yyyy)
                dob_str = row.get('date_of_birth', '').strip()
                dob = None
                if dob_str:
                    try:
                        dob = datetime.strptime(dob_str, '%d-%m-%Y').date()
                    except:
                        pass
                
                # Create or update profile
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
                
                stats['profiles'] += 1
                
                # Import profile images
                profile_image_url = row.get('profile_image', '').strip()
                if profile_image_url:
                    UserProfileImage.objects.get_or_create(
                        user_profile=profile,
                        image_url=profile_image_url,
                        image_type='additional',
                        position=0
                    )
                    stats['images'] += 1
                
                # Import additional images
                for i in range(1, 5):
                    img_url = row.get(f'additional_image_{i}', '').strip()
                    if img_url:
                        UserProfileImage.objects.get_or_create(
                            user_profile=profile,
                            image_url=img_url,
                            image_type='additional',
                            position=i
                        )
                        stats['images'] += 1
                
                # Import private images
                for i in range(1, 6):
                    img_url = row.get(f'private_image_{i}', '').strip()
                    if img_url:
                        UserProfileImage.objects.get_or_create(
                            user_profile=profile,
                            image_url=img_url,
                            image_type='private',
                            position=i
                        )
                        stats['images'] += 1
                
            except Exception as e:
                print(f"  ✗ Error: {str(e)}")
                continue
    
    print(f"\n✅ IMPORT COMPLETE!")
    print(f"   Users: {stats['users']}")
    print(f"   Profiles: {stats['profiles']}")
    print(f"   Images: {stats['images']}")
    print(f"\n⚠️  IMPORTANT: Run 'python manage.py migrate' to ensure schema is up to date")
    print(f"⚠️  IMPORTANT: Create superuser: 'python manage.py createsuperuser'")

if __name__ == '__main__':
    print("=" * 60)
    print("SYNERGY DATABASE RESET & IMPORT")
    print("=" * 60)
    print("This will:")
    print("1. DELETE ALL existing users (except superuser)")
    print("2. DELETE ALL profiles and images")
    print("3. Re-import CSV with matching IDs")
    print("=" * 60)
    
    confirm = input("Type 'YES' to continue: ")
    if confirm != 'YES':
        print("Cancelled.")
        sys.exit(0)
    
    reset_database()
    import_csv_with_matching_ids()
    
    print("\n" + "=" * 60)
    print("NEXT STEPS:")
    print("1. Run: python manage.py migrate")
    print("2. Run: python manage.py createsuperuser")
    print("3. Test: http://localhost:8000/dashboard/")
    print("=" * 60)
