# db_helpers.py - UPDATED VERSION WITH EXCLUDE PARAMETER
import sqlite3
from pathlib import Path
from django.conf import settings
from datetime import date

def get_database_connection():
    db_path = Path(settings.BASE_DIR) / 'db.sqlite3'
    return sqlite3.connect(str(db_path))

def get_profile_by_id(user_id):
    try:
        conn = get_database_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                up.id,
                up.user_id,
                up.profile_name,
                up.date_of_birth,
                up.relationship_status,
                up.body_type,
                up.has_children,
                up.children_details,
                up.is_smoker,
                up.location,
                up.profile_photo,
                up.height,
                up.gender,
                up.looking_for,
                up.profile_image_url,
                up.story,
                up.communication_style,
                u.username,
                u.first_name,
                u.last_name
            FROM website_userprofile up
            LEFT JOIN auth_user u ON up.user_id = u.id
            WHERE up.id = ? OR up.user_id = ?
        """, (user_id, user_id))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        row_dict = dict(row)
        
        # FIX: Calculate age properly
        age = 'Not provided'
        if row_dict['date_of_birth']:
            try:
                birth_date = row_dict['date_of_birth']
                if isinstance(birth_date, str):
                    # Convert string to date if needed
                    from datetime import datetime
                    birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
                
                today = date.today()
                age_calc = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                age = str(age_calc)
            except:
                age = 'Not provided'
        
        # FIX: Get correct username - use profile_name first, then username
        display_name = row_dict['profile_name'] or row_dict['username'] or f"User {row_dict['id']}"
        
        profile = {
            'id': row_dict['id'],  # Make sure this key exists!
            'user_id': row_dict['id'],
            'username': row_dict['username'] or f"user_{row_dict['id']}",
            'profile_name': display_name,
            'display_name': display_name,  # Add this for template compatibility
            'age': age,
            'location': row_dict['location'] or 'Location not provided',
            'relationship_status': row_dict['relationship_status'] or 'Not provided',
            'body_type': row_dict['body_type'] or 'Not provided',
            'has_children': bool(row_dict['has_children']),
            'children_details': row_dict['children_details'] or '',
            'is_smoker': bool(row_dict['is_smoker']),
            'height': row_dict['height'] or 'Not provided',
            'gender': row_dict['gender'] or 'Not provided',
            'looking_for': row_dict['looking_for'] or 'Not specified',
            'story': row_dict['story'] or 'No story provided yet.',
            'communication_style': row_dict['communication_style'] or 'Friendly',
        }
        
        # FIX: Use profile_image_url first (these files exist)
        if row_dict['profile_image_url']:
            profile['profile_image'] = row_dict['profile_image_url']
        elif row_dict['profile_photo']:
            profile['profile_image'] = f"/media/{row_dict['profile_photo']}"
        else:
            profile['profile_image'] = None
        
        # GET ADDITIONAL IMAGES
        cursor.execute("""
            SELECT image_url 
            FROM website_userprofileimage 
            WHERE user_profile_id = ? AND image_type = 'additional'
            ORDER BY position
        """, (row_dict['id'],))
        
        additional_images = []
        for img_row in cursor.fetchall():
            if img_row[0]:
                additional_images.append(img_row[0])
        
        profile['additional_images'] = additional_images
        
        # GET PRIVATE IMAGES COUNT
        cursor.execute("""
            SELECT COUNT(*) 
            FROM website_userprofileimage 
            WHERE user_profile_id = ? AND image_type = 'private'
        """, (row_dict['id'],))
        
        private_count = cursor.fetchone()[0]
        profile['private_images'] = bool(private_count > 0)
        
        conn.close()
        return profile
        
    except Exception as e:
        print(f"Error getting profile {user_id}: {e}")
        return None

def get_all_profile_ids(exclude_id=None):
    """Get all profile IDs, optionally excluding one"""
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        if exclude_id:
            cursor.execute("SELECT id FROM website_userprofile WHERE id != ? ORDER BY id", (exclude_id,))
        else:
            cursor.execute("SELECT id FROM website_userprofile ORDER BY id")
            
        ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        return ids
    except Exception as e:
        print(f"Error getting profile IDs: {e}")
        return []

def get_all_profiles(exclude_id=None):
    """Get all profiles, optionally excluding one"""
    try:
        profile_ids = get_all_profile_ids(exclude_id)
        profiles = []
        for profile_id in profile_ids:
            profile = get_profile_by_id(profile_id)
            if profile:
                profiles.append(profile)
        return profiles
    except Exception as e:
        print(f"Error getting all profiles: {e}")
        return []
