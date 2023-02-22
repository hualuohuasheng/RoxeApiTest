# -*- coding: utf-8 -*-
import requests
import json


class ChainClient:

    def __init__(self, url):
        self.rpcNode = url

    def getInfo(self):
        return requests.post(self.rpcNode + "/get_info").json()

    def getTransaction(self, tx_id):
        return requests.post(self.rpcNode + "/transaction", json.dumps({"id": tx_id})).json()

    def getBlock(self, blockNumber):
        return requests.post(self.rpcNode + "/get_block", data=json.dumps({"block_num_or_id": blockNumber})).json()

    def getAccount(self, account):
        accountInfo = requests.post(self.rpcNode + "/get_account", data=json.dumps({"account_name": account})).json()
        # parsePrintJson(accountInfo)
        return accountInfo

    def getCodeHash(self, account_name):
        return requests.post(self.rpcNode + "/get_code_hash", data=json.dumps({"account_name": account_name}))

    def getTableRows(self, scope, code, table, isJson=True):
        d = {"scope": scope, "code": code, "table": table, "json": isJson, "limit": 100}
        # print(d)
        info = requests.post(self.rpcNode + "/get_table_rows", data=json.dumps(d)).json()
        # parsePrintJson(info)
        # print(info)
        return info

    def abi_json_to_bin(self, code, action, args):
        d = {"code": code, "action": action, "args": args}
        res = requests.post(self.rpcNode + "/abi_json_to_bin", data=json.dumps(d))
        if res.status_code == 200:
            return res.json()
        else:
            return res.json()

    def get_required_keys(self, available_keys, transaction):
        d = {"transaction": transaction, "available_keys": available_keys}
        res = requests.post(self.rpcNode + "/get_required_keys", data=json.dumps(d))
        return res.json()

    def push_transaction(self, compression, transaction, signatures):
        d = {"compression": compression, "transaction": transaction, "signatures": signatures}
        # parsePrintJson(d)
        return requests.post(self.rpcNode + "/push_transaction", data=json.dumps(d)).json()

    def push_transactions(self, xActions):
        return requests.post(self.rpcNode + "/push_transactions", data=json.dumps(xActions)).json()
