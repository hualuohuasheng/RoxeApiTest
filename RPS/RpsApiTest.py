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
        user_not_login = "100142"  # ????????????????????????kyc
        user_not_kyc = "100147"  # ????????????kyc?????????
        user_not_kyc_login_token = "eyJhbGciOiJIUzI1NiJ9.eyJpdGMiOiI4NiIsImlzcyI6IlJPWEUiLCJhdWQiOiIxMDAxNDciLCJzdWIiOiJVU0VSX0xPR0lOIiwibmJmIjoxNjMxNTE3OTYxfQ.bbQjxl1B_yOxIgSTuOwg-_2pSp-7SKEhfyExY1dODUk"  # ????????????kyc?????????

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
            self.client.logger.info("setUp????????????")
            self.client.deleteAchAccountFromDB(self, RPSData.user_id)

    def tearDown(self) -> None:
        if RPSData.is_check_db:
            self.client.logger.info("teardown????????????")
            self.client.deleteAchAccountFromDB(self, RPSData.user_id)

    def checkCodeAndMessage(self, msg, expect_code='0', expect_message='Success'):
        """
        ?????????????????????code??????message
        :param msg: ????????????????????????json??????
        :param expect_code: ??????????????????code??????0
        :param expect_message: ??????????????????message???Success
        """
        self.assertEqual(msg["code"], expect_code, f"?????????code?????????: {msg}")
        self.assertEqual(msg["message"], expect_message, f"?????????code?????????: {msg}")

    def test_001_queryBindBankAccountWhenUserNotHaveBindAccount(self):
        """
        ?????????ach???????????????????????????????????????
        """
        sign = RPSData.sign
        accounts = self.client.queryBindBankAccount(sign, RPSData.app_key, RPSData.user_id, "USD")
        self.assertEqual(accounts, [], "????????????????????????????????????")

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
        self.client.logger.info("??????ach??????????????????")

    def checkAchAccountInfoFromDB(self, ach_account, user_id):
        if RPSData.is_check_db:
            sql = "select * from roxe_pay_in_user_bank_account where roxe_user_id='{}' and status<>0".format(user_id)
            db_account_info = self.mysql.exec_sql_query(sql)
            self.client.logger.debug("???????????????: {}".format(db_account_info))
            for key in ach_account.keys():
                if key in ["isPlaidUser", "createDate"]:
                    self.assertIsNotNone(ach_account[key])
                else:
                    self.assertEqual(ach_account[key], db_account_info[0][key], f"{key}??????????????????????????????")

    @unittest.skip("???ACH?????????????????????payment method???????????????????????????")
    def test_002_bindAchAccount(self):
        """
        ???????????????ach??????
        """
        account_info = RPSData.ach_account.copy()
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res)
        self.checkAchAccountInfo(bind_res["data"], account_info, RPSData.user_id)
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        self.assertEqual(len(accounts), 1, "?????????????????????????????????????????????")
        self.checkAchAccountInfoFromDB(accounts[0], RPSData.user_id)

    @unittest.skip("???ACH?????????????????????payment method???????????????????????????")
    def test_003_verifyAchAccount(self):
        """
        ????????????ach??????
        """
        self.test_002_bindAchAccount()
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, RPSData.ach_account["currency"].upper())
        account_id = accounts[0]["id"]
        verify_info = self.client.verifyBankAccount(RPSData.user_id, RPSData.user_login_token, account_id, 0.32, 0.45)
        self.checkCodeAndMessage(verify_info)
        self.assertEqual(verify_info["data"], True, "??????????????????")
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, "USD")
        self.assertEqual(len(accounts), 1, "?????????????????????????????????????????????")
        self.checkAchAccountInfoFromDB(accounts[0], RPSData.user_id)

    @unittest.skip("???ACH?????????????????????payment method???????????????????????????")
    def test_004_unbindAchAccount(self):
        """
        ??????ach?????????????????????????????????????????????????????????
        """
        self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, RPSData.ach_account["currency"].upper())
        account_id = accounts[0]["id"]
        unbind_info = self.client.unbindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_id)
        self.assertEqual(unbind_info, True, "??????????????????")
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, "USD")
        self.assertEqual(accounts, [], "????????????????????????????????????")

    def test_005_getPlaidLinkToken(self):
        """
        ??????plaid???link token
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
                self.client.logger.debug("????????????????????????: {}".format(m))
                self.client.logger.debug("???????????????: {}".format(db_method))
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
                    fee = 0  # ?????????????????????????????????0
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
                            self.assertEqual(m["channelBankAccount"][k], expect_data, f"{k}??????????????????: {db_method[0]}")
                    fee = self.client.calChannelFee(db_fee_config, m["amount"], m["serviceChannel"])
                    self.client.logger.info(f"{m['type']}??????????????????: {fee}")
                    fee = ApiUtils.parseNumberDecimal(fee, 2, True)
                    self.client.logger.info(f"{m['type']}??????????????????: {fee}")
                    allowance_fee = self.client.calAllowanceFee(self, fee, m["type"])
                    self.client.logger.info(f"{m['type']}???????????????????????????: {allowance_fee}")
                    self.assertAlmostEqual(allowance_fee, m["currencyList"][0]["allowanceFee"], delta=0.1**8)
                    show_fee = ApiUtils.parseNumberDecimal(fee - allowance_fee)
                    self.client.logger.info(f"{m['type']}????????????????????????: {show_fee}")
                    self.assertAlmostEqual(show_fee, m["currencyList"][0]["showFee"], delta=0.1**8)
                    self.assertAlmostEqual(m["currencyList"][0]["fee"], fee, delta=0.1**8, msg=f"{m['type']}???????????????:{db_fee_config}")
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
                self.client.logger.info(f"??????????????????{m['type']}?????????????????????")

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
                        self.assertEqual(value, db_order_info[0][key], "{}??????????????????".format(key))
                self.client.logger.info("???????????????????????????????????????")
            except Exception as e:
                self.client.logger.info("???????????????????????????: {}".format(pay_order))
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
        self.client.logger.info("?????????????????????????????????????????????")

    def waitUntilPayChannelOrderComplete(self, pay_order, order_type="in", time_out=120, time_inner=10):
        """
        ????????????????????????
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
            self.client.logger.info("?????????????????????????????????")
        else:
            self.client.logger.error(f"????????????????????????{time_out}?????????????????????")
            assert False, f"????????????????????????{time_out}?????????????????????"

    @unittest.skip("card??????????????????stripe?????????????????????")
    def test_006_placePaymentOrder_deposit_card(self):
        """
        ?????????????????????->ro, ??????????????????card
        """
        # ???????????????
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
        self.assertIsNotNone(pay_order, "??????????????????????????????")
        self.checkPayOrderInDB(pay_order, pay_order_info)
        # ??????????????????
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)
        self.checkCodeAndMessage(methods)
        self.assertEqual(len(methods["data"]), len(RPSData.payment_methods["deposit"]), "?????????data?????????")
        self.checkPaymentMethod(methods["data"], pay_order_info["businessAmount"], RPSData.user_id)

        # ??????????????????????????????
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.CARD.value][0]
        self.client.logger.info("?????????????????????: {}".format(select_method))
        order_info = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, RPSData.app_key, pay_order, pay_order_info["currency"], select_method["type"], select_method["serviceChannel"], select_method["currencyList"][0]["fee"], pay_order_info["businessAmount"] + select_method["currencyList"][0]["fee"])
        self.checkCodeAndMessage(order_info)
        self.assertEqual(order_info["data"]["id"], pay_order)
        self.assertIsNotNone(order_info["data"]["serviceChannelPayNo"])

        # ???????????????????????????????????????

    def test_007_placePaymentOrder_deposit_ach_outsideDeduction(self):
        """
         ?????????????????????->ro, ??????????????????ach
        """
        self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        # ???????????????
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
        # ??????????????????
        targetAccountBalance = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"??????????????????: {targetAccountBalance}")
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.assertIsNotNone(pay_order, "??????????????????????????????")
        self.checkPayOrderInDB(pay_order, pay_order_info)
        # ??????????????????
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)
        self.checkCodeAndMessage(methods)
        # self.assertEqual(len(methods["data"]), 2, "?????????data?????????")
        self.checkPaymentMethod(methods["data"], pay_order_info["businessAmount"], RPSData.user_id)

        # ??????????????????????????????
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.ACH.value][0]
        self.client.logger.info("?????????????????????: {}".format(select_method))
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
        # ???????????????????????????????????????
        query_order = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info["businessOrderNo"])
        self.assertEqual(query_order["businessAmount"], pay_order_info["businessAmount"])
        # ??????????????????????????????????????????
        self.waitUntilPayChannelOrderComplete(pay_order)
        query_order = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info["businessOrderNo"])
        self.assertEqual(query_order["status"], PayOrder.PAY_SUCCESS.value)

        targetAccountBalance2 = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"??????????????????: {targetAccountBalance2}, ?????????: {targetAccountBalance2 - targetAccountBalance}")

        self.assertEqual(query_order["status"], PayOrder.PAY_SUCCESS.value, "???????????????????????????")
        self.assertAlmostEqual(targetAccountBalance2 - targetAccountBalance, 0, msg="???????????????????????????????????????????????????", delta=0.1**7)

    @unittest.skip("wire??????????????????")
    def test_008_placePaymentOrder_deposit_wire_outsideDeduction(self):
        """
        ?????????????????????->ro, ??????????????????wire
        """
        # ???????????????
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
        self.assertIsNotNone(pay_order, "??????????????????????????????")
        self.checkPayOrderInDB(pay_order, pay_order_info)
        # ??????????????????
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)
        self.checkCodeAndMessage(methods)
        self.assertEqual(len(methods["data"]), len(RPSData.payment_methods["deposit"]), "?????????data?????????")
        self.checkPaymentMethod(methods["data"], pay_order_info["businessAmount"], RPSData.user_id)

        # ??????????????????????????????
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.WIRE.value][0]
        self.client.logger.info("?????????????????????: {}".format(select_method))
        order_info = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, RPSData.app_key,
                                                        pay_order, pay_order_info["currency"], select_method["type"],
                                                        select_method["serviceChannel"],
                                                        select_method["currencyList"][0]["fee"],
                                                        pay_order_info["businessAmount"] + select_method["currencyList"][0]["fee"])
        self.checkCodeAndMessage(order_info)
        self.checkSubmitOrderInfo(order_info["data"], select_method["currencyList"][0]["fee"], pay_order, select_method["type"], pay_order_info["businessOrderNo"])
        # TODO ??????wire???????????????
        # ???????????????????????????????????????
        query_order = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info["businessOrderNo"])
        self.assertEqual(query_order["businessAmount"], pay_order_info["businessAmount"])
        # ??????????????????????????????????????????
        self.waitUntilPayChannelOrderComplete(pay_order)

    def test_009_placePaymentOrder_transfer_walletToWallet_outsideDeduction(self):
        """
        ???????????????ro->ro, ??????????????????wallet
        """
        # ???????????????
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
        # ??????????????????
        sourceAccountBalance = self.client.getRoAccountBalance(pay_order_info["sourceRoxeAccount"], pay_order_info["currency"])
        targetAccountBalance = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"???????????????: {sourceAccountBalance}")
        self.client.logger.info(f"??????????????????: {targetAccountBalance}")
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.assertIsNotNone(pay_order, "??????????????????????????????")
        self.checkPayOrderInDB(pay_order, pay_order_info)
        # ??????????????????
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)
        self.checkCodeAndMessage(methods)
        self.assertEqual(len(methods["data"]), len(RPSData.payment_methods["deposit"]), "?????????data?????????")
        self.checkPaymentMethod(methods["data"], pay_order_info["businessAmount"], RPSData.user_id, sourceAccountBalance)

        # ??????????????????????????????
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("?????????????????????: {}".format(select_method))
        self.client.logger.info("???????????????????????????: {}".format(select_method["currencyList"][0]["fee"]))
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

        # ???????????????????????????????????????`
        query_order_info = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info["businessOrderNo"])
        self.assertEqual(query_order_info["businessAmount"], pay_order_info["businessAmount"])
        self.waitUntilPayChannelOrderComplete(pay_order, time_out=300)
        query_order_info = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info["businessOrderNo"])
        self.assertEqual(query_order_info["status"], PayOrder.PAY_SUCCESS.value)
        sourceAccountBalance2 = self.client.getRoAccountBalance(pay_order_info["sourceRoxeAccount"], pay_order_info["currency"])
        targetAccountBalance2 = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"???????????????: {sourceAccountBalance2}, ?????????: {sourceAccountBalance2 - sourceAccountBalance}")
        self.client.logger.info(f"??????????????????: {targetAccountBalance2}, ?????????: {targetAccountBalance2 - targetAccountBalance}")

        self.assertAlmostEqual(sourceAccountBalance - sourceAccountBalance2, pay_order_info["businessAmount"] + select_method["currencyList"][0]["fee"], msg="????????????????????????", delta=0.1**7)
        self.assertAlmostEqual(targetAccountBalance2 - targetAccountBalance, pay_order_info["businessAmount"], msg="???????????????????????????", delta=0.1**7)
        self.assertIsNotNone(query_order_info["serviceChannelOrderId"], "????????????????????????????????????id")

        # ????????????hash
        tx_hash = query_order_info["serviceChannelOrderId"]
        self.client.checkRoTransactionHash(tx_hash, pay_order_info, select_method["currencyList"][0]["fee"])

    @unittest.skip("card??????????????????stripe?????????????????????")
    def test_010_placePaymentOrder_transfer_cardToWallet_outsideDeduction(self):
        """
        ?????????????????????->ro, ??????????????????card
        """
        # ???????????????
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
        self.assertIsNotNone(pay_order, "??????????????????????????????")
        self.checkPayOrderInDB(pay_order, pay_order_info)
        # ??????????????????
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)
        self.checkCodeAndMessage(methods)
        self.assertEqual(len(methods["data"]), len(RPSData.payment_methods["transfer"]), "?????????data?????????")
        self.checkPaymentMethod(methods["data"], pay_order_info["businessAmount"], RPSData.user_id)

        # ??????????????????????????????
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.CARD.value][0]
        self.client.logger.info("?????????????????????: {}".format(select_method))
        self.client.logger.info("???????????????????????????: {}".format(select_method["currencyList"][0]["fee"]))
        order_info = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, RPSData.app_key,
                                                        pay_order, pay_order_info["currency"], select_method["type"],
                                                        select_method["serviceChannel"],
                                                        select_method["currencyList"][0]["fee"],
                                                        pay_order_info["businessAmount"] + select_method["currencyList"][0]["fee"])
        self.checkCodeAndMessage(order_info)

        # ???????????????????????????????????????

    def test_011_placePaymentOrder_transfer_achToWallet_outsideDeduction(self):
        """
        ?????????????????????->ro, ??????????????????ach
        """
        self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        # ???????????????
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
        # ??????????????????
        sourceAccountBalance = self.client.getRoAccountBalance(pay_order_info["sourceRoxeAccount"], pay_order_info["currency"])
        targetAccountBalance = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"???????????????: {sourceAccountBalance}")
        self.client.logger.info(f"??????????????????: {targetAccountBalance}")
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        # pay_order = 25034928328540160
        self.assertIsNotNone(pay_order, "??????????????????????????????")
        self.checkPayOrderInDB(pay_order, pay_order_info)
        # ??????????????????
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)
        self.checkCodeAndMessage(methods)
        self.assertEqual(len(methods["data"]), len(RPSData.payment_methods["transfer"]), "?????????data?????????")
        self.checkPaymentMethod(methods["data"], pay_order_info["businessAmount"], RPSData.user_id, sourceAccountBalance)

        # ??????????????????????????????
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.ACH.value][0]
        self.client.logger.info("?????????????????????: {}".format(select_method))
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
        # ???????????????????????????????????????
        query_order = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info["businessOrderNo"])
        self.assertEqual(query_order["businessAmount"], pay_order_info["businessAmount"])
        # ??????????????????????????????????????????
        self.waitUntilPayChannelOrderComplete(pay_order)

        query_order = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info["businessOrderNo"])
        self.assertEqual(query_order["status"], PayOrder.PAY_SUCCESS.value)
        sourceAccountBalance2 = self.client.getRoAccountBalance(pay_order_info["sourceRoxeAccount"], pay_order_info["currency"])
        targetAccountBalance2 = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"???????????????: {sourceAccountBalance2}, ?????????: {sourceAccountBalance2 - sourceAccountBalance}")
        self.client.logger.info(f"??????????????????: {targetAccountBalance2}, ?????????: {targetAccountBalance2 - targetAccountBalance}")

        # rps??????????????????send???????????????????????????
        self.assertEqual(query_order["status"], PayOrder.PAY_SUCCESS.value, "???????????????????????????")
        self.assertAlmostEqual(sourceAccountBalance2 - sourceAccountBalance, 0, delta=0.1**7)

    @unittest.skip("wire??????????????????")
    def test_012_placePaymentOrder_transfer_wireToWallet(self):
        """
        ?????????????????????->ro, ??????????????????wire
        """
        # ???????????????
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
        self.assertIsNotNone(pay_order, "??????????????????????????????")
        self.checkPayOrderInDB(pay_order, pay_order_info)
        # ??????????????????
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)
        self.checkCodeAndMessage(methods)
        self.assertEqual(len(methods["data"]), len(RPSData.payment_methods["transfer"]), "?????????data?????????")
        self.checkPaymentMethod(methods["data"], pay_order_info["businessAmount"], RPSData.user_id)

        # ??????????????????????????????
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.WIRE.value][0]
        self.client.logger.info("?????????????????????: {}".format(select_method))
        order_info = self.client.submitOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, RPSData.app_key,
                                                        pay_order, pay_order_info["currency"], select_method["type"],
                                                        select_method["serviceChannel"],
                                                        select_method["currencyList"][0]["fee"],
                                                        pay_order_info["businessAmount"] +
                                                        select_method["currencyList"][0]["fee"])
        self.checkCodeAndMessage(order_info)

        # ???????????????????????????????????????

    def test_013_placePaymentOrder_withdraw(self):
        """
        ????????????????????????ro???????????????????????????,
        """
        # ???????????????
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
        self.assertIsNotNone(pay_order, "??????????????????????????????")
        self.checkPayOrderInDB(pay_order, pay_order_info)
        # ??????????????????
        sourceAccountBalance = self.client.getRoAccountBalance(pay_order_info["sourceRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"???????????????: {sourceAccountBalance}")
        targetAccountBalance = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"??????????????????: {targetAccountBalance}")
        # ??????????????????
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)
        self.checkCodeAndMessage(methods)
        self.assertEqual(len(methods["data"]), len(RPSData.payment_methods["withdraw"]), "?????????data?????????")
        self.checkPaymentMethod(methods["data"], pay_order_info["businessAmount"], RPSData.user_id, sourceAccountBalance)

        # ??????????????????????????????
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("?????????????????????: {}".format(select_method))
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
        # ???????????????????????????????????????
        query_order = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info["businessOrderNo"])
        self.assertEqual(query_order["businessAmount"], pay_order_info["businessAmount"])
        # ??????????????????????????????????????????
        # self.waitUntilPayChannelOrderComplete(pay_order)
        self.waitUntilPayChannelOrderComplete(pay_order)
        query_order = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info["businessOrderNo"])
        self.assertEqual(query_order["status"], PayOrder.PAY_SUCCESS.value)
        # ??????????????????
        sourceAccountBalance2 = self.client.getRoAccountBalance(pay_order_info["sourceRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"???????????????: {sourceAccountBalance2}, ?????????{sourceAccountBalance2 - sourceAccountBalance}")
        targetAccountBalance2 = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"??????????????????: {targetAccountBalance2}, ?????????{targetAccountBalance2 - targetAccountBalance}")

        self.assertAlmostEqual(sourceAccountBalance - sourceAccountBalance2, pay_order_info["businessAmount"] + select_method["currencyList"][0]["fee"], delta=0.1**7)
        self.assertAlmostEqual(targetAccountBalance2 - targetAccountBalance, pay_order_info["businessAmount"], delta=0.1**7)
        self.assertIsNotNone(query_order["serviceChannelOrderId"], "????????????????????????????????????id")

        # ????????????hash
        tx_hash = query_order["serviceChannelOrderId"]
        self.client.checkRoTransactionHash(tx_hash, pay_order_info, select_method["currencyList"][0]["fee"])

    """
    ?????????????????????
    """

    def test_014_queryBindAchAccount_userNotExist(self):
        """
        ?????????????????????????????????ach??????
        """
        self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        sign = RPSData.sign
        accounts = self.client.queryBindBankAccount(sign, RPSData.app_key, RPSData.user_not_exist, "USD")
        self.assertEqual(accounts, [], "????????????????????????????????????")

    def test_015_queryBindAchAccount_userNotLogin(self):
        """
        ?????????????????????????????????ach??????
        """
        self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        sign = RPSData.sign
        accounts = self.client.queryBindBankAccount(sign, RPSData.app_key, RPSData.user_not_login, "USD")
        self.assertEqual(accounts, [], "????????????????????????????????????")

    def test_016_queryBindAchAccount_appKeyNotCorrect(self):
        """
        appkey???????????????none?????????????????????ach??????
        """
        sign = RPSData.sign
        accounts = self.client.queryBindBankAccount(sign, RPSData.app_key + "abc", RPSData.user_not_login, "USD")
        self.checkCodeAndMessage(accounts, "PAY_RPS_664", "appkey not exist")

        accounts = self.client.queryBindBankAccount(RPSData.sign, None, RPSData.user_id, "USD")
        self.checkCodeAndMessage(accounts, "PAY_RPS_663", "header parameter appkey cannot be null")

    def test_017_bindAchAccount_userNotExist(self):
        """
        ????????????????????????ach??????
        """
        account_info = RPSData.ach_account.copy()
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_not_exist, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res, "PAY_RPS_715", "userid not match")
        # ????????????????????????????????????
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_not_exist, account_info["currency"])
        self.assertEqual(accounts, [])

    def test_018_bindAchAccount_userNotLogin(self):
        """
        ????????????????????????ach??????
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
        # ????????????????????????????????????
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_not_login, account_info["currency"])
        self.assertEqual(accounts, [])

    def test_019_bindAchAccount_userNotKyc(self):
        """
        ????????????kyc???????????????ach??????
        """
        account_info = RPSData.ach_account.copy()
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_not_kyc, RPSData.user_not_kyc_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res, "PAY_RPS_674", "The bank account name does not match the KYC name")
        self.assertIsNone(bind_res["data"])
        # ????????????????????????????????????
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_not_kyc, account_info["currency"])
        self.assertEqual(accounts, [])

    def test_020_bindAchAccount_accountHasBeenBind(self):
        """
        ??????ach??????, ??????????????????????????????
        """
        self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        account_info = RPSData.ach_account.copy()
        # account_info["holder"] += "asd"
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res, "PAY_RPS_710", "verified account cannot be more than 1")
        self.assertIsNone(bind_res["data"])
        # ????????????????????????????????????
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        self.assertEqual(len(accounts), 1)

    def test_021_bindAchAccount_accountNameNotMatchKycName_firstNameMatch(self):
        """
        ??????ach??????, ???????????????????????????kyc?????????, firstName????????????
        """
        account_info = RPSData.ach_account.copy()
        account_info["holder"] += "asd"
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res)
        self.checkAchAccountInfo(bind_res["data"], account_info, RPSData.user_id)
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        self.assertEqual(len(accounts), 1, "?????????????????????????????????????????????")
        self.checkAchAccountInfoFromDB(accounts[0], RPSData.user_id)

    def test_022_bindAchAccount_accountNameNotMatchKycName_lastNameMatch(self):
        """
        ??????ach??????, ???????????????????????????kyc?????????, lastName?????????
        """
        account_info = RPSData.ach_account.copy()
        account_info["holder"] += "asd"
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res)
        self.checkAchAccountInfo(bind_res["data"], account_info, RPSData.user_id)
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        self.assertEqual(len(accounts), 1, "?????????????????????????????????????????????")
        self.checkAchAccountInfoFromDB(accounts[0], RPSData.user_id)

    def test_023_bindAchAccount_accountNameNotMatchKycName_bothNotMatch(self):
        """
        ??????ach??????, ???????????????????????????kyc?????????, firstName???lastName???????????????
        """
        account_info = RPSData.ach_account.copy()
        account_info["holder"] = "Ass" + account_info["holder"] + "asd"
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res, "PAY_RPS_674", "The bank account name does not match the KYC name")
        self.assertIsNone(bind_res["data"])
        # ????????????????????????????????????
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        self.assertEqual(accounts, [])

    def test_024_bindAchAccount_routingNumberNotCorrect(self):
        """
        ??????ach?????????routingNumber????????? TODO bug
        """
        account_info = RPSData.ach_account.copy()
        account_info["routingNumber"] = account_info["routingNumber"].replace("1", "2")
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res, "PAY_RPS_717", "bank account token cannot be empty")
        self.assertIsNone(bind_res["data"])
        # ????????????????????????????????????
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        self.assertEqual(accounts, [])

    def test_025_bindAchAccount_accountNumberNotCorrect(self):
        """
        ??????ach?????????routingNumber????????? TODO bug
        """
        account_info = RPSData.ach_account.copy()
        account_info["accountNumber"] = account_info["accountNumber"].replace("1", "2")
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res, "PAY_RPS_717", "bank account token cannot be empty")
        self.assertIsNone(bind_res["data"])
        # ????????????????????????????????????
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        self.assertEqual(accounts, [])

    def test_026_bindAchAccount_holderTypeNotCorrect(self):
        """
        ??????ach?????????holderType????????? TODO bug
        """
        account_info = RPSData.ach_account.copy()
        account_info["holderType"] = "111asd"
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res, "PAY_RPS_717", "bank account token cannot be empty")
        self.assertIsNone(bind_res["data"])
        # ????????????????????????????????????
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        self.assertEqual(accounts, [])

    def test_027_bindAchAccount_countryNotCorrect(self):
        """
        ??????ach?????????country????????? TODO bug
        """
        account_info = RPSData.ach_account.copy()
        account_info["country"] = "UK"
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res, "PAY_RPS_717", "bank account token cannot be empty")
        self.assertIsNone(bind_res["data"])
        # ????????????????????????????????????
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        self.assertEqual(accounts, [])

    def test_028_bindAchAccount_accountInfoIsMissingItem(self):
        """
        ??????ach????????????????????????????????????????????? TODO bug
        """
        account_info = RPSData.ach_account.copy()
        account_info.pop("country")
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res, "PAY_RPS_684", "bank acount country cannot be empty")
        self.assertIsNone(bind_res["data"])
        # ????????????????????????????????????
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        self.assertEqual(accounts, [])

    def test_029_verifyAchAccount_oneCheckAmountEnterError(self):
        """
        ??????ach????????????????????????????????????????????????????????????????????????????????????
        """
        account_info = RPSData.ach_account.copy()
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res)
        self.assertIsNotNone(bind_res["data"])
        # ????????????????????????????????????
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        account_id = accounts[0]["id"]
        check_info = self.client.verifyBankAccount(RPSData.user_id, RPSData.user_login_token, account_id, 0.11, 0.45)
        self.checkCodeAndMessage(check_info, "PAYIN_STRIPE_610", "bank account verify failed ,The amounts provided do not match the amounts that were sent to the bank account")
        self.assertIsNone(check_info["data"])
        check_info2 = self.client.verifyBankAccount(RPSData.user_id, RPSData.user_login_token, account_id, 0.32, 0.45)
        self.checkCodeAndMessage(check_info2)
        self.assertEqual(check_info2["data"], True, "??????????????????")
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, "USD")
        self.assertEqual(len(accounts), 1, "?????????????????????????????????????????????")
        self.checkAchAccountInfoFromDB(accounts[0], RPSData.user_id)
        self.assertEqual(accounts[0]["status"], PayOrder.PAY_FAIL.value)

    def test_030_verifyAchAccount_checkAmountEnterIllegal(self):
        """
        ??????ach??????????????????????????????????????????????????????????????????????????????????????????
        """
        account_info = RPSData.ach_account.copy()
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res)
        self.assertIsNotNone(bind_res["data"])
        # ????????????????????????????????????
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        account_id = accounts[0]["id"]
        check_info = self.client.verifyBankAccount(RPSData.user_id, RPSData.user_login_token, account_id, 0, 0.45)
        self.checkCodeAndMessage(check_info, "PAY_RPS_687", "verify amount cannot be null or<=0")
        self.assertIsNone(check_info["data"])
        check_info = self.client.verifyBankAccount(RPSData.user_id, RPSData.user_login_token, account_id, "abc123", 0.45)
        self.checkCodeAndMessage(check_info, "PAY_RPS_600", "service error")  # ???????????????
        self.assertIsNone(check_info["data"])
        check_info2 = self.client.verifyBankAccount(RPSData.user_id, RPSData.user_login_token, account_id, 0.32, 0.45)
        self.checkCodeAndMessage(check_info2)
        self.assertEqual(check_info2["data"], True, "??????????????????")
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, "USD")
        self.assertEqual(len(accounts), 1, "?????????????????????????????????????????????")
        self.checkAchAccountInfoFromDB(accounts[0], RPSData.user_id)
        self.assertEqual(accounts[0]["status"], PayOrder.PAY_FAIL.value)

    def test_031_verifyAchAccount_checkAmountEnterError3times(self):
        """
        ??????ach???????????????????????????????????????3?????????
        """
        account_info = RPSData.ach_account.copy()
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res)
        self.assertIsNotNone(bind_res["data"])
        # ????????????????????????????????????
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
        self.assertIsNone(check_info2["data"], "??????????????????")
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, "USD")
        self.assertEqual(len(accounts), 1, "?????????????????????????????????????????????")
        self.checkAchAccountInfoFromDB(accounts[0], RPSData.user_id)
        self.assertEqual(accounts[0]["status"], 1, "????????????????????????????????????")

    def test_032_verifyAchAccount_checkAccountHasBeenVerified(self):
        """
        ??????ach???????????????????????????????????????????????????
        """
        account_info = RPSData.ach_account.copy()
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res)
        self.assertIsNotNone(bind_res["data"])
        # ????????????????????????????????????
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        account_id = accounts[0]["id"]
        check_info = self.client.verifyBankAccount(RPSData.user_id, RPSData.user_login_token, account_id, 0.32, 0.45)
        self.checkCodeAndMessage(check_info)
        self.assertEqual(check_info["data"], True, "??????????????????")
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, "USD")
        self.assertEqual(len(accounts), 1, "?????????????????????????????????????????????")
        self.checkAchAccountInfoFromDB(accounts[0], RPSData.user_id)
        self.assertEqual(accounts[0]["status"], 3)

        check_info = self.client.verifyBankAccount(RPSData.user_id, RPSData.user_login_token, account_id, 0.32, 0.45)
        self.checkCodeAndMessage(check_info, "PAY_RPS_718", "a bank account has verified")
        self.assertIsNone(check_info["data"])

    def test_033_verifyAchAccount_userNotMatchWithBindUser(self):
        """
        ??????ach?????????A?????????????????????????????????B?????????????????????
        """
        account_info = RPSData.ach_account.copy()
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res)
        self.assertIsNotNone(bind_res["data"])
        # ????????????????????????????????????
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        account_id = accounts[0]["id"]
        check_info = self.client.verifyBankAccount(RPSData.user_not_kyc, RPSData.user_not_kyc_login_token, account_id, 0.32, 0.45)
        self.checkCodeAndMessage(check_info, "PAY_RPS_671", "bank account not exist")
        self.assertIsNone(check_info["data"], "??????????????????")
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, "USD")
        self.assertEqual(accounts[0]["id"], account_id, "?????????????????????????????????????????????")
        self.assertEqual(accounts[0]["status"], 1, "?????????????????????????????????????????????")
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_not_kyc, "USD")
        self.assertEqual(accounts, [], "?????????????????????????????????????????????")

    def test_034_verifyAchAccount_userLogout(self):
        """
        ??????ach?????????A?????????????????????????????????token??????????????????????????????
        """
        account_info = RPSData.ach_account.copy()
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res)
        self.assertIsNotNone(bind_res["data"])
        # ????????????????????????????????????
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        account_id = accounts[0]["id"]
        check_info = self.client.verifyBankAccount(RPSData.user_not_login, RPSData.user_login_token.replace("e", "a"), account_id, 0.32, 0.45)
        self.checkCodeAndMessage(check_info, "PAY_RPS_713", "user token invalid")
        self.assertIsNone(check_info["data"], "??????????????????")
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, "USD")
        self.assertEqual(accounts[0]["id"], account_id, "?????????????????????????????????????????????")
        self.assertEqual(accounts[0]["status"], 1, "?????????????????????????????????????????????")
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_not_login, "USD")
        self.assertEqual(accounts, [], "?????????????????????????????????????????????")

    def test_035_verifyAchAccount_userNotExist(self):
        """
        ??????ach?????????A?????????????????????????????????????????????B?????????????????????
        """
        account_info = RPSData.ach_account.copy()
        account_info["bankAccountToken"] = self.client.getStripeToken(account_info)
        bind_res = self.client.bindBankAccount(RPSData.user_id, RPSData.user_login_token, account_info, RPSData.app_key)
        self.checkCodeAndMessage(bind_res)
        self.assertIsNotNone(bind_res["data"])
        # ????????????????????????????????????
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_info["currency"])
        account_id = accounts[0]["id"]
        check_info = self.client.verifyBankAccount(RPSData.user_not_exist, RPSData.user_login_token.replace("e", "a"), account_id, 0.32, 0.45)
        self.checkCodeAndMessage(check_info, "PAY_RPS_713", "user token invalid")
        self.assertIsNone(check_info["data"], "??????????????????")
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, "USD")
        self.assertEqual(accounts[0]["id"], account_id, "?????????????????????????????????????????????")
        self.assertEqual(accounts[0]["status"], 1, "?????????????????????????????????????????????")
        accounts = self.client.queryBindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_not_exist, "USD")
        self.assertEqual(accounts, [], "?????????????????????????????????????????????")

    def test_036_unbindAchAccount_bindAccountNotExist(self):
        """
        ?????????????????????id?????????????????????????????????
        """
        account_id = 111111111
        unbind_res = self.client.unbindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_id, account_id, int(time.time()))
        self.checkCodeAndMessage(unbind_res, "PAY_RPS_671", "bank account not exist")

    def test_037_unbindAchAccount_otherUserBindAccount(self):
        """
        ???????????????????????????????????????????????????
        """
        account_id = self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        unbind_res = self.client.unbindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_not_kyc, account_id, int(time.time()))
        self.checkCodeAndMessage(unbind_res, "PAY_RPS_671", "bank account not exist")

    def test_038_unbindAchAccount_userNotExist(self):
        """
        ?????????????????????????????????????????????
        """
        account_id = self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        unbind_res = self.client.unbindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_not_exist, account_id, int(time.time()))
        self.checkCodeAndMessage(unbind_res, "PAY_RPS_671", "bank account not exist")

    def test_039_unbindAchAccount_userLogout(self):
        """
        ????????????????????????????????????????????????
        """
        account_id = self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        unbind_res = self.client.unbindBankAccount(RPSData.sign, RPSData.app_key, RPSData.user_not_login, account_id, int(time.time()))
        self.checkCodeAndMessage(unbind_res, "PAY_RPS_671", "bank account not exist")

    def test_040_unbindAchAccount_appKeyInCorrect(self):
        """
        ???????????????appkey?????????
        """
        account_id = self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        unbind_res = self.client.unbindBankAccount(RPSData.sign, RPSData.app_key + "23", RPSData.user_id, account_id, int(time.time()))
        self.checkCodeAndMessage(unbind_res, "PAY_RPS_664", "appkey not exist")

    def test_041_unbindAchAccount_accountNotPassVerify(self):
        """
        ????????????????????????????????????
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
        ?????????????????????????????????????????????
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
        ??????plaid token???appkey?????????
        """
        account_id = self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        q_res = self.client.queryPlaidLinkToken(RPSData.user_id, RPSData.user_login_token, RPSData.app_key + "23", account_id)
        self.checkCodeAndMessage(q_res, "PAY_RPS_664", "appkey not exist")

    def test_044_queryPlaidLinkToken_userNotExist(self):
        """
        ??????plaid token??????????????????
        """
        account_id = self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        q_res = self.client.queryPlaidLinkToken(RPSData.user_not_exist, RPSData.user_login_token.replace("e", "a"), RPSData.app_key, account_id)
        self.checkCodeAndMessage(q_res, "PAY_RPS_713", "user token invalid")

    def test_045_queryPlaidLinkToken_userNotMatchAccount(self):
        """
        ??????plaid token?????????????????????????????????
        """
        account_id = self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        q_res = self.client.queryPlaidLinkToken(RPSData.user_not_kyc, RPSData.user_not_kyc_login_token, RPSData.app_key, account_id)
        self.checkCodeAndMessage(q_res, "PAY_RPS_601", "parameter check failed:bank account not exist")

    def test_046_submitPayInOrder_appKeyInCorrect(self):
        """
        ???????????????appkey?????????
        """
        # ???????????????
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
        ???????????????appkey???None
        """
        # ???????????????
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
        ???????????????businessAmount???????????????0????????????none????????????????????????
        """
        # ???????????????
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
        pay_order_info["businessAmount"] = "!@#$???%"
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_600", "service error")
        pay_order_info["businessAmount"] = "abc"
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_600", "service error")

    def test_049_submitPayInOrder_channelFeeDeductionMethodNotSupport(self):
        """
        ???????????????channelFeeDeductionMethod?????????????????????0????????????none????????????????????????
        """
        # ???????????????
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
        pay_order_info["channelFeeDeductionMethod"] = "!@#$???%"
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_600", "service error")
        pay_order_info["channelFeeDeductionMethod"] = "abc"
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.checkCodeAndMessage(pay_order, "PAY_RPS_600", "service error")

    def test_050_submitPayInOrder_businessOrderNoIsRepeat_oldOrderNotPay(self):
        """
        ???????????????????????????businessOrderNo????????????????????????????????????????????????businessOrderNo??????????????????
        """
        # ???????????????
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
        ???????????????????????????businessOrderNo??????????????????????????????????????????businessOrderNo??????????????????
        """
        # ???????????????
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
        # ??????????????????
        sourceAccountBalance = self.client.getRoAccountBalance(pay_order_info["sourceRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"??????????????????: {sourceAccountBalance}")
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        self.assertTrue(isinstance(pay_order, int))
        # ??????????????????
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)
        self.checkCodeAndMessage(methods)
        self.checkPaymentMethod(methods["data"], pay_order_info["businessAmount"], RPSData.user_id, sourceAccountBalance)

        # ??????????????????????????????
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("?????????????????????: {}".format(select_method))
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
        ???????????????businessItemName???????????????None, ????????????
        """
        # ???????????????
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
        ???????????????currency??????????????????None???????????????
        """
        # ???????????????
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
        ???????????????currency????????????????????????????????????
        """
        # ???????????????
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
        ??????????????????????????????sourceRoxeAccount????????????None???????????????
        """
        # ???????????????
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
        ??????????????????????????????targetRoxeAccount????????????None???????????????
        """
        # ???????????????
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
        ???????????????businessType????????????None?????????????????????
        """
        # ???????????????
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
        ???????????????country????????????None?????????????????????
        """
        # ???????????????
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
        ????????????????????????????????????appkey?????????
        """
        # ???????????????
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
        ?????????????????????????????????????????????????????????
        """
        pay_order = 12345678901234567
        pay_methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order, RPSData.app_key)
        self.checkCodeAndMessage(pay_methods, "PAY_RPS_700", "order not exist")

    def test_061_queryOrderPayInMethod_userLoginTokenNotInvalid(self):
        """
        ???????????????????????????????????????????????????token??????
        """
        # ???????????????
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
        ???????????????????????????????????????????????????token???userId?????????
        """
        # ???????????????
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
        ????????????????????????????????????????????????????????????
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
        ????????????????????????????????????????????????????????????
        """
        account_info = RPSData.ach_account.copy()
        account_info["accountNumber"] = RPSData.account_using_failed
        self.client.bindAndVerifyAchAccount(account_info)
        # ???????????????
        amount = 12.34
        currency = RPSData.ach_account["currency"].upper()
        # ??????????????????
        targetAccountBalance = self.client.getRoAccountBalance(RPSData.user_roxe_account, currency)
        self.client.logger.info(f"??????????????????: {targetAccountBalance}")

        pay_order, coupon_code = self.client.submitAchPayOrder(RPSData.user_roxe_account, amount, currency, expect_pay_success=False)
        time_out = 60
        flag = False
        if RPSData.is_check_db:
            sql = "select * from `roxe_pay_in_out`.roxe_pay_in_order where id='{}'".format(pay_order["id"])
            b_time = time.time()
            while time.time() - b_time < time_out:
                db_res = self.mysql.exec_sql_query(sql)
                self.client.logger.info(f"????????????????????????: {db_res[0]}")
                if db_res[0]["payFailedReason"]:
                    flag = True
                    reason = "The customer\'s bank account could not be located."
                    self.assertIn(reason, db_res[0]["payFailedReason"], "???????????????????????????")
                    break
                time.sleep(10)
        self.assertTrue(flag, "ach????????????????????????")
        pay_order_id = pay_order["id"]
        pay_methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order_id, RPSData.app_key)
        s_balance = self.client.getRoAccountBalance(RPSData.user_roxe_account, "USD")
        self.checkCodeAndMessage(pay_methods)
        self.checkPaymentMethod(pay_methods["data"], amount, RPSData.user_id, s_balance)

    def test_065_selectPaymentMethod_appKeyInCorrect(self):
        """
        ?????????????????????appkey?????????????????????None
        """
        # ???????????????
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
        self.client.logger.info("?????????????????????: {}".format(select_method))
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
        ???????????????????????????token??????
        """
        # ???????????????
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
        self.client.logger.info("?????????????????????: {}".format(select_method))
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
        ???????????????????????????token???userId?????????
        """
        # ???????????????
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
        self.client.logger.info("?????????????????????: {}".format(select_method))
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
        ?????????????????????currency?????????: ????????????????????????
        """
        # ???????????????
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
        self.client.logger.info("?????????????????????: {}".format(select_method))
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
        ????????????????????????????????????type????????????????????????
        """
        # ???????????????
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
        self.client.logger.info("?????????????????????: {}".format(select_method))
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
        ?????????????????????????????????????????????????????????
        """
        # ???????????????
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
        self.client.logger.info("?????????????????????: {}".format(select_method))
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
        ??????????????????????????????????????????
        """
        # ???????????????
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
        self.client.logger.info("?????????????????????: {}".format(select_method))
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
        ???????????????????????????????????????????????????
        """
        # ???????????????
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
        self.client.logger.info("?????????????????????: {}".format(select_method))
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
        ?????????????????????????????????????????????
        """
        # ???????????????
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
        self.client.logger.info("?????????????????????: {}".format(select_method))
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
        ?????????????????????????????????id???None
        """
        # ???????????????
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
        self.client.logger.info("?????????????????????: {}".format(select_method))
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
        ??????????????????????????????????????????: ???????????????currency???payMethod???serviceChannel???channelFee???payableAmount
        """
        # ???????????????
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
        self.client.logger.info("?????????????????????: {}".format(select_method))
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
        ??????ach???????????????????????????????????????, ??????ach????????????
        """
        account_info = RPSData.ach_account.copy()
        account_info["accountNumber"] = RPSData.account_using_failed
        self.client.bindAndVerifyAchAccount(account_info)
        # ???????????????
        amount = 12.34
        currency = RPSData.ach_account["currency"].upper()
        # ??????????????????
        targetAccountBalance = self.client.getRoAccountBalance(RPSData.user_roxe_account, currency)
        self.client.logger.info(f"??????????????????: {targetAccountBalance}")

        pay_order, coupon_code = self.client.submitAchPayOrder(RPSData.user_roxe_account, amount, currency, expect_pay_success=False)
        time_out = 60
        flag = False
        if RPSData.is_check_db:
            sql = "select * from `roxe_pay_in_out`.roxe_pay_in_order where id='{}'".format(pay_order["id"])
            b_time = time.time()
            while time.time() - b_time < time_out:
                db_res = self.mysql.exec_sql_query(sql)
                self.client.logger.info(f"????????????????????????: {db_res[0]}")
                if db_res[0]["payFailedReason"]:
                    flag = True
                    reason = "The customer\'s bank account could not be located."
                    self.assertIn(reason, db_res[0]["payFailedReason"], "???????????????????????????")
                    break
                time.sleep(20)
        # ??????????????????
        targetAccountBalance2 = self.client.getRoAccountBalance(RPSData.user_roxe_account, currency)
        self.client.logger.info(f"??????????????????: {targetAccountBalance2}")
        self.assertEqual(targetAccountBalance, targetAccountBalance2)
        query_order = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order["businessOrderNo"])
        self.assertEqual(query_order["status"], PayOrder.PAY_FAIL.value, "?????????????????????status??????3")
        if not flag:
            self.assertTrue(False, f"??????{time_out}?????????????????????????????????")

    def test_077_selectPaymentMethod_AchAccount_accountHasBeenCanceled(self):
        """
        ??????ach??????????????????????????????????????????, ??????ach????????????
        """
        account_info = RPSData.ach_account.copy()
        account_info["accountNumber"] = RPSData.account_canceled
        self.client.bindAndVerifyAchAccount(account_info)
        # ???????????????
        amount = 12.34
        currency = RPSData.ach_account["currency"].upper()
        # ??????????????????
        targetAccountBalance = self.client.getRoAccountBalance(RPSData.user_roxe_account, currency)
        self.client.logger.info(f"??????????????????: {targetAccountBalance}")

        pay_order, coupon_code = self.client.submitAchPayOrder(RPSData.user_roxe_account, amount, currency, expect_pay_success=False)
        time_out = 60
        flag = False
        if RPSData.is_check_db:
            sql = "select * from `roxe_pay_in_out`.roxe_pay_in_order where id='{}'".format(pay_order["id"])
            b_time = time.time()
            while time.time() - b_time < time_out:
                db_res = self.mysql.exec_sql_query(sql)
                self.client.logger.info(f"????????????????????????: {db_res[0]}")
                if db_res[0]["payFailedReason"]:
                    flag = True
                    reason = "The customer's bank account has been closed."
                    self.assertIn(reason, db_res[0]["payFailedReason"], "???????????????????????????")
                    break
                time.sleep(20)
        # ??????????????????
        targetAccountBalance2 = self.client.getRoAccountBalance(RPSData.user_roxe_account, currency)
        self.client.logger.info(f"??????????????????: {targetAccountBalance2}")
        self.assertEqual(targetAccountBalance, targetAccountBalance2)
        query_order = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order["businessOrderNo"])
        self.assertEqual(query_order["status"], PayOrder.PAY_FAIL.value, "?????????????????????status??????1")
        if not flag:
            self.assertTrue(False, f"??????{time_out}?????????????????????????????????")

    def test_078_selectPaymentMethod_AchAccount_accountInsufficientBalance(self):
        """
        ??????ach?????????????????????????????????????????????, ??????ach????????????
        """
        account_info = RPSData.ach_account.copy()
        account_info["accountNumber"] = RPSData.account_insufficient_balance
        self.client.bindAndVerifyAchAccount(account_info)
        # ???????????????
        amount = 12.34
        currency = RPSData.ach_account["currency"].upper()
        # ??????????????????
        targetAccountBalance = self.client.getRoAccountBalance(RPSData.user_roxe_account, currency)
        self.client.logger.info(f"??????????????????: {targetAccountBalance}")

        pay_order, coupon_code = self.client.submitAchPayOrder(RPSData.user_roxe_account, amount, currency, expect_pay_success=False)
        time_out = 60
        flag = False
        if RPSData.is_check_db:
            sql = "select * from `roxe_pay_in_out`.roxe_pay_in_order where id='{}'".format(pay_order["id"])
            b_time = time.time()
            while time.time() - b_time < time_out:
                db_res = self.mysql.exec_sql_query(sql)
                self.client.logger.info(f"????????????????????????: {db_res[0]}")
                if db_res[0]["payFailedReason"]:
                    flag = True
                    reason = "The customer's account has insufficient funds to cover this payment."
                    self.assertIn(reason, db_res[0]["payFailedReason"], "???????????????????????????")
                    break
                time.sleep(20)
        # ??????????????????
        targetAccountBalance2 = self.client.getRoAccountBalance(RPSData.user_roxe_account, currency)
        self.client.logger.info(f"??????????????????: {targetAccountBalance2}")
        self.assertEqual(targetAccountBalance, targetAccountBalance2)
        query_order = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order["businessOrderNo"])
        self.assertEqual(query_order["status"], PayOrder.PAY_FAIL.value, "?????????????????????status??????3")
        if not flag:
            self.assertTrue(False, f"??????{time_out}?????????????????????????????????")

    def test_079_selectPaymentMethod_AchAccount_accountUnauthorizedWithdrawal(self):
        """
        ??????ach???????????????????????????????????????????????????, ??????ach????????????
        """
        account_info = RPSData.ach_account.copy()
        account_info["accountNumber"] = RPSData.account_unauthorized_withdrawal
        self.client.bindAndVerifyAchAccount(account_info)
        # ???????????????
        amount = 12.34
        currency = RPSData.ach_account["currency"].upper()
        # ??????????????????
        targetAccountBalance = self.client.getRoAccountBalance(RPSData.user_roxe_account, currency)
        self.client.logger.info(f"??????????????????: {targetAccountBalance}")

        pay_order, coupon_code = self.client.submitAchPayOrder(RPSData.user_roxe_account, amount, currency, expect_pay_success=False)
        time_out = 60
        flag = False
        if RPSData.is_check_db:
            sql = "select * from `roxe_pay_in_out`.roxe_pay_in_order where id='{}'".format(pay_order["id"])
            b_time = time.time()
            while time.time() - b_time < time_out:
                db_res = self.mysql.exec_sql_query(sql)
                self.client.logger.info(f"????????????????????????: {db_res[0]}")
                if db_res[0]["payFailedReason"]:
                    flag = True
                    reason = "The customer has notified their bank that this payment was unauthorized."
                    self.assertIn(reason, db_res[0]["payFailedReason"], "???????????????????????????")
                    break
                time.sleep(20)
        # ??????????????????
        targetAccountBalance2 = self.client.getRoAccountBalance(RPSData.user_roxe_account, currency)
        self.client.logger.info(f"??????????????????: {targetAccountBalance2}")
        self.assertEqual(targetAccountBalance, targetAccountBalance2)
        query_order = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order["businessOrderNo"])
        self.assertEqual(query_order["status"], PayOrder.PAY_FAIL.value, "?????????????????????status??????3")
        if not flag:
            self.assertTrue(False, f"??????{time_out}?????????????????????????????????")

    def test_080_selectPaymentMethod_AchAccount_accountNotSupportCurrentCurrency(self):
        """
        ??????ach?????????????????????????????????????????????, ??????ach????????????
        """
        account_info = RPSData.ach_account.copy()
        account_info["accountNumber"] = RPSData.account_invalid_currency
        self.client.bindAndVerifyAchAccount(account_info)
        # ???????????????
        amount = 12.34
        currency = RPSData.ach_account["currency"].upper()
        # ??????????????????
        targetAccountBalance = self.client.getRoAccountBalance(RPSData.user_roxe_account, currency)
        self.client.logger.info(f"??????????????????: {targetAccountBalance}")

        pay_order, coupon_code = self.client.submitAchPayOrder(RPSData.user_roxe_account, amount, currency, expect_pay_success=False)
        time_out = 60
        flag = False
        if RPSData.is_check_db:
            sql = "select * from `roxe_pay_in_out`.roxe_pay_in_order where id='{}'".format(pay_order["id"])
            b_time = time.time()
            while time.time() - b_time < time_out:
                db_res = self.mysql.exec_sql_query(sql)
                self.client.logger.info(f"????????????????????????: {db_res[0]}")
                if db_res[0]["payFailedReason"]:
                    flag = True
                    reason = "The bank was unable to process this payment because of its currency. "
                    self.assertIn(reason, db_res[0]["payFailedReason"], "???????????????????????????")
                    break
                time.sleep(20)
        # ??????????????????
        targetAccountBalance2 = self.client.getRoAccountBalance(RPSData.user_roxe_account, currency)
        self.client.logger.info(f"??????????????????: {targetAccountBalance2}")
        self.assertEqual(targetAccountBalance, targetAccountBalance2)
        query_order = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order["businessOrderNo"])
        self.assertEqual(query_order["status"], PayOrder.PAY_FAIL.value, "?????????????????????status??????3")
        if not flag:
            self.assertTrue(False, f"??????{time_out}?????????????????????????????????")

    def test_081_selectPaymentMethod_Wallet_accountBalanceLessThanTransferAmount(self):
        """
        ????????????????????????????????????????????? < ????????????
        """
        source_account = RPSData.user_roxe_account
        target_account = RPSData.user_roxe_account_a
        s_balance = self.client.getRoAccountBalance(source_account, "USD")
        self.client.logger.info(f"{source_account}????????????: {s_balance}")
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
        # ????????????
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        # ??????????????????
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)

        # ??????????????????????????????
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("?????????????????????: {}".format(select_method))
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

    @unittest.skip("?????????????????????0, ??????")
    def test_082_selectPaymentMethod_Wallet_accountBalanceLessThanTransferAmountAddTransferFee(self):
        """
        ???????????????????????????????????????????????? < ??????????????? < ??????????????? + ??????????????????
        """
        source_account = RPSData.user_roxe_account_a
        target_account = RPSData.user_roxe_account
        s_balance = self.client.getRoAccountBalance(source_account, "USD")
        self.client.logger.info(f"{source_account}????????????: {s_balance}")
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
        # ????????????
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        # ??????????????????
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)

        # ??????????????????????????????
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("?????????????????????: {}".format(select_method))
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
        ????????????????????????????????????????????????????????????????????????
        """
        source_account = RPSData.user_roxe_account_a
        s_balance = self.client.getRoAccountBalance(source_account, "USD")
        self.client.logger.info(f"{source_account}????????????: {s_balance}")
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
        # ????????????
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        # ??????????????????
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)

        # ??????????????????????????????
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("?????????????????????: {}".format(select_method))
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
        ???????????????????????????????????????2??????????????????????????????1??????????????????2????????????????????????????????????2???????????????
        """
        source_account = RPSData.user_roxe_account_a
        target_account = RPSData.user_roxe_account
        s_balance = self.client.getRoAccountBalance(source_account, "USD")
        self.client.logger.info(f"{source_account}????????????: {s_balance}")
        # ???1?????????
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
        # ????????????
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        # ??????????????????
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)

        # ??????????????????????????????
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("?????????????????????: {}".format(select_method))
        payment_amount = pay_order_info["businessAmount"] + select_method["currencyList"][0]["fee"]
        if ApiUtils.parseNumberDecimal(payment_amount) < payment_amount:
            payment_amount = ApiUtils.parseNumberDecimal(payment_amount, isUp=True)

        # ???2?????????
        pay_order_info_2 = pay_order_info.copy()
        pay_order_info_2["businessAmount"] = ApiUtils.parseNumberDecimal(s_balance - 1)
        pay_order_info_2["businessOrderNo"] = "test" + str(int(time.time() * 1000))
        # ????????????
        pay_order_2 = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info_2)
        # ??????????????????
        methods_2 = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order_2)

        # ??????????????????????????????
        select_method_2 = [i for i in methods_2["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("?????????????????????: {}".format(select_method_2))
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

        self.client.logger.info(f"???1???????????????: {payment_amount}")
        submit_order = self.client.submitOrderPayInMethod(
            RPSData.user_id, RPSData.user_login_token, RPSData.app_key, pay_order, pay_order_info["currency"],
            select_method["type"], select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
            payment_amount, **fees
        )
        self.checkCodeAndMessage(submit_order)

        self.client.logger.info(f"???2???????????????: {payment_amount_2}")
        submit_order_2 = self.client.submitOrderPayInMethod(
            RPSData.user_id, RPSData.user_login_token, RPSData.app_key, pay_order_2, pay_order_info_2["currency"],
            select_method["type"], select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
            payment_amount_2, **fees
        )
        self.checkCodeAndMessage(submit_order_2, "PAYIN_WALLET_609", "wallet balance not enough")
        # ??????????????????
        b_time = time.time()
        query_order = None
        while time.time() - b_time < 60:
            query_order = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info["businessOrderNo"])
            if query_order["serviceChannelOrderId"] != "":
                break
            time.sleep(10)
        query_order_2 = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info_2["businessOrderNo"])
        self.assertEqual(query_order_2["status"], 0, "?????????????????????????????????")
        self.assertEqual(query_order["status"], PayOrder.PAY_SUCCESS.value, "???????????????????????????")

    def test_085_selectPaymentMethod_Wallet_secondTransFailed_accountBalanceEnough(self):
        """
        ???????????????????????????????????????2??????????????????????????????1??????????????????2????????????????????????????????????2???????????????
        """
        source_account = RPSData.user_roxe_account_a
        target_account = RPSData.user_roxe_account
        s_balance = self.client.getRoAccountBalance(source_account, "USD")
        self.client.logger.info(f"{source_account}????????????: {s_balance}")
        t_balance = self.client.getRoAccountBalance(target_account, "USD")
        self.client.logger.info(f"{target_account}????????????: {t_balance}")
        # ???1?????????
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
        # ????????????
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        # ??????????????????
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)

        # ??????????????????????????????
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("?????????????????????: {}".format(select_method))
        payment_amount = pay_order_info["businessAmount"] + select_method["currencyList"][0]["fee"]
        if ApiUtils.parseNumberDecimal(payment_amount) < payment_amount:
            payment_amount = ApiUtils.parseNumberDecimal(payment_amount, isUp=True)

        # ???2?????????
        pay_order_info_2 = pay_order_info.copy()
        pay_order_info_2["businessAmount"] = 10.35
        pay_order_info_2["businessOrderNo"] = "test" + str(int(time.time() * 1000))
        # ????????????
        pay_order_2 = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info_2)
        # ??????????????????
        methods_2 = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order_2)

        # ??????????????????????????????
        select_method_2 = [i for i in methods_2["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("?????????????????????: {}".format(select_method_2))
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

        self.client.logger.info(f"???1???????????????: {payment_amount}")
        submit_order = self.client.submitOrderPayInMethod(
            RPSData.user_id, RPSData.user_login_token, RPSData.app_key, pay_order, pay_order_info["currency"],
            select_method["type"], select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
            payment_amount, **fees
        )
        self.checkCodeAndMessage(submit_order)

        self.client.logger.info(f"???2???????????????: {payment_amount_2}")
        submit_order_2 = self.client.submitOrderPayInMethod(
            RPSData.user_id, RPSData.user_login_token, RPSData.app_key, pay_order_2, pay_order_info_2["currency"],
            select_method["type"], select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
            payment_amount_2, **fees
        )
        self.checkCodeAndMessage(submit_order_2)
        # ??????????????????
        b_time = time.time()
        query_order, query_order_2 = None, None
        while time.time() - b_time < 60:
            query_order = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info["businessOrderNo"])
            query_order_2 = self.client.queryPaymentOrder(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info_2["businessOrderNo"])
            if query_order["serviceChannelOrderId"] != "" and query_order_2["serviceChannelOrderId"] != "":
                break
            time.sleep(10)
        self.assertEqual(query_order["status"], PayOrder.PAY_SUCCESS.value, "???????????????????????????")
        self.assertEqual(query_order_2["status"], PayOrder.PAY_SUCCESS.value, "???????????????????????????")
        s_balance2 = self.client.getRoAccountBalance(source_account, "USD")
        self.client.logger.info(f"{source_account}????????????: {s_balance2}, ?????????: {s_balance2 - s_balance}")
        t_balance2 = self.client.getRoAccountBalance(target_account, "USD")
        self.client.logger.info(f"{target_account}????????????: {t_balance2}, ?????????: {t_balance2 - t_balance}")
        self.assertAlmostEqual(s_balance - s_balance2, pay_order_info["businessAmount"] + pay_order_info_2["businessAmount"], delta=0.001)
        self.assertAlmostEqual(t_balance2 - t_balance, pay_order_info["businessAmount"] + pay_order_info_2["businessAmount"], delta=0.001)

    def test_086_selectPaymentMethod_Wallet_sourceAccountIncorrect(self):
        """
        ????????????????????????????????????????????????????????????
        """
        source_account = "asdxxx"
        target_account = RPSData.user_roxe_account
        s_balance = self.client.getRoAccountBalance(source_account, "USD")
        self.client.logger.info(f"{source_account}????????????: {s_balance}")
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
        # ????????????
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        # ??????????????????
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)

        # ??????????????????????????????
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("?????????????????????: {}".format(select_method))
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
        ???????????????????????????????????????????????????????????????
        """
        source_account = RPSData.user_roxe_account
        target_account = "asdxxx"
        s_balance = self.client.getRoAccountBalance(source_account, "USD")
        self.client.logger.info(f"{source_account}????????????: {s_balance}")
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
        # ????????????
        pay_order = self.client.submitOrderPayIn(RPSData.app_key, RPSData.sign, int(time.time()), pay_order_info)
        # ??????????????????
        methods = self.client.queryOrderPayInMethod(RPSData.user_id, RPSData.user_login_token, pay_order)

        # ??????????????????????????????
        select_method = [i for i in methods["data"] if i["type"] == PaymentMethods.BALANCE.value][0]
        self.client.logger.info("?????????????????????: {}".format(select_method))

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

    # ??????????????????????????????

    @unittest.skip("?????????????????????????????????")
    def test_088_placePaymentOrder_deposit_ach_outsideDeduction_partOfAllowance(self):
        """
         ?????????????????????->ro, ??????????????????ach, ?????????????????????????????????
        """
        self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        # ???????????????
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
        # ??????????????????
        targetAccountBalance = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"??????????????????: {targetAccountBalance}")

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
            self.client.logger.info(f"??????????????????: {targetAccountBalance2}, ?????????: {targetAccountBalance2 - targetAccountBalance}")

            self.assertAlmostEqual(targetAccountBalance2 - targetAccountBalance, 0, msg="???????????????????????????????????????????????????", delta=0.1**7)

            self.assertTrue(pay_order["channelFee"] > 0, "???????????????????????????channelFee?????????")
        except Exception as e:
            flag = False
            self.client.logger.error(e.args, exc_info=True)
        finally:
            u_sql = f"update roxe_pay_in_allowance set rate={allowance_rate} where pay_method='{PaymentMethods.ACH.value}'"
            self.mysql.exec_sql_query(u_sql)
            assert flag, "??????????????????"

    def test_089_placePaymentOrder_deposit_ach_outsideDeduction_allowanceFeeExceedCouponMax(self):
        """
         ?????????????????????->ro, ??????????????????ach, ?????????????????????rps?????????????????????????????????????????????????????????????????????
        """
        self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        # ???????????????
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
        # ??????????????????
        targetAccountBalance = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"??????????????????: {targetAccountBalance}")

        pay_order, coupon_code = self.client.submitAchPayOrder(RPSData.user_roxe_account, pay_order_info["businessAmount"], pay_order_info["currency"], caseObj=self)
        self.assertEqual(pay_order["status"], PayOrder.PAY_SUCCESS.value)

        targetAccountBalance2 = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"??????????????????: {targetAccountBalance2}, ?????????: {targetAccountBalance2 - targetAccountBalance}")

        self.assertAlmostEqual(targetAccountBalance2 - targetAccountBalance, 0, msg="???????????????????????????????????????????????????", delta=0.1**7)

    def test_090_placePaymentOrder_deposit_ach_afterAllowanceEndDate(self):
        """
         ?????????????????????->ro, ??????????????????ach, ????????????????????????????????????????????????, ?????????????????????????????????
        """
        self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        # ???????????????
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
        # ??????????????????
        targetAccountBalance = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"??????????????????: {targetAccountBalance}")

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
            self.client.logger.info(f"??????????????????: {targetAccountBalance2}, ?????????: {targetAccountBalance2 - targetAccountBalance}")

            self.assertAlmostEqual(targetAccountBalance2 - targetAccountBalance, 0, msg="???????????????????????????????????????????????????", delta=0.1**7)

            self.assertTrue(pay_order["channelFee"] > 0, "????????????????????????")
        except Exception as e:
            flag = False
            self.client.logger.error(e.args, exc_info=True)
        finally:
            u_sql = f"update roxe_pay_in_allowance set end_date='{end_date}' where pay_method='{PaymentMethods.ACH.value}'"
            self.mysql.exec_sql_query(u_sql)
            assert flag, "??????????????????"

    def test_091_placePaymentOrder_deposit_ach_beforeAllowanceStartDate(self):
        """
         ?????????????????????->ro, ??????????????????ach, ????????????????????????????????????????????????, ?????????????????????????????????
        """
        self.client.bindAndVerifyAchAccount(RPSData.ach_account)
        # ???????????????
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
        # ??????????????????
        targetAccountBalance = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
        self.client.logger.info(f"??????????????????: {targetAccountBalance}")

        sql = f"select * from roxe_pay_in_allowance where pay_method='{PaymentMethods.ACH.value}'"
        db_allowance = self.mysql.exec_sql_query(sql)
        start_date = db_allowance[0]["startDate"]
        end_date = db_allowance[0]["endDate"]
        flag = True
        try:
            cur_time = datetime.datetime.utcnow()
            u_date = (cur_time + datetime.timedelta(minutes=3)).strftime("%y-%m-%d %H:%M:%S")
            self.client.logger.info(f"?????????start_date????????????: {u_date}")
            u_sql = f"update roxe_pay_in_allowance set start_date='{u_date}' where pay_method='{PaymentMethods.ACH.value}'"
            self.mysql.exec_sql_query(u_sql)
            time.sleep(1)

            pay_order, coupon_code = self.client.submitAchPayOrder(RPSData.user_roxe_account, pay_order_info["businessAmount"], pay_order_info["currency"], caseObj=self)
            self.assertEqual(pay_order["status"], PayOrder.PAY_SUCCESS.value)

            targetAccountBalance2 = self.client.getRoAccountBalance(pay_order_info["targetRoxeAccount"], pay_order_info["currency"])
            self.client.logger.info(f"??????????????????: {targetAccountBalance2}, ?????????: {targetAccountBalance2 - targetAccountBalance}")

            self.assertAlmostEqual(targetAccountBalance2 - targetAccountBalance, 0, msg="???????????????????????????????????????????????????", delta=0.1**7)
            self.assertTrue(pay_order["channelFee"] > 0, "????????????????????????")
        except Exception as e:
            flag = False
            self.client.logger.error(e.args, exc_info=True)
        finally:
            u_sql = f"update roxe_pay_in_allowance set start_date='{start_date}' where pay_method='{PaymentMethods.ACH.value}'"
            self.mysql.exec_sql_query(u_sql)
            assert flag, "??????????????????"
