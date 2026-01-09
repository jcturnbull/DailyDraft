"""
Simple file-based storage for Daily Draft
Persists game completion status across browser sessions
"""
import json
import os
from pathlib import Path
from datetime import datetime
import pytz

# Storage file location
STORAGE_DIR = Path(".streamlit_data")
STORAGE_FILE = STORAGE_DIR / "completed_games.json"


def ensure_storage_dir():
    """Create storage directory if it doesn't exist"""
    STORAGE_DIR.mkdir(exist_ok=True)


def load_completed_games():
    """Load completed games from file"""
    ensure_storage_dir()

    if not STORAGE_FILE.exists():
        return {}

    try:
        with open(STORAGE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}


def save_completed_game(date_str, user_id, score, max_score, results):
    """Save a completed game"""
    ensure_storage_dir()

    completed_games = load_completed_games()

    # Store by date and user_id
    if date_str not in completed_games:
        completed_games[date_str] = {}

    completed_games[date_str][user_id] = {
        'score': score,
        'max_score': max_score,
        'results': results,
        'completed_at': datetime.now(pytz.timezone('America/Los_Angeles')).isoformat()
    }

    try:
        with open(STORAGE_FILE, 'w') as f:
            json.dump(completed_games, f, indent=2)
        return True
    except:
        return False


def get_completed_game(date_str, user_id):
    """Get a completed game for specific date and user"""
    completed_games = load_completed_games()

    if date_str in completed_games and user_id in completed_games[date_str]:
        return completed_games[date_str][user_id]

    return None


def has_completed_today(date_str, user_id):
    """Check if user completed today's challenge"""
    return get_completed_game(date_str, user_id) is not None


def cleanup_old_games(days_to_keep=7):
    """Remove games older than X days to keep file size manageable"""
    ensure_storage_dir()

    if not STORAGE_FILE.exists():
        return

    completed_games = load_completed_games()
    pacific = pytz.timezone('America/Los_Angeles')
    now = datetime.now(pacific)

    # Filter to keep only recent games
    filtered = {}
    for date_str, users in completed_games.items():
        try:
            game_date = datetime.strptime(date_str, "%Y-%m-%d")
            days_old = (now - pacific.localize(game_date.replace(tzinfo=None))).days

            if days_old <= days_to_keep:
                filtered[date_str] = users
        except:
            # Keep if we can't parse date (safety)
            filtered[date_str] = users

    try:
        with open(STORAGE_FILE, 'w') as f:
            json.dump(filtered, f, indent=2)
    except:
        pass
