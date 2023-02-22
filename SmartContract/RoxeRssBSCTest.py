# -*- coding: utf-8 -*-

# author: liminglei
# CreateTime: 2021-05-20 19:39

from roxe_libs.pub_function import setCustomLogger
from web3 import Web3, HTTPProvider, WebsocketProvider
import logging
import json
import requests
import traceback
import time


class BActionTest:

    def __init__(self, rpc_url, ETHPrivateChainNode, BSCNode):
        if rpc_url.startswith("http"):
            self.web3 = Web3(HTTPProvider(rpc_url, request_kwargs={'timeout': 120}))
            # logger.info("web3 connect status: {}".format(self.web3.isConnected()))
        else:
            self.web3 = Web3(WebsocketProvider(rpc_url))
            # logger.info("web3 connect status: {}".format(self.web3.isConnected()))
        # self.account = self.web3.eth.account.privateKeyToAccount(private_key)
        self.ETHTestNode = ETHPrivateChainNode
        self.BSCTestNode = BSCNode
        self.header = {"Content-type": "application/json"}

    def getEthBalnceOf(self, account):
        dataBody = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "eth_getBalance",
            "params": [
                account,
                "latest"
            ]
        }
        logger.info("{} 准备查询ETH测试链的ETH资产".format(account))
        res = requests.post(self.ETHTestNode, data=json.dumps(dataBody), headers=self.header).json()
        ethBalance = None
        if "result" in res:
            logger.debug("原始请求结果: {}".format(res))
            ethBalance = int(res["result"], 16)
            logger.info("资产: {} wei= {} eth".format(ethBalance, self.web3.fromWei(ethBalance, "ether")))
        return ethBalance

    def getBNBBalnceOf(self, account):
        dataBody = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "eth_getBalance",
            "params": [
                account,
                "latest"
            ]
        }
        logger.info("{} 准备查询BSC测试链的BNB资产".format(account))
        res = requests.post(self.BSCTestNode, data=json.dumps(dataBody), headers=self.header).json()
        bnbBalance = None
        if "result" in res:
            logger.debug("原始请求结果: {}".format(res))
            bnbBalance = int(res["result"], 16)
            logger.info("资产: {} wei= {} bnb".format(bnbBalance, self.web3.fromWei(bnbBalance, "ether")))
        return bnbBalance

    def getMeeBalanceOf(self, account, meeAddress, chain="eth"):
        dataBody = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [
                {
                    "to": meeAddress,
                    "data": "0x70a08231000000000000000000000000" + account[2::]
                },
                "latest"
            ]
        }
        logger.info("{} 准备查询{}测试链的ETH资产".format(account, chain))
        host = self.ETHTestNode if chain == "eth" else self.BSCTestNode
        res = requests.post(host, data=json.dumps(dataBody), headers=self.header).json()
        meeBalance = None
        if "result" in res:
            logger.debug("原始请求结果: {}".format(res))
            meeBalance = int(res["result"], 16)
            logger.info("资产: {} wei = {} mee.{}".format(meeBalance, self.web3.fromWei(meeBalance, "ether"), chain))
        return meeBalance

    def getTransactionReceipt(self, txHash, chain="eth"):
        dataBody = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "eth_getTransactionReceipt",
            "params": [txHash]
        }
        host = self.ETHTestNode if chain == "eth" else self.BSCTestNode
        res = requests.post(host, data=json.dumps(dataBody), headers=self.header).json()
        logger.info(res)


RPC_ADDRESS = 'https://kovan.infura.io/v3/be5b825be13b4dda87056e6b073066dc'
ETHTestNode = "http://192.168.38.133:18545/"
BSCTestNode = "http://192.168.37.22:8575/"

# 对公账户的地址
ethMEE = "0x0a1baf18bc17f980a753f89ba1d75e6a371152fa"
bscMEE = "0x0009976a3c6c2f0ec0a4ed891cd0312e181daf70"

# MEE在ETH测试链和BSC链上的合约地址
ethMEEContract = "0xe6C1eEf95a74cd184E3Efd319d156AAB997Cffc0"
bscMEEContract = "0x9914cc1B147bb3C03cF902e3dE9F9504f44e109F"

myAccount = "0x64a6C85595755CaF084Fdf4eC8017bD6A4bE21a9"

logger = setCustomLogger("BSC跨链测试", "RoxeRssBsc.log", isprintsreen=True, level=logging.INFO)

if __name__ == "__main__":
    client = BActionTest(RPC_ADDRESS, ETHTestNode, BSCTestNode)

    logger.info("查询对公账户信息")
    client.getEthBalnceOf(ethMEE)
    client.getBNBBalnceOf(bscMEE)

    client.getMeeBalanceOf(ethMEE, ethMEEContract)
    client.getMeeBalanceOf(bscMEE, bscMEEContract, "bsc")

    logger.info("查询个人账户信息")
    client.getMeeBalanceOf(myAccount, ethMEEContract)
    client.getMeeBalanceOf(myAccount, bscMEEContract, "bsc")

    # client.getTransactionReceipt("0x0a437c3024f834c8868949d5222896471772a12e3ce0ead23639f9c586b9a038", "bsc")

