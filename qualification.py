def get_qualified_teams(standings_df):
    qualified = set()
    eliminated = set()

    third_place_rows = []

    for group in standings_df["Group"].unique():
        group_table = standings_df[standings_df["Group"] == group].copy()

        # Only process a group once everyone has played 3 matches
        if group_table["Played"].min() < 3:
            continue

        group_table = group_table.sort_values(
            ["Points", "GD", "GF"],
            ascending=[False, False, False]
        )

        # Top 2 qualify automatically
        qualified.update(group_table.iloc[0:2]["Team"])

        # 3rd place goes into best-third-place comparison
        third_place_rows.append(group_table.iloc[2])

        # 4th place is eliminated
        eliminated.add(group_table.iloc[3]["Team"])

    # Work out best 8 third-place teams
    if len(third_place_rows) == 12:
        third_place_df = standings_df.__class__(third_place_rows)

        third_place_df = third_place_df.sort_values(
            ["Points", "GD", "GF"],
            ascending=[False, False, False]
        )

        best_thirds = third_place_df.iloc[0:8]["Team"]
        worst_thirds = third_place_df.iloc[8:12]["Team"]

        qualified.update(best_thirds)
        eliminated.update(worst_thirds)

    return qualified, eliminated

def update_tournament_state(tournament_state, qualified, eliminated):
    for team in qualified:
        tournament_state[team]["stage"] = "Out of Group"
        tournament_state[team]["alive"] = True

    for team in eliminated:
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

        if not tournament_state[winner]["alive"]:
            continue

        winner_game_number = games_played[winner]

        if winner_game_number < 4:
            continue

        tournament_state[winner]["stage"] = (
            knockout_stage_by_game_number[winner_game_number]
        )

        tournament_state[winner]["alive"] = True
        tournament_state[loser]["alive"] = False

    return tournament_state

