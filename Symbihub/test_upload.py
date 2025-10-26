from app import app, db
from io import BytesIO

app.testing = True

with app.test_client() as client:
    # Login
    rv = client.post('/login', data={'username': 'anita-sharma', 'password': 'password123'}, follow_redirects=True)
    print('Login:', rv.status_code)

    # Prepare a fake image
    img = BytesIO()
    img.write(b'\x89PNG\r\n\x1a\n')
    img.seek(0)

    tomorrow = '2025-10-27'
    data = {
        'title': 'Upload Test Event',
        'tagline': 'Test upload',
        'description': 'Testing image upload',
        'event_date': tomorrow,
        'venue': 'Test Venue',
        'category': 'Tech',
        'organization': 'TestOrg',
        'speakers': 'X',
        'schedule': 'N/A',
        'rules': '',
        'registration_fee': '0',
        'max_participants': '10',
    }

    # files must be provided via a dict where value is (fileobj, filename)
    data_files = {
        'cover_image': (img, 'test.png')
    }

    rv = client.post('/create_event', data={**data, **data_files}, content_type='multipart/form-data', follow_redirects=True)
    print('Create with file status:', rv.status_code)

    # Check DB for the event
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, cover_image FROM events WHERE title = ? ORDER BY id DESC LIMIT 1", ('Upload Test Event',))
    row = cur.fetchone()
    print('DB row:', row)
    conn.close()
