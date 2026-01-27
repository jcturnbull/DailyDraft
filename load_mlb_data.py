"""
MLB data loading module for Daily Draft
Uses pybaseball to fetch batting and pitching statistics
"""
import pandas as pd
from config import MLB_MIN_PLATE_APPEARANCES, MLB_MIN_INNINGS_PITCHED

# Team to League mapping (current as of 2024)
# Note: Some teams have moved leagues historically (HOU, MIL, etc.)
TEAM_TO_LEAGUE = {
    # American League
    'BAL': 'AL', 'BOS': 'AL', 'NYY': 'AL', 'TBR': 'AL', 'TOR': 'AL',  # AL East
    'TB': 'AL', 'TAM': 'AL',  # Tampa Bay aliases
    'CLE': 'AL', 'CWS': 'AL', 'DET': 'AL', 'KCR': 'AL', 'MIN': 'AL',  # AL Central
    'CHW': 'AL', 'KC': 'AL', 'KAN': 'AL',  # Aliases
    'HOU': 'AL', 'LAA': 'AL', 'OAK': 'AL', 'SEA': 'AL', 'TEX': 'AL',  # AL West
    'ANA': 'AL', 'CAL': 'AL', 'LAD': 'NL',  # LA Angels aliases (not Dodgers)

    # National League
    'ATL': 'NL', 'MIA': 'NL', 'NYM': 'NL', 'PHI': 'NL', 'WSN': 'NL',  # NL East
    'FLA': 'NL', 'MON': 'NL', 'WAS': 'NL', 'WSH': 'NL',  # Aliases (Florida Marlins, Montreal, Washington)
    'CHC': 'NL', 'CIN': 'NL', 'MIL': 'NL', 'PIT': 'NL', 'STL': 'NL',  # NL Central
    'ARI': 'NL', 'COL': 'NL', 'LAD': 'NL', 'SDP': 'NL', 'SFG': 'NL',  # NL West
    'SD': 'NL', 'SF': 'NL', 'LA': 'NL', 'AZ': 'NL',  # Aliases

    # Historical teams that may appear in older data
    'MON': 'NL',  # Montreal Expos (became Nationals)
    'FLO': 'NL',  # Florida Marlins
}

# Try to import pybaseball and enable caching
try:
    from pybaseball import batting_stats, pitching_stats, cache
    cache.enable()
    PYBASEBALL_AVAILABLE = True
except ImportError:
    PYBASEBALL_AVAILABLE = False
    print("Warning: pybaseball not installed. MLB features will not work.")


def load_mlb_data_for_year(year: int):
    """
    Loads MLB batting and pitching data for a specified year.

    Args:
        year (int): The MLB season year to load data for.

    Returns:
        tuple: Contains DataFrames for:
               1. batters_df (qualified batters)
               2. pitchers_df (qualified pitchers)
               Returns empty DataFrames if loading fails.
    """
    print(f"Loading MLB data for year: {year}...")

    batters_df = pd.DataFrame()
    pitchers_df = pd.DataFrame()

    if not PYBASEBALL_AVAILABLE:
        print("pybaseball not available, returning empty DataFrames")
        return batters_df, pitchers_df

    # --- Load Batting Stats ---
    try:
        batters_df = batting_stats(year, qual=MLB_MIN_PLATE_APPEARANCES)

        if batters_df.empty:
            print(f"Warning: No batting data returned for {year}")
        else:
            batters_df = _standardize_batting_columns(batters_df)
            print(f"Loaded {len(batters_df)} qualified batters for {year}")

    except Exception as e:
        print(f"Error loading batting stats for {year}: {e}")
        batters_df = pd.DataFrame()

    # --- Load Pitching Stats ---
    try:
        pitchers_df = pitching_stats(year, qual=MLB_MIN_INNINGS_PITCHED)

        if pitchers_df.empty:
            print(f"Warning: No pitching data returned for {year}")
        else:
            pitchers_df = _standardize_pitching_columns(pitchers_df)
            print(f"Loaded {len(pitchers_df)} qualified pitchers for {year}")

    except Exception as e:
        print(f"Error loading pitching stats for {year}: {e}")
        pitchers_df = pd.DataFrame()

    print(f"MLB data loading for year {year} complete.")
    return batters_df, pitchers_df


def _standardize_batting_columns(df):
    """Standardize batting DataFrame column names."""
    df = df.copy()

    # Ensure player_id column
    if 'IDfg' in df.columns:
        df['player_id'] = df['IDfg'].astype(str)
    elif 'playerid' in df.columns:
        df['player_id'] = df['playerid'].astype(str)
    else:
        df['player_id'] = df.index.astype(str)

    # Standardize name column
    if 'Name' in df.columns:
        df['player_name'] = df['Name']

    # Standardize team column
    if 'Team' in df.columns:
        df['team'] = df['Team']

    # Derive league from team (NOT from 'Lg' column which is WAR adjustment)
    if 'Team' in df.columns:
        df['league'] = df['Team'].map(TEAM_TO_LEAGUE)

    return df


def _standardize_pitching_columns(df):
    """Standardize pitching DataFrame column names."""
    df = df.copy()

    # Ensure player_id column
    if 'IDfg' in df.columns:
        df['player_id'] = df['IDfg'].astype(str)
    elif 'playerid' in df.columns:
        df['player_id'] = df['playerid'].astype(str)
    else:
        df['player_id'] = df.index.astype(str)

    # Standardize name column
    if 'Name' in df.columns:
        df['player_name'] = df['Name']

    # Standardize team column
    if 'Team' in df.columns:
        df['team'] = df['Team']

    # Derive league from team
    if 'Team' in df.columns:
        df['league'] = df['Team'].map(TEAM_TO_LEAGUE)

    return df


def get_players_by_league(df, league):
    """
    Filter DataFrame to only include players from a specific league.

    Args:
        df: DataFrame of players
        league: League to filter for ("AL" or "NL")

    Returns:
        Filtered DataFrame
    """
    if df.empty or 'league' not in df.columns:
        return pd.DataFrame()

    return df[df['league'] == league].copy()


def get_stat_leader_mlb(df, stat_column, inverted=False):
    """
    Find the player with the best value for a given stat.

    Args:
        df: DataFrame of players
        stat_column: Column name for the stat
        inverted: If True, lower values are better (e.g., ERA)

    Returns:
        dict with player info and stat values, or None if not found
    """
    if df.empty or stat_column not in df.columns or 'player_id' not in df.columns:
        return None

    try:
        df_copy = df.copy()
        df_copy[stat_column] = pd.to_numeric(df_copy[stat_column], errors='coerce')
        df_copy = df_copy.dropna(subset=[stat_column])

        if df_copy.empty:
            return None

        if inverted:
            leader_idx = df_copy[stat_column].idxmin()
            worst_value = df_copy[stat_column].max()
        else:
            leader_idx = df_copy[stat_column].idxmax()
            worst_value = df_copy[stat_column].min()

        leader = df_copy.loc[leader_idx]

        return {
            'player_id': leader['player_id'],
            'player_name': leader.get('player_name', 'Unknown'),
            'team': leader.get('team', ''),
            'stat_value': leader[stat_column],
            'worst_stat_value': worst_value
        }
    except Exception as e:
        print(f"Error finding stat leader for {stat_column}: {e}")
        return None
