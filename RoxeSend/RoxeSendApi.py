# coding=utf-8
# author: Li MingLei
# date: 2021-09-26
"""
RoxeSend系统各api的实现
"""
import logging
from roxe_libs.Global import Global
from roxe_libs.baseApi import *
from roxe_libs import settings
from roxe_libs.ContractChainTool import RoxeChainClient


class RoxeSendApiClient:

    def __init__(self, host, chain_host, user_id, user_login_token):
        self.host = host
        self.user_id = user_id
        self.user_login_token = user_login_token
        self.logger = logging.getLogger(Global.getValue(settings.logger_name))

        if chain_host:
            self.chain_client = RoxeChainClient(chain_host)

        traceable = Global.getValue(settings.enable_trace)
        if traceable:
            for handle in self.logger.handlers:
                handle.setLevel(logging.DEBUG)

    def getRoAccountBalance(self, account, currency):
        self.logger.info(f"查询账号{account}, {currency}的资产")
        account_balance = self.chain_client.getBalance(account)
        currency_balance = 0
        for b in account_balance:
            if b.endswith(" " + currency.upper()):
                currency_balance = float(b.split(" ")[0])
                break
        return currency_balance

    def listCurrency(self, token=None, pop_header=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        if pop_header:
            headers.pop(pop_header)
        self.logger.info("获取币种列表")
        res = sendGetRequest(self.host + "/roxe-app/common/listCurrency", headers=headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def listFee(self, token=None, pop_header=None):
        """已废弃"""
        token = token if token else self.user_login_token
        headers = {"token": token}
        if pop_header:
            headers.pop(pop_header)
        self.logger.info("获取币种手续费列表")
        res = sendGetRequest(self.host + "/roxe-app/common/listFee", headers=headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def getExchangeRate(self, from_currency, to_currency, b_type, ensure_side, from_amount="", to_amount="", from_country="US", to_country="US", outer_node_roxe="", token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        params = {
            "from": from_currency,
            "fromAmount": from_amount,
            "fromCountry": from_country,
            "to": to_currency,
            "toAmount": to_amount,
            "toCountry": to_country,
            "type": b_type,
            "ensureSide": ensure_side,
            "outerNodeRoxe": outer_node_roxe,
        }
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            params.pop(pop_param)
        self.logger.info("获取币种汇率")
        res = sendGetRequest(self.host + "/roxe-app/common/exchangeRate", params, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {params}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json(), params

    def getOuterMethod(self, currency, outer_node="", token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        params = {
            "outerNodeRxoe": outer_node,
            "currency": currency
        }
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            params.pop(pop_param)
        self.logger.info("获取出金方式")
        res = sendGetRequest(self.host + "/roxe-app/receiver/get-payout-method", params, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {params}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def getOuterFields(self, currency, out_method="BANK", outer_node="", token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        params = {
            "outerNodeRxoe": outer_node,
            "payOutMethod": out_method,
            "currency": currency
        }
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            params.pop(pop_param)
        self.logger.info("获取出金必填字段")
        res = sendGetRequest(self.host + "/roxe-app/receiver/get-outer-fields", params, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {params}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def checkOuterFields(self, currency, outer_info, outer_node="", token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        body = {
            "outerNodeRoxe": outer_node,
            "outerInfo": outer_info,
            "currency": currency
        }
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            body.pop(pop_param)
        self.logger.info("校验出金必填字段")
        res = sendPostRequest(self.host + "/roxe-app/receiver/check-outer-fields", body, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {body}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def listReceiverAccount(self, currency, b_type="BankAccount", token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        params = {
            "type": b_type,
            "currency": currency
        }
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            params.pop(pop_param)
        self.logger.info("列出所有收款账户")
        res = sendGetRequest(self.host + "/roxe-app/receiver/list", params, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {params}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def bindReceiverAccount(self, currency, bank_account, outer_node="", b_type="BankAccount", token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        body = {
            "outerNodeCode": outer_node,
            "bankAccount": bank_account,
            "type": b_type,
            "currency": currency
        }
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            body.pop(pop_param)
        self.logger.info("绑定收款账户")
        res = sendPostRequest(self.host + "/roxe-app/receiver/bind", body, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {body}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json(), body

    def deleteReceiverAccount(self, account_id, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        body = {"accountId": account_id}
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            body.pop(pop_param)
        self.logger.info("删除账户")
        res = sendPostRequest(self.host + "/roxe-app/receiver/delete", body, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {body}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def listBalance(self, token=None, pop_header=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        if pop_header:
            headers.pop(pop_header)
        self.logger.info("查询资产列表")
        res = sendGetRequest(self.host + "/roxe-app/wallet/listBalance", None, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def listCurrencyBalance(self, currency, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        params = {"currency": currency}
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            params.pop(pop_param)
        self.logger.info("查询币种资产")
        res = sendGetRequest(self.host + "/roxe-app/wallet/balance", params, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {params}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def deposit(self, currency, amount, country="US", token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        body = {"currency": currency, "amount": amount, "country": country}
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            body.pop(pop_param)
        self.logger.info("充值")
        res = sendPostRequest(self.host + "/roxe-app/wallet/deposit", body, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {body}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json(), body

    def withdraw(self, currency, amount, receive_account_id, outer_node, country="US", token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        body = {
            "currency": currency,
            "amount": amount,
            "receiveAccountId": receive_account_id,
            "outerNodeRoxe": outer_node,
            "country": country
        }
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            body.pop(pop_param)
        self.logger.info("提现")
        res = sendPostRequest(self.host + "/roxe-app/wallet/withdraw", body, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {body}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def addCurrency(self, currency, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        body = {"currency": currency}
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            body.pop(pop_param)
        self.logger.info("提现")
        res = sendPostRequest(self.host + "/roxe-app/wallet/addCurrency", body, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {body}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def sendToRoxeAccount(self, to_ro_id, exchange_rate, send_currency, send_amount, re_currency, re_amount, side="", scope=2, send_country="US", re_country="US", outer_node="", note="", token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        body = {
            "counterpartyRxId": to_ro_id,
            "exchangeRate": exchange_rate,
            "sendCurrency": send_currency,
            "sendAmount": send_amount,
            "receiveAmount": re_amount,
            "receiveCurrency": re_currency,
            "ensureSideEnum": side,
            "scope": scope,
            "note": note,
            "sendCountry": send_country,
            "receiveCountry": re_country,
            "outer_node": outer_node
        }
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            body.pop(pop_param)
        self.logger.info("转账到Ro账户")
        res = sendPostRequest(self.host + "/roxe-app/transaction/sendToRoxeAccount", body, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {body}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json(), body

    def sendToBankAccount(self, to_account_id, exchange_rate, send_currency, send_amount, re_currency, re_amount, note="", token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        body = {
            "counterpartyAccountId": to_account_id,
            "exchangeRate": exchange_rate,
            "sendCurrency": send_currency,
            "sendAmount": send_amount,
            "receiveAmount": re_amount,
            "receiveCurrency": re_currency,
            # "ensureSideEnum": side,
            # "scope": scope,
            "note": note,
            # "sendCountry": send_country,
            # "receiveCountry": re_country,
            # "outer_node": outer_node
        }
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            body.pop(pop_param)
        self.logger.info("转账到Ro账户")
        res = sendPostRequest(self.host + "/roxe-app/transaction/sendToBankAccount", body, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {body}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def request(self, to_user_id, re_currency, re_amount, note="", token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        body = {
            "counterpartyUserId": to_user_id,
            "receiveAmount": re_amount,
            "receiveCurrency": re_currency,
            "note": note
        }
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            body.pop(pop_param)
        self.logger.info("发起request")
        res = sendPostRequest(self.host + "/roxe-app/transaction/request", body, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {body}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json(), body

    def payRequest(self, tx_id, to_ro_id, exchange_rate, send_currency, send_amount, re_currency, re_amount, scope=2, note="", token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        body = {
            "transactionId": tx_id,
            "counterpartyRxId": to_ro_id,
            "sendCurrency": send_currency,
            "sendAmount": send_amount,
            "receiveAmount": re_amount,
            "receiveCurrency": re_currency,
            "exchangeRate": exchange_rate,
            "scope": scope,
            "note": note
        }
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            body.pop(pop_param)
        self.logger.info("向request进行支付")
        res = sendPostRequest(self.host + "/roxe-app/transaction/request/send", body, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {body}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json(), body

    def declineRequest(self, order_id, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        body = {"orderId": order_id}
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            body.pop(pop_param)
        self.logger.info("拒绝向request支付")
        res = sendPostRequest(self.host + "/roxe-app/transaction/request/decline", body, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {body}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def cancelRequest(self, tx_id, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        body = {"transactionId": tx_id}
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            body.pop(pop_param)
        self.logger.info("取消request请求")
        res = sendPostRequest(self.host + "/roxe-app/transaction/request/cancel", body, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {body}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def cancelTransaction(self, tx_id, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        body = {"transactionId": tx_id}
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            body.pop(pop_param)
        self.logger.info("取消交易")
        res = sendPostRequest(self.host + "/roxe-app/transaction/cancel", body, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {body}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def confirmPayMethod(self, pay_id, tx_id, pay_type, channel_fee, bindAndPay=0, third_bank_account_id="", auth_consent="", tx_detail="", revocation_tip="", token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        body = {
            "paymentMethodId": pay_id,
            "transactionId": tx_id,
            "payType": pay_type,
            "channelFee": channel_fee,
            "bindAndPay": bindAndPay,
            "thirdBankAccountID": third_bank_account_id,
            "grant": {
                "authConsent": auth_consent,
                "transactionSpecificDetails": tx_detail,
                "revocationTip": revocation_tip,
            }
        }
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            if pop_param in body["grant"]:
                body["grant"].pop(pop_param)
            else:
                body.pop(pop_param)
        self.logger.info("确认支付方式")
        res = sendPostRequest(self.host + "/roxe-app/transaction/confirmPay", body, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {body}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def getAccountList(self, currency, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        params = {"currency": currency}
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            params.pop(pop_param)
        self.logger.info("查询绑定的ach账户")
        res = sendGetRequest(self.host + "/roxe-app/paymenthannel/getAccountList", params, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {params}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def deleteAccountById(self, del_id, token=None, pop_header=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        if pop_header:
            headers.pop(pop_header)
        self.logger.info("删除绑定的ach账户")
        res = sendDeleteRequest(self.host + "/roxe-app/paymenthannel/delAccountById/" + str(del_id), headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def kycVerification(self, currency, amount, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        params = {"currency": currency, "amount": amount}
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            params.pop(pop_param)
        self.logger.info("校验金额是否达到KYC认证上限")
        res = sendGetRequest(self.host + "/roxe-app/kyc/kycVerification", params, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {params}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def getTransactionHistory(self, currency="", b_type="", begin="", end="", to_user_id="", key_word="", page_number=1, page_size=20, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        params = {
            "keyword": key_word,
            "type": b_type,
            "currency": currency,
            "counterpartyId": to_user_id,
            "begin": begin,
            "end": end,
            "pageNumber": page_number,
            "pageSize": page_size,
        }
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            params.pop(pop_param)
        self.logger.info("查询交易历史")
        res = sendGetRequest(self.host + "/roxe-app/transaction/history", params, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {params}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json(), params

    def getTransactionDetail(self, tx_id, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        params = {"transactionId": tx_id}
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            params.pop(pop_param)
        self.logger.info("查询交易详情")
        res = sendGetRequest(self.host + "/roxe-app/transaction/detail", params, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {params}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def updateUserReadOrder(self, user_id, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        params = {"friendId": user_id}
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            params.pop(pop_param)
        self.logger.info("用户读取未读订单信息")
        res = sendGetRequest(self.host + "/roxe-app/transaction/updateUserReadOrder", params, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {params}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def getUserRecentContact(self, p_num=1, p_size=5, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        params = {"pageNumber": p_num, "pageSize": p_size}
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            params.pop(pop_param)
        self.logger.info("查询交易详情")
        res = sendGetRequest(self.host + "/roxe-app/transaction/getUserRecentContact", params, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {params}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def querySendAmount(self, currency, amount, mode=1, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        params = {"currency": currency, "amount": amount, "mode": mode}
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            params.pop(pop_param)
        self.logger.info("查询汇出的金额是否达到上限")
        res = sendGetRequest(self.host + "/roxe-app/statistics/sendAmount", params, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {params}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def queryRecentBankAccounts(self, token=None, pop_header=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        if pop_header:
            headers.pop(pop_header)
        self.logger.info("查询最近交易的银行卡")
        res = sendGetRequest(self.host + "/roxe-app/contact/recentBankAccounts", None, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def listNotification(self, token=None, pop_header=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        if pop_header:
            headers.pop(pop_header)
        self.logger.info("交易通知列表")
        res = sendGetRequest(self.host + "/roxe-app/notification/list", None, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def getOrderShareList(self, o_type=1, scope=1, user_id=None, p_num=1, p_size=20, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        params = {
            "pageNumber": p_num,
            "pageSize": p_size,
            "type": o_type,
            "scope": scope,
            "userID": user_id,
        }
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            params.pop(pop_param)
        self.logger.info("查询订单分享list")
        res = sendGetRequest(self.host + "/roxe-app/orderShare/getOrderShareList", params, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {params}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json(), params

    def getOrderShareTransactionId(self, order_id, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        params = {"orderId": order_id}
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            params.pop(pop_param)
        self.logger.info("根据分享的订单id查询交易详情")
        res = sendGetRequest(self.host + "/roxe-app/orderShare/getTransactionId", params, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {params}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def getOrderComment(self, order_id, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        params = {"orderId": order_id}
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            params.pop(pop_param)
        self.logger.info("根据分享的订单id查询评论")
        res = sendGetRequest(self.host + "/roxe-app/comment/findCommentList", params, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {params}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def postComment(self, order_id, comment, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        body = {"orderId": order_id, "content": comment}
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            body.pop(pop_param)
        self.logger.info("发表评论")
        res = sendPostRequest(self.host + "/roxe-app/comment/publishComment", body, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {body}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def deleteComment(self, order_id, user_id, token=None, pop_header=None):
        token = token if token else self.user_login_token
        headers = {"token": token, "userId": user_id}
        if pop_header:
            headers.pop(pop_header)
        self.logger.info("删除评论")
        res = sendDeleteRequest(self.host + "/roxe-app/comment/delComment/" + order_id, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def getOrderSharePraise(self, order_id, p_num=1, p_size=20, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        params = {
            "pageNumber": p_num,
            "pageSize": p_size,
            "orderId": order_id
        }
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            params.pop(pop_param)
        self.logger.info("获取当前订单的点赞list")
        res = sendGetRequest(self.host + "/roxe-app/praise/praiseDetailPage", params, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {params}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def clickPraise(self, order_id, user_name, status, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        body = {"orderId": order_id, "userName": user_name, "status": status}
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            body.pop(pop_param)
        self.logger.info("点赞")
        res = sendPostRequest(self.host + "/roxe-app/praise/clickPraise", body, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {body}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def deleteReceiverAccountFromDB(self, case_obj, account_id=None, user_id=None):
        user_id = user_id if user_id else self.user_id
        sql = f"update ro_receive_account set is_delete=1 where user_id='{user_id}' and account_type='BankAccount'"
        if account_id:
            sql += f" and account_id='{account_id}'"

        case_obj.mysql.exec_sql_query(sql)

    def calKycLimitAmount(self, case_obj, user_id, user_token):
        kyc_level = case_obj.kyc_client.getKycLevel(token=user_token)["data"]
        daily_amount = case_obj.redis.getInfoFromKey(f"Ro:Send:Daily:Amount:{user_id}")
        ninety_day_amount = case_obj.redis.getInfoFromKey(f"Ro:Send:NinetyDay:Amount:{user_id}")
        ninety_day_ttl = case_obj.redis.redisConn.ttl(f"Ro:Send:NinetyDay:Amount:{user_id}")
        left_day = ninety_day_ttl // (24 * 3600)
        daily_amount = daily_amount if daily_amount else 0
        ninety_day_amount = ninety_day_amount if ninety_day_amount else 0
        self.logger.info(f"查询到的交易金额: Daily {daily_amount}, Weekly {ninety_day_amount}")
        daily_limit, ninety_day_limit = 0, 0
        if kyc_level == "L2":
            daily_limit = 2500
            ninety_day_limit = 50000

        if kyc_level == "L3":
            daily_limit = 10000
            ninety_day_limit = 50000

        if ninety_day_amount > 0:
            daily_limit = daily_limit - daily_amount
            ninety_day_limit = ninety_day_limit - ninety_day_amount
        self.logger.info(f"计算得到的交易限额: 24h限额: {daily_limit}, 90天限额: {ninety_day_limit}, 90天期限剩余: {left_day}天")
        return daily_limit, ninety_day_limit, left_day

    # 礼品卡相关接口

    def getGiftCardList(self, key_word="", p_num=1, p_size=20, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        params = {
            "pageNumber": p_num,
            "pageSize": p_size,
            "keyword": key_word
        }
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            params.pop(pop_param)
        self.logger.info("查询礼品卡列表")
        res = sendGetRequest(self.host + "/roxe-app/gift-card/list", params, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {params}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def getGiftCardDetail(self, store_id, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        params = {
            "storeId": store_id
        }
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            params.pop(pop_param)
        self.logger.info("查询礼品卡的详情")
        res = sendGetRequest(self.host + "/roxe-app/gift-card/detail", params, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {params}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def getMerchantStoreList(self, store_id, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        params = {
            "storeId": store_id
        }
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            params.pop(pop_param)
        self.logger.info("查询商户的店铺列表")
        res = sendGetRequest(self.host + "/roxe-app/gift-card/shop-list-by-storeId", params, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {params}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def getMerchantInfoByQRCodes(self, qrcodeInfo, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        params = {
            "qrcodeInfo": qrcodeInfo
        }
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            params.pop(pop_param)
        self.logger.info("根据二维码code获取商户信息")
        res = sendGetRequest(self.host + "/roxe-app/gitCardOrder/getMerchantInfoByQRCodes", params, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {params}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def listGiftBalance(self, token=None, pop_header=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        if pop_header:
            headers.pop(pop_header)
        self.logger.info("钱包礼品卡列表")
        res = sendGetRequest(self.host + "/roxe-app/gift-wallet/listGiftBalance", None, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def getGiftOrderHistoryList(self, currency, p_num=1, p_size=20, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        params = {
            "currency": currency,
            "pageNumber": p_num,
            "pageSize": p_size,
        }
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            params.pop(pop_param)
        self.logger.info("根据用户及币种获取礼品卡交易历史")
        res = sendGetRequest(self.host + "/roxe-app/gitCardOrder/getGiftOrderListByUserIdAndCurrency", params, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {params}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def giftBalance(self, currency, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        params = {
            "currency": currency
        }
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            params.pop(pop_param)
        self.logger.info("查询礼品卡单币种资产")
        res = sendGetRequest(self.host + "/roxe-app/gift-wallet/giftBalance", params, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {params}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def createPurchaseOrder(self, batchId, branchId, merchantId, receiveCurrency, receiveAmount, sendAmount, sendCurrency, roxeId, scope, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        body = {
            "batchId": batchId,
            "branchId": branchId,
            "merchantId": merchantId,
            "receiveCurrency": receiveCurrency,
            "receiveAmount": receiveAmount,
            "sendAmount": sendAmount,
            "sendCurrency": sendCurrency,
            "roxeId": roxeId,
            "scope": scope,
        }
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            body.pop(pop_param)
        self.logger.info("创建礼品卡购买订单")
        res = sendPostRequest(self.host + "/roxe-app/gitCardOrder/createPurchaseOrder", body, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {body}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json(), body

    def createConsumptionOrder(self, roxeId, currency, amount, qrcodeInfo, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        body = {
            "currency": currency,
            "amount": amount,
            "roxeId": roxeId,
            "qrcodeInfo": qrcodeInfo
        }
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            body.pop(pop_param)
        self.logger.info("创建礼品卡消费订单")
        res = sendPostRequest(self.host + "/roxe-app/gitCardOrder/createConsumptionOrder", body, headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {body}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json(), body

    def openCheckOutAndSelectCard(self, rps_id, user_id=None, token=None):
        from .checkOut import CheckOut
        import os
        user_id = user_id if user_id else self.user_id
        token = token if token else self.user_login_token
        url = f"https://test-checkout.roxe.io/#/index?userId={user_id}&loginToken={token}&transactionId={rps_id}&appKey=adfasdas"
        c_page = CheckOut()
        c_page.accessWebsite(url)
        c_page.selectCard()
