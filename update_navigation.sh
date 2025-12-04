#!/bin/bash

# Define the new navigation HTML with Django URL patterns
NEW_NAV='
      <nav class="nav-links">
        <a href="{% url '\''discover'\'' %}" class="nav-link">Discover</a>
        <a href="{% url '\''success_stories'\'' %}" class="nav-link">Success Stories</a>
        <a href="{% url '\''about'\'' %}" class="nav-link">About</a>
      </nav>

      <div class="auth-buttons">
        <a href="{% url '\''login'\'' %}" class="btn btn-login">Sign In</a>
        <a href="{% url '\''join'\'' %}" class="btn btn-join">Join Elite</a>
      </div>'

NEW_MOBILE_NAV='
    <nav class="mobile-nav-links">
      <a href="{% url '\''discover'\'' %}" class="nav-link" style="--delay: 0.1s;">Discover</a>
      <a href="{% url '\''success_stories'\'' %}" class="nav-link" style="--delay: 0.2s;">Success Stories</a>
      <a href="{% url '\''about'\'' %}" class="nav-link" style="--delay: 0.3s;">About</a>
    </nav>'

# Update all HTML files with proper navigation
for file in ./website/templates/website/*.html; do
  if [ -f "$file" ]; then
    echo "Updating navigation in: $file"
    
    # Replace navigation sections
    sed -i '' '/<nav class="nav-links">/,/<\/nav>/c\
      <nav class="nav-links">\
        <a href="{% url '\''discover'\'' %}" class="nav-link">Discover</a>\
        <a href="{% url '\''success_stories'\'' %}" class="nav-link">Success Stories</a>\
        <a href="{% url '\''about'\'' %}" class="nav-link">About</a>\
      </nav>\
      \
      <div class="auth-buttons">\
        <a href="{% url '\''login'\'' %}" class="btn btn-login">Sign In</a>\
        <a href="{% url '\''join'\'' %}" class="btn btn-join">Join Elite</a>\
      </div>' "$file"
    
    # Replace mobile navigation
    sed -i '' '/<nav class="mobile-nav-links">/,/<\/nav>/c\
    <nav class="mobile-nav-links">\
      <a href="{% url '\''discover'\'' %}" class="nav-link" style="--delay: 0.1s;">Discover</a>\
      <a href="{% url '\''success_stories'\'' %}" class="nav-link" style="--delay: 0.2s;">Success Stories</a>\
      <a href="{% url '\''about'\'' %}" class="nav-link" style="--delay: 0.3s;">About</a>\
    </nav>' "$file"
  fi
done

echo "Navigation update complete!"
