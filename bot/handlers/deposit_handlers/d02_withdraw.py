import time

import tonsdk.utils
from TonTools import Address
from aiogram import Router, types
from aiogram.dispatcher.fsm.context import FSMContext
from aiogram.types import Message

from bot.const import MAXIMUM_WITHDRAW, MAXIMUM_WITHDRAW_DAILY, MIN_WITHDRAW
from bot.db.methods import add_new_manual_tx, get_last_manual_transaction, get_token_by_id, get_user_balance, \
    get_user_daily_total_amount, \
    update_user_balance
from bot.handlers.context import Context
from bot.handlers.states import Menu, StateKeys
from bot.menus.deposit_menus.withdraw_menu import withdraw_menu_err
from bot.menus.deposit_menus.withdraw_menu.withdraw_approve_menu import withdraw_approve_menu
from bot.menus.deposit_menus.withdraw_menu.withdraw_menu1 import withdraw_menu_amount
from bot.menus.deposit_menus.withdraw_menu.withdraw_menu2 import withdraw_menu_address
from bot.menus.deposit_menus.withdraw_menu.withdraw_menu3 import withdraw_menu_check
from bot.ton.withdraw_cash import withdraw_cash_to_user

flags = {"throttling_key": "default"}
router = Router()


@router.callback_query(text=["withdraw"])
async def withdraw(call: types.CallbackQuery, state: FSMContext):
    TOKEN_ID = 2
    await state.update_data(**{StateKeys.TOKEN_ID: TOKEN_ID})
    token = await get_token_by_id(TOKEN_ID)
    text, keyboard = withdraw_menu_amount(token.price)
    await call.message.edit_text(text, reply_markup=keyboard)

    await state.update_data(**{StateKeys.LAST_MSG_ID: call.message.message_id})

    await state.set_state(Menu.withdraw_amount)


@router.message(state=Menu.withdraw_amount)
async def withdraw_user_text(message: Message, state: FSMContext):
    await message.delete()
    context = await Context.from_fsm_context(message.from_user.id, state)

    round_user_withdraw = await check_user_input_amount(message, context)
    if round_user_withdraw is None:
        return

    await state.update_data(user_withdraw_amount=round_user_withdraw)
    last_msg = (await state.get_data()).get(StateKeys.LAST_MSG_ID)
    token_id = (await state.get_data()).get(StateKeys.TOKEN_ID)

    last_manual_tx = await get_last_manual_transaction(message.from_user.id, token_id)
    if last_manual_tx['withdraw_state'] is not None:
        text, keyboard = withdraw_menu_err.manual_tx_in_process()
        await state.bot.send_message(message.from_user.id, text, reply_markup=keyboard)
        return

    text, keyboard = withdraw_menu_address()  # input address
    await state.bot.edit_message_text(text, reply_markup=keyboard, chat_id=message.chat.id, message_id=last_msg)
    await state.set_state(Menu.withdraw_address)


@router.message(state=Menu.withdraw_address)
async def withdraw_user_address(message: Message, state: FSMContext):
    await message.delete()
    try:
        user_withdraw_address = Address(message.text)
    except tonsdk.utils.InvalidAddressError:
        text, keyboard = withdraw_menu_err.withdraw_err_incorrect_address()
        await message.answer(text, reply_markup=keyboard)
        return

    if user_withdraw_address.is_test_only:
        text, keyboard = withdraw_menu_err.withdraw_err_testnet_address()
        await message.answer(text, reply_markup=keyboard)
        return

    token_id = (await state.get_data()).get(StateKeys.TOKEN_ID)
    token = await get_token_by_id(token_id)

    user_withdraw_amount = (await state.get_data()).get('user_withdraw_amount')
    last_msg = (await state.get_data()).get(StateKeys.LAST_MSG_ID)
    await state.update_data(user_withdraw_address=user_withdraw_address.to_string())

    text, keyboard = withdraw_menu_check(user_withdraw_amount, user_withdraw_address.to_string(), token.price)
    await state.bot.edit_message_text(text, reply_markup=keyboard, chat_id=message.chat.id, message_id=last_msg)
    await state.set_state(Menu.withdraw_amount_approve)


@router.message(state=Menu.withdraw_amount_approve)
async def withdraw_user_amount_approve(message: Message, state: FSMContext):
    await message.delete()
    context = await Context.from_fsm_context(message.from_user.id, state)
    round_user_withdraw = await check_user_input_amount(message, context)
    if round_user_withdraw is None:
        return

    await state.update_data(user_withdraw_amount=round_user_withdraw)

    user_withdraw_address = (await state.get_data()).get('user_withdraw_address')
    last_msg = (await state.get_data()).get(StateKeys.LAST_MSG_ID)
    token_id = (await state.get_data()).get(StateKeys.TOKEN_ID)
    token = await get_token_by_id(token_id)

    text, keyboard = withdraw_menu_check(round_user_withdraw, user_withdraw_address, token.price)
    await state.bot.edit_message_text(text, reply_markup=keyboard, chat_id=message.chat.id, message_id=last_msg)


@router.callback_query(text=["approve"])
async def approve_withdraw(call: types.CallbackQuery, state: FSMContext):
    user_withdraw_amount = (await state.get_data()).get('user_withdraw_amount')
    user_withdraw_address = (await state.get_data()).get('user_withdraw_address')

    token_id = (await state.get_data()).get(StateKeys.TOKEN_ID)
    token = await get_token_by_id(token_id)
    ton_amount = user_withdraw_amount / token.price

    text, keyboard = withdraw_approve_menu(user_withdraw_amount)
    await call.message.edit_text(text, reply_markup=keyboard)

    correct_withdraw_tx = await check_unresolved_manual_tx(call, token, user_withdraw_amount, user_withdraw_address)
    if correct_withdraw_tx is False:
        return

    withdraw_amount_price = ton_amount * token.price
    await update_user_balance(call.from_user.id, token.token_id, -withdraw_amount_price)

    await withdraw_cash_to_user(state, user_withdraw_address, ton_amount, call.from_user.id, token)


async def check_user_input_amount(message, context):
    try:
        user_withdraw = float(message.text)
    except ValueError:
        return
    round_user_withdraw = round(user_withdraw, 2)

    token_id = context.state.get(StateKeys.TOKEN_ID)
    token = await get_token_by_id(token_id)
    user_balance = await get_user_balance(message.from_user.id, token_id)
    ton_amount = user_withdraw * token.price

    if round_user_withdraw < MIN_WITHDRAW:
        text, keyboard = withdraw_menu_err.withdraw_too_small(token_price=token.price)
        await message.answer(text, reply_markup=keyboard)
        return

    if round_user_withdraw > user_balance:
        text, keyboard = withdraw_menu_err.withdraw_err_insufficient_funds()
        await message.answer(text, reply_markup=keyboard)
        return

    if ton_amount > MAXIMUM_WITHDRAW:
        text, keyboard = withdraw_menu_err.withdraw_too_big(user_withdraw_amount=round_user_withdraw)
        await message.answer(text, reply_markup=keyboard)
        return

    return round_user_withdraw


async def check_unresolved_manual_tx(call, token, user_withdraw_amount, user_withdraw_address):
    user_daily_total_amount_nano_ton = await get_user_daily_total_amount(call.from_user.id)
    total_amount_price = user_daily_total_amount_nano_ton / 10**9 * token.price
    ton_amount = user_withdraw_amount / token.price

    if total_amount_price + user_withdraw_amount >= MAXIMUM_WITHDRAW_DAILY * token.price:
        text, keyboard = withdraw_menu_err.reached_daily_limit(MAXIMUM_WITHDRAW_DAILY*token.price - total_amount_price)
        await call.answer(chat_id=call.from_user.id, text=text, reply_markup=keyboard)

        await add_new_manual_tx(user_id=call.from_user.id, nano_ton_amount=ton_amount * 10**9, token_id=token.token_id,
                                price=token.price, tx_address=user_withdraw_address,
                                utime=int(time.time()), withdraw_state='rejected')
        return False
    return True


