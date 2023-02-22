# coding=utf-8
# author: Li MingLei
# date: 2021-08-30

import unittest
from .RpsApi import RPSApiClient
from roxe_libs.DBClient import Mysql
from roxe_libs.Global import Global
from roxe_libs import settings, ApiUtils
import time
import json
import datetime
from enum import Enum


class PaymentMethods(Enum):

    ACH = "ach"
    CARD = "card"
    WIRE = "wire"
    BALANCE = "balance"


class BusinessType(Enum):

    CHARGE = "deposit"
    TRANSFER = "transfer"
    WITHDRAW = "withdrawal"


class PayOrder(Enum):

    PAY_CONFIRM = 1
    PAY_SUCCESS = 2
    PAY_FAIL = 3


class RPSData:

    env = Global.getValue(settings.environment)
    if env.lower() == "bjtest":
        # host = "http://roxe-rps-bj-test.roxepro.top:38888/roxe-rps"
        host = "http://roxe-gateway-bj-test.roxepro.top:38889"
        chain_host = "http://testnet.roxe.tech:18888/v1"
        # chain_host = "http://192.168.37.22:18888/v1"

        app_key = "adfasdas"
        secret = "1212"
        user_id = "100144"
        user_roxe_account = "agjyrafzwlng"  # 100144
        user_id_a = "100197"
        user_roxe_account_a = "z5hkbojz2tjn"  # 100197

        custody_account = "1vtqnirollub"

        user_login_token = "eyJhbGciOiJIUzI1NiJ9.eyJpdGMiOiI4NiIsImlzcyI6IlJPWEUiLCJhdWQiOiIxMDAxNDQiLCJzdWIiOiJVU0VSX0xPR0lOIiwibmJmIjoxNjM2MzYxNzc5fQ.ltOdtqDjgUrj9d88IHD90KDD_4ggL-94OXhAIATUSiY"
        payment_methods = {
            "deposit": [
                PaymentMethods.ACH.value,
                PaymentMethods.CARD.value,
                PaymentMethods.BALANCE.value,
            ],
            "withdraw": [
                PaymentMethods.ACH.value,
                PaymentMethods.CARD.value,
                PaymentMethods.BALANCE.value,
            ],
            "transfer": [
                PaymentMethods.ACH.value,
                PaymentMethods.CARD.value,
                PaymentMethods.BALANCE.value,
            ]
        }

        currency_method = {
            "USD": [
                PaymentMethods.ACH.value,
                PaymentMethods.CARD.value,
                PaymentMethods.WIRE.value,
                PaymentMethods.BALANCE.value,
            ]
        }

        sign = "B9241072ED44CBE72E84345A7B6CF033"

        user_not_exist = "000000"
        user_not_login = "100142"  # 未登录但是进行了kyc
        user_not_kyc = "100147"  # 没有进行kyc的用户
        user_not_kyc_login_token = "eyJhbGciOiJIUzI1NiJ9.eyJpdGMiOiI4NiIsImlzcyI6IlJPWEUiLCJhdWQiOiIxMDAxNDciLCJzdWIiOiJVU0VSX0xPR0lOIiwibmJmIjoxNjMxNTE3OTYxfQ.bbQjxl1B_yOxIgSTuOwg-_2pSp-7SKEhfyExY1dODUk"  # 没有进行kyc的用户

        is_check_db = True
        sql_cfg = {
            "mysql_host": "rw-mysql-roxe-bjtest-aly.roxepro.top",
            "port": 3306,
            "user": "rwuser",
            "password": "Ro@123123",
            "db": "roxe_pay_in_out",
        }

        ach_account = {
            "accountNumber": "000123456789",
            "routingNumber": "111000025",
            "currency": "usd",
            "country": "US",
            "holder": "lind jethro",
            "holderType": "individual",
            "bankAccountToken": "btok_1JKKy0HZ6csVB3MEbRtOe07b"
        }

        account_using_failed = "000111111116"
        account_canceled = "000111111113"
        account_insufficient_balance = "000222222227"
        account_unauthorized_withdrawal = "000333333335"
        account_invalid_currency = "000444444440"


class RPSApiTest(unittest.TestCase):

    mysql = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = RPSApiClient(RPSData.host, RPSData.app_key, RPSData.secret, RPSData.user_id, RPSData.user_login_token)
        if RPSData.is_check_db:
            cls.mysql = Mysql(RPSData.sql_cfg["mysql_host"], RPSData.sql_cfg["port"], RPSData.sql_cfg["user"], RPSData.sql_cfg["password"], RPSData.sql_cfg["db"], True)
            cls.mysql.connect_database()

    @classmethod
    def tearDownClass(cls) -> None:
        if RPSData.is_check_db:
            cls.mysql.disconnect_database()

    def setUp(self) -> None:
        if RPSData.is_check_db:
            self.client.logger.info("setUp清理数据")
            self.client.deleteAchAccountFromDB(self, RPSData.user_id)

    def tearDown(self) -> None:
        if RPSData.is_check_db:
            self.client.logger.info("teardown清理数据")
            self.client.deleteAchAccountFromDB(self, RPSData.user_id)

    def checkCodeAndMessage(self, msg, expect_code='0', expect_message='Success'):
        """
        校验返回的标准code码和message
        :param msg: 接口返回的响应，json格式
        :param expect_code: 正常情况下，code码为0
        :param expect_message: 正常情况下，message为Success
        """
        self.assertEqual(msg["code"], expect_code, f"返回的code不正确: {msg}")
        self.assertEqual(msg["message"], expect_message, f"返回的code不正确: {msg}")

    def test_001_queryBindBankAccountWhenUserNotHaveBindAccount(self):
        """
        未绑定ach账户时查询已绑定的银行账户
        """
        sign = RPSData.sign
        accounts = self.client.queryBindBankAccount(sign, RPSData.app_key, RPSData.user_id, "USD")
        self.assertEqual(accounts, [], "应该返回一个空的账户信息")

    def checkAchAccountInfo(self, ach_account, request_body, user_id):
        self.assertEqual(ach_account["bankAccountLast4"], request_body["accountNumber"][-4:])
        self.assertEqual(ach_account["bankLogoUrl"], "https://roxe-pay-pro.s3.amazonaws.com/bank_logo/BankOfAmercica.png")
        self.assertEqual(ach_account["bankName"], "BANK OF AMERICA, N.A.")
        self.assertEqual(ach_account["country"], request_body["country"])
        self.assertEqual(ach_account["currency"], request_body["currency"].upper())
        self.assertEqual(ach_account["status"], 1)
        self.assertIsNotNone(ach_account["id"])
        self.assertIsNotNone(ach_account["serviceChannelBankAccountId"])
        self.assertIsNotNone(ach_account["isPlaidUser"])
        self.checkAchAccountInfoFromDB(ach_account, user_id)
        self.client.logger.info("校验ach账户信息通过")

    def checkAchAccountInfoFromDB(self, ach_account, user_id):
        if RPSData.is_check_db:
            sql = "select * from roxe_pay_in_user_bank_account where roxe_user_id='{}' and status<>0".format(user_id)
            db_account_info = self.mysql.exec_sql_query(sql)
            self.client.logger.debug("查询数据库: {}".format(db_account_info))
            for key in ach_account.keys():
                if key in ["isPlaidUser", "createDate"]:
                    self.assertIsNotNone(ach_account[key])
                else:
                    self.assertEqual(ach_account[key], db_account_info[0][key], f"{key}字段和数据库值不符合")

    @unittest.skip("当ACH的支付方式不在payment method配置中时跳过该用例")
    def test_002_bindAchAccount(self):
        """
        绑定正确的ach账户
        """
        account_info = RPSData.ach_account.copy()
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res)
        self.checkAchAccountInfo(bind_res["data"], account_info, RPSData.user_id)
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        self.assertEqual(len(accounts), 1, "查询接口查询不到绑定的银行账户")
        self.checkAchAccountInfoFromDB(accounts[0], RPSData.user_id)

    @unittest.skip("当ACH的支付方式不在payment method配置中时跳过该用例")
    def test_003_verifyAchAccount(self):
        """
        手动校验ach账户
        """
        self.test_002_bindAchAccount()
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, RPSData.ach_account["currency"].upper())
        account_id = accounts[0]["id"]
        verify_info = self.client.verifyBankAccount(RPSData.user_id, RPSData.user_login_token, account_id, 0.32, 0.45)
        self.checkCodeAndMessage(verify_info)
        self.assertEqual(verify_info["data"], True, "校验账户错误")
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, "USD")
        self.assertEqual(len(accounts), 1, "查询接口查询不到绑定的银行账户")
        self.checkAchAccountInfoFromDB(accounts[0], RPSData.user_id)

    @unittest.skip("当ACH的支付方式不在payment method配置中时跳过该用例")
    def test_004_unbindAchAccount(self):
        """
        解绑ach账户，验证成功后重新绑定、校验银行账户
        """
        self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, RPSData.ach_account["currency"].upper())
        account_id = accounts[0]["id"]
        unbind_info = self.client.unbindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_id)
        self.assertEqual(unbind_info, True, "校验账户错误")
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, "USD")
        self.assertEqual(accounts, [], "应该返回一个空的账户信息")

    def test_005_getPlaidLinkToken(self):
        """
        获取plaid的link token
        """
        self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        bank_accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, RPSData.ach_account["currency"].upper())
        bank_account_id = bank_accounts[0]["id"]
        link_token = self.client.queryPlaidLinkToken(RPSData.user_id, RPSData.user_login_token, RPSData.app_key, bank_account_id)
        self.checkCodeAndMessage(link_token)
        self.assertIsNotNone(link_token["data"])

    def checkPaymentMethod(self, payment_methods, businessAmount, user_id, accountWalletBalance=0):
        if RPSData.is_check_db:
            sql = "select * from roxe_pay_in_method as a left join roxe_pay_in_method_currency as b on a.id=b.pay_method_id left join roxe_pay_channel_bank_account as c on a.service_channel=c.service_channel"
            db_res = self.mysql.exec_sql_query(sql)
            for m in payment_methods:
                db_method = [i for i in db_res if i["type"] == m["type"] and i["serviceChannel"] == m["serviceChannel"] and i["currency"] == m["currencyList"][0]["currency"]]
                self.client.logger.debug("要对比的支付方式: {}".format(m))
                self.client.logger.debug("查询数据库: {}".format(db_method))
                self.assertEqual(m["amount"], businessAmount)
                if m["type"] == "ach":
                    if m["bankAccounts"]:
                        self.assertEqual(len(m["bankAccounts"]), 1)
                        self.checkAchAccountInfoFromDB(m["bankAccounts"][0], user_id)
                else:
                    self.assertEqual(m["bankAccounts"], [])
                self.assertEqual(m["name"], db_method[0]["name"])
                self.assertEqual(m["serviceChannel"], db_method[0]["serviceChannel"])
                self.assertEqual(m["type"], db_method[0]["type"])
                self.assertEqual(m["logoUrl"], db_method[0]["logoUrl"])
                db_fee_config = json.loads(db_method[0]["feeJson"])
                maxAmount = float(db_method[0]["maxAmount"]) if db_method[0]["maxAmount"] else 0
                minAmount = float(db_method[0]["minAmount"]) if db_method[0]["minAmount"] else 0
                if m["serviceChannel"] == "WALLET":
                    self.assertAlmostEqual(m["walletBanlance"], accountWalletBalance, delta=0.1**7)
                    self.assertIsNone(m["channelBankAccount"])
                    # fee = self.client.calChannelFee(db_fee_config, m["amount"], m["serviceChannel"])
                    fee = 0  # 测试环境链上转账费用为0
                    self.assertEqual(m["currencyList"][0]["fee"], fee)
                    self.assertEqual(m["currencyList"][0]["maxAmount"], maxAmount)
                    self.assertEqual(m["currencyList"][0]["minAmount"], minAmount)
                else:
                    self.assertEqual(m["walletBanlance"], 0)
                    if m["channelBankAccount"]:
                        for k in m["channelBankAccount"].keys():
                            if k in ["country", "currency"]:
                                db_k = "c." + k
                            else:
                                db_k = k
                            expect_data = db_method[0][db_k] if db_method[0][db_k] else ""
                            self.assertEqual(m["channelBankAccount"][k], expect_data, f"{k}字段校验失败: {db_method[0]}")
                    fee = self.client.calChannelFee(db_fee_config, m["amount"], m["serviceChannel"])
                    self.client.logger.info(f"{m['type']}的费用计算为: {fee}")
                    fee = ApiUtils.parseNumberDecimal(fee, 2, True)
                    self.client.logger.info(f"{m['type']}的费用计算为: {fee}")
                    allowance_fee = self.client.calAllowanceFee(self, fee, m["type"])
                    self.client.logger.info(f"{m['type']}的优惠券额度计算为: {allowance_fee}")
                    self.assertAlmostEqual(allowance_fee, m["currencyList"][0]["allowanceFee"], delta=0.1**8)
                    show_fee = ApiUtils.parseNumberDecimal(fee - allowance_fee)
                    self.client.logger.info(f"{m['type']}的展示费用计算为: {show_fee}")
                    self.assertAlmostEqual(show_fee, m["currencyList"][0]["showFee"], delta=0.1**8)
                    self.assertAlmostEqual(m["currencyList"][0]["fee"], fee, delta=0.1**8, msg=f"{m['type']}的费用规则:{db_fee_config}")
                    self.assertEqual(m["currencyList"][0]["maxAmount"], maxAmount)
                    self.assertEqual(m["currencyList"][0]["minAmount"], minAmount)
                self.assertEqual(len(m["currencyList"]), len(db_method))
                self.assertEqual(m["currencyList"][0]["country"], db_method[0]["country"])
                self.assertEqual(m["currencyList"][0]["currency"], db_method[0]["currency"])
                currencyLogoUrl = db_method[0]["currencyLogoUrl"] if db_method[0]["currencyLogoUrl"] else ""
                processingTime = db_method[0]["processingTime"] if db_method[0]["processingTime"] else 0
                self.assertEqual(m["currencyList"][0]["currencyLogoUrl"], currencyLogoUrl)
                self.assertEqual(m["currencyList"][0]["processingTime"], processingTime)
                self.assertEqual(m["currencyList"][0]["symbol"], db_method[0]["symbol"])
                self.client.logger.info(f"查询支付方式{m['type']}的结果校验通过")

    def checkPayOrderInDB(self, pay_order, pay_order_info):
        if RPSData.is_check_db:
            sql = "select * from roxe_pay_in_order where id='{}'".format(pay_order)
            db_order_info = self.mysql.exec_sql_query(sql)
            try:
                self.assertEqual(pay_order, db_order_info[0]["id"])
                self.assertEqual("rps" + str(pay_order), db_order_info[0]["payOrderNo"])
                for key, value in pay_order_info.items():
                    if key in ["businessAmount"]:
                        self.assertAlmostEqual(float(value), float(db_order_info[0][key]), delta=0.1**7)
                    else:
                        self.assertEqual(value, db_order_info[0][key], "{}字段校验失败".format(key))
                self.client.logger.info("支付下单接口的结果校验通过")
            except Exception as e:
                self.client.logger.info("数据库查询支付订单: {}".format(pay_order))
                self.client.logger.error(e.args, exc_info=True)

    def checkSubmitOrderInfo(self, submit_order, channelFee, payOrder, payMethod, businessOrderNo):
        self.assertEqual(submit_order["id"], str(payOrder))
        self.assertEqual(submit_order["rpsOrderId"], str(payOrder))
        self.assertEqual(submit_order["channelFee"], channelFee)
        self.assertEqual(submit_order["payMethod"], payMethod)
        self.assertEqual(submit_order["businessOrderNo"], businessOrderNo)
        self.assertIsNone(submit_order["serviceChannelOrderId"])
        self.assertIsNone(submit_order["businessExt"])
        if submit_order["payMethod"].lower() == "ach":
            self.assertIsNotNone(submit_order["couponCode"])
        else:
            self.assertIsNone(submit_order["couponCode"])
        self.client.logger.info("选择支付方式接口的结果校验通过")

    def waitUntilPayChannelOrderComplete(self, pay_order, order_type="in", time_out=120, time_inner=10):
        """
        等待支付订单完成
        """
        if order_type == "in":
            pay_order_sql = "select service_channel_order_id as channelId from roxe_pay_in_order where id={}".format(pay_order)
        else:
            pay_order_sql = "select * from roxe_pay_in_order where id={}".format(pay_order)
        b_time = time.time()
        channel_order_id = ""
        while time.time() - b_time < time_out:
            channel_order_id = self.mysql.exec_sql_query(pay_order_sql)[0]["channelId"]
            if channel_order_id:
                break
            time.sleep(time_inner)
        sql = "select * from roxe_pay_in_callback_info where callback_json like '%{}%'".format(channel_order_id)
        flag = False
        while time.time() - b_time < time_out:
            db_res = self.mysql.exec_sql_query(sql)
            if len(db_res) > 0:
                callback_info = json.loads(db_res[0]["callbackJson"])
                if "type" in callback_info and "succeeded" in callback_info["type"]:
                    flag = True
                    break
                if "status" in callback_info and "PAY_SUCCESS" in callback_info["status"]:
                    flag = True
                    break
            time.sleep(time_inner)
        if flag:
            self.client.logger.info("支付通道的订单已经完成")
        else:
            self.client.logger.error(f"支付通道的订单在{time_out}秒内未支付成功")
            assert False, f"支付通道的订单在{time_out}秒内未支付成功"

    @unittest.skip("card支付需要跳转stripe页面，暂时跳过")
    def test_006_placePaymentOrder_deposit_card(self):
        """
        充值业务，法币->ro, 支付方式选择card
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 10,
            "channelFeeDeductionMethod": 1,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": RPSData.user_roxe_account,
            "targetRoxeAccount": RPSData.user_roxe_account_a,
            "currency": "USD",
            "businessType": BusinessType.CHARGE.value,
            "country": "US",
        }
        # pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        pay_order = 24322157538443264
        self.assertIsNotNone(pay_order, "生成的支付订单不成功")
        self.checkPayOrderInDB(pay_order, pay_order_info)
        # 查询支付方式
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)
        self.checkCodeAndMessage(methods)
        self.assertEqual(len(methods["data"]), len(RPSData.payment_methods["deposit"]), "返回的data不正确")
        self.checkPaymentMethod(methods["data"], pay_order_info["businessAmount"], RPSData.user_id)

        # 选择支付方式进行支付
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.CARD.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method))
        order_info = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, RPSData.app_key, pay_order, pay_order_info["currency"], select_method["type"], select_method["serviceChannel"], select_method["currencyList"][0]["fee"], pay_order_info["businessAmount"] + select_method["currencyList"][0]["fee"])
        self.checkCodeAndMessage(order_info)
        self.assertEqual(order_info["data"]["id"], pay_order)
        self.assertIsNotNone(order_info["data"]["serviceChannelPayNo"])

        # 查询订单状态，等待支付完成

    def test_007_placePaymentOrder_deposit_ach_outsideDeduction(self):
        """
         充值业务，法币->ro, 支付方式选择ach
        """
        self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        # 下支付订单
        pay_order_info = {
            "businessAmount": 12.34,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": "xxxx",
            "targetRoxeAccount": RPSData.user_roxe_account,
            "currency": "USD",
            "businessType": BusinessType.CHARGE.value,
            "country": "US",
        }
        # 查询钱包余额
        targetAccountBalance = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"目标账户资产: {targetAccountBalance}")
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.assertIsNotNone(pay_order, "生成的支付订单不成功")
        self.checkPayOrderInDB(pay_order, pay_order_info)
        # 查询支付方式
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)
        self.checkCodeAndMessage(methods)
        # self.assertEqual(len(methods["data"]), 2, "返回的data不正确")
        self.checkPaymentMethod(methods["data"], pay_order_info["businessAmount"], RPSData.user_id)

        # 选择支付方式进行支付
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.ACH.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method))
        ach_account = {
            "allowanceFee": select_method["currencyList"][0]["allowanceFee"],
            "showFee": select_method["currencyList"][0]["showFee"],
            "payBankAccountId": select_method["bankAccounts"][0]["id"],
            "authConsent": "1212",
            "transactionSpecificDetails": "232",
            "revocationTip": "123",
            "transactionReceiptTip": "312312",
        }
        order_info = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, RPSData.app_key,
                                                        pay_order, pay_order_info["currency"], select_method["type"],
                                                        select_method["serviceChannel"],
                                                        select_method["currencyList"][0]["fee"],
                                                        ApiUtils.parseNumberDecimal(pay_order_info["businessAmount"] + select_method["currencyList"][0]["fee"] - select_method["currencyList"][0]["allowanceFee"]),
                                                        **ach_account)
        self.checkCodeAndMessage(order_info)
        self.checkSubmitOrderInfo(order_info["data"], select_method["currencyList"][0]["showFee"], pay_order, select_method["type"], pay_order_info["businessOrderNo"])
        # 查询订单状态，等待支付完成
        query_order = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info["businessOrderNo"])
        self.assertEqual(query_order["businessAmount"], pay_order_info["businessAmount"])
        # 查询数据库，直到通道回调成功
        self.waitUntilPayChannelOrderComplete(pay_order)
        query_order = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info["businessOrderNo"])
        self.assertEqual(query_order["status"], PayOrder.PAY_SUCCESS.value)

        targetAccountBalance2 = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"目标账户资产: {targetAccountBalance2}, 变化了: {targetAccountBalance2 - targetAccountBalance}")

        self.assertEqual(query_order["status"], PayOrder.PAY_SUCCESS.value, "支付订单状态不正确")
        self.assertAlmostEqual(targetAccountBalance2 - targetAccountBalance, 0, msg="需要回调业务系统，支付订单才能完成", delta=0.1**7)

    @unittest.skip("wire方式暂时跳过")
    def test_008_placePaymentOrder_deposit_wire_outsideDeduction(self):
        """
        充值业务，法币->ro, 支付方式选择wire
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 10,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": RPSData.user_roxe_account,
            "targetRoxeAccount": RPSData.user_roxe_account_a,
            "currency": "USD",
            "businessType": BusinessType.CHARGE.value,
            "country": "US",
        }
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.assertIsNotNone(pay_order, "生成的支付订单不成功")
        self.checkPayOrderInDB(pay_order, pay_order_info)
        # 查询支付方式
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)
        self.checkCodeAndMessage(methods)
        self.assertEqual(len(methods["data"]), len(RPSData.payment_methods["deposit"]), "返回的data不正确")
        self.checkPaymentMethod(methods["data"], pay_order_info["businessAmount"], RPSData.user_id)

        # 选择支付方式进行支付
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.WIRE.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method))
        order_info = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, RPSData.app_key,
                                                        pay_order, pay_order_info["currency"], select_method["type"],
                                                        select_method["serviceChannel"],
                                                        select_method["currencyList"][0]["fee"],
                                                        pay_order_info["businessAmount"] + select_method["currencyList"][0]["fee"])
        self.checkCodeAndMessage(order_info)
        self.checkSubmitOrderInfo(order_info["data"], select_method["currencyList"][0]["fee"], pay_order, select_method["type"], pay_order_info["businessOrderNo"])
        # TODO 修改wire的订单状态
        # 查询订单状态，等待支付完成
        query_order = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info["businessOrderNo"])
        self.assertEqual(query_order["businessAmount"], pay_order_info["businessAmount"])
        # 查询数据库，直到通道回调成功
        self.waitUntilPayChannelOrderComplete(pay_order)

    def test_009_placePaymentOrder_transfer_walletToWallet_outsideDeduction(self):
        """
        转账业务，ro->ro, 支付方式选择wallet
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 12.68,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            # "businessOrderNo": "2163065072245797",
            "businessItemName": "test",
            "sourceRoxeAccount": RPSData.user_roxe_account,
            "targetRoxeAccount": RPSData.user_roxe_account_a,
            "currency": "USD",
            "businessType": BusinessType.TRANSFER.value,
            "country": "US",
        }
        # 查询钱包余额
        sourceAccountBalance = self.client.getRoAccountBalance(pay_order_info["sourceRoxeAccount"], pay_order_info["currency"])
        targetAccountBalance = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"源账户资产: {sourceAccountBalance}")
        self.client.logger.info(f"目标账户资产: {targetAccountBalance}")
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.assertIsNotNone(pay_order, "生成的支付订单不成功")
        self.checkPayOrderInDB(pay_order, pay_order_info)
        # 查询支付方式
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)
        self.checkCodeAndMessage(methods)
        self.assertEqual(len(methods["data"]), len(RPSData.payment_methods["deposit"]), "返回的data不正确")
        self.checkPaymentMethod(methods["data"], pay_order_info["businessAmount"], RPSData.user_id, sourceAccountBalance)

        # 选择支付方式进行支付
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method))
        self.client.logger.info("当前支付方式的费用: {}".format(select_method["currencyList"][0]["fee"]))
        fees = {
            "allowanceFee": select_method["currencyList"][0]["allowanceFee"],
            "showFee": select_method["currencyList"][0]["showFee"],
        }
        order_info = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, RPSData.app_key,
                                                        pay_order, pay_order_info["currency"], select_method["type"],
                                                        select_method["serviceChannel"],
                                                        select_method["currencyList"][0]["fee"],
                                                        pay_order_info["businessAmount"] + select_method["currencyList"][0]["showFee"], **fees)
        self.checkCodeAndMessage(order_info)
        self.checkSubmitOrderInfo(order_info["data"], select_method["currencyList"][0]["showFee"], pay_order, select_method["type"], pay_order_info["businessOrderNo"])

        # 查询订单状态，等待支付完成`
        query_order_info = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info["businessOrderNo"])
        self.assertEqual(query_order_info["businessAmount"], pay_order_info["businessAmount"])
        self.waitUntilPayChannelOrderComplete(pay_order, time_out=300)
        query_order_info = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info["businessOrderNo"])
        self.assertEqual(query_order_info["status"], PayOrder.PAY_SUCCESS.value)
        sourceAccountBalance2 = self.client.getRoAccountBalance(pay_order_info["sourceRoxeAccount"], pay_order_info["currency"])
        targetAccountBalance2 = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"源账户资产: {sourceAccountBalance2}, 变化了: {sourceAccountBalance2 - sourceAccountBalance}")
        self.client.logger.info(f"目标账户资产: {targetAccountBalance2}, 变化了: {targetAccountBalance2 - targetAccountBalance}")

        self.assertAlmostEqual(sourceAccountBalance - sourceAccountBalance2, pay_order_info["businessAmount"] + select_method["currencyList"][0]["fee"], msg="源账户扣钱不正确", delta=0.1**7)
        self.assertAlmostEqual(targetAccountBalance2 - targetAccountBalance, pay_order_info["businessAmount"], msg="目标账户扣钱不正确", delta=0.1**7)
        self.assertIsNotNone(query_order_info["serviceChannelOrderId"], "支付订单完成后应返回通道id")

        # 查询交易hash
        tx_hash = query_order_info["serviceChannelOrderId"]
        self.client.checkRoTransactionHash(tx_hash, pay_order_info, select_method["currencyList"][0]["fee"])

    @unittest.skip("card支付需要跳转stripe页面，暂时跳过")
    def test_010_placePaymentOrder_transfer_cardToWallet_outsideDeduction(self):
        """
        转账业务，法币->ro, 支付方式选择card
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 10,
            "channelFeeDeductionMethod": 1,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": RPSData.user_roxe_account,
            "targetRoxeAccount": RPSData.user_roxe_account_a,
            "currency": "USD",
            "businessType": BusinessType.TRANSFER.value,
            "country": "US",
        }
        # pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        pay_order = "24322157538443264"
        self.assertIsNotNone(pay_order, "生成的支付订单不成功")
        self.checkPayOrderInDB(pay_order, pay_order_info)
        # 查询支付方式
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)
        self.checkCodeAndMessage(methods)
        self.assertEqual(len(methods["data"]), len(RPSData.payment_methods["transfer"]), "返回的data不正确")
        self.checkPaymentMethod(methods["data"], pay_order_info["businessAmount"], RPSData.user_id)

        # 选择支付方式进行支付
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.CARD.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method))
        self.client.logger.info("当前支付方式的费用: {}".format(select_method["currencyList"][0]["fee"]))
        order_info = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, RPSData.app_key,
                                                        pay_order, pay_order_info["currency"], select_method["type"],
                                                        select_method["serviceChannel"],
                                                        select_method["currencyList"][0]["fee"],
                                                        pay_order_info["businessAmount"] + select_method["currencyList"][0]["fee"])
        self.checkCodeAndMessage(order_info)

        # 查询订单状态，等待支付完成

    def test_011_placePaymentOrder_transfer_achToWallet_outsideDeduction(self):
        """
        转账业务，法币->ro, 支付方式选择ach
        """
        self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        # 下支付订单
        pay_order_info = {
            "businessAmount": 12,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": RPSData.user_roxe_account,
            "targetRoxeAccount": RPSData.user_roxe_account_a,
            "currency": "USD",
            "businessType": BusinessType.TRANSFER.value,
            "country": "US",
        }
        # 查询钱包余额
        sourceAccountBalance = self.client.getRoAccountBalance(pay_order_info["sourceRoxeAccount"], pay_order_info["currency"])
        targetAccountBalance = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"源账户资产: {sourceAccountBalance}")
        self.client.logger.info(f"目标账户资产: {targetAccountBalance}")
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        # pay_order = 25034928328540160
        self.assertIsNotNone(pay_order, "生成的支付订单不成功")
        self.checkPayOrderInDB(pay_order, pay_order_info)
        # 查询支付方式
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)
        self.checkCodeAndMessage(methods)
        self.assertEqual(len(methods["data"]), len(RPSData.payment_methods["transfer"]), "返回的data不正确")
        self.checkPaymentMethod(methods["data"], pay_order_info["businessAmount"], RPSData.user_id, sourceAccountBalance)

        # 选择支付方式进行支付
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.ACH.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method))
        ach_account = {
            "allowanceFee": select_method["currencyList"][0]["allowanceFee"],
            "showFee": select_method["currencyList"][0]["showFee"],
            "payBankAccountId": select_method["bankAccounts"][0]["id"],
            "authConsent": "1212",
            "transactionSpecificDetails": "232",
            "revocationTip": "123",
            "transactionReceiptTip": "312312",
        }
        order_info = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, RPSData.app_key,
                                                        pay_order, pay_order_info["currency"], select_method["type"],
                                                        select_method["serviceChannel"],
                                                        select_method["currencyList"][0]["fee"],
                                                        pay_order_info["businessAmount"] + select_method["currencyList"][0]["fee"] - select_method["currencyList"][0]["allowanceFee"],
                                                        **ach_account)
        self.checkCodeAndMessage(order_info)
        self.checkSubmitOrderInfo(order_info["data"], select_method["currencyList"][0]["showFee"], pay_order, select_method["type"], pay_order_info["businessOrderNo"])
        # 查询订单状态，等待支付完成
        query_order = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info["businessOrderNo"])
        self.assertEqual(query_order["businessAmount"], pay_order_info["businessAmount"])
        # 查询数据库，直到通道回调成功
        self.waitUntilPayChannelOrderComplete(pay_order)

        query_order = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info["businessOrderNo"])
        self.assertEqual(query_order["status"], PayOrder.PAY_SUCCESS.value)
        sourceAccountBalance2 = self.client.getRoAccountBalance(pay_order_info["sourceRoxeAccount"], pay_order_info["currency"])
        targetAccountBalance2 = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"源账户资产: {sourceAccountBalance2}, 变化了: {sourceAccountBalance2 - sourceAccountBalance}")
        self.client.logger.info(f"目标账户资产: {targetAccountBalance2}, 变化了: {targetAccountBalance2 - targetAccountBalance}")

        # rps订单需要回调send系统来修改订单状态
        self.assertEqual(query_order["status"], PayOrder.PAY_SUCCESS.value, "支付订单状态不正确")
        self.assertAlmostEqual(sourceAccountBalance2 - sourceAccountBalance, 0, delta=0.1**7)

    @unittest.skip("wire方式暂时跳过")
    def test_012_placePaymentOrder_transfer_wireToWallet(self):
        """
        转账业务，法币->ro, 支付方式选择wire
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 10,
            "channelFeeDeductionMethod": 1,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": RPSData.user_roxe_account,
            "targetRoxeAccount": RPSData.user_roxe_account_a,
            "currency": "USD",
            "businessType": BusinessType.TRANSFER.value,
            "country": "US",
        }
        # pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        pay_order = "24322157538443264"
        self.assertIsNotNone(pay_order, "生成的支付订单不成功")
        self.checkPayOrderInDB(pay_order, pay_order_info)
        # 查询支付方式
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)
        self.checkCodeAndMessage(methods)
        self.assertEqual(len(methods["data"]), len(RPSData.payment_methods["transfer"]), "返回的data不正确")
        self.checkPaymentMethod(methods["data"], pay_order_info["businessAmount"], RPSData.user_id)

        # 选择支付方式进行支付
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.WIRE.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method))
        order_info = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, RPSData.app_key,
                                                        pay_order, pay_order_info["currency"], select_method["type"],
                                                        select_method["serviceChannel"],
                                                        select_method["currencyList"][0]["fee"],
                                                        pay_order_info["businessAmount"] +
                                                        select_method["currencyList"][0]["fee"])
        self.checkCodeAndMessage(order_info)

        # 查询订单状态，等待支付完成

    def test_013_placePaymentOrder_withdraw(self):
        """
        提现业务，从用户ro账户提现到中间账户,
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 12.34,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": RPSData.user_roxe_account,
            "targetRoxeAccount": RPSData.custody_account,
            "currency": "USD",
            "businessType": BusinessType.WITHDRAW.value,
            "country": "US",
        }
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        # pay_order = "24322157538443264"
        self.assertIsNotNone(pay_order, "生成的支付订单不成功")
        self.checkPayOrderInDB(pay_order, pay_order_info)
        # 查询钱包余额
        sourceAccountBalance = self.client.getRoAccountBalance(pay_order_info["sourceRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"源账户资产: {sourceAccountBalance}")
        targetAccountBalance = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"目标账户资产: {targetAccountBalance}")
        # 查询支付方式
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)
        self.checkCodeAndMessage(methods)
        self.assertEqual(len(methods["data"]), len(RPSData.payment_methods["withdraw"]), "返回的data不正确")
        self.checkPaymentMethod(methods["data"], pay_order_info["businessAmount"], RPSData.user_id, sourceAccountBalance)

        # 选择支付方式进行支付
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method))
        fees = {
            "allowanceFee": select_method["currencyList"][0]["allowanceFee"],
            "showFee": select_method["currencyList"][0]["showFee"],
        }
        order_info = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, RPSData.app_key,
                                                        pay_order, pay_order_info["currency"], select_method["type"],
                                                        select_method["serviceChannel"],
                                                        select_method["currencyList"][0]["fee"],
                                                        ApiUtils.parseNumberDecimal(pay_order_info["businessAmount"] + select_method["currencyList"][0]["showFee"]), **fees)
        self.checkCodeAndMessage(order_info)
        self.checkSubmitOrderInfo(order_info["data"], select_method["currencyList"][0]["showFee"], pay_order, select_method["type"], pay_order_info["businessOrderNo"])
        # 查询订单状态，等待支付完成
        query_order = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info["businessOrderNo"])
        self.assertEqual(query_order["businessAmount"], pay_order_info["businessAmount"])
        # 查询数据库，直到通道回调成功
        # self.waitUntilPayChannelOrderComplete(pay_order)
        self.waitUntilPayChannelOrderComplete(pay_order)
        query_order = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info["businessOrderNo"])
        self.assertEqual(query_order["status"], PayOrder.PAY_SUCCESS.value)
        # 查询钱包余额
        sourceAccountBalance2 = self.client.getRoAccountBalance(pay_order_info["sourceRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"源账户资产: {sourceAccountBalance2}, 变化了{sourceAccountBalance2 - sourceAccountBalance}")
        targetAccountBalance2 = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"目标账户资产: {targetAccountBalance2}, 变化了{targetAccountBalance2 - targetAccountBalance}")

        self.assertAlmostEqual(sourceAccountBalance - sourceAccountBalance2, pay_order_info["businessAmount"] + select_method["currencyList"][0]["fee"], delta=0.1**7)
        self.assertAlmostEqual(targetAccountBalance2 - targetAccountBalance, pay_order_info["businessAmount"], delta=0.1**7)
        self.assertIsNotNone(query_order["serviceChannelOrderId"], "支付订单完成后应返回通道id")

        # 查询交易hash
        tx_hash = query_order["serviceChannelOrderId"]
        self.client.checkRoTransactionHash(tx_hash, pay_order_info, select_method["currencyList"][0]["fee"])

    """
    异常的测试场景
    """

    def test_014_queryBindAchAccount_userNotExist(self):
        """
        不存在的用户查询绑定的ach账户
        """
        self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        sign = RPSData.sign
        accounts = self.client.queryBindBankAccount(sign, RPSData.app_key, RPSData.user_not_exist, "USD")
        self.assertEqual(accounts, [], "应该返回一个空的账户信息")

    def test_015_queryBindAchAccount_userNotLogin(self):
        """
        未登录的用户查询绑定的ach账户
        """
        self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        sign = RPSData.sign
        accounts = self.client.queryBindBankAccount(sign, RPSData.app_key, RPSData.user_not_login, "USD")
        self.assertEqual(accounts, [], "应该返回一个空的账户信息")

    def test_016_queryBindAchAccount_appKeyNotCorrect(self):
        """
        appkey不正确或为none时，查询绑定的ach账户
        """
        sign = RPSData.sign
        accounts = self.client.queryBindBankAccount(sign, RPSData.app_key + "abc", RPSData.user_not_login, "USD")
        self.checkCodeAndMessage(accounts, "PAY_RPS_664", "appkey not exist")

        accounts = self.client.queryBindBankAccount(RPSData.sign, None, RPSData.user_id, "USD")
        self.checkCodeAndMessage(accounts, "PAY_RPS_663", "header parameter appkey cannot be null")

    def test_017_bindAchAccount_userNotExist(self):
        """
        不存在的用户绑定ach账户
        """
        account_info = RPSData.ach_account.copy()
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_not_exist, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res, "PAY_RPS_715", "userid not match")
        # 校验绑定失败后应查询不到
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_not_exist, account_info["currency"])
        self.assertEqual(accounts, [])

    def test_018_bindAchAccount_userNotLogin(self):
        """
        未登录的用户绑定ach账户
        """
        kyc_name = ""
        if RPSData.is_check_db:
            kyc_info = self.client.queryKycInfoFromDB(self, RPSData.user_not_login)
            kyc_success = [i for i in kyc_info if i["checkState"] == "SUCCESS"]
            if kyc_success:
                kyc_name = kyc_success[0]["userName"]
        account_info = RPSData.ach_account.copy()
        account_info["holder"] = kyc_name
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_not_login, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res, "PAY_RPS_715", "userid not match")
        self.assertIsNone(bind_res["data"])
        # 校验绑定失败后应查询不到
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_not_login, account_info["currency"])
        self.assertEqual(accounts, [])

    def test_019_bindAchAccount_userNotKyc(self):
        """
        没有进行kyc的用户绑定ach账户
        """
        account_info = RPSData.ach_account.copy()
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_not_kyc, RPSData.user_not_kyc_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res, "PAY_RPS_674", "The bank account name does not match the KYC name")
        self.assertIsNone(bind_res["data"])
        # 校验绑定失败后应查询不到
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_not_kyc, account_info["currency"])
        self.assertEqual(accounts, [])

    def test_020_bindAchAccount_accountHasBeenBind(self):
        """
        绑定ach账户, 银行账户已经被绑定过
        """
        self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        account_info = RPSData.ach_account.copy()
        # account_info["holder"] += "asd"
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res, "PAY_RPS_710", "verified account cannot be more than 1")
        self.assertIsNone(bind_res["data"])
        # 校验绑定失败后应查询不到
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        self.assertEqual(len(accounts), 1)

    def test_021_bindAchAccount_accountNameNotMatchKycName_firstNameMatch(self):
        """
        绑定ach账户, 银行账户的持有人和kyc不一致, firstName能对应上
        """
        account_info = RPSData.ach_account.copy()
        account_info["holder"] += "asd"
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res)
        self.checkAchAccountInfo(bind_res["data"], account_info, RPSData.user_id)
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        self.assertEqual(len(accounts), 1, "查询接口查询不到绑定的银行账户")
        self.checkAchAccountInfoFromDB(accounts[0], RPSData.user_id)

    def test_022_bindAchAccount_accountNameNotMatchKycName_lastNameMatch(self):
        """
        绑定ach账户, 银行账户的持有人和kyc不一致, lastName对应上
        """
        account_info = RPSData.ach_account.copy()
        account_info["holder"] += "asd"
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res)
        self.checkAchAccountInfo(bind_res["data"], account_info, RPSData.user_id)
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        self.assertEqual(len(accounts), 1, "查询接口查询不到绑定的银行账户")
        self.checkAchAccountInfoFromDB(accounts[0], RPSData.user_id)

    def test_023_bindAchAccount_accountNameNotMatchKycName_bothNotMatch(self):
        """
        绑定ach账户, 银行账户的持有人和kyc不一致, firstName和lastName都对应不上
        """
        account_info = RPSData.ach_account.copy()
        account_info["holder"] = "Ass" + account_info["holder"] + "asd"
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res, "PAY_RPS_674", "The bank account name does not match the KYC name")
        self.assertIsNone(bind_res["data"])
        # 校验绑定失败后应查询不到
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        self.assertEqual(accounts, [])

    def test_024_bindAchAccount_routingNumberNotCorrect(self):
        """
        绑定ach账户，routingNumber不正确 TODO bug
        """
        account_info = RPSData.ach_account.copy()
        account_info["routingNumber"] = account_info["routingNumber"].replace("1", "2")
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res, "PAY_RPS_717", "bank account token cannot be empty")
        self.assertIsNone(bind_res["data"])
        # 校验绑定失败后应查询不到
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        self.assertEqual(accounts, [])

    def test_025_bindAchAccount_accountNumberNotCorrect(self):
        """
        绑定ach账户，routingNumber不正确 TODO bug
        """
        account_info = RPSData.ach_account.copy()
        account_info["accountNumber"] = account_info["accountNumber"].replace("1", "2")
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res, "PAY_RPS_717", "bank account token cannot be empty")
        self.assertIsNone(bind_res["data"])
        # 校验绑定失败后应查询不到
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        self.assertEqual(accounts, [])

    def test_026_bindAchAccount_holderTypeNotCorrect(self):
        """
        绑定ach账户，holderType不正确 TODO bug
        """
        account_info = RPSData.ach_account.copy()
        account_info["holderType"] = "111asd"
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res, "PAY_RPS_717", "bank account token cannot be empty")
        self.assertIsNone(bind_res["data"])
        # 校验绑定失败后应查询不到
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        self.assertEqual(accounts, [])

    def test_027_bindAchAccount_countryNotCorrect(self):
        """
        绑定ach账户，country不正确 TODO bug
        """
        account_info = RPSData.ach_account.copy()
        account_info["country"] = "UK"
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res, "PAY_RPS_717", "bank account token cannot be empty")
        self.assertIsNone(bind_res["data"])
        # 校验绑定失败后应查询不到
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        self.assertEqual(accounts, [])

    def test_028_bindAchAccount_accountInfoIsMissingItem(self):
        """
        绑定ach账户，账户信息缺少某一项不正确 TODO bug
        """
        account_info = RPSData.ach_account.copy()
        account_info.pop("country")
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res, "PAY_RPS_684", "bank acount country cannot be empty")
        self.assertIsNone(bind_res["data"])
        # 校验绑定失败后应查询不到
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        self.assertEqual(accounts, [])

    def test_029_verifyAchAccount_oneCheckAmountEnterError(self):
        """
        校验ach账户，一个校验金额输入错误时报错，然后输入正确的校验金额
        """
        account_info = RPSData.ach_account.copy()
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res)
        self.assertIsNotNone(bind_res["data"])
        # 校验绑定失败后应查询不到
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        account_id = accounts[0]["id"]
        check_info = self.client.verifyBankAccount(RPSData.user_id, RPSData.user_login_token, account_id, 0.11, 0.45)
        self.checkCodeAndMessage(check_info, "PAYIN_STRIPE_610", "bank account verify failed ,The amounts provided do not match the amounts that were sent to the bank account")
        self.assertIsNone(check_info["data"])
        check_info2 = self.client.verifyBankAccount(RPSData.user_id, RPSData.user_login_token, account_id, 0.32, 0.45)
        self.checkCodeAndMessage(check_info2)
        self.assertEqual(check_info2["data"], True, "校验账户错误")
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, "USD")
        self.assertEqual(len(accounts), 1, "查询接口查询不到绑定的银行账户")
        self.checkAchAccountInfoFromDB(accounts[0], RPSData.user_id)
        self.assertEqual(accounts[0]["status"], PayOrder.PAY_FAIL.value)

    def test_030_verifyAchAccount_checkAmountEnterIllegal(self):
        """
        校验ach账户，一个校验金额输入非法错误时报错，然后输入正确的校验金额
        """
        account_info = RPSData.ach_account.copy()
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res)
        self.assertIsNotNone(bind_res["data"])
        # 校验绑定失败后应查询不到
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        account_id = accounts[0]["id"]
        check_info = self.client.verifyBankAccount(RPSData.user_id, RPSData.user_login_token, account_id, 0, 0.45)
        self.checkCodeAndMessage(check_info, "PAY_RPS_687", "verify amount cannot be null or<=0")
        self.assertIsNone(check_info["data"])
        check_info = self.client.verifyBankAccount(RPSData.user_id, RPSData.user_login_token, account_id, "abc123", 0.45)
        self.checkCodeAndMessage(check_info, "PAY_RPS_600", "service error")  # 前端做限制
        self.assertIsNone(check_info["data"])
        check_info2 = self.client.verifyBankAccount(RPSData.user_id, RPSData.user_login_token, account_id, 0.32, 0.45)
        self.checkCodeAndMessage(check_info2)
        self.assertEqual(check_info2["data"], True, "校验账户错误")
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, "USD")
        self.assertEqual(len(accounts), 1, "查询接口查询不到绑定的银行账户")
        self.checkAchAccountInfoFromDB(accounts[0], RPSData.user_id)
        self.assertEqual(accounts[0]["status"], PayOrder.PAY_FAIL.value)

    def test_031_verifyAchAccount_checkAmountEnterError3times(self):
        """
        校验ach账户，校验金额输入错误达到3次上限
        """
        account_info = RPSData.ach_account.copy()
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res)
        self.assertIsNotNone(bind_res["data"])
        # 校验绑定失败后应查询不到
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        account_id = accounts[0]["id"]
        check_info = self.client.verifyBankAccount(RPSData.user_id, RPSData.user_login_token, account_id, 1.11, 0.45)
        err_msg = 'bank account verify failed ,The amounts provided do not match the amounts that were sent to the bank account'
        self.checkCodeAndMessage(check_info, "PAYIN_STRIPE_610", err_msg)
        self.assertIsNone(check_info["data"])
        check_info = self.client.verifyBankAccount(RPSData.user_id, RPSData.user_login_token, account_id, 1.11, 0.11)
        self.checkCodeAndMessage(check_info, "PAYIN_STRIPE_610", err_msg)
        self.assertIsNone(check_info["data"])
        check_info2 = self.client.verifyBankAccount(RPSData.user_id, RPSData.user_login_token, account_id, 0.3, 0.43)
        self.checkCodeAndMessage(check_info2, "PAY_RPS_675", "bank account verify failed ,The amounts provided do not match the amounts that were sent to the bank account,bank account verify greater than 3 times")
        self.assertIsNone(check_info2["data"], "校验账户错误")
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, "USD")
        self.assertEqual(len(accounts), 1, "查询接口查询不到绑定的银行账户")
        self.checkAchAccountInfoFromDB(accounts[0], RPSData.user_id)
        self.assertEqual(accounts[0]["status"], 1, "账户状态不是待验证的状态")

    def test_032_verifyAchAccount_checkAccountHasBeenVerified(self):
        """
        校验ach账户，账户校验成功后，再次校验账户
        """
        account_info = RPSData.ach_account.copy()
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res)
        self.assertIsNotNone(bind_res["data"])
        # 校验绑定失败后应查询不到
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        account_id = accounts[0]["id"]
        check_info = self.client.verifyBankAccount(RPSData.user_id, RPSData.user_login_token, account_id, 0.32, 0.45)
        self.checkCodeAndMessage(check_info)
        self.assertEqual(check_info["data"], True, "校验账户错误")
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, "USD")
        self.assertEqual(len(accounts), 1, "查询接口查询不到绑定的银行账户")
        self.checkAchAccountInfoFromDB(accounts[0], RPSData.user_id)
        self.assertEqual(accounts[0]["status"], 3)

        check_info = self.client.verifyBankAccount(RPSData.user_id, RPSData.user_login_token, account_id, 0.32, 0.45)
        self.checkCodeAndMessage(check_info, "PAY_RPS_718", "a bank account has verified")
        self.assertIsNone(check_info["data"])

    def test_033_verifyAchAccount_userNotMatchWithBindUser(self):
        """
        校验ach账户，A用户申请绑定银行账户，B用户去校验账户
        """
        account_info = RPSData.ach_account.copy()
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res)
        self.assertIsNotNone(bind_res["data"])
        # 校验绑定失败后应查询不到
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        account_id = accounts[0]["id"]
        check_info = self.client.verifyBankAccount(RPSData.user_not_kyc, RPSData.user_not_kyc_login_token, account_id, 0.32, 0.45)
        self.checkCodeAndMessage(check_info, "PAY_RPS_671", "bank account not exist")
        self.assertIsNone(check_info["data"], "校验账户错误")
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, "USD")
        self.assertEqual(accounts[0]["id"], account_id, "查询接口查询不到绑定的银行账户")
        self.assertEqual(accounts[0]["status"], 1, "查询接口查询不到绑定的银行账户")
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_not_kyc, "USD")
        self.assertEqual(accounts, [], "查询接口查询不到绑定的银行账户")

    def test_034_verifyAchAccount_userLogout(self):
        """
        校验ach账户，A用户申请绑定银行账户，token失效的用户去验证账户
        """
        account_info = RPSData.ach_account.copy()
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res)
        self.assertIsNotNone(bind_res["data"])
        # 校验绑定失败后应查询不到
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        account_id = accounts[0]["id"]
        check_info = self.client.verifyBankAccount(RPSData.user_not_login, RPSData.user_login_token.replace("e", "a"), account_id, 0.32, 0.45)
        self.checkCodeAndMessage(check_info, "PAY_RPS_713", "user token invalid")
        self.assertIsNone(check_info["data"], "校验账户错误")
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, "USD")
        self.assertEqual(accounts[0]["id"], account_id, "查询接口查询不到绑定的银行账户")
        self.assertEqual(accounts[0]["status"], 1, "查询接口查询不到绑定的银行账户")
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_not_login, "USD")
        self.assertEqual(accounts, [], "查询接口查询不到绑定的银行账户")

    def test_035_verifyAchAccount_userNotExist(self):
        """
        校验ach账户，A用户申请绑定银行账户，不存在的B用户去校验账户
        """
        account_info = RPSData.ach_account.copy()
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res)
        self.assertIsNotNone(bind_res["data"])
        # 校验绑定失败后应查询不到
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        account_id = accounts[0]["id"]
        check_info = self.client.verifyBankAccount(RPSData.user_not_exist, RPSData.user_login_token.replace("e", "a"), account_id, 0.32, 0.45)
        self.checkCodeAndMessage(check_info, "PAY_RPS_713", "user token invalid")
        self.assertIsNone(check_info["data"], "校验账户错误")
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, "USD")
        self.assertEqual(accounts[0]["id"], account_id, "查询接口查询不到绑定的银行账户")
        self.assertEqual(accounts[0]["status"], 1, "查询接口查询不到绑定的银行账户")
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_not_exist, "USD")
        self.assertEqual(accounts, [], "查询接口查询不到绑定的银行账户")

    def test_036_unbindAchAccount_bindAccountNotExist(self):
        """
        解绑账户，账户id为不存在的一个银行账户
        """
        account_id = 111111111
        unbind_res = self.client.unbindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_id, int(time.time()))
        self.checkCodeAndMessage(unbind_res, "PAY_RPS_671", "bank account not exist")

    def test_037_unbindAchAccount_otherUserBindAccount(self):
        """
        解绑账户，解绑的是其他人绑定的账户
        """
        account_id = self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        unbind_res = self.client.unbindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_not_kyc, account_id, int(time.time()))
        self.checkCodeAndMessage(unbind_res, "PAY_RPS_671", "bank account not exist")

    def test_038_unbindAchAccount_userNotExist(self):
        """
        解绑账户，解绑人是不存在的用户
        """
        account_id = self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        unbind_res = self.client.unbindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_not_exist, account_id, int(time.time()))
        self.checkCodeAndMessage(unbind_res, "PAY_RPS_671", "bank account not exist")

    def test_039_unbindAchAccount_userLogout(self):
        """
        解绑账户，解绑人是登录失效的用户
        """
        account_id = self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        unbind_res = self.client.unbindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_not_login, account_id, int(time.time()))
        self.checkCodeAndMessage(unbind_res, "PAY_RPS_671", "bank account not exist")

    def test_040_unbindAchAccount_appKeyInCorrect(self):
        """
        解绑账户，appkey不正确
        """
        account_id = self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        unbind_res = self.client.unbindBankAccount(RPSData.sign, RPSData.app_key + "23", RPSData.user_id, account_id, int(time.time()))
        self.checkCodeAndMessage(unbind_res, "PAY_RPS_664", "appkey not exist")

    def test_041_unbindAchAccount_accountNotPassVerify(self):
        """
        解绑账户，账户未通过校验
        """
        account_info = RPSData.ach_account.copy()
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        account_id = bind_res["data"]["id"]
        unbind_res = self.client.unbindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_id, int(time.time()))
        self.assertTrue(unbind_res)
        q_account = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"].upper())
        self.assertEqual(q_account, [])

    def test_042_unbindAchAccount_accountVerifyFailedReachLimit(self):
        """
        解绑账户，账户失败次数达到上限
        """
        account_info = RPSData.ach_account.copy()
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        account_id = bind_res["data"]["id"]
        for i in range(3):
            self.client.verifyBankAccount(RPSData.user_id, RPSData.user_login_token, account_id, 0.11, 0.45)
        unbind_res = self.client.unbindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_id, int(time.time()))
        self.assertTrue(unbind_res)
        q_account = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"].upper())
        self.assertEqual(q_account, [])

    def test_043_queryPlaidLinkToken_appKeyInCorrect(self):
        """
        查询plaid token，appkey不正确
        """
        account_id = self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        q_res = self.client.queryPlaidLinkToken(RPSData.user_id, RPSData.user_login_token, RPSData.app_key + "23", account_id)
        self.checkCodeAndMessage(q_res, "PAY_RPS_664", "appkey not exist")

    def test_044_queryPlaidLinkToken_userNotExist(self):
        """
        查询plaid token，用户不存在
        """
        account_id = self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        q_res = self.client.queryPlaidLinkToken(RPSData.user_not_exist, RPSData.user_login_token.replace("e", "a"), RPSData.app_key, account_id)
        self.checkCodeAndMessage(q_res, "PAY_RPS_713", "user token invalid")

    def test_045_queryPlaidLinkToken_userNotMatchAccount(self):
        """
        查询plaid token，用户和银行账户不匹配
        """
        account_id = self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        q_res = self.client.queryPlaidLinkToken(RPSData.user_not_kyc, RPSData.user_not_kyc_login_token, RPSData.app_key, account_id)
        self.checkCodeAndMessage(q_res, "PAY_RPS_601", "parameter check failed:bank account not exist")

    def test_046_submitPayInOrder_appKeyInCorrect(self):
        """
        支付下单，appkey不正确
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 12.34,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": "xxxx",
            "targetRoxeAccount": RPSData.user_roxe_account,
            "currency": "USD",
            "businessType": BusinessType.CHARGE.value,
            "country": "US",
        }
        pay_order = self.client.submitOrderPayIn(RPSData.app_key + "abc", RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_664", "appkey not exist")

    def test_047_submitPayInOrder_appKeyIsNone(self):
        """
        支付下单，appkey为None
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 12.34,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": "xxxx",
            "targetRoxeAccount": RPSData.user_roxe_account,
            "currency": "USD",
            "businessType": BusinessType.CHARGE.value,
            "country": "US",
        }
        pay_order = self.client.submitOrderPayIn(None, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_663", "header parameter appkey cannot be null")

    def test_048_submitPayInOrder_businessAmountIllegal(self):
        """
        支付下单，businessAmount为非法值：0、负数，none、特殊字符、字母
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 0,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": "xxxx",
            "targetRoxeAccount": RPSData.user_roxe_account,
            "currency": "USD",
            "businessType": BusinessType.CHARGE.value,
            "country": "US",
        }
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_652", "businessAmount cannot be null or less than or equal to 0")
        pay_order_info["businessAmount"] = -1
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_652", "businessAmount cannot be null or less than or equal to 0")
        pay_order_info["businessAmount"] = None
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_652", "businessAmount cannot be null or less than or equal to 0")
        pay_order_info["businessAmount"] = "!@#$￥%"
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_600", "service error")
        pay_order_info["businessAmount"] = "abc"
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_600", "service error")

    def test_049_submitPayInOrder_channelFeeDeductionMethodNotSupport(self):
        """
        支付下单，channelFeeDeductionMethod为不支持的值：0、负数，none、特殊字符、字母
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 10,
            "channelFeeDeductionMethod": 1,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": "xxxx",
            "targetRoxeAccount": RPSData.user_roxe_account,
            "currency": "USD",
            "businessType": BusinessType.CHARGE.value,
            "country": "US",
        }
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_695", "channel fee deduction method invalid")
        pay_order_info["channelFeeDeductionMethod"] = 3
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_695", "channel fee deduction method invalid")
        pay_order_info["channelFeeDeductionMethod"] = None
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_694", "channel fee deduction method cannot be empty")
        pay_order_info["channelFeeDeductionMethod"] = "!@#$￥%"
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_600", "service error")
        pay_order_info["channelFeeDeductionMethod"] = "abc"
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_600", "service error")

    def test_050_submitPayInOrder_businessOrderNoIsRepeat_oldOrderNotPay(self):
        """
        支付下单，已提交的businessOrderNo，没有进行支付时，可以使用原来的businessOrderNo进行重复提交
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 10,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": "xxxx",
            "targetRoxeAccount": RPSData.user_roxe_account,
            "currency": "USD",
            "businessType": BusinessType.CHARGE.value,
            "country": "US",
        }
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.assertTrue(isinstance(pay_order, int))
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.assertTrue(isinstance(pay_order, int))

    def test_051_submitPayInOrder_businessOrderNoIsRepeat_oldOrderHasPay(self):
        """
        支付下单，已提交的businessOrderNo，进行了支付，可以使用原来的businessOrderNo进行重复提交
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 10,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": RPSData.user_roxe_account,
            "targetRoxeAccount": RPSData.user_roxe_account_a,
            "currency": "USD",
            "businessType": BusinessType.TRANSFER.value,
            "country": "US",
        }
        # 查询钱包余额
        sourceAccountBalance = self.client.getRoAccountBalance(pay_order_info["sourceRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"目标账户资产: {sourceAccountBalance}")
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.assertTrue(isinstance(pay_order, int))
        # 查询支付方式
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)
        self.checkCodeAndMessage(methods)
        self.checkPaymentMethod(methods["data"], pay_order_info["businessAmount"], RPSData.user_id, sourceAccountBalance)

        # 选择支付方式进行支付
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method))
        fees = {
            "allowanceFee": select_method["currencyList"][0]["allowanceFee"],
            "showFee": select_method["currencyList"][0]["showFee"],
        }
        order_info = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, RPSData.app_key,
                                                        pay_order, pay_order_info["currency"], select_method["type"],
                                                        select_method["serviceChannel"],
                                                        select_method["currencyList"][0]["fee"],
                                                        ApiUtils.parseNumberDecimal(pay_order_info["businessAmount"] + select_method["currencyList"][0]["showFee"]), **fees)
        self.checkCodeAndMessage(order_info)
        self.checkSubmitOrderInfo(order_info["data"], select_method["currencyList"][0]["showFee"], pay_order, select_method["type"], pay_order_info["businessOrderNo"])

        pay_order_info2 = pay_order_info.copy()
        pay_order_info2["businessAmount"] = 12
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_669", "the order has been confirmed , cannot be changed")

    def test_052_submitPayInOrder_businessItemNameIllegal(self):
        """
        支付下单，businessItemName不合法，为None, 空字符串
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 10,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": None,
            "sourceRoxeAccount": RPSData.user_roxe_account,
            "targetRoxeAccount": RPSData.user_roxe_account_a,
            "currency": "USD",
            "businessType": BusinessType.TRANSFER.value,
            "country": "US",
        }
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_668", "businessItemName cannot be empty")
        pay_order_info["businessItemName"] = ""
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_668", "businessItemName cannot be empty")

    def test_053_submitPayInOrder_currencyIllegal(self):
        """
        支付下单，currency不合法：空、None、其他币种
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 10,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "api test",
            "sourceRoxeAccount": RPSData.user_roxe_account,
            "targetRoxeAccount": RPSData.user_roxe_account_a,
            "currency": "",
            "businessType": BusinessType.TRANSFER.value,
            "country": "US",
        }
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_655", "currency cannot be empty")
        pay_order_info["currency"] = None
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_655", "currency cannot be empty")
        pay_order_info["currency"] = "asdg"
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_719", "no available payment methods")

    def test_054_submitPayInOrder_currencyNotUpper(self):
        """
        支付下单，currency不合法：小写、大小写混合
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 10,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "api test",
            "sourceRoxeAccount": RPSData.user_roxe_account,
            "targetRoxeAccount": RPSData.user_roxe_account_a,
            "currency": "usd",
            "businessType": BusinessType.TRANSFER.value,
            "country": "US",
        }
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.assertTrue(isinstance(pay_order, int))
        pay_order_info["currency"] = "Usd"
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.assertTrue(isinstance(pay_order, int))

    def test_055_submitPayInOrder_sourceRoxeAccountIllegal_transfer(self):
        """
        支付下单，转账业务，sourceRoxeAccount为：空、None、无效地址
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 10,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "api test",
            "sourceRoxeAccount": None,
            "targetRoxeAccount": RPSData.user_roxe_account_a,
            "currency": "USD",
            "businessType": BusinessType.TRANSFER.value,
            "country": "US",
        }
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_603", "parameter error:sourceRoxeAccount cannot be empty")
        pay_order_info["sourceRoxeAccount"] = ""
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_603", "parameter error:sourceRoxeAccount cannot be empty")
        pay_order_info["sourceRoxeAccount"] = "abc123"
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.assertTrue(isinstance(pay_order, int))

    def test_056_submitPayInOrder_targetRoxeAccountIllegal_transfer(self):
        """
        支付下单，转账业务，targetRoxeAccount为：空、None、无效地址
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 10,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "api test",
            "sourceRoxeAccount": RPSData.user_roxe_account_a,
            "targetRoxeAccount": None,
            "currency": "USD",
            "businessType": BusinessType.TRANSFER.value,
            "country": "US",
        }
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_603", "parameter error:targetRoxeAccount cannot be empty")
        pay_order_info["targetRoxeAccount"] = ""
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_603", "parameter error:targetRoxeAccount cannot be empty")
        pay_order_info["targetRoxeAccount"] = "abc123"
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.assertTrue(isinstance(pay_order, int))

    def test_057_submitPayInOrder_businessTypeIllegal(self):
        """
        支付下单，businessType为：空、None、其他无效类型
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 10,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "api test",
            "sourceRoxeAccount": RPSData.user_roxe_account,
            "targetRoxeAccount": RPSData.user_roxe_account,
            "currency": "USD",
            "businessType": "",
            "country": "US",
        }
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_603", "parameter error:businessType cannot be empty")
        pay_order_info["businessType"] = None
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_603", "parameter error:businessType cannot be empty")
        pay_order_info["businessType"] = "abc123"
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_719", "no available payment methods")

    def test_058_submitPayInOrder_countryIllegal(self):
        """
        支付下单，country为：空、None、其他无效类型
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 10,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "api test",
            "sourceRoxeAccount": RPSData.user_roxe_account,
            "targetRoxeAccount": RPSData.user_roxe_account,
            "currency": "USD",
            "businessType": BusinessType.TRANSFER.value,
            "country": "",
        }
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_603", "parameter error:country cannot be empty")
        pay_order_info["country"] = None
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_603", "parameter error:country cannot be empty")
        pay_order_info["country"] = "United States"
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_719", "no available payment methods")

    def test_059_queryOrderPayInMethod_appKeyInCorrect(self):
        """
        查询支付订单的支付方式，appkey不正确
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 12.34,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": "xxxx",
            "targetRoxeAccount": RPSData.user_roxe_account,
            "currency": "USD",
            "businessType": BusinessType.CHARGE.value,
            "country": "US",
        }
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()*1000), pay_order_info)
        pay_methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order, RPSData.app_key + "abc")
        self.checkCodeAndMessage(pay_methods, "PAY_RPS_664", "appkey not exist")

        pay_methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order, None, keepArg=True)
        self.checkCodeAndMessage(pay_methods, "PAY_RPS_663", "header parameter appkey cannot be null")

    def test_060_queryOrderPayInMethod_payOrderNotExist(self):
        """
        查询支付订单的支付方式，支付订单不存在
        """
        pay_order = 12345678901234567
        pay_methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order, RPSData.app_key)
        self.checkCodeAndMessage(pay_methods, "PAY_RPS_700", "order not exist")

    def test_061_queryOrderPayInMethod_userLoginTokenNotInvalid(self):
        """
        查询支付订单的支付方式，用户的登录token无效
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 12.34,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": "xxxx",
            "targetRoxeAccount": RPSData.user_roxe_account,
            "currency": "USD",
            "businessType": BusinessType.CHARGE.value,
            "country": "US",
        }
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()*1000), pay_order_info)
        pay_methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token.replace("e", "a"), pay_order, RPSData.app_key)
        self.checkCodeAndMessage(pay_methods, "PAY_RPS_713", "user token invalid")

    def test_062_queryOrderPayInMethod_userLoginTokenNotMatchUserId(self):
        """
        查询支付订单的支付方式，用户的登录token和userId不匹配
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 12.34,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": "xxxx",
            "targetRoxeAccount": RPSData.user_roxe_account,
            "currency": "USD",
            "businessType": BusinessType.CHARGE.value,
            "country": "US",
        }
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()*1000), pay_order_info)
        pay_methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_not_kyc_login_token, pay_order, RPSData.app_key)
        self.checkCodeAndMessage(pay_methods, "PAY_RPS_715", "userid not match")

    def test_063_queryOrderPayInMethod_payOrderIsComplete(self):
        """
        查询支付订单的支付方式，支付订单已经完成
        """
        amount = 12
        order = self.client.submitPayOrderTransferToRoxeAccount(RPSData.user_roxe_account, RPSData.user_roxe_account_a, amount, businessType=BusinessType.TRANSFER.value)
        pay_order_id = order["id"]
        pay_methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order_id, RPSData.app_key)
        s_balance = self.client.getRoAccountBalance(RPSData.user_roxe_account, "USD")
        self.checkCodeAndMessage(pay_methods)
        self.checkPaymentMethod(pay_methods["data"], amount, RPSData.user_id, s_balance)

    def test_064_queryOrderPayInMethod_payOrderIsFailed(self):
        """
        查询支付订单的支付方式，支付订单支付失败
        """
        account_info = RPSData.ach_account.copy()
        account_info["accountNumber"] = RPSData.account_using_failed
        self.client.bindAndVerifyAchAccount(account_info)
        # 下支付订单
        amount = 12.34
        currency = RPSData.ach_account["currency"].upper()
        # 查询钱包余额
        targetAccountBalance = self.client.getRoAccountBalance(RPSData.user_roxe_account, currency)
        self.client.logger.info(f"目标账户资产: {targetAccountBalance}")

        pay_order, coupon_code = self.client.submitAchPayOrder(RPSData.user_roxe_account, amount, currency, expect_pay_success=False)
        time_out = 60
        flag = False
        if RPSData.is_check_db:
            sql = "select * from `roxe_pay_in_out`.roxe_pay_in_order where id='{}'".format(pay_order["id"])
            b_time = time.time()
            while time.time() - b_time < time_out:
                db_res = self.mysql.exec_sql_query(sql)
                self.client.logger.info(f"查询的数据库结果: {db_res[0]}")
                if db_res[0]["payFailedReason"]:
                    flag = True
                    reason = "The customer\'s bank account could not be located."
                    self.assertIn(reason, db_res[0]["payFailedReason"], "支付失败原因不正确")
                    break
                time.sleep(10)
        self.assertTrue(flag, "ach支付订单应该失败")
        pay_order_id = pay_order["id"]
        pay_methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order_id, RPSData.app_key)
        s_balance = self.client.getRoAccountBalance(RPSData.user_roxe_account, "USD")
        self.checkCodeAndMessage(pay_methods)
        self.checkPaymentMethod(pay_methods["data"], amount, RPSData.user_id, s_balance)

    def test_065_selectPaymentMethod_appKeyInCorrect(self):
        """
        选择支付方式，appkey不正确，或者为None
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 12.34,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": RPSData.user_roxe_account,
            "targetRoxeAccount": RPSData.user_roxe_account_a,
            "currency": "USD",
            "businessType": BusinessType.TRANSFER.value,
            "country": "US",
        }
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()*1000), pay_order_info)
        pay_methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order, RPSData.app_key)
        self.checkCodeAndMessage(pay_methods)

        select_method = [i for i in pay_methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method))
        payment_amount = pay_order_info["businessAmount"] + select_method["currencyList"][0]["showFee"]
        fees = {
            "allowanceFee": select_method["currencyList"][0]["allowanceFee"],
            "showFee": select_method["currencyList"][0]["showFee"],
        }
        pay_methods = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, RPSData.app_key + "abc", pay_order,
                                                         pay_order_info["currency"], select_method["type"],
                                                         select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
                                                         payment_amount, **fees)
        self.checkCodeAndMessage(pay_methods, "PAY_RPS_664", "appkey not exist")
        submit_order = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, None, pay_order,
                                                          pay_order_info["currency"], select_method["type"],
                                                          select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
                                                          payment_amount, **fees)
        self.checkCodeAndMessage(submit_order, "PAY_RPS_663", "header parameter appkey cannot be null")

    def test_066_selectPaymentMethod_userLoginTokenInvalid(self):
        """
        选择支付方式，用户token无效
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 12.34,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": RPSData.user_roxe_account,
            "targetRoxeAccount": RPSData.user_roxe_account_a,
            "currency": "USD",
            "businessType": BusinessType.TRANSFER.value,
            "country": "US",
        }
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()*1000), pay_order_info)
        pay_methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order, RPSData.app_key)
        self.checkCodeAndMessage(pay_methods)

        select_method = [i for i in pay_methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method))
        fees = {
            "allowanceFee": select_method["currencyList"][0]["allowanceFee"],
            "showFee": select_method["currencyList"][0]["showFee"],
        }
        payment_amount = pay_order_info["businessAmount"] + select_method["currencyList"][0]["showFee"]
        submit_order = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token.replace("e", "a"), RPSData.app_key, pay_order,
                                                          pay_order_info["currency"], select_method["type"],
                                                          select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
                                                          payment_amount, **fees)
        self.checkCodeAndMessage(submit_order, "PAY_RPS_713", "user token invalid")
        self.assertIsNone(submit_order["data"])

    def test_067_selectPaymentMethod_userLoginTokenNotMatchUserId(self):
        """
        选择支付方式，用户token和userId不匹配
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 12.34,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": RPSData.user_roxe_account,
            "targetRoxeAccount": RPSData.user_roxe_account_a,
            "currency": "USD",
            "businessType": BusinessType.TRANSFER.value,
            "country": "US",
        }
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()*1000), pay_order_info)
        pay_methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order, RPSData.app_key)
        self.checkCodeAndMessage(pay_methods)

        select_method = [i for i in pay_methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method))
        fees = {
            "allowanceFee": select_method["currencyList"][0]["allowanceFee"],
            "showFee": select_method["currencyList"][0]["showFee"],
        }
        payment_amount = pay_order_info["businessAmount"] + select_method["currencyList"][0]["showFee"]
        submit_order = self.client.submitOrderPayInMethod(RPSData.user_not_kyc, RPSData.user_login_token, RPSData.app_key, pay_order,
                                                          pay_order_info["currency"], select_method["type"],
                                                          select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
                                                          payment_amount, **fees)
        self.checkCodeAndMessage(submit_order, "PAY_RPS_715", "userid not match")
        self.assertIsNone(submit_order["data"])

    def test_068_selectPaymentMethod_currencyNotMatchPayOrder(self):
        """
        选择支付方式，currency不正确: 和支付订单不一致
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 12.34,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": RPSData.user_roxe_account,
            "targetRoxeAccount": RPSData.user_roxe_account_a,
            "currency": "USD",
            "businessType": BusinessType.TRANSFER.value,
            "country": "US",
        }
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()*1000), pay_order_info)
        pay_methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order, RPSData.app_key)
        self.checkCodeAndMessage(pay_methods)

        select_method = [i for i in pay_methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method))
        fees = {
            "allowanceFee": select_method["currencyList"][0]["allowanceFee"],
            "showFee": select_method["currencyList"][0]["showFee"],
        }
        payment_amount = pay_order_info["businessAmount"] + select_method["currencyList"][0]["showFee"]
        submit_order = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, RPSData.app_key, pay_order,
                                                          pay_order_info["currency"] + "A", select_method["type"],
                                                          select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
                                                          payment_amount, **fees)
        self.checkCodeAndMessage(submit_order, "PAY_RPS_603", "parameter error currency mismatch")
        self.assertIsNone(submit_order["data"])

    def test_069_selectPaymentMethod_channelTypeIncorrect(self):
        """
        选择支付方式，支付通道的type和查询出的不一致
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 12.34,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": RPSData.user_roxe_account,
            "targetRoxeAccount": RPSData.user_roxe_account_a,
            "currency": "USD",
            "businessType": BusinessType.TRANSFER.value,
            "country": "US",
        }
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()*1000), pay_order_info)
        pay_methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order, RPSData.app_key)
        self.checkCodeAndMessage(pay_methods)

        select_method = [i for i in pay_methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method))
        fees = {
            "allowanceFee": select_method["currencyList"][0]["allowanceFee"],
            "showFee": select_method["currencyList"][0]["showFee"],
        }
        payment_amount = pay_order_info["businessAmount"] + select_method["currencyList"][0]["showFee"]
        submit_order = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, RPSData.app_key, pay_order,
                                                          pay_order_info["currency"], select_method["type"] + "A",
                                                          select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
                                                          payment_amount, **fees)
        self.checkCodeAndMessage(submit_order, "PAY_RPS_662", "payment method or currency not supported")
        self.assertIsNone(submit_order["data"])

    def test_070_selectPaymentMethod_channelIncorrect(self):
        """
        选择支付方式，支付通道和查询出的不一致
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 12.34,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": RPSData.user_roxe_account,
            "targetRoxeAccount": RPSData.user_roxe_account_a,
            "currency": "USD",
            "businessType": BusinessType.TRANSFER.value,
            "country": "US",
        }
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()*1000), pay_order_info)
        pay_methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order, RPSData.app_key)
        self.checkCodeAndMessage(pay_methods)

        select_method = [i for i in pay_methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method))
        fees = {
            "allowanceFee": select_method["currencyList"][0]["allowanceFee"],
            "showFee": select_method["currencyList"][0]["showFee"],
        }
        payment_amount = pay_order_info["businessAmount"] + select_method["currencyList"][0]["showFee"]
        submit_order = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, RPSData.app_key, pay_order,
                                                          pay_order_info["currency"], select_method["type"],
                                                          select_method["serviceChannel"] + "A", select_method["currencyList"][0]["fee"],
                                                          payment_amount, **fees)
        self.checkCodeAndMessage(submit_order, "PAY_RPS_689", "channel invalid")
        self.assertIsNone(submit_order["data"])

    def test_071_selectPaymentMethod_paymentAmountIncorrect(self):
        """
        选择支付方式，应付金额不正确
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 12.34,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": RPSData.user_roxe_account,
            "targetRoxeAccount": RPSData.user_roxe_account_a,
            "currency": "USD",
            "businessType": BusinessType.TRANSFER.value,
            "country": "US",
        }
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()*1000), pay_order_info)
        pay_methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order, RPSData.app_key)
        self.checkCodeAndMessage(pay_methods)

        select_method = [i for i in pay_methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method))
        fees = {
            "allowanceFee": select_method["currencyList"][0]["allowanceFee"],
            "showFee": select_method["currencyList"][0]["showFee"],
        }
        payment_amount = pay_order_info["businessAmount"] - 0.1
        submit_order = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, RPSData.app_key, pay_order,
                                                          pay_order_info["currency"], select_method["type"],
                                                          select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
                                                          payment_amount, **fees)
        self.checkCodeAndMessage(submit_order, "PAY_RPS_656", "invalid payableAmount")
        self.assertIsNone(submit_order["data"])
        payment_amount = 0
        submit_order = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, RPSData.app_key, pay_order,
                                                          pay_order_info["currency"], select_method["type"],
                                                          select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
                                                          payment_amount, **fees)
        self.checkCodeAndMessage(submit_order, "PAY_RPS_654", "payableAmount invalid")
        self.assertIsNone(submit_order["data"])
        payment_amount = -1
        submit_order = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, RPSData.app_key, pay_order,
                                                          pay_order_info["currency"], select_method["type"],
                                                          select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
                                                          payment_amount, **fees)
        self.checkCodeAndMessage(submit_order, "PAY_RPS_654", "payableAmount invalid")
        self.assertIsNone(submit_order["data"])
        payment_amount = pay_order_info["businessAmount"] + select_method["currencyList"][0]["showFee"] + 1
        submit_order = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, RPSData.app_key, pay_order,
                                                          pay_order_info["currency"], select_method["type"],
                                                          select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
                                                          payment_amount, **fees)
        self.checkCodeAndMessage(submit_order, "PAY_RPS_656", "invalid payableAmount")
        self.assertIsNone(submit_order["data"])

    def test_072_selectPaymentMethod_paymentFeeIncorrect(self):
        """
        选择支付方式，支付通道的费用不正确
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 12.34,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": RPSData.user_roxe_account,
            "targetRoxeAccount": RPSData.user_roxe_account_a,
            "currency": "USD",
            "businessType": BusinessType.TRANSFER.value,
            "country": "US",
        }
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()*1000), pay_order_info)
        pay_methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order, RPSData.app_key)
        self.checkCodeAndMessage(pay_methods)

        select_method = [i for i in pay_methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method))
        fees = {
            "allowanceFee": select_method["currencyList"][0]["allowanceFee"],
            "showFee": select_method["currencyList"][0]["showFee"],
        }
        payment_amount = pay_order_info["businessAmount"] + select_method["currencyList"][0]["showFee"]
        submit_order = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, RPSData.app_key, pay_order,
                                                          pay_order_info["currency"], select_method["type"],
                                                          select_method["serviceChannel"], select_method["currencyList"][0]["fee"] + 1,
                                                          payment_amount, **fees)
        self.checkCodeAndMessage(submit_order, "PAY_RPS_658", "service fee verify failed")
        self.assertIsNone(submit_order["data"])
        submit_order = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, RPSData.app_key, pay_order,
                                                          pay_order_info["currency"], select_method["type"],
                                                          select_method["serviceChannel"], -1,
                                                          payment_amount, **fees)
        self.checkCodeAndMessage(submit_order, "PAY_RPS_658", "service fee verify failed")
        self.assertIsNone(submit_order["data"])
        payment_amount = pay_order_info["businessAmount"] + select_method["currencyList"][0]["showFee"] + 1
        submit_order = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, RPSData.app_key, pay_order,
                                                          pay_order_info["currency"], select_method["type"],
                                                          select_method["serviceChannel"], select_method["currencyList"][0]["fee"] - 0.01,
                                                          payment_amount, **fees)
        self.checkCodeAndMessage(submit_order, "PAY_RPS_658", "service fee verify failed")
        self.assertIsNone(submit_order["data"])

    def test_073_selectPaymentMethod_orderHasPay(self):
        """
        选择支付方式，支付订单已经支付
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 12.34,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": RPSData.user_roxe_account,
            "targetRoxeAccount": RPSData.user_roxe_account_a,
            "currency": "USD",
            "businessType": BusinessType.TRANSFER.value,
            "country": "US",
        }
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()*1000), pay_order_info)
        pay_methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order, RPSData.app_key)
        self.checkCodeAndMessage(pay_methods)

        select_method = [i for i in pay_methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method))
        fees = {
            "allowanceFee": select_method["currencyList"][0]["allowanceFee"],
            "showFee": select_method["currencyList"][0]["showFee"],
        }
        payment_amount = pay_order_info["businessAmount"] + select_method["currencyList"][0]["showFee"]
        submit_order = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, RPSData.app_key, pay_order,
                                                          pay_order_info["currency"], select_method["type"],
                                                          select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
                                                          payment_amount, **fees)
        self.checkCodeAndMessage(submit_order)
        submit_order = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, RPSData.app_key, pay_order,
                                                          pay_order_info["currency"], select_method["type"],
                                                          select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
                                                          payment_amount, **fees)
        self.checkCodeAndMessage(submit_order, "PAY_RPS_705", "order status error")

    def test_074_selectPaymentMethod_payOrderIsNone(self):
        """
        选择支付方式，支付订单id为None
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 12.34,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": RPSData.user_roxe_account,
            "targetRoxeAccount": RPSData.user_roxe_account_a,
            "currency": "USD",
            "businessType": BusinessType.TRANSFER.value,
            "country": "US",
        }
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()*1000), pay_order_info)
        pay_methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order, RPSData.app_key)
        self.checkCodeAndMessage(pay_methods)

        select_method = [i for i in pay_methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method))
        fees = {
            "allowanceFee": select_method["currencyList"][0]["allowanceFee"],
            "showFee": select_method["currencyList"][0]["showFee"],
        }
        payment_amount = pay_order_info["businessAmount"] + select_method["currencyList"][0]["showFee"]
        submit_order = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, RPSData.app_key, None,
                                                          pay_order_info["currency"], select_method["type"],
                                                          select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
                                                          payment_amount, **fees)
        self.checkCodeAndMessage(submit_order, "PAY_RPS_704", "orderId cannot be null")

    def test_075_selectPaymentMethod_lostParameter(self):
        """
        选择支付方式，缺少某一项参数: 支付订单、currency、payMethod、serviceChannel、channelFee、payableAmount
        """
        # 下支付订单
        pay_order_info = {
            "businessAmount": 12.34,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": RPSData.user_roxe_account,
            "targetRoxeAccount": RPSData.user_roxe_account_a,
            "currency": "USD",
            "businessType": BusinessType.TRANSFER.value,
            "country": "US",
        }
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()*1000), pay_order_info)
        pay_methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order, RPSData.app_key)
        self.checkCodeAndMessage(pay_methods)

        select_method = [i for i in pay_methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method))
        fees = {
            "allowanceFee": select_method["currencyList"][0]["allowanceFee"],
            "showFee": select_method["currencyList"][0]["showFee"],
        }
        payment_amount = pay_order_info["businessAmount"] + select_method["currencyList"][0]["showFee"]
        lost_parameter_info = {
            "id": {"code": "PAY_RPS_704", "msg": "orderId cannot be null"},
            "currency": {"code": "PAY_RPS_655", "msg": "currency cannot be empty"},
            "payMethod": {"code": "PAY_RPS_650", "msg": "payMethod cannot be empty"},
            "serviceChannel": {"code": "PAY_RPS_698", "msg": "serviceChannel cannot be empty"},
            "channelFee": {"code": "PAY_RPS_658", "msg": "service fee verify failed"},
            "payableAmount": {"code": "PAY_RPS_654", "msg": "payableAmount invalid"},
        }
        for l_k, l_v in lost_parameter_info.items():
            submit_order = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, RPSData.app_key, pay_order,
                                                              pay_order_info["currency"], select_method["type"],
                                                              select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
                                                              payment_amount, lostKey=l_k, **fees)
            self.checkCodeAndMessage(submit_order, l_v["code"], l_v["msg"])

    def test_076_selectPaymentMethod_AchAccount_accountUsingFailed(self):
        """
        绑定ach账户，绑定的账户支付时失败, 选择ach账户支付
        """
        account_info = RPSData.ach_account.copy()
        account_info["accountNumber"] = RPSData.account_using_failed
        self.client.bindAndVerifyAchAccount(account_info)
        # 下支付订单
        amount = 12.34
        currency = RPSData.ach_account["currency"].upper()
        # 查询钱包余额
        targetAccountBalance = self.client.getRoAccountBalance(RPSData.user_roxe_account, currency)
        self.client.logger.info(f"目标账户资产: {targetAccountBalance}")

        pay_order, coupon_code = self.client.submitAchPayOrder(RPSData.user_roxe_account, amount, currency, expect_pay_success=False)
        time_out = 60
        flag = False
        if RPSData.is_check_db:
            sql = "select * from `roxe_pay_in_out`.roxe_pay_in_order where id='{}'".format(pay_order["id"])
            b_time = time.time()
            while time.time() - b_time < time_out:
                db_res = self.mysql.exec_sql_query(sql)
                self.client.logger.info(f"查询的数据库结果: {db_res[0]}")
                if db_res[0]["payFailedReason"]:
                    flag = True
                    reason = "The customer\'s bank account could not be located."
                    self.assertIn(reason, db_res[0]["payFailedReason"], "支付失败原因不正确")
                    break
                time.sleep(20)
        # 查询钱包余额
        targetAccountBalance2 = self.client.getRoAccountBalance(RPSData.user_roxe_account, currency)
        self.client.logger.info(f"目标账户资产: {targetAccountBalance2}")
        self.assertEqual(targetAccountBalance, targetAccountBalance2)
        query_order = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order["businessOrderNo"])
        self.assertEqual(query_order["status"], PayOrder.PAY_FAIL.value, "支付失败的订单status应为3")
        if not flag:
            self.assertTrue(False, f"超过{time_out}秒未找到支付失败的原因")

    def test_077_selectPaymentMethod_AchAccount_accountHasBeenCanceled(self):
        """
        绑定ach账户，绑定的账户支付时被注销, 选择ach账户支付
        """
        account_info = RPSData.ach_account.copy()
        account_info["accountNumber"] = RPSData.account_canceled
        self.client.bindAndVerifyAchAccount(account_info)
        # 下支付订单
        amount = 12.34
        currency = RPSData.ach_account["currency"].upper()
        # 查询钱包余额
        targetAccountBalance = self.client.getRoAccountBalance(RPSData.user_roxe_account, currency)
        self.client.logger.info(f"目标账户资产: {targetAccountBalance}")

        pay_order, coupon_code = self.client.submitAchPayOrder(RPSData.user_roxe_account, amount, currency, expect_pay_success=False)
        time_out = 60
        flag = False
        if RPSData.is_check_db:
            sql = "select * from `roxe_pay_in_out`.roxe_pay_in_order where id='{}'".format(pay_order["id"])
            b_time = time.time()
            while time.time() - b_time < time_out:
                db_res = self.mysql.exec_sql_query(sql)
                self.client.logger.info(f"查询的数据库结果: {db_res[0]}")
                if db_res[0]["payFailedReason"]:
                    flag = True
                    reason = "The customer's bank account has been closed."
                    self.assertIn(reason, db_res[0]["payFailedReason"], "支付失败原因不正确")
                    break
                time.sleep(20)
        # 查询钱包余额
        targetAccountBalance2 = self.client.getRoAccountBalance(RPSData.user_roxe_account, currency)
        self.client.logger.info(f"目标账户资产: {targetAccountBalance2}")
        self.assertEqual(targetAccountBalance, targetAccountBalance2)
        query_order = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order["businessOrderNo"])
        self.assertEqual(query_order["status"], PayOrder.PAY_FAIL.value, "支付失败的订单status应为1")
        if not flag:
            self.assertTrue(False, f"超过{time_out}秒未找到支付失败的原因")

    def test_078_selectPaymentMethod_AchAccount_accountInsufficientBalance(self):
        """
        绑定ach账户，绑定的账户支付时资产不足, 选择ach账户支付
        """
        account_info = RPSData.ach_account.copy()
        account_info["accountNumber"] = RPSData.account_insufficient_balance
        self.client.bindAndVerifyAchAccount(account_info)
        # 下支付订单
        amount = 12.34
        currency = RPSData.ach_account["currency"].upper()
        # 查询钱包余额
        targetAccountBalance = self.client.getRoAccountBalance(RPSData.user_roxe_account, currency)
        self.client.logger.info(f"目标账户资产: {targetAccountBalance}")

        pay_order, coupon_code = self.client.submitAchPayOrder(RPSData.user_roxe_account, amount, currency, expect_pay_success=False)
        time_out = 60
        flag = False
        if RPSData.is_check_db:
            sql = "select * from `roxe_pay_in_out`.roxe_pay_in_order where id='{}'".format(pay_order["id"])
            b_time = time.time()
            while time.time() - b_time < time_out:
                db_res = self.mysql.exec_sql_query(sql)
                self.client.logger.info(f"查询的数据库结果: {db_res[0]}")
                if db_res[0]["payFailedReason"]:
                    flag = True
                    reason = "The customer's account has insufficient funds to cover this payment."
                    self.assertIn(reason, db_res[0]["payFailedReason"], "支付失败原因不正确")
                    break
                time.sleep(20)
        # 查询钱包余额
        targetAccountBalance2 = self.client.getRoAccountBalance(RPSData.user_roxe_account, currency)
        self.client.logger.info(f"目标账户资产: {targetAccountBalance2}")
        self.assertEqual(targetAccountBalance, targetAccountBalance2)
        query_order = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order["businessOrderNo"])
        self.assertEqual(query_order["status"], PayOrder.PAY_FAIL.value, "支付失败的订单status应为3")
        if not flag:
            self.assertTrue(False, f"超过{time_out}秒未找到支付失败的原因")

    def test_079_selectPaymentMethod_AchAccount_accountUnauthorizedWithdrawal(self):
        """
        绑定ach账户，绑定账户后支付时未经授权撤回, 选择ach账户支付
        """
        account_info = RPSData.ach_account.copy()
        account_info["accountNumber"] = RPSData.account_unauthorized_withdrawal
        self.client.bindAndVerifyAchAccount(account_info)
        # 下支付订单
        amount = 12.34
        currency = RPSData.ach_account["currency"].upper()
        # 查询钱包余额
        targetAccountBalance = self.client.getRoAccountBalance(RPSData.user_roxe_account, currency)
        self.client.logger.info(f"目标账户资产: {targetAccountBalance}")

        pay_order, coupon_code = self.client.submitAchPayOrder(RPSData.user_roxe_account, amount, currency, expect_pay_success=False)
        time_out = 60
        flag = False
        if RPSData.is_check_db:
            sql = "select * from `roxe_pay_in_out`.roxe_pay_in_order where id='{}'".format(pay_order["id"])
            b_time = time.time()
            while time.time() - b_time < time_out:
                db_res = self.mysql.exec_sql_query(sql)
                self.client.logger.info(f"查询的数据库结果: {db_res[0]}")
                if db_res[0]["payFailedReason"]:
                    flag = True
                    reason = "The customer has notified their bank that this payment was unauthorized."
                    self.assertIn(reason, db_res[0]["payFailedReason"], "支付失败原因不正确")
                    break
                time.sleep(20)
        # 查询钱包余额
        targetAccountBalance2 = self.client.getRoAccountBalance(RPSData.user_roxe_account, currency)
        self.client.logger.info(f"目标账户资产: {targetAccountBalance2}")
        self.assertEqual(targetAccountBalance, targetAccountBalance2)
        query_order = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order["businessOrderNo"])
        self.assertEqual(query_order["status"], PayOrder.PAY_FAIL.value, "支付失败的订单status应为3")
        if not flag:
            self.assertTrue(False, f"超过{time_out}秒未找到支付失败的原因")

    def test_080_selectPaymentMethod_AchAccount_accountNotSupportCurrentCurrency(self):
        """
        绑定ach账户，绑定的账户不支持当前币种, 选择ach账户支付
        """
        account_info = RPSData.ach_account.copy()
        account_info["accountNumber"] = RPSData.account_invalid_currency
        self.client.bindAndVerifyAchAccount(account_info)
        # 下支付订单
        amount = 12.34
        currency = RPSData.ach_account["currency"].upper()
        # 查询钱包余额
        targetAccountBalance = self.client.getRoAccountBalance(RPSData.user_roxe_account, currency)
        self.client.logger.info(f"目标账户资产: {targetAccountBalance}")

        pay_order, coupon_code = self.client.submitAchPayOrder(RPSData.user_roxe_account, amount, currency, expect_pay_success=False)
        time_out = 60
        flag = False
        if RPSData.is_check_db:
            sql = "select * from `roxe_pay_in_out`.roxe_pay_in_order where id='{}'".format(pay_order["id"])
            b_time = time.time()
            while time.time() - b_time < time_out:
                db_res = self.mysql.exec_sql_query(sql)
                self.client.logger.info(f"查询的数据库结果: {db_res[0]}")
                if db_res[0]["payFailedReason"]:
                    flag = True
                    reason = "The bank was unable to process this payment because of its currency. "
                    self.assertIn(reason, db_res[0]["payFailedReason"], "支付失败原因不正确")
                    break
                time.sleep(20)
        # 查询钱包余额
        targetAccountBalance2 = self.client.getRoAccountBalance(RPSData.user_roxe_account, currency)
        self.client.logger.info(f"目标账户资产: {targetAccountBalance2}")
        self.assertEqual(targetAccountBalance, targetAccountBalance2)
        query_order = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order["businessOrderNo"])
        self.assertEqual(query_order["status"], PayOrder.PAY_FAIL.value, "支付失败的订单status应为3")
        if not flag:
            self.assertTrue(False, f"超过{time_out}秒未找到支付失败的原因")

    def test_081_selectPaymentMethod_Wallet_accountBalanceLessThanTransferAmount(self):
        """
        支付方式选择钱包余额，账户资产 < 转账金额
        """
        source_account = RPSData.user_roxe_account
        target_account = RPSData.user_roxe_account_a
        s_balance = self.client.getRoAccountBalance(source_account, "USD")
        self.client.logger.info(f"{source_account}持有资产: {s_balance}")
        pay_order_info = {
            "businessAmount": ApiUtils.parseNumberDecimal(s_balance) + 10,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": source_account,
            "targetRoxeAccount": target_account,
            "currency": "USD",
            "businessType": BusinessType.TRANSFER.value,
            "country": "US",
        }
        # 支付下单
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        # 查询支付方式
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)

        # 选择支付方式进行支付
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method))
        fees = {
            "allowanceFee": select_method["currencyList"][0]["allowanceFee"],
            "showFee": select_method["currencyList"][0]["showFee"],
        }
        payment_amount = pay_order_info["businessAmount"] + select_method["currencyList"][0]["showFee"]
        if abs(ApiUtils.parseNumberDecimal(payment_amount) - payment_amount) < 0.1 ** 7:
            payment_amount = ApiUtils.parseNumberDecimal(payment_amount)
        submit_order = self.client.submitOrderPayInMethod(
            RPSData.user_id, RPSData.user_login_token, RPSData.app_key, pay_order, pay_order_info["currency"],
            select_method["type"], select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
            payment_amount, **fees
        )
        self.checkCodeAndMessage(submit_order, "PAYIN_WALLET_609", "wallet balance not enough")

    @unittest.skip("链上转账费用为0, 跳过")
    def test_082_selectPaymentMethod_Wallet_accountBalanceLessThanTransferAmountAddTransferFee(self):
        """
        支付方式选择钱包余额，转账的金额 < 账户的资产 < 转账的金额 + 链上转账费用
        """
        source_account = RPSData.user_roxe_account_a
        target_account = RPSData.user_roxe_account
        s_balance = self.client.getRoAccountBalance(source_account, "USD")
        self.client.logger.info(f"{source_account}持有资产: {s_balance}")
        pay_order_info = {
            "businessAmount": ApiUtils.parseNumberDecimal(s_balance - 0.05),
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": source_account,
            "targetRoxeAccount": target_account,
            "currency": "USD",
            "businessType": BusinessType.TRANSFER.value,
            "country": "US",
        }
        # 支付下单
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        # 查询支付方式
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)

        # 选择支付方式进行支付
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method))
        fees = {
            "allowanceFee": select_method["currencyList"][0]["allowanceFee"],
            "showFee": select_method["currencyList"][0]["showFee"],
        }
        payment_amount = pay_order_info["businessAmount"] + select_method["currencyList"][0]["showFee"] + 1
        if abs(ApiUtils.parseNumberDecimal(payment_amount) - payment_amount) < 0.1 ** 7:
            payment_amount = ApiUtils.parseNumberDecimal(payment_amount)
        submit_order = self.client.submitOrderPayInMethod(
            RPSData.user_id, RPSData.user_login_token, RPSData.app_key, pay_order, pay_order_info["currency"],
            select_method["type"], select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
            payment_amount, **fees
        )
        self.checkCodeAndMessage(submit_order, "PAYIN_WALLET_609", "wallet balance not enough")

    def test_083_selectPaymentMethod_Wallet_sourceAccountSameWithTargetAccount(self):
        """
        支付方式选择钱包余额，转账的源账户和目标账户一致
        """
        source_account = RPSData.user_roxe_account_a
        s_balance = self.client.getRoAccountBalance(source_account, "USD")
        self.client.logger.info(f"{source_account}持有资产: {s_balance}")
        pay_order_info = {
            "businessAmount": 12.11,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": source_account,
            "targetRoxeAccount": source_account,
            "currency": "USD",
            "businessType": BusinessType.TRANSFER.value,
            "country": "US",
        }
        # 支付下单
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        # 查询支付方式
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)

        # 选择支付方式进行支付
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method))
        fees = {
            "allowanceFee": select_method["currencyList"][0]["allowanceFee"],
            "showFee": select_method["currencyList"][0]["showFee"],
        }
        payment_amount = pay_order_info["businessAmount"] + select_method["currencyList"][0]["showFee"]
        if ApiUtils.parseNumberDecimal(payment_amount) < payment_amount:
            payment_amount = ApiUtils.parseNumberDecimal(payment_amount, isUp=True)
        submit_order = self.client.submitOrderPayInMethod(
            RPSData.user_id, RPSData.user_login_token, RPSData.app_key, pay_order, pay_order_info["currency"],
            select_method["type"], select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
            payment_amount, **fees
        )
        self.checkCodeAndMessage(submit_order, "PAYIN_WALLET_601", "service error :error code: 1009, error name: not_permit, detail: to self")

    def test_084_selectPaymentMethod_Wallet_secondTransFailed_accountBalanceNotEnough(self):
        """
        支付方式选择钱包余额，发起2笔转账请求，在进行第1笔转账后，第2笔转账时账户资产不足，第2笔订单失败
        """
        source_account = RPSData.user_roxe_account_a
        target_account = RPSData.user_roxe_account
        s_balance = self.client.getRoAccountBalance(source_account, "USD")
        self.client.logger.info(f"{source_account}持有资产: {s_balance}")
        # 第1笔订单
        pay_order_info = {
            "businessAmount": 15,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time() * 1000)),
            "businessItemName": "test",
            "sourceRoxeAccount": source_account,
            "targetRoxeAccount": target_account,
            "currency": "USD",
            "businessType": BusinessType.TRANSFER.value,
            "country": "US",
        }
        # 支付下单
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        # 查询支付方式
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)

        # 选择支付方式进行支付
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method))
        payment_amount = pay_order_info["businessAmount"] + select_method["currencyList"][0]["fee"]
        if ApiUtils.parseNumberDecimal(payment_amount) < payment_amount:
            payment_amount = ApiUtils.parseNumberDecimal(payment_amount, isUp=True)

        # 第2笔订单
        pay_order_info_2 = pay_order_info.copy()
        pay_order_info_2["businessAmount"] = ApiUtils.parseNumberDecimal(s_balance - 1)
        pay_order_info_2["businessOrderNo"] = "test" + str(int(time.time() * 1000))
        # 支付下单
        pay_order_2 = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info_2)
        # 查询支付方式
        methods_2 = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order_2)

        # 选择支付方式进行支付
        select_method_2 = [i for i in methods_2["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method_2))
        fees = {
            "allowanceFee": select_method["currencyList"][0]["allowanceFee"],
            "showFee": select_method["currencyList"][0]["showFee"],
        }
        payment_amount_2 = pay_order_info_2["businessAmount"] + select_method_2["currencyList"][0]["showFee"]
        if ApiUtils.parseNumberDecimal(payment_amount_2) < payment_amount_2:
            payment_amount_2 = ApiUtils.parseNumberDecimal(payment_amount_2, isUp=True)
        elif ApiUtils.parseNumberDecimal(payment_amount_2) > payment_amount_2:
            payment_amount_2 = ApiUtils.parseNumberDecimal(payment_amount_2 - 0.01)
        else:
            payment_amount_2 = ApiUtils.parseNumberDecimal(payment_amount_2)

        self.client.logger.info(f"第1笔应付金额: {payment_amount}")
        submit_order = self.client.submitOrderPayInMethod(
            RPSData.user_id, RPSData.user_login_token, RPSData.app_key, pay_order, pay_order_info["currency"],
            select_method["type"], select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
            payment_amount, **fees
        )
        self.checkCodeAndMessage(submit_order)

        self.client.logger.info(f"第2笔应付金额: {payment_amount_2}")
        submit_order_2 = self.client.submitOrderPayInMethod(
            RPSData.user_id, RPSData.user_login_token, RPSData.app_key, pay_order_2, pay_order_info_2["currency"],
            select_method["type"], select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
            payment_amount_2, **fees
        )
        self.checkCodeAndMessage(submit_order_2, "PAYIN_WALLET_609", "wallet balance not enough")
        # 查询订单状态
        b_time = time.time()
        query_order = None
        while time.time() - b_time < 60:
            query_order = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info["businessOrderNo"])
            if query_order["serviceChannelOrderId"] != "":
                break
            time.sleep(10)
        query_order_2 = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info_2["businessOrderNo"])
        self.assertEqual(query_order_2["status"], 0, "支付单状态应为入库状态")
        self.assertEqual(query_order["status"], PayOrder.PAY_SUCCESS.value, "支付单状态应为完成")

    def test_085_selectPaymentMethod_Wallet_secondTransFailed_accountBalanceEnough(self):
        """
        支付方式选择钱包余额，发起2笔转账请求，在进行第1笔转账后，第2笔转账时账户资产不足，第2笔订单失败
        """
        source_account = RPSData.user_roxe_account_a
        target_account = RPSData.user_roxe_account
        s_balance = self.client.getRoAccountBalance(source_account, "USD")
        self.client.logger.info(f"{source_account}持有资产: {s_balance}")
        t_balance = self.client.getRoAccountBalance(target_account, "USD")
        self.client.logger.info(f"{target_account}持有资产: {t_balance}")
        # 第1笔订单
        pay_order_info = {
            "businessAmount": 15.2,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time() * 1000)),
            "businessItemName": "test",
            "sourceRoxeAccount": source_account,
            "targetRoxeAccount": target_account,
            "currency": "USD",
            "businessType": BusinessType.TRANSFER.value,
            "country": "US",
        }
        # 支付下单
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        # 查询支付方式
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)

        # 选择支付方式进行支付
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method))
        payment_amount = pay_order_info["businessAmount"] + select_method["currencyList"][0]["fee"]
        if ApiUtils.parseNumberDecimal(payment_amount) < payment_amount:
            payment_amount = ApiUtils.parseNumberDecimal(payment_amount, isUp=True)

        # 第2笔订单
        pay_order_info_2 = pay_order_info.copy()
        pay_order_info_2["businessAmount"] = 10.35
        pay_order_info_2["businessOrderNo"] = "test" + str(int(time.time() * 1000))
        # 支付下单
        pay_order_2 = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info_2)
        # 查询支付方式
        methods_2 = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order_2)

        # 选择支付方式进行支付
        select_method_2 = [i for i in methods_2["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method_2))
        fees = {
            "allowanceFee": select_method["currencyList"][0]["allowanceFee"],
            "showFee": select_method["currencyList"][0]["showFee"],
        }
        payment_amount_2 = pay_order_info_2["businessAmount"] + select_method_2["currencyList"][0]["showFee"]
        if ApiUtils.parseNumberDecimal(payment_amount_2) < payment_amount_2:
            payment_amount_2 = ApiUtils.parseNumberDecimal(payment_amount_2, isUp=True)
        elif ApiUtils.parseNumberDecimal(payment_amount_2) > payment_amount_2:
            payment_amount_2 = ApiUtils.parseNumberDecimal(payment_amount_2 - 0.01)
        else:
            payment_amount_2 = ApiUtils.parseNumberDecimal(payment_amount_2)

        self.client.logger.info(f"第1笔应付金额: {payment_amount}")
        submit_order = self.client.submitOrderPayInMethod(
            RPSData.user_id, RPSData.user_login_token, RPSData.app_key, pay_order, pay_order_info["currency"],
            select_method["type"], select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
            payment_amount, **fees
        )
        self.checkCodeAndMessage(submit_order)

        self.client.logger.info(f"第2笔应付金额: {payment_amount_2}")
        submit_order_2 = self.client.submitOrderPayInMethod(
            RPSData.user_id, RPSData.user_login_token, RPSData.app_key, pay_order_2, pay_order_info_2["currency"],
            select_method["type"], select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
            payment_amount_2, **fees
        )
        self.checkCodeAndMessage(submit_order_2)
        # 查询订单状态
        b_time = time.time()
        query_order, query_order_2 = None, None
        while time.time() - b_time < 60:
            query_order = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info["businessOrderNo"])
            query_order_2 = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info_2["businessOrderNo"])
            if query_order["serviceChannelOrderId"] != "" and query_order_2["serviceChannelOrderId"] != "":
                break
            time.sleep(10)
        self.assertEqual(query_order["status"], PayOrder.PAY_SUCCESS.value, "支付单状态应为完成")
        self.assertEqual(query_order_2["status"], PayOrder.PAY_SUCCESS.value, "支付单状态应为完成")
        s_balance2 = self.client.getRoAccountBalance(source_account, "USD")
        self.client.logger.info(f"{source_account}持有资产: {s_balance2}, 变化了: {s_balance2 - s_balance}")
        t_balance2 = self.client.getRoAccountBalance(target_account, "USD")
        self.client.logger.info(f"{target_account}持有资产: {t_balance2}, 变化了: {t_balance2 - t_balance}")
        self.assertAlmostEqual(s_balance - s_balance2, pay_order_info["businessAmount"] + pay_order_info_2["businessAmount"], delta=0.001)
        self.assertAlmostEqual(t_balance2 - t_balance, pay_order_info["businessAmount"] + pay_order_info_2["businessAmount"], delta=0.001)

    def test_086_selectPaymentMethod_Wallet_sourceAccountIncorrect(self):
        """
        支付方式选择钱包余额，转账的源账户不正确
        """
        source_account = "asdxxx"
        target_account = RPSData.user_roxe_account
        s_balance = self.client.getRoAccountBalance(source_account, "USD")
        self.client.logger.info(f"{source_account}持有资产: {s_balance}")
        pay_order_info = {
            "businessAmount": 12.11,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": source_account,
            "targetRoxeAccount": target_account,
            "currency": "USD",
            "businessType": BusinessType.TRANSFER.value,
            "country": "US",
        }
        # 支付下单
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        # 查询支付方式
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)

        # 选择支付方式进行支付
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method))
        fees = {
            "allowanceFee": select_method["currencyList"][0]["allowanceFee"],
            "showFee": select_method["currencyList"][0]["showFee"],
        }
        payment_amount = pay_order_info["businessAmount"] + select_method["currencyList"][0]["showFee"]
        if ApiUtils.parseNumberDecimal(payment_amount) < payment_amount:
            payment_amount = ApiUtils.parseNumberDecimal(payment_amount, isUp=True)
        submit_order = self.client.submitOrderPayInMethod(
            RPSData.user_id, RPSData.user_login_token, RPSData.app_key, pay_order, pay_order_info["currency"],
            select_method["type"], select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
            payment_amount, **fees
        )
        self.checkCodeAndMessage(submit_order, "PAYIN_WALLET_609", "wallet balance not enough")

    def test_087_selectPaymentMethod_Wallet_targetAccountIncorrect(self):
        """
        支付方式选择钱包余额，转账的目标账户不正确
        """
        source_account = RPSData.user_roxe_account
        target_account = "asdxxx"
        s_balance = self.client.getRoAccountBalance(source_account, "USD")
        self.client.logger.info(f"{source_account}持有资产: {s_balance}")
        pay_order_info = {
            "businessAmount": 12.11,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": source_account,
            "targetRoxeAccount": target_account,
            "currency": "USD",
            "businessType": BusinessType.TRANSFER.value,
            "country": "US",
        }
        # 支付下单
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        # 查询支付方式
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)

        # 选择支付方式进行支付
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("选择的支付方式: {}".format(select_method))

        fees = {
            "allowanceFee": select_method["currencyList"][0]["allowanceFee"],
            "showFee": select_method["currencyList"][0]["showFee"],
        }
        payment_amount = pay_order_info["businessAmount"] + select_method["currencyList"][0]["showFee"]
        if ApiUtils.parseNumberDecimal(payment_amount) < payment_amount:
            payment_amount = ApiUtils.parseNumberDecimal(payment_amount, isUp=True)
        submit_order = self.client.submitOrderPayInMethod(
            RPSData.user_id, RPSData.user_login_token, RPSData.app_key, pay_order, pay_order_info["currency"],
            select_method["type"], select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
            payment_amount, **fees
        )
        self.checkCodeAndMessage(submit_order, "PAYIN_WALLET_608", f"wallet payin targetRoxeAccount not activated:{target_account}")

    # 增加优惠券的相关用例

    @unittest.skip("暂无优惠券部分折扣场景")
    def test_088_placePaymentOrder_deposit_ach_outsideDeduction_partOfAllowance(self):
        """
         充值业务，法币->ro, 支付方式选择ach, 优惠券的折扣为部分折扣
        """
        self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        # 下支付订单
        pay_order_info = {
            "businessAmount": 12.34,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": "xxxx",
            "targetRoxeAccount": RPSData.user_roxe_account,
            "currency": "USD",
            "businessType": BusinessType.CHARGE.value,
            "country": "US",
        }
        # 查询钱包余额
        targetAccountBalance = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"目标账户资产: {targetAccountBalance}")

        sql = f"select * from roxe_pay_in_allowance where pay_method='{PaymentMethods.ACH.value}'"
        db_allowance = self.mysql.exec_sql_query(sql)
        allowance_rate = db_allowance[0]["rate"]
        flag = True
        try:
            u_sql = f"update roxe_pay_in_allowance set rate=0.33 where pay_method='{PaymentMethods.ACH.value}'"
            self.mysql.exec_sql_query(u_sql)

            pay_order, coupon_code = self.client.submitAchPayOrder(RPSData.user_roxe_account, pay_order_info["businessAmount"], pay_order_info["currency"], caseObj=self)
            self.assertEqual(pay_order["status"], PayOrder.PAY_SUCCESS.value)

            targetAccountBalance2 = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
            self.client.logger.info(f"目标账户资产: {targetAccountBalance2}, 变化了: {targetAccountBalance2 - targetAccountBalance}")

            self.assertAlmostEqual(targetAccountBalance2 - targetAccountBalance, 0, msg="需要回调业务系统，支付订单才能完成", delta=0.1**7)

            self.assertTrue(pay_order["channelFee"] > 0, "优惠券部分折扣时，channelFee不正确")
        except Exception as e:
            flag = False
            self.client.logger.error(e.args, exc_info=True)
        finally:
            u_sql = f"update roxe_pay_in_allowance set rate={allowance_rate} where pay_method='{PaymentMethods.ACH.value}'"
            self.mysql.exec_sql_query(u_sql)
            assert flag, "用例执行失败"

    def test_089_placePaymentOrder_deposit_ach_outsideDeduction_allowanceFeeExceedCouponMax(self):
        """
         充值业务，法币->ro, 支付方式选择ach, 当优惠的金额按rps的费率计算超过券本身的最大值时，按最大值来计算
        """
        self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        # 下支付订单
        pay_order_info = {
            "businessAmount": 1012.34,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": "xxxx",
            "targetRoxeAccount": RPSData.user_roxe_account,
            "currency": "USD",
            "businessType": BusinessType.CHARGE.value,
            "country": "US",
        }
        # 查询钱包余额
        targetAccountBalance = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"目标账户资产: {targetAccountBalance}")

        pay_order, coupon_code = self.client.submitAchPayOrder(RPSData.user_roxe_account, pay_order_info["businessAmount"], pay_order_info["currency"], caseObj=self)
        self.assertEqual(pay_order["status"], PayOrder.PAY_SUCCESS.value)

        targetAccountBalance2 = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"目标账户资产: {targetAccountBalance2}, 变化了: {targetAccountBalance2 - targetAccountBalance}")

        self.assertAlmostEqual(targetAccountBalance2 - targetAccountBalance, 0, msg="需要回调业务系统，支付订单才能完成", delta=0.1**7)

    def test_090_placePaymentOrder_deposit_ach_afterAllowanceEndDate(self):
        """
         充值业务，法币->ro, 支付方式选择ach, 修改优惠券的结束时间，使当前时间, 不在优惠券的时间范围内
        """
        self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        # 下支付订单
        pay_order_info = {
            "businessAmount": 12.34,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": "xxxx",
            "targetRoxeAccount": RPSData.user_roxe_account,
            "currency": "USD",
            "businessType": BusinessType.CHARGE.value,
            "country": "US",
        }
        # 查询钱包余额
        targetAccountBalance = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"目标账户资产: {targetAccountBalance}")

        sql = f"select * from roxe_pay_in_allowance where pay_method='{PaymentMethods.ACH.value}'"
        db_allowance = self.mysql.exec_sql_query(sql)
        start_date = db_allowance[0]["startDate"]
        end_date = db_allowance[0]["endDate"]
        flag = True
        try:
            cur_time = datetime.datetime.utcnow()
            if cur_time.timestamp() > start_date.timestamp():
                u_date = cur_time.strftime("%y-%m-%d %H:%M:%S")
            else:
                u_date = (start_date + datetime.timedelta(minutes=1)).strftime("%y-%m-%d %H:%M:%S")
            u_sql = f"update roxe_pay_in_allowance set end_date='{u_date}' where pay_method='{PaymentMethods.ACH.value}'"
            self.mysql.exec_sql_query(u_sql)

            time.sleep(10)

            pay_order, coupon_code = self.client.submitAchPayOrder(RPSData.user_roxe_account, pay_order_info["businessAmount"], pay_order_info["currency"], caseObj=self)
            self.assertEqual(pay_order["status"], PayOrder.PAY_SUCCESS.value)

            targetAccountBalance2 = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
            self.client.logger.info(f"目标账户资产: {targetAccountBalance2}, 变化了: {targetAccountBalance2 - targetAccountBalance}")

            self.assertAlmostEqual(targetAccountBalance2 - targetAccountBalance, 0, msg="需要回调业务系统，支付订单才能完成", delta=0.1**7)

            self.assertTrue(pay_order["channelFee"] > 0, "优惠券金额不正确")
        except Exception as e:
            flag = False
            self.client.logger.error(e.args, exc_info=True)
        finally:
            u_sql = f"update roxe_pay_in_allowance set end_date='{end_date}' where pay_method='{PaymentMethods.ACH.value}'"
            self.mysql.exec_sql_query(u_sql)
            assert flag, "用例执行失败"

    def test_091_placePaymentOrder_deposit_ach_beforeAllowanceStartDate(self):
        """
         充值业务，法币->ro, 支付方式选择ach, 修改优惠券的起始时间，使当前时间, 不在优惠券的时间范围内
        """
        self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        # 下支付订单
        pay_order_info = {
            "businessAmount": 12.34,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": "xxxx",
            "targetRoxeAccount": RPSData.user_roxe_account,
            "currency": "USD",
            "businessType": BusinessType.CHARGE.value,
            "country": "US",
        }
        # 查询钱包余额
        targetAccountBalance = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"目标账户资产: {targetAccountBalance}")

        sql = f"select * from roxe_pay_in_allowance where pay_method='{PaymentMethods.ACH.value}'"
        db_allowance = self.mysql.exec_sql_query(sql)
        start_date = db_allowance[0]["startDate"]
        end_date = db_allowance[0]["endDate"]
        flag = True
        try:
            cur_time = datetime.datetime.utcnow()
            u_date = (cur_time + datetime.timedelta(minutes=3)).strftime("%y-%m-%d %H:%M:%S")
            self.client.logger.info(f"更新的start_date时间戳为: {u_date}")
            u_sql = f"update roxe_pay_in_allowance set start_date='{u_date}' where pay_method='{PaymentMethods.ACH.value}'"
            self.mysql.exec_sql_query(u_sql)
            time.sleep(1)

            pay_order, coupon_code = self.client.submitAchPayOrder(RPSData.user_roxe_account, pay_order_info["businessAmount"], pay_order_info["currency"], caseObj=self)
            self.assertEqual(pay_order["status"], PayOrder.PAY_SUCCESS.value)

            targetAccountBalance2 = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
            self.client.logger.info(f"目标账户资产: {targetAccountBalance2}, 变化了: {targetAccountBalance2 - targetAccountBalance}")

            self.assertAlmostEqual(targetAccountBalance2 - targetAccountBalance, 0, msg="需要回调业务系统，支付订单才能完成", delta=0.1**7)
            self.assertTrue(pay_order["channelFee"] > 0, "优惠券金额不正确")
        except Exception as e:
            flag = False
            self.client.logger.error(e.args, exc_info=True)
        finally:
            u_sql = f"update roxe_pay_in_allowance set start_date='{start_date}' where pay_method='{PaymentMethods.ACH.value}'"
            self.mysql.exec_sql_query(u_sql)
            assert flag, "用例执行失败"
