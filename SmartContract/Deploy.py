# -*- coding: utf-8 -*-

from web3 import Web3, HTTPProvider
import json
from roxe_libs.pub_function import setCustomLogger
from SmartContract.CommonTool import exec_contract

logger = setCustomLogger("SmartContract", "ContractTest.log", isprintsreen=True)


class DeployContract:

    def __init__(self, url, private_key):
        self.w3 = Web3(HTTPProvider(url))
        self.deploy_account = self.w3.eth.account.privateKeyToAccount(private_key)

    def deployContract(self, abi, bytecode, contractArgs=None):
        contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)
        constructed = contract.constructor() if not contractArgs else contract.constructor(*contractArgs)
        tx = constructed.buildTransaction({
            'from': self.deploy_account.address,
            'nonce': self.w3.eth.getTransactionCount(self.deploy_account.address),
        })
        logger.info("Signing and sending raw tx ...")
        signed = self.deploy_account.signTransaction(tx)
        tx_hash = self.w3.eth.sendRawTransaction(signed.rawTransaction)
        logger.info("tx_hash = {} waiting for receipt ...".format(tx_hash.hex()))
        tx_receipt = self.w3.eth.waitForTransactionReceipt(tx_hash, timeout=120)
        contractAddress = tx_receipt["contractAddress"]
        logger.info("Receipt accepted. gasUsed={gasUsed} contractAddress={contractAddress}".format(**tx_receipt))
        return contractAddress

    def deployBFactory(self):
        with open("./abi/BFactory.json", "r") as f:
            info = json.load(f)
        bFactoryAddr = self.deployContract(info["abi"], info["data"]["bytecode"]["object"])
        logger.info("deploy BFactory: {}".format(bFactoryAddr))
        return bFactoryAddr

    def deployPairFactory(self):
        with open("./abi/PairFactory.json", "r") as f:
            info = json.load(f)
        pairFactoryAddr = self.deployContract(info["abi"], info["data"]["bytecode"]["object"])
        logger.info("deploy PairFactory: {}".format(pairFactoryAddr))
        return pairFactoryAddr

    def deployBAciton(self):
        with open("./abi/BAction.json", "r") as f:
            info = json.load(f)
        # bFactoryAddr = self.deployBFactory()
        # pairFactoryAddr = self.deployPairFactory()
        # lpMiningAddr = pairFactoryAddr
        bActionAddr = self.deployContract(info["abi"], info["data"]["bytecode"]["object"])
        logger.info("deploy BAction: {}".format(bActionAddr))

    def deployPriceOracle(self):
        with open("./abi/PriceOracle.json", "r") as f:
            info = json.load(f)
        addr = self.deployContract(info["abi"], info["data"]["bytecode"]["object"])
        logger.info("deploy oracle: {}".format(addr))
        return addr

    def deployLPMining(self, startBlock, endTripleBlock, endBlock):
        with open("./abi/LPMiningV1.json", "r") as f:
            info = json.load(f)
        oracle = self.deployPriceOracle()
        award = "0x930fABc3Ca6ab489003268840F06B3e2957EB7F3"
        tokenPerBlock = 1500000000000000000
        contractArgs = (award, tokenPerBlock, startBlock, endTripleBlock, endBlock, oracle)
        lpMiningAddr = self.deployContract(info["abi"], info["data"]["bytecode"]["object"], contractArgs)
        logger.info("deploy LPMiningV1: {}".format(lpMiningAddr))

    def build_and_send_contract_transaction(self, contract_func, nonce, gasprice=30000000000):
        construct_txn = contract_func.buildTransaction(
            {'from': self.deploy_account.address,
             'gasPrice': gasprice,
             'nonce': nonce})
        # print(construct_txn)
        # print(self.w3.eth.estimateGas(construct_txn))
        signed = self.deploy_account.signTransaction(construct_txn)
        # print(signed)
        tx_hash = self.w3.eth.sendRawTransaction(signed.rawTransaction)
        print('tx_hash={} waiting for receipt..'.format(tx_hash))
        print(self.w3.toHex(tx_hash))
        # tx_receipt = client.w3.eth.waitForTransactionReceipt(tx_hash, timeout=120)
        # print("Receipt accepted. gasUsed={gasUsed} blockNumber={blockNumber}".format(**tx_receipt))


if __name__ == "__main__":
    nodeUrl = "http://192.168.38.227:18045"
    # nodeUrl = "https://ropsten.infura.io/v3/be5b825be13b4dda87056e6b073066dc"
    nodeUrl = "https://kovan.infura.io/v3/be5b825be13b4dda87056e6b073066dc"
    privateKey = "ebed55a1f7e77144623167245abf39df053dc76fd8118ac7ae6e1ceeb84c5ed0"
    client = DeployContract(nodeUrl, privateKey)
    # client.deployBFactory()     # 0x4A496F0222239c8a63e419A5308a1c78e2280374
    # client.deployPairFactory()  # 0xEBb670f2655f1cB05041563FbBF9d218FB53E9bE
    # client.deployBAciton()      # 0xE00dCC08F7908e421E04C5705d9935D3540a3bA9
    # print(client.w3.eth.blockNumber)
    # # oracle 0x3B66a5C7206380cf051887B25Ce17cBc0B69eEd2
    # # LPMiningV1 0x5eD76Bb20B8D95E2Ee0eb0aeDf006d98d41D8643
    # client.deployLPMining(1046742, 1046942, 1056742)
    with open("./abi/ExchangeProxy.json", "r") as f:
        info = json.load(f)
    # client.deployContract(info["abi"], info["data"]["bytecode"]["object"], ["0xFF5c8de422529eDD858BD4d9Ae7Dc64A203dB331"])

    proxy = client.w3.eth.contract("0x6a7d5e399e28ff316729e2932E93C9eD9ed85828", abi=info["abi"])
    print(proxy.all_functions())
    a_func = proxy.get_function_by_args([[["0x11226C10cB03e3605171b23991dcf4948751eBB8","0x625D6686e4123d03354f8b321A436E7563EF26bc","0x9518Ef15EC4df3670b5FccE10C1863bE70a1e0f4","10000000000000000000","23453945881635705370","2360879353320969178"]]],"0x625D6686e4123d03354f8b321A436E7563EF26bc","0x9518Ef15EC4df3670b5FccE10C1863bE70a1e0f4","23453945881635705370" )

    print(a_func)
    # print(client.w3.toWei("2500", "usdt"))
    # a = proxy.find_functions_by_args()
    # a = proxy.functions.batchSwapExactIn((()), "", "", 1000, 2000)
    # with open("./abi/PriceOracle.json", "r") as f:
    #     info = json.load(f)
    # oracle_contract = client.w3.eth.contract(address="0x3B66a5C7206380cf051887B25Ce17cBc0B69eEd2", abi=info["abi"])
    # print(oracle_contract.all_functions())
    import time
    begin_time = time.time()

    usdc = "0x9518Ef15EC4df3670b5FccE10C1863bE70a1e0f4"
    mee = "0x625D6686e4123d03354f8b321A436E7563EF26bc"
    with open("BlanceFactory.json", "r") as f:
        factory_info = json.load(f)
    with open("BlancePool.json", "r") as f:
        pool_info = json.load(f)

    with open("./abi/ERC20.json", "r") as f:
        erc20_info = json.load(f)
        usdc_contract = client.w3.eth.contract(address=usdc, abi=erc20_info["abi"])

    # with open("./abi/ExchangeProxy.json", "r") as f:
    #     info = json.load(f)
    #     exchangeProxt = client.w3.eth.contra
    from_block = 21940480
    # BFactory = client.w3.eth.contract(address="0xd2aCB80694dA047ADC2b520429a405CAAcd683d5", abi=factory_info["abi"])
    # print(BFactory.all_functions())
    # events = BFactory.events.LOG_NEW_POOL.createFilter(fromBlock=from_block, address=client.deploy_account.address)
    # print(events.get_new_entries())
    entries = None
    # while True:
    #     entry = events.get_new_entries()
        # print(entry)
        # if entry:
        #     print(entry)
    #         pool_addr = entry.args.pool
    #         print(pool_addr)
    #         pool = client.w3.eth.contract(address=pool_addr, abi=pool_info["abi"])
    #         # print(pool.all_functions())
    #         tokenInfo = pool.functions.getCurrentTokens().call()
    #         if [client.w3.toChecksumAddress(usdc), client.w3.toChecksumAddress(mee)] == tokenInfo:
    #             print(tokenInfo)
    #             print(pool.functions.getBalance(usdc).call())
    #             print(pool.functions.getBalance(mee).call())
    #             print("find exact pool")
    # #         break
    entries = []
    # while not entries:
    #     entries = events.get_all_entries()
    for entry in entries:
        print(entry)
        pool_addr = entry.args.pool
        # print(pool_addr)
        pool = client.w3.eth.contract(address=pool_addr, abi=pool_info["abi"])
        # print(pool.all_functions())
        tokenInfo = pool.functions.getCurrentTokens().call()
        if [client.w3.toChecksumAddress(usdc), client.w3.toChecksumAddress(mee)] == tokenInfo:
            # print(tokenInfo)
            print("find exact pool")
            if pool.functions.getBalance(usdc).call() == 4750000000000000000000 and pool.functions.getBalance(mee).call() == 2500000000000000000000:
                print("approve...")
                print(pool_addr)
    #             balance = usdc_contract.functions.balanceOf(client.deploy_account.address).call()
    #             print(balance)
    #             nonce = client.w3.eth.getTransactionCount(client.deploy_account.address)
    #             print(nonce)
    #             contract_func = usdc_contract.functions.approve(client.w3.toChecksumAddress(pool_addr), balance)
    #             client.build_and_send_contract_transaction(contract_func, nonce)
    #             print("swap")
    #             nonce = client.w3.eth.getTransactionCount(client.deploy_account.address)
    #             print(nonce)
    #             swap_func = pool.functions.swapExactAmountIn(usdc, 2370000000000000000000, mee, 2002801193553242630000, 3590829352475123128)
    #             client.build_and_send_contract_transaction(swap_func, nonce)
    #             print("交易完成")
                break
        # print(client.w3.eth.getTransactionReceipt(info.transactionHash))
    #     # print(info.args.oldPrice, info.args.newPrice)
    end_time = time.time()
    print(end_time - begin_time)
    # print(client.w3.eth.blockNumber)
    # print(client.deploy_account.address)
    # print(client.w3.isAddress("0x0000000000000000000000000000000000000000"))
    # print(client.w3.toWei("0.003", "ether"))
    # print()
    # print(oracle_contract.functions.owner().call())
    # func = oracle_contract.functions.addTokenInfo("0xC87caBF8A42e97B1Af5822cdfd1D7C556793CF34", 0, client.w3.toWei("1", "ether"))
    #
    # nonce = client.w3.eth.getTransactionCount(client.deploy_account.address)
    # exec_contract(client.w3, client.deploy_account, nonce, func)
    # print(oracle_contract.functions.tokenPrice("0xC87caBF8A42e97B1Af5822cdfd1D7C556793CF34").call())
    #
    # func = oracle_contract.functions.respondTokenPrice("0xC87caBF8A42e97B1Af5822cdfd1D7C556793CF34",
    #                                                    client.w3.toWei("1.6", "ether"),
    #                                                    "0x5eD76Bb20B8D95E2Ee0eb0aeDf006d98d41D8643")
    # nonce = client.w3.eth.getTransactionCount(client.deploy_account.address)
    # tx_hash = exec_contract(client.w3, client.deploy_account, nonce, func)
    # print(tx_hash) # 0x67889f00b92599675fb61a46d1252e394a07229e95949c8bc6d6c0d7dc17f36d
    # receipt = client.w3.eth.waitForTransactionReceipt(tx_hash)
    # print("交易执行成功:\n{}".format(receipt))
    #
    # print(oracle_contract.functions.tokenPrice("0xC87caBF8A42e97B1Af5822cdfd1D7C556793CF34").call())

    # tx_hash = "0x736bc2923d0a04610b831865dcd6d28a6e23ae566adf92ebcd170fce19a5c44c"
    # tx_receipt = client.w3.eth.getTransactionReceipt(tx_hash)
    # print(tx_receipt)
    # for i in tx_receipt['logs']:
    #     print(i)
    # print(108890955635952417480 - 3890955635952417480)
    # print(tx_receipt['blockNumber'])
    # event = oracle_contract.events.RespondTokenPrice().processReceipt(tx_receipt)
    # print(event)
    # from_block = client.w3.eth.blockNumber - 10000
    # print(from_block)
    # events = oracle_contract.events.RespondTokenPrice.createFilter(fromBlock=from_block)
    # print(events.get_new_entries())
    # entries = None
    # while not entries:
    #     entries = events.get_all_entries()
    # # print(entries)
    # for info in entries:
    #     print(info)
    #     print(info.args.oldPrice, info.args.newPrice)
    # print(client.w3.geth.personal.listAccounts())
    # print(client.w3.geth.personal.list_wallets())

    # with open("1.json", "r") as f:
    #     lp_info = json.load(f)
    #
    # lp = client.w3.eth.contract("0xE8E5E98554d0D0BfF9C4C0922726B0D947d7159D", abi=lp_info['abi'])
    #
    # print(lp.all_functions())
    # print(lp.functions.shareInfo().call())