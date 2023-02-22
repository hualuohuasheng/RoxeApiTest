# coding=utf-8
# author: Li MingLei
# date: 2021-08-30
import logging
from roxe_libs.baseApi import *
from roxe_libs.Global import Global
from roxe_libs import settings, ContractChainTool, ApiUtils
import stripe
import stripe.error as error
import time
import datetime


class RpsApiClient:

    def __init__(self, host, chain_host, appKey, sign, user_id, user_login_token):
        self.host = host
        self.appKey = appKey
        self.sign = sign
        self.user_id = user_id
        self.user_login_token = user_login_token
        self.chain_client = ContractChainTool.RoxeChainClient(chain_host)
        # 获取全局的日志记录logger
        self.logger = logging.getLogger(Global.getValue(settings.logger_name))

        traceable = Global.getValue(settings.enable_trace)
        if traceable:
            for handle in self.logger.handlers:
                handle.setLevel(logging.DEBUG)

    def getRoAccountBalance(self, account, currency):
        self.logger.info(f"查询账号{account}, {currency}的资产")
        account_balance = self.chain_client.getBalanceWithRetry(account)
        currency_balance = 0
        for b in account_balance:
            print(b)
            if b.endswith(" " + currency.upper()):
                currency_balance = float(b.split(" ")[0])
                break
        return currency_balance

    def checkRoTransactionHash(self, tx_hash, pay_order_info, fee):
        self.logger.info(f"查询交易详情: {tx_hash}")
        tx_info = self.chain_client.getTransactionWithRetry(tx_hash)
        self.logger.info(tx_info)
        actions = [i["act"] for i in tx_info["traces"]]
        uni_actions = []
        for i in actions:
            if i in uni_actions:
                continue
            else:
                uni_actions.append(i)
        assert len(uni_actions) >= 1

        # 校验交易信息
        assert tx_info["traces"][0]["act"]["name"] == "transfer", f'{tx_info["traces"][0]["act"]["name"]}, transfer 不等'
        assert tx_info["traces"][0]["act"]["data"]["from"] == pay_order_info["sourceRoxeAccount"], f'{tx_info["traces"][0]["act"]["data"]["from"]}, {pay_order_info["sourceRoxeAccount"]} 不等'
        assert tx_info["traces"][0]["act"]["data"]["to"] == pay_order_info["targetRoxeAccount"], f'{tx_info["traces"][0]["act"]["data"]["to"]}, {pay_order_info["targetRoxeAccount"]} 不等'
        parse_ro_amount = ContractChainTool.parseNumberToString(pay_order_info["businessAmount"]) + " " + pay_order_info["currency"]
        assert tx_info['traces'][0]['act']['data']['quantity'] == parse_ro_amount, f"{tx_info['traces'][0]['act']['data']['quantity']}, {parse_ro_amount} 不等"

        if len(uni_actions) >= 2:
            # 校验该笔交易的手续费
            assert tx_info['traces'][1]['act']['data']['from'] == pay_order_info["sourceRoxeAccount"], f"{tx_info['traces'][1]['act']['data']['from']}，{pay_order_info['sourceRoxeAccount']} 不等"
            parse_ro_fee = ContractChainTool.parseNumberToString(fee) + " " + pay_order_info["currency"]
            tx_fee = tx_info["traces"][1]["act"]["data"]["quantity"]
            assert tx_fee == parse_ro_fee, f"{tx_fee}，{parse_ro_fee} 不等"

    def getStripeToken(self, account_info):
        stripe.api_key = "sk_test_51I8Vz7EKi5Dw1yexpiayms1wbZ04y5NmUEgPbUi3nOBxGbnKKiw1enbBFsSf3ob730Odm2nLHYoxaMZARtvZqgiy001kbgpm0I"
        bank_account = {
            "account_number": account_info["accountNumber"],
            "routing_number": account_info["routingNumber"],
            "currency": account_info["currency"],
            "account_holder_name": account_info["holder"],
            "account_holder_type": account_info["holderType"],
        }
        if "country" in account_info:
            bank_account["country"] = account_info["country"]
        res = None
        b_num = 0
        while b_num < 10:
            try:
                res = stripe.Token.create(bank_account=bank_account)
                self.logger.info(f"获取的stripe的token为: {res}")
                break
            except error.APIConnectionError:
                b_num += 1
                self.logger.info(f"获取stripe token 失败，进行第{b_num}次重试")
                time.sleep(5)
            except error.InvalidRequestError as e:
                self.logger.error(e.args)
                break
            except error.CardError as e:
                self.logger.error(e.args)
                break
        if res:
            res = res["id"]
        return res

    def bindBankAccount(self, userId, loginToken, accountInfo, appKey):
        """
        绑定银行账户, 目前绑定的是ach账户
        :param userId: 用户id
        :param loginToken: 用户登录token
        :param appKey:
        :param accountInfo: ach 银行账户信息, eg:
        {
            "accountNumber":"000123456789",
            "routingNumber":"111000025",
            "currency":"usd",
            "country":"US",
            "holder":"Jane Austen",
            "holderType":"individual",
            "bankAccountToken":"btok_1JKKy0HZ6csVB3MEbRtOe07b"
        }
        :return:
        """
        url = self.host + "/roxepay/bank/account"
        headers = {
            "userId": userId,
            "loginToken": loginToken,
            "appkey": appKey,
        }
        body = accountInfo
        res = sendPostRequest(url, body, headers).json()
        self.logger.debug("请求url: {}".format(url))
        self.logger.debug("请求headers: {}".format(headers))
        self.logger.debug("请求参数: {}".format(body))
        self.logger.info("请求结果: {}".format(res))
        return res

    def verifyBankAccount(self, userId, loginToken, accountId, verifyFirstAmount, verifySecondAmount):
        """
        银行账户验证接口, 目前是ach账户
        :param userId: 用户id
        :param loginToken: 用户登录token
        :param accountId: roxe绑定id
        :param verifyFirstAmount: 验证金额1, 测试环境为0.32
        :param verifySecondAmount: 验证金额2, 测试环境为0.45
        :return:
        """
        url = self.host + "/roxepay/bank/account/verify"
        headers = {
            "userId": userId,
            "loginToken": loginToken,
            "appkey": self.appKey,
        }
        body = {
            "id": accountId,
            "verifyFirstAmount": verifyFirstAmount,
            "verifySecondAmount": verifySecondAmount,
        }
        res = sendPostRequest(url, body, headers).json()
        self.logger.debug("请求url: {}".format(url))
        self.logger.debug("请求headers: {}".format(headers))
        self.logger.debug("请求参数: {}".format(body))
        self.logger.info("请求结果: {}".format(res))
        return res

    def queryBindBankAccount(self, sign, appkey, userId, currency, timestamp=None):
        """
        rpc查询绑定的银行账户
        :param sign: 签名验证
        :param timestamp:
        :param appkey:
        :param userId: 当前登录用户id
        :param currency: 币种
        :return:
        """
        url = self.host + "/inner/roxepay/bank/account"
        timestamp = timestamp if timestamp else int(time.time())
        headers = {
            "sign": sign,
            "timestamp": str(timestamp),
            "appkey": appkey,
            "userId": userId,
        }
        params = {"currency": currency}
        res = sendGetRequest(url, params, headers)
        self.logger.debug("请求url: {}".format(url))
        self.logger.debug("请求headers: {}".format(headers))
        self.logger.debug("请求参数: {}".format(params))
        self.logger.info("请求结果: {}".format(res.text))
        return res.json()

    def unbindBankAccount(self, sign, appkey, userId, bankAccountId, timestamp=None):
        """
        rpc解绑银行账户
        :param sign:
        :param timestamp:
        :param appkey:
        :param userId:
        :param bankAccountId:
        :return:
        """
        url = self.host + "/inner/roxepay/bank/account/" + str(bankAccountId)
        timestamp = timestamp if timestamp else int(time.time())
        headers = {
            "sign": sign,
            "timestamp": str(timestamp),
            "appkey": appkey,
            "userId": userId,
        }
        res = sendDeleteRequest(url, headers).json()
        self.logger.debug("请求url: {}".format(url))
        self.logger.debug("请求headers: {}".format(headers))
        self.logger.info("请求结果: {}".format(res))
        return res

    def queryPlaidLinkToken(self, userId, loginToken, appKey, bankAccountId):
        """
        获取plaid link token
        :param userId:
        :param loginToken:
        :param appKey:
        :param bankAccountId:
        :return:
        """
        url = self.host + "/roxepay/plaid/link/token"
        headers = {
            "userId": userId,
            "loginToken": loginToken,
            "appkey": appKey,
        }
        params = {"id": bankAccountId}
        res = sendGetRequest(url, params, headers).json()
        self.logger.debug("请求url: {}".format(url))
        self.logger.debug("请求headers: {}".format(headers))
        self.logger.debug("请求参数: {}".format(params))
        self.logger.info("请求结果: {}".format(res))
        return res

    def submitOrderPayIn(self, appkey, sign, timestamp, payOrderInfo, **kwargs):
        """
        支付下单接口
        :param appkey: 商户身份表示
        :param sign: 签名
        :param timestamp: 时间戳
        :param payOrderInfo: 常用的字段信息 eg:
        {
            "businessAmount": 10,
            "channelFeeDeductionMethod": 1,
            "businessOrderNo": "test" + str(int(time.time())),
            "businessItemName": "test",
            "sourceRoxeAccount": RPSData.user_roxe_account,
            "targetRoxeAccount": RPSData.user_roxe_account_a,
            "currency": "USD",
            "businessType": "charge",
            "country": "US",
        }
        :param kwargs: 其他可选字段
        :return:
        """
        url = self.host + "/inner/roxepay/orderin/payin"
        headers = {
            "appkey": appkey,
            "sign": sign,
            "timestamp": str(timestamp),
            # "loginToken": self.user_login_token,
        }
        body = payOrderInfo
        for k, v in kwargs.items():
            body[k] = v
        self.logger.info("开始支付订单")
        res = sendPostRequest(url, body, headers)
        self.logger.debug("请求url: {}".format(url))
        self.logger.debug("请求headers: {}".format(headers))
        self.logger.debug("请求参数: {}".format(body))
        self.logger.info("请求结果: {}".format(res.text))
        return res.json()

    def queryOrderPayInMethod(self, userId, loginToken, orderId, appKey=None, keepArg=False):
        """
        查询收银台选择支付方式接口
        :param userId: 用户的id
        :param loginToken: 用户登录的token, 可从redis中获取
        :param orderId: 用户生成的业务订单
        :param appKey:
        :param keepArg:
        :return:
        """
        url = self.host + "/roxepay/payin/methods"
        if keepArg:
            appKey = appKey
        else:
            appKey = appKey if appKey else self.appKey
        headers = {
            "userId": userId,
            "loginToken": loginToken,
            "appkey": appKey,
        }
        params = {"orderId": orderId}
        res = sendGetRequest(url, params, headers).json()
        self.logger.debug("请求url: {}".format(url))
        self.logger.debug("请求headers: {}".format(headers))
        self.logger.debug("请求参数: {}".format(params))
        self.logger.info("请求结果: {}".format(res))
        return res

    def submitOrderPayInMethod(self, userId, loginToken, appKey, payOrderId, currency, payMethod, serviceChannel, channelFee, payableAmount, lostKey=None, **kwargs):
        """
        收银台选择支付方式接口
        :param userId:
        :param loginToken:
        :param appKey:
        :param payOrderId: 支付订单id
        :param currency: 支付的币种
        :param payMethod: 支付方式ach、card、wire、banlance
        :param serviceChannel: 支付通道
        :param channelFee: 通道手续费
        :param payableAmount: 用户应付金额
        :param lostKey: 去除的参数
        :param kwargs: 其他字段，不同的支付方式要求的字段不一致
        :return:
        """
        url = self.host + "/roxepay/orderin/pay"
        headers = {
            "userId": userId,
            "loginToken": loginToken,
            "appkey": appKey,
        }
        body = {
            "id": payOrderId,
            "currency": currency,
            "payMethod": payMethod,
            "serviceChannel": serviceChannel,
            "channelFee": channelFee,
            "payableAmount": payableAmount
        }
        for k, v in kwargs.items():
            body[k] = v
        if lostKey:
            if isinstance(lostKey, str):
                body.pop(lostKey)
        self.logger.info("选择支付方式")
        res = sendPostRequest(url, body, headers).json()
        self.logger.debug("请求url: {}".format(url))
        self.logger.debug("请求headers: {}".format(headers))
        self.logger.debug("请求参数: {}".format(body))
        self.logger.info("请求结果: {}".format(res))
        return res

    def queryPaymentOrder(self, appKey, sign, timestamp, businessOrderNo):
        url = self.host + "/inner/roxepay/orderin/" + str(businessOrderNo)
        headers = {
            "sign": sign,
            "timestamp": str(timestamp),
            "appkey": appKey,
            # "loginToken": self.user_login_token,
        }
        self.logger.info(f"查询订单: {businessOrderNo}")
        res = sendGetRequest(url, None, headers).json()
        self.logger.debug("请求url: {}".format(url))
        self.logger.debug("请求headers: {}".format(headers))
        self.logger.info("请求结果: {}".format(res))
        return res

    @classmethod
    def calChannelFee(cls, db_fee_config, amount, channel):
        if channel == "STRIPE":
            # 按全新的费用规则计算
            fee = amount * db_fee_config["roxeRate"]
            if "roxeAdd" in db_fee_config.keys():
                fee += db_fee_config["roxeAdd"]
            if "max" in db_fee_config.keys():
                fee = db_fee_config["max"] if fee > db_fee_config["max"] else fee
            if "min" in db_fee_config.keys():
                fee = db_fee_config["min"] if fee < db_fee_config["min"] else fee
            # if "add" in db_fee_config.keys():
            #     t_amount = amount + db_fee_config["add"]
            # else:
            #     t_amount = amount
            # fee = t_amount / (1 - db_fee_config["rate"]) - amount
        else:
            if "fixed" in db_fee_config.keys():
                fee = db_fee_config["fixed"]
            elif "rate" in db_fee_config.keys():
                fee = amount * db_fee_config["rate"]
                if "add" in db_fee_config.keys():
                    fee += db_fee_config["add"]
                if "max" in db_fee_config.keys():
                    fee = db_fee_config["max"] if fee > db_fee_config["max"] else fee
                if "min" in db_fee_config.keys():
                    fee = db_fee_config["min"] if fee < db_fee_config["min"] else fee
            elif "max" in db_fee_config.keys():
                fee = amount * db_fee_config["rate"]
            else:
                fee = 0
        return fee

    @classmethod
    def calAllowanceFee(cls, case_obj, fee, method_type):
        sql = f"select * from roxe_pay_in_allowance where pay_method='{method_type}'"
        rps_allowance_fee_db = case_obj.mysql.exec_sql_query(sql)
        res_fee = 0
        if rps_allowance_fee_db:
            cur_time = datetime.datetime.utcnow().timestamp()
            if cur_time < rps_allowance_fee_db[0]["startDate"].timestamp() or (rps_allowance_fee_db[0]["endDate"] and cur_time > rps_allowance_fee_db[0]["endDate"].timestamp()):
                res_fee = 0
            else:
                coupon_id = rps_allowance_fee_db[0]["couponId"]
                coupon_sql = f"select * from roxe_coupon.coupon_config where coupon_id='{coupon_id}'"
                coupon_fee = case_obj.mysql.exec_sql_query(coupon_sql)
                res_fee = fee * float(rps_allowance_fee_db[0]["rate"])
                if coupon_fee[0]["maxAmount"]:
                    res_fee = res_fee if res_fee < coupon_fee[0]["maxAmount"] else coupon_fee[0]["maxAmount"]
        return ApiUtils.parseNumberDecimal(res_fee)

    def submitAchPayOrder(self, target_account, businessAmount, currency="USD", expect_pay_success=True, account_info=None, businessOrderNo=None, caseObj=None):
        if account_info:
            accounts = self.queryBindBankAccount(self.sign, self.appKey, self.user_id, account_info["currency"].upper())
            if not accounts:
                self.bindAndVerifyAchAccount(account_info)
        businessOrderNo = businessOrderNo if businessOrderNo else "test" + str(int(time.time() * 1000))
        pay_order_info = {
            "businessAmount": businessAmount,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": businessOrderNo,
            "businessItemName": "test",
            "sourceRoxeAccount": "",
            "targetRoxeAccount": target_account,
            "currency": currency,
            "businessType": "deposit",
            "country": "US",
        }
        # 查询钱包余额
        pay_order = self.submitOrderPayIn(self.appKey, self.sign, int(time.time()), pay_order_info)
        assert isinstance(pay_order, int)
        # 查询支付方式
        methods = self.queryOrderPayInMethod(self.user_id, self.user_login_token, pay_order)
        if caseObj:
            caseObj.checkCodeAndMessage(methods)
            caseObj.checkPaymentMethod(methods["data"], pay_order_info["businessAmount"], self.user_id)

        # 选择支付方式进行支付
        select_method = [i for i in methods["data"] if i["type"] == "ach"][0]
        self.logger.info("选择的支付方式: {}".format(select_method))
        ach_account = {
            "allowanceFee": select_method["currencyList"][0]["allowanceFee"],
            "showFee": select_method["currencyList"][0]["showFee"],
            "payBankAccountId": select_method["bankAccounts"][0]["id"],
            "authConsent": "1212",
            "transactionSpecificDetails": "232",
            "revocationTip": "123",
            "transactionReceiptTip": "312312",
        }
        payment_amount = pay_order_info["businessAmount"] + select_method["currencyList"][0]["showFee"]
        if ApiUtils.parseNumberDecimal(payment_amount) < payment_amount:
            payment_amount = ApiUtils.parseNumberDecimal(payment_amount, isUp=True)
        elif ApiUtils.parseNumberDecimal(payment_amount) > payment_amount:
            payment_amount = ApiUtils.parseNumberDecimal(payment_amount)
        submit_order = self.submitOrderPayInMethod(self.user_id, self.user_login_token, self.appKey, pay_order,
                                                   pay_order_info["currency"], select_method["type"],
                                                   select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
                                                   payment_amount,
                                                   **ach_account)
        assert submit_order["data"] is not None
        coupon_code = submit_order["data"]["couponCode"]  # 优惠券code
        # 查询订单状态
        b_time = time.time()
        query_order = None
        while time.time() - b_time < 600:
            query_order = self.queryPaymentOrder(self.appKey, self.sign, int(time.time()), pay_order_info["businessOrderNo"])
            if expect_pay_success:
                if "-" in query_order["serviceChannelOrderId"]:
                    self.logger.info("得到支付通道回调")
                    break
            else:
                break
            time.sleep(10)
        return query_order, coupon_code

    def selectAchMethodToPayOrder(self, pay_order, businessAmount, currency="USD", expect_pay_success=True, account_info=None, businessOrderNo=None, caseObj=None):
        if account_info:
            accounts = self.queryBindBankAccount(self.sign, self.appKey, self.user_id, account_info["currency"].upper())
            if not accounts:
                self.bindAndVerifyAchAccount(account_info)
        # 查询支付方式
        methods = self.queryOrderPayInMethod(self.user_id, self.user_login_token, pay_order)
        if caseObj:
            caseObj.checkCodeAndMessage(methods)

        # 选择支付方式进行支付
        select_method = [i for i in methods["data"] if i["type"] == "ach"][0]
        self.logger.info("选择的支付方式: {}".format(select_method))
        ach_account = {
            "allowanceFee": select_method["currencyList"][0]["allowanceFee"],
            "showFee": select_method["currencyList"][0]["showFee"],
            "payBankAccountId": select_method["bankAccounts"][0]["id"],
            "authConsent": "1212",
            "transactionSpecificDetails": "232",
            "revocationTip": "123",
            "transactionReceiptTip": "312312",
        }
        payment_amount = businessAmount + select_method["currencyList"][0]["showFee"]
        if ApiUtils.parseNumberDecimal(payment_amount) < payment_amount:
            payment_amount = ApiUtils.parseNumberDecimal(payment_amount, isUp=True)
        elif ApiUtils.parseNumberDecimal(payment_amount) > payment_amount:
            payment_amount = ApiUtils.parseNumberDecimal(payment_amount)
        submit_order = self.submitOrderPayInMethod(self.user_id, self.user_login_token, self.appKey, pay_order,
                                                   currency, select_method["type"],
                                                   select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
                                                   payment_amount,
                                                   **ach_account)
        assert submit_order["data"] is not None
        coupon_code = submit_order["data"]["couponCode"]  # 优惠券code
        # 查询订单状态
        b_time = time.time()
        query_order = None
        while time.time() - b_time < 60:
            query_order = self.queryPaymentOrder(self.appKey, self.sign, int(time.time()), businessOrderNo)
            if expect_pay_success:
                if "-" in query_order["serviceChannelOrderId"]:
                    self.logger.info("得到支付通道回调")
                    break
            else:
                break
            time.sleep(10)
        return query_order, coupon_code

    def submitPayOrderTransferToRoxeAccount(self, source_account, target_account, businessAmount, currency="USD", businessType="withdrawal", expect_pay_success=True, businessOrderNo=None):
        if businessOrderNo is None:
            businessOrderNo = "test" + str(int(time.time()))
        pay_order_info = {
            "businessAmount": businessAmount,
            "channelFeeDeductionMethod": 2,
            "businessOrderNo": businessOrderNo,
            "businessItemName": "test",
            "sourceRoxeAccount": source_account,
            "targetRoxeAccount": target_account,
            "currency": currency,
            "businessType": businessType,
            "country": "US",
        }
        # 支付下单
        pay_order = self.submitOrderPayIn(self.appKey, self.sign, int(time.time()), pay_order_info)
        # pay_order = 26420871744716800
        assert isinstance(pay_order, int)
        # 查询支付方式
        methods = self.queryOrderPayInMethod(self.user_id, self.user_login_token, pay_order)

        # 选择支付方式进行支付
        select_method = [i for i in methods["data"] if i["type"] == "balance"][0]
        self.logger.info("选择的支付方式: {}".format(select_method))
        fees = {
            "allowanceFee": select_method["currencyList"][0]["allowanceFee"],
            "showFee": select_method["currencyList"][0]["showFee"],
        }
        payment_amount = pay_order_info["businessAmount"] + select_method["currencyList"][0]["showFee"]
        self.logger.info(f"得到应付金额: {payment_amount}")
        if ApiUtils.parseNumberDecimal(payment_amount) < payment_amount:
            payment_amount = ApiUtils.parseNumberDecimal(payment_amount, isUp=True)
        submit_order = self.submitOrderPayInMethod(self.user_id, self.user_login_token, self.appKey, pay_order,
                                                   pay_order_info["currency"], select_method["type"],
                                                   select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
                                                   payment_amount, **fees)
        assert submit_order["data"] is not None
        # 查询订单状态
        b_time = time.time()
        query_order = None
        time_out = 120
        flag = False
        while time.time() - b_time < time_out:
            query_order = self.queryPaymentOrder(self.appKey, self.sign, int(time.time()), pay_order_info["businessOrderNo"])
            if not expect_pay_success:
                break
            if query_order["serviceChannelOrderId"] != "":
                flag = True
                break
            time.sleep(time_out/10)
        if flag:
            self.logger.info("支付订单下单成功")
        else:
            self.logger.info("支付订单下单后通道订单id返回为空")
        return query_order

    def selectWalletToPayOrder(self, pay_order, businessOrderNo, businessAmount, currency="USD", expect_pay_success=True):
        # 查询支付方式
        methods = self.queryOrderPayInMethod(self.user_id, self.user_login_token, pay_order)

        # 选择支付方式进行支付
        select_method = [i for i in methods["data"] if i["type"] == "balance"][0]
        self.logger.info("选择的支付方式: {}".format(select_method))
        fees = {
            "allowanceFee": select_method["currencyList"][0]["allowanceFee"],
            "showFee": select_method["currencyList"][0]["showFee"],
        }
        payment_amount = businessAmount + select_method["currencyList"][0]["showFee"]
        self.logger.info(f"得到应付金额: {payment_amount}")
        if ApiUtils.parseNumberDecimal(payment_amount) < payment_amount:
            payment_amount = ApiUtils.parseNumberDecimal(payment_amount, isUp=True)
        submit_order = self.submitOrderPayInMethod(self.user_id, self.user_login_token, self.appKey, pay_order,
                                                   currency, select_method["type"],
                                                   select_method["serviceChannel"], select_method["currencyList"][0]["fee"],
                                                   payment_amount, **fees)
        assert submit_order["data"] is not None
        # 查询订单状态
        b_time = time.time()
        query_order = None
        time_out = 60
        flag = False
        while time.time() - b_time < time_out:
            query_order = self.queryPaymentOrder(self.appKey, self.sign, int(time.time()), businessOrderNo)
            if not expect_pay_success:
                break
            if query_order["serviceChannelOrderId"] != "":
                flag = True
                break
            time.sleep(time_out/10)
        if flag:
            self.logger.info("支付订单下单成功")
        else:
            self.logger.info("支付订单下单后通道订单id返回为空")
        return query_order

    def queryKycInfoFromDB(self, case_object, user_id):
        """
        从数据库中查询kyc信息
        :param case_object:
        :param user_id:
        :return:
        """
        sql = "select * from `roxe_kyc`.user_kyc where user_id='{}'".format(user_id)
        db_res = case_object.mysql.exec_sql_query(sql)
        self.logger.info(f"{user_id}的kyc信息: {db_res}")
        return db_res

    def deleteAchAccountFromDB(self, case_object, user_id=None):
        if user_id:
            sql = "delete from `roxe_pay_in_out`.roxe_pay_in_user_bank_account where roxe_user_id='{}';".format(user_id)
        else:
            # 慎用
            sql = "delete from `roxe_pay_in_out`.roxe_pay_in_user_bank_account where roxe_user_id<>'0';"
        case_object.mysql.exec_sql_query(sql)
        db_res = case_object.mysql.exec_sql_query("select * from `roxe_pay_in_out`.roxe_pay_in_user_bank_account")
        self.logger.info(f"清理数据库绑定的ach账户后: {len(db_res)}")

    def bindAndVerifyAchAccount(self, account_info):
        account_info["bankAccountToken"] = self.getStripeToken(account_info)
        bind_res = self.bindBankAccount(self.user_id, self.user_login_token, account_info, self.appKey)
        assert bind_res["data"] is not None, f"{self.user_id}绑定ach账户结果: {bind_res}"
        time.sleep(1)
        accounts = self.queryBindBankAccount(self.sign, self.appKey, self.user_id, account_info["currency"].upper())
        account_id = accounts[0]["id"]
        verify_info = self.verifyBankAccount(self.user_id, self.user_login_token, account_id, 0.32, 0.45)
        assert verify_info["data"] is True, f"{self.user_id}验证ach账户结果: {verify_info}"
        return account_id
