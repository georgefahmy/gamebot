def expected(player_a, player_b):
    exp = round(1 / (1 + 10 ** ((player_b - player_a) / 400)) * 100, 1)
    return exp


def elo(player_a, player_b):
    k_factor = 32
    exp = 1 / (1 + 10 ** ((player_b - player_a) / 400))
    player_a_rank = round(player_a + k_factor * (1 - exp), 2)
    player_b_rank = round(player_b - k_factor * (1 - exp), 2)
    return player_a_rank, player_b_rank
