import logging

import ton
from bot.db.db import Wallets_key
from bot.db.methods import get_all_users, get_last_transaction, get_token_by_id
from bot.ton.wallets import TonWrapper
from bot.db.db import manager
from bot.db import methods as db

import time
from time import monotonic as timer

TOKEN_ID = 2


async def watch_txs(ton_wrapper: TonWrapper):
    while True:
        print('WATCH SUKA')
        start = timer()  # remember when the loop starts
        interval = 10  # 1 iteration per 10 sec
        for _ in range(1):
            all_users_wallet = await get_all_users()
            try:
                for user in all_users_wallet:
                    await find_new_user_tx(ton_wrapper, user)

                    time.sleep(interval - timer() % interval)

            except ton.tonlibjson.TonlibError as ex:
                logging.exception('TonLib error')


async def find_new_user_tx(ton_wrapper: TonWrapper, user: Wallets_key):
    master_address = ton_wrapper.master_wallet.address
    account = await ton_wrapper.find_account(user.address)

    last_tx_from_blockchain = account.state.last_transaction_id

    last_tx_from_db = await get_last_transaction(user.user_id, TOKEN_ID)  # типу беремо з бд

    if last_tx_from_blockchain.hash != last_tx_from_db.tx_hash:
        print("NEW TX!")
        # добуваємо нові транзи

        new_tx = await ton_wrapper.get_account_transactions(
            account.address,
            last_tx_lt=last_tx_from_blockchain.lt,
            last_tx_hash=last_tx_from_blockchain.hash,
            first_tx_hash=last_tx_from_db.tx_hash)


        token = await get_token_by_id(TOKEN_ID)

        for tx in new_tx:
            await process_tx(tx, token, user.user_id, master_address, user.address)

    else:
        print("NO NEW TX :(")


async def process_tx(tx, token, user_id, master_address, user_address):
    # поповнення рахунку для поповнення
    if tx['destination'] == user_address:
        tx_type = 1
        tx_address = tx['source']

        amount = int(tx['value']) / 1e9 * token.price
        with manager.pw_database.atomic():
            await db.deposit_token(user_id, token.token_id, amount)
            await db.add_new_transaction(user_id, token.token_id, tx['value'], tx_type, tx_address, tx['tx_hash'],
                                         logical_time=tx['tx_lt'], utime=tx['utime'])

        # одразу відправляємо отримані гроші на мастер воллет
        # await user_wallet.transfer_ton(master_wallet.address, 0, send_mode=128) # так надо  # todo

    # переказ з юзер воллету на мастер воллет
    elif tx['source'] == user_address and tx['destination'] == master_address:
        tx_type = 2
        tx_address = master_address
        await db.add_new_transaction(user_id, token.token_id, tx['value'], tx_type, tx_address, tx['tx_hash'],
                                     logical_time=tx['tx_lt'], utime=tx['utime'])


    # переказ з мастер воллету на юзер воллет
    elif tx['source'] == master_address and tx['destination'] == user_address:
        tx_type = 3
        tx_address = user_address
        await db.add_new_transaction(user_id, token.token_id, tx['value'], tx_type, tx_address, tx['tx_hash'],
                                     logical_time=tx['tx_lt'], utime=tx['utime'])


    else:
        raise AssertionError('This should not happen')
