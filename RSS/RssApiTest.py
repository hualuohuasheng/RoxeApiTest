# coding=utf-8
# author: Li MingLei
# date: 2021-08-27
import time
import json
import os
import unittest
from .RssApi import RSSApiClient
from roxe_libs.DBClient import Mysql
from roxe_libs import settings, ApiUtils
from roxe_libs.Global import Global
from roxe_libs.pub_function import loadYmlFile
from RPS.RpsApi import RPSApiClient
from RPS.RpsApi_old import RpsApiClient
from RPS.RpsApiTest import RPSData
import datetime
from functools import reduce


class RSSData:
    env = Global.getValue(settings.environment)
    cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), f"./Rss_{env}.yml"))
    _yaml_conf = loadYmlFile(cfg_path)

    host = _yaml_conf["host"]
    chain_host = _yaml_conf["chain_host"]

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

    custody_account = _yaml_conf["custody_account"]
    support_currency = _yaml_conf["support_currency"]
    out_currency = _yaml_conf["out_currency"]
    terrapay_out_currency = _yaml_conf["terrapay_out_currency"]

    # 100276/US
    sourceRoxeAccount = _yaml_conf["sourceRoxeAccount"]
    targetRoxeAccount = _yaml_conf["targetRoxeAccount"]
    userId_1 = _yaml_conf["userId_1"]
    token_1 = _yaml_conf["token_1"]

    out_bank_fields = _yaml_conf["out_bank_fields"]  # 出金必填字段
    out_bank_info = _yaml_conf["out_bank_info"]  # 银行卡信息
    if "terrapay_out_wallet_fields" in _yaml_conf:
        terrapay_out_wallet_fields = _yaml_conf["terrapay_out_wallet_fields"]  # 出金必填字段-钱包
        terrapay_out_wallet_info = _yaml_conf["terrapay_out_wallet_info"]  # 钱包信息
        terrapay_out_bank_fields = _yaml_conf["terrapay_out_bank_fields"]  # 出金必填字段-银行账户
        terrapay_out_bank_info = _yaml_conf["terrapay_out_bank_info"]  # 银行账户信息

    is_check_db = _yaml_conf["is_check_db"]
    sql_cfg = _yaml_conf["sql_cfg"]
    redis_cfg = _yaml_conf["redis_cfg"]

    is_inner = True


class RSSApiTest(unittest.TestCase):
    mysql = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = RSSApiClient(RSSData.host, RSSData.chain_host)
        cls.rpsClient = RPSApiClient(RPSData.host, RPSData.app_key, RPSData.secret)
        cls.rpsClient_old = RpsApiClient(RPSData.host, RPSData.chain_host, appKey="", sign="", user_id="", user_login_token="")

        if RSSData.is_check_db:
            cls.mysql = Mysql(RSSData.sql_cfg["mysql_host"], RSSData.sql_cfg["port"], RSSData.sql_cfg["user"],
                              RSSData.sql_cfg["password"], RSSData.sql_cfg["db"], True)
            cls.mysql.connect_database()

    @classmethod
    def tearDownClass(cls) -> None:
        if RSSData.is_check_db:
            cls.mysql.disconnect_database()

    def submitOutOrderFlow(self, outCurrency, outInfo, source_account, target_account, payAmount, payCurrency):
        """
        校验出金表单
        向中间账户转账，获取payOrderId
        提交提现表单
        查询订单信息及校验
        :param outCurrency:
        :param outInfo:
        :param source_account:
        :param target_account:
        :param payAmount:
        :param payCurrency:
        :return:
        """
        submitId = "test" + str(int(time.time() * 1000))
        # 校验出金表单
        check_res = self.client.checkPayoutForm(outCurrency, outInfo)
        self.checkStandardCodeMessage(check_res)
        self.assertTrue(check_res["data"])
        # 查询转账前出金账户资产
        account_balance = self.rpsClient_old.getRoAccountBalance(source_account, "USD")
        self.client.logger.info(f"赎回前的资产: {account_balance}")
        # 转账到中间账户，并获取提交订单所需参数payOrderId
        pay_order = self.rpsClient.rps_submit_order(RSSData.token_1, RSSData.userId_1, source_account, target_account, "debitCard", payAmount)
        payOrderId = pay_order["serviceChannelOrderId"]
        # 查询表单提交前在TerraPay通道方的中间账户金额
        TP_before_balance = self.client.terrapayQueryAccountBalance()
        # 提交提现表单
        form_info, request_body = self.client.submitOrderForm(submitId, payOrderId, payCurrency, payAmount, outCurrency,
                                                              outInfo)
        self.checkStandardCodeMessage(form_info)
        # 等待订单完成
        form_id = form_info["data"]["formId"]
        self.waitUntilTerraPayRedeemOrderCompleted(form_id)
        # 根据submitId查询订单信息
        form_info_1 = self.client.queryFormByClientID(submitId)
        time.sleep(2)
        self.checkStandardCodeMessage(form_info_1)
        self.assertEqual(form_info_1['data']['state'], 'finish')
        # 查询转账后出金账户资产
        account_balance2 = self.rpsClient_old.getRoAccountBalance(source_account, "USD")
        change_amount = round(account_balance - account_balance2, 2)
        self.client.logger.info(f"赎回后的资产: {account_balance2}, 变化了: {change_amount}")
        self.assertAlmostEqual(account_balance - account_balance2, payAmount, places=2, msg="账户资产变化与最初提交订单金额不符")
        self.checkOrderByTerrapay(form_info_1, outCurrency, payAmount, TP_before_balance)

    def checkStandardCodeMessage(self, msg, expect_code='0', expect_message='success'):
        """
        校验返回的标准code码和message
        :param msg: 接口返回的响应，json格式
        :param expect_code: 正常情况下，code码为0
        :param expect_message: 正确情况下，message为Success
        """
        self.assertEqual(msg["code"], expect_code, f"返回的code不正确: {msg}")
        self.assertEqual(msg["message"], expect_message, f"返回的code不正确: {msg}")

    def checkCurrencySupport(self, data_list):
        if RSSData.is_check_db:
            sql = "select * from rts-roxe.rts_node_router where out_node_code ='huuzj1hpycrx'"
            db_res = self.mysql.exec_sql_query(sql)
            list_a = [a["outCurrency"] for a in db_res]
            list_a.append("USD.ROXE")
            run_function = lambda x, y: x if y in x else x + [y]
            list_a_remove = reduce(run_function, [[], ] + list_a)
            data_out_list = [i["out"] for i in data_list for j in list_a if i["out"] == j]
            self.assertEqual(len(data_out_list), len(list_a_remove), msg="支持的出金币种返回不正确")
            data_roc_list = [b["roc"] for b in data_list if b["roc"] == "USD.ROXE"]
            self.assertEqual(len(data_roc_list), len(list_a_remove), msg="支持的roc币种返回不正确")
            data_pay_list = [c["pay"] for c in data_list if c["pay"] == "USD.ROXE"]
            data_pay_list.append("USD.US")
            self.assertEqual(len(data_pay_list), len(list_a_remove), msg="支持的入金币种返回不正确")


    def test_001_querySystemOnline(self):
        """
        查询系统信息
        """
        state = self.client.querySystemOnline()
        self.checkStandardCodeMessage(state)
        self.assertTrue(state["data"], "返回的系统状态不正确")

    def test_002_queryInnerCustodyAccountByRoxeCurrency(self):
        """
        查询入金账户 -- 币种为Ro币种
        币种为Ro类型时，返回的结果中账户地址应为一个Roxe Chain上的一个地址
        """
        currency = RSSData.support_currency[0]["ro"]
        account_info = self.client.queryCustodyAccount(currency)
        self.checkStandardCodeMessage(account_info)
        self.assertEqual(account_info["data"]["currency"], currency, "返回的currency不正确")
        self.assertEqual(account_info["data"]["account"], RSSData.custody_account, "返回的custodyAccount不正确")
        self.assertEqual(account_info["data"]["bankDetail"], None, "返回的bankDetail不正确")

    def test_003_queryInnerCustodyAccountByFiatCurrency(self):
        """
        查询入金账户 -- 币种为法币
        币种为法币时，返回的结果中bankDetail应有银行账户信息
        """
        currency = RSSData.support_currency[0]["fiat"]
        account_info = self.client.queryCustodyAccount(currency)
        self.checkStandardCodeMessage(account_info)
        self.assertEqual(account_info["data"]["currency"], currency, "返回的currency不正确")
        self.assertEqual(account_info["data"]["account"], None, "返回的custodyAccount不正确")
        self.assertIsNotNone(account_info["data"]["bankDetail"], "返回的bankDetail不正确")
        if RSSData.is_check_db:
            sql = "select * from rss_channel where inner_currency='{}'".format(currency)
            db_res = self.mysql.exec_sql_query(sql)
            self.assertEqual(account_info["data"]["bankDetail"], json.loads(db_res[0]["channelAddress"]),
                             json.loads(db_res[0]["channelAddress"]))

    def test_004_getQuantity_fiatToRo_innerAmount(self):
        """
        查询入金数量, 目前支持的入金方式: USD法币->RoUSD
        """
        in_currency = RSSData.support_currency[0]["fiat"]
        out_currency = RSSData.support_currency[0]["ro"]
        amount = 12.35
        account_info, params = self.client.getQuantity(in_currency, out_currency, amount, None)
        in_quantity, out_quantity, fee, fee_currency = self.client.getFee(self.mysql, params)
        self.checkStandardCodeMessage(account_info)
        self.assertEqual(account_info["data"]["innerQuantity"], in_quantity, "返回的innerQuantity不正确")
        self.assertEqual(account_info["data"]["innerCurrency"], in_currency, "返回的innerCurrency不正确")
        self.assertEqual(account_info["data"]["outerQuantity"], out_quantity, "返回的outerQuantity不正确")
        self.assertEqual(account_info["data"]["outerCurrency"], out_currency, "返回的outerCurrency不正确")
        self.assertEqual(account_info["data"]["feeQuantity"], fee, "返回的feeQuantity不正确")
        self.assertEqual(account_info["data"]["feeCurrency"], fee_currency, "返回的feeCurrency不正确")

    def test_005_getQuantity_fiatToRo_outAmount(self):
        """
        查询入金数量, 目前支持的入金方式: USD法币->RoUSD
        """
        in_currency = RSSData.support_currency[0]["fiat"]
        out_currency = RSSData.support_currency[0]["ro"]
        amount = 12.35
        account_info, params = self.client.getQuantity(in_currency, out_currency, None, amount)
        in_quantity, out_quantity, fee, fee_currency = self.client.getFee(self.mysql, params)
        self.checkStandardCodeMessage(account_info)
        self.assertAlmostEqual(account_info["data"]["innerQuantity"], in_quantity, msg="返回的innerQuantity不正确",
                               delta=0.001)
        self.assertEqual(account_info["data"]["innerCurrency"], in_currency, "返回的innerCurrency不正确")
        self.assertAlmostEqual(account_info["data"]["outerQuantity"], out_quantity, msg="返回的outerQuantity不正确",
                               delta=0.001)
        self.assertEqual(account_info["data"]["outerCurrency"], out_currency, "返回的outerCurrency不正确")
        self.assertEqual(account_info["data"]["feeQuantity"], fee, "返回的feeQuantity不正确")
        self.assertEqual(account_info["data"]["feeCurrency"], fee_currency, "返回的feeCurrency不正确")

    def test_006_getQuantity_roToFiat_innerAmount(self):
        """
        查询入金数量, 目前支持的入金方式: Ro->法币
        """
        in_currency = RSSData.support_currency[0]["ro"]
        amount = 12.35
        for out_currency in RSSData.out_currency:
            account_info, params = self.client.getQuantity(in_currency, out_currency, amount, None)
            in_quantity, out_quantity, fee, fee_currency = self.client.getFee(self.mysql, params)
            self.checkStandardCodeMessage(account_info)
            ep_dif = 0.001 if 'USD' == out_quantity else 2
            self.assertAlmostEqual(account_info["data"]["innerQuantity"], in_quantity, msg="返回的innerQuantity不正确",
                                   delta=ep_dif)
            self.assertAlmostEqual(account_info["data"]["outerQuantity"], out_quantity, msg="返回的outerQuantity不正确",
                                   delta=ep_dif)
            self.assertEqual(account_info["data"]["innerCurrency"], in_currency, "返回的innerCurrency不正确")
            self.assertEqual(account_info["data"]["outerCurrency"], out_currency, "返回的outerCurrency不正确")
            self.assertEqual(account_info["data"]["feeQuantity"], fee, "返回的feeQuantity不正确")
            self.assertEqual(account_info["data"]["feeCurrency"], fee_currency, "返回的feeCurrency不正确")

    def test_007_getQuantity_roToFiat_outAmount(self):
        """
        查询入金数量, 目前支持的入金方式: USD法币->RoUSD
        """
        in_currency = RSSData.support_currency[0]["ro"]
        amount = 12.35
        for out_currency in RSSData.out_currency:
            account_info, params = self.client.getQuantity(in_currency, out_currency, None, amount)
            in_quantity, out_quantity, fee, fee_currency = self.client.getFee(self.mysql, params)
            self.checkStandardCodeMessage(account_info)
            ep_dif = 0.001 if 'USD' == out_quantity else 2
            self.assertAlmostEqual(account_info["data"]["innerQuantity"], in_quantity, msg="返回的innerQuantity不正确",
                                   delta=ep_dif)
            self.assertEqual(account_info["data"]["innerCurrency"], in_currency, "返回的innerCurrency不正确")
            self.assertAlmostEqual(account_info["data"]["outerQuantity"], out_quantity, msg="返回的outerQuantity不正确",
                                   delta=ep_dif)
            self.assertEqual(account_info["data"]["outerCurrency"], out_currency, "返回的outerCurrency不正确")
            self.assertEqual(account_info["data"]["feeQuantity"], fee, "返回的feeQuantity不正确")
            self.assertEqual(account_info["data"]["feeCurrency"], fee_currency, "返回的feeCurrency不正确")

    def test_008_queryOuterBankMethod(self):
        """
        查询出金方式，目前只支持银行卡方式
        """
        # out_currency = RssData.support_currency[0]["fiat"]
        for out_currency in RSSData.out_currency:
            methods = self.client.queryOuterMethod(out_currency)
            self.checkStandardCodeMessage(methods)
            # RTS V2.0 暂时只支持一种出金类型
            self.assertEqual(methods["data"], ["bank"])

    def test_009_queryOuterAgent(self):
        """
        查询出金机构，未来支持
        """
        for out_currency in RSSData.out_currency:
            methods = self.client.queryOuterAgent(out_currency, "bank")
            self.checkStandardCodeMessage(methods)
            # RTS V2.0 暂时只支持一种出金类型
            if out_currency in ["USD", "MXN", ""]:
                self.assertEqual(methods["data"], [])
            else:
                # pass
                self.assertTrue(len(methods['data']) > 0)

    def test_010_queryOuterBankFields(self):
        """
        查询出金必填字段，目前只支持美元法币出金, 出金字段目前是在代码中写死的
        """
        for out_currency in RSSData.out_currency:
            methods = self.client.queryOuterMethod(out_currency)
            for m in methods["data"]:
                fields = self.client.queryOuterFields(out_currency, m)
                self.checkStandardCodeMessage(fields)
                expect_fields = []
                if m.upper() == "BANK":
                    expect_fields = RSSData.out_bank_fields[out_currency]
                self.assertEqual(len(fields["data"]), len(expect_fields))
                for field in fields["data"]:
                    expect_field = [i for i in expect_fields if i["name"] == field["name"]][0]
                    self.assertEqual(field, expect_field, "字段{}和预期不符".format(field["name"]))

    def test_011_checkOuterBankFields(self):
        """
        校验出金必填字段
        """
        for out_currency in RSSData.out_currency:
            out_info = RSSData.out_bank_info[out_currency]
            out_info['referenceId'] = 'test' + str(int(time.time() * 1000))
            check_res = self.client.checkOuterFields(out_currency, out_info)
            self.checkStandardCodeMessage(check_res)
            self.assertTrue(check_res["data"])

    def checkSettlementFormInfoMint(self, form_info, paymentId, request_body, db_name):
        if request_body:
            self.assertEqual(form_info["submitID"], request_body["submitID"])
            self.assertAlmostEqual(float(form_info["amount"]), float(request_body["amount"]), delta=0.001)
            self.assertEqual(form_info["currency"], request_body["currency"])
            self.assertEqual(form_info["outerInfo"], request_body["bankDetail"])
        if RSSData.is_check_db:
            sql = "select * from {}.rss_order where payment_id='{}'".format(db_name, paymentId)
            db_res = self.mysql.exec_sql_query(sql)
            self.assertEqual(form_info["formID"], db_res[0]["orderId"])
            self.assertEqual(form_info["submitID"], db_res[0]["clientId"])
            self.assertEqual(form_info["currency"], db_res[0]["innerCurrency"])
            self.assertEqual(form_info["amount"], db_res[0]["innerQuantity"])
            self.assertEqual(form_info["outerInfo"], json.loads(db_res[0]["outerInfo"]))
            self.assertIsNotNone(form_info["createdTime"])
            self.assertIsNotNone(form_info["updateTime"])
            if form_info["state"] in ["Submitted", "Processing"]:
                self.assertIsNone(form_info["actualAmount"])
                self.assertIsNone(form_info["txID"])
            else:
                self.assertAlmostEqual(float(form_info["actualAmount"]), float(form_info["amount"]), delta=0.001)
                self.assertIsNone(form_info["txID"], "交易完成后txID应不为None")

    def checkSettlementFormInfoRedeem(self, form_info, paymentId, request_body, outer_amount, db_name):
        if request_body:
            self.assertEqual(form_info["submitID"], request_body["submitID"])
            self.assertAlmostEqual(float(form_info["amount"]), float(request_body["amount"]), delta=0.001)
            self.assertEqual(form_info["currency"], request_body["currency"])
            self.assertEqual(form_info["outerInfo"], request_body["bankDetail"])
        if RSSData.is_check_db:
            sql = "select * from {}.rss_order where payment_id='{}'".format(db_name, paymentId)
            db_res = self.mysql.exec_sql_query(sql)
            self.assertEqual(form_info["formID"], db_res[0]["orderId"])
            self.assertEqual(form_info["submitID"], db_res[0]["clientId"])
            # self.assertEqual(form_info["paymentId"], db_res[0]["paymentId"])
            self.assertEqual(form_info["currency"], db_res[0]["innerCurrency"])
            self.assertEqual(form_info["amount"], db_res[0]["innerQuantity"])
            # self.assertEqual(form_info["outerInfo"], db_res[0]["outerInfo"])
            db_bank_info = json.loads(db_res[0]["outerInfo"])
            for b_k, b_v in form_info["outerInfo"].items():
                self.assertEqual(b_v, db_bank_info[b_k])
            self.assertIsNotNone(form_info["createdTime"])
            self.assertIsNotNone(form_info["updateTime"])
            if form_info["state"] in ["New", "Submitted"]:
                self.assertIsNone(form_info["actualAmount"])
                self.assertIsNone(form_info["txID"])
            elif form_info["state"] in ["Processing"]:
                self.assertEqual(form_info["actualAmount"], str(outer_amount))
                self.assertIsNotNone(form_info["txID"])
            else:
                self.assertEqual(form_info["actualAmount"], str(outer_amount))
                tx_sql = "select * from {}.rss_fiat_outer where outer_id='{}'".format(db_name, form_info["formID"])
                tx_res = self.mysql.exec_sql_query(tx_sql)
                self.assertEqual(form_info["txID"], tx_res[0]["outerId"], f"数据库结果: {tx_res}")
                self.assertIsNotNone(form_info["txID"], f"数据库结果: {tx_res}")

    def waitUntilOrderCompleted(self, submit_id, time_out=120, time_inner=20):
        b_time = time.time()
        while time.time() - b_time < time_out:
            q_order_info = self.client.queryFormBySubmitId(submit_id)
            if q_order_info["data"]["state"] == "Completed":
                break
            time.sleep(time_inner)

    def waitUntilRedeemOrderCompleted(self, submit_id, form_id, time_out=100, time_inner=10):
        sql = "select * from `roxe_backend_sysmngt`.roxe_pay_out_order where reference_id='{}'".format(form_id)
        b_time = time.time()
        while time.time() - b_time < time_out * 2:
            db_res = self.mysql.exec_sql_query(sql)
            if len(db_res) > 0:
                sql_2 = "update `roxe_backend_sysmngt`.roxe_pay_out_order set status='Success' where reference_id='{}'".format(
                    form_id)
                self.mysql.exec_sql_query(sql_2)
                break
            time.sleep(5)
        b_time = time.time()
        while time.time() - b_time < time_out:
            q_order_info = self.client.queryFormBySubmitId(submit_id)
            if q_order_info["data"]["state"] == "Submitted":
                self.client.logger.info("只提交了表单，未更新银行卡出金的状态")
                break
            if q_order_info["data"]["state"] == "Completed":
                break
            time.sleep(time_inner)

    def test_012_submitSettlementFormOfInner(self):
        """
        提交结算表单接口, 铸币, targetAccount必填, bankDetail不填
        """
        submit_id = "tes" + str(int(time.time() * 1000))
        currency = RSSData.support_currency[0]["fiat"]
        amount = 12.2
        target_account = RSSData.user_account
        account_balance = self.rpsClient.getRoAccountBalance(target_account, currency)
        self.client.logger.info(f"铸币前的账户资产: {account_balance}")
        # 提交rps订单
        self.client.logger.info("开始下rps订单")
        rps_order, coupon_code = self.rpsClient.submitAchPayOrder(target_account, amount,
                                                                  account_info=RPSData.ach_account)
        payment_id = rps_order["serviceChannelOrderId"]
        # third_fee = self.mysql.exec_sql_query("select third_channel_fee from roxe_pay_in_out.roxe_pay_in_order where id={payment_id}")[0]["thirdChannelFee"]
        # # 铸币金额 = 订单数量 + 优惠券数量 - 通道费用
        # mint_amount = round(amount + rps_order['channelFee'] - float(third_fee), 3)
        form_info, request_body = self.client.submitSettlementForm(submit_id, payment_id, currency, amount,
                                                                   {"receiverAddress": target_account},
                                                                   couponCode=coupon_code)
        self.checkStandardCodeMessage(form_info)
        self.waitUntilOrderCompleted(submit_id, 300)
        form_info_1 = self.client.queryFormBySubmitId(submit_id)
        self.checkStandardCodeMessage(form_info_1)
        self.checkSettlementFormInfoMint(form_info["data"], payment_id, request_body)
        # form_info_2 = self.client.queryFormBySubmitId(submit_id, currency)
        # for form_info in [form_info_1, form_info_2]:
        #     self.checkStandardCodeMessage(form_info)
        #     self.checkSettlementFormInfoMint(form_info["data"], payment_id, request_body)
        account_balance2 = self.rpsClient.getRoAccountBalance(target_account, currency)
        self.client.logger.info(f"铸币后的账户资产: {account_balance2}, 变化了: {account_balance2 - account_balance}")

        self.assertAlmostEqual(account_balance2 - account_balance, amount, msg="账户资产变化和支付订单数量不符", delta=0.1 ** 7)

    def test_013_submitSettlementFormOfOuter(self):
        """
        :提交结算表单接口, 赎回业务, bankDetail必填
        """
        submit_id = "test" + str(int(time.time() * 1000))
        ro_currency = RSSData.support_currency[0]["ro"]
        fiat_currency = RSSData.support_currency[0]["fiat"]
        amount = 12.34
        source_account = RSSData.user_account
        # target_account = self.client.queryCustodyAccount(ro_currency)["data"]["account"]
        target_account = RSSData.custody_account
        user_bank = RSSData.out_bank_info[fiat_currency].copy()
        user_bank['referenceId'] = 'test' + str(int(time.time() * 1000))
        account_info, a_body = self.client.getQuantity(ro_currency, fiat_currency, amount)
        account_balance = self.rpsClient.getRoAccountBalance(source_account, fiat_currency)
        self.client.logger.info(f"赎回前的资产: {account_balance}")
        # 转账到中间账户
        pay_order = self.rpsClient.submitPayOrderTransferToRoxeAccount(source_account, target_account, amount,
                                                                       fiat_currency, "transfer")
        payment_id = pay_order["serviceChannelOrderId"]
        form_info, request_body = self.client.submitSettlementForm(submit_id, payment_id, ro_currency, amount,
                                                                   user_bank)
        self.checkStandardCodeMessage(form_info)
        self.checkSettlementFormInfoRedeem(form_info["data"], payment_id, request_body,
                                           account_info["data"]["outerQuantity"])
        # 等待订单完成
        self.waitUntilRedeemOrderCompleted(submit_id, form_info["data"]["formID"])
        form_info_1 = self.client.queryFormBySubmitId(submit_id)
        self.checkStandardCodeMessage(form_info_1)
        self.checkSettlementFormInfoRedeem(form_info["data"], payment_id, request_body,
                                           account_info["data"]["outerQuantity"])
        # form_info_2 = self.client.queryFormBySubmitId(submit_id, ro_currency)
        # for form_info in [form_info_1, form_info_2]:
        #     self.checkStandardCodeMessage(form_info)
        #     self.checkSettlementFormInfoRedeem(form_info["data"], payment_id, request_body, account_info["data"]["outerQuantity"])

        account_balance2 = self.rpsClient.getRoAccountBalance(source_account, fiat_currency)
        self.client.logger.info(f"赎回后的资产: {account_balance2}, 变化了: {account_balance - account_balance2}")
        self.assertAlmostEqual(account_balance - account_balance2, amount + pay_order["channelFee"],
                               msg="账户资产变化和支付订单数量不符", delta=0.1 ** 7)

    # 异常场景

    def test_014_queryAccount_notSupportCurrency(self):
        """
        查询入金账户, 币种为不支持的币种, 如: CNY, CNY.ROXE
        """
        for currency in ["CNY", "CNY.ROXE"]:
            account_info = self.client.queryCustodyAccount(currency)
            self.checkStandardCodeMessage(account_info, "0x100001", "not support currency")
            self.assertIsNone(account_info["data"])

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_015_queryAccount_currencyLowerCase(self):
        """
        查询入金账户, 币种小写
        """
        for currency in [RSSData.support_currency[0]["ro"].lower(), RSSData.support_currency[0]["fiat"].lower()]:
            account_info = self.client.queryCustodyAccount(currency)
            self.checkStandardCodeMessage(account_info)
            self.assertEqual(account_info["data"]["currency"], currency, "返回的currency不正确")
            if currency.endswith("roxe"):
                # self.assertEqual(account_info["data"]["account"], RssData.custody_account, "返回的custodyAccount不正确")
                self.assertEqual(account_info["data"]["account"], None, "返回的custodyAccount不正确")
                self.assertEqual(account_info["data"]["bankDetail"], {}, "返回的bankDetail不正确")
            else:
                self.checkStandardCodeMessage(account_info)
                expect_account_info = self.mysql.exec_sql_query(
                    "select * from rss_channel where inner_currency='{}'".format(currency))
                self.assertEqual(account_info["data"]["account"], None, "返回的custodyAccount不正确")
                self.assertEqual(account_info["data"]["bankDetail"],
                                 json.loads(expect_account_info[0]['channelAddress']), "返回的bankDetail不正确")

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_016_queryAccount_currencyMixedCase(self):
        """
        查询入金账户, 币种大小写混合
        """
        for currency in ["Usd", "uSD", "Usd.Roxe", "usd.ROXE", "USD.roxe"]:
            account_info = self.client.queryCustodyAccount(currency)
            self.checkStandardCodeMessage(account_info)
            self.assertEqual(account_info["data"]["currency"], currency, "返回的currency不正确")
            if currency.lower().endswith("roxe"):
                # self.assertEqual(account_info["data"]["account"], RssData.custody_account, "返回的custodyAccount不正确")
                self.assertEqual(account_info["data"]["account"], None, "返回的custodyAccount不正确")
                self.assertEqual(account_info["data"]["bankDetail"], {}, "返回的bankDetail不正确")
            else:
                self.checkStandardCodeMessage(account_info)
                expect_account_info = self.mysql.exec_sql_query(
                    "select * from rss_channel where inner_currency='{}'".format(currency))
                self.assertEqual(account_info["data"]["account"], None, "返回的custodyAccount不正确")
                self.assertEqual(account_info["data"]["bankDetail"],
                                 json.loads(expect_account_info[0]['channelAddress']), "返回的bankDetail不正确")

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_017_queryQuantity_inCurrencyIsFiat_outAmountIllegal(self):
        """
        查询入金数量, USD法币->RoUSD, 出金数量不合法: 0, 负数, 字母, None, 空字符串
        """
        in_currency = RSSData.support_currency[0]["fiat"]
        out_currency = RSSData.support_currency[0]["ro"]

        for out_quantity in [None, "abc", "", -1, 0]:
            account_info = self.client.getQuantity(in_currency, out_currency, None, out_quantity)
            self.checkStandardCodeMessage(account_info, "", "")
            # self.checkStandardCodeMessage(account_info, "RSS100001", "Parameter error: Required BigDecimal parameter 'outerQuantity' is not present")
            # self.assertIsNone(account_info["data"])
        # account_info = self.client.getQuantity(in_currency, out_currency, out_quantity)
        # self.checkStandardCodeMessage(account_info, "RSS100002", "Unknown error")
        # self.assertIsNone(account_info["data"])
        #
        # out_quantity = ""
        # account_info = self.client.getQuantity(in_currency, out_currency, out_quantity)
        # self.checkStandardCodeMessage(account_info, "RSS100002", "Unknown error")
        # self.assertIsNone(account_info["data"])
        #
        # out_quantity = 0
        # account_info = self.client.getQuantity(in_currency, out_currency, out_quantity)
        # self.checkStandardCodeMessage(account_info)
        # self.assertEqual(account_info["data"]["innerQuantity"], 0)
        #
        # out_quantity = -1
        # account_info = self.client.getQuantity(in_currency, out_currency, out_quantity)
        # self.checkStandardCodeMessage(account_info, "RSS100002", "Unknown error")
        # self.assertIsNone(account_info["data"])

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_018_queryQuantity_inCurrencyIsFiat_outAmountDecimalExceedSix(self):
        """
        查询入金数量, USD法币->RoUSD, 出金数量的小数位数不合法，超过合约规定的6位
        """
        in_currency = RSSData.support_currency[0]["fiat"]
        out_currency = RSSData.support_currency[0]["ro"]

        out_quantity = 10.1234567
        account_info, params = self.client.getQuantity(in_currency, out_currency, out_quantity)
        self.checkStandardCodeMessage(account_info)
        self.assertEqual(len(str(account_info["data"]["innerQuantity"]).split(".")[-1]), 2, "法币保留2位小数")
        self.assertEqual(account_info["data"]["outerQuantity"], out_quantity, "指定的出金数量应和入参一致")
        self.assertTrue(account_info["data"]["innerQuantity"] > out_quantity)

        in_quantity, fee, fee_currency = self.client.getFee(self.mysql, params)
        self.assertEqual(account_info["data"]["innerCurrency"], in_currency, "返回的innerCurrency不正确")
        self.assertEqual(account_info["data"]["outerQuantity"], out_quantity, "返回的outerQuantity不正确")
        self.assertEqual(account_info["data"]["outerCurrency"], out_currency, "返回的outerCurrency不正确")
        self.assertEqual(account_info["data"]["bankCurrency"], in_currency.upper(), "返回的bankCurrency不正确")
        self.assertEqual(account_info["data"]["trMinAmount"], 0, "返回的bankMin不正确")
        self.assertEqual(account_info["data"]["trMaxAmount"], 0, "返回的bankMax不正确")
        # 铸币是没有费用的
        self.assertEqual(account_info["data"]["feeQuantity"], fee, "返回的feeQuantity不正确")
        self.assertEqual(account_info["data"]["feeCurrency"], fee_currency.upper(), "返回的feeCurrency不正确")

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_019_queryQuantity_inCurrencyIsFiat_currencyLowerCase(self):
        """
        查询入金数量, USD法币->RoUSD, 币种均小写
        """
        in_currency = RSSData.support_currency[0]["fiat"].lower()
        out_currency = RSSData.support_currency[0]["ro"].lower()

        out_quantity = 10.12
        account_info, params = self.client.getQuantity(in_currency, out_currency, out_quantity)
        in_quantity, fee, fee_currency = self.client.getFee(self.mysql, params)
        self.checkStandardCodeMessage(account_info)
        self.assertEqual(account_info["data"]["innerQuantity"], in_quantity, "返回的innerQuantity不正确")
        self.assertEqual(account_info["data"]["innerCurrency"], in_currency, "返回的innerCurrency不正确")
        self.assertEqual(account_info["data"]["outerQuantity"], out_quantity, "返回的outerQuantity不正确")
        self.assertEqual(account_info["data"]["outerCurrency"], out_currency, "返回的outerCurrency不正确")
        self.assertEqual(account_info["data"]["bankCurrency"], in_currency.upper(), "返回的bankCurrency不正确")
        self.assertEqual(account_info["data"]["trMinAmount"], 0, "返回的bankMin不正确")
        self.assertEqual(account_info["data"]["trMaxAmount"], 0, "返回的bankMax不正确")
        # 铸币是没有费用的
        self.assertEqual(account_info["data"]["feeQuantity"], fee, "返回的feeQuantity不正确")
        self.assertEqual(account_info["data"]["feeCurrency"], fee_currency.upper(), "返回的feeCurrency不正确")

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_020_queryQuantity_inCurrencyIsFiat_currencyMixedCase(self):
        """
        查询入金数量, USD法币->RoUSD, 币种大小写混合: Usd -> Usd.Roxe, uSD -> uSD.rOXE
        """
        mixed_currencies = [["Usd", "Usd.Roxe"], ["uSD", "uSD.rOXE"], ["uSd", "uSd.RoXe"]]
        out_quantity = 10.12
        for c in mixed_currencies:
            in_currency = c[0]
            out_currency = c[1]
            account_info, params = self.client.getQuantity(in_currency, out_currency, out_quantity)
            in_quantity, fee, fee_currency = self.client.getFee(self.mysql, params)
            self.checkStandardCodeMessage(account_info)
            self.assertEqual(account_info["data"]["innerQuantity"], in_quantity, "返回的innerQuantity不正确")
            self.assertEqual(account_info["data"]["innerCurrency"], in_currency, "返回的innerCurrency不正确")
            self.assertEqual(account_info["data"]["outerQuantity"], out_quantity, "返回的outerQuantity不正确")
            self.assertEqual(account_info["data"]["outerCurrency"], out_currency, "返回的outerCurrency不正确")
            self.assertEqual(account_info["data"]["bankCurrency"], in_currency.upper(), "返回的bankCurrency不正确")
            self.assertEqual(account_info["data"]["trMinAmount"], 0, "返回的bankMin不正确")
            self.assertEqual(account_info["data"]["trMaxAmount"], 0, "返回的bankMax不正确")
            # 铸币是没有费用的
            self.assertEqual(account_info["data"]["feeQuantity"], fee, "返回的feeQuantity不正确")
            self.assertEqual(account_info["data"]["feeCurrency"], fee_currency.upper(), "返回的feeCurrency不正确")

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_021_queryQuantity_inCurrencyIsFiat_missingParameter(self):
        """
        查询入金数量, USD法币->RoUSD, 缺少参数
        """
        missing_param = ["innerCurrency", "outerCurrency", "outerQuantity"]
        missing_type = ["String", "String", "BigDecimal"]
        in_currency = RSSData.support_currency[0]["fiat"]
        out_currency = RSSData.support_currency[0]["ro"]
        out_quantity = 10.12
        for i, m_p in enumerate(missing_param):
            account_info = self.client.getQuantity(in_currency, out_currency, out_quantity, popKey=m_p)
            self.checkStandardCodeMessage(account_info, "RSS100001",
                                          f"Parameter error: Required {missing_type[i]} parameter '{m_p}' is not present")
            self.assertIsNone(account_info["data"])

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_022_queryQuantity_outCurrencyIsFiat_inAmountIllegal(self):
        """
        查询出金数量, RoUSD->USD法币, 入金数量不合法: 0, 负数, 字母, None, 空字符串
        """
        in_currency = RSSData.support_currency[0]["ro"]
        out_currency = RSSData.support_currency[0]["fiat"]

        in_quantity = None
        account_info = self.client.getQuantity(in_currency, out_currency, in_quantity)
        self.checkStandardCodeMessage(account_info, "RSS100001",
                                      "Parameter error: Required BigDecimal parameter 'innerQuantity' is not present")
        self.assertIsNone(account_info["data"])

        in_quantity = "abc"
        account_info = self.client.getQuantity(in_currency, out_currency, in_quantity)
        self.checkStandardCodeMessage(account_info, "RSS100002", "Unknown error")
        self.assertIsNone(account_info["data"])

        in_quantity = ""
        account_info = self.client.getQuantity(in_currency, out_currency, in_quantity)
        self.checkStandardCodeMessage(account_info, "RSS100002", "Unknown error")
        self.assertIsNone(account_info["data"])

        in_quantity = -1
        account_info = self.client.getQuantity(in_currency, out_currency, in_quantity)
        self.checkStandardCodeMessage(account_info, "RSS100002", "Unknown error")
        self.assertIsNone(account_info["data"])

        in_quantity = 0
        account_info = self.client.getQuantity(in_currency, out_currency, in_quantity)
        self.checkStandardCodeMessage(account_info, "RSS100002", "Unknown error")
        self.assertIsNone(account_info["data"])

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_023_queryQuantity_outCurrencyIsFiat_inAmountDecimalExceedSix(self):
        """
        查询出金数量, RoUSD->USD法币, 入金数量的小数位数不合法，超过合约规定的6位
        """
        in_currency = RSSData.support_currency[0]["ro"]
        out_currency = RSSData.support_currency[0]["fiat"]

        in_quantity = 10.1234567
        account_info = self.client.getQuantity(in_currency, out_currency, in_quantity)
        self.checkStandardCodeMessage(account_info)

        out_quantity, fee, fee_currency = self.client.queryOuterFeeByRouter(self.mysql, in_currency, out_currency,
                                                                            in_quantity)
        self.assertEqual(account_info["data"]["innerQuantity"], in_quantity, "返回的innerQuantity不正确")
        self.assertEqual(account_info["data"]["innerCurrency"], in_currency, "返回的innerCurrency不正确")
        self.assertAlmostEqual(account_info["data"]["outerQuantity"], ApiUtils.parseNumberDecimal(out_quantity),
                               msg="返回的outerQuantity不正确", delta=0.1 ** 7)
        self.assertEqual(account_info["data"]["outerCurrency"], out_currency, "返回的outerCurrency不正确")
        self.assertEqual(account_info["data"]["bankCurrency"], out_currency, "返回的bankCurrency不正确")
        self.assertEqual(account_info["data"]["trMinAmount"], 0, "返回的bankMin不正确")
        self.assertEqual(account_info["data"]["trMaxAmount"], 0, "返回的bankMax不正确")
        self.assertEqual(account_info["data"]["feeQuantity"], ApiUtils.parseNumberDecimal(fee, isUp=True),
                         "返回的feeQuantity不正确")
        self.assertEqual(account_info["data"]["feeCurrency"], fee_currency, "返回的feeCurrency不正确")

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_024_queryQuantity_outCurrencyIsFiat_currencyLowerCase(self):
        """
        查询出金数量, RoUSD->USD法币, 币种均小写
        """
        in_currency = RSSData.support_currency[0]["ro"].lower()
        out_currency = RSSData.support_currency[0]["fiat"].lower()

        in_quantity = 10.12
        account_info = self.client.getQuantity(in_currency, out_currency, in_quantity)
        self.checkStandardCodeMessage(account_info)

        out_quantity, fee, fee_currency = self.client.queryOuterFeeByRouter(self.mysql, in_currency, out_currency,
                                                                            in_quantity)
        self.assertEqual(account_info["data"]["innerQuantity"], in_quantity, "返回的innerQuantity不正确")
        self.assertEqual(account_info["data"]["innerCurrency"], in_currency, "返回的innerCurrency不正确")
        self.assertAlmostEqual(account_info["data"]["outerQuantity"], ApiUtils.parseNumberDecimal(out_quantity),
                               msg="返回的outerQuantity不正确", delta=0.1 ** 7)
        self.assertEqual(account_info["data"]["outerCurrency"], out_currency, "返回的outerCurrency不正确")
        self.assertEqual(account_info["data"]["bankCurrency"], out_currency.upper(), "返回的bankCurrency不正确")
        self.assertEqual(account_info["data"]["trMinAmount"], 0, "返回的bankMin不正确")
        self.assertEqual(account_info["data"]["trMaxAmount"], 0, "返回的bankMax不正确")
        self.assertEqual(account_info["data"]["feeQuantity"], ApiUtils.parseNumberDecimal(fee, isUp=True),
                         "返回的feeQuantity不正确")
        self.assertEqual(account_info["data"]["feeCurrency"], fee_currency.upper(), "返回的feeCurrency不正确")

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_025_queryQuantity_outCurrencyIsFiat_currencyMixedCase(self):
        """
        查询出金数量, RoUSD->USD法币, 币种大小写混合: Usd.Roxe -> Usd, uSD.rOXE -> uSD
        """
        mixed_currencies = [["Usd", "Usd.Roxe"], ["uSD", "uSD.rOXE"], ["uSd", "uSd.RoXe"]]
        in_quantity = 10.12
        for c in mixed_currencies:
            in_currency = c[1]
            out_currency = c[0]
            account_info = self.client.getQuantity(in_currency, out_currency, in_quantity)
            self.checkStandardCodeMessage(account_info)

            out_quantity, fee, fee_currency = self.client.queryOuterFeeByRouter(self.mysql, in_currency, out_currency,
                                                                                in_quantity)
            self.assertEqual(account_info["data"]["innerQuantity"], in_quantity, "返回的innerQuantity不正确")
            self.assertEqual(account_info["data"]["innerCurrency"], in_currency, "返回的innerCurrency不正确")
            self.assertAlmostEqual(account_info["data"]["outerQuantity"], ApiUtils.parseNumberDecimal(out_quantity),
                                   msg="返回的outerQuantity不正确", delta=0.1 ** 7)
            self.assertEqual(account_info["data"]["outerCurrency"], out_currency, "返回的outerCurrency不正确")
            self.assertEqual(account_info["data"]["bankCurrency"], out_currency.upper(), "返回的bankCurrency不正确")
            self.assertEqual(account_info["data"]["trMinAmount"], 0, "返回的bankMin不正确")
            self.assertEqual(account_info["data"]["trMaxAmount"], 0, "返回的bankMax不正确")
            self.assertEqual(account_info["data"]["feeQuantity"], ApiUtils.parseNumberDecimal(fee, isUp=True),
                             "返回的feeQuantity不正确")
            self.assertEqual(account_info["data"]["feeCurrency"], fee_currency.upper(), "返回的feeCurrency不正确")

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_026_queryQuantity_outCurrencyIsFiat_missingParameter(self):
        """
        查询出金数量, RoUSD->USD法币, 缺少参数
        """
        missing_param = ["innerCurrency", "outerCurrency", "innerQuantity"]
        missing_type = ["String", "String", "BigDecimal"]
        in_currency = RSSData.support_currency[0]["ro"]
        out_currency = RSSData.support_currency[0]["fiat"]
        in_quantity = 10.12
        for i, m_p in enumerate(missing_param):
            account_info = self.client.getQuantity(in_currency, out_currency, in_quantity, popKey=m_p)
            self.checkStandardCodeMessage(account_info, "RSS100001",
                                          f"Parameter error: Required {missing_type[i]} parameter '{m_p}' is not present")
            self.assertIsNone(account_info["data"])

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_027_queryOuterBankMethod_notSupportCurrency(self):
        """
        查询出金方式，查询不支持的币种: CNY, 空字符串, None, USD.ROXE
        """
        out_currency = "CNY"
        methods = self.client.queryOuterMethod(out_currency)
        self.checkStandardCodeMessage(methods, "RSS100004", "Currency not supported")
        self.assertIsNone(methods["data"])

        out_currency = "USD.ROXE"
        methods = self.client.queryOuterMethod(out_currency)
        self.checkStandardCodeMessage(methods, "RSS100004", "Currency not supported")
        self.assertIsNone(methods["data"])

        out_currency = ""
        methods = self.client.queryOuterMethod(out_currency)
        self.checkStandardCodeMessage(methods, "RSS100004", "Currency not supported")
        self.assertIsNone(methods["data"])

        out_currency = None
        methods = self.client.queryOuterMethod(out_currency)
        self.checkStandardCodeMessage(methods, "RSS100001",
                                      "Parameter error: Required String parameter 'currency' is not present")
        self.assertIsNone(methods["data"])

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_028_queryOuterBankMethod_currencyLowerCase(self):
        """
        查询出金方式，币种小写
        """
        out_currency = RSSData.support_currency[0]["fiat"].lower()
        methods = self.client.queryOuterMethod(out_currency)
        self.checkStandardCodeMessage(methods)
        # RTS V2.0 暂时只支持一种出金类型
        self.assertEqual(methods["data"], ["BANK"])

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_029_queryOuterBankMethod_currencyMixedCase(self):
        """
        查询出金方式，币种大小写混合
        """
        for out_currency in ["Usd", "uSD"]:
            methods = self.client.queryOuterMethod(out_currency)
            self.checkStandardCodeMessage(methods)
            # RTS V2.0 暂时只支持一种出金类型
            self.assertEqual(methods["data"], ["BANK"])

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_030_queryOuterBankFields_notSupportCurrency(self):
        """
        查询出金必填字段，查询不支持的币种: CNY, 空，None，其他
        """
        for out_currency in ["CNY", "a", "", None]:
            fields = self.client.queryOuterFields(out_currency, "BANK")
            if out_currency is None:
                self.checkStandardCodeMessage(fields, "RSS100001",
                                              "Parameter error: Required String parameter 'currency' is not present")
            else:
                self.checkStandardCodeMessage(fields, "RSS100004", "Currency not supported")
            self.assertIsNone(fields["data"])

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_031_queryOuterBankFields_notSupportOuterMethod(self):
        """
        查询出金必填字段，查询不支持的出金方式: CASH_PICK_UP, 空，None
        """
        out_currency = RSSData.support_currency[0]["fiat"]
        for method in ["CASH_PICK_UP", "", None]:
            fields = self.client.queryOuterFields(out_currency, method)
            if method is None:
                self.checkStandardCodeMessage(fields, "RSS100001",
                                              "Parameter error: Required PayoutMethodEnum parameter 'payoutMethod' is not present")
            elif method == "":
                self.checkStandardCodeMessage(fields, "RSS000005", "Call bank error: null")
            else:
                self.checkStandardCodeMessage(fields, "RSS000005",
                                              "Call bank error: paramter error : unsupported payoutMethod and currencies and country")
            self.assertIsNone(fields["data"])

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_032_queryOuterBankFields_currencyLowerCase(self):
        """
        查询出金必填字段，币种小写
        """
        out_currency = RSSData.support_currency[0]["fiat"].lower()
        fields = self.client.queryOuterFields(out_currency, "BANK")
        self.checkStandardCodeMessage(fields)
        expect_fields = RSSData.out_bank_fields[out_currency]
        self.assertEqual(len(fields["data"]), len(expect_fields))
        for field in fields["data"]:
            expect_field = [i for i in expect_fields if i["name"] == field["name"]][0]
            self.assertEqual(field, expect_field, "字段{}和预期不符".format(field["name"]))

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_033_queryOuterBankFields_currencyMixerCase(self):
        """
        查询出金必填字段，币种大小写混合
        """
        expect_fields = RSSData.out_bank_fields["USD"]
        for out_currency in ["Usd", "uSD"]:
            fields = self.client.queryOuterFields(out_currency, "BANK")
            self.checkStandardCodeMessage(fields)
            self.assertEqual(len(fields["data"]), len(expect_fields))
            for field in fields["data"]:
                expect_field = [i for i in expect_fields if i["name"] == field["name"]][0]
                self.assertEqual(field, expect_field, "字段{}和预期不符".format(field["name"]))

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_034_queryOuterBankFields_outerMethodLowerCase(self):
        """
        查询出金必填字段，出金方式小写
        """
        out_currency = RSSData.support_currency[0]["fiat"]
        fields = self.client.queryOuterFields(out_currency, "bank")
        self.checkStandardCodeMessage(fields, "RSS100002", "Unknown error")
        self.assertIsNone(fields["data"])

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_035_queryOuterBankFields_outerMethodMixerCase(self):
        """
        查询出金必填字段，币种大小写混合
        """
        out_currency = RSSData.support_currency[0]["fiat"]
        for m in ["Bank", "bANK"]:
            fields = self.client.queryOuterFields(out_currency, m)
            self.checkStandardCodeMessage(fields, "RSS100002", "Unknown error")
            self.assertIsNone(fields["data"])

    def test_036_checkOuterBankFields_currencyNotMatchOutInfo(self):
        """
        校验出金必填字段, 币种和出金字段信息不匹配: CNY, None, 其他
        """
        out_info = RSSData.out_bank_info["USD"].copy()
        for currency in ["CMY", "abc", None]:
            check_res = self.client.checkOuterFields(currency, out_info)
            if currency is None:
                # self.checkStandardCodeMessage(check_res, "RSS100001", "Parameter error: currency is empty")
                self.checkStandardCodeMessage(check_res, "0x100001", "currency is empty")
            else:
                # self.checkStandardCodeMessage(check_res, "RSS100004", "Currency not supported")
                self.checkStandardCodeMessage(check_res, "0x100001", "not support currency")
            self.assertIsNone(check_res["data"])

    # @unittest.skipIf(RssData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_037_checkOuterBankFields_missingCurrency(self):
        """
        校验出金必填字段, 缺少currency字段: CNY, None, 其他
        """
        out_info = RSSData.out_bank_info["USD"].copy()
        check_res = self.client.checkOuterFields("USD", out_info, popKey="currency")
        # self.checkStandardCodeMessage(check_res, "RSS100001", "Parameter error: currency is empty")
        self.checkStandardCodeMessage(check_res, "0x100001", "currency is empty")
        self.assertIsNone(check_res["data"])

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_038_checkOuterBankFields_currencyLowerCase(self):
        """
        校验出金必填字段, currency字段小写
        """
        out_info = RSSData.out_bank_info["USD"].copy()
        check_res = self.client.checkOuterFields("usd", out_info)
        self.checkStandardCodeMessage(check_res)
        self.assertTrue(check_res["data"])

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_039_checkOuterBankFields_currencyMixerCase(self):
        """
        校验出金必填字段, currency字段混合大小写
        """
        out_info = RSSData.out_bank_info["USD"].copy()
        for currency in ["Usd", "uSD"]:
            check_res = self.client.checkOuterFields(currency, out_info)
            self.checkStandardCodeMessage(check_res)
            self.assertTrue(check_res["data"])

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_040_checkOuterBankFields_outInfoMissingField(self):
        """
        校验出金必填字段, 出金必填字段缺少某一字段时
        """
        for field in RSSData.out_bank_fields["USD"]:
            self.client.logger.info(f"缺少字段: {field['name']}")
            out_info = RSSData.out_bank_info["USD"].copy()
            out_info.pop(field['name'])
            check_res = self.client.checkOuterFields("USD", out_info)
            if field['name'] == "receiverFirstName":
                self.checkStandardCodeMessage(check_res, "RSS000005", "Call bank error: receiver name cannot be empty")
            elif field['name'] == "accountNumber":
                self.checkStandardCodeMessage(check_res, "RSS000005", "Call bank error: account number cannot be empty")
            elif field['name'] == "routingNumber":
                self.checkStandardCodeMessage(check_res, "RSS000005", "Call bank error: routing number cannot be empty")
            elif field['name'] == "accountType":
                self.checkStandardCodeMessage(check_res, "RSS000005",
                                              "Call bank error: receiver account type cannot be empty")
            elif field['name'] == "receiverCurrency":
                self.checkStandardCodeMessage(check_res, "RSS000005",
                                              "Call bank error: receiver currency cannot be empty")
            elif field['name'] == "payOutMethod":
                self.checkStandardCodeMessage(check_res, "RSS000005", "Call bank error: payout method cannot be empty")
            else:
                self.checkStandardCodeMessage(check_res, "RSS000005",
                                              "Call bank error: recipient country cannot be empty")
            self.assertIsNone(check_res["data"])

    def test_041_submitSettlementFormOfInner_submitIdRepeat(self):
        """
        提交结算表单接口, 铸币, submitId重复
        """
        submit_id = "tes" + str(int(time.time() * 1000))
        currency = RSSData.support_currency[0]["fiat"]
        amount = 10
        target_account = RSSData.user_account
        account_balance = self.rpsClient.getRoAccountBalance(target_account, currency)
        self.client.logger.info(f"铸币前的账户资产: {account_balance}")
        # 提交rps订单
        self.client.logger.info("开始下rps订单")
        rps_order, coupon_code = self.rpsClient.submitAchPayOrder(target_account, amount,
                                                                  account_info=RPSData.ach_account)
        payment_id = rps_order["serviceChannelOrderId"]

        form_info, request_body = self.client.submitSettlementForm(submit_id, payment_id, currency, amount,
                                                                   {"receiverAddress": target_account},
                                                                   couponCode=coupon_code)
        form_info = self.client.queryFormBySubmitId(submit_id)
        self.checkStandardCodeMessage(form_info)
        self.checkSettlementFormInfoMint(form_info["data"], payment_id, request_body)
        self.waitUntilOrderCompleted(submit_id)

        account_balance2 = self.rpsClient.getRoAccountBalance(target_account, currency)
        self.client.logger.info(f"铸币后的账户资产: {account_balance2}, 变化了: {account_balance2 - account_balance}")
        self.assertAlmostEqual(account_balance2 - account_balance, amount, msg="账户资产变化和支付订单数量不符", delta=0.1 ** 7)

        form_info, request_body = self.client.submitSettlementForm(submit_id, payment_id + "a", currency, amount,
                                                                   {"receiverAddress": target_account},
                                                                   couponCode=coupon_code)
        self.checkStandardCodeMessage(form_info, "RSS100006", "Duplicate business order ID")
        self.assertIsNone(form_info["data"])

    def test_042_submitSettlementFormOfInner_paymentOrderIdRepeat(self):
        """
        提交结算表单接口, 铸币, 支付订单id重复
        """
        submit_id = "tes" + str(int(time.time() * 1000))
        currency = RSSData.support_currency[0]["fiat"]
        amount = 10
        target_account = RSSData.user_account
        account_balance = self.rpsClient.getRoAccountBalance(target_account, currency)
        self.client.logger.info(f"铸币前的账户资产: {account_balance}")
        # 提交rps订单
        self.client.logger.info("开始下rps订单")
        rps_order, coupon_code = self.rpsClient.submitAchPayOrder(target_account, amount,
                                                                  account_info=RPSData.ach_account)
        payment_id = rps_order["serviceChannelOrderId"]

        form_info, request_body = self.client.submitSettlementForm(submit_id, payment_id, currency, amount,
                                                                   {"receiverAddress": target_account})
        self.client.logger.info(f"第1次提交结算表单: {form_info}")
        submit_id = "tes" + str(int(time.time() * 1000))
        form_info, request_body = self.client.submitSettlementForm(submit_id, payment_id, currency, amount,
                                                                   {"receiverAddress": target_account})
        self.checkStandardCodeMessage(form_info, "RSS100005", "Duplicate payment order ID")
        self.assertIsNone(form_info["data"])

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_043_submitSettlementFormOfInner_currencyLowerCase(self):
        """
        提交结算表单接口, 铸币, 币种小写
        """
        submit_id = "tes" + str(int(time.time() * 1000))
        currency = RSSData.support_currency[0]["fiat"]
        amount = 10
        target_account = RSSData.user_account
        account_balance = self.rpsClient.getRoAccountBalance(target_account, currency)
        self.client.logger.info(f"铸币前的账户资产: {account_balance}")
        # 提交rps订单
        self.client.logger.info("开始下rps订单")
        rps_order, coupon_code = self.rpsClient.submitAchPayOrder(target_account, amount,
                                                                  account_info=RPSData.ach_account)
        payment_id = rps_order["serviceChannelOrderId"]

        form_info, request_body = self.client.submitSettlementForm(submit_id, payment_id, currency.lower(), amount,
                                                                   {"receiverAddress": target_account})
        form_info = self.client.queryFormBySubmitId(form_info["data"]["formID"])
        self.checkStandardCodeMessage(form_info)
        self.checkSettlementFormInfoMint(form_info["data"], payment_id, request_body)
        self.waitUntilOrderCompleted(submit_id)

        account_balance2 = self.rpsClient.getRoAccountBalance(target_account, currency)
        self.client.logger.info(f"铸币后的账户资产: {account_balance2}, 变化了: {account_balance2 - account_balance}")
        self.assertAlmostEqual(account_balance2 - account_balance, amount, msg="账户资产变化和支付订单数量不符", delta=0.1 ** 7)

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_044_submitSettlementFormOfInner_currencyMixerCase(self):
        """
        提交结算表单接口, 铸币, 币种大小写混合
        """
        submit_id = "tes" + str(int(time.time() * 1000))
        currency = RSSData.support_currency[0]["fiat"]
        amount = 10
        target_account = RSSData.user_account
        account_balance = self.rpsClient.getRoAccountBalance(target_account, currency)
        self.client.logger.info(f"铸币前的账户资产: {account_balance}")
        # 提交rps订单
        self.client.logger.info("开始下rps订单")
        rps_order, coupon_code = self.rpsClient.submitAchPayOrder(target_account, amount,
                                                                  account_info=RPSData.ach_account)
        payment_id = rps_order["serviceChannelOrderId"]

        form_info, request_body = self.client.submitSettlementForm(submit_id, payment_id, currency.title(), amount,
                                                                   {"receiverAddress": target_account})
        form_info = self.client.queryFormBySubmitId(form_info["data"]["formID"])
        self.checkStandardCodeMessage(form_info)
        self.checkSettlementFormInfoMint(form_info["data"], payment_id, request_body)
        self.waitUntilOrderCompleted(submit_id)

        account_balance2 = self.rpsClient.getRoAccountBalance(target_account, currency)
        self.client.logger.info(f"铸币后的账户资产: {account_balance2}, 变化了: {account_balance2 - account_balance}")
        self.assertAlmostEqual(account_balance2 - account_balance, amount, msg="账户资产变化和支付订单数量不符", delta=0.1 ** 7)

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_045_submitSettlementFormOfInner_missingParameter(self):
        """
        提交结算表单接口, 铸币, 缺少某一参数
        """
        submit_id = "tes" + str(int(time.time() * 1000))
        currency = RSSData.support_currency[0]["fiat"]
        amount = 10
        target_account = RSSData.user_account
        account_balance = self.rpsClient.getRoAccountBalance(target_account, currency)
        self.client.logger.info(f"铸币前的账户资产: {account_balance}")
        # 提交rps订单
        self.client.logger.info("开始下rps订单")
        rps_order, coupon_code = self.rpsClient.submitAchPayOrder(target_account, amount,
                                                                  account_info=RPSData.ach_account)
        payment_id = rps_order["serviceChannelOrderId"]

        missing_params = ["submitID", "paymentId", "currency", "amount", "targetAccount"]
        for m_p in missing_params:
            self.client.logger.info(f"缺少参数: {m_p}")
            form_info, request_body = self.client.submitSettlementForm(submit_id, payment_id, currency, amount,
                                                                       {"receiverAddress": target_account}, popKey=m_p)
            msg = f"Parameter error: {m_p} is empty"
            if m_p == "amount":
                msg = "Parameter error: amount is null"
            elif m_p == "targetAccount":
                msg = "Parameter error: outerAddress is empty"
            self.checkStandardCodeMessage(form_info, "RSS100001", msg)

    def test_046_submitSettlementFormOfInner_formAmountLessThanPayOrder(self):
        """
        提交结算表单接口, 铸币, 表单数量位数和支付订单位数不匹配，且小于支付订单数量
        """
        submit_id = "tes" + str(int(time.time() * 1000))
        currency = RSSData.support_currency[0]["fiat"]
        amount = 10.12
        target_account = RSSData.user_account
        account_balance = self.rpsClient.getRoAccountBalance(target_account, currency)
        self.client.logger.info(f"铸币前的账户资产: {account_balance}")
        # 提交rps订单
        self.client.logger.info("开始下rps订单")
        rps_order, coupon_code = self.rpsClient.submitAchPayOrder(target_account, amount,
                                                                  account_info=RPSData.ach_account)
        payment_id = rps_order["serviceChannelOrderId"]

        form_amount = amount - 0.001
        form_info, request_body = self.client.submitSettlementForm(submit_id, payment_id, currency, form_amount,
                                                                   {"receiverAddress": target_account})
        form_info = self.client.queryFormBySubmitId(form_info["data"]["formID"])
        self.checkStandardCodeMessage(form_info)
        self.checkSettlementFormInfoMint(form_info["data"], payment_id, request_body)
        self.waitUntilOrderCompleted(submit_id)

        account_balance2 = self.rpsClient.getRoAccountBalance(target_account, currency)
        self.client.logger.info(f"铸币后的账户资产: {account_balance2}, 变化了: {account_balance2 - account_balance}")
        self.assertAlmostEqual(account_balance2 - account_balance, form_amount, msg="账户资产变化和支付订单数量不符", delta=0.1 ** 7)

    def test_047_submitSettlementFormOfInner_formAmountMoreThanPayOrder(self):
        """
        提交结算表单接口, 铸币, 表单数量位数和支付订单位数不匹配，且大于支付订单数量
        """
        submit_id = "tes" + str(int(time.time() * 1000))
        currency = RSSData.support_currency[0]["fiat"]
        amount = 10.12
        target_account = RSSData.user_account
        account_balance = self.rpsClient.getRoAccountBalance(target_account, currency)
        self.client.logger.info(f"铸币前的账户资产: {account_balance}")
        # 提交rps订单
        self.client.logger.info("开始下rps订单")
        rps_order, coupon_code = self.rpsClient.submitAchPayOrder(target_account, amount,
                                                                  account_info=RPSData.ach_account)
        payment_id = rps_order["serviceChannelOrderId"]

        form_amount = ApiUtils.parseNumberDecimal(amount + 0.007, 3)
        form_info, request_body = self.client.submitSettlementForm(submit_id, payment_id, currency, form_amount,
                                                                   {"receiverAddress": target_account})
        form_info = self.client.queryFormBySubmitId(form_info["data"]["formID"])
        self.checkStandardCodeMessage(form_info)
        self.checkSettlementFormInfoMint(form_info["data"], payment_id, request_body)
        self.waitUntilOrderCompleted(submit_id)
        # 最终铸币应失败

        account_balance2 = self.rpsClient.getRoAccountBalance(target_account, currency)
        self.client.logger.info(f"铸币后的账户资产: {account_balance2}, 变化了: {account_balance2 - account_balance}")
        self.assertNotEqual(form_info["data"]["state"], "Completed", "结算表单铸币应失败")
        self.assertAlmostEqual(account_balance2 - account_balance, amount, msg="账户资产变化和支付订单数量不符", delta=0.1 ** 7)

    def test_048_submitSettlementFormOfOuter_submitIdRepeat(self):
        """
        提交结算表单接口, 赎回业务, submitId重复
        """
        submit_id = "test" + str(int(time.time() * 1000))
        ro_currency = RSSData.support_currency[0]["ro"]
        fiat_currency = RSSData.support_currency[0]["fiat"]
        amount = 12.34
        source_account = RSSData.user_account
        target_account = self.client.queryCustodyAccount(ro_currency)["data"]["account"]
        user_bank = RSSData.out_bank_info[fiat_currency].copy()
        # 转账到中间账户
        pay_order = self.rpsClient.submitPayOrderTransferToRoxeAccount(source_account, target_account, amount,
                                                                       fiat_currency)
        payment_id = pay_order["serviceChannelOrderId"]

        form_info, request_body = self.client.submitSettlementForm(submit_id, payment_id, ro_currency, amount,
                                                                   user_bank)
        self.checkStandardCodeMessage(form_info)

        form_info2, request_body = self.client.submitSettlementForm(submit_id, payment_id + "a", ro_currency, amount,
                                                                    user_bank)
        self.checkStandardCodeMessage(form_info2, "RSS100006", "Duplicate business order ID")
        self.assertIsNone(form_info2["data"])
        self.waitUntilRedeemOrderCompleted(submit_id, form_info["data"]["formID"])

    def test_049_submitSettlementFormOfOuter_paymentOrderIdRepeat(self):
        """
        提交结算表单接口, 赎回业务, 支付订单id
        """
        submit_id = "test" + str(int(time.time() * 1000))
        ro_currency = RSSData.support_currency[0]["ro"]
        fiat_currency = RSSData.support_currency[0]["fiat"]
        amount = 12.34
        source_account = RSSData.user_account
        target_account = self.client.queryCustodyAccount(ro_currency)["data"]["account"]
        user_bank = RSSData.out_bank_info[fiat_currency].copy()

        # 转账到中间账户
        pay_order = self.rpsClient.submitPayOrderTransferToRoxeAccount(source_account, target_account, amount,
                                                                       fiat_currency)
        payment_id = pay_order["serviceChannelOrderId"]

        form_info, request_body = self.client.submitSettlementForm(submit_id, payment_id, ro_currency, amount,
                                                                   user_bank)
        self.checkStandardCodeMessage(form_info)

        form_info2, request_body = self.client.submitSettlementForm(f"test{int(time.time() * 1000)}", payment_id,
                                                                    ro_currency, amount, user_bank)
        self.checkStandardCodeMessage(form_info2, "RSS100005", "Duplicate payment order ID")
        self.assertIsNone(form_info2["data"])
        self.waitUntilRedeemOrderCompleted(submit_id, form_info["data"]["formID"])

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_050_submitSettlementFormOfOuter_currencyLowerCase(self):
        """
        提交结算表单接口, 赎回业务, 币种小写
        """
        submit_id = "test" + str(int(time.time() * 1000))
        ro_currency = RSSData.support_currency[0]["ro"]
        fiat_currency = RSSData.support_currency[0]["fiat"]
        amount = 12.34
        source_account = RSSData.user_account
        target_account = self.client.queryCustodyAccount(ro_currency)["data"]["account"]
        user_bank = RSSData.out_bank_info[fiat_currency].copy()

        account_info = self.client.getQuantity(ro_currency, fiat_currency, amount)
        account_balance = self.rpsClient.getRoAccountBalance(source_account, fiat_currency)
        self.client.logger.info(f"赎回前的资产: {account_balance}")
        # 转账到中间账户
        pay_order = self.rpsClient.submitPayOrderTransferToRoxeAccount(source_account, target_account, amount,
                                                                       fiat_currency)
        payment_id = pay_order["serviceChannelOrderId"]
        form_info, request_body = self.client.submitSettlementForm(submit_id, payment_id, ro_currency.lower(), amount,
                                                                   user_bank)
        self.checkStandardCodeMessage(form_info)
        self.checkSettlementFormInfoRedeem(form_info["data"], payment_id, request_body,
                                           account_info["data"]["outerQuantity"])
        # 等待订单完成
        self.waitUntilRedeemOrderCompleted(submit_id, form_info["data"]["formID"])
        form_info_1 = self.client.queryFormBySubmitId(submit_id)
        form_info_2 = self.client.queryFormByTransactionHash(submit_id, ro_currency)
        for form_info in [form_info_1, form_info_2]:
            self.checkStandardCodeMessage(form_info)
            self.checkSettlementFormInfoRedeem(form_info["data"], payment_id, request_body,
                                               account_info["data"]["outerQuantity"])

        account_balance2 = self.rpsClient.getRoAccountBalance(source_account, fiat_currency)
        self.client.logger.info(f"赎回后的资产: {account_balance2}, 变化了: {account_balance - account_balance2}")
        self.assertAlmostEqual(account_balance - account_balance2, amount + pay_order["channelFee"],
                               msg="账户资产变化和支付订单数量不符", delta=0.1 ** 7)

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_051_submitSettlementFormOfOuter_currencyMixerCase(self):
        """
        提交结算表单接口, 赎回业务, 币种大小写混合
        """
        submit_id = "test" + str(int(time.time() * 1000))
        ro_currency = RSSData.support_currency[0]["ro"]
        fiat_currency = RSSData.support_currency[0]["fiat"]
        amount = 12.34
        source_account = RSSData.user_account
        target_account = self.client.queryCustodyAccount(ro_currency)["data"]["account"]
        user_bank = RSSData.out_bank_info[fiat_currency].copy()

        account_info = self.client.getQuantity(ro_currency, fiat_currency, amount)
        account_balance = self.rpsClient.getRoAccountBalance(source_account, fiat_currency)
        self.client.logger.info(f"赎回前的资产: {account_balance}")
        # 转账到中间账户
        pay_order = self.rpsClient.submitPayOrderTransferToRoxeAccount(source_account, target_account, amount,
                                                                       fiat_currency)
        payment_id = pay_order["serviceChannelOrderId"]
        form_info, request_body = self.client.submitSettlementForm(submit_id, payment_id, ro_currency.title(), amount,
                                                                   user_bank)
        self.checkStandardCodeMessage(form_info)
        self.checkSettlementFormInfoRedeem(form_info["data"], payment_id, request_body,
                                           account_info["data"]["outerQuantity"])

        # 等待订单完成
        self.waitUntilRedeemOrderCompleted(submit_id, form_info["data"]["formID"])
        form_info_1 = self.client.queryFormBySubmitId(submit_id)
        form_info_2 = self.client.queryFormByTransactionHash(submit_id, ro_currency)
        for form_info in [form_info_1, form_info_2]:
            self.checkStandardCodeMessage(form_info)
            self.checkSettlementFormInfoRedeem(form_info["data"], payment_id, request_body,
                                               account_info["data"]["outerQuantity"])

        account_balance2 = self.rpsClient.getRoAccountBalance(source_account, fiat_currency)
        self.client.logger.info(f"赎回后的资产: {account_balance2}, 变化了: {account_balance - account_balance2}")
        self.assertAlmostEqual(account_balance - account_balance2, amount + pay_order["channelFee"],
                               msg="账户资产变化和支付订单数量不符", delta=0.1 ** 7)

    @unittest.skipIf(RSSData.is_inner, "系统未对外开放，错误码暂时跳过")
    def test_052_submitSettlementFormOfOuter_missingParameter(self):
        """
        提交结算表单接口, 赎回业务, 缺少某一参数
        """
        submit_id = "test" + str(int(time.time() * 1000))
        ro_currency = RSSData.support_currency[0]["ro"]
        fiat_currency = RSSData.support_currency[0]["fiat"]
        amount = 12.34
        source_account = RSSData.user_account
        target_account = self.client.queryCustodyAccount(ro_currency)["data"]["account"]
        user_bank = RSSData.out_bank_info[fiat_currency].copy()

        # 转账到中间账户
        pay_order = self.rpsClient.submitPayOrderTransferToRoxeAccount(source_account, target_account, amount,
                                                                       fiat_currency)
        payment_id = pay_order["serviceChannelOrderId"]
        missing_params = ["submitID", "paymentId", "currency", "amount", "bankDetail"]
        for m_p in missing_params:
            self.client.logger.info(f"缺少参数: {m_p}")
            form_info, request_body = self.client.submitSettlementForm(submit_id, payment_id, ro_currency, amount,
                                                                       bankDetail=user_bank, popKey=m_p)
            msg = f"Parameter error: {m_p} is empty"
            if m_p == "amount":
                msg = "Parameter error: amount is null"
            elif m_p == "targetAccount":
                msg = "Parameter error: outerAddress is empty"
            self.checkStandardCodeMessage(form_info, "RSS100001", msg)

        if RSSData.is_check_db:
            clear_sql = "delete from rss_form where payment_id='{}'".format(payment_id)
            self.mysql.exec_sql_query(clear_sql)

    def test_053_submitSettlementFormOfOuter_formAmountLessThanPayOrder(self):
        """
        提交结算表单接口, 赎回业务, 表单数量位数和支付订单位数不匹配，且小于支付订单数量
        """
        submit_id = "test" + str(int(time.time() * 1000))
        ro_currency = RSSData.support_currency[0]["ro"]
        fiat_currency = RSSData.support_currency[0]["fiat"]
        amount = 12.34
        source_account = RSSData.user_account
        target_account = self.client.queryCustodyAccount(ro_currency)["data"]["account"]
        user_bank = RSSData.out_bank_info[fiat_currency].copy()

        account_info = self.client.getQuantity(ro_currency, fiat_currency, amount)
        account_balance = self.rpsClient.getRoAccountBalance(source_account, fiat_currency)
        self.client.logger.info(f"赎回前的资产: {account_balance}")
        # 转账到中间账户
        pay_order = self.rpsClient.submitPayOrderTransferToRoxeAccount(source_account, target_account, amount,
                                                                       fiat_currency)
        payment_id = pay_order["serviceChannelOrderId"]

        form_amount = ApiUtils.parseNumberDecimal(amount - 0.012, 3)
        form_info, request_body = self.client.submitSettlementForm(submit_id, payment_id, ro_currency, form_amount,
                                                                   user_bank)
        self.checkStandardCodeMessage(form_info)
        self.checkSettlementFormInfoRedeem(form_info["data"], payment_id, request_body,
                                           account_info["data"]["outerQuantity"])
        # 等待订单完成
        self.waitUntilRedeemOrderCompleted(submit_id, form_info["data"]["formID"])
        form_info_1 = self.client.queryFormBySubmitId(submit_id)
        form_info_2 = self.client.queryFormByTransactionHash(payment_id, ro_currency)
        for form_info in [form_info_1, form_info_2]:
            self.checkStandardCodeMessage(form_info)
            self.checkSettlementFormInfoRedeem(form_info["data"], payment_id, request_body,
                                               account_info["data"]["outerQuantity"])

        account_balance2 = self.rpsClient.getRoAccountBalance(source_account, fiat_currency)
        self.client.logger.info(f"赎回后的资产: {account_balance2}, 变化了: {account_balance - account_balance2}")
        self.assertAlmostEqual(account_balance - account_balance2, amount + pay_order["channelFee"],
                               msg="账户资产变化和支付订单数量不符", delta=0.1 ** 7)

        if RSSData.is_check_db:
            clear_sql = "delete from rss_form where payment_id='{}'".format(payment_id)
            self.mysql.exec_sql_query(clear_sql)

    def test_054_submitSettlementFormOfInner_payOrderNotHaveCoupon_afterEndDate(self):
        """
        入金表单，ach方式没有优惠：订单时间不在优惠券的有效时间内, 在优惠券结束后
        """
        if not RSSData.is_check_db:
            return
        sql = f"select * from roxe_pay_in_out.roxe_pay_in_allowance where pay_method='ach'"
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
            u_sql = f"update roxe_pay_in_out.roxe_pay_in_allowance set end_date='{u_date}' where pay_method='ach'"
            self.mysql.exec_sql_query(u_sql)

            time.sleep(10)

            submit_id = "test" + str(int(time.time() * 1000))
            currency = RSSData.support_currency[0]["fiat"]
            amount = 12.13
            target_account = RSSData.user_account
            account_balance = self.rpsClient.getRoAccountBalance(target_account, currency)
            self.client.logger.info(f"铸币前的账户资产: {account_balance}")
            # 提交rps订单
            self.client.logger.info("开始下rps订单")
            rps_order, coupon_code = self.rpsClient.submitAchPayOrder(target_account, amount,
                                                                      account_info=RPSData.ach_account)
            payment_id = rps_order["serviceChannelOrderId"]

            form_info, request_body = self.client.submitSettlementForm(submit_id, payment_id, currency, amount,
                                                                       {"receiverAddress": target_account},
                                                                       couponCode=coupon_code)
            self.waitUntilOrderCompleted(submit_id)
            form_info_1 = self.client.queryFormBySubmitId(submit_id)
            form_info_2 = self.client.queryFormByTransactionHash(payment_id, currency)
            for form_info in [form_info_1, form_info_2]:
                self.checkStandardCodeMessage(form_info)
                self.checkSettlementFormInfoMint(form_info["data"], payment_id, request_body)
            account_balance2 = self.rpsClient.getRoAccountBalance(target_account, currency)
            self.client.logger.info(f"铸币后的账户资产: {account_balance2}, 变化了: {account_balance2 - account_balance}")

            self.assertAlmostEqual(account_balance2 - account_balance, amount, msg="账户资产变化和支付订单数量不符", delta=0.1 ** 7)
        except Exception as e:
            flag = False
            self.client.logger.error(e.args, exc_info=True)
        finally:
            u_sql = f"update roxe_pay_in_out.roxe_pay_in_allowance set end_date='{end_date}' where pay_method='ach'"
            self.mysql.exec_sql_query(u_sql)
            assert flag, "用例执行失败"

    def test_055_submitSettlementFormOfInner_payOrderNotHaveCoupon_beforeStartDate(self):
        """
        入金表单，ach方式没有优惠：订单时间不在优惠券的有效时间内, 在优惠券开始前
        """
        if not RSSData.is_check_db:
            return
        sql = f"select * from roxe_pay_in_out.roxe_pay_in_allowance where pay_method='ach'"
        db_allowance = self.mysql.exec_sql_query(sql)
        start_date = db_allowance[0]["startDate"]
        flag = True
        try:
            cur_time = datetime.datetime.utcnow()
            u_date = (cur_time + datetime.timedelta(minutes=3)).strftime("%y-%m-%d %H:%M:%S")
            self.client.logger.info(f"更新的start_date时间戳为: {u_date}")
            u_sql = f"update roxe_pay_in_out.roxe_pay_in_allowance set start_date='{u_date}' where pay_method='ach'"
            self.mysql.exec_sql_query(u_sql)

            time.sleep(1)

            submit_id = "test" + str(int(time.time() * 1000))
            currency = RSSData.support_currency[0]["fiat"]
            amount = 12.13
            target_account = RSSData.user_account
            account_balance = self.rpsClient.getRoAccountBalance(target_account, currency)
            self.client.logger.info(f"铸币前的账户资产: {account_balance}")
            # 提交rps订单
            self.client.logger.info("开始下rps订单")
            rps_order, coupon_code = self.rpsClient.submitAchPayOrder(target_account, amount,
                                                                      account_info=RPSData.ach_account)
            payment_id = rps_order["serviceChannelOrderId"]

            form_info, request_body = self.client.submitSettlementForm(submit_id, payment_id, currency, amount,
                                                                       {"receiverAddress": target_account},
                                                                       couponCode=coupon_code)
            self.waitUntilOrderCompleted(submit_id)
            form_info_1 = self.client.queryFormBySubmitId(form_info["data"]["formID"])
            form_info_2 = self.client.queryFormByTransactionHash(submit_id, currency)
            for form_info in [form_info_1, form_info_2]:
                self.checkStandardCodeMessage(form_info)
                self.checkSettlementFormInfoMint(form_info["data"], payment_id, request_body)
            account_balance2 = self.rpsClient.getRoAccountBalance(target_account, currency)
            self.client.logger.info(f"铸币后的账户资产: {account_balance2}, 变化了: {account_balance2 - account_balance}")

            self.assertAlmostEqual(account_balance2 - account_balance, amount, msg="账户资产变化和支付订单数量不符", delta=0.1 ** 7)
        except Exception as e:
            flag = False
            self.client.logger.error(e.args, exc_info=True)
        finally:
            u_sql = f"update roxe_pay_in_out.roxe_pay_in_allowance set start_date='{start_date}' where pay_method='ach'"
            self.mysql.exec_sql_query(u_sql)
            assert flag, "用例执行失败"

    @unittest.skip("暂无优惠券部分折扣场景")
    def test_056_submitSettlementFormOfInner_payOrderPartCoupon(self):
        """
        入金表单，优惠券部分折扣
        """
        if not RSSData.is_check_db:
            return
        sql = f"select * from roxe_pay_in_out.roxe_pay_in_allowance where pay_method='ach'"
        db_allowance = self.mysql.exec_sql_query(sql)
        allowance_rate = db_allowance[0]["rate"]
        flag = True
        try:
            u_sql = f"update roxe_pay_in_out.roxe_pay_in_allowance set rate=0.37 where pay_method='ach'"
            self.mysql.exec_sql_query(u_sql)
            time.sleep(1)

            submit_id = "test" + str(int(time.time() * 1000))
            currency = RSSData.support_currency[0]["fiat"]
            amount = 12.13
            target_account = RSSData.user_account
            account_balance = self.rpsClient.getRoAccountBalance(target_account, currency)
            self.client.logger.info(f"铸币前的账户资产: {account_balance}")
            # 提交rps订单
            self.client.logger.info("开始下rps订单")
            rps_order, coupon_code = self.rpsClient.submitAchPayOrder(target_account, amount,
                                                                      account_info=RPSData.ach_account)
            payment_id = rps_order["serviceChannelOrderId"]

            form_info, request_body = self.client.submitSettlementForm(submit_id, payment_id, currency, amount,
                                                                       {"receiverAddress": target_account},
                                                                       couponCode=coupon_code)
            self.waitUntilOrderCompleted(submit_id)
            form_info_1 = self.client.queryFormBySubmitId(submit_id)
            form_info_2 = self.client.queryFormByTransactionHash(payment_id, currency)
            for form_info in [form_info_1, form_info_2]:
                self.checkStandardCodeMessage(form_info)
                self.checkSettlementFormInfoMint(form_info["data"], payment_id, request_body)
            account_balance2 = self.rpsClient.getRoAccountBalance(target_account, currency)
            self.client.logger.info(f"铸币后的账户资产: {account_balance2}, 变化了: {account_balance2 - account_balance}")

            self.assertAlmostEqual(account_balance2 - account_balance, amount, msg="账户资产变化和支付订单数量不符", delta=0.1 ** 7)
        except Exception as e:
            flag = False
            self.client.logger.error(e.args, exc_info=True)
        finally:
            u_sql = f"update roxe_pay_in_out.roxe_pay_in_allowance set rate={allowance_rate} where pay_method='ach'"
            self.mysql.exec_sql_query(u_sql)
            assert flag, "用例执行失败"

    def test_057_queryFormStateBySubmitId(self):
        """
        查询表单状态
        """
        ro_currency = "USD.ROXE"
        fiat_currency = "USD"
        amount = 12.34
        account_info, params = self.client.getQuantity(ro_currency, fiat_currency, amount)
        submit_id = "test1637804224327"
        payment_id = "aca6cb1c0eb4adbe74eaf5e161c8ced2d689a634903719aa5597aee919fb6ec3"
        request_body = {}
        form_info = self.client.queryFormBySubmitId(submit_id)
        self.checkStandardCodeMessage(form_info)
        self.checkSettlementFormInfoRedeem(form_info["data"], payment_id, request_body, amount)

    def test_058_queryFormStateByTransaction(self):
        """
        查询哈希
        """
        ro_currency = "USD.ROXE"
        fiat_currency = "INR"
        amount = 12.34
        account_info, params = self.client.getQuantity(ro_currency, fiat_currency, amount)
        payment_id = "cd59b5917af908157fbbfdc40d04d35a61b00af77d8de9d29b2e6cb9d36d9097"
        request_body = {}
        form_info = self.client.queryFormByTransactionHash(payment_id, ro_currency)
        self.checkStandardCodeMessage(form_info)
        self.checkSettlementFormInfoRedeem(form_info["data"], payment_id, request_body,
                                           account_info["data"]["outerQuantity"])

    @unittest.skip("跳过")
    def test_059_nium_submitSettlementFormOfOuter_inr(self):
        """
        :提交结算表单接口, 赎回业务, bankDetail必填
        """
        submit_id = "test" + str(int(time.time() * 1000))
        ro_currency = RSSData.support_currency[0]["ro"]
        fiat_currency = "INR"
        source_account = RSSData.user_account
        # target_account = self.client.queryCustodyAccount(ro_currency)["data"]["account"]
        target_account = RSSData.custody_account
        user_bank = RSSData.out_bank_info[fiat_currency].copy()
        amount = 12.34
        user_bank['referenceId'] = 'test' + str(int(time.time() * 1000))
        account_info, params = self.client.getQuantity(ro_currency, fiat_currency, amount)
        user_bank['amount'] = str(amount)
        account_balance = self.rpsClient.getRoAccountBalance(source_account, fiat_currency)
        self.client.logger.info(f"赎回前的资产: {account_balance}")
        # 转账到中间账户
        pay_order = self.rpsClient.submitPayOrderTransferToRoxeAccount(source_account, target_account, amount, "USD",
                                                                       "transfer")
        payment_id = pay_order["serviceChannelOrderId"]
        form_info, request_body = self.client.submitSettlementForm(submit_id, payment_id, ro_currency, amount,
                                                                   user_bank)
        self.checkStandardCodeMessage(form_info)
        # self.checkSettlementFormInfoRedeem(form_info["data"], payment_id, request_body, account_info["data"]["outerQuantity"])
        # 等待订单完成
        self.waitUntilRedeemOrderCompleted(submit_id, form_info["data"]["formID"])
        submit_id = "test1636971604202"
        payment_id = "033378da4013850ed53462ee3e800ec945ad84ec8b5f6247fb1214c24f16b0df"
        request_body = {}
        form_info_1 = self.client.queryFormBySubmitId(submit_id)
        self.checkStandardCodeMessage(form_info_1)
        # form_info_2 = self.client.queryFormByTransactionHash(submit_id, ro_currency)
        for form_info in [form_info_1]:
            # self.checkStandardCodeMessage(form_info)
            self.checkSettlementFormInfoRedeem(form_info["data"], payment_id, request_body,
                                               account_info["data"]["outerQuantity"])

        account_balance2 = self.rpsClient.getRoAccountBalance(source_account, fiat_currency)
        self.client.logger.info(f"赎回后的资产: {account_balance2}, 变化了: {account_balance - account_balance2}")
        self.assertAlmostEqual(account_balance - account_balance2, amount + pay_order["channelFee"],
                               msg="账户资产变化和支付订单数量不符", delta=0.1 ** 7)

    @unittest.skip("跳过")
    def test_060_nium_submitSettlementFormOfOuter_brl(self):
        """
        :提交结算表单接口, 赎回业务, bankDetail必填
        """
        submit_id = "test" + str(int(time.time() * 1000))
        ro_currency = RSSData.support_currency[0]["ro"]
        fiat_currency = "BRL"
        source_account = RSSData.user_account
        # target_account = self.client.queryCustodyAccount(ro_currency)["data"]["account"]
        target_account = RSSData.custody_account
        user_bank = RSSData.out_bank_info[fiat_currency].copy()
        amount = 11.5
        user_bank["amount"] = str(amount)

        # account_info, params = self.client.getQuantity(ro_currency, fiat_currency, amount)
        account_balance = self.rpsClient.getRoAccountBalance(source_account, fiat_currency)
        self.client.logger.info(f"赎回前的资产: {account_balance}")
        # 转账到中间账户
        pay_order = self.rpsClient.submitPayOrderTransferToRoxeAccount(source_account, target_account, amount, "USD",
                                                                       "transfer")
        payment_id = pay_order["serviceChannelOrderId"]
        form_info, request_body = self.client.submitSettlementForm(submit_id, payment_id, ro_currency, amount,
                                                                   user_bank)
        self.checkStandardCodeMessage(form_info)
        # self.checkSettlementFormInfoRedeem(form_info["data"], payment_id, request_body, account_info["data"]["outerQuantity"])
        # 等待订单完成
        self.waitUntilRedeemOrderCompleted(submit_id, form_info["data"]["formID"])
        form_info_1 = self.client.queryFormBySubmitId(form_info["data"]["formID"])
        self.checkStandardCodeMessage(form_info_1)
        # form_info_2 = self.client.queryFormByTransactionHash(submit_id, ro_currency)
        # for form_info in [form_info_1, form_info_2]:
        #     self.checkStandardCodeMessage(form_info)
        #     self.checkSettlementFormInfoRedeem(form_info["data"], payment_id, request_body, account_info["data"]["outerQuantity"])

        account_balance2 = self.rpsClient.getRoAccountBalance(source_account, fiat_currency)
        self.client.logger.info(f"赎回后的资产: {account_balance2}, 变化了: {account_balance - account_balance2}")
        self.assertAlmostEqual(account_balance - account_balance2, amount + pay_order["channelFee"],
                               msg="账户资产变化和支付订单数量不符", delta=0.1 ** 7)

    @unittest.skip("跳过")
    def test_061_nium_submitSettlementFormOfOuter_cny(self):
        """
        :提交结算表单接口, 赎回业务, bankDetail必填
        """
        submit_id = "test" + str(int(time.time() * 1000))
        ro_currency = RSSData.support_currency[0]["ro"]
        fiat_currency = "CNY"
        source_account = RSSData.user_account
        # target_account = self.client.queryCustodyAccount(ro_currency)["data"]["account"]
        target_account = RSSData.custody_account
        user_bank = RSSData.out_bank_info[fiat_currency].copy()
        amount = 12.4
        user_bank["amount"] = str(amount)

        account_info, params = self.client.getQuantity(ro_currency, fiat_currency, amount)
        user_bank["tradeAmount"] = str(account_info['data']['outerQuantity'])
        account_balance = self.rpsClient.getRoAccountBalance(source_account, fiat_currency)
        self.client.logger.info(f"赎回前的资产: {account_balance}")
        # 转账到中间账户
        pay_order = self.rpsClient.submitPayOrderTransferToRoxeAccount(source_account, target_account, amount, "USD",
                                                                       "transfer")
        payment_id = pay_order["serviceChannelOrderId"]
        form_info, request_body = self.client.submitSettlementForm(submit_id, payment_id, ro_currency, amount,
                                                                   user_bank)
        self.checkStandardCodeMessage(form_info)
        # self.checkSettlementFormInfoRedeem(form_info["data"], payment_id, request_body, account_info["data"]["outerQuantity"])
        # 等待订单完成
        self.waitUntilRedeemOrderCompleted(submit_id, form_info["data"]["formID"])
        form_info_1 = self.client.queryFormBySubmitId(form_info["data"]["formID"])
        self.checkStandardCodeMessage(form_info_1)
        # form_info_2 = self.client.queryFormByTransactionHash(submit_id, ro_currency)
        # for form_info in [form_info_1, form_info_2]:
        #     self.checkStandardCodeMessage(form_info)
        #     self.checkSettlementFormInfoRedeem(form_info["data"], payment_id, request_body, account_info["data"]["outerQuantity"])

        account_balance2 = self.rpsClient.getRoAccountBalance(source_account, fiat_currency)
        self.client.logger.info(f"赎回后的资产: {account_balance2}, 变化了: {account_balance - account_balance2}")
        self.assertAlmostEqual(account_balance - account_balance2, amount + pay_order["channelFee"],
                               msg="账户资产变化和支付订单数量不符", delta=0.1 ** 7)

    @unittest.skip("跳过")
    def test_062_nium_submitSettlementFormOfOuter_php(self):
        """
        :提交结算表单接口, 赎回业务, bankDetail必填
        """
        submit_id = "test" + str(int(time.time() * 1000))
        ro_currency = RSSData.support_currency[0]["ro"]
        fiat_currency = "PHP"
        source_account = RSSData.user_account
        # target_account = self.client.queryCustodyAccount(ro_currency)["data"]["account"]
        target_account = RSSData.custody_account
        user_bank = RSSData.out_bank_info[fiat_currency].copy()
        amount = 12.4
        user_bank["amount"] = str(amount)

        # account_info = self.client.getQuantity(ro_currency, fiat_currency, amount)
        account_balance = self.rpsClient.getRoAccountBalance(source_account, fiat_currency)
        self.client.logger.info(f"赎回前的资产: {account_balance}")
        # 转账到中间账户
        pay_order = self.rpsClient.submitPayOrderTransferToRoxeAccount(source_account, target_account, amount, "USD",
                                                                       "transfer")
        payment_id = pay_order["serviceChannelOrderId"]
        form_info, request_body = self.client.submitSettlementForm(submit_id, payment_id, ro_currency, amount,
                                                                   user_bank)
        self.checkStandardCodeMessage(form_info)
        # self.checkSettlementFormInfoRedeem(form_info["data"], payment_id, request_body, account_info["data"]["outerQuantity"])
        # 等待订单完成
        self.waitUntilRedeemOrderCompleted(submit_id, form_info["data"]["formID"])
        form_info_1 = self.client.queryFormBySubmitId(form_info["data"]["formID"])
        self.checkStandardCodeMessage(form_info_1)
        # form_info_2 = self.client.queryFormByTransactionHash(submit_id, ro_currency)
        # for form_info in [form_info_1, form_info_2]:
        #     self.checkStandardCodeMessage(form_info)
        #     self.checkSettlementFormInfoRedeem(form_info["data"], payment_id, request_body, account_info["data"]["outerQuantity"])

        account_balance2 = self.rpsClient.getRoAccountBalance(source_account, fiat_currency)
        self.client.logger.info(f"赎回后的资产: {account_balance2}, 变化了: {account_balance - account_balance2}")
        self.assertAlmostEqual(account_balance - account_balance2, amount + pay_order["channelFee"],
                               msg="账户资产变化和支付订单数量不符", delta=0.1 ** 7)

    @unittest.skip("跳过")
    def test_063_nium_submitSettlementFormOfOuter_mxn(self):
        """
        :提交结算表单接口, 赎回业务, bankDetail必填
        """
        submit_id = "test" + str(int(time.time() * 1000))
        ro_currency = RSSData.support_currency[0]["ro"]
        fiat_currency = "MXN"
        source_account = RSSData.user_account
        # target_account = self.client.queryCustodyAccount(ro_currency)["data"]["account"]
        target_account = RSSData.custody_account
        user_bank = RSSData.out_bank_info[fiat_currency].copy()
        amount = 12.4
        user_bank["amount"] = str(amount)

        # account_info = self.client.getQuantity(ro_currency, fiat_currency, amount)
        # user_bank["tradeAmount"] = str(account_info['data']['outerQuantity'])
        account_balance = self.rpsClient.getRoAccountBalance(source_account, fiat_currency)
        self.client.logger.info(f"赎回前的资产: {account_balance}")
        # 转账到中间账户
        pay_order = self.rpsClient.submitPayOrderTransferToRoxeAccount(source_account, target_account, amount, "USD",
                                                                       "transfer")
        payment_id = pay_order["serviceChannelOrderId"]
        form_info, request_body = self.client.submitSettlementForm(submit_id, payment_id, ro_currency, amount,
                                                                   user_bank)
        self.checkStandardCodeMessage(form_info)
        # self.checkSettlementFormInfoRedeem(form_info["data"], payment_id, request_body, account_info["data"]["outerQuantity"])
        # 等待订单完成
        self.waitUntilRedeemOrderCompleted(submit_id, form_info["data"]["formID"])
        form_info_1 = self.client.queryFormBySubmitId(form_info["data"]["formID"])
        self.checkStandardCodeMessage(form_info_1)
        # form_info_2 = self.client.queryFormByTransactionHash(submit_id, ro_currency)
        # for form_info in [form_info_1, form_info_2]:
        #     self.checkStandardCodeMessage(form_info)
        #     self.checkSettlementFormInfoRedeem(form_info["data"], payment_id, request_body, account_info["data"]["outerQuantity"])

        account_balance2 = self.rpsClient.getRoAccountBalance(source_account, fiat_currency)
        self.client.logger.info(f"赎回后的资产: {account_balance2}, 变化了: {account_balance - account_balance2}")
        self.assertAlmostEqual(account_balance - account_balance2, amount + pay_order["channelFee"],
                               msg="账户资产变化和支付订单数量不符", delta=0.1 ** 7)

    # RMN-TerraPay校验方法
    def terrapay_checkOrderAmount(self, to_currency, from_amount, TP_before_balance, db_name):
        """
        查询收费情况及校验最终转账金额
        """
        # 获取RSS费（rssFee）
        sql2 = "select * from `{}`.sn_currency_support where out_currency='{}'".format(db_name, to_currency)
        res2 = self.mysql.exec_sql_query(sql2)
        rssFee = float(res2[0]["feeQuantity"])
        # 获取通道费（channelFee）
        channelName = "TERRAPAY"  # 目前固定TERRAPAY通道
        currency = to_currency
        fee_info = self.client.getChannelFee(channelName, currency)
        wallet_fee, bank_fee = float(fee_info["walletFeeAmount"]), float(fee_info["bankFeeAmount"])
        # payOutMethod = RMNData.out_bank_info[to_currency]["payOutMethod"]
        payOutMethod = "bank"  # 目前暂时写死为bank
        if payOutMethod == "wallet":
            channelFee = wallet_fee
        elif payOutMethod == "bank":
            channelFee = bank_fee
        # 实际提交通道方的出金金额 = 下单金额 -（RSS节点费+通道费）
        actual_amount = round(float(from_amount) - (rssFee + channelFee), 2)
        self.client.logger.info("实际提交至三方的出金金额为:{}".format(actual_amount))
        # 查询并校验在TerraPay通道方的中间账户金额
        TP_after_balance = self.client.terrapayQueryAccountBalance()
        TP_transfer_out_amount = round(TP_before_balance - TP_after_balance, 2)
        self.assertAlmostEqual(actual_amount, TP_transfer_out_amount, places=2, msg="实际出金金额不正确")
        self.client.logger.info(
            f"转账前在TP的资产:{TP_before_balance}, 转账后在TP的资产: {TP_after_balance}, 实际TP转出金额: {TP_transfer_out_amount}")

    def terrapay_waitUntilOrderFinish(self, txId, r_country, to_currency, from_amount, time_out=100):
        country = r_country.lower()
        db_name = "sn-{}-roxe-roxe".format(country)
        sql_rts = "select * from `rts-roxe`.rts_order where client_id='{}'".format(txId)
        rts_db_res = self.mysql.exec_sql_query(sql_rts)
        if len(rts_db_res) > 0:  # 处理获取的数据库数据，获取order_id
            rts_order_id = rts_db_res[0]["orderId"]
            rss_client_id = rts_order_id + "_sn2"

        rss_sql = "select * from `{}`.sn_order where client_id='{}'".format(db_name, rss_client_id)
        TP_before_balance = self.client.terrapayQueryAccountBalance()
        self.client.logger.info("转账前TerraPay账户中余额：{}".format(TP_before_balance))
        b_time = time.time()
        while time.time() - b_time < time_out * 2:
            rss_db_res = self.mysql.exec_sql_query(rss_sql)
            if len(rss_db_res) > 0:
                for res in rss_db_res:  # 处理获取的数据库数据，获取订单状态
                    orderState = res.get("orderState")
                # print("order_state是：{}".format(orderState))
                if orderState == "init":
                    self.client.logger.info("初始化中···")
                elif orderState == "deposit_finish":
                    self.client.logger.info("充值成功")
                elif orderState == "outer_generate":
                    self.client.logger.info("出金订单生成")
                elif orderState == "outer_submit":
                    self.client.logger.info("出金订单已提交")
                elif orderState == "outer_finish":
                    self.client.logger.info("出金订单完成")
                elif orderState == "destroy_submit":
                    self.client.logger.info("销毁链上订单提交")
                elif orderState == "finish":
                    self.client.logger.info("订单最终完成！")
                    break
            time.sleep(10)
        self.client.logger.warning("查询费用情况及校验实际转账金额")
        self.terrapay_checkOrderAmount(to_currency, from_amount, TP_before_balance, db_name)

    # TerraPay出金通道
    def waitUntilTerraPayRedeemOrderCompleted(self, form_id, time_out=100):
        """
        等待订单完成
        """
        sql = "select * from `sn-roxe-terrapay-roxe`.sn_order where order_id='{}'".format(form_id)
        b_time = time.time()
        while time.time() - b_time < time_out * 2:
            db_res = self.mysql.exec_sql_query(sql)
            if len(db_res) > 0:
                for res in db_res:  # 处理获取的数据库数据，获取订单状态
                    orderState = res.get("orderState")
                if orderState == "init":
                    self.client.logger.info("初始化中···")
                elif orderState == "deposit_finish":
                    self.client.logger.info("充值成功")
                elif orderState == "outer_generate":
                    self.client.logger.info("出金订单生成")
                elif orderState == "outer_submit":
                    self.client.logger.info("出金订单已提交")
                elif orderState == "outer_finish":
                    self.client.logger.info("出金订单完成")
                elif orderState == "destroy_submit":
                    self.client.logger.info("销毁链上订单提交")
                elif orderState == "finish":
                    self.client.logger.info("订单最终完成！")
                    break
            time.sleep(20)
        # sql = "select * from `{}`.sn_bank_outer where order_id='{}'".format(db_name, form_id)
        # b_time = time.time()
        # while time.time() - b_time < time_out:
        #     db_res = self.mysql.exec_sql_query(sql)
        #     if len(db_res) > 0:
        #         for res in db_res:  # 处理获取的数据库数据，获取订单状态
        #             outerState = res.get("outerState")
        #             # print("order_state是：{}".format(orderState))
        #         if outerState == "init":
        #             self.client.logger.info("出金订单生成")
        #         elif outerState == "submit":
        #             self.client.logger.info("出金订单提交")
        #         elif outerState == "success":
        #             self.client.logger.info("出金订单成功")
        #             break
        #         elif outerState == "fail":
        #             self.client.logger.info("出金订单失败")
        #             break
        #     else:
        #         self.client.logger.info("出金订单未生成")
        #
        #     time.sleep(time_inner)

    def checkSubmitOrderFormInfoRedeem(self, outMethod, outCurrency, form_id, form_info, request_body,
                                       db_name):
        """
        校验提交的订单及返回数据
        """
        if outMethod == "wallet":
            expect_info = RSSData.terrapay_out_wallet_info[outCurrency]
            # print(expect_info)
        elif outMethod == "bank":
            expect_info = RSSData.terrapay_out_bank_info[outCurrency]
            # print(expect_info)

        if request_body:
            self.assertEqual(form_info["data"]["submitId"], request_body["submitId"], msg="返回的submitId不正确")
            self.assertEqual(form_info["data"]["payOrderId"], request_body["payOrderId"], msg="返回的payOrderId不正确")
            self.assertEqual(form_info["data"]["payCurrency"], request_body["payCurrency"], msg="返回的支付币种不正确")
            self.assertEqual(form_info["data"]["payAmount"], request_body["payAmount"], msg="返回的支付金额不正确")
            self.assertEqual(form_info["data"]["outCurrency"], request_body["outCurrency"], msg="返回的出金币种不正确")
            self.assertDictEqual(form_info["data"]["outInfo"], expect_info, msg="返回的提交表单内容不正确")
        if RSSData.is_check_db:
            sql = "select * from `{}`.sn_order where order_id='{}'".format(db_name, form_id)
            db_res = self.mysql.exec_sql_query(sql)
            # print(db_res)
            sql2 = "select * from `{}`.sn_bank_outer where order_id='{}'".format(db_name, form_id)
            db_res2 = self.mysql.exec_sql_query(sql2)
            # print(db_res2)
            payout_id = db_res2[0]["payoutId"]
            outAmount = float(db_res2[0]["payoutQuantity"])
            # sql3 = "select * from roxe_rpc.rpc_pay_order where id='{}'".format(payout_id)
            # db_res3 = self.mysql.exec_sql_query(sql3)
            # print(db_res3)
            self.assertEqual(form_info["data"]["formId"], db_res[0]["orderId"], msg="返回的formId不正确")
            self.assertEqual(form_info["data"]["outOrderId"], payout_id, msg="返回的outOrderId不正确")
            self.assertAlmostEqual(form_info["data"]["outAmount"], outAmount, places=2, msg="返回的实际出金金额不正确")
            # self.assertEqual(form_info["data"]["infoReceiveCurrency"], outCurrency, msg="返回的表单接收币种不正确")
            # self.assertEqual(form_info["data"]["infoAmount"], payAmount, msg="返回的提交表单金额不正确")
            # self.assertEqual(form_info["data"]["infoReceiveAddress"], expect_info["receiverAddress"], msg="返回的出金币种不正确")
            self.assertEqual(form_info["data"]["outInfo"]["payOutMethod"], outMethod, msg="返回的表单出金方法不正确")

    def checkOrderByTerrapay(self, form_info, outCurrency, payAmount, TP_before_balance):
        """
        通过Terrapay通道方返回的数据校验提交的订单数据及返回值
        """
        outOrderId = form_info["data"]["outOrderId"]
        sql = "select * from `roxe_rpc`.rpc_pay_order where id='{}'".format(outOrderId)
        res = self.mysql.exec_sql_query(sql)
        res_id = res[0]["channelOrderId"]
        # 获取RSS费（rssFee）
        outCurrency = outCurrency + "." + outCurrency[:-1]
        sql2 = "select * from `sn-roxe-terrapay-roxe`.sn_business where out_currency='{}'".format(outCurrency)
        res2 = self.mysql.exec_sql_query(sql2)
        rssFee = float(res2[0]["feeQuantity"])
        # 获取通道费（channelFee）
        channelName = "TERRAPAY"  # 目前固定TERRAPAY通道，后期可读取yaml
        currency = outCurrency
        fee_info = self.client.getChannelFee(channelName, currency)
        wallet_fee, bank_fee = float(fee_info["walletFeeAmount"]), float(fee_info["bankFeeAmount"])
        form_info_payOutMethod = form_info["data"]["outInfo"]["payOutMethod"]
        if form_info_payOutMethod == "wallet":
            channelFee = wallet_fee
        elif form_info_payOutMethod == "bank":
            channelFee = bank_fee
        # 实际提交通道方的出金金额=下单金额-（RSS费+通道费）
        actual_amount = round(payAmount - (rssFee + channelFee), 2)
        self.client.logger.info("实际提交至三方的出金金额为:{}".format(actual_amount))
        # 调用Terrapay通道方查询订单状态接口
        Remit_State = "3000:Remit Success"
        res = self.client.terrapayQueryOrderStatus(res_id)
        method = ((res['type']).split("_")[0]).lower()
        self.assertEqual(res["transactionReference"], res_id, msg="不是同一个订单")
        self.assertEqual(res["transactionStatus"], Remit_State, msg="汇款未完成")
        # 校验rss订单
        self.assertAlmostEqual(form_info["data"]["outAmount"], float(res["amount"]), places=2, msg="返回的实际出金金额不正确")
        self.assertEqual(form_info["data"]["outCurrency"], res["currency"], msg="返回的接收币种不正确")
        self.assertEqual(form_info["data"]["outInfo"]["payOutMethod"], method, msg="返回的出金方式不正确")
        # 查询并校验在TerraPay通道方的中间账户金额
        TP_after_balance = self.client.terrapayQueryAccountBalance()
        TP_transfer_out_amount = round(TP_before_balance - TP_after_balance, 2)
        self.assertAlmostEqual(actual_amount, TP_transfer_out_amount, places=2, msg="实际出金金额不正确")
        self.client.logger.info(f"转账前在TP的资产:{TP_before_balance}, 转账后在TP的资产: {TP_after_balance}, 实际TP转出金额: {TP_transfer_out_amount}")

    def test_getSystemState(self):
        state_info = self.client.getSystemState()
        self.checkStandardCodeMessage(state_info)
        self.assertEqual(state_info["data"], "available")

    def test_terrapay_wallet_queryfee(self):
        """
        TerraPay查询汇率 wallet
        """
        value = "+8616521688080"
        beneficiaryName = "David Robinson"
        provider = "08601"
        requestAmount = 100
        requestCurrency = "USD"
        sendingCurrency = "USD"
        receivingCurrency = "CNY"
        self.client.terrapayQueryStatus(value, beneficiaryName, provider)
        self.client.terraypayQueryExchangeRate(value, requestAmount, requestCurrency, sendingCurrency,
                                               receivingCurrency)

    def test_terrapay_bank_queryfee(self):
        """
        TerraPay查询汇率 bank
        """
        value = "20408277204478"
        beneficiaryName = "RANDY OYUGI"
        bankcode = "AUBKPHMM"
        bankname = "Asia United Bank"
        country = "PH"
        requestAmount = 100
        requestCurrency = "USD"
        sendingCurrency = "USD"
        receivingCurrency = "PHP"
        self.client.terrapayQueryStatus(value, beneficiaryName, bankcode=bankcode, bankname=bankname, country=country)
        self.client.terraypayQueryExchangeRate(value, requestAmount, requestCurrency, sendingCurrency,
                                               receivingCurrency, receivingCountry=country)

    def test_064_terrapay_ph_getSystemState(self):
        """
        查询系统状态信息  PH节点
        """
        country = "ph"
        self.client.handle_host(country)
        state = self.client.getSystemState()
        self.checkStandardCodeMessage(state)
        self.assertEqual(state["data"], "AVAILABLE", msg="返回的data不正确")

    def test_065_terrapay_ph_getCurrencySupport(self):
        """
        查询支持的币种，PH节点
        """
        country = "ph"
        outCurrency = RSSData.support_currency[2]["fiat"]
        self.client.handle_host(country)
        res = self.client.getCurrencySupport()
        # print(res["data"]["inners"])
        self.checkStandardCodeMessage(res)
        self.assertEqual(res["data"]["inners"], ['USD.ROXE', 'USD'], msg="返回的入金币种不正确")
        self.assertEqual(res["data"]["outers"], ['USD.ROXE', outCurrency], msg="返回的出金币种不正确")

    def test_066_terrapay_ph_getPayoutMethod(self):
        """
        查询出金方式 币种 PHP
        """
        outCurrency = RSSData.support_currency[2]["fiat"]
        country = "ph"
        self.client.handle_host(country)
        methods = self.client.getPayoutMethod(outCurrency)
        self.checkStandardCodeMessage(methods)
        self.assertEqual(methods["data"], ["wallet", "bank"])

    def test_067_terrapay_ph_getPayoutOrgan(self):
        """
        查询出金机构  币种：PHP
        """
        outCurrency = RSSData.out_currency[4]
        outMethods = ["bank", "wallet"]
        country = "ph"
        self.client.handle_host(country)
        for outMethod in outMethods:
            self.client.handle_host("ph")
            methods = self.client.getPayoutOrgan(outCurrency, outMethod)
            self.checkStandardCodeMessage(methods)
            self.assertTrue(len(methods['data']) > 0)

    def test_068_terrapay_ph_wallet_getExchangeReatFee(self):
        """
        查询转账费用, 币种: RoUSD->PHP，金额：10.05
        """
        payCurrency = RSSData.support_currency[0]["ro"]
        outCurrency = RSSData.support_currency[2]["fiat"]
        payQuantity = 10.05
        fee = 6  # RSS费+通道费=5,暂时固定写死，后期优化动态读取
        requestAmount = round(payQuantity - fee, 2)
        outMethod = "wallet"
        value = "+638971378380"
        beneficiaryName = "David Robinson"
        provider = "06301"
        requestCurrency = str(payCurrency).split(".")[0]
        sendingCurrency = requestCurrency
        out_country = "PH"
        # 查询用户钱包状态并调用TerraPay查询汇率接口
        self.client.terrapayQueryStatus(value, beneficiaryName, provider)
        TP_res = self.client.terraypayQueryExchangeRate(value, requestAmount, requestCurrency, sendingCurrency,
                                                        outCurrency)
        in_quantity = float(TP_res['requestAmount'])
        for quotes in TP_res['quotes']:
            print(quotes)
        receivingAmount = quotes.get("receivingAmount")
        fxRate = quotes.get("fxRate")
        self.client.handle_host(out_country.lower())
        account_info, params = self.client.getExchangeReatFee(payCurrency, payQuantity, outCurrency, outMethod)
        self.checkStandardCodeMessage(account_info)
        self.assertEqual(account_info["data"]["payCurrency"], payCurrency, "返回的payCurrency不正确")
        self.assertEqual(account_info["data"]["payQuantity"], str(payQuantity), "返回的payQuantity不正确")
        self.assertEqual(account_info["data"]["feeCurrency"], "USD", "返回的feeCurrency不正确")
        self.assertEqual(account_info["data"]["feeQuantity"], str(fee), "返回的feeQuantity不正确")  # 费用=RSS费+通道费
        self.assertEqual(account_info["data"]["exchangeRate"], fxRate, "返回的exchangeRate不正确")
        self.assertEqual(account_info["data"]["outCurrency"], outCurrency, "返回的outerCurrency不正确")
        self.assertAlmostEqual(account_info["data"]["outQuantity"], receivingAmount, places=2,
                               msg="返回的outerQuantity不正确", delta=0.5)

    def test_06801_terrapay_ph_bank_getExchangeReatFee(self):
        """
        查询汇率费用, 币种: RoUSD->PHP，金额：8.56
        """
        payCurrency = RSSData.support_currency[0]["ro"]
        outCurrency = RSSData.support_currency[2]["fiat"]
        payQuantity = 8.56
        fee = 5  # RSS费+通道费=5,暂时固定写死，后期优化动态读取
        requestAmount = round(payQuantity - fee, 2)
        outMethod = "bank"
        value = "20408277204478"
        beneficiaryName = "RANDY OYUGI"
        # provider = "06301"
        requestCurrency = str(payCurrency).split(".")[0]
        sendingCurrency = requestCurrency
        bankcode = "AUBKPHMM"
        bankname = "Asia United Bank"
        out_country = "PH"
        # 查询用户银行账户状态并调用TerraPay查询汇率接口
        self.client.terrapayQueryStatus(value, beneficiaryName, bankcode=bankcode, bankname=bankname,
                                        country=out_country)
        TP_res = self.client.terraypayQueryExchangeRate(value, requestAmount, requestCurrency, sendingCurrency,
                                                        outCurrency, receivingCountry=out_country)
        for quotes in TP_res['quotes']:
            print(quotes)
        receivingAmount = quotes.get("receivingAmount")
        fxRate = quotes.get("fxRate")
        self.client.handle_host(out_country.lower())
        account_info, params = self.client.getExchangeReatFee(payCurrency, payQuantity, outCurrency, outMethod)
        self.checkStandardCodeMessage(account_info)
        self.assertEqual(account_info["data"]["payCurrency"], payCurrency, "返回的payCurrency不正确")
        self.assertEqual(account_info["data"]["payQuantity"], str(payQuantity), "返回的payQuantity不正确")
        self.assertEqual(account_info["data"]["feeCurrency"], "USD", "返回的feeCurrency不正确")
        self.assertEqual(account_info["data"]["feeQuantity"], str(fee), "返回的feeQuantity不正确")  # 费用=RSS费+通道费
        self.assertEqual(account_info["data"]["exchangeRate"], fxRate, "返回的exchangeRate不正确")
        self.assertEqual(account_info["data"]["outCurrency"], outCurrency, "返回的outerCurrency不正确")
        self.assertAlmostEqual(account_info["data"]["outQuantity"], receivingAmount, places=2,
                               msg="返回的outerQuantity不正确", delta=0.5)

    def test_069_terrapay_ph_getPayoutForm(self):
        """
        查询出金必填字段  币种：PHP  出金方式：wallet/bank
        """
        outCurrency = RSSData.support_currency[2]["fiat"]
        country = "ph"
        self.client.handle_host(country)
        methods = self.client.getPayoutMethod(outCurrency)
        for m in methods["data"]:
            fields = self.client.getPayoutForm(outCurrency, m)
            self.checkStandardCodeMessage(fields)
            expect_fields = []
            if m == "wallet":
                expect_fields = RSSData.terrapay_out_wallet_fields[outCurrency]
                # print(len(expect_fields))
            elif m == "bank":
                expect_fields = RSSData.terrapay_out_bank_fields[outCurrency]
                # print(len(expect_fields))
            self.assertEqual(len(fields["data"]), len(expect_fields))
            for field in fields["data"]:
                expect_field = [i for i in expect_fields if i["name"] == field["name"]][0]
                self.assertEqual(field, expect_field, "字段{}和预期不符".format(field["name"]))

    def test_70_terrapay_ph_checkPayoutForm(self):
        """
        校验出金必填字段  币种：PHP  出金方式：wallet/bank
        """
        outCurrency = RSSData.support_currency[2]["fiat"]
        outInfo = RSSData.terrapay_out_wallet_info[outCurrency]
        # outInfo['referenceId'] = 'test' + str(int(time.time() * 1000))
        country = "ph"
        self.client.handle_host(country)
        methods = self.client.getPayoutMethod(outCurrency)
        for m in methods["data"]:
            if m == "wallet":
                outInfo = RSSData.terrapay_out_wallet_info[outCurrency]
                # print(len(outInfo))
            elif m == "bank":
                outInfo = RSSData.terrapay_out_bank_info[outCurrency]
                # print(len(outInfo))

            check_res = self.client.checkPayoutForm(outCurrency, outInfo)
            self.checkStandardCodeMessage(check_res)
            self.assertTrue(check_res["data"])

    def test_071_terrapay_ph_wallet_submitOrderForm(self):
        """
        :提交表单接口→提现, 赎回业务, Detail必填，经校验过的正确参数，RoUSD->PHP，wallet出金方式
        """
        submitId = "test" + str(int(time.time() * 1000))
        payCurrency = RSSData.terrapay_out_currency["ro"][0]
        outCurrency = RSSData.terrapay_out_currency["fait"][1]
        outInfo = RSSData.terrapay_out_wallet_info[outCurrency]
        payAmount = float(outInfo["amount"])
        # fee = 6  # RSS费+通道费=6,暂时固定写死，后期优化动态读取
        # actual_amount = round(payAmount - fee, 2)
        country = (outInfo["receiverCountry"]).lower()
        db_name = "sn-{}-roxe-roxe".format(country)
        self.client.handle_host(country)
        source_account = RSSData.user_account
        target_account = RSSData.custody_account
        # 校验出金表单
        check_res = self.client.checkPayoutForm(outCurrency, outInfo)
        self.checkStandardCodeMessage(check_res)
        self.assertTrue(check_res["data"])
        # 查询转账前出金账户资产
        account_balance = self.rpsClient.getRoAccountBalance(source_account, "USD")
        self.client.logger.info(f"赎回前的资产: {account_balance}")
        # 转账到中间账户，并获取提交订单所需参数payOrderId
        pay_order = self.rpsClient.submitPayOrderTransferToRoxeAccount(source_account, target_account, payAmount, "USD",
                                                                       "transfer")
        payOrderId = pay_order["serviceChannelOrderId"]
        # 查询表单提交前在TerraPay通道方的中间账户金额
        TP_before_balance = self.client.terrapayQueryAccountBalance()
        # 提交提现表单
        form_info, request_body = self.client.submitOrderForm(submitId, payOrderId, payCurrency, payAmount, outCurrency,
                                                              outInfo)
        self.checkStandardCodeMessage(form_info)
        # 等待订单完成
        form_id = form_info["data"]["formId"]
        self.waitUntilTerraPayRedeemOrderCompleted(form_id, db_name=db_name)
        # 根据submitId查询订单信息
        form_info_1 = self.client.queryFormByClientID(submitId)
        self.checkStandardCodeMessage(form_info_1)
        self.assertEqual(form_info_1['data']['state'], 'finish')
        # 查询转账后出金账户资产
        account_balance2 = self.rpsClient.getRoAccountBalance(source_account, "USD")

        self.client.logger.info(f"赎回后的资产: {account_balance2}, 变化了: {account_balance - account_balance2}")
        self.assertAlmostEqual(account_balance - account_balance2, payAmount, places=2, msg="账户资产变化与最初提交订单金额不符")
        # self.checkSubmitOrderFormInfoRedeem(payAmount, outMethod, outCurrency, form_id, form_info_1, request_body,
        #                                     db_name)
        self.checkOrderByTerrapay(form_info_1, outCurrency, payAmount, TP_before_balance, db_name)

    def test_072_terrapay_ph_bank_submitOrderForm(self):
        """
        :提交表单接口→提现, 赎回业务, Detail必填，经校验过的正确参数，RoUSD->PHP，bank出金方式
        """
        submitId = "test" + str(int(time.time() * 1000))
        payCurrency = RSSData.terrapay_out_currency["ro"][0]
        outCurrency = RSSData.terrapay_out_currency["fait"][1]
        outInfo = RSSData.terrapay_out_bank_info[outCurrency]
        payAmount = float(outInfo["amount"])
        # fee = 5  # RSS费+通道费=5,暂时固定写死，后期优化动态读取
        # actual_amount = round(payAmount - fee, 2)
        country = (outInfo["receiverCountry"]).lower()
        db_name = "sn-{}-roxe-roxe".format(country)
        self.client.handle_host(country)
        source_account = RSSData.user_account
        target_account = RSSData.custody_account
        # 校验出金表单
        check_res = self.client.checkPayoutForm(outCurrency, outInfo)
        self.checkStandardCodeMessage(check_res)
        self.assertTrue(check_res["data"])
        # 查询转账前出金账户资产
        account_balance = self.rpsClient.getRoAccountBalance(source_account, "USD")
        self.client.logger.info(f"赎回前的资产: {account_balance}")
        # 转账到中间账户，并获取提交订单所需参数payOrderId
        pay_order = self.rpsClient.submitPayOrderTransferToRoxeAccount(source_account, target_account, payAmount, "USD",
                                                                       "transfer")
        payOrderId = pay_order["serviceChannelOrderId"]
        # 查询表单提交前在TerraPay通道方的中间账户金额
        TP_before_balance = self.client.terrapayQueryAccountBalance()
        # 提交提现表单
        form_info, request_body = self.client.submitOrderForm(submitId, payOrderId, payCurrency, payAmount, outCurrency,
                                                              outInfo)
        self.checkStandardCodeMessage(form_info)
        # 等待订单完成
        form_id = form_info["data"]["formId"]
        self.waitUntilTerraPayRedeemOrderCompleted(form_id, db_name=db_name)
        # 根据submitId查询订单信息
        form_info_1 = self.client.queryFormByClientID(submitId)
        self.checkStandardCodeMessage(form_info_1)
        self.assertEqual(form_info_1['data']['state'], 'finish')
        # 查询转账后出金账户资产
        account_balance2 = self.rpsClient.getRoAccountBalance(source_account, "USD")
        self.client.logger.info(f"赎回后的资产: {account_balance2}, 变化了: {account_balance - account_balance2}")
        self.assertAlmostEqual(account_balance - account_balance2, payAmount, places=2, msg="账户资产变化与最初提交订单金额不符")
        # self.checkSubmitOrderFormInfoRedeem(payAmount, outMethod, outCurrency, form_id, form_info_1, request_body,
        #                                     db_name)
        self.checkOrderByTerrapay(form_info_1, outCurrency, payAmount, TP_before_balance, db_name)

    def test_073_terrapay_id_wallet_submitOrderForm(self):
        """
        :提交表单接口→提现, 赎回业务, Detail必填，经校验过的正确参数，RoUSD->IDR，wallet出金方式
        """
        submitId = "test" + str(int(time.time() * 1000))
        payCurrency = RSSData.terrapay_out_currency["ro"][0]
        outCurrency = RSSData.terrapay_out_currency["fait"][2]
        outInfo = RSSData.terrapay_out_wallet_info[outCurrency]
        payAmount = float(outInfo["amount"])
        # fee = 6  # RSS费+通道费=6,暂时固定写死，后期优化动态读取
        # actual_amount = round(payAmount - fee, 2)
        country = (outInfo["receiverCountry"]).lower()
        db_name = "sn-{}-roxe-roxe".format(country)
        self.client.handle_host(country)
        source_account = RSSData.user_account
        target_account = RSSData.custody_account
        # 校验出金表单
        check_res = self.client.checkPayoutForm(outCurrency, outInfo)
        self.checkStandardCodeMessage(check_res)
        self.assertTrue(check_res["data"])
        # 查询转账前出金账户资产
        account_balance = self.rpsClient.getRoAccountBalance(source_account, "USD")
        self.client.logger.info(f"赎回前的资产: {account_balance}")
        # 转账到中间账户，并获取提交订单所需参数payOrderId
        pay_order = self.rpsClient.submitPayOrderTransferToRoxeAccount(source_account, target_account, payAmount, "USD",
                                                                       "transfer")
        payOrderId = pay_order["serviceChannelOrderId"]
        # 查询表单提交前在TerraPay通道方的中间账户金额
        TP_before_balance = self.client.terrapayQueryAccountBalance()
        # 提交提现表单
        form_info, request_body = self.client.submitOrderForm(submitId, payOrderId, payCurrency, payAmount, outCurrency,
                                                              outInfo)
        self.checkStandardCodeMessage(form_info)
        # 等待订单完成
        form_id = form_info["data"]["formId"]
        self.waitUntilTerraPayRedeemOrderCompleted(form_id, db_name=db_name)
        # 根据submitId查询订单信息
        form_info_1 = self.client.queryFormByClientID(submitId)
        self.checkStandardCodeMessage(form_info_1)
        self.assertEqual(form_info_1['data']['state'], 'finish')
        # 查询转账后出金账户资产
        account_balance2 = self.rpsClient.getRoAccountBalance(source_account, "USD")

        self.client.logger.info(f"赎回后的资产: {account_balance2}, 变化了: {account_balance - account_balance2}")
        self.assertAlmostEqual(account_balance - account_balance2, payAmount, places=2, msg="账户资产变化与最初提交订单金额不符")
        # self.checkSubmitOrderFormInfoRedeem(payAmount, outMethod, outCurrency, form_id, form_info_1, request_body,
        #                                     db_name)
        self.checkOrderByTerrapay(form_info_1, outCurrency, payAmount, TP_before_balance, db_name)

    def test_074_terrapay_id_bank_submitOrderForm(self):
        """
        :提交表单接口→提现, 赎回业务, Detail必填，经校验过的正确参数，RoUSD->IDR，bank出金方式
        """
        submitId = "test" + str(int(time.time() * 1000))
        payCurrency = RSSData.terrapay_out_currency["ro"][0]
        outCurrency = RSSData.terrapay_out_currency["fait"][2]
        outInfo = RSSData.terrapay_out_bank_info[outCurrency]
        payAmount = float(outInfo["amount"])
        # fee = 5  # RSS费+通道费=5,暂时固定写死，后期优化动态读取
        # actual_amount = round(payAmount - fee, 2)
        country = (outInfo["receiverCountry"]).lower()
        db_name = "sn-{}-roxe-roxe".format(country)
        self.client.handle_host(country)
        source_account = RSSData.user_account
        target_account = RSSData.custody_account
        # 校验出金表单
        check_res = self.client.checkPayoutForm(outCurrency, outInfo)
        self.checkStandardCodeMessage(check_res)
        self.assertTrue(check_res["data"])
        # 查询转账前出金账户资产
        account_balance = self.rpsClient.getRoAccountBalance(source_account, "USD")
        self.client.logger.info(f"赎回前的资产: {account_balance}")
        # 转账到中间账户，并获取提交订单所需参数payOrderId
        pay_order = self.rpsClient.submitPayOrderTransferToRoxeAccount(source_account, target_account, payAmount, "USD",
                                                                       "transfer")
        payOrderId = pay_order["serviceChannelOrderId"]
        # 查询表单提交前在TerraPay通道方的中间账户金额
        TP_before_balance = self.client.terrapayQueryAccountBalance()
        # 提交提现表单
        form_info, request_body = self.client.submitOrderForm(submitId, payOrderId, payCurrency, payAmount, outCurrency,
                                                              outInfo)
        self.checkStandardCodeMessage(form_info)
        # 等待订单完成
        form_id = form_info["data"]["formId"]
        self.waitUntilTerraPayRedeemOrderCompleted(form_id, db_name=db_name)
        # 根据submitId查询订单信息
        form_info_1 = self.client.queryFormByClientID(submitId)
        time.sleep(2)
        self.checkStandardCodeMessage(form_info_1)
        self.assertEqual(form_info_1['data']['state'], 'finish')
        # 查询转账后出金账户资产
        account_balance2 = self.rpsClient.getRoAccountBalance(source_account, "USD")
        change_amount = round(account_balance - account_balance2, 2)
        self.client.logger.info(f"赎回后的资产: {account_balance2}, 变化了: {change_amount}")
        self.assertAlmostEqual(account_balance - account_balance2, payAmount, places=2, msg="账户资产变化与最初提交订单金额不符")
        # self.checkSubmitOrderFormInfoRedeem(payAmount, outMethod, outCurrency, form_id, form_info_1, request_body,
        #                                     db_name)
        self.checkOrderByTerrapay(form_info_1, outCurrency, payAmount, TP_before_balance, db_name)

    def test_075_terrapay_cn_wallet_submitOrderForm(self):
        """
        :提交表单接口→提现, 赎回业务, Detail必填，经校验过的正确参数，RoUSD->CNY，wallet出金方式
        """
        submitId = "test" + str(int(time.time() * 1000))
        payCurrency = RSSData.terrapay_out_currency["ro"][0]
        outCurrency = RSSData.terrapay_out_currency["fait"][0]
        outInfo = RSSData.terrapay_out_wallet_info[outCurrency]
        payAmount = float(outInfo["amount"])
        # fee = 6  # RSS费+通道费=6,暂时固定写死，后期优化动态读取
        # actual_amount = round(payAmount - fee, 2)
        country = (outInfo["receiverCountry"]).lower()
        db_name = "sn-{}-roxe-roxe".format(country)
        self.client.handle_host(country)
        source_account = RSSData.user_account
        target_account = RSSData.custody_account
        # 校验出金表单
        check_res = self.client.checkPayoutForm(outCurrency, outInfo)
        self.checkStandardCodeMessage(check_res)
        self.assertTrue(check_res["data"])
        # 查询转账前出金账户资产
        account_balance = self.rpsClient.getRoAccountBalance(source_account, "USD")
        self.client.logger.info(f"赎回前的资产: {account_balance}")
        # 转账到中间账户，并获取提交订单所需参数payOrderId
        pay_order = self.rpsClient.submitPayOrderTransferToRoxeAccount(source_account, target_account, payAmount, "USD",
                                                                       "transfer")
        payOrderId = pay_order["serviceChannelOrderId"]
        # 查询表单提交前在TerraPay通道方的中间账户金额
        TP_before_balance = self.client.terrapayQueryAccountBalance()
        # 提交提现表单
        form_info, request_body = self.client.submitOrderForm(submitId, payOrderId, payCurrency, payAmount, outCurrency,
                                                              outInfo)
        self.checkStandardCodeMessage(form_info)
        # 等待订单完成
        form_id = form_info["data"]["formId"]
        self.waitUntilTerraPayRedeemOrderCompleted(form_id, db_name=db_name)
        # 根据submitId查询订单信息
        form_info_1 = self.client.queryFormByClientID(submitId)
        self.checkStandardCodeMessage(form_info_1)
        self.assertEqual(form_info_1['data']['state'], 'finish')
        # 查询转账后出金账户资产
        account_balance2 = self.rpsClient.getRoAccountBalance(source_account, "USD")
        change_amount = round(account_balance - account_balance2, 2)
        self.client.logger.info(f"赎回后的资产: {account_balance2}, 变化了: {change_amount}")
        self.assertAlmostEqual(account_balance - account_balance2, payAmount, places=2, msg="账户资产变化与最初提交订单金额不符")
        # self.checkSubmitOrderFormInfoRedeem(payAmount, outMethod, outCurrency, form_id, form_info_1, request_body,
        #                                     db_name)
        self.checkOrderByTerrapay(form_info_1, outCurrency, payAmount, TP_before_balance, db_name)

    def test_076_terrapay_cn_bank_submitOrderForm(self):
        """
        :提交表单接口→提现, 赎回业务, Detail必填，经校验过的正确参数，RoUSD->CNY，bank出金方式
        """
        submitId = "test" + str(int(time.time() * 1000))
        payCurrency = RSSData.terrapay_out_currency["ro"][0]
        outCurrency = RSSData.terrapay_out_currency["fait"][0]
        outInfo = RSSData.terrapay_out_bank_info[outCurrency]
        payAmount = float(outInfo["amount"])
        # fee = 5  # RSS费+通道费=5,暂时固定写死，后期优化动态读取
        # actual_amount = round(payAmount - fee, 2)
        country = (outInfo["receiverCountry"]).lower()
        db_name = "sn-{}-roxe-roxe".format(country)
        self.client.handle_host(country)
        source_account = RSSData.user_account
        target_account = RSSData.custody_account
        # 校验出金表单
        check_res = self.client.checkPayoutForm(outCurrency, outInfo)
        self.checkStandardCodeMessage(check_res)
        self.assertTrue(check_res["data"])
        # 查询转账前出金账户资产
        account_balance = self.rpsClient.getRoAccountBalance(source_account, "USD")
        self.client.logger.info(f"赎回前的资产: {account_balance}")
        # 转账到中间账户，并获取提交订单所需参数payOrderId
        pay_order = self.rpsClient.submitPayOrderTransferToRoxeAccount(source_account, target_account, payAmount, "USD",
                                                                       "transfer")
        payOrderId = pay_order["serviceChannelOrderId"]
        # 查询表单提交前在TerraPay通道方的中间账户金额
        TP_before_balance = self.client.terrapayQueryAccountBalance()
        # 提交提现表单
        form_info, request_body = self.client.submitOrderForm(submitId, payOrderId, payCurrency, payAmount, outCurrency,
                                                              outInfo)
        self.checkStandardCodeMessage(form_info)
        # 等待订单完成
        form_id = form_info["data"]["formId"]
        self.waitUntilTerraPayRedeemOrderCompleted(form_id, db_name=db_name)
        # 根据submitId查询订单信息
        form_info_1 = self.client.queryFormByClientID(submitId)
        time.sleep(2)
        self.checkStandardCodeMessage(form_info_1)
        self.assertEqual(form_info_1['data']['state'], 'finish')
        # 查询转账后出金账户资产
        account_balance2 = self.rpsClient.getRoAccountBalance(source_account, "USD")
        change_amount = round(account_balance - account_balance2, 2)
        self.client.logger.info(f"赎回后的资产: {account_balance2}, 变化了: {change_amount}")
        self.assertAlmostEqual(account_balance - account_balance2, payAmount, places=2, msg="账户资产变化与最初提交订单金额不符")
        # self.checkSubmitOrderFormInfoRedeem(payAmount, outMethod, outCurrency, form_id, form_info_1, request_body,
        #                                     db_name)
        self.checkOrderByTerrapay(form_info_1, outCurrency, payAmount, TP_before_balance, db_name)

    def test_077_terrapay_in_bank_submitOrderForm(self):
        """
        :提交表单接口→提现, 赎回业务, Detail必填，经校验过的正确参数，RoUSD->CNY，bank出金方式
        """
        submitId = "test" + str(int(time.time() * 1000))
        payCurrency = RSSData.terrapay_out_currency["ro"][0]
        outCurrency = RSSData.terrapay_out_currency["fait"][5]
        outInfo = RSSData.terrapay_out_bank_info[outCurrency]
        payAmount = float(outInfo["amount"])
        # fee = 5  # RSS费+通道费=5,暂时固定写死，后期优化动态读取
        # actual_amount = round(payAmount - fee, 2)
        country = (outInfo["receiverCountry"]).lower()
        db_name = "sn-{}-roxe-roxe".format(country)
        self.client.handle_host(country)
        source_account = RSSData.user_account
        target_account = RSSData.custody_account
        # 校验出金表单
        check_res = self.client.checkPayoutForm(outCurrency, outInfo)
        self.checkStandardCodeMessage(check_res)
        self.assertTrue(check_res["data"])
        # 查询转账前出金账户资产
        account_balance = self.rpsClient.getRoAccountBalance(source_account, "USD")
        self.client.logger.info(f"赎回前的资产: {account_balance}")
        # 转账到中间账户，并获取提交订单所需参数payOrderId
        pay_order = self.rpsClient.submitPayOrderTransferToRoxeAccount(source_account, target_account, payAmount, "USD",
                                                                       "transfer")
        payOrderId = pay_order["serviceChannelOrderId"]
        # 查询表单提交前在TerraPay通道方的中间账户金额
        TP_before_balance = self.client.terrapayQueryAccountBalance()
        # 提交提现表单
        form_info, request_body = self.client.submitOrderForm(submitId, payOrderId, payCurrency, payAmount, outCurrency,
                                                              outInfo)
        self.checkStandardCodeMessage(form_info)
        # 等待订单完成
        form_id = form_info["data"]["formId"]
        self.waitUntilTerraPayRedeemOrderCompleted(form_id, db_name=db_name)
        # 根据submitId查询订单信息
        form_info_1 = self.client.queryFormByClientID(submitId)
        time.sleep(2)
        self.checkStandardCodeMessage(form_info_1)
        self.assertEqual(form_info_1['data']['state'], 'finish')
        # 查询转账后出金账户资产
        account_balance2 = self.rpsClient.getRoAccountBalance(source_account, "USD")
        change_amount = round(account_balance - account_balance2, 2)
        self.client.logger.info(f"赎回后的资产: {account_balance2}, 变化了: {change_amount}")
        self.assertAlmostEqual(account_balance - account_balance2, payAmount, places=2, msg="账户资产变化与最初提交订单金额不符")
        # self.checkSubmitOrderFormInfoRedeem(payAmount, outMethod, outCurrency, form_id, form_info_1, request_body,
        #                                     db_name)
        self.checkOrderByTerrapay(form_info_1, outCurrency, payAmount, TP_before_balance, db_name)

    def test_078_terrapay_my_bank_submitOrderForm(self):
        """
        :提交表单接口→提现, 赎回业务, Detail必填，经校验过的正确参数，RoUSD->CNY，bank出金方式
        """
        submitId = "test" + str(int(time.time() * 1000))
        payCurrency = RSSData.terrapay_out_currency["ro"][0]
        outCurrency = RSSData.terrapay_out_currency["fait"][3]
        outInfo = RSSData.terrapay_out_bank_info[outCurrency]
        payAmount = float(outInfo["amount"])
        # fee = 5  # RSS费+通道费=5,暂时固定写死，后期优化动态读取
        # actual_amount = round(payAmount - fee, 2)
        country = (outInfo["receiverCountry"]).lower()
        db_name = "sn-{}-roxe-roxe".format(country)
        self.client.handle_host(country)
        source_account = RSSData.user_account
        target_account = RSSData.custody_account
        # 校验出金表单
        check_res = self.client.checkPayoutForm(outCurrency, outInfo)
        self.checkStandardCodeMessage(check_res)
        self.assertTrue(check_res["data"])
        # 查询转账前出金账户资产
        account_balance = self.rpsClient.getRoAccountBalance(source_account, "USD")
        self.client.logger.info(f"赎回前的资产: {account_balance}")
        # 转账到中间账户，并获取提交订单所需参数payOrderId
        pay_order = self.rpsClient.submitPayOrderTransferToRoxeAccount(source_account, target_account, payAmount, "USD",
                                                                       "transfer")
        payOrderId = pay_order["serviceChannelOrderId"]
        # 查询表单提交前在TerraPay通道方的中间账户金额
        TP_before_balance = self.client.terrapayQueryAccountBalance()
        # 提交提现表单
        form_info, request_body = self.client.submitOrderForm(submitId, payOrderId, payCurrency, payAmount, outCurrency,
                                                              outInfo)
        self.checkStandardCodeMessage(form_info)
        # 等待订单完成
        form_id = form_info["data"]["formId"]
        self.waitUntilTerraPayRedeemOrderCompleted(form_id, db_name=db_name)
        # 根据submitId查询订单信息
        form_info_1 = self.client.queryFormByClientID(submitId)
        time.sleep(2)
        self.checkStandardCodeMessage(form_info_1)
        self.assertEqual(form_info_1['data']['state'], 'finish')
        # 查询转账后出金账户资产
        account_balance2 = self.rpsClient.getRoAccountBalance(source_account, "USD")
        change_amount = round(account_balance - account_balance2, 2)
        self.client.logger.info(f"赎回后的资产: {account_balance2}, 变化了: {change_amount}")
        self.assertAlmostEqual(account_balance - account_balance2, payAmount, places=2, msg="账户资产变化与最初提交订单金额不符")
        # self.checkSubmitOrderFormInfoRedeem(payAmount, outMethod, outCurrency, form_id, form_info_1, request_body,
        #                                     db_name)
        self.checkOrderByTerrapay(form_info_1, outCurrency, payAmount, TP_before_balance, db_name)

    def test_079_terrapay_th_bank_submitOrderForm(self):
        """
        :提交表单接口→提现, 赎回业务, Detail必填，经校验过的正确参数，RoUSD->CNY，bank出金方式
        """
        submitId = "test" + str(int(time.time() * 1000))
        payCurrency = RSSData.terrapay_out_currency["ro"][0]
        outCurrency = RSSData.terrapay_out_currency["fait"][4]
        outInfo = RSSData.terrapay_out_bank_info[outCurrency]
        payAmount = float(outInfo["amount"])
        # payAmount = 9.5
        # fee = 5  # RSS费+通道费=5,暂时固定写死，后期优化动态读取
        # actual_amount = round(payAmount - fee, 2)
        country = (outInfo["receiverCountry"]).lower()
        db_name = "sn-{}-roxe-roxe".format(country)
        self.client.handle_host(country)
        source_account = RSSData.user_account
        target_account = RSSData.custody_account
        # 校验出金表单
        check_res = self.client.checkPayoutForm(outCurrency, outInfo)
        self.checkStandardCodeMessage(check_res)
        self.assertTrue(check_res["data"])
        # 查询转账前出金账户资产
        account_balance = self.rpsClient.getRoAccountBalance(source_account, "USD")
        self.client.logger.info(f"赎回前的资产: {account_balance}")
        # 转账到中间账户，并获取提交订单所需参数payOrderId
        pay_order = self.rpsClient.submitPayOrderTransferToRoxeAccount(source_account, target_account, payAmount, "USD",
                                                                       "transfer")
        payOrderId = pay_order["serviceChannelOrderId"]
        # 查询表单提交前在TerraPay通道方的中间账户金额
        TP_before_balance = self.client.terrapayQueryAccountBalance()
        # 提交提现表单
        form_info, request_body = self.client.submitOrderForm(submitId, payOrderId, payCurrency, payAmount, outCurrency,
                                                              outInfo)
        self.checkStandardCodeMessage(form_info)
        # 等待订单完成
        form_id = form_info["data"]["formId"]
        self.waitUntilTerraPayRedeemOrderCompleted(form_id, db_name=db_name)
        # 根据submitId查询订单信息
        form_info_1 = self.client.queryFormByClientID(submitId)
        time.sleep(2)
        self.checkStandardCodeMessage(form_info_1)
        self.assertEqual(form_info_1['data']['state'], 'finish')
        # 查询转账后出金账户资产
        account_balance2 = self.rpsClient.getRoAccountBalance(source_account, "USD")
        change_amount = round(account_balance - account_balance2, 2)
        self.client.logger.info(f"赎回后的资产: {account_balance2}, 变化了: {change_amount}")
        self.assertAlmostEqual(account_balance - account_balance2, payAmount, places=2, msg="账户资产变化与最初提交订单金额不符")
        # self.checkSubmitOrderFormInfoRedeem(payAmount, outMethod, outCurrency, form_id, form_info_1, request_body,
        #                                     db_name)
        self.checkOrderByTerrapay(form_info_1, outCurrency, payAmount, TP_before_balance, db_name)

    def test_data(self):
        # FEEINFO = self.client.getChannelFee("TERRAPAY", "INR")
        # print(FEEINFO)
        pass

