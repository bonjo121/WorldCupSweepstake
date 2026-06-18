def update_group_stages(tournament_state, standings_df):
    third_place_rows = []

    for group in standings_df["Group"].unique():
        group_table = standings_df[standings_df["Group"] == group].copy()

        group_table = group_table.sort_values(
            ["Points", "GD", "GF"],
            ascending=[False, False, False]
        )

        games_played = group_table["Played"].min()

        if games_played < 2:
            continue

        if games_played == 2:
            for _, team_row in group_table.iterrows():
                team = team_row["Team"]
                points = team_row["Points"]

                if points == 6:
                    tournament_state[team]["stage"] = "Out of Group"
                    tournament_state[team]["alive"] = True
                    continue

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

            continue

        if games_played == 3:
            for team in group_table.iloc[0:2]["Team"]:
                tournament_state[team]["stage"] = "Out of Group"
                tournament_state[team]["alive"] = True

            third_place_row = group_table.iloc[2]
            third_place_rows.append(third_place_row)

            fourth_place_team = group_table.iloc[3]["Team"]
            tournament_state[fourth_place_team]["stage"] = "Group Exit"
            tournament_state[fourth_place_team]["alive"] = False

            third_place_team = third_place_row["Team"]
            better_thirds = 0

            for other_group in standings_df["Group"].unique():
                other_table = standings_df[
                    standings_df["Group"] == other_group
                ].copy()

                if other_table["Played"].min() < 3:
                    continue

                other_table = other_table.sort_values(
                    ["Points", "GD", "GF"],
                    ascending=[False, False, False]
                )

                other_third = other_table.iloc[2]

                if other_third["Team"] == third_place_team:
                    continue

                if (
                    other_third["Points"] > third_place_row["Points"]
                    or (
                        other_third["Points"] == third_place_row["Points"]
                        and other_third["GD"] > third_place_row["GD"]
                    )
                    or (
                        other_third["Points"] == third_place_row["Points"]
                        and other_third["GD"] == third_place_row["GD"]
                        and other_third["GF"] > third_place_row["GF"]
                    )
                ):
                    better_thirds += 1

            if better_thirds >= 8:
                tournament_state[third_place_team]["stage"] = "Group Exit"
                tournament_state[third_place_team]["alive"] = False

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

        # Loser of a knockout match is eliminated
        tournament_state[loser]["alive"] = False

        # If winner was already eliminated, ignore the match
        # This protects against the third-place match
        if not tournament_state[winner]["alive"]:
            continue

        tournament_state[winner]["stage"] = knockout_stage_by_game_number[
            winner_game_number
        ]

        tournament_state[winner]["alive"] = True

    return tournament_state
