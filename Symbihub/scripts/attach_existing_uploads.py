import sqlite3, os, sys
from datetime import datetime

DB = r'a:\\Symbihub\\symbihub.db'
UPLOADS = r'a:\\Symbihub\\static\\uploads'

if not os.path.exists(DB):
    print('DB not found at', DB); sys.exit(1)
if not os.path.exists(UPLOADS):
    print('Uploads dir not found at', UPLOADS); sys.exit(1)

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
# get posts missing image_url
cur.execute("SELECT id, user_id, content, created_at FROM posts WHERE image_url IS NULL ORDER BY created_at ASC")
posts = cur.fetchall()
print('Posts missing image_url:', len(posts))
# list files sorted by mtime ascending (oldest first)
files = [f for f in os.listdir(UPLOADS) if os.path.isfile(os.path.join(UPLOADS, f))]
files.sort(key=lambda fn: os.path.getmtime(os.path.join(UPLOADS, fn)))
print('Found files:', len(files))

used = set()
file_index = 0
for p in posts:
    if file_index >= len(files):
        print('No more files to attach')
        break
    filename = files[file_index]
    file_index += 1
    image_url = '/uploads/' + filename
    print(f"Attaching {filename} -> post id {p['id']}")
    try:
        cur.execute('UPDATE posts SET image_url = ? WHERE id = ?', (image_url, p['id']))
    except Exception as e:
        print('Failed to update post', p['id'], e)

conn.commit()
conn.close()
print('Done')
