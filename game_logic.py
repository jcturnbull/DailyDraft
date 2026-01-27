"""
Core game logic dispatcher for Daily Draft
Routes to sport-specific modules (NFL, MLB)
Provides unified interfaces for the Streamlit app
"""
from datetime import datetime
import pytz

from config import (
    MAX_POINTS_PER_QUESTION,
    EMOJI_THRESHOLDS,
    SPORTS
)

# Import NFL-specific functions
from game_logic_nfl import (
    generate_nfl_questions_for_round,
    get_nfl_player_stat_for_question,
    get_nfl_eligible_players,
    get_nfl_data_for_year_cached
)

# Import MLB-specific functions
from game_logic_mlb import (
    generate_mlb_questions_for_round,
    get_mlb_player_stat_for_question,
    get_mlb_eligible_players,
    get_mlb_data_for_year_cached,
    calculate_mlb_score
)

# Re-export constants for backward compatibility
QUESTIONS_PER_ROUND = SPORTS['nfl']['questions_per_round']  # Default for compatibility


def get_daily_seed_and_date():
    """
    Generates a seed based on the current Pacific Time date.
    Returns (seed_int, date_string) for consistent daily challenges.
    Resets at midnight Pacific Time.
    """
    pacific = pytz.timezone('America/Los_Angeles')
    now_pt = datetime.now(pacific)
    date_str = now_pt.strftime("%Y-%m-%d")
    seed_str = now_pt.strftime("%Y%m%d")
    return int(seed_str), date_str


def get_questions_per_round(sport):
    """Get the number of questions per round for a sport"""
    return SPORTS.get(sport, {}).get('questions_per_round', 5)


def generate_questions_for_round(data_cache, sport="nfl", daily_mode=True, daily_seed=None):
    """
    Generate questions for a round, dispatching to the appropriate sport module.

    Args:
        data_cache: Dict for caching loaded data
        sport: "nfl" or "mlb"
        daily_mode: If True, use deterministic seed for daily challenge
        daily_seed: Seed for deterministic generation

    Returns:
        List of question objects
    """
    if sport == "nfl":
        return generate_nfl_questions_for_round(data_cache, daily_mode, daily_seed)
    elif sport == "mlb":
        return generate_mlb_questions_for_round(data_cache, daily_mode, daily_seed)
    else:
        raise ValueError(f"Unknown sport: {sport}")


def get_player_stat_for_question(guessed_player_id, question_data, data_cache, sport="nfl"):
    """
    Retrieve stat value for a guessed player, dispatching to appropriate sport module.

    Args:
        guessed_player_id: Player ID that was guessed
        question_data: Question dict containing year, stat_category, etc.
        data_cache: Dict for caching loaded data
        sport: "nfl" or "mlb"

    Returns:
        Numeric stat value
    """
    if sport == "nfl":
        return get_nfl_player_stat_for_question(guessed_player_id, question_data, data_cache)
    elif sport == "mlb":
        return get_mlb_player_stat_for_question(guessed_player_id, question_data, data_cache)
    else:
        raise ValueError(f"Unknown sport: {sport}")


def get_eligible_players_for_autocomplete(position, year, data_cache, sport="nfl"):
    """
    Get list of eligible players for autocomplete, dispatching to appropriate sport module.

    Args:
        position: Position label (e.g., "QB", "WR", "C", "SP")
        year: Season year
        data_cache: Dict for caching loaded data
        sport: "nfl" or "mlb"

    Returns:
        List of (display_name, player_id) tuples
    """
    if sport == "nfl":
        return get_nfl_eligible_players(position, year, data_cache)
    elif sport == "mlb":
        return get_mlb_eligible_players(position, year, data_cache)
    else:
        raise ValueError(f"Unknown sport: {sport}")


def get_data_for_year_cached(year, data_cache, sport="nfl"):
    """
    Get cached data for a year, dispatching to appropriate sport module.

    Args:
        year: Season year
        data_cache: Dict for caching loaded data
        sport: "nfl" or "mlb"

    Returns:
        Sport-specific data tuple
    """
    if sport == "nfl":
        return get_nfl_data_for_year_cached(year, data_cache)
    elif sport == "mlb":
        return get_mlb_data_for_year_cached(year, data_cache)
    else:
        raise ValueError(f"Unknown sport: {sport}")


def calculate_score_emojis_and_points(guessed_stat, correct_stat, is_inverted=False, worst_stat=None):
    """
    Calculates score based on how close the guess is to the correct answer.
    Supports inverted scoring for stats like ERA where lower is better.

    Args:
        guessed_stat: The guessed player's stat value
        correct_stat: The correct (leader's) stat value
        is_inverted: If True, use inverted scoring (lower is better)
        worst_stat: For inverted stats, the worst value among qualified players

    Returns:
        (emoji_string, points_earned)
    """
    # For inverted stats, use MLB scoring logic
    if is_inverted and worst_stat is not None:
        percentage, points = calculate_mlb_score(guessed_stat, correct_stat, is_inverted, worst_stat)
    else:
        # Standard scoring logic
        try:
            guessed = float(guessed_stat) if guessed_stat is not None else 0.0
        except:
            guessed = 0.0

        try:
            correct = float(correct_stat) if correct_stat is not None else 0.0
        except:
            return ("⬛⬛⬛⬛⬛", 0) if guessed != 0 else ("🟩🟩🟩🟩🟩", MAX_POINTS_PER_QUESTION)

        if correct == 0:
            if guessed == 0:
                percentage = 100.0
                points = MAX_POINTS_PER_QUESTION
            else:
                percentage = 0.0
                points = 0
        else:
            raw_percentage = (guessed / correct) * 100.0
            percentage = min(max(0.0, raw_percentage), 100.0)
            points = round(percentage * (MAX_POINTS_PER_QUESTION / 100.0))

    # Determine emoji based on percentage
    emojis = "⬛⬛⬛⬛⬛"
    for threshold, emoji_str in sorted(EMOJI_THRESHOLDS.items(), reverse=True):
        if percentage >= threshold:
            emojis = emoji_str
            break

    # Handle edge case: 0 guess when answer is non-zero
    if percentage == 0:
        emojis = "⬛⬛⬛⬛⬛"

    return emojis, int(points)


def format_share_text(results, questions, total_score, game_date, sport="nfl", app_url=None):
    """
    Formats results in a shareable format (like Wordle).

    Args:
        results: Dict of question results
        questions: List of question data
        total_score: Total points scored
        game_date: Date string for the game
        sport: "nfl" or "mlb"
        app_url: Optional URL to include

    Returns:
        Formatted share text string
    """
    sport_config = SPORTS.get(sport, SPORTS['nfl'])
    sport_name = sport_config['name']
    sport_icon = sport_config['icon']

    lines = [f"Daily Draft {sport_icon} {sport_name} Trivia {game_date}"]
    lines.append(f"Score: {total_score:,}")
    lines.append("")

    for i, q_data in enumerate(questions):
        result = results.get(i)
        if result:
            lines.append(result.get('emojis', '⬛⬛⬛⬛⬛'))

    if app_url:
        lines.append("")
        lines.append(app_url)

    return "\n".join(lines)


def format_combined_share_text(all_results, game_date, app_url=None):
    """
    Format combined results from multiple sports for sharing.

    Args:
        all_results: Dict with sport keys containing {score, results, questions}
        game_date: Date string for the game
        app_url: Optional URL to include

    Returns:
        Formatted share text string
    """
    lines = [f"Daily Draft {game_date}"]
    lines.append("")

    total_combined = 0

    for sport in ['nfl', 'mlb']:
        if sport in all_results:
            sport_data = all_results[sport]
            sport_config = SPORTS.get(sport)
            icon = sport_config['icon']
            name = sport_config['name']

            score = sport_data.get('score', 0)
            total_combined += score

            lines.append(f"{icon} {name}: {score:,}")

            results = sport_data.get('results', {})
            questions = sport_data.get('questions', [])

            for i in range(len(questions)):
                result = results.get(i) or results.get(str(i))
                if result:
                    lines.append(result.get('emojis', '⬛⬛⬛⬛⬛'))

            lines.append("")

    lines.append(f"Total: {total_combined:,}")

    if app_url:
        lines.append("")
        lines.append(app_url)

    return "\n".join(lines)
