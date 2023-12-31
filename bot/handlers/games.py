import asyncio
import json
import random
from pprint import pprint

from aiogram import F, Router, types
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command, Text
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.consts.casino_check import get_casino_result
from bot.consts.dice_texts import get_dice_text
from bot.consts.const import DELAY_BEFORE_SEND_RESULT, GAMES_LIST, PLAYER_LVLS
from bot.db import methods as db
from bot.utils.config_reader import config

router = Router()

KB_GAMES = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='🎲', callback_data="roll_cube"),
     InlineKeyboardButton(text='🎯', callback_data="roll_darts"),
     InlineKeyboardButton(text='🏀', callback_data="roll_basket")],
    [InlineKeyboardButton(text='⚽', callback_data="roll_football"),
     InlineKeyboardButton(text='🎳', callback_data="roll_bowling"),
     InlineKeyboardButton(text='🎰', callback_data="roll_casino")],
])


@router.my_chat_member(lambda member: member.new_chat_member.status == 'member')
async def on_user_join(chat_member: types.ChatMemberUpdated, state: FSMContext):
    bot_id = state.bot.id
    if chat_member.new_chat_member.user.id == bot_id:
        inviter_user_id = chat_member.from_user.id
        admins = config.admin_ids
        if str(inviter_user_id) not in admins:
            await state.bot.send_message(chat_member.chat.id, "Тільки адмін може додавати бота!")
            await state.bot.leave_chat(chat_member.chat.id)
            return


@router.message(Command("casino"))
async def casino(message: types.Message):
    await add_user_to_db(message.from_user.id, message.from_user.username)

    user_num = message.text.removeprefix("/casino")
    try:
        user_num = int(user_num)
        if not 1 <= user_num <= 100:
            raise ValueError
    except ValueError:
        await message.answer("Ви маєте ввести /casino 'number' (де number - ціле число від 1 до 100)")
        return

    random_num = random.randint(1, 100)
    if user_num != random_num:
        await message.answer(f"Ви програли, число було {random_num}")
        return

    available_promo = await db.get_available_user_promo(message.from_user.id)
    if not available_promo:
        await message.answer("Ви вгадали!")
        return
    new_promo_name = random.choice(available_promo)
    await db.add_new_promo_to_user(message.from_user.id, new_promo_name)
    await message.answer(f"Ви виграли промокод! Для перегляду введіть в приватних повідомленнях /my_promos")


@router.message(Command("stats"))
async def stats(message: types.Message):
    await db.update_username(message.from_user.id, message.from_user.username)
    bowling_point, football_point, basket_point, points_sum, bowling_strike, casino_point = await get_user_stats(
        message.from_user.id)

    player_lvl = ''
    for point, name in PLAYER_LVLS.items():
        if points_sum < point:
            player_lvl = name
            break

    user_link = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'
    text = f"{user_link} Твій результат:\n" \
           f"🎰 Виграно поінтів в казино: {casino_point}\n" \
           f"⚽ Забито голів: {football_point}\n" \
           f"🏀 Закинуто м'ячів: {basket_point}\n" \
           f"🎳 Збито кеглів: {bowling_point}\n" \
           f"       Страйків: {bowling_strike}\n\n" \
           f"Твій статус гравця: {player_lvl}"

    await message.answer(f'Статистика:\n\n{text}')


@router.message(Command("admin_stats"))
async def admin_stats(message: types.Message):
    admins = config.admin_ids
    if str(message.from_user.id) not in admins:
        await message.answer("Тільки адмін може переглядати адмін-статистику!")
        return

    result = {}

    user_ids = await db.get_unique_users()
    for user_id in user_ids:
        _, _, _, points_sum, _, _ = await get_user_stats(user_id)
        result[user_id] = points_sum

    sorted_result = dict(sorted(result.items(), key=lambda item: item[1], reverse=True))

    text = ''
    for index, (user_id, points_sum) in enumerate(sorted_result.items(), start=1):
        username = await db.get_username_by_id(user_id)
        user_link = f'<a href="tg://user?id={user_id}">{user_id}</a>'
        text += f"{index}. @{username} (id: {user_link}): {points_sum} поінтів\n"

    await message.answer(f'Адмін статистика:\n\n{text}')


@router.message(Text(startswith="/roll_"))
async def roll_command(message: types.Message, state: FSMContext):
    await add_user_to_db(message.from_user.id, message.from_user.username)

    bot_username = '@' + (await state.bot.me()).username
    game = message.text.removeprefix("/roll_").removesuffix(bot_username)

    await do_game(game, message, message.from_user)


@router.callback_query(Text(startswith="roll_"))
async def roll_btn(call: types.CallbackQuery, state: FSMContext):
    await call.answer()

    await add_user_to_db(call.from_user.id, call.from_user.username)

    game = call.data.removeprefix("roll_")
    await do_game(game, call.message, call.from_user)


async def do_game(game, message: types.Message, user: types.User):
    game_emoji = GAMES_LIST[game]
    msg = await message.answer_dice(emoji=game_emoji)
    await asyncio.sleep(DELAY_BEFORE_SEND_RESULT)

    if game_emoji == '🎰':
        text, value = get_casino_result(msg.dice.value)
        await db.add_game_result(user.id, game_emoji, value)
    else:
        text = get_dice_text(game_emoji, msg.dice.value)
        await db.add_game_result(user.id, game_emoji, msg.dice.value)

    link = f'<a href="tg://user?id={user.id}">{user.first_name}</a>\n'
    await msg.reply(link+text, reply_markup=KB_GAMES)





@router.message(Command("games"))
async def games(message: types.Message):
    text = 'Список доступних ігор:'
    await message.answer(text, reply_markup=KB_GAMES)


async def get_user_stats(user_id):
    all_stats = await db.get_user_stats(user_id)
    casino_point = await db.get_user_casino_point(user_id)

    bowling_stat = all_stats.get('🎳', '')
    bowling_strike = bowling_stat.count('6')
    bowling_point = bowling_stat.count('2') + \
                    bowling_stat.count('3') * 3 + \
                    bowling_stat.count('4') * 4 + \
                    bowling_stat.count('5') * 5 + \
                    bowling_stat.count('6') * 6
    football_point = sum(1 for char in all_stats.get('⚽', '') if char in '345')
    basket_point = sum(1 for char in all_stats.get('🏀', '') if char in '45')
    points_sum = bowling_point + football_point + basket_point + casino_point

    return bowling_point, football_point, basket_point, points_sum, bowling_strike, casino_point


async def add_user_to_db(user_id, username):
    if not await db.is_user_exists(user_id):
        await db.add_new_user(user_id, username)
