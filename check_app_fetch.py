import re

with open(r'c:\Users\markk\OneDrive\Desktop\CODE\Sports Analytics\src\App.jsx', 'r', encoding='utf-8') as f:
    app_text = f.read()

for line in app_text.splitlines():
    if 'fetch' in line or '.json' in line or 'predictions' in line:
        if len(line.strip()) < 120:
            print(line.strip())
