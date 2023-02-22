# -*- coding: utf-8 -*-
# author: liMingLei
# date: 2021-07-29
import time
import hmac
import hashlib
import collections.abc
import string
import random
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from base64 import b64encode, b64decode
from Crypto.Signature import PKCS1_v1_5
from Crypto.Cipher import DES, AES
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def expandData(val, key="", res=None, conStr=".", basicTypes=(str, int, float, bool, complex, bytes)):
    """
    将多重嵌套数据展开为一维数组，以key, value为最基础的数据
    :param val: 值, 判断值的数据类型，如果为复杂类型就做进一步分析
    :param key: 键, 默认为基础类型数据，不做进一步分析
    :param res: 用于存放结果
    :param conStr: 拼接符, 当前级的键和父级的键的连接符, 默认为"."
    :param basicTypes: 基础数据类型
    :return: 返回由元祖组成的list
    """
    if res is None:
        res = []
    if isinstance(val, dict):
        for cKey, cValue in val.items():
            expandData(cValue, conStr.join([key, cKey]).lstrip(conStr), res)
    elif isinstance(val, (list, tuple, set)):
        for item in val:
            expandData(item, key, res)
    elif isinstance(val, basicTypes) or val is None:
        res.append((str(key), val))
    return res


def getSignByHmacSha256(body: str, secKey: str):
    """
    使用hmac的sha256算法加密数据
    :param body: 待加密的数据, str类型
    :param secKey: 加密的key, str类型
    :return: 返回加密后的字符串
    """
    return hmac.new(secKey.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()


def getSignBySha256(body: str):
    """
    使用sha256算法加密数据
    :param body: 待加密的数据, str类型
    :return: 返回加密后的字符串
    """
    encryptHash = hashlib.sha256()
    encryptHash.update(body.encode("utf-8"))
    return encryptHash.hexdigest()


def makeMD5(text: str, sec=None):
    m = hashlib.md5()
    if sec:
        m.update((text + sec).encode("utf8"))
    else:
        m.update(text.encode("utf8"))
    return m.hexdigest()


def parseNumberDecimal(amount: float, float_decimal=2, isUp=False, isMid=False):
    """
    格式化浮点数，保留n位小数
    :param amount: 待格式化的小数
    :param float_decimal: 小数位数
    :param isUp: 是否进位
    :return:
    """
    amount_str = str(amount)
    res = amount
    if "." in amount_str:
        s_amount = amount_str.split(".")
        if len(s_amount[-1]) > float_decimal:
            res = float(s_amount[0] + "." + s_amount[1][0:float_decimal])
            if isMid:
                if int(s_amount[1][float_decimal]) >= 5:
                    res += 0.1 ** float_decimal
            elif isUp:
                if res < amount and amount - res > 0.1 ** 6:
                    res += 0.1 ** float_decimal

    return round(res, float_decimal)


def deepUpdateDict(sourceDict, newDict):
    """
    更新嵌套字典中的值
    :param sourceDict: 原字典
    :param newDict: 欲更新为的值
    eg:     a = {"data": {"code":"123", "data": "$data"}}
            b = {"data": {"data": "ss"}}
            deepUpdateDict(a, b) -> {'data': {'code': '123', 'data': 'ss'}}
    :return:
    """
    for k, v in newDict.items():
        if isinstance(v, collections.abc.Mapping) and v:
            s_d = sourceDict.get(k, {})
            if s_d is None:
                s_d = dict()
            sourceDict[k] = deepUpdateDict(s_d, v)
        else:
            sourceDict[k] = newDict[k]
    return sourceDict


def generateDict(pattern, value, splitStr=".", newDict=None):
    """
    生成多重字典并给最后一级的key赋值
    :param pattern: 生成多重嵌套字典的基础
    :param value: 最后一级将要赋予的值
    :param splitStr: 分割符，用例拆分pattern
    :param newDict: 存放生成的结果
    eg: generateDict('data.data', '123') -> {'data': {'data': '123'}}
    :return:
    """
    if newDict is None:
        newDict = {}
    if "." in pattern:
        keyInfos = pattern.split(".")
        newDict[keyInfos[0]] = {}
        newPattern = ".".join(keyInfos[1::]).lstrip(".")
        generateDict(newPattern, value, splitStr, newDict[keyInfos[0]])
    else:
        newDict[pattern] = value
    return newDict


def aes_encrypt(data, nonce, associated_data, aes_key):
    aes_gcm = AESGCM(bytes(aes_key, encoding='utf-8'))
    c_t = aes_gcm.encrypt(nonce.encode(), data.encode(), associated_data.encode())
    return b64encode(c_t)


def aes_decrypt(encrypt_data, nonce, associated_data, aes_key):
    encrypt_data = b64decode(encrypt_data.encode('utf-8'))
    aes_gcm = AESGCM(aes_key.encode())
    c_t = aes_gcm.decrypt(nonce.encode(), encrypt_data, associated_data.encode())
    return c_t.decode()


def rsa_sign(message, private_key_file_path):
    private_key = RSA.importKey(open(private_key_file_path).read(), 'f00bar')
    hash_obj = SHA256.new(bytes(message, encoding='utf-8'))
    signer = PKCS1_v1_5.new(private_key)
    return b64encode(signer.sign(hash_obj))


def rsa_verify(message, signature, public_key_file_path):
    public_key = RSA.importKey(open(public_key_file_path).read())
    sign = b64decode(signature)
    verifier = PKCS1_v1_5.new(public_key)
    hash_obj = SHA256.new(bytes(message, encoding='utf-8'))
    return verifier.verify(hash_obj, sign)


def aes_cbc_encrypt(data, iv, aes_key):

    def pkcs7padding(text):
        """
        明文使用PKCS7填充
        """
        bs = 16
        length = len(text)
        bytes_length = len(text.encode('utf-8'))
        padding_size = length if (bytes_length == length) else bytes_length
        padding = bs - padding_size % bs
        padding_text = chr(padding) * padding
        return text + padding_text

    cipher = AES.new(aes_key.encode("utf-8"), AES.MODE_CBC, iv.encode("utf-8"))
    # 处理明文
    content_padding = pkcs7padding(data)
    # 加密
    encrypt_bytes = cipher.encrypt(content_padding.encode('utf-8'))
    # 重新编码
    return str(b64encode(encrypt_bytes), encoding='utf-8')


def generateString(num: int):
    base_str = string.ascii_letters + string.digits
    g_res = ""
    for i in range(num):
        g_res += random.choice(base_str)
    return g_res


def randAmount(maxNumber, floatNumber, startNum=3):
    while True:
        amount = round(random.uniform(startNum, maxNumber), floatNumber)
        if amount > startNum:
            break
    return amount


def waitCondition(func, funcArgs, callback, timeOut=60, interSleep=10):
    """
    等待函数，执行func得到的结果，如果满足callback中定义的条件则返回func的结果
    :param func: 执行的函数，eg: add)
    :param funcArgs: 执行的函数的参数，eg: (1, )
    :param callback:
    :param timeOut:
    :param interSleep:
    :return:
    """
    start_time = time.time()
    func_res = None
    while time.time() - start_time < timeOut:
        func_res = func(*funcArgs)
        if callback(func_res):
            break
        time.sleep(interSleep)
    return func_res


if __name__ == "__main__":
    print(getSignBySha256("iDh2F2puiV58qJTD"))
