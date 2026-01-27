"""Debug script to verify team-to-league mapping works"""
from load_mlb_data import load_mlb_data_for_year, get_players_by_league

print("=== Testing Team-to-League Mapping for 2005 ===")
batters_df, pitchers_df = load_mlb_data_for_year(2005)

print(f"\nBatters total: {len(batters_df)}")
if 'league' in batters_df.columns:
    print(f"League values: {batters_df['league'].unique()}")
    al_batters = get_players_by_league(batters_df, 'AL')
    nl_batters = get_players_by_league(batters_df, 'NL')
    print(f"AL batters: {len(al_batters)}")
    print(f"NL batters: {len(nl_batters)}")
    # Show some unmapped teams if any
    unmapped = batters_df[batters_df['league'].isna()]['team'].unique()
    if len(unmapped) > 0:
        print(f"UNMAPPED TEAMS: {unmapped}")
else:
    print("No league column created!")

print(f"\nPitchers total: {len(pitchers_df)}")
if 'league' in pitchers_df.columns:
    print(f"League values: {pitchers_df['league'].unique()}")
    al_pitchers = get_players_by_league(pitchers_df, 'AL')
    nl_pitchers = get_players_by_league(pitchers_df, 'NL')
    print(f"AL pitchers: {len(al_pitchers)}")
    print(f"NL pitchers: {len(nl_pitchers)}")
    unmapped = pitchers_df[pitchers_df['league'].isna()]['team'].unique()
    if len(unmapped) > 0:
        print(f"UNMAPPED TEAMS: {unmapped}")
