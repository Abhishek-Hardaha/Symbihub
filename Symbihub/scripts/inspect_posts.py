import sqlite3, os, json

db = r'a:\\Symbihub\\symbihub.db'
if not os.path.exists(db):
    print('DB not found at', db)
    raise SystemExit(1)
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute('SELECT id,user_id,content,image_url,created_at FROM posts ORDER BY id DESC LIMIT 50')
rows = cur.fetchall()
print('POSTS:')
for r in rows:
    d = dict(r)
    print(json.dumps(d, default=str))
conn.close()

uploads_dir = r'a:\\Symbihub\\static\\uploads'
print('\nUPLOADS DIR EXISTS:', os.path.exists(uploads_dir))
if os.path.exists(uploads_dir):
    for f in os.listdir(uploads_dir):
        print(f)
else:
    print('No uploads directory')
