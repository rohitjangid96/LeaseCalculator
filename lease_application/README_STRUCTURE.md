# Production-Grade Application Structure

## Overview

The application has been restructured into a clean, maintainable, production-ready architecture with clear separation of concerns.

## New Structure

```
lease_application/
├── app.py                    # 🚀 Main Flask application (use this instead of main_app.py)
├── config/                   # ⚙️  Configuration management
│   └── __init__.py
├── auth/                     # 🔐 Authentication module
│   ├── __init__.py          # Auth routes (login, register, logout)
│   └── auth.py              # Auth utilities
├── api/                      # 🌐 API routes module
│   └── __init__.py          # Lease CRUD operations
├── frontend/                 # 🎨 Frontend files
│   ├── templates/           # HTML templates
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   ├── calculate.html
│   │   └── complete_lease_form.html
│   └── static/              # Static assets
│       ├── css/            # Stylesheets (extracted from HTML)
│       │   ├── common.css
│       │   ├── login.css
│       │   └── dashboard.css
│       └── js/             # JavaScript (extracted from HTML)
│           ├── api.js      # Centralized API client
│           ├── auth.js     # Auth utilities
│           ├── login.js
│           └── dashboard.js
└── lease_accounting/        # 💼 Business logic (unchanged)
```

## Key Improvements

### 1. **Separation of Concerns**
- ✅ Authentication logic moved to `auth/` module
- ✅ API routes separated into `api/` module
- ✅ Configuration externalized to `config/` module
- ✅ Frontend assets properly organized

### 2. **Maintainability**
- ✅ CSS extracted from HTML files
- ✅ JavaScript extracted from HTML files
- ✅ Centralized API client (`frontend/static/js/api.js`)
- ✅ Reusable authentication utilities

### 3. **Production Ready**
- ✅ Environment-based configuration
- ✅ Proper logging setup
- ✅ Blueprint-based architecture
- ✅ Session management

## Running the Application

### Option 1: Use the start script (Recommended)
```bash
./start_app.sh
```

### Option 2: Direct Python
```bash
cd lease_application
python3 app.py
```

The application will be available at:
- **Main App**: http://localhost:5001
- **Login**: http://localhost:5001/login.html
- **Dashboard**: http://localhost:5001/dashboard.html
- **API**: http://localhost:5001/api/

## Module Details

### `app.py` (Main Entry Point)
- Flask application factory
- Blueprint registration
- Logging configuration
- Route definitions for HTML pages

### `auth/` Module
**Routes:**
- `POST /api/register` - User registration
- `POST /api/login` - User login
- `POST /api/logout` - User logout
- `GET /api/user` - Get current user

**Utilities:**
- `require_login` decorator for protected routes

### `api/` Module
**Routes (all require authentication):**
- `GET /api/leases` - List all leases
- `GET /api/leases/<id>` - Get specific lease
- `POST /api/leases` - Create/Update lease
- `PUT /api/leases/<id>` - Update lease
- `DELETE /api/leases/<id>` - Delete lease

### `frontend/static/js/api.js`
Centralized API client with helper functions:
- `AuthAPI` - Authentication operations
- `LeasesAPI` - Lease management operations
- `CalculationAPI` - Calculation operations

All API calls automatically include credentials and proper error handling.

## Configuration

Set environment variables for production:

```bash
export FLASK_ENV=production
export SECRET_KEY=your-secret-key-here
export API_HOST=0.0.0.0
export API_PORT=5001
```

See `config/__init__.py` for all available settings.

## Migration Notes

1. **Old files are preserved** - Original HTML files still exist in root directory
2. **New structure** - All new files use the organized structure
3. **Flask templates** - HTML files now use Flask's template system
4. **Static files** - CSS/JS properly served as static assets

## Benefits

✅ **Easy to maintain** - Clear separation between frontend/backend  
✅ **Scalable** - Easy to add new routes, pages, or features  
✅ **Production ready** - Configuration management, logging, security  
✅ **Developer friendly** - Clear structure, reusable utilities  
✅ **Best practices** - Follows Flask application patterns

