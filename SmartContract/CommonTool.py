#!/usr/bin/env python3

"""
Simple example on compiling & deploying simple smartcontract, and calling its methods

Setup:
pip3 install web3
pip3 install py-solc-x
# python3 -m solc.install v0.4.24
# export PATH="$PATH:$HOME/.py-solc/solc-v0.4.24/bin"

"""

from web3 import Web3, HTTPProvider, middleware, WebsocketProvider
from solcx import compile_source, compile_files, compile_standard
import json
import re
import subprocess
import os
import sys
import random
import logging


def switchSolcVersionByContractCode(contract_source_code):
    pragmaInfos = re.findall('pragma solidity .*\d+;', contract_source_code)
    solcVersion = pragmaInfos[0].split(" ")[-1].split(";")[0].split("^")[-1]
    cmd = ["solc", "use", solcVersion]
    out_bytes = subprocess.check_output(cmd)
    out_text = out_bytes.decode("utf-8")
    print(out_text)
    curVersion = out_text.strip().split(" ")[-1]
    assert curVersion == solcVersion, "切换后solc版本{}和预期的版本{}不一致".format(curVersion, solcVersion)


def getCurrentSolcOutputValues():
    out_text = subprocess.getoutput("solc --help")
    lines = out_text.strip().split("\n")
    for index, line in enumerate(lines):
        if "--combined-json" in line:
            output_values = line.split(" ")[-1].split(",")
            return output_values


def compile_contract(contract_source_file, contractName=None):
    """
    Reads file, compiles, returns contract name and interface
    """
    with open(contract_source_file, "r") as f:
        contract_source_code = f.read()
    # print(contract_source_code)
    # switchSolcVersionByContractCode(contract_source_code)
    # output_values = getCurrentSolcOutputValues()
    # compiled_sol = compile_source(contract_source_code, output_values=["abi", "bin"])  # Compiled source code
    compiled_sol = compile_standard(contract_source_code)  # Compiled source code
    # compiled_sol = compile_files([contract_source_file])  # Compiled source code
    # print(compiled_sol)
    if not contractName:
        contractName = list(compiled_sol.keys())[0]
        contractInterface = compiled_sol[contractName]
    else:
        contractInterface = compiled_sol['<stdin>:' + contractName]
    return contractName, contractInterface


def deploy_contract(w3, account, abi, bytecode, contractArgs=None):
    """
    deploys contract using self-signed tx, waits for receipt, returns address
    """
    # print(bytecode)
    contract = w3.eth.contract(abi=abi, bytecode=bytecode, opcodes=info['data']["deployedBytecode"]["opcodes"])
    constructed = contract.constructor() if not contractArgs else contract.constructor(*contractArgs)
    tx = constructed.buildTransaction({
        'from': account.address,
        'nonce': w3.eth.getTransactionCount(account.address),
        "gasPrice": 1000000000
    })
    print("Signing and sending raw tx ...")
    signed = account.signTransaction(tx)
    tx_hash = w3.eth.sendRawTransaction(signed.rawTransaction)
    print("tx_hash = {} waiting for receipt ...".format(tx_hash.hex()))
    tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash, timeout=120)
    contractAddress = tx_receipt["contractAddress"]
    print("Receipt accepted. gasUsed={gasUsed} contractAddress={contractAddress}".format(**tx_receipt))
    return contractAddress


def exec_contract(w3, account, nonce, func):
    """
    call contract transactional function func
    """
    construct_txn = func.buildTransaction({'from': account.address, 'nonce': nonce})
    print(construct_txn)
    print(w3.eth.estimateGas(construct_txn))
    signed = account.signTransaction(construct_txn)
    tx_hash = w3.eth.sendRawTransaction(signed.rawTransaction)
    return tx_hash.hex()


def load_from_json_file(json_file):
    with open(json_file, "r") as f:
        res = json.load(f)
    return res


class BaseEthClient:
    gasPrice = 1000000000 # 1gwei

    def __init__(self, rpc_url, private_key, myLogger):
        self.logger = myLogger
        if rpc_url.startswith("http"):
            self.w3 = Web3(HTTPProvider(rpc_url, request_kwargs={'timeout': 120}))
            # self.logger.info("web3 connect status: {}".format(self.w3.isConnected()))
        else:
            self.w3 = Web3(WebsocketProvider(rpc_url))
            self.logger.info("web3 connect status: {}".format(self.w3.isConnected()))
        self.account = self.w3.eth.account.privateKeyToAccount(private_key)

    def get_contract(self, addr, abi_file):
        return self.w3.eth.contract(address=addr, abi=load_from_json_file(abi_file)["abi"])

    def deploy_contract(self, jsonFile, contractArgs=None):
        contractInfo = load_from_json_file(jsonFile)
        contract = self.w3.eth.contract(abi=contractInfo["abi"],
                                        bytecode=contractInfo["data"]["bytecode"]["object"])
        constructed = contract.constructor() if not contractArgs else contract.constructor(*contractArgs)
        tx = constructed.buildTransaction({
            'from': self.account.address,
            'nonce': self.w3.eth.getTransactionCount(self.account.address),
            "gasPrice": self.gasPrice
        })
        self.logger.info("Signing and sending raw tx ...")
        signed = self.account.signTransaction(tx)
        tx_hash = self.w3.eth.sendRawTransaction(signed.rawTransaction)
        self.logger.info("{} waiting for receipt ...".format(tx_hash.hex()))
        tx_receipt = self.w3.eth.waitForTransactionReceipt(tx_hash, timeout=120)
        contractAddress = tx_receipt["contractAddress"]
        self.logger.info("gasUsed={gasUsed} contractAddress={contractAddress}".format(**tx_receipt))
        return contractAddress

    def excuteTransaction(self, func, nonce, acc=None, gas=None, value=None):
        if acc is None:
            acc = self.account
        build_args = {'from': acc.address, 'nonce': nonce, "gasPrice": self.gasPrice}
        if gas:
            build_args["gas"] = gas
        if value:
            build_args["value"] = value
        dproxy_txn = func.buildTransaction(build_args)
        self.logger.info("构建交易: {}".format(dproxy_txn))
        signed = acc.signTransaction(dproxy_txn)
        self.logger.info("签名交易: {}".format(signed))
        tx_hash = self.w3.eth.sendRawTransaction(signed.rawTransaction)
        self.logger.info('{} waiting for receipt..'.format(self.w3.toHex(tx_hash)))
        tx_receipt = self.w3.eth.waitForTransactionReceipt(tx_hash, timeout=600)
        self.logger.info("Receipt accepted. gasUsed={gasUsed} blockNumber={blockNumber}".format(**tx_receipt))
        return self.w3.toHex(tx_hash)

    def approve(self, token_abi_file, tokens, approve_addr, account):
        for token_addr in tokens:
            token = self.get_contract(self.w3.toChecksumAddress(token_addr), token_abi_file)
            balance = token.functions.balanceOf(account.address).call()
            print(balance)
            nonce = self.w3.eth.getTransactionCount(account.address)
            print(nonce)
            contract_func = token.functions.approve(self.w3.toChecksumAddress(approve_addr), balance)
            self.excuteTransaction(contract_func, nonce)

    def allowance(self, token_abi_file, tokens, approve_addr, account):
        for token_addr in tokens:
            token = self.get_contract(self.w3.toChecksumAddress(token_addr), token_abi_file)
            balance = token.functions.balanceOf(account.address).call()
            # print(balance)
            print(token.functions.allowance(account.address, self.w3.toChecksumAddress(approve_addr)).call())

    def tokenBalanceOf(self, token_addr, account_addr):
        token = self.get_contract(self.w3.toChecksumAddress(token_addr), "./abi/ERC20.json")
        balance = token.functions.balanceOf(account_addr).call()
        return balance

    def calBalance(self, amount, decimal=18):
        parseBalance = self.w3.toWei(amount, "ether")
        if decimal == 18:
            return parseBalance
        else:
            return parseBalance // (10 ** (18 - decimal))

    def getUsdcBalance(self, contract, token_addr, account_addr):
        # USDC这种必须通过这种方式来查看balance
        callData = contract.encodeABI(fn_name="balanceOf", args=[account_addr])
        # print(callData)
        tx = {"to": token_addr, "data": callData}
        res = self.w3.eth.call(tx)
        parse_res = self.w3.toInt(res)
        return parse_res

    def getUsdcAllowance(self, contract, token_addr, from_account, account_addr):
        # USDC这种必须通过这种方式来查看balance
        callData = contract.encodeABI(fn_name="allowance", args=[from_account, account_addr])
        # print(callData)
        tx = {"to": token_addr, "data": callData}
        res = self.w3.eth.call(tx)
        parse_res = self.w3.toInt(res)
        return parse_res

    def UsdcApprove(self, contract, token, approve_addr, amount):
        callData = contract.encodeABI(fn_name="approve", args=[approve_addr, amount])
        tx = {"from": self.account.address,
              "to": token,
              "gas": 1000000,
              "gasPrice": self.gasPrice,
              "data": callData,
              "value": 0,
              "chainId": self.w3.eth.chainId,
              "nonce": self.w3.eth.getTransactionCount(self.account.address)}
        # print(callData)
        signed = self.account.signTransaction(tx)
        self.logger.info("签名交易: {}".format(signed))
        tx_hash = self.w3.eth.sendRawTransaction(signed.rawTransaction)
        # tx_hash = self.w3.eth.sendTransaction(tx)
        self.logger.info('{} waiting for receipt..'.format(self.w3.toHex(tx_hash)))
        tx_receipt = self.w3.eth.waitForTransactionReceipt(tx_hash, timeout=120)
        self.logger.info("Receipt accepted. gasUsed={gasUsed} blockNumber={blockNumber}".format(**tx_receipt))
        return self.w3.toHex(tx_hash)


if __name__ == '__main__':

    curPath = os.path.dirname(os.path.abspath(__file__))
    from roxe_libs.pub_function import setCustomLogger
    logger = setCustomLogger("web3.RequestManager", "test1.log", isprintsreen=True, level=logging.INFO)
    # config
    # RPC_ADDRESS = 'https://ropsten.infura.io/v3/be5b825be13b4dda87056e6b073066dc'
    RPC_ADDRESS = 'https://kovan.infura.io/v3/be5b825be13b4dda87056e6b073066dc'
    CONTRACT_DIR = "/Users/admin/GolandProjects/src/project/swapx-v2-contracts/contracts"
    CONTRACT_SOL = 'ExchangeProxy.sol'
    # CONTRACT_SOL = 'simplestorage.sol'
    CONTRACT_NAME = "ExchangeProxy"
    PRIVATE_KEY = "ebed55a1f7e77144623167245abf39df053dc76fd8118ac7ae6e1ceeb84c5ed0"

    # instantiate web3 object
    w3 = Web3(HTTPProvider(RPC_ADDRESS, request_kwargs={'timeout': 120}))
    # use additional middleware for PoA (eg. Rinkedby)
    # w3.middleware_stack.inject(middleware.geth_poa_middleware, layer=0)
    acct = w3.eth.account.privateKeyToAccount(PRIVATE_KEY)

    # # compile contract to get abi
    # print('Compiling contract..')
    # print(load_from_json_file("./DODO/abi/DODO.json"))
    # compiled_sol = compile_standard(load_from_json_file("./DODO/abi/DODO_metadata.json"))
    # contract_name, contract_interface = compile_contract("./DODO/abi/DODO.json", "DODO")
    # contract_name, contract_interface = compile_contract(CONTRACT_DIR + "/exchange/" + CONTRACT_SOL, CONTRACT_NAME)
    # print(compiled_sol)
    # # deploy contract
    print('Deploying contract..')
    info = load_from_json_file("./DODO/abi/DODO.json")
    contract_address = deploy_contract(w3, acct, info['abi'], info['data']["deployedBytecode"]["object"], [acct.address])
    # contract_address = deploy_contract(w3, acct, contract_interface['abi'], contract_interface['bin'], [acct.address])
    # contract_address = deploy_contract(w3, acct, contract_interface['abi'], contract_interface['bin'], ["0x321a103BDB867C830a00F4409870A5B930943e28"])

    # print(contract_address)
    # print(contract_interface)
    # contract_address = "0xacC5A82457239E89e08cD5C305a4Cef3037e16bf"
    # create contract object
    # contract = w3.eth.contract(address=contract_address, abi=contract_interface['abi'])

    # # call non-transactional method
    # val = contract.functions.get().call()
    # print('Invoke get()={}'.format(val))
    # assert val == 0
    #
    # print(contract.all_functions())
    # # call transactional method
    # nonce = w3.eth.getTransactionCount(acct.address)
    # from_block_number = w3.eth.blockNumber
    # new_val = random.randint(1, 100)
    # contract_func = contract.functions.set(new_val)
    # print(contract.encodeABI("add", [1]))
    # print('Invoke set()={}'.format(new_val))
    # print(nonce)
    # tx_hash = exec_contract(w3, acct, nonce, contract_func)
    # print('tx_hash={} waiting for receipt..'.format(tx_hash))
    # tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash, timeout=120)
    # print("Receipt accepted. gasUsed={gasUsed} blockNumber={blockNumber}".format(**tx_receipt))

    # # catch event
    # contract_filter = contract.events.Updated.createFilter(fromBlock=from_block_number)
    # entries = None
    # print('Waiting for event..')
    # while not entries: entries = contract_filter.get_all_entries()
    # # _new == new_val
    # args = entries[0].args
    # print(args)
    # assert args._old == 0
    # assert args._new == new_val
    # assert args.by == acct.address
    #
    # call non-transactional method
    # val = contract.functions.get().call()
    # print('Invoke get()={}'.format(val))
    # assert val == new_val