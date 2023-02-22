# -*- coding: utf-8 -*-
import json
import datetime
from dotenv import load_dotenv
import random
import os
import time
import subprocess
import traceback
from SmartContract.DODO.chain import ChainClient
from SmartContract.DODO.wallet import WalletClient
from SmartContract.DODO.common import *
from roxe_libs.pub_function import setCustomLogger


decimals = int(math.pow(10, 6))
curPath = os.path.dirname(os.path.abspath(__file__))
logger = setCustomLogger("dodo", curPath + "/dodo3.log", isprintsreen=True, logfilemod='a')

# 加载.env文件中变量到系统环境变量
load_dotenv()
rpcNode = "http://172.17.3.161:7878/v1/chain"
walletNode = "http://10.100.1.10:8889/v1/wallet"

interval = os.getenv("FREQ")
owner = os.getenv("ADMIN")
# dosContract = os.getenv("DOS_CONTRACT")

bp = "roxe1"
lp = "alice1111111"
trader = "bob111111111"
hexuser = "carol1111111"
# admin = "eosdoseosdos" # 4位精度
# admin = "roxeearn1213" # 6位精度
# admin = "roxeearn1211" # 6位精度
# admin = "roxeliml1211" # 6位精度
# admin = "roxeliml1222" # 1229号版本
# admin = "roxeliml1223" # 1229号21点30版本
# admin = "roxeliml1224" # 1229号21点30版本
# admin = "roxeliml1125" # 1229号21点30版本
# admin = "roxeliml1225" # 1229号21点30版本
# admin = "roxeliml1131" # 0130
# admin = "roxeliml1132" # 0130
# admin = "roxeliml1133" # 0130
admin = "roxe.earn" #

dosContract = admin

# admin = "roxeearntest"

# tokenowner = "eosdosxtoken"
tokenowner = "roxearntoken"
tokenissuer = "tokenissuer1"
maintainer = "maintainer11"
oracleadmin = "orc.polygon"
doowner = admin
dodo_ethbase_name = "ethbasemkr11"
dodo_ethquote_name = "ethquotemkr1"
# dodo_stablecoin_name = "dai2mkr11111"
# dodo_stablecoin_name = "usd2gbptest2"
# dodo_stablecoin_name = "testa2testb5"
dodo_stablecoin_name = "tb2tc222222d"
# admin_pub = "ROXE6m2TpGWE59yDPWuBaB3xSJSgYWkggzSTuDv5vLfS3hYzB6UTU2"
admin_pub = "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH"
tokenowner_pub = "ROXE5rM2nqtmCqyeRMpmQQMVTMYYZ9VYq9JDgve4t3Gzy6gVU1wB1z"
pub = "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH"
trader_pub = "ROXE6bYcFRBBLugKtxfkNxnyyrxUFV2LMGT3h9GcDisd6QYUyt2xfX"

acc2pub_keys = {
    "roxe1": "ROXE6m2TpGWE59yDPWuBaB3xSJSgYWkggzSTuDv5vLfS3hYzB6UTU2",
    "roxeearn1213": "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH",
    "roxeearntest": "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH",
    "roxeliml1211": "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH",
    "roxeliml1222": "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH",
    "roxeliml1223": "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH",
    admin: "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH",
    oracleadmin: "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH",
    "roxeswap1213": "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH",
    "roxearntoken": "ROXE5rM2nqtmCqyeRMpmQQMVTMYYZ9VYq9JDgve4t3Gzy6gVU1wB1z",
    "eosdoseosdos": "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH",
    "eosdosxtoken": "ROXE5rM2nqtmCqyeRMpmQQMVTMYYZ9VYq9JDgve4t3Gzy6gVU1wB1z",
    "eosdosoracle": "ROXE5rM2nqtmCqyeRMpmQQMVTMYYZ9VYq9JDgve4t3Gzy6gVU1wB1z",
    "ethbasemkr11": "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH",
    "ethquotemkr1": "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH",
    "daimkrdaimkr": "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH",
    "dai2mkr11111": "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH",
    "tokenissuer1": "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH",
    "maintainer11": "ROXE6m2TpGWE59yDPWuBaB3xSJSgYWkggzSTuDv5vLfS3hYzB6UTU2",
    "alice1111111": "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH",
    "bob111111111": "ROXE6bYcFRBBLugKtxfkNxnyyrxUFV2LMGT3h9GcDisd6QYUyt2xfX",
    "carol1111111": "ROXE6bYcFRBBLugKtxfkNxnyyrxUFV2LMGT3h9GcDisd6QYUyt2xfX",
    "tea2tebtest3": "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH",
    "eosdosnewdec": "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH",
    "ta2tc2222222": "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH",
}

keys = [
    os.getenv("EOS_KEY"),
    "5JZDFmwRwxJU2j1fugGtLLaNp2bcAP2PKy5zsqNkhn47v3S3e5w",
    "5JxT1aA8MiZZe7XjN3SYaQ65NSbZXrBcjePaSwRifK7jJLdjSf3",
    "5JHFTcGiKFDXFR64voMJXnxWZUqBgaEAnqMiyjJzBLQn9tHhWA8",
    "5HwYSQMW2Xy37Q9nhdKz7T32eLxwbDq29rMzGXrRQJwveh9B7sG",
    "5J6BA1U4QdQPwkFWsphU96oBusvsA8V2UJDtMtKgNneakBK9YrN",
]

avaKeys = [
  'PUB_K1_6MRyAjQq8ud7hVNYcfnVPJqcVpscN5So8BhtHuGYqET5BoDq63',
  'PUB_K1_6m2TpGWE59yDPWuBaB3xSJSgYWkggzSTuDv5vLfS3hYz86U7Ws',
  'PUB_K1_5rM2nqtmCqyeRMpmQQMVTMYYZ9VYq9JDgve4t3Gzy6gVUJvhr5',
  'PUB_K1_6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHqhqhA',
  'PUB_K1_8Av6ToXNYrGNdiQtpdUAG8LBDoMM3RZnin5NYpHk4WdKveS78Y',
  'PUB_K1_6bYcFRBBLugKtxfkNxnyyrxUFV2LMGT3h9GcDisd6QYV3YdSod'
]


def to_max_supply(sym, value=100000000000, d=4):
    q = to_wei_asset(value, sym, d)
    return q


def get_core_symbol():
    return {"symbol": "4,ROC", "contract": "roxe.token"}


def to_sym(sym, d=4, contract='roxearntoken'):
    # return {"symbol": f"{d}," + sym, "contract": contract}
    return {"symbol": f"{d}," + sym, "contract": "roxe.ro"}


def tounit(value):
    return todecimal(scalar_decimals(value))


def todecimal(value, d=4):
    tmp = str(round(int(value) / int(math.pow(10, d)), d))
    tmp = '{:.10f}'.format(float(tmp))
    # tmp = ''.join(tmp[0::(10-d)])
    float_num = tmp.split('.')[-1]
    # print(tmp, float_num)

    if len(float_num) < d:
        for i in range(d - len(float_num)):
            tmp += "0"
    elif len(float_num) > d:
        tmp = tmp[0:-(len(float_num) - d)]
    return tmp + " "


def scalar_decimals(value, d=4):
    dNumber = int(math.pow(10, d))
    # print(int(value * int(dNumber)))
    return int(value * int(dNumber))


def to_core_asset(value, sym):
    return {"quantity": tounit(value) + sym, "contract": "roxe.token"}


def to_asset(value, sym, d=4, contract='roxearntoken'):
    # print(todecimal(value, d))
    # return {"quantity": todecimal(value, d) + sym, "contract": "roxearntoken"}
    return {"quantity": todecimal(value, d) + sym, "contract": contract}
    # return {"quantity": todecimal(value, d) + sym, "contract": "roxe.ro"}
    # return {"quantity": todecimal(value, d) + sym, "contract": "eosdosxtoken"}


def to_wei_asset(value, sym, d=4, contract='roxearntoken'):
    # print(scalar_decimals(value, d))
    return to_asset(scalar_decimals(value, d), sym, d, contract)
    # return to_asset(scalar_decimals(value, d), sym, d, "roxe.ro")


def parsePrintJson(dic):
    js = json.dumps(dic, indent=4, separators=(',', ':'))
    print(js)


def require_permissions(account, key, actor, parent):
    res = {"account": account, "permission": "active", "parent": parent,
           "auth": {"threshold": 1,
                    "keys": [{"key": key, "weight": 1}],
                    "accounts": [{"permission": {"actor": actor, "permission": "roxe.code"}, "weight": 1}],
                    "waits": []
                    }
           }
    return res


def allowContract(auth, key, contract, parent=None):
    splitInfo = auth.split("@")
    account = splitInfo[0]
    permission = splitInfo[1] if len(splitInfo) > 1 else "active"
    parent = parent if parent else "owner"
    logger.debug(f"account: {account}")
    logger.debug(f"permission: {permission}")
    logger.debug(f"parent: {parent}")

    pub_keys = [key]
    tx_data = {"actions": [{
        "account": "roxe",
        "name": "updateauth",
        "authorization": [{"actor": account, "permission": permission}],
        "data": require_permissions(account, key, contract, parent)
    }], "pub_keys": pub_keys}

    logger.info(tx_data)
    return tx_data


def pushAction(account, key, action, data):
    permission = "active"
    pub_keys = [key]
    tx_data = {
        "actions": [{
            "account": dosContract,
            "name": action,
            "authorization": [{"actor": account, "permission": permission}],
            "data": data
        }],
        "pub_keys": pub_keys
    }
    # print(tx_data)
    logger.info("发送的交易数据: {}".format(tx_data))
    return tx_data


def pushTransaction(account, action, data):
    results = eosrpc.transaction(pushAction(account, acc2pub_keys[account], action, data))
    return results


def deployContract(userName, pub_keys):
    # wasmFilePath = "/Users/admin/js/RoxeChainTest/test/roxetest/src/wasms/roxe.token/roxe.token.wasm"
    # wasmFilePath = curPath + "/contracts/1209/eosdos/eosdos.wasm"
    wasmFilePath = curPath + "/contracts/1229/eosdos/eosdos.wasm"
    import binascii
    with open(wasmFilePath, "rb") as f:
        info = f.read()
        wasmHexString = binascii.hexlify(info).decode('utf-8')
        # info = str(info, encoding="hex")
    # print(wasmHexString)
    with open(curPath + "/contracts/1229/eosdos/newDoDo.compile", "r") as f:
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
    logger.info("deploy {}".format(userName))
    # logger.info(f"bin: {results[0]}")
    # logger.info(f"sig: {results[1]}")
    logger.info(f"action: {results}")


def newAccount(accountName, owner_publicKey, active_publicKey, pub_keys):
    tx_data = {
        "actions": [
            {
                "account": "roxe",
                "name": "newaccount",
                "authorization": [{"actor": "roxe1", "permission": "active"}],
                "data": {
                    "creator": "roxe1",
                    "name": accountName,
                    "owner": {
                        "threshold": 1,
                        "keys": [{"key": owner_publicKey, "weight": 1}],
                        "accounts": [],
                        "waits": [],
                    },
                    "active": {
                        "threshold": 1,
                        "keys": [{"key": active_publicKey, "weight": 1}],
                        "accounts": [],
                        "waits": [],
                    }
                }
            },
            {
                "account": "roxe",
                "name": "buyrambytes",
                "authorization":  [{"actor": "roxe1", "permission": "active"}],
                "data": {"payer": "roxe1", "receiver": accountName, "bytes": 8192000}
            },
            {
                "account": "roxe",
                "name": "delegatebw",
                "authorization": [{"actor": "roxe1", "permission": "active"}],
                "data": {
                    "from": "roxe1",
                    "receiver": accountName,
                    "stake_net_quantity": "10000.0000 ROC",
                    "stake_cpu_quantity": "10000.0000 ROC",
                    "transfer": False
                }
            }
        ],
        "pub_keys": pub_keys
    }
    results = eosrpc.transaction(tx_data)
    logger.info("newAccount {}".format(accountName))
    # logger.info(f"bin: {results[0]}")
    # logger.info(f"sig: {results[1]}")
    logger.info(f"action: {results}")


def assertEqualOnlyShowLog(a, b, msg=""):
    try:
        assert a == b, "{} {} != {} 不相等, 相差 {}".format(msg, a, b, a-b)
    except Exception as e:
        logger.error(e.args[0])
        # logger.error(e.args[0], exc_info=True)
        return True
    return False


def getFeeInfo(sym, code="roxe.ro"):
    info = c.getTableRows(sym, code, "stat")
    # logger.info("币种的配置信息: {}".format(info))
    return info


def get_transfer_fee(amount, sym, isIN=False, code="roxe.ro"):
    if code != "roxe.ro":
        return 0

    info = getFeeInfo(sym, code)
    percent_decimal = 1000000
    # fee_sym = "ROC" if info["rows"][0]["useroc"] == 0 else sym

    if isIN:
        fee_amount = (info["rows"][0]["fee"] * percent_decimal + amount * info["rows"][0]["percent"]) // (info["rows"][0]["percent"] + percent_decimal)
        # print(amount, info["rows"][0]["percent"], info["rows"][0]["fee"] * percent_decimal + amount * info["rows"][0]["percent"])
        # print(info["rows"][0]["percent"] + percent_decimal)
    else:
        fee_amount = info["rows"][0]["fee"] + amount * info["rows"][0]["percent"] // percent_decimal

    # print(fee_amount)
    if fee_amount < info["rows"][0]["minfee"]:
        fee_amount = info["rows"][0]["minfee"]

    if fee_amount > info["rows"][0]["maxfee"]:
        fee_amount = info["rows"][0]["maxfee"]

    return fee_amount


class EosRpc:

    def get_pwd(self, wallet_name):
        with open(curPath + "/._", "r") as f:
            pwdjson = json.load(f)
        return pwdjson[wallet_name]

    def create_wallet(self, name):
        res = w.create(name)
        logger.info(f"创建钱包: {res}")
        return res

    def create_default_wallet(self):
        res = self.create_wallet(w.default_wallet_name)
        return res

    def unlock_default_wallet(self):
        password = self.get_pwd(w.default_wallet_name)
        return w.unlock_wallet(w.default_wallet_name, password)

    def import_keys_by_wallet_name(self, private_keys, wallet_name, wallet_password):
        w.unlock_wallet(wallet_name, wallet_password)
        res = []
        for key in private_keys:
            res.append(w.import_key(wallet_name, key))
        return res

    def import_keys(self, keys):
        password = self.get_pwd(w.default_wallet_name)
        res = self.import_keys_by_wallet_name(keys, w.default_wallet_name, password)
        # print(res)
        return res

    def transaction(self, tx_data, useJs=True):
        if useJs:
            parseJson = json.dumps(tx_data).replace("'", '"')
            # print(parseJson)
            cmd1 = "ts-node test3.ts '{}'".format(parseJson)
            infos = subprocess.check_output(cmd1, shell=True, cwd="/Users/admin/js/RoxeChainTest/test/roxetest/src/dodo")
            split_info = infos.decode().split("\n")
            tx_res = "".join(split_info[5::])
            # print(split_info[5::])
            # print(tx_res)
            # print(json.loads(tx_res))
            # print(json.lo
            # ads(tx_res))
            if "json" in json.loads(tx_res):
                return json.loads(tx_res)["json"]
            else:
                return json.loads(tx_res)
        actions = tx_data["actions"]
        pub_keys = tx_data["pub_keys"]
        info = c.getInfo()
        ref_block_num = info["last_irreversible_block_num"]
        blockInfo = c.getBlock(ref_block_num)
        ref_block_prefix = blockInfo["ref_block_prefix"]
        expiration = datetime.datetime.strptime(blockInfo["timestamp"],
                                                "%Y-%m-%dT%H:%M:%S.%f").timestamp() * 1000 + 2 * 60 * 1000
        expiration = datetime.datetime.fromtimestamp(expiration / 1000).strftime("%Y-%m-%dT%H:%M:%S")
        # print(expiration)
        eosrpc.unlock_default_wallet()
        bin = dict()
        for a in actions:
            # print(a["data"])
            try:
                bin = c.abi_json_to_bin(a["account"], a["name"], a["data"])
                a["data"] = bin["binargs"]
            except Exception:
                print(bin)
            # print(a["data"])
        tx = {
            "ref_block_num": ref_block_num,
            "ref_block_prefix": ref_block_prefix,
            "expiration": expiration,
            "actions": actions,
            "signatures": [],
        }
        # print(tx)
        # print(pub_keys)
        res = c.get_required_keys(pub_keys, tx)
        # print(res)

        sig = w.wallet_sign_trx([tx, res["required_keys"], info["chain_id"]])
        try:
            sig["signatures"]
        except Exception:
            # print(res["required_keys"])
            print(sig)
        # print(sig)
        compression = "none"
        transaction_extensions = []
        context_free_actions = []

        transaction = {"expiration": expiration, "ref_block_num": ref_block_num, "ref_block_prefix": ref_block_prefix,
                       "context_free_actions": context_free_actions, "actions": actions,
                       "transaction_extensions": transaction_extensions}

        time.sleep(2)
        xAction = c.push_transaction(compression, transaction, sig["signatures"])
        if 'transaction_id' in xAction.keys():
            pass
            # logger.info(xAction)
        else:
            logger.error(xAction)

        return [bin, sig, xAction]


def queryBuyBaseToken(amount, storeInfo, dodo_name, oraclePrice):
    if "rows" in storeInfo:
        s_info = [i for i in storeInfo["rows"] if i["dodo"] == dodo_name]
        if len(s_info) == 0:
            logger.error(f"在stoeInfo中查询不到dodo: {dodo_name}")
        s_info = s_info[0]
    else:
        s_info = storeInfo
    newBaseTarget, newQuoteTarget = getExpectedTarget(s_info, oraclePrice)
    logger.info(f"newBaseTarget: {newBaseTarget}")
    logger.info(f"newQuoteTarget: {newQuoteTarget}")
    lpFeeBase = amount * s_info["dodos"]["_LP_FEE_RATE_"] // decimals
    mtFeeBase = amount * s_info["dodos"]["_MT_FEE_RATE_"] // decimals
    buyBaseAmount = amount + lpFeeBase + mtFeeBase
    contract = s_info["dodos"]["_BASE_TOKEN_"]["contract"]
    baseToken = s_info["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]

    logger.info(f"按base收费, lpFeeBase: {lpFeeBase}")
    logger.info(f"按base收费, mtFeeBase: {mtFeeBase}")
    logger.info(f"加上费用后购买的数量buyBaseAmount: {buyBaseAmount}")
    fee = get_transfer_fee(amount, baseToken, False, contract)
    logger.info(f"转账费用为: {fee}")
    buyBaseAmount += fee
    logger.info(f"buyBaseAmount加上转账费用为: {buyBaseAmount}")

    mtFee = get_transfer_fee(mtFeeBase, baseToken, True, contract)
    # mtFeeBase -= mtFee
    logger.info(f"mtFee的转账费用为: {mtFee}")
    logger.info(f"mtFee的实际转账数量为: {mtFeeBase - mtFee}")


    baseTokenSymbol = s_info["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
    baseTokenContract = s_info["dodos"]["_BASE_TOKEN_"]["contract"]
    transfer_fee = get_transfer_fee(amount, baseTokenSymbol, False, baseTokenContract)
    buyBaseAmount += transfer_fee

    logger.info("转账out数量为 {},转账费用: {}".format(amount, transfer_fee))
    logger.info(f"加上转账费用后购买的数量buyBaseAmount: {buyBaseAmount}")
    bBalance = int(s_info["dodos"]["_BASE_BALANCE_"])
    qBalance = int(s_info["dodos"]["_QUOTE_BALANCE_"])

    if s_info["dodos"]["_R_STATUS_"] == 0:
        payQuote = ROneBuyBaseToken(buyBaseAmount, newBaseTarget, oraclePrice, s_info["dodos"]["_K_"])
        newRStatus = 1
    elif s_info["dodos"]["_R_STATUS_"] == 1:
        payQuote = RAboveBuyBaseToken(buyBaseAmount, bBalance, newBaseTarget, oraclePrice, s_info["dodos"]["_K_"] * int(math.pow(10, 12)))
        newRStatus = 1
    elif s_info["dodos"]["_R_STATUS_"] == 2:
        backToOnePayQuote = newQuoteTarget - qBalance
        backToOneReceiveBase = bBalance - newBaseTarget
        # print(s_info["dodos"]["_BASE_BALANCE_"] - newBaseTarget)
        logger.info(f"backToOnePayQuote: {backToOnePayQuote}")
        logger.info(f"backToOneReceiveBase: {backToOneReceiveBase}")
        if buyBaseAmount < backToOneReceiveBase:
            payQuote = RBelowBuyBaseToken(buyBaseAmount, qBalance, newQuoteTarget, oraclePrice, s_info["dodos"]["_K_"] * int(math.pow(10, 12)))
            newRStatus = 2
        elif buyBaseAmount == backToOneReceiveBase:
            payQuote = backToOnePayQuote
            newRStatus = 0
        else:
            payQuote = backToOnePayQuote + ROneBuyBaseToken(buyBaseAmount - backToOneReceiveBase, newBaseTarget, oraclePrice, s_info["dodos"]["_K_"]* int(math.pow(10, 12)))
            newRStatus = 1
    logger.info(f"需要付出的quote资产, payQuote: {payQuote}")
    logger.info(f"after trade newRStatus: {newRStatus}")
    return payQuote, newRStatus, lpFeeBase, mtFeeBase, newBaseTarget, newQuoteTarget


def querySellBaseToken(amount, storeInfo, dodo_name, oraclePrice):
    if "rows" in storeInfo:
        s_info = [i for i in storeInfo["rows"] if i["dodo"] == dodo_name]
        if len(s_info) == 0:
            logger.error(f"在stoeInfo中查询不到dodo: {dodo_name}")
        s_info = s_info[0]
    else:
        s_info = storeInfo
    newBaseTarget, newQuoteTarget = getExpectedTarget(s_info, oraclePrice)
    logger.info(f"newBaseTarget: {newBaseTarget}")
    logger.info(f"newQuoteTarget: {newQuoteTarget}")
    sellBaseAmount = amount
    logger.info(f"sellBaseAmount: {sellBaseAmount}")

    if s_info["dodos"]["_R_STATUS_"] == 0:
        receiveQuote = ROneSellBaseToken(sellBaseAmount, newQuoteTarget, oraclePrice, s_info["dodos"]["_K_"] * int(math.pow(10, 12)))
        newRStatus = 2
    elif s_info["dodos"]["_R_STATUS_"] == 1:
        backToOnePayBase = newBaseTarget - int(s_info["dodos"]["_BASE_BALANCE_"])
        backToOneReceiveQuote = int(s_info["dodos"]["_QUOTE_BALANCE_"]) - newQuoteTarget
        logger.info(f"backToOnePayBase: {backToOnePayBase}")
        logger.info(f"backToOneReceiveQuote: {backToOneReceiveQuote}")

        if sellBaseAmount < backToOnePayBase:
            # case 2.1: R status do not change
            print(2.1)
            receiveQuote = RAboveSellBaseToken(sellBaseAmount, int(s_info["dodos"]["_BASE_BALANCE_"]), newBaseTarget, oraclePrice, s_info["dodos"]["_K_"] * int(math.pow(10, 12)))
            newRStatus = 1
            if receiveQuote > backToOneReceiveQuote:
                receiveQuote = backToOneReceiveQuote

        elif sellBaseAmount == backToOnePayBase:
            # case 2.2: R status changes to ONE
            print(2.2)
            receiveQuote = backToOneReceiveQuote
            newRStatus = 0
        else:
            # case 2.3: R status changes to BELOW_ONE
            print(2.3)
            receiveQuote = backToOneReceiveQuote + ROneSellBaseToken(SafeMath.sub(sellBaseAmount, backToOnePayBase), newQuoteTarget, oraclePrice, s_info["dodos"]["_K_"] * int(math.pow(10, 12)))
            newRStatus = 2

    else:
        # case 3: R<1
        receiveQuote = RBelowSellBaseToken(sellBaseAmount, int(s_info["dodos"]["_QUOTE_BALANCE_"]), newQuoteTarget, oraclePrice, s_info["dodos"]["_K_"] * int(math.pow(10, 12)))
        newRStatus = 2

    logger.info(f"with fee receiveQuote: {receiveQuote}")
    lpFeeQuote = DecimalMath.mul(receiveQuote, s_info["dodos"]["_LP_FEE_RATE_"] * int(math.pow(10, 12)));
    mtFeeQuote = DecimalMath.mul(receiveQuote, s_info["dodos"]["_MT_FEE_RATE_"] * int(math.pow(10, 12)));
    receiveQuote = receiveQuote - lpFeeQuote - mtFeeQuote

    quoteToken = s_info["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
    contract = s_info["dodos"]["_QUOTE_TOKEN_"]["contract"]
    # add transfer fee
    transfer_fee = get_transfer_fee(receiveQuote, quoteToken, False, contract)
    mtFee = get_transfer_fee(mtFeeQuote, quoteToken, True, contract)
    logger.info(f"transfer_fee: {transfer_fee}")
    logger.info(f"mt fee: {mtFee}")
    logger.info(f"after fee receiveQuote: {receiveQuote}")
    logger.info(f"after fee receiveQuote - transfer_fee: {receiveQuote - transfer_fee}")
    logger.info(f"lpFeeQuote: {lpFeeQuote}")
    logger.info(f"mtFeeQuote: {mtFeeQuote}, 减去转账费用为:{mtFeeQuote - mtFee}")
    logger.info(f"after trade newRStatus: {newRStatus}")
    return receiveQuote - transfer_fee, newRStatus, lpFeeQuote, mtFeeQuote, newBaseTarget, newQuoteTarget


def getTokenSupply(token, code="roxearntoken"):
    # print(token, code)
    res = c.getTableRows(token, code, "stat")
    # print(res)
    return res


def getTokenBalance(user, code="roxearntoken"):
    res = c.getTableRows(user, code, "accounts")
    # print(res)
    # logger.info("{}持有资产:{}".format(user, res))
    return res


def getTotalBaseCapital(baseToken, dodoName):
    # tokenInfo = getTokenSupply(baseToken, dodoName)
    tokenInfo = getTokenSupply(dodoName, admin)
    assert len(tokenInfo["rows"]) > 0, "查询不到{}的信息: {}".format(baseToken, tokenInfo)
    # totalSupply = tokenInfo["rows"][0]["supply"]
    totalSupply = [ i for i in tokenInfo["rows"] if i["supply"].split(" ")[-1] == baseToken][0]["supply"]
    # print(tokenInfo)
    # print(totalSupply)
    assert baseToken in totalSupply
    d = len(totalSupply.split(" ")[0].split(".")[-1])
    parseSupply = int(float(totalSupply.split(" ")[0]) * math.pow(10, d))
    # print(parseSupply)
    return parseSupply


def getTotalQuoteCapital(quoteToken, dodoName):
    # tokenInfo = getTokenSupply(quoteToken, dodoName)
    tokenInfo = getTokenSupply(dodoName, admin)
    # print(tokenInfo)
    assert len(tokenInfo["rows"]) > 0, "查询不到{}的信息: {}".format(quoteToken, tokenInfo)
    totalSupply = [ i for i in tokenInfo["rows"] if i["supply"].split(" ")[-1] == quoteToken][0]["supply"]
    assert quoteToken in totalSupply
    d = len(totalSupply.split(" ")[0].split(".")[-1])
    parseSupply = int(float(totalSupply.split(" ")[0]) * math.pow(10, d))
    return parseSupply


def getBaseCapitalBalanceOf(account, dodoName, baseToken):
    # balanceInfo = getTokenBalance(account, dodoName)
    balanceInfo = getTokenBalance(account, admin)
    # print(balanceInfo)
    balanceInfo = [i for i in balanceInfo["rows"] if baseToken in i["balance"]['quantity'] and dodoName == i['balance']['contract']]
    # print(balanceInfo)
    if len(balanceInfo) == 0:
        return 0
    # totalBalance = [i for i in balanceInfo if baseToken in i["balance"]]
    totalBalance = balanceInfo[0]["balance"]['quantity']
    assert baseToken in totalBalance
    d = len(totalBalance.split(" ")[0].split(".")[-1])
    parseBalance = int(float(totalBalance.split(" ")[0]) * math.pow(10, d))
    # print(parseSupply)
    return parseBalance


def getQuoteCapitalBalanceOf(account, dodoName, quoteToken):
    # balanceInfo = getTokenBalance(account, dodoName)
    balanceInfo = getTokenBalance(account, admin)
    balanceInfo = [i for i in balanceInfo["rows"] if quoteToken in i["balance"]['quantity'] and dodoName == i['balance']['contract']]
    # print(balanceInfo)
    if len(balanceInfo) == 0:
        return 0
    # totalBalance = [i for i in balanceInfo if quoteToken in i["balance"]]
    totalBalance = balanceInfo[0]["balance"]['quantity']
    assert quoteToken in totalBalance
    d = len(totalBalance.split(" ")[0].split(".")[-1])
    parseBalance = int(float(totalBalance.split(" ")[0]) * math.pow(10, d))
    # print(parseSupply)
    return parseBalance


def getWithdrawBasePenalty(amount, dodoInfo, price):
    assert amount <= int(dodoInfo["dodos"]["_BASE_BALANCE_"]), "DODO_BASE_BALANCE_NOT_ENOUGH"
    if dodoInfo["dodos"]["_R_STATUS_"] == 1:
        spareQuote = SafeMath.sub(int(dodoInfo["dodos"]["_QUOTE_BALANCE_"]), int(dodoInfo["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]))
        fairAmount = DecimalMath.divFloor(spareQuote, price)
        print(spareQuote, fairAmount)
        targetBase = DODOMath.solveQuadraticFunctionForTarget(
            int(dodoInfo["dodos"]["_BASE_BALANCE_"]), int(dodoInfo["dodos"]["_K_"]) * int(math.pow(10, 12)), fairAmount
        )
        targetBaseWithWithdraw = DODOMath.solveQuadraticFunctionForTarget(
            SafeMath.sub(int(dodoInfo["dodos"]["_BASE_BALANCE_"]), amount), int(dodoInfo["dodos"]["_K_"]) * int(math.pow(10, 12)), fairAmount
        )
        print(targetBase, targetBaseWithWithdraw, amount)
        return SafeMath.sub(targetBase, targetBaseWithWithdraw + amount)
    else:
        return 0


def getWithdrawQuotePenalty(amount, dodoInfo, price):
    assert amount <= int(dodoInfo["dodos"]["_QUOTE_BALANCE_"]), "DODO_QUOTE_BALANCE_NOT_ENOUGH"
    if dodoInfo["dodos"]["_R_STATUS_"] == 2:
        spareBase = SafeMath.sub(int(dodoInfo["dodos"]["_BASE_BALANCE_"]), int(dodoInfo["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]))
        fairAmount = DecimalMath.mul(spareBase, price)
        targetQuote = DODOMath.solveQuadraticFunctionForTarget(
            int(dodoInfo["dodos"]["_QUOTE_BALANCE_"]), int(dodoInfo["dodos"]["_K_"]), fairAmount
        )
        targetQuoteWithWithdraw = DODOMath.solveQuadraticFunctionForTarget(
            SafeMath.sub(int(dodoInfo["dodos"]["_QUOTE_BALANCE_"]), amount), int(dodoInfo["dodos"]["_K_"]), fairAmount
        )
        print(targetQuote, targetQuoteWithWithdraw + amount)
        return SafeMath.sub(targetQuote, targetQuoteWithWithdraw + amount)
    else:
        return 0


def getLpBaseBalance(user, baseToken, dodoName, storeInfo, price):
    totalBaseCapital = getTotalBaseCapital(baseToken, dodoName)
    print(totalBaseCapital)
    if totalBaseCapital == 0:
        return 0
    baseTarget, quoteTarget = getExpectedTarget(storeInfo, price)
    lpBalance = SafeMath.div(
        SafeMath.mul(getBaseCapitalBalanceOf(user, dodoName, baseToken), baseTarget),
        totalBaseCapital
    )
    return lpBalance


def getLpQuoteBalance(user, quoteToken, dodoName, storeInfo, price):
    totalQuoteCapital = getTotalQuoteCapital(quoteToken, dodoName)
    print(totalQuoteCapital)
    if totalQuoteCapital == 0:
        return 0
    baseTarget, quoteTarget = getExpectedTarget(storeInfo, price)
    lpBalance = SafeMath.div(
        SafeMath.mul(getQuoteCapitalBalanceOf(user, dodoName, quoteToken), quoteTarget),
        totalQuoteCapital
    )
    return lpBalance


class EosClient:

    def __init__(self, dodo_name):
        self.dodoName = dodo_name

    def create_wallet(self):
        results = eosrpc.create_default_wallet()
        logger.info(f"创建钱包: {results}")

    def import_keys(self):
        results = eosrpc.import_keys(keys)
        logger.info(f"导入钱包: {results}")

    def allowDosContract(self, user, pubk):
        results = eosrpc.transaction(allowContract(user, pubk, dosContract))
        # logger.info(f"allowDosContract bin: {results[0]}")
        # logger.info(f"allowDosContract sig: {results[1]}")
        logger.info(f"allowDosContract action: {results}")
        return results

    def allowDosContracts(self):
        # accounts = [k for k in acc2pub_keys.keys()]
        for acc, pubk in acc2pub_keys.items():
            self.allowDosContract(acc, pubk)

    def extransfer(self, acc):
        results = pushTransaction(bp, "extransfer", {"from": bp, "to": acc,
                                                     "quantity": to_core_asset(10000, "ROC"),
                                                     "memo": ""})
        # logger.info(f"{acc} bin : {results[0]}")
        # logger.info(f"{acc} sig : {results[1]}")
        logger.info(f"{acc} xAction : {results}")

    def extransfers(self):
        accounts = [k for k in acc2pub_keys.keys()]
        for acc in accounts:
            self.extransfer(acc)
            break

    def init(self, msg_sender, dodoZoo, weth, core_symbol):
        results = pushTransaction(msg_sender, "init", {
            "msg_sender": msg_sender,
            "dodoZoo": dodoZoo,
            "weth": weth,
            "core_symbol": core_symbol
        })
        # logger.info(f"init bin: {results[0]}")
        # logger.info(f"init sig: {results[1]}")
        logger.info(f"init action: {results}")

    def newtoken(self, msg_sender, token):
        results = pushTransaction(msg_sender, "newtoken", {
            "msg_sender": msg_sender,
            "token": token
        })
        # logger.info(f"newtoken bin: {results[0]}")
        # logger.info(f"newtoken sig: {results[1]}")
        logger.info(f"newtoken action: {results}")

    def mint(self, to, amount):
        results = pushTransaction(to, "mint", {
            "msg_sender": to,
            "amt": amount
        })
        # logger.info(f"mint to {to} bin: {results[0]}")
        # logger.info(f"mint to {to} sig: {results[1]}")
        logger.info(f"mint to {to} action: {results}")

    def neworacle(self, msg_sender, token):
        results = pushTransaction(msg_sender, "neworacle", {
            "msg_sender": msg_sender,
            "token": token
        })
        # logger.info(f"neworacle bin: {results[0]}")
        # logger.info(f"neworacle sig: {results[1]}")
        logger.info(f"neworacle action: {results}")

    def setprice(self, msg_sender, basetoken, quotetoken):
        results = pushTransaction(msg_sender, "setprice", {
            "msg_sender": msg_sender,
            "basetoken": basetoken,
            "quotetoken": quotetoken
        })
        logger.info(f"setprice {basetoken}, {quotetoken}")
        # logger.info(f"bin: {results[0]}")
        # logger.info(f"sig: {results[1]}")
        logger.info(f"action: {results}")
        return results

    def setparameter(self, msg_sender, dodo_name, para_name, para_value):
        results = pushTransaction(msg_sender, "setparameter", {
            "msg_sender": msg_sender,
            "dodo_name": dodo_name,
            "para_name": para_name,
            "para_value": para_value
        })
        logger.info(f"setparameter: {para_name} {para_value}")
        # logger.info(f"bin: {results[0]}")
        # logger.info(f"sig: {results[1]}")
        logger.info(f"results: {results}")
        return results

    def enablex(self, msg_sender, dodo_name, action_name):
        results = pushTransaction(msg_sender, action_name, {
            "msg_sender": msg_sender,
            "dodo_name": dodo_name,
        })
        logger.info(f"enablex: {dodo_name} {action_name}")
        # logger.info(f"bin: {results[0]}")
        # logger.info(f"sig: {results[1]}")
        logger.info(f"action: {results}")
        return results

    def breeddodo(self, msg_sender, dodo_name, maintainer, baseToken, quoteToken, oracle, lpFeeRate, mtFeeRate, k,
                  gasPriceLimit):
        results = pushTransaction(msg_sender, "breeddodo", {
            "msg_sender": msg_sender,
            "dodo_name": dodo_name,
            "maintainer": maintainer,
            "baseToken": baseToken,
            "quoteToken": quoteToken,
            "oracle": oracle,
            "lpFeeRate": lpFeeRate,
            "mtFeeRate": mtFeeRate,
            "k": k,
            "gasPriceLimit": gasPriceLimit
        })
        logger.info(f"breeddodo: {baseToken} {quoteToken}")
        # logger.info(f"bin: {results[0]}")
        # logger.info(f"sig: {results[1]}")
        logger.info(f"action: {results}")
        return results

    def withdrawbase(self, msg_sender, dodo_name, amt):
        results = pushTransaction(msg_sender, "withdrawbase", {
            "msg_sender": msg_sender,
            "dodo_name": dodo_name,
            "amt": amt
        })
        logger.info(f"withdrawbase: {dodo_name} {amt}")
        # logger.info(f"bin: {results[0]}")
        # logger.info(f"sig: {results[1]}")
        logger.info(f"action: {results}")
        return results

    def withdrawallbase(self, msg_sender, dodo_name):
        results = pushTransaction(msg_sender, "withdrawallb", {
            "msg_sender": msg_sender,
            "dodo_name": dodo_name,
        })
        logger.info(f"withdrawAllbase: {dodo_name}")
        # logger.info(f"bin: {results[0]}")
        # logger.info(f"sig: {results[1]}")
        logger.info(f"action: {results}")
        return results

    def withdrawquote(self, msg_sender, dodo_name, amt):
        results = pushTransaction(msg_sender, "withdrawquote", {
            "msg_sender": msg_sender,
            "dodo_name": dodo_name,
            "amt": amt
        })
        logger.info(f"withdrawbase: {dodo_name} {amt}")
        # logger.info(f"bin: {results[0]}")
        # logger.info(f"sig: {results[1]}")
        logger.info(f"action: {results}")
        return results

    def withdrawallquote(self, msg_sender, dodo_name):
        results = pushTransaction(msg_sender, "withdrawallq", {
            "msg_sender": msg_sender,
            "dodo_name": dodo_name,
        })
        logger.info(f"withdrawAllQuote: {dodo_name}")
        # logger.info(f"bin: {results[0]}")
        # logger.info(f"sig: {results[1]}")
        logger.info(f"action: {results}")
        return results

    def depositbase(self, msg_sender, dodo_name, amt):
        results = pushTransaction(msg_sender, "depositbase", {
            "msg_sender": msg_sender,
            "dodo_name": dodo_name,
            "amt": amt
        })
        logger.info(f"depositbase: {dodo_name} {amt}")
        # logger.info(f"bin: {results[0]}")
        # logger.info(f"sig: {results[1]}")
        logger.info(f"action: {results}")
        return results

    def depositquote(self, msg_sender, dodo_name, amt):
        results = pushTransaction(msg_sender, "depositquote", {
            "msg_sender": msg_sender,
            "dodo_name": dodo_name,
            "amt": amt
        })
        logger.info(f"depositbase: {dodo_name} {amt}")
        # logger.info(f"bin: {results[0]}")
        # logger.info(f"sig: {results[1]}")
        logger.info(f"action: {results}")
        return results

    def buybasetoken(self, msg_sender, dodo_name, amount, maxPayQuote):
        results = pushTransaction(msg_sender, "buybasetoken", {
            "msg_sender": msg_sender,
            "dodo_name": dodo_name,
            "amount": amount,
            "maxPayQuote": maxPayQuote
        })
        logger.info(f"buybasetoken: {dodo_name} {amount}")
        # logger.info(f"bin: {results[0]}")
        # logger.info(f"sig: {results[1]}")
        logger.info(f"action: {results}")
        if 'error' in results:
            logger.info(results["error"]["details"])
        return results

    def sellbasetoken(self, msg_sender, dodo_name, amount, minReceiveQuote):
        results = pushTransaction(msg_sender, "sellbastoken", {
            "msg_sender": msg_sender,
            "dodo_name": dodo_name,
            "amount": amount,
            "minReceiveQuote": minReceiveQuote
        })
        logger.info(f"sellbasetoken: {dodo_name} {amount}")
        # logger.info(f"bin: {results[0]}")
        # logger.info(f"sig: {results[1]}")
        logger.info(f"action: {results}")
        if 'error' in results:
            logger.info(results["error"]["details"])
        return results

    def sellquote(self, msg_sender, dodo_name, amount, minReceiveBase):
        results = pushTransaction(msg_sender, "sellquote", {
            "msg_sender": msg_sender,
            "dodo_name": dodo_name,
            "minReceiveBase": minReceiveBase,
            "amount": amount
        })
        logger.info(f"sellquote: {dodo_name} {amount}")
        # logger.info(f"bin: {results[0]}")
        # logger.info(f"sig: {results[1]}")
        logger.info(f"action: {results}")
        if 'error' in results:
            logger.info(results["error"]["details"])
        return results

    def removeDodo(self, msg_sender, dodo_name):
        results = pushTransaction(msg_sender, "removedodo", {
            "msg_sender": msg_sender,
            "_dodo": dodo_name,
        })
        logger.info(f"removedodo: {dodo_name}")
        # logger.info(f"bin: {results[0]}")
        # logger.info(f"sig: {results[1]}")
        logger.info(f"action: {results}")
        return results


class DODOTest:

    def __init__(self, dodoName):
        self.client = EosClient(dodoName)
        self.c = ChainClient(rpcNode)
        self.w = WalletClient(walletNode)

    def getDodoInfo(self, dodoName):
        table = "dodos"
        curTableInfo = self.c.getTableRows(admin, admin, table)
        print(curTableInfo)
        curDodo = [i for i in curTableInfo["rows"] if i["dodo"] == dodoName]
        logger.debug(f"获取 {admin} 的 {table}信息: {curTableInfo}")
        logger.info(f"获取dodo为 {dodoName} 的信息: {curDodo}")
        return curDodo[0]

    def checkCreatePool(self, dodoName, basestr, quotestr, d=4):
        logger.info("#######")
        logger.info("checkCreatePool....")
        msg_sender = admin
        maintainer = doowner
        baseToken = to_sym(basestr, d)
        quoteToken = to_sym(quotestr, d)
        oracle = to_sym(basestr, d)
        lpFeeRate = 595
        mtFeeRate = 105
        k = 100
        gasPriceLimit = 0
        print(baseToken, quoteToken)
        # 授权
        logger.info("进行授权操作。。")
        self.client.allowDosContract(msg_sender, acc2pub_keys[msg_sender])
        logger.info("开始创建Pool。。")
        tx_res = self.client.breeddodo(msg_sender, dodoName, maintainer, baseToken, quoteToken, oracle, lpFeeRate, mtFeeRate, k, gasPriceLimit)
        # print(tx_res)
        time.sleep(1)
        info = self.getDodoInfo(dodoName)
        assert info["dodos"]["_INITIALIZED_"] == 1
        assert info["dodos"]["initownable"]["_OWNER_"] == msg_sender
        assert info["dodos"]["_MAINTAINER_"] == maintainer
        assert info["dodos"]["_BASE_TOKEN_"] == baseToken
        assert info["dodos"]["_QUOTE_TOKEN_"] == quoteToken
        assert info["dodos"]["_ORACLE_"] == oracle
        assert info["dodos"]["_LP_FEE_RATE_"] == lpFeeRate
        assert info["dodos"]["_MT_FEE_RATE_"] == mtFeeRate
        assert info["dodos"]["_K_"] == k
        assert info["dodos"]["_GAS_PRICE_LIMIT_"] == gasPriceLimit
        assert info["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"] == 0
        assert info["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"] == 0
        assert info["dodos"]["_BASE_BALANCE_"] == 0
        assert info["dodos"]["_QUOTE_BALANCE_"] == 0
        assert info["dodos"]["_DEPOSIT_QUOTE_ALLOWED_"] == 0
        assert info["dodos"]["_DEPOSIT_BASE_ALLOWED_"] == 0
        assert info["dodos"]["_TRADE_ALLOWED_"] == 0

    def checkCreatePoolAlreadyExist(self, dodoName, basestr, quotestr):
        logger.info("#######")
        logger.info("checkCreatePoolAlreadyExist....")
        msg_sender = admin
        maintainer = doowner
        baseToken = to_sym(basestr)
        quoteToken = to_sym(quotestr)
        oracle = to_sym(basestr)
        lpFeeRate = 3
        mtFeeRate = 3
        k = 1000
        gasPriceLimit = 0
        dodoInfo = self.getDodoInfo(dodoName)
        tokens = []
        for t in ["_BASE_TOKEN_", "_QUOTE_TOKEN_"]:
            tokens.append(dodoInfo["dodos"][t]["symbol"].split(",")[-1])
        assert dodoInfo["dodo"] == dodoName, "查询到的dodo合约有误: {}".format(dodoInfo["dodo"])
        assert basestr in tokens
        assert quotestr in tokens
        # self.client.allowDosContract(msg_sender, acc2pub_keys[msg_sender])
        tx_res = self.client.breeddodo(msg_sender, dodoName, maintainer, baseToken, quoteToken, oracle,
                                       lpFeeRate, mtFeeRate, k, gasPriceLimit)

        error_msg = tx_res["error"]["details"][0]["message"]
        assert tx_res["code"] == 500, "交易应该失败"
        assert "DODO_REGISTERED" in error_msg, "报错信息有误: {}".format(error_msg)

    def checkEnableDepositeBase(self, dodoName):
        logger.info("checkEnableDepositeBase....")
        dodoInfo = self.getDodoInfo(dodoName)
        curStatus = dodoInfo["dodos"]["_DEPOSIT_BASE_ALLOWED_"]
        logger.info("当前状态: _DEPOSIT_BASE_ALLOWED_ {}".format(curStatus))
        tx_res = self.client.enablex(admin, dodoName, "enablebasdep")
        assert "transaction_id" in tx_res, "交易没有成功"
        dodoInfo2 = self.getDodoInfo(dodoName)
        logger.info("当前状态: _DEPOSIT_BASE_ALLOWED_ {}".format(dodoInfo2["dodos"]["_DEPOSIT_BASE_ALLOWED_"]))
        assert dodoInfo2["dodos"]["_DEPOSIT_BASE_ALLOWED_"] == 1, "设置权限后，状态不正确"

    def checkEnableDepositeQuote(self, dodoName):
        logger.info("checkEnableDepositeQuote....")
        dodoInfo = self.getDodoInfo(dodoName)
        curStatus = dodoInfo["dodos"]["_DEPOSIT_QUOTE_ALLOWED_"]
        logger.info("当前状态: _DEPOSIT_QUOTE_ALLOWED_ {}".format(curStatus))
        tx_res = self.client.enablex(admin, dodoName, "enablequodep")
        assert "transaction_id" in tx_res, "交易没有成功"
        dodoInfo2 = self.getDodoInfo(dodoName)
        logger.info("当前状态: _DEPOSIT_QUOTE_ALLOWED_ {}".format(dodoInfo2["dodos"]["_DEPOSIT_QUOTE_ALLOWED_"]))
        assert dodoInfo2["dodos"]["_DEPOSIT_QUOTE_ALLOWED_"] == 1, "设置权限后，状态不正确"

    def checkSetParameterExceptPass(self, dodoName):
        """

        :param dodoName: dodo name
        :return:

        检查setparameter方法正确设置k, lpfeerate, mtfeerate 参数
        """
        # 获取当前的poolInfo
        curDodo = self.getDodoInfo(dodoName)
        curParams = [curDodo['dodos']['_K_'], curDodo['dodos']['_LP_FEE_RATE_'], curDodo['dodos']['_MT_FEE_RATE_']]
        logger.info(f"当前 {dodoName} 的_K_为: {curDodo['dodos']['_K_']}")
        logger.info(f"当前 {dodoName} 的_LP_FEE_RATE_为: {curDodo['dodos']['_LP_FEE_RATE_']}")
        logger.info(f"当前 {dodoName} 的_MT_FEE_RATE_为: {curDodo['dodos']['_MT_FEE_RATE_']}")

        para_names = {"k": "_K_", "lpfeerate": "_LP_FEE_RATE_", "mtfeerate": "_MT_FEE_RATE_"}
        for setValues in [[1, 1, 0], [1, 0, 1], [100, 1, 1], curParams]:
            for i, p in enumerate(para_names.keys()):
                self.client.setparameter(admin, dodoName, p, setValues[i])
                time.sleep(2)
                curDodo = self.getDodoInfo(dodoName)
                assert curDodo["dodos"][para_names[p]] == setValues[i], f'设置{p}后，校验不正确: {setValues[i]} != {curDodo["dodos"][para_names[p]]}'
                logger.info(f'设置{p}后，校验正确: {setValues[i]} == {curDodo["dodos"][para_names[p]]}')

    def checkSetParameterKSetFail(self, dodoName):
        """

        :param dodoName: dodo name
        :return:

        检查setparameter方法设置k失败的情况
            - 1. k=0时，k设置失败
            - 2. k>=1时, k设置失败
        """
        # 获取当前的poolInfo
        beginDodoInfo = self.getDodoInfo(dodoName)
        curParams = [beginDodoInfo['dodos']['_K_'], beginDodoInfo['dodos']['_LP_FEE_RATE_'], beginDodoInfo['dodos']['_MT_FEE_RATE_']]
        logger.info(f"当前 {dodoName} 的_K_为: {beginDodoInfo['dodos']['_K_']}")
        logger.info(f"当前 {dodoName} 的_LP_FEE_RATE_为: {beginDodoInfo['dodos']['_LP_FEE_RATE_']}")
        logger.info(f"当前 {dodoName} 的_MT_FEE_RATE_为: {beginDodoInfo['dodos']['_MT_FEE_RATE_']}")

        para_names = {"k": "_K_", "lpfeerate": "_LP_FEE_RATE_", "mtfeerate": "_MT_FEE_RATE_"}

        # 设置K为0
        tx_res = self.client.setparameter(admin, dodoName, "k", 0)
        afterDodoInfo = self.getDodoInfo(dodoName)
        assert tx_res["code"] == 500, "设置k为0，交易应执行失败"
        assert "K=0" in tx_res["error"]["details"][0]["message"], \
            "设置k为0，错误信息校验失败:{}".format(tx_res["error"]["details"])
        logger.info(f'交易的错误信息: {tx_res["error"]["details"]}')
        assert afterDodoInfo["dodos"][para_names["k"]] == beginDodoInfo["dodos"][para_names["k"]], \
            f'设置k后，校验不正确: {beginDodoInfo["dodos"][para_names["k"]]} != {afterDodoInfo["dodos"][para_names["k"]]}'
        logger.info('k设置为0时，校验正确')
        # 设置k为1
        tx_res = self.client.setparameter(admin, dodoName, "k", DecimalMath.one)
        afterDodoInfo = self.getDodoInfo(dodoName)
        assert tx_res["code"] == 500, f"设置k为1: {DecimalMath.one}，交易应执行失败"
        assert "K>=1" in tx_res["error"]["details"][0]["message"], \
            "设置k为0，错误信息校验失败:{}".format(tx_res["error"]["details"])
        logger.info(f'交易的错误信息: {tx_res["error"]["details"]}')
        assert afterDodoInfo["dodos"][para_names["k"]] == beginDodoInfo["dodos"][para_names["k"]], \
            f'设置k后，校验不正确: {beginDodoInfo["dodos"][para_names["k"]]} != {afterDodoInfo["dodos"][para_names["k"]]}'

        logger.info('k设置为1时，校验正确')

    def checkSetParameterFeesSetFail(self, dodoName):
        """

        :param dodoName: dodo name
        :return:
        检查setparameter方法设置lpfeerate、 mtfeerate失败的情况
            - 1. lpfeerate、 mtfeerate均设为负数
            - 2. lpfeerate + mtfeerate >1 的情况
        """
        # 获取当前的poolInfo
        beginDodoInfo = self.getDodoInfo(dodoName)
        logger.info(f"当前 {dodoName} 的_K_为: {beginDodoInfo['dodos']['_K_']}")
        logger.info(f"当前 {dodoName} 的_LP_FEE_RATE_为: {beginDodoInfo['dodos']['_LP_FEE_RATE_']}")
        logger.info(f"当前 {dodoName} 的_MT_FEE_RATE_为: {beginDodoInfo['dodos']['_MT_FEE_RATE_']}")

        para_names = {"lpfeerate": "_LP_FEE_RATE_", "mtfeerate": "_MT_FEE_RATE_"}

        # 设置lpfee 或者 mtfeerate为负值
        for p, value in para_names.items():
            tx_res = self.client.setparameter(admin, dodoName, p, -1)
            afterDodoInfo = self.getDodoInfo(dodoName)
            assert tx_res["code"] == 500, f"设置{p}为负数，交易应执行失败"
            assert "FEE_RATE>=1" in tx_res["error"]["details"][0]["message"], \
                "设置lpfeerate为负数，错误信息校验失败:{}".format(tx_res["error"]["details"])
            logger.info(f'交易的错误信息: {tx_res["error"]["details"]}')
            assert afterDodoInfo["dodos"][para_names[p]] == beginDodoInfo["dodos"][para_names[p]], \
                f'设置k后，校验不正确: {beginDodoInfo["dodos"][para_names[p]]} != {afterDodoInfo["dodos"][para_names[p]]}'
            logger.info(f'{p} 设置为负数时，校验正确')

        # lpfee + mtfee 设置为 > 1
        for p, value in para_names.items():
            tx_res = self.client.setparameter(admin, dodoName, p, DecimalMath.one)
            afterDodoInfo = self.getDodoInfo(dodoName)
            assert tx_res["code"] == 500, f"设置{p}为{DecimalMath.one}，交易应执行失败"
            assert "FEE_RATE>=1" in tx_res["error"]["details"][0]["message"], \
                "设置lpfeerate为负数，错误信息校验失败:{}".format(tx_res["error"]["details"])
            assert afterDodoInfo["dodos"][para_names[p]] == beginDodoInfo["dodos"][para_names[p]], \
                f'设置k后，校验不正确: {beginDodoInfo["dodos"][para_names[p]]} != {afterDodoInfo["dodos"][para_names[p]]}'
            logger.info(f'lpfee + mtfee 设置为 > 1，校验正确')

    def checkSetParameterSetOtherParameter(self, dodoName):
        """

        :param dodoName: dodo name
        :return:
        检查setparameter方法设置其他的参数失败的情况. eg: 设置maintainer参数
        """
        # 获取当前的poolInfo
        beginDodoInfo = self.getDodoInfo(dodoName)
        logger.info(f"当前的dodoInfo: {beginDodoInfo}")

        tx_res = self.client.setparameter(admin, dodoName, "maintainer", 100)
        afterDodoInfo = self.getDodoInfo(dodoName)
        assert tx_res["code"] == 500, f"设置参数kk，交易应执行失败"
        assert "no  parameter" in tx_res["error"]["details"][0]["message"], \
            "设置参数kk，错误信息校验失败:{}".format(tx_res["error"]["details"])
        logger.info(f'交易的错误信息: {tx_res["error"]["details"]}')
        logger.info(f'设置参数kk，校验正确')
        assert beginDodoInfo == afterDodoInfo

    def checkSetParameterUseOtherAccount(self, dodoName):
        """

        :param dodoName: dodo name
        :return:
        检查setparameter方法使用其他账户来设置参数.
        """
        # 获取当前的poolInfo
        beginDodoInfo = self.getDodoInfo(dodoName)
        logger.info(f"当前的dodoInfo: {beginDodoInfo}")

        tx_res = self.client.setparameter(lp, dodoName, "k", 100)
        afterDodoInfo = self.getDodoInfo(dodoName)
        assert tx_res["code"] == 500, f"使用非admin账户设置参数k，交易应执行失败"
        assert "no  admin" in tx_res["error"]["details"][0]["message"], \
            "设置参数k，错误信息校验失败:{}".format(tx_res["error"]["details"])
        logger.info(f'交易的错误信息: {tx_res["error"]["details"]}')
        logger.info(f'使用非admin账户设置参数k，校验正确')
        assert beginDodoInfo == afterDodoInfo

    def getOraclePriceInfo(self, quoteToken, oracleBase, qDecimal=4):
        """

        :param quoteToken: 右侧币种名称
        :param oracleBase: _ORACLE_信息
        :param qDecimal: 右侧币种的精度
        :return: 获取指定左侧币、右侧币、右侧币种精度的oracle信息
        """
        # priceInfo = self.c.getTableRows(admin, admin, "oracles")
        priceInfo = self.c.getTableRows(admin, admin, "oracleprices")
        # print(priceInfo)
        res = None
        r = []
        for i in priceInfo["rows"]:
            qsInfo = i["quotetoken"]["quantity"].split(" ")
            if i["basetoken"] == oracleBase and qsInfo[-1] == quoteToken:
                r.append(i)
                if len(qsInfo[0].split(".")[-1]) == qDecimal:
                    res = i
        logger.info(f"现在oracles表中存在{len(r)}条记录: {r}")
        return res

    def getOraclePrice(self, quoteToken, oracleBase, qDecimal=4):
        """

        :param quoteToken: 右侧币种名称
        :param oracleBase: _ORACLE_信息
        :return: 返回转换的带精度的price价格
        """
        priceInfo = self.getOraclePriceInfo(quoteToken, oracleBase, qDecimal)
        # print(priceInfo)
        price = int(float(priceInfo["quotetoken"]["quantity"].split(" ")[0]) * DecimalMath.one)
        # print(priceInfo)
        return price

    def checkSetOraclePrice(self, dodoName):
        """

        :param dodoName: dodo name
        :return:
        检查正确传入price信息后，oracle价格更新成功
            - 获取当前oracle信息
            -
        """
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        baseDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        oracleBase = dodoInfo["dodos"]["_ORACLE_"]
        priceInfo = self.getOraclePriceInfo(quoteToken, oracleBase, quoteDecimal)
        logger.info("获取当前的oraclePrice: {}".format(priceInfo))
        logger.info(quoteDecimal)
        priceNumber = round(random.uniform(0.1 ** quoteDecimal, 10), quoteDecimal)
        # priceNumber = 10
        expectedPrice = to_wei_asset(priceNumber, quoteToken, quoteDecimal)
        logger.info(f"expectedPrice: {expectedPrice}")
        tx_res = self.client.setprice(oracleadmin, to_sym(baseToken, baseDecimal), expectedPrice)
        assert "transaction_id" in tx_res.keys(), f"交易返回结果不成功: {tx_res}"

        priceInfo2 = self.getOraclePriceInfo(quoteToken, oracleBase, quoteDecimal)
        logger.info("setPrice后, oraclePrice: {}".format(priceInfo))
        assert priceInfo2["basetoken"] == to_sym(baseToken, baseDecimal), f"setPrice后，{baseToken} 不正确"
        assert priceInfo2["quotetoken"] == expectedPrice, f"setPrice后，{quoteToken} 值不正确"

    def checkSetOraclePriceWhenPriceDecimalIsIncorrect(self, dodoName):
        """

        :param dodoName: dodo name
        :return:
        检查设置价格的精度大于token精度时，
        """
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        baseDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        oracleBase = dodoInfo["dodos"]["_ORACLE_"]
        priceInfo = self.getOraclePriceInfo(quoteToken, oracleBase, quoteDecimal)
        logger.info("获取当前的oraclePrice: {}".format(priceInfo))
        logger.info(quoteDecimal)
        priceNumber = round(random.uniform(1.1 ** (quoteDecimal+2), 1), quoteDecimal+1)
        print(priceNumber)
        expectedPrice = to_wei_asset(priceNumber, quoteToken, quoteDecimal + 1)
        # expectedPrice = {'quantity': '1.12345 TEB', 'contract': 'eosdosxtoken'}
        logger.info(f"expectedPrice: {expectedPrice}")
        tx_res = self.client.setprice(oracleadmin, to_sym(baseToken, baseDecimal), expectedPrice)
        print(tx_res)
        assert "transaction_id" in tx_res.keys(), f"交易返回结果不成功: {tx_res}"

        priceInfo2 = self.getOraclePriceInfo(quoteToken, oracleBase, quoteDecimal)
        logger.info("setPrice后, oraclePrice: {}".format(priceInfo))
        assert priceInfo2["basetoken"] == to_sym(baseToken, baseDecimal), f"setPrice后，{baseToken} 不正确"
        assert priceInfo2["quotetoken"] == expectedPrice, f"setPrice后，{quoteToken} 值不正确"

    def getAccountBalance(self, account, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal):
        # accountInfo = self.c.getTableRows(account, "eosdosxtoken", "accounts")
        # accountInfo = self.c.getTableRows(account, "roxearntoken", "accounts")
        accountInfo = self.c.getTableRows(account, "roxe.ro", "accounts")
        res = {}
        for row in accountInfo["rows"]:
            splitInfo = row["balance"].split(" ")
            if baseToken == splitInfo[-1]:
                res[baseToken] = int(float(splitInfo[0]) * math.pow(10, baseTokenDecimal))
            if quoteToken == splitInfo[-1]:
                res[quoteToken] = int(float(splitInfo[0]) * math.pow(10, quoteTokenDecimal))
        if baseToken not in res.keys():
            res[baseToken] = 0
        if quoteToken not in res.keys():
            res[quoteToken] = 0
        return res

    def checkSellQuoteToken(self, dodoName, sellAmount, minReceiveBase=None, isExcute=True):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行buyBase测试，购买base使R状态由0变为1, 实际价格和oracle价格要高。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        contract = dodoInfo["dodos"]["_BASE_TOKEN_"]["contract"]
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        logger.info("当前R状态为: {}".format(R))
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))
        poolBalance = self.getAccountBalance(dodoName, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，池子实际持有的资产: {}".format(poolBalance))
        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)

        spentQuote = DecimalMath.divFloor(sellAmount, price) * 100
        parseSellAmout = sellAmount / int(math.pow(10, quoteTokenDecimal))
        parseSpentAmout = spentQuote / int(math.pow(10, baseTokenDecimal))

        if minReceiveBase:
            parseSpentAmout = minReceiveBase

        logger.info("准备进行交易。。")

        tx = self.client.sellquote(trader, dodoName,
                                   to_wei_asset(parseSellAmout, quoteToken, quoteTokenDecimal, contract),
                                   to_wei_asset(parseSpentAmout, baseToken, baseTokenDecimal, contract))
        if "code" in tx:
            errMsg = tx["error"]["details"][0]["message"]
            contractBaseAmt = int(errMsg.split(":")[-1].strip().split("BUY_BASE_COST_TOO_MUCH")[0])
            tx2 = self.client.buybasetoken(trader, dodoName,
                                           to_wei_asset(contractBaseAmt / int(math.pow(10, baseTokenDecimal)), baseToken, baseTokenDecimal, contract),
                                           to_wei_asset(0, quoteToken, quoteTokenDecimal, contract))
            errMsg2 = tx2["error"]["details"][0]["message"]
            contractQuoteAmt = int(errMsg2.split(":")[-1].strip().split("BUY_BASE_COST_TOO_MUCH")[0])
            diff = abs(sellAmount - contractQuoteAmt)
            logger.info("-----------")
            logger.info("合约计算")
            logger.info("sellQuote: {}, 得到base: {},".format(sellAmount, contractBaseAmt))
            logger.info("buyBase: {} 得到quote:{}".format(contractBaseAmt, contractQuoteAmt))
            logger.info("sellQuote和buyBase的误差为:{}".format(diff))
            assert diff <= 1, "{}和{}的误差为{}".format(sellAmount, contractQuoteAmt, diff)
            logger.info("----------")
            spentQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = queryBuyBaseToken(contractBaseAmt, dodoInfo,
                                                                                              dodoName,
                                                                                              price)
            logger.info(f"计算购买{contractBaseAmt} 需: {spentQuote}")
            if isExcute:
                self.client.sellquote(trader, dodoName,
                                      to_wei_asset(parseSellAmout, quoteToken, quoteTokenDecimal, contract),
                                      to_wei_asset(contractBaseAmt/ int(math.pow(10, baseTokenDecimal)), baseToken, baseTokenDecimal, contract))

        time.sleep(2)
        baseTransferFee = get_transfer_fee(contractBaseAmt, baseToken, False, contract)
        mtTransferFee = get_transfer_fee(mtfee, baseToken, False, contract)
        quoteFee = get_transfer_fee(sellAmount, quoteToken, False, contract)
        logger.info("预计转账{}base的转账费用: {}".format(contractBaseAmt, baseTransferFee))
        logger.info("预计转账{}quote的转账费用: {}".format(sellAmount, quoteFee))
        logger.info("预计转账{}mtFee的转账费用: {}".format(mtfee, mtTransferFee))
        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)
        poolBalance2 = self.getAccountBalance(dodoName, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，池子实际持有的资产: {}".format(poolBalance2))
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))

        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"]) - (contractBaseAmt + mtfee + baseTransferFee)
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"]) + sellAmount
        expectedBaseTarget = newBaseTarget + lpfee
        expectedQuoteTarget = newQuoteTarget
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))

        logger.info("交易后池子资产变化 base: {}".format(int(dodoInfo2["dodos"]["_BASE_BALANCE_"]) - int(dodoInfo["dodos"]["_BASE_BALANCE_"])))
        logger.info("交易后池子资产变化 quote: {}".format(int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]) - int(dodoInfo["dodos"]["_QUOTE_BALANCE_"])))
        logger.info("交易后池子资产变化 baseTarget: {}".format(int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]) - int(dodoInfo["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])))
        logger.info("交易后池子资产变化 quoteTarget: {}".format(int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]) - int(dodoInfo["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])))
        logger.info("交易前后 池子实际持有base资产变化: {}".format(poolBalance2[baseToken] - poolBalance[baseToken]))
        logger.info("交易前后 池子实际持有quote资产变化: {}".format(poolBalance2[quoteToken] - poolBalance[quoteToken]))
        logger.info("交易前后 池子实际持有和pool中记录的base资产变化: {}".format(poolBalance2[baseToken] - int(dodoInfo2["dodos"]["_BASE_BALANCE_"])))
        logger.info("交易前后 池子实际持有和pool中记录的quote资产变化: {}".format(poolBalance2[quoteToken] - int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"])))

        logger.info("用户实际持有的base资产变化: {}".format(tradeAccount2[baseToken] - tradeAccount[baseToken]))
        logger.info("用户实际持有的quote资产变化: {}".format(tradeAccount2[quoteToken] - tradeAccount[quoteToken]))
        r1 = assertEqualOnlyShowLog(expectedBase, int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "检查池子的baseBalance")
        r2 = assertEqualOnlyShowLog(expectedQuote, int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "检查池子的quoteBalance")
        r3 = assertEqualOnlyShowLog(expectedBaseTarget, int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "检查池子的targetBaseBalance")
        r4 = assertEqualOnlyShowLog(expectedQuoteTarget, int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "检查池子的targetQuoteBalance")
        r5 = assertEqualOnlyShowLog(newR, dodoInfo2["dodos"]["_R_STATUS_"], "检查R状态")
        r6 = assertEqualOnlyShowLog(tradeAccount2[baseToken] - tradeAccount[baseToken], contractBaseAmt, "检查用户的baseBalance")
        r7 = assertEqualOnlyShowLog(tradeAccount[quoteToken] - tradeAccount2[quoteToken], sellAmount + quoteFee, "检查用户的quoteBalance")
        mtTxfee = get_transfer_fee(mtfee, baseToken, True, contract)
        r8 = assertEqualOnlyShowLog(maintainerAccount2[baseToken] - maintainerAccount[baseToken], mtfee - mtTxfee, "检查维护账户的base资产")
        r9 = assertEqualOnlyShowLog(maintainerAccount2[quoteToken], maintainerAccount[quoteToken], "检查维护账户的quote资产")

        r10 = assertEqualOnlyShowLog(expectedBase, poolBalance2[baseToken], "检查池子实际持有的baseBalance")
        r11 = assertEqualOnlyShowLog(expectedQuote, poolBalance2[quoteToken], "检查池子实际持有的quoteBalance")

        poolBaseChange = int(dodoInfo["dodos"]["_BASE_BALANCE_"]) - int(dodoInfo2["dodos"]["_BASE_BALANCE_"])
        poolQuoteChange = int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]) - int(dodoInfo["dodos"]["_QUOTE_BALANCE_"])
        logger.info("base: {}, quote: {}, 价格: {}".format(contractBaseAmt, tradeAccount[quoteToken] - tradeAccount2[quoteToken], (tradeAccount[quoteToken] - tradeAccount2[quoteToken])/sellAmount))
        logger.info("pool base: {}, quote: {}, 价格: {}".format(poolBaseChange, poolQuoteChange, poolQuoteChange/poolBaseChange))
        if r1 or r2 or r3 or r4 or r5 or r6 or r7 or r8 or r9 or r10 or r11:
            assert False, "有检查失败"

    def checkBuyBaseToken(self, dodoName, buyAmount=100000, maxPayQuote=None, isExcute=True):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行buyBase测试，购买base使R状态由0变为1, 实际价格和oracle价格要高。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        contract = dodoInfo["dodos"]["_BASE_TOKEN_"]["contract"]
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        logger.info("当前R状态为: {}".format(R))
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))
        poolBalance = self.getAccountBalance(dodoName, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，池子实际持有的资产: {}".format(poolBalance))
        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)

        # # buyAmount = 100000
        spentQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = queryBuyBaseToken(buyAmount, dodoInfo,
                                                                                          dodoName,
                                                                                          price)
        logger.info(f"准备购买baseToken的数量为: {buyAmount}")
        parseBuyAmout = buyAmount / int(math.pow(10, baseTokenDecimal))
        parseSpentAmout = spentQuote / int(math.pow(10, quoteTokenDecimal))
        if maxPayQuote:
            parseSpentAmout = maxPayQuote

        # print(to_wei_asset(parseBuyAmout, baseToken, baseTokenDecimal))
        # print(to_wei_asset(parseSpentAmout, quoteToken, quoteTokenDecimal))
        # print(to_wei_asset(parseBuyAmout, baseToken, baseTokenDecimal))
        if isExcute:
            # logger.info("交易账户授权。。")
            # self.client.allowDosContract(trader, acc2pub_keys[trader])
            logger.info("准备进行交易。。")
            tx = self.client.buybasetoken(trader, dodoName,
                                          to_wei_asset(parseBuyAmout, baseToken, baseTokenDecimal, contract),
                                          to_wei_asset(0, quoteToken, quoteTokenDecimal, contract))
            if "code" in tx:
                errMsg = tx["error"]["details"][0]["message"]
                contractAmount = int(errMsg.split(":")[-1].strip().split("BUY_BASE_COST_TOO_MUCH")[0])
                tx = self.client.buybasetoken(trader, dodoName,
                                              to_wei_asset(parseBuyAmout, baseToken, baseTokenDecimal, contract),
                                              to_wei_asset(parseSpentAmout, quoteToken, quoteTokenDecimal,
                                                           contract))
            else:
                contractAmount = spentQuote
            time.sleep(2)

        baseFee = get_transfer_fee(buyAmount, baseToken, False, contract)
        quoteFee = get_transfer_fee(contractAmount, quoteToken, False, contract)
        logger.info("合约中计算的payQuote: {}".format(contractAmount))
        logger.info("预计quote的转账费用: {}".format(quoteFee))
        logger.info("预计base的转账费用: {}".format(baseFee))
        logger.info("计算的quote数量偏差:{}".format(contractAmount - spentQuote))
        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)
        poolBalance2 = self.getAccountBalance(dodoName, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，池子实际持有的资产: {}".format(poolBalance2))
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))

        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"]) - buyAmount - mtfee - baseFee
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"]) + contractAmount
        expectedBaseTarget = newBaseTarget + lpfee
        expectedQuoteTarget = newQuoteTarget
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))

        logger.info("交易后池子资产变化 base: {}".format(int(dodoInfo2["dodos"]["_BASE_BALANCE_"]) - int(dodoInfo["dodos"]["_BASE_BALANCE_"])))
        logger.info("交易后池子资产变化 quote: {}".format(int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]) - int(dodoInfo["dodos"]["_QUOTE_BALANCE_"])))
        logger.info("交易后池子资产变化 baseTarget: {}".format(int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]) - int(dodoInfo["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])))
        logger.info("交易后池子资产变化 quoteTarget: {}".format(int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]) - int(dodoInfo["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])))
        logger.info("交易前后 池子实际持有base资产变化: {}".format(poolBalance2[baseToken] - poolBalance[baseToken]))
        logger.info("交易前后 池子实际持有quote资产变化: {}".format(poolBalance2[quoteToken] - poolBalance[quoteToken]))
        logger.info("交易前后 池子实际持有和pool中记录的base资产变化: {}".format(poolBalance2[baseToken] - int(dodoInfo2["dodos"]["_BASE_BALANCE_"])))
        logger.info("交易前后 池子实际持有和pool中记录的quote资产变化: {}".format(poolBalance2[quoteToken] - int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"])))

        logger.info("用户实际持有的base资产变化: {}".format(tradeAccount2[baseToken] - tradeAccount[baseToken]))
        logger.info("用户实际持有的quote资产变化: {}".format(tradeAccount2[quoteToken] - tradeAccount[quoteToken]))
        r1 = assertEqualOnlyShowLog(expectedBase, int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "检查池子的baseBalance")
        r2 = assertEqualOnlyShowLog(expectedQuote, int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "检查池子的quoteBalance")
        r3 = assertEqualOnlyShowLog(expectedBaseTarget, int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "检查池子的targetBaseBalance")
        r4 = assertEqualOnlyShowLog(expectedQuoteTarget, int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "检查池子的targetQuoteBalance")
        r5 = assertEqualOnlyShowLog(newR, dodoInfo2["dodos"]["_R_STATUS_"], "检查R状态")
        r6 = assertEqualOnlyShowLog(tradeAccount2[baseToken] - tradeAccount[baseToken], buyAmount, "检查用户的baseBalance")
        r7 = assertEqualOnlyShowLog(tradeAccount[quoteToken] - tradeAccount2[quoteToken], contractAmount + quoteFee, "检查用户的quoteBalance")
        mtTxfee = get_transfer_fee(mtfee, baseToken, True, contract)
        r8 = assertEqualOnlyShowLog(maintainerAccount2[baseToken] - maintainerAccount[baseToken], mtfee - mtTxfee, "检查维护账户的base资产")
        r9 = assertEqualOnlyShowLog(maintainerAccount2[quoteToken], maintainerAccount[quoteToken], "检查维护账户的quote资产")
        r10 = assertEqualOnlyShowLog(expectedBase, poolBalance2[baseToken], "检查池子实际的的base资产")
        r11 = assertEqualOnlyShowLog(expectedQuote, poolBalance2[quoteToken], "检查池子实际的quote资产")

        poolBaseChange = int(dodoInfo["dodos"]["_BASE_BALANCE_"]) - int(dodoInfo2["dodos"]["_BASE_BALANCE_"])
        poolQuoteChange = int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]) - int(dodoInfo["dodos"]["_QUOTE_BALANCE_"])
        logger.info("base: {}, quote: {}, 价格: {}".format(buyAmount, tradeAccount[quoteToken] - tradeAccount2[quoteToken], (tradeAccount[quoteToken] - tradeAccount2[quoteToken])/buyAmount))
        logger.info("pool base: {}, quote: {}, 价格: {}".format(poolBaseChange, poolQuoteChange, poolQuoteChange/poolBaseChange))
        if r1 or r2 or r3 or r4 or r5 or r6 or r7 or r8 or r9 or r10 or r11:
            assert False, "有检查失败"
        # assert expectedBase == int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "交易后资产: {}, 相差{}".format(
        #     dodoInfo2["dodos"]["_BASE_BALANCE_"], expectedBase - int(dodoInfo2["dodos"]["_BASE_BALANCE_"]))
        # assert expectedQuote == int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "交易后资产: {}, 相差{}".format(
        #     dodoInfo2["dodos"]["_QUOTE_BALANCE_"], expectedQuote - int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]))
        # assert newR == dodoInfo2["dodos"]["_R_STATUS_"], "交易后R状态: {}".format(dodoInfo2["dodos"]["_R_STATUS_"])
        # assert tradeAccount2[baseToken] - tradeAccount[baseToken] == buyAmount, "交易账户base资产不正确, {}!={}".format(tradeAccount2[baseToken] - tradeAccount[baseToken], buyAmount)
        # assert tradeAccount2[quoteToken] + spentQuote == tradeAccount[quoteToken], "交易账户quote资产不正确, {}!={}".format(tradeAccount[quoteToken] - tradeAccount2[quoteToken], spentQuote)
        # assert maintainerAccount2[baseToken] - maintainerAccount[baseToken] == mtfee, "维护账户quote资产不正确, {} != {}".format(maintainerAccount2[baseToken] - maintainerAccount[baseToken], mtfee)
        # assert maintainerAccount2[quoteToken] == maintainerAccount[quoteToken], "维护账户quote资产不正确, {}!={}".format(maintainerAccount2[quoteToken], maintainerAccount[quoteToken])

        # assert expectedBaseTarget == int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "交易后资产: {}, 相差{}".format(
        #     dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"],
        #     expectedBaseTarget - int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]))
        # assert expectedQuoteTarget == int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "交易后资产: {}, 相差{}".format(
        #     dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"],
        #     expectedQuoteTarget - int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]))

    def checkBuyBaseTokenRStatus0to1(self, dodoName, buyAmount=100000, maxPayQuote=None):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行buyBase测试，购买base使R状态由0变为1, 实际价格和oracle价格要高。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        if R != 0:
            logger.info("当前R状态为: {}, 暂不执行此用例".format(R))
            return
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)
        # buyAmount = 100000
        spentQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = queryBuyBaseToken(buyAmount, dodoInfo,
                                                                                          dodoName,
                                                                                          price)
        logger.info(f"准备购买baseToken的数量为: {buyAmount}")
        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"]) - (buyAmount + mtfee)
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"]) + spentQuote
        expectedBaseTarget = newBaseTarget + lpfee
        expectedQuoteTarget = newQuoteTarget
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))
        parseBuyAmout = buyAmount / int(math.pow(10, baseTokenDecimal))
        parseSpentAmout = spentQuote / int(math.pow(10, quoteTokenDecimal))
        if maxPayQuote:
            parseSpentAmout = maxPayQuote

        print(to_wei_asset(parseBuyAmout, baseToken, baseTokenDecimal))
        print(to_wei_asset(parseSpentAmout, quoteToken, quoteTokenDecimal))
        # print(to_wei_asset(parseBuyAmout, baseToken, baseTokenDecimal))
        # logger.info("交易账户授权。。")
        # self.client.allowDosContract(trader, acc2pub_keys[trader])
        # logger.info("准备进行交易。。")
        # self.client.buybasetoken(trader, dodoName, to_wei_asset(parseBuyAmout, baseToken, baseTokenDecimal),
        #                          to_wei_asset(parseSpentAmout, quoteToken, quoteTokenDecimal))
        # time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))
        assert expectedBase == int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_BASE_BALANCE_"])
        assert expectedQuote == int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_QUOTE_BALANCE_"])
        assert expectedBaseTarget == int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
        assert expectedQuoteTarget == int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
        assert newR == dodoInfo2["dodos"]["_R_STATUS_"], "交易后R状态: {}".format(dodoInfo2["dodos"]["_R_STATUS_"])

        assert tradeAccount2[baseToken] - tradeAccount[baseToken] == buyAmount, "交易账户base资产不正确"
        assert tradeAccount2[quoteToken] + spentQuote == tradeAccount[quoteToken], "交易账户quote资产不正确"
        assert maintainerAccount2[baseToken] - maintainerAccount[baseToken] == mtfee, "维护账户quote资产不正确"
        assert maintainerAccount2[quoteToken] == maintainerAccount[quoteToken], "维护账户quote资产不正确"

    def checkBuyBaseTokenRStatus1to1(self, dodoName, buyAmount=100000):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行buyBase测试，购买base使R状态改变为1, 实际价格和oracle价格要高。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        if R != 1:
            logger.info("当前R状态为: {}, 暂不执行此用例".format(R))
            return
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)

        spentQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = queryBuyBaseToken(buyAmount, dodoInfo,
                                                                                          dodoName,
                                                                                          price)
        logger.info(f"准备购买baseToken的数量为: {buyAmount}")
        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"]) - (buyAmount + mtfee)
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"]) + spentQuote
        expectedBaseTarget = newBaseTarget + lpfee
        expectedQuoteTarget = newQuoteTarget
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))
        parseBuyAmout = buyAmount / int(math.pow(10, baseTokenDecimal))
        parseSpentAmout = spentQuote / int(math.pow(10, quoteTokenDecimal))
        logger.info("交易账户授权。。")
        self.client.allowDosContract(trader, acc2pub_keys[trader])
        logger.info("准备进行交易。。")
        self.client.buybasetoken(trader, dodoName, to_wei_asset(parseBuyAmout, baseToken, baseTokenDecimal),
                                 to_wei_asset(parseSpentAmout, quoteToken, quoteTokenDecimal))
        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))
        assert expectedBase == int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_BASE_BALANCE_"])
        assert expectedQuote == int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_QUOTE_BALANCE_"])
        assert expectedBaseTarget == int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
        assert expectedQuoteTarget == int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
        assert newR == dodoInfo2["dodos"]["_R_STATUS_"], "交易后R状态: {}".format(dodoInfo2["dodos"]["_R_STATUS_"])

        assert tradeAccount2[baseToken] - tradeAccount[baseToken] == buyAmount, "交易账户base资产不正确"
        assert tradeAccount2[quoteToken] + spentQuote == tradeAccount[quoteToken], "交易账户quote资产不正确"
        assert maintainerAccount2[baseToken] - maintainerAccount[baseToken] == mtfee, "维护账户quote资产不正确"
        assert maintainerAccount2[quoteToken] == maintainerAccount[quoteToken], "维护账户quote资产不正确"

    def checkBuyBaseTokenRStatus2to0(self, dodoName):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行buyBase测试，购买base使R状态由2改变为0, 实际价格和oracle价格一致。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        if R != 2:
            logger.info("当前R状态为: {}, 暂不执行此用例".format(R))
            return
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)
        baseRange = int(dodoInfo['dodos']['_BASE_BALANCE_']) - int(dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_'])
        logger.info("想要保持R状态不变, 购买的baseToken加上费用用不能超过: {}".format(baseRange))
        lpFeeRate = dodoInfo["dodos"]["_LP_FEE_RATE_"]
        mtFeeRate = dodoInfo["dodos"]["_MT_FEE_RATE_"]
        buyAmount = baseRange
        calLpFee = DecimalMath.mul(buyAmount, lpFeeRate)
        calMtFee = DecimalMath.mul(buyAmount, mtFeeRate)
        while True:
            # print(buyAmount + calLpFee + calMtFee)
            if buyAmount + calLpFee + calMtFee <= baseRange:
                break
            buyAmount = baseRange - DecimalMath.one if baseRange > DecimalMath.one else baseRange - 1000
            calLpFee = DecimalMath.mul(buyAmount, lpFeeRate)
            calMtFee = DecimalMath.mul(buyAmount, mtFeeRate)

        logger.info(f"准备购买baseToken的数量为: {buyAmount}")
        spentQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = queryBuyBaseToken(buyAmount, dodoInfo,
                                                                                          dodoName,
                                                                                          price)
        excuteResult = True if spentQuote > 0 else False
        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"]) - (buyAmount + mtfee)
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"]) + spentQuote
        expectedBaseTarget = int(dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']) + lpfee
        expectedQuoteTarget = newQuoteTarget
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))
        parseBuyAmout = buyAmount / int(math.pow(10, baseTokenDecimal))
        parseSpentAmout = spentQuote / int(math.pow(10, quoteTokenDecimal))
        logger.info("交易账户授权。。")
        self.client.allowDosContract(trader, acc2pub_keys[trader])
        logger.info("准备进行交易。。")
        tx_res = self.client.buybasetoken(trader, dodoName, to_wei_asset(parseBuyAmout, baseToken, baseTokenDecimal),
                                          to_wei_asset(parseSpentAmout, quoteToken, quoteTokenDecimal))
        if excuteResult is False:
            assert tx_res["code"] == 500, "当执行交易所需资产为时, 执行交易失败, 因为转账金额不能为0"
            assert 'must transfer positive quantity' in tx_res["error"]["details"][0]["message"], "报错不是static_transfer引起的"
            logger.info("R状态由2改变为0，执行交易失败")
            return
        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))
        assert expectedBase == int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_BASE_BALANCE_"])
        assert expectedQuote == int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_QUOTE_BALANCE_"])
        assert expectedBaseTarget == int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
        assert expectedQuoteTarget == int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
        assert newR == dodoInfo2["dodos"]["_R_STATUS_"], "交易后R状态: {}".format(dodoInfo2["dodos"]["_R_STATUS_"])

        assert tradeAccount2[baseToken] - tradeAccount[baseToken] == buyAmount, "交易账户base资产不正确"
        assert tradeAccount2[quoteToken] + spentQuote == tradeAccount[quoteToken], "交易账户quote资产不正确"
        assert maintainerAccount2[baseToken] - maintainerAccount[baseToken] == mtfee, "维护账户quote资产不正确"
        assert maintainerAccount2[quoteToken] == maintainerAccount[quoteToken], "维护账户quote资产不正确"

    def checkBuyBaseTokenRStatus2to1(self, dodoName):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行buyBase测试，购买base使R状态改变为1, 实际价格和oracle价格要高。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        if R != 2:
            logger.info("当前R状态为: {}, 暂不执行此用例".format(R))
            return
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)
        baseRange = int(dodoInfo['dodos']['_BASE_BALANCE_']) - int(dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_'])
        logger.info("想要保持R状态不变, 购买的baseToken加上费用用不能超过: {}".format(baseRange))
        lpFeeRate = dodoInfo["dodos"]["_LP_FEE_RATE_"]
        mtFeeRate = dodoInfo["dodos"]["_MT_FEE_RATE_"]
        while True:
            buyAmount = baseRange + 10000
            spentQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = queryBuyBaseToken(buyAmount, dodoInfo,
                                                                                              dodoName,
                                                                                              price)
            if spentQuote > 0:
                break

        logger.info(f"准备购买baseToken的数量为: {buyAmount}")
        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"]) - (buyAmount + mtfee)
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"]) + spentQuote
        expectedBaseTarget = int(dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']) + lpfee
        expectedQuoteTarget = newQuoteTarget
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))
        parseBuyAmout = buyAmount / int(math.pow(10, baseTokenDecimal))
        parseSpentAmout = spentQuote / int(math.pow(10, quoteTokenDecimal))
        logger.info("交易账户授权。。")
        self.client.allowDosContract(trader, acc2pub_keys[trader])
        logger.info("准备进行交易。。")
        tx_res = self.client.buybasetoken(trader, dodoName, to_wei_asset(parseBuyAmout, baseToken, baseTokenDecimal),
                                          to_wei_asset(parseSpentAmout, quoteToken, quoteTokenDecimal))
        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))
        assert expectedBase == int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_BASE_BALANCE_"])
        assert expectedQuote == int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_QUOTE_BALANCE_"])
        assert expectedBaseTarget == int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
        assert expectedQuoteTarget == int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
        assert newR == dodoInfo2["dodos"]["_R_STATUS_"], "交易后R状态: {}".format(dodoInfo2["dodos"]["_R_STATUS_"])

        assert tradeAccount2[baseToken] - tradeAccount[baseToken] == buyAmount, "交易账户base资产不正确"
        assert tradeAccount2[quoteToken] + spentQuote == tradeAccount[quoteToken], "交易账户quote资产不正确"
        assert maintainerAccount2[baseToken] - maintainerAccount[baseToken] == mtfee, "维护账户quote资产不正确"
        assert maintainerAccount2[quoteToken] == maintainerAccount[quoteToken], "维护账户quote资产不正确"

    def checkBuyBaseTokenRStatus2to2(self, dodoName):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行buyBase测试, 购买数量保持R为2不变, 实际价格和oracle要低。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        if R != 2:
            logger.info("当前R状态为: {}, 暂不执行此用例".format(R))
            return
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)

        baseRange = int(dodoInfo['dodos']['_BASE_BALANCE_']) - int(dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_'])
        logger.info("想要保持R状态不变, 购买的baseToken加上费用用不能超过: {}".format(baseRange))

        buyAmount = baseRange // 2
        logger.info(f"为了保证R状态不变, 准备购买baseToken的数量为: {buyAmount}")
        spentQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = queryBuyBaseToken(buyAmount, dodoInfo,
                                                                                          dodoName,
                                                                                          price)
        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"]) - (buyAmount + mtfee)
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"]) + spentQuote
        expectedBaseTarget = int(dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']) + lpfee
        expectedQuoteTarget = newQuoteTarget
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))
        parseBuyAmout = buyAmount / int(math.pow(10, baseTokenDecimal))
        parseSpentAmout = spentQuote / int(math.pow(10, quoteTokenDecimal))
        logger.info("交易账户授权。。")
        self.client.allowDosContract(trader, acc2pub_keys[trader])
        logger.info("准备进行交易。。")
        self.client.buybasetoken(trader, dodoName, to_wei_asset(parseBuyAmout, baseToken, baseTokenDecimal),
                                 to_wei_asset(parseSpentAmout, quoteToken, quoteTokenDecimal))
        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))
        assert expectedBase == int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_BASE_BALANCE_"])
        assert expectedQuote == int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_QUOTE_BALANCE_"])
        assert expectedBaseTarget == int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
        assert expectedQuoteTarget == int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
        assert newR == dodoInfo2["dodos"]["_R_STATUS_"], "交易后R状态: {}".format(dodoInfo2["dodos"]["_R_STATUS_"])

        assert tradeAccount2[baseToken] - tradeAccount[baseToken] == buyAmount, "交易账户base资产不正确"
        assert tradeAccount2[quoteToken] + spentQuote == tradeAccount[quoteToken], "交易账户quote资产不正确"
        assert maintainerAccount2[baseToken] - maintainerAccount[baseToken] == mtfee, "维护账户quote资产不正确"
        assert maintainerAccount2[quoteToken] == maintainerAccount[quoteToken], "维护账户quote资产不正确"

    def checkBuyBaseTokenBuyMinAmount(self, dodoName):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行buyBase测试。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)

        buyAmount = 1
        logger.info(f"为了保证R状态不变, 准备购买baseToken的数量为: {buyAmount}")
        spentQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = queryBuyBaseToken(buyAmount, dodoInfo,
                                                                                          dodoName, price)
        excuteResult = True if spentQuote > 0 else False
        parseBuyAmout = buyAmount / int(math.pow(10, baseTokenDecimal))
        parseSpentAmout = spentQuote / int(math.pow(10, quoteTokenDecimal))
        to_wei_asset(parseBuyAmout, baseToken, baseTokenDecimal)
        logger.info("交易账户授权。。")
        self.client.allowDosContract(trader, acc2pub_keys[trader])
        logger.info("准备进行交易。。")
        tx_res = self.client.buybasetoken(trader, dodoName, to_wei_asset(parseBuyAmout, baseToken, baseTokenDecimal),
                                          to_wei_asset(parseSpentAmout, quoteToken, quoteTokenDecimal))
        if excuteResult is False:
            assert tx_res["code"] == 500, "当执行交易所需资产为时,执行交易失败, 因为转账金额不能为0"
            assert 'must transfer positive quantity' in tx_res["error"]["details"][0]["message"], "报错不是static_transfer引起的"
            return

        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)

        # 计算预期的资产信息
        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"]) - (buyAmount + mtfee)
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"]) + spentQuote
        expectedBaseTarget = int(dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']) + lpfee
        expectedQuoteTarget = newQuoteTarget
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))
        # 打印交易后资产信息
        logger.info(f"交易后，baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"交易后，quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("交易后，R状态: {}".format(R))
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))
        assertEqualOnlyShowLog(expectedBase, int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_BASE_BALANCE_"]))
        assertEqualOnlyShowLog(expectedQuote, int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_QUOTE_BALANCE_"]))
        assertEqualOnlyShowLog(expectedBaseTarget, int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]))
        assertEqualOnlyShowLog(expectedQuoteTarget, int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]))
        assertEqualOnlyShowLog(newR, dodoInfo2["dodos"]["_R_STATUS_"], "交易后R状态: {}".format(dodoInfo2["dodos"]["_R_STATUS_"]))

        assertEqualOnlyShowLog(tradeAccount2[baseToken] - tradeAccount[baseToken], buyAmount, "交易账户base资产不正确")
        assertEqualOnlyShowLog(tradeAccount2[quoteToken] + spentQuote, tradeAccount[quoteToken], "交易账户quote资产不正确")
        assertEqualOnlyShowLog(maintainerAccount2[baseToken] - maintainerAccount[baseToken], mtfee, "维护账户quote资产不正确")
        assertEqualOnlyShowLog(maintainerAccount2[quoteToken], maintainerAccount[quoteToken], "维护账户quote资产不正确")

    def checkBuyBaseTokenBuyAcceptMinAmount(self, dodoName):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行buyBase测试。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)

        buyAmount = 1
        while True:
            spentQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = queryBuyBaseToken(buyAmount, dodoInfo,
                                                                                              dodoName,
                                                                                              price)
            if spentQuote > 0:
                break
            else:
                buyAmount += 1
        logger.info(f"准备购买baseToken的数量为: {buyAmount}")
        parseBuyAmout = buyAmount / int(math.pow(10, baseTokenDecimal))
        parseSpentAmout = spentQuote / int(math.pow(10, quoteTokenDecimal))
        logger.info("交易账户授权。。")
        self.client.allowDosContract(trader, acc2pub_keys[trader])
        logger.info("准备进行交易。。")
        tx_res = self.client.buybasetoken(trader, dodoName, to_wei_asset(parseBuyAmout, baseToken, baseTokenDecimal),
                                          to_wei_asset(parseSpentAmout, quoteToken, quoteTokenDecimal))

        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)

        # 计算预期的资产信息
        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"]) - (buyAmount + mtfee)
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"]) + spentQuote
        expectedBaseTarget = newBaseTarget + lpfee
        expectedQuoteTarget = newQuoteTarget
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))
        # 打印交易后资产信息
        logger.info(f"交易后，baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"交易后，quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("交易后，R状态: {}".format(R))
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))
        assert expectedBase == int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_BASE_BALANCE_"])
        assert expectedQuote == int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_QUOTE_BALANCE_"])
        assert expectedBaseTarget == int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
        assert expectedQuoteTarget == int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
        assert newR == dodoInfo2["dodos"]["_R_STATUS_"], "交易后R状态: {}".format(dodoInfo2["dodos"]["_R_STATUS_"])

        assert tradeAccount2[baseToken] - tradeAccount[baseToken] == buyAmount, "交易账户base资产不正确"
        assert tradeAccount2[quoteToken] + spentQuote == tradeAccount[quoteToken], "交易账户quote资产不正确"
        assert maintainerAccount2[baseToken] - maintainerAccount[baseToken] == mtfee, "维护账户quote资产不正确"
        assert maintainerAccount2[quoteToken] == maintainerAccount[quoteToken], "维护账户quote资产不正确"

    def checkBuyBaseTokenBuyAmountExceedPoolNumber(self, dodoName):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行buyBase测试。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)

        buyAmount = int(math.pow(10, baseTokenDecimal)) + int(dodoInfo["dodos"]["_BASE_BALANCE_"])
        try:
            spentQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = queryBuyBaseToken(buyAmount, dodoInfo,
                                                                                              dodoName,
                                                                                              price)
        except Exception:
            logger.info("预计交易会报错")
            spentQuote = int(dodoInfo['dodos']['_QUOTE_BALANCE_'])
            newR = R
        logger.info(f"准备购买baseToken的数量为: {buyAmount}")
        parseBuyAmout = buyAmount / int(math.pow(10, baseTokenDecimal))
        parseSpentAmout = spentQuote / int(math.pow(10, quoteTokenDecimal))
        logger.info("交易账户授权。。")
        self.client.allowDosContract(trader, acc2pub_keys[trader])
        logger.info("准备进行交易。。")
        tx_res = self.client.buybasetoken(trader, dodoName, to_wei_asset(parseBuyAmout, baseToken, baseTokenDecimal),
                                          to_wei_asset(parseSpentAmout, quoteToken, quoteTokenDecimal))

        assert tx_res["code"] == 500, "不能购买超出池子的数量"
        assert "DODO_BASE_BALANCE_NOT_ENOUGH" in tx_res["error"]["details"][0]["message"], "不能购买超出池子的数量"
        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)

        # 计算预期的资产信息
        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"])
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"])
        expectedBaseTarget = int(dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_'])
        expectedQuoteTarget = int(dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_'])
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))
        # 打印交易后资产信息
        logger.info(f"交易后，baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"交易后，quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("交易后，R状态: {}".format(R))
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))
        assert expectedBase == int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_BASE_BALANCE_"])
        assert expectedQuote == int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_QUOTE_BALANCE_"])
        assert expectedBaseTarget == int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
        assert expectedQuoteTarget == int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
        assert newR == dodoInfo2["dodos"]["_R_STATUS_"], "交易后R状态: {}".format(dodoInfo2["dodos"]["_R_STATUS_"])

        assert tradeAccount2[baseToken] - tradeAccount[baseToken] == 0, "交易账户base资产不正确"
        assert tradeAccount2[quoteToken] == tradeAccount[quoteToken], "交易账户quote资产不正确"
        assert maintainerAccount2[baseToken] - maintainerAccount[baseToken] == 0, "维护账户quote资产不正确"
        assert maintainerAccount2[quoteToken] == maintainerAccount[quoteToken], "维护账户quote资产不正确"

    def checkBuyBaseTokenBuyAmountExceedSelfWalletNumber(self, dodoName):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行buyBase测试。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)

        buyAmount = int(dodoInfo["dodos"]["_BASE_BALANCE_"]) - 1000000000
        print(buyAmount)
        spentQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = queryBuyBaseToken(buyAmount, dodoInfo,
                                                                                          dodoName,
                                                                                          price)
        logger.info(f"准备购买baseToken的数量为: {buyAmount}")
        parseBuyAmout = buyAmount / int(math.pow(10, baseTokenDecimal))
        parseSpentAmout = spentQuote / int(math.pow(10, quoteTokenDecimal))
        logger.info("交易账户授权。。")
        self.client.allowDosContract(trader, acc2pub_keys[trader])
        logger.info("准备进行交易。。")
        tx_res = self.client.buybasetoken(trader, dodoName, to_wei_asset(parseBuyAmout, baseToken, baseTokenDecimal),
                                          to_wei_asset(parseSpentAmout, quoteToken, quoteTokenDecimal))

        assert tx_res["code"] == 500, "不能购买超出自身资产的数量"
        assert "overdrawn balance" in tx_res["error"]["details"][0]["message"], "不能购买超出自身资产的数量"
        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)

        # 计算预期的资产信息
        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"])
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"])
        expectedBaseTarget = int(dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_'])
        expectedQuoteTarget = int(dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_'])
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))
        # 打印交易后资产信息
        logger.info(f"交易后，baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"交易后，quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("交易后，R状态: {}".format(R))
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))
        assert expectedBase == int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_BASE_BALANCE_"])
        assert expectedQuote == int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_QUOTE_BALANCE_"])
        assert expectedBaseTarget == int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
        assert expectedQuoteTarget == int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
        assert newR == dodoInfo2["dodos"]["_R_STATUS_"], "交易后R状态: {}".format(dodoInfo2["dodos"]["_R_STATUS_"])

        assert tradeAccount2[baseToken] - tradeAccount[baseToken] == 0, "交易账户base资产不正确"
        assert tradeAccount2[quoteToken] == tradeAccount[quoteToken], "交易账户quote资产不正确"
        assert maintainerAccount2[baseToken] - maintainerAccount[baseToken] == 0, "维护账户quote资产不正确"
        assert maintainerAccount2[quoteToken] == maintainerAccount[quoteToken], "维护账户quote资产不正确"

    def checkBuyBaseTokenBuyAmountDecimalWrong(self, dodoName):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行buyBase测试。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)

        buyAmount = 1111112
        spentQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = queryBuyBaseToken(buyAmount, dodoInfo,
                                                                                          dodoName,
                                                                                          price)
        logger.info(f"准备购买baseToken的数量为: {buyAmount}")
        parseBuyAmout = buyAmount / int(math.pow(10, baseTokenDecimal + 1))
        parseSpentAmout = spentQuote / int(math.pow(10, quoteTokenDecimal))
        logger.info("交易账户授权。。")
        self.client.allowDosContract(trader, acc2pub_keys[trader])
        logger.info("准备进行交易。。")
        tx_res = self.client.buybasetoken(trader, dodoName, to_wei_asset(parseBuyAmout, baseToken, baseTokenDecimal +1),
                                          to_wei_asset(parseSpentAmout, quoteToken, quoteTokenDecimal))

        assert tx_res["code"] == 500, "不能购买超出池子的数量"
        assert "mismatch precision of the base token in the pair" in tx_res["error"]["details"][0]["message"], "不能购买超出池子的数量"

        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)

        # 计算预期的资产信息
        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"])
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"])
        expectedBaseTarget = int(dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_'])
        expectedQuoteTarget = int(dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_'])
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))
        # 打印交易后资产信息
        logger.info(f"交易后，baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"交易后，quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("交易后，R状态: {}".format(R))
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))
        assert expectedBase == int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_BASE_BALANCE_"])
        assert expectedQuote == int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_QUOTE_BALANCE_"])
        assert expectedBaseTarget == int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
        assert expectedQuoteTarget == int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
        assert dodoInfo["dodos"]["_R_STATUS_"] == dodoInfo2["dodos"]["_R_STATUS_"], "交易后R状态: {}".format(dodoInfo2["dodos"]["_R_STATUS_"])

        assert tradeAccount2[baseToken] - tradeAccount[baseToken] == 0, "交易账户base资产不正确"
        assert tradeAccount2[quoteToken] == tradeAccount[quoteToken], "交易账户quote资产不正确"
        assert maintainerAccount2[baseToken] - maintainerAccount[baseToken] == 0, "维护账户quote资产不正确"
        assert maintainerAccount2[quoteToken] == maintainerAccount[quoteToken], "维护账户quote资产不正确"

    def checkBuyBaseTokenBuyAmountWhenPriceAbove(self, dodoName):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行buyBase测试。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))

        curPrice = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(f"curPrice: {curPrice}")

        expectedPrice = to_wei_asset(curPrice * 1.1 / DecimalMath.one, quoteToken, quoteTokenDecimal)
        logger.info(f"expectedPrice: {expectedPrice}")
        tx_res = self.client.setprice(oracleadmin, to_sym(baseToken, baseTokenDecimal), expectedPrice)

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)

        buyAmount = 100000
        spentQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = queryBuyBaseToken(buyAmount, dodoInfo,
                                                                                          dodoName,
                                                                                          price)
        logger.info(f"准备购买baseToken的数量为: {buyAmount}")
        parseBuyAmout = buyAmount / int(math.pow(10, baseTokenDecimal))
        parseSpentAmout = spentQuote / int(math.pow(10, quoteTokenDecimal))
        logger.info("交易账户授权。。")
        self.client.allowDosContract(trader, acc2pub_keys[trader])
        logger.info("准备进行交易。。")
        tx_res = self.client.buybasetoken(trader, dodoName, to_wei_asset(parseBuyAmout, baseToken, baseTokenDecimal),
                                          to_wei_asset(parseSpentAmout, quoteToken, quoteTokenDecimal))

        # assert tx_res["code"] == 500, "不能购买超出自身资产的数量"
        # assert "overdrawn balance" in tx_res["error"]["details"][0]["message"], "不能购买超出自身资产的数量"
        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)

        # 计算预期的资产信息
        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"]) - (buyAmount + mtfee)
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"]) + spentQuote
        expectedBaseTarget = newBaseTarget + lpfee
        expectedQuoteTarget = newQuoteTarget
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))
        # 打印交易后资产信息
        logger.info(f"交易后，baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"交易后，quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("交易后，R状态: {}".format(R))
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))
        assert expectedBase == int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_BASE_BALANCE_"])
        assert expectedQuote == int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_QUOTE_BALANCE_"])
        assert expectedBaseTarget == int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
        assert expectedQuoteTarget == int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
        assert newR == dodoInfo2["dodos"]["_R_STATUS_"], "交易后R状态: {}".format(dodoInfo2["dodos"]["_R_STATUS_"])

        assert tradeAccount2[baseToken] - tradeAccount[baseToken] == buyAmount, "交易账户base资产不正确"
        assert tradeAccount2[quoteToken] + spentQuote == tradeAccount[quoteToken], "交易账户quote资产不正确"
        assert maintainerAccount2[baseToken] - maintainerAccount[baseToken] == mtfee, "维护账户quote资产不正确"
        assert maintainerAccount2[quoteToken] == maintainerAccount[quoteToken], "维护账户quote资产不正确"

    def checkBuyBaseTokenBuyAmountWhenPriceBellow(self, dodoName):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行buyBase测试。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))

        curPrice = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(f"curPrice: {curPrice}")

        expectedPrice = to_wei_asset(curPrice * 0.5 / DecimalMath.one, quoteToken, quoteTokenDecimal)
        logger.info(f"expectedPrice: {expectedPrice}")
        self.client.setprice(oracleadmin, to_sym(baseToken, baseTokenDecimal), expectedPrice)
        time.sleep(2)
        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)

        buyAmount = 100000
        spentQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = queryBuyBaseToken(buyAmount, dodoInfo,
                                                                                          dodoName,
                                                                                          price)
        logger.info(f"准备购买baseToken的数量为: {buyAmount}")
        parseBuyAmout = buyAmount / int(math.pow(10, baseTokenDecimal))
        parseSpentAmout = spentQuote / int(math.pow(10, quoteTokenDecimal))
        logger.info("交易账户授权。。")
        self.client.allowDosContract(trader, acc2pub_keys[trader])
        logger.info("准备进行交易。。")
        tx_res = self.client.buybasetoken(trader, dodoName, to_wei_asset(parseBuyAmout, baseToken, baseTokenDecimal),
                                          to_wei_asset(parseSpentAmout, quoteToken, quoteTokenDecimal))
        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)

        # 计算预期的资产信息
        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"]) - (buyAmount + mtfee)
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"]) + spentQuote
        expectedBaseTarget = newBaseTarget + lpfee
        expectedQuoteTarget = newQuoteTarget
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))
        # 打印交易后资产信息
        logger.info(f"交易后，baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"交易后，quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("交易后，R状态: {}".format(R))
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))
        assert expectedBase == int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_BASE_BALANCE_"])
        assert expectedQuote == int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_QUOTE_BALANCE_"])
        assert expectedBaseTarget == int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
        assert expectedQuoteTarget == int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
        assert newR == dodoInfo2["dodos"]["_R_STATUS_"], "交易后R状态: {}".format(dodoInfo2["dodos"]["_R_STATUS_"])

        assert tradeAccount2[baseToken] - tradeAccount[baseToken] == buyAmount, "交易账户base资产不正确"
        assert tradeAccount2[quoteToken] + spentQuote == tradeAccount[quoteToken], "交易账户quote资产不正确"
        assert maintainerAccount2[baseToken] - maintainerAccount[baseToken] == mtfee, "维护账户quote资产不正确"
        assert maintainerAccount2[quoteToken] == maintainerAccount[quoteToken], "维护账户quote资产不正确"

    def checkBuyBaseTokenBuyWrongBase(self, dodoName):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行buyBase测试。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)

        buyAmount = 1000000
        spentQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = queryBuyBaseToken(buyAmount, dodoInfo,
                                                                                          dodoName,
                                                                                          price)
        logger.info(f"准备购买baseToken的数量为: {buyAmount}")
        parseBuyAmout = buyAmount / int(math.pow(10, baseTokenDecimal))
        parseSpentAmout = spentQuote / int(math.pow(10, quoteTokenDecimal))
        logger.info("交易账户授权。。")
        self.client.allowDosContract(trader, acc2pub_keys[trader])
        logger.info("准备进行交易。。")
        tx_res = self.client.buybasetoken(trader, dodoName, to_wei_asset(parseBuyAmout, baseToken+"A", baseTokenDecimal),
                                          to_wei_asset(parseSpentAmout, quoteToken, quoteTokenDecimal))
        assert tx_res["code"] == 500, "不能购买错误的base"
        assert "no base token symbol in the pair" in tx_res["error"]["details"][0]["message"], "不能购买超出池子的数量"
        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)

        # 计算预期的资产信息
        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"])
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"])
        expectedBaseTarget = int(dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_'])
        expectedQuoteTarget = int(dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_'])
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))
        # 打印交易后资产信息
        logger.info(f"交易后，baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"交易后，quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("交易后，R状态: {}".format(R))
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))
        assert expectedBase == int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_BASE_BALANCE_"])
        assert expectedQuote == int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_QUOTE_BALANCE_"])
        assert expectedBaseTarget == int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
        assert expectedQuoteTarget == int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
        assert dodoInfo["dodos"]["_R_STATUS_"] == dodoInfo2["dodos"]["_R_STATUS_"], "交易后R状态: {}".format(dodoInfo2["dodos"]["_R_STATUS_"])

        assert tradeAccount2[baseToken] - tradeAccount[baseToken] == 0, "交易账户base资产不正确"
        assert tradeAccount2[quoteToken] == tradeAccount[quoteToken], "交易账户quote资产不正确"
        assert maintainerAccount2[baseToken] - maintainerAccount[baseToken] == 0, "维护账户quote资产不正确"
        assert maintainerAccount2[quoteToken] == maintainerAccount[quoteToken], "维护账户quote资产不正确"

    def checkSellBaseToken(self, dodoName, sellAmount=10000, minReceiveQuote=None, isExcute=True):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行buyBase测试，购买base使R状态由0变为1, 实际价格和oracle价格要高。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        contract = dodoInfo["dodos"]["_BASE_TOKEN_"]["contract"]
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        logger.info("当前R状态为: {}".format(R))
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))
        poolBalance = self.getAccountBalance(dodoName, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，池子实际持有的资产: {}".format(poolBalance))

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)
        # buyAmount = 100000
        spentQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = querySellBaseToken(sellAmount, dodoInfo,
                                                                                           dodoName,
                                                                                           price)
        logger.info(f"准备购买baseToken的数量为: {sellAmount}")

        parseSellAmount = sellAmount / int(math.pow(10, baseTokenDecimal))
        parseReceiveAmount = spentQuote / int(math.pow(10, quoteTokenDecimal))
        if minReceiveQuote:
            parseReceiveAmount = minReceiveQuote
        if isExcute:
            # logger.info("交易账户授权。。")
            # self.client.allowDosContract(trader, acc2pub_keys[trader])
            logger.info("准备进行交易。。")
            tx = self.client.sellbasetoken(trader, dodoName, to_wei_asset(parseSellAmount, baseToken, baseTokenDecimal, contract),
                                           to_wei_asset(parseReceiveAmount * 10, quoteToken, quoteTokenDecimal, contract))
            if "code" in tx:
                errMsg = tx["error"]["details"][0]["message"]
                contractAmount = int(errMsg.split(":")[-1].strip().split("SELL_BASE_RECEIVE_NOT_ENOUGH")[-1])
                tx = self.client.sellbasetoken(trader, dodoName,
                                               to_wei_asset(parseSellAmount, baseToken, baseTokenDecimal, contract),
                                               to_wei_asset(parseReceiveAmount, quoteToken, quoteTokenDecimal,contract))

            time.sleep(2)
        quotefee = get_transfer_fee(contractAmount, quoteToken, True, contract)
        baseFee = get_transfer_fee(sellAmount, baseToken, False, contract)
        logger.info("用户转账{} base的费用: {}".format(sellAmount, baseFee))
        logger.info("合约中计算quote的数量: {},转账费用为: {}".format(contractAmount, quotefee))
        logger.info("合约计算的偏差: {}".format(contractAmount - spentQuote))

        mtTransferFee = get_transfer_fee(mtfee, quoteToken, True, contract)
        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"]) + sellAmount
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"]) - contractAmount - mtfee
        expectedBaseTarget = newBaseTarget
        expectedQuoteTarget = newQuoteTarget + lpfee
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))

        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)
        poolBalance2 = self.getAccountBalance(dodoName, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易后，池子实际持有的资产: {}".format(poolBalance2))
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))
        logger.info("池子base变化: {}".format(int(dodoInfo2["dodos"]["_BASE_BALANCE_"]) - int(dodoInfo["dodos"]["_BASE_BALANCE_"])))
        logger.info("池子quote变化: {}".format(int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]) - int(dodoInfo["dodos"]["_QUOTE_BALANCE_"])))
        logger.info("池子baseTarget变化: {}".format(int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]) - int(dodoInfo["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])))
        logger.info("池子quoteTarget变化: {}".format(int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]) - int(dodoInfo["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])))

        logger.info("池子实际持有的base资产变化: {}".format(poolBalance2[baseToken] - poolBalance[baseToken]))
        logger.info("池子实际持有的quote资产变化: {}".format(poolBalance2[quoteToken] - poolBalance[quoteToken]))

        logger.info("池子和记录的实际base资产减少了: {}".format(poolBalance2[baseToken] - int(dodoInfo2["dodos"]["_BASE_BALANCE_"])))
        logger.info("池子和记录的实际quote资产减少了: {}".format(poolBalance2[quoteToken] - int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"])))

        logger.info("用户实际持有的base资产变化: {}".format(tradeAccount2[baseToken] - tradeAccount[baseToken]))
        logger.info("用户实际持有的quote资产变化: {}".format(tradeAccount2[quoteToken] - tradeAccount[quoteToken]))

        r1 = assertEqualOnlyShowLog(expectedBase, int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "检查池子的baseBalance")
        r2 = assertEqualOnlyShowLog(expectedQuote, int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "检查池子的quoteBalance")
        r3 = assertEqualOnlyShowLog(expectedBaseTarget, int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]),
                               "检查池子的targetBaseBalance")
        r4 = assertEqualOnlyShowLog(expectedQuoteTarget, int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]),
                               "检查池子的targetQuoteBalance")
        r5 = assertEqualOnlyShowLog(newR, dodoInfo2["dodos"]["_R_STATUS_"], "检查R状态")
        r6 = assertEqualOnlyShowLog(tradeAccount[baseToken] - tradeAccount2[baseToken], sellAmount + baseFee, "检查用户的baseBalance")
        r7 = assertEqualOnlyShowLog(tradeAccount2[quoteToken] - tradeAccount[quoteToken], contractAmount - quotefee, "检查用户的quoteBalance")
        r8 = assertEqualOnlyShowLog(maintainerAccount2[baseToken], maintainerAccount[baseToken], "检查维护账户的base资产")
        r9 = assertEqualOnlyShowLog(maintainerAccount2[quoteToken] - maintainerAccount[quoteToken], mtfee - mtTransferFee,"检查维护账户的quote资产")
        r10 = assertEqualOnlyShowLog(int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), poolBalance2[baseToken], "检查池子实际持有的base资产")
        r11 = assertEqualOnlyShowLog(int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), poolBalance2[quoteToken], "检查池子实际持有的quote资产")

        poolBaseChange = int(dodoInfo2["dodos"]["_BASE_BALANCE_"]) - int(dodoInfo["dodos"]["_BASE_BALANCE_"])
        poolQuoteChange = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"]) - int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"])
        logger.info("base: {}, quote: {}, 价格: {}".format(sellAmount, tradeAccount2[quoteToken] - tradeAccount[quoteToken], (tradeAccount2[quoteToken] - tradeAccount[quoteToken]) / sellAmount))
        logger.info("pool base: {}, quote: {}, 价格: {}".format(poolBaseChange, poolQuoteChange, poolQuoteChange / poolBaseChange))

        if r1 or r2 or r3 or r4 or r5 or r6 or r7 or r8 or r9 or r10 or r11:
            assert False, "有检查失败"
        # assert expectedBase == int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "交易后资产: {}".format(
        #     dodoInfo2["dodos"]["_BASE_BALANCE_"])
        # assert expectedQuote == int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "交易后资产: {}".format(
        #     dodoInfo2["dodos"]["_QUOTE_BALANCE_"])
        # assert expectedBaseTarget == int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
        #     dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
        # assert expectedQuoteTarget == int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
        #     dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
        # assert newR == dodoInfo2["dodos"]["_R_STATUS_"], "交易后R状态: {}".format(dodoInfo2["dodos"]["_R_STATUS_"])

        # assert tradeAccount2[baseToken] + sellAmount == tradeAccount[baseToken], "交易账户base资产不正确"
        # assert tradeAccount2[quoteToken] - spentQuote == tradeAccount[quoteToken], "交易账户quote资产不正确"
        # assert maintainerAccount2[baseToken] == maintainerAccount[baseToken], "维护账户quote资产不正确"
        # assert maintainerAccount2[quoteToken] - maintainerAccount[quoteToken] == mtfee, "维护账户quote资产不正确"

    def checkSellBaseTokenRStatus0to2(self, dodoName, sellAmount=10000):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行buyBase测试，购买base使R状态由0变为1, 实际价格和oracle价格要高。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        if R != 0:
            logger.info("当前R状态为: {}, 暂不执行此用例".format(R))
            return
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)
        # buyAmount = 100000
        spentQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = querySellBaseToken(sellAmount, dodoInfo,
                                                                                           dodoName,
                                                                                           price)
        logger.info(f"准备购买baseToken的数量为: {sellAmount}")
        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"]) + sellAmount
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"]) - spentQuote - mtfee
        expectedBaseTarget = newBaseTarget
        expectedQuoteTarget = newQuoteTarget + lpfee
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))

        parseSellAmount = sellAmount / int(math.pow(10, baseTokenDecimal))
        parseReceiveAmount = spentQuote / int(math.pow(10, quoteTokenDecimal))
        logger.info("交易账户授权。。")
        self.client.allowDosContract(trader, acc2pub_keys[trader])
        logger.info("准备进行交易。。")
        self.client.sellbasetoken(trader, dodoName, to_wei_asset(parseSellAmount, baseToken, baseTokenDecimal),
                                  to_wei_asset(parseReceiveAmount, quoteToken, quoteTokenDecimal))
        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))
        assert expectedBase == int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_BASE_BALANCE_"])
        assert expectedQuote == int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_QUOTE_BALANCE_"])
        assert expectedBaseTarget == int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
        assert expectedQuoteTarget == int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
        assert newR == dodoInfo2["dodos"]["_R_STATUS_"], "交易后R状态: {}".format(dodoInfo2["dodos"]["_R_STATUS_"])

        assert tradeAccount2[baseToken] + sellAmount == tradeAccount[baseToken], "交易账户base资产不正确"
        assert tradeAccount2[quoteToken] - spentQuote == tradeAccount[quoteToken], "交易账户quote资产不正确"
        assert maintainerAccount2[baseToken] == maintainerAccount[baseToken], "维护账户quote资产不正确"
        assert maintainerAccount2[quoteToken] - maintainerAccount[quoteToken] == mtfee, "维护账户quote资产不正确"

    def checkSellBaseTokenRStatus1to1(self, dodoName):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行SellBase测试，卖出base使R状态改变为1, 实际价格和oracle价格要高。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        if R != 1:
            logger.info("当前R状态为: {}, 暂不执行此用例".format(R))
            return
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)

        newBaseTarget, _newQuoteTarget = getExpectedTarget(dodoInfo, price)
        baseRange = newBaseTarget - int(dodoInfo['dodos']['_BASE_BALANCE_'])
        logger.info("想要保持R状态不变, 购买的baseToken加上费用用不能超过: {}".format(baseRange))

        sellAmount = baseRange // 2
        logger.info(f"为了保证R状态不变, 准备购买baseToken的数量为: {sellAmount}")
        spentQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = querySellBaseToken(sellAmount, dodoInfo,
                                                                                          dodoName,
                                                                                          price)
        expectedResult = True if baseRange > 0 else False
        logger.info(f"准备购买baseToken的数量为: {sellAmount}")

        parseSellAmout = sellAmount / int(math.pow(10, baseTokenDecimal))
        parseSpentAmout = spentQuote / int(math.pow(10, quoteTokenDecimal))
        logger.info("交易账户授权。。")
        self.client.allowDosContract(trader, acc2pub_keys[trader])
        logger.info("准备进行交易。。")
        tx_res = self.client.sellbasetoken(trader, dodoName, to_wei_asset(parseSellAmout, baseToken, baseTokenDecimal),
                                           to_wei_asset(parseSpentAmout, quoteToken, quoteTokenDecimal))
        if expectedResult is False:
            assert tx_res["code"] == 500, f"当执行交易所需资产为{sellAmount}时, 执行交易失败, 因为转账金额不能为0"
            assert 'must transfer positive quantity' in tx_res["error"]["details"][0][
                "message"], "报错不是static_transfer引起的"
            logger.info("R状态由1改变为1，执行交易失败")
            return

        time.sleep(2)

        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"]) + sellAmount
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"]) - spentQuote - mtfee
        expectedBaseTarget = newBaseTarget
        expectedQuoteTarget = newQuoteTarget + lpfee
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))

        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))
        assert expectedBase == int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_BASE_BALANCE_"])
        assert expectedQuote == int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_QUOTE_BALANCE_"])
        assert expectedBaseTarget == int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
        assert expectedQuoteTarget == int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
        assert newR == dodoInfo2["dodos"]["_R_STATUS_"], "交易后R状态: {}".format(dodoInfo2["dodos"]["_R_STATUS_"])

        assert tradeAccount2[baseToken] + sellAmount == tradeAccount[baseToken], "交易账户base资产不正确"
        assert tradeAccount2[quoteToken] - spentQuote == tradeAccount[quoteToken], "交易账户quote资产不正确"
        assert maintainerAccount2[baseToken] == maintainerAccount[baseToken], "维护账户quote资产不正确"
        assert maintainerAccount2[quoteToken] - maintainerAccount[quoteToken] == mtfee, "维护账户quote资产不正确"

    def checkSellBaseTokenRStatus1to0(self, dodoName):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行sellBase测试，卖出base使R状态改变为0, 实际价格和oracle价格要高。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        if R != 1:
            logger.info("当前R状态为: {}, 暂不执行此用例".format(R))
            return
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)

        newBaseTarget, _newQuoteTarget = getExpectedTarget(dodoInfo, price)
        baseRange = newBaseTarget - int(dodoInfo['dodos']['_BASE_BALANCE_'])
        logger.info("想要保持R状态不变, 购买的baseToken加上费用用不能超过: {}".format(baseRange))

        sellAmount = baseRange
        spentQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = querySellBaseToken(sellAmount, dodoInfo,
                                                                                          dodoName,
                                                                                          price)
        expectedResult = True if baseRange > 0 else False
        logger.info(f"准备卖出baseToken的数量为: {sellAmount}")

        parseSellAmout = sellAmount / int(math.pow(10, baseTokenDecimal))
        parseSpentAmout = spentQuote / int(math.pow(10, quoteTokenDecimal))
        logger.info("交易账户授权。。")
        self.client.allowDosContract(trader, acc2pub_keys[trader])
        logger.info("准备进行交易。。")
        tx_res = self.client.sellbasetoken(trader, dodoName, to_wei_asset(parseSellAmout, baseToken, baseTokenDecimal),
                                           to_wei_asset(parseSpentAmout, quoteToken, quoteTokenDecimal))
        if expectedResult is False:
            assert tx_res["code"] == 500, f"当执行交易所需资产为{sellAmount}时, 执行交易失败, 因为转账金额不能为0"
            assert 'must transfer positive quantity' in tx_res["error"]["details"][0][
                "message"], "报错不是static_transfer引起的"
            logger.info("R状态由1改变为0，执行交易失败")
            return

        time.sleep(2)

        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"]) + sellAmount
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"]) - spentQuote - mtfee
        expectedBaseTarget = newBaseTarget
        expectedQuoteTarget = newQuoteTarget + lpfee
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))

        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))
        assert expectedBase == int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_BASE_BALANCE_"])
        assert expectedQuote == int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_QUOTE_BALANCE_"])
        assert expectedBaseTarget == int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
        assert expectedQuoteTarget == int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
        assert newR == dodoInfo2["dodos"]["_R_STATUS_"], "交易后R状态: {}".format(dodoInfo2["dodos"]["_R_STATUS_"])

        assert tradeAccount2[baseToken] + sellAmount == tradeAccount[baseToken], "交易账户base资产不正确"
        assert tradeAccount2[quoteToken] - spentQuote == tradeAccount[quoteToken], "交易账户quote资产不正确"
        assert maintainerAccount2[baseToken] == maintainerAccount[baseToken], "维护账户quote资产不正确"
        assert maintainerAccount2[quoteToken] - maintainerAccount[quoteToken] == mtfee, "维护账户quote资产不正确"

    def checkSellBaseTokenRStatus1to2(self, dodoName):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行sellBase测试，卖出base使R状态改变为2, 实际价格和oracle价格要高。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        if R != 1:
            logger.info("当前R状态为: {}, 暂不执行此用例".format(R))
            return
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)

        newBaseTarget, _newQuoteTarget = getExpectedTarget(dodoInfo, price)
        baseRange = newBaseTarget - int(dodoInfo['dodos']['_BASE_BALANCE_'])
        logger.info("想要保持R状态不变, 购买的baseToken加上费用用不能超过: {}".format(baseRange))

        sellAmount = baseRange + 10000
        spentQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = querySellBaseToken(sellAmount, dodoInfo,
                                                                                          dodoName,
                                                                                          price)
        expectedResult = True if sellAmount > 0 else False
        logger.info(f"准备sellBaseToken的数量为: {sellAmount}")

        parseSellAmout = sellAmount / int(math.pow(10, baseTokenDecimal))
        parseSpentAmout = spentQuote / int(math.pow(10, quoteTokenDecimal))
        logger.info("交易账户授权。。")
        self.client.allowDosContract(trader, acc2pub_keys[trader])
        logger.info("准备进行交易。。")
        tx_res = self.client.sellbasetoken(trader, dodoName, to_wei_asset(parseSellAmout, baseToken, baseTokenDecimal),
                                           to_wei_asset(parseSpentAmout, quoteToken, quoteTokenDecimal))
        if expectedResult is False:
            assert tx_res["code"] == 500, f"当执行交易所需资产为{sellAmount}时, 执行交易失败, 因为转账金额不能为0"
            assert 'must transfer positive quantity' in tx_res["error"]["details"][0][
                "message"], "报错不是static_transfer引起的"
            logger.info("R状态由1改变为0，执行交易失败")
            return

        time.sleep(2)

        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"]) + sellAmount
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"]) - spentQuote - mtfee
        expectedBaseTarget = newBaseTarget
        expectedQuoteTarget = newQuoteTarget + lpfee
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))

        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))
        assert expectedBase == int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_BASE_BALANCE_"])
        assert expectedQuote == int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_QUOTE_BALANCE_"])
        assert expectedBaseTarget == int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
        assert expectedQuoteTarget == int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
        assert newR == dodoInfo2["dodos"]["_R_STATUS_"], "交易后R状态: {}".format(dodoInfo2["dodos"]["_R_STATUS_"])

        assert tradeAccount2[baseToken] + sellAmount == tradeAccount[baseToken], "交易账户base资产不正确"
        assert tradeAccount2[quoteToken] - spentQuote == tradeAccount[quoteToken], "交易账户quote资产不正确"
        assert maintainerAccount2[baseToken] == maintainerAccount[baseToken], "维护账户quote资产不正确"
        assert maintainerAccount2[quoteToken] - maintainerAccount[quoteToken] == mtfee, "维护账户quote资产不正确"

    def checkSellBaseTokenRStatus2to2(self, dodoName, sellAmount=100000):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行sellBase测试，购买base使R状态由2变为2, 实际价格和oracle价格要高。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        if R != 2:
            logger.info("当前R状态为: {}, 暂不执行此用例".format(R))
            return
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                   baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)
        # buyAmount = 100000
        spentQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = querySellBaseToken(sellAmount, dodoInfo,
                                                                                           dodoName,
                                                                                           price)
        logger.info(f"准备sellBaseToken的数量为: {sellAmount}")
        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"]) + sellAmount
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"]) - spentQuote - mtfee
        expectedBaseTarget = newBaseTarget
        expectedQuoteTarget = newQuoteTarget + lpfee
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))

        parseSellAmount = sellAmount / int(math.pow(10, baseTokenDecimal))
        parseReceiveAmount = spentQuote / int(math.pow(10, quoteTokenDecimal))
        logger.info("交易账户授权。。")
        self.client.allowDosContract(trader, acc2pub_keys[trader])
        logger.info("准备进行交易。。")
        self.client.sellbasetoken(trader, dodoName, to_wei_asset(parseSellAmount, baseToken, baseTokenDecimal),
                                  to_wei_asset(parseReceiveAmount, quoteToken, quoteTokenDecimal))
        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))
        assert expectedBase == int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_BASE_BALANCE_"])
        assert expectedQuote == int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_QUOTE_BALANCE_"])
        assert expectedBaseTarget == int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
        assert expectedQuoteTarget == int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
        assert newR == dodoInfo2["dodos"]["_R_STATUS_"], "交易后R状态: {}".format(dodoInfo2["dodos"]["_R_STATUS_"])

        assert tradeAccount2[baseToken] + sellAmount == tradeAccount[baseToken], "交易账户base资产不正确"
        assert tradeAccount2[quoteToken] - spentQuote == tradeAccount[quoteToken], "交易账户quote资产不正确"
        assert maintainerAccount2[baseToken] == maintainerAccount[baseToken], "维护账户base资产不正确"
        assert maintainerAccount2[quoteToken] - maintainerAccount[quoteToken] == mtfee, "维护账户quote资产不正确"

    def checkSellBaseTokenMinAmount(self, dodoName):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行sellBase测试,卖出可成交的最小数量。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)

        sellAmount = 1
        receiveQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = querySellBaseToken(sellAmount, dodoInfo,
                                                                                          dodoName, price)
        excuteResult = True if receiveQuote > 0 else False
        logger.info(f"准备sellBaseToken的数量为: {sellAmount}")
        parseBuyAmout = sellAmount / int(math.pow(10, baseTokenDecimal))
        parseSpentAmout = receiveQuote / int(math.pow(10, quoteTokenDecimal))
        logger.info("交易账户授权。。")
        self.client.allowDosContract(trader, acc2pub_keys[trader])
        logger.info("准备进行交易。。")
        tx_res = self.client.sellbasetoken(trader, dodoName, to_wei_asset(parseBuyAmout, baseToken, baseTokenDecimal),
                                          to_wei_asset(parseSpentAmout, quoteToken, quoteTokenDecimal))

        if excuteResult is False:
            assert tx_res["code"] == 500, "当执行交易所需资产为时,执行交易失败, 因为转账金额不能为0"
            assert 'must transfer positive quantity' in tx_res["error"]["details"][0]["message"], "报错不是static_transfer引起的"
            return
        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)

        # 计算预期的资产信息
        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"]) + sellAmount
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"]) - receiveQuote - mtfee
        expectedBaseTarget = newBaseTarget
        expectedQuoteTarget = newQuoteTarget + lpfee
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))
        # 打印交易后资产信息
        logger.info(f"交易后，baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"交易后，quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("交易后，R状态: {}".format(R))
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))
        assert expectedBase == int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_BASE_BALANCE_"])
        assert expectedQuote == int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_QUOTE_BALANCE_"])
        assert expectedBaseTarget == int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
        assert expectedQuoteTarget == int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
        assert newR == dodoInfo2["dodos"]["_R_STATUS_"], "交易后R状态: {}".format(dodoInfo2["dodos"]["_R_STATUS_"])

        assert tradeAccount2[baseToken] + sellAmount == tradeAccount[baseToken], "交易账户base资产不正确"
        assert tradeAccount2[quoteToken] - receiveQuote == tradeAccount[quoteToken], f"交易账户quote资产不正确: {tradeAccount2[quoteToken] - tradeAccount[quoteToken]} {receiveQuote}"
        assert maintainerAccount2[baseToken] == maintainerAccount[baseToken], "维护账户quote资产不正确"
        assert maintainerAccount2[quoteToken] - maintainerAccount[quoteToken] == mtfee, "维护账户quote资产不正确"

    def checkSellBaseTokenSellAcceptMinAmount(self, dodoName):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行sellBase测试,卖出可成交的最小数量。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)

        sellAmount = 1
        while True:
            receiveQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = querySellBaseToken(sellAmount, dodoInfo,
                                                                                              dodoName,
                                                                                              price)
            if receiveQuote > 0:
                break
            else:
                sellAmount += 1
        logger.info(f"准备购买baseToken的数量为: {sellAmount}")
        parseBuyAmout = sellAmount / int(math.pow(10, baseTokenDecimal))
        parseSpentAmout = receiveQuote / int(math.pow(10, quoteTokenDecimal))
        logger.info("交易账户授权。。")
        self.client.allowDosContract(trader, acc2pub_keys[trader])
        logger.info("准备进行交易。。")
        tx_res = self.client.sellbasetoken(trader, dodoName, to_wei_asset(parseBuyAmout, baseToken, baseTokenDecimal),
                                          to_wei_asset(parseSpentAmout, quoteToken, quoteTokenDecimal))

        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)

        # 计算预期的资产信息
        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"]) + sellAmount
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"]) - receiveQuote - mtfee
        expectedBaseTarget = newBaseTarget
        expectedQuoteTarget = newQuoteTarget + lpfee
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))
        # 打印交易后资产信息
        logger.info(f"交易后，baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"交易后，quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("交易后，R状态: {}".format(R))
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))
        assert expectedBase == int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_BASE_BALANCE_"])
        assert expectedQuote == int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_QUOTE_BALANCE_"])
        assert expectedBaseTarget == int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
        assert expectedQuoteTarget == int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
        assert newR == dodoInfo2["dodos"]["_R_STATUS_"], "交易后R状态: {}".format(dodoInfo2["dodos"]["_R_STATUS_"])

        assert tradeAccount2[baseToken] + sellAmount == tradeAccount[baseToken], "交易账户base资产不正确"
        assert tradeAccount2[quoteToken] - receiveQuote == tradeAccount[quoteToken], f"交易账户quote资产不正确: {tradeAccount2[quoteToken] - tradeAccount[quoteToken]} {receiveQuote}"
        assert maintainerAccount2[baseToken] == maintainerAccount[baseToken], "维护账户quote资产不正确"
        assert maintainerAccount2[quoteToken] - maintainerAccount[quoteToken] == mtfee, "维护账户quote资产不正确"

    # 此用例没有实际场景
    def checkSellBaseTokenAmountExceedPoolNumber(self, dodoName):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行sellBase测试。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)

        sellAmount = tradeAccount[baseToken] + 1000000
        receiveQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = querySellBaseToken(sellAmount, dodoInfo,
                                                                                             dodoName,
                                                                                             price)
        logger.info(f"准备卖出baseToken的数量为: {sellAmount}")
        parseBuyAmout = sellAmount / int(math.pow(10, baseTokenDecimal))
        parseSpentAmout = receiveQuote / int(math.pow(10, quoteTokenDecimal))
        logger.info("交易账户授权。。")
        self.client.allowDosContract(trader, acc2pub_keys[trader])
        logger.info("准备进行交易。。")
        tx_res = self.client.sellbasetoken(trader, dodoName, to_wei_asset(parseBuyAmout, baseToken, baseTokenDecimal),
                                          to_wei_asset(parseSpentAmout, quoteToken, quoteTokenDecimal))

        assert tx_res["code"] == 500, "不能购买超出池子的数量"
        assert "DODO_BASE_BALANCE_NOT_ENOUGH" in tx_res["error"]["details"][0]["message"], "不能购买超出池子的数量"
        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)

        # 计算预期的资产信息
        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"])
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"])
        expectedBaseTarget = int(dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_'])
        expectedQuoteTarget = int(dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_'])
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))
        # 打印交易后资产信息
        logger.info(f"交易后，baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"交易后，quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("交易后，R状态: {}".format(R))
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))
        assert expectedBase == int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_BASE_BALANCE_"])
        assert expectedQuote == int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_QUOTE_BALANCE_"])
        assert expectedBaseTarget == int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
        assert expectedQuoteTarget == int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
        assert newR == dodoInfo2["dodos"]["_R_STATUS_"], "交易后R状态: {}".format(dodoInfo2["dodos"]["_R_STATUS_"])

        assert tradeAccount2[baseToken] == tradeAccount[baseToken], "交易账户base资产不正确"
        assert tradeAccount2[quoteToken] == tradeAccount[quoteToken], "交易账户quote资产不正确"
        assert maintainerAccount2[baseToken] == maintainerAccount[baseToken], "维护账户quote资产不正确"
        assert maintainerAccount2[quoteToken] - maintainerAccount[quoteToken] == 0, "维护账户quote资产不正确"

    def checkSellBaseTokenSellAmountExceedSelfWalletNumber(self, dodoName):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行sellBase测试。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)

        sellAmount = tradeAccount[baseToken] + 1000000
        spentQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = querySellBaseToken(sellAmount, dodoInfo,
                                                                                          dodoName,
                                                                                          price)
        logger.info(f"准备sellBaseToken的数量为: {sellAmount}")
        parseBuyAmout = sellAmount / int(math.pow(10, baseTokenDecimal))
        parseSpentAmout = spentQuote / int(math.pow(10, quoteTokenDecimal))
        logger.info("交易账户授权。。")
        self.client.allowDosContract(trader, acc2pub_keys[trader])
        logger.info("准备进行交易。。")
        tx_res = self.client.sellbasetoken(trader, dodoName,
                                           to_wei_asset(parseBuyAmout, baseToken, baseTokenDecimal),
                                           to_wei_asset(parseSpentAmout, quoteToken, quoteTokenDecimal))

        assert tx_res["code"] == 500, "不能购买超出自身资产的数量"
        assert "overdrawn balance" in tx_res["error"]["details"][0]["message"], "不能购买超出自身资产的数量"
        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)

        # 计算预期的资产信息
        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"])
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"])
        expectedBaseTarget = int(dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_'])
        expectedQuoteTarget = int(dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_'])
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))
        # 打印交易后资产信息
        logger.info(f"交易后，baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"交易后，quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("交易后，R状态: {}".format(R))
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))
        assert expectedBase == int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_BASE_BALANCE_"])
        assert expectedQuote == int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_QUOTE_BALANCE_"])
        assert expectedBaseTarget == int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
        assert expectedQuoteTarget == int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
        assert newR == dodoInfo2["dodos"]["_R_STATUS_"], "交易后R状态: {}".format(dodoInfo2["dodos"]["_R_STATUS_"])

        assert tradeAccount2[baseToken] - tradeAccount[baseToken] == 0, "交易账户base资产不正确"
        assert tradeAccount2[quoteToken] == tradeAccount[quoteToken], "交易账户quote资产不正确"
        assert maintainerAccount2[baseToken] - maintainerAccount[baseToken] == 0, "维护账户quote资产不正确"
        assert maintainerAccount2[quoteToken] == maintainerAccount[quoteToken], "维护账户quote资产不正确"

    def checkSellBaseTokenAmountDecimalWrong(self, dodoName):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行buyBase测试。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)

        sellAmount = 111112
        spentQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = querySellBaseToken(sellAmount, dodoInfo,
                                                                                           dodoName, price)
        logger.info(f"准备购买baseToken的数量为: {sellAmount}")
        parseBuyAmout = sellAmount / int(math.pow(10, baseTokenDecimal + 1))
        parseSpentAmout = spentQuote / int(math.pow(10, quoteTokenDecimal))
        logger.info("交易账户授权。。")
        self.client.allowDosContract(trader, acc2pub_keys[trader])
        logger.info("准备进行交易。。")
        tx_res = self.client.sellbasetoken(trader, dodoName,
                                           to_wei_asset(parseBuyAmout, baseToken, baseTokenDecimal + 1),
                                           to_wei_asset(parseSpentAmout, quoteToken, quoteTokenDecimal))

        assert tx_res["code"] == 500, "不能购买超出池子的数量"
        assert "mismatch precision of the base token in the pair" in tx_res["error"]["details"][0]["message"], "不能购买超出池子的数量"
        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)

        # 计算预期的资产信息
        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"])
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"])
        expectedBaseTarget = int(dodoInfo["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
        expectedQuoteTarget = int(dodoInfo["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))
        # 打印交易后资产信息
        logger.info(f"交易后，baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"交易后，quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("交易后，R状态: {}".format(R))
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))
        assert expectedBase == int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_BASE_BALANCE_"])
        assert expectedQuote == int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_QUOTE_BALANCE_"])
        assert expectedBaseTarget == int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
        assert expectedQuoteTarget == int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
        assert dodoInfo["dodos"]["_R_STATUS_"] == dodoInfo2["dodos"]["_R_STATUS_"], "交易后R状态: {}".format(dodoInfo2["dodos"]["_R_STATUS_"])

        assert tradeAccount2[baseToken] == tradeAccount[baseToken], "交易账户base资产不正确"
        assert tradeAccount2[quoteToken] == tradeAccount[quoteToken], "交易账户quote资产不正确"
        assert maintainerAccount2[baseToken] == maintainerAccount[baseToken], "维护账户quote资产不正确"
        assert maintainerAccount2[quoteToken] - maintainerAccount[quoteToken] == 0, "维护账户quote资产不正确"

    def checkSellBaseTokenAmountWhenPriceAbove(self, dodoName):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行buyBase测试。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))

        curPrice = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(f"curPrice: {curPrice}")

        expectedPrice = to_wei_asset(curPrice * 1.1 / DecimalMath.one, quoteToken, quoteTokenDecimal)
        logger.info(f"expectedPrice: {expectedPrice}")
        tx_res = self.client.setprice(oracleadmin, to_sym(baseToken, baseTokenDecimal), expectedPrice)

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)

        sellAmount = 10000
        spentQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = querySellBaseToken(
            sellAmount, dodoInfo, dodoName, price
        )
        logger.info(f"准备购买baseToken的数量为: {sellAmount}")
        parseBuyAmout = sellAmount / int(math.pow(10, baseTokenDecimal))
        parseSpentAmout = spentQuote / int(math.pow(10, quoteTokenDecimal))
        logger.info("交易账户授权。。")
        self.client.allowDosContract(trader, acc2pub_keys[trader])
        logger.info("准备进行交易。。")
        tx_res = self.client.sellbasetoken(trader, dodoName,
                                           to_wei_asset(parseBuyAmout, baseToken, baseTokenDecimal),
                                           to_wei_asset(parseSpentAmout, quoteToken, quoteTokenDecimal))
        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)

        # 计算预期的资产信息
        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"]) + sellAmount
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"]) - spentQuote - mtfee
        expectedBaseTarget = newBaseTarget
        expectedQuoteTarget = newQuoteTarget + lpfee
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))
        # 打印交易后资产信息
        logger.info(f"交易后，baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"交易后，quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("交易后，R状态: {}".format(R))
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))
        assert expectedBase == int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_BASE_BALANCE_"])
        assert expectedQuote == int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_QUOTE_BALANCE_"])
        assert expectedBaseTarget == int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
        assert expectedQuoteTarget == int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
        assert newR == dodoInfo2["dodos"]["_R_STATUS_"], "交易后R状态: {}".format(dodoInfo2["dodos"]["_R_STATUS_"])

        assert tradeAccount2[baseToken] + sellAmount == tradeAccount[baseToken], "交易账户base资产不正确"
        assert tradeAccount2[quoteToken] - spentQuote == tradeAccount[quoteToken], "交易账户quote资产不正确"
        assert maintainerAccount2[baseToken] == maintainerAccount[baseToken], "维护账户quote资产不正确"
        assert maintainerAccount2[quoteToken] - maintainerAccount[quoteToken] == mtfee, "维护账户quote资产不正确"

    def checkSellBaseTokenSellAmountWhenPriceBellow(self, dodoName):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行sellBase测试。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))

        curPrice = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(f"curPrice: {curPrice}")

        expectedPrice = to_wei_asset(curPrice * 0.5 / DecimalMath.one, quoteToken, quoteTokenDecimal)
        logger.info(f"expectedPrice: {expectedPrice}")
        self.client.setprice(oracleadmin, to_sym(baseToken, baseTokenDecimal), expectedPrice)
        time.sleep(2)
        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)

        sellAmount = 100000
        spentQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = querySellBaseToken(sellAmount, dodoInfo,
                                                                                           dodoName,
                                                                                           price)
        logger.info(f"准备购买baseToken的数量为: {sellAmount}")
        parseBuyAmout = sellAmount / int(math.pow(10, baseTokenDecimal))
        parseSpentAmout = spentQuote / int(math.pow(10, quoteTokenDecimal))
        logger.info("交易账户授权。。")
        self.client.allowDosContract(trader, acc2pub_keys[trader])
        logger.info("准备进行交易。。")
        tx_res = self.client.sellbasetoken(trader, dodoName,
                                           to_wei_asset(parseBuyAmout, baseToken, baseTokenDecimal),
                                           to_wei_asset(parseSpentAmout, quoteToken, quoteTokenDecimal))
        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)

        # 计算预期的资产信息
        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"]) + sellAmount
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"]) - spentQuote - mtfee
        expectedBaseTarget = newBaseTarget
        expectedQuoteTarget = newQuoteTarget + lpfee
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))
        # 打印交易后资产信息
        logger.info(f"交易后，baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"交易后，quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("交易后，R状态: {}".format(R))
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))
        assert expectedBase == int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_BASE_BALANCE_"])
        assert expectedQuote == int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_QUOTE_BALANCE_"])
        assert expectedBaseTarget == int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
        assert expectedQuoteTarget == int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
        assert newR == dodoInfo2["dodos"]["_R_STATUS_"], "交易后R状态: {}".format(dodoInfo2["dodos"]["_R_STATUS_"])

        assert tradeAccount2[baseToken] + sellAmount == tradeAccount[baseToken], "交易账户base资产不正确"
        assert tradeAccount2[quoteToken] - spentQuote == tradeAccount[quoteToken], "交易账户quote资产不正确"
        assert maintainerAccount2[baseToken] == maintainerAccount[baseToken], "维护账户quote资产不正确"
        assert maintainerAccount2[quoteToken] - maintainerAccount[quoteToken] == mtfee, "维护账户quote资产不正确"

    def checkSellBaseTokenSellWrongBase(self, dodoName):
        """

        :param dodoName: dodo name
        :return:
        检查buy base token
        """
        logger.info("开始进行SellBase测试。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        R = dodoInfo["dodos"]["_R_STATUS_"]
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("当前R状态: {}".format(R))

        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，trader的资产: {}".format(tradeAccount))
        logger.info("交易前, 维护账户的资产: {}".format(maintainerAccount))

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(price)

        sellAmount = 1000000
        spentQuote, newR, lpfee, mtfee, newBaseTarget, newQuoteTarget = querySellBaseToken(sellAmount, dodoInfo, dodoName, price)
        logger.info(f"准备购买baseToken的数量为: {sellAmount}")
        parseBuyAmout = sellAmount / int(math.pow(10, baseTokenDecimal))
        parseSpentAmout = spentQuote / int(math.pow(10, quoteTokenDecimal))
        logger.info("交易账户授权。。")
        self.client.allowDosContract(trader, acc2pub_keys[trader])
        logger.info("准备进行交易。。")
        tx_res = self.client.sellbasetoken(trader, dodoName,
                                           to_wei_asset(parseBuyAmout, baseToken+"A", baseTokenDecimal),
                                           to_wei_asset(parseSpentAmout, quoteToken, quoteTokenDecimal))
        assert tx_res["code"] == 500, "不能卖出不是这个池子的base资产"
        assert "no base token symbol in the pair" in tx_res["error"]["details"][0]["message"], "不能购买超出池子的数量"
        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainerAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                    baseTokenDecimal, quoteTokenDecimal)

        # 计算预期的资产信息
        expectedBase = int(dodoInfo["dodos"]["_BASE_BALANCE_"])
        expectedQuote = int(dodoInfo["dodos"]["_QUOTE_BALANCE_"])
        expectedBaseTarget = int(dodoInfo["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
        expectedQuoteTarget = int(dodoInfo["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
        logger.info("预期的base资产: {}".format(expectedBase))
        logger.info("预期的quote资产: {}".format(expectedQuote))
        logger.info("预期的baseTarget资产: {}".format(expectedBaseTarget))
        logger.info("预期的quoteTarget资产: {}".format(expectedQuoteTarget))
        logger.info("预期的R状态: {}".format(newR))
        # 打印交易后资产信息
        logger.info(f"交易后，baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"交易后，base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"交易后，quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info("交易后，R状态: {}".format(R))
        logger.info("交易后，trader的资产: {}".format(tradeAccount2))
        logger.info("交易后，维护账户的资产: {}".format(maintainerAccount2))
        logger.info("交易后, R状态为:{}".format(dodoInfo2["dodos"]["_R_STATUS_"]))
        assert expectedBase == int(dodoInfo2["dodos"]["_BASE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_BASE_BALANCE_"])
        assert expectedQuote == int(dodoInfo2["dodos"]["_QUOTE_BALANCE_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_QUOTE_BALANCE_"])
        assert expectedBaseTarget == int(dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
        assert expectedQuoteTarget == int(dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]), "交易后资产: {}".format(
            dodoInfo2["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
        assert dodoInfo["dodos"]["_R_STATUS_"] == dodoInfo2["dodos"]["_R_STATUS_"], "交易后R状态: {}".format(dodoInfo2["dodos"]["_R_STATUS_"])

        assert tradeAccount2[baseToken] == tradeAccount[baseToken], "交易账户base资产不正确"
        assert tradeAccount2[quoteToken] == tradeAccount[quoteToken], "交易账户quote资产不正确"
        assert maintainerAccount2[baseToken] == maintainerAccount[baseToken], "维护账户quote资产不正确"
        assert maintainerAccount2[quoteToken] - maintainerAccount[quoteToken] == 0, "维护账户quote资产不正确"

    def checkDepositBaseToken(self, dodoName, amount=100000, isDepositExceed=False, priceChange=False, priceTrend="up"):
        logger.info("开始进行depositBase测试。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(f"price: {price}")

        if priceChange:
            percent = 1.1 if priceTrend == "up" else 0.9
            expectedPrice = to_wei_asset(price * percent / DecimalMath.one, quoteToken, quoteTokenDecimal)
            logger.info(f"expectedPrice: {expectedPrice}")
            tx_res = self.client.setprice(oracleadmin, to_sym(baseToken, baseTokenDecimal), expectedPrice)

            price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
            logger.info(f"price: {price}")
        newBaseTargert, newQuoteTarget = getExpectedTarget(dodoInfo, price)
        totalBaseCapital = getTotalBaseCapital(baseToken, dodoName)
        totalQuoteCapital = getTotalQuoteCapital(quoteToken, dodoName)
        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                 baseTokenDecimal, quoteTokenDecimal)

        traderLPBalance = getBaseCapitalBalanceOf(trader, dodoName, baseToken)

        logger.info("newBaseTargert: {}".format(newBaseTargert))
        logger.info("newQuoteTarget: {}".format(newQuoteTarget))
        logger.info("base的信息: {}".format(totalBaseCapital))
        logger.info("quote的信息: {}".format(totalQuoteCapital))
        logger.info("提供lp的用户资产: {}".format(tradeAccount))
        logger.info("管理费用的用户资产: {}".format(maintainAccount))
        logger.info("用户在池子持有base的资产: {}".format(traderLPBalance))
        if isDepositExceed:
            amount = tradeAccount[baseToken] + amount

        capital = amount
        if totalBaseCapital == 0:
            capital = amount + newBaseTargert
        elif newBaseTargert > 0:
            capital = SafeMath.div(SafeMath.mul(amount, totalBaseCapital), newBaseTargert)
            logger.info("capital: {}".format(amount*totalBaseCapital/newBaseTargert))

        logger.info("用户{} 准备depositBase的资产:{}, 预计得到lp: {}".format(trader, amount, capital))
        contract = dodoInfo["dodos"]["_BASE_TOKEN_"]["contract"]
        fee = get_transfer_fee(amount, baseToken, False, contract)
        logger.info("用户转账费用为: {}".format(fee))
        # # 授权
        # self.client.allowDosContract(trader, acc2pub_keys[trader])
        # 进行充值

        parseAmount = amount / int(math.pow(10, baseTokenDecimal))
        tx_res = self.client.depositbase(trader, dodoName, to_wei_asset(parseAmount, baseToken, baseTokenDecimal, contract))
        if amount == 0:
            assert tx_res["code"] == 500, "depost 数量为0时，交易应失败"
            assert "must transfer positive quantity" in tx_res["error"]["details"][0]["message"], "depost 数量为0时，转账失败"
        if isDepositExceed:
            assert tx_res["code"] == 500, "depost 数量超过自身资产时，交易应失败"
            assert "overdrawn balance" in tx_res["error"]["details"][0]["message"], "depost 数量超过自身资产时，转账失败"
            # 用户资产，lp的supply没有变更
            amount = 0
            capital = 0
        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        totalBaseCapital2 = getTotalBaseCapital(baseToken, dodoName)
        totalQuoteCapital2 = getTotalQuoteCapital(quoteToken, dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                  baseTokenDecimal, quoteTokenDecimal)
        traderLPBalance2 = getBaseCapitalBalanceOf(trader, dodoName, baseToken)

        logger.info(f"充值后baseTarget资产: {dodoInfo2['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"充值后quoteTarget资产: {dodoInfo2['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"充值后base资产: {dodoInfo2['dodos']['_BASE_BALANCE_']}")
        logger.info(f"充值后quote资产: {dodoInfo2['dodos']['_QUOTE_BALANCE_']}")
        logger.info("base的信息: {}".format(totalBaseCapital))
        logger.info("quote的信息: {}".format(totalQuoteCapital))
        logger.info("提供lp的用户资产: {}".format(tradeAccount2))
        logger.info("管理费用的用户资产: {}".format(maintainAccount2))
        logger.info("用户在池子持有base的资产: {}".format(traderLPBalance2))

        assert int(dodoInfo2['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']) - int(dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']) == amount, "Pool baseTarget 资产添加不正确"
        assert int(dodoInfo2['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']) == int(dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']), "Pool quoteTarget 资产添加不正确"
        assert int(dodoInfo2['dodos']['_BASE_BALANCE_']) - int(dodoInfo['dodos']['_BASE_BALANCE_']) == amount, "Pool base资产添加不正确"
        assert int(dodoInfo2['dodos']['_QUOTE_BALANCE_']) == int(dodoInfo['dodos']['_QUOTE_BALANCE_']), "Pool quote资产添加不正确"

        assert tradeAccount[baseToken] - tradeAccount2[baseToken] == amount + fee, "用户base资产不正确"
        assert tradeAccount[quoteToken] - tradeAccount2[quoteToken] == 0, "用户quote资产不正确"

        assert totalBaseCapital2 == totalBaseCapital + capital, "base Supply 不正确"
        assert totalQuoteCapital2 == totalQuoteCapital, "quote Supply 不正确"

        assert maintainAccount2[baseToken] == maintainAccount[baseToken], "提现费用账户base资产计算不正确"
        assert maintainAccount2[quoteToken] == maintainAccount[quoteToken], "提现费用账户quote资产计算不正确"

        assert traderLPBalance2 == traderLPBalance + capital, "提现费用账户quote资产计算不正确, {}-{} != {}".format(traderLPBalance2, traderLPBalance, capital)

    def checkDepositWrongBaseToken(self, dodoName, amount=100000, isWrongName=True):
        logger.info("开始进行depositBase测试。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(f"price: {price}")

        newBaseTargert, newQuoteTarget = getExpectedTarget(dodoInfo, price)
        totalBaseCapital = getTotalBaseCapital(baseToken, dodoName)
        totalQuoteCapital = getTotalQuoteCapital(quoteToken, dodoName)
        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                 baseTokenDecimal, quoteTokenDecimal)

        traderLPBalance = getBaseCapitalBalanceOf(trader, dodoName, baseToken)

        logger.info("newBaseTargert: {}".format(newBaseTargert))
        logger.info("newQuoteTarget: {}".format(newQuoteTarget))
        logger.info("base的信息: {}".format(totalBaseCapital))
        logger.info("quote的信息: {}".format(totalQuoteCapital))
        logger.info("提供lp的用户资产: {}".format(tradeAccount))
        logger.info("管理费用的用户资产: {}".format(maintainAccount))
        logger.info("用户在池子持有base的资产: {}".format(traderLPBalance))

        capital = amount
        if totalBaseCapital == 0:
            capital = amount + newBaseTargert
        elif newBaseTargert > 0:
            capital = SafeMath.div(SafeMath.mul(amount, totalBaseCapital), newBaseTargert)
        logger.info("用户{} 准备depositBase的资产:{}, 预计得到lp: {}".format(trader, amount, capital))
        # 授权
        self.client.allowDosContract(trader, acc2pub_keys[trader])
        # 进行充值
        if isWrongName:
            parseAmount = amount / int(math.pow(10, baseTokenDecimal))
            tx_res = self.client.depositbase(trader, dodoName,
                                             to_wei_asset(parseAmount, baseToken + "A", baseTokenDecimal))
            assert "no base token symbol in the pair" in tx_res["error"]["details"][0][
                "message"], "depost 数量超过自身资产时，转账失败"
        else:
            parseAmount = amount / int(math.pow(10, baseTokenDecimal+1))
            tx_res = self.client.depositbase(trader, dodoName,
                                             to_wei_asset(parseAmount, baseToken, baseTokenDecimal+1))
            assert "mismatch precision of the base token in the pair" in tx_res["error"]["details"][0][
                "message"], "depost 数量超过自身资产时，转账失败"

        # 用户资产，lp的supply没有变更
        amount = 0
        capital = 0
        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        totalBaseCapital2 = getTotalBaseCapital(baseToken, dodoName)
        totalQuoteCapital2 = getTotalQuoteCapital(quoteToken, dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                  baseTokenDecimal, quoteTokenDecimal)
        traderLPBalance2 = getBaseCapitalBalanceOf(trader, dodoName, baseToken)

        logger.info(f"充值后baseTarget资产: {dodoInfo2['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"充值后quoteTarget资产: {dodoInfo2['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"充值后base资产: {dodoInfo2['dodos']['_BASE_BALANCE_']}")
        logger.info(f"充值后quote资产: {dodoInfo2['dodos']['_QUOTE_BALANCE_']}")
        logger.info("base的信息: {}".format(totalBaseCapital))
        logger.info("quote的信息: {}".format(totalQuoteCapital))
        logger.info("提供lp的用户资产: {}".format(tradeAccount2))
        logger.info("管理费用的用户资产: {}".format(maintainAccount2))
        logger.info("用户在池子持有base的资产: {}".format(traderLPBalance2))

        assert int(dodoInfo2['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']) - int(dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']) == amount, "Pool baseTarget 资产添加不正确"
        assert int(dodoInfo2['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']) == int(dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']), "Pool quoteTarget 资产添加不正确"
        assert int(dodoInfo2['dodos']['_BASE_BALANCE_']) - int(dodoInfo['dodos']['_BASE_BALANCE_']) == amount, "Pool base资产添加不正确"
        assert int(dodoInfo2['dodos']['_QUOTE_BALANCE_']) == int(dodoInfo['dodos']['_QUOTE_BALANCE_']), "Pool quote资产添加不正确"

        assert tradeAccount[baseToken] - tradeAccount2[baseToken] == amount, "用户base资产不正确"
        assert tradeAccount[quoteToken] - tradeAccount2[quoteToken] == 0, "用户quote资产不正确"

        assert totalBaseCapital2 == totalBaseCapital + capital, "base Supply 不正确"
        assert totalQuoteCapital2 == totalQuoteCapital, "quote Supply 不正确"

        assert maintainAccount2[baseToken] == maintainAccount[baseToken], "提现费用账户base资产计算不正确"
        assert maintainAccount2[quoteToken] == maintainAccount[quoteToken], "提现费用账户quote资产计算不正确"

        assert traderLPBalance2 == traderLPBalance + capital, "提现费用账户quote资产计算不正确, {}-{} != {}".format(traderLPBalance2, traderLPBalance, capital)

    def checkDepositQuoteToken(self, dodoName, amount=100000, isDepositExceed=False, priceChange=False, priceTrend="up", user=trader):
        logger.info("开始进行depositQuote测试。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(f"price: {price}")

        if priceChange:
            percent = 1.1 if priceTrend == "up" else 0.9
            expectedPrice = to_wei_asset(price * percent / DecimalMath.one, quoteToken, quoteTokenDecimal)
            logger.info(f"expectedPrice: {expectedPrice}")
            tx_res = self.client.setprice(oracleadmin, to_sym(baseToken, baseTokenDecimal), expectedPrice)

            price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
            logger.info(f"price: {price}")

        newBaseTargert, newQuoteTarget = getExpectedTarget(dodoInfo, price)
        totalBaseCapital = getTotalBaseCapital(baseToken, dodoName)
        totalQuoteCapital = getTotalQuoteCapital(quoteToken, dodoName)
        tradeAccount = self.getAccountBalance(user, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                  baseTokenDecimal, quoteTokenDecimal)

        traderLPBalance = getQuoteCapitalBalanceOf(user, dodoName, quoteToken)

        logger.info("newBaseTargert: {}".format(newBaseTargert))
        logger.info("newQuoteTarget: {}".format(newQuoteTarget))
        logger.info("base的信息: {}".format(getTokenSupply(dodoName, admin)))
        logger.info("quote的信息: {}".format(getTokenSupply(dodoName, admin)))
        logger.info("提供lp的用户资产: {}".format(tradeAccount))
        logger.info("管理费用的用户资产: {}".format(maintainAccount))
        logger.info("用户在池子持有quote的资产: {}".format(traderLPBalance))
        logger.info("totalBaseCapital: {}".format(totalBaseCapital))
        logger.info("totalQuoteCapital: {}".format(totalQuoteCapital))

        if isDepositExceed:
            amount = tradeAccount[quoteToken] + amount

        capital = amount
        # print(SafeMath.mul(amount, totalQuoteCapital))
        # print(SafeMath.mul(amount, totalQuoteCapital) / newQuoteTarget)

        if totalQuoteCapital == 0:
            capital = amount + newQuoteTarget
        elif newQuoteTarget > 0:
            capital = SafeMath.div(SafeMath.mul(amount, totalQuoteCapital), newQuoteTarget)
        logger.info("用户{} 准备depositQuote的资产:{}, 预计得到lp: {}".format(trader, amount, capital))
        contract = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["contract"]
        fee = get_transfer_fee(amount, quoteToken, False, contract)
        logger.info(("用户的转账费用: {}".format(fee)))
        # # 授权
        # self.client.allowDosContract(user, acc2pub_keys[user])
        # 进行充值
        parseAmount = amount / int(math.pow(10, quoteTokenDecimal))
        tx_res = self.client.depositquote(user, dodoName, to_wei_asset(parseAmount, quoteToken, quoteTokenDecimal, contract))
        if amount == 0:
            assert tx_res["code"] == 500, "depost 数量为0时，交易应失败"
            assert "must transfer positive quantity" in tx_res["error"]["details"][0]["message"], "depost 数量为0时，转账失败"
        if isDepositExceed:
            assert tx_res["code"] == 500, "depost数量超过自身资产时，交易应失败"
            assert "overdrawn balance" in tx_res["error"]["details"][0]["message"], "depost 数量超过自身资产时，转账失败"
            # 用户资产，lp的supply没有变更
            amount = 0
            capital = 0

        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        totalBaseCapital2 = getTotalBaseCapital(baseToken, dodoName)
        totalQuoteCapital2 = getTotalQuoteCapital(quoteToken, dodoName)
        tradeAccount2 = self.getAccountBalance(user, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                  baseTokenDecimal, quoteTokenDecimal)

        traderLPBalance2 = getQuoteCapitalBalanceOf(user, dodoName, quoteToken)

        logger.info(f"充值后baseTarget资产: {dodoInfo2['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"充值后quoteTarget资产: {dodoInfo2['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"充值后base资产: {dodoInfo2['dodos']['_BASE_BALANCE_']}")
        logger.info(f"充值后quote资产: {dodoInfo2['dodos']['_QUOTE_BALANCE_']}")
        logger.info("base的信息: {}".format(getTokenSupply(dodoName, admin)))
        logger.info("quote的信息: {}".format(getTokenSupply(dodoName, admin)))
        logger.info("提供lp的用户资产: {}".format(tradeAccount2))
        logger.info("管理费用的用户资产: {}".format(maintainAccount2))
        logger.info("用户在池子持有quote的资产: {}".format(traderLPBalance2))

        assert int(dodoInfo2['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']) - int(dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']) == 0, "Pool baseTarget 资产添加不正确"
        assert int(dodoInfo2['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']) - int(dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']) == amount, "Pool quoteTarget 资产添加不正确"
        assert int(dodoInfo2['dodos']['_BASE_BALANCE_']) - int(dodoInfo['dodos']['_BASE_BALANCE_']) == 0, "Pool base资产添加不正确"
        assert int(dodoInfo2['dodos']['_QUOTE_BALANCE_']) - int(dodoInfo['dodos']['_QUOTE_BALANCE_']) == amount, "Pool quote资产添加不正确"

        assert tradeAccount[baseToken] - tradeAccount2[baseToken] == 0, "用户base资产不正确"
        assert tradeAccount[quoteToken] - tradeAccount2[quoteToken] == amount + fee, "用户quote资产不正确"

        assert totalBaseCapital2 == totalBaseCapital, "base Supply 不正确"
        assert totalQuoteCapital2 == totalQuoteCapital + capital, "quote Supply 不正确"

        assert maintainAccount2[baseToken] == maintainAccount[baseToken], "提现费用账户base资产计算不正确"
        assert maintainAccount2[quoteToken] == maintainAccount[quoteToken], "提现费用账户quote资产计算不正确"

        assert traderLPBalance2 == traderLPBalance + capital, "提现费用账户quote资产计算不正确, {}-{} != {}".format(traderLPBalance2, traderLPBalance, capital)

    def checkDepositWrongQuoteToken(self, dodoName, amount=100000, isWrongName=True):
        logger.info("开始进行depositQuote测试。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(f"price: {price}")

        newBaseTargert, newQuoteTarget = getExpectedTarget(dodoInfo, price)
        totalBaseCapital = getTotalBaseCapital(baseToken, dodoName)
        totalQuoteCapital = getTotalQuoteCapital(quoteToken, dodoName)
        tradeAccount = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                 baseTokenDecimal, quoteTokenDecimal)

        traderLPBalance = getQuoteCapitalBalanceOf(trader, dodoName, quoteToken)

        logger.info("newBaseTargert: {}".format(newBaseTargert))
        logger.info("newQuoteTarget: {}".format(newQuoteTarget))
        logger.info("base的信息: {}".format(getTokenSupply(baseToken, dodoName)))
        logger.info("quote的信息: {}".format(getTokenSupply(quoteToken, dodoName)))
        logger.info("提供lp的用户资产: {}".format(tradeAccount))
        logger.info("管理费用的用户资产: {}".format(maintainAccount))
        logger.info("用户在池子持有quote的资产: {}".format(traderLPBalance))
        logger.info("totalBaseCapital: {}".format(totalBaseCapital))
        logger.info("totalQuoteCapital: {}".format(totalQuoteCapital))

        capital = amount
        # print(SafeMath.mul(amount, totalQuoteCapital))
        # print(SafeMath.mul(amount, totalQuoteCapital) / newQuoteTarget)

        if totalQuoteCapital == 0:
            capital = amount + newQuoteTarget
        elif newQuoteTarget > 0:
            capital = SafeMath.div(SafeMath.mul(amount, totalQuoteCapital), newQuoteTarget)
        logger.info("用户{} 准备depositQuote的资产:{}, 预计得到lp: {}".format(trader, amount, capital))
        # 授权
        self.client.allowDosContract(trader, acc2pub_keys[trader])
        # 进行充值

        if isWrongName:
            parseAmount = amount / int(math.pow(10, quoteTokenDecimal))
            tx_res = self.client.depositquote(trader, dodoName, to_wei_asset(parseAmount, quoteToken + "A", quoteTokenDecimal))
            assert "no quote token symbol in the pair" in tx_res["error"]["details"][0][
                "message"], "depost 数量超过自身资产时，转账失败"
        else:
            parseAmount = amount / int(math.pow(10, quoteTokenDecimal + 1))
            tx_res = self.client.depositquote(trader, dodoName,
                                              to_wei_asset(parseAmount, quoteToken, quoteTokenDecimal + 1))
            assert "mismatch precision of the quote token in the pair" in tx_res["error"]["details"][0]["message"], "depost 数量超过自身资产时，转账失败"
        # 用户资产，lp的supply没有变更
        amount = 0
        capital = 0

        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        totalBaseCapital2 = getTotalBaseCapital(baseToken, dodoName)
        totalQuoteCapital2 = getTotalQuoteCapital(quoteToken, dodoName)
        tradeAccount2 = self.getAccountBalance(trader, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                  baseTokenDecimal, quoteTokenDecimal)

        traderLPBalance2 = getQuoteCapitalBalanceOf(trader, dodoName, quoteToken)

        logger.info(f"充值后baseTarget资产: {dodoInfo2['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"充值后quoteTarget资产: {dodoInfo2['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"充值后base资产: {dodoInfo2['dodos']['_BASE_BALANCE_']}")
        logger.info(f"充值后quote资产: {dodoInfo2['dodos']['_QUOTE_BALANCE_']}")
        logger.info("base的信息: {}".format(getTokenSupply(baseToken, dodoName)))
        logger.info("quote的信息: {}".format(getTokenSupply(quoteToken, dodoName)))
        logger.info("提供lp的用户资产: {}".format(tradeAccount2))
        logger.info("管理费用的用户资产: {}".format(maintainAccount2))
        logger.info("用户在池子持有quote的资产: {}".format(traderLPBalance2))

        assert int(dodoInfo2['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']) - int(dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']) == 0, "Pool baseTarget 资产添加不正确"
        assert int(dodoInfo2['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']) - int(dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']) == amount, "Pool quoteTarget 资产添加不正确"
        assert int(dodoInfo2['dodos']['_BASE_BALANCE_']) - int(dodoInfo['dodos']['_BASE_BALANCE_']) == 0, "Pool base资产添加不正确"
        assert int(dodoInfo2['dodos']['_QUOTE_BALANCE_']) - int(dodoInfo['dodos']['_QUOTE_BALANCE_']) == amount, "Pool quote资产添加不正确"

        assert tradeAccount[baseToken] - tradeAccount2[baseToken] == 0, "用户base资产不正确"
        assert tradeAccount[quoteToken] - tradeAccount2[quoteToken] == amount, "用户quote资产不正确"

        assert totalBaseCapital2 == totalBaseCapital, "base Supply 不正确"
        assert totalQuoteCapital2 == totalQuoteCapital + capital, "quote Supply 不正确"

        assert maintainAccount2[baseToken] == maintainAccount[baseToken], "提现费用账户base资产计算不正确"
        assert maintainAccount2[quoteToken] == maintainAccount[quoteToken], "提现费用账户quote资产计算不正确"

        assert traderLPBalance2 == traderLPBalance + capital, "提现费用账户quote资产计算不正确, {}-{} != {}".format(traderLPBalance2, traderLPBalance, capital)

    def checkWithdrawBaseToken(self, dodoName, amount=100000, isWithdrawExceed=False, priceChange=False, priceTrend="up", user=trader):
        logger.info("开始进行withdrawBase测试。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        contract = dodoInfo["dodos"]["_BASE_TOKEN_"]["contract"]
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info(f"当前R状态为: {dodoInfo['dodos']['_R_STATUS_']}")
        poolBalance = self.getAccountBalance(dodoName, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，池子实际持有的资产: {}".format(poolBalance))

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(f"price: {price}")

        if priceChange:
            percent = 1.1 if priceTrend == "up" else 0.9
            expectedPrice = to_wei_asset(price * percent / DecimalMath.one, quoteToken, quoteTokenDecimal)
            logger.info(f"expectedPrice: {expectedPrice}")
            tx_res = self.client.setprice(oracleadmin, to_sym(baseToken, baseTokenDecimal), expectedPrice)

            price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
            logger.info(f"price: {price}")
        newBaseTargert, newQuoteTarget = getExpectedTarget(dodoInfo, price)
        totalBaseCapital = getTotalBaseCapital(baseToken, dodoName)
        totalQuoteCapital = getTotalQuoteCapital(quoteToken, dodoName)
        tradeAccount = self.getAccountBalance(user, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)

        assert totalBaseCapital > 0, "NO_BASE_LP"
        traderLPBalance = getBaseCapitalBalanceOf(user, dodoName, baseToken)
        logger.info("newBaseTargert: {}".format(newBaseTargert))
        logger.info("newQuoteTarget: {}".format(newQuoteTarget))
        logger.info("base的信息: {}".format(getTokenSupply(dodoName, admin)))
        logger.info("quote的信息: {}".format(getTokenSupply(dodoName, admin)))
        logger.info("withdraw的用户资产: {}".format(tradeAccount))
        logger.info("收取费用账户的资产: {}".format(maintainAccount))
        if isWithdrawExceed:
            amount = traderLPBalance + amount

        requireBaseCapital = SafeMath.divCeil(SafeMath.mul(amount, totalBaseCapital), newBaseTargert)
        # assert requireBaseCapital <= traderLPBalance, "LP_BASE_CAPITAL_BALANCE_NOT_ENOUGH"
        penalty = getWithdrawBasePenalty(amount, dodoInfo, price)

        assert penalty <= amount, "PENALTY_EXCEED"

        logger.info("用户持有的lp数量: {}".format(traderLPBalance))
        logger.info("将要销毁的lp数量: {}".format(requireBaseCapital))
        logger.info("用户{} 准备withdrawBase的资产:{}, 预计得到lp: {}, 收费: {}".format(user, amount, amount - penalty, penalty))
        fee = get_transfer_fee(amount, baseToken, True, contract)
        logger.info("计算的转账费用为: {}".format(fee))
        actualAmount = amount - fee
        logger.info("实际的转账数量为: {}".format(actualAmount))
        # # 授权
        # self.client.allowDosContract(user, acc2pub_keys[user])
        # 进行withdraw
        parseAmount = amount / int(math.pow(10, baseTokenDecimal))
        tx_res = self.client.withdrawbase(user, dodoName, to_wei_asset(parseAmount, baseToken, baseTokenDecimal, contract))
        if amount == 0:
            assert tx_res["code"] == 500, "depost 数量为0时，交易应失败"
            assert "must transfer positive quantity" in tx_res["error"]["details"][0]["message"], "depost 数量为0时，转账失败"
        if isWithdrawExceed or traderLPBalance == 0:
            assert tx_res["code"] == 500, "depost 数量超过自身资产时，交易应失败"
            assert "LP_BASE_CAPITAL_BALANCE_NOT_ENOUGH" in tx_res["error"]["details"][0]["message"], "depost 数量超过自身资产时，转账失败"
            # 用户资产，lp的supply没有变更
            amount = 0
            penalty = 0
            requireBaseCapital = 0

        if requireBaseCapital > traderLPBalance:
            assert tx_res["code"] == 500, "depost 数量超过自身资产时，交易应失败"
            assert "LP_BASE_CAPITAL_BALANCE_NOT_ENOUGH" in tx_res["error"]["details"][0][
                "message"], "depost 数量超过自身资产时，转账失败"
            amount = 0
            penalty = 0
            requireBaseCapital = 0
        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        totalBaseCapital2 = getTotalBaseCapital(baseToken, dodoName)
        totalQuoteCapital2 = getTotalQuoteCapital(quoteToken, dodoName)
        tradeAccount2 = self.getAccountBalance(user, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                 baseTokenDecimal, quoteTokenDecimal)
        traderLPBalance2 = getBaseCapitalBalanceOf(user, dodoName, baseToken)
        logger.info(f"提现后baseTarget资产: {dodoInfo2['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"提现后quoteTarget资产: {dodoInfo2['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"提现后base资产: {dodoInfo2['dodos']['_BASE_BALANCE_']}")
        logger.info(f"提现后quote资产: {dodoInfo2['dodos']['_QUOTE_BALANCE_']}")
        logger.info("base的信息: {}".format(getTokenSupply(dodoName, admin)))
        logger.info("quote的信息: {}".format(getTokenSupply(dodoName, admin)))
        logger.info("withdraw的用户资产: {}".format(tradeAccount2))
        logger.info("收取费用账户的资产: {}".format(maintainAccount2))
        logger.info("提现用户持有的lp数量: {}".format(traderLPBalance2))

        poolBalance2 = self.getAccountBalance(dodoName, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，池子实际持有的资产: {}".format(poolBalance2))

        r1 = assertEqualOnlyShowLog(int(dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']) - int(dodoInfo2['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']), amount - penalty, "Pool baseTarget 资产减少不正确")
        r2 = assertEqualOnlyShowLog(int(dodoInfo2['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']), int(dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']), "Pool quoteTarget 资产减少不正确")
        r3 = assertEqualOnlyShowLog(int(dodoInfo['dodos']['_BASE_BALANCE_']) - int(dodoInfo2['dodos']['_BASE_BALANCE_']), amount - penalty, "Pool base 资产减少不正确")
        r4 = assertEqualOnlyShowLog(int(dodoInfo2['dodos']['_QUOTE_BALANCE_']), int(dodoInfo['dodos']['_QUOTE_BALANCE_']), "Pool quote 资产减少不正确")
        r5 = assertEqualOnlyShowLog(poolBalance[baseToken] - poolBalance2[baseToken], amount - penalty, "池子实际base资产不正确")
        r6 = assertEqualOnlyShowLog(poolBalance[quoteToken], poolBalance2[quoteToken], "池子实际quote资产不正确")
        r7 = assertEqualOnlyShowLog(tradeAccount2[baseToken] - tradeAccount[baseToken], amount - penalty - fee, "用户base资产不正确")
        r8 = assertEqualOnlyShowLog(tradeAccount[quoteToken], tradeAccount2[quoteToken], "用户quote资产不正确")
        r9 = assertEqualOnlyShowLog(totalBaseCapital2, totalBaseCapital - requireBaseCapital, "base Supply 不正确")
        r10 = assertEqualOnlyShowLog(totalQuoteCapital2, totalQuoteCapital, "quote Supply 不正确")
        r11 = assertEqualOnlyShowLog(maintainAccount2[baseToken], maintainAccount[baseToken], "提现费用账户base资产计算不正确")
        r12 = assertEqualOnlyShowLog(maintainAccount2[quoteToken], maintainAccount[quoteToken], "提现费用账户quote资产计算不正确")
        r13 = assertEqualOnlyShowLog(traderLPBalance2, traderLPBalance - requireBaseCapital, "user lp balance 不正确: {}")

        if r1 or r2 or r3 or r4 or r5 or r6 or r7 or r8 or r9 or r10 or r11 or r12 or r13:
            assert False, "有检查失败"

    def checkWithdrawWrongBaseToken(self, dodoName, amount=100000, isWrongToken=True, user=trader):
        logger.info("开始进行withdrawBase测试。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info(f"当前R状态为: {dodoInfo['dodos']['_R_STATUS_']}")

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(f"price: {price}")
        newBaseTargert, newQuoteTarget = getExpectedTarget(dodoInfo, price)
        totalBaseCapital = getTotalBaseCapital(baseToken, dodoName)
        totalQuoteCapital = getTotalQuoteCapital(quoteToken, dodoName)
        tradeAccount = self.getAccountBalance(user, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)

        assert totalBaseCapital > 0, "NO_BASE_LP"
        traderLPBalance = getBaseCapitalBalanceOf(user, dodoName, baseToken)
        logger.info("newBaseTargert: {}".format(newBaseTargert))
        logger.info("newQuoteTarget: {}".format(newQuoteTarget))
        logger.info("base的信息: {}".format(getTokenSupply(dodoName, admin)))
        logger.info("quote的信息: {}".format(getTokenSupply(dodoName, admin)))
        logger.info("withdraw的用户资产: {}".format(tradeAccount))
        logger.info("收取费用账户的资产: {}".format(maintainAccount))

        requireBaseCapital = SafeMath.divCeil(SafeMath.mul(amount, totalBaseCapital), newBaseTargert)
        # assert requireBaseCapital <= traderLPBalance, "LP_BASE_CAPITAL_BALANCE_NOT_ENOUGH"
        penalty = getWithdrawBasePenalty(amount, dodoInfo, price)

        assert penalty <= amount, "PENALTY_EXCEED"

        logger.info("用户持有的lp数量: {}".format(traderLPBalance))
        logger.info("将要销毁的lp数量: {}".format(requireBaseCapital))
        logger.info("用户{} 准备withdrawBase的资产:{}, 预计得到lp: {}, 收费: {}".format(user, amount, amount - penalty, penalty))
        # 授权
        self.client.allowDosContract(user, acc2pub_keys[user])
        # 进行withdraw
        if isWrongToken:
            parseAmount = amount / int(math.pow(10, baseTokenDecimal))
            tx_res = self.client.withdrawbase(user, dodoName, to_wei_asset(parseAmount, baseToken + "A", baseTokenDecimal))
            assert "no base token symbol in the pair" in tx_res["error"]["details"][0]["message"], "depost 数量为0时，转账失败"
        else:
            parseAmount = amount / int(math.pow(10, baseTokenDecimal + 1))
            tx_res = self.client.withdrawbase(user, dodoName, to_wei_asset(parseAmount, baseToken, baseTokenDecimal+1))
            assert "mismatch precision of the base token in the pair" in tx_res["error"]["details"][0]["message"], "depost 数量为0时，转账失败"
        # 用户资产，lp的supply没有变更
        amount = 0
        penalty = 0
        requireBaseCapital = 0

        if requireBaseCapital > traderLPBalance:
            assert tx_res["code"] == 500, "depost 数量超过自身资产时，交易应失败"
            assert "LP_BASE_CAPITAL_BALANCE_NOT_ENOUGH" in tx_res["error"]["details"][0][
                "message"], "depost 数量超过自身资产时，转账失败"
            amount = 0
            penalty = 0
            requireBaseCapital = 0
        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        totalBaseCapital2 = getTotalBaseCapital(baseToken, dodoName)
        totalQuoteCapital2 = getTotalQuoteCapital(quoteToken, dodoName)
        tradeAccount2 = self.getAccountBalance(user, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                 baseTokenDecimal, quoteTokenDecimal)
        traderLPBalance2 = getBaseCapitalBalanceOf(user, dodoName, baseToken)
        logger.info(f"提现后baseTarget资产: {dodoInfo2['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"提现后quoteTarget资产: {dodoInfo2['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"提现后base资产: {dodoInfo2['dodos']['_BASE_BALANCE_']}")
        logger.info(f"提现后quote资产: {dodoInfo2['dodos']['_QUOTE_BALANCE_']}")
        logger.info("base的信息: {}".format(getTokenSupply(dodoName, admin)))
        logger.info("quote的信息: {}".format(getTokenSupply(dodoName, admin)))
        logger.info("withdraw的用户资产: {}".format(tradeAccount2))
        logger.info("收取费用账户的资产: {}".format(maintainAccount2))
        logger.info("提现用户持有的lp数量: {}".format(traderLPBalance2))

        assert int(dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']) - int(dodoInfo2['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']) == amount - penalty, "Pool baseTarget 资产减少不正确"
        assert int(dodoInfo2['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']) == int(dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']), "Pool quoteTarget 资产减少不正确"
        assert int(dodoInfo['dodos']['_BASE_BALANCE_']) - int(dodoInfo2['dodos']['_BASE_BALANCE_']) == amount - penalty, "Pool base资产减少不正确"
        assert int(dodoInfo2['dodos']['_QUOTE_BALANCE_']) == int(dodoInfo['dodos']['_QUOTE_BALANCE_']), "Pool quote资产减少不正确"

        assert tradeAccount2[baseToken] - tradeAccount[baseToken] == amount - penalty, "用户base资产不正确"
        assert tradeAccount[quoteToken] - tradeAccount2[quoteToken] == 0, "用户quote资产不正确"

        assert totalBaseCapital2 == totalBaseCapital - requireBaseCapital, "base Supply 不正确"
        assert totalQuoteCapital2 == totalQuoteCapital, "quote Supply 不正确"

        assert maintainAccount2[baseToken] == maintainAccount[baseToken], "提现费用账户base资产计算不正确"
        assert maintainAccount2[quoteToken] == maintainAccount[quoteToken], "提现费用账户quote资产计算不正确"

        assert traderLPBalance2 == traderLPBalance - requireBaseCapital, "user lp balance 不正确: {}"

    def checkWithdrawQuoteToken(self, dodoName, amount=100000, isWithdrawExceed=False, priceChange=False, priceTrend="up", user=trader):
        logger.info("开始进行withdrawQuote测试。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info(f"当前R状态为: {dodoInfo['dodos']['_R_STATUS_']}")

        poolBalance = self.getAccountBalance(dodoName, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，池子实际持有的资产: {}".format(poolBalance))
        
        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(f"price: {price}")

        if priceChange:
            percent = 1.1 if priceTrend == "up" else 0.9
            expectedPrice = to_wei_asset(price * percent / DecimalMath.one, quoteToken, quoteTokenDecimal)
            logger.info(f"expectedPrice: {expectedPrice}")
            tx_res = self.client.setprice(oracleadmin, to_sym(baseToken, baseTokenDecimal), expectedPrice)

            price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
            logger.info(f"price: {price}")
        newBaseTargert, newQuoteTarget = getExpectedTarget(dodoInfo, price)
        totalBaseCapital = getTotalBaseCapital(baseToken, dodoName)
        totalQuoteCapital = getTotalQuoteCapital(quoteToken, dodoName)
        tradeAccount = self.getAccountBalance(user, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)

        assert totalBaseCapital > 0, "NO_BASE_LP"
        traderLPBalance = getQuoteCapitalBalanceOf(user, dodoName, quoteToken)
        logger.info("newBaseTargert: {}".format(newBaseTargert))
        logger.info("newQuoteTarget: {}".format(newQuoteTarget))
        logger.info("base的信息: {}".format(getTokenSupply(dodoName, admin)))
        logger.info("quote的信息: {}".format(getTokenSupply(dodoName, admin)))
        logger.info("withdraw的用户资产: {}".format(tradeAccount))
        logger.info("收取费用账户的资产: {}".format(maintainAccount))
        logger.info("提现用户在池子持有的quote数量: {}".format(traderLPBalance))
        if isWithdrawExceed:
            amount = traderLPBalance + amount

        requireQuoteCapital = SafeMath.divCeil(SafeMath.mul(amount, totalQuoteCapital), newQuoteTarget)
        # assert requireBaseCapital <= traderLPBalance, "LP_BASE_CAPITAL_BALANCE_NOT_ENOUGH"
        penalty = getWithdrawQuotePenalty(amount, dodoInfo, price)

        print(penalty)
        # assert penalty < amount, "PENALTY_EXCEED"

        logger.info("用户持有的lp数量: {}".format(traderLPBalance))
        logger.info("将要销毁的lp数量: {}".format(requireQuoteCapital))
        logger.info("用户{} 准备withdrawQuote的资产:{}, 预计得到: {}, 收费: {}".format(user, amount, amount - penalty, penalty))

        contract = dodoInfo["dodos"]["_BASE_TOKEN_"]["contract"]
        fee = get_transfer_fee(amount, quoteToken, True, contract)
        logger.info("计算的转账费用为: {}".format(fee))
        logger.info("实际的转账数量为: {}".format(amount - fee))
        # # 授权
        # self.client.allowDosContract(user, acc2pub_keys[user])
        # 进行withdraw
        parseAmount = amount / int(math.pow(10, quoteTokenDecimal))
        tx_res = self.client.withdrawquote(user, dodoName, to_wei_asset(parseAmount, quoteToken, quoteTokenDecimal, contract))

        if amount == 0:
            assert tx_res["code"] == 500, "withdraw 数量为0时，交易应失败"
            assert "PENALTY_EXCEED" in tx_res["error"]["details"][0]["message"], "withdraw 数量为0时，转账失败"

        if isWithdrawExceed or traderLPBalance == 0:
            assert tx_res["code"] == 500, "withdraw 数量超过自身资产时，交易应失败"
            assert "LP_QUOTE_CAPITAL_BALANCE_NOT_ENOUGH" in tx_res["error"]["details"][0]["message"], "withdraw 数量超过自身资产时，转账失败"
            # 用户资产，lp的supply没有变更
            amount = 0
            penalty = 0
            requireQuoteCapital = 0
        elif penalty >= amount:
            assert tx_res["code"] == 500, "withdraw 数量为{}时，收取费用: [}, 交易应失败".format(amount, penalty)
            assert "PENALTY_EXCEED" in tx_res["error"]["details"][0]["message"], "withdraw 数量为{}时，收取费用: [}, 交易应失败".format(amount, penalty)
            # 用户资产，lp的supply没有变更
            amount = 0
            penalty = 0
            requireQuoteCapital = 0

        if requireQuoteCapital > traderLPBalance:
            assert tx_res["code"] == 500, "withdraw 数量为{}时，收取费用: [}, 交易应失败".format(amount, penalty)
            assert "LP_QUOTE_CAPITAL_BALANCE_NOT_ENOUGH" in tx_res["error"]["details"][0]["message"], "withdraw 数量为{}时，收取费用: [}, 交易应失败".format(amount, penalty)
            # 用户资产，lp的supply没有变更
            amount = 0
            penalty = 0
            requireQuoteCapital = 0

        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        totalBaseCapital2 = getTotalBaseCapital(baseToken, dodoName)
        totalQuoteCapital2 = getTotalQuoteCapital(quoteToken, dodoName)
        tradeAccount2 = self.getAccountBalance(user, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                 baseTokenDecimal, quoteTokenDecimal)
        traderLPBalance2 = getQuoteCapitalBalanceOf(user, dodoName, quoteToken)
        logger.info(f"提现后baseTarget资产: {dodoInfo2['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"提现后quoteTarget资产: {dodoInfo2['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"提现后base资产: {dodoInfo2['dodos']['_BASE_BALANCE_']}")
        logger.info(f"提现后quote资产: {dodoInfo2['dodos']['_QUOTE_BALANCE_']}")
        logger.info("base的信息: {}".format(getTokenSupply(dodoName, admin)))
        logger.info("quote的信息: {}".format(getTokenSupply(dodoName, admin)))
        logger.info("withdraw的用户资产: {}".format(tradeAccount2))
        logger.info("收取费用账户的资产: {}".format(maintainAccount2))
        logger.info("提现用户在池子持有的quote数量: {}".format(traderLPBalance2))

        poolBalance2 = self.getAccountBalance(dodoName, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        logger.info("交易前，池子实际持有的资产: {}".format(poolBalance2))

        r1 = assertEqualOnlyShowLog(int(dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']) - int(dodoInfo2['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']), 0, "Pool baseTarget 资产减少不正确")
        r2 = assertEqualOnlyShowLog(int(dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']) - int(dodoInfo2['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']), amount - penalty, "Pool quoteTarget 资产减少不正确")
        r3 = assertEqualOnlyShowLog(int(dodoInfo['dodos']['_BASE_BALANCE_']), int(dodoInfo2['dodos']['_BASE_BALANCE_']), "Pool base资产减少不正确")
        r4 = assertEqualOnlyShowLog(int(dodoInfo['dodos']['_QUOTE_BALANCE_']) - int(dodoInfo2['dodos']['_QUOTE_BALANCE_']), amount - penalty, "Pool quote资产减少不正确")

        r5 = assertEqualOnlyShowLog(poolBalance[baseToken], poolBalance2[baseToken], "池子实际base资产不正确")
        r6 = assertEqualOnlyShowLog(poolBalance[quoteToken] - poolBalance2[quoteToken], amount - penalty, "池子实际quote资产不正确")

        r7 = assertEqualOnlyShowLog(tradeAccount2[baseToken], tradeAccount[baseToken], "用户base资产不正确")
        r8 = assertEqualOnlyShowLog(tradeAccount2[quoteToken] - tradeAccount[quoteToken], amount - penalty - fee, "用户quote资产不正确")

        r9 = assertEqualOnlyShowLog(totalBaseCapital2, totalBaseCapital, "base Supply 不正确")
        r10 = assertEqualOnlyShowLog(totalQuoteCapital2, totalQuoteCapital - requireQuoteCapital, "quote Supply 不正确")

        r11 = assertEqualOnlyShowLog(maintainAccount2[baseToken], maintainAccount[baseToken], "提现费用账户base资产计算不正确")
        r12 = assertEqualOnlyShowLog(maintainAccount2[quoteToken], maintainAccount[quoteToken], "提现费用账户quote资产计算不正确")

        r13 = assertEqualOnlyShowLog(traderLPBalance2, traderLPBalance - requireQuoteCapital, "user在池子中持有的quote资产计算不正确")

        if r1 or r2 or r3 or r4 or r5 or r6 or r7 or r8 or r9 or r10 or r11 or r12 or r13:
            assert False, "有检查失败"

    def checkWithdrawWrongQuoteToken(self, dodoName, amount=100000, isWrongToken=True, user=trader):
        logger.info("开始进行withdrawQuote测试。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info(f"当前R状态为: {dodoInfo['dodos']['_R_STATUS_']}")

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(f"price: {price}")
        newBaseTargert, newQuoteTarget = getExpectedTarget(dodoInfo, price)
        totalBaseCapital = getTotalBaseCapital(baseToken, dodoName)
        totalQuoteCapital = getTotalQuoteCapital(quoteToken, dodoName)
        tradeAccount = self.getAccountBalance(user, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)

        assert totalBaseCapital > 0, "NO_BASE_LP"
        traderLPBalance = getQuoteCapitalBalanceOf(user, dodoName, quoteToken)
        logger.info("newBaseTargert: {}".format(newBaseTargert))
        logger.info("newQuoteTarget: {}".format(newQuoteTarget))
        logger.info("base的信息: {}".format(getTokenSupply(dodoName, admin)))
        logger.info("quote的信息: {}".format(getTokenSupply(dodoName, admin)))
        logger.info("withdraw的用户资产: {}".format(tradeAccount))
        logger.info("收取费用账户的资产: {}".format(maintainAccount))
        logger.info("提现用户在池子持有的quote数量: {}".format(traderLPBalance))

        requireQuoteCapital = SafeMath.divCeil(SafeMath.mul(amount, totalQuoteCapital), newQuoteTarget)
        # assert requireBaseCapital <= traderLPBalance, "LP_BASE_CAPITAL_BALANCE_NOT_ENOUGH"
        penalty = getWithdrawQuotePenalty(amount, dodoInfo, price)

        logger.info("用户持有的lp数量: {}".format(traderLPBalance))
        logger.info("将要销毁的lp数量: {}".format(requireQuoteCapital))
        logger.info("用户{} 准备withdrawQuote的资产:{}, 预计得到: {}, 收费: {}".format(user, amount, amount - penalty, penalty))
        # # 授权
        # self.client.allowDosContract(user, acc2pub_keys[user])
        # # 进行withdraw
        # parseAmount = amount / int(math.pow(10, quoteTokenDecimal))
        # tx_res = self.client.withdrawquote(user, dodoName, to_wei_asset(parseAmount, quoteToken, quoteTokenDecimal))

        if isWrongToken:
            parseAmount = amount / int(math.pow(10, quoteTokenDecimal))
            tx_res = self.client.withdrawquote(user, dodoName, to_wei_asset(parseAmount, quoteToken + "A", quoteTokenDecimal))
            assert "no quote token symbol in the pair" in tx_res["error"]["details"][0][
                "message"], "withdraw 数量超过自身资产时，转账失败"
        else:
            parseAmount = amount / int(math.pow(10, quoteTokenDecimal + 1))
            print(to_wei_asset(parseAmount, quoteToken, quoteTokenDecimal +1))
            # tx_res = self.client.withdrawquote(user, dodoName, to_wei_asset(parseAmount, quoteToken, quoteTokenDecimal +1))
            # assert "mismatch precision of the quote token in the pair" in tx_res["error"]["details"][0][
            #     "message"], "withdraw 数量超过自身资产时，转账失败"
        # 用户资产，lp的supply没有变更
        amount = 0
        penalty = 0
        requireQuoteCapital = 0
        if requireQuoteCapital > traderLPBalance:
            assert tx_res["code"] == 500, "withdraw 数量为{}时，收取费用: [}, 交易应失败".format(amount, penalty)
            assert "LP_QUOTE_CAPITAL_BALANCE_NOT_ENOUGH" in tx_res["error"]["details"][0]["message"], "withdraw 数量为{}时，收取费用: [}, 交易应失败".format(amount, penalty)
            # 用户资产，lp的supply没有变更
            amount = 0
            penalty = 0
            requireQuoteCapital = 0

        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        totalBaseCapital2 = getTotalBaseCapital(baseToken, dodoName)
        totalQuoteCapital2 = getTotalQuoteCapital(quoteToken, dodoName)
        tradeAccount2 = self.getAccountBalance(user, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                 baseTokenDecimal, quoteTokenDecimal)
        traderLPBalance2 = getQuoteCapitalBalanceOf(user, dodoName, quoteToken)
        logger.info(f"提现后baseTarget资产: {dodoInfo2['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"提现后quoteTarget资产: {dodoInfo2['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"提现后base资产: {dodoInfo2['dodos']['_BASE_BALANCE_']}")
        logger.info(f"提现后quote资产: {dodoInfo2['dodos']['_QUOTE_BALANCE_']}")
        logger.info("base的信息: {}".format(getTokenSupply(dodoName, admin)))
        logger.info("quote的信息: {}".format(getTokenSupply(dodoName, admin)))
        logger.info("withdraw的用户资产: {}".format(tradeAccount2))
        logger.info("收取费用账户的资产: {}".format(maintainAccount2))
        logger.info("提现用户在池子持有的quote数量: {}".format(traderLPBalance2))

        assert int(dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']) - int(dodoInfo2['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']) == 0, "Pool baseTarget 资产减少不正确"
        assert int(dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']) - int(dodoInfo2['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']) == amount - penalty, "Pool quoteTarget 资产减少不正确"
        assert int(dodoInfo['dodos']['_BASE_BALANCE_']) - int(dodoInfo2['dodos']['_BASE_BALANCE_']) == 0, "Pool base资产减少不正确"
        assert int(dodoInfo['dodos']['_QUOTE_BALANCE_']) - int(dodoInfo2['dodos']['_QUOTE_BALANCE_']) == amount - penalty, "Pool quote资产减少不正确"

        assert tradeAccount2[baseToken] - tradeAccount[baseToken] == 0, "用户base资产不正确"
        assert tradeAccount2[quoteToken] - tradeAccount[quoteToken] == amount - penalty, "用户quote资产不正确"

        assert totalBaseCapital2 == totalBaseCapital, "base Supply 不正确"
        assert totalQuoteCapital2 == totalQuoteCapital - requireQuoteCapital, "quote Supply 不正确"

        assert maintainAccount2[baseToken] == maintainAccount[baseToken], "提现费用账户base资产计算不正确"
        assert maintainAccount2[quoteToken] == maintainAccount[quoteToken], "提现费用账户quote资产计算不正确"

        assert traderLPBalance2 == traderLPBalance - requireQuoteCapital, "user在池子中持有的quote资产计算不正确: { d}={}".format(traderLPBalance - traderLPBalance2, requireQuoteCapital)

    def checkWithdrawAllBaseToken(self, dodoName, priceChange=False, priceTrend="up", user=trader):
        logger.info("开始进行withdrawAllBase测试。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info(f"当前R状态为: {dodoInfo['dodos']['_R_STATUS_']}")

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(f"price: {price}")

        if priceChange:
            percent = 1.1 if priceTrend == "up" else 0.9
            expectedPrice = to_wei_asset(price * percent / 10000, quoteToken, quoteTokenDecimal)
            logger.info(f"expectedPrice: {expectedPrice}")
            tx_res = self.client.setprice(oracleadmin, to_sym(baseToken, baseTokenDecimal), expectedPrice)

            price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
            logger.info(f"price: {price}")
        newBaseTargert, newQuoteTarget = getExpectedTarget(dodoInfo, price)
        totalBaseCapital = getTotalBaseCapital(baseToken, dodoName)
        totalQuoteCapital = getTotalQuoteCapital(quoteToken, dodoName)
        tradeAccount = self.getAccountBalance(user, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)

        assert totalBaseCapital > 0, "NO_BASE_LP"
        traderLPBalance = getBaseCapitalBalanceOf(user, dodoName, baseToken)
        logger.info("newBaseTargert: {}".format(newBaseTargert))
        logger.info("newQuoteTarget: {}".format(newQuoteTarget))
        logger.info("base的信息: {}".format(getTokenSupply(dodoName, admin)))
        logger.info("quote的信息: {}".format(getTokenSupply(dodoName, admin)))
        logger.info("withdraw的用户资产: {}".format(tradeAccount))
        logger.info("收取费用账户的资产: {}".format(maintainAccount))

        amount = getLpBaseBalance(user, baseToken, dodoName, dodoInfo, price)
        logger.info(amount)

        capital = traderLPBalance
        # assert requireBaseCapital <= traderLPBalance, "LP_BASE_CAPITAL_BALANCE_NOT_ENOUGH"
        penalty = getWithdrawBasePenalty(amount, dodoInfo, price)

        assert penalty <= amount, "PENALTY_EXCEED"

        logger.info("用户持有的lp数量: {}".format(traderLPBalance))
        logger.info("将要销毁的lp数量: {}".format(capital))
        logger.info("用户{} 准备withdrawBase的资产:{}, 预计得到lp: {}, 收费: {}".format(user, amount, amount - penalty, penalty))

        contract = dodoInfo["dodos"]["_BASE_TOKEN_"]["contract"]
        fee = get_transfer_fee(amount, baseToken, True, contract)
        logger.info("计算的转账费用为: {}".format(fee))
        logger.info("实际的转账数量为: {}".format(amount - fee))
        # # 授权
        # self.client.allowDosContract(user, acc2pub_keys[user])
        # 进行withdrawAllBase
        tx_res = self.client.withdrawallbase(user, dodoName)
        if amount == 0:
            assert tx_res["code"] == 500, "depost 数量为0时，交易应失败"
            assert "must transfer positive quantity" in tx_res["error"]["details"][0]["message"], "depost 数量为0时，转账失败"
        if traderLPBalance == 0:
            assert tx_res["code"] == 500, "depost 数量超过自身资产时，交易应失败"
            assert "LP_BASE_CAPITAL_BALANCE_NOT_ENOUGH" in tx_res["error"]["details"][0]["message"], "depost 数量超过自身资产时，转账失败"
            # 用户资产，lp的supply没有变更
            amount = 0
            penalty = 0
            capital = 0
        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        totalBaseCapital2 = getTotalBaseCapital(baseToken, dodoName)
        totalQuoteCapital2 = getTotalQuoteCapital(quoteToken, dodoName)
        tradeAccount2 = self.getAccountBalance(user, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                 baseTokenDecimal, quoteTokenDecimal)
        traderLPBalance2 = getBaseCapitalBalanceOf(user, dodoName, baseToken)
        logger.info(f"提现后baseTarget资产: {dodoInfo2['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"提现后quoteTarget资产: {dodoInfo2['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"提现后base资产: {dodoInfo2['dodos']['_BASE_BALANCE_']}")
        logger.info(f"提现后quote资产: {dodoInfo2['dodos']['_QUOTE_BALANCE_']}")
        logger.info("base的信息: {}".format(getTokenSupply(dodoName, admin)))
        logger.info("quote的信息: {}".format(getTokenSupply(dodoName, admin)))
        logger.info("withdraw的用户资产: {}".format(tradeAccount2))
        logger.info("收取费用账户的资产: {}".format(maintainAccount2))
        logger.info("提现用户持有的lp数量: {}".format(traderLPBalance2))

        r1 = assertEqualOnlyShowLog(int(dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']) - int(dodoInfo2['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']), amount - penalty, "Pool baseTarget 资产减少不正确")
        r2 = assertEqualOnlyShowLog(int(dodoInfo2['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']), int(dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']), "Pool quoteTarget 资产减少不正确")
        r3 = assertEqualOnlyShowLog(int(dodoInfo['dodos']['_BASE_BALANCE_']) - int(
            dodoInfo2['dodos']['_BASE_BALANCE_']), amount - penalty, "Pool base 资产减少不正确")

        r4 = assertEqualOnlyShowLog(int(dodoInfo2['dodos']['_QUOTE_BALANCE_']), int(dodoInfo['dodos']['_QUOTE_BALANCE_']), "Pool quote资产减少不正确")

        r5 = assertEqualOnlyShowLog(tradeAccount2[baseToken] - tradeAccount[baseToken], amount - penalty - fee, "用户base资产不正确")
        r6 = assertEqualOnlyShowLog(tradeAccount[quoteToken], tradeAccount2[quoteToken], "用户quote资产不正确")
        r7 = assertEqualOnlyShowLog(totalBaseCapital2, totalBaseCapital - capital, "base Supply 不正确")
        r8 = assertEqualOnlyShowLog(totalQuoteCapital2, totalQuoteCapital, "quote Supply 不正确")

        # assert int(dodoInfo2['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']) == int(dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']), "Pool quoteTarget 资产减少不正确"
        # assert int(dodoInfo['dodos']['_BASE_BALANCE_']) - int(dodoInfo2['dodos']['_BASE_BALANCE_']) == amount - penalty, "Pool base资产减少不正确"
        # assert int(dodoInfo2['dodos']['_QUOTE_BALANCE_']) == int(dodoInfo['dodos']['_QUOTE_BALANCE_']), "Pool quote资产减少不正确"

        # assert tradeAccount2[baseToken] - tradeAccount[baseToken] == amount - penalty, "用户base资产不正确"
        # assert tradeAccount[quoteToken] - tradeAccount2[quoteToken] == 0, "用户quote资产不正确"

        # assert totalBaseCapital2 == totalBaseCapital - capital, "base Supply 不正确"
        # assert totalQuoteCapital2 == totalQuoteCapital, "quote Supply 不正确"

        r9 = assertEqualOnlyShowLog(maintainAccount2[baseToken], maintainAccount[baseToken], "提现费用账户base资产计算不正确")
        r10 = assertEqualOnlyShowLog(maintainAccount2[quoteToken], maintainAccount[quoteToken], "提现费用账户quote资产计算不正确")

        r11 = assertEqualOnlyShowLog(traderLPBalance2, traderLPBalance - capital, "user lp balance 不正确")

        if r1 or r2 or r3 or r4 or r5 or r6 or r7 or r8 or r9 or r10 or r11:
            assert False, "有检查失败"

    def checkWithdrawAllQuoteToken(self, dodoName, priceChange=False, priceTrend="up", user=trader):
        logger.info("开始进行withdrawQuote测试。。。")
        dodoInfo = self.getDodoInfo(dodoName)
        baseToken = dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[-1]
        baseTokenDecimal = int(dodoInfo["dodos"]["_BASE_TOKEN_"]["symbol"].split(",")[0])
        quoteToken = dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[-1]
        quoteTokenDecimal = int(dodoInfo["dodos"]["_QUOTE_TOKEN_"]["symbol"].split(",")[0])
        logger.info(baseToken + " " + quoteToken)
        logger.info(f"当前baseTarget资产: {dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"当前quoteTarget资产: {dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"当前base资产: {dodoInfo['dodos']['_BASE_BALANCE_']}")
        logger.info(f"当前quote资产: {dodoInfo['dodos']['_QUOTE_BALANCE_']}")
        logger.info(f"当前R状态为: {dodoInfo['dodos']['_R_STATUS_']}")

        price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
        logger.info(f"price: {price}")

        if priceChange:
            percent = 1.1 if priceTrend == "up" else 0.9
            expectedPrice = to_wei_asset(price * percent / 10000, quoteToken, quoteTokenDecimal)
            logger.info(f"expectedPrice: {expectedPrice}")
            tx_res = self.client.setprice(oracleadmin, to_sym(baseToken, baseTokenDecimal), expectedPrice)

            price = self.getOraclePrice(quoteToken, dodoInfo["dodos"]["_ORACLE_"], quoteTokenDecimal)
            logger.info(f"price: {price}")
        newBaseTargert, newQuoteTarget = getExpectedTarget(dodoInfo, price)
        totalBaseCapital = getTotalBaseCapital(baseToken, dodoName)
        totalQuoteCapital = getTotalQuoteCapital(quoteToken, dodoName)
        tradeAccount = self.getAccountBalance(user, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainAccount = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)

        assert totalQuoteCapital > 0, "NO_BASE_LP"
        traderLPBalance = getQuoteCapitalBalanceOf(user, dodoName, quoteToken)
        logger.info("newBaseTargert: {}".format(newBaseTargert))
        logger.info("newQuoteTarget: {}".format(newQuoteTarget))
        logger.info("base的信息: {}".format(getTokenSupply(dodoName, admin)))
        logger.info("quote的信息: {}".format(getTokenSupply(dodoName, admin)))
        logger.info("withdraw的用户资产: {}".format(tradeAccount))
        logger.info("收取费用账户的资产: {}".format(maintainAccount))
        logger.info("提现用户在池子持有的quote数量: {}".format(traderLPBalance))

        amount = getLpQuoteBalance(user, quoteToken, dodoName, dodoInfo, price)
        capital = traderLPBalance
        # assert requireBaseCapital <= traderLPBalance, "LP_BASE_CAPITAL_BALANCE_NOT_ENOUGH"
        penalty = getWithdrawQuotePenalty(amount, dodoInfo, price)

        # print(penalty)
        # assert penalty < amount, "PENALTY_EXCEED"

        logger.info("用户持有的lp数量: {}".format(traderLPBalance))
        logger.info("将要销毁的lp数量: {}".format(capital))
        logger.info("用户{} 准备withdrawQuote的资产:{}, 预计得到: {}, 收费: {}".format(user, amount, amount - penalty, penalty))

        contract = dodoInfo["dodos"]["_BASE_TOKEN_"]["contract"]
        fee = get_transfer_fee(amount, quoteToken, True, contract)
        logger.info("计算的转账费用为: {}".format(fee))
        logger.info("实际的转账数量为: {}".format(amount - fee))
        # # 授权
        # self.client.allowDosContract(user, acc2pub_keys[user])
        # 进行withdrawAllQuote
        tx_res = self.client.withdrawallquote(user, dodoName)

        if amount == 0:
            assert tx_res["code"] == 500, "withdraw 数量为0时，交易应失败"
            assert "PENALTY_EXCEED" in tx_res["error"]["details"][0]["message"], "withdraw 数量为0时，转账失败"

        if traderLPBalance == 0:
            assert tx_res["code"] == 500, "withdraw 数量超过自身资产时，交易应失败"
            assert "LP_QUOTE_CAPITAL_BALANCE_NOT_ENOUGH" in tx_res["error"]["details"][0]["message"], "withdraw 数量超过自身资产时，转账失败"
            # 用户资产，lp的supply没有变更
            amount = 0
            penalty = 0
            requireQuoteCapital = 0
        elif penalty >= amount:
            assert tx_res["code"] == 500, "withdraw 数量为{}时，收取费用: [}, 交易应失败".format(amount, penalty)
            assert "PENALTY_EXCEED" in tx_res["error"]["details"][0]["message"], "withdraw 数量为{}时，收取费用: [}, 交易应失败".format(amount, penalty)
            # 用户资产，lp的supply没有变更
            amount = 0
            penalty = 0
            capital = 0
        time.sleep(2)
        dodoInfo2 = self.getDodoInfo(dodoName)
        totalBaseCapital2 = getTotalBaseCapital(baseToken, dodoName)
        totalQuoteCapital2 = getTotalQuoteCapital(quoteToken, dodoName)
        tradeAccount2 = self.getAccountBalance(user, baseToken, quoteToken, baseTokenDecimal, quoteTokenDecimal)
        maintainAccount2 = self.getAccountBalance(dodoInfo["dodos"]["_MAINTAINER_"], baseToken, quoteToken,
                                                 baseTokenDecimal, quoteTokenDecimal)
        traderLPBalance2 = getQuoteCapitalBalanceOf(user, dodoName, quoteToken)
        logger.info(f"提现后baseTarget资产: {dodoInfo2['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']}")
        logger.info(f"提现后quoteTarget资产: {dodoInfo2['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']}")
        logger.info(f"提现后base资产: {dodoInfo2['dodos']['_BASE_BALANCE_']}")
        logger.info(f"提现后quote资产: {dodoInfo2['dodos']['_QUOTE_BALANCE_']}")
        logger.info("base的信息: {}".format(getTokenSupply(dodoName, admin)))
        logger.info("quote的信息: {}".format(getTokenSupply(dodoName, admin)))
        logger.info("withdraw的用户资产: {}".format(tradeAccount2))
        logger.info("收取费用账户的资产: {}".format(maintainAccount2))
        logger.info("提现用户在池子持有的quote数量: {}".format(traderLPBalance2))

        r1 = assertEqualOnlyShowLog(int(dodoInfo['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']), int(dodoInfo2['dodos']['_TARGET_BASE_TOKEN_AMOUNT_']), "Pool baseTarget 资产减少不正确")
        r2 = assertEqualOnlyShowLog(int(dodoInfo['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']) - int(dodoInfo2['dodos']['_TARGET_QUOTE_TOKEN_AMOUNT_']), amount - penalty, "Pool quoteTarget 资产减少不正确")
        r3 = assertEqualOnlyShowLog(int(dodoInfo['dodos']['_BASE_BALANCE_']), int(dodoInfo2['dodos']['_BASE_BALANCE_']), "Pool base资产减少不正确")
        r4 = assertEqualOnlyShowLog(int(dodoInfo['dodos']['_QUOTE_BALANCE_']) - int(dodoInfo2['dodos']['_QUOTE_BALANCE_']), amount - penalty, "Pool quote资产减少不正确")

        r5 = assertEqualOnlyShowLog(tradeAccount2[baseToken], tradeAccount[baseToken], "用户base资产不正确")
        r6 = assertEqualOnlyShowLog(tradeAccount2[quoteToken] - tradeAccount[quoteToken], amount - penalty - fee, "用户quote资产不正确")

        r7 = assertEqualOnlyShowLog(totalBaseCapital2, totalBaseCapital, "base Supply 不正确")
        r8 = assertEqualOnlyShowLog(totalQuoteCapital2, totalQuoteCapital - capital, "quote Supply 不正确")

        r9 = assertEqualOnlyShowLog(maintainAccount2[baseToken], maintainAccount[baseToken], "提现费用账户base资产计算不正确")
        r10 = assertEqualOnlyShowLog(maintainAccount2[quoteToken], maintainAccount[quoteToken], "提现费用账户quote资产计算不正确")
        r11 = assertEqualOnlyShowLog(traderLPBalance2, traderLPBalance - capital, "user在池子中持有的quote资产计算不正确")
        if r1 or r2 or r3 or r4 or r5 or r6 or r7 or r8 or r9 or r10 or r11:
            assert False, "有检查失败"


client = EosClient(dodo_ethbase_name)
c = ChainClient(rpcNode)
w = WalletClient(walletNode)
eosrpc = EosRpc()
if __name__ == "__main__":
    dodoTest = DODOTest(dodo_ethbase_name)

    newDodoName = "ta2tc2222222"

    # dodoTest.checkSetParameterExceptPass(dodo_stablecoin_name)
    # dodoTest.checkSetParameterKSetFail(dodo_stablecoin_name)
    # dodoTest.checkSetParameterFeesSetFail(dodo_stablecoin_name)
    # dodoTest.checkSetParameterSetOtherParameter(dodo_stablecoin_name)
    # dodoTest.checkSetParameterUseOtherAccount(dodo_stablecoin_name)

    # dodoTest.checkSetOraclePrice("tea2tebtest3")
    # dodoTest.checkSetOraclePrice("gbp2hkd22222")
    # dodoTest.checkSetOraclePrice(dodo_stablecoin_name)
    # dodoTest.checkSetOraclePriceWhenPriceDecimalIsIncorrect(dodo_stablecoin_name)

    # client.setparameter(admin, dodo_stablecoin_name, "k", 100000)
    # client.setparameter(admin, dodo_stablecoin_name, "lpfeerate", 1)
    # client.setparameter(admin, dodo_stablecoin_name, "mtfeerate", 1)

    # dodoTest.checkBuyBaseTokenRStatus2to2(dodo_stablecoin_name)
    # dodoTest.checkSellBaseTokenRStatus2to2(dodo_stablecoin_name)

    # getTotalBaseCapital("TEA") # 40000000000
    # getTotalQuoteCapital("TEB") # 30000000000
    # getTokenBalance(dodo_stablecoin_name)

    # dodoTest.checkBuyBaseToken(dodo_stablecoin_name)    # 如果R状态为2, 保持R状态不变

    # dodoTest.checkBuyBaseTokenBuyMinAmount(dodo_stablecoin_name)    # 购买最小数量的base
    # dodoTest.checkBuyBaseTokenBuyAcceptMinAmount(dodo_stablecoin_name)    #购买可交易的最小数量的base
    # dodoTest.checkBuyBaseTokenBuyAmountExceedPoolNumber(dodo_stablecoin_name)     # 购买超出池子数量
    # dodoTest.checkBuyBaseTokenBuyAmountExceedSelfWalletNumber(dodo_stablecoin_name)     # 购买超出池子数量
    # dodoTest.checkBuyBaseTokenBuyAmountDecimalWrong(dodo_stablecoin_name)     # 购买超出池子数量
    # dodoTest.checkBuyBaseTokenBuyWrongBase(dodo_stablecoin_name)     # 购买超出池子数量
    # dodoTest.checkBuyBaseTokenBuyAmountWhenPriceAbove(dodo_stablecoin_name)     # 购买超出池子数量
    # dodoTest.checkBuyBaseTokenBuyAmountWhenPriceBellow(dodo_stablecoin_name)     # 购买超出池子数量

    # dodoTest.checkBuyBaseTokenRStatus2to2(dodo_stablecoin_name)     # R状态为2时, 购买base，且使R状态不变
    # dodoTest.checkBuyBaseTokenRStatus2to0(dodo_stablecoin_name)     # R状态为2时, 购买base，且使R变为平衡
    # dodoTest.checkBuyBaseTokenRStatus2to1(dodo_stablecoin_name)     # R状态为2时, 购买base，且使R变为1
    # dodoTest.checkBuyBaseTokenRStatus1to1(dodo_stablecoin_name)     # R状态为1时, 购买base，且使R变为1
    # dodoTest.checkBuyBaseTokenRStatus0to1(dodo_stablecoin_name, 1323603731)     # R状态为1时, 购买base，且使R变为1

    # for i in range(5):
    #     time.sleep(1)
    #     dodoTest.checkSellBaseTokenRStatus2to2(dodo_stablecoin_name, 1000000000)
    #     dodoTest.checkBuyBaseTokenRStatus1to1(dodo_stablecoin_name, 1000000000)  # R状态为1时, 购买base，且使R变为1

    # dodoTest.checkSellBaseTokenRStatus0to2(dodo_stablecoin_name)     # R状态为1时, 购买base，且使R变为1
    # dodoTest.checkSellBaseTokenRStatus1to1(dodo_stablecoin_name)     # R状态为1时, 购买base，且使R变为1
    # dodoTest.checkSellBaseTokenRStatus1to0(dodo_stablecoin_name)     # R状态为1时, 购买base，且使R变为1  ROX-127
    # dodoTest.checkSellBaseTokenRStatus1to2(dodo_stablecoin_name)     # R状态为1时, 购买base，且使R变为1
    # dodoTest.checkSellBaseTokenRStatus2to2(dodo_stablecoin_name, 1000000)     # R状态为1时, 购买base，且使R变为1

    # dodoTest.checkSellBaseTokenMinAmount(dodo_stablecoin_name)    # 购买最小数量的base
    # dodoTest.checkSellBaseTokenSellAcceptMinAmount(dodo_stablecoin_name)    #购买可交易的最小数量的base
    # dodoTest.checkSellBaseTokenAmountExceedPoolNumber(dodo_stablecoin_name)     # 没有实际场景，耗费的base太高
    # dodoTest.checkSellBaseTokenSellAmountExceedSelfWalletNumber(dodo_stablecoin_name)     # 购买超出池子数量
    # dodoTest.checkSellBaseTokenAmountDecimalWrong(dodo_stablecoin_name)     # 购买超出池子数量
    # dodoTest.checkSellBaseTokenSellWrongBase(dodo_stablecoin_name)     # 购买超出池子数量
    # dodoTest.checkSellBaseTokenAmountWhenPriceAbove(dodo_stablecoin_name)     # 购买超出池子数量
    # dodoTest.checkSellBaseTokenSellAmountWhenPriceBellow(dodo_stablecoin_name)     # 购买超出池子数量

    # 充值base资产
    # dodoTest.checkDepositBaseToken(dodo_stablecoin_name)      # 充值正常
    # dodoTest.checkDepositBaseToken(dodo_stablecoin_name, 100000000)      # 充值正常
    # dodoTest.checkDepositBaseToken(dodo_stablecoin_name, 0)   # 充值0
    # dodoTest.checkDepositBaseToken(dodo_stablecoin_name, 1)     # 充值最小精度资产
    # dodoTest.checkDepositBaseToken(dodo_stablecoin_name, 1, True)     # 充值超过用户自身持有资产
    # dodoTest.checkDepositBaseToken(dodo_stablecoin_name, 1000000, False, True, "up")     # 充值前 price更新
    # dodoTest.checkDepositBaseToken(dodo_stablecoin_name, 1000000, False, True, "down")     # 充值前 price更新
    # dodoTest.checkDepositWrongBaseToken(dodo_stablecoin_name)
    # dodoTest.checkDepositWrongBaseToken(dodo_stablecoin_name, 10000, False)

    # 充值quote资产
    # dodoTest.checkDepositQuoteToken(dodo_stablecoin_name)      # 充值正常
    # dodoTest.checkDepositQuoteToken(dodo_stablecoin_name, 100000000)      # 充值正常
    # dodoTest.checkDepositQuoteToken(dodo_stablecoin_name, 0)   # 充值0
    # dodoTest.checkDepositQuoteToken(dodo_stablecoin_name, 1)     # 充值最小精度资产
    # dodoTest.checkDepositQuoteToken(dodo_stablecoin_name, 1, True) # 充值超过自己拥有的资产
    # dodoTest.checkDepositQuoteToken(dodo_stablecoin_name, 10000, False, True, "up") # 充值前 price更新
    # dodoTest.checkDepositQuoteToken(dodo_stablecoin_name, 10000, False, True, "down") # 充值前 price更新
    # dodoTest.checkDepositWrongQuoteToken(dodo_stablecoin_name, 10000)
    # dodoTest.checkDepositWrongQuoteToken(dodo_stablecoin_name, 10000, False)

    # 当R状态为1, 即base价格高于市场价格，withdrawBase时会收取费用,放回池子中
    # 当R状态为2, 即base价格低于于市场价格，withdrawQuote时会收取费用, 放回池子中

    # dodoTest.checkWithdrawBaseToken(dodo_stablecoin_name)
    # dodoTest.checkWithdrawBaseToken(dodo_stablecoin_name, 99997828)
    # dodoTest.checkWithdrawBaseToken(dodo_stablecoin_name, 0)
    # dodoTest.checkWithdrawBaseToken(dodo_stablecoin_name, 1)
    # dodoTest.checkWithdrawBaseToken(dodo_stablecoin_name, 10000, True)
    # dodoTest.checkWithdrawBaseToken(dodo_stablecoin_name, 10000, False, True, "up")
    # dodoTest.checkWithdrawBaseToken(dodo_stablecoin_name, 10000, False, True, "down")
    # dodoTest.checkWithdrawBaseToken(dodo_stablecoin_name, 10000, user=admin)
    # dodoTest.checkWithdrawBaseToken(dodo_stablecoin_name, 1000000, user=lp)
    # dodoTest.checkWithdrawWrongBaseToken(dodo_stablecoin_name, 1000000)
    # dodoTest.checkWithdrawWrongBaseToken(dodo_stablecoin_name, 1000000, False)

    # dodoTest.checkWithdrawQuoteToken(dodo_stablecoin_name)
    # dodoTest.checkWithdrawQuoteToken(dodo_stablecoin_name, 0)
    # dodoTest.checkWithdrawQuoteToken(dodo_stablecoin_name, 1)
    # dodoTest.checkWithdrawQuoteToken(dodo_stablecoin_name, 1000, True)
    # dodoTest.checkWithdrawQuoteToken(dodo_stablecoin_name, 1000, False, True, "up")
    # dodoTest.checkWithdrawQuoteToken(dodo_stablecoin_name, 1000, False, True, "down")
    # dodoTest.checkWithdrawQuoteToken(dodo_stablecoin_name, 10000, user=admin)
    # dodoTest.checkWithdrawQuoteToken(dodo_stablecoin_name, 10000, user=lp)
    # dodoTest.checkWithdrawWrongQuoteToken(dodo_stablecoin_name, 10000)
    # dodoTest.checkWithdrawWrongQuoteToken(dodo_stablecoin_name, 10000, False)

    # dodoTest.checkDepositBaseToken(dodo_stablecoin_name)
    # dodoTest.checkWithdrawAllBaseToken(dodo_stablecoin_name)

    # dodoTest.checkDepositQuoteToken(dodo_stablecoin_name)
    # dodoTest.checkWithdrawAllQuoteToken(dodo_stablecoin_name)

    # 导入key
    # client.import_keys()

    # newUser = "eosdosnewdec"
    # newUser = "testc2testd2"
    # newUser = "tb2tc222222c"
    # newUser = "usd2gbp2222a"
    # newUser = "usd2hkd2222a"
    # newUser = "usd2hkdro22a"
    newUser = "usd2gbp44444"
    # newUser = "roxeliml1223"
    pubKey = "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH"

    # #创建账户
    # newAccount(newUser, pubKey, pubKey, avaKeys)
    # newAccount(admin, pubKey, pubKey, avaKeys)
    # deploy 合约
    # deployContract(admin, [pubKey])
    # newtoken
    # client.allowDosContracts()
    # max_supply = to_max_supply("TESTA", 100000000000, 6)
    # print(max_supply)
    # client.newtoken(tokenissuer, max_supply)
    # print(to_wei_asset(2000000, "TESTB", 6))
    # client.mint(lp, to_wei_asset(1000000, "TESTA", 6))
    # client.mint(lp, to_wei_asset(1000000, "TESTC", 6))
    # client.mint(lp, to_wei_asset(1000000, "TESTB", 6))

    # client.import_keys()
    # results = eosrpc.import_keys([acc2pub_keys[trader]])
    # print(results)
    # client.allowDosContracts()
    # client.mint(lp, to_wei_asset(740000, "TESTC", 6))
    # client.mint(lp, to_wei_asset(740000, "TESTC", 6))
    # client.mint(trader, to_wei_asset(8000000, "TESTD", 6))
    # client.mint(trader, to_wei_asset(8000000, "TESTA", 6))

    # client.allowDosContract(newUser, pubKey)
    # dodoTest.checkCreatePool(newUser, "TESTA", "TESTC", 6)
    # dodoTest.checkCreatePool(newUser, "TESTA", "TESTB", 6)
    # dodoTest.checkCreatePool(newUser, "TESTB", "TESTC", 6)
    # dodoTest.checkCreatePool(newUser, "USD", "HKD", 6)

    # client.enablex(admin, newUser, "enabletradin")
    # client.enablex(admin, newUser, "enablequodep")
    # client.enablex(admin, newUser, "enablebasdep")

    # client.setparameter(admin, newUser, "trading", 1)
    # client.setparameter(admin, newUser, "basedeposit", 1)
    # client.setparameter(admin, newUser, "quotedeposit", 1)

    # client.setparameter(admin, newUser, "k", 100)
    # client.setparameter(admin, newUser, "lpfeerate", 1)
    # client.setparameter(admin, newUser, "mtfeerate", 0)

    # dodoTest.checkDepositBaseToken(newUser)      # 未设置充值权限，不允许充值base
    # dodoTest.checkDepositQuoteToken(newDodoName)      # 未设置充值权限，不允许充值quote

    # print(dodoTest.getAccountBalance(lp, "TESTA", "TESTC", 6, 6))
    # print(dodoTest.getAccountBalance(lp, "USD", "HKD", 6, 6))
    # print(dodoTest.getAccountBalance(trader, "USD", "HKD", 6, 6))
    # client.depositbase(lp, newUser, to_wei_asset(10000, "USD", 6, "roxe.ro"))  #1000000 000000
    # client.depositbase(lp, newUser, to_wei_asset(10000, "TESTA", 6))  #1000000 000000
    # client.depositquote(lp, newUser, to_wei_asset(740000, "TESTC", 6))   #7750000 000000
    # client.depositquote(lp, newUser, to_wei_asset(77523, "HKD", 6, "roxe.ro"))   #7750000 000000
    # client.depositquote(lp, newUser, to_wei_asset(77523, "TESTB", 6))   #7750000 000000
    # client.depositbase(lp, newUser, to_wei_asset(1000000, "TESTB", 6))   #7750000 000000
    # 77523000000
    # print(dodoTest.getAccountBalance(lp, "USD", "HKD", 6, 6))
    # client.setprice(admin, to_sym("TESTA", 6), to_wei_asset(0.74, "TESTC", 6))
    # client.setprice(admin, to_sym("TESTA", 6), to_wei_asset(7.7523, "TESTB", 6))
    # client.setprice(admin, to_sym("TESTB", 6), to_wei_asset(0.74, "TESTC", 6))
    # client.setprice(admin, to_sym("USD", 6), to_wei_asset(7.7523, "HKD", 6))
    #
    # client.setprice(oracleadmin, to_sym("RUSD", 6), to_wei_asset(7.75, "RHKD", 6))
    # client.setprice(oracleadmin, to_sym("USD", 6), to_wei_asset(7.75, "HKD", 6))
    # client.setprice(oracleadmin, to_sym("USD", 6), to_wei_asset(0.74, "GBP", 6))
    # client.setprice(oracleadmin, to_sym("GBP", 6), to_wei_asset(10, "HKD", 6))

    # info = dodoTest.getDodoInfo(newUser)
    # info = dodoTest.getDodoInfo("usd2gbp44444")
    # print(dodoTest.getAccountBalance(lp, "USD", "GBP", 6, 6))
    # print(dodoTest.getAccountBalance(trader, "USD", "GBP", 6, 6))
    # print(dodoTest.getAccountBalance("2dwjx243lvv4", "USD", "GBP", 6, 6))
    # price = dodoTest.getOraclePrice("GBP", info["dodos"]["_ORACLE_"], 6)
    # price = dodoTest.getOraclePrice("HKD", info["dodos"]["_ORACLE_"], 6)
    # price = dodoTest.getOraclePrice("TESTB", info["dodos"]["_ORACLE_"], 6)
    # print(price)

    # newUser = "usd2hkdro22a" # usd hkd 1万 sell 1
    # newUser = "usd2hkdro22b" # usd hkd 1万 buy 1
    # newUser = "usd2hkdro22c" # usd hkd 1万 sell 10
    # newUser = "usd2hkdro22d" # usd hkd 1万 buy 10
    # newUser = "usd2hkdro22e" # usd hkd 1万 sell 100
    # newUser = "usd2hkdro22f" # usd hkd 1万 buy 100
    # newUser = "usd2hkdro22g" # usd hkd 1万 sell 1000
    # newUser = "usd2hkdro22h" # usd hkd 1万 buy 1000
    # newUser = "usd2hkdro22i" # usd hkd 1万 sell 10000
    # newUser = "usd2hkdro22j" # usd hkd 1万 buy 10000
    # newUser = "usd2hkdro33a" # usd hkd 100万 sell 1
    # newUser = "usd2hkdro33b" # usd hkd 100万 buy 1
    # newUser = "usd2hkdro33c" # usd hkd 100万 sell 10
    # newUser = "usd2hkdro33d" # usd hkd 100万 buy 10
    # newUser = "usd2hkdro33e" # usd hkd 100万 sell 100
    # newUser = "usd2hkdro33f" # usd hkd 100万 buy 100
    # newUser = "usd2hkdro33g" # usd hkd 100万 sell 1000
    # newUser = "usd2hkdro33h" # usd hkd 100万 buy 1000
    # newUser = "usd2hkdro33i" # usd hkd 100万 sell 10000
    # newUser = "usd2hkdro33j" # usd hkd 100万 buy 10000
    # newUser = "usd2hkdro33k" # usd hkd 100万 sell 100000
    # newUser = "usd2hkdro33l" # usd hkd 100万 buy 100000
    # newUser = "usd2hkdro33m" # usd hkd 100万 sell 1000000
    # newUser = "usd2hkdro33n" # usd hkd 100万 buy 1000000
    # newUser = "usd2hkdro44a" # usd hkd 1万 buy 1
    # newUser = "usd2hkdro44b" # usd hkd 1万 buy 10
    # newUser = "usd2hkdro44c" # usd hkd 1万 buy 9992
    # newUser = "usd2gbplml11" # usd hkd 1万 buy 9992
    # newUser = "usd2gbp44444" # usd hkd 1万 buy 9992
    # newUser = "usd2gbp44444" # usd hkd 1万 buy 9992
    # newUser = "usd2gbp44444" # usd hkd 1万 buy 9992
    # newUser = "usd2gbplml11" # usd hkd 1万 buy 9992
    newUser = "usd2gbplml12" # usd hkd 1万 buy 9992
    newUser = "usd2gbplml13" # usd hkd 1万 buy 9992
    newUser = "usd2gbplml14" # usd hkd 1万 buy 9992
    newUser = "usd2gbplml21" # usd hkd 1万 buy 9992
    newUser = "usd2gbplml22" # usd hkd 1万 buy 9992
    newUser = "usd2gbp44444" # usd hkd 1万 buy 9992
    newUser = "re.usdgbp" # usd hkd 1万 buy 9992
    newUser = "re.usdinr" # usd hkd 1万 buy 9992
    pubKey = "ROXE6ftHab5c81LAcL1izHNyFVawBaZTEpFDXN3BYybx1pcJHQsTmH"
    # newAccount(newUser, pubKey, pubKey, avaKeys)
    # newAccount(admin, pubKey, pubKey, avaKeys)

    # print(dodoTest.getAccountBalance(lp, "USD", "GBP", 6, 6))
    # print(dodoTest.getAccountBalance(trader, "USD", "GBP", 6, 6))
    # print(dodoTest.getAccountBalance(newUser, "USD", "GBP", 6, 6))
    # print(getQuoteCapitalBalanceOf(lp, newUser, "USD"))
    # print(getQuoteCapitalBalanceOf(lp, newUser, "GBP"))
    # print(getQuoteCapitalBalanceOf(trader, newUser, "USD"))
    # print(getQuoteCapitalBalanceOf(trader, newUser, "HKD"))

    # dodoTest.client.setparameter(admin, newUser, "k", 10)
    # dodoTest.checkWithdrawQuoteToken(newUser, 100000000000, user=lp)
    # print(getQuoteCapitalBalanceOf(trader, newUser, "GBP"))

    # print(getLpBaseBalance(lp, admin))
    # print(getTokenBalance(lp, admin))
    # print(getTokenSupply(newUser, admin))
    # print(getTokenSupply(lp, newUser))
    # print(getTokenBalance("usd2hkdro22a", "roxe.ro"))
    # print(getTokenBalance("usd2hkdro22b", "roxe.ro"))

    # dodoTest.checkCreatePool(newUser, "USD", "GBP", 6)
    # client.setparameter(admin, newUser, "trading", 1)
    # client.setparameter(admin, newUser, "basedeposit", 1)
    # client.setparameter(admin, newUser, "quotedeposit", 1)

    # dodoTest.checkDepositBaseToken(newUser, 100000 000000)
    # dodoTest.checkDepositQuoteToken(newUser,   73000000000)
    # print(dodoTest.getAccountBalance(lp, "USD", "GBP", 6, 6))
    # client.allowDosContract(lp, acc2pub_keys[lp])
    # client.allowDosContract(newUser, pubKey)
    # client.depositbase(lp, newUser, to_wei_asset(10000, "USD", 6, "roxe.ro"))
    # client.depositbase(lp, newUser, to_wei_asset(1000000, "USD", 6, "roxe.ro"))
    # print(dodoTest.getAccountBalance(lp, "USD", "GBP", 6, 6))
    # print(dodoTest.getAccountBalance(lp, "USD", "GBP", 6, 6))
    # client.depositquote(lp, newUser, to_wei_asset(7300, "GBP", 6, "roxe.ro"))
    # client.depositquote(lp, newUser, to_wei_asset(77523, "HKD", 6, "roxe.ro"))
    # client.depositquote(lp, newUser, to_wei_asset(7752300, "HKD", 6, "roxe.ro"))
    # time.sleep(2)
    # print(dodoTest.getAccountBalance(lp, "USD", "GBP", 6, 6))
    # client.allowDosContract(newUser, pubKey)

    # client.setprice(admin, to_sym("USD", 6), to_wei_asset(7.7523, "HKD", 6))
    # client.setprice(admin, to_sym("USD", 6), to_wei_asset(7.7523, "HKD", 6))
    # client.setprice(oracleadmin, to_sym("USD", 6), to_wei_asset(0.73, "GBP", 6, "roxe.ro"))

    # dodoTest.client.allowDosContract(trader, acc2pub_keys[trader])

    # dodoTest.checkDepositBaseToken(newUser, int(1 * 1000000))
    # dodoTest.checkDepositQuoteToken(newUser, int(0.73 * 1000000))
    # dodoTest.checkWithdrawBaseToken(newUser, int(0.1 * 1000000))
    # dodoTest.checkWithdrawQuoteToken(newUser, int(0.73 * 1000000))
    # dodoTest.checkWithdrawQuoteToken(newUser, int(7.3 * 1000000), user=lp)
    # dodoTest.checkDepositBaseToken(newUser, int(10 * 1000000))
    # dodoTest.checkWithdrawAllBaseToken(newUser, user=trader)
    # dodoTest.checkDepositQuoteToken(newUser, int(7.3 * 1000000))
    # dodoTest.checkWithdrawAllQuoteToken(newUser, user=trader)

    info = dodoTest.getDodoInfo(newUser)
    print(info)
    # price = dodoTest.getOraclePrice("HKD", info["dodos"]["_ORACLE_"], 6)
    # price = dodoTest.getOraclePrice("GBP", info["dodos"]["_ORACLE_"], 6)
    # print(price)
    # querySellBaseToken(int(1 * 1000000), info, newUser, price)
    # queryBuyBaseToken(int(1 * 1000000), info, newUser, price)
    # queryBuyBaseToken(1330522, info, newUser, price)
    # dodoTest.checkWithdrawQuoteToken(newUser, user=lp)
    # dodoTest.checkWithdrawAllBaseToken(newUser, user=lp)
    # dodoTest.checkWithdrawAllBaseToken(newUser, user=lp)
    # dodoTest.checkWithdrawAllQuoteToken(newUser, user=lp)
    # querySellBaseToken(int(1000 * 1000000), info, newUser, price)

    # dodoTest.checkBuyBaseToken(newUser, int(200 * 1000000))
    # dodoTest.checkSellBaseToken(newUser, int(1 * 1000000))
    # dodoTest.checkSellBaseToken(newUser, int(500 * 1000000))

    # dodoTest.checkSellQuoteToken(newUser, int(0.00001 * 1000000))
    # dodoTest.checkSellQuoteToken(newUser, int(0.0001 * 1000000))
    # dodoTest.checkSellQuoteToken(newUser, int(0.001 * 1000000))
    # dodoTest.checkSellQuoteToken(newUser, int(0.01 * 1000000))
    # dodoTest.checkSellQuoteToken(newUser, int(1.123456 * 1000000))
    # dodoTest.checkSellQuoteToken(newUser, int(0.1 * 1000000))
    # dodoTest.checkSellQuoteToken(newUser, int(1 * 1000000))
    # dodoTest.checkSellQuoteToken(newUser, int(2190 * 1000000))
    # dodoTest.checkSellQuoteToken(newUser, int(30 * 1000000))
    # dodoTest.checkSellQuoteToken(newUser, int(1000 * 1000000))
    # dodoTest.checkSellQuoteToken(newUser, int(300 * 1000000))
    # print(DecimalMath.divFloor(10, price))

    def getJsCalPrice(action, amount):
        cmd1 = "ts-node ./PricingFormulaLocal.ts {} {}".format(action, amount)
        infos = subprocess.check_output(cmd1, shell=True,
                                        cwd="/Users/admin/js/RoxeChainTest/test/roxetest/src/dodo/pricing")
        split_info = infos.decode().strip().split("\n")
        calRes = split_info[-1]
        if "invalid" in calRes:
            print("参数错误")
        else:
            print(calRes)

    # getJsCalPrice('sellquote', 12345678)
    # dodoTest.client.sellquote(trader, newUser, to_wei_asset(12.345678, "GBP", 6, "roxe.ro"), to_wei_asset(2000000, "USD", 6, "roxe.ro"))

    # getJsCalPrice('buybase', 1234567)
    # dodoTest.client.buybasetoken(trader, newUser, to_wei_asset(1.234567, "USD", 6, "roxe.ro"), to_wei_asset(0, "GBP", 6, "roxe.ro"))

    # getJsCalPrice('sellbase', 2345678)
    # dodoTest.client.sellbasetoken(trader, newUser, to_wei_asset(2.345678, "USD", 6, "roxe.ro"), to_wei_asset(10000000, "GBP", 6, "roxe.ro"))

    # print(dodoTest.getAccountBalance(trader, "USD", "HKD", 6, 6))
    # dodoTest.checkBuyBaseToken(newUser, int(9992 * 1000000), 1)
    # print(2**60)
    # dodoTest.checkBuyBaseToken(newUser, int(9992 * 1000000), 80000000000)
    # dodoTest.checkSellBaseToken(newUser, int(1000000 * 1000000), 1000000000000)
    # dodoTest.checkSellBaseToken(newUser, int(1000000 * 1000000), 1)
    # print(dodoTest.getAccountBalance(trader, "USD", "HKD", 6, 6))
    # client.removeDodo(admin, newUser)

    # 1035554238696915
    # 1219047619 579024

    # client.setparameter(admin, newUser, "k", 100)
    # client.setparameter(admin, "usd2gbp44444", "lpfeerate", 595)
    # client.setparameter(admin, "usd2gbp44444", "mtfeerate", 105)

    # client.setparameter(admin, "usd2hkd44444", "lpfeerate", 680)
    # client.setparameter(admin, "usd2hkd44444", "mtfeerate", 120)

    # querySellBaseToken(int((1000) * 1000000), info, newUser, price)
    # queryBuyBaseToken(int((1323.603731) * 1000000), info, newUser, price)
    # querySellBaseToken(int((10000) * 1000000), info, newUser, price)
    # queryBuyBaseToken(1000 * 1000000, info, newUser, price)
    # queryBuyBaseToken(503597, info, newUser, price)
    # queryBuyBaseToken(10000 * 10000, info, "usd2hkd22222", price)
    # print(info)
    # print(price)

    # 构造数据

    # client.depositquote(lp, newUser, to_wei_asset(740000, "TESTC", 6))
    # dodoTest.checkDepositQuoteToken(newUser, int(740000 * 1000000), user=lp)
    # dodoTest.checkDepositQuoteToken(newUser, int(740000 * 1000000), user=lp)
    # dodoTest.checkWithdrawQuoteToken(newUser, int(740000 * 1000000), user=lp)
    # dodoTest.checkWithdrawQuoteToken(newUser, int(740000 * 1000000), user=lp)

    # #base 1000000000000 quote 740000000000
    # #tagertBase 1000000000000 targetQuote 740000000000

    # client.removeDodo(admin, newUser)

