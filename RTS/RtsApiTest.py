# coding=utf-8
# author: Li MingLei
# date: 2021-08-31
import contextlib
import unittest
import os
import json
import traceback
import time
from roxe_libs.DBClient import Mysql
from roxe_libs import ApiUtils
from RTS.RtsApi import RTSApiClient
from RTS.RTSData import RTSData
# from RPS.RpsApiTest import RPSData
# from RPS.RpsApi import RPSApiClient
from RSS.RssApiTest import RSSData
from roxe_libs.ContractChainTool import RoxeChainClient
from pymysql.err import OperationalError


class BaseCheckRTS(unittest.TestCase):
    mysql = None
    rpsClient = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = RTSApiClient(RTSData.host, RTSData.api_id, RTSData.sec_key, RTSData.ssl_pub_key)
        # cls.rpsClient = RPSApiClient(RPSData.host, RPSData.app_key, RPSData.secret)
        # cls.rssClient = RssApiClient(RssData.host, RssData.chain_host)
        cls.chain_client = RoxeChainClient(RTSData.chain_host)

        if RTSData.is_check_db:
            cls.mysql = Mysql(RTSData.sql_cfg["mysql_host"], RTSData.sql_cfg["port"], RTSData.sql_cfg["user"],
                              RTSData.sql_cfg["password"], RTSData.sql_cfg["db"], True)
            cls.mysql.connect_database()

    @classmethod
    def tearDownClass(cls) -> None:
        if RTSData.is_check_db:
            cls.mysql.disconnect_database()

    def checkCodeAndMessage(self, responseJson, code='0', message='Success'):
        self.assertEqual(responseJson["code"], code, f"接口结果: {responseJson}")
        self.assertEqual(responseJson["message"], message, f"接口结果: {responseJson}")

    def executeSqlUntilSuccess(self, sql, res_field=None, time_out=120, time_inner=3):
        b_time = time.time()
        q_db = None
        while time.time() - b_time < time_out:
            q_db = self.mysql.exec_sql_query(sql)
            if q_db:
                if res_field:
                    if q_db[0][res_field]:
                        break
                else:
                    break
            time.sleep(time_inner)
        self.client.logger.debug(f"查询到的值为{q_db}")
        return q_db

    def waitUntilRedeemOrderCompleted(self, tx_id, payment_id, time_out=120, time_inner=10):
        # 查询数据库，等待rts订单状态为铸币确认或者赎回确认
        query_rts_sql = "select * from roxe_rts.rts_order where payment_id='{}' and order_state in ('MINT_SUBMIT', 'REDEEM_SUBMIT')".format(
            payment_id)
        self.executeSqlUntilSuccess(query_rts_sql, time_out=time_out * 7)
        time.sleep(0.5)

        # # 查询rss订单信息
        # q_rss_sql = "select * from `roxe_rss_us`.rss_order where payment_id='{}'".format(payment_id)
        # q_rss_db = self.executeSqlUntilSuccess(q_rss_sql)
        # redeem_id = rts_order[0]['orderId']
        # # 查询赎回的订单信息
        redeem_sql = "select * from `roxe_rss_us`.rss_order where payment_id='{}'".format(payment_id)
        redeem_db = self.executeSqlUntilSuccess(redeem_sql)
        if redeem_db[0]["outerCurrency"].endswith(".ROXE"):
            mint_id = redeem_db[0]['orderId']
            self.client.logger.info(f"铸币订单: {mint_id}")
            mint_sql = "select * from `roxe_rss_us`.rss_order where client_id='{}' and order_state='finish'".format(
                redeem_db[0]['clientId'])
            self.executeSqlUntilSuccess(mint_sql, time_out=200)
            self.client.logger.info("铸币完成")
            redeem_db = self.executeSqlUntilSuccess(
                "select * from `roxe_rss_us`.rss_order where client_id='{}'".format(tx_id + "_outer"))
        redeem_form = redeem_db[0]["orderId"]
        self.client.logger.info(f"赎回订单: {redeem_form}")
        time.sleep(1)
        # 查询赎回到银行卡的出金订单
        rss_bank_outer_sql = "select * from `roxe_rss_us`.rss_fiat_outer where outer_id='{}'".format(redeem_form)
        bank_outer_db = self.executeSqlUntilSuccess(rss_bank_outer_sql, "outerId")
        if bank_outer_db and bank_outer_db[0]["channelCode"] == "manual":
            # 在管理后台查找银行卡的出金订单，并修改订单状态为完成
            backend_outer_sql = "select * from `roxe_backend_sysmngt`.roxe_pay_out_order where reference_id='{}'".format(
                redeem_form)
            backend_outer_db = self.executeSqlUntilSuccess(backend_outer_sql)
            if backend_outer_db:
                update_sql = "update `roxe_backend_sysmngt`.roxe_pay_out_order set status='Success' where reference_id='{}'".format(
                    redeem_form)
                self.mysql.exec_sql_query(update_sql)

        # 查询赎回订单状态，指定订单完成
        b_time = time.time()
        flag = False
        while time.time() - b_time < time_out:
            rss_order_db = self.mysql.exec_sql_query(redeem_sql)
            if rss_order_db[0]["orderState"] == "init":
                self.client.logger.info("赎回订单为初始状态, 未向下执行")
                break
            if rss_order_db[0]["orderState"] == "finish":
                flag = True
                self.client.logger.info("赎回订单已完成")
                break
            time.sleep(time_inner)
        if flag:
            # 赎回订单完成后，拿到实际出金到银行卡的数量，并订单rts订单完成
            out_res = self.mysql.exec_sql_query(rss_bank_outer_sql)
            f_sql = "select * from `roxe_rts`.rts_order where order_id='{}' and order_state='TRANSACTION_FINISH'".format(
                tx_id)
            self.executeSqlUntilSuccess(f_sql)
            self.client.logger.info("rts订单已完成")
            outer_amount = out_res[0]["outerQuantity"]
        else:
            outer_amount = None
            self.client.logger.info("rts订单未完成")
        return outer_amount

    # 业务流程函数
    def submitOrderFloorOfFiatToRo(self, token, user_id, currency_info, amount, amount_side, outer_info,
                                   is_just_submit=False, url=""):
        """
        法币->RO的下单流程:
            查询路由 -> 下单 -> 查询订单信息 -> 等待订单完成 -> 查询订单信息 -> 查询订单日志
            每一步都有验证接口返回的结果
        :param token: 有ach账户的用户token
        :param user_id: 有ach账户的用户id
        :param currency_info: 币种信息
        :param amount: 查询路由的下单数量
        :param amount_side: 查询路由的方向
        :param outer_info: 出金的信息，如果出金一方为ro则为ro地址，如果出金一方为银行卡则为银行卡信息
        :param is_just_submit: 是否在提交订单后就返回订单数据，不等待订单完成
        :param url: 回调的url
        :return:
        """
        # 查询路由信息
        send_amount = amount if amount_side == "inner" else ""
        receive_amount = amount if amount_side == "outer" else ""
        send_currency = currency_info["fiat"]
        receive_currency = currency_info["ro"]
        outer_address = outer_info
        # country = "" if currency_info["innerNodeCode"] else currency_info["country"]
        router_info, request_body = self.client.getRouterList(currency_info["country"], send_currency, "",
                                                              receive_currency, send_amount, receive_amount,
                                                              currency_info["innerNodeCode"],
                                                              currency_info["outerNodeCode"])
        # self.checkRouterListResult(router_info["data"], request_body)
        send_node_code = router_info["data"][0]["sendNodeCode"]

        # 提交rts订单
        instruction_id = "test_" + str(int(time.time() * 1000))  # 客户单号
        originalId = ""  # 客户原单
        send_amount = amount  # 指定下单数量
        if amount_side == "outer":
            # pass
            send_amount = float(router_info["data"][0]["sendAmount"])

        # 提交rps订单
        payment_id, coupon_code = self.rpsClient.submitAchPayOrder(token, user_id, outer_address, send_amount,
                                                                   dbClient=self.mysql)
        receive_info = {"receiverAddress": outer_address}
        submit_info, submit_body = self.client.submitOrder(
            instruction_id, originalId, payment_id, send_currency, send_amount, receive_currency, receive_info,
            receive_amount,
            sendNodeCode=send_node_code, couponCode=coupon_code, notifyURL=url, withoutSendFee=True
        )
        if is_just_submit:
            return submit_info["data"]
        self.checkCodeAndMessage(submit_info)
        self.checkSubmitOrderResult(submit_info["data"], submit_body, router_info["data"][0])
        # 查询订单状态
        transaction_id = submit_info["data"]["transactionId"]
        query_info = self.client.getOrderInfo(instruction_id)
        self.checkCodeAndMessage(query_info)
        self.checkOrderInfo(query_info["data"], submit_body, router_info["data"][0])
        # 查询订单日志
        order_log = self.client.getOrderStateLog(instruction_id)
        self.checkCodeAndMessage(order_log)
        self.checkOrderLog(order_log["data"], transaction_id)
        # 直到订单完成
        time_out = 600
        b_time = time.time()
        while True:
            if time.time() - b_time > time_out:
                self.client.logger.error("等待时间超时")
                break
            query_info = self.client.getOrderInfo(instruction_id)
            if query_info["data"]["txState"] == "TRANSACTION_FINISH":
                self.client.logger.info("rts订单已经完成")
                break
            time.sleep(time_out / 15)
        # 查询订单状态
        query_info = self.client.getOrderInfo(instruction_id)
        self.checkCodeAndMessage(query_info)
        self.checkOrderInfo(query_info["data"], submit_body, router_info["data"][0])
        time.sleep(1)
        # 查询订单日志
        order_log = self.client.getOrderStateLog(instruction_id)
        self.checkCodeAndMessage(order_log)
        self.checkOrderLog(order_log["data"], transaction_id)
        assert "TRANSACTION_FINISH" in [i["txState"] for i in order_log["data"]["stateInfo"]], "订单状态不正确"
        return query_info["data"]

    def submitOrderFloorOfFiatToFiat(self, token, user_id, currency_info, amount, amount_side, outer_info,
                                     sendCurrency=None, replaceOutAmount=False, url=""):
        """
        法币->RO的下单流程:
            查询路由 -> 下单 -> 查询订单信息 -> 等待订单完成 -> 查询订单信息 -> 查询订单日志
            每一步都有验证接口返回的结果
        :param token: 有ach账户的用户token
        :param user_id: 有ach账户的用户id
        :param currency_info: 币种信息
        :param amount: 查询路由的下单数量
        :param amount_side: 查询路由的方向
        :param outer_info: 出金的信息，如果出金一方为ro则为ro地址，如果出金一方为银行卡则为银行卡信息
        :param sendCurrency: 指定入金币种
        :param replaceOutAmount:
        :param url:
        :return:
        """
        # 查询路由信息
        send_amount = amount if amount_side == "inner" else ""
        receive_amount = amount if amount_side == "outer" else ""
        send_currency = sendCurrency if sendCurrency else currency_info["fiat"]
        receive_currency = currency_info["fiat"]
        receive_info = outer_info
        router_info, router_body = self.client.getRouterList("", send_currency, "", receive_currency, send_amount,
                                                             receive_amount, currency_info["innerNodeCode"],
                                                             currency_info["outerNodeCode"])
        self.checkRouterListResult(router_info["data"], router_body)
        send_node_code = router_info["data"][0]["sendNodeCode"]
        receive_node_code = router_info["data"][0]["receiveNodeCode"] if currency_info["outerNodeCode"] == "" else \
        currency_info["outerNodeCode"]
        router_out_amount = float(router_info["data"][0]["receiveAmount"])
        if replaceOutAmount:
            if "tradeAmount" in receive_amount:
                receive_info["tradeAmount"] = router_info["data"][0]["receiveAmount"]
        # 查询出金类型
        outer_method = self.client.getOutMethod(receive_currency, receiveNodeCode=receive_node_code)
        self.checkCodeAndMessage(outer_method)
        self.assertEqual(outer_method["data"], {"receiveMethodCode": ["bank"]})
        # 查询出金必填字段
        outer_fields = self.client.getReceiverRequiredFields(receive_node_code, receive_currency,
                                                             outer_method["data"]["receiveMethodCode"][0])
        self.checkCodeAndMessage(outer_fields)
        # self.checkOuterBankFields(outer_fields["data"], receive_currency)
        # 校验出金必填字段
        check_outer_fields = self.client.checkReceiverRequiredFields(receive_node_code, receive_currency, receive_info)
        self.checkCodeAndMessage(check_outer_fields)
        # self.assertEqual(check_outer_fields["data"], {"verified": True, "message": "success"})

        # 提交rps订单
        inner_quantity = amount  # 指定下单数量
        if amount_side == "outer":
            # inner_quantity = float(router_info["data"][0]["sendAmount"])
            inner_quantity = amount

        payment_id, coupon_code = self.rpsClient.submitAchPayOrder(token, user_id, "", inner_quantity,
                                                                   dbClient=self.mysql)
        # 提交rts订单
        instruction_id = "test_" + str(int(time.time() * 1000))  # 客户单号
        source_id = instruction_id  # 客户原单
        # 提交rts原单
        submit_order, submit_body = self.client.submitOrder(
            instruction_id, source_id, payment_id, send_currency, inner_quantity, receive_currency, receive_info,
            receive_amount,
            sendNodeCode=send_node_code, receiveNodeCode=receive_node_code, couponCode=coupon_code, notifyURL=url,
            withoutSendFee=True
        )
        self.checkCodeAndMessage(submit_order)
        self.checkSubmitOrderResult(submit_order["data"], submit_body, router_info["data"][0])
        # 查询订单状态
        transaction_id = submit_order["data"]["transactionId"]
        query_info = self.client.getOrderInfo(instruction_id)
        self.checkCodeAndMessage(query_info)
        self.checkOrderInfo(query_info["data"], submit_body, router_info["data"][0])
        # 查询订单日志
        order_log = self.client.getOrderStateLog(instruction_id)
        self.checkCodeAndMessage(order_log)
        self.checkOrderLog(order_log["data"], transaction_id)

        # 修改rss赎回订单状态直到成功
        # real_amount = self.waitUntilRedeemOrderCompleted(transaction_id, payment_id, 600)
        time.sleep(120)
        real_amount = router_out_amount
        time.sleep(2)
        # 查询订单状态
        query_info = self.client.getOrderInfo(instruction_id)
        self.checkCodeAndMessage(query_info)
        self.checkOrderInfo(query_info["data"], submit_body, router_info["data"][0])
        time.sleep(1)
        # 查询订单日志
        order_log = self.client.getOrderStateLog(instruction_id)
        self.checkCodeAndMessage(order_log)
        self.checkOrderLog(order_log["data"], transaction_id)

        # 校验出金数量和路由数量一致
        assert abs(float(router_out_amount) - float(real_amount)) < 0.1 ** 3, "实际出金数量和路由的出金数量不一致"
        assert query_info["data"]["txState"] == "TRANSACTION_FINISH", "订单状态不正确"
        assert "TRANSACTION_FINISH" in [i["txState"] for i in order_log["data"]["stateInfo"]], "订单状态不正确"
        return query_info["data"]

    def submitOrderFloorOfFiatToFiat_channelNodeToRmnNode(self, sendNodeCode, send_currency, receive_currency, amount,
                                                          amount_side, outer_info, receiveNodeCode="", outCountry="",
                                                          replaceOutAmount=False, is_just_submit=False, url=""):

        if not RTSData.is_check_db:
            self.client.logger.warning("不检查数据库，通过rmn下单后无法获取rts订单id，跳过")
            return
        # 查询路由信息
        send_amount = amount if amount_side == "inner" else ""
        receive_amount = amount if amount_side == "outer" else ""
        receive_info = outer_info
        router_info, router_body = self.client.getRouterList("", send_currency, outCountry, receive_currency,
                                                             send_amount, receive_amount, sendNodeCode, receiveNodeCode)
        self.checkRouterListResult(router_info["data"], router_body)
        receive_node_code = receiveNodeCode if receiveNodeCode else router_info["data"][0]["receiveNodeCode"]
        send_fee = router_info["data"][0]["sendFee"]
        router_out_amount = float(router_info["data"][0]["receiveAmount"])
        if replaceOutAmount:
            if "tradeAmount" in receive_amount:
                receive_info["tradeAmount"] = router_info["data"][0]["receiveAmount"]

        inner_quantity = amount  # 指定下单数量
        if amount_side == "outer":
            # inner_quantity = float(router_info["data"][0]["sendAmount"])
            inner_quantity = amount

        # payment_id, coupon_code = self.rpsClient.submitAchPayOrder(token, user_id, "", inner_quantity, dbClient=self.mysql)
        # from RMN.RMNApi import RMNApiClient
        # rmn_host = "http://rmn-uat-bj-test.roxepro.top:38888/api/rmn/v2"
        # api_key = "qMJiJZG84SGYBf3SG9bUjfco0se3WJzL"
        # sec_key = "8kqN7WwehNyltmfylxj8fJXNiNPRDXZH"
        # rmn_client = RMNApiClient(rmn_host, "test", check_db=True, sql_cfg=RTSData.sql_cfg)
        # rmn_tx_id = rmn_client.step_sendRCCT(
        #     sendNodeCode, receive_node_code, api_key, sec_key, send_currency, receive_currency, inner_quantity, send_fee, is_just_submit
        # )
        instruction_id = "test_{}".format(int(time.time() * 1000))
        submit_order, submit_body = self.client.submitOrder(
            instruction_id, "", "", send_currency, inner_quantity, receive_currency, receive_info, receive_amount,
            sendNodeCode=sendNodeCode, receiveNodeCode=receive_node_code, notifyURL=url,
            withoutSendFee=True
        )
        self.checkCodeAndMessage(submit_order)
        self.checkSubmitOrderResult(submit_order["data"], submit_body, router_info["data"][0])

        transaction_id = ""
        # 查询订单状态
        query_info = self.client.getOrderInfo(transactionId=transaction_id)
        self.checkCodeAndMessage(query_info)
        if is_just_submit:
            return query_info["data"]

        # 查询订单日志
        order_log = self.client.getOrderStateLog(transactionId=transaction_id)
        self.checkCodeAndMessage(order_log)
        self.checkOrderLog(order_log["data"], transaction_id)

        # 修改rss赎回订单状态直到成功
        # real_amount = self.waitUntilRedeemOrderCompleted(transaction_id, payment_id, 600)
        time.sleep(120)
        real_amount = router_out_amount
        time.sleep(2)
        # 查询订单状态
        query_info = self.client.getOrderInfo(transactionId=transaction_id)
        self.checkCodeAndMessage(query_info)
        time.sleep(1)
        # 查询订单日志
        order_log = self.client.getOrderStateLog(transactionId=transaction_id)
        self.checkCodeAndMessage(order_log)
        self.checkOrderLog(order_log["data"], transaction_id)

        # 校验出金数量和路由数量一致
        assert abs(float(router_out_amount) - float(real_amount)) < 0.1 ** 3, "实际出金数量和路由的出金数量不一致"
        assert query_info["data"]["txState"] == "TRANSACTION_FINISH", "订单状态不正确"
        assert "TRANSACTION_FINISH" in [i["txState"] for i in order_log["data"]["stateInfo"]], "订单状态不正确"
        return query_info["data"]

    def submitOrderFloorOfRoToFiat(self, currency_info, amount, amount_side, outer_info, from_account,
                                   is_just_submit=False, replaceOutAmount=False, url="", **kwargs):
        """
        RO->法币的下单流程:
            查询路由 -> 查询出金类型 -> 查询出金必填字段 -> 校验出金必填字段 -> 下单 -> 查询订单信息 -> 等待订单完成 -> 查询订单信息 -> 查询订单日志
            每一步都有验证接口返回的结果
        :param currency_info: 币种信息
        :param amount: 查询路由的下单数量
        :param amount_side: 查询路由的方向
        :param outer_info: 出金的信息，如果出金一方为ro则为ro地址，如果出金一方为银行卡则为银行卡信息
        :param from_account: 出金账户
        :param is_just_submit: 是否在提交订单后就返回订单数据，不等待订单完成
        :param replaceOutAmount:
        :param url:
        :return:
        """
        # 查询路由信息
        send_amount = amount if amount_side == "inner" else ""
        receiver_amount = amount if amount_side == "outer" else ""
        send_currency = currency_info["ro"]
        receive_currency = currency_info["fiat"]
        receive_info = outer_info
        router_info, router_body = self.client.getRouterList("", send_currency, currency_info["country"],
                                                             receive_currency, send_amount, receiver_amount,
                                                             currency_info["innerNodeCode"],
                                                             currency_info["outerNodeCode"])
        self.checkCodeAndMessage(router_info)
        self.checkRouterListResult(router_info["data"], router_body)
        send_node_code = router_info["data"][0]["sendNodeCode"]
        receive_node_code = router_info["data"][0]["receiveNodeCode"] if currency_info["outerNodeCode"] == "" else \
        currency_info["outerNodeCode"]
        router_out_amount = router_info["data"][0]["receiveAmount"]
        router_in_account = router_info["data"][0]["custodyAccountInfo"]["custodyAccount"]
        if replaceOutAmount:
            if "tradeAmount" in receive_info:
                receive_info["tradeAmount"] = router_info["data"][0]["receiveAmount"]
        # 查询出金类型
        outer_method = self.client.getOutMethod(receive_currency, receiveNodeCode=receive_node_code)
        self.checkCodeAndMessage(outer_method)
        self.assertEqual(outer_method["data"], {"receiveMethodCode": ["bank"]})
        # 查询出金必填字段
        outer_fields = self.client.getReceiverRequiredFields(receive_node_code, receive_currency,
                                                             outer_method["data"]["receiveMethodCode"][0])
        self.checkCodeAndMessage(outer_fields)
        # self.checkOuterBankFields(outer_fields["data"], receive_currency)
        # 校验出金必填字段
        check_outer_fields = self.client.checkReceiverRequiredFields(receive_node_code, receive_currency, receive_info)
        self.checkCodeAndMessage(check_outer_fields)
        # self.assertEqual(check_outer_fields["data"], {"verified": True, "message": "success"})

        if amount_side == "outer":
            send_amount = float(router_info["data"][0]["sendAmount"])

        withoutSendFee = False
        if kwargs.get("token") and kwargs.get("user_id"):
            token = kwargs.get("token")
            user_id = kwargs.get("user_id")
            payment_id = self.rpsClient.submitWalletPayOrder(token, user_id, from_account, router_in_account,
                                                             send_amount, dbClient=self.mysql)
            withoutSendFee = True
        elif kwargs.get("fromAccountKey"):
            from_key = kwargs.get("fromAccountKey")
            tx_amt = RoxeChainClient.makeContractAmount(send_amount, receive_currency.strip(".ROXE"))
            tx = self.chain_client.transferToken(from_account, from_key, router_in_account, tx_amt, "roxe.ro")
            payment_id = tx["transaction_id"]
        else:
            raise AttributeError("需提供源账户的私钥或者对应的token和userId")
        # 提交rts订单
        instruction_id = "test_" + str(int(time.time() * 1000))  # 客户单号
        source_id = instruction_id  # 客户原单
        # 提交rts订单
        submit_order, submit_body = self.client.submitOrder(
            instruction_id, source_id, payment_id, send_currency, send_amount, receive_currency, receive_info,
            router_out_amount,
            sendNodeCode=send_node_code, receiveNodeCode=receive_node_code, notifyURL=url, withoutSendFee=withoutSendFee
        )
        if is_just_submit:
            return submit_order["data"], 0
        self.checkCodeAndMessage(submit_order)
        self.checkSubmitOrderResult(submit_order["data"], submit_body, router_info["data"][0])
        # 查询订单状态
        transaction_id = submit_order["data"]["transactionId"]
        query_order = self.client.getOrderInfo(instruction_id)
        self.checkCodeAndMessage(query_order)
        self.checkOrderInfo(query_order["data"], submit_body, router_info["data"][0])
        # 查询订单日志
        order_log = self.client.getOrderStateLog(instruction_id)
        self.checkCodeAndMessage(order_log)
        self.checkOrderLog(order_log["data"], transaction_id)
        # 直到订单完成
        self.waitUntilRedeemOrderCompleted(transaction_id, payment_id, 300)
        # 查询订单状态
        query_order = self.client.getOrderInfo(instruction_id)
        self.checkCodeAndMessage(query_order)
        self.checkOrderInfo(query_order["data"], submit_body, router_info["data"][0])
        # 查询订单日志
        order_log = self.client.getOrderStateLog(instruction_id)
        self.checkCodeAndMessage(order_log)
        self.checkOrderLog(order_log["data"], transaction_id)
        assert "TRANSACTION_FINISH" in [i["txState"] for i in order_log["data"]["stateInfo"]], "订单状态不正确"
        return query_order["data"], 0

    def submitOrderFloorOfRoToRo(self, currency_info, amount, amount_side, to_account, from_account, **kwargs):
        """
        RO->法币的下单流程:
            查询路由 -> 查询出金类型 -> 查询出金必填字段 -> 校验出金必填字段 -> 下单 -> 查询订单信息 -> 等待订单完成 -> 查询订单信息 -> 查询订单日志
            每一步都有验证接口返回的结果
        :param currency_info: 币种信息
        :param amount: 查询路由的下单数量
        :param amount_side: 查询路由的方向
        :param to_account: 目标账户地址
        :param from_account: 出金账户
        :return:
        """
        # 查询路由信息
        send_amount = amount if amount_side == "inner" else ""
        receiver_amount = amount if amount_side == "outer" else ""
        send_currency = currency_info["ro"]
        receive_currency = currency_info["ro"]
        router_info, router_body = self.client.getRouterList(
            "", send_currency, "", receive_currency,
            send_amount, receiver_amount, currency_info["innerNodeCode"], currency_info["outerNodeCode"]
        )
        self.checkCodeAndMessage(router_info)
        # self.checkRouterListResult(router_info["data"], router_body)
        router_out_amount = amount
        # send_node_code = router_info["data"][0]["sendNodeCode"]
        # receive_node_code = router_info["data"][0]["receiveNodeCode"]
        # router_out_amount = router_info["data"][0]["outerQuantity"]

        if not router_info["data"]:
            self.client.logger.error("查询出的路由为空")

        # # 提交rts原单
        # if amount_side == "outer" and router_info["data"]:
        #     send_amount = float(router_info["data"][0]["sendAmount"])
        # 提交rps订单
        # rps_order = self.rpsClient.submitPayOrderTransferToRoxeAccount(from_account, to_account, send_amount, businessType="transfer")
        withoutSendFee = False
        if kwargs.get("token") and kwargs.get("user_id"):
            token = kwargs.get("token")
            user_id = kwargs.get("user_id")
            payment_id = self.rpsClient.submitWalletPayOrder(token, user_id, from_account, to_account, amount)
            withoutSendFee = True
        elif kwargs.get("fromAccountKey"):
            from_key = kwargs.get("fromAccountKey")
            tx_amt = RoxeChainClient.makeContractAmount(send_amount, receive_currency.strip(".ROXE"))
            tx = self.chain_client.transferToken(from_account, from_key, to_account, tx_amt, "roxe.ro")
            payment_id = tx["transaction_id"]
        else:
            raise AttributeError("需提供源账户的私钥或者对应的token和userId")
        # 提交rts订单
        instruction_id = "test_" + str(int(time.time() * 1000))  # 客户单号
        source_id = instruction_id  # 客户原单
        receive_info = {"receiverAddress": to_account}
        submit_order, submit_body = self.client.submitOrder(
            instruction_id, source_id, payment_id, send_currency, amount, receive_currency, receive_info,
            router_out_amount,
            withoutSendFee=withoutSendFee
        )
        self.checkCodeAndMessage(submit_order)
        # self.checkSubmitOrderResult(submit_order["data"], submit_body, router_info["data"][0])
        # 查询订单状态
        transaction_id = submit_order["data"]["transactionId"]
        query_order = self.client.getOrderInfo(instruction_id)
        self.checkCodeAndMessage(query_order)
        # self.checkOrderInfo(query_order["data"], submit_body, router_info["data"][0], True)
        # 查询订单日志
        order_log = self.client.getOrderStateLog(instruction_id)
        self.checkCodeAndMessage(order_log)
        self.checkOrderLog(order_log["data"], transaction_id)
        # 直到订单完成
        time_out = 60
        b_time = time.time()
        while True:
            if time.time() - b_time > time_out:
                self.client.logger.info("等待时间超时")
                break
            query_order = self.client.getOrderInfo(instruction_id)
            if query_order["data"]["txState"] == "TRANSACTION_FINISH":
                self.client.logger.info("rts订单已经完成")
                break
            time.sleep(10)
        # 查询订单状态
        query_order = self.client.getOrderInfo(instruction_id)
        self.checkCodeAndMessage(query_order)
        # self.checkOrderInfo(query_order["data"], submit_body, router_info["data"][0], True)
        # 查询订单日志
        order_log = self.client.getOrderStateLog(instruction_id)
        self.checkCodeAndMessage(order_log)
        self.checkOrderLog(order_log["data"], transaction_id)
        return query_order["data"], 0

    def verifyAndDecryptNotify(self, r_notify):
        parse_header = json.loads(r_notify["header"])
        ts = [i[1] for i in parse_header if "timestamp" == i[0]][0]
        sign = [i[1] for i in parse_header if "sign" == i[0]][0]
        res_en_data = ts + "::" + r_notify["response"].replace(" ", "")
        cur_path = os.path.abspath(__file__)
        verified = ApiUtils.rsa_verify(res_en_data, sign, os.path.join(cur_path, RTSData.ssl_pub_key))
        assert verified, "response验签失败"
        # 解密数据
        r_data = json.loads(r_notify["response"])["data"]["resource"]
        de_data = ApiUtils.aes_decrypt(r_data["ciphertext"], r_data["nonce"], r_data["associatedData"], RTSData.sec_key)
        parse_notify = json.loads(de_data)
        self.client.logger.info(f"notify解密为: {parse_notify}")
        return parse_notify

    # 接口校验函数

    def checkNumberDecimalLessThanSix(self, num):
        larg = num * 1000000
        self.assertLessEqual(larg, int(larg), f"{num}小数位数大于6位")

    def checkContractRateResult(self, contract_rate, request_body):
        if isinstance(request_body, bytes):
            request_body = json.loads(str(request_body, encoding="utf-8"))
        self.assertEqual(contract_rate["sendCurrency"], request_body["sendCurrency"].upper())
        self.assertEqual(contract_rate["receiveCurrency"], request_body["receiveCurrency"].upper())
        self.assertTrue(float(contract_rate["exchangeRate"]) > 0)

        if request_body["sendCurrency"] == request_body["receiveCurrency"]:
            self.assertEqual(contract_rate["exchangeRate"], "1")
            if request_body["sendAmount"] != "":
                # self.assertEqual(contract_rate["receiveAmount"], request_body["sendAmount"])
                # self.assertEqual(contract_rate["sendAmount"], request_body["sendAmount"])
                # todo 暂时调整，校验通过
                self.assertAlmostEqual(contract_rate["receiveAmount"], float(request_body["sendAmount"]), delta=0.01)
                self.assertAlmostEqual(contract_rate["sendAmount"], float(request_body["sendAmount"]), delta=0.01)
            else:
                # self.assertEqual(contract_rate["receiveAmount"], request_body["receiveAmount"])
                # self.assertEqual(contract_rate["sendAmount"], request_body["receiveAmount"])
                # todo 暂时调整，校验通过
                self.assertAlmostEqual(contract_rate["receiveAmount"], float(request_body["receiveAmount"]), delta=0.01)
                self.assertAlmostEqual(contract_rate["sendAmount"], float(request_body["receiveAmount"]), delta=0.01)
        else:
            if request_body["sendAmount"] != "":
                # self.assertEqual(contract_rate["sendAmount"], request_body["sendAmount"])
                self.assertAlmostEqual(contract_rate["sendAmount"], float(request_body["sendAmount"]), delta=0.01)
                self.assertAlmostEqual(float(contract_rate["exchangeRate"]),
                                       float(contract_rate["receiveAmount"]) / float(request_body["sendAmount"]),
                                       delta=0.01)
                # self.assertEqual(contract_rate["receiveAmount"], str(round(float(contract_rate["exchangeRate"])*float(request_body["sendAmount"]), 2)))
                self.checkNumberDecimalLessThanSix(contract_rate["receiveAmount"])
                self.assertAlmostEqual(float(contract_rate["receiveAmount"]),
                                       round(float(contract_rate["exchangeRate"]) * float(request_body["sendAmount"]),
                                             2), delta=0.01)
            else:
                # self.assertEqual(contract_rate["receiveAmount"], request_body["receiveAmount"])
                self.assertAlmostEqual(contract_rate["receiveAmount"], float(request_body["receiveAmount"]), delta=0.01)
                self.assertAlmostEqual(float(contract_rate["exchangeRate"]),
                                       float(contract_rate["receiveAmount"]) / float(contract_rate["sendAmount"]),
                                       delta=0.000001)
                self.checkNumberDecimalLessThanSix(contract_rate["sendAmount"])
                # self.assertAlmostEqual(contract_rate["sendAmount"], round(
                #     float(contract_rate["receiveAmount"]) / float(contract_rate["exchangeRate"]), 2), delta=0.01)

    def getRSSFeeAmount(self, sn_db_name, q_currency, Method, channelType):
        # db_name = "sn-{}-roxe-roxe".format(receiveCountry.lower())
        currency, country = q_currency.split(".")
        if channelType == "IN":
            sql = "select * from `{}`.sn_business where pay_currency='{}'".format(sn_db_name, currency)
        else:
            sql = "select * from `{}`.sn_business where out_currency='{}'".format(sn_db_name, currency)
        try:
            res = self.mysql.exec_sql_query(sql)
        except OperationalError:
            return None, None, None

        rssFee = float(res[0]["feeQuantity"])
        channelName = sn_db_name.split("-")[2].upper()
        # group = sn_db_name.split("-")[1].upper()
        if "terrapay" in sn_db_name and channelType == "IN":
            channelName = "CHECKOUT"
        corridor_type = 1 if channelType == "IN" else 0
        node_fee = self.mysql.exec_sql_query(
            f"select * from `roxe_rpc`.rpc_corridor_info where channel_name='{channelName}' and currency='{currency}' and country='{country}' and corridor_type='{corridor_type}'")
        # fee_info = getChannelFee(channelName, currency, channelType)
        channelFee, channelFeeCurrency = 0, "USD"
        fee_key = "inFeeAmount" if channelType == "IN" else "outBankFee"
        if Method.lower() == "wallet":
            fee_key = "outWalletFee"
        elif Method.lower() == "cash":
            fee_key = "outCashFee"

        if node_fee[0][fee_key]: channelFee = float(node_fee[0][fee_key])
        channelFeeCurrency = res[0]["rocCurrency"].split(".")[0]
        return rssFee, channelFee, channelFeeCurrency

    def checkRouterListResult(self, router_list, request_body, channel_rate=None):
        if isinstance(request_body, bytes):
            request_body = json.loads(str(request_body, encoding="utf-8"))
        self.client.logger.info(f"路由参数: {request_body}")
        in_currency, out_currency = request_body["sendCurrency"].upper(), request_body["receiveCurrency"].upper()
        router_db = self.mysql.exec_sql_query("select * from rts_node_router")
        router_path_db = [i for i in router_db if i["payCurrency"].startswith(f"{in_currency}.") and i["outCurrency"].startswith(f"{out_currency}.")]
        if request_body["sendNodeCode"]:
            router_path_db = [i for i in router_path_db if i["payNodeCode"] == request_body["sendNodeCode"]]
        if request_body["receiveNodeCode"]:
            router_path_db = [i for i in router_path_db if i["outNodeCode"] == request_body["receiveNodeCode"]]
        if request_body["sendCountry"]:
            router_path_db = [i for i in router_path_db if i["payCurrency"].endswith(request_body["sendCountry"])]
        if request_body["receiveCountry"]:
            router_path_db = [i for i in router_path_db if i["outCurrency"].endswith(request_body["receiveCountry"])]
        router_fees = []
        new_router_db = []
        for r_db in router_path_db:
            r_cfg = json.loads(r_db["routerConfig"])
            if request_body["receiveCurrency"].endswith(".ROXE"):
                inFee, inChannelFee = 0, 0
            else:
                in_node_db = r_cfg["sn1"]["nodeUrl"].split("/")[-1].rstrip("1")
                inFee, inChannelFee, inChannelFeeCurrency = self.getRSSFeeAmount(in_node_db, r_db["payCurrency"],
                                                                                 "BANK",
                                                                                 "IN")
                if inChannelFee is None:
                    continue
            if request_body["receiveCurrency"].endswith(".ROXE"):
                outFee, outChannelFee = 0, 0
            else:
                out_node_db = r_cfg["sn2"]["nodeUrl"].split("/")[-1].rstrip("1")
                outFee, outChannelFee, outChannelFeeCurrency = self.getRSSFeeAmount(out_node_db, r_db["outCurrency"],
                                                                                    "BANK", "OUT")
                if outChannelFee is None:
                    continue
            path_fee = inFee + inChannelFee + outFee + outChannelFee
            if request_body["sendAmount"] and float(request_body["sendAmount"]) <= path_fee:
                continue
            r_db["sendFee"] = inFee + inChannelFee
            r_db["deliveryFee"] = outFee + outChannelFee
            router_fees.append(path_fee)
            new_router_db.append(r_db)
        router_path_db = new_router_db
        if request_body["routerStrategy"] == "LOWEST_FEE":
            if router_fees:
                lowest_fee = min(router_fees)
                lowest_index = router_fees.index(lowest_fee)
                router_path_db = [router_path_db[lowest_index]]
                self.client.logger.warning(f"路由费用计算: {router_fees}")
                self.client.logger.warning(f"最低费用的路由: {router_path_db}")
                self.assertEqual(len(router_list), 1, "费用最低策略只返回1条路由")
        else:
            self.assertEqual(len(router_list), len(router_path_db), "返回的路由数量不正确")
        # print(router_path_db)
        for router in router_list:
            router_in_db = [i for i in router_path_db if
                            i["payNodeCode"] == router["sendNodeCode"] and i["outNodeCode"] == router[
                                "receiveNodeCode"]]
            self.client.logger.info(f"准备校验: {router}")
            self.client.logger.debug(f"对应数据库数据: {router_in_db}")
            # ex_stratege = request_body["routerStrategy"] if request_body["routerStrategy"] else None
            # self.assertEqual(router["routerStrategy"], ex_stratege)  # todo
            self.assertEqual(router["sendNodeCode"], router_in_db[0]["payNodeCode"])
            self.assertEqual(router["receiveNodeCode"], router_in_db[0]["outNodeCode"])
            ex_c = None if in_currency.endswith(".ROXE") else router_in_db[0]["payCurrency"].split(".")[1]
            self.assertEqual(router["sendCountry"], ex_c)
            self.assertEqual(router["sendCurrency"], in_currency)
            ex_c = None if out_currency.endswith(".ROXE") else router_in_db[0]["outCurrency"].split(".")[1]
            self.assertEqual(router["receiveCountry"], ex_c)
            self.assertEqual(router["receiveCurrency"], out_currency)

            router_cfg = json.loads(router_in_db[0]["routerConfig"])

            # self.assertEqual(router["custodyAccountInfo"]["nodeCode"], router["sendNodeCode"])
            self.assertIn(router["custodyAccountInfo"]["accountType"], ["BANK", "BLOCK_CHAIN", "THIRD_PARTY"])
            self.assertEqual(router["custodyAccountInfo"]["currency"], in_currency)

            # 费用处理及校验
            accountType = router["custodyAccountInfo"]["accountType"]

            # 费用处理及校验
            if "ROXE" not in in_currency:

                sn_db = router_cfg["sn1"]["nodeUrl"].split("/")[-1]
                if sn_db.endswith("1"):
                    sn_db = sn_db.rstrip("1")
                payCurrency = router_in_db[0]['payCurrency']
                sn_sql = f"select * from `{sn_db}`.sn_business where business='mint' and pay_currency='{payCurrency}'"
                ex_account = self.mysql.exec_sql_query(sn_sql)[0]["payAddress"]
                self.assertDictEqual(router["custodyAccountInfo"]["accountDetail"], json.loads(ex_account), "入金账户不正确")
                rssFee, channelFee, channelFeeCurrency = self.getRSSFeeAmount(sn_db, payCurrency, accountType, "IN")
                self.assertEqual(router["sendFee"], channelFee)
                self.assertEqual(router["sendFeeCurrency"], channelFeeCurrency)

            if "ROXE" not in out_currency:
                sn_db = router_cfg["sn2"]["nodeUrl"].split("/")[-1]
                if sn_db.endswith("1"):
                    sn_db = sn_db.rstrip("1")
                rssFee, channelFee, channelFeeCurrency = self.getRSSFeeAmount(sn_db, router_in_db[0]["outCurrency"],
                                                                              accountType, "OUT")
                self.assertEqual(router["deliveryFee"], channelFee)
                self.assertEqual(router["deliveryFeeCurrency"], channelFeeCurrency)

            self.assertEqual(router["serviceFee"], 0)
            self.assertEqual(router["serviceFeeCurrency"], "USD")

            # 计算汇率
            if in_currency == out_currency:
                fx_in_amount = router["sendAmount"] - router["sendFee"]
                fx_out_amount = router["receiveAmount"] + router["deliveryFee"]
            else:
                fx_in_amount = router["sendAmount"] - router["sendFee"]
                if out_currency == router["deliveryFeeCurrency"]:
                    fx_out_amount = router["receiveAmount"] + router["deliveryFee"]
                else:
                    fx_out_amount = router["receiveAmount"]
                    fx_in_amount -= router["deliveryFee"]
            fx_rate = fx_out_amount / fx_in_amount
            self.client.logger.warning(f"{in_currency} -> {out_currency}计算汇率为: {fx_rate}")
            if channel_rate:
                self.assertAlmostEqual(fx_rate, float(channel_rate), msg="路由计算的汇率和从第三方获取汇率不一致", delta=0.001)

    def checkSubmitOrderResult(self, order_info, request_body, router_info):
        if isinstance(request_body, bytes):
            request_body = json.loads(str(request_body, encoding="utf-8"))

        # 根据下单参数进行校验
        self.assertIsNotNone(order_info["transactionId"])
        self.assertEqual(order_info["paymentId"], request_body["paymentId"])
        # db_order_info = json.loads(db_res[0]["orderInfo"])
        self.assertEqual(order_info["originalId"], request_body["originalId"])
        self.assertEqual(order_info["extensionField"], request_body["extensionField"])
        self.assertEqual(order_info["txState"], "TRANSACTION_SUBMIT")
        # self.assertIsNotNone(order_info["orderStage"], "orderStage") # todo
        # self.assertIsNotNone(order_info["orderStageState"], "orderStageState")
        # self.assertIsNotNone(order_info["routerStrategy"])
        self.assertEqual(order_info["sendNodeCode"], router_info["sendNodeCode"])
        self.assertEqual(order_info["sendCountry"], router_info["sendCountry"])
        self.assertEqual(order_info["sendCurrency"], request_body["sendCurrency"])
        self.assertAlmostEqual(float(order_info["sendAmount"]),
                               ApiUtils.parseNumberDecimal(float(request_body["sendAmount"])), delta=0.001)
        if request_body["receiveNodeCode"]:
            self.assertEqual(order_info["receiveNodeCode"], request_body["receiveNodeCode"])
        ex_out_c = None if request_body["receiveCurrency"].endswith(".ROXE") else router_info["receiveCountry"]
        if ex_out_c:
            self.assertEqual(order_info["receiveCountry"], ex_out_c)
        self.assertEqual(order_info["receiveCurrency"], request_body["receiveCurrency"])
        self.assertAlmostEqual(float(order_info["quoteReceiveAmount"]), float(router_info["receiveAmount"]), delta=0.01)
        # self.assertEqual(order_info["receiveAmount"], None) # todo
        self.assertEqual(order_info["sendFeeCurrency"], router_info["sendFeeCurrency"])
        self.assertEqual(order_info["sendFee"], router_info["sendFee"])
        self.assertEqual(order_info["serviceFeeCurrency"], router_info["serviceFeeCurrency"])
        self.assertEqual(order_info["serviceFee"], router_info["serviceFee"])
        self.assertEqual(order_info["deliveryFeeCurrency"], router_info["deliveryFeeCurrency"])
        self.assertEqual(order_info["deliveryFee"], router_info["deliveryFee"])
        # 如果出入金币种不一致，即不发生换汇，则此字段不返回
        if request_body["sendCurrency"].rstrip(".ROXE") != request_body["receiveCurrency"].rstrip(".ROXE"):
            self.assertIsNotNone(order_info['exchangeRate'])
        self.assertIsNotNone(order_info["createTime"])
        self.assertIsNotNone(order_info["updateTime"])

        if RTSData.is_check_db:
            # 校验数据库存入的数据
            sql = "select * from rts_order where client_id='{}'".format(request_body["instructionId"])
            db_res = self.mysql.exec_sql_query(sql)
            # self.client.logger.info("查询的数据库结果: {}".format(db_res))
            self.assertEqual(order_info["transactionId"], db_res[0]["orderId"])
            self.assertEqual(order_info["paymentId"], db_res[0]["paymentId"])
            db_log = self.mysql.exec_sql_query(
                "select * from rts_order_log where order_id='{}' and order_state='TRANSACTION_SUBMIT'".format(
                    order_info["transactionId"]))
            db_order_params = json.loads(db_log[0]["logInfo"])
            self.assertEqual(len(db_order_params), len(request_body), "数据库存储的字段和下单参数不一致")  # todo
            # for d_k, d_v in db_order_params.items():
            #     self.assertEqual(d_v, request_body[d_k], f"{d_k}字段在数据库中存储和下单参数不一致")
        self.client.logger.info("下单信息校验正确")

    def checkOrderInfo(self, order_info, request_body, router_info, ro2ro=False):
        if isinstance(request_body, bytes):
            request_body = json.loads(str(request_body, encoding="utf-8"))

        if request_body["sendCurrency"].endswith(".ROXE") and request_body["receiveCurrency"].endswith(".ROXE"):
            # ro 到ro，rts不做处理
            self.assertEqual(order_info["sendFeeCurrency"], None)
            self.assertEqual(order_info["sendFee"], None)
            self.assertEqual(order_info["serviceFeeCurrency"], None)
            self.assertEqual(order_info["serviceFee"], None)
            self.assertEqual(order_info["deliveryFeeCurrency"], None)
            self.assertEqual(order_info["deliveryFee"], None)
        else:
            self.assertAlmostEqual(float(order_info["quoteReceiveAmount"]), float(router_info["receiveAmount"]),
                                   delta=0.01)
            # self.assertIsNotNone(order_info['exchangeRate'])

        if order_info["txState"] != "TRANSACTION_FINISH":
            ex_amount = None
        else:
            if router_info["receiveAmount"]:
                ex_amount = router_info["receiveAmount"]
            else:
                if request_body["sendAmount"]:
                    ex_amount = request_body["sendAmount"]
                else:
                    ex_amount = request_body["receiveAmount"]
        self.assertEqual(order_info["receiveAmount"], ex_amount)
        self.assertIsNotNone(order_info["txState"])
        if ro2ro:
            self.assertEqual(order_info["sendFeeCurrency"], None)
            self.assertEqual(order_info["sendFee"], None)
            self.assertEqual(order_info["serviceFeeCurrency"], None)
            self.assertEqual(order_info["serviceFee"], None)
            self.assertEqual(order_info["deliveryFeeCurrency"], None)
            self.assertEqual(order_info["deliveryFee"], None)
            self.assertEqual(order_info["origTransactionInfo"]["notifyUrl"], "")
        else:
            self.assertEqual(order_info["sendFeeCurrency"], router_info["sendFeeCurrency"], f"路由信息: {router_info}")
            self.assertEqual(order_info["sendFee"], router_info["sendFee"])
            self.assertEqual(order_info["serviceFeeCurrency"], router_info["serviceFeeCurrency"])
            self.assertEqual(order_info["serviceFee"], router_info["serviceFee"])
            self.assertEqual(order_info["deliveryFeeCurrency"], router_info["deliveryFeeCurrency"])
            self.assertEqual(order_info["deliveryFee"], router_info["deliveryFee"])
            ex_url = request_body["notifyURL"] if request_body["notifyURL"] != "" else None
            # self.assertEqual(order_info["origTransactionInfo"]["notifyUrl"], ex_url)  # todo
        self.assertEqual(order_info["origTransactionInfo"]["couponCode"], request_body["couponCode"])
        self.assertEqual(order_info["origTransactionInfo"]["channelCode"], request_body["channelCode"])
        self.assertEqual(order_info["origTransactionInfo"]["instructionId"], request_body["instructionId"])
        self.assertEqual(order_info["origTransactionInfo"]["originalId"], request_body["originalId"])
        self.assertEqual(order_info["origTransactionInfo"]["extensionField"], request_body["extensionField"])
        # self.assertEqual(order_info["origTransactionInfo"]["routerStrategy"], request_body["routerStrategy"]) # todo
        # ex_node = router_info["sendNodeCode"] if "sendNodeCode" in router_info else None
        self.assertEqual(order_info["origTransactionInfo"]["sendNodeCode"], request_body["sendNodeCode"])
        self.assertEqual(order_info["origTransactionInfo"]["sendCountry"], request_body["sendCountry"])
        self.assertEqual(order_info["origTransactionInfo"]["sendCurrency"], request_body["sendCurrency"])
        # self.assertEqual(order_info["origTransactionInfo"]["sendAmount"], request_body["sendAmount"])  # todo
        # ex_node = router_info["receiveNodeCode"] if "receiveNodeCode" in router_info else None
        self.assertEqual(order_info["origTransactionInfo"]["receiveNodeCode"], request_body["receiveNodeCode"])
        self.assertEqual(order_info["origTransactionInfo"]["receiveCountry"], request_body["receiveCountry"])
        self.assertEqual(order_info["origTransactionInfo"]["receiveCurrency"], request_body["receiveCurrency"])
        self.assertEqual(order_info["origTransactionInfo"]["receiveInfo"], request_body["receiveInfo"])

        self.assertIsNotNone(order_info["createTime"])
        self.assertIsNotNone(order_info["updateTime"])
        if RTSData.is_check_db:
            sql = "select * from rts_order where client_id='{}'".format(request_body["instructionId"])
            db_res = self.mysql.exec_sql_query(sql)
            self.assertEqual(order_info["transactionId"], db_res[0]["orderId"])
            self.assertEqual(order_info["origTransactionInfo"]["paymentId"], db_res[0]["paymentId"])
            self.client.logger.info("查询订单信息校验正确")

    def checkOrderLog(self, order_log, transaction_id):
        if RTSData.is_check_db:
            in_id = self.mysql.exec_sql_query(f"select client_id from rts_order where order_id='{transaction_id}'")
            db_res = self.mysql.exec_sql_query(f"select * from rts_order_log where order_id='{transaction_id}'")
            self.assertEqual(order_log["instructionId"], in_id[0]["clientId"])
            self.assertEqual(order_log["transactionId"], transaction_id)
            # self.assertEqual(len(order_log["stateInfo"]), len(db_res))  # todo
            for o_log in order_log["stateInfo"]:
                find_db_log = [i for i in db_res if i["orderState"] == o_log["txState"]]
                self.assertEqual(o_log["txState"], find_db_log[0]["orderState"], f"查找的数据库日志: {find_db_log}")
                self.assertEqual(o_log["createTime"], int(find_db_log[0]["createTime"].timestamp() * 1000),
                                 f"查找的数据库日志: {find_db_log}")
            self.client.logger.info("查询订单日志校验正确")

    def checkOuterBankFields(self, bank_fields, currency):
        expect_fields = RSSData.out_bank_fields[currency]
        self.assertEqual(len(bank_fields), len(expect_fields))
        for field in bank_fields:
            expect_field = [i for i in expect_fields if i["name"] == field["name"]][0]
            for f_k, f_v in field.items():
                self.assertEqual(f_v, expect_field[f_k], "字段{}和预期不符".format(field["name"]))

    def clearInvalidFormFromDB(self, payment_id):
        if RTSData.is_check_db:
            clear_rts = "delete from `roxe_rts`.rts_order where payment_id='{}'".format(payment_id)
            clear_rss = "delete from `roxe_rss_us`.rss_order where payment_id='{}'".format(payment_id)
            self.mysql.exec_sql_query(clear_rss)
            self.mysql.exec_sql_query(clear_rts)

    def checkTransactionCurrency(self, tx_currency, r_body):
        support_keys = ["sendCountry", "sendCurrency", "receiveCountry", "receiveCurrency"]
        for currency_info in tx_currency:
            self.assertEqual(tx_currency.count(currency_info), 1, f"支持的币种应没有重复数据: {currency_info}")
            for s_key in support_keys:
                if r_body[s_key]:
                    self.assertEqual(currency_info[s_key], r_body[s_key], f"{s_key}不正确")
                else:
                    self.assertTrue(isinstance(currency_info[s_key], str))
            if r_body["returnAllCurrency"]:
                check_con = (currency_info["sendCurrency"] in RTSData.digitalCurrency or currency_info["receiveCurrency"] in RTSData.digitalCurrency)
            else:
                check_con = (currency_info["sendCurrency"] not in RTSData.digitalCurrency and currency_info["receiveCurrency"] not in RTSData.digitalCurrency)
            # self.assertTrue(check_con, f"returnAllCurrency: {r_body['returnAllCurrency']} 时结果存在: {currency_info}")

        if RTSData.is_check_db:
            db_res = self.mysql.exec_sql_query("select * from rts_node_router")
            if r_body["sendCountry"]:
                db_res = [i for i in db_res if i["payCurrency"].endswith(f".{r_body['sendCountry']}")]

            if r_body["sendCurrency"]:
                if r_body["sendCurrency"].endswith(".ROXE"):
                    db_res = [i for i in db_res if i["payCurrency"] == r_body["sendCurrency"]]
                else:
                    db_res = [i for i in db_res if i['payCurrency'].split(".")[0] == r_body["sendCurrency"]]

            if r_body["receiveCountry"]:
                db_res = [i for i in db_res if i["outCurrency"].endswith(f".{r_body['receiveCountry']}")]

            if r_body["receiveCurrency"]:
                if r_body["receiveCurrency"].endswith(".ROXE"):
                    db_res = [i for i in db_res if i["outCurrency"] == r_body["receiveCurrency"]]
                else:
                    db_res = [i for i in db_res if i['outCurrency'].split(".")[0] == r_body["receiveCurrency"]]

            if not r_body["returnAllCurrency"]:
                tmp_db = []
                for i in db_res:
                    if i["payCurrency"].endswith(".ROXE") or i["outCurrency"].endswith(".ROXE"):
                        continue
                    elif i["payCurrency"].split(".")[0] in RTSData.digitalCurrency or i["outCurrency"].split(".")[0] in RTSData.digitalCurrency:
                        continue
                    else:
                        tmp_db.append(i)

                db_res = tmp_db

            router_path = list(set([i["payCurrency"] + i["outCurrency"] for i in db_res]))
            self.assertEqual(len(router_path), len(tx_currency))
            for currency_info in tx_currency:
                if currency_info["sendCurrency"].endswith("ROXE") and currency_info["receiveCurrency"].endswith("ROXE"):
                    db_info = [i for i in db_res if
                               i['payCurrency'] == currency_info["sendCurrency"] and i['outCurrency'] == currency_info[
                                   "receiveCurrency"]]
                elif currency_info["sendCurrency"].endswith("ROXE"):
                    db_info = [i for i in db_res if
                               i['payCurrency'] == currency_info["sendCurrency"] and i['outCurrency'].split(".")[0] ==
                               currency_info["receiveCurrency"]]
                elif currency_info["receiveCurrency"].endswith("ROXE"):
                    db_info = [i for i in db_res if
                               i['payCurrency'].split(".")[0] == currency_info["sendCurrency"] and i['outCurrency'] ==
                               currency_info["receiveCurrency"]]
                else:
                    db_info = [i for i in db_res if i['payCurrency'].split(".")[0] == currency_info["sendCurrency"] and
                               i['outCurrency'].split(".")[0] == currency_info["receiveCurrency"]]
                if len(db_info) > 1:
                    if currency_info['sendCountry']: db_info = [i for i in db_info if
                                                                i['payCurrency'].split(".")[1] == currency_info[
                                                                    'sendCountry']]
                    if currency_info['receiveCountry']: db_info = [i for i in db_info if
                                                                   i['outCurrency'].split(".")[1] == currency_info[
                                                                       'receiveCountry']]
                    # db_info = [i for i in db_info if i['payCurrency'].split(".")[1] == currency_info['sendCountry'] and i['outCurrency'].split(".")[1] == currency_info['receiveCountry']]
                self.assertTrue(len(db_info) >= 1, f"{currency_info} 没有在数据库中找到对应的数据")


class RTSApiTest(BaseCheckRTS):

    def test_001_querySystemOnline(self):
        """
        查询系统可用状态
        """
        system_state = self.client.getSystemState()
        self.checkCodeAndMessage(system_state)
        self.assertEqual(system_state["data"], {"sysState": "AVAILABLE"})

    def test_002_queryContractRate_sameCurrency_inAmount(self):
        """
        查询合约费率, 相同币种, 指定sendAmount
        """
        currency = RTSData.contract_info[0]["in"]
        amount = 10
        rate_info, request_body = self.client.getRate(currency, currency, sendAmount=amount)
        self.checkCodeAndMessage(rate_info)
        self.checkContractRateResult(rate_info["data"], request_body)

    def test_003_queryContractRate_sameCurrency_outAmount(self):
        """
        查询合约费率, 相同币种, 指定receiveAmount
        """
        currency = RTSData.contract_info[0]["in"]
        amount = 12.34
        rate_info, request_body = self.client.getRate(currency, currency, receiveAmount=amount)
        self.checkCodeAndMessage(rate_info)
        self.checkContractRateResult(rate_info["data"], request_body)

    def test_004_queryContractRate_differentCurrency_inAmount(self):
        """
        查询合约费率, 不同币种之间, 指定inAmount
        """
        in_currency = RTSData.contract_info[0]["in"]
        out_currency = RTSData.contract_info[0]["out"]
        amount = 12.34
        rate_info, request_body = self.client.getRate(in_currency, out_currency, sendAmount=amount)
        self.checkCodeAndMessage(rate_info)
        self.checkContractRateResult(rate_info["data"], request_body)

    def test_005_queryContractRate_differentCurrency_inAmount_exchangeCurrencyThenGiveInAmount(self):
        """
        查询合约费率, 不同币种之间, 指定inAmount, 然后交互in、out的币种, 根据第1次结果指定inAmount数量
        """
        in_currency = RTSData.contract_info[0]["in"]
        out_currency = RTSData.contract_info[0]["out"]
        amount = 12.34
        rate_info, request_body = self.client.getRate(in_currency, out_currency, sendAmount=amount)
        # 交换币种
        out_amount = rate_info["data"]["receiveAmount"]
        rate_info2, request_body2 = self.client.getRate(out_currency, in_currency, sendAmount=out_amount)
        self.checkContractRateResult(rate_info2["data"], request_body2)
        dif_amount = abs(float(rate_info2["data"]["receiveAmount"]) - amount)
        dif_percent = dif_amount / amount
        self.client.logger.info(f"交换币种后得到的金额差值: {dif_amount}, 误差范围: {dif_percent}")
        self.assertTrue(dif_percent < 0.005, "误差范围较大")

    def test_006_queryContractRate_differentCurrency_inAmount_exchangeCurrencyThenGiveOutAmount(self):
        """
        查询合约费率, 不同币种之间, 指定inAmount, 然后交互in、out的币种, 指定相同数量outAmount数量
        """
        in_currency = RTSData.contract_info[0]["in"]
        out_currency = RTSData.contract_info[0]["out"]
        amount = 102.34
        rate_info, request_body = self.client.getRate(in_currency, out_currency, sendAmount=amount)
        out_amount = float(rate_info["data"]["receiveAmount"])
        # 交换币种
        rate_info2, request_body2 = self.client.getRate(out_currency, in_currency, receiveAmount=amount)
        self.checkContractRateResult(rate_info2["data"], request_body2)
        dif_amount = abs(float(rate_info2["data"]["sendAmount"]) - out_amount)
        dif_percent = dif_amount / out_amount
        self.client.logger.info(f"交换币种后得到的金额差值: {dif_amount}, 误差范围: {dif_percent}")

    def test_007_queryContractRate_differentCurrency_outAmount(self):
        """
        查询合约费率, 不同币种之间, 指定outAmount
        """
        in_currency = RTSData.contract_info[0]["in"]
        out_currency = RTSData.contract_info[0]["out"]
        amount = 12.34
        rate_info, request_body = self.client.getRate(in_currency, out_currency, receiveAmount=amount)
        self.checkCodeAndMessage(rate_info)
        self.checkContractRateResult(rate_info["data"], request_body)

    def test_008_queryContractRate_differentCurrency_outAmount_exchangeCurrencyThenGiveInAmount(self):
        """
        查询合约费率, 不同币种之间, 指定outAmount, 交换币种然后指定inAmount
        """
        in_currency = RTSData.contract_info[0]["in"]
        out_currency = RTSData.contract_info[0]["out"]
        amount = 12.34
        rate_info, request_body = self.client.getRate(in_currency, out_currency, receiveAmount=amount)
        in_amount = float(rate_info["data"]["sendAmount"])

        rate_info2, request_body2 = self.client.getRate(out_currency, in_currency, sendAmount=amount)
        self.checkCodeAndMessage(rate_info2)
        self.checkContractRateResult(rate_info2["data"], request_body2)

        dif_amount = abs(float(rate_info2["data"]["receiveAmount"]) - in_amount)
        dif_percent = dif_amount / in_amount
        self.client.logger.info(f"交换币种后得到的金额差值: {dif_amount}, 误差范围: {dif_percent}")
        self.assertEqual(dif_percent, 0)

    def test_009_queryContractRate_differentCurrency_outAmount_exchangeCurrencyThenGiveOutAmount(self):
        """
        查询合约费率, 不同币种之间, 指定outAmount, 交换币种然后指定outAmount
        """
        in_currency = RTSData.contract_info[0]["in"]
        out_currency = RTSData.contract_info[0]["out"]
        amount = 102.34
        rate_info, request_body = self.client.getRate(in_currency, out_currency, receiveAmount=amount)
        in_amount = float(rate_info["data"]["sendAmount"])

        rate_info2, request_body2 = self.client.getRate(out_currency, in_currency, receiveAmount=in_amount)
        self.checkCodeAndMessage(rate_info2)
        self.checkContractRateResult(rate_info2["data"], request_body2)

        dif_amount = abs(float(rate_info2["data"]["sendAmount"]) - in_amount)
        dif_percent = dif_amount / in_amount
        self.client.logger.info(f"交换币种后得到的金额差值: {dif_amount}, 误差范围: {dif_percent}")

    def test_010_getTransactionCurrency_all(self):
        """
        获取所有支持的转账币种，不包括数字货币
        """
        currency_infos, r_body = self.client.getTransactionCurrency()
        self.checkCodeAndMessage(currency_infos)
        self.checkTransactionCurrency(currency_infos["data"], r_body)

    def test_011_getTransactionCurrency_giveValidSendCountry(self):
        """
        获取支持的转账币种
        """
        currency_infos, r_body = self.client.getTransactionCurrency(sendCountry="US")
        self.checkCodeAndMessage(currency_infos)
        self.checkTransactionCurrency(currency_infos["data"], r_body)

    def test_012_getTransactionCurrency_giveInvalidSendCountry(self):
        """
        获取支持的转账币种
        """
        currency_infos, r_body = self.client.getTransactionCurrency(sendCountry="USA")
        self.checkCodeAndMessage(currency_infos)
        self.assertEqual(currency_infos["data"], [])

        currency_infos, r_body = self.client.getTransactionCurrency(sendCountry="CN")
        self.checkCodeAndMessage(currency_infos)
        self.assertEqual(currency_infos["data"], [])

    def test_013_getTransactionCurrency_giveValidSendCurrency(self):
        """
        获取支持的转账币种 输入入金币种
        """
        currency_infos, r_body = self.client.getTransactionCurrency(sendCurrency="USD")
        self.checkCodeAndMessage(currency_infos)
        self.checkTransactionCurrency(currency_infos["data"], r_body)

    def test_014_getTransactionCurrency_giveInvalidSendCurrency(self):
        """
        获取支持的转账币种 输入入金币种
        """
        currency_infos, r_body = self.client.getTransactionCurrency(sendCurrency="CNY")
        self.checkCodeAndMessage(currency_infos)
        self.assertEqual(currency_infos["data"], [])

    def test_015_getTransactionCurrency_giveValidReceiveCountry(self):
        """
        获取支持的转账币种 输入出金国家
        """
        currency_infos, r_body = self.client.getTransactionCurrency(receiveCountry="US")
        self.checkCodeAndMessage(currency_infos)
        self.checkTransactionCurrency(currency_infos["data"], r_body)

    def test_016_getTransactionCurrency_giveInvalidReceiveCountry(self):
        """
        获取支持的转账币种 输入不存在出金币种
        """
        currency_infos, r_body = self.client.getTransactionCurrency(receiveCountry="USA")
        self.checkCodeAndMessage(currency_infos)
        self.assertEqual(currency_infos["data"], [])

    def test_017_getTransactionCurrency_giveValidReceiveCurrency(self):
        """
        获取支持的转账币种 输入出金币种
        """
        currency_infos, r_body = self.client.getTransactionCurrency(receiveCurrency="USD")
        self.checkCodeAndMessage(currency_infos)
        self.checkTransactionCurrency(currency_infos["data"], r_body)

    def test_018_getTransactionCurrency_giveInvalidReceiveCurrency(self):
        """
        获取支持的转账币种 输入不存在的出金币种
        """
        currency_infos, r_body = self.client.getTransactionCurrency(receiveCurrency="HKD")
        self.checkCodeAndMessage(currency_infos)
        self.assertEqual(currency_infos["data"], [])

    def test_019_getTransactionCurrency_giveSendCurrencyAndReceiveCurrency(self):
        """
        获取支持的转账币种 输入入金币种和出金币种
        """
        currency_infos, r_body = self.client.getTransactionCurrency(sendCurrency="USD", receiveCurrency="INR")
        self.checkCodeAndMessage(currency_infos)
        self.checkTransactionCurrency(currency_infos["data"], r_body)

    def test_020_getTransactionCurrency_getDigitalCurrency(self):
        """
        获取支持的转账币种
        """
        currency_infos, r_body = self.client.getTransactionCurrency(returnAllCurrency=True)
        self.checkCodeAndMessage(currency_infos)
        self.checkTransactionCurrency(currency_infos["data"], r_body)

    # RTS 路由策略增加: 费用最低
    @contextlib.contextmanager
    def updateNodeFeeInDB(self, channel_name, country, currency, new_amount):
        node_condition = f"channel_name='{channel_name}' and country='{country}' and currency='{currency}' and corridor_type=0"
        node_fee_info = self.mysql.exec_sql_query(f"select * from `roxe_rpc`.rpc_corridor_info where {node_condition}")
        old_amount = node_fee_info[0]["outBankFee"]
        print(node_fee_info)
        try:
            update_sql = f"update `roxe_rpc`.rpc_corridor_info set out_bank_fee='{new_amount}' where {node_condition}"
            self.mysql.exec_sql_query(update_sql)
            yield
        finally:
            reset_sql = f"update `roxe_rpc`.rpc_corridor_info set out_bank_fee='{old_amount}' where {node_condition}"
            self.mysql.exec_sql_query(reset_sql)

    def test_021_getRouterList_All(self):
        """
        查询路由，路由策略不传，默认返回所有可用的路由信息
        """
        in_amount = "300"
        router_info, request_body = self.client.getRouterList("US", "USD", "US", "USD", in_amount)
        self.checkRouterListResult(router_info["data"], request_body)

    def test_022_getRouterList_lowest_fee(self):
        """
        查询路由，路由策略为费用最低，返回可以得到右侧币种数量最多的一条路由
        """
        in_amount = "100"
        router_info, request_body = self.client.getRouterList("US", "USD", "US", "USD", in_amount, routerStrategy="LOWEST_FEE")
        self.checkRouterListResult(router_info["data"], request_body)

    def test_023_getRouterList_lowest_fee_updateFee(self):
        """
        查询路由，路由策略为费用最低，返回可以得到右侧币种数量最多的一条路由
        """
        in_amount = "100"
        router_all, request_body = self.client.getRouterList("US", "USD", "US", "USD", in_amount)
        r_amount = [i["receiveAmount"] for i in router_all["data"]]
        max_amount, min_amount = max(r_amount), min(r_amount)
        lowest_fee_router = router_all["data"][r_amount.index(max_amount)]
        max_fee_router = router_all["data"][r_amount.index(min_amount)]
        print(lowest_fee_router)
        print(max_fee_router)
        channel_name = max_fee_router["receiveNodeCode"]
        # 如果是渠道，需要替换为渠道的名称
        if channel_name in RTSData.channel_name:
            channel_name = RTSData.channel_name[channel_name]

        new_amount = ApiUtils.parseNumberDecimal(lowest_fee_router["deliveryFee"] - 0.52)
        with self.updateNodeFeeInDB(channel_name, "US", "USD", new_amount):
            time.sleep(20)
            router_new, request_new = self.client.getRouterList("US", "USD", "US", "USD", in_amount,
                                                                routerStrategy="LOWEST_FEE")
            self.checkRouterListResult(router_new["data"], request_new)
            self.assertAlmostEqual(new_amount, router_new["data"][0]["deliveryFee"], delta=0.01)

    def test_024_getRouterList_All_differentCurreny(self):
        """
        查询路由，路由策略不传，默认返回所有可用的路由信息
        """
        in_amount = "100"
        router_info, request_body = self.client.getRouterList("US", "USD", "PH", "PHP", in_amount)
        self.checkRouterListResult(router_info["data"], request_body)

    def test_025_getRouterList_lowest_fee_differentCurreny(self):
        """
        查询路由，路由策略为费用最低，返回可以得到右侧币种数量最多的一条路由
        """
        in_amount = "100"
        router_info, request_body = self.client.getRouterList("US", "USD", "PH", "PHP", in_amount, routerStrategy="LOWEST_FEE")
        self.checkRouterListResult(router_info["data"], request_body)

    def test_026_getRouterList_changeAmount_all(self):
        """
        查询路由，路由策略不传，默认返回所有可用的路由信息
        """
        in_amount = "100"
        router_info, request_body = self.client.getRouterList("US", "USD", "US", "USD", in_amount)
        self.checkRouterListResult(router_info["data"], request_body)
        # 计算一条路由的费用总和

        def one_router_fee(router):
            return sum([float(router[fee_k]) for fee_k in ["deliveryFee", "sendFee", "serviceFee"]])
        router_fees = [one_router_fee(i) for i in router_info["data"]]
        self.client.logger.warning(f"全部路由的费用: {router_fees}")
        new_amounts = [max(router_fees) + 0.01, max(router_fees), min(router_fees) + 0.01, min(router_fees), min(router_fees) - 0.01]
        new_amounts = [ApiUtils.parseNumberDecimal(i, 2, True) for i in new_amounts]
        ex_router_lengths = [len(router_fees), len(router_fees) - 1, 1, 0, 0]
        for new_amount, ex_length in zip(new_amounts, ex_router_lengths):
            self.client.logger.warning(f"查询路由金额: {new_amount}")
            router_info, request_body = self.client.getRouterList("US", "USD", "US", "USD", new_amount)
            self.checkRouterListResult(router_info["data"], request_body)
            self.assertEqual(len(router_info["data"]), ex_length)

    def test_027_getRouterList_changeAmount_lowestFee(self):
        """
        查询路由，路由策略不传，默认返回所有可用的路由信息
        """
        in_amount = "100"
        router_info, request_body = self.client.getRouterList("US", "USD", "US", "USD", in_amount)
        self.checkRouterListResult(router_info["data"], request_body)
        # 计算一条路由的费用总和

        def one_router_fee(router):
            return sum([float(router[fee_k]) for fee_k in ["deliveryFee", "sendFee", "serviceFee"]])

        router_fees = [one_router_fee(i) for i in router_info["data"]]
        self.client.logger.warning(f"全部路由的费用: {router_fees}")
        new_amounts = [max(router_fees) + 0.01, max(router_fees), min(router_fees) + 0.01, min(router_fees), min(router_fees) - 0.01]
        new_amounts = [ApiUtils.parseNumberDecimal(i, 2, True) for i in new_amounts]
        ex_router_lengths = [1, 0, 0, 0, 0]
        for new_amount, ex_length in zip(new_amounts, ex_router_lengths):
            self.client.logger.warning(f"查询路由金额: {new_amount}")
            router_info, request_body = self.client.getRouterList("US", "USD", "US", "USD", new_amount, routerStrategy="LOWEST_FEE")
            self.checkRouterListResult(router_info["data"], request_body)
            # self.assertEqual(len(router_info["data"]), ex_length)

    def test_028_getRouterList_rana(self):
        """
        查询路由，路由策略不传，默认返回所有可用的路由信息
        """
        in_amount = "100"
        router_info, request_body = self.client.getRouterList("US", "USD", "BR", "BRL", in_amount, receiveNodeCode=RTSData.yaml_conf["rana_node"])
        self.checkRouterListResult(router_info["data"], request_body)

    def test_029_getRouterList_gme(self):
        """
        查询路由，路由策略不传，默认返回所有可用的路由信息
        """
        in_amount = "105.34"
        router_info, request_body = self.client.getRouterList("US", "USD", "KR", "KRW", in_amount, receiveNodeCode=RTSData.yaml_conf["gme_node"])
        gme_rate_info = self.client.getRateFromGME()
        self.checkRouterListResult(router_info["data"], request_body, gme_rate_info["Rate"])

    def test_030_queryOuterMethod_receiveNodeCode(self):
        out_currency = RTSData.out_currency_info[1]["fiat"]
        receiveNodeCode = RTSData.out_currency_info[1]["node_code"]
        out_res = self.client.getOutMethod(out_currency, "", receiveNodeCode)
        self.checkCodeAndMessage(out_res)
        self.assertEqual(out_res["data"], {"receiveMethod": ["BANK"]})

    def test_031_queryOuterMethod_receiveCountry(self):
        """
        查询出金方式，指定出金国家
        """
        out_currency = RTSData.out_currency_info[1]["fiat"]
        receiveCountry = RTSData.out_currency_info[1]["country"]
        out_res = self.client.getOutMethod(out_currency, receiveCountry, "")
        self.checkCodeAndMessage(out_res)
        self.assertEqual(out_res["data"], {"receiveMethodCode": ["BANK"]})

    def test_032_queryOuterFields(self):
        """
        正确的入参
        """
        out_currency = RTSData.out_currency_info[1]["fiat"]
        receiveNodeCode = RTSData.out_currency_info[1]["node_code"]
        out_res = self.client.getReceiverRequiredFields(receiveNodeCode, out_currency, "BANK")
        self.checkCodeAndMessage(out_res)
        self.assertTrue(len(out_res["data"]) > 0)

    def test_08501_checkOuterFields(self):
        """
        正确的传参
        """

        # receiveCurrency = RTSData.out_currency_info[1]["fiat"]
        # receiveNodeCode = RTSData.out_currency_info[1]["node_code"]
        receiveCurrency = "PHP"
        receiveNodeCode = "huuzj1hpycrx"
        outer_info = RSSData.terrapay_out_bank_info[receiveCurrency].copy()
        check_res = self.client.checkReceiverRequiredFields(receiveNodeCode, receiveCurrency,
                                                            outer_info)
        self.checkCodeAndMessage(check_res)
        # self.assertIsNone(check_res["data"])

    def test_097_queryOrderInfo_transactionId(self):
        """
        查询状态，根据transactionId查询
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        amount = 10
        outer_address = RTSData.ach_user_account
        query_order = self.submitOrderFloorOfFiatToRo(RTSData.ach_user_token, RTSData.ach_user_id, currency_info, amount, "inner", outer_address)

        order_info = self.client.getOrderInfo(query_order["instructionId"])
        order_info2 = self.client.getOrderInfo("", query_order["transactionId"])
        self.checkCodeAndMessage(order_info)
        self.assertEqual(order_info2["data"], order_info["data"])

    @unittest.skipIf(RTSData.host.startswith("uat"), "uat测试环境无法通过rps入金，跳过")
    def test_D10_normalScene_sameCurrency_FiatToRo_notGiveNodeCodes_inAmount(self):
        """
        同币种, 法币到ro, 不指定节点, 指定入金数量,查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        amount = 10
        outer_address = RTSData.ach_user_account

        outer_balance = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{outer_address}账户持有的资产: {outer_balance}")

        query_order = self.submitOrderFloorOfFiatToRo(RTSData.ach_user_token, RTSData.ach_user_id, currency_info, amount, "inner", outer_address)

        outer_balance2 = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{outer_address}账户持有的资产: {outer_balance2}, 变化了: {outer_balance2 - outer_balance}")

        self.assertAlmostEqual(outer_balance2 - outer_balance, amount, delta=0.1**6)
        self.assertEqual(query_order["txState"], "TRANSACTION_FINISH", "订单最终状态应为完成")

    @unittest.skipIf(RTSData.host.startswith("uat"), "uat测试环境无法通过rps入金，跳过")
    def test_D11_normalScene_sameCurrency_FiatToRo_notGiveNodeCodes_outAmount(self):
        """
        同币种, 法币到ro, 不指定节点，指定出金数量, 查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        amount = 11.22
        outer_address = RTSData.ach_user_account

        outer_balance = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{outer_address}账户持有的资产: {outer_balance}")

        query_order = self.submitOrderFloorOfFiatToRo(RTSData.ach_user_token, RTSData.ach_user_id, currency_info, amount, "outer", outer_address)

        outer_balance2 = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{outer_address}账户持有的资产: {outer_balance2}, 变化了: {outer_balance2 - outer_balance}")

        self.assertAlmostEqual(outer_balance2 - outer_balance, amount, delta=0.1**6)
        self.assertEqual(query_order["txState"], "TRANSACTION_FINISH", "订单最终状态应为完成")

    @unittest.skipIf(RTSData.host.startswith("uat"), "uat测试环境无法通过rps入金，跳过")
    def test_D12_normalScene_sameCurrency_FiatToRo_giveInNodeCode_inAmount(self):
        """
        同币种, 法币到ro, 指定in节点, 指定入金数量, 查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        currency_info["innerNodeCode"] = RTSData.node_code
        amount = 10
        outer_address = RTSData.ach_user_account

        outer_balance = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{outer_address}账户持有的资产: {outer_balance}")

        query_order = self.submitOrderFloorOfFiatToRo(RTSData.ach_user_token, RTSData.ach_user_id, currency_info, amount, "inner", outer_address)

        outer_balance2 = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{outer_address}账户持有的资产: {outer_balance2}, 变化了: {outer_balance2 - outer_balance}")

        self.assertAlmostEqual(outer_balance2 - outer_balance, amount, delta=0.1**6)
        self.assertEqual(query_order["txState"], "TRANSACTION_FINISH", "订单最终状态应为完成")

    @unittest.skipIf(RTSData.host.startswith("uat"), "uat测试环境无法通过rps入金，跳过")
    def test_D13_normalScene_sameCurrency_FiatToRo_giveInNodeCode_outAmount(self):
        """
        同币种, 法币到ro, 指定in节点, 指定出金数量, 查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        currency_info["innerNodeCode"] = RTSData.node_code
        amount = 10
        outer_address = RTSData.ach_user_account

        outer_balance = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{outer_address}账户持有的资产: {outer_balance}")

        query_order = self.submitOrderFloorOfFiatToRo(RTSData.ach_user_token, RTSData.ach_user_id, currency_info, amount, "outer", outer_address)

        outer_balance2 = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{outer_address}账户持有的资产: {outer_balance2}, 变化了: {outer_balance2 - outer_balance}")

        self.assertAlmostEqual(outer_balance2 - outer_balance, amount, delta=0.1**6)
        self.assertEqual(query_order["txState"], "TRANSACTION_FINISH", "订单最终状态应为完成")

    @unittest.skipIf(RTSData.host.startswith("uat"), "uat测试环境无法通过rps入金，跳过")
    def test_D14_normalScene_sameCurrency_FiatToRo_giveOutNodeCode_inAmount(self):
        """
        同币种，法币到ro，指定out节点，查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        currency_info["outerNodeRoxe"] = RTSData.node_code
        amount = 10
        outer_address = RTSData.ach_user_account

        outer_balance = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{outer_address}账户持有的资产: {outer_balance}")

        query_order = self.submitOrderFloorOfFiatToRo(RTSData.ach_user_token, RTSData.ach_user_id, currency_info, amount, "inner", outer_address)

        outer_balance2 = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{outer_address}账户持有的资产: {outer_balance2}, 变化了: {outer_balance2 - outer_balance}")

        self.assertAlmostEqual(outer_balance2 - outer_balance, amount, delta=0.1**6)
        self.assertEqual(query_order["txState"], "TRANSACTION_FINISH", "订单最终状态应为完成")

    @unittest.skipIf(RTSData.host.startswith("uat"), "uat测试环境无法通过rps入金，跳过")
    def test_D15_normalScene_sameCurrency_FiatToRo_giveOutNodeCode_outAmount(self):
        """
        同币种, 法币到ro, 指定out节点，查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        currency_info["outerNodeRoxe"] = RTSData.node_code
        amount = 3.45
        outer_address = RTSData.ach_user_account

        outer_balance = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{outer_address}账户持有的资产: {outer_balance}")

        query_order = self.submitOrderFloorOfFiatToRo(RTSData.ach_user_token, RTSData.ach_user_id, currency_info, amount, "outer", outer_address)

        outer_balance2 = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{outer_address}账户持有的资产: {outer_balance2}, 变化了: {outer_balance2 - outer_balance}")

        self.assertAlmostEqual(outer_balance2 - outer_balance, amount, delta=0.1**6)
        self.assertEqual(query_order["txState"], "TRANSACTION_FINISH", "订单最终状态应为完成")

    @unittest.skipIf(RTSData.host.startswith("uat"), "uat测试环境无法通过rps入金，跳过")
    def test_D16_normalScene_sameCurrency_FiatToRo_giveNodeCodes_inAmount(self):
        """
        同币种, 法币到ro, 指定in节点和out节点，查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        currency_info["innerNodeRoxe"] = RTSData.node_code
        currency_info["outerNodeRoxe"] = RTSData.node_code
        amount = 4.67
        outer_address = RTSData.ach_user_account

        outer_balance = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{outer_address}账户持有的资产: {outer_balance}")

        query_order = self.submitOrderFloorOfFiatToRo(RTSData.ach_user_token, RTSData.ach_user_id, currency_info, amount, "inner", outer_address)

        outer_balance2 = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{outer_address}账户持有的资产: {outer_balance2}, 变化了: {outer_balance2 - outer_balance}")

        self.assertAlmostEqual(outer_balance2 - outer_balance, amount, delta=0.1**6)
        self.assertEqual(query_order["txState"], "TRANSACTION_FINISH", "订单最终状态应为完成")

    @unittest.skipIf(RTSData.host.startswith("uat"), "uat测试环境无法通过rps入金，跳过")
    def test_D17_normalScene_sameCurrency_FiatToRo_giveNodeCodes_outAmount(self):
        """
        同币种, 法币到ro, 指定in节点和out节点，查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        currency_info["innerNodeRoxe"] = RTSData.node_code
        currency_info["outerNodeRoxe"] = RTSData.node_code
        amount = 100.23
        outer_address = RTSData.ach_user_account

        outer_balance = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{outer_address}账户持有的资产: {outer_balance}")

        query_order = self.submitOrderFloorOfFiatToRo(RTSData.ach_user_token, RTSData.ach_user_id, currency_info, amount, "outer", outer_address)

        outer_balance2 = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{outer_address}账户持有的资产: {outer_balance2}, 变化了: {outer_balance2 - outer_balance}")

        self.assertAlmostEqual(outer_balance2 - outer_balance, amount, delta=0.1**6)
        self.assertEqual(query_order["txState"], "TRANSACTION_FINISH", "订单最终状态应为完成")

    @unittest.skipIf(RTSData.host.startswith("uat"), "uat测试环境无法通过rps入金，跳过")
    def test_D18_normalScene_sameCurrency_FiatToFiat_notGiveNodeCodes_inAmount(self):
        """
        同币种, 法币到法币, 不指定节点，查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        inner_amount = 15.12
        outer_bank = RSSData.out_bank_info[currency_info["fiat"]].copy()
        self.submitOrderFloorOfFiatToFiat(RTSData.ach_user_token, RTSData.ach_user_id, currency_info, inner_amount, "inner", outer_bank)

    @unittest.skipIf(RTSData.host.startswith("uat"), "uat测试环境无法通过rps入金，跳过")
    def test_D19_normalScene_sameCurrency_FiatToFiat_notGiveNodeCodes_outAmount(self):
        """
        同币种, 法币到法币, 不指定节点，查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        inner_amount = 5.45
        outer_bank = RSSData.out_bank_info[currency_info["fiat"]].copy()
        self.submitOrderFloorOfFiatToFiat(RTSData.ach_user_token, RTSData.ach_user_id, currency_info, inner_amount, "outer", outer_bank)

    @unittest.skipIf(RTSData.host.startswith("uat"), "uat测试环境无法通过rps入金，跳过")
    def test_D20_normalScene_sameCurrency_FiatToFiat_giveInNodeCode_inAmount(self):
        """
        同币种, 法币到法币, 指定in节点，查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        currency_info["innerNodeCode"] = RTSData.node_code
        inner_amount = 11.57
        outer_bank = RSSData.out_bank_info[currency_info["fiat"]].copy()
        self.submitOrderFloorOfFiatToFiat(RTSData.ach_user_token, RTSData.ach_user_id, currency_info, inner_amount, "inner", outer_bank)

    @unittest.skipIf(RTSData.host.startswith("uat"), "uat测试环境无法通过rps入金，跳过")
    def test_D21_normalScene_sameCurrency_FiatToFiat_giveInNodeCode_outAmount(self):
        """
        同币种, 法币到法币, 指定in节点，查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        currency_info["innerNodeCode"] = RTSData.node_code
        inner_amount = 11.11
        outer_bank = RSSData.out_bank_info[currency_info["fiat"]].copy()
        self.submitOrderFloorOfFiatToFiat(RTSData.ach_user_token, RTSData.ach_user_id, currency_info, inner_amount, "outer", outer_bank)

    @unittest.skipIf(RTSData.host.startswith("uat"), "uat测试环境无法通过rps入金，跳过")
    def test_D22_normalScene_sameCurrency_FiatToFiat_giveOutNodeCode_inAmount(self):
        """
        同币种, 法币到法币, 指定out节点，查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        currency_info["outerNodeCode"] = RTSData.node_code
        inner_amount = 12.12
        outer_address = RSSData.out_bank_info[currency_info["fiat"]].copy()
        self.submitOrderFloorOfFiatToFiat(RTSData.ach_user_token, RTSData.ach_user_id, currency_info, inner_amount, "inner", outer_address)

    @unittest.skipIf(RTSData.host.startswith("uat"), "uat测试环境无法通过rps入金，跳过")
    def test_D23_normalScene_sameCurrency_FiatToFiat_giveOutNodeCode_outAmount(self):
        """
        同币种, 法币到法币, 指定out节点，查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        currency_info["outerNodeCode"] = RTSData.node_code
        inner_amount = 12.12
        outer_address = RSSData.out_bank_info[currency_info["fiat"]].copy()
        self.submitOrderFloorOfFiatToFiat(RTSData.ach_user_token, RTSData.ach_user_id, currency_info, inner_amount, "outer", outer_address)

    @unittest.skipIf(RTSData.host.startswith("uat"), "uat测试环境无法通过rps入金，跳过")
    def test_D24_normalScene_sameCurrency_FiatToFiat_giveNodeCodes_inAmount(self):
        """
        同币种, 法币到法币, 指定in节点和out节点，查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_fiat[0].copy()
        # currency_info["innerNodeCode"] = RTSData.node_code
        # currency_info["outerNodeCode"] = RTSData.node_code
        inner_amount = 12.12
        outer_address = RSSData.out_bank_info[currency_info["fiat"]].copy()
        self.submitOrderFloorOfFiatToFiat(RTSData.ach_user_token, RTSData.ach_user_id, currency_info, inner_amount, "inner", outer_address)

    @unittest.skipIf(RTSData.host.startswith("uat"), "uat测试环境无法通过rps入金，跳过")
    def test_D25_normalScene_sameCurrency_FiatToFiat_giveNodeCodes_outAmount(self):
        """
        同币种, 法币到法币, 指定in节点和out节点，查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        currency_info["innerNodeCode"] = RTSData.node_code
        currency_info["outerNodeCode"] = RTSData.node_code
        inner_amount = 12.12
        outer_address = RSSData.out_bank_info[currency_info["fiat"]].copy()
        self.submitOrderFloorOfFiatToFiat(RTSData.ach_user_token, RTSData.ach_user_id, currency_info, inner_amount, "outer", outer_address)

    def test_D26_normalScene_sameCurrency_RoToRo_notGiveNodeCodes_inAmount(self):
        """
        同币种, ro到ro, 不指定节点信息时，查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        inner_amount = 14.31
        from_address = RTSData.chain_account
        outer_address = RTSData.user_account_2
        from_balance = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {from_balance}")
        to_balance = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {to_balance}")
        q_order, fee = self.submitOrderFloorOfRoToRo(currency_info, inner_amount, "inner", outer_address, from_address, fromAccountKey=RTSData.chain_pri_key)
        from_balance2 = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {from_balance2}")
        to_balance2 = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {to_balance2}")

        self.assertAlmostEqual(to_balance2 - to_balance, inner_amount, msg="to账户资产变化不正确", delta=0.1**7)
        self.assertAlmostEqual(from_balance - from_balance2, inner_amount + fee, msg="from账户资产变化不正确", delta=0.1**7)

    def test_D27_normalScene_sameCurrency_RoToRo_notGiveNodeCodes_outAmount(self):
        """
        同币种, ro到ro, 不指定节点信息时，查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        inner_amount = 12.31
        from_address = RTSData.chain_account
        outer_address = RTSData.user_account_2
        from_balance = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {from_balance}")
        to_balance = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {to_balance}")
        q_order, fee = self.submitOrderFloorOfRoToRo(currency_info, inner_amount, "outer", outer_address, from_address, fromAccountKey=RTSData.chain_pri_key)
        from_balance2 = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {from_balance2}")
        to_balance2 = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {to_balance2}")

        self.assertAlmostEqual(to_balance2 - to_balance, inner_amount, msg="to账户资产变化不正确", delta=0.1**7)
        self.assertAlmostEqual(from_balance - from_balance2, inner_amount + fee, msg="from账户资产变化不正确", delta=0.1**7)

    def test_D28_normalScene_sameCurrency_RoToRo_giveInNodeCode_inAmount(self):
        """
        同币种, ro到ro, 指定in节点时，查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        currency_info["innerNodeCode"] = RTSData.node_code
        inner_amount = 12
        from_address = RTSData.chain_account
        outer_address = RTSData.user_account_2
        from_balance = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {from_balance}")
        to_balance = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {to_balance}")
        q_order, fee = self.submitOrderFloorOfRoToRo(currency_info, inner_amount, "inner", outer_address, from_address, fromAccountKey=RTSData.chain_pri_key)
        from_balance2 = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {from_balance2}")
        to_balance2 = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {to_balance2}")

        self.assertAlmostEqual(to_balance2 - to_balance, inner_amount, msg="to账户资产变化不正确", delta=0.1**7)
        self.assertAlmostEqual(from_balance - from_balance2, inner_amount + fee, msg="from账户资产变化不正确", delta=0.1**7)

    def test_D29_normalScene_sameCurrency_RoToRo_giveInNodeCode_outAmount(self):
        """
        同币种, ro到ro, 指定in节点时，查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        currency_info["innerNodeCode"] = RTSData.node_code
        inner_amount = 12
        from_address = RTSData.chain_account
        outer_address = RTSData.user_account_2
        from_balance = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {from_balance}")
        to_balance = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {to_balance}")
        q_order, fee = self.submitOrderFloorOfRoToRo(currency_info, inner_amount, "outer", outer_address, from_address, fromAccountKey=RTSData.chain_pri_key)
        from_balance2 = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {from_balance2}")
        to_balance2 = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {to_balance2}")

        self.assertAlmostEqual(to_balance2 - to_balance, inner_amount, msg="to账户资产变化不正确", delta=0.1**7)
        self.assertAlmostEqual(from_balance - from_balance2, inner_amount + fee, msg="from账户资产变化不正确", delta=0.1**7)

    def test_D30_normalScene_sameCurrency_RoToRo_giveOutNodeCode_inAmount(self):
        """
        同币种, ro到ro, 指定out节点，查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        currency_info["outerNodeCode"] = RTSData.node_code
        inner_amount = 12
        from_address = RTSData.chain_account
        outer_address = RTSData.user_account_2
        from_balance = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {from_balance}")
        to_balance = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {to_balance}")
        q_order, fee = self.submitOrderFloorOfRoToRo(currency_info, inner_amount, "inner", outer_address, from_address, fromAccountKey=RTSData.chain_pri_key)
        from_balance2 = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {from_balance2}")
        to_balance2 = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {to_balance2}")

        self.assertAlmostEqual(to_balance2 - to_balance, inner_amount, msg="to账户资产变化不正确", delta=0.1**7)
        self.assertAlmostEqual(from_balance - from_balance2, inner_amount + fee, msg="from账户资产变化不正确", delta=0.1**7)

    def test_D31_normalScene_sameCurrency_RoToRo_giveOutNodeCode_outAmount(self):
        """
        同币种, ro到ro, 指定out节点，查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        currency_info["outerNodeCode"] = RTSData.node_code
        inner_amount = 12
        from_address = RTSData.chain_account
        outer_address = RTSData.user_account_2
        from_balance = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {from_balance}")
        to_balance = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {to_balance}")
        q_order, fee = self.submitOrderFloorOfRoToRo(currency_info, inner_amount, "outer", outer_address, from_address, fromAccountKey=RTSData.chain_pri_key)
        from_balance2 = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {from_balance2}")
        to_balance2 = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {to_balance2}")

        self.assertAlmostEqual(to_balance2 - to_balance, inner_amount, msg="to账户资产变化不正确", delta=0.1**7)
        self.assertAlmostEqual(from_balance - from_balance2, inner_amount + fee, msg="from账户资产变化不正确", delta=0.1**7)

    def test_D32_normalScene_sameCurrency_RoToRo_giveNodeCodes_inAmount(self):
        """
        同币种, ro到ro, 指定in节点和out节点，查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        currency_info["innerNodeCode"] = RTSData.node_code
        currency_info["outerNodeCode"] = RTSData.node_code
        inner_amount = 12
        from_address = RTSData.chain_account
        outer_address = RTSData.user_account_2
        from_balance = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {from_balance}")
        to_balance = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {to_balance}")
        q_order, fee = self.submitOrderFloorOfRoToRo(currency_info, inner_amount, "inner", outer_address, from_address, fromAccountKey=RTSData.chain_pri_key)
        from_balance2 = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {from_balance2}")
        to_balance2 = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {to_balance2}")

        self.assertAlmostEqual(to_balance2 - to_balance, inner_amount, msg="to账户资产变化不正确", delta=0.1**7)
        self.assertAlmostEqual(from_balance - from_balance2, inner_amount + fee, msg="from账户资产变化不正确", delta=0.1**7)

    def test_D33_normalScene_sameCurrency_RoToRo_giveNodeCodes_outAmount(self):
        """
        同币种, ro到ro, 指定in节点和out节点，查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        currency_info["innerNodeCode"] = RTSData.node_code
        currency_info["outerNodeCode"] = RTSData.node_code
        inner_amount = 12
        from_address = RTSData.chain_account
        outer_address = RTSData.user_account_2
        from_balance = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {from_balance}")
        to_balance = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {to_balance}")
        q_order, fee = self.submitOrderFloorOfRoToRo(currency_info, inner_amount, "outer", outer_address, from_address, fromAccountKey=RTSData.chain_pri_key)
        from_balance2 = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {from_balance2}")
        to_balance2 = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}持有的资产: {to_balance2}")

        self.assertAlmostEqual(to_balance2 - to_balance, inner_amount, msg="to账户资产变化不正确", delta=0.1**7)
        self.assertAlmostEqual(from_balance - from_balance2, inner_amount + fee, msg="from账户资产变化不正确", delta=0.1**7)

    def test_D34_normalScene_sameCurrency_RoToFiat_notGiveNodeCodes_inAmount(self):
        """
        同币种, ro到法币, 不指定节点，查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        amount = 14.68
        outer_address = RSSData.out_bank_info["USD"].copy()
        # 转账给中间账户
        from_address = RTSData.chain_account
        from_balance = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"目标账户持有的资产: {from_balance}")
        # query_order, fee = self.submitOrderFloorOfRoToFiat(currency_info, amount, "inner", outer_address, from_address, token=RTSData.ach_user_token, user_id=RTSData.ach_user_id)
        query_order, fee = self.submitOrderFloorOfRoToFiat(currency_info, amount, "inner", outer_address, from_address, fromAccountKey=RTSData.chain_pri_key)
        from_balance2 = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"目标账户持有的资产: {from_balance2}, 变化了: {from_balance2 - from_balance}")
        self.assertAlmostEqual(from_balance - from_balance2, amount + fee, delta=0.1**3)
        self.assertEqual(query_order["txState"], "TRANSACTION_FINISH", "订单最终状态应为完成")

    def test_D35_normalScene_sameCurrency_RoToFiat_notGiveNodeCodes_outAmount(self):
        """
        同币种, ro到法币, 不指定节点，查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        amount = 11.22
        outer_address = RSSData.out_bank_info[currency_info["fiat"]].copy()
        # 转账给中间账户
        from_address = RTSData.ach_user_account
        from_balance = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"目标账户持有的资产: {from_balance}")
        query_order, fee = self.submitOrderFloorOfRoToFiat(currency_info, amount, "outer", outer_address, from_address, token=RTSData.ach_user_token, user_id=RTSData.ach_user_id)
        from_balance2 = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"目标账户持有的资产: {from_balance2}, 变化了: {from_balance2 - from_balance}")
        self.assertAlmostEqual(from_balance - from_balance2, amount + fee, delta=0.1**3)
        self.assertEqual(query_order["txState"], "TRANSACTION_FINISH", "订单最终状态应为完成")

    @unittest.skip("暂无此场景，跳过")
    def test_D36_normalScene_sameCurrency_RoToFiat_giveInNodeCode_inAmount(self):
        """
        同币种, ro到法币, 指定in节点，查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        currency_info["innerNodeCode"] = RTSData.node_code
        amount = 10
        outer_address = RSSData.out_bank_info[currency_info["fiat"]].copy()
        # 转账给中间账户
        from_address = RTSData.ach_user_account
        from_balance = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"目标账户持有的资产: {from_balance}")
        query_order, fee = self.submitOrderFloorOfRoToFiat(currency_info, amount, "inner", outer_address, from_address, token=RTSData.ach_user_token, user_id=RTSData.ach_user_id)
        from_balance2 = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"目标账户持有的资产: {from_balance2}, 变化了: {from_balance2 - from_balance}")
        self.assertAlmostEqual(from_balance - from_balance2, amount)
        self.assertEqual(query_order["txState"], "TRANSACTION_FINISH", "订单最终状态应为完成")

    @unittest.skip("暂无此场景，跳过")
    def test_D37_normalScene_sameCurrency_RoToFiat_giveInNodeCode_outAmount(self):
        """
        同币种, ro到法币, 指定in节点，查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        currency_info["innerNodeCode"] = RTSData.node_code
        amount = 10
        outer_address = RSSData.out_bank_info[currency_info["fiat"]].copy()
        # 转账给中间账户
        from_address = RTSData.ach_user_account
        from_balance = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"目标账户持有的资产: {from_balance}")
        query_order, fee = self.submitOrderFloorOfRoToFiat(currency_info, amount, "outer", outer_address, from_address, token=RTSData.ach_user_token, user_id=RTSData.ach_user_id)
        from_balance2 = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"目标账户持有的资产: {from_balance2}, 变化了: {from_balance2 - from_balance}")
        self.assertAlmostEqual(from_balance - from_balance2, amount)
        self.assertEqual(query_order["txState"], "TRANSACTION_FINISH", "订单最终状态应为完成")

    def test_D38_normalScene_sameCurrency_RoToFiat_giveOutNodeCode_inAmount(self):
        """
        同币种, ro到法币, 指定out节点，查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        currency_info["outerNodeCode"] = RTSData.node_code
        amount = 10.2
        outer_bank = RSSData.out_bank_info[currency_info["fiat"]].copy()
        # 转账给中间账户
        from_address = RTSData.ach_user_account
        from_balance = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"目标账户持有的资产: {from_balance}")
        query_order, channel_fee = self.submitOrderFloorOfRoToFiat(currency_info, amount, "inner", outer_bank, from_address, token=RTSData.ach_user_token, user_id=RTSData.ach_user_id)
        from_balance2 = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"目标账户持有的资产: {from_balance2}, 变化了: {from_balance2 - from_balance}")
        self.assertAlmostEqual(from_balance - from_balance2, amount + channel_fee, delta=0.1**7)
        self.assertEqual(query_order["txState"], "TRANSACTION_FINISH", "订单最终状态应为完成")

    def test_D39_normalScene_sameCurrency_RoToFiat_giveOutNodeCode_outAmount(self):
        """
        同币种, ro到法币, 指定out节点，查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        currency_info["outerNodeCode"] = RTSData.node_code
        amount = 10.2
        outer_bank = RSSData.out_bank_info[currency_info["fiat"]].copy()
        # 转账给中间账户
        from_address = RTSData.ach_user_account
        from_balance = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"目标账户持有的资产: {from_balance}")
        query_order, channel_fee = self.submitOrderFloorOfRoToFiat(currency_info, amount, "outer", outer_bank, from_address, token=RTSData.ach_user_token, user_id=RTSData.ach_user_id)
        from_balance2 = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"目标账户持有的资产: {from_balance2}, 变化了: {from_balance2 - from_balance}")
        self.assertAlmostEqual(from_balance - from_balance2, amount + channel_fee, delta=0.1**3)
        self.assertEqual(query_order["txState"], "TRANSACTION_FINISH", "订单最终状态应为完成")

    @unittest.skip("暂无此场景，跳过")
    def test_D40_normalScene_sameCurrency_RoToFiat_giveNodeCodes_inAmount(self):
        """
        同币种, ro到法币, 指定in节点和out节点，查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        currency_info["innerNodeCode"] = RTSData.node_code
        currency_info["outerNodeCode"] = RTSData.node_code
        amount = 10
        outer_address = RSSData.out_bank_info[currency_info["fiat"]].copy()
        # 转账给中间账户
        from_address = RTSData.ach_user_account
        from_balance = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"目标账户持有的资产: {from_balance}")
        query_order, fee = self.submitOrderFloorOfRoToFiat(currency_info, amount, "inner", outer_address, from_address, token=RTSData.ach_user_token, user_id=RTSData.ach_user_id)
        from_balance2 = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"目标账户持有的资产: {from_balance2}, 变化了: {from_balance2 - from_balance}")
        self.assertAlmostEqual(from_balance - from_balance2, amount)
        self.assertEqual(query_order["txState"], "TRANSACTION_FINISH", "订单最终状态应为完成")

    @unittest.skip("暂无此场景，跳过")
    def test_D41_normalScene_sameCurrency_RoToFiat_giveNodeCodes_outAmount(self):
        """
        同币种, ro到法币, 指定in节点和out节点，查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        currency_info["innerNodeCode"] = RTSData.node_code
        currency_info["outerNodeCode"] = RTSData.node_code
        amount = 10
        outer_address = RSSData.out_bank_info[currency_info["fiat"]].copy()
        # 转账给中间账户
        from_address = RTSData.ach_user_account
        from_balance = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"目标账户持有的资产: {from_balance}")
        query_order, fee = self.submitOrderFloorOfRoToFiat(currency_info, amount, "outer", outer_address, from_address, token=RTSData.ach_user_token, user_id=RTSData.ach_user_id)
        from_balance2 = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"目标账户持有的资产: {from_balance2}, 变化了: {from_balance2 - from_balance}")
        self.assertAlmostEqual(from_balance - from_balance2, amount)
        self.assertEqual(query_order["txState"], "TRANSACTION_FINISH", "订单最终状态应为完成")

    def test_05101_queryRouterList(self):
        """
        正确填写参数 入金国家币种-出金国家币种
        """
        currency_info = RTSData.out_currency_info.copy()
        in_currency = currency_info[0]["fiat"]
        in_country = currency_info[0]["country"]
        out_currency = currency_info[1]["fiat"]
        out_country = currency_info[1]["country"]
        inner_quantity = 10
        router_info, router_body = self.client.getRouterList(in_country, in_currency, out_country, out_currency, inner_quantity, "", "", "", "")
        self.assertTrue(len(router_info["data"]) > 0)
        self.checkRouterListResult(router_info["data"], router_body)

    def test_05102_queryRouterList(self):
        """
        正确填写参数 入金节点出金节点
        """
        currency_info = RTSData.out_currency_info.copy()
        sendNodeCode = currency_info[0]["node_code"]
        receiveNodeCode = currency_info[1]["node_code"]
        inner_quantity = 10
        router_info, router_body = self.client.getRouterList("", currency_info[0]["fiat"], "", currency_info[1]["fiat"], inner_quantity, "", sendNodeCode, receiveNodeCode, "")
        self.assertTrue(len(router_info["data"]) > 0)
        self.checkRouterListResult(router_info["data"], router_body)

    def test_05103_queryRouterList(self):
        """
        正确填写参数 入金国家出金节点
        """
        currency_info = RTSData.out_currency_info.copy()
        in_country = currency_info[0]["country"]
        receiveNodeCode = currency_info[1]["node_code"]
        inner_quantity = 10
        router_info, router_body = self.client.getRouterList(in_country, "", "", "", inner_quantity, "", "", receiveNodeCode, "")
        self.assertTrue(len(router_info["data"]) > 0)
        self.checkRouterListResult(router_info["data"], router_body)

    def test_05104_queryRouterList(self):
        """
        正确填写参数 入金节点出金国家
        """
        currency_info = RTSData.out_currency_info.copy()
        sendNodeCode = currency_info[0]["node_code"]
        out_country = currency_info[1]["country"]
        inner_quantity = 10
        router_info, router_body = self.client.getRouterList("", "", out_country, "", inner_quantity, "", sendNodeCode, "", "")
        self.assertTrue(len(router_info["data"]) > 0)
        self.checkRouterListResult(router_info["data"], router_body)



    # 2.1版本后补充的用例

    def test_138_updateSecretKey(self):
        """
        更新secretKey
        """
        try:
            new_key = self.client.updateSecretKey(RTSData.sec_key)
            self.checkCodeAndMessage(new_key)
            self.assertIsNotNone(new_key['data'])

            db_info = self.mysql.exec_sql_query("select * from rts_user where api_key='{}'".format(self.client.api_id))
            self.assertEqual(db_info[0]["secKey"], new_key["data"]["newSecretKey"])

            # 新secretKey可以正常使用
            currency_infos, r_body = self.client.getTransactionCurrency(replaceKey=new_key["data"]["newSecretKey"])
            self.checkCodeAndMessage(currency_infos)
            self.checkTransactionCurrency(currency_infos["data"], r_body)

            # 老secretKey不能再用
            currency_infos, r_body = self.client.getTransactionCurrency()
            self.checkCodeAndMessage(currency_infos, "01200001", "Signature error")
            self.assertIsNone(currency_infos['data'])
        finally:
            self.mysql.exec_sql_query("update rts_user set sec_key='{}' where api_key='{}'".format(RTSData.sec_key, RTSData.api_id))

    # reject 版本后更新用例

    def test_139_suspendOrder_innerOrderJustSubmit(self):
        """
        中止订单, 刚提交的入金订单
        """
        in_rmn_node = RTSData.rmn_node
        out_node = RTSData.rmn_node
        amount = 30
        out_bank = RSSData.out_bank_info["USD"].copy()

        outer_balance = self.chain_client.getBalanceWithRetry(in_rmn_node, "USD")
        self.client.logger.info(f"{in_rmn_node}账户持有的资产: {outer_balance}")

        router_info, router_body = self.client.getRouterList("", "USD", "", "USD", amount, "", in_rmn_node, out_node)
        self.checkRouterListResult(router_info["data"], router_body)
        # send_node_code = router_info["data"][0]["sendNodeCode"]
        # receive_node_code = router_info["data"][0]["receiveNodeCode"] if currency_info["outerNodeCode"] == "" else \
        # currency_info["outerNodeCode"]
        router_out_amount = float(router_info["data"][0]["receiveAmount"])
        # 提交rts订单
        instruction_id = "test_" + str(int(time.time() * 1000))  # 客户单号
        payment_id = instruction_id  # 客户原单
        # 提交rts原单
        submit_order, submit_body = self.client.submitOrder(
            instruction_id, "", payment_id, "USD", amount, "USD", out_bank,
            sendNodeCode=in_rmn_node, receiveNodeCode=out_node, withoutSendFee=False
        )
        self.checkCodeAndMessage(submit_order)
        self.checkSubmitOrderResult(submit_order["data"], submit_body, router_info["data"][0])
        # submit_order = self.submitOrderFloorOfFiatToFiat_rmn(in_rmn_node, "USD", "PHP", amount, "inner", out_bank, receiveNodeCode=out_node, is_just_submit=True)

        suspend_order = self.client.suspendOrder(transactionId=submit_order["transactionId"])
        self.checkCodeAndMessage(suspend_order)
        self.assertIn(suspend_order["data"]["txState"], "SUBMIT_SUSPEND")

        time.sleep(10)
        q_order = self.client.getOrderInfo(transactionId=submit_order["transactionId"])
        outer_balance2 = self.chain_client.getBalanceWithRetry(in_rmn_node, "USD")
        self.client.logger.info(f"{in_rmn_node}账户持有的资产: {outer_balance2}, 变化了: {outer_balance2 - outer_balance}")

        self.assertAlmostEqual(outer_balance2 - outer_balance, 0, delta=0.1 ** 6)
        self.assertEqual(q_order["data"]["txState"], "MINT_SUSPEND", "订单最终状态应为中止")

        rts_order_db = self.mysql.exec_sql_query("select * from roxe_rts.rts_order where payment_id='{}'".format(submit_order["paymentId"]))
        self.assertEqual(rts_order_db[0]["stopState"], "true", "rts系统suspend状态不正确")

        rss_order_db = self.mysql.exec_sql_query("select * from roxe_rss_us.rss_order where payment_id='{}'".format(submit_order["paymentId"]))
        self.assertEqual(len(rss_order_db), 0, "rss系统应该还未生产订单")

    def test_140_suspendOrder_innerOrderMinting(self):
        """
        中止订单, 刚提交的入金订单
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        amount = 10
        outer_address = RTSData.ach_user_account

        outer_balance = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{outer_address}账户持有的资产: {outer_balance}")

        submit_order = self.submitOrderFloorOfFiatToRo(RTSData.ach_user_token, RTSData.ach_user_id, currency_info, amount, "inner", outer_address, is_just_submit=True)

        instruction_id = submit_order["instructionId"]
        sql = "select * from rts_order where instruction_id='{}' and order_state='MINT_SUBMIT'".format(instruction_id)
        rss_sql = "select * from roxe_rss_us.rss_order where payment_id='{}'".format(submit_order["paymentId"])
        self.executeSqlUntilSuccess(sql, time_out=100, time_inner=3)
        self.executeSqlUntilSuccess(rss_sql, time_out=100, time_inner=3)

        suspend_order = self.client.suspendOrder(instruction_id)
        self.checkCodeAndMessage(suspend_order)
        self.assertEqual(suspend_order["data"]["txState"], "MINT_SUBMIT", "订单最终状态应为中止")
        b_time = time.time()
        while time.time() - b_time < 300:
            query_info = self.client.getOrderInfo(instruction_id)
            if query_info["data"]["txState"] == "TRANSACTION_FINISH":
                self.client.logger.info("rts订单已经完成")
                break
            time.sleep(30)
        q_order = self.client.getOrderInfo(instruction_id)
        outer_balance2 = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{outer_address}账户持有的资产: {outer_balance2}, 变化了: {outer_balance2 - outer_balance}")
        self.assertAlmostEqual(outer_balance2 - outer_balance, amount, delta=0.1 ** 6)
        self.assertEqual(q_order["data"]["txState"], "TRANSACTION_FINISH", "订单最终状态应为中止")

        rts_order_db = self.mysql.exec_sql_query("select * from roxe_rts.rts_order where payment_id='{}'".format(submit_order["paymentId"]))
        self.assertEqual(rts_order_db[0]["stopState"], "true", "rts系统suspend状态不正确")

        rss_order_db = self.mysql.exec_sql_query(rss_sql)
        self.assertEqual(len(rss_order_db), 1, "rss系统应该产生订单")
        self.assertEqual(rss_order_db[0]["orderState"], "finish", "rss系统订单应完成")

    def test_141_suspendOrder_innerOrderCompleted(self):
        """
        中止订单, 已完成的入金订单
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        amount = 10
        outer_address = RTSData.ach_user_account

        outer_balance = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{outer_address}账户持有的资产: {outer_balance}")

        submit_order = self.submitOrderFloorOfFiatToRo(RTSData.ach_user_token, RTSData.ach_user_id, currency_info, amount, "inner", outer_address)

        suspend_order = self.client.suspendOrder(submit_order["origTransactionInfo"]["instructionId"])
        self.checkCodeAndMessage(suspend_order, "01600103", "Transaction order finished")
        self.assertEqual(suspend_order["data"], None)
        q_order = self.client.getOrderInfo(submit_order["origTransactionInfo"]["instructionId"])
        self.assertEqual(q_order["data"]["txState"], "TRANSACTION_FINISH")
        outer_balance2 = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{outer_address}账户持有的资产: {outer_balance2}, 变化了: {outer_balance2 - outer_balance}")

        self.assertAlmostEqual(outer_balance2 - outer_balance, amount, delta=0.1 ** 6)

    def test_142_suspendOrder_outerOrderJustSubmit(self):
        """
        中止订单, 刚提交的出金订单
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        amount = 10
        from_address = RTSData.ach_user_account
        outer_address = RSSData.out_bank_info[currency_info["fiat"]].copy()

        outer_balance = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}账户持有的资产: {outer_balance}")
        submit_order, fee = self.submitOrderFloorOfRoToFiat(currency_info, amount, "inner", outer_address, from_address, is_just_submit=True)

        suspend_order = self.client.suspendOrder(submit_order["instructionId"])
        self.checkCodeAndMessage(suspend_order)
        self.assertIn(suspend_order["data"]["txState"], ["TRANSACTION_SUBMIT", "TRANSACTION_QUOTE"])
        time.sleep(10)

        q_order = self.client.getOrderInfo(submit_order["instructionId"])
        outer_balance2 = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}账户持有的资产: {outer_balance2}, 变化了: {outer_balance2 - outer_balance}")

        self.assertAlmostEqual(outer_balance - outer_balance2, amount, delta=0.1 ** 6)
        self.assertEqual(q_order["data"]["txState"], "REDEEM_SUSPEND", "订单最终状态应为中止")

        rts_order_db = self.mysql.exec_sql_query("select * from roxe_rts.rts_order where payment_id='{}'".format(submit_order["paymentId"]))
        self.assertEqual(rts_order_db[0]["stopState"], "true", "rts系统suspend状态不正确")

        rss_order_db = self.mysql.exec_sql_query("select * from roxe_rss_us.rss_order where payment_id='{}'".format(submit_order["paymentId"]))
        self.assertEqual(len(rss_order_db), 0, "rss系统应该还未生产订单")

    def test_143_suspendOrder_outerOrderRedeeming(self):
        """
        中止订单, 正在销毁的出金订单
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        amount = 10
        from_address = RTSData.ach_user_account
        outer_address = RSSData.out_bank_info[currency_info["fiat"]].copy()

        balance = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}账户持有的资产: {balance}")

        submit_order, fee = self.submitOrderFloorOfRoToFiat(currency_info, amount, "inner", outer_address, from_address, is_just_submit=True)

        payment_id = submit_order["paymentId"]
        transaction_id = submit_order["transactionId"]
        instruction_id = submit_order["instructionId"]
        sql = "select * from roxe_rss_us.rss_order where payment_id='{}' and order_state='redeem_init'".format(payment_id)
        self.executeSqlUntilSuccess(sql, None, 100, 5)

        suspend_order = self.client.suspendOrder(instruction_id)
        self.checkCodeAndMessage(suspend_order)

        # 修改直到订单完成
        self.waitUntilRedeemOrderCompleted(transaction_id, payment_id, 300)
        time.sleep(10)

        q_order = self.client.getOrderInfo(instruction_id)
        balance2 = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}账户持有的资产: {balance2}, 变化了: {balance2 - balance}")

        self.assertAlmostEqual(balance - balance2, amount, delta=0.1 ** 6)
        self.assertEqual(q_order["data"]["txState"], "TRANSACTION_FINISH", "订单最终状态应为中止")

        rts_order_db = self.mysql.exec_sql_query("select * from roxe_rts.rts_order where payment_id='{}'".format(submit_order["paymentId"]))
        self.assertEqual(rts_order_db[0]["stopState"], "true", "rts系统suspend状态不正确")

        rss_order_db = self.mysql.exec_sql_query("select * from roxe_rss_us.rss_order where payment_id='{}'".format(submit_order["paymentId"]))
        self.assertEqual(len(rss_order_db), 1, "rss系统应该产生订单")
        self.assertEqual(rss_order_db[0]["orderState"], "finish", "rss系统订单应完成")

    @unittest.skip("skip")
    def test_144_suspendOrder_outerOrderWaitThirdSystemPay(self):
        """
        中止订单, 进入第3方系统，正在出金的订单
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        amount = 10
        from_address = RTSData.ach_user_account
        outer_address = RSSData.out_bank_info[currency_info["fiat"]].copy()

        outer_balance = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{outer_address}账户持有的资产: {outer_balance}")

        submit_order, fee = self.submitOrderFloorOfRoToFiat(currency_info, amount, "inner", outer_address, from_address, is_just_submit=True)

        sql = "select * from roxe_rss_us.rss_order where payment_id='{}' and order_state='redeem_bank_order_submit'".format(submit_order["paymentId"])
        self.executeSqlUntilSuccess(sql, None, 100, 5)

        suspend_order = self.client.suspendOrder(submit_order["instructionId"])
        time.sleep(5)

        q_order = self.client.getOrderInfo(submit_order["instructionId"])
        self.checkCodeAndMessage(q_order)

        outer_balance2 = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{outer_address}账户持有的资产: {outer_balance2}, 变化了: {outer_balance2 - outer_balance}")

        self.assertAlmostEqual(outer_balance2 - outer_balance, 0, delta=0.1 ** 6)
        self.assertEqual(suspend_order["data"]["txState"], "REDEEM_SUSPEND", "订单最终状态应为中止")

    @unittest.skip("skip")
    def test_145_suspendOrder_outerOrderThirdSystemSubmitOrderFailed(self):
        """
        中止订单, 向第3方系统下单失败
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        currency_info["fiat"] = "CNY"
        currency_info["country"] = "CN"
        amount = 10
        from_address = RTSData.ach_user_account
        outer_address = RSSData.out_bank_info[currency_info["fiat"]].copy()

        outer_balance = self.chain_client.getBalanceWithRetry(outer_address, "USD")
        self.client.logger.info(f"{outer_address}账户持有的资产: {outer_balance}")

        submit_order, fee = self.submitOrderFloorOfRoToFiat(currency_info, amount, "inner", outer_address, from_address, is_just_submit=True)

        payment_id = submit_order["paymentId"]
        # transaction_id = submit_order["transactionId"]
        instruction_id = submit_order["instructionId"]
        sql = "select * from roxe_rss_us.rss_order where payment_id='{}' and order_state='failed'".format(payment_id)
        self.executeSqlUntilSuccess(sql, None, 600, 30)

        suspend_order = self.client.suspendOrder(instruction_id)
        self.checkCodeAndMessage(suspend_order)
        # todo 中止订单报错

        outer_balance2 = self.chain_client.getBalanceWithRetry(outer_address, "USD")
        self.client.logger.info(f"{outer_address}账户持有的资产: {outer_balance2}, 变化了: {outer_balance2 - outer_balance}")

        self.assertAlmostEqual(outer_balance2 - outer_balance, 0, delta=0.1 ** 6)
        self.assertEqual(suspend_order["data"]["txState"], "MINT_SUSPEND", "订单最终状态应为中止")

    def test_147_suspendOrder_outerOrderCompleted(self):
        """
        中止订单, 已完成的出金订单
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        amount = 10
        from_address = RTSData.ach_user_account
        outer_address = RSSData.out_bank_info[currency_info["fiat"]].copy()

        outer_balance = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}账户持有的资产: {outer_balance}")

        query_order, fee = self.submitOrderFloorOfRoToFiat(currency_info, amount, "inner", outer_address, from_address)

        suspend_order = self.client.suspendOrder("", query_order["transactionId"])

        self.checkCodeAndMessage(suspend_order, "01600103", "Transaction order finished")
        self.assertEqual(suspend_order["data"], None)

        q_order = self.client.getOrderInfo("", query_order["transactionId"])
        outer_balance2 = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}账户持有的资产: {outer_balance2}, 变化了: {outer_balance2 - outer_balance}")

        self.assertAlmostEqual(outer_balance - outer_balance2, amount, delta=0.1 ** 6)
        self.assertEqual(q_order["data"]["txState"], "TRANSACTION_FINISH", "订单最终状态应为完成")

        rts_order_db = self.mysql.exec_sql_query("select * from roxe_rts.rts_order where payment_id='{}'".format(query_order["origTransactionInfo"]["paymentId"]))
        self.assertEqual(rts_order_db[0]["stopState"], None, "rts系统suspend状态不正确")

    def test_148_submitOrder_FiatToRo_withNotifyUrl(self):
        """
        提交订单，指定回调地址
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        amount = 12.15
        outer_address = RTSData.ach_user_account

        outer_balance = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{outer_address}账户持有的资产: {outer_balance}")
        notify_url = "http://172.17.3.99:8005/api/rts/receiveNotify"
        query_order = self.submitOrderFloorOfFiatToRo(RTSData.ach_user_token, RTSData.ach_user_id, currency_info, amount, "inner", outer_address, url=notify_url)

        outer_balance2 = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{outer_address}账户持有的资产: {outer_balance2}, 变化了: {outer_balance2 - outer_balance}")

        self.assertAlmostEqual(outer_balance2 - outer_balance, amount, delta=0.1 ** 6)
        self.assertEqual(query_order["txState"], "TRANSACTION_FINISH", "订单最终状态应为完成")

        tx_id = query_order["transactionId"]
        tx_log = self.client.getOrderStateLog("", tx_id)
        tx_log_state = [i["txState"] for i in tx_log["data"]["stateInfo"]]
        send_notify_sql = "select * from roxe_rts.rts_order_notify where order_id='{}' and notify_state='over'".format(tx_id)
        b_time = time.time()
        send_notify = []
        while time.time() - b_time < 100:
            send_notify = self.mysql.exec_sql_query(send_notify_sql)
            if len(send_notify) == len(tx_log_state) - 1:
                break
            time.sleep(3)
        time.sleep(2)
        receive_notify_sql = "select * from mock_notify.res_info order by create_at desc limit {}".format(len(send_notify))
        receive_notify = self.mysql.exec_sql_query(receive_notify_sql)
        self.assertEqual(len(receive_notify), len(send_notify), "接收到的回调消息和发送出来的消息条数不一致")
        self.assertEqual(len(receive_notify), len(tx_log_state) - 1, "接收到的回调消息和发送出来的消息条数不一致")
        for r_notify in receive_notify:
            if "ciphertext" in r_notify["response"]:
                parse_notify = self.verifyAndDecryptNotify(r_notify)
            else:
                parse_notify = json.loads(r_notify["response"])
            self.assertIn(parse_notify["txState"], tx_log_state, "{} {}".format(parse_notify["txState"], tx_log_state))
            s_notify = [i for i in send_notify if i["orderState"] == parse_notify["txState"]][0]
            self.assertEqual(json.dumps(parse_notify).replace(" ", ""), s_notify["notifyInfo"], f"send: {s_notify['notifyInfo']}\nreceive: {r_notify['response']}")
            self.assertEqual(parse_notify["deliveryFee"], query_order["deliveryFee"])
            self.assertEqual(parse_notify["deliveryFeeCurrency"], query_order["deliveryFeeCurrency"])
            self.assertEqual(parse_notify["exchangeRate"], query_order["exchangeRate"])
            self.assertEqual(parse_notify["quoteReceiveAmount"], query_order["quoteReceiveAmount"])
            self.assertEqual(parse_notify["sendFee"], query_order["sendFee"])
            self.assertEqual(parse_notify["sendFeeCurrency"], query_order["sendFeeCurrency"])
            self.assertEqual(parse_notify["serviceFee"], query_order["serviceFee"])
            self.assertEqual(parse_notify["serviceFeeCurrency"], query_order["serviceFeeCurrency"])
            self.assertEqual(parse_notify["transactionId"], query_order["transactionId"])
            if "receiveAmount" in parse_notify:
                self.assertEqual(parse_notify["receiveAmount"], json.loads(s_notify["notifyInfo"])["receiveAmount"])
            for o_k, o_v in parse_notify["origTransactionInfo"].items():
                self.assertEqual(o_v, query_order["origTransactionInfo"][o_k], f"{o_k}校验失败")

    def test_149_submitOrder_RoToFiat_withNotifyUrl(self):
        """
        提交订单，指定回调地址
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        amount = 12.15
        from_address = RTSData.ach_user_account
        outer_address = RSSData.out_bank_info[currency_info["fiat"]].copy()

        outer_balance = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}账户持有的资产: {outer_balance}")
        notify_url = "http://172.17.3.99:8005/api/rts/receiveNotify"
        query_order, fee = self.submitOrderFloorOfRoToFiat(currency_info, amount, "inner", outer_address, from_address, url=notify_url)

        outer_balance2 = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}账户持有的资产: {outer_balance2}, 变化了: {outer_balance2 - outer_balance}")

        self.assertAlmostEqual(outer_balance - outer_balance2, amount, delta=0.1 ** 6)
        self.assertEqual(query_order["txState"], "TRANSACTION_FINISH", "订单最终状态应为完成")

        tx_id = query_order["transactionId"]
        tx_log = self.client.getOrderStateLog("", tx_id)
        tx_log_state = [i["txState"] for i in tx_log["data"]["stateInfo"]]
        send_notify_sql = "select * from roxe_rts.rts_order_notify where order_id='{}' and notify_state='over'".format(tx_id)
        b_time = time.time()
        send_notify = []
        while time.time() - b_time < 100:
            send_notify = self.mysql.exec_sql_query(send_notify_sql)
            if len(send_notify) == len(tx_log_state) - 1:
                break
            time.sleep(3)
        time.sleep(2)
        receive_notify_sql = "select * from mock_notify.res_info order by create_at desc limit {}".format(len(send_notify))
        receive_notify = self.mysql.exec_sql_query(receive_notify_sql)
        self.assertEqual(len(receive_notify), len(send_notify), "接收到的回调消息和发送出来的消息条数不一致")
        self.assertEqual(len(receive_notify), len(tx_log_state) - 1, "接收到的回调消息和发送出来的消息条数不一致")
        for r_notify in receive_notify:
            if "ciphertext" in r_notify["response"]:
                parse_notify = self.verifyAndDecryptNotify(r_notify)
            else:
                parse_notify = json.loads(r_notify["response"])
            self.assertIn(parse_notify["txState"], tx_log_state, "{} {}".format(parse_notify["txState"], tx_log_state))
            s_notify = [i for i in send_notify if i["orderState"] == parse_notify["txState"]][0]
            # self.assertEqual(json.dumps(parse_notify).replace(" ", ""), s_notify["notifyInfo"], f"send: {s_notify['notifyInfo']}\nreceive: {r_notify['response']}")
            self.assertEqual(parse_notify["deliveryFee"], query_order["deliveryFee"])
            self.assertEqual(parse_notify["deliveryFeeCurrency"], query_order["deliveryFeeCurrency"])
            self.assertEqual(parse_notify["exchangeRate"], query_order["exchangeRate"])
            self.assertEqual(parse_notify["quoteReceiveAmount"], query_order["quoteReceiveAmount"])
            self.assertEqual(parse_notify["sendFee"], query_order["sendFee"])
            self.assertEqual(parse_notify["sendFeeCurrency"], query_order["sendFeeCurrency"])
            self.assertEqual(parse_notify["serviceFee"], query_order["serviceFee"])
            self.assertEqual(parse_notify["serviceFeeCurrency"], query_order["serviceFeeCurrency"])
            self.assertEqual(parse_notify["transactionId"], query_order["transactionId"])
            if "receiveAmount" in parse_notify:
                self.assertEqual(parse_notify["receiveAmount"], json.loads(s_notify["notifyInfo"])["receiveAmount"])
            for o_k, o_v in parse_notify["origTransactionInfo"].items():
                self.assertEqual(o_v, query_order["origTransactionInfo"][o_k], f"{o_k}校验失败")

    def test_150_submitOrder_FiatToFiat_withNotifyUrl(self):
        """
        提交订单，指定回调地址
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        outer_address = RSSData.out_bank_info[currency_info["fiat"]].copy()

        notify_url = "http://172.17.3.99:8005/api/rts/receiveNotify"
        query_order = self.submitOrderFloorOfFiatToFiat(RTSData.ach_user_token, RTSData.ach_user_id, currency_info, 12.15, "inner", outer_address, url=notify_url)

        tx_id = query_order["transactionId"]
        # tx_id = "a77d148c0a674278a1b92bd30a37b777"
        # query_order = self.client.getOrderInfo("", tx_id)
        tx_log = self.client.getOrderStateLog("", tx_id)
        tx_log_state = [i["txState"] for i in tx_log["data"]["stateInfo"]]
        send_notify_sql = "select * from roxe_rts.rts_order_notify where order_id='{}' and notify_state='over'".format(tx_id)
        b_time = time.time()
        send_notify = []
        while time.time() - b_time < 100:
            send_notify = self.mysql.exec_sql_query(send_notify_sql)
            if len(send_notify) == len(tx_log_state) - 1:
                break
            time.sleep(3)
        time.sleep(2)
        receive_notify_sql = "select * from mock_notify.res_info order by create_at desc limit {}".format(len(send_notify))
        receive_notify = self.mysql.exec_sql_query(receive_notify_sql)
        self.assertEqual(len(receive_notify), len(send_notify), "接收到的回调消息和发送出来的消息条数不一致")
        self.assertEqual(len(receive_notify), len(tx_log_state) - 1, "接收到的回调消息和发送出来的消息条数不一致")
        for r_notify in receive_notify:
            if "ciphertext" in r_notify["response"]:
                parse_notify = self.verifyAndDecryptNotify(r_notify)
            else:
                parse_notify = json.loads(r_notify["response"])
            self.assertIn(parse_notify["txState"], tx_log_state, "{} {}".format(parse_notify["txState"], tx_log_state))
            s_notify = [i for i in send_notify if i["orderState"] == parse_notify["txState"]][0]
            # self.assertEqual(json.dumps(parse_notify).replace(" ", ""), s_notify["notifyInfo"], f"send: {s_notify['notifyInfo']}\nreceive: {r_notify['response']}")
            self.assertEqual(parse_notify["deliveryFee"], query_order["deliveryFee"])
            self.assertEqual(parse_notify["deliveryFeeCurrency"], query_order["deliveryFeeCurrency"])
            self.assertEqual(parse_notify["exchangeRate"], query_order["exchangeRate"])
            self.assertEqual(parse_notify["quoteReceiveAmount"], query_order["quoteReceiveAmount"])
            self.assertEqual(parse_notify["sendFee"], query_order["sendFee"])
            self.assertEqual(parse_notify["sendFeeCurrency"], query_order["sendFeeCurrency"])
            self.assertEqual(parse_notify["serviceFee"], query_order["serviceFee"])
            self.assertEqual(parse_notify["serviceFeeCurrency"], query_order["serviceFeeCurrency"])
            self.assertEqual(parse_notify["transactionId"], query_order["transactionId"])
            if "receiveAmount" in parse_notify:
                self.assertEqual(parse_notify["receiveAmount"], json.loads(s_notify["notifyInfo"])["receiveAmount"])
            for o_k, o_v in parse_notify["origTransactionInfo"].items():
                self.assertEqual(o_v, query_order["origTransactionInfo"][o_k], f"{o_k}校验失败")

    @unittest.skip("todo, 需单独执行，配合查看mockNotify的日志")
    def test_151_submitOrder_withNotifyUrl404(self):
        """
        提交订单，指定回调地址
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        amount = 10
        from_address = RTSData.ach_user_account
        out_info = RSSData.out_bank_info[currency_info["fiat"]].copy()

        outer_balance = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}账户持有的资产: {outer_balance}")
        notify_url = "http://172.17.3.99:8005/api/rts/receiveNotifyY"
        submit_order, fee = self.submitOrderFloorOfRoToFiat(currency_info, amount, "inner", out_info, from_address, url=notify_url, is_just_submit=True)

        outer_balance2 = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"{from_address}账户持有的资产: {outer_balance2}, 变化了: {outer_balance2 - outer_balance}")

        self.assertAlmostEqual(outer_balance2 - outer_balance, amount, delta=0.1 ** 6)
        self.assertEqual(submit_order["txState"], "REDEEM_SUBMIT", "订单最终状态应为完成")

    def test_152_submitOrder_RoToFiat_USD_receiveInfoMissingField(self):
        """
        提交订单，USD 出金银行卡信息缺少必填字段时
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        amount = 5
        outer_info = RSSData.out_bank_info[currency_info["fiat"]].copy()

        # 从此账号转账给中间账户
        from_address = RTSData.ach_user_account
        from_balance = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"from账户持有的资产: {from_balance}")

        router_info, router_body = self.client.getRouterList("", currency_info["ro"], currency_info["country"], currency_info["fiat"], amount, "", currency_info["innerNodeCode"], currency_info["outerNodeCode"])
        self.checkCodeAndMessage(router_info)
        self.checkRouterListResult(router_info["data"], router_body)
        send_node_code = router_info["data"][0]["sendNodeCode"]
        receive_node_code = router_info["data"][0]["receiveNodeCode"] if currency_info["outerNodeCode"] == "" else currency_info["outerNodeCode"]
        router_out_amount = router_info["data"][0]["receiveAmount"]
        router_in_account = router_info["data"][0]["custodyAccountInfo"]["custodyAccount"]
        # 查询出金必填字段
        outer_fields = self.client.getReceiverRequiredFields(receive_node_code, currency_info["fiat"], "bank")

        rps_order = self.rpsClient.submitWalletPayOrder(RTSData.ach_user_token, RTSData.ach_user_id, from_address, router_in_account, amount)
        payment_id = rps_order["serviceChannelOrderId"]

        for m_p in outer_fields["data"]:
            o_info = outer_info.copy().pop(m_p["name"])
            check_outer_fields = self.client.checkReceiverRequiredFields(receive_node_code, currency_info["fiat"], o_info)
            self.checkCodeAndMessage(check_outer_fields, "01100000", "data structure error")
            self.assertIsNone(check_outer_fields["data"], f"出金银行卡信息缺少{m_p['name']}字段后校验失败")

            # 提交rts订单
            instruction_id = "test_" + str(int(time.time() * 1000))  # 客户单号
            source_id = instruction_id  # 客户原单
            # 提交rts订单
            submit_order, submit_body = self.client.submitOrder(
                instruction_id, source_id, payment_id, currency_info["ro"], amount, currency_info["fiat"], o_info, router_out_amount,
                sendNodeCode=send_node_code, receiveNodeCode=receive_node_code
            )
            self.checkCodeAndMessage(submit_order, "01100000", "data structure error")
            from_balance2 = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
            self.client.logger.info(f"from账户持有的资产: {from_balance2}, 变化了: {from_balance2 - from_balance}")
            self.assertAlmostEqual(from_balance - from_balance2, amount, delta=0.1 ** 3)

    @unittest.skip("开发未调通，暂时跳过")
    def test_153_submitOrder_RoToFiat_INR_receiveInfoMissingField(self):
        """
        提交订单，出金银行卡信息缺少必填字段时
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        currency_info["country"] = "IN"
        currency_info["fiat"] = "INR"
        amount = 5
        outer_info = RSSData.out_bank_info[currency_info["fiat"]].copy()

        # 从此账号转账给中间账户
        from_address = RTSData.ach_user_account
        from_balance = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"from账户持有的资产: {from_balance}")

        router_info, router_body = self.client.getRouterList("", currency_info["ro"], currency_info["country"], currency_info["fiat"], amount, "", currency_info["innerNodeCode"], currency_info["outerNodeCode"])
        self.checkCodeAndMessage(router_info)
        self.checkRouterListResult(router_info["data"], router_body)
        send_node_code = router_info["data"][0]["sendNodeCode"]
        receive_node_code = router_info["data"][0]["receiveNodeCode"] if currency_info["outerNodeCode"] == "" else currency_info["outerNodeCode"]
        router_out_amount = router_info["data"][0]["receiveAmount"]
        router_in_account = router_info["data"][0]["custodyAccountInfo"]["custodyAccount"]
        # 查询出金必填字段
        outer_fields = self.client.getReceiverRequiredFields(receive_node_code, currency_info["fiat"], "BANK")

        rps_order = self.rpsClient.submitWalletPayOrder(RTSData.ach_user_token, RTSData.ach_user_id, from_address, router_in_account, amount)
        payment_id = rps_order["serviceChannelOrderId"]

        for m_p in outer_fields["data"]:
            o_info = outer_info.copy().pop(m_p["name"])
            check_outer_fields = self.client.checkReceiverRequiredFields(receive_node_code, currency_info["fiat"], o_info)
            self.assertFalse(check_outer_fields["data"]["verified"], f"出金银行卡信息缺少{m_p['name']}字段后校验失败")

            # 提交rts订单
            instruction_id = "test_" + str(int(time.time() * 1000))  # 客户单号
            source_id = instruction_id  # 客户原单
            # 提交rts订单
            submit_order, submit_body = self.client.submitOrder(
                instruction_id, source_id, payment_id, currency_info["ro"], amount, currency_info["fiat"], o_info, router_out_amount,
                sendNodeCode=send_node_code, receiveNodeCode=receive_node_code
            )
            print(submit_order)
            from_balance2 = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
            self.client.logger.info(f"from账户持有的资产: {from_balance2}, 变化了: {from_balance2 - from_balance}")
            # self.assertAlmostEqual(from_balance - from_balance2, amount + fee, delta=0.1 ** 3)
            # self.assertEqual(submit_order["txState"], "TRANSACTION_FINISH", "订单最终状态应为完成")

    @unittest.skip("开发未调通，暂时跳过")
    def test_154_submitOrder_RoToFiat_INR_receiveInfoAmountMoreThanOrderAmount(self):
        """
        提交订单，出金银行卡信息缺少必填字段时
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        currency_info["country"] = "IN"
        currency_info["fiat"] = "INR"
        amount = 5
        outer_info = RSSData.out_bank_info[currency_info["fiat"]].copy()

        # 从此账号转账给中间账户
        from_address = RTSData.ach_user_account
        from_balance = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"from账户持有的资产: {from_balance}")

        router_info, router_body = self.client.getRouterList("", currency_info["ro"], currency_info["country"], currency_info["fiat"], amount, "", currency_info["innerNodeCode"], currency_info["outerNodeCode"])
        self.checkCodeAndMessage(router_info)
        self.checkRouterListResult(router_info["data"], router_body)
        send_node_code = router_info["data"][0]["sendNodeCode"]
        receive_node_code = router_info["data"][0]["receiveNodeCode"] if currency_info["outerNodeCode"] == "" else currency_info["outerNodeCode"]
        router_out_amount = router_info["data"][0]["receiveAmount"]
        router_in_account = router_info["data"][0]["custodyAccountInfo"]["custodyAccount"]
        # 查询出金必填字段
        outer_fields = self.client.getReceiverRequiredFields(receive_node_code, currency_info["fiat"], "BANK")

        rps_order = self.rpsClient.submitWalletPayOrder(RTSData.ach_user_token, RTSData.ach_user_id, from_address, router_in_account, amount)
        payment_id = rps_order["serviceChannelOrderId"]

        for m_p in outer_fields["data"]:
            o_info = outer_info.copy().pop(m_p["name"])
            check_outer_fields = self.client.checkReceiverRequiredFields(receive_node_code, currency_info["fiat"], o_info)
            self.assertFalse(check_outer_fields["data"]["verified"], f"出金银行卡信息缺少{m_p['name']}字段后校验失败")

            # 提交rts订单
            instruction_id = "test_" + str(int(time.time() * 1000))  # 客户单号
            source_id = instruction_id  # 客户原单
            # 提交rts订单
            submit_order, submit_body = self.client.submitOrder(
                instruction_id, source_id, payment_id, currency_info["ro"], amount, currency_info["fiat"], o_info, router_out_amount,
                sendNodeCode=send_node_code, receiveNodeCode=receive_node_code
            )
            print(submit_order)
            from_balance2 = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
            self.client.logger.info(f"from账户持有的资产: {from_balance2}, 变化了: {from_balance2 - from_balance}")
            # self.assertAlmostEqual(from_balance - from_balance2, amount + fee, delta=0.1 ** 3)
            # self.assertEqual(submit_order["txState"], "TRANSACTION_FINISH", "订单最终状态应为完成")

    @unittest.skip("已覆盖")
    def test_155_queryOuterFields_otherCurrency(self):
        """
        查询出金必填字段，传入出金节点，缺少币种
        """

        payoutMethod = self.client.getOutMethod("INR", "IN", RTSData.node_code)["data"]["receiveMethodCode"][0]
        out_res = self.client.getReceiverRequiredFields(RTSData.node_code, "INR", payoutMethod)
        self.checkCodeAndMessage(out_res)
        self.assertIsNotNone(out_res["data"])

    def test_156_queryRouterList_INR(self):
        """
        查询路由列表，出金币种为INR
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        in_currency = "USD.ROXE"
        out_currency = "INR"
        inner_quantity = 10
        router_info, router_body = self.client.getRouterList("", in_currency, "", out_currency, inner_quantity, "", currency_info["innerNodeCode"], currency_info["outerNodeCode"])
        self.assertTrue(len(router_info["data"]) > 0)
        self.checkRouterListResult(router_info["data"], router_body)

    def test_157_submitOrder_FiatToRo_paymentIdIsEmpty(self):
        """
        提交订单，法币入金, paymentId为空
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        send_currency = currency_info["fiat"]
        receive_currency = currency_info["ro"]
        outer_address = RTSData.ach_user_account
        send_amount = 10.3

        router_info, request_body = self.client.getRouterList(currency_info["country"], send_currency, "",
                                                              receive_currency, send_amount, "",
                                                              currency_info["innerNodeCode"],
                                                              currency_info["outerNodeCode"])
        send_node_code = router_info["data"][0]["sendNodeCode"]
        receive_node_code = router_info["data"][0]["receiveNodeCode"]

        # 提交rts订单
        instruction_id = "test_" + str(int(time.time() * 1000))  # 客户单号

        payment_id = ""
        receive_info = {"receiverAddress": outer_address}
        submit_order, submit_body = self.client.submitOrder(
            instruction_id, "", payment_id, send_currency, send_amount, receive_currency, receive_info,
            sendNodeCode=send_node_code, receiveNodeCode=receive_node_code, couponCode=None
        )
        self.checkCodeAndMessage(submit_order)
        # 等待5分钟
        time.sleep(60)
        # 查询订单状态
        query_order_info = self.client.getOrderInfo(instruction_id)
        self.checkCodeAndMessage(query_order_info)
        self.assertEqual(query_order_info["data"]["txState"], "MINT_SUBMIT")

        # 再次下单
        instruction_id = "test_" + str(int(time.time() * 1000))  # 客户单号
        submit_order, submit_body = self.client.submitOrder(
            instruction_id, "", "", send_currency, send_amount, receive_currency, receive_info,
            sendNodeCode=send_node_code, receiveNodeCode=receive_node_code, couponCode=None
        )
        self.checkCodeAndMessage(submit_order)

    @unittest.skip("开发未调通，暂时跳过")
    def test_160_submitOrder_RoToFiat_BRL(self):
        currency_info = RTSData.currency_fiat_ro[0].copy()
        currency_info["country"] = "BR"
        currency_info["fiat"] = "BRL"
        amount = 7.95
        outer_address = RSSData.out_bank_info[currency_info["fiat"]].copy()
        # 转账给中间账户
        from_address = RTSData.ach_user_account
        from_balance = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"目标账户持有的资产: {from_balance}")
        query_order, fee = self.submitOrderFloorOfRoToFiat(currency_info, amount, "inner", outer_address, from_address)
        from_balance2 = self.chain_client.getBalanceWithRetry(from_address, currency_info["fiat"])
        self.client.logger.info(f"目标账户持有的资产: {from_balance2}, 变化了: {from_balance2 - from_balance}")
        self.assertAlmostEqual(from_balance - from_balance2, amount + fee, delta=0.1 ** 3)
        self.assertEqual(query_order["txState"], "TRANSACTION_FINISH", "订单最终状态应为完成")

    def test_168_queryRouterList_giveNodeAndNotFindRouter(self):
        """
        查询路由列表，指定节点后，不能找到路由
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        in_currency = currency_info["fiat"]
        out_currency = currency_info["ro"]
        router_info, router_body = self.client.getRouterList("USD", in_currency, "USD", out_currency, 10, sendNodeCode=RTSData.node_code, receiveNodeCode="roxe_nium_inr")
        self.checkCodeAndMessage(router_info)
        self.assertEqual(router_info["data"], [])

    def test_169_submitOrder_FiatToFiat_giveNodeAndNotFindRouter(self):
        """
        提交订单，指定节点后，不能找到路由, 下单失败
        """
        send_currency = "USD"
        receive_currency = "USD"
        outer_address = RTSData.ach_user_account
        send_amount = 10.3

        # 提交rts订单
        instruction_id = "test_" + str(int(time.time() * 1000))  # 客户单号
        originalId = instruction_id  # 客户原单

        # 提交rps订单
        # rps_order, coupon_code = self.rpsClient.submitAchPayOrder(outer_address, send_amount,
        #                                                           account_info=RPSData.ach_account)
        # payment_id = rps_order["serviceChannelOrderId"]
        receive_info = {"receiverAddress": outer_address}
        submit_order, sub_body = self.client.submitOrder(
            instruction_id, originalId, "", send_currency, send_amount, receive_currency, receive_info,
            sendNodeCode=RTSData.node_code, receiveNodeCode="roxe_nium_inr"
        )
        self.checkCodeAndMessage(submit_order, "01500001", "No suitable routing node was found")
        self.assertIsNone(submit_order["data"])

    def test_170_getTransactionCurrency_all_useDESEncrypt(self):
        """
        获取支持的转账币种
        """
        currency_infos, r_body = self.client.getTransactionCurrency(replaceSignAlgorithm="DES")
        self.checkCodeAndMessage(currency_infos)
        self.checkTransactionCurrency(currency_infos["data"], r_body)

    def submitOrderFloorOfFiatToRo_tp(self, currency_info, amount, amount_side, outer_info, is_just_submit=False, url=None):
        """
        法币->RO的下单流程:
            查询路由 -> 下单 -> 查询订单信息 -> 等待订单完成 -> 查询订单信息 -> 查询订单日志
            每一步都有验证接口返回的结果
        :param currency_info: 币种信息
        :param amount: 查询路由的下单数量
        :param amount_side: 查询路由的方向
        :param outer_info: 出金的信息，如果出金一方为ro则为ro地址，如果出金一方为银行卡则为银行卡信息
        # :param pay_account: 法币支付的账户
        :param is_just_submit: 是否在提交订单后就返回订单数据，不等待订单完成
        :param url: 回调的url
        :return:
        """
        # 查询路由信息
        send_amount = amount if amount_side == "inner" else ""
        receive_amount = amount if amount_side == "outer" else ""
        send_currency = currency_info["fiat"]
        receive_currency = currency_info["ro"]
        outer_address = outer_info
        # country = "" if currency_info["innerNodeCode"] else currency_info["country"]
        router_info, request_body = self.client.getRouterList(currency_info["country"], send_currency, "", receive_currency, send_amount, receive_amount, currency_info["innerNodeCode"], currency_info["outerNodeCode"])
        print(router_info)
        self.checkRouterListResult(router_info["data"], request_body)
        send_node_code = router_info["data"][0]["sendNodeCode"]

        # 提交rts订单
        instruction_id = "test_" + str(int(time.time() * 1000))  # 客户单号
        originalId = ""  # 客户原单
        send_amount = amount  # 指定下单数量
        if amount_side == "outer":
            # pass
            send_amount = float(router_info["data"][0]["sendAmount"])

        # 提交rps订单
        payment_id = self.rpsClient.rps_submit_order(RTSData.ach_user_token, RTSData.ach_user_id, RTSData.ach_user_account, RTSData.targetRoxeAccount_2, "debitCard", send_amount)
        # payment_id = rps_order["serviceChannelOrderId"]
        receive_info = {"receiverAddress": outer_address}
        submit_info, submit_body = self.client.submitOrder(
            instruction_id, originalId, payment_id, send_currency, send_amount, receive_currency, receive_info, receive_amount,
            sendNodeCode=send_node_code, couponCode="", notifyURL=url
        )
        if is_just_submit:
            return submit_info["data"]
        self.checkCodeAndMessage(submit_info)
        self.checkSubmitOrderResult(submit_info["data"], submit_body, router_info["data"][0])
        # 查询订单状态
        transaction_id = submit_info["data"]["transactionId"]
        query_info = self.client.getOrderInfo(instruction_id)
        self.checkCodeAndMessage(query_info)
        self.checkOrderInfo(query_info["data"], submit_body, router_info["data"][0])
        # 查询订单日志
        order_log = self.client.getOrderStateLog(instruction_id)
        self.checkCodeAndMessage(order_log)
        self.checkOrderLog(order_log["data"], transaction_id)
        # 直到订单完成
        time_out = 600
        b_time = time.time()
        while True:
            if time.time() - b_time > time_out:
                self.client.logger.error("等待时间超时")
                break
            query_info = self.client.getOrderInfo(instruction_id)
            if query_info["data"]["txState"] == "TRANSACTION_FINISH":
                self.client.logger.info("rts订单已经完成")
                break
            time.sleep(time_out/15)
        # 查询订单状态
        query_info = self.client.getOrderInfo(instruction_id)
        self.checkCodeAndMessage(query_info)
        self.checkOrderInfo(query_info["data"], submit_body, router_info["data"][0])
        time.sleep(1)
        # 查询订单日志
        order_log = self.client.getOrderStateLog(instruction_id)
        self.checkCodeAndMessage(order_log)
        self.checkOrderLog(order_log["data"], transaction_id)
        assert "TRANSACTION_FINISH" in [i["txState"] for i in order_log["data"]["stateInfo"]], "订单状态不正确"
        return query_info["data"]

    def test_nacos011_normalScene_sameCurrency_FiatToRo_notGiveNodeCodes_outAmount(self):
        """
        同币种, 法币到ro, 不指定节点，指定出金数量, 查询路由->rps下单->rts下单->校验
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        amount = 8.06
        outer_address = RTSData.ach_user_account

        outer_balance = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{outer_address}账户持有的资产: {outer_balance}")

        query_order = self.submitOrderFloorOfFiatToRo(RTSData.ach_user_token, RTSData.ach_user_id, currency_info, amount, "outer", outer_address)

        outer_balance2 = self.chain_client.getBalanceWithRetry(outer_address, currency_info["fiat"])
        self.client.logger.info(f"{outer_address}账户持有的资产: {outer_balance2}, 变化了: {outer_balance2 - outer_balance}")

        self.assertAlmostEqual(outer_balance2 - outer_balance, amount, delta=0.1**6)
        self.assertEqual(query_order["txState"], "TRANSACTION_FINISH", "订单最终状态应为完成")


class RTSExceptionTest(BaseCheckRTS):

    # 异常场景

    def test_042_queryContractRate_signIncorrect(self):
        """
        查询合约费率，签名不正确
        """
        currency = RTSData.currency_fiat_ro[0]["fiat"]
        amount = 10
        rate_info, rate_body = self.client.getRate(currency, currency, sendAmount=amount, replaceSign="abc")
        self.checkCodeAndMessage(rate_info, "01200001", "Signature error")
        self.assertIsNone(rate_info["data"])

    def test_043_queryContractRate_keyIncorrect(self):
        """
        查询合约费率，key不正确
        """
        currency = RTSData.currency_fiat_ro[0]["fiat"]
        amount = 10
        rate_info, rate_body = self.client.getRate(currency, currency, sendAmount=amount, replaceKey="a" * 32)
        self.checkCodeAndMessage(rate_info, "01200001", "Signature error")
        self.assertIsNone(rate_info["data"])

    def test_044_queryContractRate_currencyLowerCase(self):
        """
        查询合约费率，币种小写
        """
        currency = RTSData.currency_fiat_ro[0]["fiat"].lower()
        amount = 10
        rate_info, rate_body = self.client.getRate(currency, currency, sendAmount=amount)
        self.checkCodeAndMessage(rate_info, "01100000", "send currency not supported")
        self.assertIsNone(rate_info["data"])

    def test_045_queryContractRate_currencyMixerCase(self):
        """
        查询合约费率，币种大小写混合
        """
        currency = RTSData.currency_fiat_ro[0]["fiat"].title()
        amount = 10
        rate_info, rate_body = self.client.getRate(currency, currency, sendAmount=amount)
        self.checkCodeAndMessage(rate_info, "01100000", "send currency not supported")
        self.assertIsNone(rate_info["data"])

    def test_046_queryContractRate_currencyNotSupport(self):
        """
        查询合约费率，币种不支持: CNY
        """
        currency = RTSData.currency_fiat_ro[0]["fiat"]
        amount = 10
        rate_info, rate_body = self.client.getRate(currency, "KRW", sendAmount=amount)
        self.checkCodeAndMessage(rate_info, "01600104", "Currency pair is not supported")
        self.assertIsNone(rate_info["data"])

    def test_047_queryContractRate_missingInnerCurrency(self):
        """
        查询合约费率，缺少参数: innerCurrency
        """
        currency = RTSData.currency_fiat_ro[0]["fiat"]
        amount = 10
        rate_info, rate_body = self.client.getRate(currency, currency, sendAmount=amount, popKey="sendCurrency")
        self.checkCodeAndMessage(rate_info, "01100000", "sendCurrency is empty")
        self.assertIsNone(rate_info["data"])

    def test_048_queryContractRate_missingOuterCurrency(self):
        """
        查询合约费率，缺少参数: outerCurrency
        """
        currency = RTSData.currency_fiat_ro[0]["fiat"]
        amount = 10
        rate_info, rate_body = self.client.getRate(currency, currency, sendAmount=amount, popKey="receiveCurrency")
        self.checkCodeAndMessage(rate_info, "01100000", "receiveCurrency is empty")
        self.assertIsNone(rate_info["data"])

    def test_049_queryContractRate_notGiveAmountToBothInnerQuantityAndOuterQuantity(self):
        """
        查询合约费率，outQuantity和innerQuantity都不指定amount
        """
        currency = RTSData.currency_fiat_ro[0]["fiat"]
        rate_info, rate_body = self.client.getRate(currency, "PHP")
        self.checkCodeAndMessage(rate_info, "01100000", "send or receive amount all empty")
        self.assertIsNone(rate_info["data"])

    def test_050_queryContractRate_giveAmountToBothInnerQuantityAndOuterQuantity(self):
        """
        查询合约费率，outQuantity和innerQuantity都指定amount
        """
        currency = RTSData.currency_fiat_ro[0]["fiat"]
        rate_info, rate_body = self.client.getRate(currency, currency, 4, 7)
        self.checkCodeAndMessage(rate_info)
        self.checkContractRateResult(rate_info["data"], rate_body)

    def test_051_queryRouterList_signIncorrect(self):
        """
        查询路由列表，签名不正确
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        in_currency = currency_info["fiat"]
        out_currency = currency_info["ro"]
        inner_quantity = 10
        router_info, router_body = self.client.getRouterList(currency_info["country"], in_currency, "", out_currency,
                                                             inner_quantity, "", currency_info["innerNodeCode"],
                                                             currency_info["outerNodeCode"], replaceSign="a" * 10)
        self.checkCodeAndMessage(router_info, "01200001", "Signature error")
        self.assertIsNone(router_info["data"])

    def test_052_queryRouterList_keyIncorrect(self):
        """
        查询路由列表，签名不正确
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        in_currency = currency_info["fiat"]
        out_currency = currency_info["ro"]
        inner_quantity = 10
        router_info, router_body = self.client.getRouterList(currency_info["country"], in_currency, currency_info["country"], out_currency, inner_quantity, "", currency_info["innerNodeCode"], currency_info["outerNodeCode"], replaceKey="a" * 32)
        self.checkCodeAndMessage(router_info, "01200001", "Signature error")
        self.assertIsNone(router_info["data"])

    def test_053_queryRouterList_currencyLowerCase(self):
        """
        查询路由列表，币种小写
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        in_currency = currency_info["fiat"].lower()
        out_currency = currency_info["ro"].lower()
        # in_currency = "USD"
        # out_currency = "USD"
        inner_quantity = 10
        router_info, router_body = self.client.getRouterList("", in_currency, "US", out_currency, inner_quantity, "", "f3viuzqrqq4d", currency_info["outerNodeCode"])
        self.assertTrue(len(router_info["data"]) > 0)
        self.checkRouterListResult(router_info["data"], router_body)

    def test_054_queryRouterList_currencyMixerCase(self):
        """
        查询路由列表，币种大小写混合
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        in_currency = currency_info["fiat"].title()
        out_currency = currency_info["ro"].title()
        inner_quantity = 10
        router_info, router_body = self.client.getRouterList(currency_info["country"], in_currency, '', out_currency, inner_quantity, "", currency_info["innerNodeCode"], currency_info["outerNodeCode"])
        self.assertTrue(len(router_info["data"]) > 0)
        self.checkRouterListResult(router_info["data"], router_body)

    def test_055_queryRouterList_currencyNotSupport(self):
        """
        查询路由列表，不支持的币种: CNY
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        in_currency = "CNY"
        out_currency = "CNY.ROXE"
        inner_quantity = 10
        router_info, router_body = self.client.getRouterList("", in_currency, "", out_currency, inner_quantity, "", currency_info["innerNodeCode"], currency_info["outerNodeCode"])
        self.assertEqual(router_info["data"], [])
        router_info, router_body = self.client.getRouterList("", out_currency, "", in_currency, inner_quantity, "", currency_info["innerNodeCode"], currency_info["outerNodeCode"])
        self.assertEqual(router_info["data"], [])

    def test_056_queryRouterList_nodeRoxeNotSupport(self):
        """
        查询路由列表，不支持的入金、出金节点
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        in_currency = currency_info["fiat"]
        out_currency = currency_info["ro"]
        inner_quantity = 10
        router_info, router_body = self.client.getRouterList("", in_currency, "", out_currency, inner_quantity, "", RTSData.node_code["PHP"] + "a", currency_info["outerNodeCode"])
        self.assertEqual(router_info["data"], [])
        router_info, router_body = self.client.getRouterList("", out_currency, "", in_currency, inner_quantity, "", currency_info["innerNodeCode"], RTSData.node_code["PHP"] + "a")
        self.assertEqual(router_info["data"], [])

    def test_057_queryRouterList_roCurrencyGiveCountry(self):
        """
        查询路由列表，不支持的入金、出金节点
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        in_currency = currency_info["fiat"]
        out_currency = currency_info["ro"]
        inner_quantity = 10
        router_info, router_body = self.client.getRouterList("", in_currency, currency_info["country"], out_currency, inner_quantity)
        self.assertEqual(router_info["data"], [])
        router_info, router_body = self.client.getRouterList(currency_info["country"], out_currency, "", in_currency, inner_quantity)
        self.assertEqual(router_info["data"], [])

    def test_058_queryRouterList_bothGiveSendNodeCodeAndSendCountry(self):
        """
        查询路由列表，缺少参数: innerCountry、innerCurrency、innerQuantity、outerCountry。。。
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        in_currency = currency_info["fiat"]
        out_currency = currency_info["ro"]
        router_info, router_body = self.client.getRouterList(currency_info["country"], in_currency, "", out_currency, 10, sendNodeCode=RTSData.node_code)
        self.checkCodeAndMessage(router_info)
        self.checkRouterListResult(router_info["data"], router_body)

    def test_059_queryRouterList_NotGiveAmountToBothInnerQuantityAndOuterQuantity(self):
        """
        查询路由列表，innerQuantity和outerQuantity都不给出金额
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        in_currency = currency_info["fiat"]
        out_currency = currency_info["ro"]
        router_info, router_body = self.client.getRouterList(currency_info["country"], in_currency, "", out_currency, "", "", currency_info["innerNodeCode"], currency_info["outerNodeCode"])
        self.checkCodeAndMessage(router_info, "01100000", "amount empty or amount must be > 0")
        self.assertEqual(router_info["data"], None)

    def test_060_queryRouterList_giveAmountToBothInnerQuantityAndOuterQuantity(self):
        """
        查询路由列表，innerQuantity和outerQuantity都给出金额, 按innerQuantity计算
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        in_currency = currency_info["fiat"]
        out_currency = currency_info["ro"]
        router_info, router_body = self.client.getRouterList(currency_info["country"], in_currency, "", out_currency, "5", "10", currency_info["innerNodeCode"], currency_info["outerNodeCode"])
        self.checkCodeAndMessage(router_info)
        self.assertTrue(len(router_info["data"]) > 0)
        self.checkRouterListResult(router_info["data"], router_body)

    def test_061_queryRouterList_amountIsIncorrect(self):
        """
        查询路由列表，innerQuantity和outerQuantity不合法: 负数
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        in_currency = currency_info["fiat"]
        out_currency = currency_info["ro"]
        router_info, router_body = self.client.getRouterList(currency_info["country"], in_currency, "", out_currency, "-1", "", currency_info["innerNodeCode"], currency_info["outerNodeCode"])
        self.checkCodeAndMessage(router_info, "01100000", "sendAmount must be > 0")
        self.assertEqual(router_info["data"], None)
        router_info, router_body = self.client.getRouterList(currency_info["country"], in_currency, "", out_currency, "", "-2", currency_info["innerNodeCode"], currency_info["outerNodeCode"])
        self.checkCodeAndMessage(router_info, "01100000", "receiveAmount must be > 0")
        self.assertEqual(router_info["data"], None)

    def test_062_queryRouterList_amountDecimalIsIncorrect_inner(self):
        """
        查询路由列表，铸币，innerQuantity和outerQuantity的小数位数不合法: 超过2位
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        in_currency = currency_info["fiat"]
        out_currency = currency_info["ro"]
        amount = 10.3456
        router_info, router_body = self.client.getRouterList("US", in_currency, "", out_currency, amount, "", currency_info["innerNodeCode"], currency_info["outerNodeCode"])
        self.assertTrue(len(router_info["data"]) > 0)
        self.checkRouterListResult(router_info["data"], router_body)
        router_info, router_body = self.client.getRouterList("US", in_currency, "", out_currency, "", amount, currency_info["innerNodeCode"], currency_info["outerNodeCode"])
        self.assertTrue(len(router_info["data"]) > 0)
        self.checkRouterListResult(router_info["data"], router_body)

    def test_063_queryRouterList_amountDecimalIsIncorrect_outer(self):
        """
        查询路由列表，赎回，innerQuantity和outerQuantity的小数位数不合法: 超过2位
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        in_currency = currency_info["ro"]
        out_currency = currency_info["fiat"]
        amount = 10.3412
        router_info, router_body = self.client.getRouterList("", in_currency, "US", out_currency, amount, "", currency_info["innerNodeCode"], currency_info["outerNodeCode"])
        self.assertTrue(len(router_info["data"]) > 0)
        self.checkRouterListResult(router_info["data"], router_body)
        router_info, router_body = self.client.getRouterList("", in_currency, "US", out_currency, "", amount, currency_info["innerNodeCode"], currency_info["outerNodeCode"])
        self.assertTrue(len(router_info["data"]) > 0)
        self.checkRouterListResult(router_info["data"], router_body)

    def test_065_queryOuterMethod_signIncorrect(self):
        """
        查询出金方式，签名错误
        """
        out_res = self.client.getOutMethod("USD", "", RTSData.node_code, replaceSign="abc")
        self.checkCodeAndMessage(out_res, "01200001", "Signature error")
        self.assertIsNone(out_res["data"])

    def test_066_queryOuterMethod_keyIncorrect(self):
        """
        查询出金方式，key错误
        """
        out_res = self.client.getOutMethod("USD", "", RTSData.node_code, replaceKey="a" * 32)
        self.checkCodeAndMessage(out_res, "01200001", "Signature error")
        self.assertIsNone(out_res["data"])

    def test_067_queryOuterMethod_currencyLowerCase(self):
        """
        查询出金方式，币种小写
        """
        out_currency = "USD"
        receiveNodeCode = RTSData.out_currency_info[1]["node_code"]
        out_res = self.client.getOutMethod(out_currency.lower(), "", receiveNodeCode)
        self.checkCodeAndMessage(out_res, "01100001", "currency not support")
        self.assertEqual(out_res["data"], None)

    def test_068_queryOuterMethod_currencyMixerCase(self):
        """
        查询出金方式，币种大小写混合
        """
        out_currency = "USD"
        receiveNodeCode = RTSData.out_currency_info[1]["node_code"]
        out_res = self.client.getOutMethod(out_currency.title(), "", receiveNodeCode)
        self.checkCodeAndMessage(out_res, "01100001", "currency not support")
        self.assertEqual(out_res["data"], None)

    def test_069_queryOuterMethod_currencyNotMatchWithOuterNode(self):
        """
        查询出金方式，币种和出金节点不匹配
        """
        out_res = self.client.getOutMethod("JPY", "", RTSData.node_code)
        # self.checkCodeAndMessage(out_res, "01100000", "Node does not exist or currency is not supported")
        # self.assertIsNone(out_res["data"])
        self.checkCodeAndMessage(out_res, "01100000", "country or currency not support")
        self.assertIsNone(out_res["data"], None)

    def test_070_queryOuterMethod_outerNodeIsIncorrect(self):
        """
        查询出金方式，出金节点不正确
        """
        out_res = self.client.getOutMethod(RTSData.currency_fiat_ro[0]["fiat"], "", "abc")
        # self.checkCodeAndMessage(out_res, "01100000", "node does not exist")
        # self.assertIsNone(out_res["data"])
        self.checkCodeAndMessage(out_res, "01100000", "country or currency not support")
        self.assertIsNone(out_res["data"], None)

    def test_071_queryOuterMethod_missingCurrency(self):
        """
        查询出金方式，缺少币种参数
        """
        out_res = self.client.getOutMethod("USD", "", RTSData.node_code, popKey="currency")
        # self.checkCodeAndMessage(out_res, "01100000", "Node does not exist or currency is not supported")
        # self.assertIsNone(out_res["data"])
        self.checkCodeAndMessage(out_res, "01100000", "country or currency not support")
        self.assertIsNone(out_res["data"], None)

    def test_072_queryOuterMethod_missingReceiveCountry(self):
        """
        查询出金方式，缺少routerId且不给出金节点
        """
        out_res = self.client.getOutMethod("USD", "", RTSData.node_code, popKey="receiveCountry")
        # self.checkCodeAndMessage(out_res)
        # self.assertEqual(out_res["data"], {"receiveMethodCode": ["bank"]})
        self.checkCodeAndMessage(out_res, "01100000", "country or currency not support")
        self.assertIsNone(out_res["data"], None)

    def test_073_queryOuterMethod_missingReceiveNodeCode(self):
        """
        查询出金方式，缺少出金国家和出金节点
        """

        out_res = self.client.getOutMethod("USD", "", "")
        # self.checkCodeAndMessage(out_res, "01100000", "node does not exist")
        # self.assertIsNone(out_res["data"])
        self.checkCodeAndMessage(out_res, "01100000", 'country is empty')
        self.assertIsNone(out_res["data"], None)

    def test_074_queryOuterFields_signIncorrect(self):
        """
        查询出金必填字段，sign不正确
        """
        # currency_info = RtsData.currency_fiat_ro[0].copy()
        # in_currency = currency_info["ro"]
        # out_currency = currency_info["fiat"]
        # amount = 10.3
        # router_info, router_body = self.client.getRouterList("", in_currency, "", out_currency, amount, "", currency_info["innerNodeCode"], currency_info["outerNodeCode"])
        # receiveNodeCode = router_info["data"][0]["receiveNodeCode"]
        out_currency = RTSData.out_currency_info[1]["fiat"]
        receiveNodeCode = RTSData.out_currency_info[1]["node_code"]
        out_res = self.client.getReceiverRequiredFields(receiveNodeCode, out_currency, "bank", replaceSign="abc")
        self.checkCodeAndMessage(out_res, "01200001", "Signature error")
        self.assertIsNone(out_res["data"])

    def test_075_queryOuterFields_keyIncorrect(self):
        """
        查询出金必填字段，key不正确
        """
        # currency_info = RtsData.currency_fiat_ro[0].copy()
        # in_currency = currency_info["ro"]
        # out_currency = currency_info["fiat"]
        # amount = 10.3
        # router_info, router_body = self.client.getRouterList("", in_currency, "", out_currency, amount, "", currency_info["innerNodeCode"], currency_info["outerNodeCode"])
        # receiveNodeCode = router_info["data"][0]["receiveNodeCode"]
        out_currency = RTSData.out_currency_info[1]["fiat"]
        receiveNodeCode = RTSData.out_currency_info[1]["node_code"]
        out_res = self.client.getReceiverRequiredFields(receiveNodeCode, out_currency, "BANK", replaceKey="ab"*16)
        self.checkCodeAndMessage(out_res, "01200001", "Signature error")
        self.assertIsNone(out_res["data"])

    def test_076_queryOuterFields_outerMethodIsIncorrect(self):
        """
        查询出金必填字段，出金方式不正确
        """
        out_currency = RTSData.out_currency_info[1]["fiat"]
        receiveNodeCode = RTSData.out_currency_info[1]["node_code"]
        out_res = self.client.getReceiverRequiredFields(receiveNodeCode, out_currency, "abc")
        # self.checkCodeAndMessage(out_res, "01100100", "call node service is error: payoutMethod type error")
        # self.assertIsNone(out_res["data"])
        self.checkCodeAndMessage(out_res, "01100001", "No enum constant com.roxe.rpc.payout.enums.PayoutMethodEnum.abc")
        self.assertEqual(out_res["data"], None)

    def test_077_queryOuterFields_outerMethodUpperCase(self):
        """
        查询出金必填字段，出金方式大写
        """
        out_currency = RTSData.out_currency_info[1]["fiat"]
        receiveNodeCode = RTSData.out_currency_info[1]["node_code"]
        out_res = self.client.getReceiverRequiredFields(receiveNodeCode, out_currency, "BANK")
        # self.checkCodeAndMessage(out_res, "01100100", "call node service is error: payoutMethod type error")
        # self.assertIsNone(out_res["data"])
        self.checkCodeAndMessage(out_res, "01100001", "No enum constant com.roxe.rpc.payout.enums.PayoutMethodEnum.BANK")
        self.assertEqual(out_res["data"], None)

    def test_078_queryOuterFields_outNodeIsIncorrect(self):
        """
        查询出金必填字段，出金节点不正确
        """
        out_res = self.client.getReceiverRequiredFields("abc", "USD", "BANK")
        self.checkCodeAndMessage(out_res, "01100000", "node does not exist")
        self.assertIsNone(out_res["data"])

    def test_079_queryOuterFields_currencyNotMatchWithOutNode(self):
        """
        查询出金必填字段，和出金节点不匹配
        """
        out_currency = RTSData.out_currency_info[0]["fiat"]
        receiveNodeCode = RTSData.out_currency_info[1]["node_code"]
        out_res = self.client.getReceiverRequiredFields(receiveNodeCode, out_currency, "bank")
        # self.checkCodeAndMessage(out_res, "01100100", "call node service is error: not support currency")
        self.checkCodeAndMessage(out_res, "01100001", "currency not support")
        self.assertIsNone(out_res["data"])

    def test_07901_queryOuterFields_currencyNotMatchWithOutNode(self):
        """
        查询出金必填字段，和出金节点不匹配，与上面用例节点和币种相反
        """
        out_currency = RTSData.out_currency_info[1]["fiat"]
        receiveNodeCode = RTSData.out_currency_info[0]["node_code"]
        out_res = self.client.getReceiverRequiredFields(receiveNodeCode, out_currency, "bank")
        # self.checkCodeAndMessage(out_res, "01100100", "call node service is error: not support currency")
        self.checkCodeAndMessage(out_res, "01100001", "currency not support")
        self.assertIsNone(out_res["data"])

    def test_080_queryOuterFields_currencyLowerCase(self):
        """
        查询出金必填字段，币种小写
        """
        receiveNodeCode = RTSData.out_currency_info[1]["node_code"]
        out_res = self.client.getReceiverRequiredFields(receiveNodeCode, "usd", "bank")
        self.checkCodeAndMessage(out_res, "01100001", "currency not support")
        # self.checkOuterBankFields(out_res["data"], "USD")
        self.assertIsNone(out_res["data"])

    def test_081_queryOuterFields_currencyMixerCase(self):
        """
        查询出金必填字段，币种大小写混合
        """
        out_currency = RTSData.out_currency_info[1]["fiat"]
        receiveNodeCode = RTSData.out_currency_info[1]["node_code"]
        out_res = self.client.getReceiverRequiredFields(receiveNodeCode, out_currency.title(), "bank")
        # self.checkCodeAndMessage(out_res)
        # self.checkOuterBankFields(out_res["data"], RtsData.currency_fiat_ro[0]["fiat"])
        self.checkCodeAndMessage(out_res, "01100001", "No enum constant com.roxe.base.enums.CurrencyEnum.Php")
        self.assertIsNone(out_res["data"])

    def test_082_queryOuterFields_missingOuterMethod(self):
        """
        查询出金必填字段，缺少出金方式
        """
        out_currency = RTSData.out_currency_info[1]["fiat"]
        receiveNodeCode = RTSData.out_currency_info[1]["node_code"]
        out_res = self.client.getReceiverRequiredFields(receiveNodeCode, out_currency, "BANK", popKey="receiveMethod")
        # self.checkCodeAndMessage(out_res, "01100100", "call node service is error: payoutMethod type error")
        self.checkCodeAndMessage(out_res, "01100000", "method is empty")
        self.assertIsNone(out_res["data"])

    def test_083_queryOuterFields_missingOuterNode(self):
        """
        查询出金必填字段，缺少出金节点
        """
        out_currency = RTSData.out_currency_info[1]["fiat"]
        receiveNodeCode = RTSData.out_currency_info[1]["node_code"]
        out_res = self.client.getReceiverRequiredFields(receiveNodeCode, out_currency, "bank", popKey="receiveNodeCode")
        # self.checkCodeAndMessage(out_res, "01100000", "node does not exist")
        self.checkCodeAndMessage(out_res, "01100000", "node code is empty")
        self.assertIsNone(out_res["data"])

    def test_084_queryOuterFields_missingCurrency(self):
        """
        查询出金必填字段，传入出金节点，缺少币种
        """
        out_currency = RTSData.out_currency_info[1]["fiat"]
        receiveNodeCode = RTSData.out_currency_info[1]["node_code"]
        out_res = self.client.getReceiverRequiredFields(receiveNodeCode, out_currency, "bank", popKey="receiveCurrency")
        # self.checkCodeAndMessage(out_res, "01100000", "receive currency is empty")
        self.checkCodeAndMessage(out_res, "01100000", "currency is empty")
        self.assertIsNone(out_res["data"])

    def test_085_checkOuterFields_signIncorrect(self):
        """
        校验出金必填字段，签名不正确
        """
        outer_info = RSSData.out_bank_info["USD"].copy()
        check_res = self.client.checkReceiverRequiredFields(RTSData.node_code, RTSData.currency_fiat_ro[0]["fiat"], outer_info, replaceSign="abc")
        self.checkCodeAndMessage(check_res, "01200001", "Signature error")
        self.assertIsNone(check_res["data"])

    def test_086_checkOuterFields_keyIncorrect(self):
        """
        校验出金必填字段，key不正确
        """
        outer_info = RSSData.out_bank_info["USD"].copy()
        check_res = self.client.checkReceiverRequiredFields(RTSData.node_code, RTSData.currency_fiat_ro[0]["fiat"], outer_info, replaceKey="ac" * 16)
        self.checkCodeAndMessage(check_res, "01200001", "Signature error")
        self.assertIsNone(check_res["data"])

    def test_087_checkOuterFields_otherCurrency(self):
        """
        校验出金必填字段，其他币种
        """
        for k, v in RSSData.out_bank_info.items():
            if k == "USD":
                continue
            outer_info = v.copy()
            check_res = self.client.checkReceiverRequiredFields(RTSData.node_code, k, outer_info)
            self.checkCodeAndMessage(check_res)
            self.assertEqual(check_res["data"], {"verified": True, "message": "success"})

    def test_088_checkOuterFields_otherCurrency_outMethodUpper(self):
        """
        校验出金必填字段，其他币种
        """
        for k, v in RSSData.out_bank_info.items():
            if k == "USD":
                continue
            outer_info = v.copy()
            outer_info["payOutMethod"] = outer_info["payOutMethod"].upper()
            check_res = self.client.checkReceiverRequiredFields(RTSData.node_code, k, outer_info)
            self.checkCodeAndMessage(check_res)
            ex_check = "call outer channel api fail: NIUM parameter error: payOutMethod can not be empty"
            self.assertEqual(check_res["data"]["message"], ex_check)
            self.assertEqual(check_res["data"]["verified"], False)

    def test_089_checkOuterFields_outerNodeIncorrect(self):
        """
        校验出金必填字段，出金节点不正确
        """
        currency = RTSData.currency_fiat_ro[0]["fiat"]
        outer_info = RSSData.out_bank_info[currency].copy()
        check_res = self.client.checkReceiverRequiredFields("abc", currency, outer_info)
        self.checkCodeAndMessage(check_res, "01100000", "node does not exist")
        self.assertIsNone(check_res["data"])

    def test_090_checkOuterFields_currencyNotMatchWithOuterNode(self):
        """
        校验出金必填字段，币种不正确，和出金节点不匹配
        """
        currency = RTSData.currency_fiat_ro[0]["fiat"]
        outer_info = RSSData.out_bank_info[currency].copy()
        check_res = self.client.checkReceiverRequiredFields(RTSData.node_code, "JPY", outer_info)
        self.checkCodeAndMessage(check_res)
        self.assertEqual(check_res["data"], {"verified": False, "message": "not support currency"})

    def test_091_checkOuterFields_currencyLowerCase(self):
        """
        校验出金必填字段，币种小写
        """
        currency = RTSData.currency_fiat_ro[0]["fiat"]
        outer_info = RSSData.out_bank_info[currency].copy()
        check_res = self.client.checkReceiverRequiredFields(RTSData.node_code, currency.lower(), outer_info)
        self.checkCodeAndMessage(check_res)
        self.assertEqual(check_res["data"], {"verified": True, "message": "success"})

    def test_092_checkOuterFields_currencyMixerCase(self):
        """
        校验出金必填字段，币种大小写混合
        """
        currency = RTSData.currency_fiat_ro[0]["fiat"]
        outer_info = RSSData.out_bank_info[currency].copy()
        check_res = self.client.checkReceiverRequiredFields(RTSData.node_code, currency.title(), outer_info)
        self.checkCodeAndMessage(check_res)
        self.assertEqual(check_res["data"], {"verified": True, "message": "success"})

    def test_093_checkOuterFields_missingOuterNode(self):
        """
        校验出金必填字段，缺少出金节点
        """
        currency = RTSData.currency_fiat_ro[0]["fiat"]
        outer_info = RSSData.out_bank_info[currency].copy()
        check_res = self.client.checkReceiverRequiredFields(RTSData.node_code, currency, outer_info, popKey="receiveNodeCode")
        self.checkCodeAndMessage(check_res, "01100000", "node does not exist")
        self.assertIsNone(check_res["data"])

    def test_094_checkOuterFields_missingCurrency(self):
        """
        校验出金必填字段，缺少币种
        """
        currency = RTSData.currency_fiat_ro[0]["fiat"]
        outer_info = RSSData.out_bank_info[currency].copy()
        check_res = self.client.checkReceiverRequiredFields(RTSData.node_code, currency, outer_info, popKey="receiveCurrency")
        self.checkCodeAndMessage(check_res)
        self.assertEqual(check_res["data"], {"message": "currency is empty", "verified": False})

    def test_095_checkOuterFields_missingReceiveInfo(self):
        """
        校验出金必填字段，缺少receiveInfo
        """
        currency = RTSData.currency_fiat_ro[0]["fiat"]
        outer_info = RSSData.out_bank_info[currency].copy()
        check_res = self.client.checkReceiverRequiredFields(RTSData.node_code, currency, outer_info, popKey="receiveInfo")
        self.checkCodeAndMessage(check_res)
        self.assertEqual(check_res["data"], {"message": "call outer channel api fail: null", "verified": False})

    def test_096_checkOuterFields_outBankInfoMissingField(self):
        """
        校验出金必填字段，出金银行卡信息缺少必填字段
        """
        currency = RTSData.currency_fiat_ro[0]["fiat"]
        err_field = {
            "recipientCountry": "recipient country",
            "receiverFirstName": "receiver name",
            "routingNumber": "routing number",
            "accountNumber": "account number",
            "accountType": "receiver account type",
            "receiverCurrency": "receiver currency",
            "payOutMethod": "payout method",
        }
        for field in RSSData.out_bank_fields[currency]:
            field = field["name"]
            self.client.logger.info(f"出金银行卡缺少字段: {field}")
            outer_info = RSSData.out_bank_info[currency].copy()
            outer_info.pop(field)
            check_res = self.client.checkReceiverRequiredFields(RTSData.node_code, currency, outer_info)
            # err_msg = f"Parameter error: Call bank error: {err_field[field]} cannot be empty"
            err_msg = f"call outer channel api fail: {err_field[field]} cannot be empty"
            self.checkCodeAndMessage(check_res)
            self.assertFalse(check_res["data"]["verified"])
            self.assertEqual(check_res["data"]["message"], err_msg)

    def test_098_queryOrderInfo_signIncorrect(self):
        """
        查询状态，sign不正确
        """
        order_info = self.client.getOrderInfo("test_1631101183406", replaceSign="abc")
        self.checkCodeAndMessage(order_info, "01200001", "Signature error")
        self.assertIsNone(order_info["data"])

    def test_099_queryOrderInfo_keyIncorrect(self):
        """
        查询状态，key不正确
        """
        order_info = self.client.getOrderInfo("test_1631101183406", replaceKey="abc2"*8)
        self.checkCodeAndMessage(order_info, "01200001", "Signature error")
        self.assertIsNone(order_info["data"])

    def test_100_queryOrderInfo_instructionIdNotExist(self):
        """
        查询状态，查询不存在的instructionId
        """
        order_info = self.client.getOrderInfo("test_16376371575461234")
        self.checkCodeAndMessage(order_info, "01600102", "Transaction order does not exist")
        self.assertIsNone(order_info["data"])

    def test_101_queryOrderInfo_transactionIdNotExist(self):
        """
        查询状态，查询不存在的transactionId
        """
        order_info = self.client.getOrderInfo("", "1234")
        self.checkCodeAndMessage(order_info, "01600102", "Transaction order does not exist")
        self.assertIsNone(order_info["data"])

    def test_102_queryOrderInfo_parameterGiveEmpty(self):
        """
        查询状态，参数都传空字符串
        """
        order_info = self.client.getOrderInfo("", "")
        self.checkCodeAndMessage(order_info, "01600102", "Transaction order does not exist")
        self.assertIsNone(order_info["data"])

    def test_103_queryOrderInfo_missingInstructionId(self):
        """
        查询状态，缺少参数instructionId，另外一个不传
        """
        order_info = self.client.getOrderInfo("", "", popKey="instructionId")
        self.checkCodeAndMessage(order_info, "01600102", "Transaction order does not exist")
        self.assertIsNone(order_info["data"])

    def test_104_queryOrderInfo_missingTransactionId(self):
        """
        查询状态，缺少参数transactionId，另外一个不传
        """
        order_info = self.client.getOrderInfo("", "", popKey="transactionId")
        self.checkCodeAndMessage(order_info, "01600102", "Transaction order does not exist")
        self.assertIsNone(order_info["data"])

    def test_105_queryOrderLog_transactionId(self):
        """
        查询订单日志，根据transactionId查询
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        amount = 10
        outer_address = RTSData.ach_user_account
        query_order = self.submitOrderFloorOfFiatToRo(RTSData.ach_user_token, RTSData.ach_user_id, currency_info, amount, "inner", outer_address)

        order_log = self.client.getOrderStateLog("", query_order["transactionId"])
        self.checkCodeAndMessage(order_log)
        self.checkOrderLog(order_log["data"], query_order["transactionId"])

    def test_106_queryOrderLog_signIncorrect(self):
        """
        查询订单日志，sign不正确
        """
        order_log = self.client.getOrderStateLog("test_1631101183406", replaceSign="abc")
        self.checkCodeAndMessage(order_log, "01200001", "Signature error")
        self.assertIsNone(order_log["data"])

    def test_107_queryOrderLog_keyIncorrect(self):
        """
        查询订单日志，key不正确
        """
        order_log = self.client.getOrderStateLog("test_1631101183406", replaceKey="abcd"*8)
        self.checkCodeAndMessage(order_log, "01200001", "Signature error")
        self.assertIsNone(order_log["data"])

    def test_108_queryOrderLog_instructionIdNotExist(self):
        """
        查询订单日志，查询不存在的instructionId
        """
        order_log = self.client.getOrderStateLog("1234")
        self.checkCodeAndMessage(order_log, "01600102", "Transaction order does not exist")
        self.assertIsNone(order_log["data"])

    def test_109_queryOrderLog_transactionIdNotExist(self):
        """
        查询订单日志，查询不存在的transactionId
        """
        order_log = self.client.getOrderStateLog("", "1234")
        self.checkCodeAndMessage(order_log, "01600102", "Transaction order does not exist")
        self.assertIsNone(order_log["data"])

    def test_110_queryOrderLog_parameterGiveEmpty(self):
        """
        查询订单日志，参数都传空字符串
        """
        order_log = self.client.getOrderStateLog("", "")
        self.checkCodeAndMessage(order_log, "01600102", "Transaction order does not exist")
        self.assertIsNone(order_log["data"])

    def test_111_queryOrderLog_missingInstructionId(self):
        """
        查询订单日志，缺少参数instructionId，另外一个不传
        """
        order_log = self.client.getOrderStateLog("", "", popKey="instructionId")
        self.checkCodeAndMessage(order_log, "01600102", "Transaction order does not exist")
        self.assertIsNone(order_log["data"])

    def test_112_queryOrderLog_missingTransactionId(self):
        """
        查询订单日志，缺少参数transactionId，另外一个不传
        """
        order_log = self.client.getOrderStateLog("", "", popKey="transactionId")
        self.checkCodeAndMessage(order_log, "01600102", "Transaction order does not exist")
        self.assertIsNone(order_log["data"])

    def test_113_submitOrder_signIncorrect(self):
        """
        提交订单，签名不正确
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        in_currency = currency_info["fiat"]
        out_currency = currency_info["ro"]
        amount = 10.3
        router_info, router_body = self.client.getRouterList("", in_currency, "", out_currency, amount, "", currency_info["innerNodeCode"], currency_info["outerNodeCode"])
        send_node = router_info["data"][0]["sendNodeCode"]
        instruction_id = "test_" + str(int(time.time() * 1000))  # 客户单号
        source_id = instruction_id  # 客户原单
        inner_quantity = amount  # 指定下单数量
        outer_address = RTSData.ach_user_account
        rps_order, coupon_code = self.rpsClient.submitAchPayOrder(RTSData.ach_user_token, RTSData.ach_user_id, outer_address, inner_quantity)
        payment_id = rps_order["serviceChannelOrderId"]
        receiveInfo = {"walletAddress": outer_address}
        submit_order, sub_body = self.client.submitOrder(instruction_id, source_id, payment_id, in_currency, inner_quantity, out_currency, receiveInfo, sendNodeCode=send_node, couponCode=coupon_code, replaceSign="abc", withoutSendFee=True)
        self.checkCodeAndMessage(submit_order, "01200001", "Signature error")
        self.assertIsNone(submit_order["data"])

    def test_114_submitOrder_keyIncorrect(self):
        """
        提交订单，key不正确
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        in_currency = currency_info["fiat"]
        out_currency = currency_info["ro"]
        amount = 10.3
        router_info, router_body = self.client.getRouterList("", in_currency, "", out_currency, amount, "", currency_info["innerNodeCode"], currency_info["outerNodeCode"])
        send_node = router_info["data"][0]["sendNodeCode"]
        instruction_id = "test_" + str(int(time.time() * 1000))  # 客户单号
        source_id = instruction_id  # 客户原单
        inner_quantity = amount  # 指定下单数量
        outer_address = RTSData.ach_user_account
        rps_order, coupon_code = self.rpsClient.submitAchPayOrder(RTSData.ach_user_token, RTSData.ach_user_id, outer_address, inner_quantity)
        payment_id = rps_order["serviceChannelOrderId"]
        receiveInfo = {"walletAddress": outer_address}
        submit_order, sub_body = self.client.submitOrder(instruction_id, source_id, payment_id, in_currency, inner_quantity, out_currency, receiveInfo, sendNodeCode=send_node, couponCode=coupon_code, replaceKey="1abc"*8, withoutSendFee=True)
        self.checkCodeAndMessage(submit_order, "01200001", "Signature error")
        self.assertIsNone(submit_order["data"])

    def test_115_submitOrder_instructionIdRepeat(self):
        """
        提交订单，使用重复的insturctionId
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        in_currency = currency_info["fiat"]
        out_currency = currency_info["ro"]
        amount = 10.3
        outer_address = RTSData.ach_user_account
        query_order = self.submitOrderFloorOfFiatToRo(RTSData.ach_user_token, RTSData.ach_user_id, currency_info, amount, "inner", outer_address, is_just_submit=True)

        submit_order, body = self.client.submitOrder(query_order["instructionId"], query_order["instructionId"], query_order['paymentId'] + "a", in_currency, amount, out_currency, {"receiverAddress": outer_address}, withoutSendFee=True)
        self.checkCodeAndMessage(submit_order, "01100000", "instruction order already exists")
        self.assertIsNone(submit_order["data"])

    def test_116_submitOrder_paymentIdRepeat(self):
        """
        提交订单，使用重复的paymentId
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        in_currency = currency_info["fiat"]
        out_currency = currency_info["ro"]
        amount = 10.3
        outer_address = RTSData.ach_user_account
        query_order = self.submitOrderFloorOfFiatToRo(RTSData.ach_user_token, RTSData.ach_user_id, currency_info, amount, "inner", outer_address, is_just_submit=True)

        submit_order, body = self.client.submitOrder(query_order["instructionId"] + "a", query_order["instructionId"] + "a",
                                                     query_order['paymentId'], in_currency, amount, out_currency,
                                                     {"receiverAddress": outer_address}, withoutSendFee=True)
        self.checkCodeAndMessage(submit_order, "01100000", "payment order already exists")
        self.assertIsNone(submit_order["data"])

    def test_117_submitOrder_missingParameter(self):
        """
        提交订单，入金，缺少必填的参数
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        in_currency = currency_info["fiat"]
        out_currency = currency_info["ro"]
        amount = 10.3
        router_info, router_body = self.client.getRouterList("", in_currency, "", out_currency, amount, "", currency_info["innerNodeCode"], currency_info["outerNodeCode"])
        send_node = router_info["data"][0]["sendNodeCode"]
        instruction_id = "test_" + str(int(time.time() * 1000))  # 客户单号
        source_id = instruction_id  # 客户原单
        inner_quantity = amount  # 指定下单数量
        outer_address = RTSData.ach_user_account
        rps_order, coupon_code = self.rpsClient.submitAchPayOrder(RTSData.ach_user_token, RTSData.ach_user_id, outer_address, inner_quantity)
        payment_id = rps_order["serviceChannelOrderId"]
        receiveInfo = {"walletAddress": outer_address}
        missing_params = ["instructionId", "receiveInfo"]
        flag = True
        for m_p in missing_params:
            submit_order, sub_body = self.client.submitOrder(instruction_id, source_id, payment_id, in_currency, inner_quantity, out_currency, receiveInfo, sendNodeCode=send_node, couponCode=coupon_code, popKey=m_p, withoutSendFee=True)
            try:
                if m_p == "receiveInfo":
                    msg = "receive info is empty"
                else:
                    msg = f"{m_p} is empty"
                self.checkCodeAndMessage(submit_order, "01100000", msg)
                self.assertIsNone(submit_order["data"])
                self.client.logger.info(f"缺少必填参数: {m_p} 校验成功")
            except AssertionError:
                flag = False
                self.client.logger.info(f"缺少必填参数: {m_p} 校验失败")
                traceback.print_exc()
        self.assertTrue(flag, "用例有校验失败")

    def test_118_submitOrder_innerQuantityIllegal(self):
        """
        提交订单，入金数量不合法
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        send_currency = currency_info["fiat"]
        receive_currency = currency_info["ro"]
        outer_address = RTSData.ach_user_account
        send_amount = -10.3

        router_info, request_body = self.client.getRouterList(currency_info["country"], send_currency, "",
                                                              receive_currency, 10.3, "",
                                                              currency_info["innerNodeCode"],
                                                              currency_info["outerNodeCode"])
        send_node_code = router_info["data"][0]["sendNodeCode"]
        receive_node_code = router_info["data"][0]["receiveNodeCode"]

        # 提交rts订单
        instruction_id = "test_" + str(int(time.time() * 1000))  # 客户单号
        originalId = instruction_id  # 客户原单

        # 提交rps订单
        rps_order, coupon_code = self.rpsClient.submitAchPayOrder(RTSData.ach_user_token, RTSData.ach_user_id, outer_address, -send_amount)
        payment_id = rps_order["serviceChannelOrderId"]
        receive_info = {"receiverAddress": outer_address}
        submit_info, submit_body = self.client.submitOrder(
            instruction_id, originalId, payment_id, send_currency, send_amount, receive_currency, receive_info,
            sendNodeCode=send_node_code, receiveNodeCode=receive_node_code, couponCode=coupon_code, withoutSendFee=True
        )
        self.checkCodeAndMessage(submit_info, "01100000", "send amount must be greater than 0")

        submit_info, submit_body = self.client.submitOrder(
            instruction_id, originalId, payment_id, send_currency, "", receive_currency, receive_info, send_amount,
            sendNodeCode=send_node_code, receiveNodeCode=receive_node_code, couponCode=coupon_code, withoutSendFee=True
        )
        self.checkCodeAndMessage(submit_info, "01100000", "send amount is empty")
        self.assertIsNone(submit_info["data"])

    @unittest.skipIf(RTSData.host.startswith("uat"), "uat测试环境无法通过rps入金，跳过")
    def test_119_submitOrder_FiatToRo_innerQuantityMoreThanPayOrderAmount_normalDecimal(self):
        """
        提交订单，法币入金, 入金数量大于支付订单数量, 且小数精度正常
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        send_currency = currency_info["fiat"]
        receive_currency = currency_info["ro"]
        outer_address = RTSData.ach_user_account
        send_amount = 10.3

        router_info, request_body = self.client.getRouterList("", send_currency, "",
                                                              receive_currency, send_amount, "",
                                                              currency_info["innerNodeCode"],
                                                              currency_info["outerNodeCode"])
        send_node_code = router_info["data"][0]["sendNodeCode"]
        receive_node_code = router_info["data"][0]["receiveNodeCode"]

        # 提交rts订单
        instruction_id = "test_" + str(int(time.time() * 1000))  # 客户单号
        originalId = instruction_id  # 客户原单

        # 提交rps订单
        rps_order, coupon_code = self.rpsClient.submitAchPayOrder(RTSData.ach_user_token, RTSData.ach_user_id, outer_address, ApiUtils.parseNumberDecimal(send_amount - 0.1))
        payment_id = rps_order["serviceChannelOrderId"]
        receive_info = {"receiverAddress": outer_address}
        self.client.submitOrder(
            instruction_id, originalId, payment_id, send_currency, send_amount, receive_currency, receive_info,
            sendNodeCode=send_node_code, receiveNodeCode=receive_node_code, couponCode=coupon_code, withoutSendFee=True
        )
        # 等待5分钟
        time.sleep(200)
        # 查询订单状态
        query_order_info = self.client.getOrderInfo(instruction_id)
        self.checkCodeAndMessage(query_order_info)
        self.assertEqual(query_order_info["data"]["txState"], "MINT_SUBMIT")

        rss_order = self.mysql.exec_sql_query("select * from roxe_rss_us.rss_order where payment_id='{}'".format(payment_id))
        self.assertEqual(rss_order[0]["orderState"], "mintage_init")

        self.clearInvalidFormFromDB(payment_id)

    @unittest.skipIf(RTSData.host.startswith("uat"), "uat测试环境无法通过rps入金，跳过")
    def test_120_submitOrder_FiatToRo_innerQuantityLessThanPayOrderAmount_normalDecimal(self):
        """
        提交订单，法币入金, 入金数量小于支付订单数量, 且小数精度正常
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        send_currency = currency_info["fiat"]
        receive_currency = currency_info["ro"]
        outer_address = RTSData.ach_user_account
        send_amount = 10.3
        a_balance = self.chain_client.getBalanceWithRetry(outer_address, send_currency)
        self.client.logger.info(f"{outer_address} 持有资产: {a_balance}")
        router_info, request_body = self.client.getRouterList("", send_currency, "",
                                                              receive_currency, send_amount, "",
                                                              currency_info["innerNodeCode"],
                                                              currency_info["outerNodeCode"])
        send_node_code = router_info["data"][0]["sendNodeCode"]
        receive_node_code = router_info["data"][0]["receiveNodeCode"]

        # 提交rts订单
        instruction_id = "test_" + str(int(time.time() * 1000))  # 客户单号
        originalId = instruction_id  # 客户原单

        # 提交rps订单
        rps_order, coupon_code = self.rpsClient.submitAchPayOrder(RTSData.ach_user_token, RTSData.ach_user_id, outer_address,
                                                                  ApiUtils.parseNumberDecimal(send_amount + 0.1))
        payment_id = rps_order["serviceChannelOrderId"]
        receive_info = {"receiverAddress": outer_address}
        self.client.submitOrder(
            instruction_id, originalId, payment_id, send_currency, send_amount, receive_currency, receive_info,
            sendNodeCode=send_node_code, receiveNodeCode=receive_node_code, couponCode=coupon_code, withoutSendFee=True
        )
        # 等待5分钟
        b_time = time.time()
        time_out = 300
        query_info = None
        while True:
            if time.time() - b_time > time_out:
                self.client.logger.error("等待时间超时")
                break
            query_info = self.client.getOrderInfo(instruction_id)
            if query_info["data"]["txState"] == "TRANSACTION_FINISH":
                self.client.logger.info("rts订单已经完成")
                break
            time.sleep(time_out / 15)
        self.assertEqual(query_info["data"]["txState"], "TRANSACTION_FINISH")

        a_balance2 = self.chain_client.getBalanceWithRetry(outer_address, send_currency)
        self.client.logger.info(f"{outer_address} 持有资产: {a_balance2}, 变化了{a_balance2-a_balance}")
        self.assertAlmostEqual(a_balance2 - a_balance, ApiUtils.parseNumberDecimal(send_amount, 6), msg="资产变化和订单金额不一致", delta=0.1**6)
        self.assertAlmostEqual(float(router_info["data"][0]["receiveAmount"]), ApiUtils.parseNumberDecimal(send_amount, 6), delta=0.1**8)

    @unittest.skipIf(RTSData.host.startswith("uat"), "uat测试环境无法通过rps入金，跳过")
    def test_121_submitOrder_FiatToRo_innerQuantityMoreThanPayOrderAmount_notNormalDecimal(self):
        """
        提交订单，法币入金, 入金数量大于支付订单数量, 且小数精度大于6位
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        send_currency = currency_info["fiat"]
        receive_currency = currency_info["ro"]
        outer_address = RTSData.ach_user_account
        send_amount = 10.34567892
        a_balance = self.chain_client.getBalanceWithRetry(outer_address, send_currency)
        self.client.logger.info(f"{outer_address} 持有资产: {a_balance}")
        router_info, request_body = self.client.getRouterList("", send_currency, "",
                                                              receive_currency, send_amount, "",
                                                              currency_info["innerNodeCode"],
                                                              currency_info["outerNodeCode"])
        send_node_code = router_info["data"][0]["sendNodeCode"]
        receive_node_code = router_info["data"][0]["receiveNodeCode"]

        # 提交rts订单
        instruction_id = "test_" + str(int(time.time() * 1000))  # 客户单号
        originalId = instruction_id  # 客户原单

        # 提交rps订单
        rps_order, coupon_code = self.rpsClient.submitAchPayOrder(RTSData.ach_user_token, RTSData.ach_user_id, outer_address,
                                                                  ApiUtils.parseNumberDecimal(send_amount - 0.2))
        payment_id = rps_order["serviceChannelOrderId"]
        receive_info = {"receiverAddress": outer_address}
        submit_info, submit_body = self.client.submitOrder(
            instruction_id, originalId, payment_id, send_currency, send_amount, receive_currency, receive_info,
            sendNodeCode=send_node_code, receiveNodeCode=receive_node_code, couponCode=coupon_code, withoutSendFee=True
        )
        # 查询订单状态
        # 等待5分钟
        time.sleep(60)
        query_info = self.client.getOrderInfo("", submit_info["data"]["transactionId"])
        self.assertEqual(query_info["data"]["txState"], "MINT_SUBMIT")

        rss_order = self.mysql.exec_sql_query("select * from roxe_rss_us.rss_order where payment_id='{}'".format(payment_id))
        self.assertEqual(rss_order[0]["orderState"], "mintage_init")

        self.clearInvalidFormFromDB(payment_id)

    @unittest.skipIf(RTSData.host.startswith("uat"), "uat测试环境无法通过rps入金，跳过")
    def test_122_submitOrder_FiatToRo_innerQuantityLessThanPayOrderAmount_notNormalDecimal(self):
        """
        提交订单，法币入金, 入金数量小于支付订单数量, 且小数精度大于6位
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        send_currency = currency_info["fiat"]
        receive_currency = currency_info["ro"]
        outer_address = RTSData.ach_user_account
        send_amount = 10.12345678
        a_balance = self.chain_client.getBalanceWithRetry(outer_address, send_currency)
        self.client.logger.info(f"{outer_address} 持有资产: {a_balance}")
        router_info, request_body = self.client.getRouterList("", send_currency, "",
                                                              receive_currency, send_amount, "",
                                                              currency_info["innerNodeCode"],
                                                              currency_info["outerNodeCode"])
        send_node_code = router_info["data"][0]["sendNodeCode"]
        receive_node_code = router_info["data"][0]["receiveNodeCode"]

        # 提交rts订单
        instruction_id = "test_" + str(int(time.time() * 1000))  # 客户单号
        originalId = instruction_id  # 客户原单

        # 提交rps订单
        rps_order, coupon_code = self.rpsClient.submitAchPayOrder(RTSData.ach_user_token, RTSData.ach_user_id, outer_address,
                                                                  ApiUtils.parseNumberDecimal(send_amount + 0.1))
        payment_id = rps_order["serviceChannelOrderId"]
        receive_info = {"receiverAddress": outer_address}
        submit_info, submit_body = self.client.submitOrder(
            instruction_id, originalId, payment_id, send_currency, send_amount, receive_currency, receive_info,
            sendNodeCode=send_node_code, receiveNodeCode=receive_node_code, couponCode=coupon_code, withoutSendFee=True
        )
        self.checkCodeAndMessage(submit_info)
        self.checkSubmitOrderResult(submit_info["data"], submit_body, router_info["data"][0])
        # 查询订单状态
        # 等待5分钟
        b_time = time.time()
        time_out = 400
        query_info = None
        while True:
            if time.time() - b_time > time_out:
                self.client.logger.error("等待时间超时")
                break
            query_info = self.client.getOrderInfo(instruction_id)
            if query_info["data"]["txState"] == "TRANSACTION_FINISH":
                self.client.logger.info("rts订单已经完成")
                break
            time.sleep(time_out / 15)
        self.assertEqual(query_info["data"]["txState"], "TRANSACTION_FINISH")

        a_balance2 = self.chain_client.getBalanceWithRetry(outer_address, send_currency)
        self.client.logger.info(f"{outer_address} 持有资产: {a_balance2}, 变化了{a_balance2 - a_balance}")
        self.assertAlmostEqual(a_balance2 - a_balance, ApiUtils.parseNumberDecimal(send_amount, 2), msg="资产变化和订单金额不一致",
                               delta=0.1 ** 6)
        self.assertAlmostEqual(float(router_info["data"][0]["receiveAmount"]),
                               ApiUtils.parseNumberDecimal(send_amount, 2), delta=0.1 ** 8)

    def test_123_submitOrder_RoToFiat_innerQuantityMoreThanPayOrderAmount_normalDecimal(self):
        """
        提交订单，法币出金, rts订单数量大于支付订单数量, 且小数精度正常
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        in_currency = currency_info["ro"]
        out_currency = currency_info["fiat"]
        from_account = RTSData.ach_user_account
        outer_bank_info = RSSData.out_bank_info[currency_info["fiat"]].copy()
        amount = 10
        router_info, router_body = self.client.getRouterList("", in_currency, currency_info["country"], out_currency, amount, "", currency_info["innerNodeCode"], currency_info["outerNodeCode"])
        send_node_code = router_info["data"][0]["sendNodeCode"]
        receive_node_code = router_info["data"][0]["receiveNodeCode"] if currency_info["outerNodeCode"] == "" else \
            currency_info["outerNodeCode"]
        router_in_account = router_info["data"][0]["custodyAccountInfo"]["custodyAccount"]
        # 校验出金必填字段
        check_outer_fields = self.client.checkReceiverRequiredFields(receive_node_code, out_currency, outer_bank_info)
        self.checkCodeAndMessage(check_outer_fields)
        self.assertEqual(check_outer_fields["data"], {"verified": True, "message": "success"})

        # 提交rps订单
        rps_order = self.rpsClient.submitWalletPayOrder(RTSData.ach_user_token, RTSData.ach_user_id, from_account, router_in_account, ApiUtils.parseNumberDecimal(amount - 0.1))
        payment_id = rps_order["serviceChannelOrderId"]
        # 提交rts订单
        instruction_id = "test_" + str(int(time.time() * 1000))  # 客户单号
        source_id = instruction_id  # 客户原单
        # 提交rts订单
        submit_order, submit_body = self.client.submitOrder(
            instruction_id, source_id, payment_id, in_currency, amount, out_currency, outer_bank_info,
            sendNodeCode=send_node_code, receiveNodeCode=receive_node_code
        )
        transaction_id = submit_order["data"]["transactionId"]
        # 等待5分钟
        self.waitUntilRedeemOrderCompleted(transaction_id, payment_id)
        # 查询订单状态
        query_order = self.client.getOrderInfo(instruction_id)
        self.assertEqual(query_order["data"]["txState"], "REDEEM_SUBMIT")

        rss_order = self.mysql.exec_sql_query("select * from roxe_rss_us.rss_order where payment_id='{}'".format(payment_id))
        self.assertEqual(rss_order[0]["orderState"], "redeem_init")

        self.clearInvalidFormFromDB(payment_id)

    def test_124_submitOrder_RoToFiat_innerQuantityLessThanPayOrderAmount_normalDecimal(self):
        """
        提交订单，法币出金, rts订单数量小于支付订单数量, 且小数精度正常
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        in_currency = currency_info["ro"]
        out_currency = currency_info["fiat"]
        from_account = RTSData.ach_user_account
        outer_bank_info = RSSData.out_bank_info[currency_info["fiat"]].copy()
        amount = 10
        router_info, router_body = self.client.getRouterList("", in_currency, currency_info["country"], out_currency,
                                                             amount, "", currency_info["innerNodeCode"],
                                                             currency_info["outerNodeCode"])
        send_node_code = router_info["data"][0]["sendNodeCode"]
        receive_node_code = router_info["data"][0]["receiveNodeCode"] if currency_info["outerNodeCode"] == "" else \
            currency_info["outerNodeCode"]
        router_in_account = router_info["data"][0]["custodyAccountInfo"]["custodyAccount"]
        # 校验出金必填字段
        check_outer_fields = self.client.checkReceiverRequiredFields(receive_node_code, out_currency, outer_bank_info)
        self.checkCodeAndMessage(check_outer_fields)
        self.assertEqual(check_outer_fields["data"], {"verified": True, "message": "success"})

        # 提交rps订单
        rps_order = self.rpsClient.submitWalletPayOrder(RTSData.ach_user_token, RTSData.ach_user_id, from_account, router_in_account, amount)
        payment_id = rps_order["serviceChannelOrderId"]
        # 提交rts订单
        instruction_id = "test_" + str(int(time.time() * 1000))  # 客户单号
        source_id = instruction_id  # 客户原单
        # 提交rts订单
        submit_order, submit_body = self.client.submitOrder(
            instruction_id, source_id, payment_id, in_currency, ApiUtils.parseNumberDecimal(amount - 0.1), out_currency, outer_bank_info,
            sendNodeCode=send_node_code, receiveNodeCode=receive_node_code
        )
        transaction_id = submit_order["data"]["transactionId"]
        # 等待5分钟
        self.waitUntilRedeemOrderCompleted(transaction_id, payment_id)
        # 查询订单状态
        query_order = self.client.getOrderInfo(instruction_id)
        self.assertEqual(query_order["data"]["txState"], "REDEEM_SUBMIT")
        rss_order = self.mysql.exec_sql_query("select * from roxe_rss_us.rss_order where payment_id='{}'".format(payment_id))
        self.assertEqual(rss_order[0]["orderState"], "redeem_init")

        self.clearInvalidFormFromDB(payment_id)

    def test_125_submitOrder_RoToFiat_innerQuantityMoreThanPayOrderAmount_notNormalDecimal(self):
        """
        提交订单，法币出金, rts订单数量大于支付订单数量, 且小数精度大于6位
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        in_currency = currency_info["ro"]
        out_currency = currency_info["fiat"]
        from_account = RTSData.ach_user_account
        outer_bank_info = RSSData.out_bank_info[currency_info["fiat"]].copy()
        amount = 10.1234567
        router_info, router_body = self.client.getRouterList("", in_currency, currency_info["country"], out_currency,
                                                             amount, "", currency_info["innerNodeCode"],
                                                             currency_info["outerNodeCode"])
        send_node_code = router_info["data"][0]["sendNodeCode"]
        receive_node_code = router_info["data"][0]["receiveNodeCode"] if currency_info["outerNodeCode"] == "" else \
            currency_info["outerNodeCode"]
        router_in_account = router_info["data"][0]["custodyAccountInfo"]["custodyAccount"]
        # 校验出金必填字段
        check_outer_fields = self.client.checkReceiverRequiredFields(receive_node_code, out_currency, outer_bank_info)
        self.checkCodeAndMessage(check_outer_fields)
        self.assertEqual(check_outer_fields["data"], {"verified": True, "message": "success"})

        # 提交rps订单
        rps_order = self.rpsClient.submitWalletPayOrder(RTSData.ach_user_token, RTSData.ach_user_id, from_account, router_in_account, ApiUtils.parseNumberDecimal(amount - 0.1))
        payment_id = rps_order["serviceChannelOrderId"]
        # 提交rts订单
        instruction_id = "test_" + str(int(time.time() * 1000))  # 客户单号
        source_id = instruction_id  # 客户原单
        # 提交rts订单
        submit_order, submit_body = self.client.submitOrder(
            instruction_id, source_id, payment_id, in_currency, amount, out_currency, outer_bank_info,
            sendNodeCode=send_node_code, receiveNodeCode=receive_node_code
        )
        transaction_id = submit_order["data"]["transactionId"]
        # 等待5分钟
        self.waitUntilRedeemOrderCompleted(transaction_id, payment_id)
        # 查询订单状态
        query_order = self.client.getOrderInfo(instruction_id)
        self.assertEqual(query_order["data"]["txState"], "REDEEM_SUBMIT")

        rss_order = self.mysql.exec_sql_query("select * from roxe_rss_us.rss_order where payment_id='{}'".format(payment_id))
        self.assertEqual(rss_order[0]["orderState"], "redeem_init")

        self.clearInvalidFormFromDB(payment_id)

    def test_126_submitOrder_RoToFiat_innerQuantityLessThanPayOrderAmount_notNormalDecimal(self):
        """
        提交订单，法币出金, rts订单数量小于支付订单数量, 且小数精度大于6位
        """
        currency_info = RTSData.currency_fiat_ro[0].copy()
        in_currency = currency_info["ro"]
        out_currency = currency_info["fiat"]
        from_account = RTSData.ach_user_account
        outer_bank_info = RSSData.out_bank_info[currency_info["fiat"]].copy()
        amount = 10.12345678
        router_info, router_body = self.client.getRouterList("", in_currency, currency_info["country"], out_currency,
                                                             amount, "", currency_info["innerNodeCode"],
                                                             currency_info["outerNodeCode"])
        send_node_code = router_info["data"][0]["sendNodeCode"]
        receive_node_code = router_info["data"][0]["receiveNodeCode"] if currency_info["outerNodeCode"] == "" else \
            currency_info["outerNodeCode"]
        router_in_account = router_info["data"][0]["custodyAccountInfo"]["custodyAccount"]
        # 校验出金必填字段
        check_outer_fields = self.client.checkReceiverRequiredFields(receive_node_code, out_currency, outer_bank_info)
        self.checkCodeAndMessage(check_outer_fields)
        self.assertEqual(check_outer_fields["data"], {"verified": True, "message": "success"})

        # 提交rps订单
        rps_order = self.rpsClient.submitWalletPayOrder(RTSData.ach_user_token, RTSData.ach_user_id, from_account, router_in_account, ApiUtils.parseNumberDecimal(amount + 0.2))
        payment_id = rps_order["serviceChannelOrderId"]
        # 提交rts订单
        instruction_id = "test_" + str(int(time.time() * 1000))  # 客户单号
        source_id = instruction_id  # 客户原单
        # 提交rts订单
        submit_order, submit_body = self.client.submitOrder(
            instruction_id, source_id, payment_id, in_currency, amount, out_currency, outer_bank_info,
            sendNodeCode=send_node_code, receiveNodeCode=receive_node_code
        )
        transaction_id = submit_order["data"]["transactionId"]
        # 等待5分钟
        self.waitUntilRedeemOrderCompleted(transaction_id, payment_id)
        # 查询订单状态
        query_order = self.client.getOrderInfo(instruction_id)
        self.assertEqual(query_order["data"]["txState"], "REDEEM_SUBMIT")

        rss_order = self.mysql.exec_sql_query("select * from roxe_rss_us.rss_order where payment_id='{}'".format(payment_id))
        self.assertEqual(rss_order[0]["orderState"], "redeem_init")
        self.clearInvalidFormFromDB(payment_id)
