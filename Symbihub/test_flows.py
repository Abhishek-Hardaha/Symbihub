from app import app, db
from datetime import datetime, timedelta

app.testing = True

with app.test_client() as client:
    # Login as sample user
    rv = client.post('/login', data={'username': 'anita-sharma', 'password': 'password123'}, follow_redirects=True)
    print('Login status code:', rv.status_code)

    # Create a post
    rv = client.post('/create_post', data={'content': 'Test post from automated test'}, follow_redirects=True)
    print('Create post status code:', rv.status_code)

    # Check feed
    rv = client.get('/feed')
    feed_html = rv.get_data(as_text=True)
    print('Feed contains test post:', 'Test post from automated test' in feed_html)

    # Create an event
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    event_data = {
        'title': 'Automated Test Event',
        'tagline': 'Testing event creation',
        'description': 'This event was created by an automated test.',
        'event_date': tomorrow,
        'venue': 'Test Hall',
        'category': 'Tech',
        'organization': 'TestOrg',
        'speakers': 'Alice,Bob',
        'schedule': '9 AM - Start',
        'rules': 'Be nice',
        'registration_fee': '0',
        'max_participants': '10'
    }
    rv = client.post('/create_event', data=event_data, follow_redirects=True)
    print('Create event status code:', rv.status_code)

    # Verify event in events listing
    rv = client.get('/events')
    events_html = rv.get_data(as_text=True)
    print('Events contains created event:', 'Automated Test Event' in events_html)

    # Find event id from DB
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM events WHERE title = ? ORDER BY id DESC LIMIT 1", ('Automated Test Event',))
    row = cur.fetchone()
    if row:
        event_id = row['id']
        print('Found event id:', event_id)

        # Register for event
        rv = client.post(f'/register_event/{event_id}', data={'ticket_type': 'Solo'}, follow_redirects=True)
        print('Register event status code:', rv.status_code)

        # Check my_events for registration
        rv = client.get('/my_events')
        my_events_html = rv.get_data(as_text=True)
        print('My events contains registration:', 'Automated Test Event' in my_events_html)
    else:
        print('Created event not found in DB')

    conn.close()

print('Automated test script finished')
