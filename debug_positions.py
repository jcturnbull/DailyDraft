"""Debug script to check pybaseball position data"""
from pybaseball import batting_stats, batting_stats_bref, cache
from pybaseball.lahman import appearances, people, fielding

cache.enable()

print("=== Option 1: FanGraphs batting_stats ===")
df = batting_stats(2023, qual=100)
print(f"Columns: {list(df.columns)}")
print(f"Sample:\n{df[['Name', 'Team']].head(3)}")

print("\n=== Option 2: Baseball-Reference batting_stats_bref ===")
try:
    df_bref = batting_stats_bref(2023)
    print(f"Columns: {list(df_bref.columns)}")
    print(f"Sample:\n{df_bref[['Name', 'Pos']].head(10) if 'Pos' in df_bref.columns else 'No Pos column'}")
except Exception as e:
    print(f"Error: {e}")

print("\n=== Option 3: Lahman Fielding table ===")
try:
    fld = fielding()
    fld_2023 = fld[fld['yearID'] == 2023]
    print(f"Columns: {list(fld.columns)}")
    print(f"Position values: {fld_2023['POS'].unique() if 'POS' in fld.columns else 'No POS'}")
    print(f"Sample:\n{fld_2023[['playerID', 'POS', 'G']].head(10)}")
except Exception as e:
    print(f"Error: {e}")
