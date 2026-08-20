# add_method.py
"""
Add analyze_values method to all service files
"""

import os
import re

files = [
    "app/services/cbc_service.py",
    "app/services/kft_service.py",
    "app/services/thyroid_service.py",
    "app/services/diabetes_service.py",
    "app/services/vitamins_service.py",
    "app/services/electrolytes_service.py"
]

method = '''
    def analyze_values(self, values: Dict[str, float]) -> Dict[str, Any]:
        """Analyze values - API compatibility method."""
        return self.analyze(values)
'''

for file in files:
    if not os.path.exists(file):
        print(f"❌ File not found: {file}")
        continue
    
    with open(file, 'r') as f:
        content = f.read()
    
    if 'def analyze_values' in content:
        print(f"⏭️ Already has analyze_values: {file}")
        continue
    
    # Find the analyze method and insert after it
    pattern = r'(def analyze\(self, values: Dict\[str, float\](?:, gender: Optional\[str\] = None)?\) -> Dict\[str, Any\]:\s*""".*?"""\s*.*?\s*return {.*?}\s*)'
    
    match = re.search(pattern, content, re.DOTALL)
    if match:
        # Insert the new method before the analyze method
        new_content = content.replace(match.group(1), method + '\n' + match.group(1))
        with open(file, 'w') as f:
            f.write(new_content)
        print(f"✅ Updated: {file}")
    else:
        # Alternative: insert after __init__
        pattern = r'(def __init__\(self.*?\):.*?\n\s*super.*?\n\s*self\.engine.*?\n)'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            new_content = content.replace(match.group(1), match.group(1) + method)
            with open(file, 'w') as f:
                f.write(new_content)
            print(f"✅ Updated: {file}")
        else:
            # Insert at the end of the class
            pattern = r'(class \w+Service:.*?\n)'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                new_content = content.replace(match.group(1), match.group(1) + method)
                with open(file, 'w') as f:
                    f.write(new_content)
                print(f"✅ Updated: {file}")
            else:
                
                print(f"⚠️ Could not find insertion point in: {file}")

print("\n✅ All done!")
