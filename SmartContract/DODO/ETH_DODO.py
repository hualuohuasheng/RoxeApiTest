# -*- coding: utf-8 -*-
import math
import os
from web3 import Web3, HTTPProvider, WebsocketProvider
from roxe_libs.pub_function import setCustomLogger
from SmartContract.CommonTool import load_from_json_file


curPath = os.path.dirname(os.path.abspath(__file__))

RPC_ADDRESS = 'https://kovan.infura.io/v3/be5b825be13b4dda87056e6b073066dc'
PRIVATE_KEY = "ebed55a1f7e77144623167245abf39df053dc76fd8118ac7ae6e1ceeb84c5ed0"

safeMathAddr = "0xfFB08bC5A3B305EF5Cb4cE7e8Bd057B3FB1ea797"
# decimalMathAddr = "0x5903DEb5a440FAeE9E968d30B494b098511c1441"
decimalMathAddr = "0x887761b9578bE62864C3e90d30B35AdF53Defde7"
# dodoMathAddr = "0x9C104B2628959eb0a2d8aCF14314BACFecc0dfEC"
dodoMathAddr = "0x3fD8521E039197a8f7A0CfA87bF479468A88514a"

token_testa = "0x82ba29500cFDB2425F8fA520eadE00ad66CFA8EB"
token_testb = "0xDd7562c26f6a377d9AAF1Ef27f0D4a79ca370c93"
token_testc = "0x8A13e107cD9C972C5B41fD5cA17755449EEEaC65"

oracleAddr = "0x5AEC9Cb4C4fe026A0186870F2DBFFBC4a6369118" # 740000

# dodoZooAddr = "0x1C7B830459d6136bbd5c5290075Af48Dd79c8f27"
dodoZooAddr = "0xbA7cE09F9B59F88f7395F47d603Cf0314A400Ee2"
# dodoAddr = "0xC703C970bE67Ee5D5028BBc7656dc7b29225F7a3"
# dodoAddr = "0x0553BB31B4368a36932bDBdF9e203300c48dE521"
dodoAddr = "0x52E27F09F42e5bB249098Ed1C7506127C2DAF201"

gasPrice = 1000000000  # 1gwei
one = int(math.pow(10, 18))


class DODOETH:

    def __init__(self, rpc_url, private_key):
        if rpc_url.startswith("http"):
            self.w3 = Web3(HTTPProvider(rpc_url, request_kwargs={'timeout': 120}))
            logger.info("web3 connect status: {}".format(self.w3.isConnected()))
        else:
            self.w3 = Web3(WebsocketProvider(rpc_url))
            logger.info("web3 connect status: {}".format(self.w3.isConnected()))

        self.account = self.w3.eth.account.privateKeyToAccount(private_key)

        self.SafeMath = self.get_contract(safeMathAddr, curPath + "/abi/SafeMath.json")
        self.DecimalMath = self.get_contract(decimalMathAddr, curPath + "/abi/DecimalMath.json")
        self.DDODOMath = self.get_contract(dodoMathAddr, curPath + "/abi/DODOMath.json")
        self.DODOZoo = self.get_contract(dodoZooAddr, curPath + "/abi/DODOZoo.json")

    def get_contract(self, addr, abi_file):
        return self.w3.eth.contract(address=addr, abi=load_from_json_file(abi_file)["abi"])

    def delolyRawTransaction(self):
        tx = {'chainId': self.w3.eth.chainId,
              'from': self.account.address,
              'nonce': self.w3.eth.getTransactionCount(self.account.address),
              'gas': 8000000, 'gasPrice': 1000000000,'value': 0,
              'to': '0x81eD447BE20723fb43a91667B1bA455a87fe6485',
              'data': ''}

    def deploy_contract(self, jsonFile, contractArgs=None):
        contractInfo = load_from_json_file(jsonFile)
        print(len(contractInfo["data"]["bytecode"]["object"]))
        contract = self.w3.eth.contract(abi=contractInfo["abi"], bytecode=contractInfo["data"]["bytecode"]["object"])
        constructed = contract.constructor() if not contractArgs else contract.constructor(*contractArgs)
        tx = constructed.buildTransaction({
            'from': self.account.address,
            'nonce': self.w3.eth.getTransactionCount(self.account.address),
            "gasPrice": gasPrice
        })
        logger.info("Signing and sending raw tx ...")
        signed = self.account.signTransaction(tx)
        tx_hash = self.w3.eth.sendRawTransaction(signed.rawTransaction)
        logger.info("{} waiting for receipt ...".format(tx_hash.hex()))
        tx_receipt = self.w3.eth.waitForTransactionReceipt(tx_hash, timeout=120)
        contractAddress = tx_receipt["contractAddress"]
        logger.info("gasUsed={gasUsed} contractAddress={contractAddress}".format(**tx_receipt))
        return contractAddress

    def excuteTransaction(self, func, nonce, acc=None, gas=None, value=None):
        if acc is None:
            acc = self.account
        build_args = {'from': acc.address, 'nonce': nonce, "gasPrice": gasPrice}
        if gas:
            build_args["gas"] = gas
        if value:
            build_args["value"] = value
        # print(build_args)
        dproxy_txn = func.buildTransaction(build_args)
        logger.info("构建交易: {}".format(dproxy_txn))
        signed = acc.signTransaction(dproxy_txn)
        logger.info("签名交易: {}".format(signed))
        tx_hash = self.w3.eth.sendRawTransaction(signed.rawTransaction)
        logger.info('{} waiting for receipt..'.format(self.w3.toHex(tx_hash)))
        tx_receipt = self.w3.eth.waitForTransactionReceipt(tx_hash, timeout=120)
        logger.info("Receipt accepted. gasUsed={gasUsed} blockNumber={blockNumber}".format(**tx_receipt))
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
        token = self.get_contract(self.w3.toChecksumAddress(token_addr), "./abi/TESTERC20.json")
        balance = token.functions.balanceOf(account_addr).call()
        return balance

    def calBalance(self, amount, decimal=18):
        parseBalance = self.w3.toWei(amount, "ether")
        if decimal == 18:
            return parseBalance
        else:
            return parseBalance // (10 ** (18 - decimal))

    def initDoDo(self, baseToken, qutoToken, oracle, lpFee=1, mtFee=0, k=1, gasPriceLimit=100000000000):
        r = self.DODOZoo.functions.isDODORegistered(baseToken, qutoToken).call()
        assert r is False, "此池子已经创建"
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        exc_func = DODO.functions.init(
            self.account.address, self.account.address, self.account.address,
            baseToken, qutoToken, oracle,
            lpFee, mtFee, k, gasPriceLimit
        )
        self.excuteTransaction(exc_func, nonce)
        self.addDoDo(self.w3.toChecksumAddress(DODO.address))

    def addDoDo(self, dodo):
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        exc_func = self.DODOZoo.functions.addDODO(dodo)
        self.excuteTransaction(exc_func, nonce, self.account)

    def enableTrading(self):
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        exc_func = DODO.functions.enableTrading()
        self.excuteTransaction(exc_func, nonce, self.account)
        assert DODO.functions._TRADE_ALLOWED_().call()

    def enableBaseDeposit(self):
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        exc_func = DODO.functions.enableBaseDeposit()
        self.excuteTransaction(exc_func, nonce, self.account)
        assert DODO.functions._DEPOSIT_BASE_ALLOWED_().call()

    def enableQuoteDeposit(self):
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        exc_func = DODO.functions.enableQuoteDeposit()
        self.excuteTransaction(exc_func, nonce, self.account)
        assert DODO.functions._DEPOSIT_QUOTE_ALLOWED_().call()

    def depositeBase(self, amount):
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        exc_func = DODO.functions.depositBase(amount)
        self.excuteTransaction(exc_func, nonce, self.account)

    def depositeQuote(self, amount):
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        exc_func = DODO.functions.depositQuote(amount)
        self.excuteTransaction(exc_func, nonce, self.account)

    def withdrawBase(self, amount):
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        exc_func = DODO.functions.withdrawBase(amount)
        self.excuteTransaction(exc_func, nonce, self.account)

    def withdrawQuote(self, amount):
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        exc_func = DODO.functions.withdrawQuote(amount)
        self.excuteTransaction(exc_func, nonce, self.account)

    def buyBaseToken(self, amount, maxPayQuote):
        logger.info("queryBuyBaseToken: {}".format(DODO.functions._queryBuyBaseToken(amount).call()))
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        exc_func = DODO.functions.buyBaseToken(amount, maxPayQuote, "0x")
        self.excuteTransaction(exc_func, nonce, self.account)

    def sellBaseToken(self, amount, minReceiveQuote):
        logger.info("querySellBaseToken: {}".format(DODO.functions._querySellBaseToken(amount).call()))
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        exc_func = DODO.functions.sellBaseToken(amount, minReceiveQuote, "0x")
        self.excuteTransaction(exc_func, nonce, self.account)

    def setK(self, newK):
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        exc_func = DODO.functions.setK(newK)
        self.excuteTransaction(exc_func, nonce, self.account)

    def setLiquidityProviderFeeRate(self, newLPFee):
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        exc_func = DODO.functions.setLiquidityProviderFeeRate(newLPFee)
        self.excuteTransaction(exc_func, nonce, self.account)

    def setMaintainerFeeRate(self, newMtFee):
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        exc_func = DODO.functions.setMaintainerFeeRate(newMtFee)
        self.excuteTransaction(exc_func, nonce, self.account)

    def getPoolBalance(self):
        baseBalance = DODO.functions._BASE_BALANCE_().call()
        quoteBalance = DODO.functions._QUOTE_BALANCE_().call()
        targetBaseBalance = DODO.functions._TARGET_BASE_TOKEN_AMOUNT_().call()
        targetQuoteBalance = DODO.functions._TARGET_QUOTE_TOKEN_AMOUNT_().call()
        logger.info("baseBalance: {}".format(baseBalance))
        logger.info("quoteBalance: {}".format(quoteBalance))
        logger.info("targetBaseBalance: {}".format(targetBaseBalance))
        logger.info("targetQuoteBalance: {}".format(targetQuoteBalance))


if __name__ == "__main__":
    logger = setCustomLogger("ethDoDo", "eth_dodo.log", isprintsreen=True)
    client = DODOETH(RPC_ADDRESS, PRIVATE_KEY)

    # client.deploy_contract(curPath + "/abi/DODOZoo.json",
    #                        [
    #                            "0x3c5Ab3757de3DfFBDb179800C26bE7705592a816",
    #                            "0xAAfF7478c1652C4D2B91C38956C01ae7DABEF109",
    #                            client.account.address
    #                        ])
    DODO = client.get_contract(dodoAddr, curPath + "/abi/DODO.json")

    # print(DODO.all_functions())
    # print(client.account.address)
    # client.initDoDo(token_testa, token_testc, oracleAddr)
    # client.initDoDo(token_testa, token_testc, oracleAddr, 595000000000000, 100000000000005, 100000000000000)
    # print(DODO.functions._BASE_TOKEN_().call())
    # client.enableTrading()
    # client.enableBaseDeposit()
    # client.enableQuoteDeposit()

    # print(client.tokenBalanceOf(token_testa, client.account.address))
    # print(client.tokenBalanceOf(token_testc, client.account.address))
    # client.allowance(curPath + "/abi/TESTERC20.json", [token_testa, token_testc], dodoAddr, client.account)
    # client.approve(curPath + "/abi/TESTERC20.json", [token_testa, token_testc], dodoAddr, client.account)

    # client.depositeBase(1000000000000)
    # client.depositeQuote(740000000000)

    # client.getPoolBalance()
    # logger.info("R: {}".format(DODO.functions._R_STATUS_().call()))
    # logger.info("_LP_FEE_RATE_: {}".format(DODO.functions._LP_FEE_RATE_().call()))
    # logger.info("_MT_FEE_RATE_: {}".format(DODO.functions._MT_FEE_RATE_().call()))
    # logger.info("_K_: {}".format(DODO.functions._K_().call()))
    # logger.info("Price: {}".format(DODO.functions.getOraclePrice().call()))
    # logger.info("queryBuyBaseToken: {}".format(DODO.functions._queryBuyBaseToken(1500000).call()))
    # logger.info("queryBuyBaseToken: {}".format(DODO.functions._queryBuyBaseToken(1340943400).call()))
    # r = DODO.functions._querySellBaseToken(1000000000).call()
    # r = DODO.functions._queryBuyBaseToken(1000000000).call()
    # logger.info("querySellBaseToken: {}, withFee: {}".format(r, r[0]+r[1]+r[2]))

    # client.buyBaseToken(1002600853104 , 79999999000000)
    # client.sellBaseToken(3000000000, 7000000)
    # client.getPoolBalance()

    # client.setLiquidityProviderFeeRate(595000000000000)
    # client.setMaintainerFeeRate(105000000000000)
    # client.setK(100000000000000)

    # client.depositeBase(100000000)
    # client.depositeQuote(100000000)
    #
    # client.withdrawBase(99997828)
    # client.withdrawQuote(100000)

    # oracle = client.get_contract(oracleAddr, curPath + "/abi/Oracle.json")
    # print(oracle.functions.getPrice().call())
    # nonce = client.w3.eth.getTransactionCount(client.account.address)
    # exc_func = oracle.functions.setPrice(int(0.74 * one))
    # client.excuteTransaction(exc_func, nonce, client.account)
    # print(client.DDODOMath.functions._SolveQuadraticFunctionForTarget(999999000000, 1, 1000000).call())

    # print(client.DecimalMath.all_functions())
    from SmartContract.DODO.common import *
    # print(client.DecimalMath.functions.mul(1, 2).call())
    fairAmount = DecimalMath.divFloor(870608442548 - 740512005520, 740000000000000000)
    targetBase = client.DDODOMath.functions._SolveQuadraticFunctionForTarget(1004496533119, 100000000000000, fairAmount).call()
    targetBaseWithWithdraw = client.DDODOMath.functions._SolveQuadraticFunctionForTarget(1004496533119 - 99999, 100000000000000, fairAmount).call()
    # client.DDODOMath.functions._SolveQuadraticFunctionForTarget(1004496533119-99999, 100000000000000, )
    print(fairAmount, targetBase, targetBaseWithWithdraw)