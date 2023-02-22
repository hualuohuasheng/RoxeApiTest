from SmartContract.DODO.EOS_DODO import *
import sys
from web3 import Web3, HTTPProvider, WebsocketProvider
from SmartContract.CommonTool import load_from_json_file
# from roxe_libs.pub_function import setcustomlogger

curPath = os.path.dirname(os.path.abspath(__file__))
mylogger = setCustomLogger("balanceEOS", curPath + "/balancer.log", isprintsreen=True)

# 加载.env文件中变量到系统环境变量
load_dotenv()
# rpcNode = "http://10.100.1.10:8888/v1/chain"
rpcNode = "http://172.17.3.161:7878/v1/chain"
walletNode = "http://10.100.1.10:8889/v1/wallet"

interval = os.getenv("FREQ")
owner = os.getenv("ADMIN")
# swapContract = os.getenv("CONTRACT")

bp = "roxe1"
nonadmin = "alice1111111"
user1 = "bob111111111"
user2 = "lml111111111"
# admin = "roxeswap1213"  # 6位精度
# admin = "roxetestswap"  # 6位精度
# admin = "roxeswaplml1"  # 6位精度
# admin = "roxeswaplml2"  # 6位精度
# admin = "roxeswaplml3"  # 6位精度
admin = "roxeswaplml4"  # 6位精度

swapContract = admin
tokenowner = "roxearntoken"
tokenissuer = "tokenissuer1"
admin_pub = "ROXE6m2TpGWE59yDPWuBaB3xSJSgYWkggzSTuDv5vLfS3hYzB6UTU2"
tokenowner_pub = "ROXE5rM2nqtmCqyeRMpmQQMVTMYYZ9VYq9JDgve4t3Gzy6gVU1wB1z"
pub = "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH"
trader_pub = "ROXE6bYcFRBBLugKtxfkNxnyyrxUFV2LMGT3h9GcDisd6QYUyt2xfX"

acc2pub_keys = {
    "roxe1": "ROXE6m2TpGWE59yDPWuBaB3xSJSgYWkggzSTuDv5vLfS3hYzB6UTU2",
    "roxeswap1213": "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH",
    admin: "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH",
    "roxetestswap": "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH",
    "roxearntoken": "ROXE5rM2nqtmCqyeRMpmQQMVTMYYZ9VYq9JDgve4t3Gzy6gVU1wB1z",
    "tokenissuer1": "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH",
    "maintainer11": "ROXE6m2TpGWE59yDPWuBaB3xSJSgYWkggzSTuDv5vLfS3hYzB6UTU2",
    "alice1111111": "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH",
    "bob111111111": "ROXE6bYcFRBBLugKtxfkNxnyyrxUFV2LMGT3h9GcDisd6QYUyt2xfX",
    user2: "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH",
    "carol1111111": "ROXE6bYcFRBBLugKtxfkNxnyyrxUFV2LMGT3h9GcDisd6QYUyt2xfX",
    "112acnogsedo": "ROXE7Bm8LAeVXTD1XMvRmj3gG4o89uySacRRvuSEQJxHBkKiiU1pZY",
    "1114wmpblocm": "ROXE7DUJAgEwxbmY2ReM8rQVTjgw83AxaRrBvoc4fauxTSenMmaQhg",
    "tbtc2tusdt55": "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH",
    "btc2usdttest": "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH",
}

keys = [
    os.getenv("EOS_KEY"),
    "5JZDFmwRwxJU2j1fugGtLLaNp2bcAP2PKy5zsqNkhn47v3S3e5w",
    "5JxT1aA8MiZZe7XjN3SYaQ65NSbZXrBcjePaSwRifK7jJLdjSf3",
    "5JHFTcGiKFDXFR64voMJXnxWZUqBgaEAnqMiyjJzBLQn9tHhWA8",
    "5HwYSQMW2Xy37Q9nhdKz7T32eLxwbDq29rMzGXrRQJwveh9B7sG",
    "5J6BA1U4QdQPwkFWsphU96oBusvsA8V2UJDtMtKgNneakBK9YrN",
    "5KQkb4xcjWfNvvotM6JspVpupddbPCj62SvTTUTKeLhHmfuH3Zp",
    "5JyL5XytgZSdDK3DR2snUX5wVEGD7Jg7mXcVNq7tNgQL5T4DxC9"
]

avaKeys = [
    'PUB_K1_6MRyAjQq8ud7hVNYcfnVPJqcVpscN5So8BhtHuGYqET5BoDq63',
    'PUB_K1_6m2TpGWE59yDPWuBaB3xSJSgYWkggzSTuDv5vLfS3hYz86U7Ws',
    'PUB_K1_5rM2nqtmCqyeRMpmQQMVTMYYZ9VYq9JDgve4t3Gzy6gVUJvhr5',
    'PUB_K1_6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHqhqhA',
    'PUB_K1_8Av6ToXNYrGNdiQtpdUAG8LBDoMM3RZnin5NYpHk4WdKveS78Y',
    'PUB_K1_6bYcFRBBLugKtxfkNxnyyrxUFV2LMGT3h9GcDisd6QYV3YdSod',
    'PUB_K1_7Bm8LAeVXTD1XMvRmj3gG4o89uySacRRvuSEQJxHBkKiegykjG',
    'PUB_K1_7DUJAgEwxbmY2ReM8rQVTjgw83AxaRrBvoc4fauxTSenRTjoNL'
]


BONE = 1000000000


def bdiv(a, b):
    a1 = a * BONE
    c = (b // 2 + a1) // b
    # print(int(c))
    return int(c)


def bmul(a, b):
    c0 = int(a * b)
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


def convert_one_decimals(tokenAmount, tokenDecimal, signed_one=1):
    res = tokenAmount * math.pow(10, signed_one * (9 - tokenDecimal))
    # res = int(res) / int(math.pow(10, tokenDecimal))
    return int(res)


def pushAction(account, key, action, data):
    permission = "active"
    pub_keys = [key]
    tx_data = {
        "actions": [{
            "account": swapContract,
            "name": action,
            "authorization": [{"actor": account, "permission": permission}],
            "data": data
        }],
        "pub_keys": pub_keys
    }
    # print(tx_data)
    mylogger.info("发送的交易数据: {}".format(tx_data))
    return tx_data


def pushTransaction(account, action, data):
    results = eosrpc.transaction(pushAction(account, acc2pub_keys[account], action, data))
    return results


def deployBalancerContract(userName, pub_keys):
    wasmFilePath = curPath + "/contracts/1211/eoswap/eoswap.wasm"
    import binascii
    with open(wasmFilePath, "rb") as f:
        info = f.read()
        wasmHexString = binascii.hexlify(info).decode('utf-8')
        # info = str(info, encoding="hex")
    # print(wasmHexString)
    with open(curPath + "/contracts/1211/eoswap/eoswap.compile", "r") as f:
        serializedAbiHexString = f.read().strip()

    # print(serializedAbiHexString)
    tx_data = {
        'actions': [
            {
                'account': 'roxe',
                'name': 'setcode',
                'authorization': [{
                    'actor': userName,
                    'permission': 'active'
                }],
                'data': {
                    'account': userName,
                    'vmtype': '0',
                    'vmversion': '0',
                    'code': wasmHexString
                }
            },
            {
                'account': 'roxe',
                'name': 'setabi',
                'authorization': [{
                    'actor': userName,
                    'permission': 'active'
                }],
                'data': {
                    'account': userName,
                    'abi': serializedAbiHexString
                }
            }
        ],
        "pub_keys": pub_keys
    }
    results = eosrpc.transaction(tx_data)
    mylogger.info("deploy {}".format(userName))
    mylogger.info(f"bin: {results[0]}")
    mylogger.info(f"sig: {results[1]}")
    mylogger.info(f"action: {results[2]}")


def newToken(tokenName, tokenDecimal):
    max_supply = to_max_supply(tokenName, int(math.pow(10, 18 - tokenDecimal)), tokenDecimal)
    print(max_supply)
    client.newtoken(tokenissuer, max_supply)


def mint(to, amount):
    results = pushTransaction(to, "mint", {
        "msg_sender": to,
        "amt": amount
    })
    mylogger.info(f"mint to {to} bin: {results[0]}")
    mylogger.info(f"mint to {to} sig: {results[1]}")
    mylogger.info(f"mint to {to} action: {results[2]}")
    # client.mint(nonadmin, to_wei_asset(0.0001, "TBTC", 8))


def to_wei(value, d=9):
    return value * int(math.pow(10, d))


def allowDosContract(user, pubk):
    results = eosrpc.transaction(allowContract(user, pubk, swapContract))
    if "transaction_id" not in results:
        # mylogger.info(f"allowDosContract bin: {results}")
        # mylogger.info(f"allowDosContract sig: {results}")
        mylogger.info(f"allowDosContract action: {results}")
    else:
        mylogger.info(f"{user}授权合约{swapContract}成功")
    return results


def allowDosContracts():
    for user, key in acc2pub_keys.items():
        allowDosContract(user, key)


def parseBalanceInfo(poolBalance):
    parsePoolBalance = {}
    for row in poolBalance["rows"]:
        s_info = row["balance"].split(" ")
        d = len(s_info[0].split(".")[-1])
        parsePoolBalance[s_info[1]] = row
        intPart = int(s_info[0].split(".")[0]) * int(math.pow(10, d))
        floatPart = int(s_info[0].split(".")[-1])
        parsePoolBalance[s_info[1]]["parseBalance"] = intPart + floatPart
    return parsePoolBalance


class SwapClient:

    def newPool(self, msgSender, poolName):
        results = pushTransaction(msgSender, "newpool", {"msg_sender": msgSender, "pool_name": poolName})
        mylogger.info(f"new pool: {poolName}")
        # mylogger.info(f"bin: {results[0]}")
        # mylogger.info(f"sig: {results[1]}")
        mylogger.info(f"action: {results}")
        return results

    def setSwapFee(self, msgSender, poolName, fee):
        results = pushTransaction(msgSender, "setswapfee", {
            "msg_sender": msgSender,
            "pool_name": poolName,
            "swapFee": fee
        })
        mylogger.info(f"setSwapFee: {fee}")
        # mylogger.info(f"bin: {results[0]}")
        # mylogger.info(f"sig: {results[1]}")
        mylogger.info(f"action: {results}")
        return results

    def transferex(self, msgSender, dst, amt):
        results = pushTransaction(msgSender, "transferex", {
            "msg_sender": msgSender,
            "dst": dst,
            "amt": amt
        })
        mylogger.info(f"transferex")
        # mylogger.info(f"bin: {results[0]}")
        # mylogger.info(f"sig: {results[1]}")
        mylogger.info(f"action: {results}")
        return results

    def extransfer(self, fromAccount, toAccount, quantity, memo):
        results = pushTransaction(fromAccount, "extransfer", {
            # "msg_sender": msgSender,
            "from": fromAccount,
            "to": toAccount,
            "quantity": quantity,
            "memo": memo,
        })
        mylogger.info(f"extransfer")
        # mylogger.info(f"bin: {results[0]}")
        # mylogger.info(f"sig: {results[1]}")
        mylogger.info(f"action: {results}")
        return results

    def setPublicSwap(self, msgSender, poolName, public_):
        results = pushTransaction(msgSender, "setpubswap", {
            "msg_sender": msgSender,
            "pool_name": poolName,
            "public_": public_
        })
        mylogger.info(f"setPublicSwap: {public_}")
        # mylogger.info(f"bin: {results[0]}")
        # mylogger.info(f"sig: {results[1]}")
        mylogger.info(f"action: {results}")
        return results

    def setControler(self, msgSender, poolName, manager):
        results = pushTransaction(msgSender, "setcontroler", {
            "msg_sender": msgSender,
            "pool_name": poolName,
            "manager": manager
        })
        mylogger.info(f"setControler: {manager}")
        # mylogger.info(f"bin: {results[0]}")
        # mylogger.info(f"sig: {results[1]}")
        mylogger.info(f"action: {results}")
        return results

    def bind(self, msgSender, poolName, balance, denorm):
        results = pushTransaction(msgSender, "bind", {
            "msg_sender": msgSender,
            "pool_name": poolName,
            "balance": balance,
            "denorm": denorm
        })
        mylogger.info(f"bind..")
        # mylogger.info(f"bin: {results[0]}")
        # mylogger.info(f"sig: {results[1]}")
        mylogger.info(f"action: {results}")
        return results

    def rebind(self, msgSender, poolName, balance, denorm):
        results = pushTransaction(msgSender, "rebind", {
            "msg_sender": msgSender,
            "pool_name": poolName,
            "balance": balance,
            "denorm": denorm
        })
        mylogger.info(f"rebind..")
        # mylogger.info(f"bin: {results[0]}")
        # mylogger.info(f"sig: {results[1]}")
        mylogger.info(f"action: {results}")
        return results

    def unbind(self, msgSender, poolName, token):
        results = pushTransaction(msgSender, "unbind", {
            "msg_sender": msgSender,
            "pool_name": poolName,
            "token": token,
        })
        mylogger.info(f"unbind..")
        # mylogger.info(f"bin: {results[0]}")
        # mylogger.info(f"sig: {results[1]}")
        mylogger.info(f"action: {results}")
        return results

    def finalize(self, msgSender, poolName):
        results = pushTransaction(msgSender, "finalize", {
            "msg_sender": msgSender,
            "pool_name": poolName,
        })
        mylogger.info(f"finalize..")
        # mylogger.info(f"bin: {results[0]}")
        # mylogger.info(f"sig: {results[1]}")
        mylogger.info(f"action: {results}")
        return results

    def joinpool(self, msgSender, poolName, poolAmountOut, maxAmountsIn):
        results = pushTransaction(msgSender, "joinpool", {
            "msg_sender": msgSender,
            "pool_name": poolName,
            "poolAmountOut": poolAmountOut,
            "maxAmountsIn": maxAmountsIn
        })
        mylogger.info(f"joinpool..")
        # mylogger.info(f"bin: {results[0]}")
        # mylogger.info(f"sig: {results[1]}")
        mylogger.info(f"action: {results}")
        return results

    def exitpool(self, msgSender, poolName, poolAmountIn, minAmountsOut):
        results = pushTransaction(msgSender, "exitpool", {
            "msg_sender": msgSender,
            "pool_name": poolName,
            "poolAmountIn": poolAmountIn,
            "minAmountsOut": minAmountsOut
        })
        mylogger.info(f"exitpool..")
        # mylogger.info(f"bin: {results[0]}")
        # mylogger.info(f"sig: {results[1]}")
        mylogger.info(f"action: {results}")
        return results

    def swapAmountIn(self, msgSender, poolName, tokenAmountIn, minAmountOut, maxPrice):
        results = pushTransaction(msgSender, "swapamtin", {
            "msg_sender": msgSender,
            "pool_name": poolName,
            "tokenAmountIn": tokenAmountIn,
            "minAmountOut": minAmountOut,
            "maxPrice": maxPrice
        })
        mylogger.info(f"swapAmountIn..")
        # mylogger.info(f"bin: {results[0]}")
        # mylogger.info(f"sig: {results[1]}")
        mylogger.info(f"action: {results}")
        return results

    def swapAmountOut(self, msgSender, poolName, maxAmountIn, tokenAmountOut, maxPrice):
        results = pushTransaction(msgSender, "swapamtout", {
            "msg_sender": msgSender,
            "pool_name": poolName,
            "maxAmountIn": maxAmountIn,
            "tokenAmountOut": tokenAmountOut,
            "maxPrice": maxPrice
        })
        mylogger.info(f"swapAmountOut..")
        # mylogger.info(f"bin: {results[0]}")
        # mylogger.info(f"sig: {results[1]}")
        mylogger.info(f"action: {results}")
        return results

    def gulp(self, msgSender, poolName, token):
        results = pushTransaction(msgSender, "gulp", {
            "msg_sender": msgSender,
            "pool_name": poolName,
            "token": token
        })
        mylogger.info(f"exitpool..")
        # mylogger.info(f"bin: {results[0]}")
        # mylogger.info(f"sig: {results[1]}")
        mylogger.info(f"action: {results}")
        return results


class BalancerEosTest:

    def __init__(self):
        self.swapClient = SwapClient()
        self.c = ChainClient(rpcNode)
        self.w = WalletClient(walletNode)
        self.w3 = None
        self.mathContract = None

    def getEthRpcNode(self):
        rpcAddr = 'https://kovan.infura.io/v3/be5b825be13b4dda87056e6b073066dc'
        bMatchAddr = "0xa7bfC6C56E9E234121e3493d22B5221A771e8279"
        self.w3 = Web3(HTTPProvider(rpcAddr, request_kwargs={'timeout': 120}))
        mathPath = os.path.join(curPath, "./BMath.json")
        self.mathContract = self.w3.eth.contract(address=bMatchAddr, abi=load_from_json_file(mathPath)["abi"])
        bMatchAddr2 = "0x76B07429bC6612ddc0aE66EA7Fe7EEC0c69A91A5"
        self.mathContract2 = self.w3.eth.contract(address=bMatchAddr2, abi=load_from_json_file(mathPath)["abi"])

    def getPoolInfo(self, poolName, poolContract):
        infos = self.c.getTableRows(poolContract, poolContract, "pools")
        res = None
        for row in infos["rows"]:
            if row["pool"] == poolName:
                res = row
                break
        return res

    def getPoolSupply(self, account, poolContract):
        infos = self.c.getTableRows(account, poolContract, "stat")
        for i in infos["rows"]:
            s_info = i["supply"].split(" ")
            d = len(s_info[0].split(".")[-1])
            parseSupply = int(float(s_info[0]) * math.pow(10, d))
            parseMaxSupply = int(float(i["max_supply"].split(" ")[0]) * math.pow(10, d))
            i["parseSupply"] = parseSupply
            i["parseMaxSupply"] = parseMaxSupply
        return infos["rows"]

    def getAccountSupply(self, account, poolContract, poolName):
        infos = self.c.getTableRows(account, poolContract, "accounts")
        res = [i for i in infos["rows"] if i['balance']['contract'] == poolName]
        if res:
            supply = res[0]["balance"]["quantity"]
            d = len(supply.split(" ")[0].split(".")[-1])
            parseSupply = int(float(supply.split(" ")[0]) * int(math.pow(10, d)))
            return parseSupply
        else:
            return 0

    def getAccountBalance(self, account, tokens, tContract="roxearntoken"):
        # print(tContract)
        infos = self.c.getTableRows(account, tContract, "accounts")
        # print(infos)
        res = {}
        for token in tokens:
            res[token] = {"balance": 0, "parseBalance": 0}

        for row in infos["rows"]:
            s_info = row["balance"].split(" ")
            if s_info[1] in tokens:
                d = len(s_info[0].split(".")[-1])
                res[s_info[1]] = row
                res[s_info[1]]["parseBalance"] = int(float(s_info[0]) * math.pow(10, d))

        return res

    def checkNewPoolWithNonAdminAccount(self, user, poolName):
        mylogger.info(sys._getframe().f_code.co_name)
        tx = self.swapClient.newPool(user, poolName)
        assert "ERR_NOT_CONTROLLER" in tx['json']["error"]["details"][0]["message"], "非admin账户创建pool失败"
        poolInfo = self.getPoolInfo(poolName, admin)
        assert poolInfo is None

    def checkNewPoolSuccess(self, poolName):
        mylogger.info(sys._getframe().f_code.co_name)
        tx = self.swapClient.newPool(admin, poolName)
        time.sleep(1)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(poolInfo)
        assert poolInfo["pool"] == poolName
        assert poolInfo["pools"]["mutex"] == 0
        assert poolInfo["pools"]["factory"] == admin
        assert poolInfo["pools"]["controller"] == admin
        assert poolInfo["pools"]["publicSwap"] == 0
        assert poolInfo["pools"]["swapFee"] == 1
        assert poolInfo["pools"]["finalized"] == 0
        assert poolInfo["pools"]["tokens"] == []
        assert poolInfo["pools"]["records"] == []
        assert poolInfo["pools"]["totalWeight"] == 0

    def checkNewPoolWhenPoolAlreadyExist(self, poolName):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        assert poolInfo is not None, "该pool还没创建，不应该执行此用例"
        tx = self.swapClient.newPool(admin, poolName)
        assert "ALREADY_EXIST_POOL" in tx["error"]["details"][0]["message"], "非admin账户创建pool失败"
        poolInfo2 = self.getPoolInfo(poolName, admin)
        assert poolInfo == poolInfo2

    def checkSetSwapFeeFeeIs0(self, poolName):
        mylogger.info(sys._getframe().f_code.co_name)
        tx = self.swapClient.setSwapFee(admin, poolName, 0)
        assert tx["code"] == 500, "交易应该失败"
        assert "ERR_MIN_FEE" in tx["error"]["details"][0]["message"], "交易费设置为0，错误信息不正确"

    def checkSetSwapFeeMsgSenderIsNotPoolController(self, poolName):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")
        assert user1 != poolInfo["pools"]["controller"]
        tx = self.swapClient.setSwapFee(user1, poolName, 0)
        assert tx["code"] == 500, "交易应该失败"
        assert "ERR_NOT_CONTROLLER" in tx["error"]["details"][0]["message"], "交易费设置为0，错误信息不正确"
        poolInfo2 = self.getPoolInfo(poolName, admin)
        assert poolInfo["pools"]["swapFee"] == poolInfo2["pools"]["swapFee"]

    def checkSetSwapFeeFeeExceedMaxFee(self, poolName):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")
        fee = int(math.pow(10, 9))
        mylogger.info("设置的费用: {}".format(fee))
        tx = self.swapClient.setSwapFee(admin, poolName, fee)
        assert tx["code"] == 500, "交易应该失败"
        assert "ERR_MAX_FEE" in tx["error"]["details"][0]["message"], "交易费设置为0，错误信息不正确"
        poolInfo2 = self.getPoolInfo(poolName, admin)
        assert poolInfo["pools"]["swapFee"] == poolInfo2["pools"]["swapFee"]

    def checkSetSwapFeePass(self, poolName, fee):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")
        mylogger.info("设置的费用: {}".format(fee))
        tx = self.swapClient.setSwapFee(admin, poolName, fee)
        assert "transaction_id" in tx.keys(), "交易应该成功"
        time.sleep(0.5)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        mylogger.info(f"设置交易费用后，{poolName} pool info: {poolInfo}")
        assert fee == poolInfo2["pools"]["swapFee"]

    def checkSetSwapFeeAfterFinalized(self, poolName):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")
        if poolInfo['pools']["finalized"] == 0:
            mylogger.info("当前pool未finalized, 不执行此用例")
            return
        fee = poolInfo["pools"]["swapFee"] + 1
        mylogger.info("设置的费用: {}".format(fee))
        tx = self.swapClient.setSwapFee(admin, poolName, fee)
        assert tx["code"] == 500, "交易应该失败"
        assert "ERR_IS_FINALIZED" in tx["error"]["details"][0]["message"], "交易费设置为0，错误信息不正确"
        poolInfo2 = self.getPoolInfo(poolName, admin)
        assert poolInfo["pools"]["swapFee"] == poolInfo2["pools"]["swapFee"]

    def checkSetPublicSwapValueIsTrue(self, poolName):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")
        if poolInfo['pools']["finalized"] == 1:
            mylogger.info("当前pool已经finalized, 不执行此用例")
            return
        tx = self.swapClient.setPublicSwap(admin, poolName, True)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        assert poolInfo2["pools"]["publicSwap"] == 1, "setPublicSwap后，pools表中状态为: {}".format(poolInfo2["pools"]["publicSwap"])

    def checkSetPublicSwapValueIsFalse(self, poolName):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")
        if poolInfo['pools']["finalized"] == 1:
            mylogger.info("当前pool已经finalized, 不执行此用例")
            return
        tx = self.swapClient.setPublicSwap(admin, poolName, False)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        assert poolInfo2["pools"]["publicSwap"] == 0, "setPublicSwap后，pools表中状态为: {}".format(poolInfo2["pools"]["publicSwap"])

    def checkSetPublicSwapMsgSenderIsNotController(self, poolName):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")
        assert user1 != poolInfo["pools"]["controller"]
        tx = self.swapClient.setPublicSwap(user1, poolName, False)
        assert tx["code"] == 500, "交易应该失败"
        assert "ERR_NOT_CONTROLLER" in tx["error"]["details"][0]["message"], "交易费设置为0，错误信息不正确"
        poolInfo2 = self.getPoolInfo(poolName, admin)
        assert poolInfo2["pools"]["publicSwap"] == poolInfo["pools"]["publicSwap"], "setPublicSwap后，pools表中状态为: {}".format(poolInfo2["pools"]["publicSwap"])

    def checkSetPublicSwapAfterFinalized(self, poolName, isPub):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")
        if poolInfo['pools']["finalized"] == 0:
            mylogger.info("当前pool未finalized, 不执行此用例")
            return
        tx = self.swapClient.setPublicSwap(admin, poolName, isPub)

        assert tx["code"] == 500, "交易应该失败"
        assert "ERR_IS_FINALIZED" in tx["error"]["details"][0]["message"], "交易费设置为0，错误信息不正确"
        poolInfo2 = self.getPoolInfo(poolName, admin)
        assert poolInfo2["pools"]["publicSwap"] == poolInfo["pools"]["publicSwap"], \
            "setPublicSwap后，pools表中状态为: {}".format(poolInfo2["pools"]["publicSwap"])

    def checkSetControllerWhenPoolIsNotFinalized(self, poolName, manager):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")
        mylogger.info("当前pool的controller为:{}".format(poolInfo["pools"]["controller"]))
        if poolInfo["pools"]["finalized"] == 1:
            return
        tx = self.swapClient.setControler(poolInfo["pools"]["controller"], poolName, manager)
        time.sleep(0.5)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        assert poolInfo2["pools"]["controller"] == manager, "controller不正确: {}".format(poolInfo2["pools"]["controller"])

    def checkSetControllerWhenPoolIsFinalized(self, poolName, manager):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")
        mylogger.info("当前pool的controller为:{}".format(poolInfo["pools"]["controller"]))
        if poolInfo["pools"]["finalized"] == 0:
            return
        tx = self.swapClient.setControler(poolInfo["pools"]["controller"], poolName, manager)
        time.sleep(0.5)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        assert poolInfo2["pools"]["controller"] == manager, "controller不正确: {}".format(poolInfo2["pools"]["controller"])

    def checkBindTokenWhenDenormLessThanMinWeight(self, poolName, token, tokenBalance, tokenDecimal):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")

        bindToken = to_wei_asset(tokenBalance, token, tokenDecimal)
        bindDenrom = to_wei(1, 0)
        userBalance = self.getAccountBalance(nonadmin, ["TBTC", "TUSDT"])
        mylogger.info(f"用户{nonadmin}的资产: {userBalance}")
        mylogger.info(f"将要bind的资产: {bindToken}")
        mylogger.info(f"将要bind的denorm: {bindDenrom}")

        tx = self.swapClient.bind(nonadmin, poolName, bindToken, bindDenrom)
        assert 'ERR_MIN_WEIGHT' in tx["error"]["details"][0]["message"]
        time.sleep(0.5)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        userBalance2 = self.getAccountBalance(nonadmin, ["TBTC", "TUSDT"])
        mylogger.info(f"bind后，pool info: {poolInfo2}")
        mylogger.info(f"bind后，用户{nonadmin}的资产: {userBalance2}")

        assert userBalance2 == userBalance, "用户资产不变"
        assert poolInfo['pools']['records'] == poolInfo2['pools']["records"]

    def checkBindTokenWhenDenormMoreThanMaxWeight(self, poolName, token, tokenBalance, tokenDecimal, denorm=to_wei(50, 9) + 1):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")

        bindToken = to_wei_asset(tokenBalance, token, tokenDecimal)
        # bindDenrom = to_wei(49, 9) + 1
        userBalance = self.getAccountBalance(nonadmin, ["TBTC", "TUSDT"])
        mylogger.info(f"用户{nonadmin}的资产: {userBalance}")
        mylogger.info(f"将要bind的资产: {bindToken}")
        mylogger.info(f"将要bind的denorm: {denorm}")

        tx = self.swapClient.bind(nonadmin, poolName, bindToken, denorm)
        assert 'ERR_MAX_WEIGHT' in tx["error"]["details"][0]["message"] or 'ERR_MAX_TOTAL_WEIGHT' in tx["error"]["details"][0]["message"]
        time.sleep(0.5)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        userBalance2 = self.getAccountBalance(nonadmin, ["TBTC", "TUSDT"])
        mylogger.info(f"bind后，pool info: {poolInfo2}")
        mylogger.info(f"bind后，用户{nonadmin}的资产: {userBalance2}")

        assert userBalance2 == userBalance, "用户资产不变"
        assert poolInfo['pools']['records'] == poolInfo2['pools']["records"]

    def checkBindTokenWhenBalanceLessThanMinBalance(self, poolName, token, tokenBalance, tokenDecimal):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")

        bindToken = to_wei_asset(tokenBalance, token, tokenDecimal)
        bindDenrom = to_wei(1, 9)
        userBalance = self.getAccountBalance(nonadmin, ["TBTC", "TUSDT"])
        min_balance = int(math.pow(10, 9) // math.pow(10, 4))
        logger.info("pool 可接受的最小资产为: {}".format(min_balance))
        mylogger.info(f"用户{nonadmin}的资产: {userBalance}")
        mylogger.info(f"将要bind的资产: {bindToken}, pool中存储为:{int(tokenBalance * math.pow(10, 9))}")
        mylogger.info(f"将要bind的denorm: {bindDenrom}")

        tx = self.swapClient.bind(nonadmin, poolName, bindToken, bindDenrom)
        assert 'ERR_MIN_BALANCE' in tx["error"]["details"][0]["message"]
        time.sleep(0.5)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        userBalance2 = self.getAccountBalance(nonadmin, ["TBTC", "TUSDT"])
        mylogger.info(f"bind后，pool info: {poolInfo2}")
        mylogger.info(f"bind后，用户{nonadmin}的资产: {userBalance2}")

        assert userBalance2 == userBalance, "用户资产不变"
        assert poolInfo['pools']['records'] == poolInfo2['pools']["records"]

    def checkBindToken(self, poolName, token, tokenBalance, tokenDecimal, tokenDenorm, contract='roxearntoken'):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")

        bindToken = to_wei_asset(tokenBalance, token, tokenDecimal, contract)
        userBalance = self.getAccountBalance(nonadmin, [token], contract)
        mylogger.info(f"用户{nonadmin}的资产: {userBalance}")
        mylogger.info(f"将要bind的资产: {bindToken}")
        mylogger.info(f"将要bind的denorm: {tokenDenorm}")

        exceptBalance = int(tokenBalance * int(math.pow(10, 9)))

        mylogger.info("exceptBalance: {}".format(exceptBalance))
        # mylogger.info("授权。。")
        # allowDosContract(nonadmin, acc2pub_keys[nonadmin])
        tx = self.swapClient.bind(nonadmin, poolName, bindToken, tokenDenorm)
        time.sleep(2)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        userBalance2 = self.getAccountBalance(nonadmin, [token], contract)

        fee = get_transfer_fee(int(tokenBalance * math.pow(10, tokenDecimal)), token, False, contract)
        mylogger.info("转账费用: {}, 实际为: {}".format(fee, fee / math.pow(10, tokenDecimal) ))

        mylogger.info(f"bind后，pool info: {poolInfo2}")
        mylogger.info(f"bind后，用户{nonadmin}的资产: {userBalance2}")

        assert len(poolInfo2["pools"]["records"]) == len(poolInfo["pools"]["records"]) + 1, "records中应增加相应记录"
        tokenInfo = [i for i in poolInfo2["pools"]["records"] if i["value"]["exsym"] == to_sym(token, tokenDecimal, contract)][0]
        assert tokenInfo["value"]["bound"] == 1, "records中该token应为bounded"
        assert tokenInfo["value"]["index"] == len(poolInfo2["pools"]["records"]) - 1, "records中该token index值不正确"
        assert tokenInfo["value"]["denorm"] == tokenDenorm, "records中该token denorm 值不正确"
        assert int(tokenInfo["value"]["balance"]) == exceptBalance, "records中该token balance 值不正确"
        assert tokenInfo["value"]["exsym"]["contract"] == bindToken["contract"], "records中该token exsym contract 值不正确"
        assert tokenInfo["key"] in poolInfo2["pools"]["tokens"]
        assert len(poolInfo2["pools"]["records"]) == len(poolInfo2["pools"]["tokens"])
        assert poolInfo2["pools"]["totalWeight"] - poolInfo["pools"]["totalWeight"] == tokenDenorm
        assert userBalance[token]["parseBalance"] - userBalance2[token]["parseBalance"] == int(tokenBalance * int(math.pow(10, tokenDecimal))) + fee

    def checkRebindToken(self, poolName, token, tokenBalance, tokenDecimal, tokenDenorm, contract='roxearntoken'):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")

        bindToken = to_wei_asset(tokenBalance, token, tokenDecimal, contract)
        userBalance = self.getAccountBalance(nonadmin, [token], contract)
        mylogger.info(f"用户{nonadmin}的资产: {userBalance}")
        mylogger.info(f"将要rebind的资产: {bindToken}")
        mylogger.info(f"将要rebind的denorm: {tokenDenorm}")

        exceptBalance = int(tokenBalance * int(math.pow(10, 9)))

        oldBalance = int(poolInfo["pools"]["records"][0]["value"]["balance"])

        if oldBalance > exceptBalance:
            outBalance = oldBalance - exceptBalance
            transfer_fee = get_transfer_fee(int(outBalance * math.pow(10, tokenDecimal - 9)), token, True, contract)
            actualAmountOut = outBalance - int(transfer_fee * math.pow(10, 9 - tokenDecimal))
        else:
            transfer_fee = 0
            actualAmountOut = oldBalance - exceptBalance
        mylogger.info("oldBalance: {}".format(oldBalance))
        mylogger.info("exceptBalance: {}".format(exceptBalance))
        mylogger.info("transfer_fee: {}".format(transfer_fee))
        mylogger.info("实际转出的out Balance: {}".format(actualAmountOut))

        # mylogger.info("授权。。")
        # allowDosContract(nonadmin, acc2pub_keys[nonadmin])
        tx = self.swapClient.rebind(nonadmin, poolName, bindToken, tokenDenorm)
        time.sleep(2)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        userBalance2 = self.getAccountBalance(nonadmin, [token], contract)
        mylogger.info(f"rebind后，pool info: {poolInfo2}")
        mylogger.info(f"rebind后，用户{nonadmin}的资产: {userBalance2}")

        # assert len(poolInfo2["pools"]["records"]) == len(poolInfo["pools"]["records"]) + 1, "records中应增加相应记录"
        tokenInfo = [i for i in poolInfo2["pools"]["records"] if i["value"]["exsym"] == to_sym(token, tokenDecimal, contract)][0]
        assert tokenInfo["value"]["bound"] == 1, "records中该token应为bounded"
        # assert tokenInfo["value"]["index"] == len(poolInfo2["pools"]["records"]) - 1, "records中该token index值不正确"
        assert tokenInfo["value"]["denorm"] == tokenDenorm, "records中该token denorm 值不正确"
        assert int(tokenInfo["value"]["balance"]) == exceptBalance, "records中该token balance 值不正确"
        assert tokenInfo["value"]["exsym"]["contract"] == bindToken["contract"], "records中该token exsym contract 值不正确"
        # assert tokenInfo["key"] in poolInfo2["pools"]["tokens"]
        assert len(poolInfo2["pools"]["records"]) == len(poolInfo2["pools"]["tokens"])
        assert poolInfo2["pools"]["totalWeight"] == tokenDenorm
        assert userBalance2[token]["parseBalance"] - userBalance[token]["parseBalance"] == int(actualAmountOut * math.pow(10, tokenDecimal-9))
        self.checkPoolBalance(poolName)

    def checkUnbindToken(self, poolName, token, tokenDecimal, contract='roxearntoken'):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")

        unbindToken = to_sym(token, tokenDecimal, contract)
        userBalance = self.getAccountBalance(nonadmin, [token], contract)
        mylogger.info(f"用户{nonadmin}的资产: {userBalance}")
        mylogger.info(f"将要unbind的token: {unbindToken}")

        oldBalance = int(poolInfo["pools"]["records"][0]["value"]["balance"])

        transfer_fee = get_transfer_fee(int(oldBalance * math.pow(10, tokenDecimal - 9)), token, True, contract)
        actualAmountOut = oldBalance - int(transfer_fee * math.pow(10, 9 - tokenDecimal))
        mylogger.info("oldBalance: {}".format(oldBalance))
        mylogger.info("transfer_fee: {}".format(transfer_fee))
        mylogger.info("实际转出的out Balance: {}".format(actualAmountOut))

        # mylogger.info("授权。。")
        # allowDosContract(nonadmin, acc2pub_keys[nonadmin])
        tx = self.swapClient.unbind(nonadmin, poolName, unbindToken)
        time.sleep(2)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        userBalance2 = self.getAccountBalance(nonadmin, [token], contract)

        mylogger.info(f"unbind后，pool info: {poolInfo2}")
        mylogger.info(f"unbind后，用户{nonadmin}的资产: {userBalance2}")

        # assert len(poolInfo2["pools"]["records"]) == len(poolInfo["pools"]["records"]) + 1, "records中应增加相应记录"
        # tokenInfo = [i for i in poolInfo2["pools"]["records"] if i["value"]["exsym"] == to_sym(token, tokenDecimal, contract)][0]
        # assert tokenInfo["value"]["bound"] == 1, "records中该token应为bounded"
        # assert tokenInfo["value"]["index"] == len(poolInfo2["pools"]["records"]) - 1, "records中该token index值不正确"
        # assert tokenInfo["value"]["denorm"] == tokenDenorm, "records中该token denorm 值不正确"
        # assert int(tokenInfo["value"]["balance"]) == exceptBalance, "records中该token balance 值不正确"
        # assert tokenInfo["value"]["exsym"]["contract"] == bindToken["contract"], "records中该token exsym contract 值不正确"
        # assert tokenInfo["key"] in poolInfo2["pools"]["tokens"]
        # assert len(poolInfo2["pools"]["records"]) == len(poolInfo2["pools"]["tokens"])
        # assert poolInfo2["pools"]["totalWeight"] - poolInfo["pools"]["totalWeight"] == tokenDenorm
        assert userBalance2[token]["parseBalance"] - userBalance[token]["parseBalance"] == int(actualAmountOut * math.pow(10, tokenDecimal-9))
        self.checkPoolBalance(poolName)

    def checkBindTokenWhenTokenAlreadyBinded(self, poolName, token, tokenBalance, tokenDecimal, tokenDenorm):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")

        tokenInfo = [i for i in poolInfo["pools"]["records"] if i["value"]["exsym"] == to_sym(token, tokenDecimal)]

        if len(tokenInfo) == 0:
            mylogger.info("pool 中此token还未bind, 不执行此用例")
            return

        bindToken = to_wei_asset(tokenBalance, token, tokenDecimal)
        userBalance = self.getAccountBalance(nonadmin, ["TBTC", "TUSDT"])
        mylogger.info(f"用户{nonadmin}的资产: {userBalance}")
        mylogger.info(f"将要bind的资产: {bindToken}")
        mylogger.info(f"将要bind的denorm: {tokenDenorm}")
        # mylogger.info("授权。。")
        # allowDosContract(nonadmin, acc2pub_keys[nonadmin])
        tx = self.swapClient.bind(nonadmin, poolName, bindToken, tokenDenorm)
        assert 'ERR_IS_BOUND' in tx["error"]["details"][0]["message"]
        time.sleep(0.5)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        userBalance2 = self.getAccountBalance(nonadmin, ["TBTC", "TUSDT"])
        mylogger.info(f"bind后，pool info: {poolInfo2}")
        mylogger.info(f"bind后，用户{nonadmin}的资产: {userBalance2}")

        assert userBalance2 == userBalance, "用户资产不变"
        assert poolInfo2["pools"]["records"] == poolInfo["pools"]["records"], "records中应保持不变"
        assert poolInfo2["pools"]["tokens"] == poolInfo["pools"]["tokens"], "records中应保持不变"

    def checkBindTokenWhenTokenDecimalMoreThanContract(self, poolName, token, tokenBalance, tokenDecimal, tokenDenorm):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")

        bindToken = to_wei_asset(tokenBalance, token, tokenDecimal)
        userBalance = self.getAccountBalance(nonadmin, ["TBTC", "TUSDT"])
        mylogger.info(f"用户{nonadmin}的资产: {userBalance}")
        mylogger.info(f"将要bind的资产: {bindToken}")
        mylogger.info(f"将要bind的denorm: {tokenDenorm}")
        # mylogger.info("授权。。")
        # allowDosContract(nonadmin, acc2pub_keys[nonadmin])
        tx = self.swapClient.bind(nonadmin, poolName, bindToken, tokenDenorm)
        assert 'unsupport the decimal' in tx["error"]["details"][0]["message"]
        time.sleep(0.5)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        userBalance2 = self.getAccountBalance(nonadmin, ["TBTC", "TUSDT"])
        mylogger.info(f"bind后，pool info: {poolInfo2}")
        mylogger.info(f"bind后，用户{nonadmin}的资产: {userBalance2}")

        assert userBalance2 == userBalance, "用户资产不变"
        assert poolInfo2["pools"]["records"] == poolInfo["pools"]["records"], "records中应保持不变"
        assert poolInfo2["pools"]["tokens"] == poolInfo["pools"]["tokens"], "records中应保持不变"

    def checkFinalized(self, poolName):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")

        userBalance = self.getAccountBalance(nonadmin, ["TBTC", "TUSDT"])
        mylogger.info(f"用户{nonadmin}的资产: {userBalance}")
        # mylogger.info("授权。。")
        # allowDosContract(nonadmin, acc2pub_keys[nonadmin])
        tx = self.swapClient.finalize(nonadmin, poolName)
        time.sleep(0.5)
        poolInfo2 = self.getPoolInfo(poolName, admin)

        assert poolInfo2["pools"]["records"] == poolInfo["pools"]["records"], "records中应保持不变"
        assert poolInfo2["pools"]["tokens"] == poolInfo["pools"]["tokens"], "records中应保持不变"
        assert poolInfo2["pools"]["finalized"] == 1

    def checkFinalizedWhenPoolAlreadyFinalized(self, poolName):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")
        if poolInfo["pools"]["finalized"] != 1:
            return

        userBalance = self.getAccountBalance(nonadmin, ["TBTC", "TUSDT"])
        mylogger.info(f"用户{nonadmin}的资产: {userBalance}")
        # mylogger.info("授权。。")
        # allowDosContract(nonadmin, acc2pub_keys[nonadmin])
        tx = self.swapClient.finalize(nonadmin, poolName)
        assert 'ERR_IS_FINALIZED' in tx["error"]["details"][0]["message"]
        time.sleep(0.5)
        poolInfo2 = self.getPoolInfo(poolName, admin)

        assert poolInfo2["pools"]["records"] == poolInfo["pools"]["records"], "records中应保持不变"
        assert poolInfo2["pools"]["tokens"] == poolInfo["pools"]["tokens"], "records中应保持不变"
        assert poolInfo2["pools"]["finalized"] == 1

    def checkFinalizedWhenbindTokensOnlyHaveOne(self, poolName):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")

        userBalance = self.getAccountBalance(nonadmin, ["TBTC", "TUSDT"])
        mylogger.info(f"用户{nonadmin}的资产: {userBalance}")
        # mylogger.info("授权。。")
        # allowDosContract(nonadmin, acc2pub_keys[nonadmin])
        tx = self.swapClient.finalize(nonadmin, poolName)
        assert 'ERR_MIN_TOKENS' in tx["error"]["details"][0]["message"]
        time.sleep(0.5)
        poolInfo2 = self.getPoolInfo(poolName, admin)

        assert poolInfo2["pools"]["records"] == poolInfo["pools"]["records"], "records中应保持不变"
        assert poolInfo2["pools"]["tokens"] == poolInfo["pools"]["tokens"], "records中应保持不变"
        assert poolInfo2["pools"]["finalized"] == 0

    def checkPoolBalance(self, poolName):
        poolInfo = self.getPoolInfo(poolName, admin)
        tokenContracts = [i["value"]["exsym"]["contract"] for i in poolInfo["pools"]["records"]]
        tokenContracts = list(set(tokenContracts))
        mylogger.info("pool {}的信息: {}".format(poolName, poolInfo["pools"]["records"]))
        # mylogger.info("pool 中 token 合约: {}".format(tokenContracts))
        poolBalance = self.c.getTableRows(poolName, tokenContracts[0], "accounts")
        # print(poolName, tokenContracts)
        parsePoolBalance = parseBalanceInfo(poolBalance)

        mylogger.info("pool实际持有的token资产: {}".format(parsePoolBalance))

        for record in poolInfo["pools"]["records"]:
            curSymbol = record["value"]["exsym"]["symbol"]
            sym = curSymbol.split(',')[-1]
            curDecimal = int(curSymbol.split(',')[0])
            # print(math.pow(10, curDecimal - 9))
            curBalance = int(int(record["value"]["balance"]) * math.pow(10, curDecimal - 9))
            # poolAssets[sym] = {'parseBalance': curBalance, "decimal": curDecimal}
            mylogger.info(f"池子中记录的{sym} 资产: {curBalance}")
            assert curBalance == parsePoolBalance[sym]["parseBalance"], "{} 和 {}不一致".format(curBalance, parsePoolBalance[sym]["parseBalance"])
            assert curDecimal == len(parsePoolBalance[sym]["balance"].split(" ")[0].split(".")[-1])

    def checkJoinPoolWhenJoinAmountIs0(self, poolName, user=nonadmin):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")
        userBalance = self.getAccountBalance(nonadmin, ["TBTC", "TUSDT"])
        mylogger.info(f"用户{nonadmin}的资产: {userBalance}")
        totalSupply = self.getPoolSupply(poolName, admin)
        mylogger.info(totalSupply)
        # mylogger.info("授权。。")
        # allowDosContract(user, acc2pub_keys[user])
        tx = self.swapClient.joinpool(user, poolName, 0, [2**10-1, 2**10-1])
        assert 'poolAmountOutmust be greater than 1' in tx["error"]["details"][0]["message"]
        time.sleep(1)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        assert poolInfo2 == poolInfo
        self.checkPoolBalance(poolName)

    def checkJoinPoolWhenJoinAmountMoreThanUserAmount(self, poolName, persent=1, user=nonadmin):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")
        balances = []
        weights = []
        syms = []
        tokenNames = []
        for token in poolInfo["pools"]["tokens"]:
            t_record = [i["value"] for i in poolInfo["pools"]["records"] if i["key"] == token][0]
            balances.append(int(t_record["balance"]))
            weights.append(t_record["denorm"])
            syms.append(t_record["exsym"])
            tokenNames.append(t_record["exsym"]['symbol'].split(",")[-1])
        userBalance = self.getAccountBalance(user, tokenNames)
        mylogger.info(f"用户{user}持有的资产: {userBalance}")
        userSupply = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"用户{user}持有的lp: {userSupply}")
        totalSupply = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("池子中总的lp为: {}".format(totalSupply))
        poolMinOut = int(totalSupply * persent)
        maxAmountsIn = []
        changedBalances = []
        ratio = bdiv(poolMinOut, totalSupply)
        for index, tokenBalnce in enumerate(balances):
            calAmountIn = bmul(ratio, tokenBalnce)
            tokenDecimal = int(syms[index]["symbol"].split(",")[0])
            parseAmountIn = convert_one_decimals(calAmountIn, tokenDecimal, -1)
            parseAmountIn = int(parseAmountIn) / int(math.pow(10, tokenDecimal))
            mylogger.info("计算出来需要增加{}的AmountIn: {}".format(tokenNames[index], calAmountIn))
            mylogger.info("转换为{}的数量: {}".format(tokenNames[index], parseAmountIn))
            maxAmountsIn.append(calAmountIn)
            parseUserChanged = int(parseAmountIn * math.pow(10, tokenDecimal))
            mylogger.info("用户将要改变{}的数量: {}".format(tokenNames[index], parseUserChanged))
            changedBalances.append(parseUserChanged)

        mylogger.info("想要添加{}的lp，需要加入的资产: {}".format(poolMinOut, maxAmountsIn))
        mylogger.info("授权。。")
        allowDosContract(user, acc2pub_keys[user])
        tx = self.swapClient.joinpool(user, poolName, poolMinOut, maxAmountsIn)
        time.sleep(3)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        mylogger.info(f"joinPool后, 池子{poolName}的信息: {poolInfo2}")
        userBalance2 = self.getAccountBalance(user, tokenNames)
        mylogger.info(f"joinPool后, 用户{user}持有的资产: {userBalance2}")
        userSupply2 = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"joinPool后, 用户{user}持有的lp: {userSupply2}")
        totalSupply2 = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("joinPool后, 池子中总的lp为: {}".format(totalSupply2))

        # 检查池子中的lp计算正确
        assert totalSupply2 - totalSupply == poolMinOut, "池子增加的lp不正确"
        # 检查用户持有的lp
        assert userSupply2 - userSupply == poolMinOut, "用户增加的lp不正确"

        # 检查池子资产中记录的balance和weight正确
        for index, tokenBalnce in enumerate(balances):
            # 检查池子资产record是否正确
            afterBalance = int(poolInfo2["pools"]['records'][index]["value"]["balance"])
            assert afterBalance - tokenBalnce == maxAmountsIn[index]
            # 检查池子的denorm是否正确
            assert poolInfo2["pools"]['records'][index]["value"]["denorm"] == weights[index]
            # 检查用户持有的资产变化
            assert userBalance2[tokenNames[index]]["parseBalance"] - userBalance[tokenNames[index]]["parseBalance"] == changedBalances[index]

        # 检查池子实际持有的token资产和record的资产是否一致
        self.checkPoolBalance(poolName)

    def checkJoinPoolWhenJoinAmountsLessThanRequireAmount(self, poolName, persent=1, user=nonadmin):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")
        balances = []
        weights = []
        syms = []
        tokenNames = []
        for token in poolInfo["pools"]["tokens"]:
            t_record = [i["value"] for i in poolInfo["pools"]["records"] if i["key"] == token][0]
            balances.append(int(t_record["balance"]))
            weights.append(t_record["denorm"])
            syms.append(t_record["exsym"])
            tokenNames.append(t_record["exsym"]['symbol'].split(",")[-1])
        userBalance = self.getAccountBalance(user, tokenNames)
        mylogger.info(f"用户{user}持有的资产: {userBalance}")
        userSupply = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"用户{user}持有的lp: {userSupply}")
        totalSupply = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("池子中总的lp为: {}".format(totalSupply))
        poolMinOut = int(totalSupply * persent)
        maxAmountsIn = []
        changedBalances = []
        ratio = bdiv(poolMinOut, totalSupply)
        for index, tokenBalnce in enumerate(balances):
            calAmountIn = bmul(ratio, tokenBalnce)
            tokenDecimal = int(syms[index]["symbol"].split(",")[0])
            parseAmountIn = convert_one_decimals(calAmountIn, tokenDecimal, -1)
            parseAmountIn = int(parseAmountIn) / int(math.pow(10, tokenDecimal))
            mylogger.info("计算出来需要增加{}的AmountIn: {}".format(tokenNames[index], calAmountIn))
            mylogger.info("转换为{}的数量: {}".format(tokenNames[index], parseAmountIn))
            maxAmountsIn.append(calAmountIn - 1)
            parseUserChanged = int(parseAmountIn * math.pow(10, tokenDecimal))
            mylogger.info("用户将要改变{}的数量: {}".format(tokenNames[index], parseUserChanged))
            changedBalances.append(parseUserChanged)

        mylogger.info("想要添加{}的lp，需要加入的资产: {}".format(poolMinOut, maxAmountsIn))
        mylogger.info("授权。。")
        allowDosContract(user, acc2pub_keys[user])
        tx = self.swapClient.joinpool(user, poolName, poolMinOut, maxAmountsIn)
        assert "ERR_LIMIT_IN" in tx["error"]["details"][0]["message"]
        time.sleep(3)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        mylogger.info(f"joinPool后, 池子{poolName}的信息: {poolInfo2}")
        userBalance2 = self.getAccountBalance(user, tokenNames)
        mylogger.info(f"joinPool后, 用户{user}持有的资产: {userBalance2}")
        userSupply2 = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"joinPool后, 用户{user}持有的lp: {userSupply2}")
        totalSupply2 = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("joinPool后, 池子中总的lp为: {}".format(totalSupply2))

        # 检查池子中的lp计算正确
        assert totalSupply2 - totalSupply == 0, "池子增加的lp不正确"
        # 检查用户持有的lp
        assert userSupply2 - userSupply == 0, "用户增加的lp不正确"

        # 检查池子资产中记录的balance和weight正确
        for index, tokenBalnce in enumerate(balances):
            # 检查池子资产record是否正确
            afterBalance = int(poolInfo2["pools"]['records'][index]["value"]["balance"])
            assert afterBalance - tokenBalnce == 0
            # 检查池子的denorm是否正确
            assert poolInfo2["pools"]['records'][index]["value"]["denorm"] == weights[index]
            # 检查用户持有的资产变化
            assert userBalance2[tokenNames[index]]["parseBalance"] - userBalance[tokenNames[index]]["parseBalance"] == 0

        # 检查池子实际持有的token资产和record的资产是否一致
        self.checkPoolBalance(poolName)

    def checkJoinPoolWhenJoinAmountsMoreThanRequireAmount(self, poolName, persent=1, user=nonadmin):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")
        balances = []
        weights = []
        syms = []
        tokenNames = []
        for token in poolInfo["pools"]["tokens"]:
            t_record = [i["value"] for i in poolInfo["pools"]["records"] if i["key"] == token][0]
            balances.append(int(t_record["balance"]))
            weights.append(t_record["denorm"])
            syms.append(t_record["exsym"])
            tokenNames.append(t_record["exsym"]['symbol'].split(",")[-1])
        userBalance = self.getAccountBalance(user, tokenNames)
        mylogger.info(f"用户{user}持有的资产: {userBalance}")
        userSupply = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"用户{user}持有的lp: {userSupply}")
        totalSupply = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("池子中总的lp为: {}".format(totalSupply))
        poolMinOut = int(totalSupply * persent)
        maxAmountsIn = []
        changedBalances = []
        ratio = bdiv(poolMinOut, totalSupply)
        addTokenBalances = [100, 10000]
        for index, tokenBalnce in enumerate(balances):
            calAmountIn = bmul(ratio, tokenBalnce)
            tokenDecimal = int(syms[index]["symbol"].split(",")[0])
            parseAmountIn = convert_one_decimals(calAmountIn, tokenDecimal, -1)
            parseAmountIn = int(parseAmountIn) / int(math.pow(10, tokenDecimal))
            mylogger.info("计算出来需要增加{}的AmountIn: {}".format(tokenNames[index], calAmountIn))
            mylogger.info("转换为{}的数量: {}".format(tokenNames[index], parseAmountIn))
            maxAmountsIn.append(calAmountIn + addTokenBalances[index])
            parseUserChanged = int(parseAmountIn * math.pow(10, tokenDecimal))
            mylogger.info("用户将要改变{}的数量: {}".format(tokenNames[index], parseUserChanged))
            changedBalances.append(parseUserChanged)

        mylogger.info("想要添加{}的lp，需要加入的资产: {}".format(poolMinOut, maxAmountsIn))
        mylogger.info("想要添加{}的lp，用户可以得到的资产: {}".format(poolMinOut, changedBalances))
        mylogger.info("授权。。")
        allowDosContract(user, acc2pub_keys[user])
        tx = self.swapClient.joinpool(user, poolName, poolMinOut, maxAmountsIn)
        time.sleep(3)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        mylogger.info(f"joinPool后, 池子{poolName}的信息: {poolInfo2}")
        userBalance2 = self.getAccountBalance(user, tokenNames)
        mylogger.info(f"joinPool后, 用户{user}持有的资产: {userBalance2}")
        userSupply2 = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"joinPool后, 用户{user}持有的lp: {userSupply2}")
        totalSupply2 = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("joinPool后, 池子中总的lp为: {}".format(totalSupply2))

        # 检查池子中的lp计算正确
        assert totalSupply2 - totalSupply == poolMinOut, "池子增加的lp不正确"
        # 检查用户持有的lp
        assert userSupply2 - userSupply == poolMinOut, "用户增加的lp不正确"

        # 检查池子资产中记录的balance和weight正确
        for index, tokenBalnce in enumerate(balances):
            # 检查池子资产record是否正确
            afterBalance = int(poolInfo2["pools"]['records'][index]["value"]["balance"])
            assert afterBalance - tokenBalnce == maxAmountsIn[index] - addTokenBalances[index]
            # 检查池子的denorm是否正确
            assert poolInfo2["pools"]['records'][index]["value"]["denorm"] == weights[index]
            # 检查用户持有的资产变化
            assert userBalance2[tokenNames[index]]["parseBalance"] - userBalance[tokenNames[index]]["parseBalance"] == changedBalances[index]

        # 检查池子实际持有的token资产和record的资产是否一致
        self.checkPoolBalance(poolName)

    def checkJoinPool(self, poolName, persent, user=nonadmin):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")
        balances = []
        weights = []
        syms = []
        tokenNames = []
        for token in poolInfo["pools"]["tokens"]:
            t_record = [i["value"] for i in poolInfo["pools"]["records"] if i["key"] == token][0]
            balances.append(int(t_record["balance"]))
            weights.append(t_record["denorm"])
            syms.append(t_record["exsym"])
            tokenNames.append(t_record["exsym"]['symbol'].split(",")[-1])
        contract = syms[0]["contract"]
        userBalance = self.getAccountBalance(user, tokenNames, contract)
        mylogger.info(f"用户{user}持有的资产: {userBalance}")
        userSupply = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"用户{user}持有的lp: {userSupply}")
        totalSupply = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("池子中总的lp为: {}".format(totalSupply))
        poolMinOut = int(totalSupply * persent)
        maxAmountsIn = []
        changedBalances = []
        ratio = bdiv(poolMinOut, totalSupply)
        for index, tokenBalnce in enumerate(balances):
            calAmountIn = bmul(ratio, tokenBalnce)
            tokenDecimal = int(syms[index]["symbol"].split(",")[0])
            # parseAmountIn = int(calAmountIn * math.pow(10, tokenDecimal-9))
            mylogger.info("计算出来需要增加{}的AmountIn: {}".format(tokenNames[index], calAmountIn))
            # mylogger.info("转换为{}的数量: {}".format(tokenNames[index], parseAmountIn))
            maxAmountsIn.append(calAmountIn)
            parseUserChanged = int(calAmountIn * math.pow(10, tokenDecimal-9))
            mylogger.info("用户将要改变{}的数量: {}".format(tokenNames[index], parseUserChanged))
            changedBalances.append(parseUserChanged)

        mylogger.info("想要添加{}的lp，需要加入的资产: {}".format(poolMinOut, maxAmountsIn))
        mylogger.info("想要添加{}的lp，用户需要付出的资产: {}".format(poolMinOut, changedBalances))
        allowDosContract(user, acc2pub_keys[user])
        tx = self.swapClient.joinpool(user, poolName, poolMinOut, maxAmountsIn)
        time.sleep(3)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        mylogger.info(f"joinPool后, 池子{poolName}的信息: {poolInfo2}")
        userBalance2 = self.getAccountBalance(user, tokenNames, contract)
        mylogger.info(f"joinPool后, 用户{user}持有的资产: {userBalance2}")
        userSupply2 = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"joinPool后, 用户{user}持有的lp: {userSupply2}")
        totalSupply2 = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("joinPool后, 池子中总的lp为: {}".format(totalSupply2))

        # 检查池子中的lp计算正确
        assert totalSupply2 - totalSupply == poolMinOut, "池子增加的lp不正确"
        # 检查用户持有的lp
        assert userSupply2 - userSupply == poolMinOut, "用户增加的lp不正确"

        # 检查池子资产中记录的balance和weight正确
        for index, tokenBalnce in enumerate(balances):
            # 检查池子资产record是否正确
            afterBalance = int(poolInfo2["pools"]['records'][index]["value"]["balance"])
            assert afterBalance - tokenBalnce == maxAmountsIn[index]
            # 检查池子的denorm是否正确
            assert poolInfo2["pools"]['records'][index]["value"]["denorm"] == weights[index]
            # 检查用户持有的资产变化
            fee = get_transfer_fee(changedBalances[index], tokenNames[index], False, syms[index]["contract"])
            assert userBalance[tokenNames[index]]["parseBalance"] - userBalance2[tokenNames[index]]["parseBalance"] == changedBalances[index] + fee

        # 检查池子实际持有的token资产和record的资产是否一致
        self.checkPoolBalance(poolName)

    def checkJoinPoolWhenJoinLpMoreThanPoolMaxSupply(self, poolName, user=nonadmin):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")
        balances = []
        weights = []
        syms = []
        tokenNames = []
        for token in poolInfo["pools"]["tokens"]:
            t_record = [i["value"] for i in poolInfo["pools"]["records"] if i["key"] == token][0]
            balances.append(int(t_record["balance"]))
            weights.append(t_record["denorm"])
            syms.append(t_record["exsym"])
            tokenNames.append(t_record["exsym"]['symbol'].split(",")[-1])
        userBalance = self.getAccountBalance(user, tokenNames)
        mylogger.info(f"用户{user}持有的资产: {userBalance}")
        userSupply = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"用户{user}持有的lp: {userSupply}")
        poolSupplyInfo = self.getPoolSupply(poolName, admin)[0]
        maxSupply = poolSupplyInfo["parseMaxSupply"]
        totalSupply = poolSupplyInfo["parseSupply"]
        mylogger.info("池子中总的lp为: {}".format(totalSupply))
        mylogger.info("池子中支持的最大lp为: {}".format(maxSupply))
        poolMinOut = maxSupply - totalSupply + 1
        logger.info("添加 {} 的lp会超过池子剩余lp的上限值: {}".format(poolMinOut, maxSupply - totalSupply))
        maxAmountsIn = []
        changedBalances = []
        ratio = bdiv(poolMinOut, totalSupply)
        for index, tokenBalnce in enumerate(balances):
            calAmountIn = bmul(ratio, tokenBalnce)
            tokenDecimal = int(syms[index]["symbol"].split(",")[0])
            parseAmountIn = convert_one_decimals(calAmountIn, tokenDecimal, -1)
            parseAmountIn = int(parseAmountIn) / int(math.pow(10, tokenDecimal))
            mylogger.info("计算出来需要增加{}的AmountIn: {}".format(tokenNames[index], calAmountIn))
            mylogger.info("转换为{}的数量: {}".format(tokenNames[index], parseAmountIn))
            maxAmountsIn.append(calAmountIn)
            parseUserChanged = int(parseAmountIn * math.pow(10, tokenDecimal))
            mylogger.info("用户将要改变{}的数量: {}".format(tokenNames[index], parseUserChanged))
            changedBalances.append(parseUserChanged)

        mylogger.info("想要添加{}的lp，需要加入的资产: {}".format(poolMinOut, maxAmountsIn))
        mylogger.info("想要添加{}的lp，用户可以得到的资产: {}".format(poolMinOut, changedBalances))
        # mylogger.info("授权。。")
        # allowDosContract(user, acc2pub_keys[user])
        tx = self.swapClient.joinpool(user, poolName, poolMinOut, maxAmountsIn)
        assert "quantity exceeds available supply" in tx["error"]["details"][0]["message"]
        time.sleep(3)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        mylogger.info(f"joinPool后, 池子{poolName}的信息: {poolInfo2}")
        userBalance2 = self.getAccountBalance(user, tokenNames)
        mylogger.info(f"joinPool后, 用户{user}持有的资产: {userBalance2}")
        userSupply2 = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"joinPool后, 用户{user}持有的lp: {userSupply2}")
        totalSupply2 = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("joinPool后, 池子中总的lp为: {}".format(totalSupply2))

        # 检查池子中的lp计算正确
        assert totalSupply2 - totalSupply == 0, "池子增加的lp不正确"
        # 检查用户持有的lp
        assert userSupply2 - userSupply == 0, "用户增加的lp不正确"

        # 检查池子资产中记录的balance和weight正确
        for index, tokenBalnce in enumerate(balances):
            # 检查池子资产record是否正确
            afterBalance = int(poolInfo2["pools"]['records'][index]["value"]["balance"])
            assert afterBalance - tokenBalnce == 0
            # 检查池子的denorm是否正确
            assert poolInfo2["pools"]['records'][index]["value"]["denorm"] == weights[index]
            # 检查用户持有的资产变化
            assert userBalance2[tokenNames[index]]["parseBalance"] - userBalance[tokenNames[index]]["parseBalance"] == 0

        # 检查池子实际持有的token资产和record的资产是否一致
        self.checkPoolBalance(poolName)

    def checkExitPool(self, poolName, persent, user=nonadmin):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")
        balances = []
        weights = []
        syms = []
        tokenNames = []
        for token in poolInfo["pools"]["tokens"]:
            t_record = [i["value"] for i in poolInfo["pools"]["records"] if i["key"] == token][0]
            balances.append(int(t_record["balance"]))
            weights.append(t_record["denorm"])
            syms.append(t_record["exsym"])
            tokenNames.append(t_record["exsym"]['symbol'].split(",")[-1])
        contract = syms[0]["contract"]
        userBalance = self.getAccountBalance(user, tokenNames, contract)
        mylogger.info(f"用户{user}持有的资产: {userBalance}")
        userSupply = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"用户{user}持有的lp: {userSupply}")
        totalSupply = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("池子中总的lp为: {}".format(totalSupply))
        poolAmountIn = int(userSupply * persent)
        minAmountsOut = []
        changedBalances = []
        exitFee = bmul(poolAmountIn, 0)
        pAiAfterExitFee = bsub(poolAmountIn, exitFee)
        ratio = bdiv(pAiAfterExitFee, totalSupply)
        fees = []
        for index, tokenBalnce in enumerate(balances):
            calAmountIn = bmul(ratio, tokenBalnce)
            tokenDecimal = int(syms[index]["symbol"].split(",")[0])
            # parseAmountIn = convert_one_decimals(calAmountIn, tokenDecimal, -1)
            parseAmountIn = int(calAmountIn * math.pow(10, tokenDecimal-9))
            mylogger.info("计算出来需要增加{}的AmountIn: {}".format(tokenNames[index], calAmountIn))
            mylogger.info("转换为{}的数量: {}".format(tokenNames[index], parseAmountIn))
            minAmountsOut.append(calAmountIn)
            parseUserChanged = parseAmountIn
            mylogger.info("用户将要改变{}的数量: {}".format(tokenNames[index], parseUserChanged))
            changedBalances.append(parseUserChanged)
            fee = get_transfer_fee(parseUserChanged, tokenNames[index], True, syms[index]["contract"])
            fees.append(fee)

        mylogger.info("想要退出{}的lp，池子变化的资产: {}".format(poolAmountIn, minAmountsOut))
        mylogger.info("想要退出{}的lp，用户可以得到的资产: {}".format(poolAmountIn, changedBalances))
        mylogger.info("想要退出{}的lp，其中的转账费用为: {}".format(poolAmountIn, fees))
        mylogger.info("想要退出{}的lp，用户实际可以得到为: {}".format(poolAmountIn, [changedBalances[i] - fees[i] for i in range(len(changedBalances))]))
        mylogger.info("授权。。")
        allowDosContract(user, acc2pub_keys[user])
        tx = self.swapClient.exitpool(user, poolName, poolAmountIn, [0,0])
        time.sleep(3)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        mylogger.info(f"退出池子后, 池子{poolName}的信息: {poolInfo2}")
        userBalance2 = self.getAccountBalance(user, tokenNames, contract)
        mylogger.info(f"退出池子后, 用户{user}持有的资产: {userBalance2}")
        userSupply2 = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"退出池子后, 用户{user}持有的lp: {userSupply2}")
        totalSupply2 = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("joinPool后, 池子中总的lp为: {}".format(totalSupply2))

        # 检查池子中的lp计算正确
        # assert totalSupply2 + poolAmountIn == totalSupply, "池子减少的lp不正确"
        # 检查用户持有的lp
        # assert userSupply2 + poolAmountIn == userSupply, "用户减少的lp不正确"

        # 检查池子资产中记录的balance和weight正确
        for index, tokenBalnce in enumerate(balances):
            # 检查池子资产record是否正确
            afterBalance = int(poolInfo2["pools"]['records'][index]["value"]["balance"])
            pAt = changedBalances[index] * int(math.pow(10, 9 - int(syms[index]["symbol"].split(",")[0])))
            assert afterBalance + pAt == tokenBalnce, "{} + {} == {}不成立".format(afterBalance, tokenBalnce, pAt)
            # 检查池子的denorm是否正确
            assert poolInfo2["pools"]['records'][index]["value"]["denorm"] == weights[index]
            # 检查用户持有的资产变化
            assert userBalance2[tokenNames[index]]["parseBalance"] - userBalance[tokenNames[index]]["parseBalance"] == changedBalances[index] - fees[index]

        # 检查池子实际持有的token资产和record的资产是否一致
        self.checkPoolBalance(poolName)

    def checkExitPoolWhenExitAmountsLessThanRequireAmount(self, poolName, persent, user=nonadmin):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")
        balances = []
        weights = []
        syms = []
        tokenNames = []
        for token in poolInfo["pools"]["tokens"]:
            t_record = [i["value"] for i in poolInfo["pools"]["records"] if i["key"] == token][0]
            balances.append(int(t_record["balance"]))
            weights.append(t_record["denorm"])
            syms.append(t_record["exsym"])
            tokenNames.append(t_record["exsym"]['symbol'].split(",")[-1])
        userBalance = self.getAccountBalance(user, tokenNames)
        mylogger.info(f"用户{user}持有的资产: {userBalance}")
        userSupply = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"用户{user}持有的lp: {userSupply}")
        totalSupply = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("池子中总的lp为: {}".format(totalSupply))
        poolAmountIn = int(userSupply * persent)
        minAmountsOut = []
        changedBalances = []
        exitFee = bmul(poolAmountIn, 0)
        pAiAfterExitFee = bsub(poolAmountIn, exitFee)
        ratio = bdiv(pAiAfterExitFee, totalSupply)
        for index, tokenBalnce in enumerate(balances):
            calAmountIn = bmul(ratio, tokenBalnce)
            tokenDecimal = int(syms[index]["symbol"].split(",")[0])
            parseAmountIn = convert_one_decimals(calAmountIn, tokenDecimal, -1)
            parseAmountIn = int(parseAmountIn) / int(math.pow(10, tokenDecimal))
            mylogger.info("计算出来需要增加{}的AmountIn: {}".format(tokenNames[index], calAmountIn))
            mylogger.info("转换为{}的数量: {}".format(tokenNames[index], parseAmountIn))
            minAmountsOut.append(calAmountIn + 1)
            parseUserChanged = int(parseAmountIn * math.pow(10, tokenDecimal))
            mylogger.info("用户将要改变{}的数量: {}".format(tokenNames[index], parseUserChanged))
            changedBalances.append(parseUserChanged)

        mylogger.info("想要退出{}的lp，池子变化的资产: {}".format(poolAmountIn, minAmountsOut))
        mylogger.info("想要退出{}的lp，用户可以得到的资产: {}".format(poolAmountIn, changedBalances))
        mylogger.info("授权。。")
        allowDosContract(user, acc2pub_keys[user])
        allowDosContract(poolName, acc2pub_keys[poolName])
        tx = self.swapClient.exitpool(user, poolName, poolAmountIn, minAmountsOut)
        assert "ERR_LIMIT_OUT" in tx["error"]["details"][0]["message"]
        time.sleep(3)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        mylogger.info(f"joinPool后, 池子{poolName}的信息: {poolInfo2}")
        userBalance2 = self.getAccountBalance(user, tokenNames)
        mylogger.info(f"joinPool后, 用户{user}持有的资产: {userBalance2}")
        userSupply2 = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"joinPool后, 用户{user}持有的lp: {userSupply2}")
        totalSupply2 = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("joinPool后, 池子中总的lp为: {}".format(totalSupply2))

        # 检查池子中的lp计算正确
        assert totalSupply2 - poolAmountIn == 0, "池子增加的lp不正确"
        # 检查用户持有的lp
        assert userSupply2 - poolAmountIn == 0, "用户增加的lp不正确"

        # 检查池子资产中记录的balance和weight正确
        for index, tokenBalnce in enumerate(balances):
            # 检查池子资产record是否正确
            afterBalance = int(poolInfo2["pools"]['records'][index]["value"]["balance"])
            assert afterBalance + tokenBalnce == 0
            # 检查池子的denorm是否正确
            assert poolInfo2["pools"]['records'][index]["value"]["denorm"] == weights[index]
            # 检查用户持有的资产变化
            assert userBalance2[tokenNames[index]]["parseBalance"] == userBalance[tokenNames[index]]["parseBalance"]

        # 检查池子实际持有的token资产和record的资产是否一致
        self.checkPoolBalance(poolName)

    def checkExitPoolWhenExitAmountMoreThanUserAmount(self, poolName, user=nonadmin):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")
        balances = []
        weights = []
        syms = []
        tokenNames = []
        for token in poolInfo["pools"]["tokens"]:
            t_record = [i["value"] for i in poolInfo["pools"]["records"] if i["key"] == token][0]
            balances.append(int(t_record["balance"]))
            weights.append(t_record["denorm"])
            syms.append(t_record["exsym"])
            tokenNames.append(t_record["exsym"]['symbol'].split(",")[-1])
        userBalance = self.getAccountBalance(user, tokenNames)
        mylogger.info(f"用户{user}持有的资产: {userBalance}")
        userSupply = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"用户{user}持有的lp: {userSupply}")
        totalSupply = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("池子中总的lp为: {}".format(totalSupply))
        poolAmountIn = userSupply + 1
        minAmountsOut = []
        changedBalances = []
        exitFee = bmul(poolAmountIn, 0)
        pAiAfterExitFee = bsub(poolAmountIn, exitFee)
        ratio = bdiv(pAiAfterExitFee, totalSupply)
        for index, tokenBalnce in enumerate(balances):
            calAmountIn = bmul(ratio, tokenBalnce)
            tokenDecimal = int(syms[index]["symbol"].split(",")[0])
            parseAmountIn = convert_one_decimals(calAmountIn, tokenDecimal, -1)
            parseAmountIn = int(parseAmountIn) / int(math.pow(10, tokenDecimal))
            mylogger.info("计算出来需要增加{}的AmountIn: {}".format(tokenNames[index], calAmountIn))
            mylogger.info("转换为{}的数量: {}".format(tokenNames[index], parseAmountIn))
            minAmountsOut.append(calAmountIn + 1)
            parseUserChanged = int(parseAmountIn * math.pow(10, tokenDecimal))
            mylogger.info("用户将要改变{}的数量: {}".format(tokenNames[index], parseUserChanged))
            changedBalances.append(parseUserChanged)

        mylogger.info("想要退出{}的lp，池子变化的资产: {}".format(poolAmountIn, minAmountsOut))
        mylogger.info("想要退出{}的lp，用户可以得到的资产: {}".format(poolAmountIn, changedBalances))
        mylogger.info("授权。。")
        allowDosContract(user, acc2pub_keys[user])
        # allowDosContract(poolName, acc2pub_keys[poolName])
        tx = self.swapClient.exitpool(user, poolName, poolAmountIn, minAmountsOut)
        assert "overdrawn balance" in tx["error"]["details"][0]["message"]
        time.sleep(3)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        mylogger.info(f"joinPool后, 池子{poolName}的信息: {poolInfo2}")
        userBalance2 = self.getAccountBalance(user, tokenNames)
        mylogger.info(f"joinPool后, 用户{user}持有的资产: {userBalance2}")
        userSupply2 = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"joinPool后, 用户{user}持有的lp: {userSupply2}")
        totalSupply2 = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("joinPool后, 池子中总的lp为: {}".format(totalSupply2))

        # 检查池子中的lp计算正确
        assert totalSupply2 - 0 == totalSupply, "池子增加的lp不正确"
        # 检查用户持有的lp
        assert userSupply2 - 0 == userSupply, "用户增加的lp不正确"

        # 检查池子资产中记录的balance和weight正确
        for index, tokenBalnce in enumerate(balances):
            # 检查池子资产record是否正确
            afterBalance = int(poolInfo2["pools"]['records'][index]["value"]["balance"])
            assert afterBalance + 0 == tokenBalnce
            # 检查池子的denorm是否正确
            assert poolInfo2["pools"]['records'][index]["value"]["denorm"] == weights[index]
            # 检查用户持有的资产变化
            assert userBalance2[tokenNames[index]]["parseBalance"] == userBalance[tokenNames[index]]["parseBalance"]

        # 检查池子实际持有的token资产和record的资产是否一致
        self.checkPoolBalance(poolName)

    def checkExitPoolWhenExitLpIs0(self, poolName, user=nonadmin):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")
        balances = []
        weights = []
        syms = []
        tokenNames = []
        for token in poolInfo["pools"]["tokens"]:
            t_record = [i["value"] for i in poolInfo["pools"]["records"] if i["key"] == token][0]
            balances.append(int(t_record["balance"]))
            weights.append(t_record["denorm"])
            syms.append(t_record["exsym"])
            tokenNames.append(t_record["exsym"]['symbol'].split(",")[-1])
        userBalance = self.getAccountBalance(user, tokenNames)
        mylogger.info(f"用户{user}持有的资产: {userBalance}")
        userSupply = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"用户{user}持有的lp: {userSupply}")
        totalSupply = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("池子中总的lp为: {}".format(totalSupply))
        poolAmountIn = 0
        minAmountsOut = []
        changedBalances = []
        exitFee = bmul(poolAmountIn, 0)
        pAiAfterExitFee = bsub(poolAmountIn, exitFee)
        ratio = bdiv(pAiAfterExitFee, totalSupply)
        for index, tokenBalnce in enumerate(balances):
            calAmountIn = bmul(ratio, tokenBalnce)
            tokenDecimal = int(syms[index]["symbol"].split(",")[0])
            parseAmountIn = convert_one_decimals(calAmountIn, tokenDecimal, -1)
            parseAmountIn = int(parseAmountIn) / int(math.pow(10, tokenDecimal))
            mylogger.info("计算出来需要增加{}的AmountIn: {}".format(tokenNames[index], calAmountIn))
            mylogger.info("转换为{}的数量: {}".format(tokenNames[index], parseAmountIn))
            minAmountsOut.append(calAmountIn + 1)
            parseUserChanged = int(parseAmountIn * math.pow(10, tokenDecimal))
            mylogger.info("用户将要改变{}的数量: {}".format(tokenNames[index], parseUserChanged))
            changedBalances.append(parseUserChanged)

        mylogger.info("想要退出{}的lp，池子变化的资产: {}".format(poolAmountIn, minAmountsOut))
        mylogger.info("想要退出{}的lp，用户可以得到的资产: {}".format(poolAmountIn, changedBalances))
        mylogger.info("授权。。")
        allowDosContract(user, acc2pub_keys[user])
        # allowDosContract(poolName, )
        tx = self.swapClient.exitpool(user, poolName, poolAmountIn, minAmountsOut)
        assert "poolAmountOut must be greater than 1" in tx["error"]["details"][0]["message"]
        time.sleep(3)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        mylogger.info(f"退出池子后, 池子{poolName}的信息: {poolInfo2}")
        userBalance2 = self.getAccountBalance(user, tokenNames)
        mylogger.info(f"退出池子后, 用户{user}持有的资产: {userBalance2}")
        userSupply2 = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"退出池子后, 用户{user}持有的lp: {userSupply2}")
        totalSupply2 = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("退出池子后, 池子中总的lp为: {}".format(totalSupply2))

        # 检查池子中的lp计算正确
        assert totalSupply2 - totalSupply == 0, "池子增加的lp不正确"
        # 检查用户持有的lp
        assert userSupply2 - userSupply == 0, "用户增加的lp不正确"

        # 检查池子资产中记录的balance和weight正确
        for index, tokenBalnce in enumerate(balances):
            # 检查池子资产record是否正确
            afterBalance = int(poolInfo2["pools"]['records'][index]["value"]["balance"])
            assert afterBalance == tokenBalnce
            # 检查池子的denorm是否正确
            assert poolInfo2["pools"]['records'][index]["value"]["denorm"] == weights[index]
            # 检查用户持有的资产变化
            assert userBalance2[tokenNames[index]]["parseBalance"] == userBalance[tokenNames[index]]["parseBalance"]

        # 检查池子实际持有的token资产和record的资产是否一致
        self.checkPoolBalance(poolName)

    def checkExitPoolWhenUserLpIs0(self, poolName, user=nonadmin):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")
        balances = []
        weights = []
        syms = []
        tokenNames = []
        for token in poolInfo["pools"]["tokens"]:
            t_record = [i["value"] for i in poolInfo["pools"]["records"] if i["key"] == token][0]
            balances.append(int(t_record["balance"]))
            weights.append(t_record["denorm"])
            syms.append(t_record["exsym"])
            tokenNames.append(t_record["exsym"]['symbol'].split(",")[-1])
        userBalance = self.getAccountBalance(user, tokenNames)
        mylogger.info(f"用户{user}持有的资产: {userBalance}")
        userSupply = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"用户{user}持有的lp: {userSupply}")
        if userSupply > 0:
            return
        totalSupply = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("池子中总的lp为: {}".format(totalSupply))
        poolAmountIn = int(totalSupply * 0.1)
        minAmountsOut = []
        changedBalances = []
        exitFee = bmul(poolAmountIn, 0)
        pAiAfterExitFee = bsub(poolAmountIn, exitFee)
        ratio = bdiv(pAiAfterExitFee, totalSupply)
        for index, tokenBalnce in enumerate(balances):
            calAmountIn = bmul(ratio, tokenBalnce)
            tokenDecimal = int(syms[index]["symbol"].split(",")[0])
            parseAmountIn = convert_one_decimals(calAmountIn, tokenDecimal, -1)
            parseAmountIn = int(parseAmountIn) / int(math.pow(10, tokenDecimal))
            mylogger.info("计算出来需要增加{}的AmountIn: {}".format(tokenNames[index], calAmountIn))
            mylogger.info("转换为{}的数量: {}".format(tokenNames[index], parseAmountIn))
            minAmountsOut.append(calAmountIn + 1)
            parseUserChanged = int(parseAmountIn * math.pow(10, tokenDecimal))
            mylogger.info("用户将要改变{}的数量: {}".format(tokenNames[index], parseUserChanged))
            changedBalances.append(parseUserChanged)

        mylogger.info("想要退出{}的lp，池子变化的资产: {}".format(poolAmountIn, minAmountsOut))
        mylogger.info("想要退出{}的lp，用户可以得到的资产: {}".format(poolAmountIn, changedBalances))
        mylogger.info("授权。。")
        allowDosContract(user, acc2pub_keys[user])
        # allowDosContract(poolName, )
        tx = self.swapClient.exitpool(user, poolName, poolAmountIn, minAmountsOut)
        assert "ERR_MATH_APPROX" in tx["error"]["details"][0]["message"]
        time.sleep(3)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        mylogger.info(f"退出池子后, 池子{poolName}的信息: {poolInfo2}")
        userBalance2 = self.getAccountBalance(user, tokenNames)
        mylogger.info(f"退出池子后, 用户{user}持有的资产: {userBalance2}")
        userSupply2 = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"退出池子后, 用户{user}持有的lp: {userSupply2}")
        totalSupply2 = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("退出池子后, 池子中总的lp为: {}".format(totalSupply2))

        # 检查池子中的lp计算正确
        assert totalSupply2 - totalSupply == 0, "池子增加的lp不正确"
        # 检查用户持有的lp
        assert userSupply2 - userSupply == 0, "用户增加的lp不正确"

        # 检查池子资产中记录的balance和weight正确
        for index, tokenBalnce in enumerate(balances):
            # 检查池子资产record是否正确
            afterBalance = int(poolInfo2["pools"]['records'][index]["value"]["balance"])
            assert afterBalance == tokenBalnce
            # 检查池子的denorm是否正确
            assert poolInfo2["pools"]['records'][index]["value"]["denorm"] == weights[index]
            # 检查用户持有的资产变化
            assert userBalance2[tokenNames[index]]["parseBalance"] == userBalance[tokenNames[index]]["parseBalance"]

        # 检查池子实际持有的token资产和record的资产是否一致
        self.checkPoolBalance(poolName)

    def checkSwapAmountIn(self, poolName, tokenIn, tokenInAmount, tokenOut, user=nonadmin, contract="roxearntoken"):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")
        balances = []
        weights = []
        tokenDecimals = []
        syms = []
        tokenNames = []
        for token in poolInfo["pools"]["tokens"]:
            t_record = [i["value"] for i in poolInfo["pools"]["records"] if i["key"] == token][0]
            balances.append(int(t_record["balance"]))
            weights.append(t_record["denorm"])
            syms.append(t_record["exsym"])
            tokenNames.append(t_record["exsym"]['symbol'].split(",")[-1])
            tokenDecimals.append(int(t_record["exsym"]['symbol'].split(",")[0]))
        swapFee = poolInfo["pools"]['swapFee']
        mylogger.info("池子的交易费用为:{} == {}".format(swapFee, swapFee/math.pow(10, 9)))
        userBalance = self.getAccountBalance(user, tokenNames, contract)
        mylogger.info(f"用户{user}持有的资产: {userBalance}")
        userSupply = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"用户{user}持有的lp: {userSupply}")
        totalSupply = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("池子中总的lp为: {}".format(totalSupply))
        mylogger.info("池子中record资产: {}".format(balances))

        # poolBalance = self.getAccountBalance(poolName, tokenNames)
        # mylogger.info("池子实际持有资产: {}".format(poolBalance))

        tokenInIndex = tokenNames.index(tokenIn)
        tokenOutIndex = tokenNames.index(tokenOut)
        spotPriceBefore = self.mathContract.functions.calcSpotPrice(
            balances[tokenInIndex], weights[tokenInIndex], balances[tokenOutIndex], weights[tokenOutIndex], swapFee
        ).call()
        spotPriceBefore2 = self.mathContract2.functions.calcSpotPrice(
            balances[tokenInIndex], weights[tokenInIndex], balances[tokenOutIndex], weights[tokenOutIndex], swapFee
        ).call()
        tokenAmountIn = int(tokenInAmount * math.pow(10, 9))
        tokenAmountOut = self.mathContract.functions.calcOutGivenIn(
            balances[tokenInIndex], weights[tokenInIndex], balances[tokenOutIndex], weights[tokenOutIndex], tokenAmountIn, swapFee
        ).call()
        tokenAmountOut2 = self.mathContract2.functions.calcOutGivenIn(
            balances[tokenInIndex], weights[tokenInIndex], balances[tokenOutIndex], weights[tokenOutIndex],
            tokenAmountIn, swapFee
        ).call()
        print(balances[tokenInIndex], weights[tokenInIndex], balances[tokenOutIndex], weights[tokenOutIndex], tokenAmountIn, swapFee)
        inRecordBalance = balances[tokenInIndex] + tokenAmountIn
        outRecordBalance = balances[tokenOutIndex] - tokenAmountOut
        spotPriceAfter = self.mathContract.functions.calcSpotPrice(
            inRecordBalance, weights[tokenInIndex], outRecordBalance, weights[tokenOutIndex], swapFee
        ).call()
        spotPriceAfter2 = self.mathContract2.functions.calcSpotPrice(
            inRecordBalance, weights[tokenInIndex], outRecordBalance, weights[tokenOutIndex], swapFee
        ).call()

        actualTokenAmountIn = int(tokenAmountIn * math.pow(10, tokenDecimals[tokenInIndex] - 9))
        actualTokenAmountOut = int(tokenAmountOut * math.pow(10, tokenDecimals[tokenOutIndex] - 9))
        mylogger.info("加入池子前的价格为: {}".format(spotPriceBefore))
        mylogger.info("加入 {} 的{}可以得到 {} 的{}".format(tokenAmountIn, tokenIn, tokenAmountOut, tokenOut))
        mylogger.info("实际加入 {}，实际可以得到 {}".format(actualTokenAmountIn, actualTokenAmountOut))
        mylogger.info("交易后预计的价格为: {}".format(spotPriceAfter))
        limitPrice = bdiv(tokenAmountIn, tokenAmountOut)
        mylogger.info("交易后成功的价格不能小于: {}".format(limitPrice))
        if spotPriceAfter < limitPrice or spotPriceBefore > limitPrice:
            logger.info("该笔交易应该会失败")
        #     return

        transfer_fee = get_transfer_fee(actualTokenAmountOut, tokenNames[tokenOutIndex], True, syms[tokenOutIndex]["contract"])
        mylogger.info("transfer_fee: {}".format(transfer_fee))
        mylogger.info("授权。。")
        allowDosContract(user, acc2pub_keys[user])
        tx = self.swapClient.swapAmountIn(user, poolName,
                                          to_wei_asset(tokenInAmount, tokenIn, tokenDecimals[tokenInIndex], contract),
                                          to_wei_asset(actualTokenAmountOut /math.pow(10, tokenDecimals[tokenOutIndex]) * 2, tokenOut, tokenDecimals[tokenOutIndex], contract),
                                          spotPriceAfter + 1)
        if "code" in tx:
            errMsg = tx["error"]["details"][0]["message"]
            contractAmount = int(errMsg.split(": ")[-1].split("ERR_LIMIT_OUT:tokenAmountOut=")[-1])
            parseAmount = int(contractAmount * math.pow(10, tokenDecimals[tokenOutIndex] - 9))
            tx = self.swapClient.swapAmountIn(user, poolName,
                                              to_wei_asset(tokenInAmount, tokenIn, tokenDecimals[tokenInIndex], contract),
                                              to_wei_asset(parseAmount / math.pow(10, tokenDecimals[tokenOutIndex]), tokenOut, tokenDecimals[tokenOutIndex], contract),
                                              spotPriceAfter + 1)
        else:
            contractAmount = tokenAmountOut
        # print(contractAmount)
        # print(int(contractAmount * math.pow(10, tokenDecimals[tokenOutIndex]-9))
        contractFee = get_transfer_fee(int(contractAmount * math.pow(10, tokenDecimals[tokenOutIndex]-9)), tokenNames[tokenOutIndex], True, syms[tokenOutIndex]["contract"])
        actulaContractAmountOut = int(contractAmount * math.pow(10, tokenDecimals[tokenOutIndex] - 9)) - contractFee

        actualTokenAmountOut = int((tokenAmountOut - transfer_fee) * math.pow(10, tokenDecimals[tokenOutIndex] - 9))
        time.sleep(3)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        # mylogger.info(f"交易后, 池子{poolName}的信息: {poolInfo2}")
        mylogger.info(f"交易后, 池子{poolName}的信息: {poolInfo2['pools']['records']}")
        userBalance2 = self.getAccountBalance(user, tokenNames, contract)
        mylogger.info(f"交易后, 用户{user}持有的资产: {userBalance2}")
        userSupply2 = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"交易后, 用户{user}持有的lp: {userSupply2}")
        totalSupply2 = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("交易后, 池子中总的lp为: {}".format(totalSupply2))

        # poolBalance2 = self.getAccountBalance(poolName, tokenNames)
        # mylogger.info("池子实际持有资产: {}".format(poolBalance2))

        mylogger.info("---计算合约和eth合约18位精度的计算偏差---")
        mylogger.info("实际输入{}的数量为: {}".format(tokenIn, to_wei_asset(tokenInAmount, tokenIn, tokenDecimals[tokenInIndex])))
        mylogger.info("balance合约18位精度下计算的tokenAmountOut为: {}".format(tokenAmountOut2))
        mylogger.info("balance合约18位精度下计算的price为: before {}, after {}".format(spotPriceBefore2, spotPriceAfter2))
        mylogger.info("合约中计算的tokenAmountOut为: {}".format(contractAmount))
        mylogger.info("合约中计算的transfer fee 为: {}".format(contractFee))
        mylogger.info("合约中计算的实际转账的tokenAmountOut为: {}".format(actulaContractAmountOut))
        amountDiff = contractAmount - tokenAmountOut2
        actualAmountDiff = amountDiff // int(math.pow(10, 9 - tokenDecimals[tokenOutIndex])) / int(math.pow(10, tokenDecimals[tokenOutIndex]))
        mylogger.info("计算和池子偏差: %s, 实际偏差: %.8f个%s" % (amountDiff, actualAmountDiff, tokenOut))
        mylogger.info("---开始进行校验---")

        # 检查池子中的lp计算正确
        assert totalSupply2 == totalSupply, "交易时，池子的lp应不变"
        # 检查用户持有的lp
        assert userSupply2 == userSupply, "用户交易lp不正确"

        # 检查池子资产中记录的balance和weight正确
        for index, tokenBalnce in enumerate(balances):

            afterBalance = int(poolInfo2["pools"]['records'][index]["value"]["balance"])
            if index == tokenInIndex:
                mylogger.info("池子{}资产变化: {}".format(tokenIn, afterBalance - balances[index]))
                userChanged = userBalance[tokenNames[index]]["parseBalance"] - userBalance2[tokenNames[index]]["parseBalance"]
                mylogger.info("用户{}资产变化: {}".format(tokenIn, userChanged))

                # 检查池子资产record是否正确
                assert afterBalance - balances[index] == tokenAmountIn, "池子{}的资产变化不正确, 实际变化了{}".format(tokenIn, afterBalance - balances[index])
                # 检查用户持有的资产变化
                fee = get_transfer_fee(actualTokenAmountIn, tokenIn, False, contract)
                assert userChanged == actualTokenAmountIn + fee, "用户实际变化了: {}".format(userChanged)
            elif index == tokenOutIndex:
                mylogger.info("池子{}资产变化: {}".format(tokenOut, balances[index] - afterBalance))
                userChanged = userBalance2[tokenNames[index]]["parseBalance"] - userBalance[tokenNames[index]]["parseBalance"]
                mylogger.info("用户{}资产变化: {}".format(tokenOut, userChanged))

                expectPoolAmount = contractAmount - contractAmount % int(math.pow(10, 9 - tokenDecimals[tokenOutIndex]))
                assert balances[index] - afterBalance == expectPoolAmount, "池子{}的资产变化不正确, 实际变化了{}".format(tokenOut, balances[index] -afterBalance)
                # 检查用户持有的资产变化
                assert userChanged == actulaContractAmountOut, "用户实际变化了: {}".format(userChanged)
            else:
                assert afterBalance == balances[tokenInIndex], "池子其他token的资产应保持不变"
            # 检查池子的denorm是否正确
            assert poolInfo2["pools"]['records'][index]["value"]["denorm"] == weights[index]
        # 检查池子实际持有的token资产和record的资产是否一致
        self.checkPoolBalance(poolName)

    def checkSwapAmountInWhentokenIsNotBoundInPool(self, poolName, tokenIn, tokenInAmount, tokenOut, user=nonadmin):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")
        balances = []
        weights = []
        tokenDecimals = []
        syms = []
        tokenNames = []
        for token in poolInfo["pools"]["tokens"]:
            t_record = [i["value"] for i in poolInfo["pools"]["records"] if i["key"] == token][0]
            balances.append(int(t_record["balance"]))
            weights.append(t_record["denorm"])
            syms.append(t_record["exsym"])
            tokenNames.append(t_record["exsym"]['symbol'].split(",")[-1])
            tokenDecimals.append(int(t_record["exsym"]['symbol'].split(",")[0]))
        swapFee = poolInfo["pools"]['swapFee']
        mylogger.info("池子的交易费用为:{} == {}".format(swapFee, swapFee/math.pow(10, 9)))
        userBalance = self.getAccountBalance(user, tokenNames)
        mylogger.info(f"用户{user}持有的资产: {userBalance}")
        userSupply = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"用户{user}持有的lp: {userSupply}")
        totalSupply = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("池子中总的lp为: {}".format(totalSupply))

        tokenInIndex = tokenNames.index(tokenIn) if tokenIn in tokenNames else tokenNames.index([i for i in tokenNames if i != tokenOut][0])
        tokenOutIndex = tokenNames.index(tokenOut) if tokenOut in tokenNames else tokenNames.index([i for i in tokenNames if i != tokenIn][0])
        spotPriceBefore = self.mathContract.functions.calcSpotPrice(
            balances[tokenInIndex], weights[tokenInIndex], balances[tokenOutIndex], weights[tokenOutIndex], swapFee
        ).call()
        tokenAmountIn = int(tokenInAmount * math.pow(10, 9))
        tokenAmountOut = self.mathContract.functions.calcOutGivenIn(
            balances[tokenInIndex], weights[tokenInIndex], balances[tokenOutIndex], weights[tokenOutIndex], tokenAmountIn, swapFee
        ).call()
        inRecordBalance = balances[tokenInIndex] + tokenAmountIn
        outRecordBalance = balances[tokenOutIndex] - tokenAmountOut
        spotPriceAfter = self.mathContract.functions.calcSpotPrice(
            inRecordBalance, weights[tokenInIndex], outRecordBalance, weights[tokenOutIndex], swapFee
        ).call()
        actualTokenAmountIn = int(tokenAmountIn * math.pow(10, tokenDecimals[tokenInIndex] - 9))
        actualTokenAmountOut = int(tokenAmountOut * math.pow(10, tokenDecimals[tokenOutIndex] - 9))
        mylogger.info("加入池子前的价格为: {}".format(spotPriceBefore))
        mylogger.info("加入 {} 的{}可以得到 {} 的{}".format(tokenAmountIn, tokenIn, tokenAmountOut, tokenOut))
        mylogger.info("实际加入 {}，实际可以得到 {}".format(actualTokenAmountIn, actualTokenAmountOut))
        mylogger.info("交易后预计的价格为: {}".format(spotPriceAfter))
        limitPrice = bdiv(tokenAmountIn, tokenAmountOut)
        mylogger.info("交易后成功的价格不能小于: {}".format(limitPrice))
        if spotPriceAfter < limitPrice or spotPriceBefore > limitPrice:
            logger.info("该笔交易应该会失败")
            return

        mylogger.info("授权。。")
        allowDosContract(user, acc2pub_keys[user])
        tx = self.swapClient.swapAmountIn(user, poolName,
                                          to_wei_asset(tokenInAmount, tokenIn, tokenDecimals[tokenInIndex]),
                                          to_wei_asset(actualTokenAmountOut/math.pow(10, tokenDecimals[tokenOutIndex]), tokenOut, tokenDecimals[tokenOutIndex]),
                                          spotPriceAfter)
        assert "ERR_NOT_BOUND" in tx["error"]["details"][0]["message"]
        time.sleep(3)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        mylogger.info(f"交易后, 池子{poolName}的信息: {poolInfo2}")
        userBalance2 = self.getAccountBalance(user, tokenNames)
        mylogger.info(f"交易后, 用户{user}持有的资产: {userBalance2}")
        userSupply2 = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"交易后, 用户{user}持有的lp: {userSupply2}")
        totalSupply2 = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("交易后, 池子中总的lp为: {}".format(totalSupply2))

        #检查池子中的lp计算正确
        assert totalSupply2 == totalSupply, "交易时，池子的lp应不变"
        # 检查用户持有的lp
        assert userSupply2 == userSupply, "用户交易lp不正确"

        # 检查池子资产中记录的balance和weight正确
        for index, tokenBalnce in enumerate(balances):

            afterBalance = int(poolInfo2["pools"]['records'][index]["value"]["balance"])
            if index == tokenInIndex:
                # 检查池子资产record是否正确
                assert afterBalance - balances[index] == 0, "池子{}的资产变化不正确".format(tokenIn)
                # 检查用户持有的资产变化
                assert userBalance2[tokenNames[index]]["parseBalance"] + 0 == \
                       userBalance[tokenNames[index]]["parseBalance"]
            elif index == tokenOutIndex:
                assert afterBalance + 0 == balances[index], "池子{}的资产变化不正确".format(tokenOut)
                # 检查用户持有的资产变化
                assert userBalance2[tokenNames[index]]["parseBalance"] - 0 == \
                       userBalance[tokenNames[index]]["parseBalance"]
            else:
                assert afterBalance == balances[tokenInIndex], "池子其他token的资产应保持不变"
            # 检查池子的denorm是否正确
            assert poolInfo2["pools"]['records'][index]["value"]["denorm"] == weights[index]
        # 检查池子实际持有的token资产和record的资产是否一致
        self.checkPoolBalance(poolName)

    def checkSwapAmountInWhenAmountInMoreThanLimit(self, poolName, tokenIn, tokenOut, user=nonadmin):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")
        balances = []
        weights = []
        tokenDecimals = []
        syms = []
        tokenNames = []
        for token in poolInfo["pools"]["tokens"]:
            t_record = [i["value"] for i in poolInfo["pools"]["records"] if i["key"] == token][0]
            balances.append(int(t_record["balance"]))
            weights.append(t_record["denorm"])
            syms.append(t_record["exsym"])
            tokenNames.append(t_record["exsym"]['symbol'].split(",")[-1])
            tokenDecimals.append(int(t_record["exsym"]['symbol'].split(",")[0]))
        swapFee = poolInfo["pools"]['swapFee']
        mylogger.info("池子的交易费用为:{} == {}".format(swapFee, swapFee/math.pow(10, 9)))
        userBalance = self.getAccountBalance(user, tokenNames)
        mylogger.info(f"用户{user}持有的资产: {userBalance}")
        userSupply = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"用户{user}持有的lp: {userSupply}")
        totalSupply = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("池子中总的lp为: {}".format(totalSupply))
        tokenInIndex = tokenNames.index(tokenIn)
        tokenOutIndex = tokenNames.index(tokenOut)
        spotPriceBefore = self.mathContract.functions.calcSpotPrice(
            balances[tokenInIndex], weights[tokenInIndex], balances[tokenOutIndex], weights[tokenOutIndex], swapFee
        ).call()
        # tokenAmountIn = int(tokenInAmount * math.pow(10, 9))
        MAX_IN_RATIO = int(math.pow(10, 9)) // 2
        tokenAmountIn = bmul(balances[tokenInIndex], MAX_IN_RATIO) + 10
        tokenInAmount = tokenAmountIn / math.pow(10, 9)
        tokenAmountOut = self.mathContract.functions.calcOutGivenIn(
            balances[tokenInIndex], weights[tokenInIndex], balances[tokenOutIndex], weights[tokenOutIndex], tokenAmountIn, swapFee
        ).call()
        inRecordBalance = balances[tokenInIndex] + tokenAmountIn
        outRecordBalance = balances[tokenOutIndex] - tokenAmountOut
        spotPriceAfter = self.mathContract.functions.calcSpotPrice(
            inRecordBalance, weights[tokenInIndex], outRecordBalance, weights[tokenOutIndex], swapFee
        ).call()
        actualTokenAmountIn = int(tokenAmountIn * math.pow(10, tokenDecimals[tokenInIndex] - 9))
        actualTokenAmountOut = int(tokenAmountOut * math.pow(10, tokenDecimals[tokenOutIndex] - 9))
        mylogger.info("加入池子前的价格为: {}".format(spotPriceBefore))
        mylogger.info("加入 {} 的{}可以得到 {} 的{}".format(tokenAmountIn, tokenIn, tokenAmountOut, tokenOut))
        mylogger.info("实际加入 {}，实际可以得到 {}".format(actualTokenAmountIn, actualTokenAmountOut))
        mylogger.info("交易后预计的价格为: {}".format(spotPriceAfter))
        limitPrice = bdiv(tokenAmountIn, tokenAmountOut)
        mylogger.info("交易后成功的价格不能小于: {}".format(limitPrice))
        if spotPriceAfter < limitPrice:
            logger.info("该笔交易应该会失败")
            return

        mylogger.info("授权。。")
        allowDosContract(user, acc2pub_keys[user])
        tx = self.swapClient.swapAmountIn(user, poolName,
                                          to_wei_asset(tokenInAmount, tokenIn, tokenDecimals[tokenInIndex]),
                                          to_wei_asset(actualTokenAmountOut/math.pow(10, tokenDecimals[tokenOutIndex]), tokenOut, tokenDecimals[tokenOutIndex]),
                                          spotPriceAfter)
        assert "ERR_MAX_IN_RATIO" in tx["error"]["details"][0]["message"]
        time.sleep(3)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        mylogger.info(f"交易后, 池子{poolName}的信息: {poolInfo2}")
        userBalance2 = self.getAccountBalance(user, tokenNames)
        mylogger.info(f"交易后, 用户{user}持有的资产: {userBalance2}")
        userSupply2 = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"交易后, 用户{user}持有的lp: {userSupply2}")
        totalSupply2 = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("交易后, 池子中总的lp为: {}".format(totalSupply2))

        #检查池子中的lp计算正确
        assert totalSupply2 == totalSupply, "交易时，池子的lp应不变"
        # 检查用户持有的lp
        assert userSupply2 == userSupply, "用户交易lp不正确"

        # 检查池子资产中记录的balance和weight正确
        for index, tokenBalnce in enumerate(balances):

            afterBalance = int(poolInfo2["pools"]['records'][index]["value"]["balance"])
            if index == tokenInIndex:
                # 检查池子资产record是否正确
                assert afterBalance - balances[index] == 0, "池子{}的资产变化不正确".format(tokenIn)
                # 检查用户持有的资产变化
                assert userBalance2[tokenNames[index]]["parseBalance"] + 0 == \
                       userBalance[tokenNames[index]]["parseBalance"]
            elif index == tokenOutIndex:
                assert afterBalance + 0 == balances[index], "池子{}的资产变化不正确".format(tokenOut)
                # 检查用户持有的资产变化
                assert userBalance2[tokenNames[index]]["parseBalance"] - 0 == \
                       userBalance[tokenNames[index]]["parseBalance"]
            else:
                assert afterBalance == balances[tokenInIndex], "池子其他token的资产应保持不变"
            # 检查池子的denorm是否正确
            assert poolInfo2["pools"]['records'][index]["value"]["denorm"] == weights[index]
        # 检查池子实际持有的token资产和record的资产是否一致
        self.checkPoolBalance(poolName)

    def checkSwapAmountOut(self, poolName, tokenOut, tokenOutAmount, tokenIn, user=nonadmin):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")
        balances = []
        weights = []
        tokenDecimals = []
        syms = []
        tokenNames = []
        for token in poolInfo["pools"]["tokens"]:
            t_record = [i["value"] for i in poolInfo["pools"]["records"] if i["key"] == token][0]
            balances.append(int(t_record["balance"]))
            weights.append(t_record["denorm"])
            syms.append(t_record["exsym"])
            tokenNames.append(t_record["exsym"]['symbol'].split(",")[-1])
            tokenDecimals.append(int(t_record["exsym"]['symbol'].split(",")[0]))
        contract = syms[0]["contract"]
        swapFee = poolInfo["pools"]['swapFee']
        mylogger.info("池子的交易费用为:{} == {}".format(swapFee, swapFee/math.pow(10, 9)))
        userBalance = self.getAccountBalance(user, tokenNames, contract)
        mylogger.info(f"用户{user}持有的资产: {userBalance}")
        userSupply = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"用户{user}持有的lp: {userSupply}")
        totalSupply = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("池子中总的lp为: {}".format(totalSupply))
        mylogger.info("池子中record资产: {}".format(balances))

        tokenInIndex = tokenNames.index(tokenIn)
        tokenOutIndex = tokenNames.index(tokenOut)

        transfer_fee = get_transfer_fee(int(tokenOutAmount * math.pow(10, tokenDecimals[tokenOutIndex])), tokenNames[tokenOutIndex], False,
                                        syms[tokenOutIndex]["contract"])

        tokenAmountOut = int(tokenOutAmount * math.pow(10, 9))
        tokenAmountOut += int(transfer_fee * math.pow(10, 9-tokenDecimals[tokenOutIndex]))
        mylogger.info("实际交易的amountOut数量为: {}".format(tokenAmountOut))
        spotPriceBefore = self.mathContract.functions.calcSpotPrice(
            balances[tokenInIndex], weights[tokenInIndex], balances[tokenOutIndex], weights[tokenOutIndex], swapFee
        ).call()
        spotPriceBefore2 = self.mathContract2.functions.calcSpotPrice(
            balances[tokenInIndex], weights[tokenInIndex], balances[tokenOutIndex], weights[tokenOutIndex], swapFee
        ).call()

        print(balances[tokenInIndex], weights[tokenInIndex], balances[tokenOutIndex], weights[tokenOutIndex], tokenAmountOut, swapFee)
        tokenAmountIn = self.mathContract.functions.calcInGivenOut(
            balances[tokenInIndex], weights[tokenInIndex], balances[tokenOutIndex], weights[tokenOutIndex], tokenAmountOut, swapFee
        ).call()
        tokenAmountIn2 = self.mathContract2.functions.calcInGivenOut(
            balances[tokenInIndex], weights[tokenInIndex], balances[tokenOutIndex], weights[tokenOutIndex],
            tokenAmountOut, swapFee
        ).call()
        inRecordBalance = balances[tokenInIndex] + tokenAmountIn
        outRecordBalance = balances[tokenOutIndex] - tokenAmountOut
        spotPriceAfter = self.mathContract.functions.calcSpotPrice(
            inRecordBalance, weights[tokenInIndex], outRecordBalance, weights[tokenOutIndex], swapFee
        ).call()
        spotPriceAfter2 = self.mathContract2.functions.calcSpotPrice(
            inRecordBalance, weights[tokenInIndex], outRecordBalance, weights[tokenOutIndex], swapFee
        ).call()
        # 计算出来的tokenAmountIn转为实际token精度时有损失
        actualTokenAmountIn = int(tokenAmountIn * math.pow(10, tokenDecimals[tokenInIndex] - 9))
        actualTokenAmountOut = int(tokenAmountOut * math.pow(10, tokenDecimals[tokenOutIndex] - 9))
        mylogger.info("加入池子前的价格为: {}".format(spotPriceBefore))
        mylogger.info("加入 {} 的{}可以得到 {} 的{}".format(tokenAmountIn, tokenIn, tokenAmountOut, tokenOut))
        mylogger.info("实际加入 {}，实际可以得到 {}".format(actualTokenAmountIn, actualTokenAmountOut))
        mylogger.info("交易后预计的价格为: {}".format(spotPriceAfter))
        limitPrice = bdiv(tokenAmountIn, tokenAmountOut)
        mylogger.info("交易前的价格不能超过: {}".format(limitPrice))
        if limitPrice < spotPriceBefore or spotPriceBefore > limitPrice:
            logger.info("该笔交易应该会失败")
            # return

        mylogger.info("transfer_fee: {}".format(transfer_fee))

        mylogger.info("授权。。")
        allowDosContract(user, acc2pub_keys[user])
        # print(to_wei_asset(actualTokenAmountIn/math.pow(10, tokenDecimals[tokenInIndex]), tokenIn, tokenDecimals[tokenInIndex]))
        # print(to_wei_asset(tokenOutAmount, tokenOut, tokenDecimals[tokenOutIndex]))
        tx = self.swapClient.swapAmountOut(user, poolName,
                                          to_wei_asset(actualTokenAmountIn * 0.1/math.pow(10, tokenDecimals[tokenInIndex]), tokenIn, tokenDecimals[tokenInIndex],contract),
                                          to_wei_asset(tokenOutAmount, tokenOut, tokenDecimals[tokenOutIndex], contract),
                                          spotPriceAfter)

        if "code" in tx:
            errMsg = tx["error"]["details"][0]["message"]
            contractAmountIn = int(errMsg.split(": ")[-1].split("ERR_LIMIT_IN:tokenAmountIn=")[-1])
            parseAmount = int(contractAmountIn * math.pow(10, tokenDecimals[tokenInIndex] - 9)) + 1
            tx = self.swapClient.swapAmountOut(user, poolName,
                                              to_wei_asset(parseAmount / math.pow(10, tokenDecimals[tokenInIndex]), tokenIn, tokenDecimals[tokenInIndex], contract),
                                              to_wei_asset(tokenOutAmount, tokenOut, tokenDecimals[tokenOutIndex], contract),
                                              spotPriceAfter)
            if "code" in tx:
                errMsg = tx["error"]["details"][0]["message"]
                maxPrice = int(errMsg.split(": ")[-1].split("ERR_LIMIT_PRICE:spotPriceAfter=")[-1])
                tx = self.swapClient.swapAmountOut(user, poolName,
                                                  to_wei_asset(parseAmount / math.pow(10, tokenDecimals[tokenInIndex]),
                                                               tokenIn, tokenDecimals[tokenInIndex], contract),
                                                  to_wei_asset(tokenOutAmount, tokenOut, tokenDecimals[tokenOutIndex], contract),
                                                  maxPrice)

        else:
            contractAmountIn = tokenAmountIn
        contractFee = transfer_fee
        poolContractAmountOut = tokenAmountOut

        time.sleep(3)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        mylogger.info(f"交易后, 池子{poolName}的信息: {poolInfo2['pools']['records']}")
        userBalance2 = self.getAccountBalance(user, tokenNames, contract)
        mylogger.info(f"交易后, 用户{user}持有的资产: {userBalance2}")
        userSupply2 = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"交易后, 用户{user}持有的lp: {userSupply2}")
        totalSupply2 = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("交易后, 池子中总的lp为: {}".format(totalSupply2))

        mylogger.info("---计算合约和eth合约18位精度的计算偏差---")
        mylogger.info("实际要得到的数量为: {}".format(to_wei_asset(tokenOutAmount, tokenOut, tokenDecimals[tokenOutIndex])))
        mylogger.info("balance合约18位精度下计算的tokenAmountIn为: {}".format(tokenAmountIn2))
        mylogger.info("balance合约18位精度下计算的price为: before {}, after {}".format(spotPriceBefore2, spotPriceAfter2))
        mylogger.info("合约中计算的tokenAmountIn为: {}".format(contractAmountIn))
        mylogger.info("合约中计算的transfer fee 为: {}".format(contractFee))
        mylogger.info("合约中计算的实际转账的tokenAmountOut为: {}".format(poolContractAmountOut))
        amountDiff = contractAmountIn - tokenAmountIn2
        actualAmountDiff = amountDiff // int(math.pow(10, 9 - tokenDecimals[tokenInIndex])) / int(
            math.pow(10, tokenDecimals[tokenInIndex]))
        mylogger.info("tokenAmountIn的计算和池子偏差: %s, 实际偏差: %.8f个%s" % (amountDiff, actualAmountDiff, tokenIn))
        mylogger.info("---开始进行校验---")

        # 检查池子中的lp计算正确
        assert totalSupply2 == totalSupply, "交易时，池子的lp应不变"
        # 检查用户持有的lp
        assert userSupply2 == userSupply, "用户交易lp不正确"
        # 检查池子资产中记录的balance和weight正确
        for index, tokenBalnce in enumerate(balances):
            afterBalance = int(poolInfo2["pools"]['records'][index]["value"]["balance"])
            if index == tokenInIndex:
                mylogger.info("池子record{}资产变化: {}".format(tokenIn, afterBalance - balances[index]))
                userChanged = userBalance[tokenNames[index]]["parseBalance"] - userBalance2[tokenNames[index]][
                    "parseBalance"]
                mylogger.info("用户{}资产变化: {}".format(tokenIn, userChanged))
                # 检查池子资产record是否正确
                expectPoolAmountIn = contractAmountIn - contractAmountIn % int(math.pow(10, 9 - tokenDecimals[tokenInIndex]))
                assert afterBalance - balances[index] == expectPoolAmountIn, "池子{}的资产变化不正确".format(tokenIn)
                # 检查用户持有的资产变化, 要加上tranferFee
                parseAmt = int(contractAmountIn * math.pow(10, tokenDecimals[tokenInIndex] - 9))
                userTransferFee = get_transfer_fee(parseAmt, tokenNames[tokenInIndex], False, syms[tokenInIndex]["contract"])
                expectUserAmountIn = parseAmt + userTransferFee
                assert userChanged == expectUserAmountIn, "用户{}资产实际变化:{}".format(tokenIn, userChanged)
            elif index == tokenOutIndex:
                mylogger.info("池子record{}资产变化: {}".format(tokenOut, balances[index] - afterBalance))
                userChanged = userBalance2[tokenNames[index]]["parseBalance"] - userBalance[tokenNames[index]][
                    "parseBalance"]
                mylogger.info("用户{}资产变化: {}".format(tokenOut, userChanged))

                expectPoolAmountOut = poolContractAmountOut - poolContractAmountOut % int(math.pow(10, 9 - tokenDecimals[tokenOutIndex]))
                assert balances[index] - afterBalance == expectPoolAmountOut, "池子{}的资产变化不正确".format(tokenOut)
                # 检查用户持有的资产变化
                assert userChanged == int(tokenOutAmount * math.pow(10, tokenDecimals[tokenOutIndex])), "用户{}资产实际变化:{}".format(tokenOut, userChanged)
            else:
                assert afterBalance == balances[tokenInIndex], "池子其他token的资产应保持不变"

            # 检查池子的denorm是否正确
            assert poolInfo2["pools"]['records'][index]["value"]["denorm"] == weights[index]
        # 检查池子实际持有的token资产和record的资产是否一致
        self.checkPoolBalance(poolName)

    def checkSwapAmountOutWhenAmountOutMoreThanLimit(self, poolName, tokenOut, tokenIn, user=nonadmin):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")
        balances = []
        weights = []
        tokenDecimals = []
        syms = []
        tokenNames = []
        for token in poolInfo["pools"]["tokens"]:
            t_record = [i["value"] for i in poolInfo["pools"]["records"] if i["key"] == token][0]
            balances.append(int(t_record["balance"]))
            weights.append(t_record["denorm"])
            syms.append(t_record["exsym"])
            tokenNames.append(t_record["exsym"]['symbol'].split(",")[-1])
            tokenDecimals.append(int(t_record["exsym"]['symbol'].split(",")[0]))
        swapFee = poolInfo["pools"]['swapFee']
        mylogger.info("池子的交易费用为:{} == {}".format(swapFee, swapFee/math.pow(10, 9)))
        userBalance = self.getAccountBalance(user, tokenNames)
        mylogger.info(f"用户{user}持有的资产: {userBalance}")
        userSupply = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"用户{user}持有的lp: {userSupply}")
        totalSupply = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("池子中总的lp为: {}".format(totalSupply))
        tokenInIndex = tokenNames.index(tokenIn)
        tokenOutIndex = tokenNames.index(tokenOut)
        spotPriceBefore = self.mathContract.functions.calcSpotPrice(
            balances[tokenInIndex], weights[tokenInIndex], balances[tokenOutIndex], weights[tokenOutIndex], swapFee
        ).call()
        # tokenAmountOut = int(tokenOutAmount * math.pow(10, 9))
        # tokenAmountOut = int(balances[tokenOutIndex] // 3)
        MAX_OUT_RATIO = int(math.pow(10, 9)) // 3 + 1
        tokenAmountOut = bmul(balances[tokenOutIndex], MAX_OUT_RATIO) + 10
        tokenOutAmount = tokenAmountOut / math.pow(10, 9)
        tokenAmountIn = self.mathContract.functions.calcInGivenOut(
            balances[tokenInIndex], weights[tokenInIndex], balances[tokenOutIndex], weights[tokenOutIndex], tokenAmountOut, swapFee
        ).call()
        inRecordBalance = balances[tokenInIndex] + tokenAmountIn
        outRecordBalance = balances[tokenOutIndex] - tokenAmountOut
        spotPriceAfter = self.mathContract.functions.calcSpotPrice(
            inRecordBalance, weights[tokenInIndex], outRecordBalance, weights[tokenOutIndex], swapFee
        ).call()
        # 计算出来的tokenAmountIn转为实际token精度时有损失, +1保证交易能成功执行
        actualTokenAmountIn = int(tokenAmountIn * math.pow(10, tokenDecimals[tokenInIndex] - 9)) + 1
        actualTokenAmountOut = int(tokenAmountOut * math.pow(10, tokenDecimals[tokenOutIndex] - 9))
        mylogger.info("加入池子前的价格为: {}".format(spotPriceBefore))
        mylogger.info("加入 {} 的{}可以得到 {} 的{}".format(tokenAmountIn, tokenIn, tokenAmountOut, tokenOut))
        mylogger.info("实际加入 {}，实际可以得到 {}".format(actualTokenAmountIn, actualTokenAmountOut))
        mylogger.info("交易后预计的价格为: {}".format(spotPriceAfter))
        limitPrice = bdiv(tokenAmountIn, tokenAmountOut)
        mylogger.info("交易前的价格不能超过: {}".format(limitPrice))
        if limitPrice < spotPriceBefore:
            logger.info("该笔交易应该会失败")

        # mylogger.info("授权。。")
        # allowDosContract(user, acc2pub_keys[user])
        # print(to_wei_asset(actualTokenAmountIn/math.pow(10, tokenDecimals[tokenInIndex]), tokenIn, tokenDecimals[tokenInIndex]))
        # print(to_wei_asset(tokenOutAmount, tokenOut, tokenDecimals[tokenOutIndex]))
        tx = self.swapClient.swapAmountOut(user, poolName,
                                          to_wei_asset(actualTokenAmountIn/math.pow(10, tokenDecimals[tokenInIndex]), tokenIn, tokenDecimals[tokenInIndex]),
                                          to_wei_asset(tokenOutAmount, tokenOut, tokenDecimals[tokenOutIndex]),
                                          spotPriceAfter)
        assert "ERR_MAX_OUT_RATIO" in tx["error"]["details"][0]["message"]
        time.sleep(3)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        mylogger.info(f"交易后, 池子{poolName}的信息: {poolInfo2}")
        userBalance2 = self.getAccountBalance(user, tokenNames)
        mylogger.info(f"交易后, 用户{user}持有的资产: {userBalance2}")
        userSupply2 = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"交易后, 用户{user}持有的lp: {userSupply2}")
        totalSupply2 = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("交易后, 池子中总的lp为: {}".format(totalSupply2))

        # 检查池子中的lp计算正确
        assert totalSupply2 == totalSupply, "交易时，池子的lp应不变"
        # 检查用户持有的lp
        assert userSupply2 == userSupply, "用户交易lp不正确"
        # 检查池子资产中记录的balance和weight正确
        for index, tokenBalnce in enumerate(balances):
            afterBalance = int(poolInfo2["pools"]['records'][index]["value"]["balance"])
            if index == tokenInIndex:
                # 检查池子资产record是否正确
                assert afterBalance - balances[index] == 0, "池子{}的资产变化不正确".format(tokenIn)
                # 检查用户持有的资产变化
                assert userBalance2[tokenNames[index]]["parseBalance"] + 0 == \
                       userBalance[tokenNames[index]]["parseBalance"]
            elif index == tokenOutIndex:
                assert afterBalance + 0 == balances[index], "池子{}的资产变化不正确".format(tokenOut)
                # 检查用户持有的资产变化
                assert userBalance2[tokenNames[index]]["parseBalance"] - 0 == \
                       userBalance[tokenNames[index]]["parseBalance"]
            else:
                assert afterBalance == balances[tokenInIndex], "池子其他token的资产应保持不变"
            # 检查池子的denorm是否正确
            assert poolInfo2["pools"]['records'][index]["value"]["denorm"] == weights[index]
        # 检查池子实际持有的token资产和record的资产是否一致
        self.checkPoolBalance(poolName)

    def checkSwapAmountOutWhenTokenNotBoundInPool(self, poolName, tokenOut, tokenOutAmount, tokenIn, user=nonadmin):
        mylogger.info(sys._getframe().f_code.co_name)
        poolInfo = self.getPoolInfo(poolName, admin)
        mylogger.info(f"{poolName} pool info: {poolInfo}")
        balances = []
        weights = []
        tokenDecimals = []
        syms = []
        tokenNames = []
        for token in poolInfo["pools"]["tokens"]:
            t_record = [i["value"] for i in poolInfo["pools"]["records"] if i["key"] == token][0]
            balances.append(int(t_record["balance"]))
            weights.append(t_record["denorm"])
            syms.append(t_record["exsym"])
            tokenNames.append(t_record["exsym"]['symbol'].split(",")[-1])
            tokenDecimals.append(int(t_record["exsym"]['symbol'].split(",")[0]))
        swapFee = poolInfo["pools"]['swapFee']
        mylogger.info("池子的交易费用为:{} == {}".format(swapFee, swapFee/math.pow(10, 9)))
        userBalance = self.getAccountBalance(user, tokenNames)
        mylogger.info(f"用户{user}持有的资产: {userBalance}")
        userSupply = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"用户{user}持有的lp: {userSupply}")
        totalSupply = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("池子中总的lp为: {}".format(totalSupply))
        # 当传入错误的token值，寻找pool中其他的正确token的index
        tokenInIndex = tokenNames.index(tokenIn) if tokenIn in tokenNames else tokenNames.index([i for i in tokenNames if i != tokenOut][0])
        tokenOutIndex = tokenNames.index(tokenOut) if tokenOut in tokenNames else tokenNames.index([i for i in tokenNames if i != tokenIn][0])
        # tokenInIndex = tokenNames.index(tokenIn)
        # tokenOutIndex = tokenNames.index(tokenOut)
        spotPriceBefore = self.mathContract.functions.calcSpotPrice(
            balances[tokenInIndex], weights[tokenInIndex], balances[tokenOutIndex], weights[tokenOutIndex], swapFee
        ).call()
        tokenAmountOut = int(tokenOutAmount * math.pow(10, 9))
        tokenAmountIn = self.mathContract.functions.calcInGivenOut(
            balances[tokenInIndex], weights[tokenInIndex], balances[tokenOutIndex], weights[tokenOutIndex], tokenAmountOut, swapFee
        ).call()
        inRecordBalance = balances[tokenInIndex] + tokenAmountIn
        outRecordBalance = balances[tokenOutIndex] - tokenAmountOut
        spotPriceAfter = self.mathContract.functions.calcSpotPrice(
            inRecordBalance, weights[tokenInIndex], outRecordBalance, weights[tokenOutIndex], swapFee
        ).call()
        # 计算出来的tokenAmountIn转为实际token精度时有损失, +1保证交易能成功执行
        actualTokenAmountIn = int(tokenAmountIn * math.pow(10, tokenDecimals[tokenInIndex] - 9)) + 1
        actualTokenAmountOut = int(tokenAmountOut * math.pow(10, tokenDecimals[tokenOutIndex] - 9))
        mylogger.info("加入池子前的价格为: {}".format(spotPriceBefore))
        mylogger.info("加入 {} 的{}可以得到 {} 的{}".format(tokenAmountIn, tokenIn, tokenAmountOut, tokenOut))
        mylogger.info("实际加入 {}，实际可以得到 {}".format(actualTokenAmountIn, actualTokenAmountOut))
        mylogger.info("交易后预计的价格为: {}".format(spotPriceAfter))
        limitPrice = bdiv(tokenAmountIn, tokenAmountOut)
        mylogger.info("交易前的价格不能超过: {}".format(limitPrice))
        if limitPrice < spotPriceBefore:
            logger.info("该笔交易应该会失败")

        # mylogger.info("授权。。")
        # allowDosContract(user, acc2pub_keys[user])
        # print(to_wei_asset(actualTokenAmountIn/math.pow(10, tokenDecimals[tokenInIndex]), tokenIn, tokenDecimals[tokenInIndex]))
        # print(to_wei_asset(tokenOutAmount, tokenOut, tokenDecimals[tokenOutIndex]))
        tx = self.swapClient.swapAmountOut(user, poolName,
                                          to_wei_asset(actualTokenAmountIn/math.pow(10, tokenDecimals[tokenInIndex]), tokenIn, tokenDecimals[tokenInIndex]),
                                          to_wei_asset(tokenOutAmount, tokenOut, tokenDecimals[tokenOutIndex]),
                                          spotPriceAfter)
        assert "ERR_NOT_BOUND" in tx["error"]["details"][0]["message"]
        time.sleep(3)
        poolInfo2 = self.getPoolInfo(poolName, admin)
        mylogger.info(f"交易后, 池子{poolName}的信息: {poolInfo2}")
        userBalance2 = self.getAccountBalance(user, tokenNames)
        mylogger.info(f"交易后, 用户{user}持有的资产: {userBalance2}")
        userSupply2 = self.getAccountSupply(user, admin, poolName)
        mylogger.info(f"交易后, 用户{user}持有的lp: {userSupply2}")
        totalSupply2 = self.getPoolSupply(poolName, admin)[0]["parseSupply"]
        mylogger.info("交易后, 池子中总的lp为: {}".format(totalSupply2))

        # 检查池子中的lp计算正确
        assert totalSupply2 == totalSupply, "交易时，池子的lp应不变"
        # 检查用户持有的lp
        assert userSupply2 == userSupply, "用户交易lp不正确"
        # 检查池子资产中记录的balance和weight正确
        for index, tokenBalnce in enumerate(balances):
            afterBalance = int(poolInfo2["pools"]['records'][index]["value"]["balance"])
            if index == tokenInIndex:
                # 检查池子资产record是否正确
                assert afterBalance - balances[index] == 0, "池子{}的资产变化不正确".format(tokenIn)
                # 检查用户持有的资产变化
                assert userBalance2[tokenNames[index]]["parseBalance"] + 0 == \
                       userBalance[tokenNames[index]]["parseBalance"]
            elif index == tokenOutIndex:
                assert afterBalance + 0 == balances[index], "池子{}的资产变化不正确".format(tokenOut)
                # 检查用户持有的资产变化
                assert userBalance2[tokenNames[index]]["parseBalance"] - 0 == \
                       userBalance[tokenNames[index]]["parseBalance"]
            else:
                assert afterBalance == balances[tokenInIndex], "池子其他token的资产应保持不变"
            # 检查池子的denorm是否正确
            assert poolInfo2["pools"]['records'][index]["value"]["denorm"] == weights[index]
        # 检查池子实际持有的token资产和record的资产是否一致
        self.checkPoolBalance(poolName)


if __name__ == "__main__":
    # newPool = "btc2usdtes11"
    # newPool = "btc2usdtest5"
    # newPool = "btc2usdtest1"
    # newPool = "btc2usdtlml1"
    # newPool = "btc2usdtlml2"
    # newPool = "btc2usdtlml3"
    # newPool = "btc2usdtlml4"
    # newPool = "btc2usdtlml5"
    newPool = "btc2usdtlm11"
    # newPool = "lml111111111"
    # newPool = "btc2usdt1215"
    poolKey = "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH"
    bTest = BalancerEosTest()
    bTest.getEthRpcNode()

    # eosrpc.import_keys(keys)
    # # 创建账户
    # newAccount(newPool, poolKey, poolKey, avaKeys)
    # newAccount(admin, acc2pub_keys[admin], acc2pub_keys[admin], avaKeys)

    # # 部署合约
    # print(w.list())
    # print(w.get_public_keys())
    # deployBalancerContract(admin, [acc2pub_keys[admin]])
    # deployBalancerContract(admin, [acc2pub_keys[admin]])
    # deployBalancerContract(admin, avaKeys)

    # allowDosContract(admin, acc2pub_keys[admin])
    # allowDosContract(newPool, poolKey)

    # allowDosContracts()
    # 创建token
    # newToken("TBTC", 8)
    # newToken("TUSDT", 6)
    # newToken("TUSDC", 6)

    # newToken("TEN", 10)

    # bTest.swapClient.extransfer(user1, nonadmin, to_wei_asset(2100000, "TUSDT", 6), "")
    # 铸币
    # allowDosContract(tokenissuer, acc2pub_keys[tokenissuer])
    # mint(nonadmin, to_wei_asset(10, "TBTC", 8))
    # mint(user1, to_wei_asset(10, "TBTC", 8))
    # mint(user1, to_wei_asset(2100000, "TUSDT", 6))
    # mint(nonadmin, to_wei_asset(10000000, "TUSDT", 6))
    # mint(nonadmin, to_wei_asset(200000, "TEN", 10))
    # mint(nonadmin, to_wei_asset(200000, "TUSDC", 6))

    # print(bTest.getPoolInfo(newPool, admin))
    # print(bTest.getPoolSupply(newPool, admin)) # 'max_supply': '10000 00000.000000 BPT' init 100000 最大 10000
    # print(bTest.getPoolSupply(nonadmin, admin))
    # print(bTest.getAccountSupply(nonadmin, admin, newPool))
    # print(bTest.getAccountSupply(admin, admin, newPool))
    print(bTest.getAccountBalance(newPool, ["BTC", "USD"], "roxe.ro"))
    print(bTest.getAccountBalance(nonadmin, ["BTC", "USD"], "roxe.ro"))
    print(bTest.getAccountBalance(user1, ["BTC", "USD"], "roxe.ro"))
    print(bTest.getAccountBalance(user2, ["BTC", "USD"], "roxe.ro"))
    # print(bTest.getAccountBalance(newPool, ["TBTC", "TUSDT", "TUSDC"]))
    # print(bTest.getAccountBalance(nonadmin, ["TBTC", "TUSDT", "TUSDC"]))
    # print(bTest.getAccountBalance(user1, ["TBTC", "TUSDT", "TUSDC"]))
    # print(to_wei_asset(20999.7961, "TBTC", 8))
    # bTest.swapClient.extransfer(user1, nonadmin, to_wei_asset(20999.7961, "TBTC", 8), "")
    # client.allowDosContract(nonadmin, acc2pub_keys[nonadmin])
    # bTest.swapClient.transferex(nonadmin, user1, to_wei_asset(10, "BTC", 8, "roxe.ro"), "")
    # bTest.swapClient.extransfer(nonadmin, user1, to_wei_asset(19957, "TBTC", 8), "")
    # bTest.swapClient.extransfer(user1, nonadmin, to_wei_asset(20998, "TBTC", 8), "")
    # print(bTest.getAccountBalance(nonadmin, ["BTC", "USD"], "roxe.ro"))

    # bTest.checkNewPoolWithNonAdminAccount(nonadmin, newPool)
    # bTest.checkNewPoolSuccess(newPool)
    # bTest.checkNewPoolWhenPoolAlreadyExist(newPool)

    # bTest.checkSetSwapFeeFeeIs0(newPool)
    # bTest.checkSetSwapFeeMsgSenderIsNotPoolController(newPool)
    # bTest.checkSetSwapFeeFeeExceedMaxFee(newPool)
    # bTest.checkSetSwapFeePass(newPool, int(0.001 * 1000000000))

    # bTest.checkSetPublicSwapValueIsTrue(newPool)
    # bTest.checkSetPublicSwapValueIsFalse(newPool)
    # bTest.checkSetPublicSwapMsgSenderIsNotController(newPool)

    # bTest.checkSetControllerWhenPoolIsNotFinalized(newPool, nonadmin)
    # bTest.checkSetControllerWhenPoolIsNotFinalized(newPool, admin)
    # bTest.checkSetControllerWhenPoolIsFinalized(newPool, nonadmin)

    # allowDosContract(newPool, poolKey)
    # allowDosContract(nonadmin, acc2pub_keys[nonadmin])

    # bTest.checkBindTokenWhenDenormLessThanMinWeight(newPool, "TBTC", 0.001, 8)
    # bTest.checkBindTokenWhenDenormMoreThanMaxWeight(newPool, "TBTC", 0.001, 8)
    # bTest.checkBindTokenWhenBalanceLessThanMinBalance(newPool, "TBTC", 0.00001, 8)

    # bTest.checkBindTokenWhenTokenDecimalMoreThanContract(newPool, "TEN", 0.0001, 10, to_wei(1, 9))
    # bTest.checkBindToken(newPool, "TBTC", 1, 8, to_wei(1, 9))
    # bTest.checkRebindToken(newPool, "TBTC", 10, 8, to_wei(1, 9)) # 10000000000
    # bTest.checkBindToken(newPool, "BTC", 10, 8, to_wei(1, 9), 'roxe.ro')
    # bTest.checkRebindToken(newPool, "BTC", 20, 8, to_wei(2, 9), 'roxe.ro')
    # bTest.checkRebindToken(newPool, "BTC", 1, 8, to_wei(2, 9), 'roxe.ro')
    # bTest.checkRebindToken(newPool, "BTC", 0.5, 8, to_wei(2, 9), 'roxe.ro')
    # bTest.checkRebindToken(newPool, "BTC", 0.1, 8, to_wei(2, 9), 'roxe.ro')
    # bTest.checkUnbindToken(newPool, "BTC", 8, 'roxe.ro')
    # bTest.checkBindToken(newPool, "USD", 341500, 6, to_wei(1, 9), 'roxe.ro')
    # bTest.checkBindTokenWhenTokenAlreadyBinded(newPool, "TBTC", 1, 8, to_wei(1, 9))
    # bTest.checkBindTokenWhenDenormMoreThanMaxWeight(newPool, "TUSDT", 1.9177, 6, to_wei(49, 9) + 1)
    # bTest.checkBindToken(newPool, "TUSDT", 329000, 6, to_wei(1, 9))
    # bTest.checkBindToken(newPool, "TUSDC", 10, 4, to_wei(1, 9))

    # 以最小资产bind， 测试lp的上限
    # bTest.checkBindToken(newPool, "TBTC", 0.0001, 8, to_wei(1, 4))
    # bTest.checkBindToken(newPool, "TUSDT", 2.295842, 6, to_wei(1, 4))

    # bTest.checkFinalizedWhenbindTokensOnlyHaveOne(newPool)
    # bTest.checkFinalized(newPool)
    # bTest.checkFinalizedWhenPoolAlreadyFinalized(newPool)

    # bTest.checkSetSwapFeeAfterFinalized(newPool)
    # bTest.checkSetPublicSwapAfterFinalized(newPool, True)

    # bTest.checkPoolBalance(newPool)
    # bTest.checkJoinPoolWhenJoinLpMoreThanPoolMaxSupply(newPool, nonadmin)

    # bTest.checkJoinPoolWhenJoinAmountIs0(newPool)
    # bTest.checkJoinPoolWhenJoinAmountMoreThanUserAmount(newPool, 1, user1)
    # bTest.checkJoinPool(newPool, 1, nonadmin)
    # bTest.checkJoinPool(newPool, 0.0002, nonadmin)
    # bTest.checkJoinPool(newPool, 0.001, user2)
    # bTest.checkJoinPoolWhenJoinAmountsMoreThanRequireAmount(newPool, 0.001, user1)
    # bTest.checkJoinPoolWhenJoinAmountsLessThanRequireAmount(newPool, 0.001, user1)

    # bTest.checkExitPool(newPool, 0)
    # bTest.checkExitPoolWhenExitAmountsLessThanRequireAmount(newPool, 0.01, user1)
    # bTest.checkExitPoolWhenExitAmountMoreThanUserAmount(newPool, user1)
    # bTest.checkExitPoolWhenExitLpIs0(newPool, nonadmin)
    # bTest.checkExitPoolWhenUserLpIs0(newPool, user1)
    # bTest.checkExitPool(newPool, 1, user1)
    # bTest.checkExitPool(newPool, 0.5)
    # bTest.checkExitPool(newPool, 1)
    # parsePrintJson(c.getAccount(user1))

    # bTest.checkSwapAmountIn(newPool, "TBTC", 0.00000001, "TUSDT", user1) # 有可能失败，pool认为价格不合适
    # bTest.checkSwapAmountInWhentokenIsNotBoundInPool(newPool, "TBTC", 0.001, "TUSDC", user1)
    # bTest.checkSwapAmountInWhentokenIsNotBoundInPool(newPool, "TUSDC", 0.001, "TUSDT", user1)
    # bTest.checkSwapAmountIn(newPool, "TBTC", 0.00001, "TUSDT", user1)
    # bTest.checkSwapAmountIn(newPool, "BTC", 0.00001, "USD", user1, "roxe.ro")
    # bTest.checkSwapAmountIn(newPool, "BTC", 0.0001, "USD", user1, "roxe.ro")
    # bTest.checkSwapAmountIn(newPool, "BTC", 0.001, "USD", user1, "roxe.ro")
    # bTest.checkSwapAmountIn(newPool, "BTC", 0.03, "USD", user1, "roxe.ro")
    # bTest.checkSwapAmountIn(newPool, "BTC", 0.1, "USD", user1, "roxe.ro")
    # bTest.checkSwapAmountIn(newPool, "BTC", 1, "USD", user1, "roxe.ro")
    # bTest.checkSwapAmountIn(newPool, "BTC", 0.12345678, "USD", user1, "roxe.ro")
    # bTest.checkSwapAmountIn(newPool, "TBTC", 0.0001, "TUSDT", user1)
    # bTest.checkSwapAmountIn(newPool, "TBTC", 0.001, "TUSDT", user1)
    # bTest.checkSwapAmountIn(newPool, "TBTC", 0.01, "TUSDT", user1)
    # bTest.checkSwapAmountIn(newPool, "TBTC", 0.1, "TUSDT", user1)
    # bTest.checkSwapAmountIn(newPool, "TBTC", 1, "TUSDT", user1)
    # bTest.checkSwapAmountIn(newPool, "TUSDT", 10, "TBTC", user1)
    # bTest.checkSwapAmountIn(newPool, "TUSDT", 100, "TBTC", user1)
    # bTest.checkSwapAmountIn(newPool, "TUSDT", 1000, "TBTC", user1)
    # bTest.checkSwapAmountIn(newPool, "TUSDT", 10000, "TBTC", user1)
    # bTest.checkSwapAmountIn(newPool, "TBTC", 1, "TUSDT", user1)
    # bTest.checkSwapAmountIn(newPool, "TBTC", 5, "TUSDT", user1)
    # bTest.checkSwapAmountInWhenAmountInMoreThanLimit(newPool, "TBTC", "TUSDT", user1)
    # bTest.checkSwapAmountOut(newPool, "BTC", 0.00001, "USD", user1)
    # bTest.checkSwapAmountOut(newPool, "BTC", 0.0001, "USD", user1)
    # bTest.checkSwapAmountOut(newPool, "BTC", 0.001, "USD", user1)
    # bTest.checkSwapAmountOut(newPool, "BTC", 0.01, "USD", user1)
    # bTest.checkSwapAmountOut(newPool, "BTC", 0.1, "USD", user1)
    # bTest.checkSwapAmountOut(newPool, "BTC", 1, "USD", user1)
    # bTest.checkSwapAmountOut(newPool, "BTC", 0.12345678, "USD", user1)
    # bTest.checkSwapAmountOut(newPool, "TBTC", 0.00001, "TUSDT", user1)
    # bTest.checkSwapAmountOut(newPool, "TBTC", 0.0001, "TUSDT", user1)
    # bTest.checkSwapAmountOut(newPool, "TBTC", 0.001, "TUSDT", user1)
    # bTest.checkSwapAmountOut(newPool, "TBTC", 0.01, "TUSDT", user1)
    # bTest.checkSwapAmountOut(newPool, "TBTC", 0.1, "TUSDT", user1)
    # bTest.checkSwapAmountOut(newPool, "TBTC", 1, "TUSDT", user1)
    # bTest.checkSwapAmountOut(newPool, "TUSDT", 1000, "TBTC", user1) # 有可能失败，pool认为价格不合适
    # bTest.checkSwapAmountOut(newPool, "TUSDT", 34237, "TBTC", user1) # 有可能失败，pool认为价格不合适
    # bTest.checkSwapAmountOutWhenAmountOutMoreThanLimit(newPool, "TBTC", "TUSDT", user1)
    # bTest.checkSwapAmountOutWhenTokenNotBoundInPool(newPool, "TBTC", 0.001, "TUSDC", user1)
    # bTest.checkSwapAmountOutWhenTokenNotBoundInPool(newPool, "TUSDC", 0.001, "TUSDT", user1)
    # bTest.checkSwapAmountOutWhenTokenNotBoundInPool(newPool, "TUSDT", 0.001, "TUSDC", user1)

    # bTest.swapClient.gulp(nonadmin, newPool, to_sym("BTC", 8, 'roxe.ro'))
    # bTest.swapClient.gulp(nonadmin, newPool, to_sym("USD", 8, 'roxe.ro'))
    # bTest.swapClient.gulp(nonadmin, newPool, to_sym("TBTC", 8, 'roxearntoken'))

    # parsePrintJson(c.getAccount(newPool))
    # parsePrintJson(c.getAccount(user1))
