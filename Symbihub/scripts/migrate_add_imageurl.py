import sqlite3, os, sys

DB = r'a:\\Symbihub\\symbihub.db'
if not os.path.exists(DB):
    print('DB not found at', DB)
    sys.exit(1)

conn = sqlite3.connect(DB)
cur = conn.cursor()
# Check if column exists
cur.execute("PRAGMA table_info(posts)")
cols = [r[1] for r in cur.fetchall()]
print('Existing columns:', cols)
if 'image_url' in cols:
    print('image_url already exists; nothing to do')
    conn.close()
    sys.exit(0)

try:
    cur.execute('ALTER TABLE posts ADD COLUMN image_url TEXT')
    conn.commit()
    print('ALTER TABLE succeeded: image_url added')
except Exception as e:
    print('ALTER TABLE failed:', e)
    conn.rollback()
finally:
    # show final columns
    cur.execute("PRAGMA table_info(posts)")
    cols2 = [r[1] for r in cur.fetchall()]
    print('Final columns:', cols2)
    conn.close()
