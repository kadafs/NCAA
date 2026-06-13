import os, re

for root, _, files in os.walk('mlb'):
    for file in files:
        if file.endswith('.py') and file not in ('mlb_time.py', 'refactor_time.py', 'refactor_date.py'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'datetime.date.today()' in content:
                content = content.replace('datetime.date.today()', 'get_mlb_now().date()')
                
                if 'from mlb_time import get_mlb_now' not in content:
                    content = 'from mlb_time import get_mlb_now\n' + content
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f'Refactored {filepath}')
