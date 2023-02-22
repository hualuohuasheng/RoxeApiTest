# -*- coding: utf-8 -*-
import requests
import json
import os

curPath = os.path.dirname(os.path.abspath(__file__))


class WalletClient:

    def __init__(self, url, default_wallet_name='34567'):
        self.walletNode = url
        self.default_wallet_name = default_wallet_name

    def create(self, name):
        return requests.post(self.walletNode + "/create", data=name).json()

    def open(self, name):
        return requests.post(self.walletNode + "/open", data=name).json()

    def lock(self, name):
        return requests.post(self.walletNode + "/lock", data=name).json()

    def lock_all(self, name):
        return requests.post(self.walletNode + "/lock_all", data=name).json()

    def unlock_wallet(self, wallet_name, password):
        d = [wallet_name, password]
        res = requests.post(self.walletNode + "/unlock", data=json.dumps(d)).json()
        return res

    def wallet_sign_trx(self, x_action):
        return requests.post(self.walletNode + "/sign_transaction", data=json.dumps(x_action)).json()

    def import_key(self, name, password):
        return requests.post(self.walletNode + "/import_key", data=json.dumps([name, password])).json()

    def list(self):
        return requests.post(self.walletNode + "/list_wallets").json()

    def list_keys(self):
        return requests.post(self.walletNode + "/list_keys").json()

    def get_public_keys(self):
        return requests.post(self.walletNode + "/get_public_keys").json()
