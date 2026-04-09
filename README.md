# Trading Dashboard - Railway Deployment

Live trading dashboard showing portfolio value, positions, and P&L.

## Features
- Real-time portfolio tracking
- Open positions table
- Clean, professional UI
- Auto-updates every 10 seconds

## Deployment

### Railway
1. Push this folder to GitHub
2. Connect to Railway
3. Deploy automatically

### Local Testing
```bash
pip install -r requirements.txt
python app.py
```

Visit: http://localhost:5000

## API Endpoints
- `/` - Dashboard UI
- `/api/data` - Portfolio data (JSON)
- `/health` - Health check

## Requirements
- Python 3.8+
- Flask
- Gunicorn
- Numpy

## Database
Reads from `trades.db` (SQLite) - must be uploaded or synced separately.
