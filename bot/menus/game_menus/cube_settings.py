from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.texts import CUBE_BET_BUTTON, CUBE_PLAY_TEXT, CUBE_SETTINGS_TEXT


def cube_settings(selected_setting, balance, bet, token_icon):
    text = CUBE_SETTINGS_TEXT.format(balance=balance, token_icon=token_icon)
    bet_text = CUBE_BET_BUTTON.format(bet=bet, token_icon=token_icon)
    kb = _keyboard(bet_text, selected_setting, play_text=CUBE_PLAY_TEXT)

    return text, kb


CUBE_VARIANTS = [
    ['1', '2', '3', '4', '5', '6'],
    ['12', '34', '56'],
    ['246', '135']
]

# todo i18n
CUBE_NAMES = {
    '1': '1',
    '2': '2',
    '3': '3',
    '4': '4',
    '5': '5',
    '6': '6',
    '12': '1-2',
    '34': '3-4',
    '56': '5-6',
    '246': 'Парне',
    '135': 'Непарне',
}


def _keyboard(bet_text, selected_setting, play_text):
    def btn_text(key_name):
        name = CUBE_NAMES[key_name]
        if key_name == selected_setting:
            return '*' + name + '*'
        return name

    settings_btns = [[
        InlineKeyboardButton(text=btn_text(key_name), callback_data="cube_game_settings_" + key_name)
        for key_name in row
    ] for row in CUBE_VARIANTS]

    kb = [
        [InlineKeyboardButton(text=bet_text, callback_data="bet")],
        *settings_btns,
        [
            InlineKeyboardButton(text='Назад', callback_data="tokens"),
            InlineKeyboardButton(text=play_text, callback_data="game_play")
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=kb)
