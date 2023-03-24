from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.texts import REPLENISH_MENU_TEXT


def replenish_menu(wallet_address):
    print(wallet_address)
    text = REPLENISH_MENU_TEXT.format(wallet_address=wallet_address)
    kb = _keyboard(wallet_address)

    return text, kb


def _keyboard(wallet_address):
    kb = [
        [
            InlineKeyboardButton(text='Відкрити Tonkeeper',
                                 url=f"https://app.tonkeeper.com/transfer/{wallet_address}")
        ],
        [
            InlineKeyboardButton(text='Todo link',
                                 url=f"https://app.tonkeeper.com/transfer/{wallet_address}")
        ],
        [
            InlineKeyboardButton(text='Мій гаманець', callback_data="deposit"),
            InlineKeyboardButton(text='Оновити баланс', callback_data="ton_check")
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=kb)