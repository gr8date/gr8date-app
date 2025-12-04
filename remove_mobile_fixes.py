import os
import re

def remove_all_mobile_fixes():
    templates_folder = 'website/templates/website/'
    
    for filename in os.listdir(templates_folder):
        if filename.endswith('.html'):
            filepath = os.path.join(templates_folder, filename)
            with open(filepath, 'r') as file:
                content = file.read()
            
            # Remove ALL the mobile CSS we added in the last few scripts
            content = re.sub(r'<style>\s*/\* Mobile-first.*?</style>', '', content, flags=re.DOTALL)
            content = re.sub(r'<style>\s*/\* Desktop styles.*?</style>', '', content, flags=re.DOTALL)
            content = re.sub(r'@media.*?\{.*?\}', '', content, flags=re.DOTALL)
            content = re.sub(r'<style>\s*/\* Mobile.*?</style>', '', content, flags=re.DOTALL)
            
            # Remove any empty style tags
            content = re.sub(r'<style>\s*</style>', '', content)
            
            with open(filepath, 'w') as file:
                file.write(content)
            print(f"✅ Removed mobile fixes from: {filename}")
    
    print("\n🎉 All mobile CSS removed! Back to clean state.")

if __name__ == "__main__":
    remove_all_mobile_fixes()
