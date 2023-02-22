# coding=utf-8
# author: ROXE
# date: 2021-11-16
# version: RTS V2.1
"""
Install third-party dependencies

pip3 install requests
pip3 install cryptography

# pycrypto can be installed directly on Mac or Linux
# Windows system needs to install a C++ compiler, you can install the compiler corresponding to the compiled source code according to the error message, Microsoft Visual C++
pip3 install pycrypto

"""
import time
import requests
import json
import string
import random
import logging
import os
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5
from base64 import b64encode, b64decode
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def initLogger(name, level=logging.INFO):
    # Define the logger object and set the log level
    my_logger = logging.getLogger(name)
    my_logger.setLevel(logging.DEBUG)
    fmt = '[%(levelname)s] %(asctime)s: [%(name)s:%(lineno)d]: %(message)s'
    formatter = logging.Formatter(fmt)
    # print the log to the console
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.setLevel(level)
    my_logger.addHandler(handler)

    return my_logger


def sendGetRequest(request_url, params=None, headers=None):
    """
    send a GET request
    :param request_url: Requested url
    :param params: Requested parameters
    :param headers: Requested headers
    :return:
    """
    return requests.get(request_url, params=params, headers=headers)


def sendPostRequest(request_url, body, headers=None):
    """
    send a POST request
    :param request_url: Requested url
    :param body: Requested body data
    :param headers: Requested headers
    :return:
    """
    if headers is None:
        headers = {"Content-Type": "application/json"}
    res = requests.post(request_url, body, headers=headers)
    return res


def getRsaKey(bit_length=2018, private_key_file='rsa_private_key.pem', public_key_file='rsa_public_key.pem'):
    """
    Used to generate the public key and private key of rsa, and save them as files
    :param bit_length: The length of the private key, the default is 2048 bit
    :param private_key_file:
    :param public_key_file:
    :return:
    """
    cur_path = os.path.dirname(os.path.abspath(__file__))
    pri_key = os.path.join(cur_path, private_key_file)
    pub_key = os.path.join(cur_path, public_key_file)
    key = RSA.generate(bit_length)
    private_key = key.export_key()
    file_out = open(pri_key, "wb")
    file_out.write(private_key)
    file_out.close()

    public_key = key.publickey().export_key()
    file_out = open(pub_key, "wb")
    file_out.write(public_key)
    file_out.close()


def aes_encrypt(data, nonce, associated_data, aes_key):
    """
    Encrypt data with AES-GCM algorithm
    :param data: the original data to be encrypted
    :param nonce:
    :param associated_data:
    :param aes_key: the key used for AES-GCM encryption
    :return:
    """
    aes_gcm = AESGCM(bytes(aes_key, encoding='utf-8'))
    c_t = aes_gcm.encrypt(nonce.encode(), data.encode(), associated_data.encode())
    return b64encode(c_t)


def aes_decrypt(encrypt_data, nonce, associated_data, aes_key):
    """
    Decrypt data with AES-GCM algorithm
    :param encrypt_data:
    :param nonce:
    :param associated_data:
    :param aes_key:
    :return:
    """
    encrypt_data = b64decode(encrypt_data.encode('utf-8'))
    aes_gcm = AESGCM(aes_key.encode())
    c_t = aes_gcm.decrypt(nonce.encode(), encrypt_data, associated_data.encode())
    return c_t.decode()


def rsa_sign(message, private_key_file='rsa_private_key.pem'):
    """
    Use RSA private key for signing
    :param message:
    :param private_key_file:
    :return:
    """
    cur_path = os.path.dirname(os.path.abspath(__file__))
    private_key = RSA.importKey(open(os.path.join(cur_path, private_key_file)).read(), 'f00bar')
    hash_obj = SHA256.new(bytes(message, encoding='utf-8'))
    signer = PKCS1_v1_5.new(private_key)
    return b64encode(signer.sign(hash_obj))


def rsa_verify(message, signature, public_key_file='rts_rsa_public_key.pem'):
    """
    Use RSA public key for signature verification
    :param message:
    :param signature:
    :param public_key_file:
    :return:
    """
    cur_path = os.path.dirname(os.path.abspath(__file__))
    public_key = RSA.importKey(open(os.path.join(cur_path, public_key_file)).read())
    sign = b64decode(signature)
    verifier = PKCS1_v1_5.new(public_key)
    hash_obj = SHA256.new(bytes(message, encoding='utf-8'))
    return verifier.verify(hash_obj, sign)


def generateString(length: int):
    """
    Generate random alphanumerics of specified length
    :param length: the length of the generated string
    :return:
    """
    choice_area = string.digits + string.ascii_letters
    random_str = "".join([random.choice(choice_area) for i in range(length)])
    return random_str


class SendApiClient:

    def __init__(self, host, partnerCode, api_secret_key, rts_rsa_pub_key_perm, logger_name="rtsDemo", debug=True):
        self.host = host
        self.partnerCode = partnerCode
        self.api_secret_key = api_secret_key
        self.rts_rsa_pub_key_perm = rts_rsa_pub_key_perm  # The rsa pubkey provided by rts is used to decrypt the returned data

        # the example of request header:
        self.headers = {
            "timestamp": "1638770830014",
            "partnerCode": self.partnerCode,
            "sign": "nwBp922sqmO4YLjTVdFqspAnR6MGYhVvQdKEVve0ot38oQA2XPodJmLH176kw8eijiEgdcmPSvEzuZwq9iopF3zpPFLCqP6S7WwVdx/0KXplHT6kgxjoA6kHn0XwgrRhtBJdbrm4I3b5x1JFf/ZZXFjm4hcM4Bxm0iASY8hnBlsBOSiFiEUhF6pt9nTRLhWgItvYUZkM8EDHH3KYQLPk6ybPnRdS/AD0hW70V74/9HQkpWievH9cgItWRaLOuiL6g4co214QVeRj8qWUN6GWKcq00RfKTRCh3W8modhwB0ewqjvYrPhEFV85LZZ4mepu/Lm48qjloWGY/eMK6x1Lew==",
            "cache-control": "no-cache",
            "Content-Type": "application/json"
        }
        self.logger = logging.getLogger(logger_name)
        if debug:
            for handle in self.logger.handlers:
                handle.setLevel(logging.DEBUG)

    def makeEncryptHeaders(self, send_time, body, secKey=None):
        secKey = secKey if secKey else self.api_secret_key
        headers = self.headers.copy()
        headers["timestamp"] = str(send_time)
        if isinstance(body, dict):
            sign_body = json.dumps(body)
        else:
            sign_body = str(body)
        parse_body = sign_body.replace(": ", ":").replace(", ", ",")
        nonce = generateString(16)
        associated_data = generateString(32)
        aes_cipher_text = aes_encrypt(parse_body, nonce, associated_data, secKey)

        encrypt_data = {
            "resource": {
                "algorithm": "AES_256_GCM",
                "ciphertext": aes_cipher_text.decode('utf-8'),
                "associatedData": associated_data,
                "nonce": nonce
            }
        }
        parse_en_body = json.dumps(encrypt_data).replace(": ", ":").replace(", ", ",")
        self.logger.debug("Original request data: {}".format(parse_body))
        rsa_data = headers["timestamp"] + "::" + encrypt_data['resource']['ciphertext']
        self.logger.debug("The original data to be encrypted: {}".format(rsa_data))
        sign = rsa_sign(rsa_data)
        self.logger.debug("The RSA signed data: {}".format(sign))
        headers["sign"] = sign
        return headers, parse_en_body

    def verify_response(self, response):
        r_data = response.text
        res_en_data = response.headers["timestamp"] + "::" + r_data
        verified = rsa_verify(res_en_data, response.headers["sign"], self.rts_rsa_pub_key_perm)
        assert verified, "Response verification failed: {}".format(response.headers["sign"])
        self.logger.info("Response verification is successful")

    def decrypt_response(self, response, replaceKey):
        return response.json()
        if response.json()["code"] != "0":
            return response.json()
        else:
            self.verify_response(response)
            r_data = response.json()["data"]["resource"]
            secKey = replaceKey if replaceKey else self.api_secret_key
            res_de_data = aes_decrypt(r_data["ciphertext"], r_data["nonce"], r_data["associatedData"], secKey)
            self.logger.info(f"The result is decrypted as: {res_de_data}")
            return json.loads(res_de_data)

    def submitTransferInfo(self, partnerUserId, orderNo, currency, amount, targetAccount="", txID=""):
        replaceKey=None
        url = self.host + "/submitTransferInfo"
        body = {
            "partnerCode": self.partnerCode,
            "partnerUserId": partnerUserId,
            "orderNo": orderNo,
            "currency": currency,
            "amount": amount,
            "targetAccount": targetAccount,
            "txID": txID
        }

        self.logger.info("submitTransferInfo")
        headers, en_body = self.makeEncryptHeaders(int(time.time() * 1000), body, replaceKey)
        res = sendPostRequest(url, en_body, headers)
        self.logger.debug(f"Requested url: {url}")
        self.logger.debug(f"Requested header: {res.request.headers}")
        self.logger.debug(f"Requested body data: {en_body}")
        self.logger.debug(f"Unencrypted requested body data: {json.dumps(body)}")
        self.logger.info(f"Response result: {res.text}")

        decrypt_res = self.decrypt_response(res, replaceKey)
        return decrypt_res, body

    def orderStatus(self, partnerUserId, orderNo):
        replaceKey=None
        url = self.host + "/orderStatus"
        body = {
            "partnerUserId": partnerUserId,
            "orderNo": orderNo
        }
        self.logger.info("updateOrderChainInfo")
        headers, en_body = self.makeEncryptHeaders(int(time.time() * 1000), body, replaceKey)
        res = sendPostRequest(url, en_body, headers)
        self.logger.debug(f"Requested url: {url}")
        self.logger.debug(f"Requested header: {headers}")
        self.logger.debug(f"Requested body data: {en_body}")
        self.logger.debug(f"Unencrypted requested body data: {json.dumps(body)}")
        self.logger.info(f"Response result: {res.text}")

        return self.decrypt_response(res, replaceKey)


if __name__ == "__main__":
    # the URL to access RTS system, eg: https://risn.roxe.pro/api/rts/v2
    rts_url = "https://risn.roxe.pro/api/rs/v1"

    # Apply for an account and get apiId, apiSecretKey and RTS public key 'rtsRsaPublicKey'
    partnerCode = "test"
    apiSecretKey = "9df122006512e2b2f9aa7aafebd2bc15"

    # Generate the RSA private key and public key according to the API document, and copy them to the current folder
    # rsa_private_key.pem is the default file name used for rsa signature
    # you can modify the relevant parameters of the rsa_sign method to your own file name

    # rtsRsaPublicKey is used to decrypt the response message returned by the interface and save it as a pem file after obtaining it
    rtsRsaPublicKey = "rts_rsa_public_key.pem"
    initLogger("send")
    client = SendApiClient(rts_url, partnerCode, apiSecretKey, rtsRsaPublicKey, "send")
    client.submitTransferInfo("10001", "10002", "USDT.ETH", "500", "xx",
                              "0x810146cfc397d73f021ed6f39469d9e05c7c8a5943c1517fc49cc894fb84b7a6")
    # client.orderStatus("100480","555666777888") # 查询订单状态
