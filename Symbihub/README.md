# SymbiHub - College Event Management Platform

A comprehensive web application for managing college events, built with Flask and SQLite.

## Features

### 🔐 User Authentication
- User registration and login
- Secure password hashing
- Session management
- User profiles with college ID

### 📅 Event Management
- Create, update, and delete events
- Event cover image upload
- Event categorization (Tech, Cultural, Sports, etc.)
- Event registration with QR codes
- Event photo galleries
- Event search and filtering

### 👥 User Features
- **Home**: Dashboard with upcoming events and recent posts
- **Events**: Browse and search all events
- **My Events**: View created events and registered events
- **Profile**: User profile with statistics and achievements

### 🏛️ Club Management
- Club profiles and information
- Club event associations
- Member management

### 📊 Additional Features
- Event attendance tracking
- QR code generation for registrations
- File upload handling for images
- Responsive design with dark mode
- Real-time notifications

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Symbihub
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python app.py
   ```

4. **Access the application**
   - Open your browser and go to `http://localhost:5000`
   - Register a new account or use existing credentials

## Database Schema

The application uses SQLite with the following main tables:
- `users` - User accounts and profiles
- `events` - Event information and details
- `clubs` - Club information
- `event_registrations` - User event registrations
- `attendance` - Event attendance tracking
- `posts` - Social media posts
- `notifications` - User notifications
- `event_photos` - Event photo galleries

## File Structure

```
Symbihub/
├── app.py                 # Main Flask application
├── database.py            # Database models and initialization
├── requirements.txt       # Python dependencies
├── static/
│   ├── js/
│   │   └── app.js        # Frontend JavaScript
│   ├── manifest.json     # PWA manifest
│   └── sw.js            # Service worker
├── templates/            # HTML templates
│   ├── base.html        # Base template with navigation
│   ├── login.html       # Login/Register page
│   ├── dashboard.html   # Home dashboard
│   ├── events.html      # Events listing
│   ├── my_events.html   # User's events
│   ├── create_event.html # Event creation form
│   ├── update_event.html # Event update form
│   └── ...              # Other templates
└── uploads/             # File upload directory
```

## Key Features Implemented

### ✅ Navigation Bar
- **Home**: Dashboard with events and posts
- **Events**: Browse all events with search and filters
- **My Events**: Manage created and registered events
- **Profile**: User profile and statistics

### ✅ Database Integration
- Replaced in-memory data with SQLite database
- Proper database schema with relationships
- Sample data initialization
- Database connection management

### ✅ Event Management
- Full CRUD operations for events
- Cover image upload functionality
- Event registration system
- QR code generation for registrations
- Event photo galleries

### ✅ User Authentication
- Secure user registration and login
- Password hashing with Werkzeug
- Session management
- Login-required decorators

### ✅ File Upload System
- Image upload handling
- File type validation
- Secure filename generation
- Upload directory management

## Usage

1. **Register/Login**: Create an account or login with existing credentials
2. **Browse Events**: Use the Events page to discover events
3. **Create Events**: Use My Events to create and manage your events
4. **Register for Events**: Register for events you're interested in
5. **Upload Photos**: Add photos to events you've attended
6. **Manage Profile**: Update your profile information

## Development

The application is built with:
- **Backend**: Flask (Python)
- **Database**: SQLite
- **Frontend**: HTML, CSS (Tailwind), JavaScript
- **Icons**: Phosphor Icons
- **File Handling**: Werkzeug secure file uploads

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.
