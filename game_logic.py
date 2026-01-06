"""
Core game logic for Daily Draft NFL Trivia
Handles question generation, scoring, and data management
"""
import random
import pandas as pd
from load_nfl_data import load_data_for_year
from datetime import datetime, timezone

# --- Constants ---
POSITIONS_FOR_DRAFT = ["QB", "WR1", "WR2", "RB", "TE"]
STAT_CATEGORIES = {
    "QB": ["passing_yards", "passing_tds", "completions", "attempts"],
    "WR": ["receptions", "receiving_yards", "receiving_tds", "targets"],
    "RB": ["rushing_yards", "rushing_tds", "carries", "receptions"],
    "TE": ["receptions", "receiving_yards", "receiving_tds", "targets"]
}
MIN_YEAR = 1999
MAX_YEAR = 2023
MAX_POINTS_PER_QUESTION = 10000
QUESTIONS_PER_ROUND = 5

# Scoring thresholds (percentage to emoji mapping)
EMOJI_THRESHOLDS = {
    100: "🟩🟩🟩🟩🟩",
    80: "🟩🟩🟩🟩🟨",
    60: "🟩🟩🟩🟨⬛",
    40: "🟩🟩🟨⬛⬛",
    20: "🟩🟨⬛⬛⬛",
    0.0001: "🟨⬛⬛⬛⬛"
}


def get_daily_seed_and_date():
    """
    Generates a seed based on the current UTC date.
    Returns (seed_int, date_string) for consistent daily challenges.
    """
    now_utc = datetime.now(timezone.utc)
    date_str = now_utc.strftime("%Y-%m-%d")
    seed_str = now_utc.strftime("%Y%m%d")
    return int(seed_str), date_str


def select_random_year_for_question(min_year=MIN_YEAR, max_year=MAX_YEAR, use_seed=True):
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


def get_data_for_year_cached(year, data_cache):
    """
    Retrieves or loads NFL data for a given year using cache.
    Returns tuple: (rosters_df, stats_with_position_df, seasonal_snap_counts_df, raw_snap_counts_df)
    """
    if year not in data_cache:
        try:
            data_tuple = load_data_for_year(year)
            # Validate data loaded successfully
            if data_tuple[0].empty or data_tuple[1].empty:
                data_cache[year] = (pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
            else:
                data_cache[year] = data_tuple
        except Exception as e:
            print(f"Error loading data for year {year}: {e}")
            data_cache[year] = (pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())

    # Return cached data (might be empty if loading failed)
    cached_data = data_cache[year]
    if cached_data[0].empty or cached_data[1].empty:
        return (pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())

    return cached_data


def get_stat_leader(stat_df, stat_column):
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


def generate_questions_for_round(data_cache, daily_mode=True, daily_seed=None):
    """
    Generates questions for a round.
    If daily_mode=True, uses daily_seed for deterministic questions.
    Otherwise, generates random questions for practice.
    """
    if daily_mode and daily_seed is not None:
        random.seed(daily_seed)

    questions = []
    used_wr_year_stats = set()  # Ensures WR questions are unique

    for slot in POSITIONS_FOR_DRAFT:
        question_year = select_random_year_for_question(use_seed=daily_mode)

        # Load data for this question's year
        rosters_df, stats_with_position_df, _, _ = get_data_for_year_cached(question_year, data_cache)

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
                'data_issue': True
            })
            continue

        # Determine position and possible stats
        actual_position = slot.rstrip('12')  # WR1 -> WR, WR2 -> WR
        possible_stats = STAT_CATEGORIES.get(actual_position, [])

        if not possible_stats:
            continue

        # Select stat (ensure uniqueness for WRs)
        selected_stat = None
        attempts = 0
        max_attempts = len(possible_stats) * 3

        if actual_position == "WR":
            # Ensure unique (year, stat) combinations for WR positions
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
                leader_info = get_stat_leader(relevant_stats, selected_stat)

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
            'data_issue': False if leader_info else True
        })

    return questions


def calculate_score_emojis_and_points(guessed_player_stat_input, correct_leader_stat_input):
    """
    Calculates score based on how close the guess is to the correct answer.
    Returns (emoji_string, points_earned)
    """
    # Parse inputs to float
    try:
        guessed_stat = float(guessed_player_stat_input) if guessed_player_stat_input is not None else 0.0
    except:
        guessed_stat = 0.0

    try:
        correct_stat = float(correct_leader_stat_input) if correct_leader_stat_input is not None else 0.0
    except:
        # If correct stat is invalid, award full points if guess is also 0
        return ("⬛⬛⬛⬛⬛", 0) if guessed_stat != 0 else ("🟩🟩🟩🟩🟩", MAX_POINTS_PER_QUESTION)

    # Calculate percentage
    percentage = 0.0
    points = 0

    if correct_stat == 0:
        if guessed_stat == 0:
            percentage = 100.0
            points = MAX_POINTS_PER_QUESTION
    else:
        raw_percentage = (guessed_stat / correct_stat) * 100.0
        percentage = min(max(0.0, raw_percentage), 100.0)
        points = round(percentage * (MAX_POINTS_PER_QUESTION / 100.0))

    # Determine emoji based on percentage
    emojis = "⬛⬛⬛⬛⬛"
    for threshold, emoji_str in sorted(EMOJI_THRESHOLDS.items(), reverse=True):
        if percentage >= threshold:
            emojis = emoji_str
            break

    # Handle edge case: 0 guess when answer is non-zero
    if percentage == 0 and guessed_stat == 0 and correct_stat != 0:
        emojis = "⬛⬛⬛⬛⬛"

    return emojis, int(points)


def get_player_stat_for_question(guessed_player_id, question_data, data_cache):
    """
    Retrieves the stat value for a guessed player for a specific question.
    """
    question_year = question_data['year']
    stat_category = question_data['stat_category']

    _, stats_with_position_df, _, _ = get_data_for_year_cached(question_year, data_cache)

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


def get_eligible_players_for_autocomplete(position_label, year, data_cache):
    """
    Gets list of eligible players for a given position and year.
    Players must have played snaps or had relevant stats.
    Returns list of tuples: [(player_name, player_id), ...]
    """
    rosters_df, stats_with_position_df, seasonal_snap_counts_df, _ = get_data_for_year_cached(year, data_cache)

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

    # Remove duplicates (players may have multiple rows from merges)
    # Keep first occurrence, prioritizing by player_id
    active_players_df = active_players_df.drop_duplicates(subset=['player_id'], keep='first')

    # Create sorted list of (player_name, player_id) tuples
    active_players_df = active_players_df.sort_values(by='player_name')
    eligible_players_list = [
        (row['player_name'], row['player_id'])
        for _, row in active_players_df.iterrows()
    ]

    return eligible_players_list if eligible_players_list else [
        (f"No eligible {position_label}s after filtering for {year}", None)
    ]


def format_share_text(results, questions, total_score, max_score, game_date):
    """
    Formats results in a shareable format (like Wordle).
    """
    lines = [f"Daily Draft NFL Trivia {game_date}"]
    lines.append(f"Score: {total_score:,}/{max_score:,} ({int((total_score/max_score)*100)}%)")
    lines.append("")

    for i, q_data in enumerate(questions):
        result = results.get(i)
        if result:
            lines.append(result.get('emojis', '⬛⬛⬛⬛⬛'))

    return "\n".join(lines)
