import asyncio
import logging
from pathlib import Path
from pprint import pprint

import ton.tonlibjson
from TonTools.Contracts import Wallet
from aiogram.utils.i18n import I18n

from bot.consts.const import TON_INITIALISATION_FEE
from bot.db import db, manager, models
from bot.db.methods import add_new_transaction, update_withdraw_tx_state
from bot.menus.wallet_menus import deposit_menu
from bot.menus.wallet_menus.withdraw_menu import withdraw_result
from bot.tokens.token_ton import TonWrapper, ton_token


# todo оптимизация: сортировать пользователей по последней активности
from bot.utils.rounding import round_down


async def watch_txs(ton_wrapper: TonWrapper, bot, i18n: I18n):

    async def find_new_master_tx():
        try:
            new_txs = await find_new_master_txs(ton_wrapper)
            if new_txs is not None:
                for tx in new_txs:
                    await process_master_tx(tx, bot, i18n)

        except ton.tonlibjson.TonlibError as ex:
            logging.exception('TonLib error')

    async def find_new_user_tx_(user_):
        try:
            new_txs = await find_new_user_txs(ton_wrapper, user_)
            if new_txs is not None:
                user_wallet = ton_wrapper.get_wallet(user_.mnemonic)
                for tx in new_txs:
                    await set_user_locale_to_i18n(user_.user_id, i18n)
                    await process_user_tx(tx, user_.user_id, user_wallet, bot)

        except ton.tonlibjson.TonlibError as ex:
            logging.exception('TonLib error')

    while True:
        await find_new_master_tx()

        all_users_wallets = await db.get_all_user_wallets()
        coros = [find_new_user_tx_(user) for user in all_users_wallets]
        await asyncio.gather(*coros)

        await asyncio.sleep(10)


async def find_new_user_txs(ton_wrapper: TonWrapper, user: models.Wallets_key):
    user_account = await ton_wrapper.find_account(user.address)

    last_tx_from_blockchain = user_account.state.last_transaction_id
    last_tx_from_db = await db.get_last_transaction(user.user_id, ton_token.id)

    if last_tx_from_blockchain.hash == last_tx_from_db.tx_hash:
        # no new txs
        return

    return await ton_wrapper.get_account_transactions(
        user_account.address,
        last_tx_lt=last_tx_from_blockchain.lt,
        last_tx_hash=last_tx_from_blockchain.hash,
        first_tx_hash=last_tx_from_db.tx_hash)


async def find_new_master_txs(ton_wrapper: TonWrapper):
    master_account = await ton_wrapper.find_account(ton_wrapper.master_wallet.address)

    last_tx_from_blockchain = master_account.state.last_transaction_id
    last_tx_from_db = await db.get_last_tx_by_tx_type(3)    # withdraw

    if last_tx_from_blockchain.hash == last_tx_from_db.tx_hash:
        # no new txs
        return

    return await ton_wrapper.get_account_transactions(
        master_account.address,
        last_tx_lt=last_tx_from_blockchain.lt,
        last_tx_hash=last_tx_from_blockchain.hash,
        first_tx_hash=last_tx_from_db.tx_hash)


async def process_master_tx(tx, bot, i18n):

    if tx['source'] != TonWrapper.INSTANCE.master_wallet.address:   # not a withdrawal
        return

    with manager.pw_database.atomic():
        withdraw_tx, msg = await approve_withdraw(tx, bot, i18n)

        await add_new_transaction(
            user_id=withdraw_tx.user_id if withdraw_tx else 0,
            token_id="ton",
            amount=int(tx['value']),
            tx_type=3,  # withdraw
            tx_address=tx['destination'],
            tx_hash=tx['tx_hash'],
            logical_time=int(tx['tx_lt']),
            utime=tx['utime'],
            comment="|".join(msg) if msg else ''),


async def approve_withdraw(tx, bot, i18n):
    if not tx['msg'].startswith('withdrawv1'):
        return None, None
    msg = tx['msg'].removeprefix('withdrawv1').split('|')

    tx_id = int(msg[0])
    tx_utime = int(msg[1])

    try:
        withdraw_tx = await db.get_withdraw_tx_by_id(tx_id)
    except:
        logging.error('Find tx in master_wallet not in WithdrawTx')
        return None, msg

    if withdraw_tx.tx_address != tx['destination'] or withdraw_tx.utime != tx_utime:
        raise ValueError(f'Ne sovpadaet. \n'
                         f'Blockchain/db destination: {tx["destination"]} vs {withdraw_tx.tx_address} \n'
                         f'Blockchain/db utime: {tx_utime} vs {withdraw_tx.utime}')

    await update_withdraw_tx_state(tx_id, 'approved')

    await set_user_locale_to_i18n(withdraw_tx.user_id, i18n)

    text, keyboard = withdraw_result(True, int(withdraw_tx.amount) / 100)
    await bot.send_message(chat_id=withdraw_tx.user_id, text=text, reply_markup=keyboard)

    return withdraw_tx, msg


async def process_user_tx(tx, user_id, user_wallet: Wallet, bot):
    # поповнення рахунку для поповнення
    if tx['destination'] == user_wallet.address:
        await user_deposited(tx, bot, user_id, user_wallet)
    # переказ з юзер воллету на мастер воллет
    elif tx['source'] == user_wallet.address and tx['destination'] == TonWrapper.INSTANCE.master_wallet.address:
        await user_deposit_moved_to_master(tx, user_id)
    else:
        raise AssertionError('This should not happen')


async def user_deposited(tx, bot, user_id, user_wallet: Wallet):
    amount_ton = int(tx['value']) / 1e9

    user_init_state = await user_wallet.get_state()
    if user_init_state == 'uninitialized':

        inited = await init_user_wallet(bot, user_id, user_wallet)
        if inited:
            amount_ton -= TON_INITIALISATION_FEE
            await asyncio.sleep(30)  # wait for user wallet to be inited

    amount_gametokens = await ton_token.to_gametokens(amount_ton)
    #todo gametokens - fee
    #todo емаунт для поповнення дивитись по грошам що прийшли на мастер воллет
    await send_successful_deposit_msg(bot, user_id, amount_gametokens)

    promo_code = await db.need_a_bonus(user_id)
    with manager.pw_database.atomic():
        await db.update_user_balance(user_id, 'general', amount_gametokens)

        if promo_code:
            promo_bonus = round_down(amount_gametokens * promo_code.bonus / 100, 2)
            await db.update_user_balance(user_id, 'promo', promo_bonus)
            await db.update_wagers(user_id, promo_bonus, promo_code)

        await db.add_new_transaction(
            user_id=user_id,
            token_id=ton_token.id,
            amount=tx['value'],
            tx_type=1,  # deposit
            tx_address=tx['source'],
            tx_hash=tx['tx_hash'],
            logical_time=tx['tx_lt'],
            utime=tx['utime']
        )

    # одразу відправляємо отримані гроші на мастер воллет
    await transfer_to_master(user_wallet)


async def user_deposit_moved_to_master(tx, user_id):
    await db.add_new_transaction(
        user_id=user_id,
        token_id=ton_token.id,
        amount=tx['value'],
        tx_type=2,  # deposit moved to master
        tx_address=TonWrapper.INSTANCE.master_wallet.address,  # todo ?
        tx_hash=tx['tx_hash'],
        logical_time=tx['tx_lt'],
        utime=tx['utime']
    )


async def transfer_to_master(user_wallet: Wallet):
    try:
        await user_wallet.transfer_ton(TonWrapper.INSTANCE.master_wallet.address, amount=500_000_000, send_mode=128)
    except:
        logging.exception('cant transfer cause wallet not inited '
                          f'(юзер: {user_wallet.address} бомж лох дєб нема 0.014 на рахунку)')


async def init_user_wallet(bot, user_id, user_wallet):
    user_balance = await user_wallet.get_balance()  # nano ton
    if user_balance <= TON_INITIALISATION_FEE * 1e9:
        await send_failed_initiation_msg(bot, user_id)
        return False

    print('deploying account', user_wallet.address)
    await user_wallet.deploy()
    await send_successful_initiation_msg(bot, user_id)
    return True


async def send_successful_deposit_msg(bot, user_id, amount):
    text, keyboard = deposit_menu.successful_deposit_menu(amount=round(amount, 2))
    await bot.send_message(user_id, text, reply_markup=keyboard)


async def send_successful_initiation_msg(bot, user_id):
    text, keyboard = deposit_menu.deposit_account_initiation(is_successful_inited=True)
    await bot.send_message(user_id, text, reply_markup=keyboard)


async def send_failed_initiation_msg(bot, user_id):
    text, keyboard = deposit_menu.deposit_account_initiation(is_successful_inited=False)
    await bot.send_message(user_id, text, reply_markup=keyboard)


async def create_master_wallet(ton_wrapper):
    mw_id = 0

    all_users_wallets = await db.get_all_user_wallets()
    for wallet in all_users_wallets:
        if mw_id == wallet.user_id:
            return

    mw_address = ton_wrapper.master_wallet.address
    mw_mnemon_arr = ton_wrapper.master_wallet.mnemonics
    mw_mnemon_string = ','.join(mw_mnemon_arr)

    await db.create_user_wallet(mw_id, mw_address, mw_mnemon_string)


async def set_user_locale_to_i18n(user_id, i18n):
    user_lang = await db.get_user_lang(user_id)
    i18n.current_locale = user_lang
    i18n.set_current(i18n)
