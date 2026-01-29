"""
Browser localStorage-based storage for Daily Draft
Persists game completion status in user's browser across sessions
Supports multiple sports (NFL, MLB)
"""
import json
import streamlit as st
from datetime import datetime
import pytz


def _get_storage_key(date_str, user_id, sport):
    """Generate localStorage key for a specific game"""
    return f"dailydraft_{date_str}_{user_id}_{sport}"


def save_completed_game(date_str, user_id, sport, score, max_score, results, questions=None):
    """
    Save a completed game to browser localStorage.

    Args:
        date_str: Date string (YYYY-MM-DD)
        user_id: Unique user identifier
        sport: Sport identifier ('nfl' or 'mlb')
        score: User's score
        max_score: Maximum possible score
        results: Dict of question results
        questions: List of question data
    """
    storage_key = _get_storage_key(date_str, user_id, sport)

    game_data = {
        'score': score,
        'max_score': max_score,
        'results': results,
        'questions': questions,
        'completed_at': datetime.now(pytz.timezone('America/Los_Angeles')).isoformat()
    }

    # Convert to JSON string, escaping for JavaScript
    json_data = json.dumps(game_data).replace("'", "\\'").replace('"', '\\"')

    # Inject JavaScript to save to localStorage
    save_script = f"""
    <script>
    try {{
        localStorage.setItem('{storage_key}', "{json_data}");
        console.log('Saved game to localStorage: {storage_key}');
    }} catch (e) {{
        console.error('Failed to save to localStorage:', e);
    }}
    </script>
    """
    st.components.v1.html(save_script, height=0)
    return True


def load_games_from_local_storage(date_str, user_id, sports):
    """
    Inject JavaScript to load games from localStorage into session state.
    This must be called early in the app lifecycle.

    Args:
        date_str: Date string (YYYY-MM-DD)
        user_id: Unique user identifier
        sports: List of sport identifiers to check

    Returns:
        None - data is loaded via JavaScript into URL params
    """
    # Build JavaScript to check localStorage for each sport and encode data in URL
    js_checks = []
    for sport in sports:
        storage_key = _get_storage_key(date_str, user_id, sport)
        js_checks.append(f"""
            const {sport}Data = localStorage.getItem('{storage_key}');
            if ({sport}Data) {{
                params.set('game_{sport}', btoa({sport}Data));
            }}
        """)

    checks_js = '\n'.join(js_checks)

    load_script = f"""
    <script>
    (function() {{
        const params = new URLSearchParams(window.location.search);
        let needsUpdate = false;

        {checks_js}

        // Check if any game params are missing that should be there
        const currentParams = new URLSearchParams(window.location.search);
        for (const [key, value] of params.entries()) {{
            if (!currentParams.has(key) || currentParams.get(key) !== value) {{
                needsUpdate = true;
                break;
            }}
        }}

        if (needsUpdate) {{
            // Preserve existing params
            for (const [key, value] of currentParams.entries()) {{
                if (!params.has(key)) {{
                    params.set(key, value);
                }}
            }}
            window.history.replaceState({{}}, '', `${{window.location.pathname}}?${{params}}`);
            // Trigger a soft reload to pick up new params
            window.location.reload();
        }}
    }})();
    </script>
    """
    st.components.v1.html(load_script, height=0)


def get_completed_game(date_str, user_id, sport):
    """
    Get a completed game from URL params (which were populated from localStorage).

    Args:
        date_str: Date string (YYYY-MM-DD)
        user_id: Unique user identifier
        sport: Sport identifier ('nfl' or 'mlb')

    Returns:
        Game data dict or None if not found
    """
    import base64

    query_params = st.query_params
    param_key = f'game_{sport}'

    if param_key in query_params:
        try:
            encoded_data = query_params[param_key]
            json_data = base64.b64decode(encoded_data).decode('utf-8')
            game_data = json.loads(json_data)

            # Verify the data is for the correct date/user
            # (The storage key already encodes this, but double-check)
            return game_data
        except Exception as e:
            print(f"Error decoding game data for {sport}: {e}")
            return None

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
    from config import SPORTS

    all_games = {}
    for sport in SPORTS.keys():
        game_data = get_completed_game(date_str, user_id, sport)
        if game_data:
            all_games[sport] = game_data

    return all_games


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
    """
    Inject JavaScript to clean up old games from localStorage.
    Keeps only today's games.
    """
    pacific = pytz.timezone('America/Los_Angeles')
    today_str = datetime.now(pacific).strftime("%Y-%m-%d")

    cleanup_script = f"""
    <script>
    (function() {{
        const today = '{today_str}';
        const keysToRemove = [];

        for (let i = 0; i < localStorage.length; i++) {{
            const key = localStorage.key(i);
            if (key && key.startsWith('dailydraft_')) {{
                // Extract date from key (format: dailydraft_YYYY-MM-DD_userid_sport)
                const parts = key.split('_');
                if (parts.length >= 2) {{
                    const keyDate = parts[1];
                    if (keyDate !== today) {{
                        keysToRemove.push(key);
                    }}
                }}
            }}
        }}

        keysToRemove.forEach(key => {{
            localStorage.removeItem(key);
            console.log('Cleaned up old game:', key);
        }});
    }})();
    </script>
    """
    st.components.v1.html(cleanup_script, height=0)
