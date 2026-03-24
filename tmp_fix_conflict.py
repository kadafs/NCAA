import re, sys

path = "data/football/universal_predictions_2026-03-23.json"
with open(path, encoding="utf-8") as f:
    content = f.read()

# Remove git conflict markers, keeping the HEAD (<<<< ... ====) section content
def resolve_conflict(text):
    pattern = re.compile(
        r'<<<<<<< HEAD\n(.*?)=======\n.*?>>>>>>> [^\n]+\n',
        re.DOTALL
    )
    resolved = pattern.sub(r'\1', text)
    return resolved

fixed = resolve_conflict(content)

with open(path, "w", encoding="utf-8") as f:
    f.write(fixed)

# Validate
import json
try:
    json.loads(fixed)
    print("JSON valid after merge conflict resolution.")
except Exception as e:
    print(f"Still invalid: {e}")
