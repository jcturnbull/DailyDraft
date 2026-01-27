"""
Simple file-based storage for Daily Draft
Persists game completion status across browser sessions
Supports multiple sports (NFL, MLB)
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


def _migrate_old_format(user_data):
    """
    Migrate old single-sport format to new multi-sport format.
    Old: {score, max_score, results, questions, completed_at}
    New: {nfl: {...}, mlb: {...}}
    """
    # Check if this is old format (has 'score' at top level instead of sport key)
    if 'score' in user_data and 'nfl' not in user_data and 'mlb' not in user_data:
        # Migrate to new format - assume old data is NFL
        return {'nfl': user_data}
    return user_data


def save_completed_game(date_str, user_id, sport, score, max_score, results, questions=None):
    """
    Save a completed game for a specific sport.

    Args:
        date_str: Date string (YYYY-MM-DD)
        user_id: Unique user identifier
        sport: Sport identifier ('nfl' or 'mlb')
        score: User's score
        max_score: Maximum possible score
        results: Dict of question results
        questions: List of question data
    """
    ensure_storage_dir()

    completed_games = load_completed_games()

    # Initialize nested structure
    if date_str not in completed_games:
        completed_games[date_str] = {}

    if user_id not in completed_games[date_str]:
        completed_games[date_str][user_id] = {}
    else:
        # Migrate old format if needed
        completed_games[date_str][user_id] = _migrate_old_format(
            completed_games[date_str][user_id]
        )

    # Store by sport
    completed_games[date_str][user_id][sport] = {
        'score': score,
        'max_score': max_score,
        'results': results,
        'questions': questions,
        'completed_at': datetime.now(pytz.timezone('America/Los_Angeles')).isoformat()
    }

    try:
        with open(STORAGE_FILE, 'w') as f:
            json.dump(completed_games, f, indent=2)
        return True
    except:
        return False


def get_completed_game(date_str, user_id, sport):
    """
    Get a completed game for specific date, user, and sport.

    Args:
        date_str: Date string (YYYY-MM-DD)
        user_id: Unique user identifier
        sport: Sport identifier ('nfl' or 'mlb')

    Returns:
        Game data dict or None if not found
    """
    completed_games = load_completed_games()

    if date_str in completed_games and user_id in completed_games[date_str]:
        user_data = _migrate_old_format(completed_games[date_str][user_id])
        return user_data.get(sport)

    return None


def get_all_completed_games(date_str, user_id):
    """
    Get all completed games for a specific date and user (all sports).

    Args:
        date_str: Date string (YYYY-MM-DD)
        user_id: Unique user identifier

    Returns:
        Dict with sport keys and game data values, or empty dict
    """
    completed_games = load_completed_games()

    if date_str in completed_games and user_id in completed_games[date_str]:
        user_data = _migrate_old_format(completed_games[date_str][user_id])
        return user_data

    return {}


def has_completed_today(date_str, user_id, sport):
    """
    Check if user completed today's challenge for a specific sport.

    Args:
        date_str: Date string (YYYY-MM-DD)
        user_id: Unique user identifier
        sport: Sport identifier ('nfl' or 'mlb')
    """
    return get_completed_game(date_str, user_id, sport) is not None


def cleanup_old_games():
    """Remove all games except today's to keep file minimal"""
    ensure_storage_dir()

    if not STORAGE_FILE.exists():
        return

    completed_games = load_completed_games()
    pacific = pytz.timezone('America/Los_Angeles')
    today_str = datetime.now(pacific).strftime("%Y-%m-%d")

    # Keep only today's games
    filtered = {}
    if today_str in completed_games:
        filtered[today_str] = completed_games[today_str]

    try:
        with open(STORAGE_FILE, 'w') as f:
            json.dump(filtered, f, indent=2)
    except:
        pass
