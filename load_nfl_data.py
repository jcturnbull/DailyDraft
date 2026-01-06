import nfl_data_py as nfl
import pandas as pd

# This file provides the load_data_for_year function.

def load_data_for_year(year: int):
    """
    Loads all necessary NFL data for a specified year.
    The main stats DataFrame returned is stats_with_position_df, which merges
    all seasonal stats with player roster positions.

    Args:
        year (int): The NFL season year to load data for.

    Returns:
        tuple: Contains DataFrames for:
               1. rosters_df (filtered for QB, WR, RB, TE)
               2. stats_with_position_df (all seasonal stats merged with roster positions)
               3. seasonal_snap_counts_df (aggregated seasonal snap counts)
               4. raw_snap_counts_df (raw game-level snap counts)
               Returns empty DataFrames for any part that fails to load or process.
    """
    print(f"Loading data for year: {year}...")

    # --- Initialize default empty DataFrames ---
    rosters_df = pd.DataFrame()
    stats_with_position_df = pd.DataFrame()
    seasonal_snap_counts_df = pd.DataFrame(columns=['player_id', 'offense_snaps'])
    raw_snap_counts_df = pd.DataFrame()

    # --- Load and Prepare Roster Data ---
    try:
        temp_rosters_df = nfl.import_seasonal_rosters([year])
        columns_to_keep = ['player_id', 'position', 'first_name', 'last_name', 'player_name']
        existing_roster_cols = [col for col in columns_to_keep if col in temp_rosters_df.columns]
        rosters_df = temp_rosters_df[existing_roster_cols].copy() # Use .copy()

        game_positions_to_include = ['WR', 'TE', 'QB', 'RB']
        if 'position' in rosters_df.columns:
            rosters_df = rosters_df[rosters_df['position'].isin(game_positions_to_include)]

        rosters_df = rosters_df.dropna(subset=['first_name', 'last_name', 'player_name', 'player_id', 'position']).copy()

        # Remove duplicate players (players who played for multiple teams in same season)
        # Keep first occurrence - stats are season totals anyway
        rosters_df = rosters_df.drop_duplicates(subset=['player_id'], keep='first')
    except Exception as e:
        print(f"Error loading or processing rosters: {e}")
        rosters_df = pd.DataFrame() # Ensure it's an empty DataFrame on error

    # --- Load All Seasonal Player Statistics ---
    all_seasonal_stats_df = pd.DataFrame()
    try:
        all_seasonal_stats_df = nfl.import_seasonal_data([year], s_type='REG')
        if all_seasonal_stats_df.empty:
            print(f"Warning: nfl.import_seasonal_data({year}) returned an empty DataFrame.")
    except Exception as e:
        print(f"Error loading seasonal stats: {e}")
        all_seasonal_stats_df = pd.DataFrame()

    # --- Merge All Stats with Roster Info to get Positions ---
    if not all_seasonal_stats_df.empty and not rosters_df.empty and \
       'player_id' in all_seasonal_stats_df.columns and 'player_id' in rosters_df.columns:
        try:
            # Select only necessary columns from rosters_df for the merge to avoid duplicate columns if any
            roster_subset_for_merge = rosters_df[['player_id', 'position', 'player_name']].copy()
            stats_with_position_df = pd.merge(all_seasonal_stats_df,
                                              roster_subset_for_merge,
                                              on='player_id',
                                              how='left') # Use left merge to keep all stats, add position
            # Drop rows where position is NaN after merge (i.e., players in stats but not in our filtered roster)
            # This ensures players in stats_with_position_df are among our game_positions_to_include
            stats_with_position_df = stats_with_position_df.dropna(subset=['position'])

            if stats_with_position_df.empty and not all_seasonal_stats_df.empty:
                 print("Warning: stats_with_position_df became empty after merging with roster and dropping NaNs in position.")
                 print(f"         all_seasonal_stats_df rows: {len(all_seasonal_stats_df)}, rosters_df rows: {len(rosters_df)}")


        except Exception as e:
            print(f"Error merging seasonal stats with roster positions: {e}")
            stats_with_position_df = pd.DataFrame() # Ensure empty on error
    elif all_seasonal_stats_df.empty:
        print("Cannot create stats_with_position_df because all_seasonal_stats_df is empty.")
    elif rosters_df.empty:
        print("Cannot create stats_with_position_df because rosters_df is empty.")
    else:
        print("Cannot create stats_with_position_df due to missing 'player_id' columns for merge.")
        
    # --- Load and Aggregate Snap Counts ---
    try:
        raw_snap_counts_df = nfl.import_snap_counts([year]) 
        player_ids_df = nfl.import_ids() 

        if (not raw_snap_counts_df.empty and 'pfr_player_id' in raw_snap_counts_df.columns and
                'offense_snaps' in raw_snap_counts_df.columns and
                not player_ids_df.empty and 'pfr_id' in player_ids_df.columns and
                'gsis_id' in player_ids_df.columns):

            merged_snaps_df = pd.merge(raw_snap_counts_df,
                                       player_ids_df[['pfr_id', 'gsis_id']],
                                       left_on='pfr_player_id',
                                       right_on='pfr_id',
                                       how='left')

            if 'gsis_id' in merged_snaps_df.columns:
                merged_snaps_df = merged_snaps_df.dropna(subset=['gsis_id'])
                temp_seasonal_snap_counts_df = merged_snaps_df.groupby('gsis_id')['offense_snaps'].sum().reset_index()
                seasonal_snap_counts_df = temp_seasonal_snap_counts_df.rename(columns={'gsis_id': 'player_id'})
        # If conditions for merge aren't met, seasonal_snap_counts_df remains the default empty one.
    except Exception as e:
        print(f"Error loading or processing snap counts: {e}")
        # seasonal_snap_counts_df remains default empty, raw_snap_counts_df might be empty or partially loaded

    print(f"Data loading for year {year} complete.")
    # The order of returned DataFrames now matches what game_logic.py expects
    return rosters_df, stats_with_position_df, seasonal_snap_counts_df, raw_snap_counts_df

# --- Example Usage (Keep commented out for module use) ---
# if __name__ == '__main__':
#     YEAR_FOR_QUESTIONS = 2022 # Example year
#     rosters, stats_with_pos, aggregated_snaps, raw_s = load_data_for_year(YEAR_FOR_QUESTIONS)

#     print("Roster Data Sample (QB, WR, RB, TE):")
#     print(rosters.head() if not rosters.empty else "Rosters empty.")
#     print(f"Total rostered players (QB,WR,RB,TE): {len(rosters)}")

#     print("\nStats with Position Info Sample:")
#     print(stats_with_pos.head() if not stats_with_pos.empty else "Stats with position empty.")
#     if not stats_with_pos.empty and 'position' in stats_with_pos.columns:
#         print("Position distribution in stats_with_position_df:")
#         print(stats_with_pos['position'].value_counts())
#     print(f"Total rows in stats_with_position_df: {len(stats_with_pos)}")


#     print("\nAggregated Seasonal Snaps Sample:")
#     print(aggregated_snaps.head() if not aggregated_snaps.empty else "Aggregated snaps empty.")
#     print(f"Total players with aggregated snaps: {len(aggregated_snaps)}")
