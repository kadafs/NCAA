import re

def get_followers(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # In followers_1.html: href="https://www.instagram.com/username"
    # Note: Sometimes there might be queries like ?igshid=..., we only want the username
    # Let's extract from the inner text of the anchor tags for safety, or just the URL.
    # From the file view: <a target="_blank" href="https://www.instagram.com/el_aderm1">el_aderm1</a>
    matches = re.findall(r'<a target="_blank" href="https://www.instagram.com/([^"/]+)">', content)
    return set(matches)

def get_following(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # In following.html: <a target="_blank" href="https://www.instagram.com/_u/aaron_n8">
    matches = re.findall(r'<a target="_blank" href="https://www.instagram.com/_u/([^"/]+)">', content)
    return set(matches)

import os

followers = get_followers(r'c:\Users\markk\OneDrive\Desktop\CODE\ncaa-api\followers_1.html')
following = get_following(r'c:\Users\markk\OneDrive\Desktop\CODE\ncaa-api\following.html')

not_following_back = following - followers

artifact_path = r'C:\Users\markk\.gemini\antigravity-ide\brain\d426eeac-ba70-4d3f-bf0c-de5d70eed2d5\unfollowers_list.md'
with open(artifact_path, 'w', encoding='utf-8') as f:
    f.write("# Accounts Not Following Back\n\n")
    for user in sorted(not_following_back):
        f.write(f"- [{user}](https://www.instagram.com/{user})\n")

print(f"Wrote {len(not_following_back)} accounts to {artifact_path}")
