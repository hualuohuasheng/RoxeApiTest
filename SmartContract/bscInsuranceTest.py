from SmartContract.CommonTool import load_from_json_file
from roxe_libs.pub_function import setCustomLogger
from web3 import Web3, HTTPProvider
from web3.contract import build_transaction_for_function
import logging
import requests
import json
import time


def findFunctionByNameFromContractAbi(funcName, contractAbi):
    for abi in contractAbi:
        # print(abi)
        if "name" in abi.keys() and abi["name"] == funcName:
            return abi


class BSCClient:

    def __init__(self, rpc_url, private_key):
        self.rpc_url = rpc_url
        self.web3 = Web3(HTTPProvider(rpc_url, request_kwargs={'timeout': 120}))
        logger.info("web3 connect status: {}".format(self.web3.isConnected()))
        self.account = self.web3.eth.account.privateKeyToAccount(private_key)

    def sendPostRequest(self, method, bscId, params=None):
        if params is None:
            params = []
        dataBody = {"jsonrpc": "2.0", "method": method, "params": params, "id": bscId}
        header = {"Content-Type": "application/json"}
        res = requests.post(self.rpc_url, data=json.dumps(dataBody), headers=header)
        if "error" not in res.json():
            return res.json()["result"]
        else:
            return res.json()

    def gasPrice(self):
        gasPrice = self.sendPostRequest("eth_gasPrice", 73)
        return gasPrice

    def accounts(self):
        return self.sendPostRequest("eth_accounts", 1)

    def blockNumber(self):
        blockNum = self.sendPostRequest("eth_blockNumber", 83)
        return int(blockNum, 16)

    def getBalance(self, address):
        balance = self.sendPostRequest("eth_getBalance", 1, [address, "latest"])
        return int(balance, 16)

    def getTransactionCount(self, address):
        count = self.sendPostRequest("eth_getTransactionCount", 1, [address, "latest"])
        return int(count, 16)

    def getBlockTransactionCountByHash(self, txhash):
        txInfo = self.sendPostRequest("eth_getBlockTransactionCountByHash", 1, [txhash])
        return txInfo

    def sendTransaction(self, transaction):
        res = self.sendPostRequest("eth_sendTransaction", 1, [transaction])
        return res

    def sendRawTransaction(self, data):
        return self.sendPostRequest("eth_sendRawTransaction", 1, [data])

    def call(self, toAddr, callData):
        params = [{
            "to": toAddr,
            "data": callData
        }, "latest"]
        return self.sendPostRequest("eth_call", 1, params)

    def estimateGas(self, transaction):
        return self.sendPostRequest("eth_estimateGas", 1, [transaction])

    def getTransactionReceipt(self, txHash):
        return self.sendPostRequest("eth_getTransactionReceipt", 1, [txHash])

    def waitForTransactionReceipt(self, transaction_hash, waitStep=0.2):
        while True:
            txn_receipt = self.getTransactionReceipt(transaction_hash)
            if txn_receipt is not None and txn_receipt['blockHash'] is not None:
                break
            time.sleep(waitStep)
        return txn_receipt

    def excuteTransaction(self, account, transaction):
        singedTx = account.signTransaction(transaction)
        tx_hash = self.sendRawTransaction(self.web3.toHex(singedTx.rawTransaction))
        logger.info('{} waiting for receipt..'.format(tx_hash))
        txReceipt = self.waitForTransactionReceipt(tx_hash)
        logger.info("Receipt accepted: ".format(txReceipt))

    def callFuncUseGas(self, contractAddr, contractAbi, fromAccount, funcName, args, value=None, isExcute=True):
        functionAbi = findFunctionByNameFromContractAbi(funcName, contractAbi)
        tx = {
            "from": fromAccount.address,
            "to": contractAddr,
            # "gasPrice": self.gasPrice(),
            "gasPrice": hex(20000000000),
            "nonce": self.getTransactionCount(fromAccount.address)
        }
        if value:
            tx["value"] = self.web3.toHex(value)
        t = build_transaction_for_function(contractAddr, self.web3, funcName, tx, contractAbi, functionAbi, *args)
        tx["data"] = t["data"]
        # tx['data'] = "0x538fa97c000000000000000000000000645e611dc68834b773edf5a98296b5abc35c170a000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000a000000000000000000000000000000000000000000000000000000000000000e00000000000000000000000000000000000000000000000000000000060c1c124000000000000000000000000000000000000000000000000000000000000001c736574537461626c65546f6b656e28616464726573732c626f6f6c29000000000000000000000000000000000000000000000000000000000000000000000040000000000000000000000000ed24fc36d5ee211ea25a80239fb8c4cfd80f12ee0000000000000000000000000000000000000000000000000000000000000001"
        logger.info("得到合约的call data: {}".format(tx["data"]))

        tx["gas"] = self.estimateGas(tx)
        if isExcute:
            self.excuteTransaction(fromAccount, tx)

    def callFunc(self, contractAddr, contractAbi, funcName, funcArgs, isCover=False):
        functionAbi = findFunctionByNameFromContractAbi(funcName, contractAbi)
        tx = {"to": contractAddr}
        t = build_transaction_for_function(contractAddr, self.web3, funcName, tx, contractAbi, functionAbi,
                                           *funcArgs)
        # logger.info("得到合约的call data: {}".format(t["data"]))

        res = self.call(contractAddr, t["data"])
        if isCover:
            if len(res) > 66:
                preInfo = res[0:2]
                tmpInfo = res[2::]
                tmpInfos = [tmpInfo[i:i+64] for i in range(0, len(res[2::]), 64)]
                parseInfo = []
                for i in tmpInfos:
                    parseInfo.append(int(preInfo + i, 16))
                return parseInfo
            else:
                return int(res, 16)
        return res


class InsuanceTest:

    def __init__(self, contractAddr, contractABI, callClient: BSCClient):
        self.contractAddr = contractAddr
        self.contractABI = contractABI
        self.client = callClient

    def testSell(self, account, marketId, rate, amount, orderIndex, tokenAddr, tokenABI):

        # if tokenAddr == wbnb:
        #     tokenAmount = self.client.getBalance(account.address)
        # else:
        tokenAmount = self.client.callFunc(tokenAddr, tokenABI, "balanceOf", (account.address,), True)
        lpAmount = client.callFunc(pancakePair, pairABI, "balanceOf", (account.address,), True)

        logger.info("创建sell订单之前数据: ")
        logger.info("token Amount: {}".format(tokenAmount))
        logger.info("lp Amount: {}".format(lpAmount))

        logger.info("准备进行sell 订单")
        # valaue = None if tokenAddr != wbnb else amount
        # self.client.callFuncUseGas(self.contractAddr, self.contractABI, account, "sell", (marketId, rate, amount))
        # if tokenAddr == wbnb:
        #     tokenAmount2 = self.client.getBalance(account.address)
        # else:
        tokenAmount2 = client.callFunc(tokenAddr, tokenABI, "balanceOf", (account.address,), True)
        lpAmount2 = client.callFunc(pancakePair, pairABI, "balanceOf", (account.address,), True)
        orderMap = self.client.callFunc(self.contractAddr, self.contractABI, "orderMap", (marketId, account.address, orderIndex, ), True)
        logger.info("订单信息: {}".format(orderMap))

        logger.info("创建sell订单之后数据: ")
        logger.info("token Amount: {}".format(tokenAmount2))
        logger.info("lp Amount: {}".format(lpAmount2))

        assert lpAmount2 == lpAmount, "lpAmount 不一致"
        assert tokenAmount - tokenAmount2 == amount, "sell 订单时，转入合约中的token数量不一致"

        assert rate == orderMap[0], "orderMap rate信息不正确"
        assert amount == orderMap[1], "orderMap amount信息不正确"

    def calBuyAmount(self, marketId, amount, isUpper=False):
        n = 1
        while True:
            perLpValue = self.client.callFunc(self.contractAddr, self.contractABI, "estimateBaseTokenAmount", (marketId, n), True)
            if perLpValue > 0:
                break
            n += 1
        lpAmount = n * amount / perLpValue

        buyAmount = int(lpAmount) + 1 if isUpper else int(lpAmount)
        buyValue = self.client.callFunc(self.contractAddr, self.contractABI, "estimateBaseTokenAmount", (marketId, buyAmount), True)
        return buyAmount, buyValue

    def testBuy(self, account, marketId, seller, orderIndex, amount, buyIndex, tokenAddr, tokenABI):

        tokenAmount = self.client.callFunc(tokenAddr, tokenABI, "balanceOf", (account.address,), True)
        lpAmount = self.client.callFunc(pancakePair, pairABI, "balanceOf", (account.address,), True)

        logger.info("创建buy订单之前数据: ")
        logger.info("token Amount: {}".format(tokenAmount))
        logger.info("lp Amount: {}".format(lpAmount))

        orderMap = self.client.callFunc(self.contractAddr, self.contractABI, "orderMap", (marketId, seller, orderIndex,), True)
        logger.info("订单信息: {}".format(orderMap))

        try:
            self.client.callFunc(self.contractAddr, self.contractABI, "buyerPolicyMap", (marketId, account.address, buyIndex,), True)
        except Exception as e:
            assert e.args[0]["message"] == "invalid opcode: opcode 0xfe not defined", "buyerPolicyMap应该为空"

        buyLp, buyLpValue = self.calBuyAmount(marketId, amount)
        logger.info("准备购买价值为{}，可以买到:{}, 实际价值: {}".format(amount, buyLp, buyLpValue))

        feeTo = hex(self.client.callFunc(self.contractAddr, self.contractABI, "feeTo", (), True))
        logger.info("feeTo: {}".format(feeTo))
        fee = amount * orderMap[0] // 10000
        logger.info("总计费用: {}".format(fee))
        platformFee = 0

        feeToBalance, feeToBalance2 = 0, 0

        if feeTo != "0x0000000000000000000000000000000000000000" and feeTo != "0x0":
            platformFeeRate = self.client.callFunc(self.contractAddr, self.contractABI, "platformFeeRate", (), True)
            logger.info("platformFeeRate: {}".format(platformFeeRate))
            platformFee = fee * platformFeeRate // 10000
            feeToBalance = self.client.callFunc(tokenAddr, tokenABI, "balanceOf", (self.client.web3.toChecksumAddress(feeTo),), True)
            fee -= platformFee
            logger.info("平台收费: {}".format(platformFee))
            logger.info("平台feeTo账户资产: {}".format(feeToBalance))
        logger.info("预计收费: {}".format(fee))
        logger.info("准备进行buy订单")
        self.client.callFuncUseGas(self.contractAddr, self.contractABI, account, "buy", (marketId, seller, orderIndex, amount, buyLp))

        tokenAmount2 = client.callFunc(tokenAddr, tokenABI, "balanceOf", (account.address,), True)
        lpAmount2 = client.callFunc(pancakePair, pairABI, "balanceOf", (account.address,), True)
        buyerPolicyMap = self.client.callFunc(self.contractAddr, self.contractABI, "buyerPolicyMap", (marketId, account.address, buyIndex, ), True)
        logger.info("buyerPolicyMap: {}".format(buyerPolicyMap))
        orderMap2 = self.client.callFunc(self.contractAddr, self.contractABI, "orderMap", (marketId, seller, orderIndex,), True)
        logger.info("订单信息: {}".format(orderMap2))
        if platformFee > 0:
            feeToBalance2 = self.client.callFunc(tokenAddr, tokenABI, "balanceOf", (self.client.web3.toChecksumAddress(feeTo),), True)
            logger.info("平台feeTo账户资产: {}".format(feeToBalance2))
        logger.info("token Amount: {}".format(tokenAmount2))
        logger.info("lp Amount: {}".format(lpAmount2))

        assert lpAmount - lpAmount2 == buyLp, "lpAmount 不一致"
        assert tokenAmount - tokenAmount2 == fee + platformFee, "buy 订单时，投保人转出的token数量不一致"
        assert orderMap[1] - orderMap2[1] == amount, "orderMap中的数量不正确"
        assert orderMap[0] == orderMap2[0], "orderMap中的rate不正确"

        assert buyerPolicyMap[0] == fee + platformFee, "premium不正确"
        # assert self.client.web3.toChecksumAddress(hex(buyerPolicyMap[1])) == account.address, "buyer不正确，{} {}".format(hex(buyerPolicyMap[1]), account.address)
        # assert self.client.web3.toChecksumAddress(hex(buyerPolicyMap[2])) == seller, "seller不正确: {} {}".format(hex(buyerPolicyMap[2]), seller)
        assert buyerPolicyMap[3] == amount, "stakeAmount不正确"
        assert buyerPolicyMap[4] == buyLp, "lpAmount不正确"

        assert buyerPolicyMap[6] == 0, "claimed不正确"

        if platformFee > 0:
            if seller == self.client.web3.toChecksumAddress(feeTo):
                assert feeToBalance2 - feeToBalance == platformFee + fee, "平台收费不正确"
            else:
                assert feeToBalance2 - feeToBalance == platformFee, "平台收费不正确"

        assert buyerPolicyMap[5] == buyLpValue, "lpValue不正确"

    def testChangeOrCancelOrder(self, fromAccount, marketId, orderIndex, amount, tokenAddr, tokenABI):
        orderMap = self.client.callFunc(self.contractAddr, self.contractABI, "orderMap",
                                        (marketId, fromAccount.address, orderIndex,), True)
        tokenAmount = self.client.callFunc(tokenAddr, tokenABI, "balanceOf", (fromAccount.address,), True)

        logger.info("change订单之前数据: ")
        logger.info("订单信息: {}".format(orderMap))
        logger.info("token Amount: {}".format(tokenAmount))

        expectChange = abs(orderMap[1] - amount)
        logger.info("准备进行change订单")
        self.client.callFuncUseGas(self.contractAddr, self.contractABI, fromAccount, "changeOrCancel",
                                   (marketId, orderIndex, amount))

        orderMap2 = self.client.callFunc(self.contractAddr, self.contractABI, "orderMap", (marketId, fromAccount.address, orderIndex,), True)
        tokenAmount2 = client.callFunc(tokenAddr, tokenABI, "balanceOf", (fromAccount.address,), True)

        logger.info("change订单之后数据: ")
        logger.info("订单信息: {}".format(orderMap2))
        logger.info("token Amount: {}, 变化了{}".format(tokenAmount2, tokenAmount2-tokenAmount))
        assert orderMap2[0] == orderMap[0], "ordermap rate不正确"
        assert orderMap2[1] == amount, "ordermap amount不正确"

        assert expectChange == abs(tokenAmount2 - tokenAmount), "seller tokenAmount 不正确"

    def testClaim(self, fromAccount, marketId, buyIndex, tokenAddr, tokenABI):
        policyMap = self.client.callFunc(self.contractAddr, self.contractABI, "buyerPolicyMap", (marketId, fromAccount.address, buyIndex,), True)
        sellerAddr = self.client.web3.toChecksumAddress(hex(policyMap[2]))
        buyerTokenAmount = self.client.callFunc(tokenAddr, tokenABI, "balanceOf", (fromAccount.address,), True)
        sellerTokenAmount = self.client.callFunc(tokenAddr, tokenABI, "balanceOf", (sellerAddr,), True)
        buyerLP = self.client.callFunc(pancakePair, pairABI, "balanceOf", (fromAccount.address, ), True)
        sellerLP = self.client.callFunc(pancakePair, pairABI, "balanceOf", (sellerAddr, ), True)

        logger.info("claim之前数据: ")
        logger.info("订单信息: {}".format(policyMap))
        logger.info("buyer lp: {}".format(buyerLP))
        logger.info("seller lp: {}".format(sellerLP))
        logger.info("buyer token Amount: {}".format(buyerTokenAmount))
        logger.info("seller token Amount: {}".format(sellerTokenAmount))
        curLpValue = self.client.callFunc(self.contractAddr, self.contractABI, "estimateBaseTokenAmount",
                                          (1, policyMap[4],), True)
        logger.info("curLp value: {}".format(curLpValue))

        toPayAmount = 0
        if curLpValue < policyMap[5]:
            toPayAmount = (policyMap[5] - curLpValue) * 70 // 100
        logger.info("应该赔付的金额: {}".format(toPayAmount))
        self.client.callFuncUseGas(self.contractAddr, self.contractABI, fromAccount, "claim", (marketId, buyIndex, ))

        policyMap2 = self.client.callFunc(self.contractAddr, self.contractABI, "buyerPolicyMap", (marketId, fromAccount.address, buyIndex,), True)
        buyerTokenAmount2 = self.client.callFunc(tokenAddr, tokenABI, "balanceOf", (fromAccount.address,), True)
        sellerTokenAmount2 = self.client.callFunc(tokenAddr, tokenABI, "balanceOf", (sellerAddr,), True)
        buyerLP2 = self.client.callFunc(pancakePair, pairABI, "balanceOf", (fromAccount.address,), True)
        sellerLP2 = self.client.callFunc(pancakePair, pairABI, "balanceOf", (sellerAddr,), True)

        logger.info("claim之后数据: ")
        logger.info("订单信息: {}".format(policyMap2))
        logger.info("buyer lp: {}, changed: {}".format(buyerLP2, buyerLP2 - buyerLP))
        logger.info("seller lp: {}, changed: {}".format(sellerLP2, sellerLP2 - sellerLP))
        logger.info("buyer token Amount: {}, changed: {}".format(buyerTokenAmount2, buyerTokenAmount2 - buyerTokenAmount))
        logger.info("seller token Amount: {}, changed: {}".format(sellerTokenAmount2, sellerTokenAmount2 - sellerTokenAmount))

        assert buyerLP2 - buyerLP == policyMap[4], "buyer lp 应该全额退回"
        assert sellerLP == sellerLP2, "seller lp 应该不变"
        assert buyerTokenAmount2 - buyerTokenAmount == toPayAmount, "buyer 赔付不正确"
        assert sellerTokenAmount2 - sellerTokenAmount == policyMap[3] - toPayAmount, "seller获取返回的资金不正确"

    def testRefund(self, fromAccount, marketId, sellIndex, tokenAddr, tokenABI):
        policyMap = self.client.callFunc(self.contractAddr, self.contractABI, "sellerPolicyMap", (marketId, fromAccount.address, sellIndex,), True)
        buyerAddr = self.client.web3.toChecksumAddress(hex(policyMap[1]))
        buyerTokenAmount = self.client.callFunc(tokenAddr, tokenABI, "balanceOf", (buyerAddr,), True)
        sellerTokenAmount = self.client.callFunc(tokenAddr, tokenABI, "balanceOf", (fromAccount.address,), True)
        buyerLP = self.client.callFunc(pancakePair, pairABI, "balanceOf", (buyerAddr, ), True)
        sellerLP = self.client.callFunc(pancakePair, pairABI, "balanceOf", (fromAccount.address, ), True)

        logger.info("claim之前数据: ")
        logger.info("订单信息: {}".format(policyMap))
        logger.info("buyer lp: {}".format(buyerLP))
        logger.info("seller lp: {}".format(sellerLP))
        logger.info("buyer token Amount: {}".format(buyerTokenAmount))
        logger.info("seller token Amount: {}".format(sellerTokenAmount))
        curLpValue = self.client.callFunc(self.contractAddr, self.contractABI, "estimateBaseTokenAmount",
                                          (marketId, policyMap[4],), True)
        logger.info("curLp value: {}".format(curLpValue))

        toPayAmount = 0
        if curLpValue < policyMap[5]:
            toPayAmount = (policyMap[5] - curLpValue) * 70 // 100
        logger.info("应该赔付的金额: {}".format(toPayAmount))
        self.client.callFuncUseGas(self.contractAddr, self.contractABI, fromAccount, "refund", (marketId, sellIndex, ))

        policyMap2 = self.client.callFunc(self.contractAddr, self.contractABI, "sellerPolicyMap", (marketId, fromAccount.address, sellIndex,), True)
        buyerTokenAmount2 = self.client.callFunc(tokenAddr, tokenABI, "balanceOf", (buyerAddr,), True)
        sellerTokenAmount2 = self.client.callFunc(tokenAddr, tokenABI, "balanceOf", (fromAccount.address,), True)
        buyerLP2 = self.client.callFunc(pancakePair, pairABI, "balanceOf", (buyerAddr,), True)
        sellerLP2 = self.client.callFunc(pancakePair, pairABI, "balanceOf", (fromAccount.address,), True)

        logger.info("claim之后数据: ")
        logger.info("订单信息: {}".format(policyMap2))
        logger.info("buyer lp: {}, changed: {}".format(buyerLP2, buyerLP2 - buyerLP))
        logger.info("seller lp: {}, changed: {}".format(sellerLP2, sellerLP2 - sellerLP))
        logger.info("buyer token Amount: {}, changed: {}".format(buyerTokenAmount2, buyerTokenAmount2 - buyerTokenAmount))
        logger.info("seller token Amount: {}, changed: {}".format(sellerTokenAmount2, sellerTokenAmount2 - sellerTokenAmount))

        assert buyerLP2 - buyerLP == policyMap[4], "buyer lp 应该全额退回"
        assert sellerLP == sellerLP2, "seller lp 应该不变"
        assert buyerTokenAmount2 - buyerTokenAmount == toPayAmount, "buyer 赔付不正确"
        assert sellerTokenAmount2 - sellerTokenAmount == policyMap[3] - toPayAmount, "seller获取返回的资金不正确"

    def getMultiplier(self, curDay):
        startDay = self.client.callFunc(inMiningAddr, inMiningABI, "startDay", (), True)
        endDay = self.client.callFunc(inMiningAddr, inMiningABI, "endDay", (), True)
        endDoubleDay = self.client.callFunc(inMiningAddr, inMiningABI, "endDoubleDay", (), True)
        if curDay - startDay >= endDoubleDay:
            return 1
        elif curDay > endDay:
            return 0
        else:
            return 2

    def calShare(self, userInfo, curDay, lastInsuranceInfo):
        shares = 0
        logger.info("现在时间段为: {} > {}, 需要分得上一个周期的奖励".format(curDay, userInfo[0]))
        # 计算奖励
        tokenPerDay = self.client.callFunc(inMiningAddr, inMiningABI, "tokenPerDay", (), True)
        # lastInsuranceInfo = self.client.callFunc(inMiningAddr, inMiningABI, "InsuranceDailyInfo", (userInfo[0], ), True)
        currentTokenPerDay = tokenPerDay * self.getMultiplier(userInfo[0])
        logger.info("上一个周期的信息:{}".format(lastInsuranceInfo))
        # logger.info("上一个周期分得奖励的额度:{}".format(currentTokenPerDay))
        if lastInsuranceInfo[0] > 0 and lastInsuranceInfo[1] < currentTokenPerDay:
            shares = currentTokenPerDay * userInfo[1] // lastInsuranceInfo[0]
            logger.info("按比例计算分得的奖励为: {}".format(shares))
            if lastInsuranceInfo[1] + shares > currentTokenPerDay:
                shares = currentTokenPerDay - lastInsuranceInfo[1]
            logger.info("实际分得的奖励为: {}".format(shares))
            lastInsuranceInfo[1] += shares
            # userInfo 记录的lp置为0
            userInfo[1] = 0
            userInfo[0] = curDay
        return userInfo, lastInsuranceInfo, shares

    def calInsuranceMining(self, account, seller, amount,):
        tokenAmount = self.client.callFunc(meeAddr, meeABI, "balanceOf", (account.address,), True)
        feeTokenAmount = self.client.callFunc(meeAddr, meeABI, "balanceOf", (self.client.account.address,), True)
        buyerAwardAmount = self.client.callFunc(awardAddr, awardABI, "getUserTotalAwards", (account.address,), True)
        sellerAwardAmount = self.client.callFunc(awardAddr, awardABI, "getUserTotalAwards", (seller,), True)

        logger.info("当前相关信息")
        logger.info("投保人持有的MEE Amount: {}".format(tokenAmount))
        logger.info("抽税账户持有的MEE Amount: {}".format(feeTokenAmount))
        logger.info("投保方进入到Award合约的Amount: {}".format(buyerAwardAmount))
        logger.info("承包方进入到Award合约的Amount: {}".format(sellerAwardAmount))

        buyerUserInfo = self.client.callFunc(inMiningAddr, inMiningABI, "userInfo", (account.address, ), True)
        sellerUserInfo = self.client.callFunc(inMiningAddr, inMiningABI, "userInfo", (seller, ), True)
        buyerPendingShare = self.client.callFunc(inMiningAddr, inMiningABI, "getPendingReward", (account.address,), True)
        sellerPendingShare = self.client.callFunc(inMiningAddr, inMiningABI, "getPendingReward", (seller,), True)
        getTotalInsuranceColume = self.client.callFunc(inMiningAddr, inMiningABI, "getTotalInsuranceColume", (), True)
        getReleaseAwards = self.client.callFunc(inMiningAddr, inMiningABI, "getReleaseAwards", (), True)

        lastBuyerInsuranceInfo = self.client.callFunc(inMiningAddr, inMiningABI, "InsuranceDailyInfo", (buyerUserInfo[0], ), True)
        lastSellerInsuranceInfo = self.client.callFunc(inMiningAddr, inMiningABI, "InsuranceDailyInfo", (sellerUserInfo[0], ), True)
        logger.info("上一个周期的buyer时间段的整体信息:{}".format(lastBuyerInsuranceInfo))
        logger.info("上一个周期的seller时间段的整体信息:{}".format(lastSellerInsuranceInfo))

        logger.info("buy用户信息: {}".format(buyerUserInfo))
        logger.info("sell用户信息: {}".format(sellerUserInfo))
        # logger.info("挖矿合约记录的dailyInfo: {}".format(inDailyInfo))
        logger.info("buy用户未进入抽税合约的奖励: {}".format(buyerPendingShare))
        logger.info("sell用户未进入抽税合约的奖励: {}".format(sellerPendingShare))
        logger.info("getTotalInsuranceColume: {}".format(getTotalInsuranceColume))
        logger.info("getReleaseAwards: {}".format(getReleaseAwards))

        yield
        time.sleep(5)

        if buyerUserInfo[0] > 0:
            # lastDay有值，则需要计算是否分得上一次的奖励
            curDay = self.client.callFunc(inMiningAddr, inMiningABI, "getCurrDay", (), True)
            buyShares, sellShares = 0, 0
            # if True:
            if curDay > buyerUserInfo[0]:
                buyerUserInfo, lastBuyerInsuranceInfo, buyShares = self.calShare(buyerUserInfo, curDay, lastBuyerInsuranceInfo)
                logger.info("buyer新的userInfo: {}".format(buyerUserInfo))
                logger.info("新的lastInsuranceInfo: {}".format(lastBuyerInsuranceInfo))
            if curDay > sellerUserInfo[0]:
                sellerUserInfo, lastSellerInsuranceInfo, sellShares = self.calShare(sellerUserInfo, curDay, lastSellerInsuranceInfo)
                logger.info("seller新的userInfo: {}".format(sellerUserInfo))
                logger.info("新的lastInsuranceInfo: {}".format(lastSellerInsuranceInfo))

            buyerPendingShare2 = self.client.callFunc(inMiningAddr, inMiningABI, "getPendingReward", (account.address,), True)
            sellerPendingShare2 = self.client.callFunc(inMiningAddr, inMiningABI, "getPendingReward", (seller,), True)
            tokenAmount2 = self.client.callFunc(meeAddr, meeABI, "balanceOf", (account.address,), True)
            feeTokenAmount2 = self.client.callFunc(meeAddr, meeABI, "balanceOf", (self.client.account.address,), True)
            buyerAwardAmount2 = self.client.callFunc(awardAddr, awardABI, "getUserTotalAwards", (account.address,), True)
            sellerAwardAmount2 = self.client.callFunc(awardAddr, awardABI, "getUserTotalAwards", (seller,), True)
            logger.info("分得上一个周期的奖励后: buyerPendingShare2: {}, 实际减少了: {}, 预期: {}".format(buyerPendingShare2, buyerPendingShare - buyerPendingShare2, buyShares))
            logger.info("分得上一个周期的奖励后: sellerPendingShare2: {}, 实际减少了: {}, 预期: {}".format(sellerPendingShare2, sellerPendingShare - sellerPendingShare2, sellShares))
            logger.info("分得上一个周期的奖励后: tokenAmount2: {}".format(tokenAmount2))
            logger.info("分得上一个周期的奖励后: feeTokenAmount2: {}".format(feeTokenAmount2))
            logger.info("分得上一个周期的奖励后: buyerAwardAmount2: {}, 实际增加了: {}, 预期: {}".format(buyerAwardAmount2, buyerAwardAmount2 - buyerAwardAmount, buyShares))
            logger.info("分得上一个周期的奖励后: sellerAwardAmount2: {}, 实际增加了: {}, 预期: {}".format(sellerAwardAmount2, sellerAwardAmount2 - sellerAwardAmount, sellShares))
            # 如果yield中进行的是claimUserShares操作，则实际只领取了一方的奖励, 需观察上方的日志看实际变化的数量和计算出的奖励数量是否一致
            # assert sellerAwardAmount2 - sellerAwardAmount == sellShares
            # assert buyerAwardAmount2 - buyerAwardAmount == buyShares
            # assert buyerPendingShare - buyerPendingShare2 == buyShares
            # assert sellerPendingShare - sellerPendingShare2 == sellShares

            newBuyerInsuranceInfo = self.client.callFunc(inMiningAddr, inMiningABI, "InsuranceDailyInfo", (buyerUserInfo[0], ), True)
            newSellerInsuranceInfo = self.client.callFunc(inMiningAddr, inMiningABI, "InsuranceDailyInfo", (sellerUserInfo[0], ), True)
            logger.info("newBuyerInsuranceInfo: {}".format(newBuyerInsuranceInfo))
            logger.info("newSellerInsuranceInfo: {}".format(newSellerInsuranceInfo))
            if sellerAwardAmount2 - sellerAwardAmount == 0:
                if buyerUserInfo[0] == sellerUserInfo[0]:
                    # 如果一直
                    assert newBuyerInsuranceInfo == newSellerInsuranceInfo
                    # assert newBuyerInsuranceInfo == lastBuyerInsuranceInfo[1] + lastSellerInsuranceInfo[1]
                else:
                    assert newBuyerInsuranceInfo == lastBuyerInsuranceInfo
                    assert newSellerInsuranceInfo == lastSellerInsuranceInfo
            elif buyerAwardAmount2 - buyerAwardAmount == 0:
                if buyerUserInfo[0] == sellerUserInfo[0]:
                    # 如果一直
                    assert newBuyerInsuranceInfo == newSellerInsuranceInfo
                    # assert newBuyerInsuranceInfo == lastBuyerInsuranceInfo[1] + lastSellerInsuranceInfo[1]
                else:
                    assert newBuyerInsuranceInfo == lastBuyerInsuranceInfo
                    assert newSellerInsuranceInfo == lastSellerInsuranceInfo
            else:
                if buyerUserInfo[0] == sellerUserInfo[0]:
                    # 如果一直
                    assert newBuyerInsuranceInfo == newSellerInsuranceInfo
                    # assert newBuyerInsuranceInfo == lastBuyerInsuranceInfo[1] + lastSellerInsuranceInfo[1]
                else:
                    assert newBuyerInsuranceInfo == lastBuyerInsuranceInfo
                    assert newSellerInsuranceInfo == lastSellerInsuranceInfo

            sellerAmount = amount // 2
            buyerAmount = amount - sellerAmount
            logger.info("投保方增加的lp数量: {}".format(buyerAmount))
            logger.info("承保方增加的lp数量: {}".format(sellerAmount))

            curDailyInfo = self.client.callFunc(inMiningAddr, inMiningABI, "InsuranceDailyInfo", (curDay, ), True)
            logger.info("投保方购买保单后，合约记录此时间段的信息:{}".format(curDailyInfo))
            buyerUserInfo2 = self.client.callFunc(inMiningAddr, inMiningABI, "userInfo", (account.address, ), True)
            sellerUserInfo2 = self.client.callFunc(inMiningAddr, inMiningABI, "userInfo", (seller, ), True)
            logger.info("新的buyerInfo:{}".format(buyerUserInfo2))
            logger.info("新的SellerInfo:{}".format(sellerUserInfo2))
            if curDailyInfo[0] != 0:
                assert buyerUserInfo2[0] == curDay
                assert buyerUserInfo2[1] == buyerUserInfo[1] + buyerAmount
                assert sellerUserInfo2[0] == curDay
                assert sellerUserInfo2[1] == sellerUserInfo[1] + sellerAmount
                # assert curDailyInfo[0] == curDay
                # assert curDailyInfo[1] == 0

        getTotalInsuranceColume2 = self.client.callFunc(inMiningAddr, inMiningABI, "getTotalInsuranceColume", (), True)
        getReleaseAwards2 = self.client.callFunc(inMiningAddr, inMiningABI, "getReleaseAwards", (), True)
        logger.info("getTotalInsuranceColume: {}, 增加了: {}".format(getTotalInsuranceColume2, getTotalInsuranceColume2 - getTotalInsuranceColume))
        logger.info("getReleaseAwards: {}, 增加了: {}".format(getReleaseAwards2, getReleaseAwards2 - getReleaseAwards))

        # 如果在yield中没有触发pendingMining操作或者claimUserShares操作, 则该项检查会失败, 需观察上方的日志看实际变化的数量
        assert getReleaseAwards2 - getReleaseAwards == buyerPendingShare + sellerPendingShare
        assert getTotalInsuranceColume2 - getTotalInsuranceColume == amount


class PairPriceOracleTest:

    def __init__(self, contractAddr, contractABI, callClient: BSCClient):
        self.contractAddr = contractAddr
        self.contractABI = contractABI
        self.client = callClient

    def testGetBNBPx(self, pair):
        lp = self.client.callFunc(pair, pairABI, "totalSupply", (), True)
        token0 = self.client.web3.toChecksumAddress(hex(self.client.callFunc(pair, pairABI, "token0", (), True)))
        token1 = self.client.web3.toChecksumAddress(hex(self.client.callFunc(pair, pairABI, "token1", (), True)))
        reverses = self.client.callFunc(pair, pairABI, "getReserves", (), True)

        if token0 == wbnb:
            token0ABI = wbnbABI
            token1ABI = busdABI
        else:
            token0ABI = busdABI
            token1ABI = wbnbABI
        token0Balance = self.client.callFunc(token0, token0ABI, "balanceOf", (pair, ), True)
        token1Balance = self.client.callFunc(token1, token1ABI, "balanceOf", (pair, ), True)
        token0Price = self.client.callFunc(tokenPriceOracle, tokenPriceOracleABI, "getBNBPx", (token0, ), True)
        token1Price = self.client.callFunc(tokenPriceOracle, tokenPriceOracleABI, "getBNBPx", (token1, ), True)
        bandDemoPrice = self.client.callFunc(testBandOracle, bandOracleABI, "getPrice", ("BUSD", "BNB",), True)
        logger.info("pair 的lp: {}".format(lp))
        logger.info("token0: {}".format(token0))
        logger.info("token1: {}".format(token1))
        logger.info("reverses: {}".format(reverses))
        logger.info("pair持有的token0 Balance: {}".format(token0Balance))
        logger.info("pair持有的token1 Balance: {}".format(token1Balance))
        logger.info("token0 Price: {}".format(token0Price))
        logger.info("token1 Price: {}".format(token1Price))
        logger.info("bandDemo Price: {}".format(bandDemoPrice))
        logger.info("busd Price: {}".format(bandDemoPrice * 2**112 // int(1e18)))

        calLpPrice = (token0Balance * token0Price + token1Balance * token1Price) // lp
        logger.info("计算出来的lpPrice: {}".format(calLpPrice))
        lpPrice = self.client.callFunc(self.contractAddr, self.contractABI, "getBNBPx", (pair, ), True)
        logger.info("合约获取的lpPrice: {}".format(lpPrice))

        assert lpPrice == calLpPrice, "获取的lp的price和计算的不一致"


# 数据部分
# RPC_ADDRESS = 'https://ropsten.infura.io/v3/be5b825be13b4dda87056e6b073066dc'
# RPC_ADDRESS = 'https://kovan.infura.io/v3/be5b825be13b4dda87056e6b073066dc'
# RPC_ADDRESS = 'http://192.168.38.227:18045'
RPC_ADDRESS = 'https://data-seed-prebsc-1-s1.binance.org:8545'

PRIVATE_KEY = "ebed55a1f7e77144623167245abf39df053dc76fd8118ac7ae6e1ceeb84c5ed0"
PRIVATE_KEY_2 = "ad246d5896fd96c40595ff58e6e2a8bd23ffb31e95b1fb786a9034d2df120492"
PRIVATE_KEY_3 = "ed35ec431b50f44b892b86af74f886cdc0d9b853487c30498e19057c5bff1733"

# insurance = "0x9347e6EB8367A6ddF24Daf738612A8556AcE594A"
# insurance = "0x149b5689380cA1B544f62FE49C5924E10F04503e"
insurance = "0x1192d63735E34B9902CD95ab6c8c7b425783dC83"

timeLock = "0x3889a0860c428A598031882BD47FDA718ACb29D1"

pancakePair = "0x575Cb459b6E6B8187d3Ef9a25105D64011874820"
pancakeRouter = "0xD99D1c33F9fC3444f8101754aBC46c52416550D1"

pairPriceOracle = "0x71c4B579C290d0c8bC7e33e0dC1153630055b93f"
tokenPriceOracle = "0x72A27738a75d26dfb19ed538D2E02678Db1fBA0f"
testBandOracle = "0x25A88Be96e581390bfEDe7bF20cD3a4817E5B597"

wbnb = "0xae13d989daC2f0dEbFf460aC112a837C89BAa7cd"
busd = "0xeD24FC36d5Ee211Ea25A80239Fb8C4Cfd80f12Ee"

# 保险挖矿部分
meeAddr = "0xDeB074F4d9De6467b021ab86F952e9191bEE0eE8"
awardAddr = "0xa8206909E89152147eFa4F440984d42c349915b9"
inMiningAddr = "0xad1637F36Dbf025c3505AE98051CBf29403C957E"

logger = setCustomLogger("web3.RequestManager", "bscTestnet.log", isprintsreen=True, level=logging.INFO)

gWei = 1000000000
if __name__ == "__main__":
    client = BSCClient(RPC_ADDRESS, PRIVATE_KEY)
    account2 = client.web3.eth.account.privateKeyToAccount(PRIVATE_KEY_2)
    account3 = client.web3.eth.account.privateKeyToAccount(PRIVATE_KEY_3)
    account4 = client.web3.eth.account.privateKeyToAccount("f03c34d7aee3a9cef4723b2860a76713f1a466d79030af04f93e49fafa8a8bcb")
    print("account2", account2.address)
    print("account3", account3.address)
    print("account4", account4.address)
    # 获取合约的ABI
    insuranceABI = load_from_json_file("./abi/insurance.json")["abi"]
    wbnbABI = load_from_json_file("./abi/WBNB.json")["abi"]
    busdABI = load_from_json_file("./abi/BUSD.json")["abi"]
    pairABI = load_from_json_file("./abi/PancakePair.json")["abi"]
    tokenPriceOracleABI = load_from_json_file("./abi/TokenPriceOracle.json")["abi"]
    pairPriceOracleABI = load_from_json_file("./abi/PairPriceOracle.json")["abi"]
    bandOracleABI = load_from_json_file("./abi/BandDemoOracle.json")["abi"]
    timeLockABI = load_from_json_file("./abi/timelock.json")["abi"]
    meeABI = load_from_json_file("./abi/GovernToken.json")["abi"]
    awardABI = load_from_json_file("./abi/AwardContract.json")["abi"]
    inMiningABI = load_from_json_file("./abi/InsuranceMining.json")["abi"]

    # print(client.callFunc(insurance, insuranceABI, "estimateBaseTokenAmount", (6, 25), True))
    # print(client.callFunc(insurance, insuranceABI, "getLpTokenPrice", (pancakePair, busd, ), True))
    # print(client.callFunc(insurance, insuranceABI, "marketMap", (1, ), True))

    # client.callFuncUseGas(pancakePair, pairABI, client.account, "transfer", (account2.address, 100000, ))
    # client.callFuncUseGas(insurance, insuranceABI, client.account, "createMarket", (6, "0x575Cb459b6E6B8187d3Ef9a25105D64011874820", 1623923208, 70,1,))

    # print(client.callFunc(insurance, insuranceABI, "estimateBaseTokenAmount", (1, 80000, ), True))
    # print(client.callFunc("0x66170441E2131cad77e243b48645Afb3912422A3", tokenPriceOracleABI, "owner", ()))
    # print(client.callFunc(insurance, insuranceABI, "isStableToken", (busd,), True))

    # client.callFuncUseGas(insurance, insuranceABI, client.account, "setStableToken", (busd, False, ), False)

    # client.callFuncUseGas(timeLock, timeLockABI, client.account, "queueTransaction", (
    # "0x9347e6EB8367A6ddF24Daf738612A8556AcE594A", 0, "setStableToken(address, bool)",
    # "0x000000000000000000000000ed24fc36d5ee211ea25a80239fb8c4cfd80f12ee0000000000000000000000000000000000000000000000000000000000000000",
    # 1623235572, ))
    # print(client.callFunc("0xD58081AA203eE0321eD965206de040FCd49B807c", pairPriceOracleABI, "owner", ()))
    # print(client.callFunc(pancakePair, pairABI, "balanceOf", (client.account.address,), True))
    # print(client.callFunc(pancakePair, pairABI, "balanceOf", (account2.address,), True))
    # print(client.callFunc(pancakePair, pairABI, "balanceOf", (account3.address,), True))
    # print(client.callFunc(pancakePair, pairABI, "allowance", (account3.address, insurance,), True))
    # print(client.callFunc(pancakePair, pairABI, "allowance", (account2.address,insurance,), True))
    # print(client.callFunc(pancakePair, pairABI, "allowance", (client.account.address,insurance,), True))
    # print(client.callFuncUseGas(pancakePair, pairABI, client.account, "transfer", (account2.address, 100000000000,)))
    # print(client.callFuncUseGas(pancakePair, pairABI, client.account, "approve", (insurance, 100000000000,)))
    # print(client.callFuncUseGas(pancakePair, pairABI, account3, "approve", (insurance, 100000000000,)))

    # print(client.callFuncUseGas(pancakePair, pairABI, account2, "approve", (insurance, 1000000000000000,)))
    # print(client.callFunc(wbnb, wbnbABI, "balanceOf", (client.account.address,), True))
    # print(client.callFunc(wbnb, wbnbABI, "balanceOf", (account2.address,), True))
    # print(client.callFunc(wbnb, wbnbABI, "balanceOf", (account3.address,), True))
    # print(client.callFunc(wbnb, wbnbABI, "balanceOf", (account4.address,), True))
    # print(client.callFunc(wbnb, wbnbABI, "allowance", (client.account.address, insurance,), True))
    # print(client.callFunc(wbnb, wbnbABI, "allowance", (account2.address, insurance,), True))
    # print(client.callFunc(wbnb, wbnbABI, "allowance", (account3.address, insurance,), True))
    # print(client.callFunc(wbnb, wbnbABI, "allowance", (account4.address, insurance,), True))
    # print(client.callFuncUseGas(wbnb, wbnbABI, client.account, "approve", (insurance,10000000000000,)))
    # print(client.callFuncUseGas(wbnb, wbnbABI, account2, "approve", (insurance,10000000000000,)))
    # print(client.callFuncUseGas(wbnb, wbnbABI, account3, "approve", (insurance, 10000000000000,)))
    # print(client.callFuncUseGas(wbnb, wbnbABI, account4, "approve", (insurance, 10000000000000,)))
    # print(client.callFuncUseGas(wbnb, wbnbABI, account2, "deposit", (), value=10000000000000))
    # print(client.callFuncUseGas(wbnb, wbnbABI, account2, "approve", (insurance, 10000000000000,)))

    instest = InsuanceTest(insurance, insuranceABI, client)
    # 挂出保单
    # instest.testSell(client.account, 1, 345, 10000000, 0, busd, busdABI)
    # instest.testSell(client.account, 1, 345, 10000000, 0, wbnb, wbnbABI)
    # instest.testSell(client.account, 3, 567, 100000, 0, wbnb, wbnbABI)

    # 吃掉保单
    # instest.testBuy(account2, 1, client.account.address, 0, 1000, 0, wbnb, wbnbABI)
    # instest.testBuy(account2, 1, client.account.address, 0, 10000, 0, wbnb, wbnbABI)
    # instest.testBuy(account2, 1, client.account.address, 0, 1000, 1, wbnb, wbnbABI)
    # instest.testBuy(account2, 2, client.account.address, 0, 1000, 0, wbnb, wbnbABI)
    # instest.testBuy(account2, 2, client.account.address, 0, 9000, 1, wbnb, wbnbABI)
    # instest.testBuy(account2, 3, client.account.address, 0, 10000, 0, wbnb, wbnbABI)
    # 改变订单
    # instest.testChangeOrCancelOrder(client.account, 1, 0, 0, wbnb, wbnbABI)
    # instest.testChangeOrCancelOrder(client.account, 6, 0, 99766, busd, busdABI)
    # instest.testChangeOrCancelOrder(client.account, 6, 0, 97766, busd, busdABI)
    # instest.testChangeOrCancelOrder(client.account, 6, 0, 12345, busd, busdABI)
    # instest.testChangeOrCancelOrder(client.account, 6, 1, 0, busd, busdABI)
    # instest.testChangeOrCancelOrder(client.account, 6, 0, 12345, busd, busdABI)

    # 投包人领取赔偿
    # instest.testClaim(account2, 2, 0, wbnb, wbnbABI)

    # 承包人进行赔付
    # instest.testRefund(client.account, 2, 1, wbnb, wbnbABI)

    # pairOracleTest = PairPriceOracleTest(pairPriceOracle, pairPriceOracleABI, client)

    # pairOracleTest.testGetBNBPx(pancakePair)

    # 保险挖矿部分
    # instest.testBuy(account2, 1, client.account.address, 0, 999, 1, wbnb, wbnbABI)
    insuranceAmount = 13579
    c = instest.calInsuranceMining(account2, client.account.address, insuranceAmount)
    # c = instest.calInsuranceMining(account3, account4.address, insuranceAmount)
    next(c)
    # logger.info("******进行购买保单操作******")
    # instest.testBuy(account2, 1, client.account.address, 0, insuranceAmount, 7, wbnb, wbnbABI)
    # instest.testBuy(client.account, 1, client.account.address, 0, insuranceAmount, 0, wbnb, wbnbABI)
    # instest.testBuy(account3, 1, client.account.address, 0, insuranceAmount, 0, wbnb, wbnbABI)
    # try:
    #     instest.testBuy(account3, 1, account4.address, 0, insuranceAmount, 4, wbnb, wbnbABI)
    # except Exception:
    #     pass
    # logger.info("******单独领取奖励******")
    client.callFuncUseGas(inMiningAddr, inMiningABI, account2, "claimUserShares", (account2.address, ))
    # client.callFuncUseGas(inMiningAddr, inMiningABI, account3, "claimUserShares", (account3.address, ))
    # client.callFuncUseGas(inMiningAddr, inMiningABI, account3, "claimUserShares", (account4.address, ))
    try:
        next(c)
    except StopIteration:
        # traceback.print_exc()
        logger.info("end")
