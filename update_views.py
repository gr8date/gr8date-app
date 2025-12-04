import os

def update_views_file():
    views_file = 'website/views.py'
    
    with open(views_file, 'r') as file:
        content = file.read()
    
    # Replace all template paths to use the new structure
    old_paths = [
        "render(request, 'website/",
        "render(request, 'website/"
    ]
    
    new_path = "render(request, 'website/"
    
    # Count replacements
    original_content = content
    content = content.replace("render(request, 'website/", "render(request, 'website/")
    
    if content != original_content:
        with open(views_file, 'w') as file:
            file.write(content)
        print("✅ Updated views.py to use new template paths")
        print("All templates now point to: 'website/templates/website/'")
    else:
        print("✅ views.py already uses correct template paths")

if __name__ == "__main__":
    update_views_file()
