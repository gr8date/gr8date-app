from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from website.models import UserProfile
import csv
from pathlib import Path
from django.db import transaction
from datetime import datetime

User = get_user_model()

class Command(BaseCommand):
    help = 'Import users from CSV into Django database'

    def handle(self, *args, **options):
        csv_path = Path('data/Master_user_sheet.csv')
        
        self.stdout.write(f"Starting import from: {csv_path}")
        
        if not csv_path.exists():
            self.stdout.write(self.style.ERROR("CSV file not found"))
            return

        imported_count = 0
        skipped_count = 0
        
        with csv_path.open('r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for i, row in enumerate(reader, 1):
                try:
                    with transaction.atomic():
                        # Get basic fields from CSV
                        user_id = row.get('user_id', '').strip()
                        username = row.get('username', '').strip()
                        email = row.get('email', '').strip()
                        
                        # Skip if essential fields are missing
                        if not user_id or not username:
                            self.stdout.write(f"Row {i}: Skipping - missing user_id or username")
                            skipped_count += 1
                            continue
                        
                        # Check if user already exists
                        if User.objects.filter(username=username).exists():
                            self.stdout.write(f"Row {i}: Skipping - user {username} already exists")
                            skipped_count += 1
                            continue
                        
                        # Create user
                        user = User.objects.create(
                            username=username,
                            email=email,
                            is_active=True
                        )
                        # Set password to synpass1234 for all imported users
                        user.set_password('synpass1234')
                        user.save()
                        
                        # Parse date of birth
                        date_of_birth = self._parse_date(row.get('date_of_birth'))
                        
                        # Handle age_min and age_max - convert 'any' to reasonable defaults
                        age_min = self._safe_convert_age(row.get('age_min', 25))
                        age_max = self._safe_convert_age(row.get('age_max', 45))
                        
                        # Handle max_distance - convert 'any' to reasonable default
                        max_distance_str = row.get('max_distance', '50')
                        if max_distance_str.lower() == 'any':
                            preferred_distance = 100
                        else:
                            preferred_distance = self._safe_convert_distance(max_distance_str)
                        
                        # Create UserProfile with CSV data
                        UserProfile.objects.create(
                            user=user,
                            profile_name=row.get('profile_name', username),
                            date_of_birth=date_of_birth,
                            relationship_status=row.get('relationship_status', 'single').lower(),
                            body_type=row.get('body_type', 'average').lower(),
                            has_children=row.get('children', '').lower() in ['yes', 'true', '1'],
                            is_smoker=row.get('smoker', '').lower() in ['yes', 'true', '1'],
                            location=row.get('location', 'Unknown'),
                            story=row.get('my_story', 'No story provided yet.'),
                            communication_style=row.get('communication_style', 'Friendly'),
                            # Use safe converted values
                            preferred_age_min=age_min,
                            preferred_age_max=age_max,
                            preferred_distance=preferred_distance,
                            # New fields for CSV compatibility
                            gender=row.get('gender', '').lower(),
                            looking_for=row.get('looking_for', ''),
                            # System fields
                            is_complete=True,
                            is_approved=True
                        )
                        
                        imported_count += 1
                        
                        if imported_count % 50 == 0:
                            self.stdout.write(f"Progress: {imported_count} users imported...")
                            
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error on row {i} (user {username}): {str(e)}"))
                    skipped_count += 1
                    continue

        self.stdout.write(self.style.SUCCESS(
            f"Import completed: {imported_count} imported, {skipped_count} skipped"
        ))
        
        # Show sample
        self.stdout.write("\nSample imported users:")
        recent_users = User.objects.order_by('-date_joined')[:5]
        for user in recent_users:
            self.stdout.write(f"  - {user.username} ({user.email})")

    def _parse_date(self, date_str):
        """Parse date from various formats"""
        if not date_str:
            return None
        try:
            # Try different date formats
            for fmt in ['%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                try:
                    return datetime.strptime(date_str.strip(), fmt).date()
                except ValueError:
                    continue
            return None
        except Exception:
            return None

    def _safe_convert_age(self, age_str):
        """Safely convert age string to integer, handling 'any' and other non-numbers"""
        if not age_str:
            return 25  # Default
        
        age_str = str(age_str).strip().lower()
        
        if age_str == 'any':
            return 18  # Minimum legal age
        
        try:
            # Handle float strings like '25.0'
            age = float(age_str)
            return int(age)
        except (ValueError, TypeError):
            # If conversion fails, return reasonable default
            return 25

    def _safe_convert_distance(self, distance_str):
        """Safely convert distance string to integer"""
        if not distance_str:
            return 50  # Default
        
        distance_str = str(distance_str).strip().lower()
        
        if distance_str == 'any':
            return 100  # Large default distance
        
        try:
            # Remove 'km' and convert
            distance_str = distance_str.replace('km', '').strip()
            distance = float(distance_str)
            return int(distance)
        except (ValueError, TypeError):
            return 50  # Default
