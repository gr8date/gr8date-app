#!/bin/bash

for file in ./website/templates/website/*.html; do
  if [ -f "$file" ]; then
    echo "Checking footer in: $file"
    
    # Check if footer links already exist
    if ! grep -q "footer.*links" "$file"; then
      echo "Adding footer links to: $file"
      
      # Create a temporary file for the modification
      temp_file="${file}.tmp"
      
      # Use awk to add footer links after the footer opening tag
      awk '/<footer/ {print; print "        <div class=\"footer-links\">"; print "          <a href=\"aboutus.html\">About</a>"; print "          <a href=\"contact us.html\">Contact</a>"; print "          <a href=\"privacy.html\">Privacy</a>"; print "          <a href=\"terms.html\">Terms</a>"; print "          <a href=\"faq.html\">FAQ</a>"; print "        </div>"; next} 1' "$file" > "$temp_file"
      
      # Replace the original file
      mv "$temp_file" "$file"
    else
      echo "Footer links already exist in: $file"
    fi
  fi
done

echo "Footer update complete!"
