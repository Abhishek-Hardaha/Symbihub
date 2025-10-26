import sqlite3
import os
from werkzeug.security import generate_password_hash
from contextlib import contextmanager


class Database:
    """SQLite helper with sane defaults and a context manager.

    This keeps the `get_connection()` API used across the app while
    adding PRAGMAs and a `connection()` context manager for safer use.
    """

    def __init__(self, db_path=None):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = db_path or os.environ.get('SYMBIHUB_DB') or os.path.join(base_dir, 'symbihub.db')
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        # enable foreign keys and set WAL mode for better concurrency
        conn.execute('PRAGMA foreign_keys = ON')
        conn.execute('PRAGMA journal_mode = WAL')
        conn.execute('PRAGMA synchronous = NORMAL')
        return conn

    @contextmanager
    def connection(self):
        conn = self.get_connection()
        cur = conn.cursor()
        try:
            yield conn, cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self):
        with self.connection() as (conn, cursor):
            # users
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    bio TEXT,
                    college_id VARCHAR(20),
                    profile_image TEXT,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    events_attended INTEGER DEFAULT 0,
                    events_organized INTEGER DEFAULT 0,
                    volunteer_hours INTEGER DEFAULT 0,
                    interests TEXT,
                    achievements TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # clubs
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS clubs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    icon VARCHAR(50),
                    banner_image TEXT,
                    members_count INTEGER DEFAULT 0,
                    events_count INTEGER DEFAULT 0,
                    followers_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # events
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title VARCHAR(200) NOT NULL,
                    tagline TEXT,
                    description TEXT,
                    cover_image TEXT,
                    event_date DATE NOT NULL,
                    venue VARCHAR(200),
                    category VARCHAR(50),
                    organization VARCHAR(100),
                    speakers TEXT,
                    schedule TEXT,
                    rules TEXT,
                    registration_fee DECIMAL(10,2) DEFAULT 0,
                    max_participants INTEGER DEFAULT 100,
                    registered_count INTEGER DEFAULT 0,
                    status VARCHAR(20) DEFAULT 'upcoming',
                    club_id INTEGER,
                    created_by INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (club_id) REFERENCES clubs (id),
                    FOREIGN KEY (created_by) REFERENCES users (id)
                )
            ''')

            # event_registrations
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS event_registrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    ticket_type VARCHAR(50) DEFAULT 'Solo',
                    payment_status VARCHAR(20) DEFAULT 'pending',
                    qr_code VARCHAR(100),
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (event_id) REFERENCES events (id),
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(event_id, user_id)
                )
            ''')

            # attendance
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    check_in TIMESTAMP,
                    check_out TIMESTAMP,
                    status VARCHAR(20) DEFAULT 'present',
                    FOREIGN KEY (event_id) REFERENCES events (id),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')

            # posts
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    likes_count INTEGER DEFAULT 0,
                    comments_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')

            # comments
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (post_id) REFERENCES posts (id),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')

            # notifications
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title VARCHAR(200) NOT NULL,
                    message TEXT NOT NULL,
                    type VARCHAR(50),
                    is_read BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')

            # user_clubs
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_clubs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    club_id INTEGER NOT NULL,
                    role VARCHAR(50) DEFAULT 'member',
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (club_id) REFERENCES clubs (id),
                    UNIQUE(user_id, club_id)
                )
            ''')

            # event_photos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS event_photos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    image_url TEXT NOT NULL,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (event_id) REFERENCES events (id),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')

            # polls
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS polls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    options TEXT NOT NULL,
                    event_id INTEGER,
                    status VARCHAR(20) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (event_id) REFERENCES events (id)
                )
            ''')

            # poll_votes
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS poll_votes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    poll_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    option_index INTEGER NOT NULL,
                    voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (poll_id) REFERENCES polls (id),
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(poll_id, user_id)
                )
            ''')

            # fundraisers
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fundraisers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title VARCHAR(200) NOT NULL,
                    description TEXT,
                    goal_amount DECIMAL(12,2) NOT NULL,
                    raised_amount DECIMAL(12,2) DEFAULT 0,
                    donors_count INTEGER DEFAULT 0,
                    status VARCHAR(20) DEFAULT 'active',
                    created_by INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users (id)
                )
            ''')

            # certificates
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS certificates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    event_id INTEGER NOT NULL,
                    certificate_type VARCHAR(50) DEFAULT 'Participation',
                    template VARCHAR(50) DEFAULT 'default',
                    issued_date DATE DEFAULT CURRENT_DATE,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (event_id) REFERENCES events (id)
                )
            ''')

        # try to insert sample data only if users table is empty
        self.insert_sample_data()

    def insert_sample_data(self):
        with self.connection() as (conn, cursor):
            try:
                cursor.execute('SELECT COUNT(*) FROM users')
                if cursor.fetchone()[0] > 0:
                    return
            except Exception:
                return

            users_data = [
                ('anita-sharma', 'anita@example.com', generate_password_hash('password123'), 'Anita Sharma', '2nd Year CSE. Passionate about AI.', 'SIT2023001', 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=100&q=60', 1250, 5, 12, 3, 25, 'AI/ML,Programming,Robotics', 'Hackathon Winner,Best Organizer'),
                ('rohan-gupta', 'rohan@example.com', generate_password_hash('password123'), 'Rohan Gupta', '3rd Year IT. Backend specialist.', 'SIT2022001', 'https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?auto=format&fit=crop&w=100&q=60', 980, 4, 8, 1, 15, 'Backend Development,Database,APIs', 'Best Backend Developer')
            ]

            for user in users_data:
                cursor.execute('''
                    INSERT INTO users (username, email, password_hash, name, bio, college_id, profile_image, xp, level, events_attended, events_organized, volunteer_hours, interests, achievements)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', user)


# module-level instance for backwards compatibility
db = Database()
