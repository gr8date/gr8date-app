import os
import re

def update_footers(directory):
    updated_files = []
    skipped_files = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check if this file has the footer structure we want to update
                    has_safety_guidelines = '/safety-guidelines/' in content
                    has_trust_safety = '/trust-safety/' in content
                    
                    if not (has_safety_guidelines or has_trust_safety):
                        skipped_files.append(filepath)
                        continue
                    
                    # Replace Safety Guidelines with Safety Center
                    new_content = re.sub(
                        r'<a href="/safety-guidelines/" class="footer-link" itemprop="url">Safety Guidelines</a>',
                        '<a href="/safety/" class="footer-link" itemprop="url">Safety Center</a>',
                        content
                    )
                    
                    # Remove Trust & Safety link
                    new_content = re.sub(
                        r'<a href="/trust-safety/" class="footer-link" itemprop="url">Trust & Safety</a>',
                        '',
                        new_content
                    )
                    
                    # Only write if changes were made
                    if new_content != content:
                        # Create backup
                        backup_path = filepath + '.backup'
                        with open(backup_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        
                        # Write updated content
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        
                        updated_files.append(filepath)
                        print(f"✅ UPDATED: {filepath}")
                    else:
                        skipped_files.append(filepath)
                        
                except Exception as e:
                    print(f"❌ ERROR processing {filepath}: {e}")
    
    # Print summary
    print(f"\n=== SUMMARY ===")
    print(f"✅ Updated files: {len(updated_files)}")
    print(f"⏭️  Skipped files: {len(skipped_files)}")
    
    if updated_files:
        print(f"\nUpdated files:")
        for file in updated_files:
            print(f"  - {file}")
    
    return updated_files

def main():
    print("=== Footer Link Updater ===")
    print("This script will:")
    print("1. Replace '/safety-guidelines/' with '/safety/' (Safety Guidelines → Safety Center)")
    print("2. Remove '/trust-safety/' link entirely")
    print("3. Skip files that don't contain these links")
    print("4. Create backup files with .backup extension")
    print()
    
    # Get templates directory path
    templates_dir = input("Enter the path to your templates directory: ").strip()
    
    # Remove quotes if user added them
    templates_dir = templates_dir.strip('"\'')
    
    # Verify directory exists
    if not os.path.exists(templates_dir):
        print(f"❌ Error: Directory '{templates_dir}' does not exist!")
        return
    
    print(f"\nScanning directory: {templates_dir}")
    
    # Confirm before proceeding
    confirm = input("\nProceed with updates? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Update cancelled.")
        return
    
    print("\nStarting update process...")
    updated_files = update_footers(templates_dir)
    
    if updated_files:
        print(f"\n🎉 Successfully updated {len(updated_files)} files!")
        print("Backup files were created with .backup extension")
    else:
        print("\nNo files needed updating.")

if __name__ == "__main__":
    main()
