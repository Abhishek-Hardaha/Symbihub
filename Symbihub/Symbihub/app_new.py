from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, send_from_directory, session, flash, url_for
import json
import csv
import io
from datetime import datetime, timedelta
import uuid
import qrcode
from io import BytesIO
import base64
import os
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from database import db
import sqlite3

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

# Configuration for file uploads
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_current_user():
    """Get current logged in user"""
    if 'user_id' in session:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],))
        user = cursor.fetchone()
        conn.close()
        return user
    return None

def login_required(f):
    """Decorator to require login for certain routes"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Serve static files
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# Serve uploaded files
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? OR email = ?", (username, username))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        college_id = request.form.get('college_id')
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if user already exists
        cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
        if cursor.fetchone():
            flash('Username or email already exists.', 'error')
            conn.close()
            return render_template('login.html')
        
        # Create new user
        password_hash = generate_password_hash(password)
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, name, college_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, email, password_hash, name, college_id))
        
        conn.commit()
        conn.close()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('landing'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get upcoming events
    cursor.execute('''
        SELECT e.*, c.name as club_name, u.name as organizer_name
        FROM events e
        LEFT JOIN clubs c ON e.club_id = c.id
        LEFT JOIN users u ON e.created_by = u.id
        WHERE e.event_date >= date('now')
        ORDER BY e.event_date ASC
        LIMIT 10
    ''')
    events = cursor.fetchall()
    
    # Get recent posts
    cursor.execute('''
        SELECT p.*, u.name, u.profile_image
        FROM posts p
        JOIN users u ON p.user_id = u.id
        ORDER BY p.created_at DESC
        LIMIT 5
    ''')
    posts = cursor.fetchall()
    
    conn.close()
    
    return render_template('dashboard.html', events=events, posts=posts)

@app.route('/events')
@login_required
def events():
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get all events with filters
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    
    query = '''
        SELECT e.*, c.name as club_name, u.name as organizer_name
        FROM events e
        LEFT JOIN clubs c ON e.club_id = c.id
        LEFT JOIN users u ON e.created_by = u.id
        WHERE 1=1
    '''
    params = []
    
    if category:
        query += " AND e.category = ?"
        params.append(category)
    
    if search:
        query += " AND (e.title LIKE ? OR e.description LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%'])
    
    query += " ORDER BY e.event_date ASC"
    
    cursor.execute(query, params)
    events = cursor.fetchall()
    
    # Get categories for filter
    cursor.execute("SELECT DISTINCT category FROM events WHERE category IS NOT NULL")
    categories = cursor.fetchall()
    
    conn.close()
    
    return render_template('events.html', events=events, categories=categories)

@app.route('/my_events')
@login_required
def my_events():
    user = get_current_user()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get events created by user
    cursor.execute('''
        SELECT e.*, c.name as club_name
        FROM events e
        LEFT JOIN clubs c ON e.club_id = c.id
        WHERE e.created_by = ?
        ORDER BY e.event_date DESC
    ''', (user['id'],))
    created_events = cursor.fetchall()
    
    # Get events user is registered for
    cursor.execute('''
        SELECT e.*, c.name as club_name, er.registration_date, er.payment_status
        FROM events e
        LEFT JOIN clubs c ON e.club_id = c.id
        JOIN event_registrations er ON e.id = er.event_id
        WHERE er.user_id = ?
        ORDER BY e.event_date DESC
    ''', (user['id'],))
    registered_events = cursor.fetchall()
    
    conn.close()
    
    return render_template('my_events.html', created_events=created_events, registered_events=registered_events)

@app.route('/profile')
@login_required
def profile():
    user = get_current_user()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get user's event statistics
    cursor.execute('''
        SELECT 
            COUNT(DISTINCT er.event_id) as events_attended,
            COUNT(DISTINCT e.id) as events_organized
        FROM users u
        LEFT JOIN event_registrations er ON u.id = er.user_id
        LEFT JOIN events e ON u.id = e.created_by
        WHERE u.id = ?
    ''', (user['id'],))
    stats = cursor.fetchone()
    
    # Get user's clubs
    cursor.execute('''
        SELECT c.*, uc.role, uc.joined_at
        FROM clubs c
        JOIN user_clubs uc ON c.id = uc.club_id
        WHERE uc.user_id = ?
    ''', (user['id'],))
    user_clubs = cursor.fetchall()
    
    conn.close()
    
    return render_template('profile.html', user=user, stats=stats, user_clubs=user_clubs)

@app.route('/event/<int:event_id>')
@login_required
def event_details(event_id):
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get event details
    cursor.execute('''
        SELECT e.*, c.name as club_name, u.name as organizer_name
        FROM events e
        LEFT JOIN clubs c ON e.club_id = c.id
        LEFT JOIN users u ON e.created_by = u.id
        WHERE e.id = ?
    ''', (event_id,))
    event = cursor.fetchone()
    
    if not event:
        flash('Event not found.', 'error')
        return redirect(url_for('events'))
    
    # Check if user is registered
    user = get_current_user()
    cursor.execute("SELECT * FROM event_registrations WHERE event_id = ? AND user_id = ?", (event_id, user['id']))
    registration = cursor.fetchone()
    
    # Get event photos
    cursor.execute('''
        SELECT ep.*, u.name as uploader_name
        FROM event_photos ep
        JOIN users u ON ep.user_id = u.id
        WHERE ep.event_id = ?
        ORDER BY ep.uploaded_at DESC
    ''', (event_id,))
    photos = cursor.fetchall()
    
    conn.close()
    
    return render_template('event_details.html', event=event, registration=registration, photos=photos)

@app.route('/create_event', methods=['GET', 'POST'])
@login_required
def create_event():
    if request.method == 'POST':
        user = get_current_user()
        
        title = request.form.get('title')
        tagline = request.form.get('tagline')
        description = request.form.get('description')
        event_date = request.form.get('event_date')
        venue = request.form.get('venue')
        category = request.form.get('category')
        organization = request.form.get('organization')
        speakers = request.form.get('speakers', '')
        schedule = request.form.get('schedule', '')
        rules = request.form.get('rules', '')
        registration_fee = float(request.form.get('registration_fee', 0))
        max_participants = int(request.form.get('max_participants', 100))
        club_id = request.form.get('club_id') or None
        
        # Handle cover image upload
        cover_image = None
        if 'cover_image' in request.files:
            file = request.files['cover_image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filename = f"{uuid.uuid4()}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                cover_image = f"/uploads/{filename}"
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO events (title, tagline, description, cover_image, event_date, venue, category, organization, speakers, schedule, rules, registration_fee, max_participants, club_id, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, tagline, description, cover_image, event_date, venue, category, organization, speakers, schedule, rules, registration_fee, max_participants, club_id, user['id']))
        
        conn.commit()
        conn.close()
        
        flash('Event created successfully!', 'success')
        return redirect(url_for('my_events'))
    
    # GET request - show form
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clubs ORDER BY name")
    clubs = cursor.fetchall()
    conn.close()
    
    return render_template('create_event.html', clubs=clubs)

@app.route('/register_event/<int:event_id>', methods=['POST'])
@login_required
def register_event(event_id):
    user = get_current_user()
    ticket_type = request.form.get('ticket_type', 'Solo')
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Check if already registered
    cursor.execute("SELECT id FROM event_registrations WHERE event_id = ? AND user_id = ?", (event_id, user['id']))
    if cursor.fetchone():
        flash('You are already registered for this event.', 'warning')
        conn.close()
        return redirect(url_for('event_details', event_id=event_id))
    
    # Check if event has space
    cursor.execute("SELECT max_participants, registered_count FROM events WHERE id = ?", (event_id,))
    event = cursor.fetchone()
    if event and event['registered_count'] >= event['max_participants']:
        flash('Event is full.', 'error')
        conn.close()
        return redirect(url_for('event_details', event_id=event_id))
    
    # Create registration
    qr_code = f"QR{event_id}_{user['id']}_{uuid.uuid4().hex[:8]}"
    cursor.execute('''
        INSERT INTO event_registrations (event_id, user_id, ticket_type, qr_code)
        VALUES (?, ?, ?, ?)
    ''', (event_id, user['id'], ticket_type, qr_code))
    
    # Update event registration count
    cursor.execute("UPDATE events SET registered_count = registered_count + 1 WHERE id = ?", (event_id,))
    
    conn.commit()
    conn.close()
    
    flash('Registration successful!', 'success')
    return redirect(url_for('event_details', event_id=event_id))

@app.route('/update_event/<int:event_id>', methods=['GET', 'POST'])
@login_required
def update_event(event_id):
    user = get_current_user()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get event and check ownership
    cursor.execute("SELECT * FROM events WHERE id = ? AND created_by = ?", (event_id, user['id']))
    event = cursor.fetchone()
    
    if not event:
        flash('Event not found or you do not have permission to edit it.', 'error')
        conn.close()
        return redirect(url_for('my_events'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        tagline = request.form.get('tagline')
        description = request.form.get('description')
        event_date = request.form.get('event_date')
        venue = request.form.get('venue')
        category = request.form.get('category')
        organization = request.form.get('organization')
        speakers = request.form.get('speakers', '')
        schedule = request.form.get('schedule', '')
        rules = request.form.get('rules', '')
        registration_fee = float(request.form.get('registration_fee', 0))
        max_participants = int(request.form.get('max_participants', 100))
        club_id = request.form.get('club_id') or None
        
        # Handle cover image upload
        cover_image = event['cover_image']
        if 'cover_image' in request.files:
            file = request.files['cover_image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filename = f"{uuid.uuid4()}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                cover_image = f"/uploads/{filename}"
        
        cursor.execute('''
            UPDATE events SET title=?, tagline=?, description=?, cover_image=?, event_date=?, venue=?, category=?, organization=?, speakers=?, schedule=?, rules=?, registration_fee=?, max_participants=?, club_id=?, updated_at=CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (title, tagline, description, cover_image, event_date, venue, category, organization, speakers, schedule, rules, registration_fee, max_participants, club_id, event_id))
        
        conn.commit()
        conn.close()
        
        flash('Event updated successfully!', 'success')
        return redirect(url_for('my_events'))
    
    # GET request - show form
    cursor.execute("SELECT * FROM clubs ORDER BY name")
    clubs = cursor.fetchall()
    conn.close()
    
    return render_template('update_event.html', event=event, clubs=clubs)

@app.route('/delete_event/<int:event_id>')
@login_required
def delete_event(event_id):
    user = get_current_user()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Check ownership
    cursor.execute("SELECT id FROM events WHERE id = ? AND created_by = ?", (event_id, user['id']))
    if not cursor.fetchone():
        flash('You do not have permission to delete this event.', 'error')
        conn.close()
        return redirect(url_for('my_events'))
    
    # Delete related records first
    cursor.execute("DELETE FROM event_registrations WHERE event_id = ?", (event_id,))
    cursor.execute("DELETE FROM attendance WHERE event_id = ?", (event_id,))
    cursor.execute("DELETE FROM event_photos WHERE event_id = ?", (event_id,))
    cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
    
    conn.commit()
    conn.close()
    
    flash('Event deleted successfully.', 'success')
    return redirect(url_for('my_events'))

@app.route('/upload_event_photo/<int:event_id>', methods=['POST'])
@login_required
def upload_event_photo(event_id):
    user = get_current_user()
    
    if 'photo' in request.files:
        file = request.files['photo']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename = f"{uuid.uuid4()}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = f"/uploads/{filename}"
            
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO event_photos (event_id, user_id, image_url)
                VALUES (?, ?, ?)
            ''', (event_id, user['id'], image_url))
            conn.commit()
            conn.close()
            
            flash('Photo uploaded successfully!', 'success')
        else:
            flash('Invalid file type.', 'error')
    else:
        flash('No file selected.', 'error')
    
    return redirect(url_for('event_details', event_id=event_id))

# Additional routes for other functionality
@app.route('/clubs')
@login_required
def clubs():
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clubs ORDER BY name")
    clubs = cursor.fetchall()
    conn.close()
    return render_template('clubs.html', clubs=clubs)

@app.route('/feed')
@login_required
def feed():
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, u.name, u.profile_image
        FROM posts p
        JOIN users u ON p.user_id = u.id
        ORDER BY p.created_at DESC
    ''')
    posts = cursor.fetchall()
    conn.close()
    return render_template('feed.html', posts=posts)

@app.route('/notifications')
@login_required
def notifications():
    user = get_current_user()
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM notifications
        WHERE user_id = ?
        ORDER BY created_at DESC
    ''', (user['id'],))
    notifications = cursor.fetchall()
    conn.close()
    return render_template('notifications.html', notifications=notifications)

# API routes
@app.route('/api/events')
def api_events():
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT e.*, c.name as club_name, u.name as organizer_name
        FROM events e
        LEFT JOIN clubs c ON e.club_id = c.id
        LEFT JOIN users u ON e.created_by = u.id
        ORDER BY e.event_date ASC
    ''')
    events = cursor.fetchall()
    conn.close()
    return jsonify([dict(event) for event in events])

@app.route('/api/user/<int:user_id>')
def api_user(user_id):
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return jsonify(dict(user))
    return jsonify({'error': 'User not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)
