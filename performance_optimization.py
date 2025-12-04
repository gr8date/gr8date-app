#!/usr/bin/env python3
import glob
import re

print("=== ADDING PERFORMANCE OPTIMIZATIONS ===")

for file_path in glob.glob('./website/templates/website/*.html'):
    with open(file_path, 'r') as f:
        content = f.read()
    
    filename = file_path.split('/')[-1]
    
    # Add preload for critical resources
    preload_tags = '''
    <!-- Preload Critical Resources -->
    <link rel="preload" href="{% static 'images/aglogo.png' %}" as="image">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
'''
    
    # Add these before the first CSS or JS link
    if '<link rel="stylesheet"' in content and 'preload' not in content:
        content = content.replace('<link rel="stylesheet"', f'{preload_tags}\n    <link rel="stylesheet"', 1)
    
    # Add lazy loading to non-critical images
    content = re.sub(
        r'<img(?!.*loading=)([^>]*)>',
        r'<img loading="lazy"\1>',
        content
    )
    
    # Write optimized content back
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Optimized: {filename}")

print("\\n🎯 PERFORMANCE OPTIMIZATIONS ADDED:")
print("✅ Critical resource preloading")
print("✅ Lazy loading for images")
print("✅ Font preconnect for faster loading")
