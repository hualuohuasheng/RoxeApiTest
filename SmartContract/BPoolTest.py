from SmartContract.CommonTool import load_from_json_file
from roxe_libs.pub_function import setCustomLogger
from web3 import Web3, HTTPProvider, WebsocketProvider
import logging
import traceback
import time

BONE = 1000000000000000000


def bdiv(a, b):
    a1 = a * BONE
    assert a1 == 0 or a1 / a == BONE
    c = (b // 2 + a1) // b
    # print(int(c))
    return int(c)


def bmul(a, b):
    c0 = int(a * b)
    # print(c0, c0/a, b)
    assert c0 == 0 or c0 // a == b
    c1 = c0 + int(BONE // 2)
    c2 = c1 // int(BONE)
    return int(c2)


def bsub(a, b):
    c, flag = bsubSign(a, b)
    if flag:
        raise Exception("{} - {} 不够减".format(a, b))
    return c


def bsubSign(a, b):
    if a >= b:
        return a - b, False
    else:
        return b - a, True


class BActionTest:

    def __init__(self, rpc_url, private_key):
        if rpc_url.startswith("http"):
            self.w3 = Web3(HTTPProvider(rpc_url, request_kwargs={'timeout': 120}))
            logger.info("web3 connect status: {}".format(self.w3.isConnected()))
        else:
            self.w3 = Web3(WebsocketProvider(rpc_url))
            logger.info("web3 connect status: {}".format(self.w3.isConnected()))
        self.bAction = self.get_contract(BAction_addr, BAction_abi_file)
        self.dProxy = self.get_contract(dProxy_addr, dProxy_abi_file)
        self.exchangeProxy = self.get_contract(exchangeProxy_addr, exchangeProxy_abi_file)
        self.account = self.w3.eth.account.privateKeyToAccount(private_key)

    def get_contract(self, addr, abi_file):
        return self.w3.eth.contract(address=self.w3.toChecksumAddress(addr), abi=load_from_json_file(abi_file)["abi"])

    def deploy_contract(self, jsonFile, contractArgs=None):
        contractInfo = load_from_json_file(jsonFile)
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
        token = self.get_contract(self.w3.toChecksumAddress(token_addr), "./abi/ERC20.json")
        balance = token.functions.balanceOf(account_addr).call()
        return balance

    def calBalance(self, amount, decimal=18):
        parseBalance = self.w3.toWei(amount, "ether")
        if decimal == 18:
            return parseBalance
        else:
            return parseBalance // (10 ** (18 - decimal))

    def getPoolInfo(self, poolAddress, userAccount):
        feeAccount = BFactoryContract.functions.feeTo().call()
        pool = self.get_contract(poolAddress, abi_file="./abi/BPool.json")
        tokens = pool.functions.getCurrentTokens().call()
        logger.info("获取当前pool的tokens:{}".format(tokens))
        tokenBalances = []
        poolInTokenBalance = []
        userBalance = []
        denorms = []
        feeBalance = []
        for token in tokens:
            tokenContract = self.get_contract(self.w3.toChecksumAddress(token), "./abi/ERC20.json")
            tokenBalances.append(pool.functions.getBalance(token).call())
            denorms.append(pool.functions.getDenormalizedWeight(token).call())
            poolInTokenBalance.append(tokenContract.functions.balanceOf(poolAddress).call())
            userBalance.append(tokenContract.functions.balanceOf(userAccount).call())
            feeBalance.append(tokenContract.functions.balanceOf(feeAccount).call())
        return tokens, tokenBalances, denorms, poolInTokenBalance, userBalance, feeBalance

    def checkBActionCreate(self, tokens):
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        decimals = []
        for t in tokens:
            tokenInContract = self.get_contract(t, "./abi/ERC20.json")
            decimals.append(tokenInContract.functions.decimals().call())
        logger.info("tokens的精度为: {}".format(decimals))
        tokenInbalance1 = self.calBalance(4750, decimals[0])
        tokenInbalance2 = self.calBalance(2500, decimals[1])
        # tokenInbalance1 = 30172805345347762825
        # tokenInbalance2 = 6281284683144818017253
        # initlp = 545553052126845541190
        initlp = 0
        action_func = self.bAction.functions.create(BFactory,
                                                    tokens,
                                                    [tokenInbalance1, tokenInbalance2],
                                                    [self.w3.toWei("1", 'ether'), self.w3.toWei("1", 'ether')],
                                                    self.w3.toWei("0.003", 'ether'),
                                                    initlp, True)
        action_txn = action_func.buildTransaction({'from': self.account.address, 'nonce': nonce, "gas": 8000000,
                                                   "gasPrice": gasPrice})

        # print("gas", self.w3.eth.estimateGas(construct_txn))
        # print(action_func)
        callData = action_txn["data"]
        logger.info("get baction create calldata: {}".format(callData))
        dproxy_func = self.dProxy.get_function_by_signature('execute(address,bytes)')(BAction_addr, callData)
        logger.info("准备通过DSProxy执行BAction的 create...")
        # tx_hash = self.excuteTransaction(dproxy_func, nonce)
        # res = self.w3.eth.getTransactionReceipt(tx_hash)
        # if res["status"] == 1:
        #     logger.info("bpool address: {}".format(res["logs"][2]["address"]))
        #     return self.w3.toChecksumAddress(res["logs"][2]["address"])

    def checkBActionCreateWithEth(self, tokens, isMoreEth=False):
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        decimals = []
        for t in tokens:
            if t == ETH:
                decimals.append(18)
                continue
            tokenInContract = self.get_contract(t, "./abi/ERC20.json")
            decimals.append(tokenInContract.functions.decimals().call())
        userETH = self.w3.eth.getBalance(self.account.address)
        logger.info("用户eth的资产:{}".format(userETH))
        logger.info("tokens的精度为: {}".format(decimals))
        ethBalance = self.calBalance(0.01, decimals[0])
        tokenInbalance2 = self.calBalance(6.2, decimals[1])
        addEth = self.calBalance(0.01, decimals[0]) if isMoreEth else 0
        initlp = 0
        action_func = self.bAction.functions.create(BFactory,
                                                    tokens,
                                                    [ethBalance, tokenInbalance2],
                                                    [self.w3.toWei("1", 'ether'), self.w3.toWei("1", 'ether')],
                                                    self.w3.toWei("0.003", 'ether'),
                                                    initlp, True)
        action_txn = action_func.buildTransaction({'from': self.account.address, 'nonce': nonce, "gas": 8000000,
                                                   "gasPrice": gasPrice, "value": ethBalance + addEth})
        # print(action_txn)
        callData = action_txn["data"]
        logger.info("get baction create calldata: {}".format(callData))
        dproxy_func = self.dProxy.get_function_by_signature('execute(address,bytes)')(BAction_addr, callData)
        logger.info("准备通过DSProxy执行BAction的 create...")
        try:
            tx_hash = self.excuteTransaction(dproxy_func, nonce, value=ethBalance+addEth)
        except Exception:
            if isMoreEth:
                logger.info("创建池子时不允许转给合约的eth和参数中balance中的值不一致")
                return
            else:
                logger.error(tx_hash)
        res = self.w3.eth.getTransactionReceipt(tx_hash)
        userETH2 = self.w3.eth.getBalance(self.account.address)
        logger.info("创建池子后,用户eth的资产:{}".format(userETH2))
        assert userETH2 + ethBalance + self.w3.toWei(res["gasUsed"], "gwei") - addEth == userETH
        if res["status"] == 1:
            logger.info("bpool address: {}".format(res["logs"][2]["address"]))
            return self.w3.toChecksumAddress(res["logs"][2]["address"])

    def checkBActionCreateWithPair(self, gp_addr, dp_weight, gp_rate, tokens):
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        decimals = []
        for t in tokens:
            tokenInContract = self.get_contract(t, "./abi/ERC20.json")
            decimals.append(tokenInContract.functions.decimals().call())
        logger.info("tokens的精度为: {}".format(decimals))
        tokenInbalance1 = self.calBalance(4750, decimals[0])
        tokenInbalance2 = self.calBalance(2500, decimals[1])
        action_func = self.bAction.functions.createWithPair(BFactory, PairFactory,
                                                            tokens,
                                                            [tokenInbalance1,
                                                             tokenInbalance2],
                                                            [self.w3.toWei("8", 'ether'),
                                                             self.w3.toWei("2", 'ether')],
                                                            gp_addr, dp_weight,
                                                            self.w3.toWei("0.003", 'ether'), gp_rate)
        action_txn = action_func.buildTransaction({'from': self.account.address,
                                                   'nonce': nonce,
                                                   "gas": 8000000,
                                                   "gasPrice": 1000000000})
        callData = action_txn["data"]
        logger.info("get baction createWithPair calldata: {}".format(callData))
        dproxy_func = self.dProxy.get_function_by_signature('execute(address,bytes)')(BAction_addr, callData)
        logger.info("准备通过DSProxy执行BAction的 createWithPair...")
        tx_hash = self.excuteTransaction(dproxy_func, nonce)
        res = self.w3.eth.getTransactionReceipt(tx_hash)
        if res["status"] == 1:
            logger.info("pool address: {}".format(self.w3.toChecksumAddress(res["logs"][2]["address"])))
            logger.info("pair address: {}".format(self.w3.toChecksumAddress(res["logs"][16]["address"])))
            return self.w3.toChecksumAddress(res["logs"][2]["address"]), self.w3.toChecksumAddress(res["logs"][16]["address"])

    def checkBActionCreateWithPairUseEth(self, gp_addr, dp_weight, gp_rate, tokens):
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        decimals = []
        for t in tokens:
            if t == ETH:
                decimals.append(18)
                continue
            tokenInContract = self.get_contract(t, "./abi/ERC20.json")
            decimals.append(tokenInContract.functions.decimals().call())
        logger.info("tokens的精度为: {}".format(decimals))
        # ethIndex = tokens.index(ETH)
        # ethBalance = self.calBalance(0.0001, decimals[ethIndex])
        tokenInbalance1 = self.calBalance(0.001, decimals[0])
        tokenInbalance2 = self.calBalance(2500, decimals[1])
        action_func = self.bAction.functions.createWithPair(BFactory, PairFactory,
                                                            tokens,
                                                            [tokenInbalance1,
                                                             tokenInbalance2],
                                                            [self.w3.toWei("1", 'ether'),
                                                             self.w3.toWei("1", 'ether')],
                                                            gp_addr, dp_weight,
                                                            self.w3.toWei("0.003", 'ether'), gp_rate)
        print(action_func)
        action_txn = action_func.buildTransaction({'from': self.account.address,
                                                   'nonce': nonce,
                                                   "gas": 8000000,
                                                   "gasPrice": 1000000000,
                                                   "value": tokenInbalance1})
        callData = action_txn["data"]
        logger.info("get baction createWithPair calldata: {}".format(callData))
        # dproxy_func = self.dProxy.get_function_by_signature('execute(address,bytes)')(BAction_addr, callData)
        # logger.info("准备通过DSProxy执行BAction的 createWithPair...")
        # tx_hash = self.excuteTransaction(dproxy_func, nonce, value=tokenInbalance1)
        # res = self.w3.eth.getTransactionReceipt(tx_hash)
        # if res["status"] == 1:
        #     logger.info("pool address: {}".format(self.w3.toChecksumAddress(res["logs"][2]["address"])))
        #     # logger.info("pair address: {}".format(self.w3.toChecksumAddress(res["logs"][16]["address"])))
        #     return self.w3.toChecksumAddress(res["logs"][2]["address"])

    def checkJoinPool(self, pool, poolAddress, acc=None):
        if acc is None:
            acc = self.account
        nonce = self.w3.eth.getTransactionCount(acc.address)
        tokens, balances, tokenDernoms, poolInTokenBalance, userBalance, feeBalance = self.getPoolInfo(poolAddress, acc.address)
        logger.info("获取当前pool记录的token balance: {}".format(balances))
        logger.info("获取当前pool在token中实际持有的balance: {}".format(poolInTokenBalance))
        currentSupply = pool.functions.totalSupply().call()
        logger.info("获取当前pool的totalSupply: {}".format(currentSupply))
        logger.info("用户持有的资产: {}".format(userBalance))
        persent = 1
        # 加入池子按1%比例添加
        poolMinOut = int(currentSupply * persent // 100)
        ratio = bdiv(poolMinOut, currentSupply)
        # print(ratio)
        maxAmountIn = []
        for i in balances:
            # print(bmul(ratio, i))
            maxAmountIn.append(bmul(ratio, i))
        logger.info("计算加入1%的LP所需的参数: lp: {}, tokenBalance:{}".format(poolMinOut, maxAmountIn))
        action_func = self.bAction.functions.joinPool(poolAddress, poolMinOut, maxAmountIn)
        action_txn = action_func.buildTransaction({'from': acc.address,
                                                   'nonce': nonce,
                                                   "gas": 8000000,
                                                   "gasPrice": 1000000000})
        callData = action_txn["data"]
        logger.info("get baction joinPool calldata: {}".format(callData))
        dproxy_func = self.dProxy.get_function_by_signature('execute(address,bytes)')(BAction_addr, callData)
        logger.info("准备通过DSProxy执行BAction的 joinPool...")
        tx_hash = self.excuteTransaction(dproxy_func, nonce, acc)
        tokens2, afterBalances, tokenDernoms2, poolInTokenBalance2, userBalance2, feeBalance2 = self.getPoolInfo(poolAddress, acc.address)

        logger.info("交易前资产: {}".format(balances))
        logger.info("交易后资产: {}".format(afterBalances))
        logger.info("交易后pool实际持有资产: {}".format(poolInTokenBalance2))
        logger.info("交易后用户持有资产: {}".format(userBalance2))
        changesBalance = []
        for i in range(2):
            tmp = afterBalances[i] - balances[i]
            ptBalance = poolInTokenBalance2[i] - poolInTokenBalance[i]
            assert tmp <= maxAmountIn[i], "{}和{}资产变化不一致".format(tmp, maxAmountIn[i])
            assert tmp == ptBalance, "pool中记录资产和实际持有资产的变化不一致: {} {}".format(tmp, ptBalance)
            assert tmp == userBalance[i] - userBalance2[i], "用户资产变化不一致: {} {}".format(tmp, userBalance[i] - userBalance2[i])
            assert afterBalances[i] == poolInTokenBalance2[i], "pool中记录资产和实际持有资产不一致: {} {}".format(afterBalances[i], ptBalance)
            changesBalance.append(tmp)
        afterSupply = pool.functions.totalSupply().call()

        logger.info("资产变化: {}".format(changesBalance))

        assert currentSupply + poolMinOut == afterSupply, "交易前 {}, 交易后{},变化:{}".format(currentSupply, afterSupply, poolMinOut)
        return tx_hash

    def checkJoinPoolWithEth(self, pool, poolAddress, acc=None):
        if acc is None:
            acc = self.account
        nonce = self.w3.eth.getTransactionCount(acc.address)
        tokens, balances, tokenDernoms, poolInTokenBalance, userBalance, feeBalance = self.getPoolInfo(poolAddress, acc.address)
        logger.info("获取当前pool记录的token balance: {}".format(balances))
        logger.info("获取当前pool在token中实际持有的balance: {}".format(poolInTokenBalance))
        currentSupply = pool.functions.totalSupply().call()
        logger.info("获取当前pool的totalSupply: {}".format(currentSupply))
        logger.info("用户持有的资产: {}".format(userBalance))
        userEth = self.w3.eth.getBalance(self.account.address)
        logger.info("用户持有的eth:{}".format(userEth))
        persent = 1
        # 加入池子按1%比例添加
        poolMinOut = int(currentSupply * persent // 100)
        ratio = bdiv(poolMinOut, currentSupply)
        # print(ratio)
        maxAmountIn = []
        for i in balances:
            # print(bmul(ratio, i))
            maxAmountIn.append(bmul(ratio, i))
        if WETH in tokens:
            wethIndex = tokens.index(WETH)
            ethValue = maxAmountIn[wethIndex]
        else:
            ethValue = 0
        logger.info("要加入的eth数量为: {}".format(ethValue))
        logger.info("计算加入1%的LP所需的参数: lp: {}, tokenBalance:{}".format(poolMinOut, maxAmountIn))
        action_func = self.bAction.functions.joinPool(poolAddress, poolMinOut, maxAmountIn)
        action_txn = action_func.buildTransaction({'from': acc.address,
                                                   'nonce': nonce,
                                                   "gas": 8000000,
                                                   "gasPrice": 1000000000,
                                                   "value": ethValue})
        callData = action_txn["data"]
        print(action_txn)
        logger.info("get baction joinPool calldata: {}".format(callData))
        dproxy_func = self.dProxy.get_function_by_signature('execute(address,bytes)')(BAction_addr, callData)
        logger.info("准备通过DSProxy执行BAction的 joinPool...")
        tx_hash = self.excuteTransaction(dproxy_func, nonce, acc, value=ethValue)
        tokens2, afterBalances, tokenDernoms2, poolInTokenBalance2, userBalance2, feeBalance2 = self.getPoolInfo(poolAddress, acc.address)

        tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
        logger.info("交易前资产: {}".format(balances))
        logger.info("交易后资产: {}".format(afterBalances))
        logger.info("交易后pool实际持有资产: {}".format(poolInTokenBalance2))
        logger.info("交易后用户持有资产: {}".format(userBalance2))
        userEth2 = self.w3.eth.getBalance(self.account.address)
        logger.info("用户持有的eth:{}".format(userEth2))
        changesBalance = []
        for i in range(2):
            tmp = afterBalances[i] - balances[i]
            ptBalance = poolInTokenBalance2[i] - poolInTokenBalance[i]
            assert tmp <= maxAmountIn[i], "{}和{}资产变化不一致".format(tmp, maxAmountIn[i])
            assert tmp == ptBalance, "pool中记录资产和实际持有资产的变化不一致: {} {}".format(tmp, ptBalance)
            if tokens[i] == WETH:
                assert tmp + self.w3.toWei(tx_info["gasUsed"], "gwei") == userEth - userEth2, "用户资产变化不一致: {} {}".format(tmp, userEth - userEth2)
            else:
                assert tmp == userBalance[i] - userBalance2[i], "用户资产变化不一致: {} {}".format(tmp, userBalance[i] - userBalance2[i])
            assert afterBalances[i] == poolInTokenBalance2[i], "pool中记录资产和实际持有资产不一致: {} {}".format(afterBalances[i], ptBalance)
            changesBalance.append(tmp)
        afterSupply = pool.functions.totalSupply().call()

        logger.info("资产变化: {}".format(changesBalance))

        assert currentSupply + poolMinOut == afterSupply, "交易前 {}, 交易后{},变化:{}".format(currentSupply, afterSupply, poolMinOut)

    def checkJoinPoolWhenAmountInLessThanRequireAmount(self, pool, poolAddress, acc=None):
        if acc is None:
            acc = self.account
        nonce = self.w3.eth.getTransactionCount(acc.address)
        tokens = pool.functions.getCurrentTokens().call()
        logger.info("获取当前pool的tokens:{}".format(tokens))
        balances = []
        poolInTokenBalance = []
        userBalance = []
        for token in tokens:
            balances.append(pool.functions.getBalance(token).call())
            poolInTokenBalance.append(self.tokenBalanceOf(token, poolAddress))
            userBalance.append(self.tokenBalanceOf(token, acc.address))
        logger.info("获取当前pool记录的token balance: {}".format(balances))
        logger.info("获取当前pool在token中实际持有的balance: {}".format(poolInTokenBalance))
        currentSupply = pool.functions.totalSupply().call()
        logger.info("获取当前pool的totalSupply: {}".format(currentSupply))
        logger.info("用户持有的资产: {}".format(userBalance))
        persent = 1
        # 加入池子按1%比例添加
        poolMinOut = int(currentSupply * persent // 100)
        ratio = bdiv(poolMinOut, currentSupply)
        # print(ratio)
        maxAmountIn = []
        for i in balances:
            # print(bmul(ratio, i))
            maxAmountIn.append(bmul(ratio, i) - 1)
        logger.info("计算加入1%的LP所需的参数: lp: {}, tokenBalance:{}".format(poolMinOut, maxAmountIn))
        action_func = self.bAction.functions.joinPool(poolAddress, poolMinOut, maxAmountIn)
        action_txn = action_func.buildTransaction({'from': acc.address,
                                                   'nonce': nonce,
                                                   "gas": 8000000,
                                                   "gasPrice": 1000000000})
        callData = action_txn["data"]
        logger.info("get baction joinPool calldata: {}".format(callData))
        dproxy_func = self.dProxy.get_function_by_signature('execute(address,bytes)')(BAction_addr, callData)
        logger.info("准备通过DSProxy执行BAction的 joinPool...")
        tx_hash = self.excuteTransaction(dproxy_func, nonce, acc, 3000000)

        tx_res = self.w3.eth.getTransactionReceipt(tx_hash)
        logger.info("交易结果: {}".format(tx_res))

        assert tx_res["status"] == 0, "交易应该会失败"
        afterBalances = []
        poolInTokenBalance2 = []
        userBalance2 = []
        for token in tokens:
            afterBalances.append(pool.functions.getBalance(token).call())
            poolInTokenBalance2.append(self.tokenBalanceOf(token, poolAddress))
            userBalance2.append(self.tokenBalanceOf(token, acc.address))

        logger.info("交易前资产: {}".format(balances))
        logger.info("交易后资产: {}".format(afterBalances))
        logger.info("交易后pool实际持有资产: {}".format(poolInTokenBalance2))
        logger.info("交易后用户持有资产: {}".format(userBalance2))
        changesBalance = []
        for i in range(2):
            tmp = afterBalances[i] - balances[i]
            ptBalance = poolInTokenBalance2[i] - poolInTokenBalance[i]
            assert tmp == 0, "{}和0资产变化不一致".format(tmp)
            assert tmp == ptBalance, "pool中记录资产和实际持有资产的变化不一致: {} {}".format(tmp, ptBalance)
            assert tmp == userBalance[i] - userBalance2[i], "用户资产变化不一致: {} {}".format(tmp, userBalance[i] - userBalance2[i])
            assert afterBalances[i] == poolInTokenBalance2[i], "pool中记录资产和实际持有资产不一致: {} {}".format(afterBalances[i], ptBalance)
            changesBalance.append(tmp)
        logger.info("资产变化: {}".format(changesBalance))
        afterSupply = pool.functions.totalSupply().call()
        assert currentSupply == afterSupply, "交易前 {}, 交易后{},变化:{}".format(currentSupply, afterSupply, 0)

    def checkJoinPoolWhenUserTokenBalanceNotEnough(self, pool, poolAddress, acc=None):
        if acc is None:
            acc = self.account
        nonce = self.w3.eth.getTransactionCount(acc.address)
        tokens = pool.functions.getCurrentTokens().call()
        logger.info("获取当前pool的tokens:{}".format(tokens))
        balances = []
        poolInTokenBalance = []
        userBalance = []
        for token in tokens:
            balances.append(pool.functions.getBalance(token).call())
            poolInTokenBalance.append(self.tokenBalanceOf(token, poolAddress))
            userBalance.append(self.tokenBalanceOf(token, acc.address))
        logger.info("获取当前pool记录的token balance: {}".format(balances))
        logger.info("获取当前pool在token中实际持有的balance: {}".format(poolInTokenBalance))
        currentSupply = pool.functions.totalSupply().call()
        logger.info("获取当前pool的totalSupply: {}".format(currentSupply))
        logger.info("用户持有的资产: {}".format(userBalance))
        persent = 1000
        # 加入池子按1%比例添加
        poolMinOut = int(currentSupply * persent // 100)
        ratio = bdiv(poolMinOut, currentSupply)
        # print(ratio)
        maxAmountIn = []
        for index, b in enumerate(balances):
            assert bmul(ratio, b) > userBalance[index]
            maxAmountIn.append(bmul(ratio, b))
        logger.info("计算加入1%的LP所需的参数: lp: {}, tokenBalance:{}".format(poolMinOut, maxAmountIn))
        action_func = self.bAction.functions.joinPool(poolAddress, poolMinOut, maxAmountIn)
        action_txn = action_func.buildTransaction({'from': acc.address,
                                                   'nonce': nonce,
                                                   "gas": 8000000,
                                                   "gasPrice": 1000000000})
        callData = action_txn["data"]
        logger.info("get baction joinPool calldata: {}".format(callData))
        dproxy_func = self.dProxy.get_function_by_signature('execute(address,bytes)')(BAction_addr, callData)
        logger.info("准备通过DSProxy执行BAction的 joinPool...")
        tx_hash = self.excuteTransaction(dproxy_func, nonce, acc, 3000000)

        tx_res = self.w3.eth.getTransactionReceipt(tx_hash)
        logger.info("交易结果: {}".format(tx_res))

        assert tx_res["status"] == 0, "交易应该会失败"
        afterBalances = []
        poolInTokenBalance2 = []
        userBalance2 = []
        for token in tokens:
            afterBalances.append(pool.functions.getBalance(token).call())
            poolInTokenBalance2.append(self.tokenBalanceOf(token, poolAddress))
            userBalance2.append(self.tokenBalanceOf(token, acc.address))

        logger.info("交易前资产: {}".format(balances))
        logger.info("交易后资产: {}".format(afterBalances))
        logger.info("交易后pool实际持有资产: {}".format(poolInTokenBalance2))
        logger.info("交易后用户持有资产: {}".format(userBalance2))
        changesBalance = []
        for i in range(2):
            tmp = afterBalances[i] - balances[i]
            ptBalance = poolInTokenBalance2[i] - poolInTokenBalance[i]
            assert tmp == 0, "{}和0资产变化不一致".format(tmp)
            assert tmp == ptBalance, "pool中记录资产和实际持有资产的变化不一致: {} {}".format(tmp, ptBalance)
            assert tmp == userBalance[i] - userBalance2[i], "用户资产变化不一致: {} {}".format(tmp, userBalance[i] - userBalance2[i])
            assert afterBalances[i] == poolInTokenBalance2[i], "pool中记录资产和实际持有资产不一致: {} {}".format(afterBalances[i], ptBalance)
            changesBalance.append(tmp)
        logger.info("资产变化: {}".format(changesBalance))
        afterSupply = pool.functions.totalSupply().call()
        assert currentSupply == afterSupply, "交易前 {}, 交易后{},变化:{}".format(currentSupply, afterSupply, 0)

    def checkJoinSwapExternAmountIn(self, pool, poolAddress, tokenInAddress):
        # joinswapExternAmountIn
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        tokens = pool.functions.getCurrentTokens().call()
        logger.info("获取当前pool的tokens:{}".format(tokens))
        balances = []
        for token in tokens:
            balances.append(pool.functions.getBalance(token).call())

        inBalance = pool.functions.getBalance(tokenInAddress).call()
        inDenorm = pool.functions.getDenormalizedWeight(tokenInAddress).call()
        logger.info("获取当前pool的tokenIn的balance: {}".format(inBalance))
        logger.info("获取当前pool的tokenIn的denorm: {}".format(inDenorm))
        totalSupply = pool.functions.totalSupply().call()
        logger.info("获取当前pool的totalSupply: {}".format(totalSupply))
        totalWeight = pool.functions.getTotalDenormalizedWeight().call()
        logger.info("获取当前pool的totalWeight: {}".format(totalWeight))
        fee = pool.functions.getSwapFee().call()
        # 加入池子的tokenIn数量
        tokenAmountIn = self.w3.toWei("10", "ether")
        poolAmountOut = pool.functions.calcPoolOutGivenSingleIn(inBalance, inDenorm, totalSupply, totalWeight,
                                                                tokenAmountIn, fee).call()
        logger.info("计算{}的tokenIn得到的LP:{}".format(tokenAmountIn, poolAmountOut))
        action_func = self.bAction.functions.joinswapExternAmountIn(poolAddress, tokenInAddress, tokenAmountIn,
                                                                    poolAmountOut)
        action_txn = action_func.buildTransaction({'from': self.account.address,
                                                   'nonce': nonce,
                                                   "gas": 8000000,
                                                   "gasPrice": 1000000000})
        callData = action_txn["data"]
        # logger.info("get baction joinPool calldata: {}".format(callData))
        dproxy_func = self.dProxy.get_function_by_signature('execute(address,bytes)')(BAction_addr, callData)
        logger.info("准备通过DSProxy执行BAction的 joinswapExternAmountIn...")
        self.excuteTransaction(dproxy_func, nonce)

        afterBalances = []
        for token in tokens:
            afterBalances.append(pool.functions.getBalance(token).call())
        changesBalance = afterBalances[0] - balances[0]
        afterSupply = pool.functions.totalSupply().call()
        logger.info("交易前资产: {}".format(balances))
        logger.info("交易后资产: {}".format(afterBalances))
        logger.info("资产变化: {}".format(changesBalance))
        assert totalSupply + poolAmountOut == afterSupply, "交易前 {}, 交易后{},变化:{}".format(totalSupply, afterSupply,
                                                                                       poolAmountOut)

    def checkSwapExactAmountIn(self, pool, poolAddress, tokenInAddress, tokenOutAddress):
        # swapExactAmountIn
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        tokens, tokenBalances, tokenDenorms, poolInTokenBalance, userBalance, feeBalance = self.getPoolInfo(
            poolAddress, self.account.address
        )

        logger.info("获取当前pool记录的token资产: {}".format(tokenBalances))
        logger.info("获取当前pool的denorm: {}".format(tokenDenorms))
        logger.info("获取当前pool实际持有的token资产: {}".format(poolInTokenBalance))
        logger.info("获取交易费用账户的资产: {}".format(feeBalance))
        logger.info("获取用户的资产: {}".format(userBalance))
        totalSupply = pool.functions.totalSupply().call()
        logger.info("获取当前pool的totalSupply: {}".format(totalSupply))
        fee = pool.functions.getSwapFee().call()
        tokenInIndex = tokens.index(tokenInAddress)
        tokenOutIndex = tokens.index(tokenOutAddress)
        # tokenBalances[tokenInIndex] = tokenBalances[tokenInIndex] - 4700537159732116252
        spotPriceBefore = pool.functions.calcSpotPrice(tokenBalances[tokenInIndex], tokenDenorms[tokenInIndex],
                                                        tokenBalances[tokenOutIndex], tokenDenorms[tokenOutIndex],
                                                        fee).call()
        logger.info("当前pool的价格:{}".format(spotPriceBefore))
        tokenInContract = self.get_contract(tokenInAddress, "./abi/ERC20.json")
        decimal = tokenInContract.functions.decimals().call()
        logger.info("tokenIn的精度为: {}".format(decimal))
        tokenAmountIn = self.calBalance(0.001, decimal)
        # tokenAmountIn = self.w3.toWei("1", "ether")
        # tokenAmountIn = 1000000
        tokenAmountOut = pool.functions.calcOutGivenIn(tokenBalances[tokenInIndex], tokenDenorms[tokenInIndex],
                                                        tokenBalances[tokenOutIndex], tokenDenorms[tokenOutIndex],
                                                        tokenAmountIn, fee).call()

        logger.info("当前pool, 用 {} 的tokenIn可以买到 {} 的tokenOut".format(tokenAmountIn, tokenAmountOut))
        swapFee = bmul(tokenAmountIn, bmul(bdiv(fee, 6), 1))
        logger.info("预计抽取的我们交易费用为: {}".format(swapFee))
        inBalance = tokenBalances[tokenInIndex] + tokenAmountIn - swapFee
        outBalance = tokenBalances[tokenOutIndex] - tokenAmountOut
        spotPriceAfter = pool.functions.calcSpotPrice(inBalance, tokenDenorms[tokenInIndex],
                                                       outBalance, tokenDenorms[tokenOutIndex],
                                                       fee).call()
        logger.info("买入后pool的价格:{}".format(spotPriceAfter))
        limitPrice = bdiv(tokenAmountIn, tokenAmountOut)
        logger.info("购买的限制价格:{}".format(limitPrice))
        if spotPriceBefore > limitPrice:
            logger.info("购买的价格低于池子的价格, 交易应该会失败")

        swaps = [[poolAddress, tokenInAddress, tokenOutAddress, tokenAmountIn, tokenAmountOut,
                 spotPriceAfter]]
        # print('[["{}","{}","{}","{}","{}","{}"]],"{}","{}","{}","{}"'
        #       .format(poolAddress, tokenInAddress, tokenOutAddress, tokenAmountIn, tokenAmountOut, spotPriceAfter,
        #               tokenInAddress, tokenOutAddress, tokenAmountIn, tokenAmountOut))
        swaps = tuple(tuple(e) for e in swaps)
        eProxy_func = self.exchangeProxy.functions.batchSwapExactIn(swaps, tokenInAddress, tokenOutAddress,
                                                                    tokenAmountIn, tokenAmountOut)

        # logger.info("准备通过ExchangeProxy执行 batchSwapExactIn...")
        # self.excuteTransaction(eProxy_func, nonce)

        tokens2, tokenBalances2, tokenDenorms2, poolInTokenBalance2, userBalance2, feeBalance2 = self.getPoolInfo(poolAddress, self.account.address)
        logger.info("交易后, pool记录的token资产:{}".format(tokenBalances2))
        logger.info("交易后, pool实际持有的token资产:{}".format(poolInTokenBalance2))
        logger.info("交易后, 交易账户持有的资产:{}".format(feeBalance2))
        logger.info("交易后, 用户持有的资产:{}".format(userBalance2))
        logger.info("tokenIn资产编号: +{}".format(tokenBalances2[tokenInIndex] - tokenBalances[tokenInIndex]))
        logger.info("tokenOut资产编号: -{}".format(tokenBalances[tokenOutIndex] - tokenBalances2[tokenOutIndex]))

        totalSupply2 = pool.functions.totalSupply().call()
        logger.info("获取当前pool的totalSupply: {}".format(totalSupply2))

        assert totalSupply2 == totalSupply
        # 校验用户资产
        assert userBalance[tokenInIndex] - tokenAmountIn == userBalance2[tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
        assert userBalance[tokenOutIndex] + tokenAmountOut == userBalance2[tokenOutIndex], "用户{}资产扣减不正确".format(tokenOutIndex)
        # 交易池子记录的资产
        assert tokenBalances[tokenInIndex] + tokenAmountIn - swapFee == tokenBalances2[tokenInIndex], "用户{}资产扣减不正确".format(
            tokenInAddress)
        assert tokenBalances[tokenOutIndex] - tokenAmountOut == tokenBalances2[tokenOutIndex], "用户{}资产扣减不正确".format(
            tokenOutIndex)
        # 校验池子实际持有的资产
        assert poolInTokenBalance[tokenInIndex] + tokenAmountIn - swapFee == poolInTokenBalance2[tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
        assert poolInTokenBalance[tokenOutIndex] - tokenAmountOut == poolInTokenBalance2[tokenOutIndex], "用户{}资产扣减不正确".format(tokenOutAddress)
        # 校验收取的交易费用正确
        assert feeBalance[tokenInIndex] + swapFee == feeBalance2[tokenInIndex]
        assert feeBalance[tokenOutIndex] == feeBalance2[tokenOutIndex]

    def checkSwapExactAmountInWithETH(self, pool, poolAddress, tokenInAddress, tokenOutAddress, tokenAmountIn=None, isAddEth=False):
        # swapExactAmountIn
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        tokens, tokenBalances, tokenDenorms, poolInTokenBalance, userBalance, feeBalance = self.getPoolInfo(poolAddress, self.account.address)
        logger.info("获取当前pool记录的token资产: {}".format(tokenBalances))
        logger.info("获取当前pool的denorm: {}".format(tokenDenorms))
        logger.info("获取当前pool实际持有的token资产: {}".format(poolInTokenBalance))
        logger.info("获取交易费用账户的资产: {}".format(feeBalance))
        logger.info("获取用户的资产: {}".format(userBalance))
        useEth = self.w3.eth.getBalance(self.account.address)
        logger.info("用户eth的资产: {}".format(useEth))
        totalSupply = pool.functions.totalSupply().call()
        logger.info("获取当前pool的totalSupply: {}".format(totalSupply))
        fee = pool.functions.getSwapFee().call()
        tokenIn = tokenInAddress
        tokenOut = tokenOutAddress
        tokenInAddress = WETH if tokenInAddress == ETH else tokenInAddress
        tokenOutAddress = WETH if tokenOutAddress == ETH else tokenOutAddress

        tokenInIndex = tokens.index(tokenInAddress)
        tokenOutIndex = tokens.index(tokenOutAddress)
        # tokenBalances[tokenInIndex] = tokenBalances[tokenInIndex] - 4700537159732116252
        spotPriceBefore = pool.functions.calcSpotPrice(tokenBalances[tokenInIndex], tokenDenorms[tokenInIndex],
                                                        tokenBalances[tokenOutIndex], tokenDenorms[tokenOutIndex],
                                                        fee).call()
        logger.info("当前pool的价格:{}".format(spotPriceBefore))
        if tokenAmountIn is None:
            tokenInContract = self.get_contract(tokenInAddress, "./abi/ERC20.json")
            decimal = tokenInContract.functions.decimals().call()
            logger.info("tokenIn的精度为: {}".format(decimal))
            tokenAmountIn = self.calBalance(0.001, decimal)
        # tokenAmountIn = 1000000
        tokenAmountOut = pool.functions.calcOutGivenIn(tokenBalances[tokenInIndex], tokenDenorms[tokenInIndex],
                                                        tokenBalances[tokenOutIndex], tokenDenorms[tokenOutIndex],
                                                        tokenAmountIn, fee).call()

        logger.info("当前pool, 用 {} 的tokenIn可以买到 {} 的tokenOut".format(tokenAmountIn, tokenAmountOut))
        swapFee = bmul(tokenAmountIn, bmul(bdiv(fee, 6), 1))
        logger.info("预计抽取的我们交易费用为: {}".format(swapFee))
        inBalance = tokenBalances[tokenInIndex] + tokenAmountIn - swapFee
        outBalance = tokenBalances[tokenOutIndex] - tokenAmountOut
        spotPriceAfter = pool.functions.calcSpotPrice(inBalance, tokenDenorms[tokenInIndex],
                                                       outBalance, tokenDenorms[tokenOutIndex],
                                                       fee).call()
        logger.info("买入后pool的价格:{}".format(spotPriceAfter))
        limitPrice = bdiv(tokenAmountIn, tokenAmountOut)
        logger.info("购买的限制价格:{}".format(limitPrice))
        if spotPriceBefore > limitPrice:
            logger.info("购买的价格低于池子的价格, 交易应该会失败")
        swaps = [[poolAddress, tokenInAddress, tokenOutAddress, tokenAmountIn, tokenAmountOut,
                 spotPriceAfter]]
        print('[["{}","{}","{}","{}","{}","{}"]],"{}","{}","{}","{}"'
              .format(poolAddress, tokenInAddress, tokenOutAddress, tokenAmountIn, tokenAmountOut, spotPriceAfter,
                      tokenIn, tokenOut, tokenAmountIn, tokenAmountOut))
        # swaps = tuple(tuple(e) for e in swaps)
        eProxy_func = self.exchangeProxy.functions.batchSwapExactIn(swaps, tokenIn, tokenOut,
                                                                    tokenAmountIn, tokenAmountOut)

        logger.info("准备通过ExchangeProxy执行 batchSwapExactIn...")
        addEth = tokenAmountIn if isAddEth else 0
        if tokenIn == ETH:
            tx_hash = self.excuteTransaction(eProxy_func, nonce, value=tokenAmountIn + addEth)
        else:
            tx_hash = self.excuteTransaction(eProxy_func, nonce)
        tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
        tokens2, tokenBalances2, tokenDenorms2, poolInTokenBalance2, userBalance2, feeBalance2 = self.getPoolInfo(poolAddress, self.account.address)

        logger.info("交易后, pool记录的token资产:{}".format(tokenBalances2))
        logger.info("交易后, pool实际持有的token资产:{}".format(poolInTokenBalance2))
        logger.info("交易后, 交易账户持有的资产:{}".format(feeBalance2))
        logger.info("交易后, 用户持有的资产:{}".format(userBalance2))
        logger.info("tokenIn资产编号: +{}".format(tokenBalances2[tokenInIndex] - tokenBalances[tokenInIndex]))
        logger.info("tokenOut资产编号: -{}".format(tokenBalances[tokenOutIndex] - tokenBalances2[tokenOutIndex]))

        useEth2 = self.w3.eth.getBalance(self.account.address)
        logger.info("用户eth的资产: {}".format(useEth2))

        # 校验用户资产
        if tokenIn == ETH:
            assert useEth - tokenAmountIn - self.w3.toWei(tx_info["gasUsed"], "gwei") == useEth2, "用户{}资产扣减不正确".format(tokenInAddress)

            assert userBalance[tokenOutIndex] + tokenAmountOut == userBalance2[tokenOutIndex], "用户{}资产扣减不正确".format(
                tokenOutAddress)
        elif tokenOut == ETH:
            assert userBalance[tokenInIndex] - tokenAmountIn == userBalance2[tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
            assert useEth + tokenAmountOut - self.w3.toWei(tx_info["gasUsed"], "gwei") == useEth2, "用户{}资产扣减不正确".format(tokenOutAddress)

        else:
            assert userBalance[tokenInIndex] - tokenAmountIn == userBalance2[tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
            assert userBalance[tokenOutIndex] + tokenAmountOut == userBalance2[tokenOutIndex], "用户{}资产扣减不正确".format(tokenOutAddress)
        # 交易池子记录的资产
        assert tokenBalances[tokenInIndex] + tokenAmountIn - swapFee == tokenBalances2[tokenInIndex], "用户{}资产扣减不正确".format(
            tokenInAddress)
        assert tokenBalances[tokenOutIndex] - tokenAmountOut == tokenBalances2[tokenOutIndex], "用户{}资产扣减不正确".format(
            tokenOutIndex)
        # 校验池子实际持有的资产
        assert poolInTokenBalance[tokenInIndex] + tokenAmountIn - swapFee == poolInTokenBalance2[tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
        assert poolInTokenBalance[tokenOutIndex] - tokenAmountOut == poolInTokenBalance2[tokenOutIndex], "用户{}资产扣减不正确".format(tokenOutAddress)
        # 校验收取的交易费用正确
        assert feeBalance[tokenInIndex] + swapFee == feeBalance2[tokenInIndex]
        assert feeBalance[tokenOutIndex] == feeBalance2[tokenOutIndex]

    def checkMultihopBatchSwapExactIn(self, poolAddressList, tokenInAddressList, tokenOutAddressList):
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        amountIns = [self.w3.toWei("0.01", "ether")]
        amountOuts = []
        poolTokens = []
        fees = []
        tbalances = []
        userBalances = []
        poolInTokenBalances = []
        feeBalances = []
        multiSwaps = []
        totalSupplys = []

        for index, poolAddress in enumerate(poolAddressList):
            logger.info("开始计算第{}个池子。。。".format(index + 1))
            pool = self.get_contract(self.w3.toChecksumAddress(poolAddress), "./abi/BPool.json")
            tokens, tokenBalances, tokenDenorms, poolInTokenBalance, userBalance, feeBalance = self.getPoolInfo(
                poolAddress, self.account.address
            )
            tbalances.append(tokenBalances)
            poolInTokenBalances.append(poolInTokenBalance)
            userBalances.append(userBalance)
            feeBalances.append(feeBalance)
            poolTokens.append(tokens)
            logger.info("获取当前pool记录的token资产: {}".format(tokenBalances))
            logger.info("获取当前pool的denorm: {}".format(tokenDenorms))
            logger.info("获取当前pool实际持有的token资产: {}".format(poolInTokenBalance))
            logger.info("获取交易费用账户的资产: {}".format(feeBalance))
            logger.info("获取用户的资产: {}".format(userBalance))
            totalSupply = pool.functions.totalSupply().call()
            totalSupplys.append(totalSupply)
            logger.info("获取当前pool的totalSupply: {}".format(totalSupply))
            fee = pool.functions.getSwapFee().call()
            tokenInAddress = tokenInAddressList[index]
            tokenOutAddress = tokenOutAddressList[index]
            tokenInIndex = tokens.index(tokenInAddress)
            tokenOutIndex = tokens.index(tokenOutAddress)
            tokenAmountIn = amountIns[index]
            # tokenBalances[tokenInIndex] = tokenBalances[tokenInIndex] - 4700537159732116252
            spotPriceBefore = pool.functions.calcSpotPrice(tokenBalances[tokenInIndex], tokenDenorms[tokenInIndex],
                                                            tokenBalances[tokenOutIndex], tokenDenorms[tokenOutIndex],
                                                            fee).call()
            logger.info("当前pool的价格:{}".format(spotPriceBefore))
            tokenAmountOut = pool.functions.calcOutGivenIn(tokenBalances[tokenInIndex], tokenDenorms[tokenInIndex],
                                                            tokenBalances[tokenOutIndex], tokenDenorms[tokenOutIndex],
                                                            tokenAmountIn, fee).call()
            amountOuts.append(tokenAmountOut)
            # 当前的tokenOut作为下次的tokenIn
            amountIns.append(tokenAmountOut)

            logger.info("当前pool, 用 {} 的tokenIn可以买到 {} 的tokenOut".format(tokenAmountIn, tokenAmountOut))
            swapFee = bmul(tokenAmountIn, bmul(bdiv(fee, 6), 1))
            fees.append(swapFee)
            inBalance = tokenBalances[tokenInIndex] + tokenAmountIn - swapFee
            outBalance = tokenBalances[tokenOutIndex] - tokenAmountOut
            spotPriceAfter = pool.functions.calcSpotPrice(inBalance, tokenDenorms[tokenInIndex],
                                                           outBalance, tokenDenorms[tokenOutIndex],
                                                           fee).call()
            logger.info("买入后pool的价格:{}".format(spotPriceAfter))
            limitPrice = bdiv(tokenAmountIn, tokenAmountOut)
            logger.info("购买的限制价格:{}".format(limitPrice))
            if spotPriceBefore > limitPrice:
                logger.info("购买的价格低于池子的价格, 交易应该会失败")

            logger.info("预计抽取的我们交易费用为: {}".format(swapFee))
            swaps = [poolAddress, tokenInAddress, tokenOutAddress, tokenAmountIn, tokenAmountOut,
                     spotPriceAfter]
            multiSwaps.append(swaps)
        multiSwaps = [multiSwaps]
        # eProxy_func = self.exchangeProxy.functions.multihopBatchSwapExactIn(multiSwaps, tokenInAddressList[0],
        #                                                                     tokenOutAddressList[-1],
        #                                                                     amountIns[0],
        #                                                                     amountOuts[-1])
        #
        # logger.info("准备通过ExchangeProxy执行 multihopBatchSwapExactIn...")
        # self.excuteTransaction(eProxy_func, nonce)
        for index, poolAddress in enumerate(poolAddressList):
            logger.info("开始校验第{}个池子。。。".format(index + 1))
            pool = self.get_contract(self.w3.toChecksumAddress(poolAddress), "./abi/BPool.json")

            tokens2, tokenBalances2, tokenDenorms2, poolInTokenBalance2, userBalance2, feeBalance2 = self.getPoolInfo(
                poolAddress, self.account.address
            )
            totalSupply2 = pool.functions.totalSupply().call()

            tokenInAddress = tokenInAddressList[index]
            tokenOutAddress = tokenOutAddressList[index]
            tokenInIndex = poolTokens[index].index(tokenInAddress)
            tokenOutIndex = poolTokens[index].index(tokenOutAddress)
            logger.info("交易后, pool记录的token资产:{}".format(tokenBalances2))
            logger.info("交易后, pool实际持有的token资产:{}".format(poolInTokenBalance2))
            logger.info("交易后, 交易账户持有的资产:{}".format(feeBalance2))
            logger.info("交易后, 用户持有的资产:{}".format(userBalance2))
            logger.info("tokenIn资产编号: +{}".format(tokenBalances2[tokenInIndex] - tbalances[index][tokenInIndex]))
            logger.info("tokenOut资产编号: -{}".format(tbalances[index][tokenOutIndex] - tokenBalances2[tokenOutIndex]))

            assert totalSupply2 == totalSupplys[index]

            # 交易池子记录的资产
            assert tbalances[index][tokenInIndex] + amountIns[index] - fees[index] == tokenBalances2[tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
            assert tbalances[index][tokenOutIndex] - amountOuts[index] == tokenBalances2[tokenOutIndex], "用户{}资产扣减不正确".format(tokenOutIndex)
            # 校验池子实际持有的资产
            assert poolInTokenBalances[index][tokenInIndex] + amountIns[index] - fees[index] == poolInTokenBalance2[tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
            assert poolInTokenBalances[index][tokenOutIndex] - amountOuts[index] == poolInTokenBalance2[tokenOutIndex], "用户{}资产扣减不正确".format(tokenOutAddress)

            # 校验收取的交易费用正确
            assert feeBalances[index][tokenInIndex] + fees[index] == feeBalance2[tokenInIndex]
            if index == len(poolAddressList) - 1:
                # 最后tokenOut不收费
                assert feeBalances[index][tokenOutIndex] == feeBalance2[tokenOutIndex]
            else:
                # tokenOut作为下一个的tokenIn,收取的是下一个的费用
                assert feeBalances[index][tokenOutIndex] + fees[index+1] == feeBalance2[tokenOutIndex]
            # 校验用户资产
            if index == 0:
                # 第一组，tokenIn资产减少，tokenOut资产因为作为第2组的tokenin而保持不变
                assert userBalances[index][tokenInIndex] - amountIns[index] == userBalance2[
                        tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
                if len(poolAddressList) == 1:
                    # 如果是只有1个池子，tokenOut有增加
                    assert userBalances[index][tokenOutIndex] + amountOuts[index] == userBalance2[
                        tokenOutIndex], "用户{}资产扣减不正确".format(
                        tokenOutIndex)
                else:
                    assert userBalances[index][tokenOutIndex] == userBalance2[tokenOutIndex], "用户{}资产扣减不正确".format(tokenOutIndex)
            elif index == len(poolAddressList) - 1:
                # 最后一组，tokenIn资产不变，tokenOut资产增加
                assert userBalances[index][tokenInIndex] == userBalance2[
                    tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
                assert userBalances[index][tokenOutIndex] + amountOuts[index] == userBalance2[tokenOutIndex], "用户{}资产扣减不正确".format(
                    tokenOutIndex)
            else:
                # 中间组，保持不变
                assert userBalances[index][tokenInIndex] == userBalance2[
                    tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
                assert userBalances[index][tokenOutIndex] == userBalance2[tokenOutIndex], "用户{}资产扣减不正确".format(
                    tokenOutIndex)

    def checkMultihopBatchSwapExactInWithEth(self, poolAddressList, tokenInAddressList, tokenOutAddressList, tokenIn, tokenOut, amount,isAddEth=False):
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        amountIns = [amount]
        amountOuts = []
        poolTokens = []
        fees = []
        tbalances = []
        userBalances = []
        poolInTokenBalances = []
        feeBalances = []
        multiSwaps = []
        totalSupplys = []

        useEth = self.w3.eth.getBalance(self.account.address)
        for index, poolAddress in enumerate(poolAddressList):
            logger.info("开始计算第{}个池子。。。".format(index + 1))
            pool = self.get_contract(self.w3.toChecksumAddress(poolAddress), "./abi/BPool.json")
            tokens, tokenBalances, tokenDenorms, poolInTokenBalance, userBalance, feeBalance = self.getPoolInfo(
                poolAddress, self.account.address
            )
            tbalances.append(tokenBalances)
            poolInTokenBalances.append(poolInTokenBalance)
            userBalances.append(userBalance)
            feeBalances.append(feeBalance)
            poolTokens.append(tokens)
            logger.info("获取当前pool记录的token资产: {}".format(tokenBalances))
            logger.info("获取当前pool的denorm: {}".format(tokenDenorms))
            logger.info("获取当前pool实际持有的token资产: {}".format(poolInTokenBalance))
            logger.info("获取交易费用账户的资产: {}".format(feeBalance))
            logger.info("获取用户的资产: {}".format(userBalance))
            totalSupply = pool.functions.totalSupply().call()
            totalSupplys.append(totalSupply)
            logger.info("获取当前pool的totalSupply: {}".format(totalSupply))
            fee = pool.functions.getSwapFee().call()
            tokenInAddress = tokenInAddressList[index]
            tokenOutAddress = tokenOutAddressList[index]
            tokenInIndex = tokens.index(tokenInAddress)
            tokenOutIndex = tokens.index(tokenOutAddress)
            tokenAmountIn = amountIns[index]
            # tokenBalances[tokenInIndex] = tokenBalances[tokenInIndex] - 4700537159732116252
            spotPriceBefore = pool.functions.calcSpotPrice(tokenBalances[tokenInIndex], tokenDenorms[tokenInIndex],
                                                            tokenBalances[tokenOutIndex], tokenDenorms[tokenOutIndex],
                                                            fee).call()
            logger.info("当前pool的价格:{}".format(spotPriceBefore))
            tokenAmountOut = pool.functions.calcOutGivenIn(tokenBalances[tokenInIndex], tokenDenorms[tokenInIndex],
                                                            tokenBalances[tokenOutIndex], tokenDenorms[tokenOutIndex],
                                                            tokenAmountIn, fee).call()
            amountOuts.append(tokenAmountOut)
            # 当前的tokenOut作为下次的tokenIn
            amountIns.append(tokenAmountOut)

            logger.info("当前pool, 用 {} 的tokenIn可以买到 {} 的tokenOut".format(tokenAmountIn, tokenAmountOut))
            swapFee = bmul(tokenAmountIn, bmul(bdiv(fee, 6), 1))
            fees.append(swapFee)
            logger.info("预计抽取的我们交易费用为: {}".format(swapFee))

            inBalance = tokenBalances[tokenInIndex] + tokenAmountIn - swapFee
            outBalance = tokenBalances[tokenOutIndex] - tokenAmountOut
            spotPriceAfter = pool.functions.calcSpotPrice(inBalance, tokenDenorms[tokenInIndex],
                                                           outBalance, tokenDenorms[tokenOutIndex],
                                                           fee).call()
            logger.info("买入后pool的价格:{}".format(spotPriceAfter))
            limitPrice = bdiv(tokenAmountIn, tokenAmountOut)
            logger.info("购买的限制价格:{}".format(limitPrice))
            if spotPriceBefore > limitPrice:
                logger.info("购买的价格低于池子的价格, 交易应该会失败")

            swaps = [poolAddress, tokenInAddress, tokenOutAddress, tokenAmountIn, tokenAmountOut,
                     spotPriceAfter]
            multiSwaps.append(swaps)
        multiSwaps = [multiSwaps]
        eProxy_func = self.exchangeProxy.functions.multihopBatchSwapExactIn(
            multiSwaps, tokenIn, tokenOut, amountIns[0], amountOuts[-1]
        )

        addEth = amountIns[0] if isAddEth else 0
        logger.info("准备通过ExchangeProxy执行 multihopBatchSwapExactIn...")
        if tokenIn == ETH:
            tx_hash = self.excuteTransaction(eProxy_func, nonce, value=amountIns[0] + addEth)
        else:
            tx_hash = self.excuteTransaction(eProxy_func, nonce)

        tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
        useEth2 = self.w3.eth.getBalance(self.account.address)
        for index, poolAddress in enumerate(poolAddressList):
            logger.info("开始校验第{}个池子。。。".format(index + 1))
            pool = self.get_contract(self.w3.toChecksumAddress(poolAddress), "./abi/BPool.json")

            tokens2, tokenBalances2, tokenDenorms2, poolInTokenBalance2, userBalance2, feeBalance2 = self.getPoolInfo(
                poolAddress, self.account.address
            )
            totalSupply2 = pool.functions.totalSupply().call()

            tokenInAddress = tokenInAddressList[index]
            tokenOutAddress = tokenOutAddressList[index]
            tokenInIndex = poolTokens[index].index(tokenInAddress)
            tokenOutIndex = poolTokens[index].index(tokenOutAddress)
            logger.info("交易后, pool记录的token资产:{}".format(tokenBalances2))
            logger.info("交易后, pool实际持有的token资产:{}".format(poolInTokenBalance2))
            logger.info("交易后, 交易账户持有的资产:{}".format(feeBalance2))
            logger.info("交易后, 用户持有的资产:{}".format(userBalance2))
            logger.info("tokenIn资产编号: +{}".format(tokenBalances2[tokenInIndex] - tbalances[index][tokenInIndex]))
            logger.info("tokenOut资产编号: -{}".format(tbalances[index][tokenOutIndex] - tokenBalances2[tokenOutIndex]))

            assert totalSupply2 == totalSupplys[index]

            # 交易池子记录的资产
            assert tbalances[index][tokenInIndex] + amountIns[index] - fees[index] == tokenBalances2[tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
            assert tbalances[index][tokenOutIndex] - amountOuts[index] == tokenBalances2[tokenOutIndex], "用户{}资产扣减不正确".format(tokenOutIndex)
            # 校验池子实际持有的资产
            assert poolInTokenBalances[index][tokenInIndex] + amountIns[index] - fees[index] == poolInTokenBalance2[tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
            assert poolInTokenBalances[index][tokenOutIndex] - amountOuts[index] == poolInTokenBalance2[tokenOutIndex], "用户{}资产扣减不正确".format(tokenOutAddress)

            # 校验收取的交易费用正确
            assert feeBalances[index][tokenInIndex] + fees[index] == feeBalance2[tokenInIndex]
            if index == len(poolAddressList) - 1:
                # 最后tokenOut不收费
                assert feeBalances[index][tokenOutIndex] == feeBalance2[tokenOutIndex]
            else:
                # tokenOut作为下一个的tokenIn,收取的是下一个的费用
                assert feeBalances[index][tokenOutIndex] + fees[index+1] == feeBalance2[tokenOutIndex]
            # 校验用户资产
            if index == 0:
                # 第一组，tokenIn资产减少，tokenOut资产因为作为第2组的tokenin而保持不变
                if tokenIn == ETH:
                    assert useEth - amountIns[index] - self.w3.toWei(tx_info["gasUsed"], "gwei") == useEth2
                    if len(poolAddressList) == 1:
                        # 如果是只有1个池子，tokenOut有增加
                        assert userBalances[index][tokenOutIndex] + amountOuts[index] == userBalance2[
                            tokenOutIndex], "用户{}资产扣减不正确".format(
                            tokenOutIndex)
                    else:
                        assert userBalances[index][tokenOutIndex] == userBalance2[tokenOutIndex], "用户{}资产扣减不正确".format(tokenOutIndex)
                elif tokenOut == ETH:
                    assert userBalances[index][tokenInIndex] - amountIns[index] == userBalance2[
                        tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
                    if len(poolAddressList) == 1:
                        assert useEth + amountOuts[index] - self.w3.toWei(tx_info["gasUsed"], "gwei") == useEth2
                    else:
                        assert userBalances[index][tokenOutIndex] == userBalance2[tokenOutIndex], "用户{}资产扣减不正确".format(
                            tokenOutIndex)
                else:
                    assert userBalances[index][tokenInIndex] - amountIns[index] == userBalance2[
                        tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
                    if len(poolAddressList) == 1:
                        # 如果是只有1个池子，tokenOut有增加
                        assert userBalances[index][tokenOutIndex] + amountOuts[index] == userBalance2[
                            tokenOutIndex], "用户{}资产扣减不正确".format(
                            tokenOutIndex)
                    else:
                        assert userBalances[index][tokenOutIndex] == userBalance2[tokenOutIndex], "用户{}资产扣减不正确".format(
                            tokenOutIndex)

            elif index == len(poolAddressList) - 1:
                if tokenOut == ETH:
                    # 最后一组，tokenIn资产不变，tokenOut资产增加
                    assert userBalances[index][tokenInIndex] == userBalance2[
                        tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
                    assert useEth + amountOuts[index] - self.w3.toWei(tx_info["gasUsed"], "gwei") == useEth2, "用户{}资产扣减不正确".format(tokenOut)
                else:
                    # 最后一组，tokenIn资产不变，tokenOut资产增加
                    assert userBalances[index][tokenInIndex] == userBalance2[
                        tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
                    assert userBalances[index][tokenOutIndex] + amountOuts[index] == userBalance2[
                        tokenOutIndex], "用户{}资产扣减不正确".format(
                        tokenOut)
            else:
                # 中间组，保持不变
                assert userBalances[index][tokenInIndex] == userBalance2[
                    tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
                assert userBalances[index][tokenOutIndex] == userBalance2[tokenOutIndex], "用户{}资产扣减不正确".format(
                    tokenOutIndex)

    def checkSwapExactAmountInByPool(self, pool, poolAddress, tokenInAddress, tokenOutAddress):
        # swapExactAmountIn
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        tokens = pool.functions.getCurrentTokens().call()
        logger.info("获取当前pool的tokens:{}".format(tokens))
        tokenBalances, tokenDenorms = [], []
        poolInTokenBalance, userBalance = [], []
        for token in tokens:
            tokenBalances.append(pool.functions.getBalance(token).call())
            tokenDenorms.append(pool.functions.getDenormalizedWeight(token).call())
            poolInTokenBalance.append(self.tokenBalanceOf(token, poolAddress))
            userBalance.append(self.tokenBalanceOf(token, self.account.address))
        logger.info("获取当前pool记录的token资产: {}".format(tokenBalances))
        logger.info("获取当前pool的denorm: {}".format(tokenDenorms))
        logger.info("获取当前pool实际持有的token资产: {}".format(poolInTokenBalance))
        logger.info("获取用户的资产: {}".format(userBalance))
        totalSupply = pool.functions.totalSupply().call()
        logger.info("获取当前pool的totalSupply: {}".format(totalSupply))
        fee = pool.functions.getSwapFee().call()
        tokenInIndex = tokens.index(tokenInAddress)
        tokenOutIndex = tokens.index(tokenOutAddress)
        # tokenBalances[tokenInIndex] = tokenBalances[tokenInIndex] - 4700537159732116252
        spotPriceBefore = pool.functions.calcSpotPrice(
            tokenBalances[tokenInIndex], tokenDenorms[tokenInIndex],
            tokenBalances[tokenOutIndex], tokenDenorms[tokenOutIndex], fee
        ).call()
        logger.info("当前pool的价格:{}".format(spotPriceBefore))
        tokenAmountIn = self.w3.toWei("1", "ether")
        # tokenAmountIn = 4268485809097499203
        tokenAmountOut = pool.functions.calcOutGivenIn(tokenBalances[tokenInIndex], tokenDenorms[tokenInIndex],
                                                       tokenBalances[tokenOutIndex], tokenDenorms[tokenOutIndex],
                                                       tokenAmountIn, fee).call()

        logger.info("当前pool, 用 {} 的tokenIn可以买到 {} 的tokenOut".format(tokenAmountIn, tokenAmountOut))
        inBalance = tokenBalances[tokenInIndex] + tokenAmountIn
        outBalance = tokenBalances[tokenOutIndex] - tokenAmountOut
        spotPriceAfter = pool.functions.calcSpotPrice(inBalance, tokenDenorms[tokenInIndex],
                                                      outBalance, tokenDenorms[tokenOutIndex],
                                                      fee).call()
        logger.info("买入后pool的价格:{}".format(spotPriceAfter))
        swapFee = bmul(tokenAmountIn, bmul(bdiv(fee, 6), 1))
        logger.info("预计抽取的我们交易费用为: {}".format(swapFee))
        # swaps = [[poolAddress, tokenInAddress, tokenOutAddress, tokenAmountIn, tokenAmountOut, spotPriceAfter]]
        swaps = [[poolAddress, tokenInAddress, tokenOutAddress, tokenAmountIn, tokenAmountOut,
                 spotPriceAfter]]
        pool_func = poolContract.functions.swapExactAmountIn(
            self.account.address, tokenInAddress, tokenOutAddress, tokenAmountOut, self.account.address, spotPriceAfter
        )

        logger.info("准备直接执行pool的swapExactAmountIn...")
        self.excuteTransaction(pool_func, nonce, gas=3000000)

        tokenBalances_1 = []
        poolInTokenBalance2, userBalance2 = [], []
        for token in tokens:
            tokenBalances_1.append(pool.functions.getBalance(token).call())
            poolInTokenBalance2.append(self.tokenBalanceOf(token, poolAddress))
            userBalance2.append(self.tokenBalanceOf(token, self.account.address))

        logger.info("交易后, pool记录的token资产:{}".format(tokenBalances_1))
        logger.info("交易后, pool实际持有的token资产:{}".format(poolInTokenBalance2))
        logger.info("交易后, 用户持有的资产:{}".format(userBalance2))
        logger.info("tokenIn资产编号: +{}".format(tokenBalances_1[tokenInIndex] - tokenBalances[tokenInIndex]))
        logger.info("tokenOut资产编号: -{}".format(tokenBalances[tokenOutIndex] - tokenBalances_1[tokenOutIndex]))

    def checkSwapExactAmountOut(self, pool, poolAddress, tokenInAddress, tokenOutAddress):
        # swapExactAmountIn
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        tokens, tokenBalances, tokenDenorms, poolInTokenBalance, userBalance, feeBalance = self.getPoolInfo(poolAddress, self.account.address)
        logger.info("获取当前pool记录的token资产: {}".format(tokenBalances))
        logger.info("获取当前pool的denorm: {}".format(tokenDenorms))
        logger.info("获取当前pool实际持有的token资产: {}".format(poolInTokenBalance))
        logger.info("获取交易费用账户的资产: {}".format(feeBalance))
        logger.info("获取用户的资产: {}".format(userBalance))
        totalSupply = pool.functions.totalSupply().call()
        logger.info("获取当前pool的totalSupply: {}".format(totalSupply))
        fee = pool.functions.getSwapFee().call()
        tokenInIndex = tokens.index(tokenInAddress)
        tokenOutIndex = tokens.index(tokenOutAddress)
        spotPriceBefore = pool.functions.calcSpotPrice(tokenBalances[tokenInIndex], tokenDenorms[tokenInIndex],
                                                        tokenBalances[tokenOutIndex], tokenDenorms[tokenOutIndex],
                                                        fee).call()
        logger.info("当前pool的价格:{}".format(spotPriceBefore))
        tokenOutContract = self.get_contract(tokenOutAddress, "./abi/ERC20.json")
        decimal = tokenOutContract.functions.decimals().call()
        tokenAmountOut = self.calBalance(0.1, decimal)
        # tokenAmountOut = self.calBalance(10, decimal)
        # tokenAmountOut = 1000
        tokenAmountIn = pool.functions.calcInGivenOut(tokenBalances[tokenInIndex], tokenDenorms[tokenInIndex],
                                                       tokenBalances[tokenOutIndex], tokenDenorms[tokenOutIndex],
                                                       tokenAmountOut, fee).call()

        logger.info("当前pool, 想买到 {} 的tokenOut需要用 {} 的tokenIn来买".format(tokenAmountOut, tokenAmountIn))
        swapFee = bmul(tokenAmountIn, bmul(bdiv(fee, 6), 1))
        logger.info("预计抽取的我们交易费用为: {}".format(swapFee))

        inBalance = tokenBalances[tokenInIndex] + tokenAmountIn - swapFee
        outBalance = tokenBalances[tokenOutIndex] - tokenAmountOut
        spotPriceAfter = pool.functions.calcSpotPrice(inBalance, tokenDenorms[tokenInIndex],
                                                       outBalance, tokenDenorms[tokenOutIndex],
                                                       fee).call()
        logger.info("买入后pool的价格:{}".format(spotPriceAfter))

        swaps = [[poolAddress, tokenInAddress, tokenOutAddress, tokenAmountOut, tokenAmountIn, spotPriceAfter]]
        print('[["{}","{}","{}","{}","{}","{}"]],"{}","{}","{}"'
              .format(poolAddress, tokenInAddress, tokenOutAddress, tokenAmountOut, tokenAmountIn, spotPriceAfter,
                      tokenInAddress, tokenOutAddress, tokenAmountIn))
        # print(swaps, tokenInAddress,tokenOutAddress, tokenAmountIn)
        logger.info("args: {},{},{},{}".format(swaps, tokenInAddress, tokenOutAddress, tokenAmountIn))
        eProxy_func = self.exchangeProxy.functions.batchSwapExactOut(swaps, tokenInAddress, tokenOutAddress, tokenAmountIn)
        # logger.info("准备通过ExchangeProxy执行 batchSwapExactOut...")
        # self.excuteTransaction(eProxy_func, nonce)

        tokens2, tokenBalances2, tokenDenorms2, poolInTokenBalance2, userBalance2, feeBalance2 = self.getPoolInfo(poolAddress, self.account.address)

        logger.info("交易后, pool记录的token资产:{}".format(tokenBalances2))
        logger.info("交易后, pool实际持有的token资产:{}".format(poolInTokenBalance2))
        logger.info("交易后, 交易账户持有的资产:{}".format(feeBalance2))
        logger.info("交易后, 用户持有的资产:{}".format(userBalance2))
        logger.info("tokenIn资产编号: +{}".format(tokenBalances2[tokenInIndex] - tokenBalances[tokenInIndex]))
        logger.info("tokenOut资产编号: -{}".format(tokenBalances[tokenOutIndex] - tokenBalances2[tokenOutIndex]))

        # 校验用户资产
        assert userBalance[tokenInIndex] - tokenAmountIn == userBalance2[tokenInIndex], "用户{}资产扣减不正确".format(
            tokenInAddress)
        assert userBalance[tokenOutIndex] + tokenAmountOut == userBalance2[tokenOutIndex], "用户{}资产扣减不正确".format(
            tokenOutIndex)
        # 交易池子记录的资产
        assert tokenBalances[tokenInIndex] + tokenAmountIn - swapFee == tokenBalances2[
            tokenInIndex], "用户{}资产扣减不正确".format(
            tokenInAddress)
        assert tokenBalances[tokenOutIndex] - tokenAmountOut == tokenBalances2[tokenOutIndex], "用户{}资产扣减不正确".format(
            tokenOutIndex)
        # 校验池子实际持有的资产
        assert poolInTokenBalance[tokenInIndex] + tokenAmountIn - swapFee == poolInTokenBalance2[
            tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
        assert poolInTokenBalance[tokenOutIndex] - tokenAmountOut == poolInTokenBalance2[
            tokenOutIndex], "用户{}资产扣减不正确".format(tokenOutAddress)
        # 校验收取的交易费用正确
        assert feeBalance[tokenInIndex] + swapFee == feeBalance2[tokenInIndex]
        assert feeBalance[tokenOutIndex] == feeBalance2[tokenOutIndex]

    def checkSwapExactAmountOutWithETH(self, pool, poolAddress, tokenInAddress, tokenOutAddress, tokenAmountOut=None, isAddEth=False):
        # swapExactAmountIn
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        tokens, tokenBalances, tokenDenorms, poolInTokenBalance, userBalance, feeBalance = self.getPoolInfo(poolAddress, self.account.address)
        logger.info("获取当前pool记录的token资产: {}".format(tokenBalances))
        logger.info("获取当前pool的denorm: {}".format(tokenDenorms))
        logger.info("获取当前pool实际持有的token资产: {}".format(poolInTokenBalance))
        logger.info("获取交易费用账户的资产: {}".format(feeBalance))
        logger.info("获取用户的资产: {}".format(userBalance))
        useEth = self.w3.eth.getBalance(self.account.address)
        logger.info("用户eth的资产: {}".format(useEth))

        totalSupply = pool.functions.totalSupply().call()
        logger.info("获取当前pool的totalSupply: {}".format(totalSupply))
        fee = pool.functions.getSwapFee().call()
        tokenIn = tokenInAddress
        tokenOut = tokenOutAddress
        tokenInAddress = WETH if tokenInAddress == ETH else tokenInAddress
        tokenOutAddress = WETH if tokenOutAddress == ETH else tokenOutAddress
        tokenInIndex = tokens.index(tokenInAddress)
        tokenOutIndex = tokens.index(tokenOutAddress)
        spotPriceBefore = pool.functions.calcSpotPrice(tokenBalances[tokenInIndex], tokenDenorms[tokenInIndex],
                                                        tokenBalances[tokenOutIndex], tokenDenorms[tokenOutIndex],
                                                        fee).call()
        logger.info("当前pool的价格:{}".format(spotPriceBefore))
        if tokenAmountOut is None:
            tokenOutContract = self.get_contract(tokenOutAddress, "./abi/ERC20.json")
            decimal = tokenOutContract.functions.decimals().call()
            tokenAmountOut = self.calBalance(0.001, decimal)
        addEth = tokenAmountOut if isAddEth else 0
        # tokenAmountOut = self.calBalance(10, decimal)
        # tokenAmountOut = 1000
        tokenAmountIn = pool.functions.calcInGivenOut(tokenBalances[tokenInIndex], tokenDenorms[tokenInIndex],
                                                       tokenBalances[tokenOutIndex], tokenDenorms[tokenOutIndex],
                                                       tokenAmountOut, fee).call()

        logger.info("当前pool, 想买到 {} 的tokenOut需要用 {} 的tokenIn来买".format(tokenAmountOut, tokenAmountIn))
        swapFee = bmul(tokenAmountIn, bmul(bdiv(fee, 6), 1))
        logger.info("预计抽取的我们交易费用为: {}".format(swapFee))

        inBalance = tokenBalances[tokenInIndex] + tokenAmountIn - swapFee
        outBalance = tokenBalances[tokenOutIndex] - tokenAmountOut
        spotPriceAfter = pool.functions.calcSpotPrice(inBalance, tokenDenorms[tokenInIndex],
                                                       outBalance, tokenDenorms[tokenOutIndex],
                                                       fee).call()
        logger.info("买入后pool的价格:{}".format(spotPriceAfter))

        swaps = [[poolAddress, tokenInAddress, tokenOutAddress, tokenAmountOut, tokenAmountIn, spotPriceAfter]]
        print('[["{}","{}","{}","{}","{}","{}"]],"{}","{}","{}"'
              .format(poolAddress, tokenInAddress, tokenOutAddress, tokenAmountOut, tokenAmountIn, spotPriceAfter,
                      tokenIn, tokenOut, tokenAmountIn))
        # print(swaps, tokenInAddress,tokenOutAddress, tokenAmountIn)
        logger.info("args: {},{},{},{}".format(swaps, tokenInAddress, tokenOutAddress, tokenAmountIn))
        eProxy_func = self.exchangeProxy.functions.batchSwapExactOut(swaps, tokenIn, tokenOut, tokenAmountIn)
        logger.info("准备通过ExchangeProxy执行 batchSwapExactOut...")
        if tokenIn == ETH:
            tx_hash = self.excuteTransaction(eProxy_func, nonce, value=tokenAmountIn + addEth)
        else:
            tx_hash = self.excuteTransaction(eProxy_func, nonce)

        tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
        tokens2, tokenBalances2, tokenDenorms2, poolInTokenBalance2, userBalance2, feeBalance2 = self.getPoolInfo(poolAddress, self.account.address)

        logger.info("交易后, pool记录的token资产:{}".format(tokenBalances2))
        logger.info("交易后, pool实际持有的token资产:{}".format(poolInTokenBalance2))
        logger.info("交易后, 交易账户持有的资产:{}".format(feeBalance2))
        logger.info("交易后, 用户持有的资产:{}".format(userBalance2))
        logger.info("tokenIn资产编号: +{}".format(tokenBalances2[tokenInIndex] - tokenBalances[tokenInIndex]))
        logger.info("tokenOut资产编号: -{}".format(tokenBalances[tokenOutIndex] - tokenBalances2[tokenOutIndex]))

        useEth2 = self.w3.eth.getBalance(self.account.address)
        logger.info("用户eth的资产: {}".format(useEth2))

        # 校验用户资产
        if tokenIn == ETH:
            assert useEth - tokenAmountIn - self.w3.toWei(tx_info["gasUsed"], "gwei") == useEth2, "用户{}资产扣减不正确".format(
                tokenInAddress)
            assert userBalance[tokenOutIndex] + tokenAmountOut == userBalance2[tokenOutIndex], "用户{}资产扣减不正确".format(
                tokenOutAddress)
        elif tokenOut == ETH:
            assert userBalance[tokenInIndex] - tokenAmountIn == userBalance2[tokenInIndex], "用户{}资产扣减不正确".format(
                tokenInAddress)
            assert useEth + tokenAmountOut - self.w3.toWei(tx_info["gasUsed"], "gwei") == useEth2, "用户{}资产扣减不正确".format(
                tokenOutAddress)
        else:
            assert userBalance[tokenInIndex] - tokenAmountIn == userBalance2[tokenInIndex], "用户{}资产扣减不正确".format(
                tokenInAddress)
            assert userBalance[tokenOutIndex] + tokenAmountOut == userBalance2[tokenOutIndex], "用户{}资产扣减不正确".format(
                tokenOutAddress)
        # 交易池子记录的资产
        assert tokenBalances[tokenInIndex] + tokenAmountIn - swapFee == tokenBalances2[
            tokenInIndex], "用户{}资产扣减不正确".format(
            tokenInAddress)
        assert tokenBalances[tokenOutIndex] - tokenAmountOut == tokenBalances2[tokenOutIndex], "用户{}资产扣减不正确".format(
            tokenOutIndex)
        # 校验池子实际持有的资产
        assert poolInTokenBalance[tokenInIndex] + tokenAmountIn - swapFee == poolInTokenBalance2[
            tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
        assert poolInTokenBalance[tokenOutIndex] - tokenAmountOut == poolInTokenBalance2[
            tokenOutIndex], "用户{}资产扣减不正确".format(tokenOutAddress)
        # 校验收取的交易费用正确
        assert feeBalance[tokenInIndex] + swapFee == feeBalance2[tokenInIndex]
        assert feeBalance[tokenOutIndex] == feeBalance2[tokenOutIndex]

    def checkMultihopBatchSwapExactOut(self, poolAddressList, tokenInAddressList, tokenOutAddressList):
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        tokenOutContract = self.get_contract(tokenOutAddressList[-1], "./abi/ERC20.json")
        decimal = tokenOutContract.functions.decimals().call()
        amountIns = []
        amountOuts = [self.calBalance(0.001, decimal)]
        poolTokens = []
        fees = []
        tbalances = []
        userBalances = []
        poolInTokenBalances = []
        feeBalances = []
        multiSwaps = []
        supplys = []

        for index in range(len(poolAddressList) - 1, -1, -1):
            poolAddress = poolAddressList[index]
            logger.info("开始计算第{}个池子。。。".format(index + 1))
            pool = self.get_contract(self.w3.toChecksumAddress(poolAddress), "./abi/BPool.json")
            tokens, tokenBalances, tokenDenorms, poolInTokenBalance, userBalance, feeBalance = self.getPoolInfo(
                poolAddress, self.account.address
            )
            tbalances.insert(0, tokenBalances)
            poolInTokenBalances.insert(0, poolInTokenBalance)
            userBalances.insert(0, userBalance)
            feeBalances.insert(0, feeBalance)
            poolTokens.insert(0, tokens)
            logger.info("获取当前pool记录的token资产: {}".format(tokenBalances))
            logger.info("获取当前pool的denorm: {}".format(tokenDenorms))
            logger.info("获取当前pool实际持有的token资产: {}".format(poolInTokenBalance))
            logger.info("获取交易费用账户的资产: {}".format(feeBalance))
            logger.info("获取用户的资产: {}".format(userBalance))
            totalSupply = pool.functions.totalSupply().call()
            supplys.insert(0, totalSupply)
            logger.info("获取当前pool的totalSupply: {}".format(totalSupply))
            fee = pool.functions.getSwapFee().call()
            tokenInAddress = tokenInAddressList[index]
            tokenOutAddress = tokenOutAddressList[index]
            tokenInIndex = tokens.index(tokenInAddress)
            tokenOutIndex = tokens.index(tokenOutAddress)

            tokenAmountOut = amountOuts[0]
            # tokenOutContract = self.get_contract(tokenOutAddress, "./abi/ERC20.json")
            # decimal = tokenOutContract.functions.decimals().call()
            # tokenBalances[tokenInIndex] = tokenBalances[tokenInIndex] - 4700537159732116252
            spotPriceBefore = pool.functions.calcSpotPrice(tokenBalances[tokenInIndex], tokenDenorms[tokenInIndex],
                                                           tokenBalances[tokenOutIndex], tokenDenorms[tokenOutIndex],
                                                           fee).call()
            logger.info("当前pool的价格:{}".format(spotPriceBefore))
            tokenAmountIn = pool.functions.calcInGivenOut(tokenBalances[tokenInIndex], tokenDenorms[tokenInIndex],
                                                          tokenBalances[tokenOutIndex], tokenDenorms[tokenOutIndex],
                                                          tokenAmountOut, fee).call()
            amountIns.insert(0, tokenAmountIn)
            if index > 0:
                amountOuts.insert(0, tokenAmountIn)

            logger.info("当前pool, 用 {} 的tokenIn可以买到 {} 的tokenOut".format(tokenAmountIn, tokenAmountOut))
            swapFee = bmul(tokenAmountIn, bmul(bdiv(fee, 6), 1))
            fees.insert(0, swapFee)
            logger.info("预计抽取的我们交易费用为: {}".format(swapFee))

            inBalance = tokenBalances[tokenInIndex] + tokenAmountIn - swapFee
            outBalance = tokenBalances[tokenOutIndex] - tokenAmountOut
            spotPriceAfter = pool.functions.calcSpotPrice(inBalance, tokenDenorms[tokenInIndex],
                                                          outBalance, tokenDenorms[tokenOutIndex],
                                                          fee).call()
            logger.info("买入后pool的价格:{}".format(spotPriceAfter))
            limitPrice = bdiv(tokenAmountIn, tokenAmountOut)
            logger.info("购买的限制价格:{}".format(limitPrice))
            if spotPriceBefore > limitPrice:
                logger.info("购买的价格低于池子的价格, 交易应该会失败")

            swaps = [poolAddress, tokenInAddress, tokenOutAddress, tokenAmountOut, tokenAmountIn,
                     spotPriceAfter]
            multiSwaps.insert(0, swaps)
            # print(multiSwaps)
            # multiSwaps.append(swaps)
        multiSwaps = [multiSwaps]
        eProxy_func = self.exchangeProxy.functions.multihopBatchSwapExactOut(multiSwaps, tokenInAddressList[0],
                                                                            tokenOutAddressList[-1],
                                                                            amountIns[0])

        logger.info("准备通过ExchangeProxy执行 multihopBatchSwapExactOut...")
        # self.excuteTransaction(eProxy_func, nonce)
        for index, poolAddress in enumerate(poolAddressList):
            logger.info("开始校验第{}个池子。。。".format(index + 1))
            pool = self.get_contract(self.w3.toChecksumAddress(poolAddress), "./abi/BPool.json")

            tokens2, tokenBalances2, tokenDenorms2, poolInTokenBalance2, userBalance2, feeBalance2 = self.getPoolInfo(
                poolAddress, self.account.address
            )

            lp = pool.functions.totalSupply().call()

            assert lp == supplys[index]
            tokenInAddress = tokenInAddressList[index]
            tokenOutAddress = tokenOutAddressList[index]
            tokenInIndex = poolTokens[index].index(tokenInAddress)
            tokenOutIndex = poolTokens[index].index(tokenOutAddress)
            logger.info("交易后, pool记录的token资产:{}".format(tokenBalances2))
            logger.info("交易后, pool实际持有的token资产:{}".format(poolInTokenBalance2))
            logger.info("交易后, 交易账户持有的资产:{}".format(feeBalance2))
            logger.info("交易后, 用户持有的资产:{}".format(userBalance2))
            logger.info("tokenIn资产编号: +{}".format(tokenBalances2[tokenInIndex] - tbalances[index][tokenInIndex]))
            logger.info("tokenOut资产编号: -{}".format(tbalances[index][tokenOutIndex] - tokenBalances2[tokenOutIndex]))

            # 交易池子记录的资产
            assert tbalances[index][tokenInIndex] + amountIns[index] - fees[index] == tokenBalances2[tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
            assert tbalances[index][tokenOutIndex] - amountOuts[index] == tokenBalances2[tokenOutIndex], "用户{}资产扣减不正确".format(tokenOutIndex)
            # 校验池子实际持有的资产
            assert poolInTokenBalances[index][tokenInIndex] + amountIns[index] - fees[index] == poolInTokenBalance2[tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
            assert poolInTokenBalances[index][tokenOutIndex] - amountOuts[index] == poolInTokenBalance2[tokenOutIndex], "用户{}资产扣减不正确".format(tokenOutAddress)

            # 校验收取的交易费用正确
            assert feeBalances[index][tokenInIndex] + fees[index] == feeBalance2[tokenInIndex]
            if index == len(poolAddressList) - 1:
                # 最后tokenOut不收费
                assert feeBalances[index][tokenOutIndex] == feeBalance2[tokenOutIndex]
            else:
                # tokenOut作为下一个的tokenIn,收取的是下一个的费用
                assert feeBalances[index][tokenOutIndex] + fees[index+1] == feeBalance2[tokenOutIndex]

            # 校验用户资产,只有1种挂池子组合的情形
            if index == 0:
                # 第一组，tokenIn资产减少，tokenOut资产因为作为第2组的tokenin而保持不变
                assert userBalances[index][tokenInIndex] - amountIns[index] == userBalance2[
                        tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
                if len(poolAddressList) == 1:
                    # 只有1个池子, tokenOut有增加
                    assert userBalances[index][tokenOutIndex] + amountOuts[index] == userBalance2[tokenOutIndex]
                else:
                    assert userBalances[index][tokenOutIndex] == userBalance2[tokenOutIndex], "用户{}资产扣减不正确".format(tokenOutIndex)
            elif index == len(poolAddressList) - 1:
                # 最后一组，tokenIn资产不变，tokenOut资产增加
                assert userBalances[index][tokenInIndex] == userBalance2[
                    tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
                assert userBalances[index][tokenOutIndex] + amountOuts[index] == userBalance2[tokenOutIndex], "用户{}资产扣减不正确".format(
                    tokenOutIndex)
            else:
                # 中间组，保持不变
                assert userBalances[index][tokenInIndex] == userBalance2[
                    tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
                assert userBalances[index][tokenOutIndex] == userBalance2[tokenOutIndex], "用户{}资产扣减不正确".format(
                    tokenOutIndex)

    def checkMultihopBatchSwapExactOutWithEth(self, poolAddressList, tokenInAddressList, tokenOutAddressList, tokenIn, tokenOut, amount, isaddEth=False):
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        amountIns = []
        amountOuts = [amount]
        poolTokens = []
        fees = []
        tbalances = []
        userBalances = []
        poolInTokenBalances = []
        feeBalances = []
        multiSwaps = []
        supplys = []
        userEth = self.w3.eth.getBalance(self.account.address)
        logger.info("用户持有的eth:{}".format(userEth))
        for index in range(len(poolAddressList) - 1, -1, -1):
            poolAddress = poolAddressList[index]
            logger.info("开始计算第{}个池子。。。".format(index + 1))
            pool = self.get_contract(self.w3.toChecksumAddress(poolAddress), "./abi/BPool.json")
            tokens, tokenBalances, tokenDenorms, poolInTokenBalance, userBalance, feeBalance = self.getPoolInfo(
                poolAddress, self.account.address
            )
            tbalances.insert(0, tokenBalances)
            poolInTokenBalances.insert(0, poolInTokenBalance)
            userBalances.insert(0, userBalance)
            feeBalances.insert(0, feeBalance)
            poolTokens.insert(0, tokens)
            logger.info("获取当前pool记录的token资产: {}".format(tokenBalances))
            logger.info("获取当前pool的denorm: {}".format(tokenDenorms))
            logger.info("获取当前pool实际持有的token资产: {}".format(poolInTokenBalance))
            logger.info("获取交易费用账户的资产: {}".format(feeBalance))
            logger.info("获取用户的资产: {}".format(userBalance))
            totalSupply = pool.functions.totalSupply().call()
            supplys.insert(0, totalSupply)
            logger.info("获取当前pool的totalSupply: {}".format(totalSupply))
            fee = pool.functions.getSwapFee().call()
            tokenInAddress = tokenInAddressList[index]
            tokenOutAddress = tokenOutAddressList[index]
            tokenInIndex = tokens.index(tokenInAddress)
            tokenOutIndex = tokens.index(tokenOutAddress)

            tokenAmountOut = amountOuts[0]
            # tokenOutContract = self.get_contract(tokenOutAddress, "./abi/ERC20.json")
            # decimal = tokenOutContract.functions.decimals().call()
            # tokenBalances[tokenInIndex] = tokenBalances[tokenInIndex] - 4700537159732116252
            spotPriceBefore = pool.functions.calcSpotPrice(tokenBalances[tokenInIndex], tokenDenorms[tokenInIndex],
                                                            tokenBalances[tokenOutIndex], tokenDenorms[tokenOutIndex],
                                                            fee).call()
            logger.info("当前pool的价格:{}".format(spotPriceBefore))
            tokenAmountIn = pool.functions.calcInGivenOut(tokenBalances[tokenInIndex], tokenDenorms[tokenInIndex],
                                                            tokenBalances[tokenOutIndex], tokenDenorms[tokenOutIndex],
                                                            tokenAmountOut, fee).call()
            amountIns.insert(0, tokenAmountIn)
            if index > 0:
                amountOuts.insert(0, tokenAmountIn)

            logger.info("当前pool, 用 {} 的tokenIn可以买到 {} 的tokenOut".format(tokenAmountIn, tokenAmountOut))

            swapFee = bmul(tokenAmountIn, bmul(bdiv(fee, 6), 1))
            fees.insert(0, swapFee)
            logger.info("预计抽取的我们交易费用为: {}".format(swapFee))

            inBalance = tokenBalances[tokenInIndex] + tokenAmountIn - swapFee
            outBalance = tokenBalances[tokenOutIndex] - tokenAmountOut
            spotPriceAfter = pool.functions.calcSpotPrice(inBalance, tokenDenorms[tokenInIndex],
                                                           outBalance, tokenDenorms[tokenOutIndex],
                                                           fee).call()
            logger.info("买入后pool的价格:{}".format(spotPriceAfter))
            limitPrice = bdiv(tokenAmountIn, tokenAmountOut)
            logger.info("购买的限制价格:{}".format(limitPrice))
            if spotPriceBefore > limitPrice:
                logger.info("购买的价格低于池子的价格, 交易应该会失败")

            swaps = [poolAddress, tokenInAddress, tokenOutAddress, tokenAmountOut, tokenAmountIn,
                     spotPriceAfter]
            multiSwaps.insert(0, swaps)
            # print(multiSwaps)
            # multiSwaps.append(swaps)
        multiSwaps = [multiSwaps]
        eProxy_func = self.exchangeProxy.functions.multihopBatchSwapExactOut(multiSwaps, tokenIn,
                                                                            tokenOut,
                                                                            amountIns[0])

        logger.info("准备通过ExchangeProxy执行 multihopBatchSwapExactOut...")
        addEth = amountIns[0] if isaddEth else 0
        if tokenIn == ETH:
            tx_hash = self.excuteTransaction(eProxy_func, nonce, value=amountIns[0] + addEth)
        else:
            tx_hash = self.excuteTransaction(eProxy_func, nonce)

        tx_info = self.w3.eth.getTransactionReceipt(tx_hash)

        user2Eth = self.w3.eth.getBalance(self.account.address)
        logger.info("用户持有的eth:{}".format(user2Eth))

        for index, poolAddress in enumerate(poolAddressList):
            logger.info("开始校验第{}个池子。。。".format(index + 1))
            pool = self.get_contract(self.w3.toChecksumAddress(poolAddress), "./abi/BPool.json")

            tokens2, tokenBalances2, tokenDenorms2, poolInTokenBalance2, userBalance2, feeBalance2 = self.getPoolInfo(
                poolAddress, self.account.address
            )

            lp = pool.functions.totalSupply().call()

            assert lp == supplys[index]
            tokenInAddress = tokenInAddressList[index]
            tokenOutAddress = tokenOutAddressList[index]
            tokenInIndex = poolTokens[index].index(tokenInAddress)
            tokenOutIndex = poolTokens[index].index(tokenOutAddress)
            logger.info("交易后, pool记录的token资产:{}".format(tokenBalances2))
            logger.info("交易后, pool实际持有的token资产:{}".format(poolInTokenBalance2))
            logger.info("交易后, 交易账户持有的资产:{}".format(feeBalance2))
            logger.info("交易后, 用户持有的资产:{}".format(userBalance2))
            logger.info("tokenIn资产编号: +{}".format(tokenBalances2[tokenInIndex] - tbalances[index][tokenInIndex]))
            logger.info("tokenOut资产编号: -{}".format(tbalances[index][tokenOutIndex] - tokenBalances2[tokenOutIndex]))

            # 交易池子记录的资产
            assert tbalances[index][tokenInIndex] + amountIns[index] - fees[index] == tokenBalances2[tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
            assert tbalances[index][tokenOutIndex] - amountOuts[index] == tokenBalances2[tokenOutIndex], "用户{}资产扣减不正确".format(tokenOutIndex)
            # 校验池子实际持有的资产
            assert poolInTokenBalances[index][tokenInIndex] + amountIns[index] - fees[index] == poolInTokenBalance2[tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
            assert poolInTokenBalances[index][tokenOutIndex] - amountOuts[index] == poolInTokenBalance2[tokenOutIndex], "用户{}资产扣减不正确".format(tokenOutAddress)

            # 校验收取的交易费用正确
            assert feeBalances[index][tokenInIndex] + fees[index] == feeBalance2[tokenInIndex]
            if index == len(poolAddressList) - 1:
                # 最后tokenOut不收费
                assert feeBalances[index][tokenOutIndex] == feeBalance2[tokenOutIndex]
            else:
                # tokenOut作为下一个的tokenIn,收取的是下一个的费用
                assert feeBalances[index][tokenOutIndex] + fees[index+1] == feeBalance2[tokenOutIndex]

            # 校验用户资产,只有1种挂池子组合的情形
            if index == 0:
                # 第一组，tokenIn资产减少，tokenOut资产因为作为第2组的tokenin而保持不变
                if tokenIn == ETH:
                    assert userEth - amountIns[index] - self.w3.toWei(tx_info["gasUsed"], "gwei") == user2Eth
                else:
                    assert userBalances[index][tokenInIndex] - amountIns[index] == userBalance2[
                            tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
                if len(poolAddressList) == 1:
                    # 只有1个池子, tokenOut有增加
                    if tokenOut == ETH:
                        assert userEth + amountOuts[index] - self.w3.toWei(tx_info["gasUsed"], "gwei") == user2Eth
                    else:
                        assert userBalances[index][tokenOutIndex] + amountOuts[index] == userBalance2[tokenOutIndex]
                else:
                    assert userBalances[index][tokenOutIndex] == userBalance2[tokenOutIndex], "用户{}资产扣减不正确".format(tokenOutIndex)
            elif index == len(poolAddressList) - 1:
                # 最后一组，tokenIn资产不变，tokenOut资产增加
                assert userBalances[index][tokenInIndex] == userBalance2[
                    tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
                if tokenOut == ETH:
                    assert userEth + amountOuts[index] - self.w3.toWei(tx_info["gasUsed"], "gwei") == user2Eth
                else:
                    assert userBalances[index][tokenOutIndex] + amountOuts[index] == userBalance2[tokenOutIndex]
            else:
                # 中间组，保持不变
                assert userBalances[index][tokenInIndex] == userBalance2[
                    tokenInIndex], "用户{}资产扣减不正确".format(tokenInAddress)
                assert userBalances[index][tokenOutIndex] == userBalance2[tokenOutIndex], "用户{}资产扣减不正确".format(
                    tokenOutIndex)

    def checkExitPool(self, pool, poolAddress, isExitAll=False):
        # exitPool
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        tokens = pool.functions.getCurrentTokens().call()
        logger.info("获取当前pool的tokens:{}".format(tokens))
        tokenBalances = []
        poolInTokenBalance = []
        userBalance = []
        for token in tokens:
            tokenBalances.append(pool.functions.getBalance(token).call())
            poolInTokenBalance.append(self.tokenBalanceOf(token, poolAddress))
            userBalance.append(self.tokenBalanceOf(token, self.account.address))
        logger.info("获取当前pool记录的token balance: {}".format(tokenBalances))
        logger.info("获取当前pool在token中实际持有的balance: {}".format(poolInTokenBalance))
        totalSupply = pool.functions.totalSupply().call()
        logger.info("获取当前pool的totalSupply: {}".format(totalSupply))
        logger.info("用户持有的资产: {}".format(userBalance))

        exitAmount = pool.functions.balanceOf(self.account.address).call() if isExitAll else self.w3.toWei("1.123456789012345678", "ether")
        exitFee = bmul(exitAmount, 0)
        pAiAfterExitFee = bsub(exitAmount, exitFee)
        ratio = bdiv(pAiAfterExitFee, totalSupply)
        logger.info("退出池子的系数为:{}".format(ratio))
        amountOut = []
        for i in range(len(tokens)):
            amountOut.append(bmul(ratio, tokenBalances[i]))
        logger.info("提取 {} 的lp，预计可以领取: {}".format(exitAmount, amountOut))
        e_func = pool.functions.exitPool(exitAmount, amountOut)
        logger.info("准备执行BPool的 exitPool...")
        tx_hash = self.excuteTransaction(e_func, nonce)

        afterBalances = []
        poolInTokenBalance2 = []
        userBalance2 = []
        for token in tokens:
            afterBalances.append(pool.functions.getBalance(token).call())
            poolInTokenBalance2.append(self.tokenBalanceOf(token, poolAddress))
            userBalance2.append(self.tokenBalanceOf(token, self.account.address))

        logger.info("交易前资产: {}".format(tokenBalances))
        logger.info("交易后资产: {}".format(afterBalances))
        logger.info("交易后pool实际持有资产: {}".format(poolInTokenBalance2))
        logger.info("交易后用户持有资产: {}".format(userBalance2))

        changesBalance = []
        for i in range(2):
            tmp = tokenBalances[i] - afterBalances[i]
            ptBalance = poolInTokenBalance[i] - poolInTokenBalance2[i]
            assert tmp == amountOut[i], "{}和{}资产变化不一致".format(tmp, amountOut[i])
            assert tmp == ptBalance, "pool中记录资产和实际持有资产的变化不一致: {} {}".format(tmp, ptBalance)
            assert tmp == userBalance2[i] - userBalance[i], "用户资产变化不一致: {} {}".format(tmp, userBalance[i] - userBalance2[i])
            assert afterBalances[i] == poolInTokenBalance2[i], "pool中记录资产和实际持有资产不一致: {} {}".format(afterBalances[i],
                                                                                                   ptBalance)
            changesBalance.append(tmp)

        logger.info("资产变化: {}".format(changesBalance))
        afterSupply = pool.functions.totalSupply().call()
        assert totalSupply - exitAmount == afterSupply, "交易前 {}, 交易后{},变化:{}".format(totalSupply, afterSupply,
                                                                                       exitAmount)
        return tx_hash

    def checkExitSwapPoolAmountIn(self, pool, tokenOut, isExitAll=False):
        # exitSwapPoolAmountIn
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        # tokens = pool.functions.getCurrentTokens().call()
        # logger.info("获取当前pool的tokens:{}".format(tokens))
        outBalance = pool.functions.getBalance(tokenOut).call()
        logger.info("获取当前pool的balance: {}".format(outBalance))
        outDenorm = pool.functions.getDenormalizedWeight(tokenOut).call()
        logger.info("获取当前pool的balance: {}".format(outDenorm))
        totalSupply = pool.functions.totalSupply().call()
        logger.info("获取当前pool的totalSupply: {}".format(totalSupply))
        totalWeight = pool.functions.getTotalDenormalizedWeight().call()
        logger.info("获取当前pool的totalWeight: {}".format(totalWeight))
        fee = pool.functions.getSwapFee().call()
        if isExitAll:
            exitAmount = pool.functions.balanceOf(self.account.address).call()
        else:
            exitAmount = self.w3.toWei("0.01", "ether")
        # outBalance = 29054517471252259865
        # outDenorm = 1000000000000000000
        # totalSupply = 545553052126845541190
        # totalWeight = 2000000000000000000
        # exitAmount = 1000000000000000000
        # fee = 3000000000000000
        # logger.info(outBalance)
        # logger.info(outDenorm)
        # logger.info(totalSupply)
        # logger.info(totalWeight)
        # logger.info(exitAmount)
        # logger.info(fee)

        tokenAmountOut = pool.functions.calcSingleOutGivenPoolIn(outBalance, outDenorm, totalSupply, totalWeight,
                                                                  exitAmount, fee).call()
        logger.info("提取 {} 的lp，预计可以领取tokenOut: {}".format(exitAmount, tokenAmountOut))
        e_func = pool.functions.exitswapPoolAmountIn(tokenOut, exitAmount, tokenAmountOut)
        logger.info("准备执行BPool的 exitswapPoolAmountIn...")
        self.excuteTransaction(e_func, nonce)

    def checkGetAmountsInWhenSwapExactAmountOut(self, pool, poolAddress, tokenInAddress, tokenOutAddress):
        # checkGetAmountsInWhenSwapExactAmountOut
        tokens, tokenBalances, tokenDenorms, poolInTokenBalance, userBalance, feeBalance = self.getPoolInfo(poolAddress, self.account.address)
        logger.info("获取当前pool记录的token资产: {}".format(tokenBalances))
        logger.info("获取当前pool的denorm: {}".format(tokenDenorms))
        logger.info("获取当前pool实际持有的token资产: {}".format(poolInTokenBalance))
        logger.info("获取交易费用账户的资产: {}".format(feeBalance))
        logger.info("获取用户的资产: {}".format(userBalance))
        totalSupply = pool.functions.totalSupply().call()
        logger.info("获取当前pool的totalSupply: {}".format(totalSupply))
        fee = pool.functions.getSwapFee().call()
        tokenInIndex = tokens.index(tokenInAddress)
        tokenOutIndex = tokens.index(tokenOutAddress)
        spotPriceBefore = pool.functions.calcSpotPrice(tokenBalances[tokenInIndex], tokenDenorms[tokenInIndex],
                                                        tokenBalances[tokenOutIndex], tokenDenorms[tokenOutIndex],
                                                        fee).call()
        logger.info("当前pool的价格:{}".format(spotPriceBefore))
        tokenOutContract = self.get_contract(tokenOutAddress, "./abi/ERC20.json")
        decimal = tokenOutContract.functions.decimals().call()
        tokenAmountOut = self.calBalance(0.001, decimal)
        # tokenAmountOut = self.calBalance(10, decimal)
        # tokenAmountOut = 1000
        tokenAmountIn = pool.functions.calcInGivenOut(tokenBalances[tokenInIndex], tokenDenorms[tokenInIndex],
                                                       tokenBalances[tokenOutIndex], tokenDenorms[tokenOutIndex],
                                                       tokenAmountOut, fee).call()

        logger.info("当前pool, 想买到 {} 的tokenOut需要用 {} 的tokenIn来买".format(tokenAmountOut, tokenAmountIn))
        swapFee = bmul(tokenAmountIn, bmul(bdiv(fee, 6), 1))
        logger.info("预计抽取的我们交易费用为: {}".format(swapFee))
        inBalance = tokenBalances[tokenInIndex] + tokenAmountIn - swapFee
        outBalance = tokenBalances[tokenOutIndex] - tokenAmountOut
        spotPriceAfter = pool.functions.calcSpotPrice(inBalance, tokenDenorms[tokenInIndex],
                                                       outBalance, tokenDenorms[tokenOutIndex],
                                                       fee).call()
        logger.info("买入后pool的价格:{}".format(spotPriceAfter))

        swaps = [[poolAddress, tokenInAddress, tokenOutAddress, tokenAmountOut, tokenAmountIn, spotPriceAfter]]
        # print('[["{}","{}","{}","{}","{}","{}"]],"{}","{}","{}"'
        #       .format(poolAddress, tokenInAddress, tokenOutAddress, tokenAmountOut, tokenAmountIn, spotPriceAfter,
        #               tokenInAddress, tokenOutAddress, tokenAmountIn))
        # print(swaps, tokenInAddress,tokenOutAddress, tokenAmountIn)
        # logger.info("args: {},{},{},{}".format(swaps, tokenInAddress, tokenOutAddress, tokenAmountIn))
        logger.info("准备通过ExchangeProxy执行 getAmountIn...")
        cal_amount = self.exchangeProxy.functions.getAmountIn(swaps[0]).call()
        cal_price = pool.functions.calcPoolSpotPrice(tokenInAddress, tokenOutAddress, 0, 0).call()
        cal_price_after = pool.functions.calcPoolSpotPrice(tokenInAddress, tokenOutAddress, tokenAmountIn, tokenAmountOut).call()
        logger.info("获取的amount: {}".format(cal_amount))
        logger.info("获取的calcPoolSpotPrice: {}".format(cal_price))
        logger.info("获取待费用的calcPoolSpotPrice: {}".format(cal_price_after))
        assert cal_amount == tokenAmountIn, "计算的tokenAmountIn不正确"
        assert cal_price == spotPriceBefore, "计算的spotPrice不正确"
        assert cal_price_after == spotPriceAfter, "计算的spotPrice不正确"

    def checkBindPair(self, pool, poolAddress):
        # checkGetAmountsInWhenSwapExactAmountOut
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        tokens, tokenBalances, tokenDenorms, poolInTokenBalance, userBalance, feeBalance = self.getPoolInfo(poolAddress, self.account.address)
        logger.info("获取当前pool记录的token资产: {}".format(tokenBalances))
        logger.info("获取当前pool的denorm: {}".format(tokenDenorms))
        logger.info("获取当前pool实际持有的token资产: {}".format(poolInTokenBalance))
        logger.info("获取交易费用账户的资产: {}".format(feeBalance))
        logger.info("获取用户的资产: {}".format(userBalance))
        totalSupply = pool.functions.totalSupply().call()
        logger.info("获取当前pool的totalSupply: {}".format(totalSupply))
        fee = pool.functions.getSwapFee().call()
        logger.info("准备执行pool的 bindPair...")
        # cal_amount = self.exchangeProxy.functions.getAmountIn(swaps[0]).call()
        logger.info('args: "{}", {}, {}, {}'.format(PairFactory, GP_addr, GP_allocPoint, GP_rate))
        exc_func = pool.functions.bindPair(PairFactory, GP_addr, GP_allocPoint, GP_rate)
        tx_hash = self.excuteTransaction(exc_func, nonce)
        # logger.info("获取的amount: {}".format(cal_amount))
        # logger.info("获取的calcPoolSpotPrice: {}".format(cal_price))
        # assert cal_amount == tokenAmountIn, "计算的tokenAmountIn不正确"
        # assert cal_price == spotPriceAfter, "计算的tokenAmountIn不正确"

    def getLPMingInfo(self, lpMining, poolAddress, pid):

        shareInfo = lpMining.functions.shareInfo().call()
        poolInfo = lpMining.functions.poolInfo(poolAddress).call()
        userInfo = lpMining.functions.userInfo(pid, self.account.address).call()
        # 为方便理解，转换下数据格式
        shareInfo = dict(tvl=shareInfo[0], accPoolPerShare=shareInfo[1], lastRewardBlock=shareInfo[2])
        poolInfo = dict(bPool=poolInfo[0], poolIndex=poolInfo[1], referIndex=poolInfo[2], allocPoint=poolInfo[3],
                        lastTvl=poolInfo[4], accTokenPerShare=poolInfo[5], rewardDebt=poolInfo[6])
        userInfo = dict(rewardDebt=userInfo)
        logger.info("shareInfo: {}".format(shareInfo))
        logger.info("poolInfo: {}".format(poolInfo))
        logger.info("userInfo: {}".format(userInfo))
        return shareInfo, poolInfo, userInfo

    @staticmethod
    def getMultiplierBlock(lpMining, fromBlock, toBlock):
        endTripleBlock = lpMining.functions.endTripleBlock().call()

        if fromBlock < toBlock:
            if fromBlock >= endTripleBlock:
                return toBlock - fromBlock
            else:
                return (endTripleBlock - fromBlock) * 3 + (toBlock - endTripleBlock)
        else:
            return 0

    def calTvl(self, pool, poolInfo: dict):
        tokens = pool.functions.getCurrentTokens().call()
        balance = pool.functions.getBalance(tokens[poolInfo['referIndex']]).call()
        denorm = pool.functions.getNormalizedWeight(tokens[poolInfo['referIndex']]).call()
        totalBalance = bdiv(balance, denorm)
        info = OracleContract.functions.tokenPrice(tokens[poolInfo['referIndex']]).call()
        divisor = int(10 ** info[0])
        logger.info("get price and divisor: {}, {}".format(info[1], divisor))
        calTvl = totalBalance * info[1] * poolInfo["allocPoint"] // divisor
        return calTvl

    def calLPMiningAward(self, passedBlock, tokenPerBlock, shareInfo, poolInfo, userInfo, changeAmount, isadd):
        newTvl = self.calTvl(poolContract, poolInfo)
        poolReward = int(passedBlock * 1000000000000000000 * tokenPerBlock // shareInfo["tvl"])
        accPoolPerShare = poolReward + shareInfo["accPoolPerShare"]
        logger.info("计算后的accPoolPerShare: {}".format(accPoolPerShare))
        totalLiquidity = poolContract.functions.totalSupply().call()
        lastLP = totalLiquidity - changeAmount if isadd else totalLiquidity + changeAmount
        tokenReward = (accPoolPerShare * poolInfo["lastTvl"] - poolInfo["rewardDebt"]) // lastLP
        accTokenPerShare = tokenReward + poolInfo["accTokenPerShare"]
        logger.info("计算后的 accTokenPerShare: {}".format(accTokenPerShare))
        userAmount = poolContract.functions.balanceOf(self.account.address).call()
        lastAmout = userAmount - changeAmount if isadd else userAmount + changeAmount
        userShare = (accTokenPerShare * lastAmout - userInfo["rewardDebt"]) // 1000000000000000000
        logger.info("本次应分得的奖励: {}".format(userShare))
        tvl = shareInfo["tvl"] + newTvl - poolInfo["lastTvl"]
        logger.info("shareInfo的tvl: {}".format(tvl))
        return accPoolPerShare, accTokenPerShare, userShare, tvl, newTvl

    def checkLPMingClaimUserShares(self, lpMining, poolAddress):
        " 检查添加LP奖励计算正确 "
        # 添加LP前获取LPMining信息
        pid = lpMining.functions.indexOfPool(poolAddress).call()
        logger.info("添加LP前获取LPMining信息...")
        shareInfo, poolInfo, userInfo = self.getLPMingInfo(lpMining, poolAddress, pid)
        awardBalance_1 = awardContract.functions.getUserTotalAwards(self.account.address).call()
        logger.info("操作前奖励: {}".format(awardBalance_1))
        # tokenPerBlock = lpMining.functions.tokenPerBlock().call()
        # self.calLPMiningAward(280, tokenPerBlock, shareInfo, poolInfo, userInfo, 0, True)
        blance = poolContract.functions.balanceOf(self.account.address).call()
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        execute_func = lpMining.functions.claimUserShares(pid, self.account.address)
        tx_hash = self.excuteTransaction(execute_func, nonce)
        time.sleep(3)
        shareInfoAfter, poolInfoAfter, userInfoAfter = self.getLPMingInfo(lpMining, poolAddress, pid)
        awardBalance_2 = awardContract.functions.getUserTotalAwards(self.account.address).call()
        logger.info("操作前奖励: {}".format(awardBalance_2))
        awardChanged = awardBalance_2 - awardBalance_1
        tokenPerBlock = lpMining.functions.tokenPerBlock().call()
        blockNum = self.getMultiplierBlock(lpMining, shareInfo["lastRewardBlock"], shareInfoAfter["lastRewardBlock"])
        accPoolPerShare, accTokenPerShare, userShare, tvl, newTvl = self.calLPMiningAward(blockNum, tokenPerBlock,
                                                                                          shareInfo, poolInfo,
                                                                                          userInfo, 0, True)
        assert accPoolPerShare == shareInfoAfter["accPoolPerShare"], "accPoolPerShare 计算不正确"
        assert accTokenPerShare == poolInfoAfter["accTokenPerShare"], "accTokenPerShare 计算不正确"
        assert tvl == shareInfoAfter["tvl"], "accPoolPerShare 计算不正确"
        assert accPoolPerShare * newTvl == poolInfoAfter["rewardDebt"], "poolInfo的rewardDebt 计算不正确"
        assert blance * accTokenPerShare == userInfoAfter["rewardDebt"], "用户的 rewardDebt 计算不正确"
        assert awardChanged == userShare, "用户得到的奖励计算不正确: {} {}".format(awardChanged, userShare)

    def checkLPMingJoinPool(self, lpMining, poolAddress):
        " 检查添加LP奖励计算正确 "
        # 添加LP前获取LPMining信息
        pid = lpMining.functions.indexOfPool(poolAddress).call()
        logger.info("添加LP前获取LPMining信息...")
        shareInfo, poolInfo, userInfo = self.getLPMingInfo(lpMining, poolAddress, pid)
        awardBalance_1 = awardContract.functions.getUserTotalAwards(self.account.address).call()
        logger.info("操作前奖励: {}".format(awardBalance_1))
        # tokenPerBlock = lpMining.functions.tokenPerBlock().call()
        # self.calLPMiningAward(280, tokenPerBlock, shareInfo, poolInfo, userInfo, 0, True)
        blance = poolContract.functions.balanceOf(self.account.address).call()
        logger.info("操作前balance: {}".format(blance))
        self.checkJoinPool(poolContract, poolAddress)
        time.sleep(3)
        shareInfoAfter, poolInfoAfter, userInfoAfter = self.getLPMingInfo(lpMining, poolAddress, pid)
        awardBalance_2 = awardContract.functions.getUserTotalAwards(self.account.address).call()
        logger.info("操作后奖励: {}".format(awardBalance_2))
        awardChanged = awardBalance_2 - awardBalance_1
        tokenPerBlock = lpMining.functions.tokenPerBlock().call()
        blance1 = poolContract.functions.balanceOf(self.account.address).call()
        changeAmount = blance1 - blance
        logger.info("操作后balance: {}, 发送变化: +{}".format(blance1, changeAmount))
        blockNum = self.getMultiplierBlock(lpMining, shareInfo["lastRewardBlock"], shareInfoAfter["lastRewardBlock"])
        accPoolPerShare, accTokenPerShare, userShare, tvl, newTvl = self.calLPMiningAward(blockNum, tokenPerBlock,
                                                                                          shareInfo, poolInfo,
                                                                                          userInfo, changeAmount, True)
        assert accPoolPerShare == shareInfoAfter["accPoolPerShare"], "accPoolPerShare 计算不正确"
        assert accTokenPerShare == poolInfoAfter["accTokenPerShare"], "accTokenPerShare 计算不正确"
        assert tvl == shareInfoAfter["tvl"], f"{tvl} 和 {shareInfoAfter['tvl']} tvl计算不正确"
        assert accPoolPerShare * newTvl == poolInfoAfter["rewardDebt"], "poolInfo的rewardDebt 计算不正确"
        assert blance1 * accTokenPerShare == userInfoAfter["rewardDebt"], "用户的 rewardDebt 计算不正确"
        assert awardChanged == userShare, "用户得到的奖励计算不正确: {} {}".format(awardChanged, userShare)

    def checkLPMingJoinSwapExternAmountIn(self, lpMining, poolAddress):
        " 检查添加LP奖励计算正确 "
        # 添加LP前获取LPMining信息
        pid = lpMining.functions.indexOfPool(poolAddress).call()
        logger.info("添加LP前获取LPMining信息...")
        shareInfo, poolInfo, userInfo = self.getLPMingInfo(lpMining, poolAddress, pid)
        awardBalance_1 = awardContract.functions.getUserTotalAwards(self.account.address).call()
        logger.info("操作前奖励: {}".format(awardBalance_1))
        # tokenPerBlock = lpMining.functions.tokenPerBlock().call()
        # self.calLPMiningAward(280, tokenPerBlock, shareInfo, poolInfo, userInfo, 0, True)
        blance = poolContract.functions.balanceOf(self.account.address).call()
        logger.info("操作前balance: {}".format(blance))
        self.checkJoinSwapExternAmountIn(poolContract, poolAddress, ERC20_testb)
        time.sleep(3)
        shareInfoAfter, poolInfoAfter, userInfoAfter = self.getLPMingInfo(lpMining, poolAddress, pid)
        awardBalance_2 = awardContract.functions.getUserTotalAwards(self.account.address).call()
        logger.info("操作后奖励: {}".format(awardBalance_2))
        awardChanged = awardBalance_2 - awardBalance_1
        tokenPerBlock = lpMining.functions.tokenPerBlock().call()
        blance1 = poolContract.functions.balanceOf(self.account.address).call()
        changeAmount = blance1 - blance
        logger.info("操作后balance: {}, 发送变化: +{}".format(blance1, changeAmount))
        blockNum = self.getMultiplierBlock(lpMining, shareInfo["lastRewardBlock"], shareInfoAfter["lastRewardBlock"])
        accPoolPerShare, accTokenPerShare, userShare, tvl, newTvl = self.calLPMiningAward(blockNum, tokenPerBlock,
                                                                                          shareInfo, poolInfo,
                                                                                          userInfo, changeAmount, True)
        assert accPoolPerShare == shareInfoAfter["accPoolPerShare"], "accPoolPerShare 计算不正确"
        assert accTokenPerShare == poolInfoAfter["accTokenPerShare"], "accTokenPerShare 计算不正确"
        assert tvl == shareInfoAfter["tvl"], f"{tvl} 和 {shareInfoAfter['tvl']} tvl计算不正确"
        assert accPoolPerShare * newTvl == poolInfoAfter["rewardDebt"], "poolInfo的rewardDebt 计算不正确"
        assert blance1 * accTokenPerShare == userInfoAfter["rewardDebt"], "用户的 rewardDebt 计算不正确"
        assert awardChanged == userShare, "用户得到的奖励计算不正确: {} {}".format(awardChanged, userShare)

    def checkLPMingExitPool(self, lpMining, poolAddress):
        " 检查添加LP奖励计算正确 "
        # 添加LP前获取LPMining信息
        pid = lpMining.functions.indexOfPool(poolAddress).call()
        logger.info("添加LP前获取LPMining信息...")
        shareInfo, poolInfo, userInfo = self.getLPMingInfo(lpMining, poolAddress, pid)
        awardBalance_1 = awardContract.functions.getUserTotalAwards(self.account.address).call()
        logger.info("操作前奖励: {}".format(awardBalance_1))
        # tokenPerBlock = lpMining.functions.tokenPerBlock().call()
        # self.calLPMiningAward(280, tokenPerBlock, shareInfo, poolInfo, userInfo, 0, True)
        blance = poolContract.functions.balanceOf(self.account.address).call()
        logger.info("操作前balance: {}".format(blance))
        self.checkExitPool(poolContract, False)
        time.sleep(3)
        shareInfoAfter, poolInfoAfter, userInfoAfter = self.getLPMingInfo(lpMining, poolAddress, pid)
        awardBalance_2 = awardContract.functions.getUserTotalAwards(self.account.address).call()
        logger.info("操作后奖励: {}".format(awardBalance_2))
        awardChanged = awardBalance_2 - awardBalance_1
        tokenPerBlock = lpMining.functions.tokenPerBlock().call()
        blance1 = poolContract.functions.balanceOf(self.account.address).call()
        changeAmount = blance - blance1
        logger.info("操作后balance: {}, 发送变化: -{}".format(blance1, changeAmount))
        blockNum = self.getMultiplierBlock(lpMining, shareInfo["lastRewardBlock"], shareInfoAfter["lastRewardBlock"])
        accPoolPerShare, accTokenPerShare, userShare, tvl, newTvl = self.calLPMiningAward(blockNum, tokenPerBlock,
                                                                                          shareInfo, poolInfo,
                                                                                          userInfo, changeAmount, False)
        assert accPoolPerShare == shareInfoAfter["accPoolPerShare"], "accPoolPerShare 计算不正确"
        assert accTokenPerShare == poolInfoAfter["accTokenPerShare"], "accTokenPerShare 计算不正确"
        assert tvl == shareInfoAfter["tvl"], f"{tvl} 和 {shareInfoAfter['tvl']} tvl计算不正确"
        assert accPoolPerShare * newTvl == poolInfoAfter["rewardDebt"], "poolInfo的rewardDebt 计算不正确"
        assert blance1 * accTokenPerShare == userInfoAfter["rewardDebt"], "用户的 rewardDebt 计算不正确"
        assert awardChanged == userShare, "用户得到的奖励计算不正确: {} {}".format(awardChanged, userShare)

    def checkLPMingExitSwapPoolAmountIn(self, lpMining, poolAddress, outTokenAddr):
        " 检查添加LP奖励计算正确 "
        # 添加LP前获取LPMining信息
        pid = lpMining.functions.indexOfPool(poolAddress).call()
        logger.info("添加LP前获取LPMining信息...")
        shareInfo, poolInfo, userInfo = self.getLPMingInfo(lpMining, poolAddress, pid)
        awardBalance_1 = awardContract.functions.getUserTotalAwards(self.account.address).call()
        logger.info("操作前奖励: {}".format(awardBalance_1))
        # tokenPerBlock = lpMining.functions.tokenPerBlock().call()
        # self.calLPMiningAward(280, tokenPerBlock, shareInfo, poolInfo, userInfo, 0, True)
        blance = poolContract.functions.balanceOf(self.account.address).call()
        logger.info("操作前balance: {}".format(blance))
        self.checkExitSwapPoolAmountIn(poolContract, outTokenAddr, False)
        time.sleep(3)
        shareInfoAfter, poolInfoAfter, userInfoAfter = self.getLPMingInfo(lpMining, poolAddress, pid)
        awardBalance_2 = awardContract.functions.getUserTotalAwards(self.account.address).call()
        logger.info("操作后奖励: {}".format(awardBalance_2))
        awardChanged = awardBalance_2 - awardBalance_1
        tokenPerBlock = lpMining.functions.tokenPerBlock().call()
        blance1 = poolContract.functions.balanceOf(self.account.address).call()
        changeAmount = blance - blance1
        logger.info("操作后balance: {}, 发送变化: -{}".format(blance1, changeAmount))
        blockNum = self.getMultiplierBlock(lpMining, shareInfo["lastRewardBlock"], shareInfoAfter["lastRewardBlock"])
        accPoolPerShare, accTokenPerShare, userShare, tvl, newTvl = self.calLPMiningAward(blockNum, tokenPerBlock,
                                                                                          shareInfo, poolInfo,
                                                                                          userInfo, changeAmount, False)
        assert accPoolPerShare == shareInfoAfter["accPoolPerShare"], "accPoolPerShare 计算不正确"
        assert accTokenPerShare == poolInfoAfter["accTokenPerShare"], "accTokenPerShare 计算不正确"
        assert tvl == shareInfoAfter["tvl"], f"{tvl} 和 {shareInfoAfter['tvl']} tvl计算不正确"
        assert accPoolPerShare * newTvl == poolInfoAfter["rewardDebt"], "poolInfo的rewardDebt 计算不正确"
        assert blance1 * accTokenPerShare == userInfoAfter["rewardDebt"], "用户的 rewardDebt 计算不正确"
        assert awardChanged == userShare, "用户得到的奖励计算不正确: {} {}".format(awardChanged, userShare)

    def checkLPMingSet(self, lpMining, poolAddress):
        " 检查添加LP奖励计算正确 "
        # 添加LP前获取LPMining信息
        pid = lpMining.functions.indexOfPool(poolAddress).call()
        logger.info("添加LP前获取LPMining信息...")
        shareInfo, poolInfo, userInfo = self.getLPMingInfo(lpMining, poolAddress, pid)
        awardBalance_1 = awardContract.functions.getUserTotalAwards(self.account.address).call()
        logger.info("操作前奖励: {}".format(awardBalance_1))
        blance = poolContract.functions.balanceOf(self.account.address).call()
        logger.info("操作前balance: {}".format(blance))
        exe_func = lpMining.functions.set(poolInfo["poolIndex"], 300)
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        tx_hash = self.excuteTransaction(exe_func, nonce)
        time.sleep(10)
        awardBalance_2 = awardContract.functions.getUserTotalAwards(self.account.address).call()
        logger.info("操作后奖励: {}".format(awardBalance_2))
        awardChanged = awardBalance_2 - awardBalance_1
        tokenPerBlock = lpMining.functions.tokenPerBlock().call()
        blance1 = poolContract.functions.balanceOf(self.account.address).call()
        changeAmount = blance - blance1
        logger.info("操作后balance: {}, 发送变化: -{}".format(blance1, changeAmount))
        shareInfoAfter, poolInfoAfter, userInfoAfter = self.getLPMingInfo(lpMining, poolAddress, pid)
        blockNum = self.getMultiplierBlock(lpMining, shareInfo["lastRewardBlock"], shareInfoAfter["lastRewardBlock"])
        accPoolPerShare, accTokenPerShare, userShare, tvl, newTvl = self.calLPMiningAward(blockNum, tokenPerBlock,
                                                                                          shareInfo, poolInfo,
                                                                                          userInfo, changeAmount, False)
        assert accPoolPerShare == shareInfoAfter["accPoolPerShare"], "accPoolPerShare 计算不正确"
        assert accTokenPerShare == poolInfoAfter["accTokenPerShare"], "accTokenPerShare 计算不正确"
        assert tvl == shareInfoAfter["tvl"], f"{tvl} 和 {shareInfoAfter['tvl']} tvl计算不正确"
        assert accPoolPerShare * newTvl == poolInfoAfter["rewardDebt"], "poolInfo的rewardDebt 计算不正确"
        assert userInfo["rewardDebt"] == userInfoAfter["rewardDebt"], "用户的 rewardDebt 计算不正确"
        assert awardChanged == 0, "用户得到的奖励计算不正确: {} {}".format(awardChanged, 0)

    def checkLPMingLPTransferFrom(self, lpMining, poolAddress, account):
        " 检查添加LP奖励计算正确 "
        # 添加LP前获取LPMining信息
        try:
            pid = lpMining.functions.indexOfPool(poolAddress).call()
            logger.info("添加LP前获取LPMining信息...")
            shareInfo, poolInfo, userInfo = self.getLPMingInfo(lpMining, poolAddress, pid)
            awardBalance1_before = awardContract.functions.getUserTotalAwards(self.account.address).call()
            logger.info("{} 操作前奖励: {}".format(self.account.address, awardBalance1_before))
            awardBalance2_bebore = awardContract.functions.getUserTotalAwards(account).call()
            logger.info("{} 操作前奖励: {}".format(account, awardBalance2_bebore))
            blance = poolContract.functions.balanceOf(self.account.address).call()
            logger.info("操作前balance: {}".format(blance))
            # approve授权
            nonce = self.w3.eth.getTransactionCount(self.account.address)
            approve_func = poolContract.functions.approve(account, blance)
            tx_hash = self.excuteTransaction(approve_func, nonce)
            # 设置白名单
            setWhiteList = BFactoryContract.functions.updateWhiteList(self.account.address, True)
            nonce = self.w3.eth.getTransactionCount(self.account.address)
            tx_hash = self.excuteTransaction(setWhiteList, nonce)
            # lp transferFrom
            nonce = self.w3.eth.getTransactionCount(self.account.address)
            transfer_func = poolContract.functions.transferFrom(self.account.address, account, 1000000)
            tx_hash = self.excuteTransaction(transfer_func, nonce)
            time.sleep(10)
            awardBalance1_after = awardContract.functions.getUserTotalAwards(self.account.address).call()
            logger.info("{} 操作后奖励: {}".format(self.account.address, awardBalance1_after))
            awardBalance2_after = awardContract.functions.getUserTotalAwards(account).call()
            logger.info("{} 操作后奖励: {}".format(account, awardBalance2_after))
            awardChanged = awardBalance1_after - awardBalance1_before
            logger.info("{} 奖励变化: {}".format(self.account.address, awardChanged))
            logger.info("{} 奖励变化: {}".format(account, awardBalance2_after - awardBalance2_bebore))
            tokenPerBlock = lpMining.functions.tokenPerBlock().call()
            blance1 = poolContract.functions.balanceOf(self.account.address).call()
            changeAmount = blance - blance1
            logger.info("操作后balance: {}, 发送变化: -{}".format(blance1, changeAmount))
            shareInfoAfter, poolInfoAfter, userInfoAfter = self.getLPMingInfo(lpMining, poolAddress, pid)
            blockNum = self.getMultiplierBlock(lpMining, shareInfo["lastRewardBlock"], shareInfoAfter["lastRewardBlock"])
            accPoolPerShare, accTokenPerShare, userShare, tvl, newTvl = self.calLPMiningAward(blockNum, tokenPerBlock,
                                                                                              shareInfo, poolInfo,
                                                                                              userInfo, changeAmount, False)
            assert accPoolPerShare == shareInfoAfter["accPoolPerShare"], "accPoolPerShare 计算不正确"
            assert accTokenPerShare == poolInfoAfter["accTokenPerShare"], "accTokenPerShare 计算不正确"
            assert tvl == shareInfoAfter["tvl"], f"{tvl} 和 {shareInfoAfter['tvl']} tvl计算不正确"
            assert accPoolPerShare * newTvl == poolInfoAfter["rewardDebt"], "poolInfo的rewardDebt 计算不正确"
            assert blance1 * accTokenPerShare == userInfoAfter["rewardDebt"], "用户的 rewardDebt 计算不正确"
            assert awardChanged == userShare, "用户得到的奖励计算不正确: {} {}".format(awardChanged, 0)
        except Exception as e:
            traceback.print_exc()
            print(e.args[0])
        finally:
            # 最后把白名单去掉
            pass
            # setWhiteList = BFactoryContract.functions.updateWhiteList(self.account.address, False)
            # nonce = self.w3.eth.getTransactionCount(self.account.address)
            # tx_hash = self.excuteTransaction(setWhiteList, nonce)

    def checkLPMingLPTransfer(self, lpMining, poolAddress, account):
        " 检查添加LP奖励计算正确 "
        # 添加LP前获取LPMining信息
        try:
            pid = lpMining.functions.indexOfPool(poolAddress).call()
            logger.info("添加LP前获取LPMining信息...")
            shareInfo, poolInfo, userInfo = self.getLPMingInfo(lpMining, poolAddress, pid)
            awardBalance1_before = awardContract.functions.getUserTotalAwards(self.account.address).call()
            logger.info("{} 操作前奖励: {}".format(self.account.address, awardBalance1_before))
            awardBalance2_bebore = awardContract.functions.getUserTotalAwards(account).call()
            logger.info("{} 操作前奖励: {}".format(account, awardBalance2_bebore))
            blance = poolContract.functions.balanceOf(self.account.address).call()
            logger.info("操作前balance: {}".format(blance))
            # 设置白名单
            setWhiteList = BFactoryContract.functions.updateWhiteList(self.account.address, True)
            nonce = self.w3.eth.getTransactionCount(self.account.address)
            tx_hash = self.excuteTransaction(setWhiteList, nonce)
            # lp transferFrom
            nonce = self.w3.eth.getTransactionCount(self.account.address)
            transfer_func = poolContract.functions.transfer(account, 1000000)
            tx_hash = self.excuteTransaction(transfer_func, nonce)
            time.sleep(10)
            awardBalance1_after = awardContract.functions.getUserTotalAwards(self.account.address).call()
            logger.info("{} 操作后奖励: {}".format(self.account.address, awardBalance1_after))
            awardBalance2_after = awardContract.functions.getUserTotalAwards(account).call()
            logger.info("{} 操作后奖励: {}".format(account, awardBalance2_after))
            awardChanged = awardBalance1_after - awardBalance1_before
            logger.info("{} 奖励变化: {}".format(self.account.address, awardChanged))
            logger.info("{} 奖励变化: {}".format(account, awardBalance2_after - awardBalance2_bebore))
            tokenPerBlock = lpMining.functions.tokenPerBlock().call()
            blance1 = poolContract.functions.balanceOf(self.account.address).call()
            changeAmount = blance - blance1
            logger.info("操作后balance: {}, 发送变化: -{}".format(blance1, changeAmount))
            shareInfoAfter, poolInfoAfter, userInfoAfter = self.getLPMingInfo(lpMining, poolAddress, pid)
            blockNum = self.getMultiplierBlock(lpMining, shareInfo["lastRewardBlock"], shareInfoAfter["lastRewardBlock"])
            accPoolPerShare, accTokenPerShare, userShare, tvl, newTvl = self.calLPMiningAward(blockNum, tokenPerBlock,
                                                                                              shareInfo, poolInfo,
                                                                                              userInfo, changeAmount, False)
            assert accPoolPerShare == shareInfoAfter["accPoolPerShare"], "accPoolPerShare 计算不正确"
            assert accTokenPerShare == poolInfoAfter["accTokenPerShare"], "accTokenPerShare 计算不正确"
            assert tvl == shareInfoAfter["tvl"], f"{tvl} 和 {shareInfoAfter['tvl']} tvl计算不正确"
            assert accPoolPerShare * newTvl == poolInfoAfter["rewardDebt"], "poolInfo的rewardDebt 计算不正确"
            assert blance1 * accTokenPerShare == userInfoAfter["rewardDebt"], "用户的 rewardDebt 计算不正确"
            assert awardChanged == userShare, "用户得到的奖励计算不正确: {} {}".format(awardChanged, 0)
        except Exception as e:
            traceback.print_exc()
        finally:
            # 最后把白名单去掉
            setWhiteList = BFactoryContract.functions.updateWhiteList(self.account.address, False)
            nonce = self.w3.eth.getTransactionCount(self.account.address)
            tx_hash = self.excuteTransaction(setWhiteList, nonce)

    def checkSwapMingSwapIn(self, pool, poolAddress, tokenInAddress, tokenOutAddress):
        " 检查添加交易奖励计算正确 "
        # 添加LP前获取LPMining信息
        # swapExactAmountIn
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        tokens = pool.functions.getCurrentTokens().call()
        logger.info("获取当前pool的tokens:{}".format(tokens))
        tokenBalances, tokenDenorms = [], []
        for token in tokens:
            tokenBalances.append(pool.functions.getBalance(token).call())
            tokenDenorms.append(pool.functions.getDenormalizedWeight(token).call())
        logger.info("获取当前pool的balance: {}".format(tokenBalances))
        logger.info("获取当前pool的denorm: {}".format(tokenDenorms))
        totalSupply = pool.functions.totalSupply().call()
        logger.info("获取当前pool的totalSupply: {}".format(totalSupply))
        fee = pool.functions.getSwapFee().call()
        tokenInIndex = tokens.index(tokenInAddress)
        tokenOutIndex = tokens.index(tokenOutAddress)
        # tokenBalances[tokenInIndex] = tokenBalances[tokenInIndex] - 4700537159732116252
        spotPriceBefore = pool.functions.calcSpotPrice(tokenBalances[tokenInIndex], tokenDenorms[tokenInIndex],
                                                        tokenBalances[tokenOutIndex], tokenDenorms[tokenOutIndex],
                                                        fee).call()
        logger.info("当前pool的价格:{}".format(spotPriceBefore))
        tokenAmountIn = self.w3.toWei("10", "ether")
        # tokenAmountIn = 4608820422605067095
        tokenAmountOut = pool.functions.calcOutGivenIn(tokenBalances[tokenInIndex], tokenDenorms[tokenInIndex],
                                                        tokenBalances[tokenOutIndex], tokenDenorms[tokenOutIndex],
                                                        tokenAmountIn, fee).call()

        logger.info("当前pool, 用 {} 的tokenIn可以买到 {} 的tokenOut".format(tokenAmountIn, tokenAmountOut))
        inBalance = tokenBalances[tokenInIndex] + tokenAmountIn
        outBalance = tokenBalances[tokenOutIndex] - tokenAmountOut
        spotPriceAfter = pool.functions.calcSpotPrice(inBalance, tokenDenorms[tokenInIndex],
                                                       outBalance, tokenDenorms[tokenOutIndex],
                                                       fee).call()
        logger.info("买入后pool的价格:{}".format(spotPriceAfter))
        swapFee = bmul(tokenAmountIn, bmul(bdiv(fee, 6), 1))
        logger.info("预计抽取的我们交易费用为: {}".format(swapFee))
        print('"{}","{}","{}","{}","{}","{}"'.format(self.account.address, tokenInAddress, tokenAmountIn,
                                                    tokenOutAddress, tokenAmountOut, spotPriceAfter))
        # exe_func = pool.functions.swapExactAmountIn(self.account.address, tokenInAddress, tokenAmountIn,
        #                                             tokenOutAddress, tokenAmountOut, spotPriceAfter)
        # swaps = ([poolAddress, tokenInAddress, tokenOutAddress, tokenAmountIn, tokenAmountOut, spotPriceAfter])
        # print(swaps, tokenInAddress, tokenOutAddress, tokenAmountIn, tokenAmountOut)
        # eProxy_func = self.exchangeProxy.functions.batchSwapExactIn(swaps, tokenInAddress, tokenOutAddress,
        #                                                             tokenAmountIn, tokenAmountOut)

        # logger.info("准备执行 batchSwapExactIn...")
        # self.excuteTransaction(exe_func, nonce)

    def checkSwapMingSwapOut(self, pool, poolAddress, tokenInAddress, tokenOutAddress):
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        tokens = pool.functions.getCurrentTokens().call()
        logger.info("获取当前pool的tokens:{}".format(tokens))
        tokenBalances, tokenDenorms = [], []
        for token in tokens:
            tokenBalances.append(pool.functions.getBalance(token).call())
            tokenDenorms.append(pool.functions.getDenormalizedWeight(token).call())
        logger.info("获取当前pool的balance: {}".format(tokenBalances))
        logger.info("获取当前pool的denorm: {}".format(tokenDenorms))
        totalSupply = pool.functions.totalSupply().call()
        logger.info("获取当前pool的totalSupply: {}".format(totalSupply))
        fee = pool.functions.getSwapFee().call()
        tokenInIndex = tokens.index(tokenInAddress)
        tokenOutIndex = tokens.index(tokenOutAddress)
        spotPriceBefore = pool.functions.calcSpotPrice(tokenBalances[tokenInIndex], tokenDenorms[tokenInIndex],
                                                        tokenBalances[tokenOutIndex], tokenDenorms[tokenOutIndex],
                                                        fee).call()
        logger.info("当前pool的价格:{}".format(spotPriceBefore))
        tokenAmountOut = self.w3.toWei("10", "ether")
        # tokenAmountOut = 4723981334316373000
        tokenAmountIn = pool.functions.calcInGivenOut(tokenBalances[tokenInIndex], tokenDenorms[tokenInIndex],
                                                       tokenBalances[tokenOutIndex], tokenDenorms[tokenOutIndex],
                                                       tokenAmountOut, fee).call()

        logger.info("当前pool, 想买到 {} 的tokenOut需要用 {} 的tokenIn来买".format(tokenAmountOut, tokenAmountIn))
        inBalance = tokenBalances[tokenInIndex] + tokenAmountIn
        outBalance = tokenBalances[tokenOutIndex] - tokenAmountOut
        spotPriceAfter = pool.functions.calcSpotPrice(inBalance, tokenDenorms[tokenInIndex],
                                                       outBalance, tokenDenorms[tokenOutIndex],
                                                       fee).call()
        logger.info("买入后pool的价格:{}".format(spotPriceAfter))
        swapFee = bmul(tokenAmountIn, bmul(bdiv(fee, 6), 1))
        logger.info("预计抽取的我们交易费用为: {}".format(swapFee))
        # swaps = ([str(poolAddress), tokenInAddress, tokenOutAddress, str(tokenAmountIn), str(tokenAmountOut),
        #           str(spotPriceAfter)])
        # print(swaps, tokenInAddress, tokenOutAddress, tokenAmountIn)
        # logger.info("args: {},{},{},{}".format(swaps, tokenInAddress,tokenOutAddress, toke
        print('"{}","{}","{}","{}","{}","{}"'.format(self.account.address, tokenInAddress, tokenAmountIn,
                                                     tokenOutAddress, tokenAmountOut, spotPriceAfter))

    def calSwapShare(self, swp, user):
        userInfo = swp.functions.userInfo(user).call()
        tokenPerDay = swp.functions.tokenPerDay().call()
        tradeInfo = swp.functions.tradeInfo(userInfo[0]).call()
        shares = tokenPerDay * userInfo[1] // tradeInfo[0]
        if tradeInfo[1] + shares > tokenPerDay:
            shares = tokenPerDay - tradeInfo[1]
        logger.info(f"{user} 待领取的奖励为: {shares}")
        return shares

    def getSwapMingInfo(self, swp):
        userInfo = swp.functions.userInfo(self.account.address).call()
        userInfo_2 = swp.functions.userInfo(SwapAccount2.address).call()
        startDay = swp.functions.startDay().call()
        currDay = swp.functions.getCurrDay().call()
        for i in range(startDay, currDay+1):
            tradeInfo = swp.functions.tradeInfo(i).call()
            logger.info(f"{i} day tradeInfo: {tradeInfo}")
        # userInfo = swp.functions.userInfo(self.account.address).call()
        logger.info(f"user1 Info: {userInfo}")
        logger.info(f"user2 Info: {userInfo_2}")
        logger.info(f"currDay: {currDay}")

    def calPendingPairShare(self, changedBlock, uInfo, accLP, lp, ratio=85):
        # b = 1000000000000
        b = 10000000000000000000000
        pending = changedBlock * 40000000000000000 * ratio * b // lp
        pendLpShare = uInfo[0] * (accLP + pending) // b - uInfo[1]
        logger.info("cal pendShare: {}".format(pendLpShare))
        return pendLpShare

    def calAccGPShare(self, changedBlock, accLp, accGp, lp, gp, gpRatio=15):
        b = 10000000000000000000000
        gpShare = changedBlock * 40000000000000000 * gpRatio
        logger.info("gp分得的奖励:{}".format(gpShare))
        newAccGP = accGp + gpShare * b // gp
        logger.info("新的accGp: {}".format(newAccGP))
        lpShare = changedBlock * 4000000000000000000 - gpShare
        logger.info("lp分得的奖励: {}".format(lpShare))
        newAccLP = accLp + lpShare * b // lp
        logger.info("新的accLp: {}".format(newAccLP))
        return newAccLP, newAccGP, lpShare, gpShare

    def checkPendingPair(self, pairAddress):
        pairContract = client.get_contract(pairAddress, "./abi/PairToken.json")
        start = pairContract.functions._poolLastRewardBlock().call()
        logger.info("_poolLastRewardBlock: {}".format(start))
        lp = pairContract.functions._totalLpSupply().call()
        accLP = pairContract.functions._poolAccPairPerShare().call()
        accGP = pairContract.functions._poolAccPairGpPerShare().call()
        uLPinfo = pairContract.functions.lpInfoList(client.account.address).call()
        uGPinfo = pairContract.functions.gpInfoList(GP_addr[0]).call()
        logger.info(f"{client.account.address} info: {uLPinfo}")
        logger.info(f"{SwapAccount2.address} info: {uGPinfo}")

        blockNum = self.w3.eth.blockNumber
        curLP = pairContract.functions.pendingPair(False, client.account.address).call()
        curGP = pairContract.functions.pendingPair(True, SwapAccount2.address).call()
        logger.info(f"total lp: {lp}")
        logger.info(f"curLp,")
        changedBlock = blockNum - start
        logger.info("blockNumber: {}".format(blockNum))
        logger.info("changedBlock: {}".format(changedBlock))
        # a = changedBlock * 40000000000000000 * 85 * 1000000000000 // lp
        # pendLpShare = uLPinfo[0] * (accLP + a) // 1000000000000 - uLPinfo[1]
        pendLpShare = self.calPendingPairShare(changedBlock, uLPinfo, accLP, lp, 85)
        logger.info("calPend: {}".format(pendLpShare))
        logger.info("pending: {}".format(curLP))

        currentBalance = pairContract.functions.balanceOf(client.account.address).call()
        logger.info("currentBalance: {}".format(currentBalance))

        # b = changedBlock * 40000000000000000 * 15 * 1000000000000 // 1000
        # pendGpShare = uGPinfo[0] * (accGP + b) // 1000000000000 - uGPinfo[1]
        pendGpShare = self.calPendingPairShare(changedBlock, uGPinfo, accGP, 1000, 15)
        logger.info("gp pending: {}".format(curGP))
        currentBalance = pairContract.functions.balanceOf(SwapAccount2.address).call()
        logger.info("gp currentBalance: {}".format(currentBalance))

        assert curGP == pendGpShare
        assert curLP == pendLpShare

    def checkJoinPoolSharePair(self, pairAddress, pool, poolAddress):
        pairContract = client.get_contract(pairAddress, "./abi/PairToken.json")
        start = pairContract.functions._poolLastRewardBlock().call()
        logger.info("_poolLastRewardBlock: {}".format(start))
        lp = pairContract.functions._totalLpSupply().call()
        logger.info(f"total lp: {lp}")
        accLP = pairContract.functions._poolAccPairPerShare().call()
        accGP = pairContract.functions._poolAccPairGpPerShare().call()
        uLPinfo = pairContract.functions.lpInfoList(client.account.address).call()
        uGPinfo = pairContract.functions.gpInfoList(GP_addr[0]).call()
        logger.info(f"{client.account.address} info: {uLPinfo}")
        logger.info(f"{SwapAccount2.address} info: {uGPinfo}")

        LpUserBalance = pairContract.functions.balanceOf(client.account.address).call()
        logger.info("lp user balance: {}".format(LpUserBalance))
        GpUserBalance = pairContract.functions.balanceOf(GP_addr[0]).call()
        logger.info("gp user Balance: {}".format(GpUserBalance))

        tx_hash = self.checkJoinPool(pool, poolAddress)
        tx_info = self.w3.eth.getTransactionReceipt(tx_hash)

        poolSupply = pool.functions.totalSupply().call()
        curlp2 = pairContract.functions._totalLpSupply().call()

        # accLP = pairContract.functions._poolAccPairPerShare().call()
        # accGP = pairContract.functions._poolAccPairGpPerShare().call()
        # 加入池子后，lp自动分得上一次的奖励，gp不分得奖励
        blockNum = tx_info["blockNumber"]
        changedBlock = blockNum - start
        logger.info("blockNumber: {}".format(blockNum))
        logger.info("changedBlock: {}".format(changedBlock))
        newAccLP, newAccGP, lpShare, gpShare = self.calAccGPShare(changedBlock, accLP, accGP, lp, 1000, 15)
        time.sleep(3)
        accLP2 = pairContract.functions._poolAccPairPerShare().call()
        accGP2 = pairContract.functions._poolAccPairGpPerShare().call()

        LpUserBalance2 = pairContract.functions.balanceOf(client.account.address).call()
        logger.info("lp user balance: {}".format(LpUserBalance2))
        GpUserBalance2 = pairContract.functions.balanceOf(GP_addr[0]).call()
        logger.info("gp user Balance: {}".format(GpUserBalance2))

        assert LpUserBalance + lpShare == LpUserBalance2, "joinPool，自动分得上一次的奖励"
        assert GpUserBalance2 == GpUserBalance, "joinPool后，gp用户不自动分得奖励"
        assert accLP2 == newAccLP
        assert accGP2 == newAccGP

        time.sleep(60)
        self.checkPendingPair(pairAddress)

        # 有可能不一致，如果先创建的pool进行了joinPool，再bindPair就有可能对不上
        assert poolSupply == curlp2, "pool中lp和pair中的lp不一致"

    def checkExitPoolSharePair(self, pairAddress, pool, poolAddress):
        pairContract = client.get_contract(pairAddress, "./abi/PairToken.json")
        start = pairContract.functions._poolLastRewardBlock().call()
        logger.info("_poolLastRewardBlock: {}".format(start))
        lp = pairContract.functions._totalLpSupply().call()
        logger.info(f"total lp: {lp}")
        accLP = pairContract.functions._poolAccPairPerShare().call()
        accGP = pairContract.functions._poolAccPairGpPerShare().call()
        uLPinfo = pairContract.functions.lpInfoList(client.account.address).call()
        uGPinfo = pairContract.functions.gpInfoList(GP_addr[0]).call()
        logger.info(f"{client.account.address} info: {uLPinfo}")
        logger.info(f"{SwapAccount2.address} info: {uGPinfo}")

        LpUserBalance = pairContract.functions.balanceOf(client.account.address).call()
        logger.info("lp user balance: {}".format(LpUserBalance))
        GpUserBalance = pairContract.functions.balanceOf(GP_addr[0]).call()
        logger.info("gp user Balance: {}".format(GpUserBalance))

        tx_hash = self.checkExitPool(pool, poolAddress, False)
        tx_info = self.w3.eth.getTransactionReceipt(tx_hash)

        poolSupply = pool.functions.totalSupply().call()
        curlp2 = pairContract.functions._totalLpSupply().call()

        # 加入池子后，lp自动分得上一次的奖励，gp不分得奖励
        blockNum = tx_info["blockNumber"]
        changedBlock = blockNum - start
        logger.info("blockNumber: {}".format(blockNum))
        logger.info("changedBlock: {}".format(changedBlock))
        newAccLP, newAccGP, lpShare, gpShare = self.calAccGPShare(changedBlock, accLP, accGP, lp, 1000, 15)
        time.sleep(3)
        accLP2 = pairContract.functions._poolAccPairPerShare().call()
        accGP2 = pairContract.functions._poolAccPairGpPerShare().call()

        LpUserBalance2 = pairContract.functions.balanceOf(client.account.address).call()
        logger.info("lp user balance: {}".format(LpUserBalance2))
        GpUserBalance2 = pairContract.functions.balanceOf(GP_addr[0]).call()
        logger.info("gp user Balance: {}".format(GpUserBalance2))

        assert LpUserBalance + lpShare == LpUserBalance2, "joinPool，自动分得上一次的奖励"
        assert GpUserBalance2 == GpUserBalance, "joinPool后，gp用户不自动分得奖励"
        assert accLP2 == newAccLP
        assert accGP2 == newAccGP

        time.sleep(60)
        self.checkPendingPair(pairAddress)
        # 有可能不一致，如果先创建的pool进行了joinPool，再bindPair就有可能对不上
        assert poolSupply == curlp2, "pool中lp和pair中的lp不一致"

    def checkLPClaimPair(self, pairAddress, pool, poolAddress):
        pairContract = client.get_contract(pairAddress, "./abi/PairToken.json")
        start = pairContract.functions._poolLastRewardBlock().call()
        logger.info("_poolLastRewardBlock: {}".format(start))
        lp = pairContract.functions._totalLpSupply().call()
        logger.info(f"total lp: {lp}")
        accLP = pairContract.functions._poolAccPairPerShare().call()
        accGP = pairContract.functions._poolAccPairGpPerShare().call()
        uLPinfo = pairContract.functions.lpInfoList(client.account.address).call()
        uGPinfo = pairContract.functions.gpInfoList(GP_addr[0]).call()
        logger.info(f"{client.account.address} info: {uLPinfo}")
        logger.info(f"{SwapAccount2.address} info: {uGPinfo}")

        LpUserBalance = pairContract.functions.balanceOf(client.account.address).call()
        logger.info("lp user balance: {}".format(LpUserBalance))
        GpUserBalance = pairContract.functions.balanceOf(GP_addr[0]).call()
        logger.info("gp user Balance: {}".format(GpUserBalance))

        nonce = self.w3.eth.getTransactionCount(self.account.address)
        ex_func = pairContract.functions.claimPair(False, self.account.address)
        tx_hash = self.excuteTransaction(ex_func, nonce)
        tx_info = self.w3.eth.getTransactionReceipt(tx_hash)

        poolSupply = pool.functions.totalSupply().call()
        curlp2 = pairContract.functions._totalLpSupply().call()

        # 加入池子后，lp自动分得上一次的奖励，gp不分得奖励
        blockNum = tx_info["blockNumber"]
        changedBlock = blockNum - start
        logger.info("blockNumber: {}".format(blockNum))
        logger.info("changedBlock: {}".format(changedBlock))
        # pendingGp = self.calPendingPairShare(changedBlock, uGPinfo, accGP, 1000, 15)
        newAccLP, newAccGP, lpShare, gpShare = self.calAccGPShare(changedBlock, accLP, accGP, lp, 1000, 15)
        time.sleep(3)
        accLP2 = pairContract.functions._poolAccPairPerShare().call()
        accGP2 = pairContract.functions._poolAccPairGpPerShare().call()

        LpUserBalance2 = pairContract.functions.balanceOf(client.account.address).call()
        logger.info("lp user balance: {}".format(LpUserBalance2))
        GpUserBalance2 = pairContract.functions.balanceOf(GP_addr[0]).call()
        logger.info("gp user Balance: {}".format(GpUserBalance2))

        assert LpUserBalance + lpShare == LpUserBalance2, "joinPool，自动分得上一次的奖励"
        assert GpUserBalance2 == GpUserBalance, "joinPool后，gp用户不自动分得奖励"
        assert accLP2 == newAccLP
        assert accGP2 == newAccGP

        time.sleep(60)
        self.checkPendingPair(pairAddress)
        # 有可能不一致，如果先创建的pool进行了joinPool，再bindPair就有可能对不上
        assert poolSupply == curlp2, "pool中lp和pair中的lp不一致"

    def checkGPClaimPair(self, pairAddress, pool, poolAddress):
        pairContract = client.get_contract(pairAddress, "./abi/PairToken.json")
        start = pairContract.functions._poolLastRewardBlock().call()
        logger.info("_poolLastRewardBlock: {}".format(start))
        lp = pairContract.functions._totalLpSupply().call()
        logger.info(f"total lp: {lp}")
        accLP = pairContract.functions._poolAccPairPerShare().call()
        accGP = pairContract.functions._poolAccPairGpPerShare().call()
        uLPinfo = pairContract.functions.lpInfoList(client.account.address).call()
        uGPinfo = pairContract.functions.gpInfoList(GP_addr[0]).call()
        logger.info(f"{client.account.address} info: {uLPinfo}")
        logger.info(f"{SwapAccount2.address} info: {uGPinfo}")

        LpUserBalance = pairContract.functions.balanceOf(client.account.address).call()
        logger.info("lp user balance: {}".format(LpUserBalance))
        GpUserBalance = pairContract.functions.balanceOf(GP_addr[0]).call()
        logger.info("gp user Balance: {}".format(GpUserBalance))

        nonce = self.w3.eth.getTransactionCount(SwapAccount2.address)
        ex_func = pairContract.functions.claimPair(True, SwapAccount2.address)
        tx_hash = self.excuteTransaction(ex_func, nonce, SwapAccount2)
        tx_info = self.w3.eth.getTransactionReceipt(tx_hash)

        poolSupply = pool.functions.totalSupply().call()
        curlp2 = pairContract.functions._totalLpSupply().call()

        # 加入池子后，lp自动分得上一次的奖励，gp不分得奖励
        blockNum = tx_info["blockNumber"]
        changedBlock = blockNum - start
        logger.info("blockNumber: {}".format(blockNum))
        logger.info("changedBlock: {}".format(changedBlock))
        pendingGp = self.calPendingPairShare(changedBlock, uGPinfo, accGP, 1000, 15)
        newAccLP, newAccGP, lpShare, gpShare = self.calAccGPShare(changedBlock, accLP, accGP, lp, 1000, 15)
        time.sleep(3)
        accLP2 = pairContract.functions._poolAccPairPerShare().call()
        accGP2 = pairContract.functions._poolAccPairGpPerShare().call()

        LpUserBalance2 = pairContract.functions.balanceOf(client.account.address).call()
        logger.info("lp user balance: {}".format(LpUserBalance2))
        GpUserBalance2 = pairContract.functions.balanceOf(GP_addr[0]).call()
        logger.info("gp user Balance: {}".format(GpUserBalance2))

        assert poolSupply == curlp2, "pool中lp和pair中的lp不一致"

        assert LpUserBalance == LpUserBalance2, "joinPool，自动分得上一次的奖励"
        assert GpUserBalance + pendingGp == GpUserBalance2, "joinPool后，gp用户不自动分得奖励"
        assert accLP2 == newAccLP
        assert accGP2 == newAccGP

        time.sleep(60)
        self.checkPendingPair(pairAddress)


# 数据部分
# RPC_ADDRESS = 'https://ropsten.infura.io/v3/be5b825be13b4dda87056e6b073066dc'
# RPC_ADDRESS = 'https://mainnet.infura.io/v3/be5b825be13b4dda87056e6b073066dc'
RPC_ADDRESS = 'https://kovan.infura.io/v3/be5b825be13b4dda87056e6b073066dc'
# RPC_ADDRESS = 'wss://kovan.infura.io/ws/v3/be5b825be13b4dda87056e6b073066dc'
# RPC_ADDRESS = 'http://192.168.38.227:18045'

ERC20_testa = "0x9518Ef15EC4df3670b5FccE10C1863bE70a1e0f4"
ERC20_testb = "0x625D6686e4123d03354f8b321A436E7563EF26bc"

# ERC20_testa = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48" # usdt
# ERC20_testb = "0xdAC17F958D2ee523a2206206994597C13D831ec7" # usdc

# ERC20_testa = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2" # usdt
# ERC20_testb = "0xdAC17F958D2ee523a2206206994597C13D831ec7" # usdc

ERC20_testc = "0x39A90F019E6da0F86C0303Deb0246A39243ec798"
ERC20_usdt = "0x17C90B589eE9EAdAf81980BEB80f209d6E0b2b72"
# WETH = "0xFF5c8de422529eDD858BD4d9Ae7Dc64A203dB331"
WETH = "0x321a103BDB867C830a00F4409870A5B930943e28"
ETH = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"

# BFactory = "0x5D169a676C97c756F862b4903306d20492341092"
# BFactory = "0x35A86bE52D624df2c0f026A501386b06B89c797a"
# BFactory = "0xA0efe4a29526fc6B276430c7edF49b5Dc9B4B47C"
# BFactory = "0x90509EC7aB9C931e45b87901454E0E03fc59d160"
BFactory = "0x417C4D34b0C6DbCca59C193D071d1A86AE3009ed"
PairFactory = "0x15Fa84a6Ea9EbCA0F51F76f303a61C3e27d65931"
# PairFactory = "0x32583CE2878F0beb8E2A766f3704875D0De182B1"
# BAction_addr = "0x1ac73dfa4B7bf5d1AB1Af625b0e39292605832C0"
# BAction_addr = "0x080e7b5FA8B7787846B9F92EaEBE78ecFE3A0a75"
BAction_addr = "0x81eD447BE20723fb43a91667B1bA455a87fe6485"

dProxy_addr = "0x684D157724Ea52AFf22d32230A8d5dA214160b42"
dProxy2_addr = "0x47df9a365bcc08e9ea8c95fb37572edc6f3b88f6"
# exchangeProxy_addr = "0x380629cca126833696f8e23AA71FA6Abf982De20"
# exchangeProxy_addr = "0x5d798B1D03101De598bd8b98F61053aacc45738F"
# exchangeProxy_addr = "0xCdb7b06b262Fa49FF1a5A8b96ae47e448Cd04040"
exchangeProxy_addr = "0xFcA00e82Aa75c5e2306e4bfec0442096Ae5aC556"

# BMatchAddr = "0x76B07429bC6612ddc0aE66EA7Fe7EEC0c69A91A5"
BMatchAddr = "0xd8C0cee63944A5498BEDA0afD4758744b1f3278d"

etfAddr = "0x8a55B0a5042B3c908050d6B9faf326F46922BA2E"
AwardAddr = "0x010FA59Cf2ed89d94E79e1F560aCBB811129F8b4"

LPMiningAddr = "0xA53f7186dEE197D1c680EA835e11a2954CEEF8E4"
SwapMiningAddr = "0x3951A6d3a620276A3AfCefbFdd6113d161909e8D"

LPStakingAddr = "0xbdc6eDD52973E35ad4C78863cCf6014776B04782"

OracleAddr = "0xdA0fb4B71e81500E2BAd9416D823b8e5c4c6ebd1"

BAction_abi_file = "./abi/BAction.json"
dProxy_abi_file = "./abi/DSProxy.json"
exchangeProxy_abi_file = "./abi/ExchangeProxy.json"

PRIVATE_KEY = "ebed55a1f7e77144623167245abf39df053dc76fd8118ac7ae6e1ceeb84c5ed0"

GP_addr = ["0xBD8592ffFb1D031f27379550064bF2CA04F9C7Cc"]
GP_allocPoint = [1000]
GP_rate = 15

gasPrice = 1000000000  # 1gwei
# logger 的名字设置为'web3.RequestManager'是为了获取web3执行的日志信息
logger = setCustomLogger("web3.RequestManager", "test1.log", isprintsreen=True, level=logging.INFO)

if __name__ == "__main__":

    client = BActionTest(RPC_ADDRESS, PRIVATE_KEY)

    # 部署合约 BFactory, BAction,ExchangeProxy, 当合约代码更新时，需要在remix编译新的合约的json文件替换为新的
    # client.deploy_contract("./abi/BFactory.json")
    # client.deploy_contract(BAction_abi_file)
    # client.deploy_contract(exchangeProxy_abi_file, [WETH])

    BFactoryContract = client.get_contract(BFactory, "./abi/BFactory.json")
    # n = client.w3.eth.getTransactionCount(client.account.address)
    # e_func = BFactoryContract.functions.setFeeTo(GP_addr[0])
    # client.excuteTransaction(e_func, n)
    # client.approve("./abi/ERC20.json", [ERC20_testa, ERC20_testb], BAction_addr, client.account)
    # client.approve("./abi/ERC20.json", [ERC20_usdt], BAction_addr, client.account)
    # client.approve("./abi/ERC20.json", [ERC20_usdt], exchangeProxy_addr, client.account)
    # client.approve("./abi/WETH.json", [WETH], exchangeProxy_addr, client.account)
    # client.approve("./abi/WETH.json", [WETH], dProxy_addr, client.account)
    # client.approve("./abi/ERC20.json", [ERC20_testa, ERC20_testb], exchangeProxy_addr, client.account)
    # client.approve("./abi/ERC20.json", [ERC20_usdt], exchangeProxy_addr, client.account)
    # client.allowance("./abi/ERC20.json", [ERC20_testa, ERC20_testb], BAction_addr, client.account)
    # client.allowance("./abi/ERC20.json", [ERC20_usdt, WETH], exchangeProxy_addr, client.account)
    # poolAddr = client.checkBActionCreate([ERC20_testa, ERC20_testb])
    # poolAddr = client.checkBActionCreate([ERC20_testa, ERC20_usdt])
    # poolAddr = client.checkBActionCreateWithEth([ETH, ERC20_usdt])
    # poolAddr = client.checkBActionCreateWithEth([ETH, ERC20_usdt], True)
    # poolAddr = client.checkBActionCreate([ERC20_testb, ERC20_usdt])
    # poolAddr = client.checkBActionCreate([ERC20_testa, WETH])
    # poolAddr, pairAddr = client.checkBActionCreateWithPair(GP_addr, GP_allocPoint, GP_rate, [ERC20_testa, ERC20_testb])
    # poolAddr, pairAddr = client.checkBActionCreateWithPair(GP_addr, GP_allocPoint, GP_rate, [ERC20_testa, ERC20_usdt])
    # poolAddr = client.checkBActionCreateWithPairUseEth(GP_addr, GP_allocPoint, GP_rate, [ETH, ERC20_usdt])

    # 不带pair
    # poolAddr = "0x071aA3434270bA3bA115f6aE00b1cf15b34e243A"   # testa testb
    poolAddr = "0x7932Cf91622E080dbFF893E603c40E8c7C24Ffac"   # weth dai
    # poolAddr2 = "0xc5b822AF7298E30cDf69B226C52524434459d58a"  # ERC20_testa, ERC20_usdt
    poolAddr2 = "0xd3Dc732E867800c78C6E6685746608abdE7C85F2"  # dai, usdc
    # poolAddr3 = "0x857d04E3B85483cd8e757db994bBD1cD385ca92E"  # ETH, ERC20_usdt
    poolAddr3 = "0x1286fb03b7d91CF4c4f0C3d38C56163779319266"  # ETH, ERC20_usdt
    pairAddr = "0xebaA8bfC1B2a89EE129Cc170A3873F37F3eEcF81"
    # 带pair
    # poolAddr = "0x5cF2f9F4CD248616fdF55133320020f93A380B3D"  # testa testb
    # poolAddr2 = "0xAa13e2a3C80959548C9Da2bc868bC6a8D07e49aD"  # ERC20_testa, ERC20_usdt
    # poolAddr3 = "0x33f41d582fa031138b017247080ccea078fe7792"  # ETH, ERC20_usdt

    # pairAddr = "0x00c49A6d652eC794bB014256051c8304274D7643"
    pairAddr2 = "0x18aD4853bBC9C1DB49eb06792ae04080b3E1d706"
    pairAddr3 = "0xE08a37EAB18162Eb7b4A2c6A5B1180462661D938"

    poolContract = client.get_contract(client.w3.toChecksumAddress(poolAddr), "./abi/BPool.json")
    poolContract2 = client.get_contract(client.w3.toChecksumAddress(poolAddr2), "./abi/BPool.json")
    poolContract3 = client.get_contract(client.w3.toChecksumAddress(poolAddr3), "./abi/BPool.json")

    wethContract = client.get_contract(client.w3.toChecksumAddress(WETH), "./abi/WETH.json")
    # print(wethContract.all_functions())
    # print(wethContract.functions.balanceOf(client.account.address).call())

    # print(poolContract.all_functions())
    # print(poolContract.functions.getCurrentTokens().call())
    account2_private_key = "ad246d5896fd96c40595ff58e6e2a8bd23ffb31e95b1fb786a9034d2df120492"
    SwapAccount2 = client.w3.eth.account.privateKeyToAccount(account2_private_key)
    # client.approve("./abi/ERC20.json", [ERC20_testa, ERC20_testb], exchangeProxy_addr, SwapAccount2)

    BMath = client.get_contract(BMatchAddr, "./abi/BMath.json")
    # print(client.w3.toWei(0.0001, "ether"))
    # client.checkJoinPool(poolContract, poolAddr, SwapAccount2)
    # client.checkJoinPool(poolContract, poolAddr)
    # client.checkJoinPool(poolContract2, poolAddr2)
    # client.checkJoinPool(poolContract3, poolAddr3)
    # client.checkJoinPoolWithEth(poolContract3, poolAddr3)
    # client.checkJoinPoolWhenAmountInLessThanRequireAmount(poolContract, poolAddr)
    # client.checkJoinPoolWhenUserTokenBalanceNotEnough(poolContract, poolAddr, SwapAccount2)
    # #client.checkJoinSwapExternAmountIn(poolContract, poolAddr, ERC20_testa) # 新版没有了

    # # 交易
    weth = "0xd0A1E359811322d97991E03f863a0C30C2cF029C"
    dai = "0x1528F3FCc26d13F7079325Fb78D9442607781c8C"
    usdc = "0x2F375e94FC336Cdec2Dc0cCB5277FE59CBf1cAe5"
    zrx = "0xccb0F4Cf5D3F97f4a55bb5f5cA321C3ED033f244"
    ant = "0x37f03a12241E9FD3658ad6777d289c3fb8512Bc9"
    # client.checkSwapExactAmountIn(poolContract, poolAddr, weth, dai)
    # client.checkSwapExactAmountIn(poolContract2, poolAddr2, dai, usdc)
    # client.checkSwapExactAmountIn(poolContract, poolAddr, ERC20_testa, ERC20_testb)
    # client.checkSwapExactAmountIn(poolContract, poolAddr, ERC20_testb, ERC20_testa)
    # client.checkSwapExactAmountIn(poolContract2, poolAddr2, ERC20_testa, ERC20_usdt)
    # client.checkSwapExactAmountIn(poolContract3, poolAddr3, ERC20_usdt, WETH)
    # print(wethContract.all_functions())

    # 转换weth
    # d_nonce = client.w3.eth.getTransactionCount(client.account.address)
    # d_func = wethContract.functions.deposit()
    # client.excuteTransaction(d_func, d_nonce, client.account, value=client.w3.toWei(0.001, "ether"))
    # client.checkSwapExactAmountIn(poolContract3, poolAddr3, WETH, ERC20_usdt)
    # client.checkSwapExactAmountInWithETH(poolContract3, poolAddr3, ERC20_usdt, ETH)
    # client.checkSwapExactAmountInWithETH(poolContract3, poolAddr3, ETH, ERC20_usdt, client.calBalance(0.0001, 18))
    # client.checkSwapExactAmountInWithETH(poolContract3, poolAddr3, ETH, ERC20_usdt, client.calBalance(0.0001, 18), True)

    # client.checkMultihopBatchSwapExactIn([poolAddr], [ERC20_testb], [ERC20_testa])
    # client.checkMultihopBatchSwapExactIn([poolAddr2], [ERC20_testa], [ERC20_usdt])
    # client.checkMultihopBatchSwapExactIn([poolAddr, poolAddr2], [weth, dai], [dai, usdc])
    # client.checkMultihopBatchSwapExactIn([poolAddr, poolAddr2], [ERC20_testb, ERC20_testa], [ERC20_testa, ERC20_usdt])
    # client.checkMultihopBatchSwapExactIn([poolAddr, poolAddr2, poolAddr3], [ERC20_testb, ERC20_testa, ERC20_usdt],[ERC20_testa, ERC20_usdt, WETH])
    # client.checkMultihopBatchSwapExactInWithEth([poolAddr3], [ERC20_usdt], [WETH], ERC20_usdt, ETH, client.calBalance(1, 6))
    # client.checkMultihopBatchSwapExactInWithEth([poolAddr3], [WETH], [ERC20_usdt], ETH, ERC20_usdt, client.calBalance(0.0001, 18))
    # client.checkMultihopBatchSwapExactInWithEth([poolAddr3], [WETH], [ERC20_usdt], ETH, ERC20_usdt, client.calBalance(0.0001, 18), True)
    # client.checkMultihopBatchSwapExactInWithEth([poolAddr2, poolAddr3], [ERC20_testa, ERC20_usdt], [ERC20_usdt, WETH], ERC20_testa, ETH, client.calBalance(1, 18))
    # client.checkMultihopBatchSwapExactInWithEth([poolAddr3, poolAddr2], [WETH, ERC20_usdt], [ERC20_usdt, ERC20_testa], ETH, ERC20_testa, client.calBalance(0.0001, 18))
    # client.checkMultihopBatchSwapExactInWithEth([poolAddr3, poolAddr2], [WETH, ERC20_usdt], [ERC20_usdt, ERC20_testa], ETH, ERC20_testa, client.calBalance(0.0001, 18), True)
    # client.checkMultihopBatchSwapExactInWithEth([poolAddr, poolAddr2, poolAddr3], [ERC20_testb, ERC20_testa, ERC20_usdt], [ERC20_testa, ERC20_usdt, WETH], ERC20_testb, ETH, client.calBalance(1, 18))
    # client.checkMultihopBatchSwapExactInWithEth([poolAddr3, poolAddr2, poolAddr], [WETH, ERC20_usdt, ERC20_testa], [ERC20_usdt, ERC20_testa, ERC20_testb], ETH, ERC20_testb, client.calBalance(0.0001, 18))

    # client.checkGetAmountsInWhenSwapExactAmountOut(poolContract, poolAddr, ERC20_testa, ERC20_testb)

    # client.checkSwapExactAmountIn(poolContract, poolAddr, weth, dai)
    # client.checkSwapExactAmountIn(poolContract2, poolAddr2, dai, usdc)

    # client.checkSwapExactAmountOut(poolContract, poolAddr, weth, zrx)
    # client.checkMultihopBatchSwapExactOut([poolAddr, poolAddr2], [weth, dai], [dai, usdc])
    # client.checkMultihopBatchSwapExactOut([poolAddr, poolAddr2, poolAddr3], [weth, dai, usdc], [dai, usdc, ant])
    # client.checkSwapExactAmountOut(poolContract, poolAddr, ERC20_testa, ERC20_testb)

    # client.checkSwapExactAmountOut(poolContract, poolAddr, ERC20_testa, ERC20_testb)
    # client.checkSwapExactAmountOut(poolContract, poolAddr, ERC20_testb, ERC20_testa)
    # client.checkSwapExactAmountOut(poolContract3, poolAddr3, ERC20_usdt, WETH)
    # client.checkSwapExactAmountOut(poolContract3, poolAddr3, WETH, ERC20_usdt)
    # client.checkSwapExactAmountOutWithETH(poolContract3, poolAddr3, ERC20_usdt, ETH)
    # client.checkSwapExactAmountOutWithETH(poolContract3, poolAddr3, ETH, ERC20_usdt)
    # client.checkSwapExactAmountOutWithETH(poolContract3, poolAddr3, ETH, ERC20_usdt, client.calBalance(0.1, 6), True)
    # client.checkMultihopBatchSwapExactOut([poolAddr], [ERC20_testb], [ERC20_testa])
    # client.checkMultihopBatchSwapExactOut([poolAddr, poolAddr2], [ERC20_testb, ERC20_testa], [ERC20_testa, ERC20_usdt])
    # client.checkMultihopBatchSwapExactOut([poolAddr, poolAddr2, poolAddr3], [ERC20_testb, ERC20_testa, ERC20_usdt], [ERC20_testa, ERC20_usdt, WETH])
    # client.checkMultihopBatchSwapExactOutWithEth([poolAddr3], [ERC20_usdt], [WETH], ERC20_usdt, ETH, client.calBalance(0.0001, 18))
    # client.checkMultihopBatchSwapExactOutWithEth([poolAddr3], [WETH], [ERC20_usdt], ETH, ERC20_usdt, client.calBalance(1, 6))
    # client.checkMultihopBatchSwapExactOutWithEth([poolAddr2, poolAddr3], [ERC20_testa, ERC20_usdt], [ERC20_usdt, WETH], ERC20_testa, ETH, client.calBalance(0.001, 18))
    # client.checkMultihopBatchSwapExactOutWithEth([poolAddr3, poolAddr2], [WETH, ERC20_usdt], [ERC20_usdt, ERC20_testa], ETH, ERC20_testa, client.calBalance(1, 18))
    # client.checkMultihopBatchSwapExactOutWithEth([poolAddr3, poolAddr2], [WETH, ERC20_usdt], [ERC20_usdt, ERC20_testa], ETH, ERC20_testa, client.calBalance(1, 18), True)
    # client.checkMultihopBatchSwapExactOutWithEth([poolAddr, poolAddr2, poolAddr3], [ERC20_testb, ERC20_testa, ERC20_usdt], [ERC20_testa, ERC20_usdt, WETH], ERC20_testb, ETH, client.calBalance(0.001, 18))
    # client.checkMultihopBatchSwapExactOutWithEth([poolAddr3, poolAddr2, poolAddr],[WETH, ERC20_usdt, ERC20_testa], [ERC20_usdt, ERC20_testa, ERC20_testb], ETH, ERC20_testb, client.calBalance(1, 18))
    # client.checkMultihopBatchSwapExactOutWithEth([poolAddr3, poolAddr2, poolAddr],[WETH, ERC20_usdt, ERC20_testa], [ERC20_usdt, ERC20_testa, ERC20_testb], ETH, ERC20_testb, client.calBalance(1, 18), True)

    # client.checkExitPool(poolContract, poolAddr, False)
    # client.checkExitPool(poolContract2, poolAddr2, False)
    # client.checkExitPool(poolContract3, poolAddr3, False)
    # client.checkExitPool(poolContract, poolAddr, True)

    # client.checkExitSwapPoolAmountIn(poolContract, ERC20_testa, False) # 新版没有了

    # # Pair相关的校验
    # client.checkBindPair(poolContract, poolAddr)
    # client.checkPendingPair(pairAddr)
    # client.checkJoinPoolSharePair(pairAddr, poolContract, poolAddr)
    # client.checkExitPoolSharePair(pairAddr, poolContract, poolAddr)
    # client.checkLPClaimPair(pairAddr, poolContract, poolAddr)
    # client.checkGPClaimPair(pairAddr, poolContract, poolAddr)

    # # TODO 以下的为未整理的
    # 测试LPMining挖矿, 提前设置好权限和认证池子
    OracleContract = client.get_contract(OracleAddr, "./abi/PriceOracle.json")
    awardContract = client.get_contract(AwardAddr, "./abi/AwardContract.json")
    LPMiningContract = client.get_contract(LPMiningAddr, "./abi/LPMiningV1.json")
    # print(LPMiningContract.all_functions())
    # client.checkLPMingClaimUserShares(LPMiningContract, poolAddr)
    # client.checkLPMingJoinPool(LPMiningContract, poolAddr)
    # client.checkLPMingJoinSwapExternAmountIn(LPMiningContract, poolAddr)
    # client.checkLPMingExitPool(LPMiningContract, poolAddr)
    # client.checkLPMingExitSwapPoolAmountIn(LPMiningContract, poolAddr, ERC20_testa)
    # client.checkLPMingSet(LPMiningContract, poolAddr)
    # account2 = client.w3.toChecksumAddress("0xBD8592ffFb1D031f27379550064bF2CA04F9C7Cc")
    # client.checkLPMingLPTransferFrom(LPMiningContract, poolAddr, account2)
    # client.checkLPMingLPTransfer(LPMiningContract, poolAddr, account2)
    # a = 55585501946669397453
    # b = 30172805345347762825
    # print(a - b)
    # print(183057279858491605045 - 157641281371313923274 - 3303537624859573 + 1651768812430)
    # print(29912235307115333896 - 29908931769490474323)
    # print(42879153646008580139 - b)
    # print((42879153646008580139 - b))
    a = client.w3.eth.getBlock('latest').timestamp
    print(a)
    # print(a + 700)
    # print(a + 700 - 8*3600)
    print(a + 5 * 3600)
    print(a + 24*3600)
    print(a + 10 * 24*3600)
    print(int(1e18))
    # b = 648528072794097136211887414641905 * 2**56
    # c = 13436578056918011776847953283351 // 2**56
    # print()
    # print(b // c)
    lpPrice = 257158878847843586097457856783754370
    buyAmount = 100
    lpAmount = buyAmount * 2**112 /lpPrice
    print(lpAmount)
    lpPrice2 = 256507443180795017565544723225662794
    lpValue = lpPrice2 * 2 / 2**112
    print(lpValue)
    # 测试SwapMing挖矿
    # SwapMingContract = client.get_contract(SwapMiningAddr, "./abi/SwapMining.json")
    # client.checkSwapMingSwapIn(poolContract, poolAddr, ERC20_testa, ERC20_testb)
    # client.checkSwapMingSwapOut(poolContract, poolAddr, ERC20_testa, ERC20_testb)

    # print(SwapAccount2.address)
    # client.getSwapMingInfo(SwapMingContract)
    # client.calSwapShare(SwapMingContract, client.account.address)
    # client.calSwapShare(SwapMingContract, SwapAccount2.address)
    # 123456789, 100000000000000000000000000
    # print(4877593122589589900 * 10000000000000000000000 * 123456789//100000000000000000000000000)
    # vol = 4877593122589589900 * 10000000000000000000000 * 123456789//100000000000000000000000000
    # print(vol)
    # print(vol + 318832062130024472974884)
    # print(318832062130024472974884 * 318832062130024472974884)
    # print(176812091511253382988500 + 318832062130024472974884)

    # poolInfo = LPMiningContract.functions.poolInfo(poolAddr).call()
    # poolInfo = dict(bPool=poolInfo[0], poolIndex=poolInfo[1], referIndex=poolInfo[2], allocPoint=poolInfo[3],
    #                 lastTvl=poolInfo[4], accTokenPerShare=poolInfo[5], rewardDebt=poolInfo[6])
    # tvl = client.calTvl(poolContract, poolInfo)
    # print(tvl)
    # poolInfo = LPMiningContract.functions.poolInfo("0x0aa7240EaE23473ab1e3c4D49Cf7e07BB8d610AA").call()
    # print(poolInfo)
    # poolInfo = dict(bPool=poolInfo[0], poolIndex=poolInfo[1], referIndex=poolInfo[2], allocPoint=poolInfo[3],
    #                 lastTvl=poolInfo[4], accTokenPerShare=poolInfo[5], rewardDebt=poolInfo[6])
    #
    # tvl = client.calTvl(poolContract, poolInfo)
    # print(tvl)
    # client
    # AvailAwards = awardContract.functions.getUserAvailAwards(client.account.address).call()
    # print("getUserAvailAwards", awardContract.functions.getUserAvailAwards(client.account.address).call())
    # print("getUserTotalAwards", awardContract.functions.getUserTotalAwards(client.account.address).call())
    #
    # for i in range(9):
    #     print(awardContract.functions.getTaxInfo(client.account.address, i).call())

    from eth_abi import encode_abi, encode_single

    a = encode_single("(address)", ["0x1084d79A66EF86BFc9c945d4a21159a024dEE14e"])
    b = encode_abi(["address", "bool"], ["0xeD24FC36d5Ee211Ea25A80239Fb8C4Cfd80f12Ee", True])
    # print(b)
    print(client.w3.toHex(a))
    print(client.w3.toHex(b))
