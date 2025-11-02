# pages/migrations/0023_add_age_field.py
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0022_blog_image_alt_text_blog_keywords_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='age',
            field=models.PositiveSmallIntegerField(
                blank=True, 
                null=True,
                help_text="User-provided age for display"
            ),
        ),
    ]
