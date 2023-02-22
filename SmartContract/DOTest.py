from SmartContract.CommonTool import BaseEthClient
from roxe_libs.pub_function import setCustomLogger
import logging
import time
import math
import os


curPath = os.path.dirname(os.path.abspath(__file__))


class ERC20Test(BaseEthClient):

    def __init__(self, rpc_url, private_key, myLogger):
        super(ERC20Test, self).__init__(rpc_url, private_key, myLogger)

    def checkApprove(self, contract, spender, amount):
        allowance = contract.functions.allowance(self.account.address, spender).call()
        self.logger.info("approve 之前的授权额度: {}".format(allowance))
        exc_func = contract.functions.approve(spender, amount)
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        self.excuteTransaction(exc_func, nonce)
        allowance2 = contract.functions.allowance(self.account.address, spender).call()
        self.logger.info("approve 之后的授权额度: {}".format(allowance2))
        assert allowance2 == amount, "approve 检查失败"

    def checkIncreaseAllowance(self, contract, spender, amount):
        allowance = contract.functions.allowance(self.account.address, spender).call()
        self.logger.info("increaseAllowance 之前的授权额度: {}".format(allowance))
        exc_func = contract.functions.increaseAllowance(spender, amount)
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        self.excuteTransaction(exc_func, nonce)
        allowance2 = contract.functions.allowance(self.account.address, spender).call()
        self.logger.info("increaseAllowance 之后的授权额度: {}".format(allowance2))
        assert allowance2 - allowance == amount, "increaseAllowance 检查失败"

    def checkDecreaseAllowance(self, contract, spender, amount):
        allowance = contract.functions.allowance(self.account.address, spender).call()
        self.logger.info("decreaseAllowance 之前的授权额度: {}".format(allowance))
        exc_func = contract.functions.decreaseAllowance(spender, amount)
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        self.excuteTransaction(exc_func, nonce)
        allowance2 = contract.functions.allowance(self.account.address, spender).call()
        self.logger.info("decreaseAllowance 之后的授权额度: {}".format(allowance2))
        assert allowance - allowance2 == amount, "decreaseAllowance 检查失败"

    def checkMint(self, contract, mintTo, amount):
        totalSupply = contract.functions.totalSupply().call()
        toBalance = contract.functions.balanceOf(mintTo).call()
        self.logger.info("mint 之前的资产: {}".format(toBalance))
        self.logger.info("mint 之前的totalSupply: {}".format(totalSupply))
        exc_func = contract.functions.mint(mintTo, amount)
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        self.excuteTransaction(exc_func, nonce)
        toBalance2 = contract.functions.balanceOf(mintTo).call()
        totalSupply2 = contract.functions.totalSupply().call()
        self.logger.info("mint 之后的资产:{}".format(toBalance2))
        self.logger.info("mint 之后的totalSupply:{}".format(totalSupply2))
        assert toBalance2 - toBalance == amount, "mint 账户资产检查失败"
        assert totalSupply2 - totalSupply == amount, "mint 账户资产检查失败"

    def checkMintWhenMsgSenderIsNotIssuer(self, contract, mintTo, amount, msgSender):
        toBalance = contract.functions.balanceOf(mintTo).call()
        self.logger.info("mint 之前的资产: {}".format(toBalance))
        exc_func = contract.functions.mint(mintTo, amount)
        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        try:
            self.excuteTransaction(exc_func, nonce, msgSender)
        except Exception as e:
            if e.args[0]["message"] == "The execution failed due to an exception.":
                self.logger.info("由没有铸币权限发起的铸币应该是失败")
                tx_hash = self.excuteTransaction(exc_func, nonce, msgSender, 3000000)
                tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
                assert tx_info["status"] == 0, "交易应失败: {}".format(tx_info)
        toBalance2 = contract.functions.balanceOf(mintTo).call()
        self.logger.info("mint 之后的资产:{}".format(toBalance2))
        assert toBalance2 - toBalance == 0, "mint 账户资产检查失败"

    def checkTransfer(self, contract, recipient, amount, msgSender=None):
        if msgSender is None:
            msgSender = self.account
        fromBalance = contract.functions.balanceOf(msgSender.address).call()
        toBalance = contract.functions.balanceOf(recipient).call()
        self.logger.info("transfer 之前的资产: from {}, to {}".format(fromBalance, toBalance))

        exc_func = contract.functions.transfer(recipient, amount)
        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        self.excuteTransaction(exc_func, nonce, msgSender)

        fromBalance2 = contract.functions.balanceOf(msgSender.address).call()
        toBalance2 = contract.functions.balanceOf(recipient).call()
        self.logger.info("transfer 之后的资产: from {}, to {}".format(fromBalance2, toBalance2))
        assert fromBalance - fromBalance2 == amount, "transfer from账户资产检查失败"
        assert toBalance2 - toBalance == amount, "transfer to账户资产检查失败"

    def checkTransferAmountIs0(self, contract, recipient):
        fromBalance = contract.functions.balanceOf(self.account.address).call()
        toBalance = contract.functions.balanceOf(recipient).call()
        self.logger.info("transfer 之前的资产: from {}, to {}".format(fromBalance, toBalance))
        exc_func = contract.functions.transfer(recipient, 0)
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        self.excuteTransaction(exc_func, nonce)
        fromBalance2 = contract.functions.balanceOf(self.account.address).call()
        toBalance2 = contract.functions.balanceOf(recipient).call()
        self.logger.info("transfer 之后的资产: from {}, to {}".format(fromBalance2, toBalance2))
        assert fromBalance - fromBalance2 == 0, "transfer from账户资产检查失败"
        assert toBalance2 - toBalance == 0, "transfer to账户资产检查失败"

    def checkTransferAmountExceedFromAccountBalance(self, contract, recipient):
        fromBalance = contract.functions.balanceOf(self.account.address).call()
        toBalance = contract.functions.balanceOf(recipient).call()
        self.logger.info("transfer 之前的资产: from {}, to {}".format(fromBalance, toBalance))
        exc_func = contract.functions.transfer(recipient, fromBalance+1)
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        try:
            self.excuteTransaction(exc_func, nonce)
        except Exception as e:
            if e.args[0]["message"] == "The execution failed due to an exception.":
                self.logger.info("转账金额超过from账户持有的数量时失败")
                tx_hash = self.excuteTransaction(exc_func, nonce, gas=3000000)
                tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
                assert tx_info["status"] == 0, "交易应失败: {}".format(tx_info)
        fromBalance2 = contract.functions.balanceOf(self.account.address).call()
        toBalance2 = contract.functions.balanceOf(recipient).call()
        self.logger.info("transfer 之后的资产: from {}, to {}".format(fromBalance2, toBalance2))
        assert fromBalance - fromBalance2 == 0, "transfer from账户资产检查失败"
        assert toBalance2 - toBalance == 0, "transfer to账户资产检查失败"

    def checkTransferFrom(self, contract, toAccount, amount):
        allowance = contract.functions.allowance(self.account.address, toAccount.address).call()
        self.logger.info("transferFrom 之前的授权额度: {}".format(allowance))
        fromBalance = contract.functions.balanceOf(self.account.address).call()
        toBalance = contract.functions.balanceOf(toAccount.address).call()
        self.logger.info("transferFrom 之前的资产: from {}, to {}".format(fromBalance, toBalance))
        exc_func = contract.functions.transferFrom(self.account.address, toAccount.address, amount)
        nonce = self.w3.eth.getTransactionCount(toAccount.address)
        self.excuteTransaction(exc_func, nonce, toAccount)
        fromBalance2 = contract.functions.balanceOf(self.account.address).call()
        toBalance2 = contract.functions.balanceOf(toAccount.address).call()
        self.logger.info("transferFrom 之后的资产: from {}, to {}".format(fromBalance2, toBalance2))
        allowance2 = contract.functions.allowance(self.account.address, toAccount.address).call()
        self.logger.info("transferFrom 之后的授权额度: {}".format(allowance2))
        assert fromBalance - fromBalance2 == amount, "transferFrom from账户资产检查失败"
        assert toBalance2 - toBalance == amount, "transferFrom to账户资产检查失败"
        assert allowance - allowance2 == amount, "transferFrom 授权额度检查失败"

    def checkTransferFromAmountExceedAllowance(self, contract, toAccount):
        allowance = contract.functions.allowance(self.account.address, toAccount.address).call()
        self.logger.info("transferFrom 之前的授权额度: {}".format(allowance))
        fromBalance = contract.functions.balanceOf(self.account.address).call()
        toBalance = contract.functions.balanceOf(toAccount.address).call()
        self.logger.info("transferFrom 之前的资产: from {}, to {}".format(fromBalance, toBalance))
        exc_func = contract.functions.transferFrom(self.account.address, toAccount.address, allowance + 1)
        nonce = self.w3.eth.getTransactionCount(toAccount.address)
        try:
            self.excuteTransaction(exc_func, nonce, toAccount)
        except Exception as e:
            if e.args[0]["message"] == "The execution failed due to an exception.":
                self.logger.info("转账金额超过from账户授权的金额时失败")
                tx_hash = self.excuteTransaction(exc_func, nonce, toAccount, gas=3000000)
                tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
                assert tx_info["status"] == 0, "交易应失败: {}".format(tx_info)
        fromBalance2 = contract.functions.balanceOf(self.account.address).call()
        toBalance2 = contract.functions.balanceOf(toAccount.address).call()
        self.logger.info("transferFrom 之后的资产: from {}, to {}".format(fromBalance2, toBalance2))
        allowance2 = contract.functions.allowance(self.account.address, toAccount.address).call()
        self.logger.info("transferFrom 之后的授权额度: {}".format(allowance2))
        assert fromBalance - fromBalance2 == 0, "transferFrom from账户资产检查失败"
        assert toBalance2 - toBalance == 0, "transferFrom to账户资产检查失败"
        assert allowance - allowance2 == 0, "transferFrom 授权额度检查失败"

    def checkTransferOwnerShip(self, contract, oldOwner, newOwner):
        owner = contract.functions.owner().call()
        self.logger.info("transferOwnership 之前的owner: {}".format(owner))
        assert owner == oldOwner.address
        exc_func = contract.functions.transferOwnership(newOwner)
        nonce = self.w3.eth.getTransactionCount(oldOwner.address)
        self.excuteTransaction(exc_func, nonce, oldOwner)
        owner2 = contract.functions.owner().call()
        self.logger.info("transferOwnership 之后的owner: {}".format(owner2))
        assert owner2 == newOwner, "转移owner权限失败"

    def checkBurn(self, contract, amount, msgSender=None):
        if msgSender is None:
            msgSender = self.account
        totalSupply = contract.functions.totalSupply().call()
        userBalance = contract.functions.balanceOf(msgSender.address).call()
        self.logger.info("burn 之前的资产: {}".format(userBalance))
        self.logger.info("burn 之前的totalSupply: {}".format(totalSupply))
        exc_func = contract.functions.burn(amount)
        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        self.excuteTransaction(exc_func, nonce, msgSender)
        totalSupply2 = contract.functions.totalSupply().call()
        userBalance2 = contract.functions.balanceOf(msgSender.address).call()
        self.logger.info("burn 之后的资产: {}".format(userBalance2))
        self.logger.info("burn 之后的totalSupply: {}".format(totalSupply2))

        assert userBalance - userBalance2 == amount, "burn之后, 用户资产检查失败"
        assert totalSupply - totalSupply2 == amount, "burn之后totalSupply检查失败"

    def checkBurnAmountExceedUserBalance(self, contract, msgSender=None):
        if msgSender is None:
            msgSender = self.account
        totalSupply = contract.functions.totalSupply().call()
        userBalance = contract.functions.balanceOf(msgSender.address).call()
        self.logger.info("burn 之前的资产: {}".format(userBalance))
        self.logger.info("burn 之前的totalSupply: {}".format(totalSupply))
        exc_func = contract.functions.burn(userBalance + 1)
        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        try:
            self.excuteTransaction(exc_func, nonce, msgSender)
        except Exception as e:
            if e.args[0]["message"] == "The execution failed due to an exception.":
                self.logger.info("burn金额超过用户资产时交易失败")
                tx_hash = self.excuteTransaction(exc_func, nonce, msgSender, gas=3000000)
                tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
                assert tx_info["status"] == 0, "交易应失败: {}".format(tx_info)
        totalSupply2 = contract.functions.totalSupply().call()
        userBalance2 = contract.functions.balanceOf(msgSender.address).call()
        self.logger.info("burn 之后的资产: {}".format(userBalance2))
        self.logger.info("burn 之后的totalSupply: {}".format(totalSupply2))

        assert userBalance - userBalance2 == 0, "burn之后, 用户资产检查失败"
        assert totalSupply - totalSupply2 == 0, "burn之后totalSupply检查失败"


class DOTest(ERC20Test):

    def __init__(self, rpc_url, private_key, myLogger):
        super(DOTest, self).__init__(rpc_url, private_key, myLogger)

    def checkBurnFrom(self, contract, burnAccount, amount, msgSender=None):
        if msgSender is None:
            msgSender = self.account
        allowance = contract.functions.allowance(burnAccount.address, msgSender.address).call()
        self.logger.info("burnFrom 之前的授权额度: {}".format(allowance))
        totalSupply = contract.functions.totalSupply().call()
        userBalance = contract.functions.balanceOf(burnAccount.address).call()
        self.logger.info("burnFrom 之前的资产: {}".format(userBalance))
        self.logger.info("burnFrom 之前的totalSupply: {}".format(totalSupply))
        exc_func = contract.functions.burnFrom(burnAccount.address, amount)
        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        self.excuteTransaction(exc_func, nonce, msgSender)
        totalSupply2 = contract.functions.totalSupply().call()
        userBalance2 = contract.functions.balanceOf(burnAccount.address).call()
        self.logger.info("burnFrom 之后的资产: {}".format(userBalance2))
        self.logger.info("burnFrom 之后的totalSupply: {}".format(totalSupply2))
        allowance2 = contract.functions.allowance(burnAccount.address, msgSender.address).call()
        self.logger.info("burnFrom 之后的授权额度: {}".format(allowance2))

        assert userBalance - userBalance2 == amount, "burnFrom之后, 用户资产检查失败"
        assert totalSupply - totalSupply2 == amount, "burnFrom之后, totalSupply检查失败"
        assert allowance - allowance2 == amount, "burnFrom之后, allowance检查失败"

    def checkBurnFromAmountExceedAllowance(self, contract, burnAccount, msgSender=None):
        if msgSender is None:
            msgSender = self.account
        allowance = contract.functions.allowance(burnAccount.address, msgSender.address).call()
        self.logger.info("burnFrom 之前的授权额度: {}".format(allowance))
        totalSupply = contract.functions.totalSupply().call()
        userBalance = contract.functions.balanceOf(burnAccount.address).call()
        self.logger.info("burnFrom 之前的资产: {}".format(userBalance))
        self.logger.info("burnFrom 之前的totalSupply: {}".format(totalSupply))
        assert userBalance > allowance, "用户资产笔授权额度大"
        exc_func = contract.functions.burnFrom(burnAccount.address, allowance + 1)
        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        try:
            self.excuteTransaction(exc_func, nonce, msgSender)
        except Exception as e:
            if e.args[0]["message"] == "The execution failed due to an exception.":
                self.logger.info("burnFrom金额超过用户授权金额时交易失败:{}".format(allowance+1))
                tx_hash = self.excuteTransaction(exc_func, nonce, msgSender, gas=3000000)
                tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
                assert tx_info["status"] == 0, "交易应失败: {}".format(tx_info)
        totalSupply2 = contract.functions.totalSupply().call()
        userBalance2 = contract.functions.balanceOf(burnAccount.address).call()
        self.logger.info("burnFrom 之后的资产: {}".format(userBalance2))
        self.logger.info("burnFrom 之后的totalSupply: {}".format(totalSupply2))
        allowance2 = contract.functions.allowance(burnAccount.address, msgSender.address).call()
        self.logger.info("burnFrom 之后的授权额度: {}".format(allowance2))

        assert userBalance - userBalance2 == 0, "burnFrom之后, 用户资产检查失败"
        assert totalSupply - totalSupply2 == 0, "burnFrom之后, totalSupply检查失败"
        assert allowance - allowance2 == 0, "burnFrom之后, allowance检查失败"


class ROCTest(ERC20Test):

    def __init__(self, rpc_url, private_key, myLogger):
        super(ROCTest, self).__init__(rpc_url, private_key, myLogger)

    def checkMintWhenNotStart(self, contract, mintTo, amount):
        timeToMintMore = contract.functions.timeToMintMore().call()
        self.logger.info("当前timeToMintMore: {}".format(timeToMintMore))
        totalSupply = contract.functions.totalSupply().call()
        userBalance = contract.functions.balanceOf(mintTo).call()
        checkpoints = contract.functions.checkpoints(mintTo, 0).call()
        numCheckpoints = contract.functions.numCheckpoints(mintTo).call()
        self.logger.info("mint 之前的资产: {}".format(userBalance))
        self.logger.info("mint 之前的totalSupply: {}".format(totalSupply))
        self.logger.info("mint 之前的checkpoints: {}".format(checkpoints))
        self.logger.info("mint 之前的numCheckpoints: {}".format(numCheckpoints))
        exc_func = contract.functions.mint(mintTo, amount)
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        try:
            self.excuteTransaction(exc_func, nonce)
        except Exception as e:
            if e.args[0]["message"] == "The execution failed due to an exception.":
                self.logger.info("burnFrom金额超过用户授权金额时交易失败:{}".format(amount))
                tx_hash = self.excuteTransaction(exc_func, nonce, gas=3000000)
                tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
                assert tx_info["status"] == 0, "交易应失败: {}".format(tx_info)
        totalSupply2 = contract.functions.totalSupply().call()
        userBalance2 = contract.functions.balanceOf(mintTo).call()
        checkpoints2 = contract.functions.checkpoints(mintTo, 0).call()
        numCheckpoints2 = contract.functions.numCheckpoints(mintTo).call()
        self.logger.info("mint 之后的资产: {}".format(userBalance2))
        self.logger.info("mint 之后的totalSupply: {}".format(totalSupply2))
        self.logger.info("mint 之后的checkpoints: {}".format(checkpoints2))
        self.logger.info("mint 之后的numCheckpoints: {}".format(numCheckpoints2))

        timeToMintMore2 = contract.functions.timeToMintMore().call()
        self.logger.info("当前的timeToMintMore: {}".format(timeToMintMore2))
        assert userBalance2 == userBalance, "用户资产检查不正确"
        assert totalSupply2 == totalSupply, "totalSupply检查不正确"
        assert totalSupply2 == totalSupply, "用户资产检查不正确"

    def checkMintWhenLessTimeToMintMore(self, contract, mintTo, amount):
        timeToMintMore = contract.functions.timeToMintMore().call()
        self.logger.info("当前timeToMintMore: {}".format(timeToMintMore))
        totalSupply = contract.functions.totalSupply().call()
        userBalance = contract.functions.balanceOf(mintTo).call()
        checkpoints = contract.functions.checkpoints(mintTo, 0).call()
        numCheckpoints = contract.functions.numCheckpoints(mintTo).call()
        self.logger.info("mint 之前的资产: {}".format(userBalance))
        self.logger.info("mint 之前的totalSupply: {}".format(totalSupply))
        self.logger.info("mint 之前的checkpoints: {}".format(checkpoints))
        self.logger.info("mint 之前的numCheckpoints: {}".format(numCheckpoints))
        exc_func = contract.functions.mint(mintTo, amount)
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        try:
            self.excuteTransaction(exc_func, nonce)
        except Exception as e:
            if e.args[0]["message"] == "The execution failed due to an exception.":
                self.logger.info("mint时未超过timeToMintMore期限，应该失败:{}".format(amount))
                tx_hash = self.excuteTransaction(exc_func, nonce, gas=3000000)
                tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
                assert tx_info["status"] == 0, "交易应失败: {}".format(tx_info)
        totalSupply2 = contract.functions.totalSupply().call()
        userBalance2 = contract.functions.balanceOf(mintTo).call()
        checkpoints2 = contract.functions.checkpoints(mintTo, 0).call()
        numCheckpoints2 = contract.functions.numCheckpoints(mintTo).call()
        self.logger.info("burnFrom 之后的资产: {}".format(userBalance2))
        self.logger.info("burnFrom 之后的totalSupply: {}".format(totalSupply2))
        self.logger.info("burnFrom 之后的checkpoints: {}".format(checkpoints2))
        self.logger.info("burnFrom 之后的numCheckpoints: {}".format(numCheckpoints2))

        timeToMintMore2 = contract.functions.timeToMintMore().call()
        self.logger.info("当前的timeToMintMore: {}".format(timeToMintMore2))
        assert userBalance2 == userBalance, "用户资产检查不正确"
        assert totalSupply2 == totalSupply, "totalSupply检查不正确"
        assert totalSupply2 == totalSupply, "用户资产检查不正确"

    def checkStart(self, contract, to):
        delegates = contract.functions.delegates(to).call()
        timeToMintMore = contract.functions.timeToMintMore().call()
        self.logger.info("当前 timeToMintMore: {}".format(timeToMintMore))
        self.logger.info("当前 delegates: {}".format(delegates))
        totalSupply = contract.functions.totalSupply().call()
        userBalance = contract.functions.balanceOf(to).call()
        checkpoints = contract.functions.checkpoints(to, 0).call()
        numCheckpoints = contract.functions.numCheckpoints(to).call()
        self.logger.info("start 之前的资产: {}".format(userBalance))
        self.logger.info("start 之前的totalSupply: {}".format(totalSupply))
        self.logger.info("start 之前的checkpoints: {}".format(checkpoints))
        self.logger.info("start 之前的numCheckpoints: {}".format(numCheckpoints))
        exc_func = contract.functions.start(to)
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        tx_info = {}
        try:
            # pass
            tx_hash = self.excuteTransaction(exc_func, nonce)
            tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
        except Exception as e:
            if e.args[0]["message"] == "The execution failed due to an exception.":
                tx_hash = self.excuteTransaction(exc_func, nonce, gas=3000000)
                tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
                assert tx_info["status"] == 0, "交易应失败: {}".format(tx_info)
        # tx_info = self.w3.eth.getTransactionReceipt("0xfac4ee21dde1d9a72a2ac1741995d4cb058c15cb56c88f5dd0807452624c5c39")
        block_info = self.w3.eth.getBlock(tx_info["blockNumber"])
        expectedTimeToMintMore = block_info["timestamp"] + 1461 * 24 * 3600
        totalSupply2 = contract.functions.totalSupply().call()
        userBalance2 = contract.functions.balanceOf(to).call()
        checkpoints2 = contract.functions.checkpoints(to, 0).call()
        numCheckpoints2 = contract.functions.numCheckpoints(to).call()
        self.logger.info("start 之后的资产: {}".format(userBalance2))
        self.logger.info("start 之后的totalSupply: {}".format(totalSupply2))
        self.logger.info("start 之后的checkpoints: {}".format(checkpoints2))
        self.logger.info("start 之后的numCheckpoints: {}".format(numCheckpoints2))

        timeToMintMore2 = contract.functions.timeToMintMore().call()
        self.logger.info("当前的timeToMintMore: {}".format(timeToMintMore2))
        assert userBalance - userBalance2 == int(math.pow(10, 29)), "用户资产检查不正确"
        assert totalSupply2 - totalSupply == int(math.pow(10, 29)), "totalSupply检查不正确"
        assert checkpoints2 == checkpoints, "用户checkpoints检查不正确"
        assert numCheckpoints2 == numCheckpoints, "用户numCheckpoints2检查不正确"
        assert timeToMintMore2 == expectedTimeToMintMore, "用户expectedTimeToMintMore检查不正确"

    def checkStartWhenStarted(self, contract, to):
        delegates = contract.functions.delegates(to).call()
        timeToMintMore = contract.functions.timeToMintMore().call()
        self.logger.info("当前 timeToMintMore: {}".format(timeToMintMore))
        self.logger.info("当前 delegates: {}".format(delegates))
        totalSupply = contract.functions.totalSupply().call()
        userBalance = contract.functions.balanceOf(to).call()
        checkpoints = contract.functions.checkpoints(to, 0).call()
        numCheckpoints = contract.functions.numCheckpoints(to).call()
        self.logger.info("start 之前的资产: {}".format(userBalance))
        self.logger.info("start 之前的totalSupply: {}".format(totalSupply))
        self.logger.info("start 之前的checkpoints: {}".format(checkpoints))
        self.logger.info("start 之前的numCheckpoints: {}".format(numCheckpoints))
        exc_func = contract.functions.start(to)
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        try:
            self.excuteTransaction(exc_func, nonce)
        except Exception as e:
            if e.args[0]["message"] == "The execution failed due to an exception.":
                tx_hash = self.excuteTransaction(exc_func, nonce, gas=3000000)
                tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
                assert tx_info["status"] == 0, "交易应失败: {}".format(tx_info)
        totalSupply2 = contract.functions.totalSupply().call()
        userBalance2 = contract.functions.balanceOf(to).call()
        checkpoints2 = contract.functions.checkpoints(to, 0).call()
        numCheckpoints2 = contract.functions.numCheckpoints(to).call()
        self.logger.info("start 之后的资产: {}".format(userBalance2))
        self.logger.info("start 之后的totalSupply: {}".format(totalSupply2))
        self.logger.info("start 之后的checkpoints: {}".format(checkpoints2))
        self.logger.info("start 之后的numCheckpoints: {}".format(numCheckpoints2))

        timeToMintMore2 = contract.functions.timeToMintMore().call()
        self.logger.info("当前的timeToMintMore: {}".format(timeToMintMore2))
        assert userBalance2 - userBalance == 0, "用户资产检查不正确"
        assert totalSupply2 - totalSupply == 0, "totalSupply检查不正确"
        assert checkpoints2 == checkpoints, "用户checkpoints检查不正确"
        assert numCheckpoints2 == numCheckpoints, "用户numCheckpoints2检查不正确"

    def checkStartWhenMsgSenderIsNotOwner(self, contract, to, msgSender):
        delegates = contract.functions.delegates(to).call()
        timeToMintMore = contract.functions.timeToMintMore().call()
        self.logger.info("当前timeToMintMore: {}".format(timeToMintMore))
        self.logger.info("当前timeToMintMore: {}".format(delegates))
        totalSupply = contract.functions.totalSupply().call()
        userBalance = contract.functions.balanceOf(to).call()
        checkpoints = contract.functions.checkpoints(to, 0).call()
        numCheckpoints = contract.functions.numCheckpoints(to).call()
        self.logger.info("mint 之前的资产: {}".format(userBalance))
        self.logger.info("mint 之前的totalSupply: {}".format(totalSupply))
        self.logger.info("mint 之前的checkpoints: {}".format(checkpoints))
        self.logger.info("mint 之前的numCheckpoints: {}".format(numCheckpoints))
        exc_func = contract.functions.start(to)
        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        try:
            self.excuteTransaction(exc_func, nonce, msgSender)
        except Exception as e:
            if e.args[0]["message"] == "The execution failed due to an exception.":
                self.logger.info("start 应该失败")
                tx_hash = self.excuteTransaction(exc_func, nonce, msgSender, gas=3000000)
                tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
                assert tx_info["status"] == 0, "交易应失败: {}".format(tx_info)
        totalSupply2 = contract.functions.totalSupply().call()
        userBalance2 = contract.functions.balanceOf(to).call()
        checkpoints2 = contract.functions.checkpoints(to, 0).call()
        numCheckpoints2 = contract.functions.numCheckpoints(to).call()
        self.logger.info("burnFrom 之后的资产: {}".format(userBalance2))
        self.logger.info("burnFrom 之后的totalSupply: {}".format(totalSupply2))
        self.logger.info("burnFrom 之后的checkpoints: {}".format(checkpoints2))
        self.logger.info("burnFrom 之后的numCheckpoints: {}".format(numCheckpoints2))

        timeToMintMore2 = contract.functions.timeToMintMore().call()
        self.logger.info("当前的timeToMintMore: {}".format(timeToMintMore2))
        assert userBalance2 == userBalance, "用户资产检查不正确"
        assert totalSupply2 == totalSupply, "totalSupply检查不正确"
        assert checkpoints2 == checkpoints, "用户checkpoints检查不正确"
        assert numCheckpoints2 == numCheckpoints, "用户numCheckpoints2检查不正确"

    def checkSetIssuer(self, contract, _issuer, _isIssuer):

        issuerMap = contract.functions.issuerMap(_issuer).call()
        self.logger.info("setIssuer 之前的issuerMap: {}".format(issuerMap))

        exc_func = contract.functions.setIssuer(_issuer, _isIssuer)
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        self.excuteTransaction(exc_func, nonce)

        issuerMap2 = contract.functions.issuerMap(_issuer).call()
        self.logger.info("setIssuer 之后的issuerMap: {}".format(issuerMap2))

        assert issuerMap2 == _isIssuer, "setIssue后 issueMap更新不正确"

    def checkBurn(self, contract, amount, msgSender=None):
        if msgSender is None:
            msgSender = self.account
        delegates = contract.functions.delegates(msgSender.address).call()
        self.logger.info("当前 delegates: {}".format(delegates))
        numCheckpoints = contract.functions.numCheckpoints(delegates).call()
        votes = contract.functions.getCurrentVotes(delegates).call()
        totalSupply = contract.functions.totalSupply().call()
        userBalance = contract.functions.balanceOf(msgSender.address).call()
        self.logger.info("burn 之前的资产: {}".format(userBalance))
        self.logger.info("burn 之前的totalSupply: {}".format(totalSupply))
        self.logger.info("burn 之前的numCheckpoints: {}".format(numCheckpoints))
        self.logger.info("burn 之前的votes: {}".format(votes))

        exc_func = contract.functions.burn(amount)
        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        self.excuteTransaction(exc_func, nonce, msgSender)
        time.sleep(1)
        totalSupply2 = contract.functions.totalSupply().call()
        userBalance2 = contract.functions.balanceOf(msgSender.address).call()
        numCheckpoints2 = contract.functions.numCheckpoints(delegates).call()
        votes2 = contract.functions.getCurrentVotes(delegates).call()
        self.logger.info("burn 之后的资产: {}".format(userBalance2))
        self.logger.info("burn 之后的totalSupply: {}".format(totalSupply2))
        self.logger.info("burn 之后的numCheckpoints2: {}".format(numCheckpoints2))
        self.logger.info("burn 之前的votes: {}".format(votes2))

        assert userBalance - userBalance2 == amount, "burn之后, 用户资产检查失败"
        assert totalSupply - totalSupply2 == amount, "burn之后totalSupply检查失败"
        if votes > 0:
            assert votes - votes2 == amount, "votes计算不正确"
        else:
            assert votes2 == votes, "votes计算不正确"

    def checkDelegate(self, contract, delegateTo, msgSender=None):
        if msgSender is None:
            msgSender = self.account
        delegates = contract.functions.delegates(msgSender.address).call()
        self.logger.info("当前 delegates: {}".format(delegates))
        votes = contract.functions.getCurrentVotes(delegateTo).call()
        self.logger.info("当前 用户的投票: {}".format(votes))
        numCheckpoints = contract.functions.numCheckpoints(delegateTo).call()
        totalSupply = contract.functions.totalSupply().call()
        userBalance = contract.functions.balanceOf(msgSender.address).call()
        self.logger.info("delegate 之前的资产: {}".format(userBalance))
        self.logger.info("delegate 之前的totalSupply: {}".format(totalSupply))
        self.logger.info("delegate 之前的numCheckpoints: {}".format(numCheckpoints))
        index = 0 if numCheckpoints == 0 else numCheckpoints-1
        checkPoints = contract.functions.checkpoints(delegateTo, index).call()
        self.logger.info("delegate 之前最新的checkPoints为: {}".format(checkPoints))

        exc_func = contract.functions.delegate(delegateTo)
        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        tx_hash = self.excuteTransaction(exc_func, nonce, msgSender)
        tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
        print(tx_info)

        totalSupply2 = contract.functions.totalSupply().call()
        userBalance2 = contract.functions.balanceOf(msgSender.address).call()
        numCheckpoints2 = contract.functions.numCheckpoints(delegateTo).call()
        votes2 = contract.functions.getCurrentVotes(delegateTo).call()
        self.logger.info("delegate 之后用户的投票: {}".format(votes2))
        self.logger.info("delegate 之后的资产: {}".format(userBalance2))
        self.logger.info("delegate 之后的totalSupply: {}".format(totalSupply2))
        self.logger.info("delegate 之后的numCheckpoints2: {}".format(numCheckpoints2))

        index2 = 0 if numCheckpoints2 == 0 else numCheckpoints2 - 1
        checkPoints2 = contract.functions.checkpoints(delegateTo, index2).call()
        self.logger.info("delegate 之前最新的checkPoints为: {}".format(checkPoints2))

        assert votes2 - votes == userBalance, "vote 计算不正确"
        assert userBalance - userBalance2 == 0, "burn之后, 用户资产检查失败"
        assert totalSupply - totalSupply2 == 0, "burn之后totalSupply检查失败"
        assert numCheckpoints2 - numCheckpoints == 1, "numCheckpoints 检查不正确"

        time.sleep(10)
        priorVotes = contract.functions.getPriorVotes(delegateTo, tx_info["blockNumber"] - 10).call()
        priorVotes2 = contract.functions.getPriorVotes(delegateTo, tx_info["blockNumber"]).call()
        priorVotes3 = contract.functions.getPriorVotes(delegateTo, tx_info["blockNumber"] + 1).call()
        self.logger.info("{} {} {}".format(priorVotes, priorVotes2, priorVotes3))
        assert priorVotes3 == priorVotes2, "priorVotes 计算不正确"
        assert priorVotes2 - priorVotes == userBalance, "priorVotes 计算不正确"


class RoUSDTest(ERC20Test):

    def __init__(self, rpc_url, private_key, myLogger):
        super(RoUSDTest, self).__init__(rpc_url, private_key, myLogger)

    def deployRoUSD(self):
        self.deploy_contract("./abi/RoUSD.json", None)

    def checkSetIssuer(self, contract, issuer, setIsIssuer, msgSender=None):
        if msgSender is None:
            msgSender = self.account
        isIssue = contract.functions.issuerMap(issuer).call()
        self.logger.info("{} 是否拥有issue权限:{}".format(issuer, isIssue))
        exc_func = contract.functions.setIssuer(issuer, setIsIssuer)
        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        self.excuteTransaction(exc_func, nonce, msgSender)
        isIssue2 = contract.functions.issuerMap(issuer).call()
        self.logger.info("{} 是否拥有issue权限:{}".format(issuer, isIssue2))

        assert isIssue2 == setIsIssuer, "issueMap 检查失败"

    def checkSetIssuerCalledByNotOwner(self, contract, issuer, setIsIssuer, msgSender=None):
        if msgSender is None:
            msgSender = self.account
        owner1 = contract.functions.owner().call()
        isIssue = contract.functions.issuerMap(issuer).call()
        self.logger.info("{} 是否拥有issue权限:{}".format(issuer, isIssue))
        self.logger.info("owner:{}".format(owner1))
        assert owner1 != msgSender.address, "此用例必须非owner调用"

        exc_func = contract.functions.setIssuer(issuer, setIsIssuer)
        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        try:
            self.excuteTransaction(exc_func, nonce, msgSender)
        except Exception as e:
            if e.args[0]["message"] == "The execution failed due to an exception.":
                self.logger.info("setIssuer 应该失败")
                tx_hash = self.excuteTransaction(exc_func, nonce, msgSender, gas=3000000)
                tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
                assert tx_info["status"] == 0, "交易应失败: {}".format(tx_info)

        isIssue2 = contract.functions.issuerMap(issuer).call()
        self.logger.info("{} 是否拥有issue权限:{}".format(issuer, isIssue2))

        assert isIssue2 == isIssue, "issueMap 检查失败"

    def checkBurnFrom(self, contract, burnAccount, amount, msgSender=None):
        if msgSender is None:
            msgSender = self.account
        allowance = contract.functions.allowance(burnAccount.address, msgSender.address).call()
        self.logger.info("burnFrom 之前的授权额度: {}".format(allowance))
        totalSupply = contract.functions.totalSupply().call()
        userBalance = contract.functions.balanceOf(burnAccount.address).call()
        self.logger.info("burnFrom 之前的资产: {}".format(userBalance))
        self.logger.info("burnFrom 之前的totalSupply: {}".format(totalSupply))
        exc_func = contract.functions.burnFrom(burnAccount.address, amount)
        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        self.excuteTransaction(exc_func, nonce, msgSender)
        totalSupply2 = contract.functions.totalSupply().call()
        userBalance2 = contract.functions.balanceOf(burnAccount.address).call()
        self.logger.info("burnFrom 之后的资产: {}".format(userBalance2))
        self.logger.info("burnFrom 之后的totalSupply: {}".format(totalSupply2))
        allowance2 = contract.functions.allowance(burnAccount.address, msgSender.address).call()
        self.logger.info("burnFrom 之后的授权额度: {}".format(allowance2))

        assert userBalance - userBalance2 == amount, "burnFrom之后, 用户资产检查失败"
        assert totalSupply - totalSupply2 == amount, "burnFrom之后, totalSupply检查失败"
        assert allowance - allowance2 == amount, "burnFrom之后, allowance检查失败"

    def checkBurnFromAmountExceedAllowance(self, contract, burnAccount, msgSender=None):
        if msgSender is None:
            msgSender = self.account
        allowance = contract.functions.allowance(burnAccount.address, msgSender.address).call()
        self.logger.info("burnFrom 之前的授权额度: {}".format(allowance))
        totalSupply = contract.functions.totalSupply().call()
        userBalance = contract.functions.balanceOf(burnAccount.address).call()
        self.logger.info("burnFrom 之前的资产: {}".format(userBalance))
        self.logger.info("burnFrom 之前的totalSupply: {}".format(totalSupply))
        assert userBalance > allowance, "用户资产笔授权额度大"
        exc_func = contract.functions.burnFrom(burnAccount.address, allowance + 1)
        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        try:
            self.excuteTransaction(exc_func, nonce, msgSender)
        except Exception as e:
            if e.args[0]["message"] == "The execution failed due to an exception.":
                self.logger.info("burnFrom金额超过用户授权金额时交易失败:{}".format(allowance+1))
                tx_hash = self.excuteTransaction(exc_func, nonce, msgSender, gas=3000000)
                tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
                assert tx_info["status"] == 0, "交易应失败: {}".format(tx_info)
        totalSupply2 = contract.functions.totalSupply().call()
        userBalance2 = contract.functions.balanceOf(burnAccount.address).call()
        self.logger.info("burnFrom 之后的资产: {}".format(userBalance2))
        self.logger.info("burnFrom 之后的totalSupply: {}".format(totalSupply2))
        allowance2 = contract.functions.allowance(burnAccount.address, msgSender.address).call()
        self.logger.info("burnFrom 之后的授权额度: {}".format(allowance2))

        assert userBalance - userBalance2 == 0, "burnFrom之后, 用户资产检查失败"
        assert totalSupply - totalSupply2 == 0, "burnFrom之后, totalSupply检查失败"
        assert allowance - allowance2 == 0, "burnFrom之后, allowance检查失败"

    def checkSetTrustedToken(self, contract, tokenAddr, setValue, msgSender=None):
        if msgSender is None:
            msgSender = self.account
        # trustBalance = contract.functions.trustedBalance(tokenAddr, msgSender.address).call()
        totalSupply = contract.functions.totalSupply().call()
        isTrusted = contract.functions.trustedMap(tokenAddr).call()
        # self.logger.info("setTrustedToken 之前的trust资产: {}".format(trustBalance))
        self.logger.info("setTrustedToken 之前的token是否trust: {}".format(isTrusted))
        self.logger.info("setTrustedToken 之前的totalSupply: {}".format(totalSupply))

        exc_func = contract.functions.setTrustedToken(tokenAddr, setValue)
        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        self.excuteTransaction(exc_func, nonce, msgSender)

        totalSupply2 = contract.functions.totalSupply().call()
        # trustBalance2 = contract.functions.trustedBalance(tokenAddr, msgSender.address).call()
        isTrusted2 = contract.functions.trustedMap(tokenAddr).call()
        # self.logger.info("setTrustedToken 之前的trust资产: {}".format(trustBalance2))
        self.logger.info("setTrustedToken 之后的totalSupply: {}".format(totalSupply2))
        self.logger.info("setTrustedToken 之前的token是否trust: {}".format(isTrusted2))

        assert isTrusted2 == setValue, "trustToken检查失败"
        assert totalSupply == totalSupply2, "totalSupply检查失败"
        # assert trustBalance2 == trustBalance, "trustBalance检查失败"

    def checkSetTrustedTokenCalledByNotOwner(self, contract, tokenAddr, setValue, msgSender=None):
        if msgSender is None:
            msgSender = self.account
        owner = contract.functions.owner().call()
        self.logger.info("当前合约的owner: {}".format(owner))
        assert owner != msgSender.address, "此用例必须由非owner执行"
        # trustBalance = contract.functions.trustedBalance(tokenAddr, msgSender.address).call()
        totalSupply = contract.functions.totalSupply().call()
        isTrusted = contract.functions.trustedMap(tokenAddr).call()
        # self.logger.info("setTrustedToken 之前的trust资产: {}".format(trustBalance))
        self.logger.info("setTrustedToken 之前的token是否trust: {}".format(isTrusted))
        self.logger.info("setTrustedToken 之前的totalSupply: {}".format(totalSupply))

        exc_func = contract.functions.setTrustedToken(tokenAddr, setValue)
        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        try:
            self.excuteTransaction(exc_func, nonce, msgSender)
        except Exception as e:
            if e.args[0]["message"] == "The execution failed due to an exception.":
                self.logger.info("setTrustedToken 由非owner用户{} 执行应该失败:".format(msgSender.address))
                tx_hash = self.excuteTransaction(exc_func, nonce, msgSender, gas=3000000)
                tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
                assert tx_info["status"] == 0, "交易应失败: {}".format(tx_info)
        totalSupply2 = contract.functions.totalSupply().call()
        # trustBalance2 = contract.functions.trustedBalance(tokenAddr, msgSender.address).call()
        isTrusted2 = contract.functions.trustedMap(tokenAddr).call()
        # self.logger.info("setTrustedToken 之前的trust资产: {}".format(trustBalance2))
        self.logger.info("setTrustedToken 之后的totalSupply: {}".format(totalSupply2))
        self.logger.info("setTrustedToken 之前的token是否trust: {}".format(isTrusted2))

        assert isTrusted2 == isTrusted, "trustToken检查失败"
        assert totalSupply == totalSupply2, "totalSupply检查失败"
        # assert trustBalance2 == trustBalance, "trustBalance检查失败"

    def checkDeposite(self, contract, tokenAddr, amount, tokenDecimal=6, msgSender=None):
        if msgSender is None:
            msgSender = self.account
        tokenAllowance = self.getUsdcAllowance(contract, tokenAddr, msgSender.address, RoUSDAddr)
        tokenBalance = self.getUsdcBalance(contract, tokenAddr, msgSender.address)
        totalSupply = contract.functions.totalSupply().call()
        userBalance = contract.functions.balanceOf(msgSender.address).call()
        # trustBalance = contract.functions.trustedBalance(msgSender.address, tokenAddr).call()
        self.logger.info("deposit 之前的tokenAllowance: {}".format(tokenAllowance))
        self.logger.info("deposit 之前的token资产: {}".format(tokenBalance))
        self.logger.info("deposit 之前的RoUSD资产: {}".format(userBalance))
        # self.logger.info("deposit 之前的trustBalance: {}".format(trustBalance))
        self.logger.info("deposit 之前的totalSupply: {}".format(totalSupply))

        exc_func = contract.functions.deposit(tokenAddr, amount)
        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        self.excuteTransaction(exc_func, nonce, msgSender)

        tokenAllowance2 = self.getUsdcAllowance(contract, tokenAddr, msgSender.address, RoUSDAddr)
        tokenBalance2 = self.getUsdcBalance(contract, tokenAddr, msgSender.address)
        totalSupply2 = contract.functions.totalSupply().call()
        userBalance2 = contract.functions.balanceOf(msgSender.address).call()
        # trustBalance2 = contract.functions.trustedBalance(msgSender.address, tokenAddr).call()
        self.logger.info("deposit 之后的tokenAllowance: {}".format(tokenAllowance2))
        self.logger.info("deposit 之后的token资产: {}".format(tokenBalance2))
        self.logger.info("deposit 之后的roUSd资产: {}".format(userBalance2))
        # self.logger.info("deposit 之前的trustBalance: {}".format(trustBalance2))
        self.logger.info("deposit 之后的totalSupply: {}".format(totalSupply2))

        expectedRoUSD = int(amount * int(math.pow(10, 18-tokenDecimal)))
        assert tokenBalance - tokenBalance2 == amount, "token资产检查不正确"
        assert userBalance2 - userBalance == expectedRoUSD, "roUSD资产检查不正确"
        # assert trustBalance2 - trustBalance == amount, "trustBalance资产检查不正确"
        # assert trustBalance2 == userBalance2, "trustBalance资产检查不正确"
        assert totalSupply2 - totalSupply == expectedRoUSD, "supply检查不正确"
        assert tokenAllowance - tokenAllowance2 == amount, "token allowance 检查不正确"

    def checkDepositeAmountExceedAllowance(self, contract, tokenAddr, msgSender=None):
        if msgSender is None:
            msgSender = self.account
        tokenAllowance = self.getUsdcAllowance(contract, tokenAddr, msgSender.address, RoUSDAddr)
        tokenBalance = self.getUsdcBalance(contract, tokenAddr, msgSender.address)
        totalSupply = contract.functions.totalSupply().call()
        userBalance = contract.functions.balanceOf(msgSender.address).call()
        # trustBalance = contract.functions.trustedBalance(msgSender.address, tokenAddr).call()
        self.logger.info("deposit 之前的tokenAllowance: {}".format(tokenAllowance))
        self.logger.info("deposit 之前的token资产: {}".format(tokenBalance))
        self.logger.info("deposit 之前的RoUSD资产: {}".format(userBalance))
        # self.logger.info("deposit 之前的trustBalance: {}".format(trustBalance))
        self.logger.info("deposit 之前的totalSupply: {}".format(totalSupply))

        exc_func = contract.functions.deposit(tokenAddr, tokenAllowance + 1)
        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        try:
            self.excuteTransaction(exc_func, nonce, msgSender)
        except Exception as e:
            if e.args[0]["message"] == "The execution failed due to an exception.":
                self.logger.info("setTrustedToken 由非owner用户{} 执行应该失败:".format(msgSender.address))
                tx_hash = self.excuteTransaction(exc_func, nonce, msgSender, gas=3000000)
                tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
                assert tx_info["status"] == 0, "交易应失败: {}".format(tx_info)

        tokenAllowance2 = self.getUsdcAllowance(contract, tokenAddr, msgSender.address, RoUSDAddr)
        tokenBalance2 = self.getUsdcBalance(contract, tokenAddr, msgSender.address)
        totalSupply2 = contract.functions.totalSupply().call()
        userBalance2 = contract.functions.balanceOf(msgSender.address).call()
        # trustBalance2 = contract.functions.trustedBalance(msgSender.address, tokenAddr).call()
        self.logger.info("deposit 之后的tokenAllowance: {}".format(tokenAllowance2))
        self.logger.info("deposit 之后的token资产: {}".format(tokenBalance2))
        self.logger.info("deposit 之后的roUSd资产: {}".format(userBalance2))
        # self.logger.info("deposit 之前的trustBalance: {}".format(trustBalance2))
        self.logger.info("deposit 之后的totalSupply: {}".format(totalSupply2))

        assert tokenBalance - tokenBalance2 == 0, "token资产检查不正确"
        assert userBalance2 - userBalance == 0, "roUSD资产检查不正确"
        # assert trustBalance2 - trustBalance == 0, "trustBalance资产检查不正确"
        # assert trustBalance2 == userBalance2, "trustBalance资产检查不正确"
        assert totalSupply2 - totalSupply == 0, "supply检查不正确"
        assert tokenAllowance - tokenAllowance2 == 0, "token allowance 检查不正确"

    def checkDepositeAmountExceedBalance(self, contract, tokenAddr, msgSender=None):
        if msgSender is None:
            msgSender = self.account
        tokenAllowance = self.getUsdcAllowance(contract, tokenAddr, msgSender.address, RoUSDAddr)
        tokenBalance = self.getUsdcBalance(contract, tokenAddr, msgSender.address)
        totalSupply = contract.functions.totalSupply().call()
        userBalance = contract.functions.balanceOf(msgSender.address).call()
        # trustBalance = contract.functions.trustedBalance(msgSender.address, tokenAddr).call()
        self.logger.info("deposit 之前的tokenAllowance: {}".format(tokenAllowance))
        self.logger.info("deposit 之前的token资产: {}".format(tokenBalance))
        self.logger.info("deposit 之前的RoUSD资产: {}".format(userBalance))
        # self.logger.info("deposit 之前的trustBalance: {}".format(trustBalance))
        self.logger.info("deposit 之前的totalSupply: {}".format(totalSupply))

        exc_func = contract.functions.deposit(tokenAddr, tokenBalance + 1)
        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        try:
            self.excuteTransaction(exc_func, nonce, msgSender)
        except Exception as e:
            if e.args[0]["message"] == "The execution failed due to an exception.":
                self.logger.info("setTrustedToken 由非owner用户{} 执行应该失败:".format(msgSender.address))
                tx_hash = self.excuteTransaction(exc_func, nonce, msgSender, gas=3000000)
                tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
                assert tx_info["status"] == 0, "交易应失败: {}".format(tx_info)

        tokenAllowance2 = self.getUsdcAllowance(contract, tokenAddr, msgSender.address, RoUSDAddr)
        tokenBalance2 = self.getUsdcBalance(contract, tokenAddr, msgSender.address)
        totalSupply2 = contract.functions.totalSupply().call()
        userBalance2 = contract.functions.balanceOf(msgSender.address).call()
        # trustBalance2 = contract.functions.trustedBalance(msgSender.address, tokenAddr).call()
        self.logger.info("deposit 之后的tokenAllowance: {}".format(tokenAllowance2))
        self.logger.info("deposit 之后的token资产: {}".format(tokenBalance2))
        self.logger.info("deposit 之后的roUSd资产: {}".format(userBalance2))
        # self.logger.info("deposit 之前的trustBalance: {}".format(trustBalance2))
        self.logger.info("deposit 之后的totalSupply: {}".format(totalSupply2))

        assert tokenBalance - tokenBalance2 == 0, "token资产检查不正确"
        assert userBalance2 - userBalance == 0, "roUSD资产检查不正确"
        # assert trustBalance2 - trustBalance == 0, "trustBalance资产检查不正确"
        # assert trustBalance2 == userBalance2, "trustBalance资产检查不正确"
        assert totalSupply2 - totalSupply == 0, "supply检查不正确"
        assert tokenAllowance - tokenAllowance2 == 0, "token allowance 检查不正确"

    def checkDepositeNotTrustedToken(self, contract, tokenAddr, msgSender=None):
        if msgSender is None:
            msgSender = self.account
        tokenAllowance = self.getUsdcAllowance(contract, tokenAddr, msgSender.address, RoUSDAddr)
        tokenBalance = self.getUsdcBalance(contract, tokenAddr, msgSender.address)
        totalSupply = contract.functions.totalSupply().call()
        userBalance = contract.functions.balanceOf(msgSender.address).call()
        # trustBalance = contract.functions.trustedBalance(msgSender.address, tokenAddr).call()
        self.logger.info("deposit 之前的tokenAllowance: {}".format(tokenAllowance))
        self.logger.info("deposit 之前的token资产: {}".format(tokenBalance))
        self.logger.info("deposit 之前的RoUSD资产: {}".format(userBalance))
        # self.logger.info("deposit 之前的trustBalance: {}".format(trustBalance))
        self.logger.info("deposit 之前的totalSupply: {}".format(totalSupply))

        exc_func = contract.functions.deposit(tokenAddr, tokenAllowance // 2)
        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        try:
            self.excuteTransaction(exc_func, nonce, msgSender)
        except Exception as e:
            if e.args[0]["message"] == "The execution failed due to an exception.":
                self.logger.info("setTrustedToken 由非owner用户{} 执行应该失败:".format(msgSender.address))
                tx_hash = self.excuteTransaction(exc_func, nonce, msgSender, gas=3000000)
                tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
                assert tx_info["status"] == 0, "交易应失败: {}".format(tx_info)

        tokenAllowance2 = self.getUsdcAllowance(contract, tokenAddr, msgSender.address, RoUSDAddr)
        tokenBalance2 = self.getUsdcBalance(contract, tokenAddr, msgSender.address)
        totalSupply2 = contract.functions.totalSupply().call()
        userBalance2 = contract.functions.balanceOf(msgSender.address).call()
        # trustBalance2 = contract.functions.trustedBalance(msgSender.address, tokenAddr).call()
        self.logger.info("deposit 之后的tokenAllowance: {}".format(tokenAllowance2))
        self.logger.info("deposit 之后的token资产: {}".format(tokenBalance2))
        self.logger.info("deposit 之后的roUSd资产: {}".format(userBalance2))
        # self.logger.info("deposit 之前的trustBalance: {}".format(trustBalance2))
        self.logger.info("deposit 之后的totalSupply: {}".format(totalSupply2))

        assert tokenBalance - tokenBalance2 == 0, "token资产检查不正确"
        assert userBalance2 - userBalance == 0, "roUSD资产检查不正确"
        # assert trustBalance2 - trustBalance == 0, "trustBalance资产检查不正确"
        assert totalSupply2 - totalSupply == 0, "supply检查不正确"
        assert tokenAllowance - tokenAllowance2 == 0, "token allowance 检查不正确"

    def checkWithdraw(self, contract, tokenAddr, amount, tokenDecimal=6, msgSender=None):
        if msgSender is None:
            msgSender = self.account
        tokenAllowance = self.getUsdcAllowance(contract, tokenAddr, msgSender.address, RoUSDAddr)
        tokenBalance = self.getUsdcBalance(contract, tokenAddr, msgSender.address)
        totalSupply = contract.functions.totalSupply().call()
        userBalance = contract.functions.balanceOf(msgSender.address).call()
        # trustBalance = contract.functions.trustedBalance(msgSender.address, tokenAddr).call()
        self.logger.info("withdraw 之前的tokenAllowance: {}".format(tokenAllowance))
        self.logger.info("withdraw 之前的token资产: {}".format(tokenBalance))
        self.logger.info("withdraw 之前的RoUSD资产: {}".format(userBalance))
        # self.logger.info("withdraw 之前的trustBalance: {}".format(trustBalance))
        self.logger.info("withdraw 之前的totalSupply: {}".format(totalSupply))

        exc_func = contract.functions.withdraw(tokenAddr, amount)
        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        self.excuteTransaction(exc_func, nonce, msgSender)

        tokenAllowance2 = self.getUsdcAllowance(contract, tokenAddr, msgSender.address, RoUSDAddr)
        tokenBalance2 = self.getUsdcBalance(contract, tokenAddr, msgSender.address)
        totalSupply2 = contract.functions.totalSupply().call()
        userBalance2 = contract.functions.balanceOf(msgSender.address).call()
        # trustBalance2 = contract.functions.trustedBalance(msgSender.address, tokenAddr).call()
        self.logger.info("withdraw 之后的tokenAllowance: {}".format(tokenAllowance2))
        self.logger.info("withdraw 之后的token资产: {}".format(tokenBalance2))
        self.logger.info("withdraw 之后的roUSd资产: {}".format(userBalance2))
        # self.logger.info("withdraw 之前的trustBalance: {}".format(trustBalance2))
        self.logger.info("withdraw 之后的totalSupply: {}".format(totalSupply2))

        expectedRoUSD = amount * int(math.pow(10, 18 - tokenDecimal))
        assert tokenBalance2 - tokenBalance == amount, "token资产检查不正确"
        assert userBalance - userBalance2 == expectedRoUSD, "roUSD资产检查不正确"
        # assert trustBalance - trustBalance2 == amount, "trustBalance资产检查不正确"
        # assert trustBalance2 == userBalance2, "trustBalance资产检查不正确"
        assert totalSupply - totalSupply2 == expectedRoUSD, "supply检查不正确"
        assert tokenAllowance == tokenAllowance2, "token allowance 检查不正确"

    def checkWithdrawAmountExceedUserBalance(self, contract, tokenAddr, msgSender=None):
        if msgSender is None:
            msgSender = self.account
        tokenAllowance = self.getUsdcAllowance(contract, tokenAddr, msgSender.address, RoUSDAddr)
        tokenBalance = self.getUsdcBalance(contract, tokenAddr, msgSender.address)
        totalSupply = contract.functions.totalSupply().call()
        userBalance = contract.functions.balanceOf(msgSender.address).call()
        # trustBalance = contract.functions.trustedBalance(msgSender.address, tokenAddr).call()
        self.logger.info("withdraw 之前的tokenAllowance: {}".format(tokenAllowance))
        self.logger.info("withdraw 之前的token资产: {}".format(tokenBalance))
        self.logger.info("withdraw 之前的RoUSD资产: {}".format(userBalance))
        # self.logger.info("withdraw 之前的trustBalance: {}".format(trustBalance))
        self.logger.info("withdraw 之前的totalSupply: {}".format(totalSupply))

        exc_func = contract.functions.withdraw(tokenAddr, userBalance + 1)
        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        try:
            self.excuteTransaction(exc_func, nonce, msgSender)
        except Exception as e:
            if e.args[0]["message"] == "The execution failed due to an exception.":
                self.logger.info("setTrustedToken 由非owner用户{} 执行应该失败:".format(msgSender.address))
                tx_hash = self.excuteTransaction(exc_func, nonce, msgSender, gas=3000000)
                tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
                assert tx_info["status"] == 0, "交易应失败: {}".format(tx_info)

        tokenAllowance2 = self.getUsdcAllowance(contract, tokenAddr, msgSender.address, RoUSDAddr)
        tokenBalance2 = self.getUsdcBalance(contract, tokenAddr, msgSender.address)
        totalSupply2 = contract.functions.totalSupply().call()
        userBalance2 = contract.functions.balanceOf(msgSender.address).call()
        # trustBalance2 = contract.functions.trustedBalance(msgSender.address, tokenAddr).call()
        self.logger.info("withdraw 之后的tokenAllowance: {}".format(tokenAllowance2))
        self.logger.info("withdraw 之后的token资产: {}".format(tokenBalance2))
        self.logger.info("withdraw 之后的roUSd资产: {}".format(userBalance2))
        # self.logger.info("withdraw 之前的trustBalance: {}".format(trustBalance2))
        self.logger.info("withdraw 之后的totalSupply: {}".format(totalSupply2))

        assert tokenBalance - tokenBalance2 == 0, "token资产检查不正确"
        assert userBalance2 - userBalance == 0, "roUSD资产检查不正确"
        # assert trustBalance2 - trustBalance == 0, "trustBalance资产检查不正确"
        # assert trustBalance2 == userBalance2, "trustBalance资产检查不正确"
        assert totalSupply2 - totalSupply == 0, "supply检查不正确"
        assert tokenAllowance - tokenAllowance2 == 0, "token allowance 检查不正确"

    def checkWithdrawNotTrustedToken(self, contract, tokenAddr, msgSender=None):
        if msgSender is None:
            msgSender = self.account
        tokenAllowance = self.getUsdcAllowance(contract, tokenAddr, msgSender.address, RoUSDAddr)
        tokenBalance = self.getUsdcBalance(contract, tokenAddr, msgSender.address)
        totalSupply = contract.functions.totalSupply().call()
        userBalance = contract.functions.balanceOf(msgSender.address).call()
        # trustBalance = contract.functions.trustedBalance(msgSender.address, tokenAddr).call()
        self.logger.info("withdraw 之前的tokenAllowance: {}".format(tokenAllowance))
        self.logger.info("withdraw 之前的token资产: {}".format(tokenBalance))
        self.logger.info("withdraw 之前的RoUSD资产: {}".format(userBalance))
        # self.logger.info("withdraw 之前的trustBalance: {}".format(trustBalance))
        self.logger.info("withdraw 之前的totalSupply: {}".format(totalSupply))

        exc_func = contract.functions.withdraw(tokenAddr, 1)
        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        try:
            self.excuteTransaction(exc_func, nonce, msgSender)
        except Exception as e:
            if e.args[0]["message"] == "The execution failed due to an exception.":
                self.logger.info("setTrustedToken 由非owner用户{} 执行应该失败:".format(msgSender.address))
                tx_hash = self.excuteTransaction(exc_func, nonce, msgSender, gas=3000000)
                tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
                assert tx_info["status"] == 0, "交易应失败: {}".format(tx_info)

        tokenAllowance2 = self.getUsdcAllowance(contract, tokenAddr, msgSender.address, RoUSDAddr)
        tokenBalance2 = self.getUsdcBalance(contract, tokenAddr, msgSender.address)
        totalSupply2 = contract.functions.totalSupply().call()
        userBalance2 = contract.functions.balanceOf(msgSender.address).call()
        # trustBalance2 = contract.functions.trustedBalance(msgSender.address, tokenAddr).call()
        self.logger.info("withdraw 之后的tokenAllowance: {}".format(tokenAllowance2))
        self.logger.info("withdraw 之后的token资产: {}".format(tokenBalance2))
        self.logger.info("withdraw 之后的roUSd资产: {}".format(userBalance2))
        # self.logger.info("withdraw 之前的trustBalance: {}".format(trustBalance2))
        self.logger.info("withdraw 之后的totalSupply: {}".format(totalSupply2))

        assert tokenBalance - tokenBalance2 == 0, "token资产检查不正确"
        assert userBalance2 - userBalance == 0, "roUSD资产检查不正确"
        # assert trustBalance2 - trustBalance == 0, "trustBalance资产检查不正确"
        # assert trustBalance2 == userBalance2, "trustBalance资产检查不正确"
        assert totalSupply2 - totalSupply == 0, "supply检查不正确"
        assert tokenAllowance - tokenAllowance2 == 0, "token allowance 检查不正确"


class ReserveTest(ERC20Test):
    PRICE_BASE = int(math.pow(10, 18))
    RATIO_BASE = int(math.pow(10, 6))
    HOLDER_SHARE_BASE = int(math.pow(10, 4))

    def __init__(self, rpc_url, private_key, myLogger):
        super(ReserveTest, self).__init__(rpc_url, private_key, myLogger)

    def initReserve(self):
        newDO = self.deploy_contract("./abi/DO.json")
        newRoUSD = self.deploy_contract("./abi/RoUSD.json")
        newROC = self.deploy_contract("./abi/ROC.json")
        self.logger.info("DO: {}".format(newDO))
        self.logger.info("ROC: {}".format(newROC))
        self.logger.info("RoUSD: {}".format(newRoUSD))
        # newDO = "0x36870E7e0bD75237d9E3dC7ec568a4C7Cc717e6C"
        # newRoUSD = "0x9aDe76F73f6772e127f346EaCE6DbCa5DF529030"
        # newROC = "0x1978EDB4F9072825aa56999Bc71429cbbBc6B46D"

        newReserve = self.deploy_contract("./abi/Reserve.json", [newROC, newDO, newRoUSD])
        self.logger.info("Reserve: {}".format(newReserve))

        holderA = self.deploy_contract("./abi/Holder.json", [newReserve, newROC, newRoUSD, "TESTA"])
        self.logger.info("holderA: {}".format(holderA))

        holderB = self.deploy_contract("./abi/Holder.json", [newReserve, newROC, newRoUSD, "TESTB"])
        self.logger.info("holderB: {}".format(holderB))

    def checkSetHolderInfoArray(self, contract, holders, shares):
        exc_func = contract.functions.setHolderInfoArray(holders, shares)
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        self.excuteTransaction(exc_func, nonce)

        for i in range(len(holders)):
            info = contract.functions.holderInfoArray(i).call()
            assert info[0] == holders[i], "holder 地址不正确"
            assert info[1] == shares[i], "holder 地址不正确"

    def checkSetFunctions(self, contract, funcName, argName, argValue, msgSender=None):
        if msgSender is None:
            msgSender = self.account

        owner = contract.functions.owner().call()
        curValue = eval(f"contract.functions.{argName}().call()")
        self.logger.info("当前 {}: {}".format(argName, curValue))
        self.logger.info("当前owner: {}".format(owner))

        exc_func = eval(f"contract.functions.{funcName}")(argValue)
        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        try:
            self.excuteTransaction(exc_func, nonce, msgSender)
        except Exception as e:
            if owner != msgSender.address and e.args[0]["message"] == "The execution failed due to an exception.":
                self.logger.info("{} 由非owner用户{} 执行应该失败:".format(argName, msgSender.address))
                tx_hash = self.excuteTransaction(exc_func, nonce, msgSender, gas=3000000)
                tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
                assert tx_info["status"] == 0, "交易应失败: {}".format(tx_info)

        curValue2 = eval(f"contract.functions.{argName}().call()")
        self.logger.info("当前 {}: {}".format(argName, curValue2))

        expectValue = argValue if msgSender.address == owner else curValue
        assert curValue2 == expectValue, "inflationThreshold 检查失败"

    def getAmountPerLayer(self, _soldAmount):
        # if _soldAmount < self.w3.toWei("5000000", "ether"):
        #     return self.w3.toWei("50000", "ether")
        # elif _soldAmount < self.w3.toWei("15000000", "ether"):
        #     return self.w3.toWei("100000", "ether")
        # elif _soldAmount < self.w3.toWei("35000000", "ether"):
        #     return self.w3.toWei("200000", "ether")
        # elif _soldAmount < self.w3.toWei("65000000", "ether"):
        #     return self.w3.toWei("300000", "ether")
        # elif _soldAmount < self.w3.toWei("115000000", "ether"):
        #     return self.w3.toWei("500000", "ether")
        # else:
        #     return self.w3.toWei("1000000", "ether")
        tAmount = 0
        amount = self.w3.toWei("1000", "ether")
        while amount < self.w3.toWei("10000", "ether"):
            tAmount += amount * 10 * 2
            if tAmount >= _soldAmount:
                return amount
            amount += self.w3.toWei("500", "ether")

        while amount < self.w3.toWei("45000", "ether"):
            tAmount += amount * 10 * 2
            if tAmount >= _soldAmount:
                return amount
            amount += self.w3.toWei("1000", "ether")
        amount = self.w3.toWei("45000", "ether")
        tAmount += amount * 9 * 2
        if tAmount >= _soldAmount:
            return amount
        return self.w3.toWei("50000", "ether")

    def getPriceIncrementPerLayer(self, _soldAmount):
        if _soldAmount < self.w3.toWei("540000", "ether"):
            return 10000000000000000
        elif _soldAmount < self.w3.toWei("1890000", "ether"):
            return 20000000000000000
        elif _soldAmount < self.w3.toWei("4790000", "ether"):
            return 30000000000000000
        elif _soldAmount < self.w3.toWei("9690000", "ether"):
            return 40000000000000000
        elif _soldAmount < self.w3.toWei("16590000", "ether"):
            return 50000000000000000
        else:
            return 60000000000000000

    def getHolderInfo(self, contract):
        begin_index = 0
        holder_infos = []
        while True:
            try:
                holder = contract.functions.holderInfoArray(begin_index).call()
                holder_infos.append(holder)
                begin_index += 1
            except Exception:
                break
        self.logger.info("找到{}条Holder".format(len(holder_infos)))
        return holder_infos

    def getHolderBalances(self, holder_infos):
        holder_balances = []
        for holder in holder_infos:
            holder_RoUsd_balance = rousdContract.functions.balanceOf(holder[0]).call()
            holder_roc_balance = rocContract.functions.balanceOf(holder[0]).call()
            holder_balances.append([holder_RoUsd_balance, holder_roc_balance])
            self.logger.info("{} 的RoUSD 资产:{}".format(holder[0], holder_RoUsd_balance))
            self.logger.info("{} 的roc 资产:{}".format(holder[0], holder_roc_balance))
        return holder_balances

    def calRoUSDAmountFromROC(self, _amountOfROC, mPrice, mSold, mSoldInPreviousLayers):
        amountOfRoUSD = 0
        remainingInLayer = self.getAmountPerLayer(mSold) + mSoldInPreviousLayers - mSold
        while _amountOfROC > 0:
            if _amountOfROC < remainingInLayer:
                amountOfRoUSD = amountOfRoUSD + _amountOfROC * mPrice // self.PRICE_BASE
                mSold = mSold + _amountOfROC
                _amountOfROC = 0
            else:
                amountOfRoUSD = amountOfRoUSD + remainingInLayer * mPrice // self.PRICE_BASE
                _amountOfROC = _amountOfROC - remainingInLayer
                mPrice = mPrice + self.getPriceIncrementPerLayer(mSold)
                self.logger.debug("price升级计算中, amountOfRoUSD: {}".format(amountOfRoUSD))
                self.logger.debug("price升级计算中, _amountOfROC: {}".format(_amountOfROC))
                self.logger.debug("price升级计算中, mPrice: {}".format(mPrice))
                mSoldInPreviousLayers = mSoldInPreviousLayers + self.getAmountPerLayer(mSold)
                mSold = mSold + remainingInLayer
                self.logger.debug("price升级计算中, msold: {}".format(mSold))
                remainingInLayer = self.getAmountPerLayer(mSold)
                self.logger.debug("price升级计算中, remainingInLayer: {}".format(remainingInLayer))
        self.logger.info("计算后, amountOfRoUSD: {}".format(amountOfRoUSD))
        self.logger.info("计算后, price: {}".format(mPrice))
        self.logger.info("计算后, sold: {}".format(mSold))
        self.logger.info("计算后, soldInPreviousLayers: {}".format(mSoldInPreviousLayers))
        return [amountOfRoUSD, mPrice, mSold, mSoldInPreviousLayers]

    def checkEstimateRoUSDAmountFromROC(self, contract, _amountOfROC):
        mPrice = contract.functions.price().call()
        mSold = contract.functions.sold().call()
        mSoldInPreviousLayers = contract.functions.soldInPreviousLayers().call()

        self.logger.info("当前的price: {}".format(mPrice))
        self.logger.info("当前的mSold: {}".format(mSold))
        self.logger.info("当前的mSoldInPreviousLayers: {}".format(mSoldInPreviousLayers))

        res = contract.functions.estimateRoUSDAmountFromROC(_amountOfROC).call()
        self.logger.info("estimateRoUSDAmountFromROC 合约返回:{}".format(res))
        calRes = self.calRoUSDAmountFromROC(_amountOfROC, mPrice, mSold, mSoldInPreviousLayers)

        assert calRes[0] == res[0], "amountOfRoUSD 检查不正确"
        assert calRes[1] == res[1], "price 检查不正确"
        assert calRes[2] == res[2], "sold 检查不正确"
        assert calRes[3] == res[3], "soldInPreviousLayers 检查不正确"

    def calROCAmountFromRoUSD(self, _amountOfRoUSD, mPrice, mSold, mSoldInPreviousLayers):
        amountOfROC = 0
        remainingInLayer = self.getAmountPerLayer(mSold) + mSoldInPreviousLayers - mSold
        while _amountOfRoUSD > 0:
            amountEstimate = _amountOfRoUSD * self.PRICE_BASE // mPrice
            if amountEstimate < remainingInLayer:
                amountOfROC += amountEstimate
                mSold = mSold + amountEstimate
                _amountOfRoUSD = 0
            else:
                amountOfROC += remainingInLayer
                _amountOfRoUSD = _amountOfRoUSD - remainingInLayer * mPrice // self.PRICE_BASE
                mPrice = mPrice + self.getPriceIncrementPerLayer(mSold)
                self.logger.debug("price升级计算中, mPrice: {}".format(mPrice))
                mSoldInPreviousLayers = mSoldInPreviousLayers + self.getAmountPerLayer(mSold)
                mSold = mSold + remainingInLayer
                self.logger.debug("price升级计算中, msold: {}".format(mSold))
                remainingInLayer = self.getAmountPerLayer(mSold)
                self.logger.debug("price升级计算中, remainingInLayer: {}".format(remainingInLayer))
        # amountOfROC = amountOfROC - (amountOfROC % (self.HOLDER_SHARE_BASE * 2))

        self.logger.info("计算后, amountOfROC: {}".format(amountOfROC))
        self.logger.info("计算后, price: {}".format(mPrice))
        self.logger.info("计算后, sold: {}".format(mSold))
        self.logger.info("计算后, soldInPreviousLayers: {}".format(mSoldInPreviousLayers))
        return [amountOfROC, mPrice, mSold, mSoldInPreviousLayers]

    def checkEstimateROCAmountFromRoUSD(self, contract, _amountOfRoUSD):
        mPrice = contract.functions.price().call()
        mSold = contract.functions.sold().call()
        mSoldInPreviousLayers = contract.functions.soldInPreviousLayers().call()

        self.logger.info("当前的price: {}".format(mPrice))
        self.logger.info("当前的mSold: {}".format(mSold))
        self.logger.info("当前的mSoldInPreviousLayers: {}".format(mSoldInPreviousLayers))

        res = contract.functions.estimateROCAmountFromRoUSD(_amountOfRoUSD).call()
        self.logger.info("estimateROCAmountFromRoUSD 合约返回:{}".format(res))

        calRes = self.calROCAmountFromRoUSD(_amountOfRoUSD, mPrice, mSold, mSoldInPreviousLayers)

        assert calRes[0] == res[0], "amountOfROC 检查不正确"
        assert calRes[1] == res[1], "price 检查不正确"
        assert calRes[2] == res[2], "sold 检查不正确"
        assert calRes[3] == res[3], "soldInPreviousLayers 检查不正确"

    def checkPurchaseExactAmountOfROCWithRoUSD(self, contract, _amountOfROC, _maxAmountOfRoUSD, deadline=300):
        cost = contract.functions.cost().call()
        price = contract.functions.price().call()
        sold = contract.functions.sold().call()
        soldInPreviousLayers = contract.functions.soldInPreviousLayers().call()

        self.logger.info("cost :{}".format(cost))
        self.logger.info("price :{}".format(price))
        self.logger.info("sold :{}".format(sold))
        self.logger.info("soldInPreviousLayers :{}".format(soldInPreviousLayers))

        rousdBalance = rousdContract.functions.balanceOf(self.account.address).call()
        rocBalance = rocContract.functions.balanceOf(self.account.address).call()
        rousdRRBalance = rousdContract.functions.balanceOf(ReserveAddr).call()
        rocRRBalance = rocContract.functions.balanceOf(ReserveAddr).call()
        self.logger.info("RR合约 rousdRRBalance :{}".format(rousdRRBalance))
        self.logger.info("RR合约 rocRRBalance :{}".format(rocRRBalance))
        self.logger.info("rousdBalance :{}".format(rousdBalance))
        self.logger.info("rocBalance :{}".format(rocBalance))

        holderInfos = self.getHolderInfo(contract)
        holderBalances = self.getHolderBalances(holderInfos)

        # realRoc = _amountOfROC - (_amountOfROC %(self.HOLDER_SHARE_BASE * 2))
        realRoc = _amountOfROC
        self.logger.info("用户实际交易的ROC数量: {}".format(realRoc))
        cal_res2 = contract.functions.estimateRoUSDAmountFromROC(_amountOfROC).call()
        cal_res = self.calRoUSDAmountFromROC(realRoc, price, sold, soldInPreviousLayers)
        self.logger.info("estimateRoUSDAmountFromROC 计算:{}".format(cal_res))
        self.logger.info("estimateRoUSDAmountFromROC 合约返回:{}".format(cal_res2))

        nonce = self.w3.eth.getTransactionCount(self.account.address)
        now = int(time.time())
        self.logger.info("参数: {}, {}, {}".format(_amountOfROC, _maxAmountOfRoUSD, now + deadline))
        exc_func = contract.functions.purchaseExactAmountOfROCWithRoUSD(_amountOfROC, _maxAmountOfRoUSD, now + deadline)
        self.excuteTransaction(exc_func, nonce)

        time.sleep(2)
        cost2 = contract.functions.cost().call()
        price2 = contract.functions.price().call()
        sold2 = contract.functions.sold().call()
        soldInPreviousLayers2 = contract.functions.soldInPreviousLayers().call()
        self.logger.info("cost :{}".format(cost2))
        self.logger.info("price :{}".format(price2))
        self.logger.info("sold :{}".format(sold2))
        self.logger.info("soldInPreviousLayers :{}".format(soldInPreviousLayers2))
        rousdBalance2 = rousdContract.functions.balanceOf(self.account.address).call()
        rocBalance2 = rocContract.functions.balanceOf(self.account.address).call()
        rousdRRBalance2 = rousdContract.functions.balanceOf(ReserveAddr).call()
        rocRRBalance2 = rocContract.functions.balanceOf(ReserveAddr).call()
        self.logger.info("RR合约 rousdRRBalance :{}".format(rousdRRBalance2))
        self.logger.info("RR合约 rocRRBalance :{}".format(rocRRBalance2))
        self.logger.info("rousdBalance :{}".format(rousdBalance2))
        self.logger.info("rocBalance :{}".format(rocBalance2))

        self.logger.info("交易后的holder资产:")
        holderBalances2 = self.getHolderBalances(holderInfos)

        assert cost2 - cost == cal_res[0], "cost计算不正确"
        assert price2 == cal_res[1], "price计算不正确"
        assert sold2 == cal_res[2], "sold计算不正确"
        assert soldInPreviousLayers2 == cal_res[3], "soldInPreviousLayers计算不正确"

        assert rousdBalance - rousdBalance2 == cal_res[0], "用户roUsd资产计算不正确"
        assert rocBalance2 - rocBalance == realRoc, "用户roc资产计算不正确"

        if len(holderInfos) > 0:
            expecteHolderA = realRoc // 2 * Shares[0] // self.HOLDER_SHARE_BASE
            expecteHolderB = realRoc // 2 * Shares[1] // self.HOLDER_SHARE_BASE

            assert holderBalances[0][1] - holderBalances2[0][1] == expecteHolderA, "holderA roc资产计算不正确"
            assert holderBalances[1][1] - holderBalances2[1][1] == expecteHolderB, "holderB roc资产计算不正确"
            assert holderBalances2[0][0] - holderBalances[0][0] == cal_res[0] // 2 * Shares[0] // self.HOLDER_SHARE_BASE, "holderA roUSD资产计算不正确"
            assert holderBalances2[1][0] - holderBalances[1][0] == cal_res[0] // 2 * Shares[1] // self.HOLDER_SHARE_BASE, "holderA roUSD资产计算不正确"
            # 合约计算除法时有可能有误差，导致最后1位差1~2
            assert rocRRBalance - rocRRBalance2 == realRoc - (expecteHolderA + expecteHolderB), "RR合约roc资产计算不正确, {} {}".format(rocRRBalance - rocRRBalance2, realRoc - (expecteHolderA + expecteHolderB))
            assert rousdRRBalance2 - rousdRRBalance - cal_res[0] // 2 <= 2, "RR合约rocusd资产计算不正确:{} {}".format(rousdRRBalance2 - rousdRRBalance, cal_res[0] // 2)
            assert realRoc // 2 - expecteHolderA - expecteHolderB <= 2
        else:
            assert rocRRBalance - rocRRBalance2 == realRoc, "RR合约roc资产计算不正确, {} {}".format(rocRRBalance - rocRRBalance2, realRoc)
            assert rousdRRBalance2 - rousdRRBalance == cal_res[0], "RR合约rocusd资产计算不正确, {} {}".format(rousdRRBalance2 - rousdRRBalance, cal_res[0])

    def checkPurchaseROCWithExactAmountOfRoUSD(self, contract, _amountOfRoUSD, _minAmountOfROC, deadline=600):
        cost = contract.functions.cost().call()
        price = contract.functions.price().call()
        sold = contract.functions.sold().call()
        soldInPreviousLayers = contract.functions.soldInPreviousLayers().call()

        self.logger.info("cost :{}".format(cost))
        self.logger.info("price :{}".format(price))
        self.logger.info("sold :{}".format(sold))
        self.logger.info("soldInPreviousLayers :{}".format(soldInPreviousLayers))

        rousdBalance = rousdContract.functions.balanceOf(self.account.address).call()
        rocBalance = rocContract.functions.balanceOf(self.account.address).call()
        rousdRRBalance = rousdContract.functions.balanceOf(ReserveAddr).call()
        rocRRBalance = rocContract.functions.balanceOf(ReserveAddr).call()
        self.logger.info("RR合约 rousdRRBalance :{}".format(rousdRRBalance))
        self.logger.info("RR合约 rocRRBalance :{}".format(rocRRBalance))
        self.logger.info("rousdBalance :{}".format(rousdBalance))
        self.logger.info("rocBalance :{}".format(rocBalance))

        holderInfos = self.getHolderInfo(contract)

        holderARoUSDBalance = rousdContract.functions.balanceOf(HolderTestAAddr).call()
        holderBRoUSDBalance = rousdContract.functions.balanceOf(HolderTestBAddr).call()
        holderARocBalance = rocContract.functions.balanceOf(HolderTestAAddr).call()
        holderBRocBalance = rocContract.functions.balanceOf(HolderTestBAddr).call()
        self.logger.info("交易前holderARoUSDBalance :{}".format(holderARoUSDBalance))
        self.logger.info("交易前holderBRoUSDBalance :{}".format(holderBRoUSDBalance))
        self.logger.info("交易前holderARocBalance :{}".format(holderARocBalance))
        self.logger.info("交易前holderBRocBalance :{}".format(holderBRocBalance))

        # cal_res = contract.functions.estimateROCAmountFromRoUSD(_amountOfROC).call()
        cal_res = self.calROCAmountFromRoUSD(_amountOfRoUSD, price, sold, soldInPreviousLayers)
        self.logger.info("estimateRoUSDAmountFromROC 合约返回:{}".format(cal_res))
        realRoc = cal_res[0]
        self.logger.info("用户实际交易的ROC数量: {}".format(realRoc))

        nonce = self.w3.eth.getTransactionCount(self.account.address)
        now = self.w3.eth.getBlock(self.w3.eth.blockNumber).timestamp
        exc_func = contract.functions.purchaseROCWithExactAmountOfRoUSD(_amountOfRoUSD, _minAmountOfROC, now + deadline)
        self.excuteTransaction(exc_func, nonce)

        time.sleep(10)
        cost2 = contract.functions.cost().call()
        price2 = contract.functions.price().call()
        sold2 = contract.functions.sold().call()
        soldInPreviousLayers2 = contract.functions.soldInPreviousLayers().call()
        self.logger.info("cost :{}".format(cost2))
        self.logger.info("price :{}".format(price2))
        self.logger.info("sold :{}".format(sold2))
        self.logger.info("soldInPreviousLayers :{}".format(soldInPreviousLayers2))
        rousdBalance2 = rousdContract.functions.balanceOf(self.account.address).call()
        rocBalance2 = rocContract.functions.balanceOf(self.account.address).call()
        rousdRRBalance2 = rousdContract.functions.balanceOf(ReserveAddr).call()
        rocRRBalance2 = rocContract.functions.balanceOf(ReserveAddr).call()
        self.logger.info("RR合约 rousdRRBalance :{}".format(rousdRRBalance2))
        self.logger.info("RR合约 rocRRBalance :{}".format(rocRRBalance2))
        self.logger.info("rousdBalance :{}".format(rousdBalance2))
        self.logger.info("rocBalance :{}".format(rocBalance2))

        holderARoUSDBalance2 = rousdContract.functions.balanceOf(HolderTestAAddr).call()
        holderBRoUSDBalance2 = rousdContract.functions.balanceOf(HolderTestBAddr).call()
        holderARocBalance2 = rocContract.functions.balanceOf(HolderTestAAddr).call()
        holderBRocBalance2 = rocContract.functions.balanceOf(HolderTestBAddr).call()
        self.logger.info("交易后holderARoUSDBalance :{}".format(holderARoUSDBalance2))
        self.logger.info("交易后holderBRoUSDBalance :{}".format(holderBRoUSDBalance2))
        self.logger.info("交易后holderARocBalance :{}".format(holderARocBalance2))
        self.logger.info("交易后holderBRocBalance :{}".format(holderBRocBalance2))

        assert cost2 - cost == _amountOfRoUSD, "cost计算不正确"
        assert price2 == cal_res[1], "price计算不正确"
        assert sold2 == cal_res[2], "sold计算不正确"
        assert soldInPreviousLayers2 == cal_res[3], "soldInPreviousLayers计算不正确"

        assert rousdBalance - rousdBalance2 == _amountOfRoUSD, "用户roUsd资产计算不正确"
        assert rocBalance2 - rocBalance == realRoc, "用户roc资产计算不正确"

        if len(holderInfos) > 0:
            expecteHolderA = realRoc // 2 * Shares[0] // self.HOLDER_SHARE_BASE
            expecteHolderB = realRoc // 2 * Shares[1] // self.HOLDER_SHARE_BASE

            assert holderARocBalance - holderARocBalance2 == expecteHolderA, "holderA roc资产计算不正确"
            assert holderBRocBalance - holderBRocBalance2 == expecteHolderB, "holderB roc资产计算不正确"
            assert holderARoUSDBalance2 - holderARoUSDBalance == _amountOfRoUSD // 2 * Shares[0] // self.HOLDER_SHARE_BASE, "holderA roUSD资产计算不正确"
            assert holderBRoUSDBalance2 - holderBRoUSDBalance == _amountOfRoUSD // 2 * Shares[1] // self.HOLDER_SHARE_BASE, "holderA roUSD资产计算不正确"

            assert rousdRRBalance2 - rousdRRBalance - _amountOfRoUSD // 2 <= 1, "RR合约rocusd资产计算不正确:{} {}".format(rousdRRBalance2 - rousdRRBalance, _amountOfRoUSD // 2)
            assert rocRRBalance - rocRRBalance2 == realRoc - expecteHolderA - expecteHolderB, "RR合约roc资产计算不正确, {} {}".format(rocRRBalance - rocRRBalance2, realRoc//2)
            assert realRoc//2 - expecteHolderA - expecteHolderB <= 2, "RR合约roc资产计算不正确, {} {}".format(expecteHolderA + expecteHolderB, realRoc//2)
        else:
            assert rocRRBalance - rocRRBalance2 == realRoc, "RR合约roc资产计算不正确, {} {}".format(rocRRBalance - rocRRBalance2, realRoc)
            assert rousdRRBalance2 - rousdRRBalance == _amountOfRoUSD, "RR合约rocusd资产计算不正确, {} {}".format(rousdRRBalance2 - rousdRRBalance, _amountOfRoUSD)

    def checkGetAveragePriceOfROC(self, contract):
        cost = contract.functions.cost().call()
        sold = contract.functions.sold().call()

        price = contract.functions.getAveragePriceOfROC().call()
        self.logger.info("当前平均价格: {}".format(price))
        expected = cost * self.PRICE_BASE // sold

        assert expected == price, "{} 和 {}不一致".format(price, expected)

    def checkMintExactAmountOfDO(self, contract, _amountOfDo, msgSender=None):
        if msgSender is None:
            msgSender = self.account
        index = 0
        while True:
            try:
                rrContract.functions.loanMap(msgSender.address, index).call()
                index += 1
            except Exception as e:
                if e.args[0]["message"] != "":
                    break
        self.logger.info("查找到的loanMap的最新index: {}".format(index))
        allowance = rocContract.functions.allowance(msgSender.address, ReserveAddr).call()
        userRocBalance = rocContract.functions.balanceOf(msgSender.address).call()
        userDoBalance = doContract.functions.balanceOf(msgSender.address).call()
        rrRocBalance = rocContract.functions.balanceOf(ReserveAddr).call()
        do_total_supply = doContract.functions.totalSupply().call()

        self.logger.info("roc 授权额度: {}".format(allowance))
        self.logger.info("userRocBalance 用户ROC资产: {}".format(userRocBalance))
        self.logger.info("userDoBalance 用户DO资产: {}".format(userDoBalance))
        self.logger.info("rrRocBalance RR合约ROC资产: {}".format(rrRocBalance))
        self.logger.info("doTotalSupply DO的totalSupply: {}".format(do_total_supply))

        avgPrice = contract.functions.getAveragePriceOfROC().call()
        self.logger.info("RR合约ROC和ROUSD的价格: {}".format(avgPrice))
        expectedROC = _amountOfDo * 2 * self.PRICE_BASE // avgPrice
        self.logger.info("要得到的do数量: {}".format(_amountOfDo))
        self.logger.info("计算出来的expectedROC: {}".format(expectedROC))
        self.logger.info("是否会因roc授权数量限制交易导致交易失败: {}".format(allowance < expectedROC))

        reserve_ratio = contract.functions.reserveRatio().call()
        rr_ro_u_sd_balance = rousdContract.functions.balanceOf(ReserveAddr).call()
        expected_rr_do = (do_total_supply + _amountOfDo) * reserve_ratio
        expected_rr_ro_usd = rr_ro_u_sd_balance * self.RATIO_BASE
        add_rr_do = expected_rr_ro_usd // reserve_ratio - do_total_supply
        self.logger.info("最大支持购买DO: {}, 想购买: {}, 结果为: {}".format(add_rr_do, _amountOfDo, expected_rr_do <= expected_rr_ro_usd))
        # self.logger.info("预计经过交易后_checkReserveRatio为参数: do为 {}, RoUSD为 {}, check {}".format(expected_rr_do, expected_rr_ro_usd, expected_rr_do <= expected_rr_ro_usd))

        deadline = self.w3.eth.getBlock(rrClient.w3.eth.blockNumber).timestamp + 600
        self.logger.info("deadline: {}".format(deadline))

        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        exc_func = contract.functions.mintExactAmountOfDO(_amountOfDo, expectedROC, deadline)
        tx_hash = self.excuteTransaction(exc_func, nonce, msgSender)
        tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
        self.logger.info("交易哈希内容: {}".format(tx_info))
        b_time = self.w3.eth.getBlock(tx_info["blockNumber"]).timestamp
        self.logger.info("交易发生的时间戳: {}".format(b_time))

        userRocBalance2 = rocContract.functions.balanceOf(msgSender.address).call()
        userDoBalance2 = doContract.functions.balanceOf(msgSender.address).call()
        rrRocBalance2 = rocContract.functions.balanceOf(ReserveAddr).call()
        doTotalSupply2 = doContract.functions.totalSupply().call()
        loanMap = rrContract.functions.loanMap(rrClient.account.address, index).call()

        self.logger.info("userRocBalance 用户ROC资产: {}".format(userRocBalance2))
        self.logger.info("userDoBalance 用户DO资产: {}".format(userDoBalance2))
        self.logger.info("rrRocBalance RR合约ROC资产: {}".format(rrRocBalance2))
        self.logger.info("doTotalSupply DO的totalSupply: {}".format(doTotalSupply2))
        self.logger.info("Reserve 的loanMap: {}".format(loanMap))

        assert userRocBalance - userRocBalance2 == expectedROC, "用户ROC资产不正确"
        assert userDoBalance2 - userDoBalance == _amountOfDo, "用户DO资产不正确"
        assert rrRocBalance2 - rrRocBalance == expectedROC, "RR持有的ROC资产不正确"
        assert doTotalSupply2 - do_total_supply == _amountOfDo, "DO的totalSupply不正确"

        assert loanMap[0] == b_time, "createAt, 检查不正确"
        assert loanMap[1] == b_time, "updateAt, 检查不正确"
        assert loanMap[2] == expectedROC, "_amountOfROC, 检查不正确"
        assert loanMap[3] == _amountOfDo, "amountOfDO, 检查不正确"

    def checkMintDOWithExactAmountOfROC(self, contract, _amountOfROC, msgSender=None):
        if msgSender is None:
            msgSender = self.account
        index = 0
        while True:
            try:
                rrContract.functions.loanMap(msgSender.address, index).call()
                index += 1
            except Exception as e:
                if e.args[0]["message"] != "":
                    break
        self.logger.info("查找到的loanMap的最新index: {}".format(index))
        allowance = rocContract.functions.allowance(msgSender.address, ReserveAddr).call()
        userRocBalance = rocContract.functions.balanceOf(msgSender.address).call()
        userDoBalance = doContract.functions.balanceOf(msgSender.address).call()
        rrRocBalance = rocContract.functions.balanceOf(ReserveAddr).call()
        do_total_supply = doContract.functions.totalSupply().call()

        self.logger.info("roc 授权额度: {}".format(allowance))
        self.logger.info("userRocBalance 用户ROC资产: {}".format(userRocBalance))
        self.logger.info("userDoBalance 用户DO资产: {}".format(userDoBalance))
        self.logger.info("rrRocBalance RR合约ROC资产: {}".format(rrRocBalance))
        self.logger.info("doTotalSupply DO的totalSupply: {}".format(do_total_supply))

        avgPrice = contract.functions.getAveragePriceOfROC().call()
        self.logger.info("RR合约ROC和ROUSD的价格:{}".format(avgPrice))
        expectedDO = _amountOfROC * avgPrice // self.PRICE_BASE // 2
        self.logger.info("要投入的roc数量: {}".format(_amountOfROC))
        self.logger.info("计算出来的expectedDO: {}".format(expectedDO))

        deadline = self.w3.eth.getBlock(rrClient.w3.eth.blockNumber).timestamp + 600
        self.logger.info("deadline: {}".format(deadline))

        reserve_ratio = contract.functions.reserveRatio().call()
        rr_ro_u_sd_balance = rousdContract.functions.balanceOf(ReserveAddr).call()
        logger.info("Reserve合约持有的roUsd数量: {}".format(rr_ro_u_sd_balance))
        expected_rr_do = (do_total_supply + expectedDO) * reserve_ratio
        expected_rr_ro_usd = rr_ro_u_sd_balance * self.RATIO_BASE
        add_rr_do = expected_rr_ro_usd // reserve_ratio - do_total_supply
        self.logger.info("最大支持购买DO: {}, 想购买: {}, 结果为: {}".format(add_rr_do, expectedDO, expected_rr_do <= expected_rr_ro_usd))

        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        exc_func = contract.functions.mintDOWithExactAmountOfROC(_amountOfROC, expectedDO, deadline)
        tx_hash = self.excuteTransaction(exc_func, nonce, msgSender)
        tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
        self.logger.info("交易哈希内容: {}".format(tx_info))
        b_time = self.w3.eth.getBlock(tx_info["blockNumber"]).timestamp
        self.logger.info("交易发生的时间戳: {}".format(b_time))

        userRocBalance2 = rocContract.functions.balanceOf(msgSender.address).call()
        userDoBalance2 = doContract.functions.balanceOf(msgSender.address).call()
        rrRocBalance2 = rocContract.functions.balanceOf(ReserveAddr).call()
        doTotalSupply2 = doContract.functions.totalSupply().call()
        loanMap = rrContract.functions.loanMap(rrClient.account.address, index).call()

        self.logger.info("userRocBalance 用户ROC资产: {}".format(userRocBalance2))
        self.logger.info("userDoBalance 用户DO资产: {}".format(userDoBalance2))
        self.logger.info("rrRocBalance RR合约ROC资产: {}".format(rrRocBalance2))
        self.logger.info("doTotalSupply DO的totalSupply: {}".format(doTotalSupply2))
        self.logger.info("Reserve 的loanMap: {}".format(loanMap))

        assert userRocBalance - userRocBalance2 == _amountOfROC, "用户ROC资产不正确"
        assert userDoBalance2 - userDoBalance == expectedDO, "用户DO资产不正确"
        assert rrRocBalance2 - rrRocBalance == _amountOfROC, "RR持有的ROC资产不正确"
        assert doTotalSupply2 - do_total_supply == expectedDO, "DO的totalSupply不正确"

        assert loanMap[0] == b_time, "createAt, 检查不正确"
        assert loanMap[1] == b_time, "updateAt, 检查不正确"
        assert loanMap[2] == _amountOfROC, "_amountOfROC, 检查不正确"
        assert loanMap[3] == expectedDO, "amountOfDO, 检查不正确"

    def checkMintExactAmountOfDOWhenAllowanceNotEnough(self, contract, msgSender=None):
        if msgSender is None:
            msgSender = self.account
        index = 0
        while True:
            try:
                rrContract.functions.loanMap(msgSender.address, index).call()
                index += 1
            except Exception as e:
                # print(e.args)
                if e.args[0]["message"] == "VM execution error." or "message" in e.args[0]:
                    break
        self.logger.info("查找到的loanMap的最新index: {}".format(index))
        allowance = rocContract.functions.allowance(msgSender.address, ReserveAddr).call()
        userRocBalance = rocContract.functions.balanceOf(msgSender.address).call()
        userDoBalance = doContract.functions.balanceOf(msgSender.address).call()
        rrRocBalance = rocContract.functions.balanceOf(ReserveAddr).call()
        do_total_supply = doContract.functions.totalSupply().call()

        self.logger.info("roc 授权额度: {}".format(allowance))
        self.logger.info("userRocBalance 用户ROC资产: {}".format(userRocBalance))
        self.logger.info("userDoBalance 用户DO资产: {}".format(userDoBalance))
        self.logger.info("rrRocBalance RR合约ROC资产: {}".format(rrRocBalance))
        self.logger.info("doTotalSupply DO的totalSupply: {}".format(do_total_supply))

        _amountOfDo = allowance + 1
        avgPrice = contract.functions.getAveragePriceOfROC().call()
        self.logger.info("RR合约ROC和ROUSD的价格".format(avgPrice))
        expectedROC = _amountOfDo * 2 * self.PRICE_BASE // avgPrice
        self.logger.info("计算出来的expectedROC: {}".format(expectedROC))
        deadline = self.w3.eth.getBlock(rrClient.w3.eth.blockNumber).timestamp + 600

        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        exc_func = contract.functions.mintExactAmountOfDO(_amountOfDo, expectedROC, deadline)
        try:
            self.excuteTransaction(exc_func, nonce)
        except Exception as e:
            if e.args[0]["message"] == "The execution failed due to an exception.":
                self.logger.info("withdrawRoUSD 由非owner用户{} 执行应该失败:".format(msgSender.address))
                tx_hash = self.excuteTransaction(exc_func, nonce, msgSender, gas=3000000)
                tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
                assert tx_info["status"] == 0, "交易应失败: {}".format(tx_info)

        userRocBalance2 = rocContract.functions.balanceOf(msgSender.address).call()
        userDoBalance2 = doContract.functions.balanceOf(msgSender.address).call()
        rrRocBalance2 = rocContract.functions.balanceOf(ReserveAddr).call()
        doTotalSupply2 = doContract.functions.totalSupply().call()

        self.logger.info("userRocBalance 用户ROC资产: {}".format(userRocBalance2))
        self.logger.info("userDoBalance 用户DO资产: {}".format(userDoBalance2))
        self.logger.info("rrRocBalance RR合约ROC资产: {}".format(rrRocBalance2))
        self.logger.info("doTotalSupply DO的totalSupply: {}".format(doTotalSupply2))

        assert userRocBalance - userRocBalance2 == 0, "用户ROC资产不正确"
        assert userDoBalance2 - userDoBalance == 0, "用户DO资产不正确"
        assert rrRocBalance2 - rrRocBalance2 == 0, "RR持有的ROC资产不正确"
        assert doTotalSupply2 - do_total_supply == 0, "DO的totalSupply不正确"

    def checkMintDOWithExactAmountOfROCWhenAllowanceNotEnough(self, contract, msgSender=None):
        if msgSender is None:
            msgSender = self.account
        index = 0
        while True:
            try:
                rrContract.functions.loanMap(msgSender.address, index).call()
                index += 1
            except Exception as e:
                if e.args[0]["message"] == "VM execution error.":
                    break
        self.logger.info("查找到的loanMap的最新index: {}".format(index))
        allowance = rocContract.functions.allowance(msgSender.address, ReserveAddr).call()
        userRocBalance = rocContract.functions.balanceOf(msgSender.address).call()
        userDoBalance = doContract.functions.balanceOf(msgSender.address).call()
        rrRocBalance = rocContract.functions.balanceOf(ReserveAddr).call()
        do_total_supply = doContract.functions.totalSupply().call()

        self.logger.info("roc 授权额度: {}".format(allowance))
        self.logger.info("userRocBalance 用户ROC资产: {}".format(userRocBalance))
        self.logger.info("userDoBalance 用户DO资产: {}".format(userDoBalance))
        self.logger.info("rrRocBalance RR合约ROC资产: {}".format(rrRocBalance))
        self.logger.info("doTotalSupply DO的totalSupply: {}".format(do_total_supply))

        _amountOfROC = allowance + 1
        avgPrice = contract.functions.getAveragePriceOfROC().call()
        self.logger.info("RR合约ROC和ROUSD的价格".format(avgPrice))
        expectedDO = _amountOfROC * avgPrice // self.PRICE_BASE // 2
        self.logger.info("计算出来的expectedROC: {}".format(expectedDO))

        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        exc_func = contract.functions.mintDOWithExactAmountOfROC(_amountOfROC)
        try:
            self.excuteTransaction(exc_func, nonce, msgSender)
        except Exception as e:
            if e.args[0]["message"] == "The execution failed due to an exception.":
                self.logger.info("withdrawRoUSD 由非owner用户{} 执行应该失败:".format(msgSender.address))
                tx_hash = self.excuteTransaction(exc_func, nonce, msgSender, gas=3000000)
                tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
                assert tx_info["status"] == 0, "交易应失败: {}".format(tx_info)

        userRocBalance2 = rocContract.functions.balanceOf(msgSender.address).call()
        userDoBalance2 = doContract.functions.balanceOf(msgSender.address).call()
        rrRocBalance2 = rocContract.functions.balanceOf(ReserveAddr).call()
        doTotalSupply2 = doContract.functions.totalSupply().call()

        self.logger.info("userRocBalance 用户ROC资产: {}".format(userRocBalance2))
        self.logger.info("userDoBalance 用户DO资产: {}".format(userDoBalance2))
        self.logger.info("rrRocBalance RR合约ROC资产: {}".format(rrRocBalance2))
        self.logger.info("doTotalSupply DO的totalSupply: {}".format(doTotalSupply2))

        assert userRocBalance - userRocBalance2 == 0, "用户ROC资产不正确"
        assert userDoBalance2 - userDoBalance == 0, "用户DO资产不正确"
        assert rrRocBalance2 - rrRocBalance2 == 0, "RR持有的ROC资产不正确"
        assert doTotalSupply2 - do_total_supply == 0, "DO的totalSupply不正确"

    def checkRedeemROC(self, contract, _index, msgSender=None):
        if msgSender is None:
            msgSender = self.account
        index = 0
        while True:
            try:
                rrContract.functions.loanMap(msgSender.address, index).call()
                index += 1
            except Exception as e:
                if e.args[0]["message"] != "":
                    break
        self.logger.info("查找到的loanMap的最新index: {}".format(index))

        loanMap = contract.functions.loanMap(msgSender.address, _index).call()
        self.logger.info("index: {}, loanMap: {}".format(_index, loanMap))
        allowance = doContract.functions.allowance(msgSender.address, ReserveAddr).call()
        self.logger.info("用户授权Reserve的DO的资产: {}".format(allowance))
        userRocBalance = rocContract.functions.balanceOf(msgSender.address).call()
        userDoBalance = doContract.functions.balanceOf(msgSender.address).call()
        rrRocBalance = rocContract.functions.balanceOf(ReserveAddr).call()
        do_total_supply = doContract.functions.totalSupply().call()
        self.logger.info("userRocBalance 用户ROC资产: {}".format(userRocBalance))
        self.logger.info("userDoBalance 用户DO资产: {}".format(userDoBalance))
        self.logger.info("rrRocBalance RR合约ROC资产: {}".format(rrRocBalance))
        self.logger.info("doTotalSupply DO的totalSupply: {}".format(do_total_supply))

        exc_func = contract.functions.redeemROC(_index)
        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        tx_hash = self.excuteTransaction(exc_func, nonce, msgSender)
        tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
        u_time = self.w3.eth.getBlock(tx_info["blockNumber"]).timestamp
        self.logger.info("updateTime: {}".format(u_time))

        loanMap2 = contract.functions.loanMap(msgSender.address, _index).call()
        self.logger.info("redeemROC后, loanMap: {}".format(loanMap2))
        userRocBalance2 = rocContract.functions.balanceOf(msgSender.address).call()
        userDoBalance2 = doContract.functions.balanceOf(msgSender.address).call()
        rrRocBalance2 = rocContract.functions.balanceOf(ReserveAddr).call()
        doTotalSupply2 = doContract.functions.totalSupply().call()
        self.logger.info("userRocBalance 用户ROC资产: {}".format(userRocBalance2))
        self.logger.info("userDoBalance 用户DO资产: {}".format(userDoBalance2))
        self.logger.info("rrRocBalance RR合约ROC资产: {}".format(rrRocBalance2))
        self.logger.info("doTotalSupply DO的totalSupply: {}".format(doTotalSupply2))

        assert userRocBalance2 - userRocBalance == loanMap[2], "用户ROC资产增加不正确"
        assert userDoBalance - userDoBalance2 == loanMap[3], "用户DO资产减少不正确"
        assert rrRocBalance - rrRocBalance2 == loanMap[2], "Reserve合约ROC资产减少不正确"
        assert do_total_supply - doTotalSupply2 == loanMap[3], "DO合约的totalSupply减少不正确"

        assert loanMap2[2] == 0, "redeem后，loanMap中ROC记录应为0"
        assert loanMap2[3] == 0, "redeem后，loanMap中DO记录应为0"
        assert loanMap2[1] == u_time, "redeem后，loanMap中updateTime更新不正确"

    def checkWithdrawRoUSD(self, contract, amount, msgSender=None):
        if msgSender is None:
            msgSender = self.account

        rrRoUSDBalance = rousdContract.functions.balanceOf(ReserveAddr).call()
        userRoUSDBalance = rousdContract.functions.balanceOf(msgSender.address).call()
        self.logger.info("Reserve RoUSD的持有量: {}".format(rrRoUSDBalance))
        self.logger.info("用户 RoUSD的持有量: {}".format(userRoUSDBalance))

        exc_func = contract.functions.withdrawRoUSD(amount)
        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        self.excuteTransaction(exc_func, nonce, msgSender)

        rrRoUSDBalance2 = rousdContract.functions.balanceOf(ReserveAddr).call()
        userRoUSDBalance2 = rousdContract.functions.balanceOf(msgSender.address).call()
        self.logger.info("Reserve RoUSD的持有量: {}".format(rrRoUSDBalance2))
        self.logger.info("用户 RoUSD的持有量: {}".format(userRoUSDBalance2))

        assert rrRoUSDBalance - rrRoUSDBalance2 == amount, "Reserve合约 RoUSD资产计算不正确"
        assert userRoUSDBalance2 - userRoUSDBalance == amount, "用户 RoUSD资产计算不正确"

    def checkHolderWithdrawRoUSD(self, holderAddr):
        contract = self.get_contract(holderAddr, abi_file="./abi/Holder.json")

        HolderRoUSDBalance = rousdContract.functions.balanceOf(holderAddr).call()
        userRoUSDBalance = rousdContract.functions.balanceOf(self.account.address).call()

        self.logger.info("Holder地址持有的RoUSD资产: {}".format(HolderRoUSDBalance))
        self.logger.info("用户持有的RoUSD资产: {}".format(userRoUSDBalance))

        exc_func = contract.functions.withdrawRoUSD()
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        self.excuteTransaction(exc_func, nonce)

        HolderRoUSDBalance2 = rousdContract.functions.balanceOf(holderAddr).call()
        userRoUSDBalance2 = rousdContract.functions.balanceOf(self.account.address).call()

        self.logger.info("Holder地址持有的RoUSD资产: {}".format(HolderRoUSDBalance2))
        self.logger.info("用户持有的RoUSD资产: {}".format(userRoUSDBalance2))

        assert HolderRoUSDBalance2 == 0, "提现后，Holder持有RoUSD不正确"
        assert userRoUSDBalance2 - userRoUSDBalance == HolderRoUSDBalance, "提现后，用户持有RoUSD不正确"

    def checkHolderWithdrawRoUSDCalldeNotOwner(self, holderAddr, msgSender):
        contract = self.get_contract(holderAddr, abi_file="./abi/Holder.json")

        HolderRoUSDBalance = rousdContract.functions.balanceOf(holderAddr).call()
        userRoUSDBalance = rousdContract.functions.balanceOf(self.account.address).call()
        owner = contract.functions.owner().call()
        self.logger.info("Holder地址持有的RoUSD资产: {}".format(HolderRoUSDBalance))
        self.logger.info("用户持有的RoUSD资产: {}".format(userRoUSDBalance))

        exc_func = contract.functions.withdrawRoUSD()
        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        try:
            self.excuteTransaction(exc_func, nonce, msgSender)
        except Exception as e:
            if owner != msgSender.address and e.args[0]["message"] == "The execution failed due to an exception.":
                self.logger.info("withdrawRoUSD 由非owner用户{} 执行应该失败:".format(msgSender.address))
                tx_hash = self.excuteTransaction(exc_func, nonce, msgSender, gas=3000000)
                tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
                assert tx_info["status"] == 0, "交易应失败: {}".format(tx_info)

        HolderRoUSDBalance2 = rousdContract.functions.balanceOf(holderAddr).call()
        userRoUSDBalance2 = rousdContract.functions.balanceOf(self.account.address).call()

        self.logger.info("Holder地址持有的RoUSD资产: {}".format(HolderRoUSDBalance2))
        self.logger.info("用户持有的RoUSD资产: {}".format(userRoUSDBalance2))

        assert HolderRoUSDBalance2 == HolderRoUSDBalance, "提现后，Holder持有RoUSD不正确"
        assert userRoUSDBalance2 - userRoUSDBalance == 0, "提现后，用户持有RoUSD不正确"

    def checkHolderDelegate(self, holderAddr, delegateTo=None):
        contract = self.get_contract(holderAddr, abi_file="./abi/Holder.json")

        if delegateTo is None:
            delegateTo = self.account.address
        delegates = rocContract.functions.delegates(holderAddr).call()
        self.logger.info("当前Holder delegates: {}".format(delegates))
        votes = rocContract.functions.getCurrentVotes(delegateTo).call()
        self.logger.info("当前 delegateTo用户的投票: {}".format(votes))
        numCheckpoints = rocContract.functions.numCheckpoints(delegateTo).call()
        totalSupply = rocContract.functions.totalSupply().call()
        userBalance = rocContract.functions.balanceOf(holderAddr).call()
        self.logger.info("delegate 之前的资产: {}".format(userBalance))
        self.logger.info("delegate 之前的totalSupply: {}".format(totalSupply))
        self.logger.info("delegate 之前的numCheckpoints: {}".format(numCheckpoints))
        index = 0 if numCheckpoints == 0 else numCheckpoints - 1
        checkPoints = rocContract.functions.checkpoints(delegateTo, index).call()
        self.logger.info("delegate 之前最新的checkPoints为: {}".format(checkPoints))

        exc_func = contract.functions.delegate(delegateTo)
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        tx_hash = self.excuteTransaction(exc_func, nonce)
        tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
        print(tx_info)

        totalSupply2 = rocContract.functions.totalSupply().call()
        userBalance2 = rocContract.functions.balanceOf(holderAddr).call()
        numCheckpoints2 = rocContract.functions.numCheckpoints(delegateTo).call()
        votes2 = rocContract.functions.getCurrentVotes(delegateTo).call()
        self.logger.info("delegate 之后用户的投票: {}".format(votes2))
        self.logger.info("delegate 之后的资产: {}".format(userBalance2))
        self.logger.info("delegate 之后的totalSupply: {}".format(totalSupply2))
        self.logger.info("delegate 之后的numCheckpoints2: {}".format(numCheckpoints2))

        index2 = 0 if numCheckpoints2 == 0 else numCheckpoints2 - 1
        checkPoints2 = rocContract.functions.checkpoints(delegateTo, index2).call()
        self.logger.info("delegate 之前最新的checkPoints为: {}".format(checkPoints2))

        assert votes2 - votes == userBalance, "vote 计算不正确"
        assert userBalance - userBalance2 == 0, "burn之后, 用户资产检查失败"
        assert totalSupply - totalSupply2 == 0, "burn之后totalSupply检查失败"
        assert numCheckpoints2 - numCheckpoints == 1, "numCheckpoints 检查不正确"

        time.sleep(10)
        priorVotes = rocContract.functions.getPriorVotes(delegateTo, tx_info["blockNumber"] - 10).call()
        priorVotes2 = rocContract.functions.getPriorVotes(delegateTo, tx_info["blockNumber"]).call()
        priorVotes3 = rocContract.functions.getPriorVotes(delegateTo, tx_info["blockNumber"] + 1).call()
        self.logger.info("{} {} {}".format(priorVotes, priorVotes2, priorVotes3))
        assert priorVotes3 == priorVotes2, "priorVotes 计算不正确"
        assert priorVotes2 - priorVotes == userBalance, "priorVotes 计算不正确"

    @staticmethod
    def getReverse():
        res = pairContract.functions.getReserves().call()
        token0 = pairContract.functions.token0().call()
        if token0 == DOAddr:
            return res[0], res[1]
        else:
            return res[1], res[0]

    def checkCanInflate(self, contract):
        reverseDo, reverseRoUSD = self.getReverse()

        self.logger.info("do reverse: {}".format(reverseDo))
        self.logger.info("roUsd reverse: {}".format(reverseRoUSD))
        inflationThreshold = contract.functions.inflationThreshold().call()
        inflationTarget = contract.functions.inflationTarget().call()
        inflationUntil = contract.functions.inflationUntil().call()

        self.logger.info("合约中 inflationThreshold: {}".format(inflationThreshold))
        self.logger.info("合约中 inflationTarget: {}".format(inflationTarget))
        self.logger.info("合约中 inflationUntil: {}".format(inflationUntil))
        r = contract.functions.canInflate().call()

        self.logger.info("当前价格 {}".format(reverseRoUSD / reverseDo))
        self.logger.info("cal RoUSD: {}".format(reverseRoUSD * self.RATIO_BASE))
        self.logger.info("cal DO: {}".format(reverseDo * inflationThreshold))
        self.logger.info("cal DO target: {}".format(reverseDo * inflationThreshold))
        con1 = reverseRoUSD * self.RATIO_BASE > reverseDo * inflationThreshold
        con2 = reverseRoUSD * self.RATIO_BASE > reverseDo * inflationTarget and int(time.time()) < inflationUntil
        self.logger.info("con1判断是否超过阈值: {}".format(con1))
        self.logger.info("con2判断是否超过阈值: {}".format(con2))
        res = con1 or con2
        assert r == res, "canInflate 不正确"

    def checkCanDeflate(self, contract):
        reverseDo, reverseRoUSD = self.getReverse()

        self.logger.info("do reverse: {}".format(reverseDo))
        self.logger.info("roUsd reverse: {}".format(reverseRoUSD))
        deflationThreshold = contract.functions.deflationThreshold().call()
        deflationTarget = contract.functions.deflationTarget().call()
        deflationUntil = contract.functions.deflationUntil().call()

        self.logger.info("合约中 deflationThreshold: {}".format(deflationThreshold))
        self.logger.info("合约中 deflationTarget: {}".format(deflationTarget))
        self.logger.info("合约中 deflationUntil: {}".format(deflationUntil))
        r = contract.functions.canDeflate().call()

        self.logger.info("当前价格 {}".format(reverseRoUSD / reverseDo))
        self.logger.info("cal RoUSD: {}".format(reverseRoUSD * self.RATIO_BASE))
        self.logger.info("cal DO: {}".format(reverseDo * deflationThreshold))
        self.logger.info("cal DO target: {}".format(reverseDo * deflationTarget))
        con1 = reverseRoUSD * self.RATIO_BASE < reverseDo * deflationThreshold
        con2 = reverseRoUSD * self.RATIO_BASE < reverseDo * deflationTarget and int(time.time()) < deflationUntil
        self.logger.info("con1判断是否超过阈值: {}".format(con1))
        self.logger.info("con2判断是否超过阈值: {}".format(reverseRoUSD * self.RATIO_BASE < reverseDo * deflationTarget))
        self.logger.info("con2判断是否超过阈值: {}".format(con2))
        assert r == (con1 or con2), "canInflate 不正确"

    def uniswapSwapExactTokensForTokens(self, tokenPath, amount):

        reserveDo, reserveRoUSD = self.getReverse()

        self.logger.info("DO: {}, RoUSD: {}".format(reserveDo,  reserveRoUSD))
        amountB = routerContract.functions.getAmountsOut(amount, tokenPath).call()
        self.logger.info("预计得到的数量: {}".format(amountB))

        deadLine = int(time.time()) + 300
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        exc_func = routerContract.functions.swapExactTokensForTokens(amount, 0, tokenPath, self.account.address, deadLine)
        self.excuteTransaction(exc_func, nonce)

        reserveDo2, reserveRoUSD2 = self.getReverse()
        self.logger.info("DO: {}, RoUSD: {}".format(reserveDo2, reserveRoUSD2))

    def uniswapAddLiquidity(self, amount):

        deadLine = int(time.time()) + 300
        nonce = self.w3.eth.getTransactionCount(self.account.address)
        exc_func = routerContract.functions.addLiquidity(DOAddr, RoUSDAddr, amount, amount, 0, 0, self.account.address, deadLine)
        self.excuteTransaction(exc_func, nonce)

        reserveDo2, reserveRoUSD2 = self.getReverse()
        self.logger.info("DO: {}, RoUSD: {}".format(reserveDo2, reserveRoUSD2))

    def checkInflat(self, contract, msgSender=None):
        if msgSender is None:
            msgSender = self.account

        rrRoUSDBalance = rousdContract.functions.balanceOf(ReserveAddr).call()
        rrDOBalance = doContract.functions.balanceOf(ReserveAddr).call()
        dodoTotalSupply = doContract.functions.totalSupply().call()
        userDoBalance = doContract.functions.balanceOf(msgSender.address).call()
        self.logger.info("reserve合约RoUSD资产: {}".format(rrRoUSDBalance))
        self.logger.info("reserve合约ROC资产: {}".format(rrDOBalance))
        self.logger.info("DO合约的totalSupply: {}".format(dodoTotalSupply))
        self.logger.info("DO合约的totalSupply: {}".format(userDoBalance))

        indStep = contract.functions.indStep().call()
        indIncentive = contract.functions.indIncentive().call()
        indIncentiveLimit = contract.functions.indIncentiveLimit().call()
        reserveDo, reserveRoUSD = self.getReverse()
        self.logger.info("uni pair中DO和RpUSD资产分别为: {}, {}".format(reserveDo, reserveRoUSD))
        self.logger.info("将要调整的比例: {}".format(indStep))
        self.logger.info("奖励DO的比例: {}".format(indIncentive))
        self.logger.info("奖励DO的限制: {}".format(indIncentiveLimit))

        amountOfDoToInflate = reserveDo * indStep // self.RATIO_BASE
        incentive = amountOfDoToInflate * indIncentive // self.RATIO_BASE
        incentive = indIncentiveLimit if incentive > indIncentiveLimit else incentive
        self.logger.info("预计将要调整的DO数量为: {}".format(amountOfDoToInflate))
        self.logger.info("预计调整后可以得到的奖励DO数量为: {}".format(incentive))

        amountOfRoUSD = routerContract.functions.getAmountsOut(amountOfDoToInflate, [DOAddr, RoUSDAddr]).call()
        self.logger.info("预计得到RoUSD的数量: {}".format(amountOfRoUSD))

        deadLine = int(time.time()) + 3000
        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        exc_func = contract.functions.inflate(deadLine)
        tx_hash = self.excuteTransaction(exc_func, nonce, msgSender)
        tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
        n_time = self.w3.eth.getBlock(tx_info["blockNumber"]).timestamp

        rrRoUSDBalance2 = rousdContract.functions.balanceOf(ReserveAddr).call()
        rrDOBalance2 = doContract.functions.balanceOf(ReserveAddr).call()
        dodoTotalSupply2 = doContract.functions.totalSupply().call()
        userDoBalance2 = doContract.functions.balanceOf(msgSender.address).call()

        inflationLast = contract.functions.inflationLast().call()
        self.logger.info("reserve合约RoUSD资产: {}".format(rrRoUSDBalance2))
        self.logger.info("reserve合约DO资产: {}".format(rrDOBalance2))
        self.logger.info("DO合约的totalSupply: {}".format(dodoTotalSupply2))
        self.logger.info("用户的DO资产: {}".format(userDoBalance2))
        self.logger.info("inflationLast: {}".format(inflationLast))

        assert rrRoUSDBalance2 - rrRoUSDBalance == amountOfRoUSD[-1], "Reserve得到的RoUSD数量不正确: {} {}".format(rrRoUSDBalance2 - rrRoUSDBalance, amountOfRoUSD)
        assert rrDOBalance2 - rrDOBalance == 0, "Reserve Do数量应不变"
        assert userDoBalance2 - userDoBalance == incentive, "用户领取的DO奖励不对"
        assert dodoTotalSupply2 - dodoTotalSupply == incentive + amountOfDoToInflate, "DO的totalSupply不对"
        assert inflationLast == n_time, "inflationLast 不正确"

    def checkDeflate(self, contract, msgSender=None):
        if msgSender is None:
            msgSender = self.account

        rrRoUSDBalance = rousdContract.functions.balanceOf(ReserveAddr).call()
        rrDOBalance = doContract.functions.balanceOf(ReserveAddr).call()
        dodoTotalSupply = doContract.functions.totalSupply().call()
        userDoBalance = doContract.functions.balanceOf(msgSender.address).call()
        self.logger.info("reserve合约RoUSD资产: {}".format(rrRoUSDBalance))
        self.logger.info("reserve合约ROC资产: {}".format(rrDOBalance))
        self.logger.info("DO合约的totalSupply: {}".format(dodoTotalSupply))
        self.logger.info("用户的DO资产: {}".format(userDoBalance))

        indStep = contract.functions.indStep().call()
        indIncentive = contract.functions.indIncentive().call()
        indIncentiveLimit = contract.functions.indIncentiveLimit().call()
        reserveDo, reserveRoUSD = self.getReverse()
        self.logger.info("uni pair中DO和RpUSD资产分别为: {}, {}".format(reserveDo, reserveRoUSD))
        self.logger.info("将要调整的比例: {}".format(indStep))
        self.logger.info("奖励DO的比例: {}".format(indIncentive))
        self.logger.info("奖励DO的限制: {}".format(indIncentiveLimit))

        amountRoUSDToSwap = reserveRoUSD * indStep // self.RATIO_BASE
        amountRoUSDToSwap = amountRoUSDToSwap if amountRoUSDToSwap <= rrRoUSDBalance else rrRoUSDBalance
        amounts = routerContract.functions.getAmountsOut(amountRoUSDToSwap, [RoUSDAddr, DOAddr]).call()

        incentive = amounts[-1] * indIncentive // self.RATIO_BASE
        incentive = indIncentiveLimit if incentive > indIncentiveLimit else incentive

        self.logger.info("预计将要调整的RoUSD数量为: {}".format(amountRoUSDToSwap))
        self.logger.info("预计调整后可以得到的奖励DO数量为: {}".format(incentive))
        self.logger.info("预计的结果: {}".format(amounts))

        deadLine = int(time.time()) + 300
        nonce = self.w3.eth.getTransactionCount(msgSender.address)
        exc_func = contract.functions.deflate(deadLine)
        tx_hash = self.excuteTransaction(exc_func, nonce, msgSender)
        tx_info = self.w3.eth.getTransactionReceipt(tx_hash)
        n_time = self.w3.eth.getBlock(tx_info["blockNumber"]).timestamp

        rrRoUSDBalance2 = rousdContract.functions.balanceOf(ReserveAddr).call()
        rrDOBalance2 = doContract.functions.balanceOf(ReserveAddr).call()
        dodoTotalSupply2 = doContract.functions.totalSupply().call()
        userDoBalance2 = doContract.functions.balanceOf(msgSender.address).call()

        deflationLast = contract.functions.deflationLast().call()
        self.logger.info("reserve合约RoUSD资产: {}".format(rrRoUSDBalance2))
        self.logger.info("reserve合约DO资产: {}".format(rrDOBalance2))
        self.logger.info("DO合约的totalSupply: {}".format(dodoTotalSupply2))
        self.logger.info("用户的DO资产: {}".format(userDoBalance2))
        self.logger.info("deflationLast: {}".format(deflationLast))

        reserveDo2, reserveRoUSD2 = self.getReverse()
        self.logger.info("当前价格为: {}".format(reserveRoUSD2/reserveDo2))

        assert rrDOBalance2 - rrDOBalance == 0, "Reserve Do数量应不变"
        assert userDoBalance2 - userDoBalance == incentive, "用户领取的DO奖励不对"
        assert dodoTotalSupply - dodoTotalSupply2 == amounts[-1] - incentive, "DO的totalSupply不对"
        assert deflationLast == n_time, "deflationLast 不正确"
        assert rrRoUSDBalance - rrRoUSDBalance2 == amountRoUSDToSwap, "Reserve得到的RoUSD数量不正确: {} {}".format(rrRoUSDBalance2 - rrRoUSDBalance, amountRoUSDToSwap)


# 数据部分
RPC_ADDRESS = 'https://kovan.infura.io/v3/be5b825be13b4dda87056e6b073066dc'
# RPC_ADDRESS = 'https://ropsten.infura.io/v3/be5b825be13b4dda87056e6b073066dc'

PRIVATE_KEY = "ebed55a1f7e77144623167245abf39df053dc76fd8118ac7ae6e1ceeb84c5ed0"

gasPrice = 1000000000  # 1gwei
# logger 的名字设置为'web3.RequestManager'是为了获取web3执行的日志信息
logger = setCustomLogger("web3.RequestManager", os.path.join(curPath, "./doTest.log"), isprintsreen=True, level=logging.INFO)

# RoUSDAddr = "0x513a2C89F857362979BE6991A7bEC76DE6e9eDb3"
# RoUSDAddr = "0x4fC9D3c7361A9856340e230522f33ba2a6137dbf"
# RoUSDAddr = "0xDbA488b4Ea456d5067FF724937C2B4bAF3Fc2636"
# RoUSDAddr = "0xA66c32411963786CbaA0402CB4eF521a5a492468"
RoUSDAddr = "0x189d4a077C3a24740A15662016A05b04B8393373"

# ROCAddr = "0x879C03805c2DDE4c0fdf659eD7eAB172E81D8E48"
# ROCAddr = "0x4285E68fba3fa5787209d135767762A7E874d5e7"
# ROCAddr = "0x74577B5163660F17Ba10F22645F7A8cf739c12a0"
# ROCAddr = "0x82B6E11f3eE2869D5187A7968616f926b9172ec2"
# ROCAddr = "0x36BaA33c2Ab31cB533b2a58802A92F94bfF6cacb"
ROCAddr = "0x19f152aC3AA449b5F92c37375430A7ce385Be47d"

# DOAddr = "0xC01c3810Ec3e48Aa341D13cE912A23FA11692Dba"
# DOAddr = "0x91fb91f6033C19C9275f3148cF2985369C943F69"
# DOAddr = "0x62eA212726BD0Bd8f19969FD1E1AEE6E164A5123"
# DOAddr = "0xb7E70fc41D4D8Fa6c8a6087A979d8FCDeb71f6eE"
DOAddr = "0xD8Fc4d815aD4f9F6022d14f0BEd96F6C40007d2f"

# ReserveAddr = "0x5901419bA436d21c9693ff06103edf1E283C4798"
# ReserveAddr = "0x1BeaA816AeB589271F31EC9968ee7b020B19E437"
# ReserveAddr = "0xdE02583Cdd60901275AA9B0a04b998CC40a7eC1f"
# ReserveAddr = "0x5B87A4F5bf5FC7E94177c9f6313572E6d0e55402"
# ReserveAddr = "0xc2264471ff7E195d97465fed4c6D5b1ae8e78347"
ReserveAddr = "0x613dEF6f85001eA2b0a25E32AB5D61Ff309c8Eaf"  # 修改setInitPrice后重新发布

layerManagerAddr = "0x2eFC40229CC7f9FA9788Fd61c0a03Ef2Ef7A0a38"

usdtAddr = "0x2Bc66b06e0741B4AdFBAC6F3297Abb9AE110a240"
usdcAddr = "0x7677d0FB9a708F72bAe5f0631Ef42CBbD401a45b"

# uniswap

# routerAddr = "0x0b55864274ef4c0C0A686815A32e4D078691FC3c"
# routerAddr = "0x1C7B830459d6136bbd5c5290075Af48Dd79c8f27"
# routerAddr = "0xc271737BCBCb380eFc610F442C427570F5B3F643"
routerAddr = "0x07CC5D7DB9dc57422AE92a2e828A5B488b8A70cc"
# factoryAddr = "0x27F567e4fD472CC7Aac1Cb216eeBa596ebD65688"
# factoryAddr = "0xf297A34c226603b7D3409961412948378FAa0429"
# factoryAddr = "0x260Eed41776c2A80998a7C7bFD6397CB39F2ffd3"
factoryAddr = "0x1e4a8782fC1054e90900802a1Ab34fb94ef3CF75"
# RoUSDDoPair = "0x08E4F8D405923328bd11c8c42A22451CFAE1A19a"
# RoUSDDoPair = "0xafb9d0a44aa652335DdF47E18B454814061b4689"
# RoUSDDoPair = "0x349b4867Fe8b6079fdCc8484362E1ABD649943B5"
RoUSDDoPair = "0xab951FF0546Ec6be7ff0aCD7f1599676b37D8Ff8"

# HolderTestAAddr = "0xAD43E7AA474Ab9111c7d5F435429C9A092572321"
# HolderTestAAddr = "0x1Dd16bC783496b9303373a17a2F0Fa24Dc84285D"
# HolderTestAAddr = "0x9854B4Fb43E19494752eCd7F7D52d829Fd7858A0"
# HolderTestAAddr = "0x5a0b2bcb5DDcB89Ac7cec50D53E9161A44E19053"
HolderTestAAddr = "0x68E5444054B79c11ceBBe3C32dB943976100F8Fa"
# HolderTestBAddr = "0x4d7fa4137eaE1bf7A007eff70188f61B96Dd85ed"
# HolderTestBAddr = "0x52897E24cffAfD28ef99E9b18b812cCC15E5BBec"
# HolderTestBAddr = "0x615cD3B6E0cE145cA67bA2b374E02b28841259E2"
# HolderTestBAddr = "0x160A90B8A3fD1B8b280679D35AD7f6FA95be4C21"
HolderTestBAddr = "0xD4b53FBb773AD28e114C96cab4c59D6b152E0D13"

Holders = [HolderTestAAddr, HolderTestBAddr]
Shares = [4321, 5679]

if __name__ == "__main__":

    doClient = DOTest(RPC_ADDRESS, PRIVATE_KEY, logger)

    account2_private_key = "ad246d5896fd96c40595ff58e6e2a8bd23ffb31e95b1fb786a9034d2df120492"
    account2 = doClient.w3.eth.account.privateKeyToAccount(account2_private_key)

    doContract = doClient.get_contract(DOAddr, "./abi/DO.json")
    rocContract = doClient.get_contract(ROCAddr, "./abi/ROC.json")
    rousdContract = doClient.get_contract(RoUSDAddr, "./abi/RoUSD.json")
    rrContract = doClient.get_contract(ReserveAddr, "./abi/Reserve.json")
    # print(doContract.functions.totalSupply().call())
    # ######################## 测试DO ########################
    # doClient.checkApprove(doContract, account2.address, 1000)
    # doClient.checkIncreaseAllowance(doContract, account2.address, 1000)
    # doClient.checkDecreaseAllowance(doContract, account2.address, 1910)

    # doClient.checkMint(doContract, client.account.address, 100)
    # doClient.checkMint(doContract, client.account.address, 0)
    # doClient.checkMint(doContract, client.account.address, client.w3.toWei(1, "ether"))
    # doClient.checkMint(doContract, client.account.address, client.w3.toWei(10, "ether"))
    # doClient.checkMint(doContract, client.account.address, client.w3.toWei(100, "ether"))
    # doClient.checkMint(doContract, client.account.address, client.w3.toWei(1000, "ether"))
    # doClient.checkMint(doContract, client.account.address, client.w3.toWei(100000000000, "ether"))
    # doClient.checkMintWhenMsgSenderIsNotIssuer(doContract, client.account.address, 10, account2)
    # doClient.checkTransfer(doContract, account2.address, 10)
    # doClient.checkTransferAmountIs0(doContract, account2.address)
    # doClient.checkTransferAmountExceedFromAccountBalance(doContract, account2.address)
    # doClient.checkTransferFrom(doContract, account2, 5)
    # doClient.checkTransferFrom(doContract, account2, 0)
    # doClient.checkTransferFromAmountExceedAllowance(doContract, account2)

    # doClient.checkTransferOwnerShip(doContract, client.account, account2.address)
    # doClient.checkTransferOwnerShip(doContract, account2, client.account.address)

    # doClient.checkTransferOwnerShip(doContract, doClient.account, ReserveAddr)

    # doClient.checkBurn(doContract, 5)
    # doClient.checkBurn(doContract, client.w3.toWei(1, "ether"))
    # doClient.checkBurn(doContract, client.w3.toWei(10, "ether"))
    # doClient.checkBurn(doContract, client.w3.toWei(100, "ether"))
    # doClient.checkBurn(doContract, client.w3.toWei(1000, "ether"))
    # doClient.checkBurn(doContract, client.w3.toWei(100000000000, "ether"))
    # doClient.checkBurn(doContract, 15, account2)
    # doClient.checkBurnAmountExceedUserBalance(doContract)

    # doClient.checkBurnFrom(doContract, client.account, 0, account2)
    # doClient.checkBurnFrom(doContract, client.account, 5, account2)
    # doClient.checkBurnFromAmountExceedAllowance(doContract, client.account, account2)
    # doClient.checkBurnFrom(doContract, client.account, 50, account2)
    # doClient.checkBurnFrom(doContract, client.account, 5, account2)

    # ######################## 测试ROC ########################
    rocClient = ROCTest(RPC_ADDRESS, PRIVATE_KEY, logger)

    # print(rocContract.functions.totalSupply().call())
    # print(rocContract.functions.balanceOf(rocClient.account.address).call())
    # print(rocClient.w3.toWei(int(math.pow(10, 10)), "ether"))
    # print(rocContract.functions.balanceOf(account2.address).call())
    # print(rocContract.functions.balanceOf(ReserveAddr).call())
    # print(rocContract.functions.issuerMap(rocClient.account.address).call())

    # rocClient.checkMintWhenNotStart(rocContract, account2.address, 0)
    # rocClient.checkMintWhenMsgSenderIsNotIssuer(rocContract, account2.address, 10, account2)
    # rocClient.checkStartWhenMsgSenderIsNotOwner(rocContract, rocClient.account.address, account2)
    # rocClient.checkSetIssuer(rocContract, rocClient.account.address, True)
    # rocClient.checkStart(rocContract, rocClient.account.address)
    # rocClient.checkStartWhenStarted(rocContract, rocClient.account.address)
    # rocClient.checkMintWhenLessTimeToMintMore(rocContract, rocClient.account.address, 10)
    # rocClient.checkBurn(rocContract, 0)

    # rocClient.checkBurn(rocContract, client.w3.toWei(1, "ether"))

    # rocClient.checkApprove(rocContract, account2.address, 1000)
    # rocClient.checkIncreaseAllowance(rocContract, account2.address, 1000)
    # rocClient.checkDecreaseAllowance(rocContract, account2.address, 1900)

    # rocClient.checkTransfer(rocContract, rocClient.account.address, 1000, account2)
    # rocClient.checkTransfer(rocContract, account2.address, 1000)
    # rocClient.checkTransfer(rocContract, account2.address, rocClient.w3.toWei(10, "ether"))
    # rocClient.checkTransferAmountIs0(rocContract, account2.address)
    # rocClient.checkTransferAmountExceedFromAccountBalance(rocContract, account2.address)
    # rocClient.checkTransferFrom(rocContract, account2, 5)
    # rocClient.checkTransferFrom(rocContract, account2, 0)
    # rocClient.checkTransferFromAmountExceedAllowance(rocContract, account2)
    # rocClient.checkTransferFrom(rocContract, ReserveAddr, 4000000000000000000000000000)

    # 等timeToMintMore后才能执行
    # rocClient.checkMint(rocContract, rocClient.account.address, 80)
    # rocClient.checkMint(rocContract, rocClient.account.address, 0)
    # rocClient.checkMint(rocContract, account2.address, 10)
    # rocClient.checkMint(rocContract, rocClient.account.address, rocClient.w3.toWei(1, "ether"))
    # rocClient.checkMint(rocContract, rocClient.account.address, client.w3.toWei(10, "ether"))
    # rocClient.checkMint(rocContract, rocClient.account.address, client.w3.toWei(100, "ether"))
    # rocClient.checkMint(rocContract, rocClient.account.address, rocClient.w3.toWei(1000, "ether"))
    # rocClient.checkMint(rocContract, rocClient.account.address, client.w3.toWei(100000000000, "ether"))
    # rocClient.checkMintWhenMsgSenderIsNotIssuer(rocContract, client.account.address, 10, account2)

    # rocClient.checkTransferOwnerShip(rocContract, client.account, account2)
    # rocClient.checkTransferOwnerShip(rocContract, account2, client.account)

    # rocClient.checkBurn(rocContract, 90000000000000000000000000000)
    # rocClient.checkBurn(rocContract, 1000)
    # rocClient.checkBurn(rocContract, rocClient.w3.toWei(1, "ether"))
    # rocClient.checkBurn(rocContract, rocClient.w3.toWei(10, "ether"))
    # rocClient.checkBurn(rocContract, rocClient.w3.toWei(100, "ether"))
    # rocClient.checkBurn(rocContract, rocClient.w3.toWei(1000, "ether"))
    # rocClient.checkBurn(rocContract, rocClient.w3.toWei(10000, "ether"))
    # rocClient.checkBurn(rocContract, rocClient.w3.toWei(100000, "ether"))
    # rocClient.checkBurn(rocContract, 15, account2)
    # rocClient.checkBurnAmountExceedUserBalance(rocContract)

    # rocClient.checkDelegate(rocContract, client.account.address, account2)
    # rocClient.checkDelegate(rocContract, account2.address, account2)
    # rocClient.checkDelegate(rocContract, "0x0000000000000000000000000000000000000000", account2)
    # rocClient.checkDelegate(rocContract, DOAddr, account2)
    # rocClient.checkDelegate(rocContract, DOAddr, client.account)

    # rocClient.checkBurn(rocContract, 5, account2)
    # rocClient.checkBurn(rocContract, client.w3.toWei(1, "ether") - 5, account2)
    # rocClient.checkBurn(rocContract, client.w3.toWei(1, "ether"), account2)

    # ######################## 测试RoUSD ########################
    rousdClient = RoUSDTest(RPC_ADDRESS, PRIVATE_KEY, logger)

    # rousdClient.checkSetIssuer(rousdContract, rousdClient.account.address, True)
    # rousdClient.checkSetIssuer(rousdContract, rousdClient.account.address, False)
    # rousdClient.checkSetIssuerCalledByNotOwner(rousdContract, rousdClient.account.address, True, account2)

    # rousdClient.checkApprove(rousdContract, account2.address, 1000)
    # rousdClient.checkApprove(rousdContract, account2.address, 1000)
    # rousdClient.checkIncreaseAllowance(rousdContract, account2.address, 1000)
    # rousdClient.checkDecreaseAllowance(rousdContract, account2.address, 1900)

    # print(rousdContract.functions.decimals().call())
    # rousdClient.checkMint(rousdContract, rousdClient.account.address, 100)
    # rousdClient.checkMint(rousdContract, client.account.address, 0)
    # rousdClient.checkMint(rousdContract, rousdClient.account.address, rousdClient.w3.toWei(1, "ether"))
    # rousdClient.checkMint(rousdContract, ReserveAddr, rousdClient.w3.toWei(10000, "ether"))
    # rousdClient.checkMint(rousdContract, client.account.address, client.w3.toWei(10, "ether"))
    # rousdClient.checkMint(rousdContract, rousdClient.account.address, rousdClient.w3.toWei(100, "ether"))
    # rousdClient.checkMint(rousdContract, rousdClient.account.address, rousdClient.w3.toWei(50000, "ether"))
    # rousdClient.checkMint(rousdContract, client.account.address, client.w3.toWei(100000000000, "ether"))
    # rousdClient.checkMintWhenMsgSenderIsNotIssuer(rousdContract, client.account.address, 10, account2)

    # rousdClient.checkTransfer(rousdContract, account2.address, 100)
    # rousdClient.checkTransferAmountIs0(rousdContract, account2.address)
    # rousdClient.checkTransferAmountExceedFromAccountBalance(rousdContract, account2.address)
    # rousdClient.checkTransferFrom(rousdContract, account2, 100)
    # rousdClient.checkTransferFrom(rousdContract, account2, 0)
    # rousdClient.checkTransferFromAmountExceedAllowance(rousdContract, account2)

    # rousdClient.checkTransferOwnerShip(rousdContract, client.account, account2)
    # rousdClient.checkTransferOwnerShip(rousdContract, account2, client.account)

    # rousdClient.checkBurn(rousdContract, 10)
    # rousdClient.checkBurn(rousdContract, 999999999999999999870)
    # rousdClient.checkBurn(rousdContract, 190, account2)
    # rousdClient.checkBurn(rousdContract, rousdClient.w3.toWei(1, "ether"))
    # rousdClient.checkBurn(rousdContract, client.w3.toWei(10, "ether"))
    # rousdClient.checkBurn(rousdContract, client.w3.toWei(100, "ether"))
    # rousdClient.checkBurn(rousdContract, client.w3.toWei(1000, "ether"))
    # rousdClient.checkBurn(rousdContract, client.w3.toWei(100000000000, "ether"))
    # rousdClient.checkBurn(rousdContract, 15, account2)
    # rousdClient.checkBurnAmountExceedUserBalance(rousdContract)

    # rousdClient.checkBurnFrom(rousdContract, client.account, 0, account2)
    # rousdClient.checkBurnFrom(rousdContract, rousdClient.account, 90, account2)
    # rousdClient.checkBurnFromAmountExceedAllowance(rousdContract, client.account, account2)
    # rousdClient.checkBurnFrom(rousdContract, client.account, 50, account2)
    # rousdClient.checkBurnFrom(rousdContract, client.account, 5, account2)

    # rousdClient.checkSetTrustedToken(rousdContract, usdcAddr, True)
    # rousdClient.checkSetTrustedToken(rousdContract, usdcAddr, False)
    # rousdClient.checkSetTrustedTokenCalledByNotOwner(rousdContract, usdcAddr, True, account2)
    # rousdClient.checkSetTrustedToken(rousdContract, usdcAddr, True)

    # rousdClient.UsdcApprove(rousdContract, usdcAddr, RoUSDAddr, rousdClient.calBalance(10, 6))
    # rousdClient.approve("./abi/USDT.json", [usdtAddr], RoUSDAddr, client.account)
    # print(rousdClient.getUsdcBalance(rousdContract, usdcAddr, rousdClient.account.address))
    # print(rousdClient.tokenBalanceOf(usdtAddr, rousdClient.account.address))

    # rousdClient.checkDeposite(rousdContract, usdcAddr, rousdClient.calBalance(1, 6), 6)
    # rousdClient.checkDepositeAmountExceedAllowance(rousdContract, usdcAddr)
    # rousdClient.checkDepositeAmountExceedBalance(rousdContract, usdcAddr)
    # rousdClient.checkDepositeNotTrustedToken(rousdContract, usdtAddr)

    # rousdClient.checkWithdraw(rousdContract, usdcAddr, rousdClient.calBalance(1, 6))
    # rousdClient.checkWithdraw(rousdContract, usdcAddr, 10)
    # rousdClient.checkWithdrawAmountExceedUserBalance(rousdContract, usdcAddr)
    # rousdClient.checkWithdrawNotTrustedToken(rousdContract, usdtAddr)

    # rousdClient.checkBurn(rousdContract, 999999999998999000)
    # rousdClient.checkWithdraw(rousdContract, usdcAddr, 100)
    # rousdClient.checkMint(rousdContract, client.account.address, 1000)
    # rousdClient.checkWithdraw(rousdContract, usdcAddr, 211089)

    # ######################## 测试Reserve ########################
    rrClient = ReserveTest(RPC_ADDRESS, PRIVATE_KEY, logger)

    # ROC总发行量100亿，预留5000万，其他39.75亿打给RR合约，39.75亿分给holders，holders持有的ROC随RR合约发售，随售比例1:1
    # 即用户从RR合约购买100个ROC，其中50个来自于Holders，50个按Holder的比例分配
    # print(rocContract.functions.decimals().call())
    # print(rrClient.w3.toWei(int(math.pow(10, 10)), "ether"))
    # print(rrClient.w3.toWei(int(3.975 * math.pow(10, 9)), "ether"))

    # rrClient.checkSetFunctions(rrContract, "setRouter", "router", routerAddr, account2) # 非owner执行
    # rrClient.checkSetFunctions(rrContract, "setRouter", "router", routerAddr) # owner执行

    # rrClient.checkSetFunctions(rrContract, "setReserveRatio", "reserveRatio", 900000, account2)
    # rrClient.checkSetFunctions(rrContract, "setReserveRatio", "reserveRatio", 900000)
    # rrClient.checkSetFunctions(rrContract, "setReserveRatio", "reserveRatio", 800000)

    # rrClient.checkSetFunctions(rrContract, "setInflationThreshold", "inflationThreshold", 1030000, account2)
    # rrClient.checkSetFunctions(rrContract, "setInflationThreshold", "inflationThreshold", 1040000)
    # rrClient.checkSetFunctions(rrContract, "setInflationThreshold", "inflationThreshold", 1030000)
    #
    # rrClient.checkSetFunctions(rrContract, "setDeflationThreshold", "deflationThreshold", 970000, account2)
    # rrClient.checkSetFunctions(rrContract, "setDeflationThreshold", "deflationThreshold", 960000)
    # rrClient.checkSetFunctions(rrContract, "setDeflationThreshold", "deflationThreshold", 970000)
    #
    # rrClient.checkSetFunctions(rrContract, "setInflationTarget", "inflationTarget", 1010000, account2)
    # rrClient.checkSetFunctions(rrContract, "setInflationTarget", "inflationTarget", 1020000)
    # rrClient.checkSetFunctions(rrContract, "setInflationTarget", "inflationTarget", 1010000)
    #
    # rrClient.checkSetFunctions(rrContract, "setDeflationTarget", "deflationTarget", 990000, account2)
    # rrClient.checkSetFunctions(rrContract, "setDeflationTarget", "deflationTarget", 980000)
    # rrClient.checkSetFunctions(rrContract, "setDeflationTarget", "deflationTarget", 990000)
    #
    # rrClient.checkSetFunctions(rrContract, "setIndIncentive", "indIncentive", 1000, account2)
    # rrClient.checkSetFunctions(rrContract, "setIndIncentive", "indIncentive", 10000)
    # rrClient.checkSetFunctions(rrContract, "setIndIncentive", "indIncentive", 1000)

    # 每次扩张或者收缩1次的获得的DO的最大奖励限制
    # rrClient.checkSetFunctions(rrContract, "setIndIncentiveLimit", "indIncentiveLimit", 100, account2)
    # rrClient.checkSetFunctions(rrContract, "setIndIncentiveLimit", "indIncentiveLimit", rrClient.w3.toWei(100, "ether"))
    # rrClient.checkSetFunctions(rrContract, "setIndIncentiveLimit", "indIncentiveLimit", 100)

    # 每次扩张或者收缩1次的比例
    # rrClient.checkSetFunctions(rrContract, "setIndStep", "indStep", 3000, account2)
    # rrClient.checkSetFunctions(rrContract, "setIndStep", "indStep", 3500)
    # rrClient.checkSetFunctions(rrContract, "setIndStep", "indStep", 3000)
    #
    # rrClient.checkSetFunctions(rrContract, "setIndWindow", "indWindow", 3600, account2)
    # rrClient.checkSetFunctions(rrContract, "setIndWindow", "indWindow", 1800)
    # rrClient.checkSetFunctions(rrContract, "setIndWindow", "indWindow", 3600)
    #
    # rrClient.checkSetFunctions(rrContract, "setIndGap", "indGap", 60, account2)
    # rrClient.checkSetFunctions(rrContract, "setIndGap", "indGap", 300)
    # rrClient.checkSetFunctions(rrContract, "setIndGap", "indGap", 60)

    # 未发行roUSD前，设置roc的价格
    # rrClient.checkSetFunctions(rrContract, "setEarlyPrice", "earlyPrice", rrClient.w3.toWei('0.365061', 'ether'))

    # print(rrClient.w3.toWei('12345678.012345678901234567', 'ether'))
    # print(rrClient.w3.toWei('15000000', 'ether'))
    # print(rrClient.w3.toWei('0.8230452008230452', 'ether'))
    # print( rrClient.w3.toWei('12345678.012345678901234567', 'ether') * rrClient.w3.toWei('0.8230452008230452', 'ether') // rrClient.w3.toWei('1', 'ether'))
    # rrClient.checkSetFunctions(rrContract, "setInitialPrice", "price", rrClient.w3.toWei('0.8230452008230452', 'ether'))
    # rrClient.checkSetFunctions(rrContract, "setInitialPrice", "price", rrClient.w3.toWei('0.8230452008230452', 'ether'))

    # print(doContract.functions.totalSupply().call())
    # print(rocContract.functions.totalSupply().call())
    # print(rocContract.functions.balanceOf(rrClient.account.address).call())
    # print(rocContract.functions.balanceOf(ReserveAddr).call())
    # print(rocContract.functions.balanceOf(HolderTestAAddr).call())
    # print(rocContract.functions.balanceOf(HolderTestBAddr).call())
    # print(rrClient.w3.toWei(int(3.975 * math.pow(10, 9)), "ether"))
    # # shareA = rrClient.w3.toWei(0.4321 * int(3.975 * math.pow(10, 9)), "ether")
    # shareA = rrClient.w3.toWei(Shares[0] * 25000000 // 10000, "ether")
    # # shareB = rrClient.w3.toWei(0.5679 * int(3.975 * math.pow(10, 9)), "ether")
    # shareB = rrClient.w3.toWei(Shares[1] * 25000000 // 10000, "ether")
    # print(shareA)
    # print(shareB)
    # print(shareA + shareB)

    # 4997762 622311827956989244
    # rocClient.checkMint(rocContract, ReserveAddr, rrClient.w3.toWei(255000000, "ether"))
    # rocClient.checkMint(rocContract, HolderTestAAddr, shareA)
    # rocClient.checkMint(rocContract, HolderTestBAddr, shareB)
    print(rrClient.w3.eth.getBlock(rrClient.w3.eth.blockNumber).timestamp + 600)
    # rrClient.checkEstimateRoUSDAmountFromROC(rrContract, 2)
    # rrClient.checkEstimateROCAmountFromRoUSD(rrContract, 1)
    # rrClient.checkEstimateRoUSDAmountFromROC(rrContract, 99504950495049504950495)
    # rrClient.checkEstimateROCAmountFromRoUSD(rrContract, 10000000000000000000000)
    # rrClient.checkEstimateRoUSDAmountFromROC(rrContract, rrClient.w3.toWei(1, "ether"))
    # rrClient.checkEstimateRoUSDAmountFromROC(rrContract, rrClient.w3.toWei(100, "ether"))
    # rrClient.checkEstimateRoUSDAmountFromROC(rrContract, rrClient.w3.toWei(12345, "ether"))
    # rrClient.checkEstimateRoUSDAmountFromROC(rrContract, rrClient.w3.toWei(123, "ether"))
    # rrClient.checkEstimateRoUSDAmountFromROC(rrContract, rrClient.w3.toWei(22222, "ether"))
    # rrClient.checkEstimateRoUSDAmountFromROC(rrContract, rrClient.w3.toWei(1000000, "ether"))

    # rrClient.checkEstimateROCAmountFromRoUSD(rrContract, rrClient.w3.toWei(1, "ether"))

    print("用户的roUSD对RR合约的授权额度", rousdContract.functions.allowance(rrClient.account.address, ReserveAddr).call())
    print("用户的roUSD资产", rousdContract.functions.balanceOf(rrClient.account.address).call())
    # print(rousdContract.functions.balanceOf(ReserveAddr).call())
    print("RR合约持有的ROC", rocContract.functions.balanceOf(ReserveAddr).call())
    # print(rocContract.functions.balanceOf(rrClient.account.address).call())
    # rousdClient.checkMint(rousdContract, rrClient.account.address, rrClient.w3.toWei(2000000, "ether"))
    # rousdClient.checkApprove(rousdContract, ReserveAddr, rrClient.w3.toWei(10000000000, "ether"))
    # rocClient.checkMint(rocContract, HolderTestAAddr, rocClient.w3.toWei(10000000, "ether"))
    # rocClient.checkMint(rocContract, HolderTestBAddr, rocClient.w3.toWei(10000000, "ether"))

    # doClient.checkTransferOwnerShip(doContract, doClient.account, ReserveAddr)

    # rrClient.checkSetHolderInfoArray(rrContract, Holders, Shares)
    # rrClient.checkPurchaseExactAmountOfROCWithRoUSD(rrContract, 1000, 1000)

    # tt = 1164039603960396038380
    # a = tt //2 * Shares[0] // 10000
    # b = tt //2 * Shares[1] // 10000
    # print(a, b)
    # print(a + b, tt//2, tt - a - b)
    # rousdClient.checkMint(rousdContract, rousdClient.account.address, rousdClient.w3.toWei("10000000000", "ether"))
    # rousdClient.checkApprove(rousdContract, ReserveAddr, rousdClient.w3.toWei("10000000000", "ether"))
    # rrClient.checkEstimateRoUSDAmountFromROC(rrContract, 1233960396039603834)
    # rrClient.checkPurchaseExactAmountOfROCWithRoUSD(rrContract, 1233960396039603834, 1015605181966100126)
    # rrClient.checkPurchaseExactAmountOfROCWithRoUSD(rrContract, rrClient.w3.toWei(1, "ether"), rrClient.w3.toWei(1, "ether"))
    # rrClient.checkPurchaseExactAmountOfROCWithRoUSD(rrContract, rrClient.w3.toWei(10, "ether"), rrClient.w3.toWei("8.231", "ether"))
    # rrClient.checkPurchaseExactAmountOfROCWithRoUSD(rrContract, rrClient.w3.toWei(100, "ether"), rrClient.w3.toWei(100, "ether"))
    # rrClient.checkPurchaseExactAmountOfROCWithRoUSD(rrContract, rrClient.w3.toWei(1234.32247, "ether"), rrClient.w3.toWei(1300, "ether"))
    # rrClient.checkPurchaseExactAmountOfROCWithRoUSD(rrContract, rrClient.w3.toWei(1000, "ether"), rrClient.w3.toWei(1000, "ether"))
    # rrClient.checkPurchaseExactAmountOfROCWithRoUSD(rrContract, rrClient.w3.toWei(10000, "ether"), rrClient.w3.toWei(10000, "ether"))
    # rrClient.checkPurchaseExactAmountOfROCWithRoUSD(rrContract, rrClient.w3.toWei("20000", "ether"), rrClient.w3.toWei(10000, "ether"))
    # rrClient.checkPurchaseExactAmountOfROCWithRoUSD(rrContract, rrClient.w3.toWei(100000, "ether"), rrClient.w3.toWei(100000, "ether"))
    # rrClient.checkPurchaseExactAmountOfROCWithRoUSD(rrContract, rrClient.w3.toWei(12345678, "ether"), rrClient.w3.toWei(120000000, "ether"))
    # rrClient.checkPurchaseExactAmountOfROCWithRoUSD(rrContract, rrClient.w3.toWei(40000000, "ether"), rrClient.w3.toWei(40000000, "ether"))
    # a = rrClient.w3.toWei("100000.00000000000045678", "ether")
    # print(a)
    # print(rrClient.HOLDER_SHARE_BASE * 2)
    # print(a % (rrClient.HOLDER_SHARE_BASE * 2))
    # rrClient.checkEstimateROCAmountFromRoUSD(rrContract, rrClient.w3.toWei(1.12345678, "ether"))
    # rrClient.checkPurchaseExactAmountOfROCWithRoUSD(rrContract, rrClient.w3.toWei("100000.00000000000045678", "ether"), rrClient.w3.toWei(100000, "ether"))
    # rrClient.checkPurchaseExactAmountOfROCWithRoUSD(rrContract, rrClient.w3.toWei(10000000, "ether"), rrClient.w3.toWei(100000000, "ether"))
    # rrClient.checkPurchaseExactAmountOfROCWithRoUSD(rrContract, rrClient.w3.toWei("100000000", "ether"), rrClient.w3.toWei("100000000", "ether"))
    # rrClient.checkPurchaseROCWithExactAmountOfRoUSD(rrContract, 100, 100)
    # rrClient.checkPurchaseROCWithExactAmountOfRoUSD(rrContract, rrClient.w3.toWei(1, "ether"), rrClient.w3.toWei(1, "ether"))
    # rrClient.checkPurchaseROCWithExactAmountOfRoUSD(rrContract, rrClient.w3.toWei("1.123456789012345678", "ether"), rrClient.w3.toWei(1, "ether"))
    # rrClient.checkPurchaseROCWithExactAmountOfRoUSD(rrContract, rrClient.w3.toWei(100, "ether"), rrClient.w3.toWei(100, "ether"))
    # rrClient.checkPurchaseROCWithExactAmountOfRoUSD(rrContract, rrClient.w3.toWei(1000, "ether"), rrClient.w3.toWei(100, "ether"))
    # rrClient.checkPurchaseROCWithExactAmountOfRoUSD(rrContract, rrClient.w3.toWei(3000, "ether"), rrClient.w3.toWei(300, "ether"))
    # rrClient.checkPurchaseROCWithExactAmountOfRoUSD(rrContract, rrClient.w3.toWei(10000, "ether"), rrClient.w3.toWei(100, "ether"))
    # rrClient.checkPurchaseROCWithExactAmountOfRoUSD(rrContract, rrClient.w3.toWei(100000, "ether"), rrClient.w3.toWei(10000, "ether"))
    # rrClient.checkPurchaseROCWithExactAmountOfRoUSD(rrContract, rrClient.w3.toWei(1000000, "ether"), rrClient.w3.toWei(10000, "ether"))
    # rrClient.checkPurchaseROCWithExactAmountOfRoUSD(rrContract, rrClient.w3.toWei(10000000, "ether"), rrClient.w3.toWei(10000, "ether"))

    # rrClient.checkGetAveragePriceOfROC(rrContract)
    # rrClient.checkHolderDelegate(HolderTestAAddr)
    # rrClient.checkHolderDelegate(HolderTestAAddr, account2.address)
    # rrClient.checkHolderWithdrawRoUSD(HolderTestAAddr)
    # rrClient.checkHolderWithdrawRoUSDCalldeNotOwner(HolderTestBAddr, account2)

    # print(rrContract.functions.loanMap(rrClient.account.address, 0).call())
    # rrClient.checkMintExactAmountOfDOWhenAllowanceNotEnough(rrContract)
    # rocClient.checkApprove(rocContract, ReserveAddr, rrClient.w3.toWei(10000000, "ether"))
    # print(rocContract.functions.allowance(rrClient.account.address, ReserveAddr).call())
    # print(doContract.functions.balanceOf(rrClient.account.address).call())
    # print(doContract.functions.balanceOf(ReserveAddr).call())
    # rrClient.checkMintExactAmountOfDO(rrContract, 100)
    # rrClient.checkMintExactAmountOfDO(rrContract, 1234567890123456789)
    # rrClient.checkMintExactAmountOfDO(rrContract, rrClient.w3.toWei(1, "ether"))
    # rrClient.checkMintExactAmountOfDO(rrContract, rrClient.w3.toWei(10.52, "ether"))
    # rrClient.checkMintExactAmountOfDO(rrContract, rrClient.w3.toWei(1000, "ether"))
    # rrClient.checkMintExactAmountOfDO(rrContract, rrClient.w3.toWei(5000, "ether"))
    # rrClient.checkMintExactAmountOfDO(rrContract, rrClient.w3.toWei(50000, "ether"))
    # rrClient.checkMintExactAmountOfDO(rrContract, rrClient.w3.toWei(100000, "ether"))
    # rrClient.checkMintExactAmountOfDO(rrContract, rrClient.w3.toWei(1000000, "ether"))
    # rrClient.checkMintExactAmountOfDO(rrContract, rrClient.w3.toWei(30000000, "ether"))
    # rrClient.checkMintDOWithExactAmountOfROC(rrContract, 10000)
    # rrClient.checkMintDOWithExactAmountOfROC(rrContract, rrClient.w3.toWei("100", "ether"))
    # rrClient.checkMintDOWithExactAmountOfROC(rrContract, rrClient.w3.toWei(0.1, "ether"))
    # rrClient.checkMintDOWithExactAmountOfROC(rrContract, rrClient.w3.toWei("123.456789012345678901", "ether"))
    # rrClient.checkMintDOWithExactAmountOfROC(rrContract, rrClient.w3.toWei(1000, "ether"))
    # rrClient.checkMintDOWithExactAmountOfROC(rrContract, rrClient.w3.toWei(10000, "ether"))
    # rrClient.checkMintDOWithExactAmountOfROC(rrContract, rrClient.w3.toWei(100000, "ether"))
    # rrClient.checkMintDOWithExactAmountOfROC(rrContract, rrClient.w3.toWei(1000000, "ether"))
    # rrClient.checkMintDOWithExactAmountOfROCWhenAllowanceNotEnough(rrContract)

    # print(doContract.functions.allowance(rrClient.account.address, ReserveAddr).call())
    # doClient.checkApprove(doContract, ReserveAddr, rrClient.w3.toWei(10000, "ether"))
    # rrClient.checkRedeemROC(rrContract, 2)
    # rrClient.checkRedeemROC(rrContract, 2)
    # rrClient.checkRedeemROC(rrContract, 3)
    # rrClient.checkWithdrawRoUSD(rrContract, 100)
    # rrClient.checkWithdrawRoUSD(rrContract, 0)
    # doTotalSupply = doContract.functions.totalSupply().call()
    # reserveRatio = rrContract.functions.reserveRatio().call()
    # RRRoUSdBalance = rousdContract.functions.balanceOf(ReserveAddr).call()
    # expectedRRDo = doTotalSupply * reserveRatio
    # expectedRRRoUSD = RRRoUSdBalance * rrClient.RATIO_BASE
    # print(expectedRRDo // rrClient.RATIO_BASE - RRRoUSdBalance)
    # logger.info("expectedRRDo: {}, expectedRRRoUSD: {}".format(expectedRRDo, expectedRRRoUSD))
    # rrClient.checkWithdrawRoUSD(rrContract, 47990009182925250112929)
    # rrClient.checkWithdrawRoUSD(rrContract, rrClient.w3.toWei(1, "ether"))
    # rrClient.checkWithdrawRoUSD(rrContract, rrClient.w3.toWei("188037683.1", "ether"))
    # rrClient.checkWithdrawRoUSD(rrContract, )

    # print(rrClient.w3.toWei(100, "ether"))
    # print(doContract.functions.allowance(rrClient.account.address, routerAddr).call())
    # doClient.checkApprove(doContract, routerAddr, rrClient.w3.toWei(100000, "ether"))
    # print(rousdContract.functions.allowance(rrClient.account.address, routerAddr).call())
    # rousdClient.checkApprove(rousdContract, routerAddr, rrClient.w3.toWei(100000, "ether"))

    pairContract = rrClient.get_contract(RoUSDDoPair, "./abi/UNIPair.json")
    routerContract = rrClient.get_contract(routerAddr, "./abi/UNIRouter2.json")
    # print(pairContract.functions.getReserves().call())
    # print(pairContract.functions.token0().call())

    # 测试调节do价格的前置条件
    # 创建pair
    # rrClient.uniswapAddLiquidity(rrClient.w3.toWei(10000, "ether"))
    # rrClient.checkSetFunctions(rrContract, "setRoUSDDOPair", "roUSDDOPair", RoUSDDoPair)  # owner执行
    # rrClient.checkSetFunctions(rrContract, "setRouter", "router", routerAddr)
    # rrClient.checkCanInflate(rrContract)
    # rrClient.checkCanDeflate(rrContract)

    # rousdClient.checkMint(rousdContract, rrClient.account.address, rrClient.w3.toWei(50000, "ether"))
    # rousdClient.checkApprove(rousdContract, routerAddr, rrClient.w3.toWei(1000000000, "ether"))
    # doClient.checkApprove(doContract, routerAddr, rrClient.w3.toWei(1000000000, "ether"))
    # doClient.checkMint(doContract, doClient.account.address, doClient.w3.toWei(1000000000, "ether"))
    # print(rousdContract.functions.balanceOf(rrClient.account.address).call())
    # print(rousdContract.functions.allowance(rrClient.account.address, routerAddr).call())
    # print(doContract.functions.balanceOf(rrClient.account.address).call())
    # print(doContract.functions.allowance(rrClient.account.address, routerAddr).call())
    # rrClient.uniswapAddLiquidity(rrClient.w3.toWei(100000000, "ether"))
    # rrClient.uniswapSwapExactTokensForTokens([RoUSDAddr, DOAddr], rrClient.w3.toWei(300, "ether"))
    # rrClient.checkCanInflate(rrContract)
    # rrClient.checkInflat(rrContract)
    # rrClient.checkCanInflate(rrContract)
    # rrClient.uniswapSwapExactTokensForTokens([DOAddr, RoUSDAddr], rrClient.w3.toWei(50, "ether"))
    rrClient.checkCanDeflate(rrContract)
    # rrClient.checkDeflate(rrContract)

    # print(rousdContract.functions.balanceOf(ReserveAddr).call())
    # print(rousdContract.functions.balanceOf(rrClient.account.address).call())

    # 重新部署Reserve合约
    # rrClient.initReserve()
    # 130693998305445058433703200000, expectedRRRoUSD: 130850137094780763563342000000
    # 130933289836096585928044800000, expectedRRRoUSD: 131151266216167624159610000000

    # ######### 开始测试timelock ###########

    # rocAddr = rocClient.deploy_contract("./abi/ROC.json")
    # logger.info("roc合约: {}".format(rocAddr))
    # tl = rocClient.deploy_contract("./abi/timelock.json", [rocClient.account.address, 600])
    # logger.info("timelock合约: {}".format(tl))

    # print(rocContract.all_functions())
    # print(tlContract.all_functions())

    # # 转移 ROC合约的owner给timeLock时间锁
    # rocAddr = "0xc89fC625b4AF5fc5f266A2B536020ee6874d4bF4"
    # tlAddr = "0xbA7e330A3D0D8937adEfB352fcBE485630C118d9"
    #
    # rocContract = rocClient.get_contract(rocAddr, "./abi/ROC.json")
    # tlContract = rocClient.get_contract(tlAddr, "./abi/timelock.json")
    # rocClient.checkSetIssuer(rocContract, rocClient.account.address, True)
    # rocClient.checkTransferOwnerShip(rocContract, rocClient.account, tlAddr)
    # print(account2.address)
    # print(rocContract.encodeABI(fn_name="setIssuer", args=[account2.address, True]))
    # from eth_abi import encode_abi, encode_single
    # a = encode_single("(address)", [rocClient.account.address])
    # b = encode_abi(["address", "bool"], [account2.address, True])
    # print(a)
    # print(b)
    # print(rocClient.w3.toHex(a))
    # print(rocClient.w3.toHex(b))
    # print(rocClient.w3.toWei(100, "ether"))
    # print(int(time.time()) + 400)

    # governolAddr = "0x5f28EC1a50646BDDE6EA2485FECaB30767b6A36F"
    # print(account2.address)
    # print(rocClient.w3.toWei(1900, "ether"))

    # print(rocContract.functions.balanceOf(rocClient.account.address).call())
    # print(rocContract.functions.balanceOf(account2.address).call())
    # rocClient.checkMint(rocContract, rocClient.account.address, rocClient.w3.toWei(20, "ether"))
    # rocClient.checkMint(rocContract, account2.address, rocClient.w3.toWei(100, "ether"))
    # rocClient.checkDelegate(rocContract, account2.address, account2)
