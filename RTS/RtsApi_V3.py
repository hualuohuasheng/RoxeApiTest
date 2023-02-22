# coding=utf-8
# author: Roxe
# date: 2022-06-23
"""
安装依赖

pip3 install requests
pip3 install cryptography
pip3 install pycrypto # mac linux 可直接安装，Windows系统可按报错信息安装编译源码相应的编译器Microsoft Visual C++

"""
import copy
import time
import requests
import json
from decimal import Decimal
from roxe_libs.Global import Global
from roxe_libs.baseApi import *
from roxe_libs import settings, ApiUtils
from roxe_libs.DBClient import Mysql
import logging
import os
from Crypto.Cipher import DES
import datetime
from RTS.RTSStatusCode import RtsCodEnum
from RTS.RTSData import RTSData
from roxepy import ROXEKey, Clroxe
from roxe_libs.ContractChainTool import RoxeChainClient


def pad(text):
    # 如果text不是8的倍数【加密文本text必须为8的倍数！】，补足为8的倍数
    while len(text) % 8 != 0:
        text += ' '
    return text


def des_encrypt(data, des_key):
    print(des_key.encode("utf-8"))
    des = DES.new(des_key.encode("utf-8"), DES.MODE_CBC)
    p_data = pad(data)
    en_text = des.encrypt(p_data.encode("utf-8"))
    print(p_data)
    return en_text


def des_decrypt(data, des_key):
    des = DES.new(bytes(des_key, encoding='utf-8'), DES.MODE_CBC)
    de_text = des.decrypt(data)
    print(de_text)
    return de_text.decode().rstrip(' ')


class RTSApiClient:

    def __init__(self, host, env, api_id, sec_key, ssl_pub_key, check_db=False, sql_cfg=None, ns_host=None):
        self.host = host
        self.ns_host = ns_host
        self.env = env
        self.api_id = api_id
        self.sec_key = sec_key
        self.ssl_pub_key = ssl_pub_key  # rts提供的pubkey，用于解密返回的数据
        # 获取全局的日志记录logger
        self.logger = logging.getLogger(Global.getValue(settings.logger_name))
        self.headers = {
            "timestamp": "1627096879199",
            "apiId": self.api_id,
            "sign": "2333",
            "cache-control": "no-cache",
            "Content-Type": "application/json"
        }

        traceable = Global.getValue(settings.enable_trace)
        self.check_db = check_db
        if check_db:
            self.mysql = Mysql(sql_cfg["mysql_host"], sql_cfg["port"], sql_cfg["user"], sql_cfg["password"],
                               sql_cfg["db"], True)
            self.mysql.connect_database()
        if traceable:
            for handle in self.logger.handlers:
                if "filehand" in str(handle).lower():
                    handle.setLevel(logging.DEBUG)
                handle.setLevel(logging.DEBUG)

    def makeEncryptHeaders(self, send_time, body, secKey=None, replaceSignAlgorithm=None):
        secKey = secKey if secKey else self.sec_key
        headers = self.headers.copy()
        headers["timestamp"] = str(send_time)
        if isinstance(body, dict):
            sign_body = json.dumps(body)
        else:
            sign_body = str(body)
        parse_body = sign_body.replace(": ", ":").replace(", ", ",")
        nonce = "Jdiw8ID12yHyd123"
        associated_data = "eKdj7Iklsc82djH"
        # print(parse_body, nonce, associated_data, secKey)
        if replaceSignAlgorithm:
            des_cipher_text = des_encrypt(parse_body, secKey)

            encrypt_data = {
                "resource": {
                    "algorithm": "DES",
                    "ciphertext": des_cipher_text.decode('utf-8')
                }
            }
        else:
            aes_cipher_text = ApiUtils.aes_encrypt(parse_body, nonce, associated_data, secKey)

            encrypt_data = {
                "resource": {
                    "algorithm": "AES_256_GCM",
                    "ciphertext": aes_cipher_text.decode('utf-8'),
                    "associatedData": associated_data,
                    "nonce": nonce
                }
            }
        parse_en_body = json.dumps(encrypt_data).replace(": ", ":").replace(", ", ",")
        # self.logger.debug("原始请求数据: {}".format(parse_body))
        rsa_data = headers["timestamp"] + "::" + parse_en_body
        # self.logger.debug("原始加密数据: {}".format(rsa_data))
        cur_path = os.path.dirname(__file__)
        sign = ApiUtils.rsa_sign(rsa_data, os.path.join(cur_path, RTSData.ssl_pri_key))
        # self.logger.debug("rsa签名后数据: {}".format(sign))
        headers["sign"] = sign
        return headers, parse_en_body

    def makeDesHeaders(self, send_time, body):
        headers = self.headers.copy()
        headers["signTime"] = str(send_time)
        if isinstance(body, dict):
            sign_body = json.dumps(body)
        else:
            sign_body = str(body)
        parse_body = sign_body.replace(": ", ":").replace(", ", ",")
        aes_cipher_text = ApiUtils.getSignByHmacSha256(parse_body, self.sec_key)
        print(aes_cipher_text, type(aes_cipher_text))
        encrypt_data = {
            "resource": {
                "algorithm": "DES",
                "ciphertext": aes_cipher_text,
            }
        }
        parse_en_body = json.dumps(encrypt_data).replace(": ", ":").replace(", ", ",")
        rsa_data = headers["signTime"] + "::" + parse_en_body
        sign = ApiUtils.rsa_sign(rsa_data, RTSData.ssl_pri_key)
        headers["sign"] = sign
        return headers, parse_en_body

    def verify_response(self, response):
        r_data = response.text
        res_en_data = response.headers["timestamp"] + "::" + r_data
        verified = ApiUtils.rsa_verify(res_en_data, response.headers["sign"], self.ssl_pub_key)
        assert verified, "response验签失败: {}".format(response.headers["sign"])
        self.logger.info("response验签成功")

    def decrypt_response(self, response, replaceKey):
        if response.json()["code"] != "0":
            self.logger.info(response.json())
            return response.json()
        else:
            r_data = response.json()["data"]["resource"]
            secKey = replaceKey if replaceKey else self.sec_key
            res_de_data = ApiUtils.aes_decrypt(r_data["ciphertext"], r_data["nonce"], r_data["associatedData"], secKey)
            self.logger.info(f"结果解密为: {res_de_data}")
            return json.loads(res_de_data)

    def make_instructionId(self):
        cur_now = datetime.datetime.now()
        instructionId = 'rtstest0' + str(int(cur_now.timestamp() * 10000000))
        self.logger.debug(f"生成clientInvokeId: {instructionId}")
        return instructionId

    def post_request(self, method, body, popHeader=None, popBody=None, repBody=None, sendTime=None, replaceSign=None, replaceKey=None,
                               replaceSignAlgorithm=None, isNs=False):
        if sendTime is None:
            sendTime = int(time.time() * 1000)
        en_headers, en_body = self.makeEncryptHeaders(sendTime, body, replaceKey, replaceSignAlgorithm)
        if popHeader:
            en_headers.pop(popHeader)
        if popBody:
            en_body = json.loads(en_body)
            en_body["resource"].pop(popBody)
            en_body = json.dumps(en_body)
        if repBody:
            en_body = json.loads(en_body)
            en_body["resource"][repBody] = "1234"
            en_body = json.dumps(en_body)
        url = self.host + "/" + method
        if isNs: url = self.ns_host + "/" + method
        if replaceSign:
            en_headers["sign"] = replaceSign
        en_res = sendPostRequest(url, en_body, headers=en_headers)

        self.logger.debug(f"请求url: {url}")
        self.logger.debug(f"请求headers: {en_headers}")
        self.logger.debug(f"请求参数: {en_body}")
        self.logger.info(f"原始参数: {json.dumps(body, ensure_ascii=False)}")
        self.logger.info(f"请求结果: {en_res.text}")
        decrypt_res = self.decrypt_response(en_res, replaceKey)

        return decrypt_res, body

    def make_receiveInfo(self, receiverBankRoxeId, receiveCurrency):
        receiveInfo = {
            "receiverFirstName": "Jack XX",
            "receiverLastName": "Bob XX",
            "receiverAccountName": "Jack Bob",
            "receiverAccountNumber": "1234567890",
            "receiverIdType": "individual",
            "receiverIdNumber": "123456",
            "receiverBankRoxeId": receiverBankRoxeId,
            "receiveCurrency": receiveCurrency
        }
        return receiveInfo

    def make_passByNodes(self, node, *args):
        passByNodes = [node]
        for add_node in args:
            passByNodes.append(add_node)

        return passByNodes

    def make_order_passByNodes(self, nodeCode, *args):
        nodeCode = {"nodeCode": nodeCode}
        passByNodes = [nodeCode]
        for add_node in args:
            if add_node != nodeCode:
                nodeCodes = {}
                nodeCodes["nodeCode"] = add_node
                passByNodes.append(nodeCodes.copy())

        return passByNodes

    def getSystemState(self):
        url = self.host + "/system/state"
        self.logger.info("获取系统可用状态")
        res = sendGetRequest(url)
        self.logger.debug(f"请求url: {url}")
        self.logger.info(f"请求结果: {res.text}")

        return res.json()

    def getRate(self, sendCurrency, receiveCurrency, sendAmount="", receiveAmount="", sendTime=None, popKey=None,
                replaceSign=None, replaceKey=None):
        url = self.host + "/contract/get-rate"
        body = {
            "sendCurrency": sendCurrency,
            "sendAmount": sendAmount,
            "receiveCurrency": receiveCurrency,
            "receiveAmount": receiveAmount,
        }
        if popKey:
            body.pop(popKey)
        self.logger.info("查询换汇汇率")
        if sendTime is None:
            sendTime = int(time.time() * 1000)
        headers, en_body = self.makeEncryptHeaders(sendTime, body, replaceKey)
        if replaceSign:
            headers["sign"] = replaceSign
        res = sendPostRequest(url, en_body, headers)
        # res = sendPostRequest(url, body)
        self.logger.debug(f"请求url: {url}")
        self.logger.debug(f"请求headers: {headers}")
        self.logger.debug(f"请求参数: {en_body}")
        self.logger.info(f"原始请求参数: {json.dumps(body)}")
        self.logger.debug(f"请求结果: {res.text}")

        decrypt_res = self.decrypt_response(res, replaceKey)
        return decrypt_res, body
        # decrypt_res, body = self.post_request("contract/get-rate", body)
        # return decrypt_res, body

    def updateSecretKey(self, currentSecretKey, popKey=None, replaceSign=None, replaceKey=None):
        url = self.host + "/secret/update-secret-key"
        body = {"currentSecretKey": currentSecretKey}
        self.logger.info("修改Secret Key")
        if popKey:
            body.pop(popKey)
        headers, en_body = self.makeEncryptHeaders(int(time.time() * 1000), body, replaceKey)
        if replaceSign:
            headers["sign"] = replaceSign
        res = sendPostRequest(url, en_body, headers)
        # res = sendPostRequest(url, body)
        self.logger.debug(f"请求url: {url}")
        self.logger.debug(f"请求headers: {headers}")
        self.logger.debug(f"请求参数: {en_body}")
        self.logger.info(f"原始请求参数: {json.dumps(body)}")
        self.logger.debug(f"请求结果: {res.text}")

        return self.decrypt_response(res, replaceKey)

    def getTransactionCurrency(self, sendCountry="", sendCurrency="", receiveCountry="", receiveCurrency="", returnAllCurrency=False, popKey=None, replaceKey=None):
        url = self.host + "/router/get-transaction-currency"
        body = {
            "sendCountry": sendCountry,
            "sendCurrency": sendCurrency,
            "receiveCountry": receiveCountry,
            "receiveCurrency": receiveCurrency,
            "returnAllCurrency": returnAllCurrency,
        }
        if popKey:
            body.pop(popKey)
        self.logger.info("获取支持的转账币种")
        # if sendTime is None:
        #     sendTime = int(time.time() * 1000)
        # headers, en_body = self.makeEncryptHeaders(sendTime, body, replaceKey, replaceSignAlgorithm)
        # if replaceSign:
        #     headers["sign"] = replaceSign
        # res = sendPostRequest(url, en_body, headers)
        # # res = sendPostRequest(url, body)
        # self.logger.debug(f"请求url: {url}")
        # self.logger.debug(f"请求headers: {headers}")
        # self.logger.debug(f"请求参数: {en_body}")
        # self.logger.info(f"原始请求参数: {json.dumps(body)}")
        # self.logger.debug(f"请求结果: {res.text}")
        #
        # decrypt_res = self.decrypt_response(res, replaceKey)
        # return decrypt_res, body
        decrypt_res, body = self.post_request("router/get-transaction-currency", body, replaceKey=replaceKey)
        return decrypt_res, body

    def getRouterList(self, sendCurrency, receiveCurrency, sendNodeCode=None, sendCountry=None, sendAmount=None,
                      receiveNodeCode=None, receiveCountry=None, receiveAmount=None, eWalletCode=None, passByNodes=None ,
                      routerStrategy=None, businessType=None, receiveMethodCode=None,isReturnOrder=False, popKey=None):
        """
        routerStrategy：ENUM 路由策略，不填写返回所有路由路径（LOWEST_FEE、BEST_TIMES、FEE_SEQUENCE、TIME_SEQUENCE、HOT_SEQUENCE）
        businessType：ENUM 业务类型（B2B、C2C、B2C、C2B）
        receiveMethod：ENUM 客户收款方式 （BANK、CASH、EWALLET）
        eWalletCode：ENUM 钱包编码（当receiveMethod=EWALLET时，必填）
        passByNodes：结算过程途径节点列表
        """
        url = self.host + "/router/get-router-list"
        inAmount = sendAmount if sendAmount else ApiUtils.randAmount(20000, 2, 10000)
        # if isinstance(sendAmount, str):
        #     inAmount = sendAmount if sendAmount else ApiUtils.randAmount(100, 2, 20)
        if isinstance(receiveAmount, str):
            receiveAmount = float(receiveAmount)
        body = {
            "routerStrategy": routerStrategy,
            "businessType": businessType,
            "isReturnOrder": isReturnOrder,
            "sendNodeCode": sendNodeCode,
            "sendCountry": sendCountry,
            "sendCurrency": sendCurrency,
            "sendAmount": inAmount,
            "receiveNodeCode": receiveNodeCode,
            "receiveCountry": receiveCountry,
            "receiveCurrency": receiveCurrency,
            "receiveAmount": receiveAmount,
            "receiveMethodCode": receiveMethodCode,
            "eWalletCode": eWalletCode,
            "passByNodes": passByNodes
        }
        if popKey:
            body.pop(popKey)
        self.logger.info("查询路由")
        # headers, en_body = self.makeEncryptHeaders(int(time.time() * 1000), body, replaceKey)
        # if replaceSign:
        #     headers["sign"] = replaceSign
        # res = sendPostRequest(url, en_body, headers)
        # # res = sendPostRequest(url, body)
        # self.logger.debug(f"请求url: {url}")
        # self.logger.debug(f"请求headers: {res.request.headers}")
        # self.logger.debug(f"请求参数: {en_body}")
        # self.logger.info(f"原始请求参数: {json.dumps(body)}")
        # self.logger.debug(f"请求结果: {res.text}")
        #
        # decrypt_res = self.decrypt_response(res, replaceKey)
        # return decrypt_res, body
        decrypt_res, body = self.post_request("router/get-router-list", body)
        return decrypt_res, body

    def getPayoutMethod(self, receiveNodeCode, receiveCountry, receiveCurrency):
        """
        :param receiveCurrency:汇入币种
        :param receiveNodeCode:汇入节点编码
        :param receiveCountry:汇入国家编码
        """
        url = self.host + "/router/payout-method"
        body = {
            "receiveNodeCode": receiveNodeCode,
            "receiveCountry": receiveCountry,
            "receiveCurrency": receiveCurrency,
        }
        self.logger.info("获取支持的收款类型")
        # if popKey:
        #     body.pop(popKey)
        # headers, en_body = self.makeEncryptHeaders(int(time.time() * 1000), body, replaceKey)
        # if replaceSign:
        #     headers["sign"] = replaceSign
        # res = sendPostRequest(url, en_body, headers)
        # # res = sendPostRequest(url, body)
        # self.logger.debug(f"请求url: {url}")
        # self.logger.debug(f"请求headers: {headers}")
        # self.logger.debug(f"请求参数: {en_body}")
        # self.logger.info(f"原始请求参数: {json.dumps(body)}")
        # self.logger.debug(f"请求结果: {res.text}")
        #
        # return self.decrypt_response(res, replaceKey)
        decrypt_res, body = self.post_request("router/payout-method", body)
        return decrypt_res, body

    def getReceiverRequiredFields(self, receiveNodeCode, receiveCurrency, businessType=None, receiveMethodCode=None):
        url = self.host + "/router/get-receiver-required-fields"
        body = {
            "receiveNodeCode": receiveNodeCode,
            "receiveCurrency": receiveCurrency,
            "businessType": businessType,
            "receiveMethodCode": receiveMethodCode
        }
        self.logger.info("获取汇入表单")
        # if popKey:
        #     body.pop(popKey)
        # headers, en_body = self.makeEncryptHeaders(int(time.time() * 1000), body, replaceKey)
        # if replaceSign:
        #     headers["sign"] = replaceSign
        # res = sendPostRequest(url, en_body, headers)
        # # res = sendPostRequest(url, body)
        # self.logger.debug(f"请求url: {url}")
        # self.logger.debug(f"请求headers: {headers}")
        # self.logger.debug(f"请求参数: {en_body}")
        # self.logger.info(f"原始请求参数: {json.dumps(body)}")
        # self.logger.debug(f"请求结果: {res.text}")
        #
        # return self.decrypt_response(res, replaceKey)
        decrypt_res, body = self.post_request("router/get-receiver-required-fields", body)
        return decrypt_res, body

    def checkReceiverRequiredFields(self, receiveNodeCode, receiveCurrency, receiveInfo, businessType=None):
        url = self.host + "/router/check-receiver-required-fields"
        body = {
            "receiveNodeCode": receiveNodeCode,
            "receiveCurrency": receiveCurrency,
            "receiveInfo": receiveInfo,
            "businessType": businessType
            # "receiveMethodCode": receiveMethodCode  # 文档删除此参数, receiveMethodCode=None
        }
        self.logger.info("校验汇入表单")
        # if popKey:
        #     body.pop(popKey)
        # headers, en_body = self.makeEncryptHeaders(int(time.time() * 1000), body, replaceKey)
        # if replaceSign:
        #     headers["sign"] = replaceSign
        # res = sendPostRequest(url, en_body, headers)
        # # res = sendPostRequest(url, body)
        # self.logger.debug(f"请求url: {url}")
        # self.logger.debug(f"请求headers: {headers}")
        # self.logger.debug(f"请求参数: {en_body}")
        # self.logger.info(f"原始请求参数: {json.dumps(body)}")
        # self.logger.debug(f"请求结果: {res.text}")
        #
        # return self.decrypt_response(res, replaceKey)
        decrypt_res, body = self.post_request("router/check-receiver-required-fields", body)
        return decrypt_res, body

    def submitOrder(self, paymentId, sendCurrency, receiveCurrency, receiveInfo="", sendNodeCode="", sendCountry="",
                    receiveNodeCode="", receiveCountry="", originalId=None, businessType=None, extensionField=None,
                    routerStrategy=None, sendAmount=None, receiveAmount=None, receiveMethodCode=None, eWalletCode=None,
                    notifyURL=None, channelCode=None, couponCode=None, passByNodes=None, instructionId=None,
                    receiverAddress=None, isReturnOrder=False, popKey=None):
        """

        :param paymentId: 当后付款补单号时非必填，目前业务仅支持先付款订单（必填）
        :param sendCurrency:
        :param receiveCurrency:
        :param receiveInfo:
        :param sendNodeCode:
        :param sendCountry:
        :param receiveNodeCode:
        :param receiveCountry:
        :param originalId:
        :param businessType:
        :param extensionField:
        :param sendAmount:
        :param receiveAmount:
        :param routerStrategy:
        :param notifyURL:
        :param channelCode:
        :param couponCode:
        :param instructionId:
        :param receiverAddress:
        :param isReturnOrder:
        :return:
        """
        url = self.host + "/order/submit"
        if not instructionId:
            instructionId = self.make_instructionId()
        if isinstance(sendAmount, str):
            sendAmount = float(sendAmount)

        if receiverAddress:
            receiveInfo = {"receiverAddress": receiverAddress}

        body = {
            "instructionId": instructionId,
            "paymentId": paymentId,
            "originalId": originalId,
            "businessType": businessType,
            "isReturnOrder": isReturnOrder,
            "extensionField": extensionField,
            "routerStrategy": routerStrategy,
            "sendNodeCode": sendNodeCode,
            "sendCountry": sendCountry,
            "sendCurrency": sendCurrency,
            "sendAmount": sendAmount,
            "receiveNodeCode": receiveNodeCode,
            "receiveCountry": receiveCountry,
            "receiveCurrency": receiveCurrency,
            "receiveAmount": receiveAmount,
            "receiveInfo": receiveInfo,
            "notifyURL": notifyURL,
            "channelCode": channelCode,
            "couponCode": couponCode,
            "passByNodes": passByNodes,
            "receiveMethodCode": receiveMethodCode,
            "eWalletCode": eWalletCode
        }
        if popKey:
            body.pop(popKey)
        self.logger.info("提交订单")
        # if popKey:
        #     body.pop(popKey)
        # headers, en_body = self.makeEncryptHeaders(int(time.time() * 1000), body, replaceKey)
        # if replaceSign:
        #     headers["sign"] = replaceSign
        # res = sendPostRequest(url, en_body, headers)
        # # res = sendPostRequest(url, body)
        # self.logger.debug(f"请求url: {url}")
        # self.logger.debug(f"请求headers: {headers}")
        # self.logger.debug(f"请求参数: {en_body}")
        # self.logger.info(f"原始请求参数: {json.dumps(body)}")
        # self.logger.debug(f"请求结果: {res.text}")
        #
        # decrypt_res = self.decrypt_response(res, replaceKey)
        # return decrypt_res, body
        decrypt_res, body = self.post_request("order/submit", body)
        return decrypt_res, body

    def suspendOrder(self, message, instructionId=None, transactionId=None):
        url = self.host + "/order/suspend"
        body = {
            "instructionId": instructionId,
            "transactionId": transactionId,
            "message": message
        }
        self.logger.info("挂起订单")
        # if popKey:
        #     body.pop(popKey)
        # headers, en_body = self.makeEncryptHeaders(int(time.time() * 1000), body, replaceKey)
        # if replaceSign:
        #     headers["sign"] = replaceSign
        # res = sendPostRequest(url, en_body, headers)
        # # res = sendPostRequest(url, body)
        # self.logger.debug(f"请求url: {url}")
        # self.logger.debug(f"请求headers: {headers}")
        # self.logger.debug(f"请求参数: {en_body}")
        # self.logger.debug(f"原始请求参数: {json.dumps(body)}")
        # self.logger.info(f"请求结果: {res.text}")
        #
        # return self.decrypt_response(res, replaceKey)
        decrypt_res, body = self.post_request("order/suspend", body)
        return decrypt_res, body

    def getOrderInfo(self, instructionId="", transactionId=""):
        url = self.host + "/order/get-order-info"
        body = {
            "instructionId": instructionId,
            "transactionId": transactionId,
        }
        self.logger.info("查询订单状态")
        # if popKey:
        #     body.pop(popKey)
        # headers, en_body = self.makeEncryptHeaders(int(time.time() * 1000), body, replaceKey)
        # if replaceSign:
        #     headers["sign"] = replaceSign
        # res = sendPostRequest(url, en_body, headers)
        # # res = sendPostRequest(url, body)
        # self.logger.debug(f"请求url: {url}")
        # self.logger.debug(f"请求headers: {headers}")
        # self.logger.debug(f"请求参数: {en_body}")
        # self.logger.debug(f"原始请求参数: {json.dumps(body)}")
        # self.logger.info(f"请求结果: {res.text}")
        #
        # return self.decrypt_response(res, replaceKey)
        decrypt_res, body = self.post_request("order/get-order-info", body)
        return decrypt_res

    def getOrderStateLog(self, instructionId="", transactionId=""):
        url = self.host + "/order/get-state-log"
        body = {
            "instructionId": instructionId,
            "transactionId": transactionId,
        }
        self.logger.info("查询订单状态变更记录")
        # if popKey:
        #     body.pop(popKey)
        # headers, en_body = self.makeEncryptHeaders(int(time.time() * 1000), body, replaceKey)
        # if replaceSign:
        #     headers["sign"] = replaceSign
        # res = sendPostRequest(url, en_body, headers)
        # # res = sendPostRequest(url, body)
        # self.logger.debug(f"请求url: {url}")
        # self.logger.debug(f"请求headers: {headers}")
        # self.logger.debug(f"请求参数: {en_body}")
        # self.logger.debug(f"原始请求参数: {json.dumps(body)}")
        # self.logger.info(f"请求结果: {res.text}")
        #
        # return self.decrypt_response(res, replaceKey)
        decrypt_res, body = self.post_request("order/get-state-log", body)
        return decrypt_res

    def getRateFromGME(self):
        import nacos, yaml
        client = nacos.NacosClient("172.17.3.95:8848", namespace="public", username="nacos", password="nacos")
        data_id = "roxe-rpc-data.yaml"
        rpc_info = client.get_config(data_id, "DEFAULT_GROUP", 10)

        rpc_info = yaml.load(rpc_info, Loader=yaml.FullLoader)
        gme_info = rpc_info.get("gme")
        # print(gme_info)

        author_body = {
            "Username": gme_info["username"],
            "AuthKey": gme_info["auth-key"],
            "AgentCode": gme_info["agent-code"]
        }
        headers = {"Content-Type": "application/json"}
        gme_auth = sendPostRequest(gme_info["base-url"] + "/api/inbound/authenticate", json.dumps(author_body), headers)
        gme_auth = gme_auth.json()
        # gme_auth = {'Code': '0', 'Message': '0:Authentication success.', 'ProcessIdentifier': '886F52C9-6769-4451-8480-49234153EC5C', 'Detail': {'Token': 'o28LSvFt3hUqR9B8i6cdzd7/BL0BI5KTnY8iKbeWKcEfYBerxWh3OpkNLigH63sr5d5UYted4H1u4ySHqc+lrMXUfPD1cYI1123u45qz/owUxC89vjpWxmOp7GGsPxqL20K7JfmtG9+eJvVuXSpRou5KRQJUjMIvNg5/OT5h5I4bXiPOmWxj2cwjtEf5EzWv1xdtWGtH3vyStoLGpb7E/83NqxwF9U5jdzS2ECNXSTRmCL+YdC43+cKqPDCDh5cSaCed/XG6mnoA8DpFRKIl7zle5rUOGKa5+ZOa25XLrJAuHLZh0vR9sXJsGF3A37cuO5n4m+0hOhZCuNyArLhXNPYuPLKKcUMrqtUZH0fZ485/TKfTdDVh1xlE6lXEntjKdXuqTL3yAegrbmL2diyjpti1D4+T/VJB47LSAnXZKpRlSquKXlWHDyBfsIivNG8cbmJKGg7VDqGUn7xuQ8yjh6tbF2ZhY8dtYxh8rImeXdo=', 'Note': 'Token will only be Valid for 10000 minutes.'}}
        # print(gme_auth)

        headers["Authorization"] = gme_auth["Detail"]["Token"]
        headers["Client"] = gme_info["client"]
        sig_body = gme_info["agent-code"] + gme_info["username"] + "US" + "KR" + "KRW" + gme_auth["ProcessIdentifier"]
        en_body = ApiUtils.aes_cbc_encrypt(sig_body, gme_info["iv"], gme_info["secret-key"])
        # print(sig_body)
        # print(en_body)
        rate_body = {
            "Body": {"receivingCountry": "KR", "receivingCurrency": "KRW", "sendingCountry": "US"},
            "Head": {"agentCode":gme_info["agent-code"], "username": gme_info["username"]},
            "ProcessIdentifier": gme_auth["ProcessIdentifier"],
            "Signature": en_body
        }
        gme_rate = sendPostRequest(gme_info["base-url"] + "/api/inbound/CalculateExRate", json.dumps(rate_body), headers)
        self.logger.warning(f"gme汇率信息: {gme_rate.text}")
        return gme_rate.json().get("Detail")

    # 校验函数
    @staticmethod
    def checkCodeAndMessage(res, code="0", msg="Success"):
        # 校验response的code、message
        if isinstance(code, RtsCodEnum):
            assert res["code"] == code.code, f"{res['code']} not equal {code.code}"
            assert res["message"] == code.msg, f"{res['message']} not equal {code.msg}"
            return
        assert res["code"] == code, f"{res['code']} not equal {code}"
        assert res["message"] == msg, f"{res['message']} not equal {msg}"

    # roxe-ns
    def ns_setWebhookUrl(self, url, nodeCode, msgType="NOTICE"):
        p = {
            "msgType": msgType,
            "url": url,
            "nodeCode": nodeCode,
        }

        # decrypt_res, body = self.post_request("setting/set-webhook-url", p, isNs=True)
        # print(decrypt_res, body)
        decrypt_res = requests.post(self.ns_host + "/setting/set-webhook-url", data=json.dumps(p), headers={"Content-Type": "application/json"}).json()
        return decrypt_res

    def ns_orderSubmit(self, transactionId, orderState, sendCountry, sendAmount, sendCurrency, feeAmount, feeCurrency, receiveCountry, receiveAmount, receiveCurrency, remark=None):
        p = {
            "transactionId": transactionId,
            "orderState": orderState,
            "sendCountry": sendCountry,
            "sendAmount": sendAmount,
            "sendCurrency": sendCurrency,
            "feeAmount": feeAmount,
            "feeCurrency": feeCurrency,
            "receiveCountry": receiveCountry,
            "receiveAmount": receiveAmount,
            "receiveCurrency": receiveCurrency,
            "remark": remark,
        }

        decrypt_res, body = self.post_request("order/submit-state", p, isNs=True)
        print(decrypt_res, body)

    def ns_balanceNotice(self, txID, transactionId, amount, currency, feeAmount, feeCurrency, balance, sourceAccount, custodyAccountType, custodyAccount):
        p = {
            "txID": txID,
            "transactionId": transactionId,
            "amount": amount,
            "currency": currency,
            "feeAmount": feeAmount,
            "feeCurrency": feeCurrency,
            "balance": balance,
            "sourceAccount": sourceAccount,
            "custodyAccountInfo": {
                "custodyAccountType": custodyAccountType,
                "custodyAccount": custodyAccount,
                "currency": currency
            },
            # "memo": memo,
            "createTime": int(time.time() * 1000)
        }

        # decrypt_res, body = self.post_request("balance/debit-notice", p, isNs=True)
        decrypt_res = requests.post(self.ns_host + "/balance/change-notice", data=json.dumps(p),
                                    headers={"Content-Type": "application/json"}).json()
        print(p)
        print(decrypt_res)
        return decrypt_res


if __name__ == "__main__":
    # the URL to access RTS system, eg: https://risn.roxe.pro/api/rts/v2
    # rts_url = "http://roxe-rts-bj-test.roxepro.top:38888"
    rts_url = "http://rts-uat.roxepro.top:38888/roxe-rts"
    chain_url = "http://testnet.rocpro.me/v1"
    # rts_url = "https://sandbox-risn.roxe.pro/api/rts/v2"
    # rts_url = "http://roxe-gateway-sandbox1.roxe.pro/api/rts/v2"
    # Apply for an account and get apiId, apiSecretKey and RTS public key 'rtsRsaPublicKey'
    apiId = "JQ3wRBWVxwh4r9eq6V08gWF3mUuQTbn7"
    apiSecretKey = "5f20e76fe8ba4b6cbb0d316fb3478f2c"

    # Generate the RSA private key and public key according to the API document, and copy them to the current folder
    # rsa_private_key_prod.pem is the default file name used for rsa signature
    # you can modify the relevant parameters of the rsa_sign method to your own file name

    # rtsRsaPublicKey is used to decrypt the response message returned by the interface and save it as a pem file after obtaining it
    rtsRsaPublicKey = "rts_rsa_public_key.pem"
    my_logger = logging.getLogger("rtsDemo")
    my_logger.setLevel(logging.DEBUG)
    fmt = '[%(levelname)s] %(asctime)s: [%(name)s:%(lineno)d]: %(message)s'
    formatter = logging.Formatter(fmt)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    my_logger.addHandler(handler)
    Global.setValue(settings.logger_name, my_logger.name)
    Global.setValue(settings.enable_trace, False)
    client = RTSApiClient(rts_url, "uat", apiId, apiSecretKey, rtsRsaPublicKey, check_db=True, sql_cfg=RTSData.sql_cfg, ns_host="http://gateway-uat-bj-test.roxepro.top:40000/roxe-ns")

    # client.getSystemState()
    # client.getTransactionCurrency("US", "USD", "", "PHP")
    # client.getRouterList("C2C", "USD", "PHP", "BANK", sendCountry="US", receiveCountry="US", sendAmount="100")
    # client.getRouterList("USD", "PHP", "BANK", sendNodeCode="hpuuz5siv3tr", receiveNodeCode="ponoim2hcpin", sendAmount="100")  # fait-fait
    # client.getRouterList("USD.ROXE", "USD.ROXE", sendAmount="100")  # ro-ro
    # client.getRouterList("USD", "USD.ROXE", sendAmount="100")  # fait-ro
    # client.getRouterList("USD.ROXE", "PHP", sendAmount="100")  # ro-fait
    client.ns_setWebhookUrl("https://www.yourdomain.com/order/notify")
    # client.getPayoutMethod("huuzj1hpycrx", "PH", "PHP")
    # client.getReceiverRequiredFields("huuzj1hpycrx", "PHP", "C2C", "BANK")
    # RMN节点INFO
    receiveInfo = {
        "receiverFirstName": "Jack XX",
        "receiverLastName": "Bob XX",
        "receiverAccountName": "Jack Bob",
        "receiverAccountNumber": "1234567890",
        "receiverIdType": "individual",
        "receiverIdNumber": "123456",
        "receiverBankRoxeId": "fape1meh4bsz",
        "receiverCurrency": "USD",
        "receiveMethodCode": "BANK"

    }
    # CHANNEL节点INFO
    # receiveInfo = {
    #     "senderFirstName": "Jack XX",
    #     "senderLastName": "Bob XX",
    #     "senderIdType": "nationalidcard",
    #     "senderIdNumber": "012345",
    #     "senderIdExpireDate": "2100-06-01",
    #     "senderNationality": "US",
    #     "senderCountry": "US",
    #     "senderCity": "New York",
    #     "senderAddress": "Street 123",
    #     "senderPhone": "789123456",
    #     "senderBirthday": "2000-06-01",
    #     "senderBeneficiaryRelationship": "Friend",
    #     "senderSourceOfFund": "Salary",
    #     "purpose": "Gift",
    #
    #     "receiverFirstName": "RANDY",
    #     "receiverLastName": "OYUGI",
    #     "receiverAccountName": "Asia United Bank",
    #     "receiverAccountNumber": "20408277204478",
    #     "receiverBankName": "XXX BANK",
    #     # "receiverBankRoxeId": "fape1meh4bsz",
    #     "receiverCountry": "PH",
    #     "receiverCurrency": "PHP",
    #     "receiveMethodCode": "BANK",
    #     "receiverBankBIC": "AUBKPHMM"
    # }

    # client.checkReceiverRequiredFields("fape1meh4bsz", "USD", receiveInfo)
    # client.submitOrder("1543127747879051266", receiveInfo, sendNodeCode="hpuuz5siv3tr", receiveNodeCode="huuzj1hpycrx", sendAmount="30")
    # client.suspendOrder("hpuuz5siv3tr", "huuzj1hpycrx", "rtstest016565811308273630")
    # client.getOrderInfo("rtstest016600431395330380")


