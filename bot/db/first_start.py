from .db import ManualTXs, Token, User, Balance, Transactions, GameLog, Wallets_key, manager
from ..texts import DEMO_FUNDS_ICON, TON_FUNDS_ICON


async def first_start():
    if Token.table_exists():
        return

    print("First start, creating tables...")

    # await Token.create_table()
    await manager.create_tables(Wallets_key, Token, User, Balance, Transactions, ManualTXs, GameLog)

    await Token.create(name='DEMO', price=1, icon=DEMO_FUNDS_ICON)
    await Token.create(name='TON', price=100, icon=TON_FUNDS_ICON)