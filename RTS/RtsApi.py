# coding=utf-8
# author: Li MingLei
# date: 2021-11-16
"""
安装依赖

pip3 install requests
pip3 install cryptography
pip3 install pycrypto # mac linux 可直接安装，Windows系统可按报错信息安装编译源码相应的编译器Microsoft Visual C++

"""
import time
import requests
import json
from roxe_libs.Global import Global
from roxe_libs.baseApi import *
from roxe_libs import settings, ApiUtils
import logging
import os
from Crypto.Cipher import DES


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

    def __init__(self, host, api_id, sec_key, ssl_pub_key):
        self.host = host
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
        if traceable:
            for handle in self.logger.handlers:
                if "filehand" in str(handle).lower():
                    handle.setLevel(logging.DEBUG)
                # handle.setLevel(logging.DEBUG)

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
        sign = ApiUtils.rsa_sign(rsa_data, os.path.join(cur_path, "keys/rsa_private_key.pem"))
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
        sign = ApiUtils.rsa_sign(rsa_data, "keys/rsa_private_key.pem")
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

    def getSystemState(self):
        url = self.host + "/system/state"
        self.logger.info("获取系统可用状态")
        res = sendGetRequest(url)
        self.logger.debug(f"请求url: {url}")
        self.logger.info(f"请求结果: {res.text}")

        return res.json()

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

    def getTransactionCurrency(self, sendCountry="", sendCurrency="", receiveCountry="", receiveCurrency="",
                               returnAllCurrency=False, sendTime=None, replaceSign=None, replaceKey=None,
                               replaceSignAlgorithm=None):
        url = self.host + "/router/get-transaction-currency"
        body = {
            "sendCountry": sendCountry,
            "sendCurrency": sendCurrency,
            "receiveCountry": receiveCountry,
            "receiveCurrency": receiveCurrency,
            "returnAllCurrency": returnAllCurrency,
        }
        self.logger.info("获取支持的转账币种")
        if sendTime is None:
            sendTime = int(time.time() * 1000)
        headers, en_body = self.makeEncryptHeaders(sendTime, body, replaceKey, replaceSignAlgorithm)
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

    def getRate(self, sendCurrency, receiveCurrency, sendAmount="", receiveAmount="", sendTime=None, popKey=None,
                replaceSign=None, replaceKey=None):
        url = self.host + "/contract/get-rate"
        body = {
            "sendCurrency": sendCurrency,
            "sendAmount": str(sendAmount),
            "receiveCurrency": receiveCurrency,
            "receiveAmount": str(receiveAmount),
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

    def getRouterList(self, sendCountry, sendCurrency, receiveCountry, receiveCurrency, sendAmount="", receiveAmount="",
                      sendNodeCode="", receiveNodeCode="", routerStrategy="", popKey=None, replaceSign=None,
                      replaceKey=None, passByNodes="", isReturnOrder=False, businessType="C2C", receiveMethod="BANK", eWalletCode=None, enableRuleBook=False):
        url = self.host + "/router/get-router-list"
        tmp_body = {
            "routerStrategy": routerStrategy,
            "sendNodeCode": sendNodeCode,
            "sendCountry": sendCountry,
            "sendCurrency": sendCurrency,
            "sendAmount": str(sendAmount),
            "receiveNodeCode": receiveNodeCode,
            "receiveCountry": receiveCountry,
            "receiveCurrency": receiveCurrency,
            "receiveAmount": str(receiveAmount),
            "businessType": businessType,
            "isReturnOrder": isReturnOrder,
            "receiveMethodCode": receiveMethod,
            "eWalletCode": eWalletCode,
            "passByNodes": passByNodes,
            # 'iban': "FR7630106000011234567890189",
            "enableRuleBook": enableRuleBook
        }
        body = {}
        for k, v in tmp_body.items():
            if v: body[k] = v
        if popKey:
            body.pop(popKey)
        self.logger.info("查询路由")
        headers, en_body = self.makeEncryptHeaders(int(time.time() * 1000), body, replaceKey)
        if replaceSign:
            headers["sign"] = replaceSign
        res = sendPostRequest(url, en_body, headers)
        # res = sendPostRequest(url, body)
        self.logger.debug(f"请求url: {url}")
        self.logger.debug(f"请求headers: {res.request.headers}")
        self.logger.debug(f"请求参数: {en_body}")
        self.logger.info(f"原始请求参数: {json.dumps(body)}")
        self.logger.debug(f"请求结果: {res.text}")

        decrypt_res = self.decrypt_response(res, replaceKey)
        return decrypt_res, body

    def getOutMethod(self, currency, receiveCountry="", receiveNodeCode="", popKey=None, replaceSign=None,
                     replaceKey=None):
        url = self.host + "/router/payout-method"
        body = {
            "receiveCountry": receiveCountry,
            "receiveNodeCode": receiveNodeCode,
            "currency": currency,
        }
        self.logger.info("获取支持的收款类型")
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

    def getReceiverRequiredFields(self, receiveNodeCode, receiveCurrency, receiveMethod, businessType="", popKey=None, replaceSign=None,
                                  replaceKey=None, enableRuleBook=False):
        url = self.host + "/router/get-receiver-required-fields"
        body = {
            "receiveNodeCode": receiveNodeCode,
            "receiveCurrency": receiveCurrency,
            "receiveMethod": receiveMethod,
            "businessType": businessType,
            "enableRuleBook": enableRuleBook
        }
        self.logger.info("获取汇入表单")
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

    def checkReceiverRequiredFields(self, receiveNodeCode, receiveCurrency, receiveInfo="", popKey=None,
                                    replaceSign=None, replaceKey=None):
        url = self.host + "/router/check-receiver-required-fields"
        body = {
            "receiveNodeCode": receiveNodeCode,
            "receiveCurrency": receiveCurrency,
            "receiveInfo": receiveInfo,
        }
        self.logger.info("校验汇入表单")
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

    def submitOrder(self, instructionId, originalId, paymentId, sendCurrency, sendAmount, receiveCurrency, receiveInfo,
                    receiveAmount="", sendCountry="", receiveCountry="", sendNodeCode="", receiveNodeCode="",
                    extensionField="", routerStrategy=None, notifyURL="", withoutSendFee=False, channelCode="",
                    popKey=None, replaceSign=None, couponCode=None, replaceKey=None, businessType="C2C", isReturnOrder=False, refundServiceFee=False):
        url = self.host + "/order/submit"
        if isinstance(sendAmount, str):
            # sendAmount = decimal.Decimal(sendAmount)
            sendAmount = float(sendAmount)
        if isinstance(receiveAmount, str) and receiveAmount:
            # receiveAmount = decimal.Decimal(receiveAmount)
            receiveAmount = float(receiveAmount)
        if not paymentId:
            paymentId = instructionId
        body = {
            "instructionId": instructionId,
            "paymentId": paymentId,
            "originalId": originalId,
            "businessType": businessType,
            "isReturnOrder": isReturnOrder,
            "refundServiceFee": refundServiceFee,
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
            "couponCode": couponCode
        }
        # body = {
        #     "instructionId": instructionId,
        #     "paymentId": paymentId,
        #     "originalId": originalId,
        #     "extensionField": extensionField,
        #     "routerStrategy": routerStrategy,
        #     "sendNodeCode": sendNodeCode,
        #     "sendCountry": sendCountry,
        #     "sendCurrency": sendCurrency,
        #     "sendAmount": str(sendAmount),
        #     "receiveNodeCode": receiveNodeCode,
        #     "receiveCountry": receiveCountry,
        #     "receiveCurrency": receiveCurrency,
        #     "receiveAmount": str(receiveAmount),
        #     "receiveInfo": receiveInfo,
        #     "notifyURL": notifyURL,
        #     "channelCode": channelCode,
        #     "couponCode": couponCode,
        #     "withoutSendFee": withoutSendFee,  # 内部字段，通过rps入金时使用
        # }
        self.logger.info("提交订单")
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

        decrypt_res = self.decrypt_response(res, replaceKey)
        return decrypt_res, body

    def suspendOrder(self, instructionId="", transactionId="", sendNodeCode="", receiveNodeCode="", popKey=None,
                     replaceSign=None, replaceKey=None):
        url = self.host + "/order/suspend"
        body = {
            "instructionId": instructionId,
            "transactionId": transactionId,
            "sendNodeCode": sendNodeCode,
            "receiveNodeCode": receiveNodeCode,
        }
        self.logger.info("中止订单")
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
        self.logger.debug(f"原始请求参数: {json.dumps(body)}")
        self.logger.info(f"请求结果: {res.text}")

        return self.decrypt_response(res, replaceKey)

    def getOrderInfo(self, instructionId="", transactionId="", popKey=None, replaceSign=None, replaceKey=None):
        url = self.host + "/order/get-order-info"
        body = {
            "instructionId": instructionId,
            "transactionId": transactionId,
        }
        self.logger.info("查询订单状态")
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
        self.logger.debug(f"原始请求参数: {json.dumps(body)}")
        self.logger.info(f"请求结果: {res.text}")

        return self.decrypt_response(res, replaceKey)

    def getOrderStateLog(self, instructionId="", transactionId="", popKey=None, replaceSign=None, replaceKey=None):
        url = self.host + "/order/get-state-log"
        body = {
            "instructionId": instructionId,
            "transactionId": transactionId,
        }
        self.logger.info("查询订单状态变更记录")
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
        self.logger.debug(f"原始请求参数: {json.dumps(body)}")
        self.logger.info(f"请求结果: {res.text}")

        return self.decrypt_response(res, replaceKey)

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


if __name__ == "__main__":
    # the URL to access RTS system, eg: https://risn.roxe.pro/api/rts/v2
    # rts_url = "http://roxe-rts-bj-test.roxepro.top:38888/roxe-rts"
    rts_url = "http://rts-uat.roxepro.top:38888/roxe-rts"
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
    client = RTSApiClient(rts_url, apiId, apiSecretKey, rtsRsaPublicKey)

    # client.getSystemState()
    # client.getRate("USD", "PHP", "", "")
    # client.getOutMethod("GBP", "GB", "fape1meh4bsz")
    # client.getOutMethod("USD", "GB", "fape1meh4bsz")

    # {"businessType":"B2B","receiveCurrency":"USD","receiveMethod":"BANK","receiveNodeCode":"fape1meh4bsz"}
    # client.getReceiverRequiredFields("iovqxmagbm5m", "BRL", "BANK", "C2B")
    # fields = client.getReceiverRequiredFields("iovqxmagbm5m", "EUR", "BANK", "C2C", enableRuleBook=True)
    # fields = client.getReceiverRequiredFields("huu4lssdbmbt", "USD", "BANK", "C2C")
    # fields = client.getReceiverRequiredFields("huuzj1hpycrx", "CAD", "BANK", "C2C", enableRuleBook=True)
    # fields = client.getReceiverRequiredFields("ifomx232tdly", "EGP", "BANK", "C2C")
    # fields = client.getReceiverRequiredFields("pn.test.gb", "USD", "BANK", "C2C")
    # fields = client.getReceiverRequiredFields("huu4lssdbmbt", "USD", "BANK", "B2B")
    # for f in fields["data"]:
    #     if f["required"]: client.logger.warning(json.dumps(f))
    # ,"METHOD":"GET","PARAMS":
    # 2022-09-16 03:44:22.880 ERROR 7 --- [nio-9001-exec-1] i.r.n.application.config.AspectConfig :
    # params = {"payCurrency":"INR","payQuantity":"1120","outCurrency":"USD.ROXE","receiveMethod":"BANK","feeType":"send"}
    params = {"payCurrency":"USD.ROXE","payQuantity":"101.10","outCurrency":"USD","receiveMethod":"BANK","feeType":"delivery"}
    rr = requests.get("http://gateway-uat-bj-test.roxepro.top:40000/roxe-node/huuzj1hpycrx/exchange-rate-fee", params=params)
    # rr = requests.get("http://gateway-uat-bj-test.roxepro.top:40000/roxe-node/ifomx232tdly/exchange-rate-fee", params=params)
    # client.logger.warning(rr.request.url)
    client.logger.warning(rr.text)
    # client.getRouterList("US", "USD", "", "PHP", "102.21", "", "fape1meh4bsz", "huuzj1hpycrx")
    # client.getRouterList("", "USD", "", "INR", "100.21", "", "jeu3ne2se", "")
    # client.getRouterList("", "USD", "", "BRL", "100", "", "fape1meh4bsz", "iovqxmagbm5m", businessType="B2B")
    # client.getRouterList("", "GBP", "GB", "GBP", "1002.21", "", "fape1meh4bsz", "")
    # client.getRouterList("", "USD", "PH", "PHP", "1000.3", "", "fape1meh4bsz", "", receiveMethod="EWALLET", eWalletCode="GCASH")
    # client.getRouterList("", "USD", "PH", "PHP", "100.3", "", "fape1meh4bsz", "", receiveMethod="EWALLET", eWalletCode="GCASH")
    # client.getRouterList("", "USD", "KR", "KRW", 52.95, "", "fape1meh4bsz", "")
    # client.getRouterList("", "USD", "US", "USD", "100", "", "fape1meh4bsz", businessType="B2B")
    # client.getRouterList("", "USD", "", "USD", "1000", "", "huuzj1hpycrx", "fape1meh4bsz", isReturnOrder=True)
    # client.getRouterList("", "EUR", "US", "USD", "120", "", "finknight1z3", "")
    # client.getRouterList("", "USD", "", "PHP", "500", "", "fape1meh4bsz", "ponoim2hcpin")
    # client.getRouterList("", "USD", "", "USD", "50", "", "fape1meh4bsz", "huu4lssdbmbt", businessType='B2B')
    # client.getRouterList("", "USD", "PH", "PHP", "101.07", "", "fape1meh4bsz", "huuzj1hpycrx", enableRuleBook=True)
    client.getRouterList("", "USD", "FR", "EUR", "101.07", "", "fape1meh4bsz", "", enableRuleBook=True)
    # client.getRouterList("", "INR", "", "USD", "1000", "", "iovqxmagbm5m", "fape1meh4bsz", isReturnOrder=True)
    # client.getRouterList("", "PHP", "", "USD", "1000", "", "huuzj1hpycrx", "fape1meh4bsz", isReturnOrder=True)
    # client.getRouterList("", "USD", "FR", "CNY", "50", "", "jeu3ne2se", "")
    # client.getRouterList("", "USD", "", "USD", "67.13", "", "huu4lssdbmbt", "pn.test.us", isReturnOrder=True)
    # client.getRouterList("", "USD", "", "USD", "22.61", "", "pn.test.us", "pn.test.gb", businessType='B2B')

    # client.getRouterList("", "USD", "", "EUR", "102.21", "", "fape1meh4bsz", "")
    # client.getRouterList("US", "USD", "", "KRW", "102.21", "", "fape1meh4bsz", "hqw4usgdmgnx")
    # client.getRouterList("US", "USD", "", "BRL", "102.21", "", "fape1meh4bsz", "ieqnv2lurwaj")
    # client.getRateFromGME()
    # client.getRouterList("", "USD", "", "USD", "102.21", "", "fape1meh4bsz", "huu4lssdbmbt")
    # client.getRouterList("", "USD", "", "USD", "102.21", "", "huu4lssdbmbt")
    # q_field = client.getReceiverRequiredFields("FIAT_US_0002", "INR", "bank")

    # client.getOrderInfo(transactionId="1212802365fc43e384a6773f833016c8")
    #
    # res = {}
    # for i in q_field["data"]:
    #     res[i["name"]] = ""
    # client.logger.warning(json.dumps(res)) 1000000 000000


    # 提交rts订单
    instruction_id = "test_" + str(int(time.time() * 1000))  # 客户单号
    # 提交rts订单
    receive_info = {
        "senderSourceOfFund": "Salary",
        "receiverLastName": "OYUGI",
        "senderNationality": "US",
        "senderAddress": "No. 1 chang an Avenue",
        "purpose": "Gift",
        "receiverBankName": "Asia United Bank",
        "senderIdNumber": "123456789",
        "receiverCountry": "PH",
        "receiverAccountNumber": "20408277204478",
        "senderMiddleName": "Test",
        "senderBirthday": "1999-01-02",
        "receiverFirstName": "RANDY",
        "senderLastName": "001",
        "senderAccountNumber": "123456789012",
        "senderIdType": "nationalidcard",
        "senderFirstName": "Jethro",
        "receiverNationality": "PH",
        "receiveMethodCode": "BANK",
        "senderIdExpireDate": "2023-09-26",
        "senderCity": "helel",
        "senderPhone": "+8613300000000",
        "receiverBankBIC": "AUBKPHMM",
        "senderIdIssueCountry": "SN",
        "receiverCurrency": "PHP",
        "senderBeneficiaryRelationship": "Friend"
    }
    new_msg = {}
    for k, v in receive_info.items():
        if k in ["senderSourceOfFund", "senderBeneficiaryRelationship"]:
            new_msg[k] = v
        else:
            if k.startswith("sender"):
                new_k = k.replace("sender", "receiver")
                new_msg[new_k] = v
            elif k.startswith("receiver"):
                new_k = k.replace("receiver", "sender")
                new_msg[new_k] = v
            else:
                new_msg[k] = v
    # notifyURL = "http://172.17.3.99:8005/api/rts/receiveNotify"
    notifyURL = ""
    payment_id = "dd87f26d912db3c2e42b047f008a93395b161435d57019adc2a4fffaa8f775b1"
    originalId = "6cffa2c3f58e48c2b1e078eab73b043c"
    # rts_order, order_params = client.submitOrder(
    #     instruction_id, originalId, payment_id, "USD", "35.42", "USD", new_msg,
    #     receiveCountry="US", sendNodeCode="huuzj1hpycrx", receiveNodeCode="fape1meh4bsz", isReturnOrder=True, businessType="C2C", routerStrategy="LOWEST_FEE"
    # )

    # print(json.dumps(receive_info))
    # print(json.dumps(new_msg))