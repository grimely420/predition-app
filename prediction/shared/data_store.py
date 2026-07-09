#!/usr/bin/env python3
"""
Generic SQLite data manager for price and prediction records.
"""

import sqlite3
import json
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any

from .utils import setup_logging

logger = setup_logging("DataStore")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DataStore:
    """Manages a single coin's SQLite database."""

    def __init__(self, db_path: str, coin_symbol: str):
        self.db_path = db_path
        self.symbol = coin_symbol
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                price REAL NOT NULL,
                source TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_prices_timestamp ON prices(timestamp)
        ''')
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_prices_id ON prices(id)
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_time TEXT NOT NULL,
                horizon_min INTEGER NOT NULL,
                current_price REAL NOT NULL,
                predicted_price REAL NOT NULL,
                actual_price REAL,
                error REAL,
                error_pct REAL,
                checked INTEGER DEFAULT 0,
                is_correct INTEGER,
                model_used TEXT,
                model_version TEXT,
                source TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Backward-compatible schema migrations (must run before indexes)
        existing = [col[1] for col in c.execute("PRAGMA table_info(predictions)").fetchall()]
        for col, dtype in [
            ('horizon_min', 'INTEGER NOT NULL DEFAULT 5'),
            ('current_price', 'REAL'),
            ('error_pct', 'REAL'),
            ('model_version', 'TEXT'),
            ('created_at', 'TEXT'),
        ]:
            if col not in existing:
                try:
                    c.execute(f"ALTER TABLE predictions ADD COLUMN {col} {dtype}")
                except Exception as e:
                    logger.warning(f"Could not add column {col}: {e}")

        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_predictions_time ON predictions(prediction_time DESC)
        ''')
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_predictions_checked ON predictions(checked)
        ''')
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_predictions_horizon ON predictions(horizon_min)
        ''')

        conn.commit()
        conn.close()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def save_price(self, price: float, source: str = '') -> bool:
        try:
            conn = self._conn()
            c = conn.cursor()
            c.execute(
                "INSERT INTO prices (timestamp, price, source, created_at) VALUES (?, ?, ?, ?)",
                (now_iso(), price, source, now_iso())
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"[{self.symbol}] save_price error: {e}")
            return False

    def get_prices(self, limit: Optional[int] = None,
                   since: Optional[str] = None,
                   until: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            conn = self._conn()
            c = conn.cursor()
            query = "SELECT id, timestamp, price, source FROM prices WHERE 1=1"
            params = []
            if since:
                query += " AND timestamp >= ?"
                params.append(since)
            if until:
                query += " AND timestamp <= ?"
                params.append(until)
            query += " ORDER BY timestamp ASC"
            if limit:
                query += f" LIMIT {int(limit)}"
            c.execute(query, params)
            rows = c.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"[{self.symbol}] get_prices error: {e}")
            return []

    def count_prices(self) -> int:
        try:
            conn = self._conn()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM prices")
            n = c.fetchone()[0]
            conn.close()
            return n
        except Exception as e:
            logger.error(f"[{self.symbol}] count_prices error: {e}")
            return 0

    def last_price(self) -> Optional[Tuple[float, str]]:
        try:
            conn = self._conn()
            c = conn.cursor()
            c.execute("SELECT price, timestamp FROM prices ORDER BY id DESC LIMIT 1")
            row = c.fetchone()
            conn.close()
            if row:
                return float(row['price']), row['timestamp']
            return None
        except Exception as e:
            logger.error(f"[{self.symbol}] last_price error: {e}")
            return None

    def price_at_or_after(self, target_iso: str, window_seconds: int = 60) -> Optional[Tuple[float, str]]:
        """Return the price nearest to target time (after target, within window)."""
        try:
            conn = self._conn()
            c = conn.cursor()
            c.execute(
                "SELECT price, timestamp FROM prices WHERE timestamp >= ? ORDER BY timestamp ASC LIMIT 1",
                (target_iso,)
            )
            row = c.fetchone()
            conn.close()
            if row:
                ts = row['timestamp']
                if abs(self._dt_diff_seconds(ts, target_iso)) <= window_seconds:
                    return float(row['price']), ts
            return None
        except Exception as e:
            logger.error(f"[{self.symbol}] price_at_or_after error: {e}")
            return None

    def price_at_or_before(self, target_iso: str, window_seconds: int = 60) -> Optional[Tuple[float, str]]:
        try:
            conn = self._conn()
            c = conn.cursor()
            c.execute(
                "SELECT price, timestamp FROM prices WHERE timestamp <= ? ORDER BY timestamp DESC LIMIT 1",
                (target_iso,)
            )
            row = c.fetchone()
            conn.close()
            if row:
                ts = row['timestamp']
                if abs(self._dt_diff_seconds(ts, target_iso)) <= window_seconds:
                    return float(row['price']), ts
            return None
        except Exception as e:
            logger.error(f"[{self.symbol}] price_at_or_before error: {e}")
            return None

    def _dt_diff_seconds(self, ts_a: str, ts_b: str) -> float:
        try:
            a = datetime.fromisoformat(ts_a.replace('Z', '+00:00'))
            b = datetime.fromisoformat(ts_b.replace('Z', '+00:00'))
            return abs((a - b).total_seconds())
        except Exception:
            return 1e9

    def log_prediction(self, horizon_min: int, current_price: float,
                       predicted_price: float, model_used: str,
                       model_version: str = '') -> int:
        try:
            conn = self._conn()
            c = conn.cursor()
            c.execute(
                """INSERT INTO predictions
                   (prediction_time, horizon_min, current_price, predicted_price,
                    checked, model_used, model_version, created_at)
                   VALUES (?, ?, ?, ?, 0, ?, ?, ?)""",
                (now_iso(), horizon_min, current_price, predicted_price,
                 model_used, model_version, now_iso())
            )
            pred_id = c.lastrowid
            conn.commit()
            conn.close()
            return pred_id
        except Exception as e:
            logger.error(f"[{self.symbol}] log_prediction error: {e}")
            return -1

    def get_unvalidated_predictions(self, max_age_minutes: int = 120) -> List[Dict[str, Any]]:
        """Get predictions that are ready to be validated (target time has passed)."""
        try:
            conn = self._conn()
            c = conn.cursor()
            cutoff = datetime.now(timezone.utc).isoformat()
            c.execute(
                """SELECT id, prediction_time, horizon_min, predicted_price,
                          current_price, model_used, model_version
                   FROM predictions
                   WHERE checked = 0
                   AND datetime(prediction_time, '+'||horizon_min||' minutes') <= datetime(?)
                   ORDER BY id ASC
                   LIMIT 200""",
                (cutoff,)
            )
            rows = [dict(r) for r in c.fetchall()]
            conn.close()
            return rows
        except Exception as e:
            logger.error(f"[{self.symbol}] get_unvalidated_predictions error: {e}")
            return []

    def update_prediction(self, pred_id: int, actual_price: float,
                          error: float, error_pct: float,
                          is_correct: int) -> bool:
        try:
            conn = self._conn()
            c = conn.cursor()
            c.execute(
                """UPDATE predictions
                   SET actual_price = ?, error = ?, error_pct = ?,
                       checked = 1, is_correct = ?
                   WHERE id = ?""",
                (actual_price, error, error_pct, is_correct, pred_id)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"[{self.symbol}] update_prediction error: {e}")
            return False

    def get_prediction_stats(self, window: int = 100,
                             horizon: Optional[int] = None) -> Dict[str, Any]:
        try:
            conn = self._conn()
            c = conn.cursor()
            query = """SELECT
                          COUNT(*) as n,
                          AVG(ABS(error_pct)) as avg_abs_err,
                          AVG(error_pct) as avg_err,
                          MAX(ABS(error_pct)) as max_abs_err,
                          SUM(CASE WHEN ABS(error_pct) < ? THEN 1 ELSE 0 END) as within
                       FROM predictions
                       WHERE checked = 1 AND actual_price IS NOT NULL"""
            params = [1.0]
            if horizon:
                query += " AND horizon_min = ?"
                params.append(horizon)
            query += " ORDER BY id DESC LIMIT ?"
            params.append(window)
            # NOTE: LIMIT in subquery is safer; this works on SQLite but does not limit efficiently.
            # Use subquery wrapper to limit rows before aggregating.
            wrapped = f"""SELECT
                              COUNT(*) as n,
                              AVG(ABS(error_pct)) as avg_abs_err,
                              AVG(error_pct) as avg_err,
                              MAX(ABS(error_pct)) as max_abs_err,
                              SUM(CASE WHEN ABS(error_pct) < ? THEN 1 ELSE 0 END) as within
                           FROM ({query.replace('ORDER BY id DESC LIMIT ?', 'ORDER BY id DESC LIMIT ?')}) tmp"""
            # Simpler direct:
            c.execute(
                """SELECT
                      COUNT(*),
                      AVG(ABS(error_pct)),
                      AVG(error_pct),
                      MAX(ABS(error_pct)),
                      SUM(CASE WHEN ABS(error_pct) < 1.0 THEN 1 ELSE 0 END)
                   FROM (
                       SELECT error_pct FROM predictions
                       WHERE checked = 1 AND actual_price IS NOT NULL
                       AND horizon_min = COALESCE(?, horizon_min)
                       ORDER BY id DESC LIMIT ?
                   ) tmp""",
                (horizon if horizon else 0, window)
            )
            row = c.fetchone()
            conn.close()
            n = row[0] or 0
            avg_abs = round(row[1] or 0, 4) if n else None
            avg = round(row[2] or 0, 4) if n else None
            max_abs = round(row[3] or 0, 4) if n else None
            within = row[4] or 0
            return {
                'total': n,
                'avg_abs_error_pct': avg_abs,
                'avg_error_pct': avg,
                'max_abs_error_pct': max_abs,
                'within_threshold_1pct': within,
                'accuracy_pct_1pct': round(100 * within / n, 2) if n else 0,
            }
        except Exception as e:
            logger.error(f"[{self.symbol}] get_prediction_stats error: {e}")
            return {'total': 0}

    def get_recent_predictions(self, limit: int = 50,
                               horizon: Optional[int] = None) -> List[Dict[str, Any]]:
        try:
            conn = self._conn()
            c = conn.cursor()
            query = """SELECT id, prediction_time, horizon_min, current_price,
                              predicted_price, actual_price, error_pct,
                              checked, is_correct, model_used
                       FROM predictions WHERE 1=1"""
            params = []
            if horizon:
                query += " AND horizon_min = ?"
                params.append(horizon)
            query += " ORDER BY id DESC LIMIT ?"
            params.append(limit)
            c.execute(query, params)
            rows = [dict(r) for r in c.fetchall()]
            conn.close()
            return rows
        except Exception as e:
            logger.error(f"[{self.symbol}] get_recent_predictions error: {e}")
            return []
