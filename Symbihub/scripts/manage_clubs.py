from database import Database

clubs = [
    ("AI Club", "Community for AI learners and practitioners. Workshops, hackathons, and study groups.", "ph-brain"),
    ("Foss Club", "Free and Open Source Software club: contributors, meetups, and projects.", "ph-code"),
    ("Google Developers", "Google Developer Student Club chapter focusing on web and cloud development.", "ph-google-logo"),
    ("Codex", "Coding community for competitive programming and system design.", "ph-terminal"),
    ("Mosaic", "Interdisciplinary creative tech and arts club.", "ph-palette"),
    ("Symbiosis Music Society", "Music society for performances, jams and workshops.", "ph-music-notes"),
    ("Sole to Soul", "Dance club promoting choreography and cultural dance forms.", "ph-walking"),
    ("Antriksh Space Club", "Aerospace and rocketry interest group conducting workshops and launches.", "ph-rocket-launch")
]

if __name__ == '__main__':
    db = Database()
    with db.connection() as (conn, cur):
        # Insert clubs if they don't already exist
        for name, desc, icon in clubs:
            cur.execute('SELECT id FROM clubs WHERE name = ?', (name,))
            if not cur.fetchone():
                cur.execute('''
                    INSERT INTO clubs (name, description, icon, members_count, events_count, followers_count)
                    VALUES (?, ?, ?, 0, 0, 0)
                ''', (name, desc, icon))
                print(f"Inserted club: {name}")
            else:
                print(f"Club already exists: {name}")

        # Remove events named 'Automated Test Event' safely (delete dependent rows first)
        cur.execute('SELECT id FROM events WHERE title = ?', ("Automated Test Event",))
        rows = cur.fetchall()
        event_ids = [r['id'] for r in rows]
        if event_ids:
            for eid in event_ids:
                # Delete registrations
                cur.execute('DELETE FROM event_registrations WHERE event_id = ?', (eid,))
                # Delete attendance
                cur.execute('DELETE FROM attendance WHERE event_id = ?', (eid,))
                # Delete event photos
                cur.execute('DELETE FROM event_photos WHERE event_id = ?', (eid,))
                # Delete polls
                cur.execute('DELETE FROM polls WHERE event_id = ?', (eid,))
                # Finally delete the event
                cur.execute('DELETE FROM events WHERE id = ?', (eid,))
                print(f"Deleted event id={eid} titled 'Automated Test Event' and its dependents.")
        else:
            print("No 'Automated Test Event' events found.")
    print('Done.')
