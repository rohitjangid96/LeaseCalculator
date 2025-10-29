# Quick Start Guide

## Starting the Application

### Option 1: Use the start script (Recommended)
```bash
./start_app.sh
```

This will:
- Install dependencies
- Kill any existing processes
- Start the Flask server
- Wait for it to be ready
- Open the login page in your browser

### Option 2: Manual start
```bash
cd lease_application
python3 app.py
```

Then open: **http://localhost:5001/login.html**

## Important URLs

- **Login**: http://localhost:5001/login.html
- **Dashboard**: http://localhost:5001/dashboard.html
- **API**: http://localhost:5001/api/
- **Calculate**: http://localhost:5001/calculate.html
- **Lease Form**: http://localhost:5001/complete_lease_form.html

## Troubleshooting

### Login page not loading
1. Check if server is running: `curl http://localhost:5001/login.html`
2. Check logs: `tail -f lease_application/logs/lease_app.log`
3. Ensure port 5001 is not in use: `lsof -i :5001`

### Server not starting
1. Check Python version: `python3 --version` (needs 3.7+)
2. Install dependencies: `pip3 install flask flask-cors python-dateutil`
3. Check database: Ensure `lease_management.db` exists or is writable

### Static files (CSS/JS) not loading
- Verify files exist in `frontend/static/` directory
- Check browser console for 404 errors
- Ensure Flask is serving static files correctly

## Stopping the Server

```bash
pkill -f app.py
```

Or find the process:
```bash
ps aux | grep app.py
kill <PID>
```

