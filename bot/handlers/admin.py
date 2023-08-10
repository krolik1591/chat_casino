from aiogram import F, Router, types
from aiogram.filters import Command, Text

from bot.db.methods import create_new_promo, is_promo_in_db
from bot.utils.config_reader import config

router = Router()


@router.message(Text(startswith="/add_promo"))
async def add_promo(message: types.Message):
    print('hi bitch')
    admins = config.admin_ids
    if str(message.from_user.id) not in admins:
        return

    promo_name = message.text.removeprefix('/add_promo')
    if not promo_name:
        await message.answer("Введіть промо!")
        return

    if await is_promo_in_db(promo_name):
        await message.answer(f'Промо з назвою {promo_name} вже існує!')
        return

    await create_new_promo(message.from_user.id, promo_name.lstrip())
    await message.answer(f'Промокод <code>{promo_name}</code> створено!')
