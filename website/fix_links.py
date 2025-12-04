import os
import shutil

# Backup first!
if os.path.exists('website_backup'):
    shutil.rmtree('website_backup')
shutil.copytree('website', 'website_backup')
print("Backup created at website_backup/")

replacements = {
    'href="loginpage.html"': 'href="{% url \'login\' %}"',
    'href="premiummembershipsdetails.html"': 'href="{% url \'premium\' %}"',
    'href="join.html"': 'href="{% url \'join\' %}"',
    'href="discoverelitemembers.html"': 'href="{% url \'discover\' %}"',
    'href="successstories.html"': 'href="{% url \'success_stories\' %}"',
    'href="exclusiveevents.html"': 'href="{% url \'events\' %}"',
    'href="aboutus.html"': 'href="{% url \'about\' %}"',
    'href="helpcenter.html"': 'href="{% url \'help\' %}"',
    'href="faq.html"': 'href="{% url \'faq\' %}"',
    'href="terms.html"': 'href="{% url \'terms\' %}"',
    'href="privacy.html"': 'href="{% url \'privacy\' %}"',
    'href="safetyguidelines.html"': 'href="{% url \'safety\' %}"',
    'href="trustsafety.html"': 'href="{% url \'trust\' %}"',
    'href="contact us.html"': 'href="{% url \'contact\' %}"'
}

for filename in os.listdir('website/'):
    if filename.endswith('.html'):
        filepath = f'website/{filename}'
        with open(filepath, 'r') as file:
            content = file.read()
        
        original_content = content
        
        for old, new in replacements.items():
            content = content.replace(old, new)
        
        # Only write if changes were made
        if content != original_content:
            with open(filepath, 'w') as file:
                file.write(content)
            print(f"Updated: {filename}")

print("Done! Backup available at website_backup/")
