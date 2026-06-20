import pandas as pd
from groups import groups


def get_group(team):
    for group_name, teams in groups.items():
        if team in teams:
            return group_name

    raise ValueError(f"Team not found in groups: {team}")


def create_standings():
    standings = {}

    for group_name, teams in groups.items():
        for team in teams:
            standings[team] = {
                "Group": group_name,
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


def head_to_head_winner(team_a, team_b, matches_df):
    match = matches_df[
        (
            ((matches_df["home"] == team_a) & (matches_df["away"] == team_b))
            |
            ((matches_df["home"] == team_b) & (matches_df["away"] == team_a))
        )
    ]

    if match.empty:
        return None

    match = match.iloc[0]

    if match["home_score"] == match["away_score"]:
        return None

    if match["home_score"] > match["away_score"]:
        return match["home"]

    return match["away"]


def sort_group_with_head_to_head(group_table, matches_df):
    group_table = group_table.sort_values(
        ["Points", "GD", "GF"],
        ascending=[False, False, False]
    ).reset_index(drop=True)

    sorted_rows = []
    i = 0

    while i < len(group_table):
        same_points_rows = [group_table.iloc[i]]
        j = i + 1

        while (
            j < len(group_table)
            and group_table.iloc[j]["Points"] == group_table.iloc[i]["Points"]
        ):
            same_points_rows.append(group_table.iloc[j])
            j += 1

        if len(same_points_rows) == 2:
            team_a = same_points_rows[0]["Team"]
            team_b = same_points_rows[1]["Team"]

            winner = head_to_head_winner(team_a, team_b, matches_df)

            if winner == team_b:
                same_points_rows = [same_points_rows[1], same_points_rows[0]]

        sorted_rows.extend(same_points_rows)
        i = j

    return pd.DataFrame(sorted_rows).reset_index(drop=True)


def build_group_tables(matches_df):
    standings = create_standings()

    for _, match in matches_df.iterrows():
        home = match["home"]
        away = match["away"]
        home_score = match["home_score"]
        away_score = match["away_score"]

        update_team(standings, home, home_score, away_score)
        update_team(standings, away, away_score, home_score)

    standings_df = pd.DataFrame(standings.values())

    sorted_groups = []

    for group in standings_df["Group"].unique():
        group_table = standings_df[standings_df["Group"] == group].copy()
        sorted_group = sort_group_with_head_to_head(group_table, matches_df)
        sorted_groups.append(sorted_group)

    return pd.concat(sorted_groups, ignore_index=True)

