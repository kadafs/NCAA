# Extract Links from Proballers Sitemap

The goal is to extract all links from `https://www.proballers.com/medias/sitemap.html` and save them to a file.

## Proposed Changes

### [Script] proballers_extractor.py [NEW]
A script to extract links from the sitemap. This will be done via the browser subagent.

#### [NEW] [proballers_links.txt](file:///C:/Users/markk/.gemini/antigravity/scratch/proballers_links.txt)
Storage for the extracted links.

## Verification Plan

### Manual Verification
- Verify the content of `proballers_links.txt` to ensure it contains a list of valid URLs.
- Check a few links to see if they point to correct player/team pages on Proballers.
