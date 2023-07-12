import time

from aiogram import Router, types
from aiogram.filters import Text
from aiogram.fsm.context import FSMContext

from bot.db import db
from bot.consts.const import START_POINTS
from bot.handlers.context import Context
from bot.handlers.games_handlers.m04_game_settings import settings_menu
from bot.handlers.games_handlers.m05_bets import bet_menu
from bot.handlers.states import Menu, StateKeys
from bot.menus.game_menus import select_balance_menu
from aiogram.utils.i18n import gettext as _


router = Router()


async def balances_menu(context: Context, msg_id):
    balances = await db.get_user_balances(context.user_id)
    text, keyboard = select_balance_menu(balances)

    await context.fsm_context.bot.edit_message_text(
        chat_id=context.user_id, message_id=msg_id, text=text, reply_markup=keyboard)
    await context.fsm_context.set_state(Menu.delete_message)


@router.callback_query(Text("select_balance_type"))
async def balance_type_show(call: types.CallbackQuery, state: FSMContext):
    context = await Context.from_fsm_context(call.from_user.id, state)
    await balances_menu(context, msg_id=call.message.message_id)


@router.callback_query(Text(startswith='set_balance_type_'))
async def set_balance_type(call: types.CallbackQuery, state: FSMContext):
    balance_type = call.data.removeprefix('set_balance_type_')
    if balance_type == 'promo':
        sum_bets, min_wager = await db.get_sum_bets_from_activated_promo_and_min_wager(call.from_user.id)
        if not min_wager or sum_bets > min_wager:
            await call.answer(_('M03_BALANCE_NOT_ENOUGH_BETS_TO_PLAY_PROMO'), show_alert=True)
            return
    await state.update_data(**{StateKeys.BALANCE_TYPE: balance_type})

    context = await Context.from_fsm_context(call.from_user.id, state)
    await settings_menu(context, msg_id=call.message.message_id)


# only for DEMO balance_type
@router.callback_query(Text("end_money"))
async def replenish_demo_balance(call: types.CallbackQuery, state: FSMContext):
    context = await Context.from_fsm_context(call.from_user.id, state)
    DEMO_TYPE = 'demo'
    assert context.balance_type == DEMO_TYPE, "REPLENISH NOT A DEMO TOKEN"

    await db.update_user_balance(call.from_user.id, DEMO_TYPE, START_POINTS)
    await db.add_new_transaction(call.from_user.id, DEMO_TYPE, 500, int(time.time()), START_POINTS, 'demo_address',
                                 'demo_hash', int(time.time()))

    # context with updated balance
    context = await Context.from_fsm_context(call.from_user.id, state)
    await bet_menu(context, msg_id=call.message.message_id)
