import pandas as pd
from groups import groups


def create_empty_standings():
    standings = {}

    for group, teams in groups.items():
        for team in teams:
            standings[team] = {
                "Group": group,
                "Team": team,
                "Played": 0,
                "Wins": 0,
                "Draws": 0,
                "Losses": 0,
                "GF": 0,
                "GA": 0,
                "GD": 0,
                "Points": 0
            }

    return standings


def update_team(standings, team, goals_for, goals_against):
    standings[team]["Played"] += 1
    standings[team]["GF"] += goals_for
    standings[team]["GA"] += goals_against
    standings[team]["GD"] = standings[team]["GF"] - standings[team]["GA"]

    if goals_for > goals_against:
        standings[team]["Wins"] += 1
        standings[team]["Points"] += 3
    elif goals_for == goals_against:
        standings[team]["Draws"] += 1
        standings[team]["Points"] += 1
    else:
        standings[team]["Losses"] += 1


def build_group_tables(matches_df):
    standings = create_empty_standings()

    for _, match in matches_df.iterrows():
        home = match["home"]
        away = match["away"]
        home_score = match["home_score"]
        away_score = match["away_score"]

        update_team(standings, home, home_score, away_score)
        update_team(standings, away, away_score, home_score)

    standings_df = pd.DataFrame(standings.values())

    standings_df = standings_df.sort_values(
        ["Group", "Points", "GD", "GF"],
        ascending=[True, False, False, False]
    )

    return standings_df

