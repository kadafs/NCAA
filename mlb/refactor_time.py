import os, re

for root, _, files in os.walk('mlb'):
    for file in files:
        if file.endswith('.py') and file not in ('mlb_time.py', 'refactor_time.py'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'datetime.now()' in content or 'datetime.datetime.now()' in content:
                content = re.sub(r'(?<!\.)datetime\.datetime\.now\(\)', 'get_mlb_now()', content)
                content = re.sub(r'(?<!\.)datetime\.now\(\)', 'get_mlb_now()', content)
                
                if 'from mlb_time import get_mlb_now' not in content:
                    content = 'from mlb_time import get_mlb_now\n' + content
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f'Refactored {filepath}')
