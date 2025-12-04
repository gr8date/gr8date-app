import os
import re

def diagnose_remaining_issues():
    templates_folder = 'website/templates/website/'
    
    print("🔍 Diagnosing remaining issues...")
    
    for filename in os.listdir(templates_folder):
        if filename.endswith('.html'):
            filepath = os.path.join(templates_folder, filename)
            
            with open(filepath, 'r') as file:
                content = file.read()
            
            # Check for specific problematic patterns
            issues_found = []
            
            # Pattern 1: mobile-cta-container
            if 'mobile-cta-container' in content:
                issues_found.append('mobile-cta-container')
            
            # Pattern 2: REMOVED comments
            if '/* REMOVED */' in content:
                issues_found.append('REMOVED comments')
            
            # Pattern 3: Excessive !important chains
            if '!important' in content and content.count('!important') > 10:
                issues_found.append('excessive !important')
            
            # Pattern 4: Duplicate media queries from fix scripts
            media_query_count = len(re.findall(r'@media.*?max-width.*?768px', content, re.IGNORECASE | re.DOTALL))
            if media_query_count > 1:
                issues_found.append(f'duplicate media queries ({media_query_count} found)')
            
            if issues_found:
                print(f"\n⚠️  {filename}:")
                print(f"   Issues: {', '.join(issues_found)}")
                
                # Show context around the issues
                for issue in issues_found:
                    if issue == 'mobile-cta-container':
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if 'mobile-cta-container' in line:
                                start = max(0, i-2)
                                end = min(len(lines), i+3)
                                print(f"   Context for {issue}:")
                                for j in range(start, end):
                                    print(f"      {j+1}: {lines[j]}")
                                break

if __name__ == "__main__":
    diagnose_remaining_issues()
