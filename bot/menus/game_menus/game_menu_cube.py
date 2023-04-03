from pprint import pprint

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.const import MIN_BET
from bot.menus.main_menu import balance_text
from bot.texts import DEFAULT_BALANCE_TEXT, DEMO_FUNDS_ICON, DEFAULT_PLAY_TEXT


def game_menu_cube(
        balance, bet, token_id, which_game,
        text=DEFAULT_BALANCE_TEXT,
        btns_before_bet=[],
        btns_after_bet=[],
        token_icon=DEMO_FUNDS_ICON,
        play_text=DEFAULT_PLAY_TEXT,
):
    text = text.format(balance=balance, bet=bet)

    add_replenish_btn = bet <= balance >= MIN_BET
    kb = _keyboard(bet, btns_before_bet, btns_after_bet, token_icon, play_text, add_replenish_btn, token_id)

    return text, kb


def _keyboard(
        bet,
        btns_before_bet, btns_after_bet,
        token_icon, play_text,
        add_replenish_btn, token_id
):
    kb = [

        *([] if add_replenish_btn else _btn_replenish(token_id)),
        *btns_before_bet,
        [
            InlineKeyboardButton(text=f'⚙️ Сума ставки • {bet}{token_icon}', callback_data="cube_change_bet"),
        ],
        [
            InlineKeyboardButton(text='1', callback_data="bet_minus"),
            InlineKeyboardButton(text='2', callback_data="bet_token_icon"),
            InlineKeyboardButton(text='3', callback_data="bet_plus"),
            InlineKeyboardButton(text='4', callback_data="bet_minus"),
            InlineKeyboardButton(text='5', callback_data="bet_token_icon"),
            InlineKeyboardButton(text='6', callback_data="bet_minus")
        ],
        [
            InlineKeyboardButton(text='1-2', callback_data="bet_min"),
            InlineKeyboardButton(text='3-4', callback_data="bet_x2"),
            InlineKeyboardButton(text='5-6', callback_data="bet_max")
        ],
        [
            InlineKeyboardButton(text='Парне', callback_data="casino"),
            InlineKeyboardButton(text='Непарне', callback_data="game_play")
        ],
        *btns_after_bet,
        [
            InlineKeyboardButton(text='Назад', callback_data="casino"),
            InlineKeyboardButton(text=play_text, callback_data="game_play")
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=kb)


def _btn_replenish(token_id):
    if token_id != 1:
        return []
    return [[InlineKeyboardButton(text='Дай гроші', callback_data="end_money")]]
