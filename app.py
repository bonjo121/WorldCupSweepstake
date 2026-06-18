import pandas as pd
from tournament_state import tournament_state
import streamlit as st
from qualification import update_group_stages, update_knockout_stages
from matches import get_finished_matches
from standings import build_group_tables
from datetime import datetime

st.set_page_config(
    page_title="World Cup Sweepstake",
    layout="wide"
)

# Load sweepstake draw
players = pd.read_csv("players.csv")

# Build teams dictionary from players.csv
teams = {}

for _, row in players.iterrows():
    for pot in range(1, 7):
        team = row[f"Pot{pot}"]

        teams[team] = {
            "owner": row["Player"],
            "pot": pot
        }

# Update Live Info
matches_df = get_finished_matches()
group_matches_df = matches_df[matches_df["round"] <= 3].copy()
standings_df = build_group_tables(group_matches_df)

for team in tournament_state:
    tournament_state[team]["stage"] = "Group Exit"
    tournament_state[team]["alive"] = True

tournament_state = update_group_stages(
    tournament_state,
    standings_df
)

tournament_state = update_knockout_stages(
    tournament_state,
    matches_df
)


def get_points(team):
    stage = tournament_state[team]["stage"]
    pot = teams[team]["pot"]

    if stage == "Group Exit":
        return 0

    stage_points = {
        "Out of Group": 1,
        "Won R32": 2,
        "Won R16": 3,
        "Won QF": 4,
        "Won SF": 5,
        "Won Final": 6
    }

    return stage_points[stage] + pot - 1

# Function for Formatting
def format_team(team):
    points = get_points(team)
    return f"{team} ({points})"


def get_player_score(player_name):
    row = players.loc[players["Player"] == player_name].iloc[0]

    total = 0

    for pot in range(1, 7):
        team = row[f"Pot{pot}"]
        total += get_points(team)

    return total


# Add total score column
players["Total"] = players["Player"].apply(get_player_score)



# App
leaderboard = players.sort_values("Total", ascending=False)

display_df = leaderboard.copy()

for pot in range(1, 7):
    display_df[f"Pot{pot}"] = display_df[f"Pot{pot}"].apply(format_team)


def team_colour(cell):
    team = cell.split(" (")[0]

    if tournament_state[team]["alive"]:
        return "background-color: lightgreen"

    return "background-color: salmon"


styled = display_df.style.map(
    team_colour,
    subset=["Pot1", "Pot2", "Pot3", "Pot4", "Pot5", "Pot6"]
)

st.title("World Cup Sweepstake")
st.caption("Data automatically updated from WorldCup26 API")
st.caption(f"Last updated: {datetime.now():%Y-%m-%d %H:%M}")

st.dataframe(
    styled,
    hide_index=True
)

st.markdown(
    """
🟩 **Still in contention**

🟥 **Eliminated**
"""
)