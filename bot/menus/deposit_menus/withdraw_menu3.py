from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.texts import WITHDRAW_MENU_TEXT3


def withdraw_menu_check(user_withdraw_amount, user_withdraw_address):
    text = WITHDRAW_MENU_TEXT3.format(user_withdraw_amount=user_withdraw_amount, user_withdraw_address=user_withdraw_address)
    kb = _keyboard()

    return text, kb


def _keyboard():
    kb = [
        [
            InlineKeyboardButton(text='Підтвердити', callback_data="approve")
        ],
        [
            InlineKeyboardButton(text='Назад', callback_data="withdraw")
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=kb)