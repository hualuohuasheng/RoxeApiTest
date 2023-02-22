# coding=utf-8
# author: Li MingLei
# date: 2021-08-27
"""
RTS2.0重构后，RSS随之一起做了重构
"""
import logging
from roxe_libs.baseApi import *
from roxe_libs import settings, ContractChainTool
from roxe_libs.Global import Global
from roxe_libs import ApiUtils
import time
# import nacos
from roxe_libs.DBClient import Mysql
import yaml


def getNacosConfigInfo():
    """
    获取nacos上通道费用的配置文件
    """
    SERVER_ADDRESSES = "172.17.3.6:8848"  # nacos的ip:port
    NAMESPACE = "public"  # 命名空间
    client = nacos.NacosClient(SERVER_ADDRESSES, namespace=NAMESPACE, username="nacos", password="nacos")
    data_id = "roxe-rpc-channels.yaml"
    group = "DEFAULT_GROUP"
    config_info = client.get_config(data_id, group, 10)
    return config_info

def getChannelFee(channelName, currency, channelType="OUT"):
    """
    通过处理读取的nacos通道费用配置文件来获取对应的费用
    """
    config_info = getNacosConfigInfo()
    info = config_info.split(":", 1)[1].strip().strip("'")
    channel_info = [i for i in json.loads(info) if i["channelName"] == channelName]

    if len(channel_info) != 1:
        print(f"未找到唯一channel{channelName}: {channel_info}")

    fee_info = [c_info for c_info in channel_info[0]["channelInfo"] if c_info["currency"] == currency and c_info["channelType"] == channelType][0]
    print(f"费用配置为:{fee_info}")
    return fee_info


class RSSApiClient:

    def __init__(self, host, chain_host):
        self.host = host
        self.logger = logging.getLogger(Global.getValue(settings.logger_name))  # 获取全局的日志记录logger
        self.chain_client = ContractChainTool.RoxeChainClient(chain_host)
        self.terrapay_host = "https://uat-connect.terrapay.com:21211/eig/gsma"

        traceable = Global.getValue(settings.enable_trace)
        if traceable:
            for handle in self.logger.handlers:
                if "filehand" in str(handle).lower():
                    handle.setLevel(logging.DEBUG)
                # handle.setLevel(logging.DEBUG)

    # def handle_host(self, country):
    #     # c_url = self.host.split("-")[1]
    #     c_url = self.host.split("-")[4]
    #     self.host = self.host.replace(c_url, country)

    def getSystemState(self):
        url = self.host + "/system/state"
        res = sendGetRequest(url)
        self.logger.debug("请求url: {}".format(url))
        self.logger.info("请求结果: {}".format(res.text))
        return res.json()

    def getCurrencySupport(self):
        url = self.host + "/currency-support"
        res = sendGetRequest(url)
        self.logger.info("查询支持的币种")
        self.logger.debug("请求url: {}".format(url))
        self.logger.info("请求结果: {}".format(res.text))
        return res.json()

    def getCustodyAccount(self, currency):
        url = self.host + "/custody-account"
        if currency:
            url += "/" + currency
        res = sendGetRequest(url).json()
        self.logger.info("查询入金账户")
        self.logger.debug("请求url: {}".format(url))
        self.logger.info("请求结果: {}".format(res))
        return res

    def getExchangeReatFee(self, payCurrency, payQuantity, outCurrency, outMethod, popKey=None):
        url = self.host + "/exchange-rate-fee"
        params = {
            "payCurrency": payCurrency,
            "payQuantity": payQuantity,
            "outCurrency": outCurrency,
            "outMethod": outMethod,
        }
        if popKey:
            params.pop(popKey)
        self.logger.info("查询汇率费用")
        res = sendGetRequest(url, params).json()
        self.logger.debug("请求url: {}".format(url))
        self.logger.debug("请求参数: {}".format(params))
        self.logger.info("请求结果: {}".format(res))
        return res, params

    def getPayoutMethod(self, outCurrency):
        url = self.host + "/get-payout-method"
        params = {"outCurrency": outCurrency}
        self.logger.info("查询出金方式")
        res = sendGetRequest(url, params).json()
        self.logger.debug("请求url: {}".format(url))
        self.logger.debug("请求参数: {}".format(params))
        self.logger.info("请求结果: {}".format(res))
        return res

    def getPayoutOrgan(self, outCurrency, outMethod, keyword=""):
        url = self.host + "/get-payout-organ"
        params = {
            "outCurrency": outCurrency,
            "outMethod": outMethod,
            "keyword": keyword,
        }
        self.logger.info("查询出金机构")
        res = sendGetRequest(url, params).json()
        self.logger.debug("请求url: {}".format(url))
        self.logger.debug("请求参数: {}".format(params))
        self.logger.info("请求结果: {}".format(res))
        return res

    def getPayoutForm(self, outCurrency, outMethod, outOrgan=""):
        url = self.host + "/get-payout-form"
        params = {
            "outCurrency": outCurrency,
            "outMethod": outMethod,
            "outOrgan": outOrgan,
        }
        self.logger.info("查询出金必填字段")
        res = sendGetRequest(url, params).json()
        self.logger.debug("请求url: {}".format(url))
        self.logger.debug("请求参数: {}".format(params))
        self.logger.info("请求结果: {}".format(res))
        return res

    def checkPayoutForm(self, outCurrency, outInfo, popKey=None):
        url = self.host + "/check-payout-form"
        body = {
            "outCurrency": outCurrency,
            "outInfo": outInfo,
        }
        if popKey:
            body.pop(popKey)
        self.logger.info("校验出金必填字段")
        res = sendPostRequest(url, body).json()
        self.logger.debug("请求url: {}".format(url))
        self.logger.debug("请求body: {}".format(body))
        self.logger.info("请求结果: {}".format(res))
        return res

    def submitOrderForm(self, submitId, payOrderId, payCurrency, payAmount, outCurrency, outInfo=None, popKey=None):
        url = self.host + "/submit-order-form"
        if outInfo is None:
            outInfo = {}
        body = {
            "submitId": submitId,
            "payOrderId": payOrderId,
            "payCurrency": payCurrency,
            "payAmount": payAmount,
            "outCurrency": outCurrency,
            "outInfo": outInfo,
        }
        if popKey:
            body.pop(popKey)
        self.logger.info("提交结算表单")
        res = sendPostRequest(url, body)
        self.logger.debug("请求url: {}".format(url))
        self.logger.debug("请求body: {}".format(body))
        self.logger.info("请求结果: {}".format(res.json()))
        return res.json(), body

    def queryFormByClientID(self, clientID):
        """
        clientID：用户提交订单时的ID，即为submitId
        """
        url = self.host + "/get-state-client/" + clientID
        self.logger.info("根据clientID查询表单信息")
        res = sendGetRequest(url).json()
        self.logger.debug("请求url: {}".format(url))
        self.logger.info("请求结果: {}".format(res))
        return res

    def queryFormByOrderID(self, orderID):
        url = self.host + "/get-state-form/" + orderID
        self.logger.info("根据orderID查询表单信息")
        res = sendGetRequest(url).json()
        self.logger.debug("请求url: {}".format(url))
        self.logger.info("请求结果: {}".format(res))
        return res

    @classmethod
    def getFee(cls, db_client, r_params):
        """
        根据一定的路由规则，计算入金的数量，所需的费用，
        :param db_client: mysql的client,
        :param r_params: 请求参数,
        :return:
        """
        in_currency = r_params["innerCurrency"]
        out_currency = r_params["outerCurrency"]
        in_quantity = r_params["innerQuantity"]
        out_quantity = r_params["outerQuantity"]
        channel_sql = "select * from roxe_rss_us.rss_channel where inner_currency='{}' and outer_currency='{}'".format(
            in_currency, out_currency)
        db_channel_res = db_client.exec_sql_query(channel_sql)
        # print("查询数据库结果: {}".format(db_channel_res))
        fee_cfg = json.loads(db_channel_res[0]["feeConfig"])
        # print("查询数据库中铸币赎回的fee_config: {}".format(fee_cfg))
        inner_quantity, outer_quantity, fee = 0, 0, 0

        if in_currency.endswith(".ROXE"):
            fee_currency = out_currency
            if "USD" not in out_currency:
                fee_currency = in_currency.split(".ROXE")[0]
        else:
            fee_currency = in_currency

        rate_cfg = {"BRL": 5.49, "CNY": 6.40, "INR": 74.41, "MXN": 20.61, "PHP": 50.08, "NGN": 410.08, "USD": 1}

        if len(db_channel_res) > 0:
            if len(db_channel_res) == 1:
                if in_quantity:
                    fee = ApiUtils.parseNumberDecimal(float(fee_cfg['add']))
                    outer_quantity = in_quantity - fee if 'USD' in out_currency else (in_quantity - fee) * rate_cfg[
                        out_currency]
                    inner_quantity = in_quantity
                else:
                    fee = ApiUtils.parseNumberDecimal(float(fee_cfg['add']))
                    inner_quantity = out_quantity + fee if 'USD' in out_currency else out_quantity / rate_cfg[
                        out_currency] + fee
                    outer_quantity = out_quantity
            else:
                # 数据库查询出多条数据，根据一定算法算出入金费用
                pass
        print("计算出的结果: inner_quantity {}, outer_quantity {}, fee {}, fee_currency {}".format(inner_quantity,
                                                                                             outer_quantity, fee,
                                                                                             fee_currency))

        return inner_quantity, outer_quantity, fee, fee_currency, fee_cfg

    def queryOuterFeeByRouter(self, db_client, in_currency, out_currency, in_quantity: float):
        """
        根据一定的路由规则，计算出金的数量，所需的费用，
        :param db_client: mysql的client,
        :param in_currency: 指定赎回的币种,
        :param out_currency: 指定出金的币种,
        :param in_quantity: 指定赎回的数量,
        :return:
        """
        channel_sql = "select * from rss_channel where inner_currency='{}' and outer_currency='{}'".format(in_currency,
                                                                                                           out_currency)
        db_channel_res = db_client.exec_sql_query(channel_sql)
        self.logger.info("查询数据库中channel结果: {}".format(db_channel_res))
        fee_cfg_sql = "select * from rss_config where config_code='fee_config'"
        fee_cfg = db_client.exec_sql_query(fee_cfg_sql)
        fee_cfg = json.loads(fee_cfg[0]["configValue"].replace("\n    ", "").replace(",\n", ""))
        self.logger.info("查询数据库中铸币赎回的fee_config: {}".format(fee_cfg))
        out_quantity, fee, fee_currency = 0, 0, in_currency
        if len(db_channel_res) > 0:
            if len(db_channel_res) == 1:
                # 数据库只查询出1条数据
                db_channel_fee = json.loads(db_channel_res[0]["channelFee"])
                fee_currency = in_currency  # 赎回时收取费用的币种为Ro
                # 销毁费用计算: amount * 销毁费率
                redeem_fee = in_quantity * fee_cfg["redeemFeeRate"]
                self.logger.info("出金时的赎回费用: {}".format(redeem_fee))
                # 销毁通道费用计算
                channel_fee = (in_quantity - redeem_fee) * float(db_channel_fee["feeRate"])
                if channel_fee < float(db_channel_fee["feeMin"]):
                    channel_fee = float(db_channel_fee["feeMin"])
                if channel_fee >= float(db_channel_fee["feeMax"]):
                    channel_fee = float(db_channel_fee["feeMax"])
                if float(db_channel_fee["feeAdd"]) > 0:
                    channel_fee += float(db_channel_fee["feeAdd"])
                self.logger.info("出金时的通道费用: {}".format(channel_fee))
                out_quantity = in_quantity - redeem_fee - channel_fee
                # out_quantity = ContractChainTool.parseNumberToString(out_quantity, is_keep=True)
                fee = redeem_fee + channel_fee
                # fee = ContractChainTool.parseNumberToString(redeem_fee)
            else:
                # 数据库查询出多条数据，根据一定算法算出入金费用
                pass
        self.logger.info("计算出的结果: quantity {}, fee {}, fee_currency {}".format(out_quantity, fee, fee_currency))
        return out_quantity, fee, fee_currency

    def getNacosConfigInfo(self):
        """
        获取nacos上通道费用的配置文件
        """
        SERVER_ADDRESSES = "172.17.3.6:8848"  # nacos的ip:port
        NAMESPACE = "public"  # 命名空间
        client = nacos.NacosClient(SERVER_ADDRESSES, namespace=NAMESPACE, username="nacos", password="nacos")
        data_id = "roxe-rpc-channels.yaml"
        group = "DEFAULT_GROUP"
        config_info = client.get_config(data_id, group, 10)
        return config_info

    def getChannelFee(self, channelName, currency, channelType="OUT"):
        """
        通过处理读取的数据库通道费用配置表来获取对应的费用
        """
        config_info = self.getNacosConfigInfo()
        info = yaml.load(config_info, Loader=yaml.FullLoader)
        channel_info = [i for i in info["channel-config"]["channels"] if i["channelName"] == channelName]

        if len(channel_info) != 1:
            self.logger.info(f"未找到唯一channel{channelName}: {channel_info}")

        fee_info = [c_info for c_info in channel_info[0]["channelInfo"] if c_info["currency"] == currency and c_info["channelType"] == channelType][0]
        self.logger.info(f"费用配置为:{fee_info}")
        return fee_info

    def terrapayQueryStatus(self, value, beneficiaryName=None, provider=None, bankcode=None, bankname=None,
                            country=None):
        """
        value:如果查询收款人电子钱包状态则为收款人带国家编码的手机号，如果查询收款人银行账户状态则为收款人用于收钱的银行账户ID
        """
        url_w = self.terrapay_host + f"/accounts/msisdn/{value}/status"
        url_b = self.terrapay_host + f"/accounts/{value}/status"

        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())  # 获取当前时间
        headers = {
            'X-USERNAME': 'roxeUAT',
            'X-PASSWORD': '8d07054c448e457d4b5aae6f5fd83f5d264b0d150718cbcfce56b648733ffdd4',
            'X-DATE': current_time,
            'X-ORIGINCOUNTRY': 'US'
        }

        if value.startswith("+"):
            self.logger.info("查询收款人电子钱包状态")
            params = {
                "bnv": beneficiaryName,
                "provider": provider,
            }
            res = sendGetRequest(url_w, headers=headers, params=params, verify=False).json()
            self.logger.debug("请求url:{}".format(url_w))
            self.logger.info("请求结果:{}".format(res))
        else:
            self.logger.info("查询收款人银行账户状态")
            params = {
                "bnv": beneficiaryName,
                "bankcode": bankcode,
                "bankname": bankname,
                "country": country
            }
            res = sendGetRequest(url_b, headers=headers, params=params, verify=False).json()
            self.logger.debug("请求url:{}".format(url_b))
            self.logger.debug("请求参数:{}".format(params))
            self.logger.info("请求结果:{}".format(res))

        return res

    def terraypayQueryExchangeRate(self, value, requestAmount, requestCurrency, sendingCurrency, receivingCurrency,
                                   receivingCountry=None):
        """
        value:如果查询电子钱包汇率报价则为收款人带国家编码的手机号，如果查询银行账户报价则为收款人用于收钱的银行账户ID
        """
        url = self.terrapay_host + "/quotations"
        current_time = time.strftime("%Y-%m-%d %H:00:00", time.localtime())  # 获取当前时间，精确到小时
        headers = {
            'X-USERNAME': 'roxeUAT',
            'X-PASSWORD': '8d07054c448e457d4b5aae6f5fd83f5d264b0d150718cbcfce56b648733ffdd4',
            'X-DATE': current_time,
            'X-ORIGINCOUNTRY': 'US'
        }
        if value.startswith("+"):
            self.logger.info("查询电子钱包汇率报价")
            body = {
                "requestDate": current_time,
                "debitParty": [
                    {
                        "key": "msisdn",
                        "value": ""
                    }
                ],
                "creditParty": [
                    {
                        "key": "msisdn",
                        "value": value  # 收款人带国家编码的手机号，钱包时必填
                    }
                ],
                "requestAmount": requestAmount,
                "requestCurrency": requestCurrency,
                "quotes": [
                    {
                        "sendingCurrency": sendingCurrency,
                        "receivingCurrency": receivingCurrency
                    }
                ]
            }
        else:
            self.logger.info("查询银行账户报价则")
            body = {
                "requestDate": current_time,
                "debitParty": [{
                    "key": "msisdn",
                    "value": ""
                }],
                "creditParty": [{
                    "key": "msisdn",
                    "value": ""
                },
                    {
                        "key": "bankaccountno",
                        "value": value
                    },
                    {
                        "key": "receivingCountry",
                        "value": receivingCountry
                    }
                ],
                "requestAmount": requestAmount,
                "requestCurrency": requestCurrency,
                "quotes": [{
                    "sendingCurrency": sendingCurrency,
                    "receivingCurrency": receivingCurrency
                }]
            }
        res = sendPostRequest(url, headers=headers, body=body, verify=False).json()
        self.logger.debug("请求url:{}".format(url))
        self.logger.debug("请求body:{}".format(body))
        self.logger.info("请求结果:{}".format(res))
        return res

    def terrapayQueryOrderStatus(self, channel_order_id):
        """
        根据ID查询订单状态
        """
        url = self.terrapay_host + f"/transactions/{channel_order_id}"
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())  # 获取当前时间
        headers = {
            'X-USERNAME': 'roxeUAT',
            'X-PASSWORD': '8d07054c448e457d4b5aae6f5fd83f5d264b0d150718cbcfce56b648733ffdd4',
            'X-DATE': current_time,
            'X-ORIGINCOUNTRY': 'US'
        }
        res = sendGetRequest(url, headers=headers, verify=False).json()
        self.logger.debug("请求url:{}".format(url))
        self.logger.info("请求结果:{}".format(res))
        return res

    def terrapayQueryAccountBalance(self):
        """
        查询账户余额（账户指的是我司在通道方的账户）
        """
        url = self.terrapay_host + "/accounts/all/balance"
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())  # 获取当前时间
        headers = {
            'X-USERNAME': 'roxeUAT',
            'X-PASSWORD': '8d07054c448e457d4b5aae6f5fd83f5d264b0d150718cbcfce56b648733ffdd4',
            'X-DATE': current_time,
            'X-ORIGINCOUNTRY': 'US'
        }
        try:
            res = sendGetRequest(url, headers=headers, verify=False).json()
            balance = float(res[1]["currentBalance"])
            self.logger.debug("请求url:{}".format(url))
            self.logger.info("请求结果:{}".format(res))
        except Exception:
            balance = 0
        return balance


if __name__ == "__main__":
    my_logger = logging.getLogger("rtsDemo")
    my_logger.setLevel(logging.DEBUG)
    fmt = '[%(levelname)s] %(asctime)s: [%(name)s:%(lineno)d]: %(message)s'
    formatter = logging.Formatter(fmt)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    my_logger.addHandler(handler)
    Global.setValue(settings.logger_name, my_logger.name)
    Global.setValue(settings.enable_trace, False)

    client = RSSApiClient("http://rss-roxe-cn-bj-test.roxepro.top:38888", "http://192.168.37.22:18888/v1")
    client.handle_host("us")
    client.querySystemOnline()
    # client.queryOuterMethod("USD")
    client.queryOuterMethod("INR")

    q_fields = client.queryOuterFields("INR", "bank", "")
    res = {}
    for i in q_fields["data"]:
        res[i["name"]] = ""
    print(json.dumps(res))
    out_info = {
        "senderSourceOfFund": "salary",
        "receiverBirthday": "June 1, 1991",
        "senderNationality": "CNINA",
        "senderAddress": "No. 1 chang 'an Avenue",
        "purpose": "withdraw",
        "receiverIdNumber": "R20211221001",
        "senderIdNumber": "S20211221001",
        "receiverCity": "beijing",
        "referenceId": "20211221001",
        "receiverAccountName": "Li XX",
        "senderFullName": "AliPay",
        "receiverCountry": "CN",
        "senderPostcode": "123456",
        "receiverAccountNumber": "123123123",
        "senderBirthday": "1999-01-02",
        "receiverFirstName": "Robinson",
        "senderCountry": "CN",
        "receiverIdType": "number",
        "amount": "28.33",
        "senderIdType": "CCPT",
        "receiverIdExpireDate": "20211231",
        "senderFirstName": "Pay",
        "receiveMethodCode": "BANK",
        "senderIdExpireDate": "20221231",
        "receiverFullName": "David Robinson",
        "quoteId": "1221001",
        "senderCity": "beijing",
        "receiverAddress": "No. 22 chang 'an Avenue",
        "senderPhone": "3300000000",
        "receiverCurrency": "CNY",
        "senderBeneficiaryRelationship": "friend"
    }

    # client.checkOuterFields("CNY", out_info)
    submit_id = "test" + str(int(time.time() * 1000))
    out_info = {
        "payOutMethod": "bank",
        "receiverBankId": "LOCAL____IFSC____HDFC0000136",
        "referenceId": str(int(time.time() * 1000)),
        "amount": "12",
        "purpose": "Family Maintenance",
        "pledgeAccountCurrency": "USD",
        "receiverAccountNumber": "12345678901234",
        "senderCountry": "US",
        "senderFirstName": "Michael",
        "senderLastName": "L Stallman",
        "senderAccountType": "Individual",
        "senderIdType": "CCPT",
        "senderIdNumber": "12345678911234",
        "senderAddress": "beijing",
        "receiverFirstName": "Edward",
        "receiverLastName": "Nelms",
        "receiverCountry": "IN",
        "receiverCurrency": "INR",
        "receiverAccountType": "Individual"
    }
    # client.checkOuterFields("INR", out_info)
