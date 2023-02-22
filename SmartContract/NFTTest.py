# -*- coding: utf-8 -*-
import os
from web3 import Web3, HTTPProvider
from roxe_libs.pub_function import setCustomLogger
from SmartContract.CommonTool import load_from_json_file
import time
import random


RPC_ADDRESS = 'https://rinkeby.infura.io/v3/be5b825be13b4dda87056e6b073066dc'

rpcNode = Web3(HTTPProvider(RPC_ADDRESS, request_kwargs={'timeout': 120}))

# nftAddress = "0x020Ef3c3740Ab2308A68686C44919be00807bdE1"
# getCardAddress = "0x0C0fbC5C07160B98219927eFd94Ae403B8979e15"
meeAddress = "0x2245b2880bCB77AEa20c9a261E1C0AA8fC24E2dD"

# nftAddress = "0xC88BD7735B154ade03dD409713aC45bEd28cCA56"
# getCardAddress = "0xA6F1093ff87aA25fd60c614195766A4F6bb0f59E"
#
# nftAddress = "0x944e29a6D3DbF49c5fB0b357b7F08c1d5D1f68aB"
# getCardAddress = "0x5AB68194A797df16B663a164763A3B7c7c83b602"
#
# nftAddress = "0xE818895efCedE0af595fD33d1651c027Ec7c81D4"
# getCardAddress = "0x5570Fd4Ae96e2fCca7530d446a5baF8317166fdE"
#
# nftAddress = "0xD362c1C30a872429B549A69dDa26Dd929b1Cf08A"
# getCardAddress = "0xD3Ac1Fca48a3D560b59d40B5DE328bB7556e092f"
#
# nftAddress = "0x8C84E2f25e84A25036843c1d9754696F80934830"
# getCardAddress = "0x2f33EeB48156dF9841FeA2102ad81936D7c52d8c"

nftAddress = "0x37933b0CB78eaf651Cf699e8107a1461f43848B7"
getCardAddress = "0xCc7A98317656A6EC4A89B374557da94e52ba3D8e"

privateKey = "ebed55a1f7e77144623167245abf39df053dc76fd8118ac7ae6e1ceeb84c5ed0"
account = rpcNode.eth.account.privateKeyToAccount(privateKey)
gasPrice = 1000000000
curPath = os.path.dirname(os.path.abspath(__file__))

logger = setCustomLogger("nft", curPath + "/nft3.log", isprintsreen=True)


def excuteTransaction(client, func, nonce, acc, isadd=True):
    dproxy_txn = func.buildTransaction({'from': acc.address, 'nonce': nonce, "gasPrice": gasPrice})
    # gas = client.eth.estimateGas(dproxy_txn)
    if isadd:
        dproxy_txn["gas"] += 20000
    # print(gas)
    # print(dproxy_txn)
    logger.info("构建交易: {}".format(dproxy_txn))
    signed = acc.signTransaction(dproxy_txn)
    logger.info("签名交易: {}".format(signed))
    tx_hash = client.eth.sendRawTransaction(signed.rawTransaction)
    logger.info('交易hash: {}'.format(client.toHex(tx_hash)))
    tx_receipt = client.eth.waitForTransactionReceipt(tx_hash, timeout=120)
    logger.info("此次交易，gasUsed: {gasUsed} blockNumber: {blockNumber}".format(**tx_receipt))
    # logger.info("Receipt accepted. gasUsed={gasUsed} blockNumber={blockNumber}".format(**tx_receipt))
    return client.toHex(tx_hash)


def alwaysDrawCard(endNumber, endTime=None, oneTime=1):
    adds = [account.address for i in range(6)]
    burnAdds = ["0xcaA0604362B10a54C3791c23e2ac96Ea58EA34Cf" for i in range(6)]
    cards = [i for i in range(1, 7)]
    num = 0
    errorNum = 0
    errorTransactions = []
    begin_time = time.time()
    while True:
        num += 1
        logger.info("第{}次进行抽卡".format(num))
        mee_before = rpcNode.fromWei(meeContract.functions.balanceOf(account.address).call(), "ether")
        cards_before = nftContract.functions.balanceOfBatch(adds, cards).call()
        burnMee = rpcNode.fromWei(meeContract.functions.balanceOf(burnAdds[0]).call(), "ether")
        burnCards = nftContract.functions.balanceOfBatch(burnAdds, cards).call()
        logger.info("抽卡之前，持有mee的数量: {}".format(mee_before))
        logger.info("抽卡之前，持有卡片的数量: {}".format(cards_before))
        logger.info("抽卡之前，销毁的MEE数量: {}".format(burnMee))
        logger.info("抽卡之前，销毁的卡片数量: {}".format(burnCards))

        if mee_before < 50:
            break
        nonce = rpcNode.eth.getTransactionCount(account.address)
        seed = random.randint(1, 10000)
        # seed = 1
        logger.info("抽卡随机的seed: {}".format(seed))
        drawCard = getCardContract.functions.drawCard(oneTime, seed)
        txId = excuteTransaction(rpcNode, drawCard, nonce, account)
        time.sleep(2)
        txInfo = rpcNode.eth.getTransactionReceipt(txId)
        if txInfo["status"] != 1:
            errorNum += 1
            errorTransactions.append(txId)
            logger.info("此次交易执行失败: {}".format(txId))
        time.sleep(1)
        mee_after = rpcNode.fromWei(meeContract.functions.balanceOf(account.address).call(), "ether")
        cards_after = nftContract.functions.balanceOfBatch(adds, cards).call()

        logger.info("抽卡之后，持有mee的数量: {}".format(mee_after))
        logger.info("抽卡之后，持有卡片的数量: {}".format(cards_after))
        flag = True
        for i in cards_after[1::]:
            # 当抽卡后，卡片数量不满足card1的兑换数量时，flag置为false，继续抽卡
            if i < endNumber * 2:
                flag = False
        if flag:
            break
        if endTime:
            if time.time() - begin_time > endTime:
                logger.info("运行时长达到{}秒, 停止运行".format(endTime))
                break
        # break
    logger.info("此次共计抽卡次数: {}".format(num))
    logger.info("抽卡执行失败次数: {}".format(errorNum))
    logger.info("抽卡执行失败的交易: {}".format(errorTransactions))
    logger.info("抽卡结束。。")


def exchangeCard1(num):
    adds = [account.address for i in range(6)]
    burnAdds = ["0xcaA0604362B10a54C3791c23e2ac96Ea58EA34Cf" for i in range(6)]
    cards = [i for i in range(1, 7)]
    mee_before = rpcNode.fromWei(meeContract.functions.balanceOf(account.address).call(), "ether")
    cards_before = nftContract.functions.balanceOfBatch(adds, cards).call()
    burnMee = rpcNode.fromWei(meeContract.functions.balanceOf(burnAdds[0]).call(), "ether")
    burnCards = nftContract.functions.balanceOfBatch(burnAdds, cards).call()
    logger.info("抽卡之前，持有mee的数量: {}".format(mee_before))
    logger.info("抽卡之前，持有卡片的数量: {}".format(cards_before))
    logger.info("抽卡之前，销毁的MEE数量: {}".format(burnMee))
    logger.info("抽卡之前，销毁的卡片数量: {}".format(burnCards))

    nonce = rpcNode.eth.getTransactionCount(account.address)
    ex_func = getCardContract.functions.exchangeCard1(num)
    txId = excuteTransaction(rpcNode, ex_func, nonce, account, False)
    time.sleep(2)
    txInfo = rpcNode.eth.getTransactionReceipt(txId)
    if txInfo["status"] != 1:
        logger.info("此次交易执行失败: {}".format(txId))
    time.sleep(1)
    mee_after = rpcNode.fromWei(meeContract.functions.balanceOf(account.address).call(), "ether")
    cards_after = nftContract.functions.balanceOfBatch(adds, cards).call()

    logger.info("抽卡之后，持有mee的数量: {}".format(mee_after))
    logger.info("抽卡之后，持有卡片的数量: {}".format(cards_after))


if __name__ == "__main__":
    nftContract = rpcNode.eth.contract(nftAddress, abi=load_from_json_file(curPath + "/abi/NFT.json")["abi"])
    getCardContract = rpcNode.eth.contract(getCardAddress, abi=load_from_json_file(curPath + "/abi/getCard.json")["abi"])
    meeContract = rpcNode.eth.contract(meeAddress, abi=load_from_json_file(curPath + "/abi/GovernToken.json")['abi'])
    # print(account)
    # print(rpcNode.eth.blockNumber)
    # print(nftContract.all_functions())
    # print(getCardContract.all_functions())

    # 铸币
    curMEE = meeContract.functions.balanceOf(account.address).call()
    print("当前的MEE数量:{}".format(rpcNode.fromWei(curMEE, "ether")))
    # mintMee = meeContract.functions.issue(account.address, rpcNode.toWei(50000, "ether"))
    # n = rpcNode.eth.getTransactionCount(account.address)
    # excuteTransaction(rpcNode, mintMee, n, account)
    # 授权
    # approveMee = meeContract.functions.approve(getCardAddress, curMEE)
    # n = rpcNode.eth.getTransactionCount(account.address)
    # excuteTransaction(rpcNode, approveMee, n, account)

    alwaysDrawCard(203, 3600, 10)

    # exchangeCard1(5)




