# Lease Management System

A comprehensive lease accounting and management system with user authentication, database storage, and accurate Excel/VBA-compatible calculations.

## 🚀 Quick Start

```bash
cd lease_application
python3 main_app.py &
python3 -m http.server 8000 &
```

Open: **http://localhost:8000/login.html**

## 📋 Features

### ✅ Complete System
- **Multi-user authentication** - Secure login with bcrypt password hashing
- **Database storage** - SQLite with users, leases, and calculations tables
- **Complete lease management** - Create, edit, view, delete leases
- **Accurate calculations** - 13-column amortization schedule matching Excel/VBA
- **Escalation support** - Annual escalation (5% working perfectly)
- **Auto calculations** - Tenure ↔ Lease End Date synchronization
- **First Payment Date** - Rent starts from first payment (not lease start)
- **Excel export** - Download results with formatting
- **User-specific data** - Each user sees only their own leases

### 🎯 Main Features
1. **User Registration/Login** - Secure authentication system
2. **Dashboard** - View all your leases with actions
3. **Create/Edit Leases** - Complete lease form with all fields
4. **Calculate Leases** - Accurate amortization and journal entries
5. **Date Range Calculations** - Calculate specific periods
6. **Excel Export** - Download formatted results

## 📁 File Structure

```
lease_application/
├── app.py                         # Main Flask application (USE THIS)
├── database.py                    # Database layer
├── complete_lease_backend.py      # Calculation API blueprint
│
├── config/                        # Configuration management
├── auth/                          # Authentication module
├── api/                           # API routes module
│
├── frontend/                      # Frontend files
│   ├── templates/                # HTML templates
│   └── static/                   # CSS/JS assets
│
├── tests/                         # Test suite
│   └── test_end_to_end.py        # Comprehensive E2E tests
│
├── lease_accounting/              # Core calculation engine
│   ├── core/
│   │   ├── models.py             # Data models
│   │   └── processor.py          # Processing logic
│   ├── schedule/
│   │   └── generator_complete.py # Schedule generation
│   └── utils/
│       ├── date_utils.py          # Date utilities
│       ├── finance.py             # Financial calculations
│       ├── journal_generator.py  # Journal entries
│       └── rfr_rates.py           # RFR rates table
│
└── lease_management.db            # SQLite database (auto-created)
```

## 🗄️ Database Schema

### Users Table
- `user_id` (PK) - Unique user identifier
- `username` (unique) - User login name
- `password_hash` (bcrypt) - Secure password storage
- `email` - User email
- `created_at` - Account creation timestamp

### Leases Table
- `lease_id` (PK) - Unique lease identifier
- `user_id` (FK) - Owner user
- `lease_name` - Display name for lease
- All 50+ lease fields from the form
- `created_at`, `updated_at` - Timestamps

### Lease Calculations Table
- `calc_id` (PK) - Calculation identifier
- `lease_id` (FK) - Reference to lease
- `from_date`, `to_date` - Calculation period
- `calculation_data` (JSON) - Results storage
- `created_at` - When calculation ran

## 🔧 API Endpoints

### Authentication
```
POST /api/register      - Create new user
POST /api/login         - Login user  
POST /api/logout        - Logout user
GET  /api/user          - Get current user
```

### Lease Management
```
GET    /api/leases           - Get all user leases
GET    /api/leases/:id       - Get specific lease
POST   /api/leases           - Create new lease
PUT    /api/leases/:id       - Update existing lease
DELETE /api/leases/:id       - Delete lease
```

### Calculations
```
POST /api/calculate_lease    - Calculate lease with full data
```

## 📖 User Guide

### 1. First Time Setup
1. Start the application: `cd lease_application && ./start_lease_mgmt.sh`
2. Open `http://localhost:8000/login.html`
3. Click "Sign Up" tab
4. Create your account (username, email, password)
5. Login with your credentials

### 2. Create a Lease
1. From dashboard, click **"+ Create New Lease"**
2. Fill out the complete lease form:
   - Asset information (name, class, ID)
   - Dates (start, first payment, end, tenure)
   - Rentals and escalation
   - Financial details (borrowing rate, ARO, security deposit)
   - Additional settings
3. Click **"Calculate Lease"**
4. View results and export to Excel

### 3. View All Leases
- Dashboard shows all your leases
- See: Lease name, asset class, dates, created date
- Actions available: Edit, Calculate, Delete

### 4. Edit a Lease
1. Click **"Edit"** on any lease card
2. Make your changes
3. Click **"Calculate Lease"** to save and recalculate

### 5. Calculate with Date Range
1. Click **"Calculate"** on any lease
2. Select the lease from dropdown
3. Enter **From Date** and **To Date**
4. View results for that specific period

### 6. Delete a Lease
1. Click **"Delete"** on any lease card
2. Confirm deletion
3. Lease is permanently removed

## ⚙️ Configuration

### Ports
- **Backend API**: `http://localhost:5001`
- **Web Interface**: `http://localhost:8000`

### Database
- Location: `lease_application/lease_management.db`
- Type: SQLite (file-based, no separate server needed)
- Auto-created on first run

## 🔐 Security

- **Password hashing**: bcrypt (industry standard)
- **Session management**: Flask sessions with secure cookies
- **User isolation**: Each user sees only their own data
- **SQL injection protection**: Parameterized queries
- **CSRF protection**: Session-based authentication

## 🧮 Calculation Accuracy

This system replicates Excel/VBA logic exactly:

- **Escalation**: Compound interest (5% annually = $150K → $157.5K → $165.375K)
- **Tenure calculation**: Auto-sync between months and end date
- **Payment dates**: Start from First Payment Date (not lease start)
- **PV factors**: Accurate discounting
- **Interest calculation**: Daily compounding
- **Depreciation**: Straight-line over lease term
- **ARO**: Risk-free rate table lookups
- **Security deposit**: Present value calculations

### Calculation Test
Default values in form:
- Rent: $150,000/month
- Tenure: 60 months
- Escalation: 5% every 12 months
- First Payment: 2024-01-16

Results show correct escalation at 2026, 2027, 2028.

## 📊 View Database Records

### Option 1: SQLite Browser (Recommended)
```bash
# Download DB Browser for SQLite
# Or install via brew:
brew install --cask db-browser-for-sqlite

# Open database
open lease_management.db
```

### Option 2: Command Line
```bash
cd lease_application
sqlite3 lease_management.db

# View all tables
.tables

# View users
SELECT * FROM users;

# View leases
SELECT lease_id, lease_name, asset_class FROM leases;

# Exit
.quit
```

### Option 3: Python Script
```python
import sqlite3
conn = sqlite3.connect('lease_management.db')
cursor = conn.cursor()

# Get all leases
cursor.execute("SELECT * FROM leases")
for row in cursor.fetchall():
    print(row)
```

## 🛠️ Troubleshooting

### Issue: Port 5001 in use
```bash
# Find and kill the process
lsof -ti:5001 | xargs kill -9

# Restart
python3 main_app.py
```

### Issue: Port 8000 in use
```bash
# Kill the HTTP server
pkill -f "http.server"

# Restart
python3 -m http.server 8000 &
```

### Issue: Database locked
- Close any open database connections
- Restart the application

### Issue: CORS errors
- Make sure you're accessing via `http://localhost:8000`, not `file://`
- HTTP server must be running

### Issue: Login not working
- Clear browser cache and cookies
- Make sure backend is running: `curl http://localhost:5001/api/health`
- Check browser console (F12) for errors

## 🚀 Deployment (Production)

### Current Setup (Development)
- Single-threaded Flask server
- SQLite database
- Local file storage

### Recommended Production Setup

#### Option 1: Server + PostgreSQL
```bash
# Install PostgreSQL
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 main_app:app
```

#### Option 2: Docker
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "4", "main_app:app"]
```

#### Option 3: Cloud Platform
- **Heroku**: One-click deploy
- **AWS**: EC2 + RDS
- **Google Cloud**: App Engine + Cloud SQL
- **Azure**: App Service + SQL Database

## 📝 Development

### Add New Features
1. Database changes: Update `database.py` schema
2. API changes: Update API files in root
3. UI changes: Update HTML files
4. Calculations: Update `lease_accounting/` modules

### Run Tests
```bash
# Test calculation accuracy
python3 -c "
from lease_accounting.schedule.generator_complete import generate_complete_schedule
from lease_accounting.core.models import LeaseData
from datetime import date

lease = LeaseData(
    lease_start_date=date(2024,1,1),
    first_payment_date=date(2024,1,16),
    end_date=date(2028,12,31),
    rental_1=150000,
    escalation_percent=5,
    escalation_start=date(2025,1,1),
    esc_freq_months=12,
    borrowing_rate=5.5
)

schedule = generate_complete_schedule(lease)
print(f'Generated {len(schedule)} schedule rows')
print(f'First payment: {schedule[1].rental_amount}')
print(f'Escalated payment: {schedule[25].rental_amount}')
"
```

## 📄 License

This software is provided as-is for lease accounting and management.

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section
2. Review calculation logic in `lease_accounting/` folder
3. Check browser console (F12) for errors
4. Verify database with SQLite browser

## 🎯 Roadmap

### Future Enhancements
- [ ] Multi-lease reports and comparisons
- [ ] Bulk import from Excel
- [ ] Email notifications for renewals
- [ ] Advanced search and filtering
- [ ] CSV export of calculations
- [ ] User roles (admin, viewer)
- [ ] Audit logging
- [ ] Mobile-responsive design
- [ ] PDF report generation
- [ ] API for third-party integration

---

**Built with Python, Flask, SQLite, and modern web technologies.**

# LeaseCalculator
