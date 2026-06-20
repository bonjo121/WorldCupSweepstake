def third_place_status(standings_df, third_place_row):
    team_points = third_place_row["Points"]
    team_gd = third_place_row["GD"]
    team_gf = third_place_row["GF"]
    team_name = third_place_row["Team"]

    confirmed_better = 0
    possible_better = 0

    for group in standings_df["Group"].unique():
        group_table = standings_df[standings_df["Group"] == group].copy()
        group_table = group_table.reset_index(drop=True)

        if group_table["Played"].min() == 3:
            other_third = group_table.iloc[2]

            if other_third["Team"] == team_name:
                continue

            other_is_better = (
                other_third["Points"] > team_points
                or (
                    other_third["Points"] == team_points
                    and other_third["GD"] > team_gd
                )
                or (
                    other_third["Points"] == team_points
                    and other_third["GD"] == team_gd
                    and other_third["GF"] > team_gf
                )
            )

            if other_is_better:
                confirmed_better += 1
                possible_better += 1

        else:
            possible = group_table.copy()

            possible["Max Points"] = (
                possible["Points"] + ((3 - possible["Played"]) * 3)
            )

            if possible["Max Points"].max() > team_points:
                possible_better += 1

    if confirmed_better >= 8:
        return "eliminated"

    if possible_better <= 4:
        return "qualified"

    return "unknown"


def teams_have_played(team_a, team_b, matches_df):
    match = matches_df[
        (
            ((matches_df["home"] == team_a) & (matches_df["away"] == team_b))
            |
            ((matches_df["home"] == team_b) & (matches_df["away"] == team_a))
        )
    ]

    return not match.empty


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

    for group in standings_df["Group"].unique():
        group_table = standings_df[standings_df["Group"] == group].copy()
        group_table = group_table.reset_index(drop=True)

        games_played = group_table["Played"].min()

        # Any team on 6 points is already through.
        for _, team_row in group_table.iterrows():
            team = team_row["Team"]
            points = team_row["Points"]

            if points == 6:
                tournament_state[team]["stage"] = "Out of Group"
                tournament_state[team]["alive"] = True

        # Early elimination case:
        # A team on 0 points after 2 games is out if:
        # - their unplayed opponent has 4+ points
        # - the other two teams both have 3+ points
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

            status = third_place_status(standings_df, third_place_row)

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