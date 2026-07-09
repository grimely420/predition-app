#!/usr/bin/env python3
"""
Enhanced BNB API with ML predictions and improved validation.
"""

import sqlite3
import json
import sys
import os
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta, timezone
import threading
import time
import pytz

# Add project directory to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PREDICTION_DIR = os.path.join(BASE_DIR, "prediction")
sys.path.insert(0, PREDICTION_DIR)

from bnb.config import DB_PATH, MODEL_DIR, THRESHOLD_FILE, SYMBOL, PREDICTION_HORIZON
from shared.predictor import get_predictor
from bnb import engine as bnb_engine
from shared.dashboard import coin_dashboard_html
from shared.utils import setup_logging

app = Flask(__name__)
CORS(app)

# Setup logging
logger = setup_logging("BNB-API")

# Initialize ML predictor
bnb_predictor = get_predictor(
    symbol=SYMBOL,
    model_dir=MODEL_DIR,
    feature_engineer=bnb_engine,
    prediction_horizon=PREDICTION_HORIZON
)

# Set Eastern Time Zone
ET = pytz.timezone('US/Eastern')

def get_local_time():
    """Get current Eastern Time"""
    return datetime.now(ET)

def format_local_time(dt_str):
    """Convert UTC timestamp to Eastern Time"""
    try:
        # Parse UTC timestamp
        if dt_str.endswith('Z'):
            dt_str = dt_str.replace('Z', '+00:00')
        utc_dt = datetime.fromisoformat(dt_str)
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=timezone.utc)
        # Convert to Eastern Time
        et_dt = utc_dt.astimezone(ET)
        return et_dt.strftime('%I:%M:%S %p ET').lstrip('0')
    except:
        return dt_str

def get_threshold():
    try:
        with open(THRESHOLD_FILE, 'r') as f:
            return float(f.read().strip())
    except:
        return 1.0

def get_current_price():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT price, timestamp FROM prices ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        conn.close()
        if row:
            # Convert timestamp to Eastern Time for display
            local_ts = format_local_time(row[1])
            return row[0], local_ts
        return None, None
    except:
        return None, None

def get_price_for_validation():
    """Get raw UTC timestamp for validation"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT price, timestamp FROM prices ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        conn.close()
        return row if row else (None, None)
    except:
        return None, None

def log_prediction(predicted_price, model_used, confidence_interval=None):
    """Log prediction with enhanced metadata."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        pred_time = datetime.now(timezone.utc).isoformat()
        
        # Convert confidence interval to JSON if provided
        conf_json = json.dumps(confidence_interval) if confidence_interval else None
        
        c.execute('''INSERT INTO predictions 
                     (prediction_time, predicted_price, model_used, checked) 
                     VALUES (?, ?, ?, 0)''',
                  (pred_time, predicted_price, model_used))
        conn.commit()
        conn.close()
        
        logger.info(f"Logged prediction: ${predicted_price:.2f} using {model_used}")
    except Exception as e:
        logger.error(f"Log prediction error: {e}")

def validate_old_predictions():
    """Enhanced prediction validation with better error handling and logging."""
    while True:
        try:
            time.sleep(60)
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            now = datetime.now(timezone.utc)
            cutoff = (now - timedelta(minutes=PREDICTION_HORIZON + 2)).isoformat()
            
            # Get predictions that need validation
            c.execute('''SELECT id, prediction_time, predicted_price, model_used 
                        FROM predictions 
                        WHERE (checked IS NULL OR checked=0) 
                        AND prediction_time <= ? 
                        ORDER BY prediction_time ASC''', (cutoff,))
            rows = c.fetchall()
            
            if rows:
                logger.info(f"Found {len(rows)} predictions to validate")
            
            threshold = get_threshold()
            validated_count = 0
            
            for pid, pt_str, pred_price, model_used in rows:
                try:
                    target_dt = datetime.fromisoformat(pt_str) + timedelta(minutes=PREDICTION_HORIZON)
                    target = target_dt.isoformat()
                    
                    # Get actual price at target time (allow 1 minute window)
                    c.execute('''SELECT price, timestamp 
                                FROM prices 
                                WHERE timestamp >= ? 
                                AND timestamp <= ?
                                ORDER BY timestamp ASC 
                                LIMIT 1''',
                              (target, (target_dt + timedelta(minutes=2)).isoformat()))
                    row = c.fetchone()
                    
                    if row:
                        actual, actual_timestamp = row
                        error = actual - pred_price
                        error_pct = (error / pred_price) * 100
                        is_correct = 1 if abs(error_pct) < threshold else 0
                        
                        c.execute('''UPDATE predictions 
                                    SET actual_price=?, error=?, checked=1, is_correct=? 
                                    WHERE id=?''',
                                  (actual, error, is_correct, pid))
                        conn.commit()
                        
                        validated_count += 1
                        logger.info(
                            f"Validated BNB pred {pid}: ${pred_price:.2f} → ${actual:.2f} "
                            f"(Error: {error_pct:+.2f}%, Correct: {is_correct}, Model: {model_used})"
                        )
                    else:
                        logger.warning(f"No actual price found for prediction {pid} at {target}")
                        
                except Exception as e:
                    logger.error(f"Error validating prediction {pid}: {e}")
            
            if validated_count > 0:
                logger.info(f"Validated {validated_count} predictions this cycle")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Validation cycle error: {e}")
            time.sleep(30)  # Wait before retry

threading.Thread(target=validate_old_predictions, daemon=True).start()

@app.route('/predict')
def predict():
    """Make prediction using ML model."""
    try:
        current, _ = get_price_for_validation()
        if not current:
            logger.warning("No price data available for prediction")
            return jsonify({'error': 'No price data'}), 400
        
        # Use ML predictor
        result = bnb_predictor.predict(current)
        
        if result and result.get('success'):
            # Log the prediction
            log_prediction(
                result['predicted_price'], 
                result.get('model_used', 'unknown')
            )
            
            # Format response
            response = {
                'success': True,
                'current_price': round(result['current_price'], 2),
                f'predicted_price_{PREDICTION_HORIZON}min': round(result['predicted_price'], 2),
                'change_percent': round(result['change_percent'], 4),
                'model_used': result.get('model_used', 'unknown'),
                'prediction_horizon': PREDICTION_HORIZON,
                'confidence_interval': result.get('confidence_interval', {}),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Add fallback flag if applicable
            if result.get('fallback'):
                response['fallback_used'] = True
                logger.warning("Used fallback prediction for BNB")
            
            return jsonify(response)
        else:
            logger.error("ML prediction failed, using fallback")
            # Fallback to simple prediction
            predicted = current * 1.0005
            log_prediction(predicted, 'fallback')
            return jsonify({
                'success': True,
                'current_price': round(current, 2),
                f'predicted_price_{PREDICTION_HORIZON}min': round(predicted, 2),
                'change_percent': 0.05,
                'model_used': 'fallback',
                'fallback_used': True,
                'prediction_horizon': PREDICTION_HORIZON
            })
            
    except Exception as e:
        logger.error(f"Prediction endpoint error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    """Enhanced health check with comprehensive status."""
    try:
        # Check database connectivity
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get data stats
        cursor.execute("SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM prices")
        count, min_ts, max_ts = cursor.fetchone()
        
        # Get prediction stats
        cursor.execute("SELECT COUNT(*) FROM predictions WHERE checked=1 AND actual_price IS NOT NULL")
        validated_preds = cursor.fetchone()[0]
        
        # Get model info
        model_exists = os.path.exists(os.path.join(MODEL_DIR, "xgb_5min_latest.pkl"))
        
        conn.close()
        
        # Check if data is recent
        last_data_age = None
        if max_ts:
            try:
                last_ts = datetime.fromisoformat(max_ts)
                last_data_age = (datetime.now(timezone.utc) - last_ts).total_seconds()
            except:
                pass
        
        status = {
            'status': 'healthy',
            'service': 'BNB',
            'version': '2.0.0',
            'data_points': count,
            'validated_predictions': validated_preds,
            'model_available': model_exists,
            'last_data_seconds_ago': round(last_data_age, 1) if last_data_age else None,
            'prediction_horizon': PREDICTION_HORIZON,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Determine health status
        if last_data_age and last_data_age > 120:
            status['status'] = 'degraded'
            status['message'] = 'Data collection may be delayed'
        
        if not model_exists:
            status['status'] = 'warning'
            status['message'] = 'ML model not yet trained'
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'error',
            'service': 'BNB',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500

@app.route('/current_price')
def current_price():
    price, local_ts = get_current_price()
    if price:
        return jsonify({'price': price, 'timestamp': local_ts})
    return jsonify({'error': 'No data'}), 404

@app.route('/accuracy_summary')
def accuracy_summary():
    window = request.args.get('window', 100, type=int)
    threshold = get_threshold()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT AVG(ABS(error)/predicted_price*100), AVG(ABS(error)), COUNT(*),
                        SUM(CASE WHEN ABS(error)/predicted_price < ?/100 THEN 1 ELSE 0 END)
                 FROM (SELECT error, predicted_price FROM predictions WHERE checked=1 AND actual_price IS NOT NULL ORDER BY id DESC LIMIT ?)''', (threshold, window))
    row = c.fetchone()
    conn.close()
    avg_pct = round(row[0] or 0, 2)
    avg_usd = round(row[1] or 0, 2)
    cnt = row[2] or 0
    within = row[3] or 0
    acc = round(100*within/cnt, 1) if cnt else 0
    return jsonify({'last_n_predictions': cnt, 'avg_error_percent': avg_pct, 'avg_abs_error_usd': avg_usd,
                    'predictions_within_threshold': within, 'accuracy_percent': acc, 'threshold': threshold})

@app.route('/recent_predictions')
def recent_predictions():
    limit = request.args.get('limit', 20, type=int)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT id, prediction_time, predicted_price, actual_price, error, checked, is_correct, model_used,
                        ROUND(100.0*error/predicted_price,2) as error_pct
                 FROM predictions WHERE checked=1 ORDER BY id DESC LIMIT ?''', (limit,))
    rows = c.fetchall()
    conn.close()
    out = []
    for r in rows:
        # Convert prediction time to local time
        local_time = format_local_time(r[1])
        out.append({'id':r[0], 'prediction_time':local_time, 'predicted_price':r[2], 'actual_price':r[3],
                    'error':r[4], 'validated':bool(r[5]), 'is_correct':bool(r[6]) if r[6] is not None else None,
                    'model_used':r[7], 'error_percent':r[8]})
    return jsonify(out)

@app.route('/error_history')
def error_history():
    limit = request.args.get('limit', 50, type=int)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT prediction_time, 100.0 * error / predicted_price as error_percent 
                 FROM predictions WHERE checked=1 AND actual_price IS NOT NULL ORDER BY id DESC LIMIT ?''', (limit,))
    rows = c.fetchall()
    conn.close()
    data = [{'time': format_local_time(r[0]), 'error_percent': round(r[1],2)} for r in reversed(rows)]
    return jsonify(data)

@app.route('/detailed_stats')
def detailed_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT model_used, COUNT(*), AVG(ABS(error)/predicted_price*100),
                        SUM(CASE WHEN ABS(error)/predicted_price*100 < 1 THEN 1 ELSE 0 END)
                 FROM predictions WHERE checked=1 AND error IS NOT NULL GROUP BY model_used''')
    rows = c.fetchall()
    conn.close()
    stats = {}
    for row in rows:
        stats[row[0]] = {'count': row[1], 'avg_error': round(row[2] or 0, 2), 'accuracy': round(100 * (row[3] or 0) / row[1], 2) if row[1] > 0 else 0}
    return jsonify(stats)

@app.route('/advanced_metrics')
def advanced_metrics():
    """Advanced validation metrics including directional accuracy and volatility-adjusted performance."""
    try:
        window = request.args.get('window', 100, type=int)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Get recent predictions with actual prices
        c.execute('''SELECT predicted_price, actual_price, error, model_used
                    FROM predictions 
                    WHERE checked=1 AND actual_price IS NOT NULL 
                    ORDER BY id DESC LIMIT ?''', (window,))
        rows = c.fetchall()
        conn.close()
        
        if not rows:
            return jsonify({'error': 'No validated predictions available'}), 404
        
        # Calculate advanced metrics
        predictions = []
        for pred, actual, error, model in rows:
            predictions.append({
                'predicted': pred,
                'actual': actual,
                'error': error,
                'error_pct': (error / pred) * 100,
                'model': model
            })
        
        # Directional accuracy (did we predict the right direction?)
        directional_correct = 0
        total = len(predictions)
        
        # Calculate various metrics
        total_abs_error = sum(abs(p['error']) for p in predictions)
        total_abs_error_pct = sum(abs(p['error_pct']) for p in predictions)
        max_error = max(abs(p['error']) for p in predictions)
        min_error = min(abs(p['error']) for p in predictions)
        
        # Error distribution
        errors_pct = [p['error_pct'] for p in predictions]
        mean_error_pct = sum(errors_pct) / total
        std_error_pct = (sum((x - mean_error_pct) ** 2 for x in errors_pct) / total) ** 0.5
        
        # Performance by model
        model_performance = {}
        for p in predictions:
            model = p['model']
            if model not in model_performance:
                model_performance[model] = {'count': 0, 'total_error': 0, 'errors': []}
            model_performance[model]['count'] += 1
            model_performance[model]['total_error'] += abs(p['error_pct'])
            model_performance[model]['errors'].append(abs(p['error_pct']))
        
        # Calculate per-model averages
        for model in model_performance:
            data = model_performance[model]
            data['avg_error_pct'] = data['total_error'] / data['count']
            data['std_error_pct'] = (sum((x - data['avg_error_pct']) ** 2 for x in data['errors']) / data['count']) ** 0.5
        
        metrics = {
            'total_predictions': total,
            'mean_abs_error_pct': round(total_abs_error_pct / total, 4),
            'std_error_pct': round(std_error_pct, 4),
            'max_abs_error_pct': round(max(abs(p['error_pct']) for p in predictions), 4),
            'min_abs_error_pct': round(min(abs(p['error_pct']) for p in predictions), 4),
            'mean_error_pct': round(mean_error_pct, 4),
            'model_performance': model_performance,
            'window': window,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        return jsonify(metrics)
        
    except Exception as e:
        logger.error(f"Advanced metrics error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/set_threshold', methods=['POST'])
def set_threshold_route():
    data = request.get_json()
    threshold = float(data.get('threshold', 1.0))
    with open(THRESHOLD_FILE, 'w') as f:
        f.write(str(threshold))
    return jsonify({'success': True})

@app.route('/retrain', methods=['POST'])
def force_retrain():
    return jsonify({'success': False, 'error': 'Auto-retrain active'})

@app.route('/')
@app.route('/dashboard')
def dashboard():
    endpoints = [
        { 'method': 'GET', 'path': '/', 'desc': 'This dashboard page. Returns the API overview.' },
        { 'method': 'GET', 'path': '/health', 'desc': 'Service health check with data and model status.' },
        { 'method': 'GET', 'path': '/predict', 'desc': 'Make a single-horizon ML prediction.' },
        { 'method': 'GET', 'path': '/current_price', 'desc': 'Latest collected price and timestamp.' },
        { 'method': 'GET', 'path': '/accuracy_summary', 'desc': 'Accuracy and error summary over recent predictions.' },
        { 'method': 'GET', 'path': '/recent_predictions', 'desc': 'List of recent validated predictions.' },
        { 'method': 'GET', 'path': '/error_history', 'desc': 'Historical error percentages.' },
        { 'method': 'GET', 'path': '/detailed_stats', 'desc': 'Per-model performance statistics.' },
        { 'method': 'GET', 'path': '/advanced_metrics', 'desc': 'Advanced validation metrics.' },
        { 'method': 'POST', 'path': '/set_threshold', 'desc': 'Set the accuracy threshold percentage.' },
        { 'method': 'POST', 'path': '/retrain', 'desc': 'Trigger a model retrain (disabled when auto-retrain is active).' },
    ]
    html = coin_dashboard_html('bnb', 'BNB', endpoints, coin_emoji='&#9650;', stats_endpoint='/detailed_stats', stats_title='Detailed Stats')
    return Response(html, mimetype='text/html')

if __name__ == '__main__':
    print("🚀 Futuristic BNB API starting on port 5002")
    app.run(host='0.0.0.0', port=5002, debug=False)
