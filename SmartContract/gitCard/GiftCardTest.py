# coding=utf-8
# author: Li MingLei
# date: 2021-10-25
from roxe_libs.pub_function import setCustomLogger
from roxe_libs.Global import Global
from roxe_libs import settings, ApiUtils
from roxepy.clroxe import Clroxe
from roxepy.types import Abi
from roxepy import ROXEKey
import datetime
import json
import os
import pytz

logger = setCustomLogger("test", os.path.join(os.path.dirname(os.path.abspath(__file__)), "gitCardTest.log"), isprintsreen=True, isrotaing=True, logRedirectHandler=True)
Global.setValue(settings.logger_name, logger.name)
Global.setValue(settings.enable_trace, True)


# Roxe Chain rpc地址
# rpc_host = "http://testnet.roxe.tech:18888"
rpc_host = "http://192.168.37.22:18888"
# rpc_host = "http://47.242.190.66:18888"
user_account = "rsstestbtc11"
user_key = "5JYy1FU6EiAS4DCVttEB4QxKo8BePxzpnY8wei6Sy1z4z5XkCgK"
user_pub_key = "ROXE5qEcKJWqicsarqicWkyf25fem7BF2S1T6HLKzyN7A66qXKTV26"

user_account2 = "giftcard1111"
user_key2 = "5K68D9H8bbgu288ShDCtniU6FuMvZT1gMBCaiNh3bN7642Yqcvn"
user_pub_key2 = "ROXE85QQYo84FRFPcPnAoLHKNWG96De155okjqmgT1XhHaCjr9uQMb"

credit_account = "roxe.credit"
credit_key = "5J54M8sWW4eKrxzYp8LmvBDVRSZB2ivzcU1LvonZW4T5ntLcjPK"

gift_card_account = "roxe.tokenz"
gift_card_key = "5KHGj8nePrd1sEPe2RfbomN5sjyYnEZjLfVYcvBLds4KeTLouaS"
gift_card_pub_key = "ROXE8PZJeGRnkuKftwzZteYNpvHcLEcwQyiidan7WZvC9Pc6L1pR4d"

gift_symbol = "JETHRO"
gift_decimal = 6

group = "rogrouptest1"
# group = "roxegiftcard"
# group = "rogiftcard"
group_key = "5J77cNSXBSzECS82RXuy17iaPTmoSFVdMnzVb1zHrUKiupL2Mkj"


ratio_base = int(10 ** 8)
token_base = int(10 ** 6)


def calPlatAmount(act_info, group_info, order_info):
    plat_ratio = act_info["rows"][0]["_ACTIVITY_STORE_"]["_PLATFORM_SHARE_RATIO_"] / ratio_base
    logger.info(f"平台分账的系数: {plat_ratio}")
    invite_ratio = act_info["rows"][0]["_ACTIVITY_STORE_"]["_REBATE_SHARE_RATIO_"] / ratio_base
    logger.info(f"邀请人返利的系数: {invite_ratio}")
    sponsor_ratio = act_info["rows"][0]["_ACTIVITY_STORE_"]["_SPONSOR_SHARE_RATIO_"] / ratio_base
    logger.info(f"发起人返利的系数: {sponsor_ratio}")
    order_ratio = act_info["rows"][0]["_ACTIVITY_STORE_"]["_ORDER_REBATE_SHARE_RATIO_"] / ratio_base
    logger.info(f"订单返利的系数: {order_ratio}")
    pay_amount = int(order_info["rows"][0]["_PAYAMOUNT_"])
    total_plat = int(pay_amount * plat_ratio)
    busi_amount = order_info["rows"][0]["_PAYAMOUNT_"] - total_plat - int(group_info["rows"][0]["_BUSINESSAMOUNT_"])
    logger.info(f"商家应分得: {busi_amount}")
    invite_amount = int(pay_amount * invite_ratio)
    if order_info["rows"][0]["_INVITOR_"] == "roxe.null":
        invite_amount = 0
    sponsor_amount = int(pay_amount * sponsor_ratio)
    order_amount = int(pay_amount * order_ratio)
    logger.info(f"发起人应分得: {sponsor_amount}")
    logger.info(f"邀请人应分得: {invite_amount}")
    logger.info(f"订单获利的收益人应分得: {order_amount}")
    plat_amount = total_plat - sponsor_amount - invite_amount - int(group_info["rows"][0]["_PLATFORMAMOUNT_"]) - order_amount
    logger.info(f"平台应分得: {plat_amount}")
    return busi_amount, plat_amount, sponsor_amount, invite_amount, order_amount


class GiftCard:

    def __init__(self, chain_host):
        self.chain_client = Clroxe(chain_host)
        self.script_dir = os.path.dirname(os.path.realpath(__file__))
        self.creditAbi = self.getAbiObj('roxe.credibility.abi')
        self.giftCardAbi = self.getAbiObj('roxe.giftcard.abi')
        self.tokenAbi = self.getAbiObj('roxe.token.abi')
        self.purchaseAbi = self.getAbiObj('group.purchase.abi')

    def getAbiObj(self, abi_file_name):
        abi_file = os.path.join(self.script_dir, abi_file_name)
        with open(abi_file) as rf:
            abj_obj = Abi(json.load(rf))
        return abj_obj

    def transferToken(self, fromAccount, fromKey, toAccount, amount, contract):
        arguments = {
            "from": fromAccount,  # sender
            "to": toAccount,  # receiver
            "quantity": amount,  # In Roxe
            "memo": "",
        }
        payload = {
            "account": contract,
            "name": "transfer",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        # abi_data = self.giftCardAbi.json_to_bin(payload['name'], arguments)
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        logger.info(f"转账结果: {resp}")
        return resp

    def allowTransfer(self, account, account_key, pub_key, to_contract):
        arguments = {
            "account": account,
            "permission": "active",
            "parent": "owner",
            "auth": {
                "threshold": 1,
                "keys": [{"key": pub_key, "weight": 1}],
                "accounts": [
                    {
                        "permission": {
                            "actor": to_contract,
                            "permission": "roxe.code"
                        },
                        "weight": 1
                    }
                ],
                "waits": [],
            },
        }
        payload = {
            "account": "roxe",
            "name": "updateauth",
            "authorization": [{
                "actor": account,
                "permission": "owner",
            }],
        }

        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        # abi_data = self.giftCardAbi.json_to_bin(payload['name'], arguments)
        logger.info(F"action: {arguments}")
        # print(abi_data)
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(account_key)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp

    # 礼品卡token合约
    def createGiftCardToken(self, issuer, maximum_supply):
        arguments = {
            "issuer": issuer,
            "maximum_supply": maximum_supply,
        }
        payload = {
            "account": gift_card_account,
            "name": "create",
            "authorization": [{
                "actor": gift_card_account,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        # abi_data = self.giftCardAbi.json_to_bin(payload['name'], arguments)
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(gift_card_key)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp

    def issueGiftCardToken(self, fromAccount, toAccount, quantity, fromKey, memo=""):
        arguments = {
            "from": fromAccount,
            "to": toAccount,
            "quantity": quantity,
            "memo": memo,
        }
        payload = {
            "account": gift_card_account,
            "name": "issue",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }

        # data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)
        abi_data = self.giftCardAbi.json_to_bin(payload['name'], arguments)
        logger.info(F"action: {arguments}")
        # print(abi_data)
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp

    def transferGiftCardToken(self, fromAccount, toAccount, quantity, fromKey, memo=""):
        arguments = {
            "from": fromAccount,
            "to": toAccount,
            "quantity": quantity,
            "memo": memo,
        }
        payload = {
            "account": gift_card_account,
            "name": "transfer",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }

        # data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)
        abi_data = self.giftCardAbi.json_to_bin(payload['name'], arguments)
        logger.info(F"action: {arguments}")
        # print(abi_data)
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp

    def retireGiftCardToken(self, fromAccount, quantity, fromKey, memo="", retireAccount=None):
        retireAccount = retireAccount if retireAccount else fromAccount
        arguments = {
            "from": retireAccount,
            "quantity": quantity,
            "memo": memo,
        }
        payload = {
            "account": gift_card_account,
            "name": "retire",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        logger.info(F"action: {arguments}")
        # data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)
        abi_data = self.giftCardAbi.json_to_bin(payload['name'], arguments)
        # print(abi_data)
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp

    def addAuthor(self, sym, author, fromAccount=gift_card_account, fromKey=gift_card_key):
        arguments = {
            "sym": sym,
            "author": author,
        }
        payload = {
            "account": gift_card_account,
            "name": "addauthor",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        logger.info(F"action: {arguments}")
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        # abi_data = self.giftCardAbi.json_to_bin(payload['name'], arguments)
        # print(abi_data)
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp

    def deleteAuthor(self, sym, author, fromAccount=gift_card_account, fromKey=gift_card_key):
        arguments = {
            "sym": sym,
            "from": author,
        }
        payload = {
            "account": gift_card_account,
            "name": "delauthor",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        logger.info(F"action: {arguments}")
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        # abi_data = self.giftCardAbi.json_to_bin(payload['name'], arguments)
        # print(abi_data)
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp

    def test_createGiftCard_normal(self, max_supply):
        res = self.createGiftCardToken(user_account, "100.000000 ab")
        logger.info(f"交易结果: {res}")
        state = self.chain_client.get_table(gift_card_account, max_supply.split(" ")[1], "stat")
        logger.info(f"礼品卡: {state}")

        assert state["rows"][0]["max_supply"] == max_supply
        assert state["rows"][0]["issuer"] == user_account
        assert state["rows"][0]["authors"] == [user_account]
        assert state["rows"][0]["fee"] == 0
        assert state["rows"][0]["fixed"] == 1
        assert state["rows"][0]["percent"] == 0
        assert state["rows"][0]["maxfee"] == 0
        assert state["rows"][0]["minfee"] == 0
        assert state["rows"][0]["useroc"] == 1

    def test_createGiftCard_symbolInvalid(self):
        res = self.createGiftCardToken(user_account, "100.000000 ab")
        logger.info(f"交易结果: {res}")
        assert "invalid symbol name" in res["error"]["details"][0]["message"]
        state = self.chain_client.get_table(gift_card_account, "ab", "stat")
        logger.info(f"礼品卡: {state}")
        assert state["rows"] == []

    def test_createGiftCard_symbolRepeat(self):
        res = self.createGiftCardToken(user_account, "100.000000 USD")
        logger.info(f"交易结果: {res}")
        assert "token with symbol already exists" in res["error"]["details"][0]["message"]
        state = self.chain_client.get_table(gift_card_account, "ab", "stat")
        logger.info(f"礼品卡: {state}")
        assert state["rows"] == []

    def test_createGiftCard_maxSupplyInvalid(self):
        res = self.createGiftCardToken(user_account, "0.000000 USD")
        logger.info(f"交易结果: {res}")
        assert "max-supply must be positive" in res["error"]["details"][0]["message"]

        res = self.createGiftCardToken(user_account, "-1.000000 USD")
        logger.info(f"交易结果: {res}")
        assert "max-supply must be positive" in res["error"]["details"][0]["message"]

        state = self.chain_client.get_table(gift_card_account, "ab", "stat")
        logger.info(f"礼品卡: {state}")
        assert state["rows"] == []

    def test_issue_normal(self, quantity="1.000000 USD", toAccount="giftcard1111", memo=""):
        symbol = quantity.split(" ")[1]
        balance1 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"资产: {balance1}")
        state = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state}")

        res = self.issueGiftCardToken(user_account, toAccount, quantity, user_key, memo)
        logger.info(f"交易的结果: {res}")
        state2 = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state2}")

        balance2 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"资产: {balance2}")

        supply1 = float(state["rows"][0]["supply"].split(" ")[0]) if state["rows"] else 0
        supply2 = float(state2["rows"][0]["supply"].split(" ")[0])
        add_amount = float(quantity.split(" ")[0])
        assert supply1 + add_amount == supply2

        find_currency_balance = [i for i in balance1 if symbol in i]
        amount1 = float(find_currency_balance[0].split(" ")[0]) if find_currency_balance else 0
        amount2 = float([i for i in balance2 if symbol in i][0].split(" ")[0])
        assert amount2 == amount1 + add_amount

    def test_issue_symbolNotExist(self, quantity="1.000000 ABC", toAccount="giftcard1111"):
        symbol = quantity.split(" ")[1]
        balance1 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"资产: {balance1}")
        state = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state}")

        res = self.issueGiftCardToken(user_account, toAccount, quantity, user_key)
        logger.info(f"交易的结果: {res}")
        assert "token with symbol does not exist, create token before issue" in res["error"]["details"][0]["message"]
        state2 = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state2}")

        balance2 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"资产: {balance2}")

        assert state == state2
        assert balance1 == balance2

    def test_issue_symbolInvalid(self, quantity="1.000000 abc", toAccount="giftcard1111"):
        symbol = quantity.split(" ")[1]
        balance1 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"资产: {balance1}")
        state = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state}")

        res = self.issueGiftCardToken(user_account, toAccount, quantity, user_key)
        logger.info(f"交易的结果: {res}")
        assert "invalid symbol name" in res["error"]["details"][0]["message"]
        state2 = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state2}")

        balance2 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"资产: {balance2}")

        assert state == state2
        assert balance1 == balance2

    def test_issue_noPermission(self):
        quantity = "1.000000 USD"
        symbol = quantity.split(" ")[1]
        balance1 = self.chain_client.get_currency_balance(user_account2, gift_card_account, symbol)
        logger.info(f"资产: {balance1}")
        state = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state}")

        res = self.issueGiftCardToken(user_account2, user_account2, quantity, user_key2)
        logger.info(f"交易的结果: {res}")
        assert "issue account from must be authorized" in res["error"]["details"][0]["message"]
        state2 = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state2}")

        balance2 = self.chain_client.get_currency_balance(user_account2, gift_card_account, symbol)
        logger.info(f"资产: {balance2}")

        assert state == state2
        assert balance1 == balance2

    def test_issue_toAccountInvalid(self, quantity="1.000000 USD", toAccount="abc123"):
        symbol = quantity.split(" ")[1]
        balance1 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"资产: {balance1}")
        state = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state}")

        res = self.issueGiftCardToken(user_account, toAccount, quantity, user_key)
        logger.info(f"交易的结果: {res}")
        assert "to account does not exist" in res["error"]["details"][0]["message"]
        state2 = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state2}")

        balance2 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"资产: {balance2}")

        assert state == state2
        assert balance1 == balance2

    def test_issue_memoExceedLimit(self):
        quantity = "1.000000 USD"
        toAccount = user_account2
        symbol = quantity.split(" ")[1]
        balance1 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"资产: {balance1}")
        state = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state}")
        memo = "1" * 257
        res = self.issueGiftCardToken(user_account, toAccount, quantity, user_key, memo)
        logger.info(f"交易的结果: {res}")
        assert "memo has more than 256 bytes" in res["error"]["details"][0]["message"]
        state2 = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state2}")

        balance2 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"资产: {balance2}")

        assert state == state2
        assert balance1 == balance2

    def test_issue_quantityDecimalInvalid(self):
        quantity = "1.0000 USD"
        toAccount = user_account2
        symbol = quantity.split(" ")[1]
        balance1 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"资产: {balance1}")
        state = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state}")
        res = self.issueGiftCardToken(user_account, toAccount, quantity, user_key)
        logger.info(f"交易的结果: {res}")
        assert "symbol precision mismatch" in res["error"]["details"][0]["message"]
        state2 = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state2}")

        balance2 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"资产: {balance2}")

        assert state == state2
        assert balance1 == balance2

    def test_issue_quantityInvalid(self):
        quantity = "0.000000 USD"
        toAccount = user_account2
        symbol = quantity.split(" ")[1]
        balance1 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"资产: {balance1}")
        state = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state}")
        res = self.issueGiftCardToken(user_account, toAccount, quantity, user_key)
        logger.info(f"交易的结果: {res}")
        assert "must issue positive quantity" in res["error"]["details"][0]["message"]

        res = self.issueGiftCardToken(user_account, toAccount, "-100.000000 USD", user_key)
        logger.info(f"交易的结果: {res}")
        assert "must issue positive quantity" in res["error"]["details"][0]["message"]

        state2 = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state2}")

        balance2 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"资产: {balance2}")

        assert state == state2
        assert balance1 == balance2

    def test_issue_quantityExceedMaxSupply(self):
        quantity = "0.000000 USD"
        toAccount = user_account2
        symbol = quantity.split(" ")[1]
        balance1 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"资产: {balance1}")
        state = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state}")
        quantity = state["rows"][0]["max_supply"]
        res = self.issueGiftCardToken(user_account, toAccount, quantity, user_key)
        logger.info(f"交易的结果: {res}")
        assert "quantity exceeds available supply" in res["error"]["details"][0]["message"]

        state2 = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state2}")

        balance2 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"资产: {balance2}")

        assert state == state2
        assert balance1 == balance2

    def test_transfer_normal(self, quantity="1.000000 USD", toAccount="giftcard1111", fromAccount=user_account, fromKey=user_key, memo=""):
        symbol = quantity.split(" ")[1]
        from_balance1 = self.chain_client.get_currency_balance(fromAccount, gift_card_account, symbol)
        to_balance1 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"from资产: {from_balance1}")
        logger.info(f"to资产: {to_balance1}")
        state = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state}")

        res = self.transferGiftCardToken(fromAccount, toAccount, quantity, fromKey, memo)
        logger.info(f"交易的结果: {res}")
        state2 = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state2}")

        from_balance2 = self.chain_client.get_currency_balance(fromAccount, gift_card_account, symbol)
        to_balance2 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"from资产: {from_balance2}")
        logger.info(f"to资产: {to_balance2}")

        supply1 = float(state["rows"][0]["supply"].split(" ")[0]) if state["rows"] else 0
        supply2 = float(state2["rows"][0]["supply"].split(" ")[0]) if state2["rows"] else 0
        assert supply1 == supply2, "supply 应不变"

        add_amount = float(quantity.split(" ")[0])
        to_currency_balance = [i for i in to_balance1 if symbol in i]
        to_amount1 = float(to_currency_balance[0].split(" ")[0]) if to_currency_balance else 0
        to_amount2 = float([i for i in to_balance2 if symbol in i][0].split(" ")[0])
        from_currency_balance = [i for i in from_balance1 if symbol in i]
        from_amount1 = float(from_currency_balance[0].split(" ")[0]) if from_currency_balance else 0
        from_amount2 = float([i for i in from_balance2 if symbol in i][0].split(" ")[0])

        assert abs(to_amount2 - to_amount1 - add_amount) < 0.1 ** 7, f"to账户变化了{to_amount2 - to_amount1}"
        assert abs(from_amount2 - from_amount1 + add_amount) < 0.1 ** 7, f"from账户变化了{from_amount2 - from_amount1}"

    def test_transfer_symbolNotExist(self, quantity="1.000000 ABC", toAccount="giftcard1111"):
        symbol = quantity.split(" ")[1]
        from_balance1 = self.chain_client.get_currency_balance(user_account, gift_card_account, symbol)
        to_balance1 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"from资产: {from_balance1}")
        logger.info(f"to资产: {to_balance1}")
        state = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state}")

        res = self.transferGiftCardToken(user_account, toAccount, quantity, user_key)
        logger.info(f"交易的结果: {res}")
        assert "unable to find key" in res["error"]["details"][0]["message"]
        state2 = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state2}")

        from_balance2 = self.chain_client.get_currency_balance(user_account, gift_card_account, symbol)
        to_balance2 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"from资产: {from_balance2}")
        logger.info(f"to资产: {to_balance2}")

        assert state == state2
        assert from_balance1 == from_balance2
        assert to_balance1 == to_balance2

    def test_transfer_symbolInvalid(self, quantity="1.000000 abc", toAccount="giftcard1111"):
        symbol = quantity.split(" ")[1]
        from_balance1 = self.chain_client.get_currency_balance(user_account, gift_card_account, symbol)
        to_balance1 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"from资产: {from_balance1}")
        logger.info(f"to资产: {to_balance1}")
        state = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state}")

        res = self.transferGiftCardToken(user_account, toAccount, quantity, user_key)
        logger.info(f"交易的结果: {res}")
        assert "unable to find key" in res["error"]["details"][0]["message"]
        state2 = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state2}")

        from_balance2 = self.chain_client.get_currency_balance(user_account, gift_card_account, symbol)
        to_balance2 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"from资产: {from_balance2}")
        logger.info(f"to资产: {to_balance2}")

        assert state == state2
        assert from_balance1 == from_balance2
        assert to_balance1 == to_balance2

    def test_transfer_toAccountInvalid(self, quantity="1.000000 USD", toAccount="abc123"):
        symbol = quantity.split(" ")[1]
        from_balance1 = self.chain_client.get_currency_balance(user_account, gift_card_account, symbol)
        to_balance1 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"from资产: {from_balance1}")
        logger.info(f"to资产: {to_balance1}")
        state = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state}")

        res = self.transferGiftCardToken(user_account, toAccount, quantity, user_key)
        logger.info(f"交易的结果: {res}")
        assert "to account does not exist" in res["error"]["details"][0]["message"]
        state2 = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state2}")

        from_balance2 = self.chain_client.get_currency_balance(user_account, gift_card_account, symbol)
        to_balance2 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"from资产: {from_balance2}")
        logger.info(f"to资产: {to_balance2}")

        assert state == state2
        assert from_balance1 == from_balance2
        assert to_balance1 == to_balance2

    def test_transfer_memoExceedLimit(self):
        quantity = "1.000000 USD"
        toAccount = user_account2
        symbol = quantity.split(" ")[1]
        from_balance1 = self.chain_client.get_currency_balance(user_account, gift_card_account, symbol)
        to_balance1 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"from资产: {from_balance1}")
        logger.info(f"to资产: {to_balance1}")
        state = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state}")
        memo = "1" * 257
        res = self.transferGiftCardToken(user_account, toAccount, quantity, user_key, memo)
        logger.info(f"交易的结果: {res}")
        assert "memo has more than 256 bytes" in res["error"]["details"][0]["message"]
        state2 = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state2}")

        from_balance2 = self.chain_client.get_currency_balance(user_account, gift_card_account, symbol)
        to_balance2 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"from资产: {from_balance2}")
        logger.info(f"to资产: {to_balance2}")

        assert state == state2
        assert from_balance1 == from_balance2
        assert to_balance1 == to_balance2

    def test_transfer_quantityDecimalInvalid(self):
        quantity = "1.0000 USD"
        toAccount = user_account2
        symbol = quantity.split(" ")[1]
        from_balance1 = self.chain_client.get_currency_balance(user_account, gift_card_account, symbol)
        to_balance1 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"from资产: {from_balance1}")
        logger.info(f"to资产: {to_balance1}")
        state = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state}")

        res = self.transferGiftCardToken(user_account, toAccount, quantity, user_key)
        logger.info(f"交易的结果: {res}")
        assert "symbol precision mismatch" in res["error"]["details"][0]["message"]
        state2 = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state2}")

        from_balance2 = self.chain_client.get_currency_balance(user_account, gift_card_account, symbol)
        to_balance2 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"from资产: {from_balance2}")
        logger.info(f"to资产: {to_balance2}")

        assert state == state2
        assert from_balance1 == from_balance2
        assert to_balance1 == to_balance2

    def test_transfer_quantityInvalid(self):
        quantity = "0.000000 USD"
        toAccount = user_account2
        symbol = quantity.split(" ")[1]
        from_balance1 = self.chain_client.get_currency_balance(user_account, gift_card_account, symbol)
        to_balance1 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"from资产: {from_balance1}")
        logger.info(f"to资产: {to_balance1}")
        state = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state}")

        res = self.transferGiftCardToken(user_account, toAccount, quantity, user_key)
        logger.info(f"交易的结果: {res}")
        assert "must transfer positive quantity" in res["error"]["details"][0]["message"]
        state2 = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state2}")

        from_balance2 = self.chain_client.get_currency_balance(user_account, gift_card_account, symbol)
        to_balance2 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"from资产: {from_balance2}")
        logger.info(f"to资产: {to_balance2}")

        assert state == state2
        assert from_balance1 == from_balance2
        assert to_balance1 == to_balance2

    def test_transfer_quantityExceedBalance(self):
        toAccount = user_account2
        symbol = "USD"
        from_balance1 = self.chain_client.get_currency_balance(user_account, gift_card_account, symbol)
        to_balance1 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"from资产: {from_balance1}")
        logger.info(f"to资产: {to_balance1}")
        state = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state}")

        quantity = str(ApiUtils.parseNumberDecimal(0.1 + float(from_balance1[0].split(" ")[0]), 6, True)) + " " + symbol
        res = self.transferGiftCardToken(user_account, toAccount, quantity, user_key)
        logger.info(f"交易的结果: {res}")
        assert "overdrawn balance" in res["error"]["details"][0]["message"]
        state2 = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state2}")

        from_balance2 = self.chain_client.get_currency_balance(user_account, gift_card_account, symbol)
        to_balance2 = self.chain_client.get_currency_balance(toAccount, gift_card_account, symbol)
        logger.info(f"from资产: {from_balance2}")
        logger.info(f"to资产: {to_balance2}")

        assert state == state2
        assert from_balance1 == from_balance2
        assert to_balance1 == to_balance2

    def test_retire_normal(self, quantity="1.000000 USD", retireAccount=user_account, accountKey=user_key):
        symbol = quantity.split(" ")[1]
        balance1 = self.chain_client.get_currency_balance(retireAccount, gift_card_account, symbol)
        logger.info(f"资产: {balance1}")
        state = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state}")

        res = self.retireGiftCardToken(retireAccount, quantity, accountKey)
        logger.info(f"交易的结果: {res}")
        state2 = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state2}")

        balance2 = self.chain_client.get_currency_balance(retireAccount, gift_card_account, symbol)
        logger.info(f"资产: {balance2}")

        supply1 = float(state["rows"][0]["supply"].split(" ")[0]) if state["rows"] else 0
        supply2 = float(state2["rows"][0]["supply"].split(" ")[0])
        add_amount = float(quantity.split(" ")[0])
        logger.info(f"supply变化了: {supply2 - supply1}")

        find_currency_balance = [i for i in balance1 if symbol in i]
        amount1 = float(find_currency_balance[0].split(" ")[0]) if find_currency_balance else 0
        amount2 = float([i for i in balance2 if symbol in i][0].split(" ")[0])
        logger.info(f"用户资产变化了: {amount2 - amount1}")
        assert abs(supply1 - add_amount - supply2) < 0.1 ** 7
        assert abs(amount1 - add_amount - amount2) < 0.1 ** 7

    def test_retire_otherUserBalance(self):
        quantity = "1.000000 USD"
        symbol = quantity.split(" ")[1]
        balance1 = self.chain_client.get_currency_balance(user_account2, gift_card_account, symbol)
        logger.info(f"资产: {balance1}")
        state = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state}")

        res = self.retireGiftCardToken(user_account, quantity, user_key, retireAccount=user_account2)
        logger.info(f"交易的结果: {res}")
        assert "missing authority" in res["error"]["details"][0]["message"]
        state2 = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state2}")

        balance2 = self.chain_client.get_currency_balance(user_account2, gift_card_account, symbol)
        logger.info(f"资产: {balance2}")

        assert state == state2
        assert balance1 == balance2

    def test_retire_memoExceedLimit(self, quantity="1.000000 USD"):
        symbol = quantity.split(" ")[1]
        balance1 = self.chain_client.get_currency_balance(user_account, gift_card_account, symbol)
        logger.info(f"资产: {balance1}")
        state = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state}")

        memo = "1" * 257
        res = self.retireGiftCardToken(user_account, quantity, user_key, memo)
        logger.info(f"交易的结果: {res}")
        assert "memo has more than 256 bytes" in res["error"]["details"][0]["message"]
        state2 = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state2}")

        balance2 = self.chain_client.get_currency_balance(user_account, gift_card_account, symbol)
        logger.info(f"资产: {balance2}")

        assert state == state2
        assert balance1 == balance2

    def test_retire_quantityDecimalInvalid(self, quantity="1.0000 USD"):
        symbol = quantity.split(" ")[1]
        balance1 = self.chain_client.get_currency_balance(user_account, gift_card_account, symbol)
        logger.info(f"资产: {balance1}")
        state = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state}")

        res = self.retireGiftCardToken(user_account, quantity, user_key)
        logger.info(f"交易的结果: {res}")
        assert "symbol precision mismatch" in res["error"]["details"][0]["message"]
        state2 = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state2}")

        balance2 = self.chain_client.get_currency_balance(user_account, gift_card_account, symbol)
        logger.info(f"资产: {balance2}")

        assert state == state2
        assert balance1 == balance2

    def test_retire_quantityExceedBalance(self):
        symbol = "USD"
        balance1 = self.chain_client.get_currency_balance(user_account, gift_card_account, symbol)
        logger.info(f"资产: {balance1}")
        state = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state}")

        quantity = str(ApiUtils.parseNumberDecimal(0.1 + float(balance1[0].split(" ")[0]), 6, True)) + " " + symbol

        res = self.retireGiftCardToken(user_account, quantity, user_key)
        logger.info(f"交易的结果: {res}")
        assert "overdrawn balance" in res["error"]["details"][0]["message"]
        state2 = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state2}")

        balance2 = self.chain_client.get_currency_balance(user_account, gift_card_account, symbol)
        logger.info(f"资产: {balance2}")

        assert state == state2
        assert balance1 == balance2

    def test_retire_notHaveAuthorPermission(self, quantity="1.00000 USD"):
        symbol = quantity.split(" ")[1]
        balance1 = self.chain_client.get_currency_balance(user_account, gift_card_account, symbol)
        logger.info(f"资产: {balance1}")
        state = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state}")

        assert user_account2 not in state["rows"][0]["authors"], "将要之下的交易必须没有author权限"

        res = self.retireGiftCardToken(user_account2, quantity, user_key2)
        logger.info(f"交易的结果: {res}")
        assert "retire account from must be authorized" in res["error"]["details"][0]["message"]
        state2 = self.chain_client.get_table(gift_card_account, symbol, "stat")
        logger.info(f"礼品卡: {state2}")

        balance2 = self.chain_client.get_currency_balance(user_account, gift_card_account, symbol)
        logger.info(f"资产: {balance2}")

        assert state == state2
        assert balance1 == balance2

    def test_addAuthor(self, author, symbol="6,USD"):
        state = self.chain_client.get_table(gift_card_account, symbol.split(",")[1], "stat")
        logger.info(f"礼品卡: {state}")

        res = self.addAuthor(symbol, author)
        logger.info(f"交易的结果: {res}")
        state2 = self.chain_client.get_table(gift_card_account, symbol.split(",")[1], "stat")
        logger.info(f"礼品卡: {state2}")

        assert author in state2["rows"][0]["authors"], "addAuthor后，应在表中"

    def test_delAuthor(self, author, symbol="6,USD"):
        state = self.chain_client.get_table(gift_card_account, symbol.split(",")[1], "stat")
        logger.info(f"礼品卡: {state}")

        res = self.deleteAuthor(symbol, author)
        logger.info(f"交易的结果: {res}")
        state2 = self.chain_client.get_table(gift_card_account, symbol.split(",")[1], "stat")
        logger.info(f"礼品卡: {state2}")

        assert author not in state2["rows"][0]["authors"], "addAuthor后，应在表中"

    # 商户信誉合约
    def incScore(self, account, score):
        arguments = {
            "credit_account": account,
            "score": score,
        }
        payload = {
            "account": "roxe.credit",
            "name": "incscore",
            "authorization": [{
                "actor": credit_account,
                "permission": "owner",
            }],
        }
        score_table = self.chain_client.get_table("roxe.credit", account, "credits")
        logger.info(f"执行{payload['name']}前的table数据: {score_table}")
        logger.info(f"actions: {arguments}")
        abi_data = self.creditAbi.json_to_bin(payload['name'], arguments)
        logger.info(f"获取abi: {abi_data}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(credit_key)
        logger.info(F"交易: {trx}")
        resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        logger.info('------------------------------------------------')
        logger.info(resp)
        logger.info('------------------------------------------------')
        tx_info = self.chain_client.get_transaction(resp["transaction_id"], timeout=60)
        logger.info(f"交易详情: {tx_info}")
        score_table2 = self.chain_client.get_table("roxe.credit", account, "credits")
        logger.info(f"执行{payload['name']}后的table数据: {score_table2}")

        inc_score = score_table["rows"][0]["credit_score"] + score
        if inc_score >= 100:
            assert score_table2["rows"][0]["credit_score"] == 100
        else:
            assert score_table2["rows"][0]["credit_score"] == inc_score

    def decScore(self, account, score):
        arguments = {
            "credit_account": account,
            "score": score,
        }
        payload = {
            "account": "roxe.credit",
            "name": "decscore",
            "authorization": [{
                "actor": credit_account,
                "permission": "owner",
            }],
        }
        score_table = self.chain_client.get_table("roxe.credit", account, "credits")
        logger.info(f"执行{payload['name']}前的table数据: {score_table}")
        logger.info(f"actions: {arguments}")
        abi_data = self.creditAbi.json_to_bin(payload['name'], arguments)
        logger.info(f"获取abi: {abi_data}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(credit_key)
        logger.info(F"交易: {trx}")
        resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        logger.info('------------------------------------------------')
        logger.info(resp)
        logger.info('------------------------------------------------')
        tx_info = self.chain_client.get_transaction(resp["transaction_id"], timeout=60)
        logger.info(f"交易详情: {tx_info}")
        score_table2 = self.chain_client.get_table("roxe.credit", account, "credits")
        logger.info(f"执行{payload['name']}后的table数据: {score_table2}")

        # if score_table["rows"][0]["credit_score"] - score <= 100:
        dec_score = score_table["rows"][0]["credit_score"] - score
        if dec_score > 0:
            assert score_table2["rows"][0]["credit_score"] == dec_score
        else:
            assert score_table2["rows"][0]["credit_score"] == 0

    def incVip(self, account):
        arguments = {
            "vip_account": account
        }
        payload = {
            "account": "roxe.credit",
            "name": "incvip",
            "authorization": [{
                "actor": credit_account,
                "permission": "owner",
            }],
        }
        score_table = self.chain_client.get_table("roxe.credit", account, "vipclass")
        logger.info(f"执行{payload['name']}前的table数据: {score_table}")
        logger.info(f"actions: {arguments}")
        abi_data = self.creditAbi.json_to_bin(payload['name'], arguments)
        logger.info(f"获取abi: {abi_data}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(credit_key)
        logger.info(F"交易: {trx}")
        resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        logger.info('------------------------------------------------')
        logger.info(resp)
        logger.info('------------------------------------------------')
        tx_info = self.chain_client.get_transaction(resp["transaction_id"], timeout=60)
        logger.info(f"交易详情: {tx_info}")
        score_table2 = self.chain_client.get_table("roxe.credit", account, "vipclass")
        logger.info(f"执行{payload['name']}后的table数据: {score_table2}")
        
        inc_vip = score_table["rows"][0]["vip"] + 1 if score_table2["rows"] else 1
        if inc_vip >= 5:
            assert score_table2["rows"][0]["vip"] == 5
        else:
            assert score_table2["rows"][0]["vip"] == inc_vip

    def decVip(self, account):
        arguments = {
            "vip_account": account
        }
        payload = {
            "account": "roxe.credit",
            "name": "decvip",
            "authorization": [{
                "actor": credit_account,
                "permission": "owner",
            }],
        }
        score_table = self.chain_client.get_table("roxe.credit", account, "vipclass")
        logger.info(f"执行{payload['name']}前的table数据: {score_table}")
        logger.info(f"actions: {arguments}")
        abi_data = self.creditAbi.json_to_bin(payload['name'], arguments)
        logger.info(f"获取abi: {abi_data}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(credit_key)
        logger.info(F"交易: {trx}")
        resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        logger.info('------------------------------------------------')
        logger.info(resp)
        logger.info('------------------------------------------------')
        tx_info = self.chain_client.get_transaction(resp["transaction_id"], timeout=60)
        logger.info(f"交易详情: {tx_info}")
        score_table2 = self.chain_client.get_table("roxe.credit", account, "vipclass")
        logger.info(f"执行{payload['name']}后的table数据: {score_table2}")

        inc_vip = score_table["rows"][0]["vip"] - 1 if score_table2["rows"] else 1
        if inc_vip >= 5:
            assert score_table2["rows"][0]["vip"] == 5
        else:
            assert score_table2["rows"][0]["vip"] == inc_vip

    # 拼团合约
    def updateController(self, controller, fromAccount, fromKey):
        arguments = {
            "controller": controller
        }
        payload = {
            "account": group,
            "name": "updatectler",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp

    def addBlackUser(self, user, fromAccount=group, fromKey=group_key):
        arguments = {
            "user": user
        }
        payload = {
            "account": group,
            "name": "addblackuser",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp

    def delBlackUser(self, user, fromAccount=group, fromKey=group_key):
        arguments = {
            "user": user
        }
        payload = {
            "account": group,
            "name": "delblackuser",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp

    def setCreditScore(self, required, score, fromAccount=group, fromKey=group_key):
        arguments = {
            "required": required,
            "score": score
        }
        payload = {
            "account": group,
            "name": "setcrdscore",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp

    def addConductor(self, business, _activity, user, fromAccount, fromKey):
        arguments = {
            "business": business,
            "_activity": _activity,
            "user": user,
        }
        payload = {
            "account": group,
            "name": "addconductor",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp

    def delConductor(self, business, _activity, user, fromAccount, fromKey):
        arguments = {
            "business": business,
            "_activity": _activity,
            "user": user,
        }
        payload = {
            "account": group,
            "name": "delconductor",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp

    def autoGroup(self, business, _activity, auto_group: bool, fromAccount, fromKey):
        arguments = {
            "business": business,
            "_activity": _activity,
            "auto_group": auto_group,
        }
        payload = {
            "account": group,
            "name": "autogroup",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp

    def setFreeStart(self, business, _activity, free: bool, fromAccount, fromKey):
        arguments = {
            "business": business,
            "_activity": _activity,
            "free": free,
        }
        payload = {
            "account": group,
            "name": "setfreestart",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp

    def setExceed(self, business, _activity, can_exceed: bool, fromAccount, fromKey):
        arguments = {
            "business": business,
            "_activity": _activity,
            "can_exceed": can_exceed,
        }
        payload = {
            "account": group,
            "name": "setexceed",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp

    def freezeGift(self, business, _activity, amount, fromAccount, fromKey):
        arguments = {
            "_business": business,
            "_activity": _activity,
            "amount": amount,
        }
        payload = {
            "account": group,
            "name": "freezegift",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp

    def unfreezeGift(self, business, _activity, amount, fromAccount, fromKey):
        arguments = {
            "_business": business,
            "_activity": _activity,
            "amount": amount,
        }
        payload = {
            "account": group,
            "name": "unfreezegift",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp

    def setOrdCancel(self, business, _activity, _cancel, fromAccount, fromKey):
        """
        设置指定活动是否允许取消订单的权限
        """
        arguments = {
            "business": business,
            "_activity": _activity,
            "_cancel": _cancel,
        }
        payload = {
            "account": group,
            "name": "setordcancel",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp

    def setRebate(self, business, _activity, _rebate_now, fromAccount, fromKey):
        """
        设置指定活动是否允许及时返利
        """
        arguments = {
            "business": business,
            "_activity": _activity,
            "_rebate_now": _rebate_now,
        }
        payload = {
            "account": group,
            "name": "setrebate",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp

    def setCancelRatio(self, business, _activity, _cancel_order_ratio, fromAccount, fromKey):
        """
        设置指定活动的取消订单费率
        """
        arguments = {
            "business": business,
            "_activity": _activity,
            "_cancel_order_ratio": _cancel_order_ratio,
        }
        payload = {
            "account": group,
            "name": "setcelratio",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp

    def createActivity(self, business, server_provider, _plat_provider, _activity, sponsor, subscriptoken, giftoken, standard_price, discount_price, total_amount, standard_amount, fromAccount, fromKey):
        """
        商家新建拼团活动
        :param business:
        :param server_provider:
        :param _plat_provider:
        :param _activity:
        :param sponsor:
        :param subscriptoken:
        :param giftoken:
        :param standard_price:
        :param discount_price:
        :param total_amount:
        :param standard_amount:
        :param fromAccount:
        :param fromKey:
        :return:
        """
        arguments = {
            "business": business,
            "server_provider": server_provider,
            "_plat_provider": _plat_provider,
            "_activity": _activity,
            "sponsor": sponsor,
            "subscriptoken": subscriptoken,
            "giftoken": giftoken,
            "standard_price": standard_price,
            "discount_price": discount_price,
            "total_amount": total_amount,
            "standard_amount": standard_amount,
        }
        payload = {
            "account": group,
            "name": "createact",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp, arguments

    def initActivity(self, business, _activity, start_time, terminal_time, amount_reach_to_standard, halfway_redeemable, percent_redeem_fee, group_min_person_count, group_min_amount, group_max_amount, fromAccount, fromKey):
        """
        商家初始化拼团配置
        """
        arguments = {
            "business": business,
            "_activity": _activity,
            "start_time": start_time,
            "terminal_time": terminal_time,
            "amount_reach_to_standard": amount_reach_to_standard,
            "halfway_redeemable": halfway_redeemable,
            "percent_redeem_fee": percent_redeem_fee,
            "group_min_person_count": group_min_person_count,
            "group_min_amount": group_min_amount,
            "group_max_amount": group_max_amount,
        }
        payload = {
            "account": group,
            "name": "init",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp, arguments

    def setBonusConf(self, business, _activity, platform_share_ratio, sponsor_share_ratio, rebate_share_ratio, bus_first_redeem_ratio, performance_ratio, order_rebate_share_ratio, fromAccount, fromKey):
        """
        商家设置平台分账比例
        """
        arguments = {
            "business": business,
            "_activity": _activity,
            "platform_share_ratio": platform_share_ratio,
            "sponsor_share_ratio": sponsor_share_ratio,
            "rebate_share_ratio": rebate_share_ratio,
            "bus_first_redeem_ratio": bus_first_redeem_ratio,
            "performance_ratio": performance_ratio,
            "order_rebate_share_ratio": order_rebate_share_ratio,
        }
        payload = {
            "account": group,
            "name": "setbonusconf",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp, arguments

    def newGroup(self, activity, group_id, sponsor, min_person_count, discount_price, max_amount, fromAccount, fromKey):
        """
        新建拼团
        """
        arguments = {
            "_activity": activity,
            "_group_id": group_id,
            "_sponsor": sponsor,
            "_min_person_count": min_person_count,
            "_discount_price": discount_price,
            "_max_amount": max_amount,
        }
        payload = {
            "account": group,
            "name": "newgroup",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp, arguments

    def revokeGroup(self, activity, group_id, fromAccount, fromKey):
        """
        撤销拼团
        """
        arguments = {
            "_activity": activity,
            "_group_id": group_id,
        }
        payload = {
            "account": group,
            "name": "revokegroup",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp, arguments

    def purchase(self, activity, group_id, _order_id, _buyer, _receiver, _invitor, _subscript_amounts, fromAccount, fromKey, memo=""):
        """
        新建拼团
        """
        arguments = {
            "_activity": activity,
            "_group_id": group_id,
            "_order_id": _order_id,
            "_buyer": _buyer,
            "_receiver": _receiver,
            "_invitor": _invitor,
            "_subscript_amounts": _subscript_amounts,
            "memo": memo,
        }
        payload = {
            "account": group,
            "name": "purchase",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp, arguments

    def newGroupAndBuy(self, activity, group_id, order_id, sponsor, min_person_count, discount_price, max_amount, _receiver, _subscript_amounts, fromAccount, fromKey, memo=""):
        """
        拼团并下单
        """
        arguments = {
            "_activity": activity,
            "_group_id": group_id,
            "_order_id": order_id,
            "_sponsor": sponsor,
            "_min_person_count": min_person_count,
            "_discount_price": discount_price,
            "_max_amount": max_amount,
            "_receiver": _receiver,
            "_subscript_amounts": _subscript_amounts,
            "memo": memo,
        }
        payload = {
            "account": group,
            "name": "newgpbuy",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp, arguments

    def confirmOrder(self, activity, group_id, order_id, fromAccount, fromKey):
        """
        撤销拼团
        """
        arguments = {
            "_activity": activity,
            "_group_id": group_id,
            "_order_id": order_id,
        }
        payload = {
            "account": group,
            "name": "confirmorder",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp, arguments

    def revokeOrder(self, activity, group_id, order_id, fromAccount, fromKey, memo=""):
        """
        撤销拼团
        """
        arguments = {
            "_activity": activity,
            "_group_id": group_id,
            "_order_id": order_id,
            "memo": memo,
        }
        payload = {
            "account": group,
            "name": "revokeorder",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp, arguments

    def delivery(self, activity, group_id, order_id, fromAccount, fromKey, memo=""):
        """
        分发礼品卡
        """
        arguments = {
            "_activity": activity,
            "_group_id": group_id,
            "_order_id": order_id,
            "memo": memo,
        }
        payload = {
            "account": group,
            "name": "delivery",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp, arguments

    def collect(self, activity, group_id, _amount, fromAccount, fromKey, memo=""):
        """
        平台方领取分账
        """
        arguments = {
            "_activity": activity,
            "_group_id": group_id,
            "_amount": _amount,
            "memo": memo,
        }
        payload = {
            "account": group,
            "name": "collect",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp, arguments

    def rebate(self, activity, group_id, order_id, fromAccount, fromKey, memo=""):
        """
        订单返利
        """
        arguments = {
            "_activity": activity,
            "_group_id": group_id,
            "_order_id": order_id,
            "memo": memo,
        }
        payload = {
            "account": group,
            "name": "rebate",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp, arguments

    def withdraw(self, activity, group_id, _amount, fromAccount, fromKey, memo=""):
        """
        商家或者服务提供商领取分账
        """
        arguments = {
            "_activity": activity,
            "_group_id": group_id,
            "_amount": _amount,
            "memo": memo,
        }
        payload = {
            "account": group,
            "name": "withdraw",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp, arguments

    def performance(self, activity, _amount, fromAccount, fromKey, memo=""):
        """
        商家履约
        """
        arguments = {
            "_activity": activity,
            "_amount": _amount,
            "memo": memo,
        }
        payload = {
            "account": group,
            "name": "performance",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        logger.info(F"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        key = ROXEKey(fromKey)
        logger.info(F"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, key, broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp, arguments

    def test_updateController(self, controller, fromAccount, fromKey):
        state = self.chain_client.get_table(group, group, "activity")
        logger.info(f"group factory表信息: {state}")

        res = self.updateController(controller, fromAccount, fromKey)
        logger.info(f"交易结果: {res}")

        state = self.chain_client.get_table(group, group, "activity")
        logger.info(f"group factory表信息: {state}")

        assert controller == state["rows"][0]["_CONTROLLER_"]

    def test_updateController_notExist(self, controller, fromAccount, fromKey):
        state = self.chain_client.get_table(group, group, "activity")
        logger.info(f"group factory表信息: {state}")

        res = self.updateController(controller, fromAccount, fromKey)
        logger.info(f"交易结果: {res}")

        state2 = self.chain_client.get_table(group, group, "activity")
        logger.info(f"group factory表信息: {state}")

        assert state == state2
        assert "controller invalid" in res["error"]["details"][0]["message"]

    def test_addBlackUser(self, user):
        state = self.chain_client.get_table(group, group, "activity")
        logger.info(f"group factory表信息: {state}")

        res = self.addBlackUser(user)
        logger.info(f"交易结果: {res}")

        state2 = self.chain_client.get_table(group, group, "activity")
        logger.info(f"group factory表信息: {state2}")

        assert user not in state["rows"][0]["_BLACKLISTS_"]
        assert user in state2["rows"][0]["_BLACKLISTS_"]

    def test_addBlackUser_added(self, user):
        state = self.chain_client.get_table(group, group, "activity")
        logger.info(f"group factory表信息: {state}")

        res = self.addBlackUser(user)
        logger.info(f"交易结果: {res}")

        state2 = self.chain_client.get_table(group, group, "activity")
        logger.info(f"group factory表信息: {state2}")

        assert user in state2["rows"][0]["_BLACKLISTS_"]

    def test_addBlackUser_userInvalid(self, user):
        state = self.chain_client.get_table(group, group, "activity")
        logger.info(f"group factory表信息: {state}")

        res = self.addBlackUser(user)
        logger.info(f"交易结果: {res}")

        state2 = self.chain_client.get_table(group, group, "activity")
        logger.info(f"group factory表信息: {state2}")

        assert state == state2
        assert "user account invalid" in res["error"]["details"][0]["message"]

    def test_delBlackUser(self, user):
        state = self.chain_client.get_table(group, group, "activity")
        logger.info(f"group factory表信息: {state}")

        res = self.delBlackUser(user)
        logger.info(f"交易结果: {res}")

        state2 = self.chain_client.get_table(group, group, "activity")
        logger.info(f"group factory表信息: {state2}")

        assert user in state["rows"][0]["_BLACKLISTS_"]
        assert user not in state2["rows"][0]["_BLACKLISTS_"]

    def test_delBlackUser_deleted(self, user):
        state = self.chain_client.get_table(group, group, "activity")
        logger.info(f"group factory表信息: {state}")

        res = self.delBlackUser(user)
        logger.info(f"交易结果: {res}")

        state2 = self.chain_client.get_table(group, group, "activity")
        logger.info(f"group factory表信息: {state2}")

        assert user not in state2["rows"][0]["_BLACKLISTS_"]

    def test_delBlackUser_userInvalid(self, user):
        state = self.chain_client.get_table(group, group, "activity")
        logger.info(f"group factory表信息: {state}")

        res = self.delBlackUser(user)
        logger.info(f"交易结果: {res}")

        state2 = self.chain_client.get_table(group, group, "activity")
        logger.info(f"group factory表信息: {state2}")

        assert user not in state2["rows"][0]["_BLACKLISTS_"]
        # assert "user account invalid" in res["error"]["details"][0]["message"]

    def test_setCreditScore(self, required, score):
        state = self.chain_client.get_table(group, group, "activity")
        logger.info(f"group factory表信息: {state}")

        res = self.setCreditScore(required, score)
        logger.info(f"交易结果: {res}")

        state2 = self.chain_client.get_table(group, group, "activity")
        logger.info(f"group factory表信息: {state2}")
        ex_req = 1 if required else 0
        assert ex_req == state2["rows"][0]["_CREDIT_REQUIRED_"]
        assert score == state2["rows"][0]["_CREDIT_SCORE_REQUIRED_"]

    def test_createActivity(self, act_id, standard_price=int(5 * ratio_base), discount_price=int(4 * ratio_base), total_amount=int(10 * token_base), standard_amount=int(2 * token_base)):
        factory_table = self.chain_client.get_table(group, group, "activity")
        logger.info(f"表数据: {factory_table}")

        sub_scrip_token = {"symbol": "6,USD", "contract": "roxe.ro"}
        sub_gift = {"symbol": f"{gift_decimal},{gift_symbol}", "contract": "roxe.tokenz"}
        res, action = self.createActivity(user_account, user_account, user_account2, act_id, user_account, sub_scrip_token, sub_gift, standard_price, discount_price, total_amount, standard_amount, user_account, user_key)
        logger.info(res)

        factory_table2 = self.chain_client.get_table(group, group, "activity")
        logger.info(f"表数据: {factory_table2}")

        act_table = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"表数据: {act_table}")

        reg_group = [i for i in factory_table2["rows"][0]["_REGISTRY_USER_GROUPS_"] if i["key"] == user_account]
        assert len(reg_group) > 0
        assert act_id in reg_group[0]["value"]["_IDSET_"]

        act_data = [i for i in act_table["rows"] if i["_ACTIVITY_ID_"] == act_id][0]
        assert act_data["_ACTIVITY_STORE_"]["_PLATE_MANAGER_"] == action["_plat_provider"]
        assert act_data["_ACTIVITY_STORE_"]["_SERVER_PROVIDER_"] == action["server_provider"]
        assert act_data["_ACTIVITY_STORE_"]["_SPONSOR_"] == action["sponsor"]
        assert act_data["_ACTIVITY_STORE_"]["_CONSTRAINT_START_"] == 1
        assert action["business"] in act_data["_ACTIVITY_STORE_"]["_GROUP_CONDUCTORS_"]
        assert act_data["_ACTIVITY_STORE_"]["_GIFT_TOKEN_STANDARD_PRICE_"] == action["standard_price"]
        assert act_data["_ACTIVITY_STORE_"]["_GIFT_TOKEN_DISCOUNT_PRICE_"] == action["discount_price"]
        assert act_data["_ACTIVITY_STORE_"]["_GIFT_TOKEN_TOTAL_AMOUNT_"] == action["total_amount"]
        assert act_data["_ACTIVITY_STORE_"]["_GROUP_STANDARD_AMOUNT_"] == action["standard_amount"]
        assert act_data["_ACTIVITY_STORE_"]["_SUBSCRIPTION_TOKEN_"] == action["subscriptoken"]
        assert act_data["_ACTIVITY_STORE_"]["_GIFT_TOKEN_"] == action["giftoken"]

    def test_createActivity_actAlreadyExist(self, act_id):
        factory_table = self.chain_client.get_table(group, group, "activity")
        logger.info(f"表数据: {factory_table}")

        sub_scrip_token = {"symbol": "6,USD", "contract": "roxe.ro"}
        sub_gift = {"symbol": "6,USD", "contract": "roxe.tokenz"}
        standard_price = int(5 * ratio_base)
        discount_price = int(4 * ratio_base)
        total_amount = int(10 * (10**6))
        standard_amount = int(2 * (10**6))
        res, action = self.createActivity(user_account, user_account, user_account2, act_id, user_account, sub_scrip_token, sub_gift, standard_price, discount_price, total_amount, standard_amount, user_account, user_key)
        logger.info(res)
        assert "group activity already exists" in res["error"]["details"][0]["message"]
        factory_table2 = self.chain_client.get_table(group, group, "activity")
        logger.info(f"表数据: {factory_table2}")

        act_table = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"表数据: {act_table}")

        assert factory_table2 == factory_table

    def test_createActivity_businessAccountInvalid(self, act_id):
        factory_table = self.chain_client.get_table(group, group, "activity")
        logger.info(f"表数据: {factory_table}")

        sub_scrip_token = {"symbol": "6,USD", "contract": "roxe.ro"}
        sub_gift = {"symbol": "6,USD", "contract": "roxe.tokenz"}
        standard_price = int(5 * ratio_base)
        discount_price = int(4 * ratio_base)
        total_amount = int(10 * (10**6))
        standard_amount = int(2 * (10**6))
        res, action = self.createActivity("abc123", user_account, user_account2, act_id, user_account, sub_scrip_token, sub_gift, standard_price, discount_price, total_amount, standard_amount, user_account, user_key)
        logger.info(res)
        assert "business account invalid" in res["error"]["details"][0]["message"]

        res, action = self.createActivity(user_account, "abc123", user_account2, act_id, user_account, sub_scrip_token, sub_gift, standard_price, discount_price, total_amount, standard_amount, user_account, user_key)
        logger.info(res)
        assert "server provider invalid" in res["error"]["details"][0]["message"]

        res, action = self.createActivity(user_account, user_account, "abc123", act_id, user_account, sub_scrip_token, sub_gift, standard_price, discount_price, total_amount, standard_amount, user_account, user_key)
        logger.info(res)
        assert "platform provider invalid" in res["error"]["details"][0]["message"]

        res, action = self.createActivity(user_account, user_account, user_account2, act_id, "abc123", sub_scrip_token, sub_gift, standard_price, discount_price, total_amount, standard_amount, user_account, user_key)
        logger.info(res)
        assert "sponsor account invalid" in res["error"]["details"][0]["message"]

        factory_table2 = self.chain_client.get_table(group, group, "activity")
        logger.info(f"表数据: {factory_table2}")

        act_table = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"表数据: {act_table}")

        assert factory_table2 == factory_table

    def test_initActivity(self, act_id, start_time=int(datetime.datetime.utcnow().timestamp() * 1000), end_time=int(datetime.datetime.utcnow().timestamp() * 1000 + 2 * 24 * 3600 * 1000), amount_reach_to_standard=0, group_min_amount=int(0.1 * token_base), group_max_amount=int(1000 * token_base)):
        factory_table = self.chain_client.get_table(group, group, "activity")
        logger.info(f"表数据: {factory_table}")

        amount_reach_to_standard = amount_reach_to_standard  # int(0.1 * (10**6))
        halfway_redeemable = True
        percent_redeem_fee = int(0 * token_base)
        group_min_person_count = 1
        res, action = self.initActivity(user_account, act_id, start_time, end_time, amount_reach_to_standard, halfway_redeemable, percent_redeem_fee, group_min_person_count, group_min_amount, group_max_amount, user_account, user_key)
        logger.info(res)

        factory_table2 = self.chain_client.get_table(group, group, "activity")
        logger.info(f"表数据: {factory_table2}")

        act_table = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"表数据: {act_table}")

        reg_group = [i for i in factory_table2["rows"][0]["_REGISTRY_USER_GROUPS_"] if i["key"] == user_account]
        assert len(reg_group) > 0

        act_data = [i for i in act_table["rows"] if i["_ACTIVITY_ID_"] == act_id][0]
        assert act_data["_ACTIVITY_STORE_"]["_AMOUNT_REACH_TO_STANDARD_"] == action["amount_reach_to_standard"]
        e_fee = 1 if action["halfway_redeemable"] else 0
        assert act_data["_ACTIVITY_STORE_"]["_HALFWAY_REDEEMABLE_"] == e_fee
        assert act_data["_ACTIVITY_STORE_"]["_PERCENT_REDEEM_FEE_"] == action["percent_redeem_fee"]
        assert act_data["_ACTIVITY_STORE_"]["_GROUP_MIN_PERSON_COUNT_"] == action["group_min_person_count"]
        assert act_data["_ACTIVITY_STORE_"]["_GROUP_PURCHASE_MIN_AMOUNT_"] == action["group_min_amount"]
        assert act_data["_ACTIVITY_STORE_"]["_GROUP_PURCHASE_MAX_AMOUNT_"] == action["group_max_amount"]
        assert act_data["_ACTIVITY_STORE_"]["_GROUP_TERMINAL_TIME"] == str(action["terminal_time"])
        assert act_data["_ACTIVITY_STORE_"]["_GROUP_START_TIME"] == str(action["start_time"])

    def test_initActivity_alreadyInit(self, act_id):
        act_table = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"表数据: {act_table}")

        start_time = int(datetime.datetime.utcnow().timestamp() * 1000 + 6 * 3600 * 1000)
        terminal_time = int(datetime.datetime.utcnow().timestamp() * 1000 + 2 * 24 * 3600 * 1000)
        amount_reach_to_standard = int(0.1 * (10**6))
        halfway_redeemable = True
        percent_redeem_fee = int(0.1 * (10**6))
        group_min_person_count = 1
        group_min_amount = int(0.1 * (10**6))
        group_max_amount = int(2 * (10**6))
        res, action = self.initActivity(user_account, act_id, start_time, terminal_time, amount_reach_to_standard, halfway_redeemable, percent_redeem_fee, group_min_person_count, group_min_amount, group_max_amount, user_account, user_key)
        logger.info(res)

        assert "already initialized" in res["error"]["details"][0]["message"]

        act_table2 = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"表数据: {act_table2}")

        assert act_table2 == act_table

    def test_initActivity_startTimeMoreThanTerminalTime(self, act_id):
        act_table = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"表数据: {act_table}")

        start_time = int(datetime.datetime.utcnow().timestamp() * 1000 + 6 * 3600 * 1000)
        terminal_time = int(datetime.datetime.utcnow().timestamp() * 1000 + 2 * 3600 * 1000)
        amount_reach_to_standard = int(5 * ratio_base)
        halfway_redeemable = True
        percent_redeem_fee = int(0.1 * ratio_base)
        group_min_person_count = 1
        group_min_amount = int(0.1 * (10**6))
        group_max_amount = int(2 * (10**6))
        res, action = self.initActivity(user_account, act_id, start_time, terminal_time, amount_reach_to_standard, halfway_redeemable, percent_redeem_fee, group_min_person_count, group_min_amount, group_max_amount, user_account, user_key)
        logger.info(res)

        assert "terminal_time invalid" in res["error"]["details"][0]["message"]

        act_table2 = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"表数据: {act_table2}")

        assert act_table2 == act_table

    def test_initActivity_terminalTimeLessThanCurrentTime(self, act_id):
        act_table = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"表数据: {act_table}")

        start_time = int(datetime.datetime.utcnow().timestamp() * 1000 + 1 * 3600)
        terminal_time = int(datetime.datetime.utcnow().timestamp() * 1000 + 2 * 3600)
        amount_reach_to_standard = int(5 * ratio_base)
        halfway_redeemable = True
        percent_redeem_fee = int(0.1 * ratio_base)
        group_min_person_count = 1
        group_min_amount = int(0.1 * (10**6))
        group_max_amount = int(2 * (10**6))
        res, action = self.initActivity(user_account, act_id, start_time, terminal_time, amount_reach_to_standard, halfway_redeemable, percent_redeem_fee, group_min_person_count, group_min_amount, group_max_amount, user_account, user_key)
        logger.info(res)

        assert "terminal_time expired" in res["error"]["details"][0]["message"]

        act_table2 = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"表数据: {act_table2}")

        assert act_table2 == act_table

    def test_setBonusConf(self, act_id, platform_share_ratio=int(0.15 * ratio_base), rebate_share_ratio=int(0.02 * ratio_base), sponsor_share_ratio=int(0.05 * ratio_base), bus_first_redeem_ratio=int(0 * ratio_base), performance_ratio=int(0.8 * ratio_base), order_rebate_share_ratio=int(0.03 * ratio_base)):
        # platform_share_ratio = int(0.15 * ratio_base)
        # rebate_share_ratio = int(0.02 * ratio_base)
        # sponsor_share_ratio = int(0.05 * ratio_base)
        # bus_first_redeem_ratio = int(0 * ratio_base)
        # performance_ratio = int(0.8 * ratio_base)
        # order_rebate_share_ratio = int(0.03 * ratio_base)
        res, action = self.setBonusConf(user_account, act_id, platform_share_ratio, sponsor_share_ratio, rebate_share_ratio, bus_first_redeem_ratio, performance_ratio, order_rebate_share_ratio, user_account, user_key)
        logger.info(res)

        act_table = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"表数据: {act_table}")

        act_data = [i for i in act_table["rows"] if i["_ACTIVITY_ID_"] == act_id][0]
        assert act_data["_ACTIVITY_STORE_"]["_PLATFORM_SHARE_RATIO_"] == action["platform_share_ratio"]
        assert act_data["_ACTIVITY_STORE_"]["_SPONSOR_SHARE_RATIO_"] == action["sponsor_share_ratio"]
        assert act_data["_ACTIVITY_STORE_"]["_REBATE_SHARE_RATIO_"] == action["rebate_share_ratio"]
        assert act_data["_ACTIVITY_STORE_"]["_BUS_FIRST_REDEEM_RATIO_"] == action["bus_first_redeem_ratio"]
        assert act_data["_ACTIVITY_STORE_"]["_PERFORMANCE_RATIO_"] == action["performance_ratio"]

    def test_setBonusConf_ratioTooHigh(self, act_id):

        act_table = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"表数据: {act_table}")

        platform_share_ratio = int(0.1 * ratio_base)
        rebate_share_ratio = int(0.3 * ratio_base)
        sponsor_share_ratio = int(0.4 * ratio_base)
        bus_first_redeem_ratio = int(0.3 * ratio_base)
        performance_ratio = int(0.8 * ratio_base)
        order_rebate_share_ratio = int(0.03 * ratio_base)
        res, action = self.setBonusConf(user_account, act_id, platform_share_ratio + 100000000, sponsor_share_ratio, rebate_share_ratio, bus_first_redeem_ratio, performance_ratio, order_rebate_share_ratio, user_account, user_key)
        logger.info(res)
        assert "platform share invalid" in res["error"]["details"][0]["message"]

        res, action = self.setBonusConf(user_account, act_id, platform_share_ratio, sponsor_share_ratio + 100000000, rebate_share_ratio, bus_first_redeem_ratio, performance_ratio, order_rebate_share_ratio, user_account, user_key)
        logger.info(res)
        assert "rebate share ratio too high" in res["error"]["details"][0]["message"]

        res, action = self.setBonusConf(user_account, act_id, platform_share_ratio, sponsor_share_ratio, rebate_share_ratio + 100000000, bus_first_redeem_ratio, performance_ratio, order_rebate_share_ratio, user_account, user_key)
        logger.info(res)
        assert "rebate share ratio too high" in res["error"]["details"][0]["message"]

        res, action = self.setBonusConf(user_account, act_id, platform_share_ratio, sponsor_share_ratio, rebate_share_ratio, bus_first_redeem_ratio + 100000000, performance_ratio, order_rebate_share_ratio, user_account, user_key)
        logger.info(res)
        assert "business first redeem ratio invalid" in res["error"]["details"][0]["message"]

        res, action = self.setBonusConf(user_account, act_id, platform_share_ratio, sponsor_share_ratio, rebate_share_ratio, bus_first_redeem_ratio, performance_ratio + 100000000, order_rebate_share_ratio, user_account, user_key)
        logger.info(res)
        assert "performance ratio invalid" in res["error"]["details"][0]["message"]

        act_table2 = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"表数据: {act_table2}")

        assert act_table2 == act_table

    def test_addConductor(self, business, activity, conductor, business_key):
        state = self.chain_client.get_table(group, activity, "activityinfo")
        logger.info(f"group factory表信息: {state}")

        res = self.addConductor(business, activity, conductor, business, business_key)
        logger.info(f"交易结果: {res}")

        state2 = self.chain_client.get_table(group, activity, "activityinfo")
        logger.info(f"group factory表信息: {state2}")

        assert conductor in state2["rows"][0]["_ACTIVITY_STORE_"]["_GROUP_CONDUCTORS_"]

    def test_delConductor(self, business, activity, conductor, business_key):
        state = self.chain_client.get_table(group, activity, "activityinfo")
        logger.info(f"group factory表信息: {state}")

        res = self.delConductor(business, activity, conductor, business, business_key)
        logger.info(f"交易结果: {res}")

        state2 = self.chain_client.get_table(group, activity, "activityinfo")
        logger.info(f"group factory表信息: {state2}")

        assert conductor not in state2["rows"][0]["_ACTIVITY_STORE_"]["_GROUP_CONDUCTORS_"]

    def test_autoGroup(self, business, activity, autoGroup, business_key):
        state = self.chain_client.get_table(group, activity, "activityinfo")
        logger.info(f"group factory表信息: {state}")

        res = self.autoGroup(business, activity, autoGroup, business, business_key)
        logger.info(f"交易结果: {res}")

        state2 = self.chain_client.get_table(group, activity, "activityinfo")
        logger.info(f"group factory表信息: {state2}")

        ex_auto_group = 1 if autoGroup else 0
        assert ex_auto_group == state2["rows"][0]["_ACTIVITY_STORE_"]["_AUTO_GROUPING_"]

    def test_autoGroup_activityNotExist(self, business, activity, autoGroup, business_key):
        state = self.chain_client.get_table(group, activity, "activityinfo")
        logger.info(f"group factory表信息: {state}")

        res = self.autoGroup(business, activity, autoGroup, business, business_key)
        logger.info(f"交易结果: {res}")
        assert "group activity not exist" in res["error"]["details"][0]["message"]
        state2 = self.chain_client.get_table(group, activity, "activityinfo")
        logger.info(f"group factory表信息: {state2}")

        assert state2 == state2

    def test_setFreeStart(self, business, activity, free, business_key):
        state = self.chain_client.get_table(group, activity, "activityinfo")
        logger.info(f"group factory表信息: {state}")

        res = self.setFreeStart(business, activity, free, business, business_key)
        logger.info(f"交易结果: {res}")

        state2 = self.chain_client.get_table(group, activity, "activityinfo")
        logger.info(f"group factory表信息: {state2}")

        ex_free = 1 if free else 0
        assert ex_free == state2["rows"][0]["_ACTIVITY_STORE_"]["_CONSTRAINT_START_"]

    def test_setExceed(self, business, activity, can_exceed, business_key):
        state = self.chain_client.get_table(group, activity, "activityinfo")
        logger.info(f"group factory表信息: {state}")

        res = self.setExceed(business, activity, can_exceed, business, business_key)
        logger.info(f"交易结果: {res}")

        state2 = self.chain_client.get_table(group, activity, "activityinfo")
        logger.info(f"group factory表信息: {state2}")

        ex_can_exceed = 1 if can_exceed else 0
        assert ex_can_exceed == state2["rows"][0]["_ACTIVITY_STORE_"]["_CAN_EXCEED_TOTAL_AMOUNT_"]

    def test_freezeGift(self, business, activity, freeze_amount, business_key):
        state = self.chain_client.get_table(group, activity, "activityinfo")
        logger.info(f"group factory表信息: {state}")

        res = self.freezeGift(business, activity, freeze_amount, business, business_key)
        logger.info(f"交易结果: {res}")

        state2 = self.chain_client.get_table(group, activity, "activityinfo")
        logger.info(f"group factory表信息: {state2}")

        assert freeze_amount == state2["rows"][0]["_ACTIVITY_STORE_"]["_GIFT_TOKEN_FREEZED_AMOUNT_"] - state["rows"][0]["_ACTIVITY_STORE_"]["_GIFT_TOKEN_FREEZED_AMOUNT_"]

    def test_unfreezeGift(self, business, activity, unfreeze_amount, business_key):
        state = self.chain_client.get_table(group, activity, "activityinfo")
        logger.info(f"group factory表信息: {state}")

        res = self.unfreezeGift(business, activity, unfreeze_amount, business, business_key)
        logger.info(f"交易结果: {res}")

        state2 = self.chain_client.get_table(group, activity, "activityinfo")
        logger.info(f"group factory表信息: {state2}")

        assert unfreeze_amount == state["rows"][0]["_ACTIVITY_STORE_"]["_GIFT_TOKEN_FREEZED_AMOUNT_"] - state2["rows"][0]["_ACTIVITY_STORE_"]["_GIFT_TOKEN_FREEZED_AMOUNT_"]

    def test_setOrdCancel(self, business, activity, is_cancel, business_key):
        state = self.chain_client.get_table(group, activity, "activityinfo")
        logger.info(f"group factory表信息: {state}")

        res = self.setOrdCancel(business, activity, is_cancel, business, business_key)
        logger.info(f"交易结果: {res}")

        state2 = self.chain_client.get_table(group, activity, "activityinfo")
        logger.info(f"group factory表信息: {state2}")

        ex_value = 1 if is_cancel else 0
        assert ex_value == state2["rows"][0]["_ACTIVITY_STORE_"]["_CAN_CANCEL_ORDER_"]

    def test_setRebate(self, business, activity, is_rebate, business_key):
        state = self.chain_client.get_table(group, activity, "activityinfo")
        logger.info(f"group factory表信息: {state}")

        res = self.setRebate(business, activity, is_rebate, business, business_key)
        logger.info(f"交易结果: {res}")

        state2 = self.chain_client.get_table(group, activity, "activityinfo")
        logger.info(f"group factory表信息: {state2}")

        ex_value = 1 if is_rebate else 0
        assert ex_value == state2["rows"][0]["_ACTIVITY_STORE_"]["_REBATE_ORDER_NOW_"]

    def test_setCancelOrderRatio(self, business, activity, _cancel_order_ratio, business_key):
        state = self.chain_client.get_table(group, activity, "activityinfo")
        logger.info(f"group factory表信息: {state}")

        res = self.setCancelRatio(business, activity, _cancel_order_ratio, business, business_key)
        logger.info(f"交易结果: {res}")

        state2 = self.chain_client.get_table(group, activity, "activityinfo")
        logger.info(f"group factory表信息: {state2}")

        assert _cancel_order_ratio == state2["rows"][0]["_ACTIVITY_STORE_"]["_CANCEL_ORDER_RATIO_"]

    def test_newGroup_notSponsorCall(self, act_id, group_id, price=400000000, max_gift_amount=2000000, min_person=1):
        res, action = self.newGroup(act_id, group_id, user_account2, min_person, price, max_gift_amount, user_account2, user_key2)
        logger.info(f"交易结果: {res}")

        group_info = self.chain_client.get_table(group, group_id, "groupinfo")
        logger.info(group_info)

        assert group_info["rows"][0]["_GROUP_ID_"] == action["_group_id"]
        assert group_info["rows"][0]["_SPONSOR_"] == action["_sponsor"]
        assert group_info["rows"][0]["_MAX_GIFT_AMOUNT_"] == action["_max_amount"]
        assert group_info["rows"][0]["_DISCOUNT_PRICE_"] == action["_discount_price"]
        assert group_info["rows"][0]["_MIN_PERSON_COUNT"] == action["_min_person_count"]
        assert group_info["rows"][0]["_PLATFORMAMOUNT_"] == 0
        assert group_info["rows"][0]["_BUSINESSAMOUNT_"] == 0
        assert group_info["rows"][0]["_ISSUED_"] == 0
        assert group_info["rows"][0]["_FINISH_"] == 0
        assert group_info["rows"][0]["_CANCELED_"] == 0

    def test_newGroup_activityNotInit(self, act_id, group_id):
        res, action = self.newGroup(act_id, group_id, user_account2, 1, 400000000, 2000000, user_account2, user_key2)
        logger.info(f"交易结果: {res}")

        assert "activity not initialized" in res["error"]["details"][0]["message"]

    def test_revokeGroup_justNew(self, act_id, group_id, order_id=None):
        ro_balance = self.chain_client.get_currency_balance(user_account2, "roxe.ro", "USD")
        logger.info(f"账户ro资产: {ro_balance}")
        gift_balance = self.chain_client.get_currency_balance(user_account2, gift_card_account, gift_symbol)
        logger.info(f"账户礼品卡资产: {gift_balance}")

        group_info = self.chain_client.get_table(group, group_id, "groupinfo")
        logger.info(group_info)

        order_info = None
        if order_id:
            order_info = self.chain_client.get_table(group, order_id, "orderinfo")
            logger.info(f"订单信息: {order_info}")
        res, action = self.revokeGroup(act_id, group_id, user_account2, user_key2)
        logger.info(f"交易结果: {res}")

        group_info = self.chain_client.get_table(group, group_id, "groupinfo")
        logger.info(group_info)
        ro_balance2 = self.chain_client.get_currency_balance(user_account2, "roxe.ro", "USD")
        logger.info(f"账户ro资产: {ro_balance2}")
        gift_balance2 = self.chain_client.get_currency_balance(user_account2, gift_card_account, gift_symbol)
        logger.info(f"账户礼品卡资产: {gift_balance2}")

        if "error" not in res:
            assert group_info["rows"][0]["_CANCELED_"] == 1

        GiftCard.checkBalanceChange(ro_balance, ro_balance2, order_info["rows"][0]["_PAYAMOUNT_"] / 1000000)

    @staticmethod
    def parseBalance(balance):
        b1 = 0
        if balance:
            if isinstance(balance, list):
                balance = balance[0]
            else:
                balance = balance

            if isinstance(balance, str) and " " in balance:
                b1 = float(balance.split(" ")[0])
            else:
                b1 = balance
        return b1

    @staticmethod
    def checkBalanceChange(balance1, balance2, change_amount, msg="持有的ro数量"):
        b1 = GiftCard.parseBalance(balance1)
        b2 = GiftCard.parseBalance(balance2)
        logger.info(f"{msg}变化了: {b2 - b1}")
        assert abs(b2 - b1 - change_amount) < 0.1 ** 7, f"资产校验失败: {b2 - b1}、{change_amount}"

    def test_purchase_totalAmount(self, act_id, group_id, order_id, group_amount, invitor=""):

        group_info = self.chain_client.get_table(group, group_id, "groupinfo")
        logger.info(f"拼团详情: {group_info}")

        act_info = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"活动详情: {act_info}")

        ro_balance = self.chain_client.get_currency_balance(user_account2, "roxe.ro", "USD")
        logger.info(f"账户ro资产: {ro_balance}")
        gift_balance = self.chain_client.get_currency_balance(user_account2, gift_card_account, gift_symbol)
        logger.info(f"账户礼品卡资产: {gift_balance}")

        gift_info = self.chain_client.get_table(gift_card_account, gift_symbol, "stat")
        logger.info(f"礼品卡发行: {gift_info}")

        res, action = self.purchase(act_id, group_id, order_id, user_account2, user_account2, invitor, group_amount, user_account2, user_key2)
        logger.info(f"交易结果: {res}")

        order_info = self.chain_client.get_table(group, order_id, "orderinfo")
        logger.info(order_info)

        busi_amount, plat_amount, sponsor_amount, invite_amount, order_amount = calPlatAmount(act_info, group_info, order_info)

        ro_balance2 = self.chain_client.get_currency_balance(user_account2, "roxe.ro", "USD")
        logger.info(f"账户ro资产: {ro_balance2}")
        gift_balance2 = self.chain_client.get_currency_balance(user_account2, gift_card_account, gift_symbol)
        logger.info(f"账户礼品卡资产: {gift_balance2}")

        gift_info2 = self.chain_client.get_table(gift_card_account, gift_symbol, "stat")
        logger.info(f"礼品卡发行: {gift_info2}")

        group_info2 = self.chain_client.get_table(group, group_id, "groupinfo")
        logger.info(group_info2)

        act_info2 = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"活动详情: {act_info2}")
        assert order_info["rows"][0]["_ORDER_ID_"] == order_id
        assert order_info["rows"][0]["_CUSTOMER_"] == action["_buyer"]
        assert order_info["rows"][0]["_RECEIVER_"] == action["_receiver"]
        assert order_info["rows"][0]["_PAYAMOUNT_"] == action["_subscript_amounts"]

        ex_ro = group_amount - sponsor_amount - order_amount if act_info["rows"][0]["_ACTIVITY_STORE_"]["_REBATE_ORDER_NOW_"] == 1 else group_amount
        GiftCard.checkBalanceChange(ro_balance, ro_balance2, - ex_ro / 1000000)
        ex_gift = ApiUtils.parseNumberDecimal(group_amount * 100 / group_info["rows"][0]["_DISCOUNT_PRICE_"], 6)
        if act_info["rows"][0]["_ACTIVITY_STORE_"]["_AUTO_GROUPING_"] == 0:
            ex_gift = 0
        GiftCard.checkBalanceChange(gift_balance, gift_balance2, ex_gift, "持有的礼品卡数量")
        GiftCard.checkBalanceChange(gift_info["rows"][0]["supply"], gift_info2["rows"][0]["supply"], ex_gift, "礼品卡发行量")
        GiftCard.checkBalanceChange(act_info["rows"][0]["_ACTIVITY_STORE_"]["_GIFT_TOKEN_FREEZED_AMOUNT_"], act_info2["rows"][0]["_ACTIVITY_STORE_"]["_GIFT_TOKEN_FREEZED_AMOUNT_"], int(ex_gift * token_base), "礼品卡发行量在activity中的记录")
        GiftCard.checkBalanceChange(act_info["rows"][0]["_ACTIVITY_STORE_"]["_GIFT_TOKEN_PERFORM_AMOUNT_"], act_info2["rows"][0]["_ACTIVITY_STORE_"]["_GIFT_TOKEN_PERFORM_AMOUNT_"], 0, "礼品卡商家销毁的总量")

        if act_info["rows"][0]["_ACTIVITY_STORE_"]["_REBATE_ORDER_NOW_"] == 1:
            assert order_info["rows"][0]["_REBATED_"] == 1
        else:
            assert order_info["rows"][0]["_REBATED_"] == 0
        assert order_info["rows"][0]["_CANCELED_"] == 0
        assert order_info["rows"][0]["_CONFIRMED_"] == 1

    def test_newGroupAndBuy_notSponsorCall(self, act_id, group_id, order_id, group_amount, price=400000000, max_gift_amount=2000000, min_person=1):
        act_info = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"活动详情: {act_info}")

        from_account = user_account2
        from_key = user_key2

        ro_balance = self.chain_client.get_currency_balance(from_account, "roxe.ro", "USD")
        logger.info(f"账户ro资产: {ro_balance}")
        gift_balance = self.chain_client.get_currency_balance(from_account, gift_card_account, gift_symbol)
        logger.info(f"账户礼品卡资产: {gift_balance}")

        gift_info = self.chain_client.get_table(gift_card_account, gift_symbol, "stat")
        logger.info(f"礼品卡发行: {gift_info}")

        res, action = self.newGroupAndBuy(act_id, group_id, order_id, from_account, min_person, price, max_gift_amount, from_account, group_amount, from_account, from_key)
        logger.info(f"交易结果: {res}")
        if "message" in res:
            raise Exception(json.dumps(res))
        group_info = self.chain_client.get_table(group, group_id, "groupinfo")
        logger.info(f"拼团详情: {group_info}")

        order_info = self.chain_client.get_table(group, order_id, "orderinfo")
        logger.info(f"订单详情: {order_info}")

        busi_amount, plat_amount, sponsor_amount, invite_amount, order_amount = calPlatAmount(act_info, group_info, order_info)

        ro_balance2 = self.chain_client.get_currency_balance(from_account, "roxe.ro", "USD")
        logger.info(f"账户ro资产: {ro_balance2}")
        gift_balance2 = self.chain_client.get_currency_balance(from_account, gift_card_account, gift_symbol)
        logger.info(f"账户礼品卡资产: {gift_balance2}")

        gift_info2 = self.chain_client.get_table(gift_card_account, gift_symbol, "stat")
        logger.info(f"礼品卡发行: {gift_info2}")

        group_info2 = self.chain_client.get_table(group, group_id, "groupinfo")
        logger.info(f"拼团详情: {group_info2}")

        act_info2 = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"活动详情: {act_info2}")
        assert str(order_info["rows"][0]["_ORDER_ID_"]) == str(order_id)
        assert order_info["rows"][0]["_CUSTOMER_"] == action["_sponsor"]
        assert order_info["rows"][0]["_RECEIVER_"] == action["_receiver"]
        assert str(order_info["rows"][0]["_PAYAMOUNT_"]) == str(action["_subscript_amounts"])

        ex_ro = group_amount - sponsor_amount - order_amount if act_info["rows"][0]["_ACTIVITY_STORE_"]["_REBATE_ORDER_NOW_"] == 1 else group_amount
        if act_info["rows"][0]["_ACTIVITY_STORE_"]["_AMOUNT_REACH_TO_STANDARD_"] > 0:
            if group_amount * price / ratio_base < act_info["rows"][0]["_ACTIVITY_STORE_"]["_AMOUNT_REACH_TO_STANDARD_"]:
                ex_ro = group_amount

            if act_info["rows"][0]["_ACTIVITY_STORE_"]["_GROUP_TERMINAL_TIME"] != 0 and act_info["rows"][0]["_ACTIVITY_STORE_"]["_CAN_EXCEED_TOTAL_AMOUNT_"] == 1:
                ex_ro = group_amount
        GiftCard.checkBalanceChange(ro_balance, ro_balance2, - ex_ro / 1000000)
        ex_gift = ApiUtils.parseNumberDecimal(group_amount * 100 / group_info["rows"][0]["_DISCOUNT_PRICE_"], 6)
        if act_info["rows"][0]["_ACTIVITY_STORE_"]["_AUTO_GROUPING_"] == 0:
            ex_gift = 0

        if act_info["rows"][0]["_ACTIVITY_STORE_"]["_AMOUNT_REACH_TO_STANDARD_"] > 0:
            if group_amount * price / ratio_base < act_info["rows"][0]["_ACTIVITY_STORE_"]["_AMOUNT_REACH_TO_STANDARD_"]:
                ex_gift = 0
        GiftCard.checkBalanceChange(gift_balance, gift_balance2, ex_gift, "持有的礼品卡数量")
        GiftCard.checkBalanceChange(gift_info["rows"][0]["supply"], gift_info2["rows"][0]["supply"], ex_gift, "礼品卡发行量")
        GiftCard.checkBalanceChange(int(act_info["rows"][0]["_ACTIVITY_STORE_"]["_GIFT_TOKEN_FREEZED_AMOUNT_"]), int(act_info2["rows"][0]["_ACTIVITY_STORE_"]["_GIFT_TOKEN_FREEZED_AMOUNT_"]), int(ex_gift * token_base), "礼品卡发行量在activity中的记录")
        GiftCard.checkBalanceChange(int(act_info["rows"][0]["_ACTIVITY_STORE_"]["_GIFT_TOKEN_PERFORM_AMOUNT_"]), int(act_info2["rows"][0]["_ACTIVITY_STORE_"]["_GIFT_TOKEN_PERFORM_AMOUNT_"]), 0, "礼品卡商家销毁的总量")

        assert group_info["rows"][0]["_GROUP_ID_"] == action["_group_id"]
        assert group_info["rows"][0]["_SPONSOR_"] == action["_sponsor"]
        assert group_info["rows"][0]["_MAX_GIFT_AMOUNT_"] == action["_max_amount"]
        assert group_info["rows"][0]["_DISCOUNT_PRICE_"] == action["_discount_price"]
        assert group_info["rows"][0]["_MIN_PERSON_COUNT"] == action["_min_person_count"]
        assert group_info["rows"][0]["_PLATFORMAMOUNT_"] == 0
        assert group_info["rows"][0]["_BUSINESSAMOUNT_"] == 0

        assert order_info["rows"][0]["_REBATED_"] == act_info["rows"][0]["_ACTIVITY_STORE_"]["_REBATE_ORDER_NOW_"]
        assert order_info["rows"][0]["_CANCELED_"] == 0
        assert order_info["rows"][0]["_CONFIRMED_"] == 1
        assert group_info["rows"][0]["_ISSUED_"] == 1
        assert group_info["rows"][0]["_FINISH_"] == 1
        assert group_info["rows"][0]["_CANCELED_"] == 0

    def test_delivery(self, act_id, group_id, order_id):

        group_info = self.chain_client.get_table(group, group_id, "groupinfo")
        logger.info(f"拼团详情: {group_info}")

        act_info = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"活动详情: {act_info}")

        gift_info = self.chain_client.get_table(gift_card_account, gift_symbol, "stat")
        logger.info(f"礼品卡发行: {gift_info}")

        ro_balance = self.chain_client.get_currency_balance(user_account2, "roxe.ro", "USD")
        logger.info(f"账户ro资产: {ro_balance}")
        gift_balance = self.chain_client.get_currency_balance(user_account2, gift_card_account, gift_symbol)
        logger.info(f"账户礼品卡资产: {gift_balance}")

        res, action = self.delivery(act_id, group_id, order_id, user_account2, user_key2)
        logger.info(f"交易结果: {res}")

        order_info = self.chain_client.get_table(group, order_id, "orderinfo")
        logger.info(order_info)

        ro_balance2 = self.chain_client.get_currency_balance(user_account2, "roxe.ro", "USD")
        logger.info(f"账户ro资产: {ro_balance2}")
        gift_balance2 = self.chain_client.get_currency_balance(user_account2, gift_card_account, gift_symbol)
        logger.info(f"账户礼品卡资产: {gift_balance2}")

        gift_info2 = self.chain_client.get_table(gift_card_account, gift_symbol, "stat")
        logger.info(f"礼品卡发行: {gift_info2}")

        group_info2 = self.chain_client.get_table(group, group_id, "groupinfo")
        logger.info(group_info2)

        act_info2 = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"活动详情: {act_info2}")

        ex_gift = ApiUtils.parseNumberDecimal(order_info["rows"][0]["_PAYAMOUNT_"] * 100 / group_info["rows"][0]["_DISCOUNT_PRICE_"], 6)
        GiftCard.checkBalanceChange(gift_balance, gift_balance2, ex_gift, "持有的礼品卡数量")
        GiftCard.checkBalanceChange(gift_info["rows"][0]["supply"], gift_info2["rows"][0]["supply"], ex_gift, "礼品卡发行量")
        GiftCard.checkBalanceChange(act_info["rows"][0]["_ACTIVITY_STORE_"]["_GIFT_TOKEN_FREEZED_AMOUNT_"], act_info2["rows"][0]["_ACTIVITY_STORE_"]["_GIFT_TOKEN_FREEZED_AMOUNT_"], int(ex_gift * token_base), "礼品卡发行量在activity中的记录")
        GiftCard.checkBalanceChange(act_info["rows"][0]["_ACTIVITY_STORE_"]["_GIFT_TOKEN_PERFORM_AMOUNT_"], act_info2["rows"][0]["_ACTIVITY_STORE_"]["_GIFT_TOKEN_PERFORM_AMOUNT_"], 0, "礼品卡商家销毁的总量")

        assert order_info["rows"][0]["_CONFIRMED_"] == act_info["rows"][0]["_ACTIVITY_STORE_"]["_REBATE_ORDER_NOW_"]

    def test_confirmOrder(self, act_id, group_id, order_id):

        group_info = self.chain_client.get_table(group, group_id, "groupinfo")
        logger.info(group_info)

        ro_balance = self.chain_client.get_currency_balance(user_account2, "roxe.ro", "USD")
        logger.info(f"账户ro资产: {ro_balance}")
        gift_balance = self.chain_client.get_currency_balance(user_account2, gift_card_account, gift_symbol)
        logger.info(f"账户礼品卡资产: {gift_balance}")

        res, action = self.confirmOrder(act_id, group_id, order_id, user_account2, user_key2)
        logger.info(f"交易结果: {res}")

        order_info = self.chain_client.get_table(group, order_id, "orderinfo")
        logger.info(order_info)

        ro_balance2 = self.chain_client.get_currency_balance(user_account2, "roxe.ro", "USD")
        logger.info(f"账户ro资产: {ro_balance2}")
        gift_balance2 = self.chain_client.get_currency_balance(user_account2, gift_card_account, gift_symbol)
        logger.info(f"账户礼品卡资产: {gift_balance2}")

        assert order_info["rows"][0]["_CONFIRMED_"] == 1
        assert order_info["rows"][0]["_FINISH_"] == 1

    def test_plat_collect_amount(self, act_id, group_id, collect_amount):

        group_info = self.chain_client.get_table(group, group_id, "groupinfo")
        logger.info(f"拼团详情: {group_info}")

        act_info = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"活动详情: {act_info}")

        plat_user = act_info["rows"][0]["_ACTIVITY_STORE_"]["_PLATE_MANAGER_"]

        groups = self.chain_client.get_table(group, group, "group")
        group_orders = []
        for i in groups["rows"][0]["_GROUPORDERS_"]:
            if i["key"] == group_id:
                group_orders = i["value"]["_IDSET_"]
        logger.info(f"找到的拼团订单: {group_orders}")
        ro_balance = self.chain_client.get_currency_balance(plat_user, "roxe.ro", "USD")
        logger.info(f"账户ro资产: {ro_balance}")
        gift_balance = self.chain_client.get_currency_balance(plat_user, gift_card_account, "USD")
        logger.info(f"账户礼品卡资产: {gift_balance}")

        gift_info = self.chain_client.get_table(gift_card_account, gift_symbol, "stat")
        logger.info(f"礼品卡发行: {gift_info}")

        assert plat_user == user_account2
        order_id = group_orders[0]
        order_info = self.chain_client.get_table(group, order_id, "orderinfo")
        logger.info(f"订单详情: {order_info}")
        busi_amount, plat_amount, sponsor_amount, invite_amount, order_amount = calPlatAmount(act_info, group_info, order_info)
        logger.info(f"平台方最大可以分得: {plat_amount}, 分账数量: {collect_amount}, 是否成功: {plat_amount >= collect_amount}")
        res, action = self.collect(act_id, group_id, collect_amount, user_account2, user_key2)
        logger.info(f"交易结果: {res}")

        ro_balance2 = self.chain_client.get_currency_balance(plat_user, "roxe.ro", "USD")
        logger.info(f"账户ro资产: {ro_balance2}")
        gift_balance2 = self.chain_client.get_currency_balance(plat_user, gift_card_account, "USD")
        logger.info(f"账户礼品卡资产: {gift_balance2}")

        gift_info2 = self.chain_client.get_table(gift_card_account, gift_symbol, "stat")
        logger.info(f"礼品卡发行: {gift_info2}")

        group_info2 = self.chain_client.get_table(group, group_id, "groupinfo")
        logger.info(group_info2)

        act_info2 = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"活动详情: {act_info2}")

        GiftCard.checkBalanceChange(ro_balance, ro_balance2, collect_amount / 1000000)
        GiftCard.checkBalanceChange(gift_balance, gift_balance2, 0, "持有的礼品卡数量")
        GiftCard.checkBalanceChange(group_info["rows"][0]["_PLATFORMAMOUNT_"], group_info2["rows"][0]["_PLATFORMAMOUNT_"], collect_amount, "平台分账的数量在group的记录")

    def test_plat_collect_amountTooMuch(self, act_id, group_id):

        group_info = self.chain_client.get_table(group, group_id, "groupinfo")
        logger.info(f"拼团详情: {group_info}")

        act_info = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"活动详情: {act_info}")

        plat_user = act_info["rows"][0]["_ACTIVITY_STORE_"]["_PLATE_MANAGER_"]

        groups = self.chain_client.get_table(group, group, "group")
        group_orders = []
        for i in groups["rows"][0]["_GROUPORDERS_"]:
            if i["key"] == group_id:
                group_orders = i["value"]["_IDSET_"]
        logger.info(f"找到的拼团订单: {group_orders}")
        ro_balance = self.chain_client.get_currency_balance(plat_user, "roxe.ro", "USD")
        logger.info(f"账户ro资产: {ro_balance}")
        gift_balance = self.chain_client.get_currency_balance(plat_user, gift_card_account, "USD")
        logger.info(f"账户礼品卡资产: {gift_balance}")

        gift_info = self.chain_client.get_table(gift_card_account, gift_symbol, "stat")
        logger.info(f"礼品卡发行: {gift_info}")

        order_id = group_orders[0]
        order_info = self.chain_client.get_table(group, order_id, "orderinfo")
        logger.info(order_info)

        assert plat_user == user_account2

        busi_amount, plat_amount, sponsor_amount, invite_amount, order_amount = calPlatAmount(act_info, group_info, order_info)
        collect_amount = plat_amount + 1
        logger.info(f"平台方最大可以分得: {plat_amount}, 分账数量: {collect_amount}, 是否成功: {plat_amount >= collect_amount}")
        res, action = self.collect(act_id, group_id, collect_amount, user_account2, user_key2)
        logger.info(f"交易结果: {res}")

        assert f"platform provider subscription-token overdrawn, left {plat_amount}" in res["error"]["details"][0]["message"]

        order_info = self.chain_client.get_table(group, order_id, "orderinfo")
        logger.info(order_info)

        ro_balance2 = self.chain_client.get_currency_balance(plat_user, "roxe.ro", "USD")
        logger.info(f"账户ro资产: {ro_balance2}")
        gift_balance2 = self.chain_client.get_currency_balance(plat_user, gift_card_account, "USD")
        logger.info(f"账户礼品卡资产: {gift_balance2}")

        gift_info2 = self.chain_client.get_table(gift_card_account, gift_symbol, "stat")
        logger.info(f"礼品卡发行: {gift_info2}")

        group_info2 = self.chain_client.get_table(group, group_id, "groupinfo")
        logger.info(group_info2)

        act_info2 = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"活动详情: {act_info2}")

        GiftCard.checkBalanceChange(ro_balance, ro_balance2, 0)
        GiftCard.checkBalanceChange(gift_balance, gift_balance2, 0, "持有的礼品卡数量")
        GiftCard.checkBalanceChange(group_info["rows"][0]["_PLATFORMAMOUNT_"], group_info2["rows"][0]["_PLATFORMAMOUNT_"], 0, "平台分账的数量在group的记录")

    def test_plat_collect_notPlatUserCall(self, act_id, group_id):

        group_info = self.chain_client.get_table(group, group_id, "groupinfo")
        logger.info(f"拼团详情: {group_info}")

        act_info = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"活动详情: {act_info}")

        plat_user = act_info["rows"][0]["_ACTIVITY_STORE_"]["_PLATE_MANAGER_"]

        groups = self.chain_client.get_table(group, group, "group")
        group_orders = []
        for i in groups["rows"][0]["_GROUPORDERS_"]:
            if i["key"] == group_id:
                group_orders = i["value"]["_IDSET_"]
        logger.info(f"找到的拼团订单: {group_orders}")
        ro_balance = self.chain_client.get_currency_balance(plat_user, "roxe.ro", "USD")
        logger.info(f"账户ro资产: {ro_balance}")
        gift_balance = self.chain_client.get_currency_balance(plat_user, gift_card_account, "USD")
        logger.info(f"账户礼品卡资产: {gift_balance}")

        gift_info = self.chain_client.get_table(gift_card_account, gift_symbol, "stat")
        logger.info(f"礼品卡发行: {gift_info}")

        order_id = group_orders[0]
        order_info = self.chain_client.get_table(group, order_id, "orderinfo")
        logger.info(order_info)

        assert plat_user == user_account2

        busi_amount, plat_amount, sponsor_amount, invite_amount, order_amount = calPlatAmount(act_info, group_info, order_info)
        collect_amount = plat_amount + 1
        logger.info(f"平台方最大可以分得{plat_amount}, 分账数量: {collect_amount}, 是否成功: {plat_amount >= collect_amount}")
        res, action = self.collect(act_id, group_id, collect_amount, group, group_key)
        logger.info(f"交易结果: {res}")

        assert f"missing authority of {plat_user}" in res["error"]["details"][0]["message"]

        order_info = self.chain_client.get_table(group, order_id, "orderinfo")
        logger.info(order_info)

        ro_balance2 = self.chain_client.get_currency_balance(plat_user, "roxe.ro", "USD")
        logger.info(f"账户ro资产: {ro_balance2}")
        gift_balance2 = self.chain_client.get_currency_balance(plat_user, gift_card_account, "USD")
        logger.info(f"账户礼品卡资产: {gift_balance2}")

        gift_info2 = self.chain_client.get_table(gift_card_account, gift_symbol, "stat")
        logger.info(f"礼品卡发行: {gift_info2}")

        group_info2 = self.chain_client.get_table(group, group_id, "groupinfo")
        logger.info(group_info2)

        act_info2 = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"活动详情: {act_info2}")

        GiftCard.checkBalanceChange(ro_balance, ro_balance2, 0)
        GiftCard.checkBalanceChange(gift_balance, gift_balance2, 0, "持有的礼品卡数量")
        GiftCard.checkBalanceChange(group_info["rows"][0]["_PLATFORMAMOUNT_"], group_info2["rows"][0]["_PLATFORMAMOUNT_"], 0, "平台分账的数量在group的记录")

    def test_order_rebate_amount(self, act_id, group_id):

        group_info = self.chain_client.get_table(group, group_id, "groupinfo")
        logger.info(f"拼团详情: {group_info}")

        act_info = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"活动详情: {act_info}")

        groups = self.chain_client.get_table(group, group, "group")
        group_orders = []
        for i in groups["rows"][0]["_GROUPORDERS_"]:
            if str(i["key"]) == str(group_id):
                group_orders = i["value"]["_IDSET_"]
        logger.info(f"找到的拼团订单: {group_orders}")
        order_id = group_orders[0]
        order_info = self.chain_client.get_table(group, order_id, "orderinfo")
        logger.info(f"订单详情: {order_info}")

        order_user = order_info["rows"][0]["_CUSTOMER_"]
        ro_balance = self.chain_client.get_currency_balance(order_user, "roxe.ro", "USD")
        logger.info(f"账户ro资产: {ro_balance}")
        gift_balance = self.chain_client.get_currency_balance(order_user, gift_card_account, gift_symbol)
        logger.info(f"账户礼品卡资产: {gift_balance}")

        gift_info = self.chain_client.get_table(gift_card_account, gift_symbol, "stat")
        logger.info(f"礼品卡发行: {gift_info}")

        assert order_user == user_account2

        busi_amount, plat_amount, sponsor_amount, invite_amount, order_amount = calPlatAmount(act_info, group_info, order_info)
        res, action = self.rebate(act_id, group_id, order_id, user_account2, user_key2)
        logger.info(f"交易结果: {res}")

        ro_balance2 = self.chain_client.get_currency_balance(order_user, "roxe.ro", "USD")
        logger.info(f"账户ro资产: {ro_balance2}")
        gift_balance2 = self.chain_client.get_currency_balance(order_user, gift_card_account, gift_symbol)
        logger.info(f"账户礼品卡资产: {gift_balance2}")

        gift_info2 = self.chain_client.get_table(gift_card_account, gift_symbol, "stat")
        logger.info(f"礼品卡发行: {gift_info2}")

        group_info2 = self.chain_client.get_table(group, group_id, "groupinfo")
        logger.info(group_info2)

        act_info2 = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"活动详情: {act_info2}")
        order_info2 = self.chain_client.get_table(group, order_id, "orderinfo")

        GiftCard.checkBalanceChange(ro_balance, ro_balance2, (sponsor_amount + order_amount) / 1000000)
        GiftCard.checkBalanceChange(gift_balance, gift_balance2, 0, "持有的礼品卡数量")
        assert order_info2["rows"][0]["_REBATED_"] == 1, f"订单返利状态信息不正确: {order_info2}"
        GiftCard.checkBalanceChange(group_info["rows"][0]["_PLATFORMAMOUNT_"], group_info2["rows"][0]["_PLATFORMAMOUNT_"], 0, "平台分账的数量在group的记录")
        GiftCard.checkBalanceChange(act_info["rows"][0]["_ACTIVITY_STORE_"]["_GIFT_TOKEN_FREEZED_AMOUNT_"], act_info2["rows"][0]["_ACTIVITY_STORE_"]["_GIFT_TOKEN_FREEZED_AMOUNT_"], 0, "礼品卡发行量在activity中的记录")

    def test_order_rebate_hasRebated(self, act_id, group_id):

        group_info = self.chain_client.get_table(group, group_id, "groupinfo")
        logger.info(f"拼团详情: {group_info}")

        act_info = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"活动详情: {act_info}")

        groups = self.chain_client.get_table(group, group, "group")
        group_orders = []
        for i in groups["rows"][0]["_GROUPORDERS_"]:
            if i["key"] == group_id:
                group_orders = i["value"]["_IDSET_"]
        logger.info(f"找到的拼团订单: {group_orders}")
        order_id = group_orders[0]
        order_info = self.chain_client.get_table(group, order_id, "orderinfo")
        logger.info(f"订单详情: {order_info}")

        order_user = order_info["rows"][0]["_CUSTOMER_"]
        ro_balance = self.chain_client.get_currency_balance(order_user, "roxe.ro", "USD")
        logger.info(f"账户ro资产: {ro_balance}")
        gift_balance = self.chain_client.get_currency_balance(order_user, gift_card_account, "USD")
        logger.info(f"账户礼品卡资产: {gift_balance}")

        gift_info = self.chain_client.get_table(gift_card_account, gift_symbol, "stat")
        logger.info(f"礼品卡发行: {gift_info}")

        assert order_user == user_account2

        busi_amount, plat_amount, sponsor_amount, invite_amount, order_amount = calPlatAmount(act_info, group_info, order_info)
        logger.info(f"订单计算出的返利金额: {sponsor_amount}")
        res, action = self.rebate(act_id, group_id, order_id, user_account2, user_key2)
        logger.info(f"交易结果: {res}")
        assert "order duplicate rebate" in res["error"]["details"][0]["message"]

        ro_balance2 = self.chain_client.get_currency_balance(order_user, "roxe.ro", "USD")
        logger.info(f"账户ro资产: {ro_balance2}")
        gift_balance2 = self.chain_client.get_currency_balance(order_user, gift_card_account, "USD")
        logger.info(f"账户礼品卡资产: {gift_balance2}")

        gift_info2 = self.chain_client.get_table(gift_card_account, gift_symbol, "stat")
        logger.info(f"礼品卡发行: {gift_info2}")

        group_info2 = self.chain_client.get_table(group, group_id, "groupinfo")
        logger.info(group_info2)

        act_info2 = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"活动详情: {act_info2}")
        order_info2 = self.chain_client.get_table(group, order_id, "orderinfo")

        GiftCard.checkBalanceChange(ro_balance, ro_balance2, 0)
        GiftCard.checkBalanceChange(gift_balance, gift_balance2, 0, "持有的礼品卡数量")
        assert order_info2["rows"][0]["_REBATED_"] == 1, f"订单返利状态信息不正确: {order_info2}"
        GiftCard.checkBalanceChange(group_info["rows"][0]["_PLATFORMAMOUNT_"], group_info2["rows"][0]["_PLATFORMAMOUNT_"], 0, "平台分账的数量在group的记录")
        GiftCard.checkBalanceChange(act_info["rows"][0]["_ACTIVITY_STORE_"]["_GIFT_TOKEN_FREEZED_AMOUNT_"], act_info2["rows"][0]["_ACTIVITY_STORE_"]["_GIFT_TOKEN_FREEZED_AMOUNT_"], 0, "礼品卡发行量在activity中的记录")

    def test_business_withdraw_amount(self, act_id, group_id, amount):

        group_info = self.chain_client.get_table(group, group_id, "groupinfo")
        logger.info(f"拼团详情: {group_info}")

        act_info = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"活动详情: {act_info}")

        groups = self.chain_client.get_table(group, group, "group")
        group_orders = []
        for i in groups["rows"][0]["_GROUPORDERS_"]:
            if i["key"] == group_id:
                group_orders = i["value"]["_IDSET_"]
        logger.info(f"找到的拼团订单: {group_orders}")
        order_id = group_orders[0]
        order_info = self.chain_client.get_table(group, order_id, "orderinfo")
        logger.info(f"订单详情: {order_info}")

        business_user = act_info["rows"][0]["_ACTIVITY_STORE_"]["_SERVER_PROVIDER_"]
        ro_balance = self.chain_client.get_currency_balance(business_user, "roxe.ro", "USD")
        logger.info(f"账户ro资产: {ro_balance}")
        gift_balance = self.chain_client.get_currency_balance(business_user, gift_card_account, gift_symbol)
        logger.info(f"账户礼品卡资产: {gift_balance}")

        gift_info = self.chain_client.get_table(gift_card_account, gift_symbol, "stat")
        logger.info(f"礼品卡发行: {gift_info}")

        assert business_user == user_account

        busi_amount, plat_amount, sponsor_amount, invite_amount, order_amount = calPlatAmount(act_info, group_info, order_info)
        logger.info(f"商家最大可以分得{busi_amount}, 分账数量: {amount}, 是否成功: {busi_amount >= amount}")
        res, action = self.withdraw(act_id, group_id, amount, user_account, user_key)
        logger.info(f"交易结果: {res}")

        ro_balance2 = self.chain_client.get_currency_balance(business_user, "roxe.ro", "USD")
        logger.info(f"账户ro资产: {ro_balance2}")
        gift_balance2 = self.chain_client.get_currency_balance(business_user, gift_card_account, gift_symbol)
        logger.info(f"账户礼品卡资产: {gift_balance2}")

        gift_info2 = self.chain_client.get_table(gift_card_account, gift_symbol, "stat")
        logger.info(f"礼品卡发行: {gift_info2}")

        group_info2 = self.chain_client.get_table(group, group_id, "groupinfo")
        logger.info(group_info2)

        act_info2 = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"活动详情: {act_info2}")
        order_info2 = self.chain_client.get_table(group, order_id, "orderinfo")

        GiftCard.checkBalanceChange(ro_balance, ro_balance2, amount / 1000000)
        GiftCard.checkBalanceChange(gift_balance, gift_balance2, 0, "持有的礼品卡数量")
        assert order_info2["rows"][0]["_REBATED_"] == 1, f"订单返利状态信息不正确: {order_info2}"
        GiftCard.checkBalanceChange(group_info["rows"][0]["_PLATFORMAMOUNT_"], group_info2["rows"][0]["_PLATFORMAMOUNT_"], 0, "平台分账的数量在group的记录")
        GiftCard.checkBalanceChange(act_info["rows"][0]["_ACTIVITY_STORE_"]["_GIFT_TOKEN_FREEZED_AMOUNT_"], act_info2["rows"][0]["_ACTIVITY_STORE_"]["_GIFT_TOKEN_FREEZED_AMOUNT_"], 0, "礼品卡发行量在activity中的记录")

    def test_business_withdraw_amountTooMuch(self, act_id, group_id):

        group_info = self.chain_client.get_table(group, group_id, "groupinfo")
        logger.info(f"拼团详情: {group_info}")

        act_info = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"活动详情: {act_info}")

        groups = self.chain_client.get_table(group, group, "group")
        group_orders = []
        for i in groups["rows"][0]["_GROUPORDERS_"]:
            if i["key"] == group_id:
                group_orders = i["value"]["_IDSET_"]
        logger.info(f"找到的拼团订单: {group_orders}")
        order_id = group_orders[0]
        order_info = self.chain_client.get_table(group, order_id, "orderinfo")
        logger.info(f"订单详情: {order_info}")

        business_user = act_info["rows"][0]["_ACTIVITY_STORE_"]["_SERVER_PROVIDER_"]
        ro_balance = self.chain_client.get_currency_balance(business_user, "roxe.ro", "USD")
        logger.info(f"账户ro资产: {ro_balance}")
        gift_balance = self.chain_client.get_currency_balance(business_user, gift_card_account, "USD")
        logger.info(f"账户礼品卡资产: {gift_balance}")

        gift_info = self.chain_client.get_table(gift_card_account, gift_symbol, "stat")
        logger.info(f"礼品卡发行: {gift_info}")

        assert business_user == user_account

        busi_amount, plat_amount, sponsor_amount, invite_amount, order_amount = calPlatAmount(act_info, group_info, order_info)
        amount = busi_amount + 1
        logger.info(f"商家最大可以分得: {busi_amount}, 分账数量: {amount}, 是否成功: {busi_amount >= amount}")
        res, action = self.withdraw(act_id, group_id, amount, user_account, user_key)
        logger.info(f"交易结果: {res}")

        assert f"subscription-token overdrawn {busi_amount}" in res["error"]["details"][0]["message"]
        ro_balance2 = self.chain_client.get_currency_balance(business_user, "roxe.ro", "USD")
        logger.info(f"账户ro资产: {ro_balance2}")
        gift_balance2 = self.chain_client.get_currency_balance(business_user, gift_card_account, "USD")
        logger.info(f"账户礼品卡资产: {gift_balance2}")

        gift_info2 = self.chain_client.get_table(gift_card_account, gift_symbol, "stat")
        logger.info(f"礼品卡发行: {gift_info2}")

        group_info2 = self.chain_client.get_table(group, group_id, "groupinfo")
        logger.info(group_info2)

        act_info2 = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"活动详情: {act_info2}")
        order_info2 = self.chain_client.get_table(group, order_id, "orderinfo")

        GiftCard.checkBalanceChange(ro_balance, ro_balance2, 0)
        GiftCard.checkBalanceChange(gift_balance, gift_balance2, 0, "持有的礼品卡数量")
        assert order_info2["rows"][0]["_REBATED_"] == 1, f"订单返利状态信息不正确: {order_info2}"
        GiftCard.checkBalanceChange(group_info["rows"][0]["_PLATFORMAMOUNT_"], group_info2["rows"][0]["_PLATFORMAMOUNT_"], 0, "平台分账的数量在group的记录")
        GiftCard.checkBalanceChange(act_info["rows"][0]["_ACTIVITY_STORE_"]["_GIFT_TOKEN_FREEZED_AMOUNT_"], act_info2["rows"][0]["_ACTIVITY_STORE_"]["_GIFT_TOKEN_FREEZED_AMOUNT_"], 0, "礼品卡发行量在activity中的记录")

    def test_business_performance_amount(self, act_id, amount):

        act_info = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"活动详情: {act_info}")

        business_user = act_info["rows"][0]["_ACTIVITY_STORE_"]["_SERVER_PROVIDER_"]
        ro_balance = self.chain_client.get_currency_balance(business_user, "roxe.ro", "USD")
        logger.info(f"账户ro资产: {ro_balance}")
        gift_balance = self.chain_client.get_currency_balance(business_user, gift_card_account, gift_symbol)
        logger.info(f"账户礼品卡资产: {gift_balance}")

        gift_info = self.chain_client.get_table(gift_card_account, gift_symbol, "stat")
        logger.info(f"礼品卡发行: {gift_info}")

        assert business_user == user_account
        res, action = self.performance(act_id, amount, user_account, user_key)
        logger.info(f"交易结果: {res}")

        ro_balance2 = self.chain_client.get_currency_balance(business_user, "roxe.ro", "USD")
        logger.info(f"账户ro资产: {ro_balance2}")
        gift_balance2 = self.chain_client.get_currency_balance(business_user, gift_card_account, gift_symbol)
        logger.info(f"账户礼品卡资产: {gift_balance2}")

        gift_info2 = self.chain_client.get_table(gift_card_account, gift_symbol, "stat")
        logger.info(f"礼品卡发行: {gift_info2}")

        act_info2 = self.chain_client.get_table(group, act_id, "activityinfo")
        logger.info(f"活动详情: {act_info2}")

        GiftCard.checkBalanceChange(ro_balance, ro_balance2, 0)
        GiftCard.checkBalanceChange(gift_balance, gift_balance2, - amount / 1000000, "持有的礼品卡数量")
        GiftCard.checkBalanceChange(gift_info["rows"][0]["supply"], gift_info2["rows"][0]["supply"], - amount / 1000000, "礼品卡的销毁量")
        GiftCard.checkBalanceChange(act_info["rows"][0]["_ACTIVITY_STORE_"]["_GIFT_TOKEN_FREEZED_AMOUNT_"], act_info2["rows"][0]["_ACTIVITY_STORE_"]["_GIFT_TOKEN_FREEZED_AMOUNT_"], 0, "礼品卡发行量在activity中的记录")
        GiftCard.checkBalanceChange(act_info["rows"][0]["_ACTIVITY_STORE_"]["_GIFT_TOKEN_PERFORM_AMOUNT_"], act_info2["rows"][0]["_ACTIVITY_STORE_"]["_GIFT_TOKEN_PERFORM_AMOUNT_"], amount, "礼品卡发行量在activity中的记录")


client = GiftCard(rpc_host)

# print(client.chain_client.get_currency_balance(user_account, "roxe.ro", None))
# print(client.chain_client.get_currency_balance(user_account, "roxe.ro", "USD"))
# print(client.chain_client.get_currency_balance("agjyrafzwlng", "roxe.ro", "USD"))
# client.transfer()
# client.createGiftCardToken(user_account, "1000000.000000 JETHRO")
# client.createGiftCardToken(user_account, "1844674407370955.1616 TTA")
# print(2 ** 62)
# client.createGiftCardToken(user_account, "461168601842738.7903 TTA")
# client.issueGiftCardToken(user_account, "giftcard1111", "0.000001 JETHRO", user_key)
# client.incScore(user_account, 10)
# client.decScore(user_account, 100)
# client.incVip(user_account)

# client.test_createGiftCard_normal("10000.000000 HKD")
# client.test_createGiftCard_symbolInvalid()
# client.test_createGiftCard_symbolRepeat()
# client.test_createGiftCard_maxSupplyInvalid()

# client.test_issue_normal()
# client.test_issue_normal(memo="hello this is a test")
# client.test_issue_symbolNotExist()
# client.test_issue_symbolInvalid()
# client.test_issue_noPermission()
# client.test_issue_toAccountInvalid()
# client.test_issue_memoExceedLimit()
# client.test_issue_quantityDecimalInvalid()
# client.test_issue_quantityInvalid()
# client.test_issue_quantityExceedMaxSupply()

# client.test_issue_normal("100.000000 USD", user_account, "issue for transfer test")
# client.test_transfer_normal()
# client.test_transfer_normal("12.234567 USD")
# client.test_transfer_normal("0.000001 USD")
# client.test_transfer_symbolNotExist()
# client.test_transfer_symbolInvalid()
# client.test_transfer_toAccountInvalid()
# client.test_transfer_memoExceedLimit()
# client.test_transfer_quantityDecimalInvalid()
# client.test_transfer_quantityInvalid()
# client.test_transfer_quantityExceedBalance()

# client.test_retire_normal()
# client.test_retire_normal("1.234567 USD")
# client.test_retire_normal("0.000001 USD")
# client.test_retire_noPermission()
# client.test_retire_memoExceedLimit()
# client.test_retire_quantityDecimalInvalid()
# client.test_retire_notHaveAuthorPermission()
# client.test_retire_quantityExceedBalance()

# client.test_addAuthor(user_account2, "6,USD")
# client.test_addAuthor(user_account2, "6,JETHRO")

# client.test_retire_normal("1.000000 USD", user_account2, user_key2)

# client.test_delAuthor(user_account2, "6,USD")

# client.test_updateController(user_account, group, group_key)
# client.test_updateController(group, user_account, user_key)
# client.test_updateController(group, group, group_key)
# client.test_updateController_notExist("abc123", group, group_key)
# client.test_addBlackUser(user_account)
# client.test_addBlackUser_added(user_account)
# client.test_addBlackUser_userInvalid("abc123")

# client.test_delBlackUser(user_account)
# client.test_delBlackUser_deleted(user_account)
# client.test_delBlackUser_userInvalid("abc123")

# client.test_setCreditScore(True, 63)
# client.test_setCreditScore(False, 0)

# client.test_createActivity(10009)
# client.test_createActivity_actAlreadyExist(10001)
# client.test_createActivity_businessAccountInvalid(10001)

# client.test_initActivity(10009, int(datetime.datetime.utcnow().timestamp() * 1000 + 2 * 3600 * 1000), int(datetime.datetime.utcnow().timestamp() * 1000 + 25 * 3600 * 1000), 0)
# client.test_initActivity_alreadyInit(10001)
# client.test_initActivity_startTimeMoreThanTerminalTime(10002)
# client.test_initActivity_terminalTimeLessThanCurrentTime(10002)

# client.test_setBonusConf(10009)
# client.test_setBonusConf_ratioTooHigh(10001)

# client.test_addConductor(user_account, 10001, user_account, user_key)
# client.test_addConductor(user_account, 10001, user_account2, user_key)

# client.test_delConductor(user_account, 10001, user_account2, user_key)

# client.test_autoGroup(user_account, 10020, True, user_key)
# client.test_autoGroup(user_account, 10020, True, user_key)
# client.test_autoGroup_activityNotExist(user_account, 1000001, True, user_key)

# client.test_setFreeStart(user_account, 10001, False, user_key)
# client.test_setFreeStart(user_account, 10001, True, user_key)

# client.test_setExceed(user_account, 10001, False, user_key)
# client.test_setExceed(user_account, 10023, True, user_key)

# client.test_freezeGift(user_account, 10001, 12, user_key)

# client.test_unfreezeGift(user_account, 10001, 100, user_key)

# client.test_setOrdCancel(user_account, 10001, True, user_key)
# client.test_setOrdCancel(user_account, 10001, False, user_key)

# client.test_setRebate(user_account, 10001, True, user_key)
# client.test_setRebate(user_account, 10020, True, user_key)  # 自动返利

# client.test_setCancelOrderRatio(user_account, 10001, int(0.2 * ratio_base), user_key)


# 10008, 没有开始时间和结束时间
# 10011, 有开始时间和结束时间
# 10012, 没有开始时间和结束时间, 认购币种必须大于5
# client.test_createActivity(10024, int(5 * ratio_base), int(1 * ratio_base), int(1000000 * token_base), int(1 * token_base))
# client.test_createActivity(21, 100000000, 100000000, 1000000000000, 0)
# client.test_createActivity(10020, 100000000, 100000000, 1000000000000, 0)
# client.test_initActivity(10021, int(datetime.datetime.now().timestamp() * 1000 + 1 * 3600 * 1000), int(datetime.datetime.now().timestamp() * 1000 + 23 * 3600 * 1000), 1000000)
# client.test_initActivity(10023, 0, int(datetime.datetime.now().timestamp() * 1000 + 20 * 60 * 1000), 1000000)
# client.test_initActivity(10024, 0, 0, 0, 1000000, 500000000)
# client.test_newGroup_activityNotInit(10008, 11)
# client.test_initActivity(10020, 0, 0, 0)
# client.test_setBonusConf(21, 20000000, 0, 0, 100000000, 0, 10000000)
# client.test_setBonusConf(10020, bus_first_redeem_ratio=int(0 * ratio_base))
# client.test_setBonusConf(10020, 0, 0, 0, 0, 0, 0)
# client.test_setBonusConf(10020, int(0.05 * ratio_base), 0, int(0.03 * ratio_base), int(1 * ratio_base), int(0.3 * ratio_base), int(0.02 * ratio_base))
# client.test_setBonusConf(10023, int(0.055 * ratio_base), int(0.01 * ratio_base), int(0.033 * ratio_base), int(1 * ratio_base), int(0.3 * ratio_base), int(0.012 * ratio_base))
# client.test_setBonusConf(10024, int(0.0597 * ratio_base), int(0.0123 * ratio_base), int(0.0343 * ratio_base), int(1 * ratio_base), int(0.3 * ratio_base), int(0.0131 * ratio_base))

# client.test_newGroup_notSponsorCall(10001, 2)
# client.test_revokeGroup_justNew(10006, 9)  # 撤团
# client.test_purchase_totalAmount(10001, 2, 1

# client.allowTransfer(user_account2, user_key2, user_pub_key2, group)  # 用户授权给group
# client.allowTransfer(user_account, user_key, user_pub_key, group)  # 商户授权给group
# client.allowTransfer(gift_card_account, gift_card_key, gift_card_pub_key, group)  # 礼品卡合约授权给group

# client.test_newGroup_notSponsorCall(10022, 57, int(0.35 * ratio_base), int(10 * token_base))
# client.test_newGroup_notSponsorCall(10020, 46, int(1 * ratio_base), int(50 * token_base))
# client.test_newGroup_notSponsorCall(10012, 29, int(4 * math.pow(10, 8)), int(5 * token_base))
# client.test_newGroup_notSponsorCall(21, 1456099177345130497, 100000000, 50000000)
# client.test_newGroupAndBuy_notSponsorCall(21, 1456099177345130497, 1456099177345130497, 50000000, 100000000, 50000000)
# client.test_newGroupAndBuy_notSponsorCall(10018, 1456099177345130497, 1456099177345130497, int(50 * token_base), int(1 * ratio_base), int(50 * token_base))
# client.test_newGroupAndBuy_notSponsorCall(10024, 61, 61, int(1.23 * token_base), int(1 * ratio_base), int(1.23 * token_base))

import random
from_order = 4400
count = 0
t_num = 0
err_num = 0
while t_num < count:
    r_amount = random.randint(10000, 300000000)
    try:
        client.test_newGroupAndBuy_notSponsorCall(10024, from_order, from_order, r_amount, int(1 * ratio_base), r_amount)
    except Exception as o_e:
        logger.error(f"下单出错数量为 {r_amount}, 错误: {o_e.args[0]}", exc_info=True)
        err_num += 1
    from_order += 1
    t_num += 1
# logger.error(f"总计出错: {err_num}")
# client.test_purchase_totalAmount(10022, 56, 56, int(2 * token_base))
# client.test_purchase_totalAmount(10012, 29, 29, int(1 * token_base))
# client.test_purchase_totalAmount(10012, 28, 28, int(5 * token_base))
# client.test_purchase_totalAmount(10013, 33, 33, int(1 * token_base))
# client.test_purchase_totalAmount(10021, 50, 50, int(2 * token_base))
# client.test_purchase_totalAmount(21, 1456099177345130497, 1456099177345130497, 50000000)
# client.test_delivery(21, 1456099177345130497, 1456099177345130497)
# client.test_delivery(10015, 36, 36)
# client.test_delivery(10023, 58, 58)
# client.test_revokeGroup_justNew(10022, 56, 56)  # 撤团
# client.test_plat_collect_amountTooMuch(10022, 55)  # 平台领取数量超过应得
# client.test_plat_collect_amount(10012, 30, int(12.3456 * math.pow(10, 4)))
# client.test_plat_collect_amount(10022, 55, 20000)
# client.test_plat_collect_amount(10011, 26, 12321)
# client.test_plat_collect_amount(10008, 17, 9850)
# client.test_plat_collect_notPlatUserCall(10011, 26)  # 非平台用户领取
# client.test_order_rebate_amount(21, 1456099177345130497)
# client.test_order_rebate_amount(10023, 59)
# client.test_order_rebate_hasRebated(10021, 50)
# client.test_business_withdraw_amount(10022, 55, 1890000)  # 商家领取数量
# client.test_business_withdraw_amountTooMuch(10021, 51)

# client.test_transfer_normal("300.000000 JETHRO", user_account, user_account2, user_key2)
# client.test_business_performance_amount(10020, 14000000)  # 商家履约，销毁礼品卡

# client.test_addAuthor(group, "6,USD")
# client.test_addAuthor(group, "6,JETHRO")
# client.test_delivery(10004, 7, 6)
# client.test_delivery(10004, 7, 6)
# client.test_delivery(10001, 3, 2)
# client.test_confirmOrder(10023, 60, 60)
# client.test_confirmOrder(10001, 6, 5)
# 18446744073709551615
# print(client.chain_client.get_currency_balance(user_account, "roxe.ro", "USD"))
# print(client.chain_client.get_currency_balance(user_account2, "roxe.ro", "USD"))
# print(client.chain_client.get_currency_balance("agjyrafzwlng", "roxe.ro", "USD"))
# print(client.chain_client.get_currency_balance("z5hkbojz2tjn", "roxe.ro", USD))
# print(client.chain_client.get_currency_balance("rss_Brazil", "roxe.ro", "USD"))
# print(client.chain_client.get_currency_balance("5chnthreqiow", "roxe.ro", "USD"))
# print(client.chain_client.get_currency_balance("f3viuzqrqq4d", "roxe.ro", "USD"))
# print(client.chain_client.get_currency_balance("fape1meh4bsz", "roxe.ro", "USD"))
print(client.chain_client.get_currency_balance("ifomx232tdly", "roxe.ro", None))
print(client.chain_client.get_currency_balance("bfpz3uajhyeg", "roxe.ro", None))
# import string
# print("".join([random.choice(string.ascii_letters + string.digits) for i in range(32)]))
dodos = client.chain_client.get_table("roxe.earn", "roxe.earn", "dodos")
# print(dodos)
dodoInfo = [i for i in dodos["rows"] if i["dodo"] == "re.usdphp"][0]
tx2 = client.chain_client.get_table("roxe.earn", "roxe.earn", "oracleprices")
priceInfo = [i for i in tx2["rows"] if i["basetoken"] == dodoInfo["dodos"]["_BASE_TOKEN_"] and i["quotetoken"]["quantity"].endswith(" PHP")][0]
price = int(float(priceInfo["quotetoken"]["quantity"].split(" ")[0]) * 1000000)
# print(json.dumps(dodoInfo))
# print("base", float(dodoInfo["dodos"]["_BASE_BALANCE_"]) / 1000000)
# print("quote", float(dodoInfo["dodos"]["_QUOTE_BALANCE_"]) / 1000000)
# print(price)

# price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)

# from SmartContract.DODO.EOS_DODO import queryBuyBaseToken, querySellBaseToken
# buyAmount = 100000
# spentQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = querySellBaseToken(int(102.34 * 10**6), dodoInfo, "re.usdgbpnew", price)
# print(spentQuote)
# print(client.chain_client.get_currency_balance("crxaptw4rqcf", "roxe.rg", "null"))
# transferRoUSD(user_account2, 1000)
# client.transferToken(user_account, user_key, user_account2, "1.000000 USD", "roxe.ro")
