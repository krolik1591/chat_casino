from datetime import datetime

from peewee import fn

from bot.db import first_start
from bot.db.db import Balances, User, Token, Transactions, GameLogs


async def create_new_user(tg_id):
    return await User.create(tg_id=tg_id, timestamp_registered=datetime.utcnow(),
                             timestamp_last_active=datetime.utcnow())


async def add_new_transaction(user_id, token_id, is_deposit, logical_time, amount, tx_address, tx_hash):
    return await Transactions.create(user_id=user_id, token_id=token_id, is_deposit=is_deposit,
                                     logical_time=logical_time, amount=amount,
                                     tx_address=tx_address, tx_hash=tx_hash)


async def get_user_balances(user_id):
    result = await Token.select(Balances.amount or 0, Token.icon, Token.name) \
        .join(Balances, JOIN.LEFT_OUTER).switch(Balances) \
        .where((Balances.user_id == user_id) | (Balances.user_id.is_null(True))).dicts()

    return {
        i['name']: {**i, 'amount': i['amount'] or 0}  # replace `amount` field, set 0 instead None
        for i in result
    }


async def get_last_transaction(tg_id, token_id):
    return await Transactions.select(Transactions.tx_hash, fn.Max(Transactions.logical_time)) \
        .where(Transactions.user_id == tg_id, Transactions.token_id == token_id)


async def get_user_lang(tg_id):
    user_lang = await User.select(User.lang).where(User.tg_id == tg_id)
    if not user_lang:
        raise ValueError
    return user_lang[0].lang



async def set_user_lang(tg_id, new_lang):
    return await User.update({User.lang: new_lang}).where(User.tg_id == tg_id)


async def set_user_last_active(tg_id):
    return await User.update({User.timestamp_last_active: datetime.utcnow()}).where(User.tg_id == tg_id)


async def insert_game_log(user_id, token_id, game_info, bet, result, game):
    return await GameLogs.create(user_id=user_id, token_id=token_id, game_info=game_info,
                                 bet=bet, result=result, timestamp=datetime.utcnow(), game=game)


if __name__ == "__main__":
    async def test():
        await first_start()

        x = await get_user_balances(4)
        print(len(x))
        # print(await deposit_token(4, 1, 228))


    import asyncio

    asyncio.run(test())
