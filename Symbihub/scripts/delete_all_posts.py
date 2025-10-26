import sqlite3, os, sys
DB = r'a:\\Symbihub\\symbihub.db'
if not os.path.exists(DB):
    print('DB not found at', DB)
    sys.exit(1)
conn = sqlite3.connect(DB)
cur = conn.cursor()
print('Deleting all rows from posts table...')
cur.execute('DELETE FROM posts')
conn.commit()
print('Deleted rows:', conn.total_changes)
conn.close()
print('Done')
