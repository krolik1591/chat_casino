from TonTools import *
from TonTools.Contracts.Wallet import Wallet
from aiogram import Router, types
from aiogram.dispatcher.fsm.context import FSMContext

from bot.db.methods import get_user_wallet
from bot.menus.deposit_menus.replenish_menu import replenish_menu
from bot.ton.wallets import TonWrapper

flags = {"throttling_key": "default"}
router = Router()


@router.callback_query(text=["replenish"])
async def replenish(call: types.CallbackQuery, state: FSMContext):
    user_wallet = await get_user_wallet(call.from_user.id)

    text, keyboard = replenish_menu(user_wallet.address)
    await call.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(text=["delete_replenish_message"])
async def del_replenish_message(call: types.CallbackQuery, state: FSMContext):
    await call.message.delete()


@router.callback_query(text=["ton_check"])
async def ton_check(call: types.CallbackQuery, state: FSMContext):
    master_wallet, user_wallet = await prepare_wallets_to_work(state, call.from_user.id)

    user_init_condition = await user_wallet.get_state()

    if user_init_condition == 'uninitialized':
        # todo if balance < 13 centiv:  fuck off
        print('мінус 13 центів сучара')
        await user_wallet.deploy()

    mw_init_condition = await master_wallet.get_state()
    if mw_init_condition == 'uninitialized':
        print('mw not inited')
        non_bounceable_master_wallet_address = Address(master_wallet.address).to_string(True, True, False)
        await user_wallet.transfer_ton(destination_address=non_bounceable_master_wallet_address, amount=0.02)
        await master_wallet.deploy()

    print(user_init_condition, mw_init_condition)

    mw_balance = await master_wallet.get_balance()
    print('mw balance', mw_balance)



async def prepare_wallets_to_work(state, user_id):
    ton_client: TonWrapper = state.bot.ton_client

    master_wallet = ton_client.master_wallet

    user_wallet_info = await get_user_wallet(user_id)
    user_mnemonic = user_wallet_info.mnemonic.split(',')
    user_wallet = Wallet(provider=ton_client, mnemonics=user_mnemonic)

    return master_wallet, user_wallet
