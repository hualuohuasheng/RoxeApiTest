# -*- coding: utf-8 -*-

from web3 import Web3
import json
import time
from decimal import Decimal, localcontext
from roxe_libs.CoreFunction import Mysql
import math


def check_pwards_by_sql():
    e_reward = 2000000000000000000000
    admin_addr = "0x9842495d6bab5cb632777ff25b5b4c1e1d595f24"
    mysql = Mysql("192.168.43.208", 3306, "exone", "da0llarG!", "eth_data")
    mysql.connect_database()
    sql = "SELECT m.cycle, m.block, m.p_token, m.addr, m.s_balance, t.supply,m.p_awards, m.p_balance, m.p_unclaimed " \
          "FROM mining_data m LEFT JOIN token_supply t ON m.s_token = t.token  and m.block = t.block;"
    sql_res = mysql.exec_sql_query(sql)
    admin_reward = Decimal(0)
    tmp_reward = Decimal(0)
    for info in sql_res:
        if info['addr'] == admin_addr:
            a_reward = Decimal(e_reward) - tmp_reward
            print(a_reward == info['p_awards'], a_reward, info['p_awards'], tmp_reward + info['p_awards'])
            # assert a_reward == info['p_awards'], f"sql: {info['p_awards']} cal: {a_reward}, other: {tmp_reward}"
            tmp_reward = Decimal(0)
            continue
        print(info['s_balance'], info['supply'], info['p_awards'])
        cal_reward = Decimal(info['s_balance']) * Decimal(e_reward) * Decimal("0.85") / Decimal(info['supply'])
        cal_reward = Decimal(str(cal_reward).split('.')[0])
        assert cal_reward == info['p_awards'], f"sql: {info['p_awards']} cal: {cal_reward}"
        tmp_reward += cal_reward
        # print(tmp_reward)
    mysql.disconnect_database()


class SwapData:
    # eth 私链地址
    # provider = "http://192.168.38.227:18045"
    # eth 测试链地址
    provider = "https://ropsten.infura.io/v3/be5b825be13b4dda87056e6b073066dc"
    # provider = "https://mainnet.infura.io/v3/be5b825be13b4dda87056e6b073066dc"
    # provider = "https://mainnet.infura.io/v3/7688b2a20b8148db89f175da89c035bd"

    # factory_address = "0x9b1e7f15c9c32d1f18df1c70b320e6f0e783ef76"
    # router_address = "0x44cd9841b802482ea2bc773bb6d475124451400e"
    # pair_address = "0xda38632e43e00701897f2B15a2ED3f6441fa3594"
    #
    # token0_address = "0xd4956ae41ca6587aa050da6a63c425d1fc87f116"
    # token1_address = "0x9c6333c8141a0da7ac57b14052e35b08df877163"
    # token2_address = "0xf667d2f47a1d13eb36213fdab9725dda790237c7"
    # token3_address = "0xfc6847e8b8154214f2e8fb5f11a8516f3f2f6aa8"
    # token4_address = "0xea3ad11ae18bba3a5c937d3221bbf0b1bbbb0d0d"
    # token5_address = "0x69af52cd895ece886a918a3a4fb726f63e486cbb"

    factory_address = "0x39df422789de097f82ebc157e38880c2cc9a7f19"      # swapx
    # factory_address = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"    # uniswap
    # factory_address = "0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac"
    router_address = "0x4844ca662f66363f2c71ea833d2c9b152a026eb9"
    # router_address = "0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac"
    pair_address = "0x57F6dE84e9d74B53B69f3fB39dE4148D01090599"
    # pair_address = "0x20d7391103c0CceBA7e977Ef23443C1810AB66a5"
    swp_address = "0x06403D9DC00B7cF577023D49f96f899AEd86d6c0"

    # token0_address = "0xEB770B1883Dcce11781649E8c4F1ac5F4B40C978"  # ass
    # token1_address = "0xf80A32A835F79D7787E8a8ee5721D0fEaFd78108"  # wata

    token0_address = "0xf6f6bb2587155437c1c46e3E823E0a57175493FF"  # ass
    # token1_address = "0x18ea6e432c610b355a1fa6f2ad6cfe0885d291ca"  # wata
    token1_address = "0x82992557a3f4d5dfa298524b833ff38d1f088311"  # ltc


def get_abi(json_file):
    with open(json_file, 'r') as f:
        abi = json.dumps(json.load(f))
    return abi


class SwapClient:

    def __init__(self, provider_url):
        self.provider_url = provider_url
        self.web3 = Web3(Web3.HTTPProvider(self.provider_url))

        # 初始化factory, router
        self.factory = self.web3.eth.contract(address=self.web3.toChecksumAddress(SwapData.factory_address),
                                              abi=get_abi('./abi/Factory.json'))
        self.router = self.web3.eth.contract(address=self.web3.toChecksumAddress(SwapData.router_address),
                                             abi=get_abi('./abi/Router.json'))
        self.pair = self.web3.eth.contract(address=self.web3.toChecksumAddress(SwapData.pair_address),
                                           abi=get_abi('./abi/PairToken.json'))

        self.token0 = self.web3.eth.contract(address=self.web3.toChecksumAddress(SwapData.token0_address),
                                             abi=get_abi('./abi/CustomTokenERC20.json'))
        self.token1 = self.web3.eth.contract(address=self.web3.toChecksumAddress(SwapData.token1_address),
                                             abi=get_abi('./abi/CustomTokenERC20.json'))
        self.swp = self.web3.eth.contract(address=self.web3.toChecksumAddress(SwapData.swp_address),
                                          abi=get_abi("./abi/SwapXGovernToken.json"))
        # self.token2 = self.web3.eth.contract(address=self.web3.toChecksumAddress(SwapData.token2_address),
        #                                      abi=get_abi('./abi/CustomTokenERC20.json'))
        # self.token3 = self.web3.eth.contract(address=self.web3.toChecksumAddress(SwapData.token3_address),
        #                                      abi=get_abi('./abi/CustomTokenERC20.json'))
        # self.token4 = self.web3.eth.contract(address=self.web3.toChecksumAddress(SwapData.token4_address),
        #                                      abi=get_abi('./abi/CustomTokenERC20.json'))
        # self.token5 = self.web3.eth.contract(address=self.web3.toChecksumAddress(SwapData.token5_address),
        #                                      abi=get_abi('./abi/CustomTokenERC20.json'))

    def get_balance_of(self, account):
        balance = self.web3.eth.getBalance(account)
        return self.web3.fromWei(balance, 'ether')

    def getTransactionReceipt(self, transaction_hash):
        r = self.web3.eth.getTransactionReceipt(transaction_hash)
        print(r)
        print(r['status'])
        return r['status']

    def get_block_data(self, start_block, end_block):
        for i in range(start_block, end_block + 1):
            # print(i)
            info = self.web3.eth.getBlock(i)
            if info.transactions:
                print('------')
                print(info.number)
                print(info.transactions)
                for t_hash in info.transactions:
                    r = self.web3.eth.getTransactionReceipt(t_hash)
                    print(r)
                    print(r['from'], r['to'])
                    print(r['logs'])
                    print(len(r['logs']))
                    print(r['logs'][0]['data'])
                    # print(r['transactionHash'])
                    # print(self.web3.toBytes(r['transactionHash']))

    def add_liquidity(self):
        print("get balance...")
        print(self.token2.find_functions_by_name('balanceOf')[0](self.web3.eth.accounts[0]).call())
        print(self.token2.find_functions_by_name('balanceOf')[0](self.web3.eth.accounts[1]).call())
        print(self.token1.find_functions_by_name('balanceOf')[0](self.web3.eth.accounts[0]).call())
        print(self.token1.find_functions_by_name('balanceOf')[0](self.web3.eth.accounts[1]).call())
        self.web3.geth.personal.unlockAccount(self.web3.eth.accounts[0], '123456')

        print(self.token1.caller().call_function(self.token1.find_functions_by_name('approve')[0],
                                                 self.router.address, self.web3.toWei(10000, 'ether'),
                                                 transaction={
                                                     'from': self.web3.toChecksumAddress(self.web3.eth.accounts[0])}))
        print(self.token2.caller().call_function(self.token1.find_functions_by_name('approve')[0],
                                                 self.router.address, self.web3.toWei(10000, 'ether'),
                                                 transaction={
                                                     'from': self.web3.toChecksumAddress(self.web3.eth.accounts[0])}))
        # print(self.token1.find_functions_by_name('approve')[0](self.router.address, self.web3.toWei(10000, 'ether')).call({'from': self.web3.toChecksumAddress(self.web3.eth.accounts[0])}))
        # print(self.token2.find_functions_by_name('approve')[0](self.router.address, self.web3.toWei(10000, 'ether')).call({'from': self.web3.toChecksumAddress(self.web3.eth.accounts[0])}))

        print(self.router.find_functions_by_name('addLiquidity')[0](
            self.web3.toChecksumAddress(self.token2.address.lower()),
            self.web3.toChecksumAddress(self.token1.address.lower()),
            self.web3.toWei(1000, 'ether'), self.web3.toWei(1000, 'ether'),
            self.web3.toWei(0, 'ether'), self.web3.toWei(0, 'ether'),
            self.web3.toChecksumAddress(self.web3.eth.accounts[0].lower()),
            self.web3.toWei(1600769111199, 'ether')
        ).call({'from': self.web3.toChecksumAddress(self.web3.eth.accounts[0])}))
        # print(self.router.caller().call_function(self.router.find_functions_by_name('addLiquidity')[0],
        #                                          self.web3.toChecksumAddress(self.token2.address.lower()),
        #                                          self.web3.toChecksumAddress(self.token1.address.lower()),
        #                                          self.web3.toWei(1000, 'ether'), self.web3.toWei(1000, 'ether'),
        #                                          self.web3.toWei(0, 'ether'), self.web3.toWei(0, 'ether'),
        #                                          self.web3.toChecksumAddress(self.web3.eth.accounts[0].lower()),
        #                                          1600769111199,
        #                                          transaction={'from': self.web3.toChecksumAddress(self.web3.eth.accounts[0].lower())}))


# 初始化 ###
client = SwapClient(SwapData.provider)
# b = client.web3.eth.getBlock(client.web3.eth.blockNumber)
# t = b.timestamp + 2 * 24 * 3600 + 200
# print(client.web3.eth.blockNumber)
# print(b)
# print(client.web3.eth.blockNumber)
# print(b.timestamp)
# print(t)
# print(t * (10 ** 18))
# print(client.factory.all_functions())
# # # print(client.factory.all_functions())
# print(client.web3.eth.getBlock('last'))
# print(client.factory.find_functions_by_name('allPairsLength')[0]().call())
# p_addr = client.factory.find_functions_by_name('allPairs')[0](6).call()
# print(p_addr)
# p = client.web3.eth.contract(address=client.web3.toChecksumAddress(p_addr), abi=get_abi('./abi/PairToken.json'))
# token0 = p.find_functions_by_name('token0')[0]().call()
# token1 = p.find_functions_by_name('token1')[0]().call()
# print(token0)
# print(token1)
# a = client.factory.find_functions_by_name("getPair")[0]("0x82992557A3F4d5dfA298524B833FF38d1F088311", "0xf6f6bb2587155437c1c46e3E823E0a57175493FF").call()
# #
# print(a)
for i in range(0):
    p_addr = client.factory.find_functions_by_name('allPairs')[0](i).call()
    p = client.web3.eth.contract(address=client.web3.toChecksumAddress(p_addr), abi=get_abi('./abi/PairToken.json'))
    token0 = p.find_functions_by_name('token0')[0]().call()
    token1 = p.find_functions_by_name('token1')[0]().call()
    print('----')
    print(p_addr)
    print(token0)
    print(token1)
    # print(p.find_functions_by_name('balanceOf')[0]('0xBD8592ffFb1D031f27379550064bF2CA04F9C7Cc').call())


client.web3.eth.defaultAccount = client.web3.toChecksumAddress("0x1084d79A66EF86BFc9c945d4a21159a024dEE14e")
# # client.web3.eth.accounts.wa
# print(client.web3.eth.accounts)
# acc = client.web3.eth.account.from_key("ad246d5896fd96c40595ff58e6e2a8bd23ffb31e95b1fb786a9034d2df120492")
acc = client.web3.eth.account.from_key("ebed55a1f7e77144623167245abf39df053dc76fd8118ac7ae6e1ceeb84c5ed0")
# print(client.web3.eth.getBalance("0x1084d79A66EF86BFc9c945d4a21159a024dEE14e"))

# print(client.web3.eth.accounts)
# print(acc.address)
# print(acc.key)
# print(acc.privateKey)
private_key = b'\xeb\xedU\xa1\xf7\xe7qDb1g$Z\xbf9\xdf\x05=\xc7o\xd8\x11\x8a\xc7\xaen\x1c\xee\xb8L^\xd0'
# private_key = b'\xad$mX\x96\xfd\x96\xc4\x05\x95\xffX\xe6\xe2\xa8\xbd#\xff\xb3\x1e\x95\xb1\xfbxj\x904\xd2\xdf\x12\x04\x92'
# # print(client.web3.eth.getBlock('latest'))
nonce = client.web3.eth.getTransactionCount(client.web3.eth.defaultAccount)
print(client.web3.eth.defaultAccount)
print(client.pair.all_functions())

# print()
# print(client.pair.functions.allowance("0xBD8592ffFb1D031f27379550064bF2CA04F9C7Cc","0x1084d79A66EF86BFc9c945d4a21159a024dEE14e").call())

# txh = client.pair.functions.transferFrom("0xBD8592ffFb1D031f27379550064bF2CA04F9C7Cc",
#                                          "0x1084d79A66EF86BFc9c945d4a21159a024dEE14e", 100).transact({'from': "0x1084d79A66EF86BFc9c945d4a21159a024dEE14e"})
# print(txh)
# tx_receipt = client.web3.eth.waitForTransactionReceipt(txh)
# print(tx_receipt)
# print(client.pair.functions.allowance("0xBD8592ffFb1D031f27379550064bF2CA04F9C7Cc","0x1084d79A66EF86BFc9c945d4a21159a024dEE14e").call())
# print(client.web3.isConnected())
unicorn_txn = client.pair.functions.transfer(
    client.web3.toChecksumAddress("0x1084d79A66EF86BFc9c945d4a21159a024dEE14e"), 100).buildTransaction(
    {"chainId": 1, "gas": 3000000, "gasPrice": client.web3.toWei('1', 'gwei'), "nonce": nonce, "from": client.web3.toChecksumAddress("0x1084d79A66EF86BFc9c945d4a21159a024dEE14e")})
print(unicorn_txn)
# # signed_txn = client.web3.eth.account.signTransaction(unicorn_txn, acc.key)
signed_txn = acc.sign_transaction(unicorn_txn)
print(signed_txn)
txn = client.web3.toHex(client.web3.keccak(signed_txn.rawTransaction))
print(txn)
import traceback
try:
    print(type(signed_txn.rawTransaction))
    print(client.web3.eth.sendRawTransaction(signed_txn.rawTransaction))
    tx_receipt = client.web3.eth.waitForTransactionReceipt(txn)
    print(tx_receipt)
except Exception:
    traceback.print_exc()
# print(client.web3.eth.getTransactionReceipt(txn))
# print(client.web3.eth.gasPrice)
# print(client.web3.eth.getBalance("0xBD8592ffFb1D031f27379550064bF2CA04F9C7Cc"))
# print(client.pair.all_functions())
# print(client.pair.functions)
# print(client.pair.functions.balanceOf('0xBD8592ffFb1D031f27379550064bF2CA04F9C7Cc').call())
# print(client.pair.functions.transfer('0x1084d79A66EF86BFc9c945d4a21159a024dEE14e', 100).transact())
# print(client.pair.find_functions_by_name('balanceOf')[0]('0xBD8592ffFb1D031f27379550064bF2CA04F9C7Cc').call())
# print(client.pair.find_functions_by_name('transfer')[0]('0x1084d79A66EF86BFc9c945d4a21159a024dEE14e', 100).call())
# print(client.pair.interface)
# print(client.pair.find_functions_by_name('transfer')[0]('0x1084d79A66EF86BFc9c945d4a21159a024dEE14e', 100).call({"from": "0xBD8592ffFb1D031f27379550064bF2CA04F9C7Cc"}))
# print(client.pair.caller().call_function(client.pair.find_functions_by_name('transfer')[0], '0x1084d79A66EF86BFc9c945d4a21159a024dEE14e', 100))
# print(client.swp.all_functions())
# print(client.swp.find_functions_by_name('balanceOf')[0]('0x1084d79A66EF86BFc9c945d4a21159a024dEE14e').call())
# print(client.pair.find_functions_by_name('transfer')[0]('0x1084d79A66EF86BFc9c945d4a21159a024dEE14e', 100).call())
# print(client.pair.find_functions_by_name('balanceOf')[0]('0x2b8ADB96c423512f56a0E1468dAca4621E6B4Ea1').call())
# print(client.pair.find_functions_by_name('balanceOf')[0](
#     client.web3.toChecksumAddress('0x7e56c279f2cf775b8dda7cb334d5cef3f79aa8be')).call())
# print(client.pair.find_functions_by_name('balanceOf')[0](
#     client.web3.toChecksumAddress('0x20d7391103c0CceBA7e977Ef23443C1810AB66a5')).call())
# print(client.pair.find_functions_by_name('totalSupply')[0]().call())
#
# token0 = client.pair.find_functions_by_name('token0')[0]().call()
# token1 = client.pair.find_functions_by_name('token1')[0]().call()
# print(token0)
# print(token1)
# print(client.factory.find_functions_by_name('getPair')[0](token0, token1).call())
# # print(client.factory.find_functions_by_name('createPair')[0](token0, token1).call())
#
# f = client.web3.eth.contract(address=client.web3.toChecksumAddress('0x39df422789de097f82ebc157e38880c2cc9a7f19'),
#                              abi=get_abi('./abi/Factory.json'))
# print(f.all_functions())
# print(f.find_functions_by_name('allPairsLength')[0]().call())
# print(f.find_functions_by_name('getPair')[0](token0, token1).call())

# print(client.web3.eth.getTransactionReceipt('0x7e020ff71443c87cd7fb0cc637cc487c1387a9f21dc516cb95d1e42add06abf3'))
# print(client.web3.eth.getTransaction('0x7e020ff71443c87cd7fb0cc637cc487c1387a9f21dc516cb95d1e42add06abf3'))
# print(client.factory.find_functions_by_name('getPair')[0])
# print(client.factory.find_functions_by_name('getPair'))
# print(client.factory.find_functions_by_name('getPair')[0](client.web3.toChecksumAddress('0x6B175474E89094C44Da98b954EedeAC495271d0F'),
#                                                           client.web3.toChecksumAddress('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')).call())
# print(client.factory.address)
# print(client.router.all_functions())
# print(client.router.address)
# print(client.token1.all_functions())
# print(client.router.find_functions_by_name('factory')[0]().call())

# client.add_liquidity()
# print(client.web3.isConnected())
# print(client.get_balance_of('0x9842495d6bab5cb632777ff25b5b4c1e1d595f24'))
# client.getTransactionReceipt('0x3934f805bcec2c44a8ae67b394327635630fa1fa19ffb783c6b67cad669b78fe')
# client.getTransactionReceipt('0x476bc36ea654664c592b595af2994c8c623e11cdcf4e7f8041e2608827720e42')
# client.get_block_data(627469, 627533)
# accounts = client.web3.eth.accounts
# print(accounts[0])

# a = 2.88e+42
# b = 218838333181362268625
# c = 2.4e+21
# x1 = Decimal(a) / (Decimal(b) * Decimal(0.997) + Decimal(c))
# print(x1)
# y1 = Decimal(1.2e+21) - Decimal(x1)
# print(y1)
#
# print(Decimal(b) * Decimal(0.997))
# print(Decimal(b) * Decimal(0.003))
# print(Decimal(b) * Decimal(0.003) /Decimal(2.618838333181362268625e+21))
# print((Decimal(b) * Decimal(0.003) /Decimal(2.618838333181362268625e+21)) * (Decimal(1.414213562373095047801e+21) + Decimal(282842712474619009760)))
#
# print(Decimal(1.1e+21) - Decimal(1.093518323257742061689e+21))
# print(Decimal(2.603407002712348467332e+21) - Decimal(2.618838333181362268625e+21))
# print(Decimal(15431330469014142976) - Decimal(15431330469013801293))
# print(Decimal(15431330469013801293) / Decimal(6481676742257938311))
# print(Decimal(2.618838333181362268625e+21) / Decimal(1.1e+21))
# print(Decimal(2e+20) / Decimal(1.1e+21))
# print(Decimal(2e+20) / Decimal(1.1e+21) * (Decimal(1.414213562373095047801e+21) + Decimal(282842712474619009760)))
# print((Decimal(1.414213562373095047801e+21) + Decimal(282842712474619009760) - Decimal(308555686335948007371.6363636)))
# # print(Decimal(1388500588511766043360) / Decimal(308555686335948007371))
# print(Decimal(2841700652300000000000) / Decimal(558263617100000000000))
# print(Decimal(1.414213562373095047801e+21) / Decimal(272842712474619009760))
# print(Decimal(0.85))
# check_pwards_by_sql()

# with localcontext() as ctx:
#     ctx.prec = 28
#     print(ctx.prec)
#     # print(ctx.prec)
#     print(Decimal(1414213562373095047801))
#     print(Decimal(1697056274847714057561))
#     print(Decimal(2000000000000000000000))
#     print(Decimal("0.85"))
#     print(Decimal(1414213562373095047801) / Decimal(1697056274847714057561))
#     print(1414213562373095047801 / 1697056274847714057561 * 2000000000000000000000 * 0.85)
#     # print(Decimal(282842712474619009760) / Decimal(1697056274847714057561))
#     print(Decimal(1414213562373095047801) * Decimal(2000000000000000000000) * Decimal("0.85") / Decimal(1697056274847714057561))
#     print(Decimal(282842712474619009760) * Decimal(2000000000000000000000) * Decimal("0.85") / Decimal(1697056274847714057561))
#     print(282842712474619009760 / 1697056274847714057561 * 2000000000000000000000 * 0.85)
#
# print(Decimal(2841700652300000000000) + Decimal(558263617100000000000) + Decimal(35725500000000000) + Decimal(4600000005100000000000))
# print(Decimal(35725500000000000) + Decimal(4600000005100000000000))
#
# print(Decimal(2841700652300000000000) / Decimal(8000000000000000000000))
# print(Decimal(558263617100000000000) / Decimal(8000000000000000000000))
# print(Decimal(35725500000000000) / Decimal(8000000000000000000000))
# print(Decimal(4600000005100000000000) / Decimal(8000000000000000000000))
# print(Decimal(1388500588511766043360) / Decimal(308555686335948007371))
# print(Decimal(c) * Decimal(0.997))
# print(Decimal(a) + Decimal(b) <= Decimal(c))

# accounts = client.web3.eth.accounts
# account = '0x2b8ADB96c423512f56a0E1addLiquidity468dAca4621E6B4Ea1'
# print(len(accounts))
# print(accounts)
# print(accounts.index('0x5792f745f632fe6ac28f65e4ffe606d5c9fd9393'))
# print(accounts.index('0x9842495d6bab5cb632777ff25b5b4c1e1d595f24'))
# print(w3.eth.gasPrice)
# print(client.web3.eth.blockNumber)
# res = client.web3.eth.getBlock(627533, True)
# print(res)
# for k, v in dict(res).items():
#     print(k, v)
# print(client.web3.eth.getBlock(626900).timestamp)
# print(client.web3.eth.getBlock(627597).timestamp)
# print(client.web3.eth.getBlock(627000).timestamp)
# print(time.time())

# print(time.strftime("%Y-%m-%d %H:%M:%M", time.localtime()))
# now_time = time.time()
# end_num = 627228
# for i in range(626900, 627228):
# print(i)
# block_time = client.web3.eth.getBlock(i).timestamp
# print(now_time - block_time)
# if now_time - block_time < 90 *60:
#     print(i)
#     break

# # account0_balance = w3.eth.getBalance()
# account0_balance = w3.eth.getBalance(account)
# print(account0_balance)
# print(w3.fromWei(account0_balance, 'ether'))
# print(w3.eth.getTransactionReceipt('0x9cdc4f8c018ca6f6f930ad3071b8204efa796e90ee507b04cf5158b8dc40d514'))

# with open('./abi/Factory.json', 'r') as f:
#     factory_abi = json.dumps(json.load(f))
# print(factory_abi)

# factory_address = "0xf94c890b541c5d4182de831bf0c02c808850d0fc"
# factory_address = "0x9b1e7f15c9c32d1f18df1c70b320e6f0e783ef76"
# print(w3.toChecksumAddress(factory_address))

# factory = client.web3.eth.contract(address=client.web3.toChecksumAddress(factory_address), abi=factory_abi)

# rr = factory.web3.eth.getProof(client.web3.toChecksumAddress(accounts[0]), [0])
# print('======')
# print(rr)
# print(factory.address)
# print(factory.all_functions())
# print(factory.events.MyEvent())
# print(type(factory.events))
# print(factory.events)
# print(client.web3.eth.filter({'fromBlock': 0, 'toBlock': 'latest'}).get_new_entries())
# print(factory.caller().web3.eth.filter({'fromBlock': 0, 'toBlock': 'latest'}))
# print(factory.caller().call_function(factory.find_functions_by_name('allEvents')[0]))
# print(factory.caller().call_function(factory.find_functions_by_name('allPairsLength')[0]))
# print(factory.caller().call_function(factory.find_functions_by_name('allPairs')[0], 0))
# print(factory.find_functions_by_name('allPairsLength')[0]().call())
# print(factory.find_functions_by_name('allPairs')[0](2).call())

# with open('./abi/PairToken.json', 'r') as f:
#     sToken_abi = json.dumps(json.load(f))
# print(sToken_abi)
#
# sToken_addr = "0xda38632e43e00701897f2b15a2ed3f6441fa3594"
# sToken = client.web3.eth.contract(address=client.web3.toChecksumAddress(sToken_addr), abi=sToken_abi)
# print(router.address)
# print(sToken.all_functions())
# print(sToken.events.abi)
# print(w3.geth.personal.unlockAccount(w3.eth.accounts[0], '123456'))


# staking

# web3 = Web3(Web3.HTTPProvider('https://ropsten.infura.io/v3/be5b825be13b4dda87056e6b073066dc'))
#
# with open('./abi/Staking.json', 'r') as f:
#     infos = json.load(f)
#     # print(infos)
# # print(infos[])
# staking_abi = json.dumps(infos['abi'])
# staking_addr = "0x7e56c279f2cf775b8dda7cb334d5cef3f79aa8be"
# # print(staking_abi)
# staking = web3.eth.contract(address=web3.toChecksumAddress(staking_addr), abi=staking_abi)
# print(staking.address)
# print(staking.all_functions())
# print(staking.find_functions_by_name('userInfo'))

# web3 = client.web3

# with open('./abi/SwapXGovernToken.json', 'r') as f:
#     infos = json.load(f)
#     # print(infos)
# # print(infos[])
# swp_abi = json.dumps(infos['abi'])
# swp_addr = "0x06403d9dc00b7cf577023d49f96f899aed86d6c0"
# swp = web3.eth.contract(address=web3.toChecksumAddress(swp_addr), abi=swp_abi)
# print(swp.all_functions())
# print(swp.find_functions_by_name('totalSupply')[0]().call())
# print(swp.find_functions_by_name('balanceOf')[0](
#     web3.toChecksumAddress('0x7e56c279f2cf775b8dda7cb334d5cef3f79aa8be')).call())
# print(swp.find_functions_by_name('balanceOf')[0](
#     web3.toChecksumAddress('0x2b8ADB96c423512f56a0E1468dAca4621E6B4Ea1')).call())
#
# print(swp.find_functions_by_name('balanceOf')[0](web3.toChecksumAddress('0xd1646323954129450345656ae86adbbf47674382')).call())
#
# print(swp.find_functions_by_name('balanceOf')[0](web3.toChecksumAddress('0xCEC0Ac18d0F4A8D6CdC93f4920A1d850ABE4fA63')).call())
#
# print(1*24*60*60)
# with open('./abi/Migrator.json', 'r') as f:
#     infos = json.load(f)
#     # print(infos)
# 501127
# 249909 3840 3420
# # print(infos[])
# migrator_abi = json.dumps(infos)
# migrator_addr = "0x5824d0081e9e4Bd45C26C7ed175630A357344329"
# migrator = web3.eth.contract(address=web3.toChecksumAddress(migrator_addr), abi=migrator_abi)
# print(migrator.all_functions())
# print(migrator.find_functions_by_name('chef')[0]().call())
# print(migrator.find_functions_by_name('migrate')[0]('0x20d7391103c0CceBA7e977Ef23443C1810AB66a5').call())
# print(migrator.find_functions_by_name('totalSupply')[0]().call())
# print(migrator.find_functions_by_name('balanceOf')[0](web3.toChecksumAddress('0x7e56c279f2cf775b8dda7cb334d5cef3f79aa8be')).call())
# print(migrator.find_functions_by_name('migrate')[0](web3.toChecksumAddress('0x20d7391103c0CceBA7e977Ef23443C1810AB66a5')).call())

