#!/usr/bin/env python3
import os
import glob

standard_footer = '''
        <div class="footer-links">
          <a href="index.html">Home</a>
          <a href="aboutus.html">About</a>
          <a href="contact us.html">Contact</a>
          <a href="privacy.html">Privacy</a>
          <a href="terms.html">Terms</a>
          <a href="faq.html">FAQ</a>
          <a href="trustsafety.html">Safety</a>
        </div>'''

for file_path in glob.glob('./website/templates/website/*.html'):
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Remove any existing footer links section
    lines = content.split('\n')
    new_lines = []
    in_footer_links = False
    
    for line in lines:
        if 'footer-links' in line:
            in_footer_links = True
            continue
        if in_footer_links and '</div>' in line:
            in_footer_links = False
            continue
        if not in_footer_links:
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    
    # Add standard footer links after <footer
    if '<footer' in content:
        content = content.replace('<footer', '<footer' + standard_footer)
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Updated footer in: {file_path}")

print("All footers updated consistently!")
