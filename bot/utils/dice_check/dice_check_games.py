from bot.games_const import BET_ON_PARITY, BET_ON_RANGE, CLEAR_HIT, DIRTY_HIT, EXACT_VALUE_BET, GOAL, HIT_1_CIRCLE, \
    HIT_2_CIRCLE, HIT_CENTER, ONE_PIN_LEFT, STRIKE


def get_coefficient_cube(dice_value: int, user_bet_on) -> float:
    if len(user_bet_on) == 1 and str(dice_value) in user_bet_on:
        return EXACT_VALUE_BET
    if len(user_bet_on) == 2 and str(dice_value) in user_bet_on:
        return BET_ON_RANGE
    if len(user_bet_on) == 3 and str(dice_value) in user_bet_on:
        return BET_ON_PARITY
    return 0


def get_coefficient_basket(dice_value: int) -> float:
    if dice_value == 5:
        return CLEAR_HIT
    if dice_value == 4:
        return DIRTY_HIT
    return 0


def get_coefficient_darts(dice_value: int) -> float:
    if dice_value == 6:
        return HIT_CENTER
    if dice_value == 5:
        return HIT_1_CIRCLE
    if dice_value == 4:
        return HIT_2_CIRCLE
    return 0


def get_coefficient_bowling(dice_value: int) -> float:
    if dice_value == 6:
        return STRIKE
    if dice_value == 5:
        return ONE_PIN_LEFT
    return 0


def get_coefficient_football(dice_value: int) -> float:
    ez_win = [3, 4, 5]
    if dice_value in ez_win:
        return GOAL
    return 0
