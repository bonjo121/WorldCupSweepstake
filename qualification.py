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


def is_better(row_a, row_b):
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
        played_pairs.add(frozenset([match["home"], match["away"]]))

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


def generate_result_combinations(number_of_matches):
    if number_of_matches == 0:
        return [[]]

    smaller_combinations = generate_result_combinations(
        number_of_matches - 1
    )

    combinations = []

    for result in SIMULATED_RESULTS:
        for smaller_combination in smaller_combinations:
            combinations.append([result] + smaller_combination)

    return combinations


def build_simulated_matches(remaining_matches, results):
    rows = []

    for match, result in zip(remaining_matches, results):
        rows.append({
            "home": match[0],
            "away": match[1],
            "home_score": result[0],
            "away_score": result[1],
            "round": 3
        })

    return pd.DataFrame(rows)


def build_group_scenarios(matches_df):
    scenarios = {}

    for group_name in groups:
        remaining_matches = get_remaining_group_matches(group_name, matches_df)

        # Safety guard: this simulator is designed for the late group stage
        # where unfinished groups have 1 or 2 matches left.
        if len(remaining_matches) > 2:
            scenarios[group_name] = []
            continue

        group_scenarios = []
        result_combinations = generate_result_combinations(
            len(remaining_matches)
        )

        for results in result_combinations:
            simulated_matches = build_simulated_matches(
                remaining_matches,
                results
            )

            if simulated_matches.empty:
                test_matches_df = matches_df.copy()
            else:
                test_matches_df = pd.concat(
                    [matches_df, simulated_matches],
                    ignore_index=True
                )

            scenario_standings_df = build_group_tables(test_matches_df)

            group_table = scenario_standings_df[
                scenario_standings_df["Group"] == group_name
            ].reset_index(drop=True)

            group_scenarios.append(group_table)

        scenarios[group_name] = group_scenarios

    return scenarios


def third_place_status(target_group, target_third_row, group_scenarios):
    confirmed_better = 0
    possible_better = 0

    for group_name, scenarios in group_scenarios.items():
        if group_name == target_group:
            continue

        if not scenarios:
            possible_better += 1
            continue

        better_count = 0

        for group_table in scenarios:
            other_third = group_table.iloc[2]

            if is_better(other_third, target_third_row):
                better_count += 1

        if better_count == len(scenarios):
            confirmed_better += 1

        elif better_count > 0:
            possible_better += 1

    if confirmed_better >= 8:
        return "eliminated"

    if confirmed_better + possible_better <= 7:
        return "qualified"

    return "unknown"


def team_status_in_scenario(team, group_name, group_table, group_scenarios):
    position = group_table.index[group_table["Team"] == team][0]

    # Top 2 always qualify
    if position <= 1:
        return "qualified"

    # 4th is out
    if position == 3:
        return "eliminated"

    # 3rd place depends on the best-third-place comparison
    third_place_row = group_table.iloc[2]

    return third_place_status(
        group_name,
        third_place_row,
        group_scenarios
    )


def update_group_stages(tournament_state, standings_df, matches_df):
    group_scenarios = build_group_scenarios(matches_df)

    for group_name, scenarios in group_scenarios.items():
        if not scenarios:
            continue

        for team in groups[group_name]:
            possible_statuses = []

            for group_table in scenarios:
                status = team_status_in_scenario(
                    team,
                    group_name,
                    group_table,
                    group_scenarios
                )

                possible_statuses.append(status)

            if all(status == "qualified" for status in possible_statuses):
                tournament_state[team]["stage"] = "Out of Group"
                tournament_state[team]["alive"] = True

            elif all(status == "eliminated" for status in possible_statuses):
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