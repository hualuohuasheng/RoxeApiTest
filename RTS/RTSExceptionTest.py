# coding=utf-8
# author: ROXE
# date: 2022-7-10


import json
import traceback
from contextlib import contextmanager
import requests
import unittest
import copy
import time
from .RtsApiTest_V3 import RTSData, RTSApiClient, ApiUtils, BaseCheckRTS

from roxe_libs.Global import Global
from roxe_libs import settings
from .RTSStatusCode import RtsCodEnum

class RTSExceptionTest(BaseCheckRTS):

    # 获取支持的转账币种
    def test_001_getTransactionCurrency_sendCountry_lower(self):
        res_data, body = self.client.getTransactionCurrency("us")
        self.checkCodeAndMessage(res_data)
        self.assertEqual(res_data["data"], [])

    def test_002_getTransactionCurrency_sendCurrency_mix(self):
        res_data, body = self.client.getTransactionCurrency("", "usD")
        self.checkCodeAndMessage(res_data)
        self.assertEqual(res_data["data"], [])

    def test_003_getTransactionCurrency_receiveCountry_mix(self):
        res_data, body = self.client.getTransactionCurrency("", "", "Us")
        self.checkCodeAndMessage(res_data)
        self.assertEqual(res_data["data"], [])

    def test_004_getTransactionCurrency_receiveCurrency_lower(self):
        res_data, body = self.client.getTransactionCurrency("", "", "", "usd")
        self.checkCodeAndMessage(res_data)
        self.assertEqual(res_data["data"], [])

    def test_005_getTransactionCurrency_sendCountry_error(self):
        res_data, body = self.client.getTransactionCurrency("aa")
        self.checkCodeAndMessage(res_data)
        self.assertEqual(res_data["data"], [])

    def test_006_getTransactionCurrency_sendCurrency_error(self):
        res_data, body = self.client.getTransactionCurrency("", "abc")
        self.checkCodeAndMessage(res_data)
        self.assertEqual(res_data["data"], [])

    def test_007_getTransactionCurrency_sendCountry_sendCurrency_Mismatch(self):
        res_data, body = self.client.getTransactionCurrency("USD", "DE")
        self.checkCodeAndMessage(res_data)
        self.assertEqual(res_data["data"], [])

    def test_008_getTransactionCurrency_returnAllCurrency_error(self):
        res_data, body = self.client.getTransactionCurrency("", "", "", "", returnAllCurrency="abc")
        self.assertEqual(res_data["code"], "01100000")
        self.assertEqual(res_data["message"], "data structure error")
        self.assertIsNone(res_data["data"])

    def test_009_getTransactionCurrency_sendCountry_missing(self):
        res_data, body = self.client.getTransactionCurrency(popKey="sendCountry")
        self.client.checkCodeAndMessage(res_data)
        assert len(res_data["data"]) > 0

    def test_010_getTransactionCurrency_receiveCurrency_missing(self):
        res_data, body = self.client.getTransactionCurrency(popKey="receiveCurrency")
        self.client.checkCodeAndMessage(res_data)
        assert len(res_data["data"]) > 0

    # 获取支持的收款类型
    def test_011_getPayoutMethod_receiveNodeCode_isNone(self):
        res_data, body = self.client.getPayoutMethod("", "US", "USD")
        self.assertEqual(res_data["code"], "01100000")
        self.assertEqual(res_data["message"], "nodeCode is empty")
        self.assertIsNone(res_data["data"])

    def test_012_getPayoutMethod_receiveNodeCode_error(self):
        res_data, body = self.client.getPayoutMethod("abc", "US", "USD")
        self.assertEqual(res_data["code"], "01100000")
        self.assertEqual(res_data["message"], "nodeCode is error")
        self.assertIsNone(res_data["data"])

    def test_013_getPayoutMethod_receiveCountry_isNone(self):
        res_data, body = self.client.getPayoutMethod(RTSData.node_code_sn["US"], "", "USD")
        self.assertEqual(res_data["code"], "01100000")
        self.assertEqual(res_data["message"], "receiveCountry is empty")
        self.assertIsNone(res_data["data"])

    @unittest.skip("文档已修改，接口无receiveCountry参数")
    def test_014_getPayoutMethod_receiveCountry_isLower(self):
        res_data, body = self.client.getPayoutMethod(RTSData.node_code_sn["US"], "us", "USD")
        self.client.checkCodeAndMessage(res_data)
        self.assertEqual(res_data["data"]["receiveMethodCode"], [])

    @unittest.skip("文档已修改，接口无receiveCountry参数")
    def test_015_getPayoutMethod_receiveCountry_mix(self):
        res_data, body = self.client.getPayoutMethod(RTSData.node_code_sn["US"], "Us", "USD")
        self.client.checkCodeAndMessage(res_data)
        self.assertEqual(res_data["data"]["receiveMethodCode"], [])

    @unittest.skip("文档已修改，接口无receiveCountry参数")
    def test_016_getPayoutMethod_receiveCountry_error(self):
        res_data, body = self.client.getPayoutMethod(RTSData.node_code_sn["US"], "ab", "USD")
        self.client.checkCodeAndMessage(res_data)
        self.assertEqual(res_data["data"]["receiveMethodCode"], [])

    def test_017_getPayoutMethod_receiveCurrency_isNone(self):
        res_data, body = self.client.getPayoutMethod(RTSData.node_code_sn["US"], "US", "")
        self.assertEqual(res_data["code"], "01100000")
        self.assertEqual(res_data["message"], "receiveCurrency is empty")
        self.assertIsNone(res_data["data"])

    def test_018_getPayoutMethod_receiveCurrency_isLower(self):
        res_data, body = self.client.getPayoutMethod(RTSData.node_code_sn["US"], "US", "usd")
        self.assertEqual(res_data["code"], "01100100")
        self.assertEqual(res_data["message"], 'node error: {"code":"0x000002","message":"outCurrency no support"}')
        self.assertIsNone(res_data["data"])

    def test_019_getPayoutMethod_receiveCurrency_mix(self):
        res_data, body = self.client.getPayoutMethod(RTSData.node_code_sn["US"], "US", "usD")
        self.assertEqual(res_data["code"], "01100100")
        self.assertEqual(res_data["message"], 'node error: {"code":"0x000002","message":"outCurrency no support"}')
        self.assertIsNone(res_data["data"])

    def test_020_getPayoutMethod_receiveCurrency_error(self):
        res_data, body = self.client.getPayoutMethod(RTSData.node_code_sn["US"], "US", "abc")
        self.assertEqual(res_data["code"], "01100100")
        self.assertEqual(res_data["message"], 'node error: {"code":"0x000002","message":"outCurrency no support"}')
        self.assertIsNone(res_data["data"])

    # 获取汇入列表
    def test_021_getReceiverRequiredFields_receiveNodeCode_isNone(self):
        res_data, body = self.client.getReceiverRequiredFields("", "USD")
        self.assertEqual(res_data["code"], "01100000")
        self.assertEqual(res_data["message"], "nodeCode is empty")
        self.assertIsNone(res_data["data"])

    def test_022_getReceiverRequiredFields_receiveNodeCode_error(self):
        res_data, body = self.client.getReceiverRequiredFields("abc", "USD")
        self.assertEqual(res_data["code"], "01100000")
        self.assertEqual(res_data["message"], "nodeCode is error")
        self.assertIsNone(res_data["data"])

    def test_023_getReceiverRequiredFields_receiveCurrency_isNone(self):
        res_data, body = self.client.getReceiverRequiredFields(RTSData.node_code_sn["US"], "")
        self.assertEqual(res_data["code"], "01100000")
        self.assertEqual(res_data["message"], "currency is empty")
        self.assertIsNone(res_data["data"])

    def test_024_getReceiverRequiredFields_receiveCurrency_isLower(self):
        res_data, body = self.client.getReceiverRequiredFields(RTSData.node_code_sn["US"], "usd")
        self.assertEqual(res_data["code"], "01100100")
        self.assertEqual(res_data["message"], 'node error: {"code":"0x000002","message":"outCurrency no support"}')
        self.assertIsNone(res_data["data"])

    def test_025_getReceiverRequiredFields_receiveCurrency_mix(self):
        res_data, body = self.client.getReceiverRequiredFields(RTSData.node_code_sn["US"], "usD")
        self.assertEqual(res_data["code"], "01100100")
        self.assertEqual(res_data["message"], 'node error: {"code":"0x000002","message":"outCurrency no support"}')
        self.assertIsNone(res_data["data"])

    def test_026_getReceiverRequiredFields_receiveCurrency_error(self):
        res_data, body = self.client.getReceiverRequiredFields(RTSData.node_code_sn["US"], "abc")
        self.assertEqual(res_data["code"], "01100100")
        self.assertEqual(res_data["message"], 'node error: {"code":"0x000002","message":"outCurrency no support"}')
        self.assertIsNone(res_data["data"])

    def test_027_getReceiverRequiredFields_businessType_isLower(self):
        res_data, body = self.client.getReceiverRequiredFields(RTSData.node_code_sn["US"], "USD", "c2c")
        self.assertEqual(res_data["code"], "01100000")
        self.assertEqual(res_data["message"], "The businessType parameter is invalid")
        self.assertIsNone(res_data["data"])

    def test_028_getReceiverRequiredFields_businessType_mix(self):
        res_data, body = self.client.getReceiverRequiredFields(RTSData.node_code_sn["US"], "USD", "C2c")
        self.assertEqual(res_data["code"], "01100000")
        self.assertEqual(res_data["message"], "The businessType parameter is invalid")
        self.assertIsNone(res_data["data"])

    def test_029_getReceiverRequiredFields_businessType_error(self):
        res_data, body = self.client.getReceiverRequiredFields(RTSData.node_code_sn["US"], "USD", "def")
        self.assertEqual(res_data["code"], "01100000")
        self.assertEqual(res_data["message"], "The businessType parameter is invalid")
        self.assertIsNone(res_data["data"])

    def test_030_getReceiverRequiredFields_receiveMethodCode_isLower(self):
        res_data, body = self.client.getReceiverRequiredFields(RTSData.node_code_sn["US"], "USD", receiveMethodCode="bank")
        self.assertEqual(res_data["code"], "01100000")
        self.assertEqual(res_data["message"], "The receiveMethodCode parameter is invalid")
        self.assertIsNone(res_data["data"])

    def test_031_getReceiverRequiredFields_receiveMethodCode_mix(self):
        res_data, body = self.client.getReceiverRequiredFields(RTSData.node_code_sn["US"], "USD", receiveMethodCode="Bank")
        self.assertEqual(res_data["code"], "01100000")
        self.assertEqual(res_data["message"], "The receiveMethodCode parameter is invalid")
        self.assertIsNone(res_data["data"])

    def test_032_getReceiverRequiredFields_receiveMethodCode_error(self):
        res_data, body = self.client.getReceiverRequiredFields(RTSData.node_code_sn["US"], "USD", receiveMethodCode="egh")
        self.assertEqual(res_data["code"], "01100000")
        self.assertEqual(res_data["message"], "The receiveMethodCode parameter is invalid")
        self.assertIsNone(res_data["data"])

    def test_033_getReceiverRequiredFields_receiveMethodCode_notMatchNode(self):
        res_data, body = self.client.getReceiverRequiredFields(RTSData.node_code_sn["US"], "USD", receiveMethodCode="EWALLET")
        self.assertEqual(res_data["code"], "01100100")
        self.assertEqual(res_data["message"], 'node error: {"code":"0x000004","message":"RPC getUserRequiredFields: no route to a specific channel"}')
        self.assertIsNone(res_data["data"])

    # 校验汇入表单
    def test_034_checkReceiverRequiredFields_receiveNodeCode_isNone(self):
        receiveNodeCode = RTSData.node_code_sn["GB"]
        receiveCurrency = "GBP"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency, "C2C", "BANK")
        receiveInfo = self.makeReceiveInfo(res, body)
        res_data, body = self.client.checkReceiverRequiredFields("", receiveCurrency, receiveInfo)
        self.assertEqual(res_data["code"], "01100000")
        self.assertEqual(res_data["message"], "nodeCode is empty")
        self.assertIsNone(res_data["data"])

    def test_035_checkReceiverRequiredFields_receiveNodeCode_error(self):
        receiveNodeCode = RTSData.node_code_sn["GB"]
        receiveCurrency = "GBP"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency, "C2C", "BANK")
        receiveInfo = self.makeReceiveInfo(res, body)
        res_data, body = self.client.checkReceiverRequiredFields("abc", receiveCurrency, receiveInfo)
        self.assertEqual(res_data["code"], "01100000")
        self.assertEqual(res_data["message"], "nodeCode is error")
        self.assertIsNone(res_data["data"])

    def test_036_checkReceiverRequiredFields_receiveCurrency_isNone(self):
        receiveNodeCode = RTSData.node_code_sn["GB"]
        receiveCurrency = "GBP"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency, "C2C", "BANK")
        receiveInfo = self.makeReceiveInfo(res, body)
        res_data, body = self.client.checkReceiverRequiredFields(receiveNodeCode, "", receiveInfo)
        self.assertEqual(res_data["code"], "01100000")
        self.assertEqual(res_data["message"], "currency is empty")
        self.assertIsNone(res_data["data"])

    def test_037_checkReceiverRequiredFields_receiveCurrency_isLower(self):
        receiveNodeCode = RTSData.node_code_sn["GB"]
        receiveCurrency = "GBP"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency, "C2C", "BANK")
        receiveInfo = self.makeReceiveInfo(res, body)
        res_data, body = self.client.checkReceiverRequiredFields(receiveNodeCode, "gbp", receiveInfo)
        self.client.checkCodeAndMessage(res_data)
        self.assertEqual(res_data["data"]["message"], "node error: {\"code\":\"0x000002\",\"message\":\"outCurrency no support\"}")
        self.assertFalse(res_data["data"]["verified"])

    def test_038_checkReceiverRequiredFields_receiveCurrency_mix(self):
        receiveNodeCode = RTSData.node_code_sn["GB"]
        receiveCurrency = "GBP"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency, "C2C", "BANK")
        receiveInfo = self.makeReceiveInfo(res, body)
        res_data, body = self.client.checkReceiverRequiredFields(receiveNodeCode, "gBp", receiveInfo)
        self.client.checkCodeAndMessage(res_data)
        self.assertEqual(res_data["data"]["message"], "node error: {\"code\":\"0x000002\",\"message\":\"outCurrency no support\"}")
        self.assertFalse(res_data["data"]["verified"])

    def test_039_checkReceiverRequiredFields_receiveCurrency_error(self):
        receiveNodeCode = RTSData.node_code_sn["GB"]
        receiveCurrency = "GBP"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency, "C2C", "BANK")
        receiveInfo = self.makeReceiveInfo(res, body)
        res_data, body = self.client.checkReceiverRequiredFields(receiveNodeCode, "abc", receiveInfo)
        self.client.checkCodeAndMessage(res_data)
        self.assertEqual(res_data["data"]["message"], "node error: {\"code\":\"0x000002\",\"message\":\"outCurrency no support\"}")
        self.assertFalse(res_data["data"]["verified"])

    def test_040_checkReceiverRequiredFields_receiveInfo_isNone(self):
        receiveNodeCode = RTSData.node_code_sn["GB"]
        receiveCurrency = "GBP"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency, "C2C", "BANK")
        receiveInfo = self.makeReceiveInfo(res, body)
        res_data, body = self.client.checkReceiverRequiredFields(receiveNodeCode, receiveCurrency, "")
        self.assertEqual(res_data["code"], "01100000")
        self.assertEqual(res_data["message"], "info is empty")
        self.assertIsNone(res_data["data"])

    def test_041_checkReceiverRequiredFields_receiveInfo_isList(self):
        receiveNodeCode = RTSData.node_code_sn["GB"]
        receiveCurrency = "GBP"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency, "C2C", "BANK")
        receiveInfo = self.makeReceiveInfo(res, body)
        res_data, body = self.client.checkReceiverRequiredFields(receiveNodeCode, receiveCurrency, [receiveInfo])
        self.assertEqual(res_data["code"], "01100000")
        self.assertEqual(res_data["message"], "data structure error")
        self.assertIsNone(res_data["data"])

    def test_042_checkReceiverRequiredFields_receiveInfo_internalFieldMissing(self):
        receiveNodeCode = RTSData.node_code_sn["GB"]
        receiveCurrency = "GBP"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency, "C2C", "BANK")
        receiveInfo = self.makeReceiveInfo(res, body)
        receiveInfo.pop("receiverCurrency")
        res_data, body = self.client.checkReceiverRequiredFields(receiveNodeCode, receiveCurrency, receiveInfo)
        self.checkCodeAndMessage(res_data)
        self.assertEqual(res_data["data"]["message"], "node error: {\"code\":\"0x000002\",\"message\":\"outInfo receiveCurrency is empty\"}")
        self.assertFalse(res_data["data"]["verified"])

    def test_043_checkReceiverRequiredFields_businessType_isLower(self):
        receiveNodeCode = RTSData.node_code_sn["GB"]
        receiveCurrency = "GBP"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency, "C2C", "BANK")
        receiveInfo = self.makeReceiveInfo(res, body)
        res_data, body = self.client.checkReceiverRequiredFields(receiveNodeCode, receiveCurrency, receiveInfo, businessType="c2c")
        self.assertEqual(res_data["code"], "01100000")
        self.assertEqual(res_data["message"], "data structure error")
        self.assertIsNone(res_data["data"])

    def test_044_checkReceiverRequiredFields_businessType_mix(self):
        receiveNodeCode = RTSData.node_code_sn["GB"]
        receiveCurrency = "GBP"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency, "C2C", "BANK")
        receiveInfo = self.makeReceiveInfo(res, body)
        res_data, body = self.client.checkReceiverRequiredFields(receiveNodeCode, receiveCurrency, receiveInfo, businessType="C2c")
        self.assertEqual(res_data["code"], "01100000")
        self.assertEqual(res_data["message"], "data structure error")
        self.assertIsNone(res_data["data"])

    def test_045_checkReceiverRequiredFields_businessType_error(self):
        receiveNodeCode = RTSData.node_code_sn["GB"]
        receiveCurrency = "GBP"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency, "C2C", "BANK")
        receiveInfo = self.makeReceiveInfo(res, body)
        res_data, body = self.client.checkReceiverRequiredFields(receiveNodeCode, receiveCurrency, receiveInfo, businessType="egh")
        self.assertEqual(res_data["code"], "01100000")
        self.assertEqual(res_data["message"], "data structure error")
        self.assertIsNone(res_data["data"])

    def test_046_checkReceiverRequiredFields_businessType_notMatchType(self):
        receiveNodeCode = RTSData.node_code_sn["GB"]
        receiveCurrency = "GBP"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency, "C2C", "BANK")
        receiveInfo = self.makeReceiveInfo(res, body)
        res_data, body = self.client.checkReceiverRequiredFields(receiveNodeCode, receiveCurrency, receiveInfo, businessType="B2C")
        self.client.checkCodeAndMessage(res_data)
        self.assertEqual(res_data["data"]["message"], "node error: {\"code\":\"0x000001\",\"message\":\"Rpc payout form check: RPC check: parameter is missing: at least one of [senderOrgBIC, senderOrgLei, senderOrgIdNumber] must be filled in\"}")
        self.assertFalse(res_data["data"]["verified"])

    def test_047_checkReceiverRequiredFields_businessType_notMatchMethod(self):
        receiveNodeCode = RTSData.gcash_node
        receiveCurrency = "PHP"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency, "C2C", "EWALLET")
        receiveInfo = self.makeReceiveInfo(res, body)
        receiveInfo["receiveMethodCode"] = "BANK"
        receiveInfo["receiverWalletCode"] = "GCASH"
        res_data, body = self.client.checkReceiverRequiredFields(receiveNodeCode, receiveCurrency, receiveInfo)
        self.client.checkCodeAndMessage(res_data)
        self.assertEqual(res_data["data"]["message"], "node error: {\"code\":\"0x000001\",\"message\":\"Rpc payout form check: RPC check: no route to a specific channel\"}")
        self.assertFalse(res_data["data"]["verified"])

    def test_048_checkReceiverRequiredFields_receiveMethodCode_receiverWalletCodeError(self):
        receiveNodeCode = RTSData.gcash_node
        receiveCurrency = "PHP"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency, "C2C", "EWALLET")
        receiveInfo = self.makeReceiveInfo(res, body)
        receiveInfo["receiverWalletCode"] = "ABCDE"
        res_data, body = self.client.checkReceiverRequiredFields(receiveNodeCode, receiveCurrency, receiveInfo)  # , receiveMethodCode="EWALLET"
        self.client.checkCodeAndMessage(res_data)
        self.assertEqual(res_data["data"]["message"], "node error: {\"code\":\"0x000001\",\"message\":\"Rpc payout form check: RPC check: no match ewalletCode,Gcash corridor is GCASH\"}")
        self.assertFalse(res_data["data"]["verified"])

    # 获取路由列表
    def test_049_getRouterList_ro2ro_routerStrategy_error(self):
        res_router, body = self.client.getRouterList("USD.ROXE", "USD.ROXE", routerStrategy="abcdefg")
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "routerStrategy error")
        self.assertIsNone(res_router["data"])

    def test_050_getRouterList_fait2fait_snsn_routerStrategy_error(self):
        res_router, body = self.client.getRouterList("USD", "PHP", sendNodeCode=RTSData.checkout_node, receiveNodeCode=RTSData.terrapay_node_ph, routerStrategy="abcdefg")
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "routerStrategy error")
        self.assertIsNone(res_router["data"])

    def test_051_getRouterList_fait2fait_pnsnsnpn_routerStrategy_error(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendNodeCode="pnuzj1hpyxxx", receiveNodeCode="pnuzj1hpyyyy", routerStrategy="abcdefg")
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "routerStrategy error")
        self.assertIsNone(res_router["data"])

    def test_052_getRouterList_ro2fait_businessType_isLower(self):
        res_router, body = self.client.getRouterList("USD.ROXE", "PHP", receiveNodeCode=RTSData.terrapay_node_ph, businessType="c2c")
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "businessType error")
        self.assertIsNone(res_router["data"])

    def test_053_getRouterList_fait2fait_snsn_businessType_isLower(self):
        res_router, body = self.client.getRouterList("USD", "PHP", sendNodeCode=RTSData.checkout_node, receiveNodeCode=RTSData.terrapay_node_ph, businessType="c2c")
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "businessType error")
        self.assertIsNone(res_router["data"])

    def test_054_getRouterList_fait2fait_pnsnsn_businessType_mix(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendNodeCode=RTSData.node_code_pn["US"], receiveNodeCode=RTSData.node_code_sn["US"], businessType="C2b")
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "businessType error")
        self.assertIsNone(res_router["data"])

    def test_055_getRouterList_fait2fait_snsnpn_businessType_mix(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendNodeCode=RTSData.node_code_sn["US"], receiveNodeCode=RTSData.node_code_pn["US"], businessType="c2B")
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "businessType error")
        self.assertIsNone(res_router["data"])

    def test_056_getRouterList_ro2fait_businessType_error(self):
        res_router, body = self.client.getRouterList("USD.ROXE", "PHP", receiveNodeCode=RTSData.terrapay_node_ph, businessType="ABC")
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "businessType error")
        self.assertIsNone(res_router["data"])

    def test_057_getRouterList_fait2fait_pnsnsnpn_businessType_error(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendNodeCode="pnuzj1hpyxxx", receiveNodeCode="pnuzj1hpyyyy", businessType="123")
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "businessType error")
        self.assertIsNone(res_router["data"])

    def test_058_getRouterList_fait2fait_pnsnsnpn_businessType_typeError(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendNodeCode="pnuzj1hpyxxx", receiveNodeCode="pnuzj1hpyyyy", businessType=123)
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "businessType error")
        self.assertIsNone(res_router["data"])

    def test_059_getRouterList_fait2fait_snsn_isReturnOrder_error(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendNodeCode=RTSData.node_code_sn["US"], receiveNodeCode=RTSData.node_code_sn["US"], isReturnOrder="abcd")
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "data structure error")
        self.assertIsNone(res_router["data"])

    def test_060_getRouterList_fait2ro_inSendCountry_isLower(self):
        res_router, body = self.client.getRouterList("USD", "USD.ROXE", sendCountry="us")
        self.client.checkCodeAndMessage(res_router)
        self.assertEqual(res_router["data"]["roxeRouters"], [])

    def test_061_getRouterList_fait2fait_snsn_inSendCountry_isLower(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendCountry="us", receiveNodeCode=RTSData.node_code_sn["US"])
        self.client.checkCodeAndMessage(res_router)
        self.assertEqual(res_router["data"]["roxeRouters"], [])

    def test_062_getRouterList_fait2fait_snsn_inSendCountry_mix(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendCountry="Us", receiveNodeCode=RTSData.node_code_sn["US"])
        self.client.checkCodeAndMessage(res_router)
        self.assertEqual(res_router["data"]["roxeRouters"], [])

    def test_063_getRouterList_fait2fait_pnsnsnpn_inSendCountry_mix(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendCountry="Us", receiveNodeCode="pnuzj1hpyyyy")
        self.client.checkCodeAndMessage(res_router)
        self.assertEqual(res_router["data"]["roxeRouters"], [])

    def test_064_getRouterList_fait2ro_inSendCountry_error(self):
        res_router, body = self.client.getRouterList("USD", "USD.ROXE", sendCountry="AA")
        self.client.checkCodeAndMessage(res_router)
        self.assertEqual(res_router["data"]["roxeRouters"], [])

    def test_065_getRouterList_fait2fait_snsnpn_inSendCountry_error(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendCountry="BB", receiveNodeCode=RTSData.node_code_pn["US"])
        self.client.checkCodeAndMessage(res_router)
        self.assertEqual(res_router["data"]["roxeRouters"], [])

    def test_066_getRouterList_fait2ro_sendNodeCode_error(self):
        res_router, body = self.client.getRouterList("USD", "USD.ROXE", sendNodeCode="111111111111111")
        self.client.checkCodeAndMessage(res_router)
        self.assertEqual(res_router["data"]["roxeRouters"], [])

    def test_067_getRouterList_fait2fait_snsn_sendNodeCode_error(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendNodeCode="abcdefg", receiveCountry="US")
        self.client.checkCodeAndMessage(res_router)
        self.assertEqual(res_router["data"]["roxeRouters"], [])

    def test_068_getRouterList_fait2ro_sendCountryAndSendNodeCode_empty(self):
        res_router, body = self.client.getRouterList("USD", "USD.ROXE")
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "sendNodeCode and sendCountry are both empty")
        self.assertIsNone(res_router["data"])

    def test_069_getRouterList_ro2ro_sendCurrency_isLower(self):
        res_router, body = self.client.getRouterList("usd.roxe", "USD.ROXE")
        self.client.checkCodeAndMessage(res_router)
        self.assertEqual(res_router["data"]["roxeRouters"], [])

    def test_070_getRouterList_fait2ro_sendCurrency_isLower(self):
        res_router, body = self.client.getRouterList("usd", "USD.ROXE", sendNodeCode=RTSData.checkout_node)
        self.client.checkCodeAndMessage(res_router)
        self.assertEqual(res_router["data"]["roxeRouters"], [])

    def test_071_getRouterList_ro2fait_sendCurrency_mix(self):
        res_router, body = self.client.getRouterList("uSD.ROXE", "PHP", receiveNodeCode=RTSData.terrapay_node_ph)
        self.client.checkCodeAndMessage(res_router)
        self.assertEqual(res_router["data"]["roxeRouters"], [])

    def test_072_getRouterList_fait2fait_snsn_sendCurrency_mix(self):
        res_router, body = self.client.getRouterList("UsD", "PHP", sendNodeCode=RTSData.checkout_node, receiveNodeCode=RTSData.terrapay_node_ph)
        self.client.checkCodeAndMessage(res_router)
        self.assertEqual(res_router["data"]["roxeRouters"], [])

    def test_073_getRouterList_fait2fait_pnsnsn_sendCurrency_error(self):
        res_router, body = self.client.getRouterList("111", "GBP", sendNodeCode=RTSData.node_code_pn["US"], receiveNodeCode=RTSData.node_code_sn["GB"])
        self.client.checkCodeAndMessage(res_router)
        self.assertEqual(res_router["data"]["roxeRouters"], [])

    def test_074_getRouterList_ro2ro_sendCurrency_empty(self):
        res_router, body = self.client.getRouterList("", "USD.ROXE")
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "sendCurrency is empty")

    def test_075_getRouterList_fait2fait_snsnpn_sendCurrency_empty(self):
        res_router, body = self.client.getRouterList("", "USD", sendNodeCode=RTSData.node_code_sn["US"], receiveNodeCode=RTSData.node_code_pn["US"], routerStrategy="LOWEST_FEE")
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "sendCurrency is empty")

    def test_076_getRouterList_ro2ro_sendCurrency_sendAmount_0(self):
        res_router, body = self.client.getRouterList("USD.ROXE", "USD.ROXE", sendAmount="0")
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "amount cannot be empty and amount must be > 0")
        self.assertIsNone(res_router["data"])

    def test_077_getRouterList_fait2fait_snsn_sendAmount_0(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendNodeCode=RTSData.node_code_sn["US"], receiveNodeCode=RTSData.mock_node, sendAmount="0")
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "amount cannot be empty and amount must be > 0")
        self.assertIsNone(res_router["data"])

    def test_078_getRouterList_ro2fait_sendAmount_empty(self):
        res_router, body = self.client.getRouterList("USD.ROXE", "PHP", receiveCountry="PH", sendAmount="", popKey="sendAmount")
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "amount cannot be empty and amount must be > 0")
        self.assertIsNone(res_router["data"])

    def test_079_getRouterList_fait2fait_snsn_sendAmount_negativeNumber(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendNodeCode=RTSData.node_code_sn["US"], receiveNodeCode=RTSData.mock_node, sendAmount=-10)
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "amount cannot be empty and amount must be > 0")
        self.assertIsNone(res_router["data"])

    def test_080_getRouterList_fait2fait_snsn_sendAmount_error(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendNodeCode=RTSData.node_code_sn["US"], receiveNodeCode=RTSData.mock_node, sendAmount="abc")
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "data structure error")
        self.assertIsNone(res_router["data"])

    def test_081_getRouterList_ro2fait_inReceiveCountry_isLower(self):
        res_router, body = self.client.getRouterList("USD.ROXE", "PHP", receiveCountry="ph")
        self.client.checkCodeAndMessage(res_router)
        self.assertEqual(res_router["data"]["roxeRouters"], [])

    def test_082_getRouterList_fait2fait_snsn_inReceiveCountry_isLower(self):
        res_router, body = self.client.getRouterList("USD", "GBP", sendNodeCode=RTSData.node_code_sn["US"], receiveCountry="gb")
        self.client.checkCodeAndMessage(res_router)
        self.assertEqual(res_router["data"]["roxeRouters"], [])

    def test_083_getRouterList_fait2fait_snsn_inReceiveCountry_mix(self):
        res_router, body = self.client.getRouterList("USD", "GBP", sendNodeCode=RTSData.node_code_sn["US"], receiveCountry="Gb")
        self.client.checkCodeAndMessage(res_router)
        self.assertEqual(res_router["data"]["roxeRouters"], [])

    def test_084_getRouterList_fait2fait_pnsnsn_inReceiveCountry_mix(self):
        res_router, body = self.client.getRouterList("USD", "GBP", sendNodeCode=RTSData.node_code_pn["US"], receiveCountry="gB")
        self.client.checkCodeAndMessage(res_router)
        self.assertEqual(res_router["data"]["roxeRouters"], [])

    def test_085_getRouterList_fait2fait_snsnpn_inReceiveCountry_error(self):
        res_router, body = self.client.getRouterList("USD", "GBP", sendNodeCode=RTSData.node_code_sn["US"], receiveCountry="1111")
        self.client.checkCodeAndMessage(res_router)
        self.assertEqual(res_router["data"]["roxeRouters"], [])

    def test_086_getRouterList_fait2fait_pnsnsnpn_inReceiveCountry_error(self):
        res_router, body = self.client.getRouterList("USD", "GBP", sendNodeCode=RTSData.node_code_pn["US"], receiveCountry="abcde")
        self.client.checkCodeAndMessage(res_router)
        self.assertEqual(res_router["data"]["roxeRouters"], [])

    def test_087_getRouterList_ro2fait_inReceiveNodeCode_error(self):
        res_router, body = self.client.getRouterList("USD.ROXE", "PHP", receiveNodeCode="11111111")
        self.client.checkCodeAndMessage(res_router)
        self.assertEqual(res_router["data"]["roxeRouters"], [])

    def test_088_getRouterList_fait2fait_pnsnsn_inReceiveNodeCode_error(self):
        res_router, body = self.client.getRouterList("USD", "GBP", sendNodeCode=RTSData.node_code_pn["US"], receiveNodeCode="abcdefg")
        self.client.checkCodeAndMessage(res_router)
        self.assertEqual(res_router["data"]["roxeRouters"], [])

    def test_089_getRouterList_fait2fait_snsnpn_receiveCountryAndReceiveNodeCode_empty(self):
        res_router, body = self.client.getRouterList("USD", "GBP", sendNodeCode=RTSData.node_code_sn["US"])
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "receiveNodeCode and receiveCountry are both empty")
        self.assertIsNone(res_router["data"])

    def test_090_getRouterList_fait2ro_receiveCurrency_isLower(self):
        res_router, body = self.client.getRouterList("USD", "usd.roxe", sendNodeCode=RTSData.checkout_node)
        self.client.checkCodeAndMessage(res_router)
        self.assertEqual(res_router["data"]["roxeRouters"], [])

    def test_091_getRouterList_ro2fait_receiveCurrency_mix(self):
        res_router, body = self.client.getRouterList("USD.ROXE", "PHp", receiveNodeCode=RTSData.terrapay_node_ph)
        self.client.checkCodeAndMessage(res_router)
        self.assertEqual(res_router["data"]["roxeRouters"], [])

    def test_092_getRouterList_fait2fait_pnsnsn_receiveCurrency_error(self):
        res_router, body = self.client.getRouterList("USD", "111", sendNodeCode=RTSData.node_code_pn["US"], receiveNodeCode=RTSData.node_code_sn["GB"])
        self.client.checkCodeAndMessage(res_router)
        self.assertEqual(res_router["data"]["roxeRouters"], [])

    def test_093_getRouterList_ro2ro_receiveCurrency_empty(self):
        res_router, body = self.client.getRouterList("USD.ROXE", "")
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "receiveCurrency is empty")

    def test_094_getRouterList_fait2fait_snsnpn_receiveCurrency_empty(self):
        res_router, body = self.client.getRouterList("USD", "", sendNodeCode=RTSData.node_code_sn["US"], receiveNodeCode=RTSData.node_code_pn["US"], routerStrategy="LOWEST_FEE")
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "receiveCurrency is empty")



    def test_095_getRouterList_ro2fait_inReceiveMethodCode_isLower(self):
        res_router, body = self.client.getRouterList("USD.ROXE", "PHP", receiveNodeCode=RTSData.terrapay_node_ph, receiveMethodCode="bank")
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "receiveMethodCode error")
        self.assertIsNone(res_router["data"])

    def test_096_getRouterList_fait2fait_snsn_inReceiveMethodCode_isLower(self):
        res_router, body = self.client.getRouterList("USD", "GBP", sendNodeCode=RTSData.node_code_sn["US"], receiveNodeCode=RTSData.node_code_sn["GB"], receiveMethodCode="bank")
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "receiveMethodCode error")
        self.assertIsNone(res_router["data"])

    def test_097_getRouterList_fait2fait_pnsnsn_inReceiveMethodCode_mix(self):
        res_router, body = self.client.getRouterList("USD", "GBP", sendNodeCode=RTSData.node_code_pn["US"], receiveNodeCode=RTSData.node_code_sn["GB"], receiveMethodCode="bANK")
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "receiveMethodCode error")
        self.assertIsNone(res_router["data"])

    def test_098_getRouterList_fait2fait_snsnpn_inReceiveMethodCode_error(self):
        res_router, body = self.client.getRouterList("USD", "GBP", sendNodeCode=RTSData.node_code_sn["US"], receiveNodeCode=RTSData.node_code_pn["GB"], receiveMethodCode="ABCD")
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "receiveMethodCode error")
        self.assertIsNone(res_router["data"])

    def test_099_getRouterList_fait2fait_snsn_inReceiveMethodCode_eWALLET_isLower(self):
        res_router, body = self.client.getRouterList("USD", "PHP", sendNodeCode=RTSData.node_code_sn["US"], receiveNodeCode=RTSData.gcash_node, receiveMethodCode="ewallet", eWalletCode="GCASH")
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "receiveMethodCode error")
        self.assertIsNone(res_router["data"])

    def test_100_getRouterList_fait2fait_snsn_inReceiveMethodCode_eWALLET_mix(self):
        res_router, body = self.client.getRouterList("USD", "PHP", sendNodeCode=RTSData.node_code_sn["US"], receiveNodeCode=RTSData.gcash_node, receiveMethodCode="eWALLET", eWalletCode="GCASH")
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "receiveMethodCode error")
        self.assertIsNone(res_router["data"])

    def test_101_getRouterList_fait2fait_snsn_inReceiveMethodCode_eWALLET_error(self):
        res_router, body = self.client.getRouterList("USD", "PHP", sendNodeCode=RTSData.node_code_sn["US"], receiveNodeCode=RTSData.gcash_node, receiveMethodCode="abccccc", eWalletCode="GCASH")
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "receiveMethodCode error")
        self.assertIsNone(res_router["data"])

    def test_102_getRouterList_fait2fait_snsn_inReceiveMethodCode_eWALLET_eWalletCode_error(self):
        res_router, body = self.client.getRouterList("USD", "PHP", sendNodeCode=RTSData.node_code_sn["US"], receiveNodeCode=RTSData.gcash_node, receiveMethodCode="EWALLET", eWalletCode="cash")
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "eWalletCode error")
        self.assertIsNone(res_router["data"])

    def test_103_getRouterList_fait2fait_snsn_inReceiveMethodCode_eWALLET_eWalletCode_Mismatch(self):
        res_router, body = self.client.getRouterList("USD", "PHP", sendNodeCode=RTSData.node_code_sn["US"], receiveNodeCode=RTSData.gcash_node, receiveMethodCode="BANK", eWalletCode="GCASH")
        self.client.checkCodeAndMessage(res_router)
        self.assertEqual(res_router["data"]["roxeRouters"], [])

    def test_104_getRouterList_fait2fait_snsn_inReceiveMethodCode_eWALLET_eWalletCode_empty(self):
        res_router, body = self.client.getRouterList("USD", "PHP", sendNodeCode=RTSData.node_code_sn["US"], receiveNodeCode=RTSData.gcash_node, receiveMethodCode="EWALLET", eWalletCode="")
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "eWalletCode is empty")
        self.assertIsNone(res_router["data"])

    def test_105_getRouterList_fait2ro_inPassByNodes_dataError(self):
        res_router, body = self.client.getRouterList("USD", "USD.ROXE", sendNodeCode=RTSData.checkout_node, passByNodes=["1111111111"])
        self.checkCodeAndMessage(res_router)
        self.assertEqual(res_router["data"]["roxeRouters"], [])

    def test_106_getRouterList_fait2fait_snsn_inPassByNodes_dataError(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendNodeCode=RTSData.checkout_node, receiveCountry="US", passByNodes=["aaaaaaaaaaa"])
        self.checkCodeAndMessage(res_router)
        self.assertEqual(res_router["data"]["roxeRouters"], [])

    @unittest.skip("暂时跳过，后期优化处理")
    def test_107_getRouterList_fait2ro_inPassByNodes_typeError(self):
        res_router, body = self.client.getRouterList("USD", "USD.ROXE", sendNodeCode=RTSData.checkout_node, passByNodes=123456)
        self.assertEqual(res_router["code"], "01100000")
        self.assertEqual(res_router["message"], "type error")
        self.assertIsNone(res_router["data"])

    # todo 后期优化处理, 加解密解析问题
    def test_108_getRouterList_fait2fait_pnsnsn_inPassByNodes_typeError(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendCountry="GB", receiveCountry="US", passByNodes=RTSData.node_code_pn["GB"])

    def test_109_getRouterList_fait2fait_snsn_inPassByNodes_Mismatch(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendNodeCode=RTSData.checkout_node, receiveCountry="GB", passByNodes=[RTSData.node_code_pn["US"]])
        self.checkCodeAndMessage(res_router)
        self.assertEqual(res_router["data"]["roxeRouters"], [])

    # 下单
    def test_110_submitOrder_RoToRo_instructionId_empty(self):
        sendCurrency = "USD.ROXE"
        receiveCurrency = "USD.ROXE"
        from_address = RTSData.chain_account
        outer_address = RTSData.user_account_2
        fromAccountKey = RTSData.chain_pri_key
        order_info, submit_body = self.client.submitOrder("", sendCurrency, receiveCurrency, sendAmount=100, receiverAddress=outer_address, popKey="instructionId")
        self.assertEqual(order_info["code"], "01100000")
        self.assertEqual(order_info["message"], "instructionId is empty")
        self.assertIsNone(order_info["data"])

    def test_111_submitOrder_FaitToRo_instructionId_empty(self):
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        sendCurrency = "USD"
        receiveCurrency = "USD.ROXE"
        from_address = RTSData.chain_account
        outer_address = RTSData.user_account_2
        paymentId = time.time()
        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              sendAmount=100, receiverAddress=outer_address, popKey="instructionId")
        self.assertEqual(rts_order_info["code"], "01100000")
        self.assertEqual(rts_order_info["message"], "instructionId is empty")
        self.assertIsNone(rts_order_info["data"])

    def test_112_submitOrder_FaitToRo_sendNodeCodeAndSendCountry_empty(self):
        sendNodeCode = ""
        sendCountry = ""
        sendCurrency = "USD"
        receiveCurrency = "USD.ROXE"
        from_address = RTSData.chain_account
        outer_address = RTSData.user_account_2
        paymentId = time.time()
        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              sendAmount=100, receiverAddress=outer_address)
        self.assertEqual(rts_order_info["code"], "01100000")
        self.assertEqual(rts_order_info["message"], "Both sendNodeCode and sendCountry are empty")
        self.assertIsNone(rts_order_info["data"])

    def test_113_submitOrder_RoToFait_instructionId_empty(self):
        sendCurrency = "USD.ROXE"
        receiveCurrency = "PHP"
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        from_address = RTSData.chain_account
        fromAccountKey = RTSData.chain_pri_key
        receive_info = RTSData.terrapay_receive_info
        paymentId = time.time()
        submit_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                                 receiveNodeCode=receiveNodeCode,
                                                                 receiveCountry=receiveCountry, sendAmount=100, popKey="instructionId")
        self.assertEqual(submit_order_info["code"], "01100000")
        self.assertEqual(submit_order_info["message"], "instructionId is empty")
        self.assertIsNone(submit_order_info["data"])

    def test_114_submitOrder_RoToFait_receiveNodeCodeAndReceiveCountry_empty(self):
        sendCurrency = "USD.ROXE"
        receiveCurrency = "PHP"
        receiveNodeCode = ""
        receiveCountry = ""
        from_address = RTSData.chain_account
        fromAccountKey = RTSData.chain_pri_key
        receive_info = RTSData.terrapay_receive_info
        paymentId = time.time()
        submit_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                                 receiveNodeCode=receiveNodeCode,
                                                                 receiveCountry=receiveCountry, sendAmount=100)
        self.assertEqual(submit_order_info["code"], "01100000")
        self.assertEqual(submit_order_info["message"], "Both receiveNodeCode and receiveCountry are empty")
        self.assertIsNone(submit_order_info["data"])

    def test_115_submitOrder_FaitToFait_terrapay_instructionId_empty(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = "RTSData.checkout_node"
        sendCountry = "US"
        receiveNodeCode = "RTSData.terrapay_node_ph"
        receiveCountry = "PH"
        inner_amount = 25
        passByNodes = [RTSData.checkout_node, RTSData.terrapay_node_ph]
        receive_info = RTSData.terrapay_receive_info
        paymentId = time.time()
        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                              sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              receiveNodeCode=receiveNodeCode,
                                                              receiveCountry=receiveCountry, sendAmount=100, popKey="instructionId")
        self.assertEqual(rts_order_info["code"], "01100000")
        self.assertEqual(rts_order_info["message"], "instructionId is empty")
        self.assertIsNone(rts_order_info["data"])

    def test_116_submitOrder_FaitToFait_terrapay_routerStrategy_error(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        inner_amount = 25
        receive_info = RTSData.terrapay_receive_info
        paymentId = time.time()
        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                              sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              receiveNodeCode=receiveNodeCode, receiveCountry=receiveCountry,
                                                              sendAmount=100, routerStrategy="123456")
        self.assertEqual(rts_order_info["code"], "01100000")
        self.assertEqual(rts_order_info["message"], "data structure error")
        self.assertIsNone(rts_order_info["data"])

    def test_117_submitOrder_FaitToFait_terrapay_businessType_error(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        inner_amount = 25
        receive_info = RTSData.terrapay_receive_info
        paymentId = time.time()
        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                              sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              receiveNodeCode=receiveNodeCode, receiveCountry=receiveCountry,
                                                              sendAmount=100, businessType="123456")
        self.assertEqual(rts_order_info["code"], "01100000")
        self.assertEqual(rts_order_info["message"], "businessType error")
        self.assertIsNone(rts_order_info["data"])

    def test_118_submitOrder_FaitToFait_terrapay_paymentId_repeat(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        inner_amount = 25
        receive_info = RTSData.terrapay_receive_info


        rts_order_info, submit_body = self.client.submitOrder("123456", sendCurrency, receiveCurrency, receive_info,
                                                              sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              receiveNodeCode=receiveNodeCode, receiveCountry=receiveCountry,
                                                              sendAmount=100)
        self.assertEqual(rts_order_info["code"], "01600103")
        self.assertEqual(rts_order_info["message"], "Payment order already exist")
        self.assertIsNone(rts_order_info["data"])

    def test_119_submitOrder_FaitToFait_terrapay_sendCurrency_isLower(self):
        sendCurrency = "usd"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        inner_amount = 25
        receive_info = RTSData.terrapay_receive_info
        paymentId = time.time()

        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                              sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              receiveNodeCode=receiveNodeCode, receiveCountry=receiveCountry,
                                                              sendAmount=100)
        self.assertEqual(rts_order_info["code"], "01500002")
        self.assertEqual(rts_order_info["message"], "No available settlement node was found")
        self.assertIsNone(rts_order_info["data"])

    def test_120_submitOrder_FaitToFait_terrapay_sendCurrency_mix(self):
        sendCurrency = "uSd"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        inner_amount = 25
        receive_info = RTSData.terrapay_receive_info
        paymentId = time.time()

        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                              sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              receiveNodeCode=receiveNodeCode, receiveCountry=receiveCountry,
                                                              sendAmount=100)
        self.assertEqual(rts_order_info["code"], "01500002")
        self.assertEqual(rts_order_info["message"], "No available settlement node was found")
        self.assertIsNone(rts_order_info["data"])

    def test_121_submitOrder_FaitToFait_terrapay_sendCurrency_error(self):
        sendCurrency = "111"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        inner_amount = 25
        receive_info = RTSData.terrapay_receive_info
        paymentId = time.time()

        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                              sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              receiveNodeCode=receiveNodeCode, receiveCountry=receiveCountry,
                                                              sendAmount=100)
        self.assertEqual(rts_order_info["code"], "01500002")
        self.assertEqual(rts_order_info["message"], "No available settlement node was found")
        self.assertIsNone(rts_order_info["data"])

    def test_122_submitOrder_FaitToFait_terrapay_sendCurrency_empty(self):
        sendCurrency = ""
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        inner_amount = 25
        receive_info = RTSData.terrapay_receive_info
        paymentId = time.time()

        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                              sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              receiveNodeCode=receiveNodeCode, receiveCountry=receiveCountry,
                                                              sendAmount=100)
        self.assertEqual(rts_order_info["code"], "01100000")
        self.assertEqual(rts_order_info["message"], "sendCurrency is empty")
        self.assertIsNone(rts_order_info["data"])

    def test_123_submitOrder_FaitToFait_terrapay_sendAmount_0(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        inner_amount = 25
        receive_info = RTSData.terrapay_receive_info
        paymentId = time.time()

        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                              sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              receiveNodeCode=receiveNodeCode, receiveCountry=receiveCountry,
                                                              sendAmount=0)
        self.assertEqual(rts_order_info["code"], "01100000")
        self.assertEqual(rts_order_info["message"], "send amount must be greater than 0")
        self.assertIsNone(rts_order_info["data"])

    def test_124_submitOrder_FaitToFait_terrapay_sendAmount_negativeNumber(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        inner_amount = 25
        receive_info = RTSData.terrapay_receive_info
        paymentId = time.time()

        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                              sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              receiveNodeCode=receiveNodeCode, receiveCountry=receiveCountry,
                                                              sendAmount=-10)
        self.assertEqual(rts_order_info["code"], "01100000")
        self.assertEqual(rts_order_info["message"], "send amount must be greater than 0")
        self.assertIsNone(rts_order_info["data"])

    def test_125_submitOrder_FaitToFait_terrapay_sendNodeCodeAndSendCountry_empty(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = ""
        sendCountry = ""
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        inner_amount = 25
        receive_info = RTSData.terrapay_receive_info
        paymentId = time.time()

        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                              sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              receiveNodeCode=receiveNodeCode, receiveCountry=receiveCountry,
                                                              sendAmount=10)
        self.assertEqual(rts_order_info["code"], "01100000")
        self.assertEqual(rts_order_info["message"], "Both sendNodeCode and sendCountry are empty")
        self.assertIsNone(rts_order_info["data"])

    def test_126_submitOrder_FaitToFait_terrapay_receiveNodeCodeAndReceiveCountry_empty(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        receiveNodeCode = ""
        receiveCountry = ""
        inner_amount = 25
        receive_info = RTSData.terrapay_receive_info
        paymentId = time.time()

        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                              sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              receiveNodeCode=receiveNodeCode, receiveCountry=receiveCountry,
                                                              sendAmount=10)
        self.assertEqual(rts_order_info["code"], "01100000")
        self.assertEqual(rts_order_info["message"], "Both receiveNodeCode and receiveCountry are empty")
        self.assertIsNone(rts_order_info["data"])

    def test_127_submitOrder_FaitToFait_terrapay_receiveCurrency_isLower(self):
        sendCurrency = "USD"
        receiveCurrency = "php"
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        inner_amount = 25
        receive_info = RTSData.terrapay_receive_info
        paymentId = time.time()

        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                              sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              receiveNodeCode=receiveNodeCode,
                                                              receiveCountry=receiveCountry,
                                                              sendAmount=100)
        self.assertEqual(rts_order_info["code"], "01500002")
        self.assertEqual(rts_order_info["message"], "No available settlement node was found")
        self.assertIsNone(rts_order_info["data"])

    def test_128_submitOrder_FaitToFait_terrapay_receiveCurrency_mix(self):
        sendCurrency = "USD"
        receiveCurrency = "PhP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        inner_amount = 25
        receive_info = RTSData.terrapay_receive_info
        paymentId = time.time()

        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                              sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              receiveNodeCode=receiveNodeCode,
                                                              receiveCountry=receiveCountry,
                                                              sendAmount=100)
        self.assertEqual(rts_order_info["code"], "01500002")
        self.assertEqual(rts_order_info["message"], "No available settlement node was found")
        self.assertIsNone(rts_order_info["data"])

    def test_129_submitOrder_FaitToFait_terrapay_receiveCurrency_error(self):
        sendCurrency = "USD"
        receiveCurrency = "222"
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        inner_amount = 25
        receive_info = RTSData.terrapay_receive_info
        paymentId = time.time()

        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                              sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              receiveNodeCode=receiveNodeCode,
                                                              receiveCountry=receiveCountry,
                                                              sendAmount=100)
        self.assertEqual(rts_order_info["code"], "01500002")
        self.assertEqual(rts_order_info["message"], "No available settlement node was found")
        self.assertIsNone(rts_order_info["data"])

    def test_130_submitOrder_FaitToFait_terrapay_receiveCurrency_empty(self):
        sendCurrency = "USD"
        receiveCurrency = ""
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        inner_amount = 25
        receive_info = RTSData.terrapay_receive_info
        paymentId = time.time()

        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                              sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              receiveNodeCode=receiveNodeCode,
                                                              receiveCountry=receiveCountry,
                                                              sendAmount=100)
        self.assertEqual(rts_order_info["code"], "01100000")
        self.assertEqual(rts_order_info["message"], "receiveCurrency is empty")
        self.assertIsNone(rts_order_info["data"])

    def test_131_submitOrder_FaitToFait_terrapay_receiveInfo_empty(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        inner_amount = 25
        receive_info = ""
        paymentId = time.time()

        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                              sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              receiveNodeCode=receiveNodeCode,
                                                              receiveCountry=receiveCountry,
                                                              sendAmount=100)
        self.assertEqual(rts_order_info["code"], "01100000")
        self.assertEqual(rts_order_info["message"], "receive info is empty")
        self.assertIsNone(rts_order_info["data"])

    def test_132_submitOrder_FaitToRo_receiverAddress_empty(self):
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        sendCurrency = "USD"
        receiveCurrency = "USD.ROXE"
        from_address = RTSData.chain_account
        outer_address = ""
        receive_info = {"receiverAddress": None}
        paymentId = time.time()
        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receiveInfo=receive_info,
                                                              sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              sendAmount=100, receiverAddress=outer_address)
        self.assertEqual(rts_order_info["code"], "01100000")
        self.assertEqual(rts_order_info["message"], "receiverAddress is empty")
        self.assertIsNone(rts_order_info["data"])

    def test_133_submitOrder_FaitToFait_terrapay_receiveMethodCode_isLower(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        inner_amount = 25
        receive_info = RTSData.terrapay_receive_info
        paymentId = time.time()

        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                              sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              receiveNodeCode=receiveNodeCode,
                                                              receiveCountry=receiveCountry,
                                                              sendAmount=100, receiveMethodCode="bank")
        self.assertEqual(rts_order_info["code"], "01100000")
        self.assertEqual(rts_order_info["message"], "receiveMethodCode error")
        self.assertIsNone(rts_order_info["data"])

    def test_134_submitOrder_FaitToFait_terrapay_receiveMethodCode_mix(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        inner_amount = 25
        receive_info = RTSData.terrapay_receive_info
        paymentId = time.time()

        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                              sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              receiveNodeCode=receiveNodeCode,
                                                              receiveCountry=receiveCountry,
                                                              sendAmount=100, receiveMethodCode="Bank")
        self.assertEqual(rts_order_info["code"], "01100000")
        self.assertEqual(rts_order_info["message"], "receiveMethodCode error")
        self.assertIsNone(rts_order_info["data"])

    def test_135_submitOrder_FaitToFait_terrapay_receiveMethodCode_error(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        inner_amount = 25
        receive_info = RTSData.terrapay_receive_info
        paymentId = time.time()

        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                              sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              receiveNodeCode=receiveNodeCode,
                                                              receiveCountry=receiveCountry,
                                                              sendAmount=100, receiveMethodCode="abck")
        self.assertEqual(rts_order_info["code"], "01100000")
        self.assertEqual(rts_order_info["message"], "receiveMethodCode error")
        self.assertIsNone(rts_order_info["data"])

    def test_136_submitOrder_FaitToFait_gcash_receiveMethodCode_eWALLET_isLower(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        receiveNodeCode = RTSData.gcash_node
        receiveCountry = ""
        receive_info = RTSData.gcash_receive_info
        paymentId = time.time()

        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                              sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              receiveNodeCode=receiveNodeCode,
                                                              receiveCountry=receiveCountry,
                                                              sendAmount=100, receiveMethodCode="ewallet", eWalletCode="GCASH")
        self.assertEqual(rts_order_info["code"], "01100000")
        self.assertEqual(rts_order_info["message"], "receiveMethodCode error")
        self.assertIsNone(rts_order_info["data"])

    def test_137_submitOrder_FaitToFait_gcash_receiveMethodCode_eWALLET_mix(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        receiveNodeCode = RTSData.gcash_node
        receiveCountry = ""
        receive_info = RTSData.gcash_receive_info
        paymentId = time.time()

        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                              sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              receiveNodeCode=receiveNodeCode,
                                                              receiveCountry=receiveCountry,
                                                              sendAmount=100, receiveMethodCode="eWALLET", eWalletCode="GCASH")
        self.assertEqual(rts_order_info["code"], "01100000")
        self.assertEqual(rts_order_info["message"], "receiveMethodCode error")
        self.assertIsNone(rts_order_info["data"])

    def test_138_submitOrder_FaitToFait_gcash_receiveMethodCode_eWALLET_error(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        receiveNodeCode = RTSData.gcash_node
        receiveCountry = ""
        receive_info = RTSData.gcash_receive_info
        paymentId = time.time()

        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                              sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              receiveNodeCode=receiveNodeCode,
                                                              receiveCountry=receiveCountry,
                                                              sendAmount=100, receiveMethodCode="ABCDEFG", eWalletCode="GCASH")
        self.assertEqual(rts_order_info["code"], "01100000")
        self.assertEqual(rts_order_info["message"], "receiveMethodCode error")
        self.assertIsNone(rts_order_info["data"])

    def test_139_submitOrder_FaitToFait_gcash_receiveMethodCode_eWALLET_eWalletCode_error(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        receiveNodeCode = RTSData.gcash_node
        receiveCountry = ""
        receive_info = RTSData.gcash_receive_info
        paymentId = time.time()

        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                              sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              receiveNodeCode=receiveNodeCode,
                                                              receiveCountry=receiveCountry,
                                                              sendAmount=100, receiveMethodCode="EWALLET", eWalletCode="123abc")
        self.assertEqual(rts_order_info["code"], "01100000")
        self.assertEqual(rts_order_info["message"], "eWalletCode error")
        self.assertIsNone(rts_order_info["data"])

    def test_140_submitOrder_FaitToRo_passByNodes_Mismatch(self):
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        sendCurrency = "USD"
        receiveCurrency = "USD.ROXE"
        from_address = RTSData.chain_account
        outer_address = RTSData.user_account_2
        paymentId = time.time()
        passByNodes = [{"nodeCode": RTSData.node_code_sn["US"]}]
        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              sendAmount=100, receiverAddress=outer_address, passByNodes=passByNodes)
        self.assertEqual(rts_order_info["code"], "01500002")
        self.assertEqual(rts_order_info["message"], "No available settlement node was found")
        self.assertIsNone(rts_order_info["data"])

    def test_141_submitOrder_RoToFait_passByNodes_Mismatch(self):
        sendCurrency = "USD.ROXE"
        receiveCurrency = "PHP"
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        from_address = RTSData.chain_account
        fromAccountKey = RTSData.chain_pri_key
        receive_info = RTSData.terrapay_receive_info
        paymentId = time.time()
        passByNodes = [{"nodeCode": RTSData.node_code_sn["US"]}]
        submit_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                                 receiveNodeCode=receiveNodeCode,
                                                                 receiveCountry=receiveCountry, sendAmount=100, passByNodes=passByNodes)
        self.assertEqual(submit_order_info["code"], "01500002")
        self.assertEqual(submit_order_info["message"], "No available settlement node was found")
        self.assertIsNone(submit_order_info["data"])

    def test_142_submitOrder_FaitToFait_terrapay_passByNodes_Mismatch(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        inner_amount = 25
        receive_info = RTSData.terrapay_receive_info
        passByNodes = [{"nodeCode": RTSData.node_code_sn["US"]}]
        paymentId = time.time()

        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                              sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              receiveNodeCode=receiveNodeCode, receiveCountry=receiveCountry,
                                                              sendAmount=100, passByNodes=passByNodes)
        self.assertEqual(rts_order_info["code"], "01500002")
        self.assertEqual(rts_order_info["message"], "No available settlement node was found")
        self.assertIsNone(rts_order_info["data"])

    def test_143_submitOrder_RoToRo_passByNodes_Mismatch(self):
        sendCurrency = "USD.ROXE"
        receiveCurrency = "USD.ROXE"
        from_address = RTSData.chain_account
        outer_address = RTSData.user_account_2
        fromAccountKey = RTSData.chain_pri_key
        passByNodes = [{"nodeCode": RTSData.node_code_sn["US"]}]
        paymentId = time.time()
        order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, sendAmount=100, receiverAddress=outer_address, passByNodes=passByNodes)
        self.assertEqual(order_info["code"], "01500002")
        self.assertEqual(order_info["message"], "No available settlement node was found")
        self.assertIsNone(order_info["data"])

    def test_144_submitOrder_RoToFait_passByNodes_typeError(self):
        sendCurrency = "USD.ROXE"
        receiveCurrency = "PHP"
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        from_address = RTSData.chain_account
        fromAccountKey = RTSData.chain_pri_key
        receive_info = RTSData.terrapay_receive_info
        paymentId = time.time()
        passByNodes = RTSData.terrapay_node_ph
        submit_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                                 receiveNodeCode=receiveNodeCode,
                                                                 receiveCountry=receiveCountry, sendAmount=100, passByNodes=passByNodes)
        self.assertEqual(submit_order_info["code"], "01100000")
        self.assertEqual(submit_order_info["message"], "data structure error")
        self.assertIsNone(submit_order_info["data"])

    def test_145_submitOrder_FaitToFait_terrapay_passByNodes_typeError(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        inner_amount = 25
        receive_info = RTSData.terrapay_receive_info
        passByNodes = RTSData.terrapay_node_ph
        paymentId = time.time()

        rts_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                              sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              receiveNodeCode=receiveNodeCode, receiveCountry=receiveCountry,
                                                              sendAmount=100, passByNodes=passByNodes)
        self.assertEqual(rts_order_info["code"], "01100000")
        self.assertEqual(rts_order_info["message"], "data structure error")
        self.assertIsNone(rts_order_info["data"])

    # 挂起订单
    def test_146_suspendOrder_instructionId_error(self):
        result_data, body = self.client.suspendOrder("This is the suspendOrder test", instructionId="123123123")
        self.assertEqual(result_data["code"], "01600102")
        self.assertEqual(result_data["message"], "Transaction order does not exist")
        self.assertIsNone(result_data["data"])

    def test_147_suspendOrder_transactionId_error(self):
        result_data, body = self.client.suspendOrder("This is the suspendOrder test", transactionId="123123123")
        self.assertEqual(result_data["code"], "01600102")
        self.assertEqual(result_data["message"], "Transaction order does not exist")
        self.assertIsNone(result_data["data"])

    def test_148_suspendOrder_instructionIdAndTransactionId_error(self):
        result_data, body = self.client.suspendOrder("This is the suspendOrder test", instructionId="123123123", transactionId="123123123")
        self.assertEqual(result_data["code"], "01600102")
        self.assertEqual(result_data["message"], "Transaction order does not exist")
        self.assertIsNone(result_data["data"])

    # todo 后期优化处理, 加解密解析问题
    def test_149_suspendOrder_instructionId_typeError(self):
        result_data, body = self.client.suspendOrder("This is the suspendOrder test", instructionId=1234567)

    # todo 后期优化处理, 加解密解析问题
    def test_150_suspendOrder_transactionId_typeError(self):
        result_data, body = self.client.suspendOrder("This is the suspendOrder test", transactionId=1234567)

    def test_151_suspendOrder_instructionIdAndTransactionId_empty(self):
        result_data, body = self.client.suspendOrder("This is the suspendOrder test")
        self.assertEqual(result_data["code"], "01100000")
        self.assertEqual(result_data["message"], "Both instructionId and transactionId are empty")
        self.assertIsNone(result_data["data"])

    # todo 后期优化处理, 加解密解析问题
    def test_152_suspendOrder_message_typeError(self):
        result_data, body = self.client.suspendOrder(1234567, instructionId=536232475869839360)

    def test_153_suspendOrder_message_empty(self):
        result_data, body = self.client.suspendOrder(None, instructionId=536232475869839360)
        self.assertEqual(result_data["code"], "01100000")
        self.assertEqual(result_data["message"], "message is empty")
        self.assertIsNone(result_data["data"])

    # 查询订单状态
    def test_154_getOrderInfo_instructionId_error(self):
        order_info = self.client.getOrderInfo(instructionId="123123123")
        self.assertEqual(order_info["code"], "01600102")
        self.assertEqual(order_info["message"], "Transaction order does not exist")
        self.assertIsNone(order_info["data"])

    def test_155_getOrderInfo_transactionId_error(self):
        order_info = self.client.getOrderInfo(transactionId="123123123")
        self.assertEqual(order_info["code"], "01600102")
        self.assertEqual(order_info["message"], "Transaction order does not exist")
        self.assertIsNone(order_info["data"])

    # todo 后期优化处理, 加解密解析问题
    def test_156_getOrderInfo_instructionId_typeError(self):
        order_info = self.client.getOrderInfo(instructionId=123)

    # todo 后期优化处理, 加解密解析问题
    def test_157_getOrderInfo_transactionId_typeError(self):
        order_info = self.client.getOrderInfo(transactionId=123)

    def test_158_getOrderInfo_instructionIdAndTransactionId_empty(self):
        order_info = self.client.getOrderInfo()
        self.assertEqual(order_info["code"], "01100000")
        self.assertEqual(order_info["message"], "Both instructionId and transactionId are Empty")
        self.assertIsNone(order_info["data"])

    # 查询订单状态变更记录
    def test_159_getOrderStateLog_instructionId_error(self):
        order_info = self.client.getOrderStateLog(instructionId="123123123")
        self.assertEqual(order_info["code"], "01600102")
        self.assertEqual(order_info["message"], "Transaction order does not exist")
        self.assertIsNone(order_info["data"])

    def test_160_getOrderStateLog_transactionId_error(self):
        order_info = self.client.getOrderStateLog(transactionId="123123123")
        self.assertEqual(order_info["code"], "01600102")
        self.assertEqual(order_info["message"], "Transaction order does not exist")
        self.assertIsNone(order_info["data"])

    # todo 后期优化处理, 加解密解析问题
    def test_161_getOrderStateLog_instructionId_typeError(self):
        order_info = self.client.getOrderStateLog(instructionId=123)

    # todo 后期优化处理, 加解密解析问题
    def test_162_getOrderStateLog_transactionId_typeError(self):
        order_info = self.client.getOrderStateLog(transactionId=123)

    def test_163_getOrderStateLog_instructionIdAndTransactionId_empty(self):
        order_info = self.client.getOrderStateLog()
        self.assertEqual(order_info["code"], "01100000")
        self.assertEqual(order_info["message"], "Both instructionId and transactionId are Empty")
        self.assertIsNone(order_info["data"])

    # 查询汇率
    def test_164_queryContractRate_signIncorrect(self):
        """
        查询合约费率，签名不正确
        """
        currency = RTSData.currency_fiat_ro[0]["fiat"]
        amount = 10
        rate_info, rate_body = self.client.getRate(currency, currency, sendAmount=amount, replaceSign="abc")
        self.checkCodeAndMessage(rate_info, "01200001", "Signature error")
        self.assertIsNone(rate_info["data"])

    def test_165_queryContractRate_keyIncorrect(self):
        """
        查询合约费率，key不正确
        """
        currency = RTSData.currency_fiat_ro[0]["fiat"]
        amount = 10
        rate_info, rate_body = self.client.getRate(currency, currency, sendAmount=amount, replaceKey="a" * 32)
        self.checkCodeAndMessage(rate_info, "01200001", "Signature error")
        self.assertIsNone(rate_info["data"])

    def test_166_queryContractRate_sendCurrencyLowerCase(self):
        """
        查询合约费率，币种小写
        """
        currency = RTSData.currency_fiat_ro[0]["fiat"].lower()
        amount = 10
        rate_info, rate_body = self.client.getRate(currency, "USD", sendAmount=amount)
        self.checkCodeAndMessage(rate_info, "01100000", "sendCurrency is not support")
        self.assertIsNone(rate_info["data"])

    def test_167_queryContractRate_sendCurrencyMixerCase(self):
        """
        查询合约费率，币种大小写混合
        """
        currency = RTSData.currency_fiat_ro[0]["fiat"].title()
        amount = 10
        rate_info, rate_body = self.client.getRate(currency, "USD", sendAmount=amount)
        self.checkCodeAndMessage(rate_info, "01100000", "sendCurrency is not support")
        self.assertIsNone(rate_info["data"])

    def test_168_queryContractRate_receiveCurrencyLowerCase(self):
        """
        查询合约费率，币种小写
        """
        currency = RTSData.currency_fiat_ro[0]["fiat"].lower()
        amount = 10
        rate_info, rate_body = self.client.getRate("USD", currency, sendAmount=amount)
        self.checkCodeAndMessage(rate_info, "01100000", "receiveCurrency is not support")
        self.assertIsNone(rate_info["data"])

    def test_169_queryContractRate_receiveCurrencyMixerCase(self):
        """
        查询合约费率，币种大小写混合
        """
        currency = RTSData.currency_fiat_ro[0]["fiat"].title()
        amount = 10
        rate_info, rate_body = self.client.getRate("USD", currency, sendAmount=amount)
        self.checkCodeAndMessage(rate_info, "01100000", "receiveCurrency is not support")
        self.assertIsNone(rate_info["data"])

    def test_170_queryContractRate_currencyNotSupport(self):
        """
        查询合约费率，币种不支持: CNY
        """
        currency = RTSData.currency_fiat_ro[0]["fiat"]
        amount = 10
        rate_info, rate_body = self.client.getRate(currency, "KRW", sendAmount=amount)
        self.checkCodeAndMessage(rate_info, "01600104", "Currency pair is not supported")
        self.assertIsNone(rate_info["data"])

    def test_171_queryContractRate_missingInnerCurrency(self):
        """
        查询合约费率，缺少参数: innerCurrency
        """
        currency = RTSData.currency_fiat_ro[0]["fiat"]
        amount = 10
        rate_info, rate_body = self.client.getRate(currency, currency, sendAmount=amount, popKey="sendCurrency")
        self.checkCodeAndMessage(rate_info, "01100000", "sendCurrency is empty")
        self.assertIsNone(rate_info["data"])

    def test_172_queryContractRate_missingOuterCurrency(self):
        """
        查询合约费率，缺少参数: outerCurrency
        """
        currency = RTSData.currency_fiat_ro[0]["fiat"]
        amount = 10
        rate_info, rate_body = self.client.getRate(currency, currency, sendAmount=amount, popKey="receiveCurrency")
        self.checkCodeAndMessage(rate_info, "01100000", "receiveCurrency is empty")
        self.assertIsNone(rate_info["data"])

    def test_173_queryContractRate_notGiveAmountToBothInnerQuantityAndOuterQuantity(self):
        """
        查询合约费率，outQuantity和innerQuantity都不指定amount
        """
        currency = RTSData.currency_fiat_ro[0]["fiat"]
        rate_info, rate_body = self.client.getRate(currency, "PHP")
        self.checkCodeAndMessage(rate_info, "01100000", "send or receive amount all empty")
        self.assertIsNone(rate_info["data"])

    def test_174_queryContractRate_giveAmountToBothInnerQuantityAndOuterQuantity(self):
        """
        查询合约费率，outQuantity和innerQuantity都指定amount
        """
        currency = RTSData.currency_fiat_ro[0]["fiat"]
        rate_info, rate_body = self.client.getRate(currency, currency, 4, 7)
        self.checkCodeAndMessage(rate_info)
        self.checkContractRateResult(rate_info["data"], rate_body)

    #  修改Secret Key
    def test_175_updateSecretKey_currentSecretKey_empty(self):
        res = self.client.updateSecretKey(None)
        self.assertEqual(res["code"], "01100000")
        self.assertEqual(res["message"], "current secret key is empty")
        self.assertIsNone(res["data"])

    def test_176_updateSecretKey_currentSecretKey_error(self):
        res = self.client.updateSecretKey("123456")
        self.assertEqual(res["code"], "01100000")
        self.assertEqual(res["message"], "currentSecretKey error")
        self.assertIsNone(res["data"])