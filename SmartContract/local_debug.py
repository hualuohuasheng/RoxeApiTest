# -*- coding: utf-8 -*-
"""

安装依赖包

    pip3 install web3

"""

from web3 import Web3, HTTPProvider
import base64
import json


def deploy_contract(w3, acct, abi, bytecode, contract_args=None):
    """
    deploys contract using self-signed tx, waits for receipt, returns address
    """
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    constructed = contract.constructor() if not contract_args else contract.constructor(*contract_args)
    tx = constructed.buildTransaction({
        'from': acct.address,
        'nonce': w3.eth.getTransactionCount(acct.address),
    })
    print("Signing and sending raw tx ...")
    signed = acct.signTransaction(tx)
    tx_hash = w3.eth.sendRawTransaction(signed.rawTransaction)
    print("tx_hash = {} waiting for receipt ...".format(tx_hash.hex()))
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash, timeout=120)
    contractAddress = tx_receipt["contractAddress"]
    print("Receipt accepted. gasUsed={gasUsed} contractAddress={contractAddress}".format(**tx_receipt))
    return contractAddress


def load_abi_from_json_file(json_file):
    with open(json_file, "r") as f:
        res = json.load(f)
    if "abi" in res:
        # print(res)
        return json.dumps(res['abi'])
    else:
        return json.dumps(res)


class ETHClient:

    def __init__(self, url, timeout=120):
        """

        :param url: 节点地址
        :param timeout: 等待节点响应的超时时间
        """
        self.w3 = Web3(HTTPProvider(url, request_kwargs={'timeout': timeout}))

    def setDefaultAccount(self, privateKey):
        """

        :param privateKey: 发出交易的账户私钥，并将此账户地址设置为默认的from地址
        eg:
            从A账户转给B账户1个ETH, 此时传入的就是A账户的私钥地址，因为发起交易需要对交易信息进行签名
        """
        self.account = self.w3.eth.account.privateKeyToAccount(privateKey)
        self.w3.eth.defaultAccount = self.account.address

    @staticmethod
    def transferMemo(memo):
        """

        :param memo: string类型，把memo信息转为的16进制字节字节码
        """
        return base64.b16encode(bytes(memo, encoding="utf-8"))

    def transferEthAmount(self, targetAddress, amount, memo=b""):
        """

        :param targetAddress: 目标地址，由默认账户向目标地址转账
        :param amount: 转账金额
        :param memo: 附加的备注信息, 默认不加备注
        :return:
        流程:
            1、格式化目标地址
            2、打印转账前2个账户的资产余额
            3、格式化转账数量
            4、建立交易信息，并估算gas费用
            5、对交易信息进行签名
            6、发送交易
            7、等待交易完成
            8、打印转账后2个账户的资产余额
        """
        toAddr = self.w3.toChecksumAddress(targetAddress)
        print("transfer before balance:")
        print("{} have {}".format(self.account.address, self.w3.fromWei(self.w3.eth.getBalance(self.account.address), 'ether')))
        print("{} have {}".format(toAddr, self.w3.fromWei(self.w3.eth.getBalance(toAddr), "ether")))
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        transfer_amount = self.w3.toWei(amount, "ether")
        transaction = dict(
            nonce=nonce,
            gasPrice=self.w3.eth.gasPrice,
            to=toAddr,
            value=transfer_amount,
            data=memo,
        )
        transaction["gas"] = self.w3.eth.estimateGas(transaction)
        print("transaction: {}".format(transaction))
        signed_txn = self.account.signTransaction(transaction)
        # print(signed_txn)
        tx_hash = self.w3.eth.sendRawTransaction(signed_txn.rawTransaction)
        print("获得交易哈希: {}".format(tx_hash.hex()))
        tx_receipt = self.w3.eth.waitForTransactionReceipt(tx_hash)
        print("交易执行成功:\n{}".format(tx_receipt))
        print("transfer after balance:")
        print("{} have {}".format(self.account.address,
                                  self.w3.fromWei(self.w3.eth.getBalance(self.account.address), 'ether')))
        print("{} have {}".format(toAddr, self.w3.fromWei(self.w3.eth.getBalance(toAddr), "ether")))

    def transferERC20Amount(self, ercAddr, targetAddress, amount):
        """

        :param ercAddr: erc20合约地址
        :param targetAddress: 目标地址，由默认账户向目标地址转账
        :param amount: 转账金额

        """
        with open("./abi/ERC20.json", "r") as f:
            c_info = json.load(f)
        contract = self.w3.eth.contract(address=ercAddr, abi=c_info['abi'])
        # print(contract.all_functions())
        # print(contract.functions.balanceOf(self.account.address).call())
        toAddr = self.w3.toChecksumAddress(targetAddress)
        print("transfer before balance:")
        print("{} have {}".format(self.account.address, self.w3.fromWei(contract.functions.balanceOf(self.account.address).call(), 'ether')))
        print("{} have {}".format(toAddr, self.w3.fromWei(contract.functions.balanceOf(toAddr).call(), 'ether')))
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        transfer_amount = self.w3.toWei(amount, "ether")
        exec_func = contract.functions.transfer(toAddr, transfer_amount)
        construct_txn = exec_func.buildTransaction({'from': self.account.address, 'nonce': nonce})
        print("transaction: {}".format(construct_txn))
        # print(construct_txn['data'] + str(memo, encoding="utf-8"))
        signed_txn = self.account.signTransaction(construct_txn)
        # print(signed_txn)
        tx_hash = self.w3.eth.sendRawTransaction(signed_txn.rawTransaction)
        print("获得交易哈希: {}".format(tx_hash.hex()))
        tx_receipt = self.w3.eth.waitForTransactionReceipt(tx_hash)
        print("交易执行成功:\n{}".format(tx_receipt))
        print("transfer after balance:")
        print("{} have {}".format(self.account.address,
                                  self.w3.fromWei(contract.functions.balanceOf(self.account.address).call(), 'ether')))
        print("{} have {}".format(toAddr, self.w3.fromWei(contract.functions.balanceOf(toAddr).call(), 'ether')))


# RPC_ADDRESS = 'https://ropsten.infura.io/v3/be5b825be13b4dda87056e6b073066dc' # ropsten测试链节点
RPC_ADDRESS = 'http://192.168.38.227:18045'     # 私链测试节点    -- 智能合约测试使用
# RPC_ADDRESS = 'http://192.168.38.227:18545'   # eth私链测试节点 -- rss测试节点
PRIVATE_KEY = "XXXX"

if __name__ == "__main__":
    eth_client = ETHClient(RPC_ADDRESS)
    eth_client.setDefaultAccount(PRIVATE_KEY)
    # print(eth_client.account.address)
    # ETH转账不带memo
    # eth_client.transferEthAmount("0xBD8592ffFb1D031f27379550064bF2CA04F9C7Cc", 1)
    # ETH转账带memo
    # eth_client.transferEthAmount("0xBD8592ffFb1D031f27379550064bF2CA04F9C7Cc", 1,
    #                              eth_client.transferMemo("liminglei#btc"))
    # ERC20转账不带memo，且只能不带memo
    # eth_client.transferERC20Amount("0xC87caBF8A42e97B1Af5822cdfd1D7C556793CF34",
    #                                "0xBD8592ffFb1D031f27379550064bF2CA04F9C7Cc", 1)
