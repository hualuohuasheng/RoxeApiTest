# coding=utf-8
# author: Li MingLei
# date: 2021-09-26
"""
RoxeSend系统【RoxeApp的后台服务】Api的测试用例
"""
import unittest
import json
import os
import datetime
import time
from .RoxeSendApi import RoxeSendApiClient
from .RoxeCommerceAPI import CommerceApiClient
from RTS.RtsApiTest import RTSApiClient, RTSData
from RSS.RssApiTest import RSSData
from RPS.RpsApiTest import RPSData, RpsApiClient
from RoxeKyc.RoxeKycApiTest import RoxeKycApiClient, RoxeKycData
from roxe_libs import settings, ApiUtils
from roxe_libs.Global import Global
from roxe_libs.DBClient import RedisClient, Mysql
from roxe_libs.pub_function import loadYmlFile
from enum import Enum


class RoxeSendEnum(Enum):

    ENSURE_SIDE_INNER = "INNER"
    ENSURE_SIDE_OUTER = "OUTER"
    BUSINESS_TYPE_SENDTOROXEACCOUNT = "SendToRoxeAccount"
    BUSINESS_TYPE_REQUEST = "Request"
    BUSINESS_TYPE_DEPOSIT = "Deposit"
    BUSINESS_TYPE_WITHDRAW = "Withdraw"
    SCOP_PRIVATE = "private"
    SCOP_PUBLIC = "public"


class RoxeSendData:

    env = Global.getValue(settings.environment)
    cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), f"./RoxeSend_{env}.yml"))
    _yaml_conf = loadYmlFile(cfg_path)
    host = _yaml_conf["host"]
    chain_host = _yaml_conf["chain_host"]
    commerce_host = _yaml_conf["commerce_host"]
    commerce_token = _yaml_conf["commerce_token"]
    # 通过km的用户
    user_id = _yaml_conf["user_id"]
    user_account = _yaml_conf["user_account"]
    user_login_token = _yaml_conf["user_login_token"]

    # 通过ka的用户
    user_id_b = _yaml_conf["user_id_b"]
    user_account_b = _yaml_conf["user_account_b"]
    user_login_token_b = _yaml_conf["user_login_token_b"]

    # 没有通过kyc的用户
    user_id_c = _yaml_conf["user_id_c"]
    user_account_c = _yaml_conf["user_account_c"]
    user_login_token_c = _yaml_conf["user_login_token_c"]

    currency = _yaml_conf["currency"]

    kyc_limit_level1 = _yaml_conf["L1Limit"]
    kyc_limit_level2 = _yaml_conf["L2Limit"]
    kyc_limit_level3 = _yaml_conf["L3Limit"]

    user_outer_bank = _yaml_conf["user_outer_bank"]  # 校验出金字段
    user_outer_bank_1 = _yaml_conf["user_outer_bank_1"]  # 绑卡
    user_outer_bank_2 = _yaml_conf["user_outer_bank_2"]  # 绑卡

    is_check_db = _yaml_conf["is_check_db"]
    sql_cfg = _yaml_conf["sql_cfg"]
    redis_cfg = _yaml_conf["redis_cfg"]


class RoxeSendApiTest(unittest.TestCase):

    mysql = None
    redis = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = RoxeSendApiClient(RoxeSendData.host, RoxeSendData.chain_host, RoxeSendData.user_id, RoxeSendData.user_login_token)
        # cls.rts_client = RtsApiClient(RtsData.host, RtsData.sign_key, RtsData.sec_key)
        # cls.rps_client = RpsApiClient(RPSData.host, RPSData.chain_host, RPSData.app_key, RPSData.sign, RoxeSendData.user_id, RoxeSendData.user_login_token)
        cls.kyc_client = RoxeKycApiClient(RoxeKycData.host, RoxeKycData.user_id, RoxeKycData.user_login_token)
        cls.commerce_client = CommerceApiClient(RoxeSendData.commerce_host, RoxeSendData.commerce_token)
        if RoxeSendData.is_check_db:
            cls.mysql = Mysql(RoxeSendData.sql_cfg["mysql_host"], RoxeSendData.sql_cfg["port"], RoxeSendData.sql_cfg["user"], RoxeSendData.sql_cfg["password"], RoxeSendData.sql_cfg["db"], True)
            cls.mysql.connect_database()

            cls.redis = RedisClient(RoxeSendData.redis_cfg["host"], RoxeSendData.redis_cfg["password"], RoxeSendData.redis_cfg["db"], RoxeSendData.redis_cfg["port"])

    @classmethod
    def tearDownClass(cls) -> None:
        if RoxeSendData.is_check_db:
            cls.mysql.disconnect_database()
            cls.redis.closeClient()

    def checkCodeMessage(self, api_result, code="0", message="Success"):
        self.assertEqual(api_result["code"], code, "code检查不正确")
        self.assertEqual(api_result["message"], message, "message检查不正确")

    def checkExchangeRate(self, rate_info, request_params):

        self.assertEqual(rate_info["sendCurrency"], request_params["from"])
        self.assertEqual(rate_info["receiveCurrency"], request_params["to"])
        from_currency = request_params["from"]
        to_currency = request_params["to"]
        if request_params["type"] != RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value:
            # 非提现业务，查询路由时实际为法币->RO
            to_currency = request_params["to"] + ".ROXE"
        else:
            # 提现业务，查询路由时实际为RO->法币
            from_currency = request_params["to"] + ".ROXE"

        if request_params["type"] in [RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value]:
            # sendToRoxeAccount, withdraw都是保的左边
            self.assertEqual(rate_info["ensureSide"], request_params["ensureSide"])
        else:
            # request, deposit都是保的右边
            self.assertEqual(rate_info["ensureSide"], RoxeSendEnum.ENSURE_SIDE_OUTER.value)

        rts_router = self.rts_client.queryRouterList(request_params["fromCountry"], from_currency, request_params["toCountry"], to_currency, request_params["fromAmount"], request_params["toAmount"], "", request_params["outerNodeRoxe"]).json()

        # if request_params["type"] == RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value:
        #     self.assertEqual(rate_info["outerNodeCode"], rts_router["data"][0]["outerNodeCode"])
        # else:
        #     self.assertEqual(rate_info["outerNodeCode"], None)
        self.assertEqual(rate_info["outerNodeCode"], rts_router["data"][0]["outerNodeCode"])
        self.assertEqual(rate_info["sendAmount"], rts_router["data"][0]["innerQuantity"])
        self.assertEqual(rate_info["receiveAmount"], rts_router["data"][0]["outerQuantity"])
        self.assertEqual(rate_info["serviceFee"], rts_router["data"][0]["serviceFee"])
        self.assertEqual(rate_info["serviceFeeCurrency"], request_params["from"])
        e_delivery_fee = rts_router["data"][0]["deliveryFee"] if rts_router["data"][0]["deliveryFee"] else "0"
        self.assertEqual(rate_info["deliveryFee"], e_delivery_fee)
        self.assertEqual(rate_info["deliveryFeeCurrency"], request_params["from"])
        self.assertEqual(rate_info["routerId"], rts_router["data"][0]["routerId"])
        self.assertEqual(rate_info["innerAccount"], rts_router["data"][0]["innerAccount"])
        self.assertEqual(rate_info["innerNodeCode"], rts_router["data"][0]["innerNodeCode"])

    def checkBindReceiverAccount(self, bind_info, request_body, user_id):
        self.assertEqual(bind_info["accountType"], request_body["type"])
        self.assertEqual(bind_info["currency"], request_body["currency"])
        self.assertEqual(bind_info["country"], request_body["bankAccount"]["countryCode"])
        self.assertIsNotNone(bind_info["accountId"])
        self.assertIsNotNone(bind_info["createdAt"])
        self.assertEqual(bind_info["accountDetail"]["receiverFirstName"], request_body["bankAccount"]["name"])
        self.assertEqual(bind_info["accountDetail"]["recipientCountry"], request_body["bankAccount"]["countryCode"])
        self.assertEqual(bind_info["accountDetail"]["payOutMethod"], "BANK")
        accountType = "individual" if "accountType" not in request_body["bankAccount"] else request_body["bankAccount"]["accountType"]
        self.assertEqual(bind_info["accountDetail"]["accountType"], accountType)
        self.assertEqual(bind_info["accountDetail"]["mask"], str(request_body["bankAccount"]["accountNumber"])[-4:])  # 银行卡后4位
        self.assertEqual(bind_info["accountDetail"]["accountNumber"], str(request_body["bankAccount"]["accountNumber"]))
        self.assertEqual(bind_info["accountDetail"]["routingNumber"], str(request_body["bankAccount"]["routingNumber"]))
        if RoxeSendData.is_check_db:
            sql = f"select * from ro_receive_account where user_id='{user_id}' and is_delete=0"
            accounts_db = self.mysql.exec_sql_query(sql)
            bind_db = [i for i in accounts_db if i["accountId"] == bind_info["accountId"]]
            self.assertEqual(len(bind_db), 1, f"{bind_info['accountId']}在数据库应查询不到账户: {accounts_db}")
            s_keys = ["country", "currency", "accountId", "accountType", "outerNodeCode"]
            for s_k in s_keys:
                self.assertEqual(bind_info[s_k], bind_db[0][s_k])

    def checkListReceiverAccount(self, list_info, user_id):
        if RoxeSendData.is_check_db:
            sql = f"select * from ro_receive_account where user_id='{user_id}' and is_delete=0"
            accounts_db = self.mysql.exec_sql_query(sql)
            self.assertEqual(len(accounts_db), len(accounts_db), f"在数据库查询结果条数和结果对不上: {accounts_db}")
            s_keys = ["country", "currency", "accountId", "accountType", "outerNodeCode"]
            for bind_info in list_info:
                bind_db = [i for i in accounts_db if i["accountId"] == bind_info["accountId"]]
                for s_k in s_keys:
                    self.assertEqual(bind_info[s_k], bind_db[0][s_k])

    def checkAccountBalance(self, balance_info, user_id):
        if RoxeSendData.is_check_db:
            account_sql = f"select address from ro_user_account where user_id='{user_id}'"
            user_account = self.mysql.exec_sql_query(account_sql)[0]["address"]
            chain_balance = self.client.chain_client.getBalance(user_account)
            self.client.logger.info(f"账户{user_account}资产: {chain_balance }")
            balance_info = balance_info if isinstance(balance_info, list) else [balance_info]
            for u_balance in balance_info:
                r_balance = [i for i in chain_balance if i.endswith(" " + u_balance["currency"])]
                self.assertAlmostEqual(u_balance["amount"], float(r_balance[0].split(" ")[0]), delta=0.1 ** 6)

    def checkDepositOrderInfo(self, order_info, request_body, user_id):
        self.assertIsNotNone(order_info["transactionId"])
        self.assertIsNotNone(order_info["orderId"])
        self.assertIsNotNone(order_info["rpsId"])
        self.assertEqual(order_info["userId"], user_id)
        self.assertEqual(order_info["counterpartyUserId"], user_id)
        self.assertEqual(order_info["type"], "Deposit")
        self.assertEqual(order_info["direction"], "Income")
        self.assertEqual(order_info["amount"], request_body["amount"])
        self.assertEqual(order_info["currency"], request_body["currency"])
        self.assertEqual(order_info["status"], "Submitted")
        self.assertIsNotNone(order_info["createdAt"])
        for k in ["practicalAmount", "note", "requestCurrency", "requestAmount"]:
            self.assertIsNone(order_info[k], f"{k}检查不为None")
        self.checkTransactionFromDB(order_info, order_info["transactionId"])
        self.checkOrderInfoFromDB(order_info, order_info["orderId"], request_body)

    def checkSenToRoAccountOrderInfo(self, order_info, request_body, user_id, to_user_id):
        self.assertIsNotNone(order_info["transactionId"])
        self.assertIsNotNone(order_info["orderId"])
        self.assertIsNotNone(order_info["rpsId"])
        self.assertEqual(order_info["userId"], user_id)
        self.assertEqual(order_info["counterpartyUserId"], to_user_id)
        self.assertEqual(order_info["type"], "SendToRoxeAccount")
        self.assertEqual(order_info["direction"], "Expenditure")
        self.assertEqual(order_info["amount"], request_body["sendAmount"])
        self.assertEqual(order_info["currency"], request_body["sendCurrency"])
        self.assertEqual(order_info["status"], "Submitted")
        self.assertEqual(order_info["note"], request_body["note"])
        self.assertEqual(order_info["practicalAmount"], float(request_body["receiveAmount"]))
        self.assertIsNotNone(order_info["createdAt"])
        for k in ["requestCurrency", "requestAmount"]:
            self.assertIsNone(order_info[k], f"{k}检查不为None")
        self.checkTransactionFromDB(order_info, order_info["transactionId"])
        self.checkOrderInfoFromDB(order_info, order_info["orderId"], request_body)

    def checkPayRequestOrderInfo(self, order_info, request_body, user_id, to_user_id):
        self.assertIsNotNone(order_info["transactionId"])
        self.assertIsNotNone(order_info["orderId"])
        self.assertEqual(order_info["userId"], user_id)
        self.assertEqual(order_info["counterpartyUserId"], to_user_id)
        self.assertEqual(order_info["type"], "Request")
        self.assertEqual(order_info["direction"], "Expenditure")
        self.assertEqual(str(order_info["amount"]), request_body["sendAmount"])
        self.assertEqual(order_info["currency"], request_body["sendCurrency"])
        self.assertEqual(order_info["status"], "Temporary")
        self.assertEqual(order_info["note"], request_body["note"])
        self.assertIsNotNone(order_info["createdAt"])
        for k in ["requestCurrency", "requestAmount", "practicalAmount"]:
            self.assertIsNone(order_info[k], f"{k}检查不为None")
        self.checkTransactionFromDB(order_info, order_info["transactionId"])

    def checkRequestOrderInfo(self, order_info, request_body, user_id, to_user_id):
        self.assertIsNotNone(order_info["transactionId"])
        self.assertIsNotNone(order_info["orderId"])
        self.assertEqual(order_info["userId"], user_id)
        self.assertEqual(order_info["counterpartyUserId"], to_user_id)
        self.assertEqual(order_info["type"], "Request")
        self.assertEqual(order_info["direction"], "Income")
        self.assertEqual(order_info["amount"], request_body["receiveAmount"])
        self.assertEqual(order_info["currency"], request_body["receiveCurrency"])
        self.assertEqual(order_info["status"], "Temporary")
        self.assertEqual(order_info["note"], request_body["note"])
        self.assertIsNotNone(order_info["createdAt"])
        for k in ["requestCurrency", "requestAmount", "rpsId", "practicalAmount"]:
            self.assertIsNone(order_info[k], f"{k}检查不为None")
        self.checkTransactionFromDB(order_info, order_info["transactionId"])

    def checkTransactionFromDB(self, tx_info, tx_id):
        self.assertEqual(tx_info["transactionId"], tx_id)
        if RoxeSendData.is_check_db:
            tx_sql = f"select * from ro_transaction_history where id='{tx_id}'"
            tx_db = self.mysql.exec_sql_query(tx_sql)
            self.assertEqual(tx_db[0]["orderId"], tx_info["orderId"])
            self.assertEqual(tx_db[0]["userId"], tx_info["userId"])
            self.assertEqual(tx_db[0]["counterpartyId"], tx_info["counterpartyUserId"])
            self.assertEqual(tx_db[0]["direction"], tx_info["direction"])
            self.assertEqual(tx_db[0]["status"], tx_info["status"])
            self.assertEqual(tx_db[0]["note"], tx_info["note"])
            if tx_info["practicalAmount"]:
                self.assertEqual(float(tx_db[0]["practicalAmount"]), tx_info["practicalAmount"])
            else:
                self.assertEqual(None, tx_info["practicalAmount"])
            if tx_info["status"] == "Temporary":
                self.assertEqual(None, tx_info["requestCurrency"])
                self.assertEqual(None, tx_info["requestAmount"])
            else:
                self.assertEqual(tx_db[0]["requestCurrency"], tx_info["requestCurrency"])
                self.assertEqual(tx_db[0]["requestAmount"], tx_info["requestAmount"])

    def checkOrderInfoFromDB(self, order_info, order_id, request_body):
        if RoxeSendData.is_check_db:
            order_sql = f"select * from ro_order where order_id='{order_id}'"
            order_db = self.mysql.exec_sql_query(order_sql)

            self.assertEqual(order_db[0]["orderId"], order_info["orderId"])
            self.assertAlmostEqual(float(order_db[0]["sendAmount"]), order_info["amount"], delta=0.001)
            e_k = "sendCountry" if "sendCountry" in request_body else "country"
            self.assertEqual(order_db[0]["sendCountry"], request_body[e_k])
            e_k = "receiveCountry" if "receiveCountry" in request_body else "country"
            self.assertEqual(order_db[0]["receiveCountry"], request_body[e_k])
            e_k = "receiveCurrency" if "receiveCurrency" in request_body else "currency"
            self.assertEqual(order_db[0]["receiveCurrency"], request_body[e_k])
            e_k = "sendCurrency" if "sendCurrency" in request_body else "currency"
            self.assertEqual(order_db[0]["sendCurrency"], request_body[e_k])
            self.assertEqual(order_db[0]["status"], order_info["status"])
            self.assertEqual(order_db[0]["type"], order_info["type"])

    def checkCounterpartyFromDB(self, counterparty, user_id):
        user_sql = "select * from roxe_user_center_cloud.user_info where user_id='{}'".format(user_id)
        user_db = self.mysql.exec_sql_query(user_sql)
        self.assertEqual(counterparty["roxeId"], user_db[0]["userRoxeId"])
        parse_user_expand = json.loads(user_db[0]["userExpand"])
        self.assertEqual(counterparty["firstName"], parse_user_expand["firstName"])
        self.assertEqual(counterparty["lastName"], parse_user_expand["lastName"])
        e_img = parse_user_expand["headImage"] if "headImage" in parse_user_expand else None
        self.assertEqual(counterparty["headImage"], e_img)
        self.assertEqual(counterparty["nickName"], user_db[0]["userName"])

    def checkTransactionDetail(self, tx_detail, tx_id, user_id, out_account=None, to_user_id=None):
        self.assertEqual(tx_detail["transactionId"], tx_id)
        if RoxeSendData.is_check_db:
            tx_sql = f"select * from ro_transaction_history where id='{tx_id}'"
            tx_db = self.mysql.exec_sql_query(tx_sql)
            self.assertEqual(tx_db[0]["currency"], tx_detail["currency"])
            self.assertAlmostEqual(float(tx_db[0]["amount"]), tx_detail["amount"], delta=0.001)
            self.assertEqual(tx_db[0]["status"], tx_detail["status"])
            self.assertEqual(tx_db[0]["direction"], tx_detail["direction"])
            self.assertEqual(tx_db[0]["type"], tx_detail["type"])
            self.assertEqual(tx_db[0]["note"], tx_detail["note"])
            if tx_detail["practicalAmount"]:
                self.assertEqual(float(tx_db[0]["practicalAmount"]), tx_detail["practicalAmount"])
            else:
                self.assertEqual(tx_db[0]["practicalAmount"], tx_detail["practicalAmount"])
            self.assertEqual(tx_db[0]["orderId"], tx_detail["orderId"])

            if tx_detail["type"] == "Withdraw":
                for out_k, out_v in tx_detail["counterparty"].items():
                    self.assertEqual(out_v, out_account[out_k], f"{out_k}校验失败")
            else:
                to_user_id = to_user_id if to_user_id else user_id
                self.checkCounterpartyFromDB(tx_detail["counterparty"], to_user_id)

            order_sql = "select * from ro_order where order_id='{}'".format(tx_detail["orderId"])
            order_db = self.mysql.exec_sql_query(order_sql)
            r_key = {"channelfee": "channelFee", "paymentMethodType": "payType"}
            if tx_detail["orderSummary"]:
                # 刚发起的request没有订单详情
                for o_key, o_value in tx_detail["orderSummary"].items():
                    if o_key in ["createdAt", "updatedAt"]:
                        time_dif = 0 if "UTC" in time.tzname else 8 * 3600 * 1000
                        expect_time = int(order_db[0][o_key].timestamp() * 1000) + time_dif if order_db[0][o_key] else None
                        self.assertEqual(o_value, expect_time)
                    elif o_key in ["sendAmount", "receiveAmount", "exchangeRate", "serviceFee", "deliveryFee"]:
                        self.assertAlmostEqual(float(order_db[0][o_key]), o_value, msg=f"{o_key}校验失败", delta=0.001)
                    elif o_key in ["paymentMethod", "bank"]:
                        self.assertIsNone(o_value)
                    else:
                        db_key = r_key[o_key] if o_key in r_key else o_key
                        if tx_detail["status"] in ["Processing", "Complete"] and o_key == "channelfee":
                            self.assertAlmostEqual(o_value, float(order_db[0][db_key]), delta=0.1**6)
                        elif o_key == "paymentMethodType":
                            if tx_detail["status"] in ["Processing", "Complete"] or tx_detail["type"] == "Withdraw":
                                self.assertEqual(o_value, order_db[0][db_key].title(), f"{o_key}校验不正确")
                            else:
                                if o_value:
                                    self.assertEqual(o_value, order_db[0][db_key].title(), f"{o_key}校验不正确")
                                else:
                                    self.assertEqual(o_value, order_db[0][db_key], f"{o_key}校验不正确")
                        else:
                            self.assertEqual(o_value, order_db[0][db_key], f"{o_key}校验不正确")

    def checkTransactionHistory(self, tx_history, re_body, user_id):
        if RoxeSendData.is_check_db:
            sql = f"select * from roxe_send_app.ro_transaction_history as a left join roxe_user_center_cloud.user_info as b on a.counterparty_id=b.user_id where a.user_id='{user_id}' order by created_at desc"
            db_res = self.mysql.exec_sql_query(sql)
            if re_body["keyword"]:
                tmp_db = []
                for i in db_res:
                    if i["note"] and re_body["keyword"] in i["note"]:
                        tmp_db.append(i)
                        continue
                    if i["userExpand"]:
                        user_expand = json.loads(i["userExpand"])
                        if re_body["keyword"] in user_expand["firstName"] or re_body["keyword"] in user_expand["lastName"]:
                            tmp_db.append(i)
                db_res = tmp_db
            if re_body["begin"]:
                tmp_db = []
                for i in db_res:
                    db_time = i["createdAt"].timestamp() * 1000
                    if db_time >= re_body["begin"]:
                        if re_body["end"]:
                            if db_time <= re_body["end"]:
                                tmp_db.append(i)
                        else:
                            tmp_db.append(i)
                db_res = tmp_db
            if re_body["currency"]:
                tmp_db = [i for i in db_res if i["currency"] == re_body["currency"]]
                db_res = tmp_db
            # if re_body["pageSize"]:
            #     self.assertEqual(tx_history["pageSize"], re_body["pageSize"])
            if tx_history["totalCount"] > tx_history["pageSize"]:
                self.assertTrue(tx_history["totalCount"] <= tx_history["pageNumber"] * tx_history["pageSize"] * tx_history["totalPage"])
            else:
                self.assertEqual(tx_history["totalCount"], len(db_res), "数据库查询出的记录条数和接口返回不一致")

            if re_body["type"]:
                uni_tx_type = set([i["type"] for i in tx_history["data"]])
                self.assertEqual(uni_tx_type, {re_body["type"]}, "交易类型不正确")

            for tx in tx_history["data"]:
                if re_body["begin"]:
                    self.assertTrue(tx["createdAt"] >= re_body["begin"], "筛选出的交易的时间戳不正确")
                if re_body["end"]:
                    self.assertTrue(tx["createdAt"] <= re_body["end"], "筛选出的交易的时间戳不正确")

                tx_db = [i for i in db_res if i["id"] == tx["transactionId"]]
                self.assertEqual(len(tx_db), 1, f"{tx['transactionId']} 交易未在数据库中找到")
                self.assertEqual(tx["transactionId"], tx_db[0]["id"])
                s_keys = ["type", "direction", "currency", "status", "note", "requestCurrency", "requestAmount"]
                for s_k in s_keys:
                    self.assertEqual(tx[s_k], tx_db[0][s_k], f"{s_k}校验失败")
                if tx["type"] == "Withdraw":
                    for out_k, out_v in tx["counterparty"].items():
                        self.assertIsNotNone(out_v, f"{out_k}应不为空")
                elif tx['type'] in ['Cashback', 'GiftCardPurchase']:
                    card_db = self.mysql.exec_sql_query("select * from roxe_gift.gift_card_order a left join roxe_commerce.merchant_info b on a.merchant_id = b.id where send_order_id='{}'".format(tx["orderID"]))
                    self.assertEqual(tx["counterparty"]["id"], card_db[0]["merchantId"])
                    self.assertEqual(tx["counterparty"]["merchantName"], card_db[0]["merchantName"])
                    self.assertEqual(tx["counterparty"]["logo"], card_db[0]["logo"])
                    self.assertEqual(tx["counterparty"]["state"], card_db[0]["state"])
                    self.assertEqual(tx["giftCardCurrency"], card_db[0]["receiveCurrency"])
                else:
                    self.checkCounterpartyFromDB(tx["counterparty"], tx_db[0]['counterpartyId'])
                for f_key in ["requestAmount", "practicalAmount"]:
                    ex_pAmount = float(tx_db[0][f_key]) if tx[f_key] else tx_db[0][f_key]
                    self.assertEqual(tx[f_key], ex_pAmount, f"{f_key}校验失败")
                order_sql = "select * from ro_order where order_id='{}'".format(tx["orderID"])
                order_db = self.mysql.exec_sql_query(order_sql)
                exp_order_num = 1
                if len(tx["orderID"]) == 32:
                    exp_order_num = 0
                self.assertEqual(len(order_db), exp_order_num, f"数据库订单数据不一致: {order_db}, {tx}")
                if order_db:
                    if order_db[0]["payType"]:
                        exp_pay_type = order_db[0]["payType"].title()
                    else:
                        exp_pay_type = order_db[0]["payType"]
                    self.assertEqual(exp_pay_type, tx["paymentMethodType"], f"出错订单: {tx['orderID']}, {order_db[0]}")
                    self.assertEqual(order_db[0]["receiveCurrency"], tx["receiveCurrency"])
                    self.assertEqual(None, tx["requestCurrency"])
                    self.assertEqual(tx["amount"], float(tx_db[0]["amount"]))
                    for f_key in ["receiveAmount"]:
                        ex_pAmount = float(order_db[0][f_key]) if tx[f_key] else order_db[0][f_key]
                        self.assertEqual(tx[f_key], ex_pAmount, f"{f_key}校验失败")

    def checkRecentContact(self, recent_info, user_id):
        if RoxeSendData.is_check_db:
            sql = f"select * from roxe_send_app.ro_transaction_history as a left join roxe_user_center_cloud.user_info as b on a.counterparty_id=b.user_id where a.user_id='{user_id}' order by created_at desc"
            db_res = self.mysql.exec_sql_query(sql)
            recent_db = {}
            for i in db_res:
                if i["counterpartyId"] in recent_db:
                    continue
                elif i["counterpartyId"] != i["userId"] and len(i["counterpartyId"]) == len(i["userId"]):
                    recent_db[i["counterpartyId"]] = i
            r_times = []
            for r_info in recent_info:
                r_db = [i for i in recent_db.values() if i["counterpartyId"] == r_info["userId"]]
                self.assertEqual(len(r_db), 1, f"数据库找到的数据不正确: {r_db}")
                self.assertEqual(r_info["roxeId"], r_db[0]["userRoxeId"])
                parse_user_expand = json.loads(r_db[0]["userExpand"])
                self.assertEqual(r_info["firstName"], parse_user_expand["firstName"])
                self.assertEqual(r_info["lastName"], parse_user_expand["lastName"])
                e_img = parse_user_expand["headImage"] if "headImage" in parse_user_expand else None
                self.assertEqual(r_info["headImage"], e_img)
                self.assertEqual(r_info["nickName"], r_db[0]["userName"])
                self.assertEqual(r_info["country"], None)
                self.assertEqual(r_info["area"], None)
                r_times.append(r_info["time"])
            self.assertTrue(len(recent_info) <= len(recent_db))
            self.assertEqual(r_times, sorted(r_times, reverse=True), "时间戳应倒叙排列")
            return len(recent_db)

    def checkNotifications(self, notifications, user_id):
        if RoxeSendData.is_check_db:
            sql = f"select * from roxe_send_app.ro_notification where user_id='{user_id}'"
            db_res = self.mysql.exec_sql_query(sql)
            self.assertEqual(len(db_res), len(notifications))
            for i in notifications:
                n_db = None
                for d in db_res:
                    body_db = json.loads(d["body"])
                    if body_db["transactionId"] == i["body"]["transactionId"] and body_db["type"] == i["body"]["type"]:
                        n_db = d
                self.assertEqual(i["protocol"], n_db["protocol"])
                body_db = json.loads(n_db["body"])
                for n_k, n_v in i["body"].items():
                    self.assertEqual(n_v, body_db[n_k], f"{n_k}校验失败:\n{i}\n{n_db}")

    def checkOrderShareList(self, share_list, user_id, share_params):
        if RoxeSendData.is_check_db:
            sql = f"select * from roxe_middle_service.ro_order_share where status='Completed' order by update_time desc"
            share_db = self.mysql.exec_sql_query(sql)

            if share_params["userID"]:
                tmp_db = []
                for i in share_db:
                    if i["rivalUserId"] == share_params["userID"]:
                        tmp_db.append(i)
                    if i["sendUserId"] == share_params["userID"]:
                        tmp_db.append(i)
                share_db = tmp_db

            if share_params["scope"] > 0:
                tmp_db = [i for i in share_db if i["scope"] == share_params["scope"]]
                share_db = tmp_db

            if share_params["type"] == 3:
                tmp_db = [i for i in share_db if i["sendUserId"] == user_id or i["rivalUserId"] == user_id]
                share_db = tmp_db
            elif share_params["type"] == 2:
                tmp_db = [i for i in share_db if i["rivalUserId"] == user_id]
                share_db = tmp_db

            if share_list["totalCount"] <= share_list["pageSize"]:
                self.assertEqual(len(share_list["data"]), len(share_db), share_db)
            else:
                self.assertTrue(len(share_db) >= len(share_list))
            for o_share in share_list["data"]:
                o_db = [i for i in share_db if o_share["orderId"] == i["orderId"]]
                self.assertEqual(o_share["node"], o_db[0]["note"], f"订单{o_share['orderId']}在数据库中的数据: {o_db}")
                expect_currency, expect_amount = None, None
                if user_id == o_db[0]["sendUserId"]:
                    expect_currency = o_db[0]["sendCurrency"]
                    expect_amount = -float(o_db[0]["sendAmount"])
                elif user_id == o_db[0]["rivalUserId"]:
                    expect_currency = o_db[0]["receiveCurrency"]
                    expect_amount = float(o_db[0]["receiveAmount"])
                self.assertEqual(o_share["currency"], expect_currency)
                self.assertEqual(o_share["amount"], expect_amount)
                self.checkOrderShareUserInfoFromDB(o_share["sendUserInfo"], o_db[0]["sendUserId"])
                if o_share["revalUserInfo"]:
                    self.checkOrderShareUserInfoFromDB(o_share["revalUserInfo"], o_db[0]["rivalUserId"])
                else:
                    gift_sql = "select * from roxe_gift.gift_card_order a left join roxe_commerce.merchant_info b on a.merchant_id = b.id where a.send_order_id='{}'".format(o_share["orderId"])
                    gift_db = self.mysql.exec_sql_query(gift_sql)
                    self.assertEqual(o_share["merchantInfo"]["id"], gift_db[0]["merchantId"])
                    self.assertEqual(o_share["merchantInfo"]["merchantName"], gift_db[0]["merchantName"])
                    self.assertEqual(o_share["merchantInfo"]["logo"], gift_db[0]["logo"])
                    self.assertEqual(o_share["merchantInfo"]["state"], gift_db[0]["state"])
                self.assertEqual(o_share["praiseCount"], o_db[0]["praiseCount"])
                # e_parse = True if o_share["praiseCount"] > 0 else False
                # self.assertEqual(o_share["praise"], e_parse)
                self.assertEqual(o_share["commentCoune"], o_db[0]["commentCount"])
                # e_comment = True if o_share["commentCoune"] > 0 else False
                # self.assertEqual(o_share["comment"], e_comment)
                self.assertEqual(o_share["scope"], o_db[0]["scope"])

    def checkOrderShareUserInfoFromDB(self, user_info, user_id):
        user_sql = "select * from roxe_user_center_cloud.user_info where user_id='{}'".format(user_id)
        user_db = self.mysql.exec_sql_query(user_sql)
        self.assertEqual(user_info["userId"], str(user_db[0]["userId"]))
        self.assertEqual(user_info["roxeId"], user_db[0]["userRoxeId"])
        parse_user_expand = json.loads(user_db[0]["userExpand"])
        self.assertEqual(user_info["firstName"], parse_user_expand["firstName"])
        self.assertEqual(user_info["lastName"], parse_user_expand["lastName"])
        e_img = parse_user_expand["headImage"] if "headImage" in parse_user_expand else None
        self.assertEqual(user_info["headImage"], e_img)
        self.assertEqual(user_info["nickName"], user_db[0]["userName"])
        e_country = user_db[0]["country"] if "country" in user_db[0] else None
        e_area = user_db[0]["area"] if "area" in user_db[0] else None
        self.assertEqual(user_info["country"], e_country)
        self.assertEqual(user_info["area"], e_area)

    def updateOrderExpireTimeInDB(self, order_id, expire_min=2):
        if RoxeSendData.is_check_db:
            q_sql = f"select expired_at from ro_order where order_id='{order_id}'"
            expire_at = self.mysql.exec_sql_query(q_sql)[0]["expiredAt"]
            u_expire_at = expire_at + datetime.timedelta(minutes=expire_min)
            self.client.logger.info(f"订单过期时间: {expire_at}, 修改为: {u_expire_at}")
            u_sql = f"update ro_order set expired_at='{u_expire_at}' where order_id='{order_id}'"
            self.mysql.exec_sql_query(u_sql)
            time.sleep(expire_min * 60)

    def waitOrderStatusInDB(self, order_id, status="Completed", time_out=300):
        b_time = time.time()
        sql = f"select * from ro_order where order_id='{order_id}'"
        time_out_flag = True
        while time.time() - b_time < time_out:
            db_res = self.mysql.exec_sql_query(sql)
            if db_res and db_res[0]["status"] == status:
                time_out_flag = False
                self.client.logger.info(f"订单{order_id}状态为: {status}")
                break
            time.sleep(3)
        if time_out_flag:
            self.client.logger.error(f"{time_out}秒内订单状态未变为{status}")

    def waitGiftCardOrderStatusInDB(self, order_id, status=3, time_out=300):
        b_time = time.time()
        sql = f"select * from roxe_gift.gift_card_order where send_order_id='{order_id}'"
        while True:
            db_res = self.mysql.exec_sql_query(sql)
            if db_res and db_res[0]["status"] == status:
                self.client.logger.info(f"礼品卡订单{order_id}状态为: {status}")
                self.client.logger.info(f"礼品卡订单总耗时: {db_res[0]['updateTime'] - db_res[0]['createTime']}")
                break
            if time.time() - b_time > time_out:
                self.client.logger.error(f"{time_out}秒内订单状态未变为{status}, 内部处理状态为: {db_res[0]['innerStatus']}")
                break
            """
                WaitingForConfirm(0, "已提交，等待确认"),
                ConfirmCompleted(1, "已确认支付"),
                PaymentCompleted(2, "支付成功"),
                TransferCompleted(3, "转账成功"),
                WaitingForMinting(4, "提交合约进行铸币并返利"),
                MintCompleted(5, "铸币成功返利成功"),
                WaitingForTheRebateStoresTheFashionable(6, "等待商家分成"),
                StoresTheFashionableCompleted(7, "商家分成成功"),
                WaitingForTheSplitAccount(8, "等待平台分账"),
                SplitAccountCompleted(9, "平台分账成功"),
                TimeoutToCancel(10, "超时取消"),
                PaymentFailed(11, "支付失败"),
                TransferFailed(12, "转账失败"),
                MintFailed(13, "铸币失败"),
                RebateFailed(14, "返利失败"),
                SplitAccountFailed(15, "分账失败"),
            """
            self.client.logger.info(f"礼品卡订单{order_id}状态为: {db_res[0]['status']}, 内部处理状态为: {db_res[0]['innerStatus']}")
            time.sleep(10)

    def waitOuterOrderStatusInDB(self, order_id, status="Completed", time_out=300):
        b_time = time.time()
        sql = f"select * from ro_order where order_id='{order_id}'"
        time_out_flag = True
        db_res = None
        while time.time() - b_time < time_out:
            db_res = self.mysql.exec_sql_query(sql)
            if db_res and db_res[0]["rpsId"]:
                self.client.logger.info(f"rps订单: {db_res[0]['rpsId']}")
                break
            time.sleep(3)
        rps_tx_id = None
        while time.time() - b_time < time_out:
            rps_order_sql = f"select * from roxe_pay_in_out.roxe_pay_in_order where id='{db_res[0]['rpsId']}'"
            rps_order = self.mysql.exec_sql_query(rps_order_sql)
            if rps_order and rps_order[0]['serviceChannelOrderId']:
                rps_tx_id = rps_order[0]['serviceChannelOrderId']
                self.client.logger.info(f"支付渠道订单完成: {rps_tx_id}")
                break
            time.sleep(3)
        while time.time() - b_time < time_out:
            rts_order = self.mysql.exec_sql_query(f"select * from roxe_transaction.rts_transaction where instruction_id='{order_id}'")
            if rts_order and rts_order[0]["transactionState"] == "outer_submit":
                out_order_sql = f"select * from roxe_settlement_us001.rss_form as a " \
                                f"left join roxe_settlement_us001.rss_bank_outer as b on a.form_id=b.form_id " \
                                f"where a.payment_id='{rps_tx_id}';"
                out_order = self.mysql.exec_sql_query(out_order_sql)
                if out_order and out_order[0]['outerId']:
                    bank_outer_sql = f"select * from roxe_backend_sysmngt.roxe_pay_out_order where reference_id='{out_order[0]['outerId']}' and status='Processing'"
                    bank_outer = self.mysql.exec_sql_query(bank_outer_sql)
                    if bank_outer:
                        self.mysql.exec_sql_query(f"update roxe_backend_sysmngt.roxe_pay_out_order set status='Success' where reference_id='{out_order[0]['outerId']}'")
                        self.client.logger.info(f"银行卡出金订单: {out_order[0]['outerId']} 修改为完成")
                        break
            time.sleep(3)
        while time.time() - b_time < time_out:
            db_res = self.mysql.exec_sql_query(sql)
            if db_res and db_res[0]["status"] == status:
                time_out_flag = False
                self.client.logger.info(f"订单完成: {order_id}")
                break
            time.sleep(3)
        if time_out_flag:
            self.client.logger.error(f"{time_out}秒内订单状态未变为{status}")

    def checkOrderShareComments(self, comments, order_id, comment=None, user_id=None):
        if comment:
            self.assertEqual(comments["data"][0]["content"], comment)
            self.assertEqual(comments["data"][0]["orderId"], order_id)
            self.checkOrderShareUserInfoFromDB(comments["data"][0]["userInfo"], user_id)
            self.assertIsNotNone(comments["data"][0]["id"])
            self.assertIsNotNone(comments["data"][0]["publishTime"])
        # if RoxeSendData.is_check_db:
        #     sql = ""
        #     db = self.mysql.exec_sql_query(sql)
        #     self.assertEqual(len(comments["data"]), len(db))
        #     for comment in comments["data"]["data"]:
        #         self.assertEqual(comment, db[0])

    def test_001_listCurrency(self):
        """
        获取币种列表
        """
        currency_info = self.client.listCurrency()
        self.checkCodeMessage(currency_info)
        self.assertTrue(len(currency_info["data"]) > 0)
        if RoxeSendData.is_check_db:
            sql = f"select * from ro_currency where state=0"
            currency_db = self.mysql.exec_sql_query(sql)
            for c_info in currency_info["data"]:
                c_db = [i for i in currency_db if i["currency"] == c_info["currency"]]
                self.assertEqual(len(c_db), 1, f"数据库中未找到{c_info['currency']}的币种信息: {currency_db}")
                for key, value in c_info.items():
                    if key == "settlementDate":
                        self.assertEqual(value, 0)
                    elif key == "jsonRemark":
                        self.assertEqual(value, json.loads(c_db[0][key]), f"{key}和数据库校验不一致: {c_db[0][key]}")
                    else:
                        self.assertEqual(value, c_db[0][key], f"{key}和数据库校验不一致: {c_db[0][key]}")

    def test_002_getExchangeRate_sameCurrency_inner_sendToRoxeAccount(self):
        """
        获取币种汇率，同币种，确保INNER, 业务类型为SendToRoxeAccount
        """
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, 10.23)
        self.checkCodeMessage(rate_info)
        self.checkExchangeRate(rate_info["data"], r_params)

    def test_003_getExchangeRate_sameCurrency_inner_request(self):
        """
        获取币种汇率，同币种，确保INNER, 业务类型为request
        """
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_REQUEST.value
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, 10.23)
        self.checkCodeMessage(rate_info)
        self.checkExchangeRate(rate_info["data"], r_params)

    def test_004_getExchangeRate_sameCurrency_inner_deposit(self):
        """
        获取币种汇率，同币种，确保INNER, 业务类型为deposit
        """
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_DEPOSIT.value
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, 10.23)
        self.checkCodeMessage(rate_info)
        self.checkExchangeRate(rate_info["data"], r_params)

    def test_005_getExchangeRate_sameCurrency_inner_withdraw(self):
        """
        获取币种汇率，同币种，确保INNER, 业务类型为withdraw
        """
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, 10.23)
        self.checkCodeMessage(rate_info)
        self.checkExchangeRate(rate_info["data"], r_params)

    def test_006_getExchangeRate_sameCurrency_outer_sendToRoxeAccount(self):
        """
        获取币种汇率，同币种，确保OUTER, 业务类型为SendToRoxeAccount
        """
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_OUTER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, "", 10.23)
        self.checkCodeMessage(rate_info)
        self.checkExchangeRate(rate_info["data"], r_params)

    def test_007_getExchangeRate_sameCurrency_outer_request(self):
        """
        获取币种汇率，同币种，确保OUTER, 业务类型为request
        """
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_OUTER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_REQUEST.value
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, "", 10.23)
        self.checkCodeMessage(rate_info)
        self.checkExchangeRate(rate_info["data"], r_params)

    def test_008_getExchangeRate_sameCurrency_outer_deposit(self):
        """
        获取币种汇率，同币种，确保OUTER, 业务类型为deposit
        """
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_OUTER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_DEPOSIT.value
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, "", 10.23)
        self.checkCodeMessage(rate_info)
        self.checkExchangeRate(rate_info["data"], r_params)

    def test_009_getExchangeRate_sameCurrency_outer_withdraw(self):
        """
        获取币种汇率，同币种，确保OUTER, 业务类型为withdraw
        """
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_OUTER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, "", 10.23)
        self.checkCodeMessage(rate_info, "PAY_RPS_697", "amount invalid")
        self.assertIsNone(rate_info["data"])

    def test_010_queryOuterMethod(self):
        """
        查询出金方式, 需要先查询汇率得到出金节点
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        method_info = self.client.getOuterMethod(currency, rate_info["data"]["outerNodeCode"])
        self.checkCodeMessage(method_info)
        self.assertEqual(method_info["data"], ["BANK"])

    def test_011_queryOuterFields(self):
        """
        查询出金必填字段, 需要先查询汇率得到出金节点
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        fields = self.client.getOuterFields(currency, outer_node=rate_info["data"]["outerNodeCode"])
        self.checkCodeMessage(fields)
        self.assertEqual(fields["data"], RSSData.manual_bank_fields)

    def test_012_checkOuterFields(self):
        """
        校验出金必填字段, 需要先查询汇率得到出金节点
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        check_fields = self.client.checkOuterFields(currency, RoxeSendData.user_outer_bank, rate_info["data"]["outerNodeCode"])
        self.checkCodeMessage(check_fields)
        self.assertTrue(check_fields["data"])

    def test_013_listReceiverAccount_notHaveReceiverAccount(self):
        """
        列出收款人账户，没有绑定收款人账户时查询为空
        """
        self.client.deleteReceiverAccountFromDB(self)
        r_accounts = self.client.listReceiverAccount(RoxeSendData.currency[0])
        self.checkCodeMessage(r_accounts)
        self.assertEqual(r_accounts["data"], [])

    def checkBindAccountWithListReceiverAccount(self, bind_account, list_accounts):
        # self.assertIn(bind_account, list_accounts, "绑定的收款人账户1未在查询结果中")
        list_account = [i for i in list_accounts if i['accountId'] == bind_account["accountId"]]
        for k, v in bind_account.items():
            if k == "createdAt":
                self.assertAlmostEqual(v, list_account[0][k], delta=1000)
                continue
            self.assertEqual(v, list_account[0][k], f"绑定的收款人账户{k}校验失败")

    def test_014_bindReceiverAccount_notHaveReceiverAccount(self):
        """
        绑定收款人账户，没有绑定收款人账户时应可以绑定，绑定完后可以查询到
        """
        self.client.deleteReceiverAccountFromDB(self)
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        bind_res, r_body = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_1, rate_info["data"]["outerNodeCode"])
        self.checkCodeMessage(bind_res)
        self.checkBindReceiverAccount(bind_res["data"], r_body, RoxeSendData.user_id)

        r_accounts = self.client.listReceiverAccount(currency)
        self.checkCodeMessage(r_accounts)
        self.checkListReceiverAccount(r_accounts["data"], RoxeSendData.user_id)
        self.checkBindAccountWithListReceiverAccount(bind_res["data"], r_accounts["data"])

    def test_015_bindReceiverAccount_haveReceiverAccount(self):
        """
        绑定收款人账户，有绑定收款人账户时应可以绑定，绑定完后可以查询到
        """
        self.client.deleteReceiverAccountFromDB(self)
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        bind_res, r_body = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_1, rate_info["data"]["outerNodeCode"])
        self.checkCodeMessage(bind_res)
        self.checkBindReceiverAccount(bind_res["data"], r_body, RoxeSendData.user_id)

        bind_res2, r_body2 = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_2, rate_info["data"]["outerNodeCode"])
        self.checkCodeMessage(bind_res2)
        self.checkBindReceiverAccount(bind_res2["data"], r_body2, RoxeSendData.user_id)

        r_accounts = self.client.listReceiverAccount(currency)
        self.checkCodeMessage(r_accounts)
        self.checkListReceiverAccount(r_accounts["data"], RoxeSendData.user_id)
        self.checkBindAccountWithListReceiverAccount(bind_res["data"], r_accounts["data"])
        self.checkBindAccountWithListReceiverAccount(bind_res2["data"], r_accounts["data"])

    def test_016_bindReceiverAccount_deleteReceiverAccount(self):
        """
        绑定收款人账户，删除绑定的收款人账户时应可以再次绑定，绑定完后可以查询到
        """
        self.client.deleteReceiverAccountFromDB(self)
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        bind_res, r_body = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_1, rate_info["data"]["outerNodeCode"])

        delete_res = self.client.deleteReceiverAccount(bind_res["data"]["accountId"])
        self.checkCodeMessage(delete_res)
        self.assertTrue(delete_res["data"])

        bind_res2, r_body2 = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_1, rate_info["data"]["outerNodeCode"])
        self.checkCodeMessage(bind_res2)
        self.checkBindReceiverAccount(bind_res2["data"], r_body2, RoxeSendData.user_id)

        r_accounts = self.client.listReceiverAccount(currency)
        self.checkCodeMessage(r_accounts)
        self.checkListReceiverAccount(r_accounts["data"], RoxeSendData.user_id)
        self.checkBindAccountWithListReceiverAccount(bind_res2["data"], r_accounts["data"])

    def test_017_queryAccountBalance(self):
        """
        查询账户资产列表
        """
        balance_info = self.client.listBalance()
        self.checkCodeMessage(balance_info)
        self.assertIsNotNone(balance_info["data"])
        self.checkAccountBalance(balance_info["data"], RoxeSendData.user_id)

    def test_018_queryAccountCurrencyBalance(self):
        """
        查询账户币种资产
        """
        currency = RoxeSendData.currency[0]
        balance_info = self.client.listCurrencyBalance(currency)
        self.checkCodeMessage(balance_info)
        self.assertEqual(balance_info["data"]["currency"], currency)
        self.checkAccountBalance(balance_info["data"], RoxeSendData.user_id)

    def test_019_deposit_notPayThenCancel(self):
        """
        充值下单, 查询交易详情，然后撤销, 查询交易详情
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        user_balance = self.client.listCurrencyBalance(currency)

        daily_limit, ninety_day_limit, left_day = self.client.calKycLimitAmount(self, RoxeSendData.user_id, RoxeSendData.user_login_token)

        deposit_info, re_body = self.client.deposit(currency, amount)
        self.checkCodeMessage(deposit_info)
        self.checkDepositOrderInfo(deposit_info["data"], re_body, RoxeSendData.user_id)
        tx_id = deposit_info["data"]["transactionId"]

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Submitted")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id)

        # 取消交易
        cancel_info = self.client.cancelTransaction(tx_id)
        self.checkCodeMessage(cancel_info)
        self.assertTrue(cancel_info["data"])

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Cancelled")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id)

        user_balance2 = self.client.listCurrencyBalance(currency)
        self.assertEqual(user_balance2, user_balance, "账户资产不正确")

        daily_limit2, ninety_day_limit2, left_day2 = self.client.calKycLimitAmount(self, RoxeSendData.user_id, RoxeSendData.user_login_token)

        self.assertAlmostEqual(daily_limit - daily_limit2, 0, delta=0.1**6)
        self.assertAlmostEqual(ninety_day_limit - ninety_day_limit2, 0, delta=0.1**6)

    def test_020_deposit_selectAchPay(self):
        """
        充值下单, 查询交易详情，选择ach支付, 查询交易详情
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        user_balance = self.client.listCurrencyBalance(currency)

        daily_limit, ninety_day_limit, left_day = self.client.calKycLimitAmount(self, RoxeSendData.user_id, RoxeSendData.user_login_token)

        deposit_info, re_body = self.client.deposit(currency, amount)
        self.checkCodeMessage(deposit_info)
        self.checkDepositOrderInfo(deposit_info["data"], re_body, RoxeSendData.user_id)
        tx_id = deposit_info["data"]["transactionId"]

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Submitted")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id)

        # 选择ach支付
        order_id = tx_info["data"]["orderId"]
        target_account = tx_info["data"]["counterparty"]["roxeId"]
        self.rps_client.submitAchPayOrder(target_account, amount, expect_pay_success=False, account_info=RPSData.ach_account, businessOrderNo=order_id)
        self.waitOrderStatusInDB(order_id, "Processing")
        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id)

        self.waitOrderStatusInDB(order_id)
        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Complete")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id)
        user_balance2 = self.client.listCurrencyBalance(currency)
        self.assertAlmostEqual(user_balance2["data"]["amount"] - user_balance["data"]["amount"], amount, delta=0.1**6)
        time.sleep(2)
        daily_limit2, ninety_day_limit2, left_day2 = self.client.calKycLimitAmount(self, RoxeSendData.user_id, RoxeSendData.user_login_token)

        self.assertAlmostEqual(daily_limit - daily_limit2, amount, delta=0.1**6)
        self.assertAlmostEqual(ninety_day_limit - ninety_day_limit2, amount, delta=0.1**6)

    def test_021_withdraw(self):
        """
        提现, 查询交易详情
        """
        currency = RoxeSendData.currency[0]
        r_accounts = self.client.listReceiverAccount(currency)["data"]
        if len(r_accounts) == 0:
            bind_res, r_body = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_1, RTSData.node_code)
            out_account = bind_res
        else:
            out_account = r_accounts[0]
        amount = 6.35
        user_balance = self.client.listCurrencyBalance(currency)
        daily_limit, ninety_day_limit, left_day = self.client.calKycLimitAmount(self, RoxeSendData.user_id, RoxeSendData.user_login_token)

        withdraw_info = self.client.withdraw(currency, amount, out_account["accountId"], RTSData.node_code)
        self.checkCodeMessage(withdraw_info)
        tx_id = withdraw_info["data"]["transactionId"]

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id, out_account["accountDetail"])

        self.waitOuterOrderStatusInDB(tx_info["data"]["orderId"])
        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Complete")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id, out_account["accountDetail"])

        user_balance2 = self.client.listCurrencyBalance(currency)
        self.client.logger.info(f"资产变化了: {user_balance2['data']['amount'] - user_balance['data']['amount']}")
        self.assertAlmostEqual(user_balance['data']['amount'] - user_balance2['data']['amount'], amount, delta=0.1**6)

        daily_limit2, ninety_day_limit2, left_day2 = self.client.calKycLimitAmount(self, RoxeSendData.user_id, RoxeSendData.user_login_token)
        self.assertAlmostEqual(daily_limit - daily_limit2, amount, delta=0.1**6)
        self.assertAlmostEqual(ninety_day_limit - ninety_day_limit2, amount, delta=0.1**6)

    def test_022_sendToRoAccount_notPayThenCancel(self):
        """
        Pay，不支付，撤销交易
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b

        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")
        daily_limit, ninety_day_limit, left_day = self.client.calKycLimitAmount(self, RoxeSendData.user_id, RoxeSendData.user_login_token)

        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount)
        pay_info, re_body = self.client.sendToRoxeAccount(
            to_ro_id, rate_info["data"]["exchangeRate"], currency, amount, currency, rate_info["data"]["receiveAmount"], ensure_side, 2
        )
        self.checkCodeMessage(pay_info)
        self.checkSenToRoAccountOrderInfo(pay_info["data"], re_body, RoxeSendData.user_id, RoxeSendData.user_id_b)
        tx_id = pay_info["data"]["transactionId"]

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Submitted")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        # 取消交易
        cancel_info = self.client.cancelTransaction(tx_id)
        self.checkCodeMessage(cancel_info)
        self.assertTrue(cancel_info["data"])

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Cancelled")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertEqual(from_balance2, from_balance, msg="from账户资产不正确")
        self.assertEqual(to_balance2, to_balance, msg="to账户资产不正确")

        daily_limit2, ninety_day_limit2, left_day2 = self.client.calKycLimitAmount(self, RoxeSendData.user_id, RoxeSendData.user_login_token)
        self.assertAlmostEqual(daily_limit - daily_limit2, 0, delta=0.1**6)
        self.assertAlmostEqual(ninety_day_limit - ninety_day_limit2, 0, delta=0.1**6)

    def test_023_sendToRoAccount_selectAchPay(self):
        """
        Pay，选择ach支付，等待交易完成
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b
        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")
        daily_limit, ninety_day_limit, left_day = self.client.calKycLimitAmount(self, RoxeSendData.user_id, RoxeSendData.user_login_token)

        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount)
        pay_info, re_body = self.client.sendToRoxeAccount(
            to_ro_id, rate_info["data"]["exchangeRate"], currency, amount, currency, rate_info["data"]["receiveAmount"], ensure_side, 2, note="pay"
        )
        self.checkCodeMessage(pay_info)
        self.checkSenToRoAccountOrderInfo(pay_info["data"], re_body, RoxeSendData.user_id, RoxeSendData.user_id_b)
        tx_id = pay_info["data"]["transactionId"]

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Submitted")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        # 选择ach支付
        order_id = tx_info["data"]["orderId"]
        target_account = tx_info["data"]["counterparty"]["roxeId"]
        self.rps_client.submitAchPayOrder(target_account, amount, expect_pay_success=False, account_info=RPSData.ach_account, businessOrderNo=order_id)
        self.waitOrderStatusInDB(order_id, "Processing")

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        self.waitOrderStatusInDB(order_id)

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Complete")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertAlmostEqual(from_balance2, from_balance, msg="from账户资产不正确", delta=0.1**6)
        self.assertAlmostEqual(to_balance2 - to_balance, amount, msg="to账户资产不正确", delta=0.1**6)

        daily_limit2, ninety_day_limit2, left_day2 = self.client.calKycLimitAmount(self, RoxeSendData.user_id, RoxeSendData.user_login_token)
        self.assertAlmostEqual(daily_limit - daily_limit2, amount, delta=0.1**6)
        self.assertAlmostEqual(ninety_day_limit - ninety_day_limit2, amount, delta=0.1**6)

    def test_024_sendToRoAccount_selectWalletPay(self):
        """
        Pay，选择wallet支付，等待交易完成
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b
        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")
        daily_limit, ninety_day_limit, left_day = self.client.calKycLimitAmount(self, RoxeSendData.user_id, RoxeSendData.user_login_token)

        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount)
        pay_info, re_body = self.client.sendToRoxeAccount(
            to_ro_id, rate_info["data"]["exchangeRate"], currency, amount, currency, rate_info["data"]["receiveAmount"], ensure_side, 2
        )
        self.checkCodeMessage(pay_info)
        self.checkSenToRoAccountOrderInfo(pay_info["data"], re_body, RoxeSendData.user_id, RoxeSendData.user_id_b)
        tx_id = pay_info["data"]["transactionId"]

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Submitted")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        # 选择wallet支付
        order_id = tx_info["data"]["orderId"]
        self.rps_client.submitPayOrderTransferToRoxeAccount(from_ro_id, to_ro_id, amount, businessType="transfer", expect_pay_success=False, businessOrderNo=order_id)
        self.waitOrderStatusInDB(order_id, "Processing")

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        self.waitOrderStatusInDB(order_id)

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Complete")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertAlmostEqual(from_balance - from_balance2, amount, msg="from账户资产不正确", delta=0.1**6)
        self.assertAlmostEqual(to_balance2 - to_balance, amount, msg="to账户资产不正确", delta=0.1**6)

        daily_limit2, ninety_day_limit2, left_day2 = self.client.calKycLimitAmount(self, RoxeSendData.user_id, RoxeSendData.user_login_token)
        self.assertAlmostEqual(daily_limit - daily_limit2, amount, delta=0.1**6)
        self.assertAlmostEqual(ninety_day_limit - ninety_day_limit2, amount, delta=0.1**6)

    def test_025_request_notPayThenCancelRequest(self):
        """
        request，不支付，撤销交易
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b

        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")
        daily_limit, ninety_day_limit, left_day = self.client.calKycLimitAmount(self, RoxeSendData.user_id, RoxeSendData.user_login_token)

        pay_info, re_body = self.client.request(RoxeSendData.user_id_b, currency, amount, "hello")
        self.checkCodeMessage(pay_info)
        self.checkRequestOrderInfo(pay_info["data"], re_body, RoxeSendData.user_id, RoxeSendData.user_id_b)
        tx_id = pay_info["data"]["transactionId"]

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Temporary")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        # B查询到的request订单
        tx_h, tx_body = self.client.getTransactionHistory(token=RoxeSendData.user_login_token_b)
        tx_id_b = tx_h["data"]["data"][0]["transactionId"]

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Temporary")
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        # 取消交易
        cancel_info = self.client.cancelTransaction(tx_id)
        self.checkCodeMessage(cancel_info)
        self.assertTrue(cancel_info["data"])

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Cancelled")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Cancelled")
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertEqual(from_balance2, from_balance, msg="from账户资产不正确")
        self.assertEqual(to_balance2, to_balance, msg="to账户资产不正确")

        daily_limit2, ninety_day_limit2, left_day2 = self.client.calKycLimitAmount(self, RoxeSendData.user_id, RoxeSendData.user_login_token)
        self.assertAlmostEqual(daily_limit - daily_limit2, 0, delta=0.1**6)
        self.assertAlmostEqual(ninety_day_limit - ninety_day_limit2, 0, delta=0.1**6)

    def test_026_request_declineRequest(self):
        """
        request，拒绝支付交易
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b

        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")
        daily_limit, ninety_day_limit, left_day = self.client.calKycLimitAmount(self, RoxeSendData.user_id, RoxeSendData.user_login_token)

        pay_info, re_body = self.client.request(RoxeSendData.user_id_b, currency, amount, "hello")
        self.checkCodeMessage(pay_info)
        self.checkRequestOrderInfo(pay_info["data"], re_body, RoxeSendData.user_id, RoxeSendData.user_id_b)
        tx_id = pay_info["data"]["transactionId"]
        order_id = pay_info["data"]["orderId"]

        # A查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Temporary")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        # B查询到的request订单
        tx_h, tx_body = self.client.getTransactionHistory(token=RoxeSendData.user_login_token_b)
        tx_id_b = tx_h["data"]["data"][0]["transactionId"]
        # B查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Temporary")
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        # 拒绝支付交易
        decline_info = self.client.declineRequest(order_id, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(decline_info)
        self.assertTrue(decline_info["data"])

        # A查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Declined")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        # B查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Declined")
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertEqual(from_balance2, from_balance, msg="from账户资产不正确")
        self.assertEqual(to_balance2, to_balance, msg="to账户资产不正确")

        daily_limit2, ninety_day_limit2, left_day2 = self.client.calKycLimitAmount(self, RoxeSendData.user_id, RoxeSendData.user_login_token)
        self.assertAlmostEqual(daily_limit - daily_limit2, 0, delta=0.1**6)
        self.assertAlmostEqual(ninety_day_limit - ninety_day_limit2, 0, delta=0.1**6)

    def test_027_payRequest_selectAchPay(self):
        """
        request，选择ach支付，等待交易完成
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b

        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")

        daily_limit, ninety_day_limit, left_day = self.client.calKycLimitAmount(self, RoxeSendData.user_id_b, RoxeSendData.user_login_token_b)

        pay_info, re_body = self.client.request(RoxeSendData.user_id_b, currency, amount, "hello")
        tx_id = pay_info["data"]["transactionId"]

        # A查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Temporary")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)
        # B查询到的request订单
        tx_h, tx_body = self.client.getTransactionHistory(token=RoxeSendData.user_login_token_b)
        tx_id_b = tx_h["data"]["data"][0]["transactionId"]

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Temporary")
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_REQUEST.value
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount)
        # 另外一方进行支付
        pay_request, pay_body = self.client.payRequest(
            tx_id_b, from_ro_id, rate_info["data"]["exchangeRate"], currency,
            rate_info["data"]["sendAmount"], currency, rate_info["data"]["receiveAmount"],
            2, "pay request", RoxeSendData.user_login_token_b
        )
        self.checkCodeMessage(pay_request)
        self.checkPayRequestOrderInfo(pay_request["data"], pay_body, RoxeSendData.user_id_b, RoxeSendData.user_id)
        # 选择ach支付
        order_id = pay_request["data"]["orderId"]
        pay_amount = ApiUtils.parseNumberDecimal(float(rate_info["data"]["sendAmount"]))
        self.rps_client.submitAchPayOrder(from_ro_id, pay_amount, expect_pay_success=False, account_info=RPSData.ach_account, businessOrderNo=order_id)
        self.waitOrderStatusInDB(order_id, "Processing")

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        self.waitOrderStatusInDB(order_id)

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Complete")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Complete")
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertAlmostEqual(from_balance2 - from_balance, amount, msg="from账户资产不正确", delta=0.1**6)
        self.assertAlmostEqual(to_balance2, to_balance, msg="to账户资产不正确", delta=0.1**6)

        daily_limit2, ninety_day_limit2, left_day2 = self.client.calKycLimitAmount(self, RoxeSendData.user_id_b, RoxeSendData.user_login_token_b)
        self.assertAlmostEqual(daily_limit - daily_limit2, amount, delta=0.1**6)
        self.assertAlmostEqual(ninety_day_limit - ninety_day_limit2, amount, delta=0.1**6)

    def test_028_payRequest_selectWalletPay(self):
        """
        request，选择wallet支付，等待交易完成
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b

        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")

        daily_limit, ninety_day_limit, left_day = self.client.calKycLimitAmount(self, RoxeSendData.user_id_b, RoxeSendData.user_login_token_b)

        pay_info, re_body = self.client.request(RoxeSendData.user_id_b, currency, amount, "hello")
        tx_id = pay_info["data"]["transactionId"]

        # A查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Temporary")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        # B查询到的交易
        tx_h, tx_body = self.client.getTransactionHistory(token=RoxeSendData.user_login_token_b)
        tx_id_b = tx_h["data"]["data"][0]["transactionId"]

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Temporary")
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_REQUEST.value
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount)
        # 另外一方进行支付
        pay_request, pay_body = self.client.payRequest(
            tx_id_b, from_ro_id, rate_info["data"]["exchangeRate"], currency,
            rate_info["data"]["sendAmount"], currency, rate_info["data"]["receiveAmount"],
            2, "pay request", RoxeSendData.user_login_token_b
        )
        self.checkCodeMessage(pay_request)
        self.checkPayRequestOrderInfo(pay_request["data"], pay_body, RoxeSendData.user_id_b, RoxeSendData.user_id)

        # 选择wallet支付
        order_id = pay_request["data"]["orderId"]
        pay_amount = ApiUtils.parseNumberDecimal(float(rate_info["data"]["sendAmount"]))
        self.rps_client.submitPayOrderTransferToRoxeAccount(to_ro_id, from_ro_id, pay_amount, businessType="transfer", expect_pay_success=False, businessOrderNo=order_id)
        self.waitOrderStatusInDB(order_id, "Processing")

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        self.waitOrderStatusInDB(order_id)

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Complete")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Complete")
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertAlmostEqual(from_balance2 - from_balance, amount, msg="from账户资产不正确", delta=0.1**6)
        self.assertAlmostEqual(to_balance - to_balance2, pay_amount, msg="to账户资产不正确", delta=0.1**6)

        daily_limit2, ninety_day_limit2, left_day2 = self.client.calKycLimitAmount(self, RoxeSendData.user_id_b, RoxeSendData.user_login_token_b)
        self.assertAlmostEqual(daily_limit - daily_limit2, amount, delta=0.1**6)
        self.assertAlmostEqual(ninety_day_limit - ninety_day_limit2, amount, delta=0.1**6)

    def test_029_getTransactionHistory(self):
        """
        查询历史交易，默认查询所有
        """

        transactions, r_params = self.client.getTransactionHistory()
        self.checkCodeMessage(transactions)
        self.checkTransactionHistory(transactions["data"], r_params, RoxeSendData.user_id)

    def test_030_getTransactionHistory_searchNote(self):
        """
        查询历史交易，搜索备注
        """

        transactions, r_params = self.client.getTransactionHistory(key_word="pay")
        self.checkCodeMessage(transactions)
        self.checkTransactionHistory(transactions["data"], r_params, RoxeSendData.user_id)

    def test_031_getTransactionHistory_searchFirstName(self):
        """
        查询历史交易，搜索FirstName
        """

        transactions, r_params = self.client.getTransactionHistory(key_word="Li")
        self.checkCodeMessage(transactions)
        self.checkTransactionHistory(transactions["data"], r_params, RoxeSendData.user_id)

    def test_032_getTransactionHistory_searchLastName(self):
        """
        查询历史交易，搜索LastName
        """

        transactions, r_params = self.client.getTransactionHistory(key_word="ing")
        self.checkCodeMessage(transactions)
        self.checkTransactionHistory(transactions["data"], r_params, RoxeSendData.user_id)

    def test_033_getTransactionHistory_typeIsSendToRoxeAccount(self):
        """
        查询历史交易，筛选sendToRoxeAccount
        """

        transactions, r_params = self.client.getTransactionHistory(b_type=RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value)
        self.checkCodeMessage(transactions)
        self.checkTransactionHistory(transactions["data"], r_params, RoxeSendData.user_id)

    def test_034_getTransactionHistory_typeIsRequest(self):
        """
        查询历史交易，筛选Request
        """

        transactions, r_params = self.client.getTransactionHistory(b_type=RoxeSendEnum.BUSINESS_TYPE_REQUEST.value)
        self.checkCodeMessage(transactions)
        self.checkTransactionHistory(transactions["data"], r_params, RoxeSendData.user_id)

    def test_035_getTransactionHistory_typeIsDeposit(self):
        """
        查询历史交易，筛选deposit
        """

        transactions, r_params = self.client.getTransactionHistory(b_type=RoxeSendEnum.BUSINESS_TYPE_DEPOSIT.value)
        self.checkCodeMessage(transactions)
        self.checkTransactionHistory(transactions["data"], r_params, RoxeSendData.user_id)

    def test_036_getTransactionHistory_typeIsWithdraw(self):
        """
        查询历史交易，筛选withdraw
        """

        transactions, r_params = self.client.getTransactionHistory(b_type=RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value)
        self.checkCodeMessage(transactions)
        self.checkTransactionHistory(transactions["data"], r_params, RoxeSendData.user_id)

    def test_037_getTransactionHistory_selectCurrentYear(self):
        """
        查询历史交易，筛选当前整年的数据
        """
        cur_year = datetime.datetime.utcnow().year
        b_time = int(datetime.datetime.strptime(f"{cur_year}-01-01", "%Y-%m-%d").timestamp() * 1000)
        transactions, r_params = self.client.getTransactionHistory(begin=b_time)
        self.checkCodeMessage(transactions)
        self.checkTransactionHistory(transactions["data"], r_params, RoxeSendData.user_id)

    def test_038_getTransactionHistory_selectLastYear(self):
        """
        查询历史交易，筛选上一年的数据
        """
        cur_year = datetime.datetime.utcnow().year
        b_time = int(datetime.datetime.strptime(f"{cur_year - 1}-01-01", "%Y-%m-%d").timestamp() * 1000)
        e_time = int(datetime.datetime.strptime(f"{cur_year}-01-01", "%Y-%m-%d").timestamp() * 1000)
        transactions, r_params = self.client.getTransactionHistory(begin=b_time, end=e_time)
        self.checkCodeMessage(transactions)
        self.checkTransactionHistory(transactions["data"], r_params, RoxeSendData.user_id)

    def test_039_getTransactionHistory_selectNextYear(self):
        """
        查询历史交易，筛选下一年的数据
        """
        cur_year = datetime.datetime.utcnow().year
        b_time = int(datetime.datetime.strptime(f"{cur_year + 1}-01-01", "%Y-%m-%d").timestamp() * 1000)
        e_time = int(datetime.datetime.strptime(f"{cur_year + 2}-01-01", "%Y-%m-%d").timestamp() * 1000)
        transactions, r_params = self.client.getTransactionHistory(begin=b_time, end=e_time)
        self.checkCodeMessage(transactions)
        self.assertEqual(transactions["data"]["data"], [])

    def test_040_getTransactionHistory_selectCurrentMonth(self):
        """
        查询历史交易，筛选当前月份的数据
        """
        cur_time = datetime.datetime.utcnow()
        b_time = int(datetime.datetime.strptime(f"{cur_time.year}-{cur_time.month}-01", "%Y-%m-%d").timestamp() * 1000)
        e_time = int(datetime.datetime.strptime(f"{cur_time.year}-{cur_time.month + 1}-01", "%Y-%m-%d").timestamp() * 1000)
        transactions, r_params = self.client.getTransactionHistory(begin=b_time, end=e_time)
        self.checkCodeMessage(transactions)
        self.checkTransactionHistory(transactions["data"], r_params, RoxeSendData.user_id)

    def test_041_getTransactionHistory_selectLastMonth(self):
        """
        查询历史交易，筛选上一月份的数据
        """
        cur_time = datetime.datetime.utcnow()
        b_time = int(datetime.datetime.strptime(f"{cur_time.year}-{cur_time.month - 1}-01", "%Y-%m-%d").timestamp() * 1000)
        e_time = int(datetime.datetime.strptime(f"{cur_time.year}-{cur_time.month}-01", "%Y-%m-%d").timestamp() * 1000)
        transactions, r_params = self.client.getTransactionHistory(begin=b_time, end=e_time)
        self.checkCodeMessage(transactions)
        self.checkTransactionHistory(transactions["data"], r_params, RoxeSendData.user_id)

    def test_042_getTransactionHistory_selectNextMonth(self):
        """
        查询历史交易，筛选下一月份的数据
        """
        cur_time = datetime.datetime.now()
        b_str = f"{cur_time.year}-{cur_time.month + 1}-01" if cur_time.month < 12 else f"{cur_time.year + 1}-01-01"
        e_str = f"{cur_time.year}-{cur_time.month + 1}-01" if cur_time.month < 11 else f"{cur_time.year + 1}-0{cur_time.month + 2 - 12}-01"
        b_time = int(datetime.datetime.strptime(b_str, "%Y-%m-%d").timestamp() * 1000)
        e_time = int(datetime.datetime.strptime(e_str, "%Y-%m-%d").timestamp() * 1000)
        transactions, r_params = self.client.getTransactionHistory(begin=b_time, end=e_time)
        self.checkCodeMessage(transactions)
        self.assertEqual(transactions["data"]["data"], [])

    def test_043_getRecentContact(self):
        """
        获取最近的联系人
        """
        recent_info = self.client.getUserRecentContact()
        self.checkCodeMessage(recent_info)
        self.checkRecentContact(recent_info["data"], RoxeSendData.user_id)

    def test_044_getRecentContact_pay(self):
        """
        获取最近的联系人，pay业务，pay订单完成前数量不变，订单完成后数量加1
        """
        recent_info = self.client.getUserRecentContact()
        self.checkCodeMessage(recent_info)
        self.checkRecentContact(recent_info["data"], RoxeSendData.user_id)
        count = recent_info["data"][0]["count"]

        recent_info_b = self.client.getUserRecentContact(token=RoxeSendData.user_login_token_b)
        amount = 4.35
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        to_ro_id = RoxeSendData.user_account

        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount)
        pay_info, re_body = self.client.sendToRoxeAccount(
            to_ro_id, rate_info["data"]["exchangeRate"], currency, amount, currency, rate_info["data"]["receiveAmount"], ensure_side, 2, note="pay", token=RoxeSendData.user_login_token_b
        )
        order_id = pay_info["data"]["orderId"]
        # 选择ach支付
        self.rps_client.submitAchPayOrder(to_ro_id, amount, expect_pay_success=False, account_info=RPSData.ach_account, businessOrderNo=order_id)
        self.waitOrderStatusInDB(order_id, "Processing")
        recent_info = self.client.getUserRecentContact()
        self.checkCodeMessage(recent_info)
        self.assertEqual(recent_info["data"][0]["count"], count, "未读取订单数量不正确")
        self.checkRecentContact(recent_info["data"], RoxeSendData.user_id)
        self.waitOrderStatusInDB(order_id)
        recent_info = self.client.getUserRecentContact()
        self.checkCodeMessage(recent_info)
        self.checkRecentContact(recent_info["data"], RoxeSendData.user_id)
        self.assertEqual(int(recent_info["data"][0]["count"]), int(count) + 1, "未读取订单数量不正确")

        recent_info_b2 = self.client.getUserRecentContact(token=RoxeSendData.user_login_token_b)
        self.assertEqual(recent_info_b["data"][0]["count"], recent_info_b2["data"][0]["count"], "发起支付的未读取数量应不变")

    def test_045_getRecentContact_request(self):
        """
        获取最近的联系人，request, A向B发起request, B的数量就加1
        """
        recent_info = self.client.getUserRecentContact()
        self.checkCodeMessage(recent_info)
        self.checkRecentContact(recent_info["data"], RoxeSendData.user_id)
        count = recent_info["data"][0]["count"]

        recent_info_b = self.client.getUserRecentContact(token=RoxeSendData.user_login_token_b)

        amount = 4
        currency = RoxeSendData.currency[0]
        pay_info, re_body = self.client.request(RoxeSendData.user_id, currency, amount, "hello", token=RoxeSendData.user_login_token_b)

        recent_info = self.client.getUserRecentContact()
        self.checkCodeMessage(recent_info)
        self.checkRecentContact(recent_info["data"], RoxeSendData.user_id)
        self.assertEqual(int(recent_info["data"][0]["count"]), int(count) + 1, "未订单数量不正确")

        recent_info_b2 = self.client.getUserRecentContact(token=RoxeSendData.user_login_token_b)
        self.assertEqual(recent_info_b["data"][0]["count"], recent_info_b2["data"][0]["count"], "发起支付的未读取数量应不变")
        # 撤销交易
        tx_id = pay_info["data"]["transactionId"]
        self.client.cancelTransaction(tx_id, token=RoxeSendData.user_login_token_b)

    def test_046_updateUserReadOrder_countIsNone(self):
        """
        更新用户未读取的订单数量，更新未读取订单数量为none的用户
        """
        recent_info = self.client.getUserRecentContact()
        self.checkCodeMessage(recent_info)
        self.checkRecentContact(recent_info["data"], RoxeSendData.user_id)
        r_info = [i for i in recent_info["data"] if i["count"] is None]

        update_info = self.client.updateUserReadOrder(r_info[0]["userId"])
        self.checkCodeMessage(update_info)
        self.assertIsNone(update_info["data"])

        recent_info2 = self.client.getUserRecentContact()
        self.checkCodeMessage(recent_info2)
        self.checkRecentContact(recent_info2["data"], RoxeSendData.user_id)
        u_r_info = [i for i in recent_info2["data"] if i["userId"] == r_info[0]["userId"]]
        self.assertEqual(u_r_info[0]["count"], r_info[0]["count"])

    def test_047_updateUserReadOrder_countIsNotNone(self):
        """
        更新用户未读取的订单数量，更新未读取订单数量不为none的用户
        """
        recent_info = self.client.getUserRecentContact()
        self.checkCodeMessage(recent_info)
        self.checkRecentContact(recent_info["data"], RoxeSendData.user_id)
        r_info = [i for i in recent_info["data"] if i["count"]]

        update_info = self.client.updateUserReadOrder(r_info[0]["userId"])
        self.checkCodeMessage(update_info)
        self.assertIsNone(update_info["data"])

        recent_info2 = self.client.getUserRecentContact()
        self.checkCodeMessage(recent_info2)
        self.checkRecentContact(recent_info2["data"], RoxeSendData.user_id)
        u_r_info = [i for i in recent_info2["data"] if i["userId"] == r_info[0]["userId"]]
        self.assertIsNone(u_r_info[0]["count"])

    def test_048_kycVerification_notKyc(self):
        """
        判断转账金额是否达到kyc上限，没有通过kyc的用户
        """
        kyc_info = self.client.kycVerification(RoxeSendData.currency[0], 1, RoxeSendData.user_login_token_c)
        self.checkCodeMessage(kyc_info, "RSD10401", "Kyc not pass,level: L2")
        self.assertIsNone(kyc_info["data"])

    def test_049_kycVerification_kaKyc(self):
        """
        判断转账金额是否达到kyc上限，通过ka的用户
        """
        kyc_info = self.client.kycVerification(RoxeSendData.currency[0], 1000, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(kyc_info)
        self.assertEqual(kyc_info["data"], "SUCCESS")

    def test_050_kycVerification_kmKyc(self):
        """
        判断转账金额是否达到kyc上限，通过km的用户
        """
        kyc_info = self.client.kycVerification(RoxeSendData.currency[0], 10100, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(kyc_info, "RSD10402", "Kyc not pass,level: L3")
        self.assertEqual(kyc_info["data"], None)

    def test_051_listNotification(self):
        """
        查看交易通知列表
        """
        notifications = self.client.listNotification()
        self.checkCodeMessage(notifications)
        self.checkNotifications(notifications["data"], RoxeSendData.user_id)

    def test_052_listNotification_pay(self):
        """
        查看交易通知列表, pay业务，只有成功后，收款人才能收到通知
        """
        notifications = self.client.listNotification()
        self.checkCodeMessage(notifications)
        self.checkNotifications(notifications["data"], RoxeSendData.user_id)

        amount = 4.35
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        from_ro_id = RoxeSendData.user_account_b
        to_ro_id = RoxeSendData.user_account

        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount)
        pay_info, re_body = self.client.sendToRoxeAccount(
            to_ro_id, rate_info["data"]["exchangeRate"], currency, amount, currency, rate_info["data"]["receiveAmount"], ensure_side, 2, token=RoxeSendData.user_login_token_b
        )

        # 选择wallet支付
        order_id = pay_info["data"]["orderId"]
        self.rps_client.submitPayOrderTransferToRoxeAccount(from_ro_id, to_ro_id, amount, businessType="transfer", expect_pay_success=False, businessOrderNo=order_id)
        self.waitOrderStatusInDB(order_id, "Processing")

        notifications_2 = self.client.listNotification()
        self.checkCodeMessage(notifications_2)
        self.assertEqual(notifications_2["data"], notifications["data"], "支付中的订单不会发送通知")

        self.waitOrderStatusInDB(order_id)

        notifications_3 = self.client.listNotification()
        self.checkCodeMessage(notifications_3)
        self.checkNotifications(notifications_3["data"], RoxeSendData.user_id)
        self.assertEqual(len(notifications_3["data"]), len(notifications["data"]) + 1, "支付完成的订单没有发送通知")

        self.assertEqual(notifications_3["data"][0]["body"]["type"], "Receive_Complete")

    def test_053_listNotification_declineRequest(self):
        """
        查看交易通知列表, request业务，B发起request，A会收到通知, A拒绝，B会收到通知
        """
        notifications_from = self.client.listNotification()
        self.checkCodeMessage(notifications_from)
        self.checkNotifications(notifications_from["data"], RoxeSendData.user_id)

        notifications_to = self.client.listNotification(token=RoxeSendData.user_login_token_b)
        self.checkCodeMessage(notifications_to)
        self.checkNotifications(notifications_to["data"], RoxeSendData.user_id_b)

        pay_info, re_body = self.client.request(RoxeSendData.user_id_b, RoxeSendData.currency[0], 4.35, "hello")
        order_id = pay_info["data"]["orderId"]
        # B查询到的request订单
        tx_his, tx_body = self.client.getTransactionHistory(token=RoxeSendData.user_login_token_b)

        notifications_from_2 = self.client.listNotification()
        self.checkCodeMessage(notifications_from_2)
        self.assertEqual(notifications_from_2["data"], notifications_from["data"], "支付中的订单不会发送通知")
        notifications_to_2 = self.client.listNotification(token=RoxeSendData.user_login_token_b)
        self.checkCodeMessage(notifications_to_2)
        self.checkNotifications(notifications_to_2["data"], RoxeSendData.user_id_b)
        self.assertEqual(len(notifications_to_2["data"]), len(notifications_to["data"]) + 1, "支付中的订单不会发送通知")
        self.assertEqual(notifications_to_2["data"][0]["body"]["type"], "Request_New")
        self.assertEqual(notifications_to_2["data"][0]["body"]["transactionId"], tx_his["data"]["data"][0]["transactionId"])

        # 拒绝支付交易
        decline_info = self.client.declineRequest(order_id, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(decline_info)
        self.assertTrue(decline_info["data"])

        notifications_from_3 = self.client.listNotification()
        self.checkCodeMessage(notifications_from_3)
        self.checkNotifications(notifications_from_3["data"], RoxeSendData.user_id)
        self.assertEqual(len(notifications_from_3["data"]), len(notifications_from["data"]) + 1, "支付中的订单不会发送通知")
        self.assertEqual(notifications_from_3["data"][0]["body"]["type"], "Request_Decline")
        self.assertEqual(notifications_from_3["data"][0]["body"]["transactionId"], pay_info["data"]["transactionId"])

        notifications_to_3 = self.client.listNotification(token=RoxeSendData.user_login_token_b)
        self.checkCodeMessage(notifications_to_3)
        self.checkNotifications(notifications_to_3["data"], RoxeSendData.user_id_b)
        self.assertEqual(len(notifications_to_3["data"]), len(notifications_to_2["data"]), "支付中的订单不会发送通知")

    def test_054_listNotification_cancelRequest(self):
        """
        查看交易通知列表, request业务，B发起request，A会收到通知, B撤销请求，双方不会收到通知
        """
        notifications_from = self.client.listNotification()
        self.checkCodeMessage(notifications_from)
        self.checkNotifications(notifications_from["data"], RoxeSendData.user_id)

        notifications_to = self.client.listNotification(token=RoxeSendData.user_login_token_b)
        self.checkCodeMessage(notifications_to)
        self.checkNotifications(notifications_to["data"], RoxeSendData.user_id_b)

        pay_info, re_body = self.client.request(RoxeSendData.user_id_b, RoxeSendData.currency[0], 4.35, "hello")
        tx_id = pay_info["data"]["transactionId"]
        # B查询到的request订单
        tx_his, tx_body = self.client.getTransactionHistory(token=RoxeSendData.user_login_token_b)

        notifications_from_2 = self.client.listNotification()
        self.checkCodeMessage(notifications_from_2)
        self.assertEqual(notifications_from_2["data"], notifications_from["data"], "支付中的订单不会发送通知")
        notifications_to_2 = self.client.listNotification(token=RoxeSendData.user_login_token_b)
        self.checkCodeMessage(notifications_to_2)
        self.checkNotifications(notifications_to_2["data"], RoxeSendData.user_id_b)
        self.assertEqual(len(notifications_to_2["data"]), len(notifications_to["data"]) + 1, "支付中的订单不会发送通知")
        self.assertEqual(notifications_to_2["data"][0]["body"]["type"], "Request_New")
        self.assertEqual(notifications_to_2["data"][0]["body"]["transactionId"], tx_his["data"]["data"][0]["transactionId"])

        # 撤销交易
        cancel_info = self.client.cancelTransaction(tx_id)
        self.checkCodeMessage(cancel_info)
        self.assertTrue(cancel_info["data"])

        notifications_from_3 = self.client.listNotification()
        self.checkCodeMessage(notifications_from_3)
        self.checkNotifications(notifications_from_3["data"], RoxeSendData.user_id)
        self.assertEqual(len(notifications_from_3["data"]), len(notifications_from["data"]), "撤销的订单不会发送通知")

        notifications_to_3 = self.client.listNotification(token=RoxeSendData.user_login_token_b)
        self.checkCodeMessage(notifications_to_3)
        self.checkNotifications(notifications_to_3["data"], RoxeSendData.user_id_b)
        self.assertEqual(len(notifications_to_3["data"]), len(notifications_to_2["data"]), "撤销的订单不会发送通知")

    def test_055_listNotification_payRequest(self):
        """
        查看交易通知列表, request业务，B发起request，A会收到通知, A支付，支付完成后，B会收到通知
        """
        notifications_from = self.client.listNotification()
        self.checkCodeMessage(notifications_from)
        self.checkNotifications(notifications_from["data"], RoxeSendData.user_id)

        notifications_to = self.client.listNotification(token=RoxeSendData.user_login_token_b)
        self.checkCodeMessage(notifications_to)
        self.checkNotifications(notifications_to["data"], RoxeSendData.user_id_b)

        currency = RoxeSendData.currency[0]
        amount = 5.36
        pay_info, re_body = self.client.request(RoxeSendData.user_id_b, currency, amount, "hello")
        # B查询到的request订单
        tx_his, tx_body = self.client.getTransactionHistory(token=RoxeSendData.user_login_token_b)
        tx_id_b = tx_his["data"]["data"][0]["transactionId"]

        notifications_from_2 = self.client.listNotification()
        self.checkCodeMessage(notifications_from_2)
        self.assertEqual(notifications_from_2["data"], notifications_from["data"], "支付中的订单不会发送通知")
        notifications_to_2 = self.client.listNotification(token=RoxeSendData.user_login_token_b)
        self.checkCodeMessage(notifications_to_2)
        self.checkNotifications(notifications_to_2["data"], RoxeSendData.user_id_b)
        self.assertEqual(len(notifications_to_2["data"]), len(notifications_to["data"]) + 1, "支付中的订单不会发送通知")
        self.assertEqual(notifications_to_2["data"][0]["body"]["type"], "Request_New")
        self.assertEqual(notifications_to_2["data"][0]["body"]["transactionId"], tx_id_b)

        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_REQUEST.value
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount)
        # 另外一方进行支付
        pay_request, pay_body = self.client.payRequest(
            tx_id_b, RoxeSendData.user_account, rate_info["data"]["exchangeRate"], currency,
            rate_info["data"]["sendAmount"], currency, rate_info["data"]["receiveAmount"],
            2, "pay request", RoxeSendData.user_login_token_b
        )
        # 选择wallet支付
        order_id = pay_request["data"]["orderId"]
        pay_amount = ApiUtils.parseNumberDecimal(float(rate_info["data"]["sendAmount"]))
        self.rps_client.submitPayOrderTransferToRoxeAccount(RoxeSendData.user_account_b, RoxeSendData.user_account, pay_amount, businessType="transfer", expect_pay_success=False, businessOrderNo=order_id)
        self.waitOrderStatusInDB(order_id, "Processing")

        notifications_from_3 = self.client.listNotification()
        self.checkCodeMessage(notifications_from_3)
        self.checkNotifications(notifications_from_3["data"], RoxeSendData.user_id)
        self.assertEqual(len(notifications_from_3["data"]), len(notifications_from["data"]), "支付中的订单不会发送通知")

        notifications_to_3 = self.client.listNotification(token=RoxeSendData.user_login_token_b)
        self.checkCodeMessage(notifications_to_3)
        self.checkNotifications(notifications_to_3["data"], RoxeSendData.user_id_b)

        self.waitOrderStatusInDB(order_id)

        notifications_from_4 = self.client.listNotification()
        self.checkCodeMessage(notifications_from_4)
        self.checkNotifications(notifications_from_4["data"], RoxeSendData.user_id)
        self.assertEqual(len(notifications_from_4["data"]), len(notifications_from["data"]) + 1, "支付完成的订单会发送通知")
        self.assertEqual(notifications_from_4["data"][0]["body"]["type"], "Request_Complete")
        self.assertEqual(notifications_from_4["data"][0]["body"]["transactionId"], pay_info["data"]["transactionId"])

        notifications_to_4 = self.client.listNotification(token=RoxeSendData.user_login_token_b)
        self.checkCodeMessage(notifications_to_4)
        self.checkNotifications(notifications_to_4["data"], RoxeSendData.user_id_b)

    def test_056_deleteAchAccount(self):
        """
        删除ach账户, 删除后查询为空
        """
        currency = RoxeSendData.currency[0]
        accounts = self.client.getAccountList(currency)
        if len(accounts["data"]) == 0:
            self.rps_client.bindAndVerifyAchAccount(RPSData.ach_account)
            accounts = self.client.getAccountList(currency)
        ach_id = accounts["data"][0]["id"]
        delete_info = self.client.deleteAccountById(ach_id)
        self.checkCodeMessage(delete_info)
        self.assertTrue(delete_info["data"])
        accounts = self.client.getAccountList(currency)
        self.assertEqual(accounts["data"], [], "删除后获取账户应为空")

    def test_057_getAchAccount_notBindAccount(self):
        """
        查询ach账号，未绑定ach
        """
        self.rps_client.deleteAchAccountFromDB(self, RoxeSendData.user_id)
        currency = RoxeSendData.currency[0]
        accounts = self.client.getAccountList(currency)
        self.checkCodeMessage(accounts)
        self.assertEqual(accounts["data"], [], "获取账户应为空")

    def test_058_getAchAccount_bindAccount(self):
        """
        查询ach账号，绑定ach
        """
        self.rps_client.deleteAchAccountFromDB(self, RoxeSendData.user_id)
        currency = RoxeSendData.currency[0]
        account_id = self.rps_client.bindAndVerifyAchAccount(RPSData.ach_account)
        accounts = self.client.getAccountList(currency)
        self.checkCodeMessage(accounts)

        self.assertEqual(len(accounts["data"]), 1)
        self.assertEqual(accounts["data"][0]["id"], account_id)

    """
    异常场景
    """
    def test_059_listCurrency_tokenIsError(self):
        """
        查询币种列表, 传入错误的token
        """
        currency_info = self.client.listCurrency("abc")
        self.checkCodeMessage(currency_info)
        self.assertTrue(len(currency_info["data"]) > 0)
        if RoxeSendData.is_check_db:
            sql = f"select * from ro_currency where state=0"
            currency_db = self.mysql.exec_sql_query(sql)
            for c_info in currency_info["data"]:
                c_db = [i for i in currency_db if i["currency"] == c_info["currency"]]
                self.assertEqual(len(c_db), 1, f"数据库中未找到{c_info['currency']}的币种信息: {currency_db}")
                for key, value in c_info.items():
                    if key == "settlementDate":
                        self.assertEqual(value, 0)
                    elif key == "jsonRemark":
                        self.assertEqual(value, json.loads(c_db[0][key]), f"{key}和数据库校验不一致: {c_db[0][key]}")
                    else:
                        self.assertEqual(value, c_db[0][key], f"{key}和数据库校验不一致: {c_db[0][key]}")

    def test_060_listCurrency_missingToken(self):
        """
        查询币种列表, 不传token
        """
        currency_info = self.client.listCurrency(RoxeSendData.user_login_token, pop_header="token")
        self.checkCodeMessage(currency_info)
        self.assertTrue(len(currency_info["data"]) > 0)
        if RoxeSendData.is_check_db:
            sql = f"select * from ro_currency where state=0"
            currency_db = self.mysql.exec_sql_query(sql)
            for c_info in currency_info["data"]:
                c_db = [i for i in currency_db if i["currency"] == c_info["currency"]]
                self.assertEqual(len(c_db), 1, f"数据库中未找到{c_info['currency']}的币种信息: {currency_db}")
                for key, value in c_info.items():
                    if key == "settlementDate":
                        self.assertEqual(value, 0)
                    elif key == "jsonRemark":
                        self.assertEqual(value, json.loads(c_db[0][key]), f"{key}和数据库校验不一致: {c_db[0][key]}")
                    else:
                        self.assertEqual(value, c_db[0][key], f"{key}和数据库校验不一致: {c_db[0][key]}")

    def test_061_getExchangeRate_tokenIsError(self):
        """
        币种汇率, token错误
        """
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, 10.23, token="token")
        self.checkCodeMessage(rate_info)
        self.checkExchangeRate(rate_info["data"], r_params)

    def test_062_getExchangeRate_missingToken(self):
        """
        币种汇率, 不传token
        """
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, 10.23, pop_header="token")
        self.checkCodeMessage(rate_info)
        self.checkExchangeRate(rate_info["data"], r_params)

    def test_063_getExchangeRate_currencyNotSupport(self):
        """
        币种汇率, 传入不支持的币种: CNY
        """
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        rate_info, r_params = self.client.getExchangeRate(currency, "CNY", b_type, ensure_side, 10.23)
        self.checkCodeMessage(rate_info, "RSD10001", "Illegal to: CNY")
        self.assertIsNone(rate_info["data"])

        rate_info, r_params = self.client.getExchangeRate("CNY", currency, b_type, ensure_side, 10.23)
        self.checkCodeMessage(rate_info, "RSD10001", "Illegal from: CNY")
        self.assertIsNone(rate_info["data"])

    def test_064_getExchangeRate_currencyLowerCase(self):
        """
        币种汇率, 币种小写
        """
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        rate_info, r_params = self.client.getExchangeRate(currency.lower(), currency, b_type, ensure_side, 10.23)
        self.checkCodeMessage(rate_info, "RSD10001", f"Illegal from: {currency.lower()}")
        self.assertIsNone(rate_info["data"])

        rate_info, r_params = self.client.getExchangeRate(currency, currency.lower(), b_type, ensure_side, 10.23)
        self.checkCodeMessage(rate_info, "RSD10001", f"Illegal to: {currency.lower()}")
        self.assertIsNone(rate_info["data"])

    def test_065_getExchangeRate_currencyMixerCase(self):
        """
        币种汇率, 币种大小写混合
        """
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        rate_info, r_params = self.client.getExchangeRate(currency.title(), currency, b_type, ensure_side, 10.23)
        self.checkCodeMessage(rate_info, "RSD10001", f"Illegal from: {currency.title()}")
        self.assertIsNone(rate_info["data"])

        rate_info, r_params = self.client.getExchangeRate(currency, currency.title(), b_type, ensure_side, 10.23)
        self.checkCodeMessage(rate_info, "RSD10001", f"Illegal to: {currency.title()}")
        self.assertIsNone(rate_info["data"])

    def test_066_getExchangeRate_typeIsError(self):
        """
        币种汇率, 业务类型错误
        """
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value + "abc"
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, 10.23)
        self.checkCodeMessage(rate_info, "RMS10002", "ServerError")
        self.assertIsNone(rate_info["data"])

    def test_067_getExchangeRate_ensureSideIsError(self):
        """
        币种汇率, ensureSide错误
        """
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value + "ABC"
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, 10.23)
        self.checkCodeMessage(rate_info, "RMS10002", "ServerError")
        self.assertIsNone(rate_info["data"])

    def test_068_getExchangeRate_bothGiveFromAmountAndToAmount(self):
        """
        币种汇率, 同时给出fromAmount和toAmount
        """
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, 10.23, 12)
        self.checkCodeMessage(rate_info, "RSD10001", "only one amount")
        self.assertIsNone(rate_info["data"])

    def test_069_getExchangeRate_amountIllegal(self):
        """
        币种汇率, 数量非法: 0, 负数，字母，小数后超过2位
        """
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, 0)
        self.checkCodeMessage(rate_info)
        self.checkExchangeRate(rate_info["data"], r_params)

        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, -1)
        self.checkCodeMessage(rate_info)
        self.assertIsNotNone(rate_info["data"])

        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, "abc")
        self.checkCodeMessage(rate_info, "RMS10002", "ServerError")
        self.assertIsNone(rate_info["data"])

    def test_070_getExchangeRate_countryNotMatchCurrency(self):
        """
        币种汇率, 国家和币种不匹配：USD时国家传CN
        """
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, 12, from_country="CN")
        self.checkCodeMessage(rate_info, "RSD10501", "Transfers in this currency are not supported")
        self.assertIsNone(rate_info["data"])

        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, 12, to_country="CN")
        self.checkCodeMessage(rate_info)
        self.assertIsNotNone(rate_info["data"])

    def test_071_getExchangeRate_outNodeError(self):
        """
        币种汇率, 出金节点错误
        """
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, 12, outer_node_roxe="CN")
        self.checkCodeMessage(rate_info, "RSD10501", "Transfers in this currency are not supported")
        self.assertIsNone(rate_info["data"])

    def test_072_getExchangeRate_missingCurrency(self):
        """
        币种汇率, 缺少币种
        """
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, 12, pop_param="from")
        self.checkCodeMessage(rate_info, "RMS10001", "Required String parameter 'from' is not present")
        self.assertIsNone(rate_info["data"])

        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, 12, pop_param="to")
        self.checkCodeMessage(rate_info, "RMS10001", "Required String parameter 'to' is not present")
        self.assertIsNone(rate_info["data"])

    def test_073_getExchangeRate_missingType(self):
        """
        币种汇率, 缺少业务类型
        """
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, 12, pop_param="type")
        self.checkCodeMessage(rate_info)
        self.assertIsNotNone(rate_info["data"])

    def test_074_getExchangeRate_bothNotGiveFromAmountAndToAmount(self):
        """
        币种汇率, fromAmount和toAmount都不传
        """
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side)
        self.checkCodeMessage(rate_info, "RSD10001", "only one amount")
        self.assertIsNone(rate_info["data"])

    def test_075_listReceiverAccount_tokenError(self):
        """
        列出收款人账户，token错误
        """
        r_accounts = self.client.listReceiverAccount(RoxeSendData.currency[0], token="abc")
        self.checkCodeMessage(r_accounts, "RUC200001", "Token exception")
        self.assertIsNone(r_accounts["data"])

    def test_076_listReceiverAccount_missingToken(self):
        """
        列出收款人账户，不传token
        """
        r_accounts = self.client.listReceiverAccount(RoxeSendData.currency[0], pop_header="token")
        self.checkCodeMessage(r_accounts, "RUC100002", "token is empty")
        self.assertIsNone(r_accounts["data"])

    def test_077_listReceiverAccount_currencyNotSupport(self):
        """
        列出收款人账户，币种不支持
        """
        r_accounts = self.client.listReceiverAccount("CNY")
        self.checkCodeMessage(r_accounts)
        self.assertEqual(r_accounts["data"], [])

    def test_078_listReceiverAccount_currencyLowerCase(self):
        """
        列出收款人账户，币种小写
        """
        r_accounts = self.client.listReceiverAccount(RoxeSendData.currency[0].lower())
        self.checkCodeMessage(r_accounts)
        self.assertEqual(r_accounts["data"], [])

    def test_079_listReceiverAccount_currencyMixerCase(self):
        """
        列出收款人账户，币种大小写混合
        """
        r_accounts = self.client.listReceiverAccount(RoxeSendData.currency[0].title())
        self.checkCodeMessage(r_accounts)
        self.assertEqual(r_accounts["data"], [])

    def test_080_listReceiverAccount_accountTypeError(self):
        """
        列出收款人账户，账户类型错误
        """
        r_accounts = self.client.listReceiverAccount(RoxeSendData.currency[0], b_type="abc")
        self.checkCodeMessage(r_accounts, "RMS10002", "ServerError")
        self.assertIsNone(r_accounts["data"])

    def test_081_bindReceiverAccount_tokenError(self):
        """
        绑定收款人账户，token错误
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        bind_res, r_body = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_1, rate_info["data"]["outerNodeCode"], token=RoxeSendData.user_login_token.replace("e", "a"))
        self.checkCodeMessage(bind_res, "RUC200001", "Token exception")
        self.assertIsNone(bind_res["data"])

    def test_082_bindReceiverAccount_missingToken(self):
        """
        绑定收款人账户，header中缺少token
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        bind_res, r_body = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_1, rate_info["data"]["outerNodeCode"], pop_header="token")
        self.checkCodeMessage(bind_res, "RUC100002", "token is empty")
        self.assertIsNone(bind_res["data"])

    def test_083_bindReceiverAccount_currencyNotSupport(self):
        """
        绑定收款人账户，currency为不支持的币种: CNY
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        bind_res, r_body = self.client.bindReceiverAccount("CNY", RoxeSendData.user_outer_bank_1, rate_info["data"]["outerNodeCode"])
        self.checkCodeMessage(bind_res, "RSD10001", "Parameter error: Currency not supported")
        self.assertIsNone(bind_res["data"])

    def test_084_bindReceiverAccount_currencyLowerCase(self):
        """
        绑定收款人账户，currency小写
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        bind_res, r_body = self.client.bindReceiverAccount(currency.lower(), RoxeSendData.user_outer_bank_1, rate_info["data"]["outerNodeCode"])
        self.checkCodeMessage(bind_res)
        self.checkBindReceiverAccount(bind_res["data"], r_body, RoxeSendData.user_id)

        r_accounts = self.client.listReceiverAccount(currency.lower())
        self.checkCodeMessage(r_accounts)
        self.checkListReceiverAccount(r_accounts["data"], RoxeSendData.user_id)
        self.checkBindAccountWithListReceiverAccount(bind_res["data"], r_accounts["data"])

    def test_085_bindReceiverAccount_currencyMixerCase(self):
        """
        绑定收款人账户，currency大小写混合
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        bind_res, r_body = self.client.bindReceiverAccount(currency.title(), RoxeSendData.user_outer_bank_1, rate_info["data"]["outerNodeCode"])
        self.checkCodeMessage(bind_res)
        self.checkBindReceiverAccount(bind_res["data"], r_body, RoxeSendData.user_id)

        r_accounts = self.client.listReceiverAccount(currency.title())
        self.checkCodeMessage(r_accounts)
        self.checkListReceiverAccount(r_accounts["data"], RoxeSendData.user_id)
        self.checkBindAccountWithListReceiverAccount(bind_res["data"], r_accounts["data"])

    def test_086_bindReceiverAccount_accountTypeError(self):
        """
        绑定收款人账户，账户类型错误
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        bind_res, r_body = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_1, rate_info["data"]["outerNodeCode"], "abc")
        self.checkCodeMessage(bind_res, "RMS10001", "Missing request body")
        self.assertIsNone(bind_res["data"])

    def test_087_bindReceiverAccount_nodeCodeError(self):
        """
        绑定收款人账户，节点错误
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        bind_res, r_body = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_1, rate_info["data"]["outerNodeCode"] + "abc")
        self.checkCodeMessage(bind_res)
        self.assertIsNotNone(bind_res["data"])

    def test_088_bindReceiverAccount_missingParams(self):
        """
        绑定收款人账户，缺少参数
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        mis_params = ["currency", "type", "bankAccount", "outerNodeCode"]
        for m_p in mis_params:
            bind_res, r_body = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_1, rate_info["data"]["outerNodeCode"], pop_param=m_p)
            msg = "Parameter error: currency is empty"
            if m_p != "currency":
                msg = m_p + "is required"
            self.checkCodeMessage(bind_res, "RSD10001", msg)
            self.assertIsNone(bind_res["data"])

    def test_089_bindReceiverAccount_bankAccountMissingParams(self):
        """
        绑定收款人账户，收款人账户缺少必填的字段信息
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        mis_params = [i for i in RoxeSendData.user_outer_bank_1.keys() if i != "bankName"]
        for m_p in mis_params:
            bank_account = RoxeSendData.user_outer_bank_1.copy()
            bank_account.pop(m_p)
            self.client.logger.info(f"银行账户缺少: {m_p}")
            bind_res, r_body = self.client.bindReceiverAccount(currency, bank_account, rate_info["data"]["outerNodeCode"])
            msg = m_p + "is required"
            self.checkCodeMessage(bind_res, "RSD10001", msg)
            self.assertIsNone(bind_res["data"])

    def test_090_bindReceiverAccount_bankAccountHasBind(self):
        """
        绑定收款人账户，绑定的银行卡账户以及被绑定
        """
        # 清理绑定的收款人账户
        self.client.deleteReceiverAccountFromDB(self)
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        # 第一次绑定收款人账户
        bind_res, r_body = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_1, rate_info["data"]["outerNodeCode"])
        self.checkCodeMessage(bind_res)
        self.checkBindReceiverAccount(bind_res["data"], r_body, RoxeSendData.user_id)

        r_accounts = self.client.listReceiverAccount(currency)
        self.checkCodeMessage(r_accounts)
        self.checkListReceiverAccount(r_accounts["data"], RoxeSendData.user_id)
        self.checkBindAccountWithListReceiverAccount(bind_res["data"], r_accounts["data"])

        # 绑定已绑的银行卡
        bind_res, r_body = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_1, rate_info["data"]["outerNodeCode"])
        self.checkCodeMessage(bind_res)
        self.checkBindReceiverAccount(bind_res["data"], r_body, RoxeSendData.user_id)

        r_accounts = self.client.listReceiverAccount(currency)
        self.checkCodeMessage(r_accounts)

    def test_091_deleteReceiverAccount_tokenError(self):
        """
        删除收款人账户，token错误
        """
        currency = RoxeSendData.currency[0]
        r_accounts = self.client.listReceiverAccount(currency)
        if r_accounts["data"]:
            account_id = r_accounts["data"][0]["accountId"]
        else:
            rate_info, r_params = self.client.getExchangeRate(
                currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
            )
            bind_res, r_body = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_1, rate_info["data"]["outerNodeCode"], token=RoxeSendData.user_login_token.replace("e", "a"))
            account_id = bind_res["data"]["accountId"]
        delete_res = self.client.deleteReceiverAccount(account_id, token=RoxeSendData.user_login_token.replace("e", "a"))
        self.checkCodeMessage(delete_res, "RUC200001", "Token exception")
        self.assertIsNone(delete_res["data"])

    def test_092_deleteReceiverAccount_missingToken(self):
        """
        删除收款人账户，header中缺少token
        """
        currency = RoxeSendData.currency[0]
        r_accounts = self.client.listReceiverAccount(currency)
        if r_accounts["data"]:
            account_id = r_accounts["data"][0]["accountId"]
        else:
            rate_info, r_params = self.client.getExchangeRate(
                currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
            )
            bind_res, r_body = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_1, rate_info["data"]["outerNodeCode"], token=RoxeSendData.user_login_token.replace("e", "a"))
            account_id = bind_res["data"]["accountId"]
        delete_res = self.client.deleteReceiverAccount(account_id, pop_header="token")
        self.checkCodeMessage(delete_res, "RUC100002", "token is empty")
        self.assertIsNone(delete_res["data"])

    def test_093_deleteReceiverAccount_accountIdNotExist(self):
        """
        删除收款人账户，accountId不存在
        """
        currency = RoxeSendData.currency[0]
        r_accounts = self.client.listReceiverAccount(currency)
        if r_accounts["data"]:
            account_id = r_accounts["data"][0]["accountId"]
        else:
            rate_info, r_params = self.client.getExchangeRate(
                currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
            )
            bind_res, r_body = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_1, rate_info["data"]["outerNodeCode"], token=RoxeSendData.user_login_token.replace("e", "a"))
            account_id = bind_res["data"]["accountId"]
        delete_res = self.client.deleteReceiverAccount(account_id - 1)
        self.checkCodeMessage(delete_res, "RSD10001", "accountis required")
        self.assertIsNone(delete_res["data"])

    def test_094_deleteReceiverAccount_accountIdNotBelongUser(self):
        """
        删除收款人账户，accountId不属于当前用户
        """
        currency = RoxeSendData.currency[0]
        r_accounts = self.client.listReceiverAccount(currency)
        if r_accounts["data"]:
            account_id = r_accounts["data"][0]["accountId"]
        else:
            rate_info, r_params = self.client.getExchangeRate(
                currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
            )
            bind_res, r_body = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_1, rate_info["data"]["outerNodeCode"], token=RoxeSendData.user_login_token.replace("e", "a"))
            account_id = bind_res["data"]["accountId"]
        delete_res = self.client.deleteReceiverAccount(account_id, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(delete_res, "RSD10001", "Illegal request!The resource does not belong to you!")
        self.assertIsNone(delete_res["data"])

    def test_095_queryOuterMethod_tokenError(self):
        """
        查询出金方式, 需要先查询汇率得到出金节点, token错误
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        method_info = self.client.getOuterMethod(currency, rate_info["data"]["outerNodeCode"], token=RoxeSendData.user_login_token.replace("e", "a"))
        self.checkCodeMessage(method_info, "RUC200001", "Token exception")
        self.assertIsNone(method_info["data"])

    def test_096_queryOuterMethod_missingToken(self):
        """
        查询出金方式, 需要先查询汇率得到出金节点, token不传
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        method_info = self.client.getOuterMethod(currency, rate_info["data"]["outerNodeCode"], pop_header="token")
        self.checkCodeMessage(method_info, "RUC100002", "token is empty")
        self.assertIsNone(method_info["data"])

    def test_097_queryOuterMethod_currencyNotSupport(self):
        """
        查询出金方式, 币种不支持
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        method_info = self.client.getOuterMethod("CNY", rate_info["data"]["outerNodeCode"])
        self.checkCodeMessage(method_info, "RSD10001", "Unknown error")
        self.assertIsNone(method_info["data"])

    def test_098_queryOuterMethod_currencyLowerCase(self):
        """
        查询出金方式, 币种小写
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        method_info = self.client.getOuterMethod(currency.lower(), rate_info["data"]["outerNodeCode"])
        self.checkCodeMessage(method_info)
        self.assertEqual(method_info["data"], ["BANK"])

    def test_099_queryOuterMethod_currencyMixerCase(self):
        """
        查询出金方式, 币种大小写混合
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        method_info = self.client.getOuterMethod(currency.title(), rate_info["data"]["outerNodeCode"])
        self.checkCodeMessage(method_info)
        self.assertEqual(method_info["data"], ["BANK"])

    def test_100_queryOuterMethod_nodeCodeError(self):
        """
        查询出金方式, 出金节点错误
        """
        method_info = self.client.getOuterMethod(RoxeSendData.currency[0], "abc")
        self.checkCodeMessage(method_info, "RSD10001", "Unknown error")
        self.assertIsNone(method_info["data"])

    def test_101_queryOuterMethod_missingParams(self):
        """
        查询出金方式, 不传参数：currency或者出金节点
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        method_info = self.client.getOuterMethod(currency, rate_info["data"]["outerNodeCode"], pop_param="currency")
        self.checkCodeMessage(method_info, "RMS10001", "Required String parameter 'currency' is not present")
        self.assertIsNone(method_info["data"])

        method_info = self.client.getOuterMethod(currency, rate_info["data"]["outerNodeCode"], pop_param="outerNodeRxoe")
        self.checkCodeMessage(method_info, "RSD10001", "Parameter error: outerNodeRoxe is empty")
        self.assertIsNone(method_info["data"])

    def test_102_queryOuterFields_tokenError(self):
        """
        查询出金必填字段, token错误
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        fields = self.client.getOuterFields(currency, outer_node=rate_info["data"]["outerNodeCode"], token="abc")
        self.checkCodeMessage(fields, "RUC200001", "Token exception")
        self.assertIsNone(fields["data"])

    def test_103_queryOuterFields_missingToken(self):
        """
        查询出金必填字段, token不传
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        fields = self.client.getOuterFields(currency, outer_node=rate_info["data"]["outerNodeCode"], pop_header="token")
        self.checkCodeMessage(fields, "RUC100002", "token is empty")
        self.assertIsNone(fields["data"])

    def test_104_queryOuterFields_currencyNotSupport(self):
        """
        查询出金必填字段, currency为不支持的币种
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        fields = self.client.getOuterFields("CNY", outer_node=rate_info["data"]["outerNodeCode"])
        self.checkCodeMessage(fields)
        self.assertIsNone(fields["data"])

    def test_105_queryOuterFields_currencyLowerCase(self):
        """
        查询出金必填字段, 币种小写
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        fields = self.client.getOuterFields(currency.lower(), outer_node=rate_info["data"]["outerNodeCode"])
        self.checkCodeMessage(fields)
        self.assertEqual(fields["data"], RSSData.manual_bank_fields)

    def test_106_queryOuterFields_currencyMixerCase(self):
        """
        查询出金必填字段, 币种大小写混合
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        fields = self.client.getOuterFields(currency.title(), outer_node=rate_info["data"]["outerNodeCode"])
        self.checkCodeMessage(fields)
        self.assertEqual(fields["data"], RSSData.manual_bank_fields)

    def test_107_queryOuterFields_nodeCodeError(self):
        """
        查询出金必填字段, 出金节点错误
        """
        currency = RoxeSendData.currency[0]
        fields = self.client.getOuterFields(currency, outer_node="abc")
        self.checkCodeMessage(fields)
        self.assertIsNone(fields["data"])

    def test_108_queryOuterFields_outMethodError(self):
        """
        查询出金必填字段, 出金方式错误
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        fields = self.client.getOuterFields(currency, "abc", outer_node=rate_info["data"]["outerNodeCode"])
        self.checkCodeMessage(fields, "RSD10001", "Calling settlement node error")
        self.assertIsNone(fields["data"])

    def test_109_queryOuterFields_missingParams(self):
        """
        查询出金必填字段, 缺少参数
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        mis_params = ["currency", "outerNodeRxoe", "payOutMethod"]
        for m_p in mis_params:
            self.client.logger.info(f"不传参数: {m_p}")
            fields = self.client.getOuterFields(currency, outer_node=rate_info["data"]["outerNodeCode"], pop_param=m_p)
            if m_p == "currency":
                code = "RMS10001"
                msg = "Required String parameter 'currency' is not present"
            elif m_p == "outerNodeRxoe":
                code = "RSD10001"
                msg = "Parameter error: outerNodeRoxe is empty"
            else:
                code = "0"
                msg = "Success"

            self.checkCodeMessage(fields, code, msg)
            if code != "0":
                self.assertIsNone(fields["data"])
            else:
                # 如果前端不传出金方式, 后台默认为BANK类型
                self.assertEqual(fields["data"], RSSData.manual_bank_fields)

    def test_110_checkOuterFields_tokenError(self):
        """
        校验出金必填字段, token错误
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        check_fields = self.client.checkOuterFields(currency, RoxeSendData.user_outer_bank, rate_info["data"]["outerNodeCode"], token="abc")
        self.checkCodeMessage(check_fields, "RUC200001", "Token exception")
        self.assertIsNone(check_fields["data"])

    def test_111_checkOuterFields_missingToken(self):
        """
        校验出金必填字段, token不传
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        check_fields = self.client.checkOuterFields(currency, RoxeSendData.user_outer_bank, rate_info["data"]["outerNodeCode"], pop_header="token")
        self.checkCodeMessage(check_fields, "RUC100002", "token is empty")
        self.assertIsNone(check_fields["data"])

    def test_112_checkOuterFields_currencyNotSupport(self):
        """
        校验出金必填字段, 币种不支持
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        check_fields = self.client.checkOuterFields("CNY", RoxeSendData.user_outer_bank, rate_info["data"]["outerNodeCode"])
        self.checkCodeMessage(check_fields, "RSD10001", "Parameter error: Currency not supported")
        self.assertIsNone(check_fields["data"])

    def test_113_checkOuterFields_currencyLowerCase(self):
        """
        校验出金必填字段, 币种小写
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        check_fields = self.client.checkOuterFields(currency.lower(), RoxeSendData.user_outer_bank, rate_info["data"]["outerNodeCode"])
        self.checkCodeMessage(check_fields)
        self.assertTrue(check_fields["data"])

    def test_114_checkOuterFields_currencyMixerCase(self):
        """
        校验出金必填字段, 币种大小写混合
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        check_fields = self.client.checkOuterFields(currency.title(), RoxeSendData.user_outer_bank, rate_info["data"]["outerNodeCode"])
        self.checkCodeMessage(check_fields)
        self.assertTrue(check_fields["data"])

    def test_115_checkOuterFields_nodeCodeError(self):
        """
        校验出金必填字段, 出金节点错误
        """
        currency = RoxeSendData.currency[0]
        check_fields = self.client.checkOuterFields(currency, RoxeSendData.user_outer_bank, "abc")
        self.checkCodeMessage(check_fields)
        self.assertTrue(check_fields["data"])

    def test_116_checkOuterFields_outBankMissingField(self):
        """
        校验出金必填字段, 出金银行卡缺少必填字段
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        for m_f in RoxeSendData.user_outer_bank.keys():
            bank_info = RoxeSendData.user_outer_bank.copy()
            bank_info.pop(m_f)
            self.client.logger.info(f"出金银行卡缺少字段: {m_f}")
            check_fields = self.client.checkOuterFields(currency, bank_info, rate_info["data"]["outerNodeCode"])
            e_f = "recipient country"
            if m_f == "receiverFirstName":
                e_f = "receiver name"
            elif m_f == "routingNumber":
                e_f = "routing number"
            elif m_f == "accountNumber":
                e_f = "account number"
            elif m_f == "accountType":
                e_f = "receiver account type"
            elif m_f == "receiverCurrency":
                e_f = "receiver currency"
            elif m_f == "payOutMethod":
                e_f = "payout method"
            self.checkCodeMessage(check_fields, "RSD10001", f"Parameter error: Call bank error: {e_f} cannot be empty")
            self.assertIsNone(check_fields["data"])

    def test_117_checkOuterFields_missingParams(self):
        """
        校验出金必填字段, 缺少参数
        """
        currency = RoxeSendData.currency[0]
        rate_info, r_params = self.client.getExchangeRate(
            currency, currency, RoxeSendEnum.BUSINESS_TYPE_WITHDRAW.value, RoxeSendEnum.ENSURE_SIDE_INNER.value, 10.23
        )
        for m_p in ["outerNodeRoxe", "outerInfo", "currency"]:
            self.client.logger.info(f"缺少参数: {m_p}")
            check_fields = self.client.checkOuterFields(currency, RoxeSendData.user_outer_bank, rate_info["data"]["outerNodeCode"], pop_param=m_p)
            e_f = f"{m_p} is empty"
            if m_p == "outerInfo":
                e_f = "outerInfo is null"
            self.checkCodeMessage(check_fields, "RSD10001", f"Parameter error: {e_f}")
            self.assertIsNone(check_fields["data"])

    def test_118_queryAccountBalance_tokenError(self):
        """
        查询账户资产列表, token错误
        """
        balance_info = self.client.listBalance(token="abc")
        self.checkCodeMessage(balance_info, "RUC200001", "Token exception")
        self.assertIsNone(balance_info["data"])

    def test_119_queryAccountBalance_missingToken(self):
        """
        查询账户资产列表, token不传
        """
        balance_info = self.client.listBalance(pop_header="token")
        self.checkCodeMessage(balance_info, "RUC100002", "token is empty")
        self.assertIsNone(balance_info["data"])

    def test_120_queryAccountCurrencyBalance_tokenError(self):
        """
        查询账户币种资产, token错误
        """
        currency = RoxeSendData.currency[0]
        balance_info = self.client.listCurrencyBalance(currency, token="abc")
        self.checkCodeMessage(balance_info, "RUC200001", "Token exception")
        self.assertIsNone(balance_info["data"])

    def test_121_queryAccountCurrencyBalance_missingToken(self):
        """
        查询账户币种资产, token不传
        """
        currency = RoxeSendData.currency[0]
        balance_info = self.client.listCurrencyBalance(currency, pop_header="token")
        self.checkCodeMessage(balance_info, "RUC100002", "token is empty")
        self.assertIsNone(balance_info["data"])

    def test_122_queryAccountCurrencyBalance_currencyNotSupport(self):
        """
        查询账户币种资产, 币种不支持: CNY
        """
        balance_info = self.client.listCurrencyBalance("CNY")
        self.checkCodeMessage(balance_info, "RSD10001", "Illegal currency: CNY")
        self.assertIsNone(balance_info["data"])

    def test_123_queryAccountCurrencyBalance_currencyLowerCase(self):
        """
        查询账户币种资产, 币种小写
        """
        currency = RoxeSendData.currency[0]
        balance_info = self.client.listCurrencyBalance(currency.lower())
        self.checkCodeMessage(balance_info, "RSD10001", "Illegal currency: {}".format(currency.lower()))
        self.assertIsNone(balance_info["data"])

    def test_124_queryAccountCurrencyBalance_currencyMixerCase(self):
        """
        查询账户币种资产, 币种大小写混合
        """
        currency = RoxeSendData.currency[0]
        balance_info = self.client.listCurrencyBalance(currency.title())
        self.checkCodeMessage(balance_info, "RSD10001", "Illegal currency: {}".format(currency.title()))
        self.assertIsNone(balance_info["data"])

    def test_125_deposit_tokenError(self):
        """
        充值下单, token错误
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        user_balance = self.client.listCurrencyBalance(currency)
        deposit_info, re_body = self.client.deposit(currency, amount, token="abc")
        self.checkCodeMessage(deposit_info, "RUC200001", "Token exception")
        self.assertIsNone(deposit_info["data"])

        user_balance2 = self.client.listCurrencyBalance(currency)
        self.assertEqual(user_balance2, user_balance, "账户资产不正确")

    def test_126_deposit_missingToken(self):
        """
        充值下单, token不传
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        user_balance = self.client.listCurrencyBalance(currency)
        deposit_info, re_body = self.client.deposit(currency, amount, pop_header="token")
        self.checkCodeMessage(deposit_info, "RUC100002", "token is empty")
        self.assertIsNone(deposit_info["data"])

        user_balance2 = self.client.listCurrencyBalance(currency)
        self.assertEqual(user_balance2, user_balance, "账户资产不正确")

    def test_127_deposit_currencyNotSupport(self):
        """
        充值下单, 币种不支持: CNY
        """
        amount = 4.35
        user_balance = self.client.listBalance()
        deposit_info, re_body = self.client.deposit("CNY", amount)
        self.checkCodeMessage(deposit_info, "RSD10001", "Illegal from: CNY")
        self.assertIsNone(deposit_info["data"])

        user_balance2 = self.client.listBalance()
        self.assertEqual(user_balance, user_balance2)

    def test_128_deposit_currencyLowerCase(self):
        """
        充值下单, 币种小写
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        user_balance = self.client.listCurrencyBalance(currency)
        deposit_info, re_body = self.client.deposit(currency.lower(), amount)
        self.checkCodeMessage(deposit_info, "RSD10002", "ServerError")
        self.assertIsNone(deposit_info["data"])

        user_balance2 = self.client.listCurrencyBalance(currency)
        self.assertEqual(user_balance2, user_balance, "账户资产不正确")

    def test_129_deposit_currencyMixerCase(self):
        """
        充值下单, 币种大小写混合
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        user_balance = self.client.listCurrencyBalance(currency)
        deposit_info, re_body = self.client.deposit(currency.title(), amount)
        self.checkCodeMessage(deposit_info, "RSD10002", "ServerError")
        self.assertIsNone(deposit_info["data"])

        user_balance2 = self.client.listCurrencyBalance(currency)
        self.assertEqual(user_balance2, user_balance, "账户资产不正确")

    def test_130_deposit_amountIllegal(self):
        """
        充值下单, 金额不合法
        """
        currency = RoxeSendData.currency[0]
        user_balance = self.client.listCurrencyBalance(currency)
        deposit_info, re_body = self.client.deposit(currency, -1)
        self.checkCodeMessage(deposit_info, "PAY_RPS_652", "businessAmount cannot be null or less than or equal to 0")
        self.assertIsNone(deposit_info["data"])

        deposit_info, re_body = self.client.deposit(currency, 0)
        self.checkCodeMessage(deposit_info, "PAY_RPS_652", "businessAmount cannot be null or less than or equal to 0")
        self.assertIsNone(deposit_info["data"])

        deposit_info, re_body = self.client.deposit(currency, "0")
        self.checkCodeMessage(deposit_info, "PAY_RPS_652", "businessAmount cannot be null or less than or equal to 0")
        self.assertIsNone(deposit_info["data"])

        deposit_info, re_body = self.client.deposit(currency, 1.1234567)
        self.checkCodeMessage(deposit_info)
        self.assertIsNotNone(deposit_info["data"])

        user_balance2 = self.client.listCurrencyBalance(currency)
        self.assertEqual(user_balance2, user_balance, "账户资产不正确")

    def test_131_withdraw_tokenError(self):
        """
        提现, token错误
        """
        currency = RoxeSendData.currency[0]
        r_accounts = self.client.listReceiverAccount(currency)["data"]
        if len(r_accounts) == 0:
            bind_res, r_body = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_1, RTSData.node_code)
            out_account = bind_res
        else:
            out_account = r_accounts[0]
        amount = 6.35
        user_balance = self.client.listCurrencyBalance(currency)
        withdraw_info = self.client.withdraw(currency, amount, out_account["accountId"], RTSData.node_code, token="abc")
        self.checkCodeMessage(withdraw_info, "RUC200001", "Token exception")
        self.assertIsNone(withdraw_info["data"])
        user_balance2 = self.client.listCurrencyBalance(currency)
        self.client.logger.info(f"资产变化了: {user_balance2['data']['amount'] - user_balance['data']['amount']}")
        self.assertEqual(user_balance['data'], user_balance2['data'])

    def test_132_withdraw_missingToken(self):
        """
        提现, token不传
        """
        currency = RoxeSendData.currency[0]
        r_accounts = self.client.listReceiverAccount(currency)["data"]
        if len(r_accounts) == 0:
            bind_res, r_body = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_1, RTSData.node_code)
            out_account = bind_res
        else:
            out_account = r_accounts[0]
        amount = 6.35
        user_balance = self.client.listCurrencyBalance(currency)
        withdraw_info = self.client.withdraw(currency, amount, out_account["accountId"], RTSData.node_code, pop_header="token")
        self.checkCodeMessage(withdraw_info, "RUC100002", "token is empty")
        self.assertIsNone(withdraw_info["data"])
        user_balance2 = self.client.listCurrencyBalance(currency)
        self.client.logger.info(f"资产变化了: {user_balance2['data']['amount'] - user_balance['data']['amount']}")
        self.assertEqual(user_balance['data'], user_balance2['data'])

    def test_133_withdraw_currencyNotSupport(self):
        """
        提现, 币种不支持
        """
        currency = RoxeSendData.currency[0]
        r_accounts = self.client.listReceiverAccount(currency)["data"]
        if len(r_accounts) == 0:
            bind_res, r_body = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_1, RTSData.node_code)
            out_account = bind_res
        else:
            out_account = r_accounts[0]
        amount = 6.35
        user_balance = self.client.listCurrencyBalance(currency)
        withdraw_info = self.client.withdraw("CNY", amount, out_account["accountId"], RTSData.node_code)
        self.checkCodeMessage(withdraw_info, "RSD10001", "Illegal from: CNY")
        self.assertIsNone(withdraw_info["data"])

        user_balance2 = self.client.listCurrencyBalance(currency)
        self.client.logger.info(f"资产变化了: {user_balance2['data']['amount'] - user_balance['data']['amount']}")
        self.assertAlmostEqual(user_balance['data']['amount'] - user_balance2['data']['amount'], 0, delta=0.1**6)

    def test_134_withdraw_currencyLowerCase(self):
        """
        提现, 币种小写
        """
        currency = RoxeSendData.currency[0]
        r_accounts = self.client.listReceiverAccount(currency)["data"]
        if len(r_accounts) == 0:
            bind_res, r_body = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_1, RTSData.node_code)
            out_account = bind_res
        else:
            out_account = r_accounts[0]
        amount = 6.35
        user_balance = self.client.listCurrencyBalance(currency)
        withdraw_info = self.client.withdraw(currency.lower(), amount, out_account["accountId"], RTSData.node_code)
        self.checkCodeMessage(withdraw_info, "RSD10002", f"ServerError")
        self.assertIsNone(withdraw_info["data"])

        user_balance2 = self.client.listCurrencyBalance(currency)
        self.client.logger.info(f"资产变化了: {user_balance2['data']['amount'] - user_balance['data']['amount']}")
        self.assertAlmostEqual(user_balance['data']['amount'] - user_balance2['data']['amount'], 0, delta=0.1**6)

    def test_135_withdraw_currencyMixerCase(self):
        """
        提现, 币种大小写混合
        """
        currency = RoxeSendData.currency[0]
        r_accounts = self.client.listReceiverAccount(currency)["data"]
        if len(r_accounts) == 0:
            bind_res, r_body = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_1, RTSData.node_code)
            out_account = bind_res
        else:
            out_account = r_accounts[0]
        amount = 6.35
        user_balance = self.client.listCurrencyBalance(currency)
        withdraw_info = self.client.withdraw(currency.title(), amount, out_account["accountId"], RTSData.node_code)
        self.checkCodeMessage(withdraw_info, "RSD10002", f"ServerError")
        self.assertIsNone(withdraw_info["data"])

        user_balance2 = self.client.listCurrencyBalance(currency)
        self.client.logger.info(f"资产变化了: {user_balance2['data']['amount'] - user_balance['data']['amount']}")
        self.assertAlmostEqual(user_balance['data']['amount'] - user_balance2['data']['amount'], 0, delta=0.1**6)

    def test_136_withdraw_amountIllegal(self):
        """
        提现, 数量不合法
        """
        currency = RoxeSendData.currency[0]
        r_accounts = self.client.listReceiverAccount(currency)["data"]
        if len(r_accounts) == 0:
            bind_res, r_body = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_1, RTSData.node_code)
            out_account = bind_res
        else:
            out_account = r_accounts[0]
        user_balance = self.client.listCurrencyBalance(currency)
        withdraw_info = self.client.withdraw(currency, 0, out_account["accountId"], RTSData.node_code)
        self.checkCodeMessage(withdraw_info, "PAY_RPS_697", "amount invalid")
        self.assertIsNone(withdraw_info["data"])

        withdraw_info = self.client.withdraw(currency, -10, out_account["accountId"], RTSData.node_code)
        self.checkCodeMessage(withdraw_info, "PAY_RPS_697", "amount invalid")
        self.assertIsNone(withdraw_info["data"])

        withdraw_info = self.client.withdraw(currency, "abc", out_account["accountId"], RTSData.node_code)
        self.checkCodeMessage(withdraw_info, "RMS10001", "Missing request body")
        self.assertIsNone(withdraw_info["data"])

        withdraw_info = self.client.withdraw(currency, 0.01, out_account["accountId"], RTSData.node_code)
        self.checkCodeMessage(withdraw_info)
        self.assertIsNotNone(withdraw_info["data"])

        user_balance2 = self.client.listCurrencyBalance(currency)
        self.client.logger.info(f"资产变化了: {user_balance2['data']['amount'] - user_balance['data']['amount']}")
        self.assertAlmostEqual(user_balance['data']['amount'] - user_balance2['data']['amount'], 0.01, delta=0.1**6)

    def test_137_withdraw_amountIdIncorrect(self):
        """
        提现, 账户id不正确
        """
        currency = RoxeSendData.currency[0]
        r_accounts = self.client.listReceiverAccount(currency)["data"]
        if len(r_accounts) == 0:
            bind_res, r_body = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_1, RTSData.node_code)
            out_account = bind_res
        else:
            out_account = r_accounts[0]
        user_balance = self.client.listCurrencyBalance(currency)
        withdraw_info = self.client.withdraw(currency, 10, out_account["accountId"] + 100, RTSData.node_code)
        self.checkCodeMessage(withdraw_info, "RSD10002", "ServerError")
        self.assertIsNone(withdraw_info["data"])

        user_balance2 = self.client.listCurrencyBalance(currency)
        self.client.logger.info(f"资产变化了: {user_balance2['data']['amount'] - user_balance['data']['amount']}")
        self.assertAlmostEqual(user_balance['data']['amount'] - user_balance2['data']['amount'], 0, delta=0.1**6)

    def test_138_withdraw_nodeCodeIncorrect(self):
        """
        提现, 出金节点不正确
        """
        currency = RoxeSendData.currency[0]
        r_accounts = self.client.listReceiverAccount(currency)["data"]
        if len(r_accounts) == 0:
            bind_res, r_body = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_1, RTSData.node_code)
            out_account = bind_res
        else:
            out_account = r_accounts[0]
        user_balance = self.client.listCurrencyBalance(currency)
        withdraw_info = self.client.withdraw(currency, 10, out_account["accountId"], RTSData.node_code + "abc")
        self.checkCodeMessage(withdraw_info, "RSD10501", "Transfers in this currency are not supported")
        self.assertIsNone(withdraw_info["data"])

        user_balance2 = self.client.listCurrencyBalance(currency)
        self.client.logger.info(f"资产变化了: {user_balance2['data']['amount'] - user_balance['data']['amount']}")
        self.assertAlmostEqual(user_balance['data']['amount'] - user_balance2['data']['amount'], 0, delta=0.1**6)

    def test_139_withdraw_missingParams(self):
        """
        提现, 缺少必填参数
        """
        currency = RoxeSendData.currency[0]
        r_accounts = self.client.listReceiverAccount(currency)["data"]
        if len(r_accounts) == 0:
            bind_res, r_body = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_1, RTSData.node_code)
            out_account = bind_res
        else:
            out_account = r_accounts[0]
        user_balance = self.client.listCurrencyBalance(currency)
        mis_params = ["currency", "amount", "outerNodeRoxe", "receiveAccountId"]
        for m_p in mis_params:
            self.client.logger.info(f"缺少必填参数: {m_p}")
            withdraw_info = self.client.withdraw(currency, 10, out_account["accountId"], RTSData.node_code, pop_param=m_p)
            err_msg = "outerNoderRoxeis required" if m_p == "outerNodeRoxe" else f"{m_p}is required"
            self.checkCodeMessage(withdraw_info, "RSD10001", err_msg)
            self.assertIsNone(withdraw_info["data"])

        user_balance2 = self.client.listCurrencyBalance(currency)
        self.client.logger.info(f"资产变化了: {user_balance2['data']['amount'] - user_balance['data']['amount']}")
        self.assertAlmostEqual(user_balance['data']['amount'] - user_balance2['data']['amount'], 0, delta=0.1**6)

    def test_140_sendToRoAccount_tokenError(self):
        """
        Pay，token错误
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b
        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount)
        pay_info, re_body = self.client.sendToRoxeAccount(
            to_ro_id, rate_info["data"]["exchangeRate"], currency, amount, currency, rate_info["data"]["receiveAmount"], ensure_side, 2, token="abc"
        )
        self.checkCodeMessage(pay_info, "RUC200001", "Token exception")
        self.assertIsNone(pay_info["data"])

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertAlmostEqual(from_balance - from_balance2, 0, msg="from账户资产不正确", delta=0.1**6)
        self.assertAlmostEqual(to_balance2 - to_balance, 0, msg="to账户资产不正确", delta=0.1**6)

    def test_141_sendToRoAccount_missingToken(self):
        """
        Pay，不传token
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b
        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount)
        pay_info, re_body = self.client.sendToRoxeAccount(
            to_ro_id, rate_info["data"]["exchangeRate"], currency, amount, currency, rate_info["data"]["receiveAmount"], ensure_side, 2, pop_header="token"
        )
        self.checkCodeMessage(pay_info, "RUC100002", "token is empty")
        self.assertIsNone(pay_info["data"])

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertAlmostEqual(from_balance - from_balance2, 0, msg="from账户资产不正确", delta=0.1**6)
        self.assertAlmostEqual(to_balance2 - to_balance, 0, msg="to账户资产不正确", delta=0.1**6)

    def test_142_sendToRoAccount_currencyNotSupport(self):
        """
        Pay，币种不支持
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b
        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount)
        pay_info, re_body = self.client.sendToRoxeAccount(
            to_ro_id, rate_info["data"]["exchangeRate"], "CNY", amount, currency, rate_info["data"]["receiveAmount"], ensure_side, 2
        )
        self.checkCodeMessage(pay_info, "RSD10001", "Illegal from: CNY")
        self.assertIsNone(pay_info["data"])
        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertAlmostEqual(from_balance - from_balance2, 0, msg="from账户资产不正确", delta=0.1**6)
        self.assertAlmostEqual(to_balance2 - to_balance, 0, msg="to账户资产不正确", delta=0.1**6)

    def test_143_sendToRoAccount_currencyLowerCase(self):
        """
        Pay，选择wallet支付，等待交易完成，币种小写
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b
        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount)
        pay_info, re_body = self.client.sendToRoxeAccount(
            to_ro_id, rate_info["data"]["exchangeRate"], currency.lower(), amount, currency.lower(), rate_info["data"]["receiveAmount"], ensure_side, 2
        )
        self.checkCodeMessage(pay_info, "RSD10002", "ServerError")
        self.assertIsNone(pay_info["data"])

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertAlmostEqual(from_balance - from_balance2, 0, msg="from账户资产不正确", delta=0.1**6)
        self.assertAlmostEqual(to_balance2 - to_balance, 0, msg="to账户资产不正确", delta=0.1**6)

    def test_144_sendToRoAccount_currencyMixerCase(self):
        """
        Pay，选择wallet支付，等待交易完成, 币种大小写混合
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b
        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount)
        pay_info, re_body = self.client.sendToRoxeAccount(
            to_ro_id, rate_info["data"]["exchangeRate"], currency.title(), amount, currency.title(), rate_info["data"]["receiveAmount"], ensure_side, 2
        )
        self.checkCodeMessage(pay_info, "RSD10002", "ServerError")
        self.assertIsNone(pay_info["data"])

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertAlmostEqual(from_balance - from_balance2, 0, msg="from账户资产不正确", delta=0.1**6)
        self.assertAlmostEqual(to_balance2 - to_balance, 0, msg="to账户资产不正确", delta=0.1**6)

    def test_145_sendToRoAccount_giveReceiveAmount(self):
        """
        Pay，选择wallet支付，等待交易完成, 指定到账金额
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_OUTER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b
        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, to_amount=amount)
        pay_info, re_body = self.client.sendToRoxeAccount(
            to_ro_id, rate_info["data"]["exchangeRate"], currency, float(rate_info["data"]["sendAmount"]), currency, amount, ensure_side, 1
        )
        self.checkCodeMessage(pay_info)
        self.checkSenToRoAccountOrderInfo(pay_info["data"], re_body, RoxeSendData.user_id, RoxeSendData.user_id_b)
        tx_id = pay_info["data"]["transactionId"]

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Submitted")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        # 选择wallet支付
        order_id = tx_info["data"]["orderId"]
        self.rps_client.submitPayOrderTransferToRoxeAccount(from_ro_id, to_ro_id, amount, businessType="transfer", expect_pay_success=False, businessOrderNo=order_id)
        self.waitOrderStatusInDB(order_id, "Processing")

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        self.waitOrderStatusInDB(order_id)

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Complete")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertAlmostEqual(from_balance - from_balance2, amount, msg="from账户资产不正确", delta=0.1**6)
        self.assertAlmostEqual(to_balance2 - to_balance, amount, msg="to账户资产不正确", delta=0.1**6)

    def test_146_sendToRoAccount_missingParams(self):
        """
        Pay，选择wallet支付，等待交易完成, 缺少必填参数
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b
        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount)
        mis_params = ["counterpartyRxId", "sendCurrency", "receiveCurrency", "sendAmount"]
        for m_p in mis_params:
            self.client.logger.info(f"缺少参数: {m_p}")
            pay_info, re_body = self.client.sendToRoxeAccount(
                to_ro_id, rate_info["data"]["exchangeRate"], currency, amount, currency, amount, ensure_side, 2, pop_param=m_p
            )
            if m_p == "counterpartyRxId":
                self.checkCodeMessage(pay_info, "RSD10001", "The counterparty has not generated a roxeID")
            elif m_p == "receiveCurrency":
                self.checkCodeMessage(pay_info, "RSD10001", "Illegal to: null")
            else:
                self.checkCodeMessage(pay_info, "RSD10002", "ServerError")
            self.assertIsNone(pay_info["data"])

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertAlmostEqual(from_balance - from_balance2, 0, msg="from账户资产不正确", delta=0.1**6)
        self.assertAlmostEqual(to_balance2 - to_balance, 0, msg="to账户资产不正确", delta=0.1**6)

    def test_147_request_tokenError(self):
        """
        request，token错误
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b

        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")

        pay_info, re_body = self.client.request(RoxeSendData.user_id_b, currency, amount, "hello", token="abc")
        self.checkCodeMessage(pay_info, "RUC200001", "Token exception")
        self.assertIsNone(pay_info["data"])

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertEqual(from_balance2, from_balance, msg="from账户资产不正确")
        self.assertEqual(to_balance2, to_balance, msg="to账户资产不正确")

    def test_148_request_missingToken(self):
        """
        request，token不传
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b

        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")

        pay_info, re_body = self.client.request(RoxeSendData.user_id_b, currency, amount, "hello", pop_header="token")
        self.checkCodeMessage(pay_info, "RUC100002", "token is empty")
        self.assertIsNone(pay_info["data"])

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertEqual(from_balance2, from_balance, msg="from账户资产不正确")
        self.assertEqual(to_balance2, to_balance, msg="to账户资产不正确")

    def test_149_request_currencyNotSupport(self):
        """
        request，币种不支持
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b

        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")

        pay_info, re_body = self.client.request(RoxeSendData.user_id_b, "CNY", amount, "hello")
        self.checkCodeMessage(pay_info, "RSD10001", "Illegal currency: CNY")
        self.assertEqual(pay_info["data"], None)

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertEqual(from_balance2, from_balance, msg="from账户资产不正确")
        self.assertEqual(to_balance2, to_balance, msg="to账户资产不正确")

    def test_150_request_currencyLowerCase(self):
        """
        request，币种为小写
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b

        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")

        pay_info, re_body = self.client.request(RoxeSendData.user_id_b, currency.lower(), amount, "hello")
        self.checkCodeMessage(pay_info, "RSD10001", f"Illegal currency: {currency.lower()}")
        self.assertEqual(pay_info["data"], None)

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertAlmostEqual(from_balance2 - from_balance, 0, msg="from账户资产不正确", delta=0.1**6)
        self.assertAlmostEqual(to_balance - to_balance2, 0, msg="to账户资产不正确", delta=0.1**6)

    def test_151_request_currencyMixerCase(self):
        """
        request，币种大小写混合
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b

        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")

        pay_info, re_body = self.client.request(RoxeSendData.user_id_b, currency.title(), amount, "hello")
        self.checkCodeMessage(pay_info, "RSD10001", f"Illegal currency: {currency.title()}")
        self.assertEqual(pay_info["data"], None)

        # # A查询交易详情
        # tx_info = self.client.getTransactionDetail(tx_id)
        # self.checkCodeMessage(tx_info)
        # self.assertEqual(tx_info["data"]["status"], "Temporary")
        # self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)
        #
        # # B查询到的交易
        # tx_h, tx_body = self.client.getTransactionHistory(token=RoxeSendData.user_login_token_b)
        # tx_id_b = tx_h["data"]["data"][0]["transactionId"]
        #
        # tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        # self.checkCodeMessage(tx_info)
        # self.assertEqual(tx_info["data"]["status"], "Temporary")
        # self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)
        #
        # ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        # b_type = RoxeSendEnum.BUSINESS_TYPE_REQUEST.value
        # rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount)
        # # 另外一方进行支付
        # pay_request, pay_body = self.client.payRequest(
        #     tx_id_b, from_ro_id, rate_info["data"]["exchangeRate"], currency,
        #     rate_info["data"]["sendAmount"], currency, rate_info["data"]["receiveAmount"],
        #     2, "pay request", RoxeSendData.user_login_token_b
        # )
        # self.checkCodeMessage(pay_request)
        # self.checkPayRequestOrderInfo(pay_request["data"], pay_body, RoxeSendData.user_id_b, RoxeSendData.user_id)
        #
        # # 选择wallet支付
        # order_id = pay_request["data"]["orderId"]
        # pay_amount = ApiUtils.parseNumberDecimal(float(rate_info["data"]["sendAmount"]))
        # self.rps_client.submitPayOrderTransferToRoxeAccount(to_ro_id, from_ro_id, pay_amount, businessType="transfer", expect_pay_success=False, businessOrderNo=order_id)
        # self.waitOrderStatusInDB(order_id, "Processing")
        #
        # # 查询交易详情
        # tx_info = self.client.getTransactionDetail(tx_id)
        # self.checkCodeMessage(tx_info)
        # self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)
        #
        # tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        # self.checkCodeMessage(tx_info)
        # self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)
        #
        # self.waitOrderStatusInDB(order_id)
        #
        # # 查询交易详情
        # tx_info = self.client.getTransactionDetail(tx_id)
        # self.checkCodeMessage(tx_info)
        # self.assertEqual(tx_info["data"]["status"], "Complete")
        # self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)
        #
        # tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        # self.checkCodeMessage(tx_info)
        # self.assertEqual(tx_info["data"]["status"], "Complete")
        # self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertAlmostEqual(from_balance2 - from_balance, 0, msg="from账户资产不正确", delta=0.1**6)
        self.assertAlmostEqual(to_balance - to_balance2, 0, msg="to账户资产不正确", delta=0.1**6)

    def test_152_request_missingParams(self):
        """
        request，不支付，撤销交易
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b

        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")
        mis_params = ["counterpartyUserId", "receiveAmount", "receiveCurrency"]
        for m_p in mis_params:
            self.client.logger.info(f"缺少参数: {m_p}")
            pay_info, re_body = self.client.request(RoxeSendData.user_id_b, currency, amount, "hello", pop_param=m_p)
            err_msg = f"{m_p}is required"
            self.checkCodeMessage(pay_info, "RSD10001", err_msg)
            self.assertIsNone(pay_info["data"])

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertEqual(from_balance2, from_balance, msg="from账户资产不正确")
        self.assertEqual(to_balance2, to_balance, msg="to账户资产不正确")

    def test_153_request_cancelHasCanceledRequest(self):
        """
        request，不支付，撤销交易, 再次撤销交易
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b

        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")

        pay_info, re_body = self.client.request(RoxeSendData.user_id_b, currency, amount, "hello")
        self.checkCodeMessage(pay_info)
        self.checkRequestOrderInfo(pay_info["data"], re_body, RoxeSendData.user_id, RoxeSendData.user_id_b)
        tx_id = pay_info["data"]["transactionId"]

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Temporary")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        # B查询到的request订单
        tx_h, tx_body = self.client.getTransactionHistory(token=RoxeSendData.user_login_token_b)
        tx_id_b = tx_h["data"]["data"][0]["transactionId"]

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Temporary")
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        # 取消交易
        cancel_info = self.client.cancelTransaction(tx_id)
        self.checkCodeMessage(cancel_info)
        self.assertTrue(cancel_info["data"])

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Cancelled")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Cancelled")
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        # 再次取消交易
        cancel_info = self.client.cancelTransaction(tx_id)
        self.checkCodeMessage(cancel_info, "RSD10001", "Illegal request")
        self.assertIsNone(cancel_info["data"])

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertEqual(from_balance2, from_balance, msg="from账户资产不正确")
        self.assertEqual(to_balance2, to_balance, msg="to账户资产不正确")

    def test_154_request_cancelHasPayedRequest(self):
        """
        request，支付，然后撤销支付中的交易
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b

        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")

        pay_info, re_body = self.client.request(RoxeSendData.user_id_b, currency, amount, "hello")
        tx_id = pay_info["data"]["transactionId"]

        # A查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Temporary")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        # B查询到的交易
        tx_h, tx_body = self.client.getTransactionHistory(token=RoxeSendData.user_login_token_b)
        tx_id_b = tx_h["data"]["data"][0]["transactionId"]

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Temporary")
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_REQUEST.value
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount)
        # 另外一方进行支付
        pay_request, pay_body = self.client.payRequest(
            tx_id_b, from_ro_id, rate_info["data"]["exchangeRate"], currency,
            rate_info["data"]["sendAmount"], currency, rate_info["data"]["receiveAmount"],
            2, "pay request", RoxeSendData.user_login_token_b
        )
        self.checkCodeMessage(pay_request)
        self.checkPayRequestOrderInfo(pay_request["data"], pay_body, RoxeSendData.user_id_b, RoxeSendData.user_id)

        # 选择wallet支付
        order_id = pay_request["data"]["orderId"]
        pay_amount = ApiUtils.parseNumberDecimal(float(rate_info["data"]["sendAmount"]))
        self.rps_client.submitPayOrderTransferToRoxeAccount(to_ro_id, from_ro_id, pay_amount, businessType="transfer", expect_pay_success=False, businessOrderNo=order_id)
        self.waitOrderStatusInDB(order_id, "Processing")

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        # 撤销正在支付中的交易
        cancel_info = self.client.cancelTransaction(tx_id)
        self.checkCodeMessage(cancel_info, "RSD10001", "Illegal request")
        self.assertIsNone(cancel_info["data"])

        self.waitOrderStatusInDB(order_id)

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Complete")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Complete")
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertAlmostEqual(from_balance2 - from_balance, amount, msg="from账户资产不正确", delta=0.1**6)
        self.assertAlmostEqual(to_balance - to_balance2, pay_amount, msg="to账户资产不正确", delta=0.1**6)

    def test_155_request_payHasCanceledRequest(self):
        """
        request，撤销交易, 然后支付已经撤销的交易
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b

        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")

        pay_info, re_body = self.client.request(RoxeSendData.user_id_b, currency, amount, "hello")
        self.checkCodeMessage(pay_info)
        self.checkRequestOrderInfo(pay_info["data"], re_body, RoxeSendData.user_id, RoxeSendData.user_id_b)
        tx_id = pay_info["data"]["transactionId"]

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Temporary")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        # B查询到的request订单
        tx_h, tx_body = self.client.getTransactionHistory(token=RoxeSendData.user_login_token_b)
        tx_id_b = tx_h["data"]["data"][0]["transactionId"]

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Temporary")
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        # 取消交易
        cancel_info = self.client.cancelTransaction(tx_id)
        self.checkCodeMessage(cancel_info)
        self.assertTrue(cancel_info["data"])

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Cancelled")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Cancelled")
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_REQUEST.value
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount)
        # 另外一方进行支付
        pay_request, pay_body = self.client.payRequest(
            tx_id_b, from_ro_id, rate_info["data"]["exchangeRate"], currency,
            rate_info["data"]["sendAmount"], currency, rate_info["data"]["receiveAmount"],
            2, "pay request", RoxeSendData.user_login_token_b
        )
        self.checkCodeMessage(pay_request, "RSD10001", "The current order has been cancelled")
        self.assertIsNone(pay_request["data"])

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertEqual(from_balance2, from_balance, msg="from账户资产不正确")
        self.assertEqual(to_balance2, to_balance, msg="to账户资产不正确")

    def test_156_request_payHasPayedRequest(self):
        """
        request，支付，然后再次支付正在支付中的交易
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b

        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")

        pay_info, re_body = self.client.request(RoxeSendData.user_id_b, currency, amount, "hello")
        tx_id = pay_info["data"]["transactionId"]

        # A查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Temporary")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        # B查询到的交易
        tx_h, tx_body = self.client.getTransactionHistory(token=RoxeSendData.user_login_token_b)
        tx_id_b = tx_h["data"]["data"][0]["transactionId"]

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Temporary")
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_REQUEST.value
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount)
        # 另外一方进行支付
        pay_request, pay_body = self.client.payRequest(
            tx_id_b, from_ro_id, rate_info["data"]["exchangeRate"], currency,
            rate_info["data"]["sendAmount"], currency, rate_info["data"]["receiveAmount"],
            2, "pay request", RoxeSendData.user_login_token_b
        )
        self.checkCodeMessage(pay_request)
        self.checkPayRequestOrderInfo(pay_request["data"], pay_body, RoxeSendData.user_id_b, RoxeSendData.user_id)

        # 选择wallet支付
        order_id = pay_request["data"]["orderId"]
        pay_amount = ApiUtils.parseNumberDecimal(float(rate_info["data"]["sendAmount"]))
        self.rps_client.submitPayOrderTransferToRoxeAccount(to_ro_id, from_ro_id, pay_amount, businessType="transfer", expect_pay_success=False, businessOrderNo=order_id)
        self.waitOrderStatusInDB(order_id, "Processing")

        # 另外一方进行支付
        pay_request, pay_body = self.client.payRequest(
            tx_id_b, from_ro_id, rate_info["data"]["exchangeRate"], currency,
            rate_info["data"]["sendAmount"], currency, rate_info["data"]["receiveAmount"],
            2, "pay request", RoxeSendData.user_login_token_b
        )
        self.checkCodeMessage(pay_request, "RMS10002", "ServerError")
        self.assertIsNone(pay_request["data"])

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        self.waitOrderStatusInDB(order_id)

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Complete")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Complete")
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertAlmostEqual(from_balance2 - from_balance, amount, msg="from账户资产不正确", delta=0.1**6)
        self.assertAlmostEqual(to_balance - to_balance2, pay_amount, msg="to账户资产不正确", delta=0.1**6)

    def test_157_request_declineHasCanceledRequest(self):
        """
        request，撤销交易, 然后拒绝已经撤销的交易
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b

        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")

        pay_info, re_body = self.client.request(RoxeSendData.user_id_b, currency, amount, "hello")
        self.checkCodeMessage(pay_info)
        self.checkRequestOrderInfo(pay_info["data"], re_body, RoxeSendData.user_id, RoxeSendData.user_id_b)
        tx_id = pay_info["data"]["transactionId"]

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Temporary")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        # B查询到的request订单
        tx_h, tx_body = self.client.getTransactionHistory(token=RoxeSendData.user_login_token_b)
        tx_id_b = tx_h["data"]["data"][0]["transactionId"]

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Temporary")
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        # 取消交易
        cancel_info = self.client.cancelTransaction(tx_id)
        self.checkCodeMessage(cancel_info)
        self.assertTrue(cancel_info["data"])

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Cancelled")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        # 拒绝支付交易
        decline_info = self.client.declineRequest(pay_info["data"]["orderId"], RoxeSendData.user_login_token_b)
        self.checkCodeMessage(decline_info, "RSD10001", "Illegal request")
        self.assertIsNone(decline_info["data"])

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Cancelled")
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertEqual(from_balance2, from_balance, msg="from账户资产不正确")
        self.assertEqual(to_balance2, to_balance, msg="to账户资产不正确")

    def test_158_request_declineHasPayedRequest(self):
        """
        request，支付，然后拒绝正在支付中的交易
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b

        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")

        pay_info, re_body = self.client.request(RoxeSendData.user_id_b, currency, amount, "hello")
        tx_id = pay_info["data"]["transactionId"]

        # A查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Temporary")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        # B查询到的交易
        tx_h, tx_body = self.client.getTransactionHistory(token=RoxeSendData.user_login_token_b)
        tx_id_b = tx_h["data"]["data"][0]["transactionId"]

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Temporary")
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_REQUEST.value
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount)
        # 另外一方进行支付
        pay_request, pay_body = self.client.payRequest(
            tx_id_b, from_ro_id, rate_info["data"]["exchangeRate"], currency,
            rate_info["data"]["sendAmount"], currency, rate_info["data"]["receiveAmount"],
            2, "pay request", RoxeSendData.user_login_token_b
        )
        self.checkCodeMessage(pay_request)
        self.checkPayRequestOrderInfo(pay_request["data"], pay_body, RoxeSendData.user_id_b, RoxeSendData.user_id)

        # 选择wallet支付
        order_id = pay_request["data"]["orderId"]
        pay_amount = ApiUtils.parseNumberDecimal(float(rate_info["data"]["sendAmount"]))
        self.rps_client.submitPayOrderTransferToRoxeAccount(to_ro_id, from_ro_id, pay_amount, businessType="transfer", expect_pay_success=False, businessOrderNo=order_id)
        self.waitOrderStatusInDB(order_id, "Processing")

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        # 拒绝支付交易
        decline_info = self.client.declineRequest(order_id, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(decline_info, "RSD10001", "Illegal request")
        self.assertIsNone(decline_info["data"])

        self.waitOrderStatusInDB(order_id)

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Complete")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Complete")
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertAlmostEqual(from_balance2 - from_balance, amount, msg="from账户资产不正确", delta=0.1**6)
        self.assertAlmostEqual(to_balance - to_balance2, pay_amount, msg="to账户资产不正确", delta=0.1**6)

    def test_159_getTransactionHistory_tokenError(self):
        """
        查询历史交易，token错误
        """

        transactions, r_params = self.client.getTransactionHistory(token="abc")
        self.checkCodeMessage(transactions, "RUC200001", "Token exception")
        self.assertIsNone(transactions["data"])

    def test_160_getTransactionHistory_missingToken(self):
        """
        查询历史交易，token不传
        """

        transactions, r_params = self.client.getTransactionHistory(pop_header="token")
        self.checkCodeMessage(transactions, "RUC100002", "token is empty")
        self.assertIsNone(transactions["data"])

    def test_161_getTransactionHistory_currencyNotSupport(self):
        """
        查询历史交易，币种为不支持的币种
        """
        transactions, r_params = self.client.getTransactionHistory(currency="CNYA")
        self.checkCodeMessage(transactions)
        self.assertEqual(transactions["data"]["pageNumber"], 1)
        self.assertEqual(transactions["data"]["pageSize"], 0)
        self.assertEqual(transactions["data"]["totalCount"], 0)
        self.assertIsNone(transactions["data"]["totalPage"])
        self.assertEqual(transactions["data"]["data"], [])

    def test_162_getTransactionHistory_currencyLowerCase(self):
        """
        查询历史交易，币种小写
        """
        transactions, r_params = self.client.getTransactionHistory(currency=RoxeSendData.currency[0].lower())
        self.checkCodeMessage(transactions)
        self.checkTransactionHistory(transactions["data"], r_params, RoxeSendData.user_id)

    def test_163_getTransactionHistory_currencyMixerCase(self):
        """
        查询历史交易，币种大小写混合
        """
        transactions, r_params = self.client.getTransactionHistory(currency=RoxeSendData.currency[0].title())
        self.checkCodeMessage(transactions)
        self.checkTransactionHistory(transactions["data"], r_params, RoxeSendData.user_id)

    def test_164_getTransactionHistory_multipleSelect(self):
        """
        查询历史交易，组合筛选，类别、时间、关键字搜索
        """
        b_type = RoxeSendEnum.BUSINESS_TYPE_REQUEST.value
        cur_time = datetime.datetime.utcnow()
        b_time = int(datetime.datetime.strptime(f"{cur_time.year}-{cur_time.month}-01", "%Y-%m-%d").timestamp() * 1000)
        e_time = int(datetime.datetime.strptime(f"{cur_time.year}-{cur_time.month + 1}-01", "%Y-%m-%d").timestamp() * 1000)
        transactions, r_params = self.client.getTransactionHistory(b_type=b_type, begin=b_time, end=e_time, key_word="hello")
        self.checkCodeMessage(transactions)
        self.checkTransactionHistory(transactions["data"], r_params, RoxeSendData.user_id)

    def test_165_getTransactionHistory_pageSizeBigger(self):
        """
        查询历史交易，pageSize设置大
        """
        transactions, r_params = self.client.getTransactionHistory(page_size=100)
        self.checkCodeMessage(transactions)
        self.checkTransactionHistory(transactions["data"], r_params, RoxeSendData.user_id)

    def test_166_getTransactionHistory_giveSeveralPageNumber(self):
        """
        查询历史交易，pageNumber多获取几页
        """
        transactions, r_params = self.client.getTransactionHistory(page_number=5)
        self.checkCodeMessage(transactions)
        self.checkTransactionHistory(transactions["data"], r_params, RoxeSendData.user_id)

    def test_167_getTransactionHistory_noteNotExist(self):
        """
        查询历史交易，搜索不存在的备注
        """
        transactions, r_params = self.client.getTransactionHistory(key_word=str(int(time.time())))
        self.checkCodeMessage(transactions)
        self.assertEqual(transactions["data"]["pageNumber"], 1)
        self.assertEqual(transactions["data"]["pageSize"], 0)
        self.assertEqual(transactions["data"]["totalCount"], 0)
        self.assertIsNone(transactions["data"]["totalPage"])
        self.assertEqual(transactions["data"]["data"], [])

    def test_168_getRecentContact_tokenError(self):
        """
        获取最近的联系人, token错误
        """
        recent_info = self.client.getUserRecentContact(token="abc")
        self.checkCodeMessage(recent_info, "RUC200001", "Token exception")
        self.assertIsNone(recent_info["data"])

    def test_169_getRecentContact_missingToken(self):
        """
        获取最近的联系人, 不传token
        """
        recent_info = self.client.getUserRecentContact(pop_header="token")
        self.checkCodeMessage(recent_info, "RUC100002", "token is empty")
        self.assertIsNone(recent_info["data"])

    def test_170_getRecentContact_givePageSize(self):
        """
        获取最近的联系人, 传入pageSize
        """
        for p_size in [10, 15, 20]:
            recent_info = self.client.getUserRecentContact(p_size=p_size)
            self.checkCodeMessage(recent_info)
            self.checkRecentContact(recent_info["data"], RoxeSendData.user_id)

    def test_171_getRecentContact_givePageNumber(self):
        """
        获取最近的联系人, 传入pageNumber
        """
        # 得到全部的联系人
        recent_info = self.client.getUserRecentContact()
        total_db = self.checkRecentContact(recent_info["data"], RoxeSendData.user_id)

        p_size = 6
        for p_num in range(1, total_db//p_size + 2):
            self.client.logger.info(f"查询第{p_num}页的最近联系人")
            recent_info = self.client.getUserRecentContact(p_num, p_size)
            self.checkCodeMessage(recent_info)
            self.checkRecentContact(recent_info["data"], RoxeSendData.user_id)
            if p_num * p_size <= total_db:
                self.assertTrue(len(recent_info["data"]) <= p_size, "结果数量应不大于pageSize")
            else:
                self.assertEqual(recent_info["data"], [], "超过数据库中的数据量应该返回空")

    def test_172_updateUserReadOrder_tokenError(self):
        """
        更新用户未读取的订单数量，token错误
        """
        recent_info = self.client.getUserRecentContact()
        r_info = [i for i in recent_info["data"] if i["count"] is None]

        update_info = self.client.updateUserReadOrder(r_info[0]["userId"], token="abc")
        self.checkCodeMessage(update_info, "RUC200001", "Token exception")
        self.assertIsNone(update_info["data"])

        recent_info2 = self.client.getUserRecentContact()
        u_r_info = [i for i in recent_info2["data"] if i["userId"] == r_info[0]["userId"]]
        self.assertEqual(u_r_info[0]["count"], r_info[0]["count"])

    def test_173_updateUserReadOrder_missingToken(self):
        """
        更新用户未读取的订单数量，不传token
        """
        recent_info = self.client.getUserRecentContact()
        r_info = [i for i in recent_info["data"] if i["count"]]

        update_info = self.client.updateUserReadOrder(r_info[0]["userId"], pop_header="token")
        self.checkCodeMessage(update_info, "RUC100002", "token is empty")
        self.assertIsNone(update_info["data"])

        recent_info2 = self.client.getUserRecentContact()
        u_r_info = [i for i in recent_info2["data"] if i["userId"] == r_info[0]["userId"]]
        self.assertEqual(u_r_info[0]["count"], r_info[0]["count"])

    def test_174_updateUserReadOrder_userNotExist(self):
        """
        更新用户未读取的订单数量，不存在的联系人
        """
        update_info = self.client.updateUserReadOrder("100000")
        self.checkCodeMessage(update_info)
        self.assertIsNone(update_info["data"])

    def test_175_updateUserReadOrder_userNotInRecentContract(self):
        """
        更新用户未读取的订单数量，用户不在最近的联系人中
        """
        recent_info = self.client.getUserRecentContact(p_size=100)
        r_users = [i["userId"] for i in recent_info["data"]]
        update_user = ""
        for r_u in reversed(r_users):
            if str(int(r_u) - 1) not in r_users:
                update_user = str(int(r_u) - 1)
                break

        update_info = self.client.updateUserReadOrder(update_user)
        self.checkCodeMessage(update_info)
        self.assertIsNone(update_info["data"])

    def test_176_kycVerification_tokenError(self):
        """
        判断转账金额是否达到kyc上限，token错误
        """
        kyc_info = self.client.kycVerification(RoxeSendData.currency[0], 1, token="abc")
        self.checkCodeMessage(kyc_info, "RUC200001", "Token exception")
        self.assertIsNone(kyc_info["data"])

    def test_177_kycVerification_missingToken(self):
        """
        判断转账金额是否达到kyc上限，token不传
        """
        kyc_info = self.client.kycVerification(RoxeSendData.currency[0], 1, pop_header="token")
        self.checkCodeMessage(kyc_info, "RUC100002", "token is empty")
        self.assertIsNone(kyc_info["data"])

    def test_178_kycVerification_amountReachLimit_notKyc(self):
        """
        判断转账金额是否达到kyc上限，传入金额达到上限，没有经过kyc的用户
        """
        daily_limit, ninety_day_limit, left_day = self.client.calKycLimitAmount(self, RoxeSendData.user_id_c, RoxeSendData.user_login_token_c)
        daily_limit = 1 if daily_limit == 0 else daily_limit
        ninety_day_limit = 1 if ninety_day_limit == 0 else ninety_day_limit
        kyc_info = self.client.kycVerification(RoxeSendData.currency[0], daily_limit, RoxeSendData.user_login_token_c)
        self.checkCodeMessage(kyc_info, "RSD10401", "Kyc not pass,level: L2")
        self.assertIsNone(kyc_info["data"])
        kyc_info = self.client.kycVerification(RoxeSendData.currency[0], ninety_day_limit, RoxeSendData.user_login_token_c)
        self.checkCodeMessage(kyc_info, "RSD10401", "Kyc not pass,level: L2")
        self.assertIsNone(kyc_info["data"])

        kyc_info = self.client.kycVerification(RoxeSendData.currency[0], ninety_day_limit + 10, RoxeSendData.user_login_token_c)
        self.checkCodeMessage(kyc_info, "RSD10401", "Kyc not pass,level: L2")
        self.assertIsNone(kyc_info["data"])

    def test_179_kycVerification_amountReachLimit_kaKyc(self):
        """
        判断转账金额是否达到kyc上限，传入金额达到上限, 通过ka的用户
        """
        daily_limit, ninety_day_limit, left_day = self.client.calKycLimitAmount(self, RoxeSendData.user_id_b, RoxeSendData.user_login_token_b)

        kyc_info = self.client.kycVerification(RoxeSendData.currency[0], daily_limit, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(kyc_info)
        self.assertEqual(kyc_info["data"], "SUCCESS")

        kyc_info = self.client.kycVerification(RoxeSendData.currency[0], daily_limit + 10, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(kyc_info, "RSD10402", "Kyc not pass,level: L3")
        self.assertIsNone(kyc_info["data"])

        kyc_info = self.client.kycVerification(RoxeSendData.currency[0], ninety_day_limit, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(kyc_info, "RSD10402", "Kyc not pass,level: L3")
        self.assertIsNone(kyc_info["data"])

        kyc_info = self.client.kycVerification(RoxeSendData.currency[0], ninety_day_limit + 10, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(kyc_info, "RSD10402", "Kyc not pass,level: L3")
        self.assertIsNone(kyc_info["data"])

    def test_180_kycVerification_amountReachLimit_kmKyc(self):
        """
        判断转账金额是否达到kyc上限，传入金额达到上限, 通过km的用户
        """
        daily_limit, ninety_day_limit, left_day = self.client.calKycLimitAmount(self, RoxeSendData.user_id, RoxeSendData.user_login_token)

        kyc_info = self.client.kycVerification(RoxeSendData.currency[0], daily_limit, RoxeSendData.user_login_token)
        self.checkCodeMessage(kyc_info)
        self.assertEqual(kyc_info["data"], "SUCCESS")

        kyc_info = self.client.kycVerification(RoxeSendData.currency[0], daily_limit + 0.1, RoxeSendData.user_login_token)
        self.checkCodeMessage(kyc_info, "RSD10403", "You’ve reached your daily transaction limit. Please try again tomorrow")
        self.assertIsNone(kyc_info["data"])

        kyc_info = self.client.kycVerification(RoxeSendData.currency[0], ninety_day_limit, RoxeSendData.user_login_token)
        self.checkCodeMessage(kyc_info, "RSD10403", "You’ve reached your daily transaction limit. Please try again tomorrow")
        self.assertIsNone(kyc_info["data"])

        kyc_info = self.client.kycVerification(RoxeSendData.currency[0], ninety_day_limit + 0.01, RoxeSendData.user_login_token)
        self.checkCodeMessage(kyc_info, "RSD10404", str(left_day))
        self.assertIsNone(kyc_info["data"])

    def test_181_listNotification_tokenError(self):
        """
        查看交易通知列表, token错误
        """
        notifications = self.client.listNotification(token="abc")
        self.checkCodeMessage(notifications, "RUC200001", "Token exception")
        self.assertIsNone(notifications["data"])

    def test_182_listNotification_missingToken(self):
        """
        查看交易通知列表, token不传
        """
        notifications = self.client.listNotification(pop_header="token")
        self.checkCodeMessage(notifications, "RUC100002", "token is empty")
        self.assertIsNone(notifications["data"])

    def test_183_getAchAccount_tokenError(self):
        """
        查询ach账号，token错误
        """
        currency = RoxeSendData.currency[0]
        accounts = self.client.getAccountList(currency, token="abc")
        self.checkCodeMessage(accounts, "RUC200001", "Token exception")
        self.assertIsNone(accounts["data"])

    def test_184_getAchAccount_missingToken(self):
        """
        查询ach账号，token不传
        """
        currency = RoxeSendData.currency[0]
        accounts = self.client.getAccountList(currency, pop_header="token")
        self.checkCodeMessage(accounts, "RUC100002", "token is empty")
        self.assertIsNone(accounts["data"])

    def test_185_getAchAccount_currencyNotSupport(self):
        """
        查询ach账号，币种不支持
        """
        accounts = self.client.getAccountList("CNY")
        self.checkCodeMessage(accounts)
        self.assertEqual(accounts["data"], [])

    def test_186_getAchAccount_currencyLowerCase(self):
        """
        查询ach账号，币种小写
        """
        self.rps_client.deleteAchAccountFromDB(self, RoxeSendData.user_id)
        currency = RoxeSendData.currency[0]
        account_id = self.rps_client.bindAndVerifyAchAccount(RPSData.ach_account)
        accounts = self.client.getAccountList(currency.lower())
        self.checkCodeMessage(accounts)

        self.assertEqual(len(accounts["data"]), 1)
        self.assertEqual(accounts["data"][0]["id"], account_id)

    def test_187_getAchAccount_currencyMixerCase(self):
        """
        查询ach账号，币种大小写混合
        """
        self.rps_client.deleteAchAccountFromDB(self, RoxeSendData.user_id)
        currency = RoxeSendData.currency[0]
        account_id = self.rps_client.bindAndVerifyAchAccount(RPSData.ach_account)
        accounts = self.client.getAccountList(currency.title())
        self.checkCodeMessage(accounts)

        self.assertEqual(len(accounts["data"]), 1)
        self.assertEqual(accounts["data"][0]["id"], account_id)

    def test_188_deleteAchAccount_tokenError(self):
        """
        删除ach账户, token错误
        """
        currency = RoxeSendData.currency[0]
        accounts = self.client.getAccountList(currency)
        if len(accounts["data"]) == 0:
            self.rps_client.bindAndVerifyAchAccount(RPSData.ach_account)
            accounts = self.client.getAccountList(currency)
        ach_id = accounts["data"][0]["id"]
        delete_info = self.client.deleteAccountById(ach_id, token="abc")
        self.checkCodeMessage(delete_info, "RUC200001", "Token exception")
        self.assertIsNone(delete_info["data"])
        accounts2 = self.client.getAccountList(currency)
        self.assertEqual(accounts2, accounts)

    def test_189_deleteAchAccount_missingToken(self):
        """
        删除ach账户, 不传token
        """
        currency = RoxeSendData.currency[0]
        accounts = self.client.getAccountList(currency)
        if len(accounts["data"]) == 0:
            self.rps_client.bindAndVerifyAchAccount(RPSData.ach_account)
            accounts = self.client.getAccountList(currency)
        ach_id = accounts["data"][0]["id"]
        delete_info = self.client.deleteAccountById(ach_id, pop_header="token")
        self.checkCodeMessage(delete_info, "RUC100002", "token is empty")
        self.assertIsNone(delete_info["data"])
        accounts2 = self.client.getAccountList(currency)
        self.assertEqual(accounts2, accounts, "删除后获取账户应为空")

    def test_190_deleteAchAccount_accountIdIncorrect(self):
        """
        删除ach账户, 账户id不正确
        """
        currency = RoxeSendData.currency[0]
        accounts = self.client.getAccountList(currency)
        if len(accounts["data"]) == 0:
            self.rps_client.bindAndVerifyAchAccount(RPSData.ach_account)
            accounts = self.client.getAccountList(currency)
        ach_id = accounts["data"][0]["id"]
        delete_info = self.client.deleteAccountById(ach_id - 1)
        self.checkCodeMessage(delete_info, "PAY_RPS_671", "bank account not exist")
        self.assertIsNone(delete_info["data"])
        accounts2 = self.client.getAccountList(currency)
        self.assertEqual(accounts, accounts2)

    """
    关于kyc交易限额的场景
    """

    def test_191_deposit_notKycAmountMoreThanLimit(self):
        """
        充值下单, 没有经过kyc，即级别L1的用户调用失败
        """
        currency = RoxeSendData.currency[0]
        user_balance = self.client.listCurrencyBalance(currency, token=RoxeSendData.user_login_token_c)
        deposit_info, re_body = self.client.deposit(currency, 10 + RoxeSendData.kyc_limit_level1["24HourAmount"], token=RoxeSendData.user_login_token_c)
        self.checkCodeMessage(deposit_info, "RSD10401", "Kyc not pass,level: L2")
        self.assertIsNone(deposit_info["data"])

        deposit_info, re_body = self.client.deposit(currency, 10 + RoxeSendData.kyc_limit_level2["24HourAmount"], token=RoxeSendData.user_login_token_c)
        self.checkCodeMessage(deposit_info, "RSD10401", "Kyc not pass,level: L2")
        self.assertIsNone(deposit_info["data"])

        deposit_info, re_body = self.client.deposit(currency, 10 + RoxeSendData.kyc_limit_level3["24HourAmount"], token=RoxeSendData.user_login_token_c)
        self.checkCodeMessage(deposit_info, "RSD10401", "Kyc not pass,level: L2")
        self.assertIsNone(deposit_info["data"])

        user_balance2 = self.client.listCurrencyBalance(currency, token=RoxeSendData.user_login_token_c)
        self.assertEqual(user_balance2, user_balance, "账户资产不正确")

    def test_192_withdraw_notKycAmountMoreThanLimit(self):
        """
        提现, 没有经过kyc，即级别L1的用户调用失败
        """
        currency = RoxeSendData.currency[0]
        r_accounts = self.client.listReceiverAccount(currency, token=RoxeSendData.user_login_token_c)["data"]
        if len(r_accounts) == 0:
            bind_res, r_body = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_1, RTSData.node_code, token=RoxeSendData.user_login_token_c)
            out_account = bind_res["data"]
        else:
            out_account = r_accounts[0]
        user_balance = self.client.listCurrencyBalance(currency, token=RoxeSendData.user_login_token_c)
        withdraw_info = self.client.withdraw(currency, 10 + RoxeSendData.kyc_limit_level1["24HourAmount"], out_account["accountId"], RTSData.node_code, token=RoxeSendData.user_login_token_c)
        self.checkCodeMessage(withdraw_info, "RSD10401", "Kyc not pass,level: L2")
        self.assertIsNone(withdraw_info["data"])

        withdraw_info = self.client.withdraw(currency, 10 + RoxeSendData.kyc_limit_level2["24HourAmount"], out_account["accountId"], RTSData.node_code, token=RoxeSendData.user_login_token_c)
        self.checkCodeMessage(withdraw_info, "RSD10401", "Kyc not pass,level: L2")
        self.assertIsNone(withdraw_info["data"])

        withdraw_info = self.client.withdraw(currency, 10 + RoxeSendData.kyc_limit_level3["24HourAmount"], out_account["accountId"], RTSData.node_code, token=RoxeSendData.user_login_token_c)
        self.checkCodeMessage(withdraw_info, "RSD10401", "Kyc not pass,level: L2")
        self.assertIsNone(withdraw_info["data"])
        user_balance2 = self.client.listCurrencyBalance(currency, token=RoxeSendData.user_login_token_c)
        self.client.logger.info(f"资产变化了: {user_balance2['data']['amount'] - user_balance['data']['amount']}")
        self.assertAlmostEqual(user_balance['data']['amount'] - user_balance2['data']['amount'], 0, delta=0.1**6)

    def test_193_sendToRoAccount_notKycAmountMoreThanLimit(self):
        """
        Pay，没有经过kyc，即级别L1的用户调用失败
        """
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        from_ro_id = RoxeSendData.user_account_c
        to_ro_id = RoxeSendData.user_account_b

        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")

        for amount in [10 + RoxeSendData.kyc_limit_level1["24HourAmount"], 10 + RoxeSendData.kyc_limit_level2["24HourAmount"], 10 + RoxeSendData.kyc_limit_level3["24HourAmount"]]:
            rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount)
            pay_info, re_body = self.client.sendToRoxeAccount(
                to_ro_id, rate_info["data"]["exchangeRate"], currency, amount, currency, rate_info["data"]["receiveAmount"], ensure_side, 2, token=RoxeSendData.user_login_token_c
            )
            self.checkCodeMessage(pay_info, "RSD10401", "Kyc not pass,level: L2")
            self.assertIsNone(pay_info["data"])

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertEqual(from_balance2, from_balance, msg="from账户资产不正确")
        self.assertEqual(to_balance2, to_balance, msg="to账户资产不正确")

    def test_194_request_notKycAmountMoreThanLimit(self):
        """
        request，没有经过kyc，即级别L1的用户可以发起request, 不支付，撤销交易
        """
        # amount = 4.35
        currency = RoxeSendData.currency[0]
        from_ro_id = RoxeSendData.user_account_c
        to_ro_id = RoxeSendData.user_account_b

        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")

        for amount in [10 + RoxeSendData.kyc_limit_level1["24HourAmount"], 10 + RoxeSendData.kyc_limit_level2["24HourAmount"], 10 + RoxeSendData.kyc_limit_level3["24HourAmount"]]:

            pay_info, re_body = self.client.request(RoxeSendData.user_id_b, currency, amount, "hello", token=RoxeSendData.user_login_token_c)
            self.checkCodeMessage(pay_info)
            self.checkRequestOrderInfo(pay_info["data"], re_body, RoxeSendData.user_id_c, RoxeSendData.user_id_b)
            tx_id = pay_info["data"]["transactionId"]

            # 查询交易详情
            tx_info = self.client.getTransactionDetail(tx_id, token=RoxeSendData.user_login_token_c)
            self.checkCodeMessage(tx_info)
            self.assertEqual(tx_info["data"]["status"], "Temporary")
            self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

            # B查询到的request订单
            tx_h, tx_body = self.client.getTransactionHistory(token=RoxeSendData.user_login_token_b)
            tx_id_b = tx_h["data"]["data"][0]["transactionId"]

            tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
            self.checkCodeMessage(tx_info)
            self.assertEqual(tx_info["data"]["status"], "Temporary")
            self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id_c)

            # 取消交易
            cancel_info = self.client.cancelTransaction(tx_id, token=RoxeSendData.user_login_token_c)
            self.checkCodeMessage(cancel_info)
            self.assertTrue(cancel_info["data"])

            # 查询交易详情
            tx_info = self.client.getTransactionDetail(tx_id, token=RoxeSendData.user_login_token_c)
            self.checkCodeMessage(tx_info)
            self.assertEqual(tx_info["data"]["status"], "Cancelled")
            self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

            tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
            self.checkCodeMessage(tx_info)
            self.assertEqual(tx_info["data"]["status"], "Cancelled")
            self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id_c)

            from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
            self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
            to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
            self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
            self.assertEqual(from_balance2, from_balance, msg="from账户资产不正确")
            self.assertEqual(to_balance2, to_balance, msg="to账户资产不正确")

    def test_195_payRequest_notKycAmountMoreThanLimit(self):
        """
        request，没有经过kyc，即级别L1的用户不能进行支付
        """
        currency = RoxeSendData.currency[0]
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_c

        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")

        for amount in [10 + RoxeSendData.kyc_limit_level1["24HourAmount"], 10 + RoxeSendData.kyc_limit_level2["24HourAmount"], 10 + RoxeSendData.kyc_limit_level3["24HourAmount"]]:

            pay_info, re_body = self.client.request(RoxeSendData.user_id_c, currency, amount, "hello")
            tx_id = pay_info["data"]["transactionId"]

            # A查询交易详情
            tx_info = self.client.getTransactionDetail(tx_id)
            self.checkCodeMessage(tx_info)
            self.assertEqual(tx_info["data"]["status"], "Temporary")
            self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_c)
            # B查询到的request订单
            tx_h, tx_body = self.client.getTransactionHistory(token=RoxeSendData.user_login_token_c)
            tx_id_b = tx_h["data"]["data"][0]["transactionId"]

            tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_c)
            self.checkCodeMessage(tx_info)
            self.assertEqual(tx_info["data"]["status"], "Temporary")
            self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

            ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
            b_type = RoxeSendEnum.BUSINESS_TYPE_REQUEST.value
            rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount)
            # 另外一方进行支付
            pay_request, pay_body = self.client.payRequest(
                tx_id_b, from_ro_id, rate_info["data"]["exchangeRate"], currency,
                rate_info["data"]["sendAmount"], currency, rate_info["data"]["receiveAmount"],
                2, "pay request", RoxeSendData.user_login_token_c
            )
            self.checkCodeMessage(pay_request, "RSD10401", "Kyc not pass,level: L2")
            self.assertIsNone(pay_request["data"])
            # 取消交易
            cancel_info = self.client.cancelTransaction(tx_id)
            self.checkCodeMessage(cancel_info)
            self.assertTrue(cancel_info["data"])

            from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
            self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
            to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
            self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
            self.assertAlmostEqual(from_balance2 - from_balance, 0, msg="from账户资产不正确", delta=0.1**6)
            self.assertAlmostEqual(to_balance2, to_balance, msg="to账户资产不正确", delta=0.1**6)

    def test_196_deposit_kaKycAmountMoreThanLimit(self):
        """
        充值下单, 经过ka，即级别L2的用户调用超出金额失败
        """
        currency = RoxeSendData.currency[0]
        user_balance = self.client.listCurrencyBalance(currency, token=RoxeSendData.user_login_token_b)

        deposit_info, re_body = self.client.deposit(currency, 10 + RoxeSendData.kyc_limit_level2["24HourAmount"], token=RoxeSendData.user_login_token_b)
        self.checkCodeMessage(deposit_info, "RSD10402", "Kyc not pass,level: L3")
        self.assertIsNone(deposit_info["data"])

        deposit_info, re_body = self.client.deposit(currency, 10 + RoxeSendData.kyc_limit_level3["24HourAmount"], token=RoxeSendData.user_login_token_b)
        self.checkCodeMessage(deposit_info, "RSD10402", "Kyc not pass,level: L3")
        self.assertIsNone(deposit_info["data"])

        user_balance2 = self.client.listCurrencyBalance(currency, token=RoxeSendData.user_login_token_b)
        self.assertEqual(user_balance2, user_balance, "账户资产不正确")

    def test_197_withdraw_kaKycAmountMoreThanLimit(self):
        """
        提现, 经过ka，即级别L2的用户调用超出金额失败
        """
        currency = RoxeSendData.currency[0]
        r_accounts = self.client.listReceiverAccount(currency, token=RoxeSendData.user_login_token_b)["data"]
        if len(r_accounts) == 0:
            bind_res, r_body = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_1, RTSData.node_code, token=RoxeSendData.user_login_token_b)
            out_account = bind_res["data"]
        else:
            out_account = r_accounts[0]
        user_balance = self.client.listCurrencyBalance(currency, token=RoxeSendData.user_login_token_b)

        withdraw_info = self.client.withdraw(currency, 10 + RoxeSendData.kyc_limit_level2["24HourAmount"], out_account["accountId"], RTSData.node_code, token=RoxeSendData.user_login_token_b)
        self.checkCodeMessage(withdraw_info, "RSD10402", "Kyc not pass,level: L3")
        self.assertIsNone(withdraw_info["data"])

        withdraw_info = self.client.withdraw(currency, 10 + RoxeSendData.kyc_limit_level3["24HourAmount"], out_account["accountId"], RTSData.node_code, token=RoxeSendData.user_login_token_b)
        self.checkCodeMessage(withdraw_info, "RSD10402", "Kyc not pass,level: L3")
        self.assertIsNone(withdraw_info["data"])
        user_balance2 = self.client.listCurrencyBalance(currency, token=RoxeSendData.user_login_token_b)
        self.client.logger.info(f"资产变化了: {user_balance2['data']['amount'] - user_balance['data']['amount']}")
        self.assertAlmostEqual(user_balance['data']['amount'] - user_balance2['data']['amount'], 0, delta=0.1**6)

    def test_198_sendToRoAccount_kaKycAmountMoreThanLimit(self):
        """
        Pay，没有经过kyc，即级别L1的用户调用失败
        """
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        from_ro_id = RoxeSendData.user_account_b
        to_ro_id = RoxeSendData.user_account_c

        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")

        for amount in [10 + RoxeSendData.kyc_limit_level2["24HourAmount"], 10 + RoxeSendData.kyc_limit_level3["24HourAmount"]]:
            rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount, token=RoxeSendData.user_login_token_b)
            pay_info, re_body = self.client.sendToRoxeAccount(
                to_ro_id, rate_info["data"]["exchangeRate"], currency, amount, currency, rate_info["data"]["receiveAmount"], ensure_side, 2, token=RoxeSendData.user_login_token_b
            )
            self.checkCodeMessage(pay_info, "RSD10402", "Kyc not pass,level: L3")
            self.assertIsNone(pay_info["data"])

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertEqual(from_balance2, from_balance, msg="from账户资产不正确")
        self.assertEqual(to_balance2, to_balance, msg="to账户资产不正确")

    def test_199_request_kaKycAmountMoreThanLimit(self):
        """
        request，经过ka的kyc，即级别L2的用户可以发起request, 不支付，撤销交易
        """
        currency = RoxeSendData.currency[0]
        from_ro_id = RoxeSendData.user_account_b
        to_ro_id = RoxeSendData.user_account_c

        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")

        for amount in [10 + RoxeSendData.kyc_limit_level2["24HourAmount"], 10 + RoxeSendData.kyc_limit_level3["24HourAmount"]]:

            pay_info, re_body = self.client.request(RoxeSendData.user_id_c, currency, amount, "hello", token=RoxeSendData.user_login_token_b)
            self.checkCodeMessage(pay_info)
            self.checkRequestOrderInfo(pay_info["data"], re_body, RoxeSendData.user_id_b, RoxeSendData.user_id_c)
            tx_id = pay_info["data"]["transactionId"]

            # 查询交易详情
            tx_info = self.client.getTransactionDetail(tx_id, token=RoxeSendData.user_login_token_b)
            self.checkCodeMessage(tx_info)
            self.assertEqual(tx_info["data"]["status"], "Temporary")
            self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_c)

            # B查询到的request订单
            tx_h, tx_body = self.client.getTransactionHistory(token=RoxeSendData.user_login_token_c)
            tx_id_b = tx_h["data"]["data"][0]["transactionId"]

            tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_c)
            self.checkCodeMessage(tx_info)
            self.assertEqual(tx_info["data"]["status"], "Temporary")
            self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id_b)

            # 取消交易
            cancel_info = self.client.cancelTransaction(tx_id, token=RoxeSendData.user_login_token_b)
            self.checkCodeMessage(cancel_info)
            self.assertTrue(cancel_info["data"])

            # 查询交易详情
            tx_info = self.client.getTransactionDetail(tx_id, token=RoxeSendData.user_login_token_b)
            self.checkCodeMessage(tx_info)
            self.assertEqual(tx_info["data"]["status"], "Cancelled")
            self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_c)

            tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_c)
            self.checkCodeMessage(tx_info)
            self.assertEqual(tx_info["data"]["status"], "Cancelled")
            self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id_b)

            from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
            self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
            to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
            self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
            self.assertEqual(from_balance2, from_balance, msg="from账户资产不正确")
            self.assertEqual(to_balance2, to_balance, msg="to账户资产不正确")

    def test_200_payRequest_kaKycAmountMoreThanLimit(self):
        """
        request，没有经过kyc，即级别L1的用户不能进行支付
        """
        currency = RoxeSendData.currency[0]
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b

        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")

        for amount in [10 + RoxeSendData.kyc_limit_level2["24HourAmount"], 10 + RoxeSendData.kyc_limit_level3["24HourAmount"]]:

            pay_info, re_body = self.client.request(RoxeSendData.user_id_b, currency, amount, "hello")
            tx_id = pay_info["data"]["transactionId"]

            # A查询交易详情
            tx_info = self.client.getTransactionDetail(tx_id)
            self.checkCodeMessage(tx_info)
            self.assertEqual(tx_info["data"]["status"], "Temporary")
            self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)
            # B查询到的request订单
            tx_h, tx_body = self.client.getTransactionHistory(token=RoxeSendData.user_login_token_b)
            tx_id_b = tx_h["data"]["data"][0]["transactionId"]

            tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
            self.checkCodeMessage(tx_info)
            self.assertEqual(tx_info["data"]["status"], "Temporary")
            self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

            ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
            b_type = RoxeSendEnum.BUSINESS_TYPE_REQUEST.value
            rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount)
            # 另外一方进行支付
            pay_request, pay_body = self.client.payRequest(
                tx_id_b, from_ro_id, rate_info["data"]["exchangeRate"], currency,
                rate_info["data"]["sendAmount"], currency, rate_info["data"]["receiveAmount"],
                2, "pay request", RoxeSendData.user_login_token_b
            )
            self.checkCodeMessage(pay_request, "RSD10402", "Kyc not pass,level: L3")
            self.assertIsNone(pay_request["data"])
            # 取消交易
            cancel_info = self.client.cancelTransaction(tx_id)
            self.checkCodeMessage(cancel_info)
            self.assertTrue(cancel_info["data"])

            from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
            self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
            to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
            self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
            self.assertAlmostEqual(from_balance2 - from_balance, 0, msg="from账户资产不正确", delta=0.1**6)
            self.assertAlmostEqual(to_balance2, to_balance, msg="to账户资产不正确", delta=0.1**6)

    def test_201_deposit_kmKycAmountMoreThanLimit(self):
        """
        充值下单, 经过km，即级别L3的用户调用超出金额失败
        """
        currency = RoxeSendData.currency[0]
        user_balance = self.client.listCurrencyBalance(currency)

        deposit_info, re_body = self.client.deposit(currency, 10 + RoxeSendData.kyc_limit_level3["24HourAmount"])
        self.checkCodeMessage(deposit_info, "RSD10403", "You’ve reached your daily transaction limit. Please try again tomorrow")
        self.assertIsNone(deposit_info["data"])

        user_balance2 = self.client.listCurrencyBalance(currency)
        self.assertEqual(user_balance2, user_balance, "账户资产不正确")

    def test_202_withdraw_kmKycAmountMoreThanLimit(self):
        """
        提现, 经过km，即级别L3的用户调用超出金额失败
        """
        currency = RoxeSendData.currency[0]
        r_accounts = self.client.listReceiverAccount(currency)["data"]
        if len(r_accounts) == 0:
            bind_res, r_body = self.client.bindReceiverAccount(currency, RoxeSendData.user_outer_bank_1, RTSData.node_code)
            out_account = bind_res["data"]
        else:
            out_account = r_accounts[0]
        user_balance = self.client.listCurrencyBalance(currency)

        withdraw_info = self.client.withdraw(currency, 10 + RoxeSendData.kyc_limit_level3["24HourAmount"], out_account["accountId"], RTSData.node_code)
        self.checkCodeMessage(withdraw_info, "RSD10403", "You’ve reached your daily transaction limit. Please try again tomorrow")
        self.assertIsNone(withdraw_info["data"])

        user_balance2 = self.client.listCurrencyBalance(currency)
        self.client.logger.info(f"资产变化了: {user_balance2['data']['amount'] - user_balance['data']['amount']}")
        self.assertAlmostEqual(user_balance['data']['amount'] - user_balance2['data']['amount'], 0, delta=0.1**6)

    def test_203_sendToRoAccount_kmKycAmountMoreThanLimit(self):
        """
        Pay，经过km，即级别L3的用户调用超出金额失败
        """
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_c

        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")

        for amount in [10 + RoxeSendData.kyc_limit_level3["24HourAmount"]]:
            rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount)
            pay_info, re_body = self.client.sendToRoxeAccount(
                to_ro_id, rate_info["data"]["exchangeRate"], currency, amount, currency, rate_info["data"]["receiveAmount"], ensure_side, 2
            )
            self.checkCodeMessage(pay_info, "RSD10403", "You’ve reached your daily transaction limit. Please try again tomorrow")
            self.assertIsNone(pay_info["data"])

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertEqual(from_balance2, from_balance, msg="from账户资产不正确")
        self.assertEqual(to_balance2, to_balance, msg="to账户资产不正确")

    def test_204_request_kmKycAmountMoreThanLimit(self):
        """
        request，经过km，即级别L3的用户调用超出金额可以发起request, 不支付，撤销交易
        """
        currency = RoxeSendData.currency[0]
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_c

        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")

        for amount in [10 + RoxeSendData.kyc_limit_level3["24HourAmount"]]:

            pay_info, re_body = self.client.request(RoxeSendData.user_id_c, currency, amount, "hello")
            self.checkCodeMessage(pay_info)
            self.checkRequestOrderInfo(pay_info["data"], re_body, RoxeSendData.user_id, RoxeSendData.user_id_c)
            tx_id = pay_info["data"]["transactionId"]

            # 查询交易详情
            tx_info = self.client.getTransactionDetail(tx_id)
            self.checkCodeMessage(tx_info)
            self.assertEqual(tx_info["data"]["status"], "Temporary")
            self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_c)

            # B查询到的request订单
            tx_h, tx_body = self.client.getTransactionHistory(token=RoxeSendData.user_login_token_c)
            tx_id_b = tx_h["data"]["data"][0]["transactionId"]

            tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_c)
            self.checkCodeMessage(tx_info)
            self.assertEqual(tx_info["data"]["status"], "Temporary")
            self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

            # 取消交易
            cancel_info = self.client.cancelTransaction(tx_id)
            self.checkCodeMessage(cancel_info)
            self.assertTrue(cancel_info["data"])

            # 查询交易详情
            tx_info = self.client.getTransactionDetail(tx_id)
            self.checkCodeMessage(tx_info)
            self.assertEqual(tx_info["data"]["status"], "Cancelled")
            self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_c)

            tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_c)
            self.checkCodeMessage(tx_info)
            self.assertEqual(tx_info["data"]["status"], "Cancelled")
            self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

            from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
            self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
            to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
            self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
            self.assertEqual(from_balance2, from_balance, msg="from账户资产不正确")
            self.assertEqual(to_balance2, to_balance, msg="to账户资产不正确")

    def test_205_payRequest_kmKycAmountMoreThanLimit(self):
        """
        request，经过km，即级别L3的用户调用超出金额不能支付
        """
        currency = RoxeSendData.currency[0]
        from_ro_id = RoxeSendData.user_account_c
        to_ro_id = RoxeSendData.user_account

        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")

        for amount in [10 + RoxeSendData.kyc_limit_level3["24HourAmount"]]:

            pay_info, re_body = self.client.request(RoxeSendData.user_id, currency, amount, "hello", token=RoxeSendData.user_login_token_c)
            tx_id = pay_info["data"]["transactionId"]

            # A查询交易详情
            tx_info = self.client.getTransactionDetail(tx_id, token=RoxeSendData.user_login_token_c)
            self.checkCodeMessage(tx_info)
            self.assertEqual(tx_info["data"]["status"], "Temporary")
            self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id)
            # B查询到的request订单
            tx_h, tx_body = self.client.getTransactionHistory()
            tx_id_b = tx_h["data"]["data"][0]["transactionId"]

            tx_info = self.client.getTransactionDetail(tx_id_b)
            self.checkCodeMessage(tx_info)
            self.assertEqual(tx_info["data"]["status"], "Temporary")
            self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id_c)

            ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
            b_type = RoxeSendEnum.BUSINESS_TYPE_REQUEST.value
            rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount)
            # 另外一方进行支付
            pay_request, pay_body = self.client.payRequest(
                tx_id_b, from_ro_id, rate_info["data"]["exchangeRate"], currency,
                rate_info["data"]["sendAmount"], currency, rate_info["data"]["receiveAmount"],
                2, "pay request"
            )
            self.checkCodeMessage(pay_request, "RSD10403", "You’ve reached your daily transaction limit. Please try again tomorrow")
            self.assertIsNone(pay_request["data"])
            # 取消交易
            cancel_info = self.client.cancelTransaction(tx_id, token=RoxeSendData.user_login_token_c)
            self.checkCodeMessage(cancel_info)
            self.assertTrue(cancel_info["data"])

            from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
            self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
            to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
            self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
            self.assertAlmostEqual(from_balance2 - from_balance, 0, msg="from账户资产不正确", delta=0.1**6)
            self.assertAlmostEqual(to_balance2, to_balance, msg="to账户资产不正确", delta=0.1**6)

    # 关于订单分享的用例

    def test_206_getOrderShareList_all(self):
        """
        获取分享订单，获取所有的分享订单
        """
        order_share, share_params = self.client.getOrderShareList(o_type=1, scope=0, p_size=500)
        self.checkCodeMessage(order_share)

        self.checkOrderShareList(order_share["data"], RoxeSendData.user_id, share_params)

    def test_207_getOrderShareList_allPublic(self):
        """
        获取分享订单，获取所有公开的分享订单
        """
        order_share, share_params = self.client.getOrderShareList(o_type=1, scope=2, p_size=500)
        self.checkCodeMessage(order_share)

        self.checkOrderShareList(order_share["data"], RoxeSendData.user_id, share_params)

    def test_208_getOrderShareList_allPrivate(self):
        """
        获取分享订单，获取所有私有的分享订单
        """
        order_share, share_params = self.client.getOrderShareList(o_type=1, scope=1, p_size=500)
        self.checkCodeMessage(order_share)

        self.checkOrderShareList(order_share["data"], RoxeSendData.user_id, share_params)

    def test_209_getOrderShareList_selfAll(self):
        """
        获取分享订单, 查询自己所有的数据
        """
        order_share, share_params = self.client.getOrderShareList(o_type=3, scope=0, user_id=RoxeSendData.user_id)
        self.checkCodeMessage(order_share)

        self.checkOrderShareList(order_share["data"], RoxeSendData.user_id, share_params)

    def test_210_getOrderShareList_selfPublic(self):
        """
        获取分享订单, 查询自己公开的数据
        """
        order_share, share_params = self.client.getOrderShareList(o_type=3, scope=2)
        self.checkCodeMessage(order_share)

        self.checkOrderShareList(order_share["data"], RoxeSendData.user_id, share_params)

    def test_211_getOrderShareList_selfPrivate(self):
        """
        获取分享订单, 查询自己私有的数据
        """
        order_share, share_params = self.client.getOrderShareList(o_type=3, scope=1)
        self.checkCodeMessage(order_share)

        self.checkOrderShareList(order_share["data"], RoxeSendData.user_id, share_params)

    def test_212_getOrderShareList_otherAll(self):
        """
        获取分享订单, 查询某个人所有的数据
        """
        order_share, share_params = self.client.getOrderShareList(o_type=2, scope=0, user_id=RoxeSendData.user_id_b)
        self.checkCodeMessage(order_share)

        self.checkOrderShareList(order_share["data"], RoxeSendData.user_id, share_params)

    def test_213_getOrderShareList_otherPublic(self):
        """
        获取分享订单, 查询某个人公开的数据
        """
        order_share, share_params = self.client.getOrderShareList(o_type=2, scope=2, user_id=RoxeSendData.user_id_b)
        self.checkCodeMessage(order_share)

        self.checkOrderShareList(order_share["data"], RoxeSendData.user_id, share_params)

    def test_214_getOrderShareList_otherPrivate(self):
        """
        获取分享订单, 查询某个人私有的数据
        """
        order_share, share_params = self.client.getOrderShareList(o_type=2, scope=1, user_id=RoxeSendData.user_id_b)
        self.checkCodeMessage(order_share)

        self.checkOrderShareList(order_share["data"], RoxeSendData.user_id, share_params)

    def test_215_getOrderShareList_depositNotInOrderShareList(self):
        """
        获取分享订单，充值的订单不在订单分享列表中
        """
        order_share, share_params = self.client.getOrderShareList(o_type=1, scope=0)
        self.checkCodeMessage(order_share)
        self.checkOrderShareList(order_share["data"], RoxeSendData.user_id, share_params)

        self.test_020_deposit_selectAchPay()

        order_share2, share_params = self.client.getOrderShareList(o_type=1, scope=0)
        self.checkCodeMessage(order_share2)
        self.checkOrderShareList(order_share2["data"], RoxeSendData.user_id, share_params)
        self.assertEqual(order_share["data"]["data"], order_share2["data"]["data"])

    def test_216_getOrderShareList_withdrawNotInOrderShareList(self):
        """
        获取分享订单，提现的订单不在订单分享列表中
        """
        order_share, share_params = self.client.getOrderShareList(o_type=1, scope=0)
        self.checkCodeMessage(order_share)
        self.checkOrderShareList(order_share["data"], RoxeSendData.user_id, share_params)

        self.test_021_withdraw()

        order_share2, share_params = self.client.getOrderShareList(o_type=1, scope=0)
        self.checkCodeMessage(order_share2)
        self.checkOrderShareList(order_share2["data"], RoxeSendData.user_id, share_params)
        self.assertEqual(order_share["data"]["data"], order_share2["data"]["data"])

    def test_217_getOrderShareList_payOrderInOrderShareList(self):
        """
        获取分享订单, pay完成的订单在订单分享列表中
        """
        order_share, share_params = self.client.getOrderShareList(o_type=1, scope=0)
        self.checkCodeMessage(order_share)
        self.checkOrderShareList(order_share["data"], RoxeSendData.user_id, share_params)

        amount = 4.35
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b
        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")

        daily_limit, ninety_day_limit, left_day = self.client.calKycLimitAmount(self, RoxeSendData.user_id, RoxeSendData.user_login_token)

        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount)
        pay_info, re_body = self.client.sendToRoxeAccount(
            to_ro_id, rate_info["data"]["exchangeRate"], currency, amount, currency, rate_info["data"]["receiveAmount"], ensure_side, 2
        )
        self.checkCodeMessage(pay_info)
        self.checkSenToRoAccountOrderInfo(pay_info["data"], re_body, RoxeSendData.user_id, RoxeSendData.user_id_b)
        tx_id = pay_info["data"]["transactionId"]

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Submitted")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        # 未支付前，订单不显示在分享列表中
        order_share2, share_params = self.client.getOrderShareList(o_type=1, scope=0)
        self.assertEqual(order_share2["data"], order_share["data"])

        # 选择wallet支付
        order_id = tx_info["data"]["orderId"]
        self.rps_client.submitPayOrderTransferToRoxeAccount(from_ro_id, to_ro_id, amount, businessType="transfer", expect_pay_success=False, businessOrderNo=order_id)
        self.waitOrderStatusInDB(order_id, "Processing")

        # 支付中，订单不显示在分享列表中
        order_share2, share_params = self.client.getOrderShareList(o_type=1, scope=0)
        self.assertEqual(order_share2["data"], order_share["data"])
        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        self.waitOrderStatusInDB(order_id)

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Complete")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertAlmostEqual(from_balance - from_balance2, amount, msg="from账户资产不正确", delta=0.1**6)
        self.assertAlmostEqual(to_balance2 - to_balance, amount, msg="to账户资产不正确", delta=0.1**6)

        daily_limit2, ninety_day_limit2, left_day2 = self.client.calKycLimitAmount(self, RoxeSendData.user_id, RoxeSendData.user_login_token)
        self.assertAlmostEqual(daily_limit - daily_limit2, amount, delta=0.1**6)
        self.assertAlmostEqual(ninety_day_limit - ninety_day_limit2, amount, delta=0.1**6)

        order_share3, share_params = self.client.getOrderShareList(o_type=1, scope=0)
        self.checkCodeMessage(order_share3)
        self.checkOrderShareList(order_share3["data"], RoxeSendData.user_id, share_params)
        self.assertEqual(order_share3["data"]["data"][0]["orderId"], pay_info["data"]["orderId"])

    def test_218_getOrderShareList_payRequestOrderInOrderShareList(self):
        """
        获取分享订单，request支付完的订单在订单分享列表中
        """
        order_share, share_params = self.client.getOrderShareList(o_type=1, scope=2)
        self.checkCodeMessage(order_share)
        self.checkOrderShareList(order_share["data"], RoxeSendData.user_id, share_params)

        amount = 4.35
        currency = RoxeSendData.currency[0]
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b

        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")

        daily_limit, ninety_day_limit, left_day = self.client.calKycLimitAmount(self, RoxeSendData.user_id_b, RoxeSendData.user_login_token_b)

        pay_info, re_body = self.client.request(RoxeSendData.user_id_b, currency, amount, "hello")
        tx_id = pay_info["data"]["transactionId"]

        order_share2, share_params = self.client.getOrderShareList(o_type=1, scope=2)
        self.assertEqual(order_share2["data"], order_share["data"])

        # A查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Temporary")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        # B查询到的交易
        tx_h, tx_body = self.client.getTransactionHistory(token=RoxeSendData.user_login_token_b)
        tx_id_b = tx_h["data"]["data"][0]["transactionId"]

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Temporary")
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_REQUEST.value
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount)
        # 另外一方进行支付
        pay_request, pay_body = self.client.payRequest(
            tx_id_b, from_ro_id, rate_info["data"]["exchangeRate"], currency,
            rate_info["data"]["sendAmount"], currency, rate_info["data"]["receiveAmount"],
            2, "pay request", RoxeSendData.user_login_token_b
        )
        self.checkCodeMessage(pay_request)
        self.checkPayRequestOrderInfo(pay_request["data"], pay_body, RoxeSendData.user_id_b, RoxeSendData.user_id)

        # 选择wallet支付
        order_id = pay_request["data"]["orderId"]
        pay_amount = ApiUtils.parseNumberDecimal(float(rate_info["data"]["sendAmount"]))
        self.rps_client.submitPayOrderTransferToRoxeAccount(to_ro_id, from_ro_id, pay_amount, businessType="transfer", expect_pay_success=False, businessOrderNo=order_id)
        self.waitOrderStatusInDB(order_id, "Processing")

        order_share3, share_params = self.client.getOrderShareList(o_type=1, scope=2)
        self.assertEqual(order_share3["data"], order_share["data"])
        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        self.waitOrderStatusInDB(order_id)

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Complete")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)
        order_id_a = tx_info["data"]["orderId"]

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Complete")
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertAlmostEqual(from_balance2 - from_balance, amount, msg="from账户资产不正确", delta=0.1**6)
        self.assertAlmostEqual(to_balance - to_balance2, pay_amount, msg="to账户资产不正确", delta=0.1**6)

        daily_limit2, ninety_day_limit2, left_day2 = self.client.calKycLimitAmount(self, RoxeSendData.user_id_b, RoxeSendData.user_login_token_b)
        self.assertAlmostEqual(daily_limit - daily_limit2, amount, delta=0.1**6)
        self.assertAlmostEqual(ninety_day_limit - ninety_day_limit2, amount, delta=0.1**6)

        order_share4, share_params4 = self.client.getOrderShareList(o_type=1, scope=2)
        self.checkCodeMessage(order_share4)
        self.checkOrderShareList(order_share4["data"], RoxeSendData.user_id, share_params4)
        self.assertEqual(order_share4["data"]["data"][0]["orderId"], order_id_a)

        order_share_b, share_params_b = self.client.getOrderShareList(o_type=1, scope=2, token=RoxeSendData.user_login_token_b)
        self.checkCodeMessage(order_share_b)
        self.checkOrderShareList(order_share_b["data"], RoxeSendData.user_id_b, share_params_b)
        self.assertEqual(order_share_b["data"]["data"][0]["orderId"], order_id)

    def test_219_getOrderShareList_requestDeclinedOrderNotInOrderShareList(self):
        """
        获取分享订单，request拒绝的订单不在订单分享列表中
        """
        order_share, share_params = self.client.getOrderShareList(o_type=1, scope=0)
        self.checkCodeMessage(order_share)
        self.checkOrderShareList(order_share["data"], RoxeSendData.user_id, share_params)

        self.test_026_request_declineRequest()

        order_share2, share_params = self.client.getOrderShareList(o_type=1, scope=0)
        self.checkCodeMessage(order_share2)
        self.checkOrderShareList(order_share2["data"], RoxeSendData.user_id, share_params)
        self.assertEqual(order_share["data"]["data"], order_share2["data"]["data"])

    def test_220_getOrderShareList_requestCanceledOrderNotInOrderShareList(self):
        """
        获取分享订单，request取消的订单不在订单分享列表中
        """
        order_share, share_params = self.client.getOrderShareList(o_type=1, scope=0)
        self.checkCodeMessage(order_share)
        self.checkOrderShareList(order_share["data"], RoxeSendData.user_id, share_params)

        self.test_025_request_notPayThenCancelRequest()

        order_share2, share_params = self.client.getOrderShareList(o_type=1, scope=0)
        self.checkCodeMessage(order_share2)
        self.checkOrderShareList(order_share2["data"], RoxeSendData.user_id, share_params)
        self.assertEqual(order_share["data"]["data"], order_share2["data"]["data"])

    def test_221_getOrderShareTransactionId(self):
        """
        根据订单分享的订单id获取交易id
        """
        order_share, share_params = self.client.getOrderShareList(o_type=3, scope=2, p_size=5)
        order_id = order_share["data"]["data"][0]["orderId"]

        order_detail = self.client.getOrderShareTransactionId(order_id)
        self.checkCodeMessage(order_detail)
        self.assertIsNotNone(order_detail["data"])
        if RoxeSendData.is_check_db:
            sql = f"select * from roxe_send_app.ro_transaction_history where order_id='{order_id}'"
            order_db = self.mysql.exec_sql_query(sql)
            self.assertEqual(order_detail["data"], order_db[0]["id"], f"数据库数据:{order_db}")

    def test_222_getShareOrderComment(self):
        """
        获取当前分享订单的评论
        """
        order_share, share_params = self.client.getOrderShareList(o_type=1, scope=2, p_size=1)
        order_id = order_share["data"]["data"][0]["orderId"]

        comments = self.client.getOrderComment(order_id)
        self.checkCodeMessage(comments)
        self.assertEqual(comments["data"]["totalCount"], order_share["data"]["data"][0]["commentCoune"])
        self.checkOrderShareComments(comments["data"], order_id)

    def test_223_postComment(self):
        """
        对订单发表评论
        """
        order_share, share_params = self.client.getOrderShareList(o_type=1, scope=2, p_size=1)
        order_id = order_share["data"]["data"][0]["orderId"]

        comment = "order share test" + str(int(time.time() * 1000))
        post_comment = self.client.postComment(order_id, comment)
        self.checkCodeMessage(post_comment)
        self.assertIsNone(post_comment["data"])

        comments = self.client.getOrderComment(order_id)
        self.checkCodeMessage(comments)
        self.assertEqual(comments["data"]["totalCount"], order_share["data"]["data"][0]["commentCoune"] + 1)
        self.checkOrderShareComments(comments["data"], order_id, comment, RoxeSendData.user_id)

    def test_224_deleteComment(self):
        """
        对订单发表评论, 删除评论
        """
        order_share, share_params = self.client.getOrderShareList(o_type=1, scope=2, p_size=1)
        order_id = order_share["data"]["data"][0]["orderId"]

        comment = "order share test" + str(int(time.time() * 1000))
        post_comment = self.client.postComment(order_id, comment)
        self.checkCodeMessage(post_comment)
        self.assertIsNone(post_comment["data"])

        comments = self.client.getOrderComment(order_id)
        self.checkCodeMessage(comments)
        self.assertEqual(comments["data"]["totalCount"], order_share["data"]["data"][0]["commentCoune"] + 1)
        self.checkOrderShareComments(comments["data"], order_id, comment, RoxeSendData.user_id)

        delete_comment = self.client.deleteComment(comments["data"]["data"][0]["id"], RoxeSendData.user_id)
        self.checkCodeMessage(delete_comment)

        comments = self.client.getOrderComment(order_id)
        self.checkCodeMessage(comments)
        self.assertEqual(comments["data"]["totalCount"], order_share["data"]["data"][0]["commentCoune"])
        self.checkOrderShareComments(comments["data"], order_id)

    def test_225_clickPraise(self):
        """
        获取点赞列表，然后点赞, 取消点赞
        """
        order_share, share_params = self.client.getOrderShareList(o_type=1, scope=2, p_size=100)
        order_info = [i for i in order_share["data"]["data"] if i["comment"]]
        order_id = order_info[0]["orderId"]
        comments = self.client.getOrderComment(order_id)
        praise_list = self.client.getOrderSharePraise(order_id)
        self.checkCodeMessage(praise_list)
        self.assertEqual(praise_list["data"]["praiseCount"], order_info[0]["praiseCount"])
        self.assertEqual(praise_list["data"]["isPraise"], order_info[0]["praise"])
        if praise_list["data"]["praiseCount"] == 0:
            self.assertEqual(praise_list["data"]["userInfoList"], [])
        user_name = comments["data"]["data"][0]["userInfo"]["nickName"]

        click_praise = self.client.clickPraise(order_id, user_name, 0)
        self.checkCodeMessage(click_praise)
        praise_list = self.client.getOrderSharePraise(order_id)
        self.checkCodeMessage(praise_list)
        self.assertEqual(praise_list["data"]["praiseCount"], order_info[0]["praiseCount"] + 1)
        self.assertEqual(praise_list["data"]["isPraise"], not order_info[0]["praise"])
        click_user = [i for i in praise_list["data"]["userInfoList"] if i["userId"] == RoxeSendData.user_id]
        self.checkOrderShareUserInfoFromDB(click_user[0], RoxeSendData.user_id)

        click_praise = self.client.clickPraise(order_id, user_name, 1)
        self.checkCodeMessage(click_praise)
        praise_list = self.client.getOrderSharePraise(order_id)
        self.checkCodeMessage(praise_list)
        self.assertEqual(praise_list["data"]["praiseCount"], order_info[0]["praiseCount"])
        self.assertEqual(praise_list["data"]["isPraise"], order_info[0]["praise"])
        if praise_list["data"]["praiseCount"] == 0:
            self.assertEqual(praise_list["data"]["userInfoList"], [])

    # 礼品卡相关接口

    def checkGiftCardListWithDB(self, card_list):
        if RoxeSendData.is_check_db:
            sql = "select * from roxe_gift.gift_card_batch a left join roxe_gift.merchant_account b on a.merchant_id = b.merchant_id where a.status=4 "
            db_res = self.mysql.exec_sql_query(sql)
            self.assertEqual(card_list["totalCount"], len(db_res))
            self.assertTrue(len(card_list["data"]) <= card_list["pageSize"])
            for card_info in card_list["data"]:
                db_card = [i for i in db_res if i["giftCardBrand"] == card_info["brandName"]]
                self.client.logger.info(f"数据库数据: {db_card}")
                self.assertTrue(len(db_card) > 0, f"{card_info['brandName']} 礼品卡在数据库中未找到可用的相关数据")
                self.assertEqual(card_info["cashback"], float(db_card[0]["userCashback"]), "返利比和数据库不一致")
                self.assertEqual(card_info["storeId"], db_card[0]["merchantId"], "storeId和数据库不一致")
                merchant_info = self.mysql.exec_sql_query(f"select * from roxe_commerce.merchant_info where merchant_name='{db_card[0]['merchantName']}'")
                self.assertEqual(card_info["storeImg"], merchant_info[0]["logo"], "商户图片和数据库不一致")

    def checkGiftCardDetailWithDB(self, card_detail, store_id):
        if RoxeSendData.is_check_db:
            sql = f"select * from roxe_gift.gift_card_batch a left join roxe_gift.merchant_account b on a.merchant_id = b.merchant_id where a.merchant_id='{store_id}'"
            db_res = self.mysql.exec_sql_query(sql)
            self.client.logger.info(f"数据库中礼品卡数据: {db_res}")
            self.assertEqual(card_detail['brandName'], db_res[0]['giftCardBrand'], f"{card_detail['brandName']} 礼品卡在数据库中未找到可用的相关数据")
            self.assertEqual(card_detail["cashback"], float(db_res[0]["userCashback"]), "返利比和数据库不一致")
            self.assertEqual(card_detail["storeId"], store_id, "storeId和数据库不一致")
            self.assertEqual(card_detail["batchId"], str(db_res[0]['id']), "batchId和数据库不一致")
            self.assertEqual(card_detail["bannerImg"], db_res[0]['giftCardCoverUrl'], "bannerImg和数据库不一致")
            self.assertEqual(card_detail["activityValidityDescription"], db_res[0]['giftCardIntroduction'], "有效期说明和数据库不一致")
            self.assertEqual(card_detail["nonReturnableDescription"], db_res[0]['redemptionNotes'], "不可退说明和数据库不一致")
            self.assertEqual(card_detail["disclaimers"], db_res[0]['disclaimers'], "商家免责说明和数据库不一致")
            self.assertEqual(card_detail["status"], db_res[0]['status'], "status和数据库不一致")
            self.assertEqual(card_detail["minimum"], float(db_res[0]['singlePurchaseLower']), "单笔最小限额和数据库不一致")
            self.assertEqual(card_detail["maxmum"], float(db_res[0]['singlePurchaseUpper']), "单笔最大限额和数据库不一致")
            self.assertEqual(card_detail["purchaseMinimum"], float(db_res[0]['purchaseMinimum']), "单笔精度和数据库不一致")
            self.assertEqual(card_detail["giftCardCurrency"], db_res[0]['giftCardCurrency'], "giftCardCurrency和数据库不一致")
            merchant_info = self.mysql.exec_sql_query(f"select * from roxe_commerce.merchant_info where merchant_name='{db_res[0]['merchantName']}'")
            self.client.logger.info(f"数据库中商户数据: {merchant_info}")
            self.assertEqual(card_detail["storeImg"], merchant_info[0]["logo"], "商户图片和数据库不一致")
            branch_info = self.mysql.exec_sql_query(f"select * from roxe_commerce.branch_info where merchant_id='{db_res[0]['merchantId']}'")
            # 目前接口中只返回第一个门店信息
            self.client.logger.debug(f"数据库中门店数据: {branch_info}")
            self.assertEqual(card_detail["shopId"], str(branch_info[0]['id']), "店铺id和数据库不一致")
            self.assertEqual(card_detail["address"], branch_info[0]['branchAddress'], "地址和数据库不一致")
            self.assertEqual(card_detail["phone"], branch_info[0]['branchPhone'], "手机号和数据库不一致")
            self.assertEqual(card_detail["area"], branch_info[0]['branchPhoneItc'], "区号和数据库不一致")
            self.assertEqual(card_detail["storeTotal"], len(branch_info), "店铺总数和数据库不一致")

    def checkShopStoreListWithDB(self, shop_store, store_id):
        if RoxeSendData.is_check_db:
            branch_info = self.mysql.exec_sql_query(f"select * from roxe_commerce.branch_info where merchant_id='{store_id}'")
            for store in shop_store["data"]:
                db_store = [i for i in branch_info if str(i["id"]) == store["shopId"]]
                # self.client.logger.debug(f"数据库中门店数据: {branch_info}")
                # self.client.logger.info(f"{store['shopId']}在数据库中未查到: {db_store}")
                self.assertTrue(len(db_store) == 1, f"{store['shopId']}在数据库中未查到: {db_store}")
                self.assertEqual(store["shopId"], str(db_store[0]['id']), "店铺id和数据库不一致")
                self.assertEqual(store["address"], db_store[0]['branchAddress'], "地址和数据库不一致")
                self.assertEqual(store["shopName"], db_store[0]['branchName'], "地址和数据库不一致")
                self.assertEqual(store["phone"], db_store[0]['branchPhone'], "手机号和数据库不一致")
                self.assertEqual(store["area"], db_store[0]['branchPhoneItc'], "区号和数据库不一致")

    def checkGiftCardHistoryList(self, card_history, user_id, currency):
        if RoxeSendData.is_check_db:
            sql = f"select * from roxe_gift.gift_card_order a left join roxe_commerce.merchant_info b on a.merchant_id = b.id where a.user_id='{user_id}' and a.receive_currency='{currency}'and a.status not in (0, 5) order by a.create_time desc"
            db_res = self.mysql.exec_sql_query(sql)
            self.assertEqual(card_history["totalCount"], len(db_res), f"数据库有{len(db_res)}条，和接口返回的数据量不一致")
            for c_history in card_history["data"]:
                db_his = [i for i in db_res if i["orderId"] == c_history['orderId']]
                self.assertTrue(len(db_his) > 0, f"{c_history['orderId']} 订单未在数据库中找到")
                self.assertEqual(c_history["merchantId"], db_his[0]['merchantId'])
                self.assertAlmostEqual(c_history["amount"], float(db_his[0]['receiveAmount']), delta=0.1**6)
                self.assertIn(c_history["type"], ['UserPurchase', 'Consumption'])
                if db_his[0]['status'] == 3:
                    ex_status = 'Completed'
                elif db_his[0]['status'] == 4:
                    ex_status = 'Failed'
                else:
                    ex_status = 'Processing'
                self.assertEqual(c_history["status"], ex_status)
                self.assertEqual(c_history["merchantInfo"]["id"], db_his[0]['merchantId'])
                self.assertEqual(c_history["merchantInfo"]["merchantName"], db_his[0]['merchantName'])
                self.assertEqual(c_history["merchantInfo"]["logo"], db_his[0]['logo'])
                self.assertEqual(c_history["merchantInfo"]["state"], db_his[0]['state'])

    def checkGiftCardBalance(self, balances, chain_balance):
        if RoxeSendData.is_check_db:
            db_res = self.mysql.exec_sql_query("select * from roxe_gift.currency_map a left join roxe_commerce.merchant_info b on a.merchant_id=b.id")
            balances = balances if isinstance(balances, list) else [balances]
            for b in balances:
                currency_info = [i for i in db_res if i['currency'] == b['currency']][0]
                chain_b = [i for i in chain_balance if i.endswith(f' {currency_info["symbol"]}')]
                c_amount = float(chain_b[0].split(" ")[0]) if chain_b else 0
                self.assertAlmostEqual(ApiUtils.parseNumberDecimal(c_amount, 2), b['amount'], delta=0.001)
                self.assertEqual(b["merchantInfo"]['id'], currency_info['merchantId'])
                self.assertEqual(b["merchantInfo"]['logo'], currency_info['logo'])
                self.assertEqual(b["merchantInfo"]['state'], currency_info['state'])

    def test_226_getGiftCardList(self):
        """
        获取礼品卡列表
        """
        cards = self.client.getGiftCardList()
        self.checkCodeMessage(cards)
        self.checkGiftCardListWithDB(cards["data"])

    def test_227_getGiftCardDetail(self):
        """
        获取礼品卡详情
        """
        cards = self.client.getGiftCardList()
        for card_info in cards["data"]["data"]:
            card_details = self.client.getGiftCardDetail(card_info["storeId"])
            self.checkCodeMessage(card_details)
            self.checkGiftCardDetailWithDB(card_details["data"], card_info["storeId"])

    def test_228_getGiftCardShopStoreList(self):
        """
        礼品卡商户店铺列表
        """
        cards = self.client.getGiftCardList()
        for card_info in cards["data"]["data"]:
            stores = self.client.getMerchantStoreList(card_info["storeId"])
            self.checkCodeMessage(stores)
            self.checkShopStoreListWithDB(stores["data"], card_info["storeId"])

    def test_229_getGiftCardBalance(self):
        """
        钱包礼品卡资产列表
        """
        balances = self.client.listGiftBalance()
        self.checkCodeMessage(balances)
        chain_balances = self.client.chain_client.getBalance(RoxeSendData.user_account, "roxe.rg")
        self.client.logger.info(f"账户在链上的资产: {chain_balances}")
        self.checkGiftCardBalance(balances["data"], chain_balances)

    def test_230_getGiftCardBalanceByCurrency(self):
        """
        根据币种查询礼品卡的资产
        """
        chain_balances = self.client.chain_client.getBalance(RoxeSendData.user_account, "roxe.rg")
        self.client.logger.info(f"账户在链上的资产: {chain_balances}")
        cards = self.client.getGiftCardList()
        for card_info in cards["data"]["data"]:
            card_details = self.client.getGiftCardDetail(card_info["storeId"])
            balance = self.client.giftBalance(card_details['data']['giftCardCurrency'])
            if card_details['data']['giftCardCurrency'] in str(chain_balances):
                self.checkCodeMessage(balance)
                self.checkGiftCardBalance(balance["data"], chain_balances)

    def test_231_getGiftCardBalanceByCurrency_currencyNotUsed(self):
        """
        根据币种查询礼品卡的资产
        """
        balance = self.client.giftBalance('rgTESTA')
        self.checkCodeMessage(balance, "RGT10404", "You have not purchased this gift card")
        self.assertIsNone(balance["data"])

    def test_232_buyGiftCard_ach(self):
        """
        创建礼品卡购买订单, 购买礼品卡, 使用ach支付
        """
        cards = self.client.getGiftCardList()
        store_id = cards["data"]["data"][0]["storeId"]
        card_details = self.client.getGiftCardDetail(store_id)
        amount = card_details["data"]["minimum"] + 1.23
        currency = RoxeSendData.currency[0]
        order, body = self.client.createPurchaseOrder(
            card_details["data"]["batchId"], card_details["data"]["shopId"], store_id,
            card_details["data"]["giftCardCurrency"], amount, amount, currency, RoxeSendData.user_account, 2
        )
        self.checkCodeMessage(order)
        self.assertIsNotNone(order["data"])
        gift_balance = self.client.giftBalance(card_details["data"]["giftCardCurrency"])
        # self.client.openCheckOutAndSelectCard(order["data"])
        user_balance = self.client.listCurrencyBalance(currency)
        order_id = self.mysql.exec_sql_query("select business_order_no from roxe_pay_in_out.roxe_pay_in_order where id={}".format(int(order["data"])))[0]["businessOrderNo"]
        # 选择ach支付
        self.rps_client.selectAchMethodToPayOrder(int(order["data"]), amount, "USD", expect_pay_success=False, account_info=RPSData.ach_account, businessOrderNo=order_id)
        self.waitOrderStatusInDB(order_id, "Processing")

        self.waitGiftCardOrderStatusInDB(order_id)
        self.waitOrderStatusInDB(order_id)
        gift_balance2 = self.client.giftBalance(card_details["data"]["giftCardCurrency"])
        user_balance2 = self.client.listCurrencyBalance(currency)
        gift_amount = gift_balance["data"]["amount"] if gift_balance["data"] else 0
        self.assertAlmostEqual(gift_balance2["data"]["amount"] - gift_amount, amount, delta=0.1**6, msg="礼品卡数量不正确")
        self.assertAlmostEqual(user_balance2["data"]["amount"] - user_balance["data"]["amount"], amount * card_details["data"]["cashback"] / 100, delta=0.1**6, msg="订单返现数量不正确")

    def test_233_buyGiftCard_card(self):
        """
        创建礼品卡购买订单, 购买礼品卡, 使用card支付
        """
        cards = self.client.getGiftCardList()
        store_id = cards["data"]["data"][0]["storeId"]
        card_details = self.client.getGiftCardDetail(store_id)
        amount = card_details["data"]["minimum"] + 1
        currency = RoxeSendData.currency[0]
        order, body = self.client.createPurchaseOrder(
            card_details["data"]["batchId"], card_details["data"]["shopId"], store_id,
            card_details["data"]["giftCardCurrency"], amount, amount, currency, RoxeSendData.user_account, 2
        )
        self.checkCodeMessage(order)
        self.assertIsNotNone(order["data"])
        gift_balance = self.client.giftBalance(card_details["data"]["giftCardCurrency"])
        user_balance = self.client.listCurrencyBalance(currency)

        # 选择card支付
        self.client.openCheckOutAndSelectCard(order["data"])
        order_id = self.mysql.exec_sql_query("select business_order_no from roxe_pay_in_out.roxe_pay_in_order where id={}".format(int(order["data"])))[0]["businessOrderNo"]

        self.waitOrderStatusInDB(order_id, "Processing")

        self.waitGiftCardOrderStatusInDB(order_id)
        self.waitOrderStatusInDB(order_id)
        gift_balance2 = self.client.giftBalance(card_details["data"]["giftCardCurrency"])
        user_balance2 = self.client.listCurrencyBalance(currency)
        self.assertAlmostEqual(gift_balance2["data"]["amount"] - gift_balance["data"]["amount"], amount, delta=0.1**6, msg="礼品卡数量不正确")
        self.assertAlmostEqual(user_balance2["data"]["amount"] - user_balance["data"]["amount"], amount * card_details["data"]["cashback"] / 100, delta=0.1**6, msg="订单返现数量不正确")

    def test_234_buyGiftCard_wallet(self):
        """
        创建礼品卡购买订单, 购买礼品卡, 使用余额支付
        """
        cards = self.client.getGiftCardList()
        store_id = cards["data"]["data"][0]["storeId"]
        card_details = self.client.getGiftCardDetail(store_id)
        amount = card_details["data"]["minimum"] + 1
        currency = RoxeSendData.currency[0]
        order, body = self.client.createPurchaseOrder(
            card_details["data"]["batchId"], card_details["data"]["shopId"], store_id,
            card_details["data"]["giftCardCurrency"], amount, amount, currency, RoxeSendData.user_account, 2
        )
        self.checkCodeMessage(order)
        self.assertIsNotNone(order["data"])
        gift_balance = self.client.giftBalance(card_details["data"]["giftCardCurrency"])
        # self.client.openCheckOutAndSelectCard(order["data"])
        user_balance = self.client.listCurrencyBalance(currency)
        order_id = self.mysql.exec_sql_query("select business_order_no from roxe_pay_in_out.roxe_pay_in_order where id={}".format(int(order["data"])))[0]["businessOrderNo"]
        # 选择wallet余额支付
        self.rps_client.selectWalletToPayOrder(int(order["data"]), order_id, amount, "USD", expect_pay_success=False)
        self.waitOrderStatusInDB(order_id, "Processing")

        self.waitGiftCardOrderStatusInDB(order_id)
        self.waitOrderStatusInDB(order_id)
        gift_balance2 = self.client.giftBalance(card_details["data"]["giftCardCurrency"])
        user_balance2 = self.client.listCurrencyBalance(currency)
        self.assertAlmostEqual(gift_balance2["data"]["amount"] - gift_balance["data"]["amount"], amount, delta=0.1**6, msg="礼品卡数量不正确")
        self.assertAlmostEqual(user_balance["data"]["amount"] - user_balance2["data"]["amount"], amount * (1 - card_details["data"]["cashback"] / 100), delta=0.1**6, msg="余额实际支付数量不正确")

    def test_235_buyGifCard_amountLessThanMin(self):
        """
        创建礼品卡购买订单, 购买礼品卡, 数量小于最小数量
        """
        cards = self.client.getGiftCardList()
        store_id = cards["data"]["data"][0]["storeId"]
        card_details = self.client.getGiftCardDetail(store_id)
        amount = card_details["data"]["minimum"] - 0.001
        currency = RoxeSendData.currency[0]
        gift_balance = self.client.giftBalance(card_details["data"]["giftCardCurrency"])
        user_balance = self.client.listCurrencyBalance(currency)
        order, body = self.client.createPurchaseOrder(
            card_details["data"]["batchId"], card_details["data"]["shopId"], store_id,
            card_details["data"]["giftCardCurrency"], amount, amount, currency, RoxeSendData.user_account, 2
        )
        self.checkCodeMessage(order, "RGT10201", "Less than minimum")
        self.assertIsNone(order["data"])

        gift_balance2 = self.client.giftBalance(card_details["data"]["giftCardCurrency"])
        user_balance2 = self.client.listCurrencyBalance(currency)
        self.assertAlmostEqual(gift_balance2["data"]["amount"] - gift_balance["data"]["amount"], 0, delta=0.1**6, msg="礼品卡数量不正确")
        self.assertAlmostEqual(user_balance["data"]["amount"] - user_balance2["data"]["amount"], 0, delta=0.1**6, msg="余额实际支付数量不正确")

    def test_236_buyGifCard_amountMoreThanMax(self):
        """
        创建礼品卡购买订单, 购买礼品卡, 数量大于最大数量
        """
        cards = self.client.getGiftCardList()
        store_id = cards["data"]["data"][0]["storeId"]
        card_details = self.client.getGiftCardDetail(store_id)
        amount = card_details["data"]["maxmum"] + 0.01
        currency = RoxeSendData.currency[0]
        gift_balance = self.client.giftBalance(card_details["data"]["giftCardCurrency"])
        user_balance = self.client.listCurrencyBalance(currency)
        order, body = self.client.createPurchaseOrder(
            card_details["data"]["batchId"], card_details["data"]["shopId"], store_id,
            card_details["data"]["giftCardCurrency"], amount, amount, currency, RoxeSendData.user_account, 2
        )
        self.checkCodeMessage(order, "RGT10202", "Greater than maximum limit")
        self.assertIsNone(order["data"])

        gift_balance2 = self.client.giftBalance(card_details["data"]["giftCardCurrency"])
        user_balance2 = self.client.listCurrencyBalance(currency)
        self.assertAlmostEqual(gift_balance2["data"]["amount"] - gift_balance["data"]["amount"], 0, delta=0.1**6, msg="礼品卡数量不正确")
        self.assertAlmostEqual(user_balance["data"]["amount"] - user_balance2["data"]["amount"], 0, delta=0.1**6, msg="余额实际支付数量不正确")

    def test_237_buyGifCard_amountMoreThanPurchaseLimit(self):
        """
        创建礼品卡购买订单, 购买礼品卡, 数量大于最大数量
        """
        store_id = 1
        card_details = self.client.getGiftCardDetail(store_id)
        card_info = self.mysql.exec_sql_query("select * from roxe_gift.gift_card_batch where merchant_id={}".format(store_id))
        amount = float(card_info[0]["dailyPurchaseLimit"]) + 0.1
        currency = RoxeSendData.currency[0]
        gift_balance = self.client.giftBalance(card_details["data"]["giftCardCurrency"])
        user_balance = self.client.listCurrencyBalance(currency)
        order, body = self.client.createPurchaseOrder(
            card_details["data"]["batchId"], card_details["data"]["shopId"], store_id,
            card_details["data"]["giftCardCurrency"], amount, amount, currency, RoxeSendData.user_account, 2
        )
        if float(card_info[0]["dailyPurchaseLimit"]) > card_details["data"]["maxmum"]:
            self.checkCodeMessage(order, "RGT10202", "Greater than maximum limit")
        else:
            self.checkCodeMessage(order, "RGT10403", "Current Giftcard Purchase limit Reached")
        self.assertIsNone(order["data"])

        gift_balance2 = self.client.giftBalance(card_details["data"]["giftCardCurrency"])
        user_balance2 = self.client.listCurrencyBalance(currency)
        self.assertAlmostEqual(gift_balance2["data"]["amount"] - gift_balance["data"]["amount"], 0, delta=0.1**6, msg="礼品卡数量不正确")
        self.assertAlmostEqual(user_balance["data"]["amount"] - user_balance2["data"]["amount"], 0, delta=0.1**6, msg="余额实际支付数量不正确")

    def test_238_queryGiftCardHistory(self):
        """
        查询礼品卡的交易历史，此接口只有购买和消费礼品卡的历史
        """
        cards = self.client.getGiftCardList()
        card_details = self.client.getGiftCardDetail(cards["data"]["data"][0]["storeId"])
        card_history = self.client.getGiftOrderHistoryList(card_details["data"]["giftCardCurrency"])
        self.checkCodeMessage(card_history)
        self.checkGiftCardHistoryList(card_history['data'], RoxeSendData.user_id, card_details["data"]["giftCardCurrency"])

    def test_239_getMerchantInfoByQRCodes(self):
        """
        根据二维码code获取商户信息
        """
        # cards = self.client.getGiftCardList()
        # store_id = cards["data"]["data"][0]["storeId"]
        store_id = 1
        card_details = self.client.getGiftCardDetail(store_id)
        qc_code = self.commerce_client.getBranchQrCodeInfo(card_details["data"]["shopId"])
        info = self.client.getMerchantInfoByQRCodes(qc_code["data"])
        self.checkCodeMessage(info)

        balance = self.client.giftBalance(card_details["data"]["giftCardCurrency"])
        self.assertEqual(info["data"]["merchantName"], balance["data"]["merchantInfo"]["merchantName"])
        self.assertEqual(info["data"]["merchantLogo"], card_details["data"]["storeImg"])

        self.assertAlmostEqual(info["data"]["balance"], balance["data"]["amount"], delta=0.001)
        currency_map = self.mysql.exec_sql_query("select * from roxe_gift.currency_map where currency='{}'".format(card_details["data"]["giftCardCurrency"]))
        self.assertEqual(info["data"]["giftCardName"], currency_map[0]["giftCardName"])
        self.assertEqual(info["data"]["currency"], currency_map[0]["currency"])
        self.assertEqual(info["data"]["currencyIcon"], currency_map[0]["currencyIcon"])

    def test_240_spentGiftCard(self):
        """
        消费礼品卡
        """
        store_id = 1
        card_details = self.client.getGiftCardDetail(store_id)
        qc_code = self.commerce_client.getBranchQrCodeInfo(card_details["data"]["shopId"])
        amount = 1.35
        gift_card = card_details["data"]["giftCardCurrency"]
        balance = self.client.giftBalance(gift_card)
        consumption_order, body = self.client.createConsumptionOrder(RoxeSendData.user_account, gift_card, amount, qc_code["data"])
        self.checkCodeMessage(consumption_order)
        time.sleep(3)
        order_id = self.mysql.exec_sql_query("select * from roxe_gift.gift_card_order where roxe_id='{}' and type=3 order by create_time desc".format(RoxeSendData.user_account))[0]["sendOrderId"]
        self.waitGiftCardOrderStatusInDB(order_id)
        balance2 = self.client.giftBalance(gift_card)

        self.assertAlmostEqual(balance["data"]["amount"] - balance2["data"]["amount"], amount, delta=0.001)

    def test_241_spentGiftCard_amountMoreThanBalance(self):
        """
        消费礼品卡
        """
        store_id = 1
        card_details = self.client.getGiftCardDetail(store_id)
        qc_code = self.commerce_client.getBranchQrCodeInfo(card_details["data"]["shopId"])
        gift_card = card_details["data"]["giftCardCurrency"]
        balance = self.client.giftBalance(gift_card)
        amount = ApiUtils.parseNumberDecimal(balance["data"]["amount"] + 0.02)

        consumption_order, body = self.client.createConsumptionOrder(RoxeSendData.user_account, gift_card, amount, qc_code["data"])
        self.checkCodeMessage(consumption_order, "RGT10401", "Insufficient gift card balance")

        balance2 = self.client.giftBalance(gift_card)

        self.assertAlmostEqual(balance["data"]["amount"] - balance2["data"]["amount"], 0, delta=0.001)

    def test_242_sendToRoAccount_selectCardPay(self):
        """
        Pay，选择card支付，等待交易完成
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_SENDTOROXEACCOUNT.value
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b
        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")
        daily_limit, ninety_day_limit, left_day = self.client.calKycLimitAmount(self, RoxeSendData.user_id, RoxeSendData.user_login_token)

        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount)
        pay_info, re_body = self.client.sendToRoxeAccount(
            to_ro_id, rate_info["data"]["exchangeRate"], currency, amount, currency, rate_info["data"]["receiveAmount"], ensure_side, 2, note="pay"
        )
        self.checkCodeMessage(pay_info)
        self.checkSenToRoAccountOrderInfo(pay_info["data"], re_body, RoxeSendData.user_id, RoxeSendData.user_id_b)
        tx_id = pay_info["data"]["transactionId"]

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Submitted")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        # 选择card支付
        order_id = tx_info["data"]["orderId"]
        # target_account = tx_info["data"]["counterparty"]["roxeId"]
        # self.rps_client.submitAchPayOrder(target_account, amount, expect_pay_success=False, account_info=RPSData.ach_account, businessOrderNo=order_id)
        rps_id = self.mysql.exec_sql_query("select id from roxe_pay_in_out.roxe_pay_in_order where business_order_no='{}'".format(order_id))[0]["id"]
        self.client.openCheckOutAndSelectCard(rps_id, RoxeSendData.user_id)
        self.waitOrderStatusInDB(order_id, "Processing")

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        self.waitOrderStatusInDB(order_id)

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Complete")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertAlmostEqual(from_balance2, from_balance, msg="from账户资产不正确", delta=0.1**6)
        self.assertAlmostEqual(to_balance2 - to_balance, amount, msg="to账户资产不正确", delta=0.1**6)

        daily_limit2, ninety_day_limit2, left_day2 = self.client.calKycLimitAmount(self, RoxeSendData.user_id, RoxeSendData.user_login_token)
        self.assertAlmostEqual(daily_limit - daily_limit2, amount, delta=0.1**6)
        self.assertAlmostEqual(ninety_day_limit - ninety_day_limit2, amount, delta=0.1**6)

    def test_243_payRequest_selectCardPay(self):
        """
        request，选择card支付，等待交易完成
        """
        amount = 4.35
        currency = RoxeSendData.currency[0]
        from_ro_id = RoxeSendData.user_account
        to_ro_id = RoxeSendData.user_account_b

        from_balance = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance}")
        to_balance = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance}")

        daily_limit, ninety_day_limit, left_day = self.client.calKycLimitAmount(self, RoxeSendData.user_id_b, RoxeSendData.user_login_token_b)

        pay_info, re_body = self.client.request(RoxeSendData.user_id_b, currency, amount, "hello")
        tx_id = pay_info["data"]["transactionId"]

        # A查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Temporary")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)
        # B查询到的request订单
        tx_h, tx_body = self.client.getTransactionHistory(token=RoxeSendData.user_login_token_b)
        tx_id_b = tx_h["data"]["data"][0]["transactionId"]

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Temporary")
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        ensure_side = RoxeSendEnum.ENSURE_SIDE_INNER.value
        b_type = RoxeSendEnum.BUSINESS_TYPE_REQUEST.value
        rate_info, r_params = self.client.getExchangeRate(currency, currency, b_type, ensure_side, amount)
        # 另外一方进行支付
        pay_request, pay_body = self.client.payRequest(
            tx_id_b, from_ro_id, rate_info["data"]["exchangeRate"], currency,
            rate_info["data"]["sendAmount"], currency, rate_info["data"]["receiveAmount"],
            2, "pay request", RoxeSendData.user_login_token_b
        )
        self.checkCodeMessage(pay_request)
        self.checkPayRequestOrderInfo(pay_request["data"], pay_body, RoxeSendData.user_id_b, RoxeSendData.user_id)
        # 选择card支付
        order_id = pay_request["data"]["orderId"]
        rps_id = self.mysql.exec_sql_query("select id from roxe_pay_in_out.roxe_pay_in_order where business_order_no='{}'".format(order_id))[0]["id"]
        self.client.openCheckOutAndSelectCard(rps_id, RoxeSendData.user_id)
        self.waitOrderStatusInDB(order_id, "Processing")

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        self.waitOrderStatusInDB(order_id)

        # 查询交易详情
        tx_info = self.client.getTransactionDetail(tx_id)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Complete")
        self.checkTransactionDetail(tx_info["data"], tx_id, RoxeSendData.user_id_b)

        tx_info = self.client.getTransactionDetail(tx_id_b, RoxeSendData.user_login_token_b)
        self.checkCodeMessage(tx_info)
        self.assertEqual(tx_info["data"]["status"], "Complete")
        self.checkTransactionDetail(tx_info["data"], tx_id_b, RoxeSendData.user_id)

        from_balance2 = self.rps_client.getRoAccountBalance(from_ro_id, currency)
        self.client.logger.info(f"{from_ro_id}资产: {from_balance2}")
        to_balance2 = self.rps_client.getRoAccountBalance(to_ro_id, currency)
        self.client.logger.info(f"{to_ro_id}资产: {to_balance2}")
        self.assertAlmostEqual(from_balance2 - from_balance, amount, msg="from账户资产不正确", delta=0.1**6)
        self.assertAlmostEqual(to_balance2, to_balance, msg="to账户资产不正确", delta=0.1**6)

        daily_limit2, ninety_day_limit2, left_day2 = self.client.calKycLimitAmount(self, RoxeSendData.user_id_b, RoxeSendData.user_login_token_b)
        self.assertAlmostEqual(daily_limit - daily_limit2, amount, delta=0.1**6)
        self.assertAlmostEqual(ninety_day_limit - ninety_day_limit2, amount, delta=0.1**6)
