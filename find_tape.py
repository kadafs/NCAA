import sys
sys.stdout.reconfigure(encoding='utf-8')

mr_path = r'c:\Users\markk\OneDrive\Desktop\CODE\Sports Analytics\src\components\MatchRow.jsx'
with open(mr_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Search for "Matches Played" or "Tale of the Tape"
idx = text.find("Matches Played")
if idx != -1:
    print("Found 'Matches Played' at index", idx)
    start = max(0, idx - 500)
    end = min(len(text), idx + 1500)
    print(text[start:end])
else:
    print("'Matches Played' not found directly, searching for Tape:")
    idx2 = text.find("TALE OF THE TAPE")
    if idx2 != -1:
        print(text[max(0, idx2-200):min(len(text), idx2+1500)])
