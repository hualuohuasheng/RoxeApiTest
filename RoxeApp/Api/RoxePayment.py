# -*- coding: utf-8 -*-
# author: liminglei
# date: 2021-06-25

import requests
import redis
# import jwt
import json
import time


class RedisClient:

    def __init__(self, redisHost, redisPWD, db=0, redisPort=6379):
        self.redisHost = redisHost
        self.redisPWD = redisPWD
        self.redisConn = redis.Redis(self.redisHost, redisPort, password=self.redisPWD, db=db)

    def getInfoFromKey(self, key, hashKey=None):
        # res = self.redisConn.get(key)
        # print(res)
        try:
            res = self.redisConn.get(key)
        except redis.exceptions.ResponseError:
            res = self.redisConn.hget(key, hashKey)
        if res:
            # return json.loads(res.decode("utf-8"))
            try:
                return json.loads(res.decode("utf-8"))
            except json.decoder.JSONDecodeError:
                return res.decode("utf-8")


class RoxePaymentApi:

    def __init__(self, url, redisHost, redisPWD):
        self.host = url
        self.redisClient = RedisClient(redisHost, redisPWD, 0)
        self.redisClient2 = RedisClient(redisHost, redisPWD, 2)

    def getAccountList(self, userId, currency):
        """
        获取订单分享list
        :param userId: 请求发起方的userId
        :param currency: 币种
        :return:
        """
        loginToken = self.getLoginTokenFromRedis(userId)
        headers = {"loginToken": loginToken, "userId": userId}
        data = {
            "currency": currency
        }
        res = requests.get(self.host + "/paymenthannel/getAccountList", data, headers=headers)
        print(res.json())

    def delAccount(self, userId, id):
        loginToken = self.getLoginTokenFromRedis(userId)
        headers = {"loginToken": loginToken, "userId": userId}
        res = requests.delete(self.host + "/paymenthannel/delAccountById/{}".format(id), headers=headers)
        print(res.json())

    def listCurrency(self):
        """
        :return: 币种列表, 直接获取数据库配置信息
        """

        res = requests.get(self.host + "/common/listCurrency")
        return res.json()

    def listFee(self):
        """
        :return: 币种手续费列表
        """
        res = requests.get(self.host + "/common/listFee")
        return res.json()

    def exchangeRate(self, fromCurrency, toCurrency, fromAmount, toAmount=''):
        """
        :param fromCurrency: USD
        :param toCurrency: HKD
        :param fromAmount: 100
        :param toAmount:
        :return: 汇率列表
        """
        dataParams = {
            "from": fromCurrency,
            "to": toCurrency,
            "fromAmount": fromAmount,
            "toAmount": toAmount
        }
        res = requests.get(self.host + "/common/exchangeRate", params=dataParams)
        return res.json()

    def bindReceiver(self, userId, loginToken, currency, bankName, bankNumber, accountNumber, routingNumber, name,
                     email, country, countryCode, city, zipCode, address1, note, address2, province=None,
                     swiftCode=None, sortCode=None, phoneNumber=None):
        headers = {
            "Content-Type": "application/json",
            "loginToken": loginToken,
            "userId": userId
        }
        dataBody = {
            "currency": currency,
            "type": "BankAccount",
            "bankAccount": {
                "bankName": bankName,
                "bankNumber": bankNumber,
                "accountNumber": accountNumber,
                "routingNumber": routingNumber,
                "swiftCode": swiftCode,
                "sortCode": sortCode,
                "name": name,
                "country": country,
                "countryCode": countryCode,
                "province": province,
                "city": city,
                "zipCode": zipCode,
                "address1": address1,
                "address2": address2,
                "phoneNumber": phoneNumber,
                "email": email,
                "note": note
            }
        }
        res = requests.post(self.host + "/receiver/bind", data=json.dumps(dataBody), headers=headers)
        return res.json()

    def listReceiver(self, userId, loginToken, currency, receiverType="BankAccount"):
        """

        :param userId: 用户id
        :param loginToken: 登录的token
        :param currency: 币种
        :param receiverType: 收款人方式
        :return: 列出所有收款账户
        """
        headers = {
            "Content-Type": "application/json",
            "loginToken": loginToken,
            "userId": userId
        }
        dataParams = {
            "currency": currency,
            "type": receiverType,
        }
        res = requests.get(self.host + "/receiver/list", params=dataParams, headers=headers)
        return res.json()

    def deleteReceiver(self, userId, loginToken, accountId):
        headers = {
            "Content-Type": "application/json",
            "loginToken": loginToken,
            "userId": userId
        }
        dataParams = {
            "accountId": accountId,
        }
        res = requests.get(self.host + "/receiver/delete", params=dataParams, headers=headers)
        return res.json()

    def generateRxId(self, userId, loginToken):
        headers = {
            "Content-Type": "application/json",
            "cache-control": "no-cache",
            "loginToken": loginToken,
            "userId": userId
        }
        res = requests.get(self.host + "/wallet/generateRxId", headers=headers)
        return res.json()

    def addCurrency(self, userId, loginToken, currency):
        """
        添加币种
        :param userId: 用户id
        :param loginToken: 登录的token
        :param currency: 币种
        :return:
        """
        headers = {
            "Content-Type": "application/json",
            "loginToken": loginToken,
            "userId": userId
        }
        dataBody = {"currency": currency}
        res = requests.post(self.host + "/wallet/addCurrency", data=json.dumps(dataBody), headers=headers)
        return res.json()

    def bindRoxeId(self, userId, loginToken, roxeId):
        """
        绑定 ROXEID
        :param userId: 用户id
        :param loginToken: 登录的token
        :param roxeId: 用于Roxe chain 上的账户id
        :return:
        """
        headers = {
            "Content-Type": "application/json",
            "loginToken": loginToken,
            "userId": userId
        }
        dataBody = {"roxeId": roxeId}
        res = requests.post(self.host + "/wallet/bindRxId", data=json.dumps(dataBody), headers=headers)
        return res.json()

    def checkRoxeIdAvailable(self, userId, loginToken):
        """
        检查 ROXEID 可用性
        :param userId: 用户id
        :param loginToken: 登录的token
        :return:
        """
        headers = {
            "Content-Type": "application/json",
            "loginToken": loginToken,
            "userId": userId
        }
        res = requests.get(self.host + "/wallet/rxIdAvailable", headers=headers)
        return res.json()

    def listBalanceByCurrency(self, userId, loginToken, currency):
        """
        查询单币种资产
        :param userId: 用户id
        :param loginToken: 登录的token
        :param currency: 币种，如USD、HKD、GBP
        :return:
        """
        headers = {
            "Content-Type": "application/json",
            "loginToken": loginToken,
            "userId": userId
        }
        dataParams = {"currency": currency}
        res = requests.get(self.host + "/wallet/balance", params=dataParams, headers=headers)
        return res.json()

    def listBalance(self, userId, loginToken):
        """
        查询资产列表
        :param userId: 用户id
        :param loginToken: 登录的token
        :return:
        """
        headers = {
            "Content-Type": "application/json",
            "loginToken": loginToken,
            "userId": userId
        }
        res = requests.get(self.host + "/wallet/listBalance", headers=headers)
        return res.json()

    def deposit(self, userId, loginToken, currency, amount):
        """
        充值
        :param userId: 用户id
        :param loginToken: 登录的token
        :param currency: 充值的币种
        :param amount: 充值数量, 最小为0.01
        :return:
        """
        headers = {
            "Content-Type": "application/json",
            "loginToken": loginToken,
            "userId": userId
        }
        dataBody = {"currency": currency, "amount": amount}
        res = requests.post(self.host + "/wallet/deposit", body=json.dumps(dataBody), headers=headers)
        return res.json()

    def withdraw(self, userId, loginToken, currency, amount, receiveAccountId):
        """
        提现
        :param userId: 用户id
        :param loginToken: 登录的token
        :param currency: 充值的币种
        :param amount: 充值数量, 最小为0.01
        :param receiveAccountId: 提现到的账户id，如提现给银行卡A
        :return:
        """
        headers = {
            "Content-Type": "application/json",
            "loginToken": loginToken,
            "userId": userId
        }
        dataBody = {"currency": currency, "amount": amount, "receiveAccountId": receiveAccountId}
        res = requests.post(self.host + "/wallet/withdraw", body=json.dumps(dataBody), headers=headers)
        return res.json()

    def convert(self, userId, loginToken, sendCurrency, sendAmount, receiveCurrency, receiveAmount, exchangeRate):
        """
        转换
        :param userId: 用户id
        :param loginToken: 登录的token
        :param sendCurrency: 支付币种
        :param sendAmount: 支付币种的数量
        :param receiveCurrency: 接收币种
        :param receiveAmount: 接收币种的数量
        :param exchangeRate: 转换汇率
        :return:
        """
        headers = {
            "Content-Type": "application/json",
            "loginToken": loginToken,
            "userId": userId
        }
        dataBody = {
            "sendCurrency": sendCurrency,
            "sendAmount": sendAmount,
            "receiveCurrency": receiveCurrency,
            "receiveAmount": receiveAmount,
            "exchangeRate": exchangeRate
        }
        res = requests.post(self.host + "/wallet/convert", body=json.dumps(dataBody), headers=headers)
        return res.json()

    def sendToRoxeAccount(self, userId, loginToken, counterPartyRxId, sendCurrency, sendAmount, receiveCurrency, receiveAmount, exchangeRate, note):
        """
        转账给用户余额
        :param userId: 用户id
        :param loginToken: 登录的token
        :param counterPartyRxId: 接收方的roxe Id
        :param sendCurrency: 支付币种
        :param sendAmount: 支付币种的数量
        :param receiveCurrency: 接收币种
        :param receiveAmount: 接收币种的数量
        :param exchangeRate: 转换汇率
        :param note: 备注
        :return:
        """
        headers = {
            "Content-Type": "application/json",
            "loginToken": loginToken,
            "userId": userId
        }
        dataBody = {
            "counterpartyRxId": counterPartyRxId,
            "exchangeRate": exchangeRate,
            "note": note,
            "receiveAmount": receiveAmount,
            "receiveCurrency": receiveCurrency,
            "sendAmount": sendAmount,
            "sendCurrency": sendCurrency
        }
        res = requests.post(self.host + "/transaction/sendToRoxeAccount", body=json.dumps(dataBody), headers=headers)
        return res.json()

    def sendToBankAccount(self, userId, loginToken, counterPartyAccountId, sendCurrency, sendAmount, receiveCurrency, receiveAmount, exchangeRate, note):
        """
        转账给用户的银行卡
        :param userId: 用户id
        :param loginToken: 登录的token
        :param counterPartyAccountId: 接收方的账户id
        :param sendCurrency: 支付币种
        :param sendAmount: 支付币种的数量
        :param receiveCurrency: 接收币种
        :param receiveAmount: 接收币种的数量
        :param exchangeRate: 转换汇率
        :param note: 备注
        :return:
        """
        headers = {
            "Content-Type": "application/json",
            "loginToken": loginToken,
            "userId": userId
        }
        dataBody = {
            "counterpartyAccountId": counterPartyAccountId,
            "exchangeRate": exchangeRate,
            "note": note,
            "receiveAmount": receiveAmount,
            "receiveCurrency": receiveCurrency,
            "sendAmount": sendAmount,
            "sendCurrency": sendCurrency
        }
        res = requests.post(self.host + "/transaction/sendToBankAccount", body=json.dumps(dataBody), headers=headers)
        return res.json()

    def request(self, userId, loginToken, counterPartyUserId, receiveCurrency, receiveAmount, note):
        """
        发起转账请求，向用户A请求支付
        :param userId: 用户id
        :param loginToken: 登录的token
        :param counterPartyUserId: 用户A的userId
        :param receiveCurrency: 接收币种
        :param receiveAmount: 接收币种的数量
        :param note: 备注
        :return:
        """
        headers = {
            "Content-Type": "application/json",
            "loginToken": loginToken,
            "userId": userId
        }
        dataBody = {
            "counterpartyUserId": counterPartyUserId,
            "receiveAmount": receiveAmount,
            "receiveCurrency": receiveCurrency,
            "note": note,
        }
        res = requests.post(self.host + "/transaction/request", body=json.dumps(dataBody), headers=headers)
        return res.json()

    def declineRequest(self, userId, loginToken, transactionId):
        """
        拒绝转账请求
        :param userId: 用户id
        :param loginToken: 登录的token
        :param transactionId: 交易id
        :return:
        """
        headers = {
            "Content-Type": "application/json",
            "loginToken": loginToken,
            "userId": userId
        }
        dataBody = {
            "transactionId": transactionId,
        }
        res = requests.post(self.host + "/transaction/request/decline", body=json.dumps(dataBody), headers=headers)
        return res.json()

    def payRequest(self, userId, loginToken, transactionId, sendCurrency, sendAmount, receiveCurrency, receiveAmount, exchangeRate, note):
        """
        支付请求
        :param userId: 用户id
        :param loginToken: 登录的token
        :param transactionId: 用户A的userId
        :param sendCurrency: 支付币种
        :param sendAmount: 支付数量
        :param receiveCurrency: 接收币种
        :param receiveAmount: 接收币种的数量
        :param exchangeRate: 汇率
        :param note: 备注
        :return:
        """
        headers = {
            "Content-Type": "application/json",
            "loginToken": loginToken,
            "userId": userId
        }
        dataBody = {
            "transactionId": transactionId,
            "sendCurrency": sendCurrency,
            "sendAmount": sendAmount,
            "receiveAmount": receiveAmount,
            "receiveCurrency": receiveCurrency,
            "exchangeRate": exchangeRate,
            "note": note,
        }
        res = requests.post(self.host + "/transaction/request/send", body=json.dumps(dataBody), headers=headers)
        return res.json()

    def cancelRequest(self, userId, loginToken, transactionId):
        """
        发起方取消请求
        :param userId: 用户id
        :param loginToken: 登录的token
        :param transactionId: 交易id
        :return:
        """
        headers = {
            "Content-Type": "application/json",
            "loginToken": loginToken,
            "userId": userId
        }
        dataBody = {
            "transactionId": transactionId,
        }
        res = requests.post(self.host + "/transaction/request/cancel", body=json.dumps(dataBody), headers=headers)
        return res.json()

    def confirmPaymentMethod(self, userId, loginToken, paymentMethodId,transactionId):
        """
        确认支付方式
        :param userId: 用户id
        :param loginToken: 登录的token
        :param paymentMethodId: 支付方式: wallet为1，wire transfer为2
        :param transactionId: 交易id
        :return:
        """
        headers = {
            "Content-Type": "application/json",
            "loginToken": loginToken,
            "userId": userId
        }
        dataBody = {
            "paymentMethodId": paymentMethodId,
            "transactionId": transactionId,
        }
        res = requests.post(self.host + "/transaction/confirm", body=json.dumps(dataBody), headers=headers)
        return res.json()

    def cancelTransaction(self, userId, loginToken, transactionId):
        """
        取消交易
        :param userId: 用户id
        :param loginToken: 登录的token
        :param transactionId: 交易id
        :return:
        """
        headers = {
            "Content-Type": "application/json",
            "loginToken": loginToken,
            "userId": userId
        }
        dataBody = {"transactionId": transactionId}
        res = requests.post(self.host + "/transaction/cancel", body=json.dumps(dataBody), headers=headers)
        return res.json()

    def queryWireInfo(self, userId, loginToken, transactionId):
        """
        查询wireInfo

        :param userId: 用户id
        :param loginToken: 登录的token
        :param transactionId: 交易id
        :return:
        """
        headers = {
            "Content-Type": "application/json",
            "loginToken": loginToken,
            "userId": userId
        }
        dataParams = {"transactionId": transactionId}
        res = requests.get(self.host + "/transaction/wireInfo", params=json.dumps(dataParams), headers=headers)
        return res.json()

    def queryTransactionHistory(self, userId, loginToken, receiverType, counterPartyId, currency, begin=None, end=None, pageNumber=1, pageSize=20):
        """
        查询交易历史

        :param userId: 用户id
        :param loginToken: 登录的token
        :param receiverType: 接收的方式: SendToRoxeAccount[发送到对方的roxe账户]、SendToBankAccount[发送到对方的银行卡上]
        :param counterPartyId: 发生交易的另一方的userId
        :param currency: 币种
        :param begin: 开始时间
        :param end: 结束时间
        :return:
        """
        headers = {
            "Content-Type": "application/json",
            "loginToken": loginToken,
            "userId": userId
        }
        dataParams = {
            "type": receiverType,
            "pageNumber": pageNumber,
            "pageSize": pageSize,
            "counterpartyId": counterPartyId,
            "currency": currency,
            "begin": begin,
            "end": end
        }
        res = requests.get(self.host + "/transaction/history", params=json.dumps(dataParams), headers=headers)
        return res.json()

    def getPlaidLinkToken(self, userId, loginToken):
        """
        获取plaid-link-token
        :param userId: 用户id
        :param loginToken: 登录的token
        :return:
        """
        headers = {
            "Content-Type": "application/json",
            "loginToken": loginToken,
            "userId": userId
        }
        res = requests.get(self.host + "/payment-method/plaid-link-token", headers=headers)
        return res.json()

    def queryTransactionDetail(self, userId, loginToken, transactionId):
        """
        获取plaid-link-token
        :param userId: 用户id
        :param loginToken: 登录的token
        :param transactionId: 交易id
        :return:
        """
        headers = {
            "Content-Type": "application/json",
            "loginToken": loginToken,
            "userId": userId
        }
        dataParams = {"transactionId": transactionId}
        res = requests.get(self.host + "/transaction/detail", params=json.dumps(dataParams), headers=headers)
        return res.json()

    def listPaymentMethod(self, userId, loginToken, currency):
        """
        获取支付方式列表
        :param userId: 用户id
        :param loginToken: 登录的token
        :param currency: 币种
        :return:
        """
        headers = {
            "Content-Type": "application/json",
            "loginToken": loginToken,
            "userId": userId
        }
        dataParams = {"currency": currency}
        res = requests.get(self.host + "/payment-method/list", params=json.dumps(dataParams), headers=headers)
        return res.json()

    def querySendAmount(self, userId, loginToken, currency, amount, mode):
        """
        查询已汇出金额
        :param userId: 用户id
        :param loginToken: 登录的token
        :param currency: 币种
        :param amount: 支付数量
        :param mode: 模式
        :return:
        """
        headers = {
            "Content-Type": "application/json",
            "loginToken": loginToken,
            "userId": userId
        }
        dataParams = {"currency": currency, "amount": amount, "mode": mode}
        res = requests.get(self.host + "/statistics/sendAmount", params=json.dumps(dataParams), headers=headers)
        return res.json()

    def queryRecentBankAccounts(self, userId, loginToken):
        """
        查询最近交易过的银行账户

        :param userId: 用户id
        :param loginToken: 登录的token
        :return:
        """
        headers = {
            "Content-Type": "application/json",
            "loginToken": loginToken,
            "userId": userId
        }
        res = requests.get(self.host + "/contact/recentBankAccounts", headers=headers)
        return res.json()

    def bindPaymentMethod(self, userId, loginToken, publicToken, currency, mask, name, subType, payType, institutionName):
        """
        绑定支付方式的账户

        :param userId: 用户id
        :param loginToken: 登录的token
        :param publicToken: token
        :param currency: 币种
        :param mask:
        :param name: 名称
        :param subType: 下一级类型:
        :param payType: 支付方式类型
        :param institutionName
        :return:
        """
        headers = {
            "Content-Type": "application/json",
            "loginToken": loginToken,
            "userId": userId
        }
        dataBody = {
            "publicToken": publicToken,
            "currency": currency,
            "mask": mask,
            "name": name,
            "subType": subType,
            "type": payType,
            "institutionName": institutionName,
        }
        res = requests.post(self.host + "/payment-method/bind", body=json.dumps(dataBody), headers=headers)
        return res.json()

    def unbindPaymentMethod(self, userId, loginToken, paymentMethodId):
        """
        解绑

        :param userId: 用户id
        :param loginToken: 登录的token
        :param paymentMethodId: 支付方式id
        :return:
        """
        headers = {
            "Content-Type": "application/json",
            "loginToken": loginToken,
            "userId": userId
        }
        dataBody = {"paymentMethodId": paymentMethodId}
        res = requests.post(self.host + "/payment-method/unbind", body=json.dumps(dataBody), headers=headers)
        return res.json()

    def getLoginTokenFromRedis(self, userId):
        info = self.redisClient2.getInfoFromKey("TOKEN:USER_LOGIN:" + userId)
        return info

    def kycVerification(self, userId, currency, amount):
        loginToken = self.getLoginTokenFromRedis(userId)
        headers = {"loginToken": loginToken, "userId": userId}
        params = {"amount": amount, "currency": currency}
        res = requests.get(self.host + "/kyc/kycVerification", params=params, headers=headers)
        print(res.json())

    def getUserRecentContact(self, userId):
        loginToken = self.getLoginTokenFromRedis(userId)
        headers = {"loginToken": loginToken, "userId": userId}
        res = requests.get(self.host + "/transaction/getUserRecentContact", headers=headers)
        print(res.json())

    def getOrderShareList(self, userId, toUserId, shareType=2, shareScope=2):
        """
        获取订单分享list
        :param userId: 请求发起方的userId
        :param toUserId: 请求获取某人分享订单的userId
        :param shareType: 类型 1 ：所有 ，2：个人
        :param shareScope: 范围 1 ：私有 ，2公开
        :return:
        """
        loginToken = self.getLoginTokenFromRedis(userId)
        headers = {"loginToken": loginToken, "userId": userId}
        data = {
            "pageNumber": 1,
            "pageSize": 10,
            "userID": toUserId,
            "type": shareType,
            "scope": shareScope
        }
        res = requests.get(self.host + "/orderShare/getOrderShareList", data, headers=headers)
        print(res.json())


if __name__ == "__main__":
    testUrl = "https://xxxx/roxe-send"
    redisUrl = "xxxx"
    redisPwd = "xxxx"
    paymentClient = RoxePaymentApi(testUrl, redisUrl, redisPwd)
    # print(paymentClient.redisClient.getInfoFromKey("USER_INFO:100153"))
    print(paymentClient.redisClient2.getInfoFromKey("TOKEN:USER_LOGIN:100218"))
    print(paymentClient.redisClient2.getInfoFromKey("USER:ONLY:KEY", "100108"))
    # print(paymentClient.redisClient2.redisConn.ttl("TOKEN:USER_LOGIN:100197"))
    # paymentClient.kycVerification("100153", "USD", 14996)
    # paymentClient.kycVerification("100155", "USD", 24699)
    # paymentClient.kycVerification("100144", "USD", 100)
    # paymentClient.kycVerification("100107", "USD", 1)
    # paymentClient.getOrderShareList("100107", "100028", 2, 2)
    # paymentClient.getUserRecentContact("100144")
    # paymentClient.getAccountList("100144", "USD")
    # paymentClient.delAccount("100144", 67)
    # print("100107:", paymentClient.redisClient.getInfoFromKey("Ro:Send:Daily:Amount", "100107"))
    # print("100107:", paymentClient.redisClient.getInfoFromKey("Ro:Send:Weekly:Amount", "100107"))
    # print("100108:", paymentClient.redisClient.getInfoFromKey("Ro:Send:Daily:Amount", "100108"))
    # print("100108:", paymentClient.redisClient.getInfoFromKey("Ro:Send:Weekly:Amount:100107"))
    # print(time.time() - 1624605719)

