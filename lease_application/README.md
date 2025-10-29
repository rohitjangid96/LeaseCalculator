# Lease Accounting Application

## Quick Start

```bash
cd lease_application
python3 main_app.py &
python3 -m http.server 8000 &
```

Open: **http://localhost:8000/login.html**

## Core Files

- `main_app.py` - Flask application with authentication and API
- `complete_lease_backend.py` - Lease calculation engine
- `database.py` - SQLite database operations
- `lease_accounting/` - Core calculation modules (VBA-compatible)

## Features

- User authentication with secure login
- Create, edit, delete leases
- Accurate amortization schedule (13 columns)
- Journal entries with Excel export
- Date range calculations
- Escalation support
- ARO, Security Deposits, Lease Modifications

