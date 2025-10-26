from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, send_from_directory
import json
import csv
import io
from datetime import datetime, timedelta
import uuid
import qrcode
from io import BytesIO
import base64
import os

app = Flask(__name__)

# Serve static files
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# In-memory database with enhanced structure
db = {
    "clubs": [
        {"id": 1, "name": "AI Club", "desc": "Exploring the frontiers of AI.", "icon": "ph-robot", "members": 150, "events_count": 8, "followers": 200, "banner": "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?auto=format&fit=crop&w=1200&q=60"},
        {"id": 2, "name": "Foss Club", "desc": "Promoting Free and Open Source Software.", "icon": "ph-git-branch", "members": 120, "events_count": 5, "followers": 180, "banner": "https://images.unsplash.com/photo-1555066931-4365d14bab8c?auto=format&fit=crop&w=1200&q=60"},
        {"id": 3, "name": "Google Developers", "desc": "The official GDSC of SIT Pune.", "icon": "ph-google-logo", "members": 200, "events_count": 12, "followers": 300, "banner": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1200&q=60"},
        {"id": 4, "name": "Codex", "desc": "The official coding club.", "icon": "ph-code", "members": 180, "events_count": 15, "followers": 250, "banner": "https://images.unsplash.com/photo-1517180102446-f3ece451e9d8?auto=format&fit=crop&w=1200&q=60"},
        {"id": 5, "name": "Mosaic", "desc": "The arts and crafts club.", "icon": "ph-paint-brush", "members": 100, "events_count": 6, "followers": 150, "banner": "https://images.unsplash.com/photo-1541961017774-22349e4a1262?auto=format&fit=crop&w=1200&q=60"},
        {"id": 6, "name": "Symbiosis Music Society", "desc": "The heart of music on campus.", "icon": "ph-music-notes", "members": 80, "events_count": 10, "followers": 120, "banner": "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?auto=format&fit=crop&w=1200&q=60"},
        {"id": 7, "name": "Sole to Soul", "desc": "The official dance club.", "icon": "ph-person-simple-run", "members": 90, "events_count": 8, "followers": 140, "banner": "https://images.unsplash.com/photo-1508700929628-666bc8bd84ea?auto=format&fit=crop&w=1200&q=60"},
        {"id": 8, "name": "Antriksh Space Club", "desc": "For all astronomy enthusiasts.", "icon": "ph-planet", "members": 60, "events_count": 4, "followers": 100, "banner": "https://images.unsplash.com/photo-1446776877081-d282a0f896e2?auto=format&fit=crop&w=1200&q=60"},
    ],
    "events": [
        {"id": 1, "title": "Codex Hackathon 2025", "tagline": "36 hours of code, innovation, and prizes.", "img": "https://images.unsplash.com/photo-1511578314322-379afb476865?auto=format&fit=crop&w=800&q=60", "date": "2024-10-28", "org": "Codex", "cat": "Tech", "venue": "Main Auditorium", "description": "Join us for 36 hours of coding, innovation, and amazing prizes!", "speakers": ["Dr. John Smith", "Jane Doe"], "schedule": "Day 1: 9 AM - Registration, 10 AM - Opening Ceremony", "rules": "Teams of 2-4 members allowed", "registration_fee": 0, "max_participants": 100, "registered": 45, "status": "upcoming", "club_id": 4},
        {"id": 2, "title": "Reverb 2025", "tagline": "The official cultural fest.", "img": "https://images.unsplash.com/photo-1517457373958-b7bdd4587205?auto=format&fit=crop&w=800&q=60", "date": "2024-11-05", "org": "Cultural Committee", "cat": "Fest", "venue": "Campus Grounds", "description": "The biggest cultural festival of the year!", "speakers": ["Cultural Committee"], "schedule": "3 days of cultural events", "rules": "Open to all students", "registration_fee": 0, "max_participants": 1000, "registered": 300, "status": "upcoming", "club_id": None},
        {"id": 3, "title": "AI & ML Workshop", "tagline": "A hands-on workshop by the AI Club.", "img": "https://images.unsplash.com/photo-1587825140708-df876c1b5df1?auto=format&fit=crop&w=800&q=60", "date": "2024-11-12", "org": "AI Club", "cat": "Tech", "venue": "Computer Lab 1", "description": "Learn AI and ML from industry experts", "speakers": ["Dr. AI Expert", "ML Specialist"], "schedule": "9 AM - 5 PM", "rules": "Bring your laptop", "registration_fee": 0, "max_participants": 50, "registered": 25, "status": "upcoming", "club_id": 1},
    ],
    "posts": [
        {"id": 1, "name": "Anita Sharma", "img": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=100&q=60", "post": "Just finished the AI & ML Workshop! Big thanks to the AI Club!", "likes": 24, "comments": 5, "timestamp": "2024-10-20T10:30:00"},
        {"id": 2, "name": "Rohan Gupta", "img": "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?auto=format&fit=crop&w=100&q=60", "post": "Anyone forming a team for the 'Codex Hackathon'? LMK!", "likes": 15, "comments": 8, "timestamp": "2024-10-19T15:45:00"},
    ],
    "students": {
        "anita-sharma": {
            "name": "Anita Sharma", 
            "img": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=100&q=60", 
            "bio": "2nd Year CSE. Passionate about AI.",
            "xp": 1250,
            "level": 5,
            "badges": ["AI Enthusiast", "Event Organizer", "Community Helper"],
            "events_attended": 12,
            "events_organized": 3,
            "volunteer_hours": 25,
            "college_id": "SIT2023001",
            "interests": ["AI/ML", "Programming", "Robotics"],
            "joined_clubs": [1, 4],
            "achievements": ["Hackathon Winner", "Best Organizer"]
        },
        "rohan-gupta": {
            "name": "Rohan Gupta", 
            "img": "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?auto=format&fit=crop&w=100&q=60", 
            "bio": "3rd Year IT. Backend specialist.",
            "xp": 980,
            "level": 4,
            "badges": ["Code Master", "Team Player"],
            "events_attended": 8,
            "events_organized": 1,
            "volunteer_hours": 15,
            "college_id": "SIT2022001",
            "interests": ["Backend Development", "Database", "APIs"],
            "joined_clubs": [2, 4],
            "achievements": ["Best Backend Developer"]
        },
    },
    "registrations": [
        {"id": 1, "event_id": 1, "student_id": "anita-sharma", "ticket_type": "Team", "payment_status": "completed", "qr_code": "QR001", "registration_date": "2024-10-15"},
        {"id": 2, "event_id": 2, "student_id": "rohan-gupta", "ticket_type": "Solo", "payment_status": "completed", "qr_code": "QR002", "registration_date": "2024-10-16"},
    ],
    "attendance": [
        {"id": 1, "event_id": 1, "student_id": "anita-sharma", "check_in": "2024-10-28T09:00:00", "check_out": "2024-10-28T18:00:00", "status": "present"},
    ],
    "polls": [
        {"id": 1, "question": "Which programming language should we focus on in the next workshop?", "options": ["Python", "JavaScript", "Java", "C++"], "votes": [45, 30, 20, 15], "event_id": 1, "status": "active"},
    ],
    "notifications": [
        {"id": 1, "student_id": "anita-sharma", "title": "Event Reminder", "message": "AI & ML Workshop starts in 2 hours!", "type": "reminder", "timestamp": "2024-10-20T07:00:00", "read": False},
        {"id": 2, "student_id": "rohan-gupta", "title": "Registration Confirmed", "message": "Your registration for Codex Hackathon has been confirmed!", "type": "registration", "timestamp": "2024-10-19T14:30:00", "read": True},
    ],
    "leaderboard": [
        {"rank": 1, "student_id": "anita-sharma", "name": "Anita Sharma", "xp": 1250, "events_attended": 12, "badges": 3},
        {"rank": 2, "student_id": "rohan-gupta", "name": "Rohan Gupta", "xp": 980, "events_attended": 8, "badges": 2},
    ],
    "volunteer_opportunities": [
        {"id": 1, "title": "Event Setup Helper", "event_id": 1, "description": "Help set up the hackathon venue", "hours": 4, "skills_required": ["Event Management"], "volunteers_needed": 5, "registered_volunteers": 2},
        {"id": 2, "title": "Registration Desk", "event_id": 2, "description": "Manage registration desk during Reverb", "hours": 6, "skills_required": ["Communication"], "volunteers_needed": 3, "registered_volunteers": 1},
    ],
    "fundraisers": [
        {"id": 1, "title": "Help Flood Victims", "description": "Support flood-affected families", "goal": 50000, "raised": 25000, "donors": 45, "status": "active"},
        {"id": 2, "title": "Scholarship Fund", "description": "Support underprivileged students", "goal": 100000, "raised": 75000, "donors": 120, "status": "active"},
    ],
    "certificates": [
        {"id": 1, "student_id": "anita-sharma", "event_id": 1, "certificate_type": "Participation", "issued_date": "2024-10-29", "template": "default"},
    ],
    "event_photos": [
        {"id": 1, "event_id": 1, "url": "https://images.unsplash.com/photo-1511578314322-379afb476865?auto=format&fit=crop&w=800&q=60", "uploaded_by": "anita-sharma", "timestamp": "2024-10-28T20:00:00"},
    ],
    "admin_users": {
        "admin1": {"name": "Dr. Principal", "role": "Principal", "permissions": ["approve_events", "manage_clubs", "view_reports"]},
    }
}

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', events=db['events'])

@app.route('/feed')
def feed():
    return render_template('feed.html', posts=db['posts'])

@app.route('/clubs')
def clubs():
    return render_template('clubs.html', clubs=db['clubs'])

@app.route('/profile/<student_id>')
def profile(student_id):
    student = db['students'].get(student_id)
    if not student:
        return "Student not found", 404
    return render_template('profile.html', student=student)

@app.route('/organizer')
def organizer():
    return render_template('organizer.html', events=db['events'])

@app.route('/create_event', methods=['POST'])
def create_event():
    # Get form data
    title = request.form.get('title')
    tagline = request.form.get('tagline')
    date = request.form.get('date')
    org = request.form.get('org')
    cat = request.form.get('cat')
    img = request.form.get('img')
    venue = request.form.get('venue', 'TBA')
    description = request.form.get('description', '')
    registration_fee = float(request.form.get('registration_fee', 0))
    max_participants = int(request.form.get('max_participants', 100))
    
    # Create new event
    new_id = max([event['id'] for event in db['events']], default=0) + 1
    new_event = {
        "id": new_id,
        "title": title,
        "tagline": tagline,
        "img": img,
        "date": date,
        "org": org,
        "cat": cat,
        "venue": venue,
        "description": description,
        "speakers": [],
        "schedule": "",
        "rules": "",
        "registration_fee": registration_fee,
        "max_participants": max_participants,
        "registered": 0,
        "status": "upcoming",
        "club_id": None
    }
    
    # Add to database
    db['events'].append(new_event)
    
    # Redirect back to organizer page
    return redirect(url_for('organizer'))

# New routes for enhanced functionality
@app.route('/event/<int:event_id>')
def event_details(event_id):
    event = next((e for e in db['events'] if e['id'] == event_id), None)
    if not event:
        return "Event not found", 404
    return render_template('event_details.html', event=event)

@app.route('/register_event/<int:event_id>', methods=['POST'])
def register_event(event_id):
    student_id = request.form.get('student_id', 'anita-sharma')
    ticket_type = request.form.get('ticket_type', 'Solo')
    
    # Create registration
    new_registration = {
        "id": len(db['registrations']) + 1,
        "event_id": event_id,
        "student_id": student_id,
        "ticket_type": ticket_type,
        "payment_status": "completed",
        "qr_code": f"QR{len(db['registrations']) + 1:03d}",
        "registration_date": datetime.now().strftime("%Y-%m-%d")
    }
    
    db['registrations'].append(new_registration)
    
    # Update event registration count
    event = next((e for e in db['events'] if e['id'] == event_id), None)
    if event:
        event['registered'] += 1
    
    return redirect(url_for('event_details', event_id=event_id))

@app.route('/club/<int:club_id>')
def club_profile(club_id):
    club = next((c for c in db['clubs'] if c['id'] == club_id), None)
    if not club:
        return "Club not found", 404
    
    # Get club events
    club_events = [e for e in db['events'] if e.get('club_id') == club_id]
    
    return render_template('club_profile.html', club=club, events=club_events)

@app.route('/leaderboard')
def leaderboard():
    return render_template('leaderboard.html', leaderboard=db['leaderboard'])

@app.route('/notifications')
def notifications():
    student_id = request.args.get('student_id', 'anita-sharma')
    user_notifications = [n for n in db['notifications'] if n['student_id'] == student_id]
    return render_template('notifications.html', notifications=user_notifications)

@app.route('/polls')
def polls():
    return render_template('polls.html', polls=db['polls'])

@app.route('/vote_poll/<int:poll_id>', methods=['POST'])
def vote_poll(poll_id):
    option_index = int(request.form.get('option'))
    poll = next((p for p in db['polls'] if p['id'] == poll_id), None)
    if poll:
        poll['votes'][option_index] += 1
    return redirect(url_for('polls'))

@app.route('/volunteer')
def volunteer():
    return render_template('volunteer.html', opportunities=db['volunteer_opportunities'])

@app.route('/register_volunteer/<int:opportunity_id>', methods=['POST'])
def register_volunteer(opportunity_id):
    student_id = request.form.get('student_id', 'anita-sharma')
    opportunity = next((o for o in db['volunteer_opportunities'] if o['id'] == opportunity_id), None)
    if opportunity:
        opportunity['registered_volunteers'] += 1
    return redirect(url_for('volunteer'))

@app.route('/fundraisers')
def fundraisers():
    return render_template('fundraisers.html', fundraisers=db['fundraisers'])

@app.route('/donate/<int:fundraiser_id>', methods=['POST'])
def donate(fundraiser_id):
    amount = float(request.form.get('amount'))
    fundraiser = next((f for f in db['fundraisers'] if f['id'] == fundraiser_id), None)
    if fundraiser:
        fundraiser['raised'] += amount
        fundraiser['donors'] += 1
    return redirect(url_for('fundraisers'))

@app.route('/event_photos/<int:event_id>')
def event_photos(event_id):
    photos = [p for p in db['event_photos'] if p['event_id'] == event_id]
    return render_template('event_photos.html', photos=photos, event_id=event_id)

@app.route('/attendance/<int:event_id>')
def attendance(event_id):
    event = next((e for e in db['events'] if e['id'] == event_id), None)
    if not event:
        return "Event not found", 404
    
    # Generate QR code for attendance
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f"ATTENDANCE_{event_id}")
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    qr_code_b64 = base64.b64encode(img_buffer.getvalue()).decode()
    
    # Get attendance records for this event
    event_attendance = [a for a in db['attendance'] if a['event_id'] == event_id]
    
    return render_template('attendance.html', event=event, attendance=event_attendance, qr_code=qr_code_b64)

@app.route('/export_attendance/<int:event_id>')
def export_attendance(event_id):
    event_attendance = [a for a in db['attendance'] if a['event_id'] == event_id]
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student ID', 'Check In', 'Check Out', 'Status'])
    
    for record in event_attendance:
        student = db['students'].get(record['student_id'], {})
        writer.writerow([
            student.get('college_id', ''),
            record['check_in'],
            record['check_out'],
            record['status']
        ])
    
    output.seek(0)
    
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'attendance_event_{event_id}.csv'
    )

@app.route('/certificate_generator')
def certificate_generator():
    return render_template('certificate_generator.html')

@app.route('/generate_certificate', methods=['POST'])
def generate_certificate():
    student_name = request.form.get('student_name')
    event_name = request.form.get('event_name')
    date = request.form.get('date')
    certificate_type = request.form.get('certificate_type', 'Participation')
    
    # Create certificate record
    new_certificate = {
        "id": len(db['certificates']) + 1,
        "student_id": "anita-sharma",
        "event_id": 1,
        "certificate_type": certificate_type,
        "issued_date": datetime.now().strftime("%Y-%m-%d"),
        "template": "default"
    }
    
    db['certificates'].append(new_certificate)
    
    return redirect(url_for('certificate_generator'))

@app.route('/resume_builder')
def resume_builder():
    student_id = request.args.get('student_id', 'anita-sharma')
    student = db['students'].get(student_id, {})
    
    # Get student's event history
    student_registrations = [r for r in db['registrations'] if r['student_id'] == student_id]
    student_events = []
    for reg in student_registrations:
        event = next((e for e in db['events'] if e['id'] == reg['event_id']), None)
        if event:
            student_events.append(event)
    
    # Get certificates
    student_certificates = [c for c in db['certificates'] if c['student_id'] == student_id]
    
    return render_template('resume_builder.html', 
                         student=student, 
                         events=student_events, 
                         certificates=student_certificates)

@app.route('/admin')
def admin_panel():
    return render_template('admin_panel.html', 
                         events=db['events'], 
                         clubs=db['clubs'], 
                         students=db['students'])

@app.route('/approve_event/<int:event_id>')
def approve_event(event_id):
    event = next((e for e in db['events'] if e['id'] == event_id), None)
    if event:
        event['status'] = 'approved'
    return redirect(url_for('admin_panel'))

@app.route('/api/notifications')
def api_notifications():
    student_id = request.args.get('student_id', 'anita-sharma')
    user_notifications = [n for n in db['notifications'] if n['student_id'] == student_id and not n['read']]
    return jsonify(user_notifications)

@app.route('/api/events')
def api_events():
    return jsonify(db['events'])

@app.route('/api/clubs')
def api_clubs():
    return jsonify(db['clubs'])

@app.route('/api/leaderboard')
def api_leaderboard():
    return jsonify(db['leaderboard'])

@app.route('/api/student/<student_id>')
def api_student(student_id):
    student = db['students'].get(student_id)
    if student:
        return jsonify(student)
    return jsonify({'error': 'Student not found'}), 404

@app.route('/mark_notification_read/<int:notification_id>')
def mark_notification_read(notification_id):
    notification = next((n for n in db['notifications'] if n['id'] == notification_id), None)
    if notification:
        notification['read'] = True
    return redirect(url_for('notifications'))

# Additional routes for full functionality
@app.route('/join_club/<int:club_id>', methods=['POST'])
def join_club(club_id):
    student_id = request.form.get('student_id', 'anita-sharma')
    club = next((c for c in db['clubs'] if c['id'] == club_id), None)
    if club:
        club['members'] += 1
        # Add to student's joined clubs
        student = db['students'].get(student_id, {})
        if 'joined_clubs' not in student:
            student['joined_clubs'] = []
        if club_id not in student['joined_clubs']:
            student['joined_clubs'].append(club_id)
    return redirect(url_for('club_profile', club_id=club_id))

@app.route('/follow_club/<int:club_id>', methods=['POST'])
def follow_club(club_id):
    club = next((c for c in db['clubs'] if c['id'] == club_id), None)
    if club:
        club['followers'] += 1
    return redirect(url_for('club_profile', club_id=club_id))

@app.route('/bookmark_event/<int:event_id>', methods=['POST'])
def bookmark_event(event_id):
    student_id = request.form.get('student_id', 'anita-sharma')
    # Add bookmark functionality
    return redirect(url_for('event_details', event_id=event_id))

@app.route('/share_event/<int:event_id>', methods=['POST'])
def share_event(event_id):
    # Add sharing functionality
    return redirect(url_for('event_details', event_id=event_id))

@app.route('/like_post/<int:post_id>', methods=['POST'])
def like_post(post_id):
    post = next((p for p in db['posts'] if p['id'] == post_id), None)
    if post:
        post['likes'] += 1
    return redirect(url_for('feed'))

@app.route('/comment_post/<int:post_id>', methods=['POST'])
def comment_post(post_id):
    comment = request.form.get('comment')
    post = next((p for p in db['posts'] if p['id'] == post_id), None)
    if post:
        if 'comments' not in post:
            post['comments'] = []
        post['comments'].append({
            'id': len(post.get('comments', [])) + 1,
            'author': 'Current User',
            'text': comment,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    return redirect(url_for('feed'))

@app.route('/create_post', methods=['POST'])
def create_post():
    content = request.form.get('content')
    author = request.form.get('author', 'Current User')
    new_post = {
        'id': len(db['posts']) + 1,
        'name': author,
        'img': 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=100&q=60',
        'post': content,
        'likes': 0,
        'comments': 0,
        'timestamp': datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    }
    db['posts'].append(new_post)
    return redirect(url_for('feed'))

@app.route('/create_poll', methods=['POST'])
def create_poll():
    question = request.form.get('question')
    options = [request.form.get('option1'), request.form.get('option2')]
    if request.form.get('option3'):
        options.append(request.form.get('option3'))
    if request.form.get('option4'):
        options.append(request.form.get('option4'))
    
    new_poll = {
        'id': len(db['polls']) + 1,
        'question': question,
        'options': options,
        'votes': [0] * len(options),
        'event_id': None,
        'status': 'active'
    }
    db['polls'].append(new_poll)
    return redirect(url_for('polls'))

@app.route('/create_fundraiser', methods=['POST'])
def create_fundraiser():
    title = request.form.get('title')
    description = request.form.get('description')
    goal = float(request.form.get('goal', 10000))
    category = request.form.get('category', 'general')
    
    new_fundraiser = {
        'id': len(db['fundraisers']) + 1,
        'title': title,
        'description': description,
        'goal': goal,
        'raised': 0,
        'donors': 0,
        'status': 'active',
        'category': category
    }
    db['fundraisers'].append(new_fundraiser)
    return redirect(url_for('fundraisers'))

@app.route('/upload_event_photo/<int:event_id>', methods=['POST'])
def upload_event_photo(event_id):
    photo_url = request.form.get('photo_url')
    uploaded_by = request.form.get('uploaded_by', 'anita-sharma')
    
    new_photo = {
        'id': len(db['event_photos']) + 1,
        'event_id': event_id,
        'url': photo_url,
        'uploaded_by': uploaded_by,
        'timestamp': datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    }
    db['event_photos'].append(new_photo)
    return redirect(url_for('event_photos', event_id=event_id))

@app.route('/check_in/<int:event_id>', methods=['POST'])
def check_in(event_id):
    student_id = request.form.get('student_id', 'anita-sharma')
    action = request.form.get('action', 'check_in')
    
    if action == 'check_in':
        new_attendance = {
            'id': len(db['attendance']) + 1,
            'event_id': event_id,
            'student_id': student_id,
            'check_in': datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            'check_out': None,
            'status': 'present'
        }
        db['attendance'].append(new_attendance)
    else:  # check_out
        attendance = next((a for a in db['attendance'] if a['event_id'] == event_id and a['student_id'] == student_id), None)
        if attendance:
            attendance['check_out'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    
    return redirect(url_for('attendance', event_id=event_id))

@app.route('/create_announcement', methods=['POST'])
def create_announcement():
    title = request.form.get('title')
    message = request.form.get('message')
    announcement_type = request.form.get('type', 'general')
    
    # Add announcement to all students
    for student_id in db['students'].keys():
        new_notification = {
            'id': len(db['notifications']) + 1,
            'student_id': student_id,
            'title': title,
            'message': message,
            'type': announcement_type,
            'timestamp': datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            'read': False
        }
        db['notifications'].append(new_notification)
    
    return redirect(url_for('admin_panel'))

@app.route('/update_profile', methods=['POST'])
def update_profile():
    student_id = request.form.get('student_id', 'anita-sharma')
    name = request.form.get('name')
    bio = request.form.get('bio')
    interests = request.form.get('interests', '').split(',')
    
    student = db['students'].get(student_id, {})
    if name:
        student['name'] = name
    if bio:
        student['bio'] = bio
    if interests:
        student['interests'] = [i.strip() for i in interests if i.strip()]
    
    return redirect(url_for('profile', student_id=student_id))

@app.route('/search_events')
def search_events():
    query = request.args.get('q', '')
    category = request.args.get('category', '')
    
    filtered_events = db['events']
    if query:
        filtered_events = [e for e in filtered_events if query.lower() in e['title'].lower() or query.lower() in e['tagline'].lower()]
    if category:
        filtered_events = [e for e in filtered_events if e['cat'] == category]
    
    return render_template('dashboard.html', events=filtered_events)

@app.route('/search_clubs')
def search_clubs():
    query = request.args.get('q', '')
    filtered_clubs = db['clubs']
    if query:
        filtered_clubs = [c for c in filtered_clubs if query.lower() in c['name'].lower() or query.lower() in c['desc'].lower()]
    
    return render_template('clubs.html', clubs=filtered_clubs)

@app.route('/mark_all_notifications_read', methods=['POST'])
def mark_all_notifications_read():
    student_id = request.form.get('student_id', 'anita-sharma')
    for notification in db['notifications']:
        if notification['student_id'] == student_id:
            notification['read'] = True
    return redirect(url_for('notifications'))

@app.route('/delete_notification/<int:notification_id>')
def delete_notification(notification_id):
    db['notifications'] = [n for n in db['notifications'] if n['id'] != notification_id]
    return redirect(url_for('notifications'))

@app.route('/delete_post/<int:post_id>')
def delete_post(post_id):
    db['posts'] = [p for p in db['posts'] if p['id'] != post_id]
    return redirect(url_for('feed'))

@app.route('/reject_event/<int:event_id>')
def reject_event(event_id):
    event = next((e for e in db['events'] if e['id'] == event_id), None)
    if event:
        event['status'] = 'rejected'
    return redirect(url_for('admin_panel'))

@app.route('/delete_event/<int:event_id>')
def delete_event(event_id):
    db['events'] = [e for e in db['events'] if e['id'] != event_id]
    return redirect(url_for('organizer'))

@app.route('/delete_club/<int:club_id>')
def delete_club(club_id):
    db['clubs'] = [c for c in db['clubs'] if c['id'] != club_id]
    return redirect(url_for('admin_panel'))

@app.route('/update_event/<int:event_id>', methods=['POST'])
def update_event(event_id):
    event = next((e for e in db['events'] if e['id'] == event_id), None)
    if event:
        event['title'] = request.form.get('title', event['title'])
        event['tagline'] = request.form.get('tagline', event['tagline'])
        event['date'] = request.form.get('date', event['date'])
        event['venue'] = request.form.get('venue', event['venue'])
        event['description'] = request.form.get('description', event['description'])
    return redirect(url_for('organizer'))

@app.route('/update_club/<int:club_id>', methods=['POST'])
def update_club(club_id):
    club = next((c for c in db['clubs'] if c['id'] == club_id), None)
    if club:
        club['name'] = request.form.get('name', club['name'])
        club['desc'] = request.form.get('desc', club['desc'])
    return redirect(url_for('admin_panel'))

@app.route('/send_message/<student_id>', methods=['POST'])
def send_message(student_id):
    message = request.form.get('message')
    # Add message to notifications
    new_notification = {
        'id': len(db['notifications']) + 1,
        'student_id': student_id,
        'title': 'New Message',
        'message': message,
        'type': 'message',
        'timestamp': datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        'read': False
    }
    db['notifications'].append(new_notification)
    return redirect(url_for('profile', student_id=student_id))

@app.route('/follow_student/<student_id>', methods=['POST'])
def follow_student(student_id):
    # Add follow functionality
    return redirect(url_for('profile', student_id=student_id))

@app.route('/download_certificate/<int:certificate_id>')
def download_certificate(certificate_id):
    certificate = next((c for c in db['certificates'] if c['id'] == certificate_id), None)
    if certificate:
        # Generate and return certificate PDF
        return send_file('certificate.pdf', as_attachment=True)
    return redirect(url_for('certificate_generator'))

@app.route('/download_resume/<student_id>')
def download_resume(student_id):
    # Generate and return resume PDF
    return send_file('resume.pdf', as_attachment=True)

@app.route('/email_resume/<student_id>', methods=['POST'])
def email_resume(student_id):
    email = request.form.get('email')
    # Send email functionality
    return redirect(url_for('resume_builder', student_id=student_id))

@app.route('/bulk_generate_certificates', methods=['POST'])
def bulk_generate_certificates():
    # Process CSV file and generate certificates
    return redirect(url_for('certificate_generator'))

@app.route('/print_attendance/<int:event_id>')
def print_attendance(event_id):
    # Generate printable attendance report
    return send_file('attendance_report.pdf', as_attachment=True)

@app.route('/email_attendance/<int:event_id>', methods=['POST'])
def email_attendance(event_id):
    email = request.form.get('email')
    # Send attendance report via email
    return redirect(url_for('attendance', event_id=event_id))

if __name__ == '__main__':
    app.run(debug=True)
