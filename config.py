"""
Shared configuration constants for Daily Draft
Supports both NFL and MLB trivia games
"""

# --- Scoring Constants ---
MAX_POINTS_PER_QUESTION = 10000

# Scoring thresholds (percentage to emoji mapping)
EMOJI_THRESHOLDS = {
    100: "🟩🟩🟩🟩🟩",
    80: "🟩🟩🟩🟩🟨",
    60: "🟩🟩🟩🟨⬛",
    40: "🟩🟩🟨⬛⬛",
    20: "🟩🟨⬛⬛⬛",
    0.0001: "🟨⬛⬛⬛⬛"
}

# --- Sport Configurations ---
SPORTS = {
    "nfl": {
        "name": "NFL",
        "full_name": "NFL Trivia",
        "icon": "🏈",
        "questions_per_round": 5,
        "min_year": 1999,
        "max_year": 2023,
        "data_source": "nfl_data_py",
        "season_start_month": 9,  # September
    },
    "mlb": {
        "name": "MLB",
        "full_name": "MLB Trivia",
        "icon": "⚾",
        "questions_per_round": 4,
        "min_year": 1995,
        "max_year": 2024,
        "data_source": "pybaseball",
        "season_start_month": 4,  # April
    }
}

# --- NFL Specific ---
NFL_POSITIONS_FOR_DRAFT = ["QB", "WR1", "WR2", "RB", "TE"]

NFL_STAT_CATEGORIES = {
    "QB": ["passing_yards", "passing_tds", "completions", "attempts"],
    "WR": ["receptions", "receiving_yards", "receiving_tds", "targets"],
    "RB": ["rushing_yards", "rushing_tds", "carries", "receptions"],
    "TE": ["receptions", "receiving_yards", "receiving_tds", "targets"]
}

# --- MLB Specific ---
# Question slots: AL Batter, NL Batter, AL Pitcher, NL Pitcher
MLB_QUESTION_SLOTS = [
    {"slot": "AL_BAT", "league": "AL", "type": "batter"},
    {"slot": "NL_BAT", "league": "NL", "type": "batter"},
    {"slot": "AL_PIT", "league": "AL", "type": "pitcher"},
    {"slot": "NL_PIT", "league": "NL", "type": "pitcher"},
]

MLB_BATTER_STATS = ["HR", "RBI", "H", "AVG", "SB", "R", "OPS"]
MLB_PITCHER_STATS = ["W", "SO", "ERA", "SV", "IP", "WHIP"]

# Stats where lower is better (require inverted scoring)
MLB_INVERTED_STATS = ["ERA", "WHIP"]

# MLB qualification thresholds
MLB_MIN_PLATE_APPEARANCES = 100  # For batters
MLB_MIN_INNINGS_PITCHED = 30     # For pitchers (lowered to include relievers)
