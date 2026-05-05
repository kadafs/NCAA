import requests, re
from html.parser import HTMLParser

class AttrCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.data_attrs = {}

    def handle_starttag(self, tag, attrs):
        for name, val in attrs:
            if name.startswith('data-') and val:
                self.data_attrs.setdefault(name, set()).add(val)

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
res = requests.get('https://nbl1.com.au/fixtures', headers=headers, timeout=20)

collector = AttrCollector()
collector.feed(res.text)

print("=== ALL data-* attribute names found in HTML ===")
for name in sorted(collector.data_attrs.keys()):
    vals = collector.data_attrs[name]
    sample = list(vals)[:2]
    print(f"  {name}: {sample} ({len(vals)} unique values)")
