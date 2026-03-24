import os
import re

UI_DIR = 'd:\\WorkSpace\\ShanYin\\ShanYinERP-v4\\ui'
PATTERNS = [
    r'session\.query\(',
    r'get_session\(',
    r'models import .* (?!get_session)'  # Looking for model imports
]

def check_compliance():
    violations = []
    for root, dirs, files in os.walk(UI_DIR):
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines):
                            for pattern in PATTERNS:
                                if re.search(pattern, line):
                                    violations.append({
                                        'file': file,
                                        'line': i + 1,
                                        'content': line.strip(),
                                        'pattern': pattern
                                    })
                except Exception as e:
                    print(f"Error reading {path}: {e}")
    
    output_path = 'd:/WorkSpace/ShanYin/ShanYinERP-v4/temp/compliance_report.txt'
    with open(output_path, 'w', encoding='utf-8') as f:
        if not violations:
            f.write("✅ No direct DB access violations found in UI layer.\n")
            print("✅ No direct DB access violations found in UI layer.")
        else:
            f.write(f"❌ Found {len(violations)} potential violations in UI layer:\n\n")
            print(f"❌ Found {len(violations)} potential violations in UI layer. Report saved to {output_path}")
            current_file = ""
            for v in violations:
                if v['file'] != current_file:
                    f.write(f"\nFile: {v['file']}\n")
                    current_file = v['file']
                f.write(f"  Line {v['line']}: {v['content']}\n")

if __name__ == "__main__":
    check_compliance()
