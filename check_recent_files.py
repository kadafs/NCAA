import os, glob, time

files = glob.glob(r'data\football\*.*')
files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
print("Most recently modified football files in ncaa-api:")
for f in files[:15]:
    mtime = time.ctime(os.path.getmtime(f))
    print(f"{f}: {mtime} ({os.path.getsize(f)} bytes)")
