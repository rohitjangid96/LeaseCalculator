# Application Structure

## Production-Grade File Organization

This application follows a clean, maintainable structure suitable for production deployment.

## Directory Structure

```
lease_application/
├── app.py                          # Main Flask application entry point
├── main_app.py                     # Legacy entry point (deprecated - use app.py)
├── database.py                     # Database operations
├── complete_lease_backend.py       # Calculation API blueprint
│
├── config/                         # Configuration management
│   └── __init__.py                # Configuration classes (Dev/Prod)
│
├── auth/                          # Authentication module
│   ├── __init__.py                # Auth blueprint (routes)
│   └── auth.py                    # Auth utilities (require_login decorator)
│
├── api/                           # API routes module
│   └── __init__.py                # Lease management API routes
│
├── lease_accounting/              # Core lease accounting logic
│   ├── core/                     # Core business logic
│   │   ├── models.py            # Data models
│   │   ├── processor.py         # Lease processor (VBA compu() port)
│   │   └── lease_modifications.py
│   ├── schedule/                # Schedule generation
│   │   └── generator_vba_complete.py  # VBA datessrent()/basic_calc() port
│   └── utils/                    # Utilities
│       ├── date_utils.py
│       ├── finance.py
│       ├── journal_generator.py
│       └── rfr_rates.py
│
├── frontend/                      # Frontend files
│   ├── templates/                # HTML templates (Flask template directory)
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   ├── calculate.html
│   │   └── complete_lease_form.html
│   └── static/                   # Static assets (Flask static directory)
│       ├── css/                 # Stylesheets
│       │   ├── common.css       # Shared styles
│       │   ├── login.css        # Login page styles
│       │   └── dashboard.css    # Dashboard styles
│       └── js/                  # JavaScript
│           ├── api.js           # API client (centralized HTTP calls)
│           ├── auth.js          # Authentication utilities
│           ├── login.js         # Login page logic
│           └── dashboard.js     # Dashboard page logic
│
├── logs/                          # Application logs
│   ├── lease_app.log
│   └── http_server.log
│
└── lease_management.db           # SQLite database
```

## Module Responsibilities

### `app.py`
- Main Flask application entry point
- Application factory pattern
- Logging setup
- Blueprint registration
- Configuration loading

### `config/`
- Environment-based configuration
- Development vs Production settings
- Environment variable management

### `auth/`
- User authentication routes (`/api/login`, `/api/register`, `/api/logout`)
- Session management
- Authentication decorators (`require_login`)

### `api/`
- Lease management CRUD operations
- RESTful API endpoints for leases
- User-specific data filtering

### `frontend/`
- **Templates**: HTML files served by Flask
- **Static/CSS**: Extracted stylesheets (no inline styles)
- **Static/JS**: Extracted JavaScript modules (no inline scripts)
  - `api.js`: Centralized API communication
  - `auth.js`: Authentication helpers
  - Page-specific scripts: `login.js`, `dashboard.js`, etc.

## Key Improvements

1. **Separation of Concerns**
   - Auth logic separated from main app
   - API routes in dedicated module
   - Frontend assets properly organized

2. **Maintainability**
   - CSS and JS extracted from HTML
   - Centralized API client
   - Reusable authentication utilities

3. **Production Ready**
   - Configuration management
   - Environment variables
   - Proper logging
   - Blueprint-based architecture

4. **Scalability**
   - Easy to add new routes
   - Simple to add new pages
   - Modular structure supports growth

## Running the Application

### Development
```bash
python3 app.py
```

### Production
Set environment variables:
```bash
export FLASK_ENV=production
export SECRET_KEY=your-secret-key-here
export API_HOST=0.0.0.0
export API_PORT=5001
python3 app.py
```

## Migration Notes

- Old HTML files with inline CSS/JS can be found in root (backup)
- New structure uses Flask's template and static folders
- All routes now use blueprints for better organization
- Configuration externalized for deployment flexibility

