"""
NFL-specific game logic for Daily Draft
Handles NFL question generation, scoring, and player selection
"""
import random
import pandas as pd
from datetime import datetime, timezone

from config import (
    NFL_POSITIONS_FOR_DRAFT,
    NFL_STAT_CATEGORIES,
    MAX_POINTS_PER_QUESTION,
    SPORTS
)
from load_nfl_data import load_data_for_year

# Global cache for daily questions (shared across all users)
_NFL_DAILY_QUESTIONS_CACHE = {}

# NFL configuration from config
NFL_CONFIG = SPORTS['nfl']
NFL_MIN_YEAR = NFL_CONFIG['min_year']
NFL_MAX_YEAR = NFL_CONFIG['max_year']
NFL_QUESTIONS_PER_ROUND = NFL_CONFIG['questions_per_round']


def get_nfl_data_for_year_cached(year, data_cache):
    """
    Retrieves or loads NFL data for a given year using cache.
    Returns tuple: (rosters_df, stats_with_position_df, seasonal_snap_counts_df, raw_snap_counts_df)
    """
    cache_key = f"nfl_{year}"
    if cache_key not in data_cache:
        try:
            data_tuple = load_data_for_year(year)
            if data_tuple[0].empty or data_tuple[1].empty:
                data_cache[cache_key] = (pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
            else:
                data_cache[cache_key] = data_tuple
        except Exception as e:
            print(f"Error loading NFL data for year {year}: {e}")
            data_cache[cache_key] = (pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())

    cached_data = data_cache[cache_key]
    if cached_data[0].empty or cached_data[1].empty:
        return (pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())

    return cached_data


def select_random_nfl_year(min_year=NFL_MIN_YEAR, max_year=NFL_MAX_YEAR):
    """
    Selects a year for a question.
    Adjusts max_year to be the last fully completed season.
    """
    current_datetime = pd.Timestamp.now(timezone.utc)

    # Before September, use previous year; otherwise current year
    if current_datetime.month < 9:
        actual_max_year = min(max_year, current_datetime.year - 1)
    else:
        actual_max_year = min(max_year, current_datetime.year)

    if min_year > actual_max_year:
        return actual_max_year

    return random.randint(min_year, actual_max_year)


def get_nfl_stat_leader(stat_df, stat_column):
    """
    Finds the player with the highest value for a given stat.
    Returns dict with player_id and stat_value, or None if not found.
    """
    if stat_df.empty or stat_column not in stat_df.columns or 'player_id' not in stat_df.columns:
        return None

    try:
        df_copy = stat_df.copy()
        df_copy[stat_column] = pd.to_numeric(df_copy[stat_column], errors='coerce')
        df_copy = df_copy.dropna(subset=[stat_column])

        if df_copy.empty:
            return None

        leader_idx = df_copy[stat_column].idxmax()
        leader = df_copy.loc[leader_idx]

        return {
            'player_id': leader['player_id'],
            'stat_value': leader[stat_column]
        }
    except Exception as e:
        print(f"Error finding stat leader for {stat_column}: {e}")
        return None


def generate_nfl_questions_for_round(data_cache, daily_mode=True, daily_seed=None):
    """
    Generates questions for an NFL round.
    If daily_mode=True, uses daily_seed for deterministic questions.
    Questions are cached globally for daily mode.
    """
    # Check cache for daily mode
    if daily_mode and daily_seed is not None:
        cache_key = f"nfl_daily_{daily_seed}"
        if cache_key in _NFL_DAILY_QUESTIONS_CACHE:
            print(f"Using cached NFL daily questions for seed {daily_seed}")
            return _NFL_DAILY_QUESTIONS_CACHE[cache_key]

        print(f"Generating new NFL daily questions for seed {daily_seed}")
        random.seed(daily_seed)

    questions = []
    used_wr_year_stats = set()  # Ensures WR questions are unique

    for slot in NFL_POSITIONS_FOR_DRAFT:
        question_year = select_random_nfl_year()

        # Load data for this question's year
        rosters_df, stats_with_position_df, _, _ = get_nfl_data_for_year_cached(question_year, data_cache)

        # Check for data issues
        if stats_with_position_df.empty or 'position' not in stats_with_position_df.columns:
            questions.append({
                'position_slot': slot,
                'question_text': f"Data unavailable for {slot} (Year: {question_year}).",
                'stat_category': None,
                'year': question_year,
                'correct_player_id': None,
                'correct_player_name': None,
                'correct_stat_value': None,
                'is_inverted': False,
                'data_issue': True
            })
            continue

        # Determine position and possible stats
        actual_position = slot.rstrip('12')  # WR1 -> WR, WR2 -> WR
        possible_stats = NFL_STAT_CATEGORIES.get(actual_position, [])

        if not possible_stats:
            continue

        # Select stat (ensure uniqueness for WRs)
        selected_stat = None
        attempts = 0
        max_attempts = len(possible_stats) * 3

        if actual_position == "WR":
            while attempts < max_attempts:
                stat_candidate = random.choice(possible_stats)
                if (question_year, stat_candidate) not in used_wr_year_stats:
                    selected_stat = stat_candidate
                    used_wr_year_stats.add((question_year, selected_stat))
                    break
                attempts += 1

            if selected_stat is None:
                selected_stat = random.choice(possible_stats)
        else:
            selected_stat = random.choice(possible_stats)

        # Generate question text
        question_text = f"Who had the most {selected_stat.replace('_', ' ')} in {question_year} for {actual_position}s?"

        # Find the stat leader
        position_filter_map = {'QB': 'QB', 'RB': 'RB', 'WR': 'WR', 'TE': 'TE'}
        target_pos = position_filter_map.get(actual_position)
        leader_info = None

        if target_pos and not stats_with_position_df.empty:
            relevant_stats = stats_with_position_df[stats_with_position_df['position'] == target_pos]
            if not relevant_stats.empty:
                leader_info = get_nfl_stat_leader(relevant_stats, selected_stat)

        # Get player name from roster
        player_name = "Unknown"
        if leader_info and not rosters_df.empty:
            if 'player_id' in rosters_df.columns and 'player_name' in rosters_df.columns:
                player_record = rosters_df[rosters_df['player_id'] == leader_info['player_id']]
                if not player_record.empty:
                    player_name = player_record.iloc[0]['player_name']

        # Create question object
        questions.append({
            'position_slot': slot,
            'question_text': question_text,
            'stat_category': selected_stat,
            'year': question_year,
            'correct_player_id': leader_info.get('player_id') if leader_info else None,
            'correct_player_name': player_name if leader_info else "N/A",
            'correct_stat_value': leader_info.get('stat_value') if leader_info else None,
            'is_inverted': False,
            'data_issue': False if leader_info else True
        })

    # Cache the questions for daily mode
    if daily_mode and daily_seed is not None:
        cache_key = f"nfl_daily_{daily_seed}"
        _NFL_DAILY_QUESTIONS_CACHE[cache_key] = questions
        print(f"Cached NFL daily questions for seed {daily_seed}")

    return questions


def get_nfl_player_stat_for_question(guessed_player_id, question_data, data_cache):
    """
    Retrieves the stat value for a guessed player for a specific question.
    """
    question_year = question_data['year']
    stat_category = question_data['stat_category']

    _, stats_with_position_df, _, _ = get_nfl_data_for_year_cached(question_year, data_cache)

    if stats_with_position_df.empty or 'player_id' not in stats_with_position_df.columns:
        return 0

    player_stat_row = stats_with_position_df[stats_with_position_df['player_id'] == guessed_player_id]

    if not player_stat_row.empty and stat_category in player_stat_row.columns:
        stat_value = player_stat_row.iloc[0][stat_category]
        try:
            return pd.to_numeric(stat_value)
        except:
            return 0

    return 0


def get_nfl_eligible_players(position_label, year, data_cache):
    """
    Gets list of eligible NFL players for a given position and year.
    Players must have played snaps or had relevant stats.
    Returns list of tuples: [(display_name, player_id), ...]
    """
    rosters_df, stats_with_position_df, seasonal_snap_counts_df, _ = get_nfl_data_for_year_cached(year, data_cache)

    # Validate data availability
    if rosters_df.empty or 'player_id' not in rosters_df.columns:
        return [("No roster data available", None)]

    if 'position' not in rosters_df.columns or 'player_name' not in rosters_df.columns:
        return [("Incomplete roster data", None)]

    # Filter roster by position
    position_roster = rosters_df[rosters_df['position'] == position_label].copy()

    if position_roster.empty:
        return [(f"No {position_label}s found in roster for {year}", None)]

    # Merge with stats
    if not stats_with_position_df.empty and 'player_id' in stats_with_position_df.columns:
        position_roster = pd.merge(
            position_roster,
            stats_with_position_df,
            on='player_id',
            how='left',
            suffixes=('', '_stats')
        )

    # Merge with snap counts
    if not seasonal_snap_counts_df.empty and 'player_id' in seasonal_snap_counts_df.columns:
        seasonal_snap_counts_df['player_id'] = seasonal_snap_counts_df['player_id'].astype(str)
        position_roster['player_id'] = position_roster['player_id'].astype(str)
        position_roster = pd.merge(
            position_roster,
            seasonal_snap_counts_df[['player_id', 'offense_snaps']],
            on='player_id',
            how='left'
        )
        position_roster['offense_snaps'] = position_roster['offense_snaps'].fillna(0)
    else:
        position_roster['offense_snaps'] = 0

    # Apply position-specific eligibility criteria
    if position_label in ['WR', 'TE']:
        position_roster['targets'] = position_roster.get('targets', pd.Series(0)).fillna(0)
        active_players_df = position_roster[
            (position_roster['targets'] > 0) | (position_roster['offense_snaps'] > 0)
        ]
    elif position_label == 'RB':
        position_roster['carries'] = position_roster.get('carries', pd.Series(0)).fillna(0)
        active_players_df = position_roster[
            (position_roster['carries'] > 0) | (position_roster['offense_snaps'] > 0)
        ]
    elif position_label == 'QB':
        position_roster['attempts'] = position_roster.get('attempts', pd.Series(0)).fillna(0)
        active_players_df = position_roster[
            (position_roster['attempts'] > 0) | (position_roster['offense_snaps'] > 0)
        ]
    else:
        active_players_df = position_roster

    if active_players_df.empty:
        return [(f"No active {position_label}s found for {year}", None)]

    # Remove duplicates
    active_players_df = active_players_df.drop_duplicates(subset=['player_id'], keep='first')

    # Format player names as "Last, First (TEAM)"
    def format_player_name(row):
        first = row.get('first_name', '')
        last = row.get('last_name', '')
        team = row.get('team', '')

        if first and last:
            name = f"{last}, {first}"
        else:
            name = row.get('player_name', 'Unknown')

        if team:
            name = f"{name} ({team})"

        return name

    active_players_df['display_name'] = active_players_df.apply(format_player_name, axis=1)

    # Sort by last name
    if 'last_name' in active_players_df.columns:
        active_players_df = active_players_df.sort_values(by='last_name')
    else:
        active_players_df = active_players_df.sort_values(by='player_name')

    eligible_players_list = [
        (row['display_name'], row['player_id'])
        for _, row in active_players_df.iterrows()
    ]

    return eligible_players_list if eligible_players_list else [
        (f"No eligible {position_label}s after filtering for {year}", None)
    ]
