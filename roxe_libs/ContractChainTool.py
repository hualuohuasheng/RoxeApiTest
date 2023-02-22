# -*- coding: utf-8 -*-
# author: liminglei
# date: 2021-07-05
import json
import requests
from requests.auth import HTTPBasicAuth
import binascii
import time
from roxepy import ROXEKey, Clroxe
import datetime
import pytz


def parsePrintJson(dic):
    js = json.dumps(dic, indent=4, separators=(',', ':'))
    print(js)


def parseNumberToString(amount, amount_decimal=6, is_carry=False, is_keep=False):
    """
    将数字格式化指定小数位的字符串，如将10.23 转为 '10.230000'
    :param amount: 待格式化的数字
    :param amount_decimal: 格式化后保留的小数位
    :param is_carry: 超过amount_decimal位数后是否进位
    :param is_keep: 超过amount_decimal位数后是否保留原有数字
    :return:
    """
    str_amount = str(amount)
    if '.' in str_amount:
        s_infos = str_amount.split('.')
        float_number = len(s_infos[1])  # 小数后位数
        if float_number > amount_decimal:
            if is_carry:
                res = s_infos[0] + "." + s_infos[1][0:5] + str(int(s_infos[5]) + 1)
            elif is_keep:
                res = str_amount
            else:
                res = s_infos[0] + "." + s_infos[1][0:6]
        else:
            res = str_amount + "0" * (amount_decimal - float_number)
    else:
        res = str_amount + "." + "0" * amount_decimal
    return res


class BTCClient:

    def __init__(self, btcHost, btcUser, btcPwd):
        self.btcHost = btcHost
        self.auth = HTTPBasicAuth(btcUser, btcPwd)
        self.transferFee = 0.0001

    def listUnspent(self, fromId, toId, address):
        """
        查找未消耗的btc数量
        :param fromId: 起始id
        :param toId: 结束id
        :param address: 地址
        :return:
        """
        requestData = {
            "method": "listunspent",
            "params": [
                fromId,
                toId,
                [address]
            ],
            "id": 1
        }
        res = requests.post(self.btcHost, data=json.dumps(requestData), auth=self.auth)
        return res.json()

    def getNewAddress(self):
        """
        生成新的地址
        :return:
        """
        requestData = {
            "method": "getnewaddress",
            "params": [],
            "id": 1
        }
        res = requests.post(self.btcHost, data=json.dumps(requestData), auth=self.auth)
        return res.json()

    def sendToAddress(self,address, amount):
        """

        :param address:
        :param amount:
        :return:
        """
        requestData = {
            "method": "sendtoaddress",
            "params": [address, amount],
            "id": 1
        }
        res = requests.post(self.btcHost, data=json.dumps(requestData), auth=self.auth)
        return res.json()

    def unlockWallet(self):
        requestData = {
            "method": "walletpassphrase",
            "params": ["123456", 60],
            "id": 1
        }
        res = requests.post(self.btcHost, data=json.dumps(requestData), auth=self.auth)
        if res.json()["error"]:
            print(res.json())
        return res.json()

    def createRawTransaction(self, txId, vout, toAddr, toAmount, changeAddr, remainingAmount, memo=None):
        requestData = {
            "method": "createrawtransaction",
            "params": [
                [{"txid": txId, "vout": vout}],
                [{toAddr: toAmount}, {changeAddr: remainingAmount}]
            ],
            "id": 1
        }
        if memo:
            requestData["params"][1].append({"data": binascii.b2a_hex(memo.encode("utf-8")).decode("utf-8")})
        print("rawTransaction params: {}".format(requestData["params"]))
        res = requests.post(self.btcHost, data=json.dumps(requestData), auth=self.auth)
        return res.json()

    def signRawTransaction(self, rawHash):
        requestData = {
            "method": "signrawtransaction",
            "params": [rawHash],
            "id": 1
        }
        res = requests.post(self.btcHost, data=json.dumps(requestData), auth=self.auth)
        return res.json()

    def sendRawTransaction(self, signedHash):
        requestData = {
            "method": "sendrawtransaction",
            "params": [signedHash],
            "id": 1
        }
        res = requests.post(self.btcHost, data=json.dumps(requestData), auth=self.auth)
        return res.json()

    def getRawTransaction(self, txHash, num=2):
        requestData = {
            "method": "getrawtransaction",
            "params": [txHash, num],
            "id": 1
        }
        res = requests.post(self.btcHost, data=json.dumps(requestData), auth=self.auth)
        return res.json()

    def getBlock(self, blockHash):
        requestData = {
            "method": "getblock",
            "params": [blockHash],
            "id": 1
        }
        res = requests.post(self.btcHost, data=json.dumps(requestData), auth=self.auth)
        return res.json()

    def findEnoughUnspent(self, fromAddr, amount, stepNum=5000, retryNum=5):
        num = 1
        flag = False
        fromId = 1
        toId = stepNum
        res = None
        while True:
            r = self.listUnspent(fromId, toId, fromAddr)
            if r["result"]:
                for info in r["result"]:
                    if info["amount"] > amount:
                        flag = True
                        res = info
                        break

            fromId += stepNum
            toId += stepNum

            if flag:
                break
            num += 1
            if num > retryNum:
                break

        return res

    def transferFromSourceAddress(self, fromAddr, amount, toAddr, memo=None):
        unspentInfo = self.findEnoughUnspent(fromAddr, amount)
        firstUnlockWallet = True
        if unspentInfo is None:
            self.unlockWallet()
            firstUnlockWallet = False
            self.sendToAddress(btcAddr, amount * 2)
            unspentInfo = self.findEnoughUnspent(fromAddr, amount)
        remainAmount = round(unspentInfo["amount"] - amount - self.transferFee, 4)
        rawHash = self.createRawTransaction(unspentInfo["txid"], unspentInfo["vout"], toAddr, amount, fromAddr, remainAmount)
        print(rawHash)
        if firstUnlockWallet:
            self.unlockWallet()
        signedHash = self.signRawTransaction(rawHash["result"])
        print("signedHash: {}".format(signedHash))
        txHash = self.sendRawTransaction(signedHash["result"]["hex"])["result"]
        print("txHash: {}".format(txHash))

        time.sleep(5)
        while True:
            txRes = self.getRawTransaction(txHash)["result"]
            if "blockhash" in txRes:
                blockHash = txRes["blockhash"]
                print("blockHash: {}".format(blockHash))
                break
            time.sleep(5)
        time.sleep(2)
        while True:
            blockInfo = self.getBlock(blockHash)["result"]
            if blockInfo["confirmations"] >= 6:
                print("blockInfo: {}".format(blockInfo))
                break
            time.sleep(5)
        return txHash


class RoxeChainClient:

    def __init__(self, host):
        self.host = host
        self.chain_client = Clroxe(self.host)

    @staticmethod
    def makeContractAmount(amt, ccy, con_len=6):
        p_amt = str(amt)
        if "." not in p_amt:
            return p_amt + "." + "0" * con_len + " " + ccy
        else:
            p_integer, p_float = p_amt.split(".")
            if len(p_float) < con_len:
                return p_amt + "0" * (con_len - len(p_float)) + " " + ccy
            else:
                return p_integer + "." + p_float[:con_len] + " " + ccy

    def getBalanceWithRetry(self, account, symbol, contract="roxe.ro", resFloat=True):
        retry_time = 10
        n = 0
        resp = None
        while n < retry_time:
            try:
                resp = self.chain_client.get_currency_balance(account, contract, symbol)
                break
            except Exception as e:
                resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
                n += 1
                print(f"进行第{n}次重试")
                time.sleep(4)
        if resFloat:
            return float(resp[0].split(" ")[0])
        else:
            return resp

    def getTransactionWithRetry(self, trans_id):
        retry_time = 5
        n = 0
        resp = None
        while n < retry_time:
            try:
                resp = self.chain_client.get_transaction(trans_id)
                break
            except Exception as e:
                resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
                n += 1
                print(f"进行第{n}次重试")
                time.sleep(4)
        return resp

    def transferToken(self, fromAccount, fromKey, toAccount, amount, contract):
        arguments = {
            "from": fromAccount,  # sender
            "to": toAccount,  # receiver
            "quantity": amount,  # In Roxe
            "memo": "",
        }
        payload = {
            "account": contract,
            "name": "transfer",
            "authorization": [{
                "actor": fromAccount,
                "permission": "owner",
            }],
        }
        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        # abi_data = self.giftCardAbi.json_to_bin(payload['name'], arguments)
        print(f"action: {arguments}")
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        print(f"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, ROXEKey(fromKey), broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        print(f"转账结果: {resp}")
        return resp

    def allowTransfer(self, account, account_key, pub_key, to_contract):
        arguments = {
            "account": account,
            "permission": "active",
            "parent": "owner",
            "auth": {
                "threshold": 1,
                "keys": [{"key": pub_key, "weight": 1}],
                "accounts": [
                    {
                        "permission": {
                            "actor": to_contract,
                            "permission": "roxe.code"
                        },
                        "weight": 1
                    }
                ],
                "waits": [],
            },
        }
        payload = {
            "account": "roxe",
            "name": "updateauth",
            "authorization": [{
                "actor": account,
                "permission": "owner",
            }],
        }

        abi_data = self.chain_client.abi_json_to_bin(payload['account'], payload['name'], arguments)["binargs"]
        # abi_data = self.giftCardAbi.json_to_bin(payload['name'], arguments)
        print(F"action: {arguments}")
        # print(abi_data)
        payload['data'] = abi_data
        trx = dict(actions=[payload])
        trx['expiration'] = str((datetime.datetime.utcnow() + datetime.timedelta(seconds=60)).replace(tzinfo=pytz.UTC))
        print(f"交易: {trx}")
        try:
            resp = self.chain_client.push_transaction(trx, ROXEKey(account_key), broadcast=True)
        except Exception as e:
            resp = json.loads(e.args[0].replace("Error: ", "").replace("'", '"'))
        return resp


if __name__ == "__main__":

    BTCRPC = "http://192.168.38.133:18610/wallet/"
    client = BTCClient(BTCRPC, "bitcoinrpc", "7bLjxV1CKhNJmdxTUMxTpF4vEemWCp49kMX9CwvZabYi")
    btcAddr = "my4rKNZWdU9wQecCwUGLf9ZpmYGTsUWLMK"
    # print(client.unlockWallet())
    # print(client.sendToAddress(btcAddr, 1))
    # print(client.findEnoughUnspent(btcAddr, 0.01, 200))
    # parsePrintJson(client.listUnspent(1, 5000, btcAddr))
    # parsePrintJson(client.getRawTransaction("5f80ec6e3e10867642a72223b3a35666eb9d71f5c9f916c0f8c77b56b3d8d57d"))
    # parsePrintJson(client.getBlock("2dd017b502c72ee0e697f735e8e8b45437b02e4baa67d4abe7ab0167fdc7a564"))
    # client.transferFromSourceAddress(btcAddr, 0.002, "2MsboQfKwAFbGCoya9cJpVRLMQPNLbwnBzq", "转账备注123")
    # parsePrintJson(client.listUnspent(1, 5000, btcAddr))

    roxeClient = RoxeChainClient("http://192.168.37.22:18888/v1")
    print(roxeClient.getBalanceWithRetry("rsstestbtc11"))
    txInfo = roxeClient.getTransactionWithRetry("36b3f692291f14eb9d6c4de82a0366b63c0381e60cc43aa0165c0d7d00e43ff6")
    if "issue" in json.dumps(txInfo):
        print(txInfo["traces"][0]["act"])
    else:
        print(txInfo["traces"][0]["act"])
        print(txInfo["traces"][1]["act"])
