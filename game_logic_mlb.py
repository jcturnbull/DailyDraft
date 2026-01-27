"""
MLB-specific game logic for Daily Draft
Handles MLB question generation, scoring, and player selection
"""
import random
import pandas as pd
from datetime import datetime, timezone

from config import (
    MLB_QUESTION_SLOTS,
    MLB_BATTER_STATS,
    MLB_PITCHER_STATS,
    MLB_INVERTED_STATS,
    MAX_POINTS_PER_QUESTION,
    SPORTS
)
from load_mlb_data import (
    load_mlb_data_for_year,
    get_players_by_league,
    get_stat_leader_mlb
)

# Global cache for daily questions
_MLB_DAILY_QUESTIONS_CACHE = {}

# MLB configuration
MLB_CONFIG = SPORTS['mlb']
MLB_MIN_YEAR = MLB_CONFIG['min_year']
MLB_MAX_YEAR = MLB_CONFIG['max_year']
MLB_QUESTIONS_PER_ROUND = MLB_CONFIG['questions_per_round']


def get_mlb_data_for_year_cached(year, data_cache):
    """Retrieves or loads MLB data for a given year using cache."""
    cache_key = f"mlb_{year}"
    if cache_key not in data_cache:
        try:
            data_tuple = load_mlb_data_for_year(year)
            if data_tuple[0].empty and data_tuple[1].empty:
                data_cache[cache_key] = (pd.DataFrame(), pd.DataFrame())
            else:
                data_cache[cache_key] = data_tuple
        except Exception as e:
            print(f"Error loading MLB data for year {year}: {e}")
            data_cache[cache_key] = (pd.DataFrame(), pd.DataFrame())

    return data_cache[cache_key]


def select_random_mlb_year(min_year=MLB_MIN_YEAR, max_year=MLB_MAX_YEAR):
    """Selects a year for a question, ensuring complete season data."""
    current_datetime = pd.Timestamp.now(timezone.utc)

    # Before April, use previous year; after October, can use current year
    if current_datetime.month < 4:
        actual_max_year = min(max_year, current_datetime.year - 1)
    elif current_datetime.month > 10:
        actual_max_year = min(max_year, current_datetime.year)
    else:
        actual_max_year = min(max_year, current_datetime.year - 1)

    if min_year > actual_max_year:
        return actual_max_year

    return random.randint(min_year, actual_max_year)


def generate_mlb_questions_for_round(data_cache, daily_mode=True, daily_seed=None):
    """Generates questions for an MLB round."""
    # Check cache for daily mode
    if daily_mode and daily_seed is not None:
        cache_key = f"mlb_daily_{daily_seed}"
        if cache_key in _MLB_DAILY_QUESTIONS_CACHE:
            print(f"Using cached MLB daily questions for seed {daily_seed}")
            return _MLB_DAILY_QUESTIONS_CACHE[cache_key]

        print(f"Generating new MLB daily questions for seed {daily_seed}")
        random.seed(daily_seed)

    questions = []
    used_stats = {"batter": set(), "pitcher": set()}

    for slot_info in MLB_QUESTION_SLOTS:
        slot = slot_info["slot"]
        league = slot_info["league"]
        player_type = slot_info["type"]

        question_year = select_random_mlb_year()
        batters_df, pitchers_df = get_mlb_data_for_year_cached(question_year, data_cache)

        if player_type == "batter":
            question = _generate_batter_question(slot, league, question_year, batters_df, used_stats["batter"])
        else:
            question = _generate_pitcher_question(slot, league, question_year, pitchers_df, used_stats["pitcher"])

        questions.append(question)

    # Cache for daily mode
    if daily_mode and daily_seed is not None:
        cache_key = f"mlb_daily_{daily_seed}"
        _MLB_DAILY_QUESTIONS_CACHE[cache_key] = questions
        print(f"Cached MLB daily questions for seed {daily_seed}")

    return questions


def _generate_batter_question(slot, league, year, batters_df, used_stats):
    """Generate a question for batters in a specific league."""
    if batters_df.empty or 'player_id' not in batters_df.columns:
        return _create_error_question(slot, year, f"Batting data unavailable for {league}")

    # Filter to this league
    league_df = get_players_by_league(batters_df, league)

    if league_df.empty:
        return _create_error_question(slot, year, f"No {league} batters found")

    # Select a stat (try to avoid repeats)
    available_stats = [s for s in MLB_BATTER_STATS if s not in used_stats]
    if not available_stats:
        available_stats = MLB_BATTER_STATS

    selected_stat = random.choice(available_stats)
    used_stats.add(selected_stat)

    is_inverted = selected_stat in MLB_INVERTED_STATS

    # Generate question text
    stat_display = _format_stat_name(selected_stat)
    league_name = "American League" if league == "AL" else "National League"

    if is_inverted:
        question_text = f"Which {league_name} batter had the lowest {stat_display} in {year}?"
    else:
        question_text = f"Which {league_name} batter had the most {stat_display} in {year}?"

    # Find the stat leader
    leader_info = get_stat_leader_mlb(league_df, selected_stat, inverted=is_inverted)

    if not leader_info:
        return _create_error_question(slot, year, f"Could not find {selected_stat} leader in {league}")

    return {
        'position_slot': slot,
        'question_text': question_text,
        'stat_category': selected_stat,
        'year': year,
        'league': league,
        'player_type': 'batter',
        'correct_player_id': leader_info['player_id'],
        'correct_player_name': leader_info['player_name'],
        'correct_stat_value': leader_info['stat_value'],
        'worst_stat_value': leader_info['worst_stat_value'] if is_inverted else None,
        'is_inverted': is_inverted,
        'data_issue': False
    }


def _generate_pitcher_question(slot, league, year, pitchers_df, used_stats):
    """Generate a question for pitchers in a specific league."""
    if pitchers_df.empty or 'player_id' not in pitchers_df.columns:
        return _create_error_question(slot, year, f"Pitching data unavailable for {league}")

    # Filter to this league
    league_df = get_players_by_league(pitchers_df, league)

    if league_df.empty:
        return _create_error_question(slot, year, f"No {league} pitchers found")

    # Select a stat (try to avoid repeats)
    available_stats = [s for s in MLB_PITCHER_STATS if s not in used_stats]
    if not available_stats:
        available_stats = MLB_PITCHER_STATS

    selected_stat = random.choice(available_stats)
    used_stats.add(selected_stat)

    is_inverted = selected_stat in MLB_INVERTED_STATS

    # Generate question text
    stat_display = _format_stat_name(selected_stat)
    league_name = "American League" if league == "AL" else "National League"

    if is_inverted:
        question_text = f"Which {league_name} pitcher had the lowest {stat_display} in {year}?"
    else:
        question_text = f"Which {league_name} pitcher had the most {stat_display} in {year}?"

    # Find the stat leader
    leader_info = get_stat_leader_mlb(league_df, selected_stat, inverted=is_inverted)

    if not leader_info:
        return _create_error_question(slot, year, f"Could not find {selected_stat} leader in {league}")

    return {
        'position_slot': slot,
        'question_text': question_text,
        'stat_category': selected_stat,
        'year': year,
        'league': league,
        'player_type': 'pitcher',
        'correct_player_id': leader_info['player_id'],
        'correct_player_name': leader_info['player_name'],
        'correct_stat_value': leader_info['stat_value'],
        'worst_stat_value': leader_info['worst_stat_value'] if is_inverted else None,
        'is_inverted': is_inverted,
        'data_issue': False
    }


def _create_error_question(slot, year, error_message):
    """Create an error question object."""
    return {
        'position_slot': slot,
        'question_text': f"{error_message} (Year: {year}).",
        'stat_category': None,
        'year': year,
        'league': None,
        'player_type': None,
        'correct_player_id': None,
        'correct_player_name': None,
        'correct_stat_value': None,
        'worst_stat_value': None,
        'is_inverted': False,
        'data_issue': True
    }


def _format_stat_name(stat):
    """Format stat name for display."""
    stat_names = {
        'HR': 'home runs',
        'RBI': 'RBIs',
        'H': 'hits',
        'R': 'runs',
        'AVG': 'batting average',
        'OPS': 'OPS',
        'SB': 'stolen bases',
        'W': 'wins',
        'SO': 'strikeouts',
        'SV': 'saves',
        'ERA': 'ERA',
        'IP': 'innings pitched',
        'WHIP': 'WHIP'
    }
    return stat_names.get(stat, stat)


def calculate_mlb_score(guessed_stat, correct_stat, is_inverted=False, worst_stat=None):
    """
    Calculate score for MLB stats, including inverted scoring for ERA/WHIP.

    For normal stats: Score = (guessed / correct) * 10000
    For inverted stats: Best value = 10000, worst = 0, linear scale
    """
    try:
        guessed = float(guessed_stat) if guessed_stat is not None else 0.0
    except:
        guessed = 0.0

    try:
        correct = float(correct_stat) if correct_stat is not None else 0.0
    except:
        return (0.0, 0)

    if is_inverted and worst_stat is not None:
        try:
            worst = float(worst_stat)
        except:
            return (0.0, 0)

        best = correct

        if worst == best:
            return (100.0, MAX_POINTS_PER_QUESTION) if guessed == best else (0.0, 0)

        range_val = worst - best

        if guessed <= best:
            return (100.0, MAX_POINTS_PER_QUESTION)

        if guessed >= worst:
            return (0.0, 0)

        distance = guessed - best
        percentage = (1 - (distance / range_val)) * 100.0
        points = int(percentage * (MAX_POINTS_PER_QUESTION / 100.0))

        return (percentage, points)

    else:
        if correct == 0:
            return (100.0, MAX_POINTS_PER_QUESTION) if guessed == 0 else (0.0, 0)

        raw_percentage = (guessed / correct) * 100.0
        percentage = min(max(0.0, raw_percentage), 100.0)
        points = int(percentage * (MAX_POINTS_PER_QUESTION / 100.0))

        return (percentage, points)


def get_mlb_player_stat_for_question(guessed_player_id, question_data, data_cache):
    """Retrieves the stat value for a guessed player."""
    question_year = question_data['year']
    stat_category = question_data['stat_category']
    player_type = question_data.get('player_type', 'batter')

    batters_df, pitchers_df = get_mlb_data_for_year_cached(question_year, data_cache)

    df = pitchers_df if player_type == 'pitcher' else batters_df

    if df.empty or 'player_id' not in df.columns:
        return 0

    player_row = df[df['player_id'] == str(guessed_player_id)]

    if not player_row.empty and stat_category in player_row.columns:
        stat_value = player_row.iloc[0][stat_category]
        try:
            return pd.to_numeric(stat_value)
        except:
            return 0

    return 0


def get_mlb_eligible_players(position_slot, year, data_cache):
    """
    Gets list of eligible MLB players for a question.
    Position slot format: "AL_BAT", "NL_BAT", "AL_PIT", "NL_PIT"
    """
    batters_df, pitchers_df = get_mlb_data_for_year_cached(year, data_cache)

    # Parse the slot to get league and type
    parts = position_slot.split('_')
    if len(parts) != 2:
        return [(f"Invalid position slot: {position_slot}", None)]

    league = parts[0]  # "AL" or "NL"
    player_type = parts[1]  # "BAT" or "PIT"

    if player_type == "BAT":
        df = get_players_by_league(batters_df, league)
    else:
        df = get_players_by_league(pitchers_df, league)

    if df.empty or 'player_id' not in df.columns:
        type_name = "batters" if player_type == "BAT" else "pitchers"
        return [(f"No {league} {type_name} found for {year}", None)]

    # Remove duplicates
    df = df.drop_duplicates(subset=['player_id'], keep='first')

    # Format player names
    def format_player_name(row):
        name = row.get('player_name', 'Unknown')
        team = row.get('team', '')

        # Try to format as "Last, First (TEAM)"
        if name and ' ' in name:
            parts = name.split(' ', 1)
            if len(parts) == 2:
                name = f"{parts[1]}, {parts[0]}"

        if team:
            name = f"{name} ({team})"

        return name

    df = df.copy()
    df['display_name'] = df.apply(format_player_name, axis=1)
    df = df.sort_values(by='display_name')

    eligible_list = [
        (row['display_name'], row['player_id'])
        for _, row in df.iterrows()
    ]

    return eligible_list if eligible_list else [(f"No eligible players for {year}", None)]
