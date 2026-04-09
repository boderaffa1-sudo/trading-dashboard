"""
Trading Dashboard for Railway Deployment
Standalone version - reads from trades.db
"""

from flask import Flask, render_template_string, jsonify
import sqlite3
import os
import logging
import numpy as np
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# HTML Template (same as dashboard_ultimate.py but embedded)
DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trading Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0e27;
            color: #e4e4e7;
            line-height: 1.6;
        }
        .header {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            padding: 2rem;
            border-bottom: 1px solid #334155;
        }
        .header h1 {
            font-size: 1.875rem;
            font-weight: 700;
            color: #f8fafc;
        }
        .container {
            max-width: 1600px;
            margin: 0 auto;
            padding: 2rem;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .metric-card {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 0.5rem;
            padding: 1.25rem;
        }
        .metric-label {
            font-size: 0.7rem;
            text-transform: uppercase;
            color: #94a3b8;
            margin-bottom: 0.5rem;
        }
        .metric-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: #f8fafc;
        }
        .metric-change {
            font-size: 0.75rem;
            margin-top: 0.25rem;
        }
        .metric-change.positive { color: #10b981; }
        .metric-change.negative { color: #ef4444; }
        .metric-change.neutral { color: #94a3b8; }
        .table-container {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 0.5rem;
            overflow: hidden;
            margin-bottom: 1.5rem;
        }
        .table-title {
            padding: 1.5rem;
            font-size: 1rem;
            font-weight: 600;
            border-bottom: 1px solid #334155;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th {
            background: #0f172a;
            padding: 0.75rem 1rem;
            text-align: left;
            font-size: 0.7rem;
            text-transform: uppercase;
            color: #94a3b8;
            border-bottom: 1px solid #334155;
        }
        td {
            padding: 0.75rem 1rem;
            border-bottom: 1px solid #334155;
            color: #e4e4e7;
        }
        tr:hover { background: #0f172a; }
        .empty-state {
            text-align: center;
            padding: 3rem;
            color: #64748b;
        }
        .status-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 0.5rem;
            background: #10b981;
            box-shadow: 0 0 8px rgba(16, 185, 129, 0.5);
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Trading Dashboard</h1>
        <div style="color: #94a3b8; font-size: 0.875rem;">
            <span class="status-indicator"></span>Live - Updates every 10s
        </div>
    </div>
    
    <div class="container">
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Portfolio Value</div>
                <div class="metric-value" id="portfolio-value">$0.00</div>
                <div class="metric-change neutral" id="portfolio-change">+0.00%</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Total Return</div>
                <div class="metric-value" id="total-return">0.00%</div>
                <div class="metric-change neutral" id="return-amount">$0.00</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Open Positions</div>
                <div class="metric-value" id="open-positions">0</div>
                <div class="metric-change neutral" id="position-value">$0.00 exposure</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Cash Balance</div>
                <div class="metric-value" id="cash-balance">$0.00</div>
                <div class="metric-change neutral">Available</div>
            </div>
        </div>
        
        <div class="table-container">
            <div class="table-title">Open Positions</div>
            <table>
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Quantity</th>
                        <th>Entry Price</th>
                        <th>Current Price</th>
                        <th>Unrealized P&L</th>
                        <th>Return %</th>
                        <th>Stop Loss</th>
                        <th>Take Profit</th>
                    </tr>
                </thead>
                <tbody id="positions-table">
                    <tr>
                        <td colspan="8" class="empty-state">No open positions</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        function formatCurrency(value) {
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD',
                minimumFractionDigits: 2
            }).format(value);
        }
        
        function formatPercent(value) {
            const sign = value >= 0 ? '+' : '';
            return sign + value.toFixed(2) + '%';
        }
        
        function updateDashboard(data) {
            document.getElementById('portfolio-value').textContent = formatCurrency(data.portfolio_value);
            document.getElementById('portfolio-change').textContent = formatPercent(data.portfolio_change_pct);
            document.getElementById('portfolio-change').className = 'metric-change ' + (data.portfolio_change_pct >= 0 ? 'positive' : 'negative');
            
            document.getElementById('total-return').textContent = formatPercent(data.total_return_pct);
            document.getElementById('return-amount').textContent = formatCurrency(data.total_return_amount);
            
            document.getElementById('open-positions').textContent = data.open_positions;
            document.getElementById('position-value').textContent = formatCurrency(data.positions_value) + ' exposure';
            
            document.getElementById('cash-balance').textContent = formatCurrency(data.cash_balance);
            
            updatePositionsTable(data.open_positions_data);
        }
        
        function updatePositionsTable(positions) {
            const table = document.getElementById('positions-table');
            if (!positions || positions.length === 0) {
                table.innerHTML = '<tr><td colspan="8" class="empty-state">No open positions</td></tr>';
                return;
            }
            
            table.innerHTML = positions.map(pos => `
                <tr>
                    <td><strong>${pos.symbol}</strong></td>
                    <td>${pos.quantity}</td>
                    <td>${formatCurrency(pos.entry_price)}</td>
                    <td>${formatCurrency(pos.current_price)}</td>
                    <td style="color: ${pos.unrealized_pnl >= 0 ? '#10b981' : '#ef4444'}">${formatCurrency(pos.unrealized_pnl)}</td>
                    <td style="color: ${pos.return_pct >= 0 ? '#10b981' : '#ef4444'}">${formatPercent(pos.return_pct)}</td>
                    <td>${formatCurrency(pos.stop_loss)}</td>
                    <td>${formatCurrency(pos.take_profit)}</td>
                </tr>
            `).join('');
        }
        
        function loadData() {
            fetch('/api/data')
                .then(response => response.json())
                .then(data => updateDashboard(data))
                .catch(error => console.error('Error:', error));
        }
        
        loadData();
        setInterval(loadData, 10000);
    </script>
</body>
</html>
'''

@app.route('/')
def dashboard():
    """Main Dashboard"""
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/data')
def api_data():
    """API Endpoint - reads from trades.db"""
    try:
        db_path = 'trades.db'
        
        # Check if database exists
        if not os.path.exists(db_path):
            logger.warning("Database not found - using defaults")
            return jsonify({
                'portfolio_value': 100000,
                'cash_balance': 100000,
                'positions_value': 0,
                'open_positions': 0,
                'portfolio_change_pct': 0,
                'total_return_pct': 0,
                'total_return_amount': 0,
                'open_positions_data': []
            })
        
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Get latest portfolio
        c.execute('SELECT portfolio_value, cash_balance, positions_value, num_positions FROM portfolio_history ORDER BY timestamp DESC LIMIT 1')
        row = c.fetchone()
        
        if not row:
            logger.warning("No portfolio history")
            conn.close()
            return jsonify({
                'portfolio_value': 100000,
                'cash_balance': 100000,
                'positions_value': 0,
                'open_positions': 0,
                'portfolio_change_pct': 0,
                'total_return_pct': 0,
                'total_return_amount': 0,
                'open_positions_data': []
            })
        
        # Get positions
        c.execute('SELECT symbol, quantity, entry_price, current_price, stop_loss, take_profit FROM positions')
        positions = c.fetchall()
        
        positions_data = []
        for p in positions:
            positions_data.append({
                'symbol': p[0],
                'quantity': p[1],
                'entry_price': p[2],
                'current_price': p[3],
                'unrealized_pnl': (p[3] - p[2]) * p[1],
                'return_pct': ((p[3] - p[2]) / p[2] * 100) if p[2] > 0 else 0,
                'stop_loss': p[4],
                'take_profit': p[5]
            })
        
        conn.close()
        
        initial_balance = 100000
        result = {
            'portfolio_value': row[0],
            'cash_balance': row[1],
            'positions_value': row[2],
            'open_positions': row[3],
            'open_positions_data': positions_data,
            'portfolio_change_pct': ((row[0] - initial_balance) / initial_balance * 100),
            'total_return_pct': ((row[0] - initial_balance) / initial_balance * 100),
            'total_return_amount': row[0] - initial_balance
        }
        
        logger.info(f"API called - Portfolio: ${result['portfolio_value']:.2f}, Positions: {result['open_positions']}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"API Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'service': 'trading-dashboard'})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    logger.info(f"Starting Trading Dashboard on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
