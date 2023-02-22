# coding:utf-8
# author: MingLei Li
# date: 2022-02-16
import json
import logging
from roxe_libs.Global import Global
from roxe_libs import settings
from roxe_libs.baseApi import *
from roxe_libs.ApiUtils import makeMD5
import datetime, time


class RPSApiClient:

    def __init__(self, host, appKey="", secret="", user_id="", user_login_token=""):
        self.host = host
        self.appKey = appKey
        self.secret = secret
        self.user_id = user_id
        self.user_login_token = user_login_token
        # 获取全局的日志记录logger
        self.logger = logging.getLogger(Global.getValue(settings.logger_name))

        traceable = Global.getValue(settings.enable_trace)
        if traceable:
            for handle in self.logger.handlers:
                if "filehand" in str(handle).lower():
                    handle.setLevel(logging.DEBUG)
                # handle.setLevel(logging.DEBUG)

    def makeSign(self, body: dict):
        sort_keys = sorted([k for k in body.keys()])
        tmp_str = ""
        for k in sort_keys:
            if tmp_str:
                tmp_str += "&"
            tmp_str += k + "=" + body[k]
        self.logger.debug(tmp_str)
        signed = makeMD5(tmp_str, self.secret).upper()
        self.logger.debug(f"sign: {signed}")

        return signed

    def getPayInMethodList(self, token, orderId):
        params = {"orderId": orderId}
        headers = {"token": token}
        self.logger.info("获取支付方式列表")
        res = sendGetRequest(self.host + "/roxe-app/rps/method/getPayInMethodList", params, headers)
        self.logger.debug("请求headers: {}".format(headers))
        self.logger.debug("请求参数: {}".format(params))
        self.logger.info("请求结果: {}".format(res.text))
        return res.json()

    def getRedirectUrl(self, token, orderId, op):
        params = {
            "ts": str(int(datetime.datetime.now().timestamp())),
            "id": orderId,
            "key": self.appKey,
            "op": op,
        }
        params["sign"] = self.makeSign(params)
        headers = {"token": token}
        self.logger.info("获取重定向 URL")
        res = sendGetRequest(self.host + "/roxe-app/rps/payin/redirectPage", params, headers)
        self.logger.debug("请求headers: {}".format(headers))
        self.logger.debug("请求参数: {}".format(params))
        self.logger.info("请求结果: {}".format(res.text))
        return res.text

    def createOrder(self, userId, payOrderInfo, **kwargs):
        body = payOrderInfo
        for k, v in kwargs.items():
            body[k] = v
        headers = {"QaKey": "10eb878b540198edfe934d16b2542315247978d9a07ec92ba25b703d566cca85", "userId": userId, "appkey": self.appKey}
        self.logger.info("下单")
        res = sendPostRequest(self.host + "/roxe-rps/inner/payin/createOrder", body, headers)
        self.logger.debug("请求headers: {}".format(headers))
        self.logger.debug("请求参数: {}".format(body))
        self.logger.info("请求结果: {}".format(res.text))
        return res.json()

    def submitPayMethod(self, token, methodInfo, **kwargs):
        body = methodInfo
        for k, v in kwargs.items():
            body[k] = v
        headers = {"token": token}
        self.logger.info("选择支付方式")
        res = sendPostRequest(self.host + "/roxe-app/rps/payin/submitPayMethod", body, headers)
        self.logger.debug("请求headers: {}".format(headers))
        self.logger.debug("请求参数: {}".format(body))
        self.logger.info("请求结果: {}".format(res.text))
        return res.json()

    def rps_submit_order(self, token, userId, sourceRoxeAccount, targetRoxeAccount, Method, amount, channelFeeDeductionMethod=2):
        """
        rps下单获取paymentId
        token：用户登录token
        userId：用户的userId
        sourceRoxeAccount：发起方账户钱包地址（roxeid）
        targetRoxeAccount：接收方账户钱包地址（托管账户地址）
        Method：debitCard或者ach或者balance
        amout：初始创建订单金额
        channelFeeDeductionMethod：费用扣减方式（1 内扣；2 外扣），默认为2
        """

        orderInfo = {
            "currency": "USD",
            "country": "US",
            "businessType": "transfer",
            "channelFeeDeductionMethod": channelFeeDeductionMethod,
            "businessAmount": amount,
            "businessOrderNo": "69",
            "businessItemName": "test",
            "sourceRoxeAccount": sourceRoxeAccount,
            "targetRoxeAccount": targetRoxeAccount
        }
        res_info = self.createOrder(userId, orderInfo)  # 创建订单
        # print(res_info["data"])
        orderId = res_info["data"]
        list_info = self.getPayInMethodList(token, orderId)  # 获取支付方式列表
        # print(list_info)
        methodList_info = list_info["data"]["methodList"]
        for i in range(len(methodList_info)):
            payMethod = list_info["data"]["methodList"][i]["type"]
            if payMethod == Method and payMethod == "debitCard":  # CHECKOUT（银行卡）
                payMethod = list_info["data"]["methodList"][i]["type"]
                serviceChannel = list_info["data"]["methodList"][i]["serviceChannel"]
                # print(serviceChannel)
                channelFee = list_info["data"]["methodList"][i]["currencyList"][0]["fee"]
                allowanceFee = list_info["data"]["methodList"][i]["currencyList"][0]["allowanceFee"]
                # payableAmount = amount + channelFee - 0
                payableAmount = list_info["data"]["methodList"][i]["currencyList"][0]["payableAmount"]
                payBankAccountId = list_info["data"]["methodList"][i]["bankAccountList"][0]["id"]
                methodInfo = {
                    "id": orderId,
                    "currency": "USD",
                    "payMethod": payMethod,
                    "serviceChannel": serviceChannel,
                    "channelFee": channelFee,
                    "allowanceFee": allowanceFee,
                    "payableAmount": payableAmount,
                    "payBankAccountId": payBankAccountId,
                    "cardDetails": "",
                    "authConsent": "",
                    "transactionSpecificDetails": "",
                    "accountOrShippingInformation": "",
                    "transactionHistory": "",
                    "transactionReceiptTip": "",
                    "revocationTip": ""
                }
                rps_order_info = self.submitPayMethod(token, methodInfo)
                # print(rps_order_info)
                paymentId = rps_order_info["data"]["serviceChannelOrderId"]
                # print(paymentId)
                return paymentId
            elif payMethod == Method and payMethod == "ach":  # STRIPE通道（plaid）
                serviceChannel = list_info["data"]["methodList"][i]["serviceChannel"]
                channelFee = list_info["data"]["methodList"][i]["currencyList"][0]["fee"]
                allowanceFee = list_info["data"]["methodList"][i]["currencyList"][0]["allowanceFee"]
                payableAmount = list_info["data"]["methodList"][i]["currencyList"][0]["payableAmount"]
                payBankAccountId = list_info["data"]["methodList"][i]["bankAccountList"][0]["id"]
                methodInfo = {
                    "id": orderId,
                    "currency": "USD",
                    "payMethod": payMethod,
                    "serviceChannel": serviceChannel,
                    "channelFee": channelFee,
                    "allowanceFee": allowanceFee,
                    "payableAmount": payableAmount,
                    "payBankAccountId": payBankAccountId,
                    "cardDetails": "",
                    "authConsent": "I authorize roxe to electronically debit my account and, if necessary, electronically credit my account to correct erroneous debits.",
                    "transactionSpecificDetails": "123",
                    "accountOrShippingInformation": "123",
                    "transactionHistory": "{\"businessType\":\"Deposit\",\"amount\":1,\"currency\":\"USD\",\"paymentFee\":0,\"bankAccount\":\"Houndstooth Bank\",\"na\":\"6789\"}",
                    "transactionReceiptTip": "After the transaction is completed, you can view the details in the app transaction history",
                    "revocationTip": "To revoke authorization, please send an email to contact@roxe.io"
                }
                rps_order_info = self.submitPayMethod(token, methodInfo)
                # print(rps_order_info)
                paymentId = rps_order_info["data"]["serviceChannelOrderId"]
                # print(paymentId)
                return paymentId
            elif payMethod == Method and payMethod == "balance":  # 余额支付方式，可购买、提现
                serviceChannel = list_info["data"]["methodList"][i]["serviceChannel"]
                channelFee = list_info["data"]["methodList"][i]["currencyList"][0]["fee"]
                allowanceFee = list_info["data"]["methodList"][i]["currencyList"][0]["allowanceFee"]
                payableAmount = list_info["data"]["methodList"][i]["currencyList"][0]["payableAmount"]
                # payableAmount = amount + channelFee - 0
                # payBankAccountId = list_info["data"]["methodList"][i]["bankAccountList"][0]["id"]
                methodInfo = {
                    "id": orderId,
                    "currency": "USD",
                    "payMethod": payMethod,
                    "serviceChannel": serviceChannel,
                    "channelFee": channelFee,
                    "allowanceFee": allowanceFee,
                    "payableAmount": payableAmount,
                    # "payBankAccountId": 0,
                    "cardDetails": "",
                    "authConsent": "",
                    "transactionSpecificDetails": "",
                    "accountOrShippingInformation": "",
                    "transactionHistory": "",
                    "transactionReceiptTip": "",
                    "revocationTip": ""
                }
                rps_order_info = self.submitPayMethod(token, methodInfo)
                # print(rps_order_info)
                paymentId = rps_order_info["data"]["serviceChannelOrderId"]
                # print(paymentId)
                return paymentId
            else:
                self.logger.info("没有找到合适对应的方式")

            # rps_order_info = self.submitPayMethod(token, methodInfo)
            # # print(rps_order_info)
            # paymentId = rps_order_info["data"]["serviceChannelOrderId"]
            # # print(paymentId)
            # return paymentId

    def queryAndSelectPayMethod(self, user_token, pay_order, pay_method):
        # 查询支付方式
        pay_methods = self.getPayInMethodList(user_token, pay_order)
        select_method = [i for i in pay_methods["data"]["methodList"] if i["type"] == pay_method][0]
        self.logger.info("选择的支付方式: {}".format(select_method))
        method_info = {
            "id": pay_order,
            "currency": "USD",
            "payMethod": select_method["type"],
            "serviceChannel": select_method["serviceChannel"],
            "channelFee": select_method["currencyList"][0]["fee"],
            "allowanceFee": select_method["currencyList"][0]["allowanceFee"],
            "payableAmount": select_method["currencyList"][0]["payableAmount"],
            "payBankAccountId": select_method["bankAccountList"][0]["id"],
            "cardDetails": "",
            "authConsent": "",
            "transactionSpecificDetails": "",
            "accountOrShippingInformation": "",
            "transactionHistory": "",
            "transactionReceiptTip": "",
            "revocationTip": ""
        }

        if pay_method == "ach":
            method_info["authConsent"] = "I authorize roxe to electronically debit my account and, if necessary, electronically credit my account to correct erroneous debits.",
            method_info["transactionSpecificDetails"] = "123"
            method_info["accountOrShippingInformation"] = "123"
            method_info["transactionHistory"] = "{\"businessType\":\"Deposit\",\"amount\":1,\"currency\":\"USD\",\"paymentFee\":0,\"bankAccount\":\"Houndstooth Bank\",\"na\":\"6789\"}",
            method_info["transactionReceiptTip"]= "After the transaction is completed, you can view the details in the app transaction history"
            method_info["revocationTip"] = "To revoke authorization, please send an email to contact@roxe.io"
        submit_order = self.submitPayMethod(token, method_info)
        return submit_order

    def submitAchPayOrder(self, userToken, userId, target_account, businessAmount, currency="USD", expect_pay_success=True, dbClient=None):
        pay_order_info = {
            "businessAmount": businessAmount,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "69",
            "businessItemName": "test",
            "sourceRoxeAccount": "",
            "targetRoxeAccount": target_account,
            "currency": currency,
            "businessType": "deposit",
            "country": "US",
        }
        # 查询钱包余额
        res_info = self.createOrder(userId, pay_order_info)  # 创建订单
        pay_order = res_info["data"]
        # 选择支付方式进行支付
        submit_order = self.queryAndSelectPayMethod(userToken, pay_order, "ach")
        assert submit_order["data"] is not None
        paymentId = submit_order["data"]["serviceChannelOrderId"]
        coupon_code = submit_order["data"]["couponCode"]  # 优惠券code
        # 查询订单状态
        b_time = time.time()
        rps_sql = f"select * from roxe_pay_in_out.roxe_pay_in_order where id='{pay_order}'"
        while time.time() - b_time < 600:
            query_order = dbClient.exec_sql_query(rps_sql)[0]
            if expect_pay_success:
                if query_order["status"] == 2:
                    paymentId = query_order["serviceChannelOrderId"]
                    coupon_code = query_order["couponCode"]
                    self.logger.info("rps订单付款成功")
                    break
            else:
                break
            time.sleep(10)
        return paymentId, coupon_code

    def submitWalletPayOrder(self, userToken, userId, source_account, target_account, businessAmount, currency="USD", expect_pay_success=True, dbClient=None):
        pay_order_info = {
            "businessAmount": businessAmount,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": "69",
            "businessItemName": "test",
            "sourceRoxeAccount": source_account,
            "targetRoxeAccount": target_account,
            "currency": currency,
            "businessType": "transfer",
            "country": "US",
        }
        # 查询钱包余额
        res_info = self.createOrder(userId, pay_order_info)  # 创建订单
        pay_order = res_info["data"]
        # 选择支付方式进行支付

        submit_order = self.queryAndSelectPayMethod(userToken, pay_order, "balance")
        paymentId = submit_order["data"]["serviceChannelOrderId"]
        assert submit_order["data"] is not None
        # 查询订单状态
        b_time = time.time()
        rps_sql = f"select * from roxe_pay_in_out.roxe_pay_in_order where id='{pay_order}'"
        flag = False
        while time.time() - b_time < 600:
            query_order = dbClient.exec_sql_query(rps_sql)[0]
            if expect_pay_success:
                if query_order["status"] == 2:
                    paymentId = query_order["serviceChannelOrderId"]
                    flag = True
                    break
            else:
                break
            time.sleep(10)
        if flag:
            self.logger.info("rps订单付款成功")
        else:
            self.logger.warning("rps订单付款还未成功")
        return paymentId


if __name__ == "__main__":
    from roxe_libs.pub_function import setCustomLogger
    my_logger = setCustomLogger("rps", "rps.txt", True)
    Global.setValue(settings.logger_name, my_logger.name)
    Global.setValue(settings.enable_trace, True)
    client = RPSApiClient("http://roxe-gateway-bj-test.roxepro.top:38889", "adfasdas", "1212")
    token = "eyJhbGciOiJIUzI1NiJ9.eyJpdGMiOiI4NiIsImlzcyI6IlJPWEUiLCJhdWQiOiIxMDAyNzYiLCJzdWIiOiJVU0VSX0xPR0lOIiwibmJmIjoxNjQ1NzgzNDY3fQ.kMAXg-qe7wxpwtfVRMuivcRqUmVSnRl8E0ukwn8wvh0"

    orderInfo = {
        "currency": "USD",
        "country": "US",
        "businessType": "transfer",
        "channelFeeDeductionMethod": 2,
        "businessAmount": 0.1,
        "businessOrderNo": "69",
        "businessItemName": "test",
        "sourceRoxeAccount": "agjyrafzwlng",
        "targetRoxeAccount": "f3viuzqrqq4d"
    }
    # order = client.createOrder("100144", orderInfo)
    # orderId = order["data"]
    orderId = "91326946545496064"
    client.getPayInMethodList(token, orderId)
    # client.getRedirectUrl(token, orderId, "success")
    methodInfo = {
        "id": orderId,
        "currency": "USD",
        "payMethod": "balance",
        "serviceChannel": "WALLET",
        "channelFee": 0,
        "allowanceFee": 0,
        "payableAmount": 0.10,
        # "payBankAccountId": 0,
        "cardDetails": "",
        "authConsent": "",
        "transactionSpecificDetails": "",
        "accountOrShippingInformation": "",
        "transactionHistory": "",
        "transactionReceiptTip": "",
        "revocationTip": ""
    }
    # client.submitPayMethod(token, methodInfo)
    # client.makeSign(orderInfo)
    # client = RPSApiClient("http://roxe-gateway-bj-test.roxepro.top:38889", "", "adfasdas", "1212")
    """
    # token = "eyJhbGciOiJIUzI1NiJ9.eyJpdGMiOiI4NiIsImlzcyI6IlJPWEUiLCJhdWQiOiIxMDAyNzYiLCJzdWIiOiJVU0VSX0xPR0lOIiwibmJmIjoxNjQ1NzgzNDY3fQ.kMAXg-qe7wxpwtfVRMuivcRqUmVSnRl8E0ukwn8wvh0"
    # userId = "100276"
    token = "eyJhbGciOiJIUzI1NiJ9.eyJpdGMiOiIxIiwiaXNzIjoiUk9YRSIsImF1ZCI6IjEwMDM1NiIsInN1YiI6IlVTRVJfTE9HSU4iLCJuYmYiOjE2NDYwMjg5ODZ9.5XHfFKtoqJYYi_KNVPxOfFquepBeF8k3rMKvIScm0hk"
    userId = "100356"
    amount = 2
    sourceRoxeAccount = "v4twt4yhqtft"
    targetRoxeAccount = "crxaptw4rqcf"

    """
    # token_2 = "eyJhbGciOiJIUzI1NiJ9.eyJpdGMiOiIxIiwiaXNzIjoiUk9YRSIsImF1ZCI6IjEwMDM1NiIsInN1YiI6IlVTRVJfTE9HSU4iLCJuYmYiOjE2NDYwMjg5ODZ9.5XHfFKtoqJYYi_KNVPxOfFquepBeF8k3rMKvIScm0hk"
    # userId_2 = "100356"
    # sourceRoxeAccount_2 = "v4twt4yhqtft"
    # targetRoxeAccount_2 = "crxaptw4rqcf"
    # amount = 2.3
    # paymentId = RPSApiClient.rps_submit_order(token_2, userId_2, sourceRoxeAccount_2, targetRoxeAccount_2, "debitCard", amount)
    # print(paymentId)