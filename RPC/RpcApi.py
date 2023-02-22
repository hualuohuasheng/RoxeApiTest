import logging
from roxe_libs.baseApi import *
from roxe_libs import settings, ContractChainTool
from roxe_libs.Global import Global
from roxe_libs import ApiUtils
import time


class RPCApiClient:

    def __init__(self, host, chain_host):
        self.host = host
        self.logger = logging.getLogger(Global.getValue(settings.logger_name))  # 获取全局的日志记录logger
        self.chain_client = ContractChainTool.RoxeChainClient(chain_host)

        traceable = Global.getValue(settings.enable_trace)
        if traceable:
            for handle in self.logger.handlers:
                if "filehand" in str(handle).lower():
                    handle.setLevel(logging.DEBUG)
                # handle.setLevel(logging.DEBUG)

    def channelsQueryRequest(self, callSource, group, channelType, country, currency, payoutMethod, strategy="", name="", notGetPayoutMethod=True, **kwargs):
        """
        获取调用RPC的基础公共参数
        :param callSource:调用来源->RSS,RMN,RPS（针对通道测试默认填写RSS)
        :param group:渠道所属分组->ROXE, RMN, APIFINY, RTS10,MOCK
        :param channelType:渠道类型->出金OUT、入金IN
        :param country:国家
        :param currency:币种
        :param strategy:路由渠道的策略->FEE,SPEED,NAME（非必填）
        :param name:渠道名称(当策略为Strategy.NAME时需填写）（非必填）
        :param payoutMethod:出金方式->cashPickup,bank,wallet,all（注：如果不是获取出金方式接口调用，该字段必填）
        """
        if notGetPayoutMethod:
            payoutMethod = payoutMethod
        else:
            payoutMethod = None

        channelsQueryRequest = {
            "callSource": callSource,
            "group": group,
            "channelType": channelType,
            "country": country,
            "currency": currency,
            "strategy": [strategy],
            "name": name,
            "payoutMethod": payoutMethod
        }
        for k, v in kwargs.items():
            channelsQueryRequest[k] = v
        self.logger.debug(f"生成channelsQueryRequest: {channelsQueryRequest}")
        return channelsQueryRequest

    def getPayoutMethod(self, body):
        """
        :param body: 请求体（需通过调用channelsQueryRequest获得）
        """
        url = self.host + "/payoutOrder/getPayoutMethod"
        self.logger.info("获取出金方式")
        res = sendPostRequest(url, body).json()
        self.logger.debug("请求url: {}".format(url))
        self.logger.debug("请求参数: {}".format(body))
        self.logger.info("请求结果: {}".format(res))
        return res

    def getBanksOrAgents(self, channelsQueryRequest, payoutMethod, keyword):
        url = self.host + "/payoutOrder/getBanksOrAgents"
        body = {
            "channelsQueryRequest": channelsQueryRequest,
            "payoutMethod": payoutMethod,
            "keyword": keyword
        }
        self.logger.info("获取银行或机构列表")
        res = sendPostRequest(url, body).json()
        self.logger.debug("请求url: {}".format(url))
        self.logger.debug("请求参数: {}".format(body))
        self.logger.info("请求结果: {}".format(res))
        return res

    def getUserRequiredFields(self, channelsQueryRequest, payoutMethod, agent=""):
        url = self.host + "/payoutOrder/getUserRequiredFields"
        body = {
            "channelsQueryRequest": channelsQueryRequest,
            "payoutMethod": payoutMethod,
            "agent": agent
        }
        self.logger.info("获取出金字段")
        res = sendPostRequest(url, body).json()
        self.logger.debug("请求url: {}".format(url))
        self.logger.debug("请求参数: {}".format(body))
        self.logger.info("请求结果: {}".format(res))
        return res

    def checkUserRequiredFields(self, channelsQueryRequest, payoutInfo):
        """
        :param channelsQueryRequest: 调用RPC的基础公共参数
        :param payoutInfo: 需要校验的出金参数
        """
        url = self.host + "/payoutOrder/check"
        body = {
            "channelsQueryRequest": channelsQueryRequest,
            "payoutInfoJson": json.dumps(payoutInfo),
            "referenceId": "123456789abcdefg12345678"
        }
        self.logger.info("校验出金字段")
        res = sendPostRequest(url, body).json()
        self.logger.debug("请求url: {}".format(url))
        self.logger.debug("请求参数: {}".format(body))
        self.logger.info("请求结果: {}".format(res))
        return res

    def getExchangeRate(self, channelsQueryRequest, sourceCurrency, targetCurrency):
        url = self.host + "/payoutOrder/getExchangeRate"
        body = {
            "channelsQueryRequest": channelsQueryRequest,
            "sourceCurrency": sourceCurrency,
            "targetCurrency": targetCurrency
        }
        self.logger.info("获取汇率")
        res = sendPostRequest(url, body).json()
        self.logger.debug("请求url: {}".format(url))
        self.logger.debug("请求参数: {}".format(body))
        self.logger.info("请求结果: {}".format(res))
        return res

    def submitPayoutOrder(self, channelsQueryRequest, payoutInfo, addInfos={}):
        url = self.host + "/payoutOrder/payout"
        referenceId = "testrpc" + str(time.time()).split(".")[0] + str(time.time()).split(".")[1]  # 拼接生成referenceId
        # referenceId = ""
        # referenceId = None
        payoutInfo["amount"] = ApiUtils.randAmount(100, 2, 10)  # 当测试金额时注销本行
        body = {
            "channelsQueryRequest": channelsQueryRequest,
            "payoutInfoJson": json.dumps(payoutInfo),
            "referenceId": referenceId
        }
        for k, v in addInfos.items():
            body[k] = v
        self.logger.info("提交出金订单")
        res = sendPostRequest(url, body).json()
        self.logger.debug("请求url: {}".format(url))
        self.logger.debug("请求参数: {}".format(body))
        self.logger.info("请求结果: {}".format(res))
        return res

    def getPayoutOrderTransactionState(self, orderId):
        url = self.host + "/payoutOrder/getTransaction"
        params = {
            "orderId": orderId
        }
        self.logger.info("查询出金交易订单状态")
        res = sendGetRequest(url, params).json()
        self.logger.debug("请求url: {}".format(url))
        self.logger.debug("请求参数: {}".format(params))
        self.logger.info("请求结果: {}".format(res))
        return res

    def submitPayinOrder(self, channelName, payBankAccountId, serviceChannelCustomerId="", sourceRoxeAccount="", targetRoxeAccount="", callSource="RPS", payMethod="balance", currency="USD", businessItemName="test123", amount=None):
        url = self.host + "/payinOrder/payin"
        referenceId = "testrpc" + str(time.time()).split(".")[0] + str(time.time()).split(".")[1]  # 拼接生成referenceId
        if not amount:
            amount = ApiUtils.randAmount(50, 2, 5)
        body = {
            "channelName": channelName,
            "callSource": callSource,
            "referenceId": referenceId,
            "payBankAccountId": payBankAccountId,
            "serviceChannelCustomerId": serviceChannelCustomerId,
            "payMethod": payMethod,
            "payToken": "",
            "amount": amount,
            "currency": currency,
            "cancelUrl": "https://www.roxe.io",
            "successUrl": "https://www.roxe.io",
            "businessItemName": businessItemName,
            "sourceRoxeAccount": sourceRoxeAccount,
            "targetRoxeAccount": targetRoxeAccount,
            "memo": "Nelms",
            "cardBin": "",
            "expiryMonth": "3",
            "expiryYear": "3"
        }
        self.logger.info("提交入金订单")
        res = sendPostRequest(url, body).json()
        self.logger.debug("请求url: {}".format(url))
        self.logger.debug("请求参数: {}".format(body))
        self.logger.info("请求结果: {}".format(res))
        return res

    def getPayinOrderTransactionStateByRpcId(self, rpcId):
        url = self.host + "/payinOrder/getTransactionByRpcId"
        params = {
            "rpcId": rpcId
        }
        self.logger.info("通过rpcId查询入金交易订单状态")
        res = sendGetRequest(url, params).json()
        self.logger.debug("请求url: {}".format(url))
        self.logger.debug("请求参数: {}".format(params))
        self.logger.info("请求结果: {}".format(res))
        return res

    def getPayinOrderTransactionStateByRefId(self, referenceId):
        url = self.host + "/payinOrder/getTransaction"
        params = {
            "referenceId": referenceId
        }
        self.logger.info("通过referenceId查询入金交易订单状态")
        res = sendGetRequest(url, params).json()
        self.logger.debug("请求url: {}".format(url))
        self.logger.debug("请求参数: {}".format(params))
        self.logger.info("请求结果: {}".format(res))
        return res


if __name__ == "__main__":
    rpc_url = "http://rpc-uat.roxepro.top:38888/roxe-rpc/inner/roxepay"
