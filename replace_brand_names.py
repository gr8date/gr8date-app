import os
import re

def replace_brand_names():
    templates_folder = 'website/templates/website/'
    
    replacements = {
        'AgreedDating': 'Favourable',
        'Agreed Dating': 'Favourable',
        'agreeddating': 'favourable',
        'agreed dating': 'favourable',
        'Elite Dating': 'Premium Connections',
        'exclusive dating': 'sophisticated connections',
        'premium dating': 'meaningful relationships'
    }
    
    updated_files = []
    
    for filename in os.listdir(templates_folder):
        if filename.endswith('.html'):
            filepath = os.path.join(templates_folder, filename)
            with open(filepath, 'r') as file:
                content = file.read()
            
            original_content = content
            
            # Replace all brand names
            for old, new in replacements.items():
                content = content.replace(old, new)
            
            if content != original_content:
                with open(filepath, 'w') as file:
                    file.write(content)
                updated_files.append(filename)
                print(f"✅ Updated brand names in: {filename}")
    
    print(f"\n🎉 Updated {len(updated_files)} files with new brand name 'Favourable'")
    print("All references to 'AgreedDating' have been replaced")

if __name__ == "__main__":
    replace_brand_names()
