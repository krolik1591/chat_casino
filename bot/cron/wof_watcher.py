import asyncio
import json
import logging
import random
import time

from bot.consts.const import WOF_MAX_NUM, WOF_MIN_NUM
from bot.db import db, manager
from bot.utils.rounding import round_down

HOUR = 3600


async def start_wof_timer():
    while True:
        logging.info("WOF TIMER STARTED")
        wof_info = await db.get_active_wheel_info()

        if not wof_info:
            await asyncio.sleep(HOUR)
            logging.info("WOF TIMER SLEEP")
            continue

        if not wof_info.timestamp_end:
            await asyncio.sleep(HOUR)
            logging.info("WOF TIMER SLEEP")
            continue

        time_before_wof_finish = wof_info.timestamp_end - time.time()
        logging.info(f"Seconds to WOF: {time_before_wof_finish}")
        if time_before_wof_finish < HOUR:
            await asyncio.sleep(time_before_wof_finish)
            logging.info("Timer to WOF is started")
            await spin_wheel_of_fortune()

        await asyncio.sleep(HOUR)


async def spin_wheel_of_fortune():
    logging.info('Starting Wheel of Fortune')
    print('Starting Wheel of Fortune')

    wof_info = await db.get_active_wheel_info()
    sold_tickets = list(await db.get_all_sold_tickets_nums())
    bank = len(sold_tickets) * wof_info.ticket_cost * (100 - wof_info.commission) / 100
    rewards = json.loads(wof_info.rewards)

    win_tickets = get_winner_tickets(wof_info.random_seed, len(rewards))

    numbers_won = []
    winners = [
        detect_winner(win_ticket, sold_tickets, numbers_won)
        for win_ticket in win_tickets
    ]
    winners = [winner for winner in winners if winner is not None]

    winners_info = []
    for winner_num, percent_reward in zip(winners, rewards):
        tg_id = await db.whose_ticket(winner_num)
        reward = round_down(bank * percent_reward / 100, 2)
        winners_info.append((winner_num, tg_id, reward))
        await db.update_user_wof_win(tg_id, reward)

    with manager.pw_database.atomic():
        await db.update_wof_result(json.dumps(winners_info))
        await db.delete_wof_tickets()


def get_winner_tickets(seed, count=1):
    random.seed(seed)
    winner_num = random.randint(WOF_MIN_NUM, WOF_MAX_NUM)
    return [winner_num] * count


def detect_winner(winner_num, sold_tickets, number_won):
    sold_tickets_without_winners = list(set(sold_tickets) - set(number_won))
    if not sold_tickets_without_winners:
        return None

    scores = (
        (ticket, calc_score(ticket, winner_num))
        for ticket in sold_tickets_without_winners
    )
    winner = min(scores, key=lambda x: x[1])
    number_won.append(winner[0])
    return winner[0]


def calc_score(user_number, winning_number):
    user_number = str(user_number).zfill(7)
    winning_number = str(winning_number).zfill(7)

    score = 0  # actually penalty

    for digit in range(7):
        user_digit = int(user_number[digit])
        winning_digit = int(winning_number[digit])
        score += calc_score_digit(user_digit, winning_digit, 6 - digit)

    return score


def calc_score_digit(user_digit, winning_digit, digit_index):
    if user_digit == winning_digit:
        return 0

    score_difference = abs(winning_digit - user_digit)
    if user_digit > winning_digit:
        score_difference -= 0.1  # If user_digit is larger, subtract a small value to prioritize it

    score_difference *= 10 ** digit_index  # first (left) digits are more important

    return 1111111 + score_difference


async def display_winners_info(wof_info):
    rewards = json.loads(wof_info.rewards)
    win_tickets = get_winner_tickets(wof_info.random_seed, len(rewards))
    sold_tickets = list(await db.get_all_sold_tickets_nums())

    numbers_won = []
    winners = [
        detect_winner(win_ticket, sold_tickets, numbers_won)
        for win_ticket in win_tickets
    ]
    winners = [winner for winner in winners if winner is not None]

    winners_info = []
    for winner_num, percent_reward in zip(winners, rewards):
        tg_id = await db.whose_ticket(winner_num)
        winners_info.append((winner_num, tg_id))

    return winners_info


if __name__ == '__main__':
    asyncio.run(spin_wheel_of_fortune())
