import pandas as pd

from groups import groups
from standings import build_group_tables


SIMULATED_RESULTS = [
    (1, 0),
    (100, 0),
    (0, 0),
    (0, 1),
    (0, 100),
]


def compare_teams(row_a, row_b):
    if row_a["Points"] != row_b["Points"]:
        return row_a["Points"] > row_b["Points"]

    if row_a["GD"] != row_b["GD"]:
        return row_a["GD"] > row_b["GD"]

    if row_a["GF"] != row_b["GF"]:
        return row_a["GF"] > row_b["GF"]

    return False


def get_played_pairs(matches_df):
    played_pairs = set()

    for _, match in matches_df.iterrows():
        pair = frozenset([match["home"], match["away"]])
        played_pairs.add(pair)

    return played_pairs


def get_remaining_group_matches(group_name, matches_df):
    group_teams = groups[group_name]
    played_pairs = get_played_pairs(matches_df)

    remaining_matches = []

    for i in range(len(group_teams)):
        for j in range(i + 1, len(group_teams)):
            team_a = group_teams[i]
            team_b = group_teams[j]

            pair = frozenset([team_a, team_b])

            if pair not in played_pairs:
                remaining_matches.append((team_a, team_b))

    return remaining_matches


def group_can_produce_better_third(
    group_name,
    matches_df,
    target_third_row
):
    remaining_matches = get_remaining_group_matches(group_name, matches_df)

    if len(remaining_matches) == 0:
        standings_df = build_group_tables(matches_df)
        group_table = standings_df[
            standings_df["Group"] == group_name
        ].reset_index(drop=True)

        other_third = group_table.iloc[2]
        return compare_teams(other_third, target_third_row)

    if len(remaining_matches) != 2:
        return True

    match_1 = remaining_matches[0]
    match_2 = remaining_matches[1]

    for result_1 in SIMULATED_RESULTS:
        for result_2 in SIMULATED_RESULTS:
            simulated_matches = pd.DataFrame([
                {
                    "home": match_1[0],
                    "away": match_1[1],
                    "home_score": result_1[0],
                    "away_score": result_1[1],
                    "round": 3
                },
                {
                    "home": match_2[0],
                    "away": match_2[1],
                    "home_score": result_2[0],
                    "away_score": result_2[1],
                    "round": 3
                }
            ])

            test_matches_df = pd.concat(
                [matches_df, simulated_matches],
                ignore_index=True
            )

            standings_df = build_group_tables(test_matches_df)

            group_table = standings_df[
                standings_df["Group"] == group_name
            ].reset_index(drop=True)

            simulated_third = group_table.iloc[2]

            if compare_teams(simulated_third, target_third_row):
                return True

    return False


def third_place_status(standings_df, matches_df, third_place_row):
    confirmed_better = 0
    possible_better = 0

    target_group = third_place_row["Group"]

    for group_name in standings_df["Group"].unique():
        if group_name == target_group:
            continue

        group_table = standings_df[
            standings_df["Group"] == group_name
        ].reset_index(drop=True)

        group_finished = group_table["Played"].min() == 3

        if group_finished:
            other_third = group_table.iloc[2]

            if compare_teams(other_third, third_place_row):
                confirmed_better += 1

        else:
            if group_can_produce_better_third(
                group_name,
                matches_df,
                third_place_row
            ):
                possible_better += 1

    if confirmed_better >= 8:
        return "eliminated"

    if confirmed_better + possible_better <= 7:
        return "qualified"

    return "unknown"


def teams_have_played(team_a, team_b, matches_df):
    pair = frozenset([team_a, team_b])
    played_pairs = get_played_pairs(matches_df)

    return pair in played_pairs


def get_unplayed_opponent(team, group_table, matches_df):
    group_teams = group_table["Team"].tolist()

    for other_team in group_teams:
        if other_team == team:
            continue

        if not teams_have_played(team, other_team, matches_df):
            return other_team

    return None


def update_group_stages(tournament_state, standings_df, matches_df):
    third_place_rows = []

    for group_name in standings_df["Group"].unique():
        group_table = standings_df[
            standings_df["Group"] == group_name
        ].reset_index(drop=True)

        games_played = group_table["Played"].min()

        for _, team_row in group_table.iterrows():
            team = team_row["Team"]
            points = team_row["Points"]

            if points == 6:
                tournament_state[team]["stage"] = "Out of Group"
                tournament_state[team]["alive"] = True

        for _, team_row in group_table.iterrows():
            team = team_row["Team"]
            points = team_row["Points"]
            played = team_row["Played"]

            if played == 2 and points == 0:
                unplayed_opponent = get_unplayed_opponent(
                    team,
                    group_table,
                    matches_df
                )

                if unplayed_opponent is None:
                    continue

                opponent_points = group_table.loc[
                    group_table["Team"] == unplayed_opponent,
                    "Points"
                ].iloc[0]

                other_teams = group_table[
                    ~group_table["Team"].isin([team, unplayed_opponent])
                ]

                if opponent_points >= 4 and other_teams["Points"].min() >= 3:
                    tournament_state[team]["stage"] = "Group Exit"
                    tournament_state[team]["alive"] = False

        if games_played < 2:
            continue

        for _, team_row in group_table.iterrows():
            team = team_row["Team"]
            points = team_row["Points"]

            other_teams = group_table[group_table["Team"] != team].copy()

            other_teams["Max Points"] = (
                other_teams["Points"] + ((3 - other_teams["Played"]) * 3)
            )

            teams_that_can_catch = other_teams[
                other_teams["Max Points"] >= points
            ]

            if len(teams_that_can_catch) <= 1:
                tournament_state[team]["stage"] = "Out of Group"
                tournament_state[team]["alive"] = True

        if games_played == 3:
            for team in group_table.iloc[0:2]["Team"]:
                tournament_state[team]["stage"] = "Out of Group"
                tournament_state[team]["alive"] = True

            third_place_row = group_table.iloc[2]
            third_place_rows.append(third_place_row)

            third_place_team = third_place_row["Team"]

            status = third_place_status(
                standings_df,
                matches_df,
                third_place_row
            )

            if status == "qualified":
                tournament_state[third_place_team]["stage"] = "Out of Group"
                tournament_state[third_place_team]["alive"] = True

            elif status == "eliminated":
                tournament_state[third_place_team]["stage"] = "Group Exit"
                tournament_state[third_place_team]["alive"] = False

            fourth_place_team = group_table.iloc[3]["Team"]
            tournament_state[fourth_place_team]["stage"] = "Group Exit"
            tournament_state[fourth_place_team]["alive"] = False

    if len(third_place_rows) == 12:
        third_place_df = standings_df.__class__(third_place_rows)

        third_place_df = third_place_df.sort_values(
            ["Points", "GD", "GF"],
            ascending=[False, False, False]
        )

        best_thirds = third_place_df.iloc[0:8]["Team"]
        worst_thirds = third_place_df.iloc[8:12]["Team"]

        for team in best_thirds:
            tournament_state[team]["stage"] = "Out of Group"
            tournament_state[team]["alive"] = True

        for team in worst_thirds:
            tournament_state[team]["stage"] = "Group Exit"
            tournament_state[team]["alive"] = False

    return tournament_state


def update_knockout_stages(tournament_state, matches_df):
    games_played = {}

    knockout_stage_by_game_number = {
        4: "Won R32",
        5: "Won R16",
        6: "Won QF",
        7: "Won SF",
        8: "Won Final"
    }

    for _, match in matches_df.iterrows():
        home = match["home"]
        away = match["away"]

        home_score = match["home_score"]
        away_score = match["away_score"]

        games_played[home] = games_played.get(home, 0) + 1
        games_played[away] = games_played.get(away, 0) + 1

        if home_score > away_score:
            winner = home
            loser = away
        elif away_score > home_score:
            winner = away
            loser = home
        else:
            continue

        winner_game_number = games_played[winner]

        if winner_game_number < 4:
            continue

        tournament_state[loser]["alive"] = False

        if not tournament_state[winner]["alive"]:
            continue

        tournament_state[winner]["stage"] = knockout_stage_by_game_number[
            winner_game_number
        ]
        tournament_state[winner]["alive"] = True

    return tournament_state