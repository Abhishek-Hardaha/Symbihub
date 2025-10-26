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
from PIL import Image, ImageDraw, ImageFont
from flask import abort, make_response

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

# Configuration for file uploads
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Optional WeasyPrint for HTML->PDF certificate generation
try:
    from weasyprint import HTML
    HAVE_WEASYPRINT = True
except Exception:
    HAVE_WEASYPRINT = False

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

def convert_event_dates(events):
    """Convert date strings to datetime objects for template rendering.

    Returns a list of plain dicts (not sqlite Row objects) with parsed date objects where possible.
    """
    out = []
    for event in events:
        # Convert sqlite3.Row to a plain dict so we can modify values
        try:
            ev = dict(event)
        except Exception:
            ev = event if isinstance(event, dict) else dict(event)

        # Parse event_date
        if ev.get('event_date'):
            try:
                if isinstance(ev['event_date'], str):
                    ev['event_date'] = datetime.strptime(ev['event_date'], '%Y-%m-%d').date()
            except Exception:
                pass

        # Parse registration_date if present
        if ev.get('registration_date'):
            try:
                if isinstance(ev['registration_date'], str):
                    ev['registration_date'] = datetime.strptime(ev['registration_date'], '%Y-%m-%d %H:%M:%S')
            except Exception:
                pass

        out.append(ev)

    return out

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
    
    # Convert date strings to datetime objects for template rendering
    events = convert_event_dates(events)
    
    # Get recent posts
    cursor.execute('''
        SELECT p.*, u.name, u.profile_image
        FROM posts p
        JOIN users u ON p.user_id = u.id
        ORDER BY p.created_at DESC
        LIMIT 5
    ''')
    posts = cursor.fetchall()
    
    # Map events to template-friendly fields used in dashboard.html
    events_mapped = []
    for e in events:
        ev = dict(e)
        ev['img'] = ev.get('cover_image')
        try:
            if ev.get('event_date'):
                ev['date'] = ev['event_date'].strftime('%Y-%m-%d')
            else:
                ev['date'] = None
        except Exception:
            ev['date'] = ev.get('event_date')
        ev['cat'] = ev.get('category')
        ev['org'] = ev.get('organization')
        events_mapped.append(ev)

    # If any event is missing an image, fetch latest photo per event in a single query
    try:
        missing_ids = [ev['id'] for ev in events_mapped if not ev.get('img')]
        if missing_ids:
            placeholders = ','.join(['?'] * len(missing_ids))
            photo_query = f"SELECT p.event_id, p.image_url FROM event_photos p JOIN (SELECT event_id, MAX(uploaded_at) AS maxt FROM event_photos WHERE event_id IN ({placeholders}) GROUP BY event_id) m ON p.event_id = m.event_id AND p.uploaded_at = m.maxt"
            cursor.execute(photo_query, missing_ids)
            photo_rows = cursor.fetchall()
            photo_map = {row['event_id']: row['image_url'] for row in photo_rows}
            for ev in events_mapped:
                if not ev.get('img') and ev['id'] in photo_map:
                    ev['img'] = photo_map[ev['id']]
    except Exception:
        pass

    conn.close()
    
    return render_template('dashboard.html', events=events_mapped, posts=posts)


# Admin panel route (simple demo: returns events, clubs and students)
@app.route('/admin')
def admin_panel():
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM events ORDER BY event_date DESC')
    events = cursor.fetchall()

    cursor.execute('SELECT * FROM clubs ORDER BY name ASC')
    clubs = cursor.fetchall()

    cursor.execute('SELECT id, username, name FROM users ORDER BY username ASC')
    students = cursor.fetchall()

    conn.close()

    return render_template('admin_panel.html', events=events, clubs=clubs, students=students)


# Certificate preview endpoint: renders the provided certificate HTML template with registration data
@app.route('/certificate/<int:reg_id>')
def certificate_preview(reg_id):
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get registration details with user and event info
    cursor.execute('''
        SELECT er.*, u.name as participant_name, e.title as event_name, e.event_date,
               strftime('%d %b %Y', e.event_date) as formatted_date
        FROM event_registrations er
        JOIN users u ON er.user_id = u.id
        JOIN events e ON er.event_id = e.id
        WHERE er.id = ?
    ''', (reg_id,))
    reg = cursor.fetchone()
    conn.close()

    if not reg:
        abort(404)

    # Prepare context for certificate template
    context = {
        'name': reg['participant_name'],
        'event': reg['event_name'],
        'date': reg['formatted_date']
    }

    # Render the certificate template
    html = render_template('certificate.html', **context)
    
    # If download parameter is present, return as attachment
    if request.args.get('download'):
        response = make_response(html)
        filename = f"certificate_{reg_id}.html"
        response.headers['Content-Type'] = 'text/html'
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        return response
        
    return html


@app.route('/certificate/download/<int:reg_id>')
def certificate_download(reg_id):
    # Redirect to certificate preview with download parameter
    return redirect(url_for('certificate_preview', reg_id=reg_id, download=1))

    if not reg:
        abort(404)

    context = {
        'name': reg['user_name'],
        'event_title': reg['event_title'],
        'date': reg.get('event_date'),
        'ticket_type': reg.get('ticket_type'),
        'qr_code': reg.get('qr_code')
    }

    rendered = render_template('certificate.html', **context)

    # If WeasyPrint is available, render to PDF and return it
    if HAVE_WEASYPRINT:
        try:
            pdf_bytes = HTML(string=rendered).write_pdf()
            return send_file(BytesIO(pdf_bytes), mimetype='application/pdf', as_attachment=True, download_name=f'certificate_{reg_id}.pdf')
        except Exception:
            # Fall back to HTML download if PDF generation fails
            pass

    # Fallback: return HTML as attachment so user can print/save from browser
    response = make_response(rendered)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename=certificate_{reg_id}.html'
    return response

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
    
    # Convert date strings to datetime objects for template rendering
    events = convert_event_dates(events)
    
    # Get categories for filter
    cursor.execute("SELECT DISTINCT category FROM events WHERE category IS NOT NULL")
    categories = cursor.fetchall()
    
    # If any event is missing a cover_image, fetch latest photo per event in a single query
    try:
        missing_ids = [ev['id'] for ev in events if not ev.get('cover_image')]
        if missing_ids:
            placeholders = ','.join(['?'] * len(missing_ids))
            photo_query = f"SELECT p.event_id, p.image_url FROM event_photos p JOIN (SELECT event_id, MAX(uploaded_at) AS maxt FROM event_photos WHERE event_id IN ({placeholders}) GROUP BY event_id) m ON p.event_id = m.event_id AND p.uploaded_at = m.maxt"
            cursor.execute(photo_query, missing_ids)
            photo_rows = cursor.fetchall()
            photo_map = {row['event_id']: row['image_url'] for row in photo_rows}
            for ev in events:
                if not ev.get('cover_image') and ev['id'] in photo_map:
                    ev['cover_image'] = photo_map[ev['id']]
    except Exception:
        pass

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
        SELECT e.*, c.name as club_name,
               er.id as registration_id, er.registration_date, er.payment_status, er.qr_code, er.ticket_type
        FROM events e
        LEFT JOIN clubs c ON e.club_id = c.id
        JOIN event_registrations er ON e.id = er.event_id
        WHERE er.user_id = ?
        ORDER BY e.event_date DESC
    ''', (user['id'],))
    registered_events = cursor.fetchall()
    
    # Convert date strings to datetime objects for created events
    created_events = convert_event_dates(created_events)
    print(f"DEBUG: Found {len(created_events)} created events")

    # Convert date strings to datetime objects for registered events
    registered_events = convert_event_dates(registered_events)
    print(f"DEBUG: Found {len(registered_events)} registered events")

    # Ensure we pass plain dicts (not sqlite Row) with python date objects for templates
    def normalize_events(rows):
        out = []
        for r in rows:
            ev = dict(r)
            # ensure event_date is a date object if possible
            try:
                if ev.get('event_date') and isinstance(ev.get('event_date'), str):
                    ev['event_date'] = datetime.strptime(ev['event_date'], '%Y-%m-%d').date()
            except Exception:
                pass
            out.append(ev)
        return out

    created_events = normalize_events(created_events)
    registered_events = normalize_events(registered_events)

    # If any created/registered events are missing cover_image, batch query latest photos
    try:
        all_events = created_events + registered_events
        missing_ids = [ev['id'] for ev in all_events if not ev.get('cover_image')]
        if missing_ids:
            placeholders = ','.join(['?'] * len(missing_ids))
            photo_query = f"SELECT p.event_id, p.image_url FROM event_photos p JOIN (SELECT event_id, MAX(uploaded_at) AS maxt FROM event_photos WHERE event_id IN ({placeholders}) GROUP BY event_id) m ON p.event_id = m.event_id AND p.uploaded_at = m.maxt"
            cursor.execute(photo_query, missing_ids)
            photo_rows = cursor.fetchall()
            photo_map = {row['event_id']: row['image_url'] for row in photo_rows}
            for ev in all_events:
                if not ev.get('cover_image') and ev['id'] in photo_map:
                    ev['cover_image'] = photo_map[ev['id']]
    except Exception:
        pass

    # Prepare stateless modal data
    created_event = None
    registration_success = None

    # Check for created_id in query params
    created_id = request.args.get('created_id')
    if created_id:
        try:
            cid = int(created_id)
            ccur = conn.cursor()
            ccur.execute('SELECT * FROM events WHERE id = ?', (cid,))
            row = ccur.fetchone()
            if row:
                created_event = dict(row)
                try:
                    if isinstance(created_event.get('event_date'), str):
                        created_event['event_date'] = datetime.strptime(created_event['event_date'], '%Y-%m-%d').date()
                except Exception:
                    pass
        except Exception:
            created_event = None

    # Check for registered_id in query params
    registered_id = request.args.get('registered_id')
    if registered_id:
        try:
            rid = int(registered_id)
            rcur = conn.cursor()
            rcur.execute('''
                SELECT er.*, e.title, e.event_date, e.venue
                FROM event_registrations er
                LEFT JOIN events e ON er.event_id = e.id
                WHERE er.id = ?
            ''', (rid,))
            reg = rcur.fetchone()
            if reg:
                registration_success = dict(reg)
                # generate QR image base64 from stored qr_code
                try:
                    qr = qrcode.QRCode(version=1, box_size=6, border=4)
                    qr.add_data(registration_success.get('qr_code'))
                    qr.make(fit=True)
                    qr_img = qr.make_image(fill_color='black', back_color='white')
                    buf = BytesIO()
                    qr_img.save(buf, format='PNG')
                    registration_success['qr_image'] = base64.b64encode(buf.getvalue()).decode()
                except Exception:
                    registration_success['qr_image'] = None
        except Exception:
            registration_success = None

    print(f"DEBUG: Sending to template - Created events: {len(created_events)}, Registered events: {len(registered_events)}")
    print("DEBUG: First registered event:", next(iter(registered_events), None))

    return render_template('my_events.html', 
                         created_events=created_events, 
                         registered_events=registered_events,
                         created_event=created_event,
                         registration_success=registration_success,
                         debug_mode=True)

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
    # Generate Symbi-Pass QR (base64) for profile display
    try:
        qr_payload = f"SYMBIPASS_USER_{user['id']}"
        qr = qrcode.QRCode(version=1, box_size=6, border=4)
        qr.add_data(qr_payload)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color='black', back_color='white')
        buf = BytesIO()
        qr_img.save(buf, format='PNG')
        qr_b64 = base64.b64encode(buf.getvalue()).decode()
    except Exception:
        qr_b64 = None
    
    # Demo badges (mock data)
    badges = [
        {'id': 1, 'name': 'First Event', 'desc': 'Created your first event', 'icon': 'ph-plus-circle', 'earned': True, 'date': '2024-09-12'},
        {'id': 2, 'name': 'Volunteer 10h', 'desc': 'Completed 10 volunteer hours', 'icon': 'ph-hand-heart', 'earned': True, 'date': '2025-03-05'},
        {'id': 3, 'name': 'Top Organizer', 'desc': 'Organized 5+ events', 'icon': 'ph-trophy', 'earned': False, 'date': None},
        {'id': 4, 'name': 'Community Helper', 'desc': 'Helped in community drives', 'icon': 'ph-heart', 'earned': True, 'date': '2025-01-20'},
    ]

    # Demo leaderboard (mock data)
    leaderboard = [
        {'rank': 1, 'name': 'Anita Sharma', 'xp': 1250},
        {'rank': 2, 'name': 'Rohan Gupta', 'xp': 980},
        {'rank': 3, 'name': 'Sneha Iyer', 'xp': 860},
        {'rank': 4, 'name': user['name'], 'xp': user['xp'] if 'xp' in user else 0},
    ]

    return render_template('profile.html', user=user, stats=stats, user_clubs=user_clubs, symbi_qr_image=qr_b64, badges=badges, leaderboard=leaderboard)

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
    
    # Convert date string to datetime object
    event_row = convert_event_dates([event])[0]

    # Build a template-friendly event dict (some templates expect different key names)
    event = dict(event_row)
    # Aliases used by templates
    event['img'] = event.get('cover_image')
    # Provide both ISO date and display date
    try:
        if event.get('event_date'):
            # event_date may be a date object from convert_event_dates
            event_date_obj = event['event_date']
            event['date'] = event_date_obj.strftime('%Y-%m-%d')
            event['date_display'] = event_date_obj.strftime('%b %d, %Y')
        else:
            event['date'] = None
            event['date_display'] = None
    except Exception:
        event['date'] = event.get('event_date')
        event['date_display'] = event.get('event_date')

    event['org'] = event.get('organization')
    event['cat'] = event.get('category')
    event['registered'] = event.get('registered_count', 0)
    # Speakers as list for templates that iterate
    speakers_raw = event.get('speakers') or ''
    event['speakers'] = [s.strip() for s in speakers_raw.split(',')] if speakers_raw else []

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


@app.route('/bookmark_event/<int:event_id>', methods=['POST'])
@login_required
def bookmark_event(event_id):
    # Simple placeholder for bookmarking functionality
    user = get_current_user()
    # Could insert into a bookmarks table; for now just flash
    flash('Event bookmarked!', 'success')
    return redirect(request.referrer or url_for('event_details', event_id=event_id))


@app.route('/share_event/<int:event_id>', methods=['POST'])
@login_required
def share_event(event_id):
    # Placeholder share endpoint; real implementation could integrate with APIs
    flash('Event share link copied to clipboard (simulated).', 'info')
    return redirect(request.referrer or url_for('event_details', event_id=event_id))

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
        # Handle cover image upload
        cover_image = None # (or existing value for update route)
        print(f"Checking for 'cover_image' in request.files: {'cover_image' in request.files}") # DEBUG

        if 'cover_image' in request.files:
            file = request.files['cover_image']
            print(f"File object found: {file}") # DEBUG
            print(f"File filename: {file.filename}") # DEBUG

            if file and file.filename: # Check if a file was actually selected
                is_allowed = allowed_file(file.filename)
                print(f"Is file allowed? {is_allowed}") # DEBUG

                if is_allowed:
                    filename = secure_filename(file.filename)
                    filename = f"{uuid.uuid4()}_{filename}"
                    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    print(f"Attempting to save file to: {save_path}") # DEBUG
                    try:
                        file.save(save_path)
                        cover_image = f"/uploads/{filename}"
                        print(f"SUCCESS: File saved as {cover_image}") # DEBUG
                    except Exception as e:
                        print(f"ERROR saving file: {e}") # DEBUG - Catch potential errors
                        flash(f"Error saving uploaded file: {e}", "error") # Show error to user
                else:
                    print(f"File type not allowed: {file.filename}") # DEBUG
                    flash(f"File type not allowed: Please upload png, jpg, jpeg, gif, or webp.", "error")
            else:
                print("No file selected or file has no filename.") # DEBUG
        else:
            print("'cover_image' field not found in uploaded files.") # DEBUG
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO events (title, tagline, description, cover_image, event_date, venue, category, organization, speakers, schedule, rules, registration_fee, max_participants, club_id, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, tagline, description, cover_image, event_date, venue, category, organization, speakers, schedule, rules, registration_fee, max_participants, club_id, user['id']))
        
        event_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Redirect with created_id to avoid relying on session memory
        return redirect(url_for('my_events', created_id=event_id))
    
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
    
    # Create registration with QR code string
    qr_code = f"QR{event_id}_{user['id']}_{uuid.uuid4().hex[:8]}"
    cursor.execute('''
        INSERT INTO event_registrations (event_id, user_id, ticket_type, qr_code)
        VALUES (?, ?, ?, ?)
    ''', (event_id, user['id'], ticket_type, qr_code))

    registration_id = cursor.lastrowid

    # Update event registration count
    cursor.execute("UPDATE events SET registered_count = registered_count + 1 WHERE id = ?", (event_id,))

    conn.commit()
    conn.close()

    # Redirect to my_events with the registration id so the page can fetch and render the QR (stateless)
    return redirect(url_for('my_events', registered_id=registration_id))

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
    
    # Convert date string to datetime object for form
    event = convert_event_dates([event])[0]
    
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


@app.route('/club/<int:club_id>')
@login_required
def club_profile(club_id):
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM clubs WHERE id = ?', (club_id,))
    club = cursor.fetchone()
    if not club:
        flash('Club not found.', 'error')
        conn.close()
        return redirect(url_for('clubs'))

    # Fetch upcoming events for this club
    cursor.execute('SELECT * FROM events WHERE club_id = ? AND event_date >= date("now") ORDER BY event_date ASC', (club_id,))
    events = cursor.fetchall()
    conn.close()
    return render_template('club_profile.html', club=club, events=events)

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
    # Map DB rows to template-friendly keys used in feed.html
    posts_mapped = []
    for p in posts:
        posts_mapped.append({
            'id': p['id'],
            'name': p['name'],
            'img': p['profile_image'] if p['profile_image'] else '/static/default_profile.png',
            'post': p['content'],
            'post_image': p['image_url'] if 'image_url' in p.keys() and p['image_url'] else None,
            'likes': p['likes_count'] if p['likes_count'] is not None else 0,
            'created_at': p['created_at']
        })
    conn.close()
    return render_template('feed.html', posts=posts_mapped)


@app.route('/create_post', methods=['POST'])
@login_required
def create_post():
    user = get_current_user()
    content = request.form.get('content')
    if not content or not content.strip():
        flash('Post content cannot be empty.', 'error')
        return redirect(url_for('feed'))

    conn = db.get_connection()
    cursor = conn.cursor()
    # Handle optional image upload for the post
    post_image_url = None
    if 'post_image' in request.files:
        file = request.files['post_image']
        if file and file.filename:
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filename = f"{uuid.uuid4()}_{filename}"
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                try:
                    file.save(save_path)
                    post_image_url = f"/uploads/{filename}"
                except Exception as e:
                    app.logger.exception('Failed to save uploaded post image')
                    flash('Failed to save uploaded image.', 'error')
            else:
                flash('File type not allowed for post image.', 'error')

    # Ensure compatibility with older DB schema that may not have image_url
    try:
        cursor.execute("PRAGMA table_info(posts)")
        cols = [r[1] for r in cursor.fetchall()]
    except Exception:
        cols = []

    if 'image_url' in cols:
        cursor.execute('''
            INSERT INTO posts (user_id, content, image_url)
            VALUES (?, ?, ?)
        ''', (user['id'], content.strip(), post_image_url))
    else:
        cursor.execute('''
            INSERT INTO posts (user_id, content)
            VALUES (?, ?)
        ''', (user['id'], content.strip()))
    conn.commit()
    conn.close()

    flash('Post created!', 'success')
    return redirect(url_for('feed'))


@app.route('/like_post/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    # Simple like increment (no per-user like tracking yet)
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT likes_count FROM posts WHERE id = ?', (post_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        flash('Post not found.', 'error')
        return redirect(url_for('feed'))

    likes = row['likes_count'] or 0
    cursor.execute('UPDATE posts SET likes_count = ? WHERE id = ?', (likes + 1, post_id))
    conn.commit()
    conn.close()

    return redirect(request.referrer or url_for('feed'))

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
    
    # Convert to dict and handle dates for JSON serialization
    events_dict = []
    for event in events:
        event_dict = dict(event)
        # Convert date to string for JSON serialization
        if event_dict['event_date']:
            try:
                event_dict['event_date'] = datetime.strptime(event_dict['event_date'], '%Y-%m-%d').strftime('%Y-%m-%d')
            except:
                pass
        events_dict.append(event_dict)
    
    return jsonify(events_dict)

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    user = get_current_user()
    name = request.form.get('name')
    bio = request.form.get('bio')
    interests = request.form.get('interests', '')
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE users SET name=?, bio=?, interests=?, updated_at=CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (name, bio, interests, user['id']))
    
    conn.commit()
    conn.close()
    
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('profile'))

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


@app.context_processor
def inject_current_user():
    """Make current user available in all templates as `current_user`."""
    return {'current_user': get_current_user()}


@app.route('/clear_modal_data')
def clear_modal_data():
    """Clear modal data from session after showing."""
    session.pop('event_created', None)
    session.pop('registration_success', None)
    return '', 204  # No content response


# Download Symbi-Pass QR as PNG
@app.route('/download_symbipass')
@login_required
def download_symbipass():
    user = get_current_user()
    try:
        qr_payload = f"SYMBIPASS_USER_{user['id']}"
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_payload)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color='black', back_color='white')
        buf = BytesIO()
        qr_img.save(buf, format='PNG')
        buf.seek(0)
        return send_file(buf, mimetype='image/png', as_attachment=True, download_name=f'symbi-pass-{user["id"]}.png')
    except Exception as e:
        flash('Could not generate Symbi-Pass.', 'error')
        return redirect(url_for('profile'))


# Download certificate for a registration (simple PNG certificate generated on the fly)
@app.route('/download_certificate/<int:registration_id>')
@login_required
def download_certificate(registration_id):
    user = get_current_user()
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT er.*, e.title as event_title, e.event_date
        FROM event_registrations er
        JOIN events e ON er.event_id = e.id
        WHERE er.id = ? AND er.user_id = ?
    ''', (registration_id, user['id']))
    reg = cursor.fetchone()
    conn.close()
    if not reg:
        flash('Certificate not found or you do not have permission.', 'error')
        return redirect(url_for('my_events'))
    # For now, simply render the HTML certificate template in the browser
    try:
        # Provide variables expected by the certificate template
        student_name = user['name'] if user and 'name' in user.keys() else (user['username'] if user and 'username' in user.keys() else 'Participant')
        event_name = reg['event_title'] if reg and 'event_title' in reg.keys() else 'Event'
        event_date = reg['event_date'] if reg and 'event_date' in reg.keys() else None
        context = {
            'student_name': student_name,
            'event_name': event_name,
            'event_date': event_date,
            'organizer_name': None
        }
        return render_template('certificate.html', **context)
    except Exception as e:
        # Log the full exception to help debugging
        app.logger.exception('Failed to render certificate for registration_id=%s', registration_id)
        # Render certificate template with placeholders so user can still view a preview
        try:
            placeholder_ctx = {
                'student_name': user['name'] if user and 'name' in user.keys() else 'Participant',
                'event_name': reg['event_title'] if reg and 'event_title' in reg.keys() else 'Event Name',
                'event_date': reg['event_date'] if reg and 'event_date' in reg.keys() else None,
                'organizer_name': None,
                'error': str(e)
            }
            flash('Rendered certificate with fallback (server logged error).', 'warning')
            return render_template('certificate.html', **placeholder_ctx)
        except Exception:
            flash('Could not render certificate.', 'error')
            return redirect(url_for('my_events'))


# Organizer scanner page - simple UI that posts scanned QR codes to /api/verify_qr
@app.route('/organizer/scan')
@login_required
def organizer_scan():
    # You might want to add an organizer-only check here (e.g., role)
    return render_template('scanner.html')


@app.route('/api/verify_qr', methods=['POST'])
@login_required
def api_verify_qr():
    data = request.get_json() or {}
    qr_code = data.get('qr_code')
    if not qr_code:
        return jsonify({'error': 'No QR provided'}), 400

    conn = db.get_connection()
    cursor = conn.cursor()
    # Find registration by qr_code
    cursor.execute('SELECT * FROM event_registrations WHERE qr_code = ?', (qr_code,))
    reg = cursor.fetchone()
    if not reg:
        conn.close()
        return jsonify({'error': 'Registration not found'}), 404

    # Check attendance table and insert if not present
    cursor.execute('SELECT * FROM attendance WHERE event_id = ? AND user_id = ?', (reg['event_id'], reg['user_id']))
    attendance = cursor.fetchone()
    if attendance:
        conn.close()
        return jsonify({'status': 'already_marked', 'registration_id': reg['id']})

    # Insert attendance
    try:
        cursor.execute('INSERT INTO attendance (event_id, user_id, scanned_at) VALUES (?, ?, CURRENT_TIMESTAMP)', (reg['event_id'], reg['user_id']))
    except Exception:
        # If attendance table doesn't exist, attempt to create it (best-effort)
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER,
                    user_id INTEGER,
                    scanned_at TEXT
                )
            ''')
            cursor.execute('INSERT INTO attendance (event_id, user_id, scanned_at) VALUES (?, ?, CURRENT_TIMESTAMP)', (reg['event_id'], reg['user_id']))
        except Exception:
            conn.rollback()
            conn.close()
            return jsonify({'error': 'Could not record attendance'}), 500

    # Award XP to attendee
    try:
        cursor.execute('SELECT xp FROM users WHERE id = ?', (reg['user_id'],))
        row = cursor.fetchone()
        current_xp = row['xp'] or 0
        cursor.execute('UPDATE users SET xp = ? WHERE id = ?', (current_xp + 10, reg['user_id']))
    except Exception:
        # continue even if XP update fails
        pass

    conn.commit()
    conn.close()
    return jsonify({'status': 'marked', 'registration_id': reg['id']})


@app.route('/leaderboard')
@login_required
def leaderboard():
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, name, xp FROM users ORDER BY xp DESC LIMIT 50')
    rows = cursor.fetchall()
    # Build leaderboard entries with rank and placeholders for events_attended/badges
    leaderboard = []
    for idx, r in enumerate(rows, start=1):
        leaderboard.append({
            'rank': idx,
            'id': r['id'],
            'username': r['username'],
            'name': r['name'],
            'xp': r['xp'] or 0,
            'events_attended': 0,
            'badges': 0
        })
    conn.close()
    return render_template('leaderboard.html', leaderboard=leaderboard)


@app.route('/resume_builder', methods=['GET', 'POST'])
@login_required
def resume_builder():
    user = get_current_user()
    conn = db.get_connection()
    cursor = conn.cursor()
    # Get attended events
    cursor.execute('''
        SELECT e.title, e.event_date, e.venue
        FROM events e
        JOIN event_registrations er ON e.id = er.event_id
        WHERE er.user_id = ?
        ORDER BY e.event_date DESC
    ''', (user['id'],))
    attended = cursor.fetchall()

    # Get certificates (if any)
    cursor.execute('SELECT * FROM certificates WHERE user_id = ?', (user['id'],))
    certs = cursor.fetchall()
    conn.close()

    if request.method == 'POST':
        # Basic resume bullet generation from events + certificates
        bullets = []
        for e in attended:
            date_str = e['event_date'] or ''
            bullets.append(f"Attended '{e['title']}' on {date_str} at {e.get('venue','N/A')}")
        for c in certs:
            bullets.append(f"Received certificate: {c.get('title') or c.get('name','Certificate')}")

        resume_text = f"Resume for {user['name']}\n\n" + "\n".join([f"- {b}" for b in bullets])

        # Return plain text file for download
        buf = BytesIO()
        buf.write(resume_text.encode('utf-8'))
        buf.seek(0)
        return send_file(buf, as_attachment=True, download_name=f"resume-{user['id']}.txt", mimetype='text/plain')

    return render_template('resume_builder.html', attended=attended, certs=certs)

@app.route('/generate_ai_resume', methods=['POST'])
def generate_ai_resume():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get user's hosted events
    cursor.execute('''
        SELECT e.title, e.description, e.event_date, e.category
        FROM events e
        WHERE e.created_by = ?
        ORDER BY e.event_date DESC
    ''', (session['user_id'],))
    hosted_events = cursor.fetchall()
    
    # Get user's attended events
    cursor.execute('''
        SELECT e.title, e.description, e.event_date, e.category,
               er.ticket_type, er.registration_date, er.payment_status
        FROM event_registrations er
        JOIN events e ON er.event_id = e.id
        WHERE er.user_id = ?
        ORDER BY e.event_date DESC
    ''', (session['user_id'],))
    attended_events = cursor.fetchall()
    
    # Get user info
    cursor.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    conn.close()

    # Format experience data
    experience = {
        'name': user['name'],
        'email': user['email'],
        'bio': user['bio'],
        'hosted_events': [dict(event) for event in hosted_events],
        'attended_events': [dict(event) for event in attended_events]
    }
    
    try:
        import google.generativeai as genai
        
        # Configure the Gemini API
        genai.configure(api_key = os.environ.get('GEMINI_API_KEY'))
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        
        prompt = f"""
        Create a professional resume for {experience['name']} based on their SymbiHub activity:
        
        Bio: {experience['bio']}
        
        Event Organization Experience:
    {', '.join(f"{event['title']} ({event.get('category','')})" for event in experience['hosted_events'])}
        
        Event Participation & Volunteering:
    {', '.join(f"{event['title']} - {event.get('ticket_type','')} (registered on {event.get('registration_date')})" for event in experience['attended_events'])}
        
        Format it as a clean HTML document with professional styling.
        Focus on highlighting leadership, organizational, and volunteer experience.
        Include a skills section based on the types of events organized and attended.
        """
        
        response = model.generate_content(prompt)
        resume_html = response.text
        
        return jsonify({
            'success': True,
            'resume_html': resume_html
        })
        
    except Exception as e:
        print(f"Resume generation error: {str(e)}")
        return jsonify({
            'error': 'Failed to generate resume. Please try again.'
        }), 500
if __name__ == '__main__':
    app.run(debug=True)
