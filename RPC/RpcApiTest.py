import time
import json
import os
import unittest
import copy
from .RpcApi import RPCApiClient
from roxe_libs.DBClient import Mysql
from roxe_libs import settings, ApiUtils
from roxe_libs.Global import Global
from roxe_libs.pub_function import loadYmlFile


class RPCData:
    env = Global.getValue(settings.environment)
    cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), f"./Rpc_{env}.yml"))
    _yaml_conf = loadYmlFile(cfg_path)

    host = _yaml_conf["host"]
    chain_host = _yaml_conf["chain_host"]

    is_check_db = _yaml_conf["is_check_db"]
    sql_cfg = _yaml_conf["sql_cfg"]

    channelsQueryRequest = _yaml_conf["channelsQueryRequest"]
    payoutInfoJson = _yaml_conf["payoutInfoJson"]


class RPCApiTest(unittest.TestCase):
    mysql = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = RPCApiClient(RPCData.host, RPCData.chain_host)

        if RPCData.is_check_db:
            cls.mysql = Mysql(RPCData.sql_cfg["mysql_host"], RPCData.sql_cfg["port"], RPCData.sql_cfg["user"],
                              RPCData.sql_cfg["password"], RPCData.sql_cfg["db"], True)
            cls.mysql.connect_database()

    @classmethod
    def tearDownClass(cls) -> None:
        if RPCData.is_check_db:
            cls.mysql.disconnect_database()

    def checkStandardCodeMessage(self, responseJson, code='0', message='Success'):
        """
        校验返回的标准code码和message
        :param responseJson: 接口返回的响应，json格式
        :param code: 正常情况下，code码为0
        :param message: 正确情况下，message为Success
        """
        self.assertEqual(responseJson["code"], code, f"返回的code不正确: {responseJson}")
        self.assertEqual(responseJson["message"], message, f"返回的code不正确: {responseJson}")
        # if code == "0":
        #     self.assertEqual(responseJson["code"], code, f"返回的code不正确: {responseJson}")
        #     self.assertEqual(responseJson["message"], message, f"返回的code不正确: {responseJson}")
        # elif code == "RPC10001":
        #     message = "Missing request body"
        #     self.assertEqual(responseJson["code"], code, f"返回的code不正确: {responseJson}")
        #     self.assertEqual(responseJson["message"], message, f"返回的code不正确: {responseJson}")

    def checkGetUserRequiredFieldsData(self, field_info):
        list_name = [i["name"] for i in field_info["data"]]
        self.assertEqual(len(list_name), len(set(list_name)), msg="返回的必填字段有重复数据")

    def checkgetPayoutOrderTransactionState(self, order_id, state_info):
        sql = "select * from roxe_rpc.rpc_pay_order where id = {}".format(order_id)
        db_res = self.mysql.exec_sql_query(sql)
        self.assertEqual(state_info["data"]["referenceId"], db_res[0]["referenceId"], msg="返回的referenceId不正确")
        self.assertEqual(state_info["data"]["channelOrderId"], db_res[0]["channelOrderId"], msg="返回的channelOrderId不正确")
        self.assertEqual(state_info["data"]["status"], "SUCCESS", msg="订单的状态不正确")

    # 正向
    def test_001_getPayoutMethod(self):
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info)
        self.assertEqual(method_info["data"], ["wallet"], msg="返回的出金方式不正确")

    def test_002_getUserRequiredFields(self):
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        field_info = self.client.getUserRequiredFields(basic_info, "BANK")
        self.checkStandardCodeMessage(field_info)
        self.checkGetUserRequiredFieldsData(field_info)

    def test_003_checkUserRequiredFields(self):
        # basic_info = self.client.channelsQueryRequest("RSS", "ROXE", "OUT", "PH", "PHP", "NAME", "GCASH", "wallet")
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        check_info = self.client.checkUserRequiredFields(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(check_info)
        self.assertIsNone(check_info["data"])

    # @unittest.skip
    def test_004_submitPayoutOrder_Gcash(self):
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info)
        self.assertIsNotNone(order_info["data"]["id"])
        state_info = self.client.getPayoutOrderTransactionState(order_info["data"]["id"])
        self.checkStandardCodeMessage(state_info)
        self.checkgetPayoutOrderTransactionState(order_info["data"]["id"], state_info)
        self.assertEqual(order_info["data"]["targetAmount"], payoutInfoJson["amount"])

    @unittest.skip("手动执行")
    def test_004_submitPayoutOrder_Nium(self):
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        basic_info["payoutMethod"] = "bank"
        basic_info["country"] = "SG"
        basic_info["currency"] = "SGD"
        basic_info["name"] = "NIUM"
        payoutInfoJson = {
            "referenceId": "77777766103",
            "amount": "100",
            "channelFeeDeductionMethod": 2,
            "payOutMethod": "bank",
            "pledgeAccountCurrency": "USD",
            "purpose": "Family Maintenance",
            "senderAccountType": "Individual",
            "senderFirstName": "Michael",
            "senderLastName": "L Stallman",
            "senderFullName": "Michael L Stallman",
            "senderIdType": "CCPT",
            "senderIdNumber": "12345678911234",
            "senderCountry": "US",
            "senderAddress": "beijing",
            "receiverAccountType": "Individual",
            "receiverAccountNumber": "12345678901234",
            "receiverFirstName": "Edward",
            "receiverLastName": "Nelms",
            "receiverFullName": "Edward Nelms",
            "receiverAddress": "asd",
            "receiverBankId": "LOCAL____IFSC____HDFC0000136",
            "receiverCountry": "IN",
            "receiverCurrency": "INR"
        }
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info)
        self.assertIsNotNone(order_info["data"]["id"])
        exchangeRate_info = self.client.getExchangeRate(basic_info, "USD", "INR")
        targetAmount = round(payoutInfoJson["amount"] * exchangeRate_info["data"], 2)
        self.assertAlmostEqual(order_info["data"]["targetAmount"], targetAmount, places=2, msg="返回的目标金额不正确", delta=2)

    @unittest.skip("暂不处理")
    def test_004_submitPayoutOrder_Apifiny(self):
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        basic_info["group"] = "APIFINY"
        basic_info["payoutMethod"] = "bank"
        basic_info["country"] = "US"
        basic_info["currency"] = "USD"
        basic_info["name"] = "APIFINY"
        payoutInfoJson = {
            "receiverCountry": "US",
            "receiverCity": "USD",
            "receiverCurrency": "US",
            "receiverRoutingNumber": "333",
            "receiverAccountName": "test",
            "receiverAccountNumber": "2222",
            "receiverAccountType": "test",
            "receiverBankName": "test",
            "receiverNCC": "test",
            "receiverBranchCode": "222",
            "receiverBranchName": "test",
            "receiverBIC": "222",
            "amount": "100",
            "remark": "test"
        }
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info)
        self.assertIsNotNone(order_info["data"]["id"])
        self.assertEqual(order_info["data"]["targetAmount"], payoutInfoJson["amount"])

    @unittest.skip("手动执行")
    def test_004_submitPayoutOrder_Terrapay(self):
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        basic_info["payoutMethod"] = "bank"
        basic_info["country"] = "PH"
        basic_info["currency"] = "PHP"
        basic_info["name"] = "TERRAPAY"
        payoutInfoJson = {
            "amount": "100",
            "payOutMethod": "bank",
            "senderFirstName": "AnaThree",
            "senderLastName": "AmariThree",
            "senderIdType": "nationalidcard",
            "senderIdNumber": "123456789",
            "senderIdExpireDate": "2033-09-26",
            "senderNationality": "CN",
            "senderCountry": "CN",
            "senderCity": "BeiJing",
            "senderAddress": "No. 1 chang an Avenue",
            "senderPhone": "+8613300000000",
            "senderBirthday": "1986-06-28",
            "purpose": "Gift",
            "senderSourceOfFund": "Salary",
            "senderBeneficiaryRelationship": "Friend",
            "receiverCurrency": "PHP",
            "receiverCountry": "PH",
            "receiverFirstName": "RANDY",
            "receiverLastName": "OYUGI",
            "receiverAccountNumber": "20408277204478",
            "receiverBankName": "Asia United Bank",
            "receiverBankBIC": "AUBKPHMM"
        }
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info)
        self.assertIsNotNone(order_info["data"]["id"])
        exchangeRate_info = self.client.getExchangeRate(basic_info, "USD", "PHP")
        targetAmount = round(payoutInfoJson["amount"] * exchangeRate_info["data"], 2)
        self.assertAlmostEqual(order_info["data"]["targetAmount"], targetAmount, places=2, msg="返回的目标金额不正确", delta=2)

    def test_005_getPayoutOrderTransactionState(self):
        order_id = "1506946369070276610"
        state_info = self.client.getPayoutOrderTransactionState(order_id)
        self.checkStandardCodeMessage(state_info)
        self.checkgetPayoutOrderTransactionState(order_id, state_info)

    def test_data(self):
        pass
    #     order_id = "1506946369070276610"
    #     sql = "select * from roxe_rpc.rpc_pay_order where id = {}".format(order_id)
    #     db_res = self.mysql.exec_sql_query(sql)
    #     print(db_res)

    # GCash平行测试
    @unittest.skip("暂不考虑")
    def test_006_submitPayoutOrder(self):

        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson["accountNumber"] = "09686470321"
        payoutInfoJson["receiverFirstName"] = "MYNTTEST SEAN"
        payoutInfoJson["receiverLastName"] = "DELA CRUZ"
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info)
        self.assertIsNotNone(order_info["data"]["id"])
        self.assertEqual(order_info["data"]["targetAmount"], payoutInfoJson["amount"])
        # {'code': 'RUC100001', 'message': 'Account status is not enabled', 'data': None}

    # 异常场景
    # 获取出金方式
    def test_007_getPayoutMethod_callSourceIncorrect(self):
        """callSource参数小写"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["callSource"] = "rss"
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_008_getPayoutMethod_callSourceIncorrect(self):
        """callSource参数混合大小写"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["callSource"] = "Rss"
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_009_getPayoutMethod_callSourceIncorrect(self):
        """callSource参数非规定值"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["callSource"] = "RPC"
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_010_getPayoutMethod_callSourceIncorrect(self):
        """callSource参数值为空"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["callSource"] = ""
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_011_getPayoutMethod_callSourceIncorrect(self):
        """callSource参数缺失"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body.pop("callSource")
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RUC100001", "request param channelType/callSource/group is null")
        self.assertIsNone(method_info["data"])

    def test_012_getPayoutMethod_groupIncorrect(self):
        """group参数小写"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["group"] = "roxe"
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_013_getPayoutMethod_groupIncorrect(self):
        """group参数混合大小写"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["group"] = "roXE"
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_014_getPayoutMethod_groupIncorrect(self):
        """group参数非规定值"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["group"] = "ABC"
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_015_getPayoutMethod_groupIncorrect(self):
        """group参数值为空"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["group"] = ""
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_016_getPayoutMethod_groupIncorrect(self):
        """group参数缺失"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body.pop("group")
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RUC100001", "request param channelType/callSource/group is null")
        self.assertIsNone(method_info["data"])

    def test_017_getPayoutMethod_channelTypeIncorrect(self):
        """channelType参数小写"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["channelType"] = "out"
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_018_getPayoutMethod_channelTypeIncorrect(self):
        """channelType参数混合大小写"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["channelType"] = "oUt"
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_019_getPayoutMethod_channelTypeIncorrect(self):
        """channelType参数非规定值"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["channelType"] = "ABC"
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_020_getPayoutMethod_channelTypeIncorrect(self):
        """channelType参数值为空"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["channelType"] = ""
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_021_getPayoutMethod_channelTypeIncorrect(self):
        """channelType参数缺失"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body.pop("channelType")
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RUC100001", "request param channelType/callSource/group is null")
        self.assertIsNone(method_info["data"])

    def test_022_getPayoutMethod_channelTypeIncorrect(self):
        """channelType参数值填写为入金传参IN"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["channelType"] = "IN"
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RUC100001", "no route to a specific channel")
        self.assertIsNone(method_info["data"])

    def test_023_getPayoutMethod_countryIncorrect(self):
        """country参数小写"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["country"] = "ph"
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_024_getPayoutMethod_countryIncorrect(self):
        """country参数混合大小写"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["country"] = "Ph"
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_025_getPayoutMethod_countryIncorrect(self):
        """country参数非规定值"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["country"] = "Phillipines"
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_026_getPayoutMethod_countryIncorrect(self):
        """country参数值为空"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["country"] = ""
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_027_getPayoutMethod_countryIncorrect(self):
        """country参数缺失"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body.pop("country")
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RUC100001", "country or currency can not be null")
        self.assertIsNone(method_info["data"])

    def test_028_getPayoutMethod_countryIncorrect(self):
        """country参数值传其他国家，例：印度 IN"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["country"] = "IN"
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RUC100001", "no route to a specific channel")
        self.assertIsNone(method_info["data"])

    def test_029_getPayoutMethod_currencyIncorrect(self):
        """currency参数小写"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["currency"] = "php"
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_030_getPayoutMethod_currencyIncorrect(self):
        """currency参数混合大小写"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["currency"] = "Php"
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_031_getPayoutMethod_currencyIncorrect(self):
        """currency参数非规定值"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["currency"] = "ABC"
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_032_getPayoutMethod_currencyIncorrect(self):
        """currency参数值为空"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["currency"] = ""
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_033_getPayoutMethod_currencyIncorrect(self):
        """currency参数缺失"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body.pop("currency")
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RUC100001", "country or currency can not be null")
        self.assertIsNone(method_info["data"])

    def test_034_getPayoutMethod_currencyIncorrect(self):
        """currency参数值传其他国家，例：印度卢比 INR"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["currency"] = "INR"
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RUC100001", "no route to a specific channel")
        self.assertIsNone(method_info["data"])

    def test_035_getPayoutMethod_strategyIncorrect(self):
        """strategy参数小写"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["strategy"] = ["name"]
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_036_getPayoutMethod_strategyIncorrect(self):
        """strategy参数混合大小写"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["strategy"] = ["NAme"]
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_037_getPayoutMethod_strategyIncorrect(self):
        """strategy参数非规定值"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["strategy"] = ["ABC"]
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_038_getPayoutMethod_strategyIncorrect(self):
        """strategy参数类型不正确"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["strategy"] = "NAME"
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_039_getPayoutMethod_strategyIncorrect(self):
        """strategy参数值为空"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["strategy"] = [""]
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_040_getPayoutMethod_strategyIncorrect(self):
        """strategy参数缺失，此种情况系统会默认查询第一个符合的路由返回对应通道的出金方式"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body.pop("strategy")
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info)
        self.assertEqual(method_info["data"], ["bank"], msg="返回的出金方式不正确")  # 当前配置情况会路由到NIUM（仅支持bank出金）

    def test_041_getPayoutMethod_nameIncorrect(self):
        """name参数小写"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["name"] = "gcash"
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_042_getPayoutMethod_nameIncorrect(self):
        """name参数混合大小写"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["name"] = "Gcash"
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_043_getPayoutMethod_nameIncorrect(self):
        """name参数非规定值"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["name"] = "ABC"
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_044_getPayoutMethod_nameIncorrect(self):
        """name参数值为空"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["name"] = ""
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info, "RPC10001", "Missing request body")
        self.assertIsNone(method_info["data"])

    def test_045_getPayoutMethod_nameIncorrect(self):
        """name参数缺失，此种情况系统会默认查询第一个符合的路由返回对应通道的出金方式"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body.pop("name")
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info)
        self.assertEqual(method_info["data"], ["bank"], msg="返回的出金方式不正确")  # 当前配置情况会路由到NIUM（仅支持bank出金）

    def test_046_getPayoutMethod_nameIncorrect(self):
        """当strategy参数传入值为FEE时，name传入正确值GCASH，此时会忽略name参数值，以FEE最低路由策略查询"""
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body["strategy"] = ["FEE"]
        body["name"] = "GCASH"
        body.pop("payoutMethod")
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info)
        self.assertEqual(method_info["data"], ["wallet", "bank"], msg="返回的出金方式不正确")  # 当前配置情况会路由到TERRAPAY（支持wallet、bank出金）

    # 获取出金字段
    def test_047_getUserRequiredFields_first_payoutMethodIncorrect(self):
        """payoutMethod参数大写"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        basic_info["payoutMethod"] = "WALLET"
        field_info = self.client.getUserRequiredFields(basic_info, "")  # GCASH渠道不需要读取第二个payoutMethod参数
        self.checkStandardCodeMessage(field_info, "RPC10001", "Missing request body")
        self.assertIsNone(field_info["data"])

    def test_048_getUserRequiredFields_first_payoutMethodIncorrect(self):
        """payoutMethod参数混合大小写"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        basic_info["payoutMethod"] = "WAllet"
        field_info = self.client.getUserRequiredFields(basic_info, "")  # GCASH渠道不需要读取第二个payoutMethod参数
        self.checkStandardCodeMessage(field_info, "RPC10001", "Missing request body")
        self.assertIsNone(field_info["data"])

    def test_049_getUserRequiredFields_first_payoutMethodIncorrect(self):
        """payoutMethod参数非规定值"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        basic_info["payoutMethod"] = "abc"
        field_info = self.client.getUserRequiredFields(basic_info, "")  # GCASH渠道不需要读取第二个payoutMethod参数
        self.checkStandardCodeMessage(field_info, "RPC10001", "Missing request body")
        self.assertIsNone(field_info["data"])

    def test_050_getUserRequiredFields_first_payoutMethodIncorrect(self):
        """payoutMethod参数传入其他出金方式->bank"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        basic_info["payoutMethod"] = "bank"
        field_info = self.client.getUserRequiredFields(basic_info, "")  # GCASH渠道不需要读取第二个payoutMethod参数
        self.checkStandardCodeMessage(field_info, "RUC100001", "no route to a specific channel")
        self.assertIsNone(field_info["data"])

    def test_051_getUserRequiredFields_first_payoutMethodIncorrect(self):
        """payoutMethod参数值为空"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        basic_info["payoutMethod"] = ""
        field_info = self.client.getUserRequiredFields(basic_info, "")  # GCASH渠道不需要读取第二个payoutMethod参数
        self.checkStandardCodeMessage(field_info, "RPC10001", "Missing request body")
        self.assertIsNone(field_info["data"])

    def test_052_getUserRequiredFields_first_payoutMethodIncorrect(self):
        """payoutMethod参数缺失"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        basic_info.pop("payoutMethod")
        field_info = self.client.getUserRequiredFields(basic_info, "")  # GCASH渠道不需要读取第二个payoutMethod参数
        self.checkStandardCodeMessage(field_info, "RUC100001", "payout method is null")
        self.assertIsNone(field_info["data"])

    # RPC接口中两个payoutMethod参数的部分通道读第一个部分通道读第二个，暂时这样后期可能会调整（GCASH仅读取第一个payoutMethod）
    @unittest.skip("手动执行，两个payoutMethod参数情况")
    def test_053_getUserRequiredFields_second_payoutMethodIncorrect(self):
        """payoutMethod第一个与第二个不一致"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        basic_info["payoutMethod"] = "wallet"
        field_info = self.client.getUserRequiredFields(basic_info, "bank")
        self.checkStandardCodeMessage(field_info, "RPC10001", "Missing request body")
        self.assertIsNone(field_info["data"])

    @unittest.skip("手动执行，两个payoutMethod参数情况")
    def test_054_getUserRequiredFields_second_payoutMethodIncorrect(self):
        """payoutMethod第二个大写（wallet出金）"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        basic_info["payoutMethod"] = "wallet"
        field_info = self.client.getUserRequiredFields(basic_info, "WALLET")
        self.checkStandardCodeMessage(field_info, "RPC10001", "Missing request body")
        self.assertIsNone(field_info["data"])

    @unittest.skip("手动执行，两个payoutMethod参数情况")
    def test_055_getUserRequiredFields_second_payoutMethodIncorrect(self):
        """payoutMethod第二个大写（bank出金）"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        basic_info["payoutMethod"] = "bank"
        field_info = self.client.getUserRequiredFields(basic_info, "BANK")
        self.checkStandardCodeMessage(field_info, "RPC10001", "Missing request body")
        self.assertIsNone(field_info["data"])

    @unittest.skip("手动执行，两个payoutMethod参数情况")
    def test_056_getUserRequiredFields_second_payoutMethodIncorrect(self):
        """payoutMethod第二个混合大小写"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        basic_info["payoutMethod"] = "wallet"
        field_info = self.client.getUserRequiredFields(basic_info, "Wallet")
        self.checkStandardCodeMessage(field_info, "RPC10001", "Missing request body")
        self.assertIsNone(field_info["data"])

    @unittest.skip("手动执行，两个payoutMethod参数情况")
    def test_057_getUserRequiredFields_second_payoutMethodIncorrect(self):
        """payoutMethod第二个非规定值"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        basic_info["payoutMethod"] = "wallet"
        field_info = self.client.getUserRequiredFields(basic_info, "abc")
        self.checkStandardCodeMessage(field_info, "RPC10001", "Missing request body")
        self.assertIsNone(field_info["data"])

    @unittest.skip("手动执行，两个payoutMethod参数情况")
    def test_058_getUserRequiredFields_second_payoutMethodIncorrect(self):
        """payoutMethod第二个值为空"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        basic_info["payoutMethod"] = "wallet"
        field_info = self.client.getUserRequiredFields(basic_info, "")
        self.checkStandardCodeMessage(field_info, "RPC10001", "Missing request body")
        self.assertIsNone(field_info["data"])

    @unittest.skip("手动执行，两个payoutMethod参数情况")
    def test_059_getUserRequiredFields_second_payoutMethodIncorrect(self):
        """payoutMethod第二个缺失"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        basic_info["payoutMethod"] = "wallet"
        field_info = self.client.getUserRequiredFields(basic_info, payoutMethod=None)
        self.checkStandardCodeMessage(field_info, "RPC10001", "Missing request body")
        self.assertIsNone(field_info["data"])

    def test_060_getUserRequiredFields_second_payoutMethodIncorrect(self):
        """payoutMethod两个均缺失"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        basic_info.pop("payoutMethod")
        field_info = self.client.getUserRequiredFields(basic_info, payoutMethod=None)
        self.checkStandardCodeMessage(field_info, "RUC100001", "payout method is null")
        self.assertIsNone(field_info["data"])

    # 验证出金字段
    def test_061_checkUserRequiredFields_accountNumberIncorrect(self):
        """accountNumber参数值为空"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson["accountNumber"] = ""
        check_info = self.client.checkUserRequiredFields(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(check_info, "RUC100001", "parameter error")
        self.assertIsNone(check_info["data"])

    def test_062_checkUserRequiredFields_accountNumberIncorrect(self):
        """accountNumber参数缺失"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson.pop("accountNumber")
        check_info = self.client.checkUserRequiredFields(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(check_info, "RUC100001", "parameter error")
        self.assertIsNone(check_info["data"])

    def test_063_checkUserRequiredFields_receiverCurrencyIncorrect(self):
        """receiverCurrency参数值为空"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson["receiverCurrency"] = ""
        check_info = self.client.checkUserRequiredFields(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(check_info, "RUC100001", "parameter error --> receiverCurrency : is empty")
        self.assertIsNone(check_info["data"])

    def test_064_checkUserRequiredFields_receiverCurrencyIncorrect(self):
        """receiverCurrency参数缺失"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson.pop("receiverCurrency")
        check_info = self.client.checkUserRequiredFields(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(check_info, "RUC100001", "parameter error --> receiverCurrency : is empty")
        self.assertIsNone(check_info["data"])

    def test_065_checkUserRequiredFields_amountIncorrect(self):
        """amount参数为 0"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson["amount"] = 0
        check_info = self.client.checkUserRequiredFields(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(check_info, "RUC100001", "parameter error:Amount Value is invalid")
        self.assertIsNone(check_info["data"])

    def test_066_checkUserRequiredFields_amountIncorrect(self):
        """amount参数值为负数"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson["amount"] = -10
        check_info = self.client.checkUserRequiredFields(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(check_info, "RUC100001", "parameter error:Amount Value is invalid")
        self.assertIsNone(check_info["data"])

    def test_067_checkUserRequiredFields_amountIncorrect(self):
        """amount参数值为空"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson["amount"] = ""
        check_info = self.client.checkUserRequiredFields(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(check_info, "RUC100001", "transferGCashOrder error,missing fields ")
        self.assertIsNone(check_info["data"])

    def test_068_checkUserRequiredFields_amountIncorrect(self):
        """amount参数缺失"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson.pop("amount")
        check_info = self.client.checkUserRequiredFields(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(check_info, "RUC100001", "transferGCashOrder error,missing fields ")
        self.assertIsNone(check_info["data"])

    # 下单
    def test_100_submitPayoutOrder_accountNumberIncorrect(self):
        """accountNumber参数错误填写"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson["accountNumber"] = "12345678910"
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "Parameter illegal")
        self.assertIsNone(order_info["data"])

    def test_101_submitPayoutOrder_accountNumberIncorrect(self):
        """accountNumber参数值为空"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson["accountNumber"] = ""
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "parameter error")
        self.assertIsNone(order_info["data"])

    def test_102_submitPayoutOrder_accountNumberIncorrect(self):
        """accountNumber参数缺失"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson.pop("accountNumber")
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "parameter error")
        self.assertIsNone(order_info["data"])

    def test_103_submitPayoutOrder_receiverFirstNameIncorrect(self):
        """receiverFirstName参数错误填写"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson["receiverFirstName"] = "Li"
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "Name mismatch")
        self.assertIsNone(order_info["data"])

    def test_104_submitPayoutOrder_receiverFirstNameIncorrect(self):
        """receiverFirstName参数值为空"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson["receiverFirstName"] = ""
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "parameter error --> receiverFirstName : is empty")
        self.assertIsNone(order_info["data"])

    def test_105_submitPayoutOrder_receiverFirstNameIncorrect(self):
        """receiverFirstName参数缺失"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson.pop("receiverFirstName")
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "parameter error --> receiverFirstName : is empty")
        self.assertIsNone(order_info["data"])

    def test_106_submitPayoutOrder_receiverLastNameIncorrect(self):
        """receiverLastName参数错误填写"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson["receiverLastName"] = "Si"
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "Name mismatch")
        self.assertIsNone(order_info["data"])

    def test_107_submitPayoutOrder_receiverLastNameIncorrect(self):
        """receiverLastName参数值为空"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson["receiverLastName"] = ""
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "parameter error --> receiverLastName : is empty")
        self.assertIsNone(order_info["data"])

    def test_108_submitPayoutOrder_receiverLastNameIncorrect(self):
        """receiverLastName参数缺失"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson.pop("receiverLastName")
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "parameter error --> receiverLastName : is empty")
        self.assertIsNone(order_info["data"])

    def test_109_submitPayoutOrder_receiverCurrencyIncorrect(self):
        """receiverCurrency参数错误填写"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson["receiverCurrency"] = "USD"
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "receiverCurrency is not 'PHP'")
        self.assertIsNone(order_info["data"])

    def test_110_submitPayoutOrder_receiverCurrencyIncorrect(self):
        """receiverCurrency参数值为空"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson["receiverCurrency"] = ""
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "parameter error --> receiverCurrency : is empty")
        self.assertIsNone(order_info["data"])

    def test_111_submitPayoutOrder_receiverCurrencyIncorrect(self):
        """receiverCurrency参数缺失"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson.pop("receiverCurrency")
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "parameter error --> receiverCurrency : is empty")
        self.assertIsNone(order_info["data"])

    def test_112_submitPayoutOrder_senderFirstNameIncorrect(self):
        """senderFirstName参数值为空"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson["senderFirstName"] = ""
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "parameter error --> senderFirstName : is empty")
        self.assertIsNone(order_info["data"])

    def test_113_submitPayoutOrder_senderFirstNameIncorrect(self):
        """senderFirstName参数缺失"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson.pop("senderFirstName")
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "parameter error --> senderFirstName : is empty")
        self.assertIsNone(order_info["data"])

    def test_114_submitPayoutOrder_senderBeneficiaryRelationshipIncorrect(self):
        """senderBeneficiaryRelationship参数值为空"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson["senderBeneficiaryRelationship"] = ""
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "parameter error --> senderBeneficiaryRelationship : is empty")
        self.assertIsNone(order_info["data"])

    def test_115_submitPayoutOrder_senderBeneficiaryRelationshipIncorrect(self):
        """senderBeneficiaryRelationship参数缺失"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson.pop("senderBeneficiaryRelationship")
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "parameter error --> senderBeneficiaryRelationship : is empty")
        self.assertIsNone(order_info["data"])

    def test_116_submitPayoutOrder_senderSourceOfFundIncorrect(self):
        """senderSourceOfFund参数值为空"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson["senderSourceOfFund"] = ""
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "parameter error --> senderSourceOfFund : is empty")
        self.assertIsNone(order_info["data"])

    def test_117_submitPayoutOrder_senderSourceOfFundIncorrect(self):
        """senderSourceOfFund参数缺失"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson.pop("senderSourceOfFund")
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "parameter error --> senderSourceOfFund : is empty")
        self.assertIsNone(order_info["data"])

    def test_118_submitPayoutOrder_senderIdTypeIncorrect(self):
        """senderIdType参数错误填写"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson["senderIdType"] = "identity card"
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "Parameter illegal")
        self.assertIsNone(order_info["data"])

    def test_119_submitPayoutOrder_senderIdTypeIncorrect(self):
        """senderIdType参数值为空"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson["senderIdType"] = ""
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "parameter error --> senderIdType : is empty")
        self.assertIsNone(order_info["data"])

    def test_120_submitPayoutOrder_senderIdTypeIncorrect(self):
        """senderIdType参数缺失"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson.pop("senderIdType")
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "parameter error --> senderIdType : is empty")
        self.assertIsNone(order_info["data"])

    def test_121_submitPayoutOrder_senderCountryIncorrect(self):
        """senderCountry参数错误填写"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson["senderCountry"] = "AB"
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "parameter error --> SenderCountry : is empty")
        self.assertIsNone(order_info["data"])

    def test_122_submitPayoutOrder_senderCountryIncorrect(self):
        """senderCountry参数值为空"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson["senderCountry"] = ""
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "parameter error --> SenderCountry : is empty")
        self.assertIsNone(order_info["data"])

    def test_123_submitPayoutOrder_senderCountryIncorrect(self):
        """senderCountry参数缺失"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson.pop("senderCountry")
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "parameter error --> SenderCountry : is empty")
        self.assertIsNone(order_info["data"])

    @unittest.skip("手动执行，执行前注释掉接口方法内amount替换这行")
    def test_124_submitPayoutOrder_amountIncorrect(self):
        """amount参数为 0"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson["amount"] = 0
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "parameter error:Amount Value is invalid")
        self.assertIsNone(order_info["data"])

    @unittest.skip("手动执行，执行前注释掉接口方法内amount替换这行")
    def test_125_submitPayoutOrder_amountIncorrect(self):
        """amount参数值为负数"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson["amount"] = -10
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "parameter error:Amount Value is invalid")
        self.assertIsNone(order_info["data"])

    @unittest.skip("手动执行，执行前注释掉接口方法内amount替换这行")
    def test_126_submitPayoutOrder_amountIncorrect(self):
        """amount参数值为空"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson["amount"] = ""
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "invoke GCash PayOut method failed")
        self.assertIsNone(order_info["data"])

    @unittest.skip("手动执行，执行前注释掉接口方法内amount替换这行")
    def test_127_submitPayoutOrder_amountIncorrect(self):
        """amount参数缺失"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson.pop("amount")
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "invoke GCash PayOut method failed")
        self.assertIsNone(order_info["data"])

    @unittest.skip("手动执行")
    def test_128_submitPayoutOrder_payoutInfoJsonIncorrect(self):
        """payoutInfoJson参数为空"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        # payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        payoutInfoJson = None
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "None")
        self.assertIsNone(order_info["data"])

    @unittest.skip("手动执行，调整接口方法内referenceId")
    def test_129_submitPayoutOrder_referenceIdIncorrect(self):
        """referenceId参数值为空"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "parameter error --> refNumber : is empty")
        self.assertIsNone(order_info["data"])

    @unittest.skip("手动执行，调整接口方法内referenceId")
    def test_130_submitPayoutOrder_referenceIdIncorrect(self):
        """referenceId参数缺失"""
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        payoutInfoJson = copy.deepcopy(RPCData.payoutInfoJson)
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info, "RUC100001", "payoutRequest or channelsQueryRequest or referenceId can not be null")
        self.assertIsNone(order_info["data"])

    # 查询订单状态
    def test_131_getPayoutOrderTransactionState_orderIdIncorrect(self):
        """orderId参数错误"""
        order_id = "123456"
        state_info = self.client.getPayoutOrderTransactionState(order_id)
        self.checkStandardCodeMessage(state_info, "RUC100001", "no such order")
        self.assertIsNone(state_info["data"])

    def test_132_getPayoutOrderTransactionState_orderIdIncorrect(self):
        """orderId参数错误"""
        order_id = "1234567891234567890"
        state_info = self.client.getPayoutOrderTransactionState(order_id)
        self.checkStandardCodeMessage(state_info, "RUC100001", "no such order")
        self.assertIsNone(state_info["data"])

    def test_133_getPayoutOrderTransactionState_orderIdIncorrect(self):
        """orderId参数为空"""
        order_id = ""
        state_info = self.client.getPayoutOrderTransactionState(order_id)
        self.checkStandardCodeMessage(state_info, "RUC100001", "request can not empty")
        self.assertIsNone(state_info["data"])

    def test_134_getPayoutOrderTransactionState_orderIdIncorrect(self):
        """orderId参数缺失"""
        order_id = None
        state_info = self.client.getPayoutOrderTransactionState(order_id)
        self.checkStandardCodeMessage(state_info, "RPC10001", "Required String parameter 'orderId' is not present")
        self.assertIsNone(state_info["data"])

    # Cebuana获取出金必填字段
    def test_135_getUserRequiredFields(self):
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        basic_info["payoutMethod"] = "BANK"
        basic_info["name"] = "CEBUANA"
        field_info = self.client.getUserRequiredFields(basic_info, "BANK")
        self.checkStandardCodeMessage(field_info)
        self.checkGetUserRequiredFieldsData(field_info)

    # CHECKOUT入金
    def test_136_submitPayinOrder_formCheckout(self):
        channelName = "CHECKOUT"
        payBankAccountId = "src_dxles3kr3zluned5xk4thhnjbe"
        # serviceChannelCustomerId = "cus_KdjzgIbjYRhJYt"
        payMethod = "debitCard"
        amount = "30"
        # sourceRoxeAccoun = "elkarluhdxew",
        # targetRoxeAccount = "vlni44ezjzf1",
        res = self.client.submitPayinOrder(channelName, payBankAccountId, payMethod=payMethod, amount=amount)
        rpcId = res["data"]["rpcId"]
        print(rpcId)
        self.client.getPayinOrderTransactionStateByRpcId(rpcId)

    def test_137_getPayinOrderTransactionStateByRpcId(self):
        rpcId = "1546749268582797313"
        self.client.getPayinOrderTransactionStateByRpcId(rpcId)

    # CASH出金（Cebuana）
    def test_138_getPayoutMethod_cebuana_cash(self):
        body = copy.deepcopy(RPCData.channelsQueryRequest)
        body.pop("payoutMethod")
        body["name"] = "CEBUANA"
        method_info = self.client.getPayoutMethod(body)
        self.checkStandardCodeMessage(method_info)
        self.assertEqual(method_info["data"], ["BANK", "CASH"], msg="返回的出金方式不正确")

    def test_139_getUserRequiredFields_cebuana_cash(self):
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        basic_info["name"] = "CEBUANA"
        field_info = self.client.getUserRequiredFields(basic_info, "CASH", "")
        self.checkStandardCodeMessage(field_info)
        self.checkGetUserRequiredFieldsData(field_info)

    def test_140_checkUserRequiredFields_cebuana_cash(self):
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        basic_info["name"] = "CEBUANA"
        payoutInfoJson = {
            "receiveMethodCode": "CASH",
            "amount": "10",
            "receiverCurrency": "PHP",
            "receiverFirstName": "Sean Warwick",
            "receiverLastName": "Dela Cruz",
            "receiverCountry": "PH",
            "senderFirstName": "ZHANG",
            "senderLastName": "SAN",
            "senderCountry": "US",
            "pledgeAccountCurrency": "USD"
        }
        check_info = self.client.checkUserRequiredFields(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(check_info)
        self.assertIsNone(check_info["data"])

    def test_141_submitPayoutOrder_cebuana_cash(self):
        basic_info = copy.deepcopy(RPCData.channelsQueryRequest)
        basic_info["name"] = "CEBUANA"
        payoutInfoJson = {
            "receiveMethodCode": "CASH",
            "amount": "10",
            "receiverCurrency": "PHP",
            "receiverFirstName": "Sean Warwick",
            "receiverLastName": "Dela Cruz",
            "receiverCountry": "PH",
            "senderFirstName": "ZHANG",
            "senderLastName": "SAN",
            "senderCountry": "US",
            "pledgeAccountCurrency": "USD"
        }
        order_info = self.client.submitPayoutOrder(basic_info, payoutInfoJson)
        self.checkStandardCodeMessage(order_info)
        self.assertIsNotNone(order_info["data"]["id"])
        order_state_info = self.client.getPayoutOrderTransactionState(order_info["data"]["id"])
        assert order_state_info["data"]["status"] in ["PROCESSING", "SUCCESS"], "订单未提交成功"