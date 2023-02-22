# coding=utf-8
# author: Li MingLei
# date: 2021-11-20
import datetime
import functools
import random

from roxe_libs.baseApi import *
import logging
from roxe_libs.Global import Global
from roxe_libs import settings, ApiUtils
from roxe_libs.DBClient import Mysql
from roxepy.clroxe import Clroxe
import os
import copy
import time
from RMN.RMNStatusCode import RmnCodEnum


class RMNApiClient:

    def __init__(self, host, env, api_key=None, sec_key=None, version="001", check_db=False, sql_cfg=None, node_rsa_key=None, chain_host=None):
        self.host = host
        self.env = env
        self.api_key = api_key
        self.sec_key = sec_key
        self.version = version
        self.iso_date_time_format = "%Y-%m-%dT%H:%M:%S"
        self.iso_date_format = "%Y-%m-%d"
        self.node_rsa_key = "../RTS/keys/rsa_private_key.pem"
        self.chain_host = chain_host
        self.chain_client = Clroxe(chain_host.rstrip("/v1")) if chain_host else None
        if node_rsa_key:
            self.node_rsa_key = node_rsa_key

        self.dir_path = os.path.dirname(os.path.abspath(__file__))
        # 获取全局的日志记录logger
        self.logger = logging.getLogger(Global.getValue(settings.logger_name))
        self.check_db = check_db
        if check_db:
            self.mysql = Mysql(sql_cfg["mysql_host"], sql_cfg["port"], sql_cfg["user"], sql_cfg["password"],
                               sql_cfg["db"], True)
            self.mysql.connect_database()

        self.rts_db_name = "roxe_rts_v3"

    def makeEncryptHeaders(self, headers, body, secret_key, replaceSignAlgorithm=None, replaceKeyFile=False, popBody=None, repBody=None):
        # 为i不将中文等字符转义，ensure_ascii设为False
        parse_body = json.dumps(body, ensure_ascii=False) if isinstance(body, dict) else str(body)
        nonce = ApiUtils.generateString(16)
        associated_data = ApiUtils.generateString(16)
        # print(parse_body, nonce, associated_data, secret_key)
        if replaceSignAlgorithm and replaceSignAlgorithm != "NO_ENCRYPTION":
            des_cipher_text = ApiUtils.getSignByHmacSha256(parse_body, secret_key)
            # des_cipher_text = des_encrypt(parse_body, secKey)

            encrypt_data = {
                "resource": {
                    "algorithm": "DES",
                    "ciphertext": des_cipher_text.decode('utf-8')
                }
            }
        elif replaceSignAlgorithm == "NO_ENCRYPTION":
            encrypt_data = {
                "resource": {
                    "algorithm": "NO_ENCRYPTION",
                    "ciphertext": parse_body
                }
            }
        else:
            aes_cipher_text = ApiUtils.aes_encrypt(parse_body, nonce, associated_data, secret_key)

            encrypt_data = {
                "resource": {
                    "algorithm": "AES_256_GCM",
                    "ciphertext": aes_cipher_text.decode('utf-8'),
                    "associatedData": associated_data,
                    "nonce": nonce
                }
            }
        if popBody:
            encrypt_data["resource"].pop(popBody)
        if repBody:
            encrypt_data["resource"][repBody] = "1234"
        parse_en_body = json.dumps(encrypt_data)
        # self.logger.debug("原始请求数据: {}".format(parse_body))
        rsa_data = headers["sndDtTm"] + "::" + parse_en_body
        # self.logger.debug("原始加密数据: {}".format(rsa_data))
        pri_key = "../RTS/keys/private_key.pem" if replaceKeyFile else self.node_rsa_key
        sign = ApiUtils.rsa_sign(rsa_data, os.path.join(self.dir_path, pri_key))
        # self.logger.debug("rsa签名后数据: {}".format(sign))
        headers["sign"] = sign.decode("utf-8")
        return headers, parse_en_body

    def verify_response(self, response):
        r_data = response.text
        res_en_data = response.headers["timestamp"] + "::" + r_data
        verified = ApiUtils.rsa_verify(res_en_data, response.headers["sign"], os.path.join(self.dir_path, "../RTS/rts_rsa_public_key.pem"))
        assert verified, "response验签失败: {}".format(response.headers["sign"])
        self.logger.info("response验签成功")

    def decrypt_response(self, response, node_secret_key):
        if response.json()["code"] != "0":
            return response.json()
        else:
            r_data = response.json()["data"]["resource"]
            res_de_data = ApiUtils.aes_decrypt(r_data["ciphertext"], r_data["nonce"], r_data["associatedData"], node_secret_key)
            self.logger.info(f"结果解密为: {res_de_data}")
            return json.loads(res_de_data)

    def make_header(self, sndrRID, sndrApiKey, msgTp, msgID=None, sign="123", sndDtTm=None, rcvrRID=None, sysFlg="Roxe"):
        sndDtTm = sndDtTm if sndDtTm else datetime.datetime.now().strftime(self.iso_date_time_format)
        msgID = msgID if msgID else self.make_msg_id()
        headers = {
            "version": self.version,
            "sndrRID": sndrRID,
            "sndrApiKey": sndrApiKey,
            "rcvrRID": rcvrRID,
            "sndDtTm": sndDtTm,
            "msgTp": msgTp,
            "msgId": msgID,
            "msgRefID": "",
            "sysFlg": sysFlg,
            "sign": sign,
            "Content-Type": "application/json"
        }
        return headers

    def make_msg_id(self):
        first = 1 if self.env == "prod" else 0
        cur_now = datetime.datetime.now()
        cur_day = cur_now.strftime("%Y%m%d")
        random_value = int(cur_now.timestamp() * 1000000)
        return f"{first}{cur_day}{random_value}"

    def make_group_header(self, senderRo, receiverRo, msg_id, settlementMethod="CLRG", clearingSystemCode="ROXE", hasSttlmInf=True):
        group_header = {
            "msgId": msg_id,
            "instgAgt": senderRo,
            "instdAgt": receiverRo,
            "creDtTm": datetime.datetime.now().strftime(self.iso_date_time_format),
        }
        if hasSttlmInf:
            group_header["sttlmInf"] = {"sttlmMtd": settlementMethod, "clrSysCd": clearingSystemCode}
        return group_header

    def make_msg_header(self, senderRo, msg_id):
        # msg_id = self.make_msg_id()
        msg_header = {
            "msgId": msg_id,
            "creDtTm": datetime.datetime.now().strftime(self.iso_date_time_format),
            "instgPty": senderRo
        }
        return msg_header

    def make_end_to_end_id(self):
        e_id = f"test_rmn_{int(datetime.datetime.now().timestamp() * 1000)}"
        self.logger.debug(f"生成endToEndId: {e_id}")
        return e_id

    def make_roxe_agent(self, roxeId, issue, name="china bank", **kwargs):
        agent = {"finInstnId": {"othr": {"id": roxeId, "schmeCd": "ROXE", "issr": issue}, "nm": name}}

        for k, v in kwargs.items():
            agent[k] = v
        self.logger.debug(f"生成agent: {agent}")
        return agent

    def make_terrapay_roxe_agent(self, name, receiverBankCode, **kwargs):
        # "clrSysMmbId": {"clrSysCd": receiverBankCode},
        # "othr": {"id": roxeId, "schmeCd": "ROXE", "issr": issue}
        agent = {"finInstnId": {"nm": name, "bicFI": receiverBankCode, }}

        for k, v in kwargs.items():
            agent[k] = v
        self.logger.debug(f"生成agent: {agent}")
        return agent

    def make_terrapay_roxe_cdtr(self, receiverName, receiverCountry, **kwargs):
        # "pstlAdr": {"twnNm": "Manila", "adrLine": "No. 1 Financial Street"},
        cdtr = {"nm": receiverName, "ctryOfRes": receiverCountry,
                "pstlAdr": {"ctry": receiverCountry},
                "prvtId": {"dtAndPlcOfBirth": {"ctryOfBirth": receiverCountry, "cityOfBirth": "on the earth"}}}
        for k, v in kwargs.items():
            cdtr[k] = v
        self.logger.debug(f"生成agent: {cdtr}")
        return cdtr

    def make_RCCT_information(self, sendCurrency, recCurrency, debtor, debtorAgent, creditor, creditorAgent, fee, feeAgent, inAmount=None, **kwargs):
        end_to_end_id = self.make_end_to_end_id()
        pmtId = {"endToEndId": end_to_end_id, "txId": end_to_end_id}
        # 如果指定amount则使用指定的amount作为下单数量，否则随机生成
        amount = inAmount if inAmount else ApiUtils.randAmount(100, 2, 30)
        from_amount = str(amount)
        to_amount = str(ApiUtils.parseNumberDecimal(amount - fee, 2, True))
        cdtTrfTxInf = {
            "instdAmt": {"ccy": sendCurrency, "amt": from_amount},
            "intrBkSttlmAmt": {"ccy": sendCurrency, "amt": to_amount},
            "intrBkSttlmDt": datetime.datetime.now().strftime(self.iso_date_format),
            "pmtId": pmtId,
            "dbtr": debtor,
            "dbtrAcct": {"acctId": "123456789012", "nm": "Jethro Lee", "ccy": sendCurrency},
            "dbtrAgt": debtorAgent,
            # "dbtrIntrmyAgt": dbtrIntrmyAgt,
            # "intrmyAgt": intrmyAgt,
            "cdtr": creditor,
            "cdtrAcct": {"nm": "Li XX", "ccy": recCurrency, "acctId": "987654321"},
            "cdtrAgt": creditorAgent,
            # "cdtrIntrmyAgt": cdtrIntrmyAgt,
            "purp": {"cd": "cod1", "desc": "transfer my money"},
            "rltnShp": {"cd": "457", "desc": "hellos"},
            "chrgsInf": [
                {"agt": {"id": feeAgent, "schmeCd": "ROXE"}, "sndFeeAmt": {"amt": str(ApiUtils.parseNumberDecimal(fee, 2, True)), "ccy": sendCurrency}}],
            "splmtryData": {
                "envlp": {"cnts": {"sndrAmt": from_amount, "sndrCcy": sendCurrency, "rcvrCcy": recCurrency}},
                "rmrk": f"remark {time.time()}",
                "addenda": {"tel": "!23123123xx"},
                }
        }
        for k, v in kwargs.items():
            cdtTrfTxInf[k] = v
        return cdtTrfTxInf

    def make_RPRN_information(self, feeNode, sendCurrency, recCurrency, old_tx_info, old_last_fee, isharf=False, **kwargs):
        """
        构造return报文
        对于完全结算, 发起节点为交易完成后的最后一个节点[PN2或SN2]
        对于半结算, 发起节点RMN节点
        :param feeNode: return费用的节点
        :param sendCurrency: return的发起币种
        :param recCurrency: return的接受币种
        :param old_tx_info: 进行return的节点A收到的原来的RCCT消息
        :param old_last_fee: 最后节点的费用
            如果最后一个节点为PN2节点: 为pn2节点的deliver费用
            如果最后一个节点为SN2节点:
                发生结算，SN2的deliver费用
                未发生结算，为0
        :param return_fee: return流程中的第一个节点的退款费用, 如果半结算为0
        :param kwargs:
        """
        re_amount = ApiUtils.parseNumberDecimal(float(old_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"]) - old_last_fee, 2, True)
        return_fee = 0
        if not isharf:
            b_type = self.matchBusinessTypeByCdtTrfTxInf(old_tx_info["cdtTrfTxInf"])
            re_type = b_type[2] + "2" + b_type[0]
            return_fee = self.getNodeFeeInDB(feeNode, recCurrency, re_amount, re_type, True)["in"]
        cdtTrfTxInf = {
            "orgnlGrpInf": {"orgnlMsgId": old_tx_info["grpHdr"]["msgId"], "orgnlMsgNmId": "RCCT"},
            "orgnlTxId": old_tx_info["cdtTrfTxInf"]["pmtId"]["txId"],
            "orgnlIntrBkSttlmAmt": old_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"],
            "rtrdInstdAmt": {"ccy": sendCurrency, "amt": str(re_amount)},
            "rtrdIntrBkSttlmAmt": {"ccy": sendCurrency, "amt": "%.2f" % (re_amount - return_fee)},
            # "chrgsInf": [{"agt": {"id": feeNode, "schmeCd": "ROXE"}, "sndFeeAmt": {"ccy": sendCurrency, "amt": f"{return_fee:.2f}"}}],
            "instgAgt": "risn2roxe51",
            "instdAgt": old_tx_info["grpHdr"]["instdAgt"],
            "rtrChain": {},
            "rtrRsnInf": {"rsn": {"cd": "1234", "prtry": "return money"}},
            "splmtryData": {"envlp": {"cnts": {"sndrAmt": str(re_amount), "sndrCcy": sendCurrency, "rcvrCcy": recCurrency}}}
        }
        if return_fee > 0:
            cdtTrfTxInf["chrgsInf"] = [{"agt": {"id": feeNode, "schmeCd": "ROXE"}, "sndFeeAmt": {"ccy": sendCurrency, "amt": f"{return_fee:.2f}"}}]
        # 交换原交易链条
        rtrChains = ["cdtr", "cdtrAcct", "cdtrAgt", "cdtrIntrmyAgt", "dbtr", "dbtrAcct", "dbtrAgt", "dbtrIntrmyAgt"]
        for agt in rtrChains:
            if agt in old_tx_info["cdtTrfTxInf"]:
                rep_key = agt.replace("cdtr", "dbtr") if agt.startswith("cdtr") else agt.replace("dbtr", "cdtr")
                cdtTrfTxInf["rtrChain"][rep_key] = old_tx_info["cdtTrfTxInf"][agt]
        if "intrmyAgt" in old_tx_info["cdtTrfTxInf"]:
            cdtTrfTxInf["rtrChain"]["intrmyAgt"] = old_tx_info["cdtTrfTxInf"]["intrmyAgt"]
        for k, v in kwargs.items():
            cdtTrfTxInf[k] = v
        if "ccy" not in cdtTrfTxInf["rtrChain"]["cdtrAcct"]:
            cdtTrfTxInf["rtrChain"]["cdtrAcct"]["ccy"] = recCurrency
        self.logger.debug("")
        return cdtTrfTxInf

    def make_channel_RCCT_information(self, sendCurrency, recCurrency, debtor, debtorAgent, creditor, creditorAgent, cdtrIntrmyAgt, fee, feeAgent, addenda, acctId, inAmount=None, **kwargs):
        end_to_end_id = self.make_end_to_end_id()
        pmtId = {"endToEndId": end_to_end_id, "txId": end_to_end_id}
        amount = ApiUtils.randAmount(100, 2, 30)
        if inAmount:
            amount = inAmount
        from_amount = str(amount)
        to_amount = str(ApiUtils.parseNumberDecimal(amount - fee, 2, True))
        cdtTrfTxInf = {
            "instdAmt": {"ccy": sendCurrency, "amt": from_amount},
            "intrBkSttlmAmt": {"ccy": sendCurrency, "amt": to_amount},
            "intrBkSttlmDt": datetime.datetime.now().strftime(self.iso_date_format),
            "pmtId": pmtId,
            "dbtr": debtor,
            "dbtrAcct": {"acctId": "123456789012", "nm": "Jethro Lee"},
            "dbtrAgt": debtorAgent,
            # "dbtrIntrmyAgt": dbtrIntrmyAgt,
            # "intrmyAgt": intrmyAgt,
            "cdtr": creditor,
            "cdtrAcct": {"ccy": recCurrency, "acctId": acctId},  # "nm": "Li XX",
            "cdtrAgt": creditorAgent,
            "cdtrIntrmyAgt": cdtrIntrmyAgt,
            "purp": {"desc": "Gift"},
            "rltnShp": {"desc": "Friend"},
            "chrgsInf": [
                {"agt": {"id": feeAgent, "schmeCd": "ROXE"}, "sndFeeAmt": {"amt": str(fee), "ccy": sendCurrency}}],
            "splmtryData": {
                "envlp": {"cnts": {"sndrAmt": from_amount, "sndrCcy": sendCurrency, "rcvrCcy": recCurrency}},
                "addenda": addenda}
        }
        for k, v in kwargs.items():
            cdtTrfTxInf[k] = v
        return cdtTrfTxInf

    def make_RCSR_information(self, rcct_msg, cdtDbtInd, nodeId):
        instgAgt = rcct_msg["grpHdr"]["instgAgt"]
        if cdtDbtInd == "DBIT":
            if rcct_msg["msgType"] == "RCCT":
                debtor = rcct_msg["cdtTrfTxInf"]["dbtrAgt"]
            else:
                if "othr" in rcct_msg["txInf"]["rtrChain"]["dbtrAgt"]["finInstnId"]:
                    debtor = rcct_msg["txInf"]["rtrChain"]["dbtrAgt"]
                else:
                    debtor = rcct_msg["txInf"]["rtrChain"]["dbtrIntrmyAgt"]
            creditor = self.make_roxe_agent(nodeId, "SN")
        else:
            debtor = self.make_roxe_agent(nodeId, "SN")
            creditor = self.make_roxe_agent("risn2roxe51", "VN")
        end_to_end_id = self.make_end_to_end_id()
        if rcct_msg["msgType"] == "RCCT":
            cdtTrfTxInf = {
                "intrBkSttlmAmt": rcct_msg["cdtTrfTxInf"]["intrBkSttlmAmt"].copy(),
                "intrBkSttlmDt": datetime.datetime.now().strftime(self.iso_date_format),
                "pmtId": {"endToEndId": end_to_end_id, "txId": end_to_end_id},
                "dbtr": debtor,
                "cdtr": creditor,
                "cdtrAcct": rcct_msg["cdtTrfTxInf"]["cdtrAcct"],
                "rmtInf": {"orgnlMsgID": rcct_msg["grpHdr"]["msgId"], "orgnlMsgTp": "RCCT", "instgAgt": instgAgt},
                "splmtryData": {"envlp": {"ustrd": {"cdtDbtInd": cdtDbtInd}}}
            }
            # 从RTS系统下的订单，没有dbtrAcct
            dbtrAcct = rcct_msg["cdtTrfTxInf"].get("dbtrAcct")
            if dbtrAcct: cdtTrfTxInf["dbtrAcct"] = dbtrAcct
        elif rcct_msg["msgType"] == "RPRN":
            cdtTrfTxInf = {
                "intrBkSttlmAmt": rcct_msg["txInf"]["rtrdIntrBkSttlmAmt"].copy(),
                "intrBkSttlmDt": datetime.datetime.now().strftime(self.iso_date_format),
                "pmtId": {"endToEndId": end_to_end_id, "txId": end_to_end_id},
                "dbtr": debtor,
                "dbtrAcct": rcct_msg["txInf"]["rtrChain"]["dbtrAcct"],
                "cdtr": creditor,
                "cdtrAcct": rcct_msg["txInf"]["rtrChain"]["cdtrAcct"],
                "rmtInf": {"orgnlMsgID": rcct_msg["grpHdr"]["msgId"], "orgnlMsgTp": "RPRN", "instgAgt": instgAgt},
                "splmtryData": {"envlp": {"ustrd": {"cdtDbtInd": cdtDbtInd}}}
            }
        else:
            cdtTrfTxInf = {}
        return cdtTrfTxInf

    def make_RTPC_information(self, rcct_msg, stsId):
        orgnlMsgId = rcct_msg["grpHdr"]["msgId"] if self.check_db else rcct_msg["grpHdr"]["msgId"]
        if rcct_msg["msgType"] == "RCCT":
            orgnlInstrId = rcct_msg["cdtTrfTxInf"]["pmtId"]["instrId"] if "instrId" in rcct_msg["cdtTrfTxInf"]["pmtId"] else ""
            orgnlEndToEndId = rcct_msg["cdtTrfTxInf"]["pmtId"]["endToEndId"]
            orgnlTxId = rcct_msg["cdtTrfTxInf"]["pmtId"]["txId"]
        else:
            orgnlInstrId = rcct_msg["txInf"]["orgnlInstrId"] if "orgnlInstrId" in rcct_msg["txInf"] else ""
            orgnlEndToEndId = None
            orgnlTxId = rcct_msg["txInf"]["rtrId"]
        instgAgt = "risn2roxe51"
        msg = {
            "orgnlGrpInfAndSts": {
                "orgnlMsgId": orgnlMsgId,
                "orgnlMsgNmId": rcct_msg["msgType"]
            },
            "txInfAndSts": {
                "stsId": stsId,
                "orgnlInstrId": orgnlInstrId,
                "orgnlEndToEndId": orgnlEndToEndId,
                "orgnlTxId": orgnlTxId,
                "stsRsnInf": None,
                "acctSvcrRef": "TXNS",
                "instgAgt": instgAgt
            }
        }
        return msg

    def make_RTSQ_information(self, search_msg_id, instgPty, txId=None, endToEndId=None, instrId=None, instdPty=None, ntryTp="STS", msgTp=None):
        msg = {
            "pmtSch": {
                "msgId": search_msg_id,
                "msgTp": msgTp,
            },
            "ptySch": {
                "instgPty": instgPty,
                "instdPty": instdPty,
            },
            "ntryTp": ntryTp,
        }
        if endToEndId or txId:
            msg["pmtSch"]["pmtId"] = {
                "txId": txId,
                "endToEndId": endToEndId,
                "instrId": instrId,
            }
        self.logger.debug(f"生成RTSQ请求内容: {msg}")
        return msg

    def make_RRLQ_information(self, sndrCcy, rcvrCcy, sndrAmt=None, rcvrAmt=None, cdtrAcct=None, cdtrAgt=None, qryTp=None, cd=None):
        rtgQryDef = {
            "qryTp": qryTp,
            "pmtTpInf": {"ctgyPurp": {"cd": cd}},
            "qryCrit": {
                "rmtInf": {
                    "sndrAmt": sndrAmt,
                    "sndrCcy": sndrCcy,
                    "rcvrAmt": rcvrAmt,
                    "rcvrCcy": rcvrCcy,
                },
                "cdtrAcct": cdtrAcct,
                "cdtrAgt": cdtrAgt,
            },
        }
        if cd is None:
            rtgQryDef.pop("pmtTpInf")
        self.logger.debug(f"生成RRLQ查询条件: {rtgQryDef}")
        return rtgQryDef

    # API函数
    def post_request(self, method, headers, msg, secretKey, popHeader=None, replaceKeyFile=False, popBody=None, repBody=None):
        en_headers, en_body = self.makeEncryptHeaders(headers, msg, secretKey, replaceKeyFile=replaceKeyFile, popBody=popBody, repBody=repBody)
        if popHeader:
            en_headers.pop(popHeader)
        # if popBody:
        #     en_body = json.loads(en_body)
        #     en_body["resource"].pop(popBody)
        #     en_body = json.dumps(en_body)
        # if repBody:
        #     en_body = json.loads(en_body)
        #     en_body["resource"][repBody] = "1234"
        #     en_body = json.dumps(en_body)
        method_url = self.host + "/" + method
        res = sendPostRequest(method_url, en_body, headers=en_headers)
        self.logger.debug(f"请求url: {method_url}")
        self.logger.debug(f"请求headers: {headers}")
        self.logger.debug(f"请求参数: {en_body}")
        self.logger.info(f"原始参数: {json.dumps(msg, ensure_ascii=False)}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def submit_transaction(self, nodeSecretKey, headers, grpHdr, cdtTrfTxInf, popHeader=None, replaceKeyFile=False, popBody=None, repBody=None):
        msg = {
            "version": self.version,
            "msgType": "RCCT",
            "grpHdr": grpHdr,
            "cdtTrfTxInf": cdtTrfTxInf
        }
        self.logger.info("提交交易请求")
        res = self.post_request("submit-transaction", headers, msg, nodeSecretKey, popHeader, replaceKeyFile, popBody, repBody)
        return res, msg

    def submit_settlement(self, nodeSecretKey, headers, grpHdr, cdtTrfTxInf, popHeader=None, replaceKeyFile=False, popBody=None, repBody=None):
        msg = {
            "version": self.version,
            "msgType": headers["msgTp"],
            "grpHdr": grpHdr,
            "cdtTrfTxInf": cdtTrfTxInf
        }
        self.logger.info("提交结算请求")
        res = self.post_request("submit-settlement", headers, msg, nodeSecretKey, popHeader, replaceKeyFile, popBody, repBody)
        return res, msg

    def proc_confirm(self, nodeSecretKey, headers, grpHdr, b_msg, popHeader=None, replaceKeyFile=False, popBody=None, repBody=None):
        msg = {
            "version": self.version,
            "msgType": "RTPC",
            "grpHdr": grpHdr,
            "orgnlGrpInfAndSts": b_msg["orgnlGrpInfAndSts"],
            "txInfAndSts": b_msg["txInfAndSts"]
        }
        self.logger.info("发送confirm消息")
        res = self.post_request("proc-confirm", headers, msg, nodeSecretKey, popHeader, replaceKeyFile, popBody, repBody)
        return res, msg

    def get_transaction_status(self, nodeSecretKey, headers, msgHdr, txQryDef, popHeader=None, replaceKeyFile=False, popBody=None, repBody=None):
        # msg_id = self.make_msg_id() if msg_id is None else msg_id
        # headers = self.make_header(sender, sendApiKey, "RTSQ", msg_id, "sign123")
        msg = {
            "version": self.version,
            "msgType": "RTSQ",
            "msgHdr": msgHdr,
            "txQryDef": txQryDef
        }
        self.logger.info("查询交易状态")
        res = self.post_request("get-transaction-status", headers, msg, nodeSecretKey, popHeader, replaceKeyFile, popBody, repBody)
        return res, msg

    def get_transaction_flow(self, nodeSecretKey, headers, msgHdr, txQryDef, popHeader=None, replaceKeyFile=False, popBody=None, repBody=None):
        # msg_id = self.make_msg_id() if msg_id is None else msg_id
        # headers = self.make_header(sender, sendApiKey, "RATQ", msg_id, "sign123")
        msg = {
            "version": self.version,
            "msgType": "RATQ",
            "msgHdr": msgHdr,
            "txQryDef": txQryDef
        }
        self.logger.info("查询交易订单流程状态")
        res = self.post_request("get-transaction-flow", headers, msg, nodeSecretKey, popHeader, replaceKeyFile, popBody, repBody)
        return res, msg

    def get_router_list(self, nodeSecretKey, headers, msgHdr, rtgQryDef, popHeader=None, replaceKeyFile=False, popBody=None, repBody=None):
        # msg_id = self.make_msg_id()
        # headers = self.make_header(senderNodeRo, senderApiKey, "RRLQ", msg_id, "sign")
        msg = {
            "version": self.version,
            "msgType": "RRLQ",
            "msgHdr": msgHdr,
            "rtgQryDef": rtgQryDef
        }
        self.logger.info("查询路由，用于查询右侧结算/支付节点")
        res = self.post_request("get-route-list", headers, msg, nodeSecretKey, popHeader, replaceKeyFile, popBody, repBody)
        return res, msg

    def get_exchange_rate(self, nodeSecretKey, headers, msgHdr, sndrCcy, sndrAmt, rcvrCcy, rcvrAmt=None, popHeader=None, replaceKeyFile=False, popBody=None, repBody=None):
        # msg_id = self.make_msg_id()
        # headers = self.make_header(senderNodeRo, nodeApiKey, "RERQ", msg_id, "sign")
        msg = {
            "version": self.version,
            "msgType": "RERQ",
            "msgHdr": msgHdr,
            "ccyQryDef": {
                "ccyCrit": {
                    "sndrCcy": sndrCcy,
                    "sndrAmt": sndrAmt,
                    "rcvrCcy": rcvrCcy,
                    "rcvrAmt": rcvrAmt,
                },
            }
        }
        headers, en_body = self.makeEncryptHeaders(headers, msg, nodeSecretKey, replaceKeyFile=replaceKeyFile, popBody=popBody, repBody=repBody)
        if popHeader:
            headers.pop(popHeader)
        # if popBody:
        #     en_body = json.loads(en_body)
        #     en_body["resource"].pop(popBody)
        #     en_body = json.dumps(en_body)
        # if repBody:
        #     en_body = json.loads(en_body)
        #     en_body["resource"][repBody] = "1234"
        #     en_body = json.dumps(en_body)
        res = sendPostRequest(self.host + "/get-exchange-rate", en_body, headers=headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求headers: {headers}")
        self.logger.debug(f"请求参数: {en_body}")
        self.logger.debug(f"原始参数: {json.dumps(msg)}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json(), msg

    def manual_proc_confirm(self, nodeSecretKey, headers, grpHdr, b_msg, popHeader=None, replaceKeyFile=False, popBody=None, repBody=None):
        msg = {
            "version": self.version,
            "msgType": "RTPC",
            "grpHdr": grpHdr,
            "orgnlGrpInfAndSts": b_msg["orgnlGrpInfAndSts"],
            "txInfAndSts": b_msg["txInfAndSts"]
        }
        self.logger.info("发送confirm消息")
        res = self.post_request("backend/manual-proc-confirm", headers, msg, nodeSecretKey, popHeader, replaceKeyFile, popBody, repBody)
        return res, msg

    def submit_return_transaction(self, nodeSecretKey, headers, grpHdr, cdtTrfTxInf, popHeader=None, replaceKeyFile=False, popBody=None, repBody=None):
        msg = {
            "version": self.version,
            "msgType": "RPRN",
            "grpHdr": grpHdr,
            "txInf": cdtTrfTxInf
        }
        self.logger.info("提交return请求")
        res = self.post_request("submit-return-txn", headers, msg, nodeSecretKey, popHeader, replaceKeyFile, popBody, repBody)
        return res, msg

    def manual_return_transaction(self, nodeSecretKey, headers, grpHdr, cdtTrfTxInf, popHeader=None, replaceKeyFile=False, popBody=None, repBody=None):
        msg = {
            "version": self.version,
            "msgType": "RPRN",
            "grpHdr": grpHdr,
            "txInf": cdtTrfTxInf
        }
        self.logger.warning("RMN提交return请求")
        res = self.post_request("submit-manual-return-txn", headers, msg, nodeSecretKey, popHeader, replaceKeyFile, popBody, repBody)
        return res, msg

    # 功能函数

    def findRouterPathFromDBData_old(self, sender, req_body, rts_client):
        in_currency = req_body["rtgQryDef"]["qryCrit"]["rmtInf"]["sndrCcy"]
        out_currency = req_body["rtgQryDef"]["qryCrit"]["rmtInf"]["rcvrCcy"]
        in_amount = req_body["rtgQryDef"]["qryCrit"]["rmtInf"]["sndrAmt"]
        out_amount = req_body["rtgQryDef"]["qryCrit"]["rmtInf"]["rcvrAmt"]

        node_infos = self.mysql.exec_sql_query("select * from roxe_risn_config.risn_node")
        rts_node_infos = self.mysql.exec_sql_query(f"select * from `{self.rts_db_name}`.rts_node_router")
        node_ros = [i["nodeRoxe"] for i in node_infos]  # 节点的roxeId
        sender_info = node_infos[node_ros.index(sender)]

        if out_amount is None:
            out_amount = ""
        if in_amount is None:
            in_amount = ""
        # 查找左侧路径, 左侧发起消息的必定是一个节点
        res_path = []
        one_router = []
        sn1_node = sender
        path_type = "sn-sn"

        def new_agt(node, currency, fee, fee_key):
            return {"agt": {"id": node, "schmeCd": "ROXE"}, fee_key: {"ccy": currency, "amt": f"{fee:.2f}"}}

        if sender_info["nodeType"] == "PN":
            if sender_info["nodeRelSn"] in node_ros:
                pn1_fee = self.getTransactionFeeInDB(sender_info["nodeRoxe"], in_currency, "in", "PN")
                one_router.append(new_agt(sender_info["nodeRoxe"], in_currency, pn1_fee, "sndFeeAmt"))
                sn1_node = sender_info["nodeRelSn"]
                path_type = "pn-" + path_type
        # 根据节点code，出入金币种 过滤sn1节点的法币路由
        rts_nodes = [i for i in rts_node_infos if
                     i["payNodeCode"] == sn1_node and i["payCurrency"].startswith(in_currency) and i[
                         "outCurrency"].startswith(out_currency) and not i["payCurrency"].endswith("ROXE") and not i[
                         "outCurrency"].endswith("ROXE")]
        node_country = list(set([i["payCurrency"].split(".")[1] for i in rts_nodes]))[0]

        sn1_fee = self.getTransactionFeeInDB(sn1_node, in_currency, "in", "SN", node_country)
        one_router.append(new_agt(sn1_node, in_currency, sn1_fee, "sndFeeAmt"))

        pn2_node, sn2_node, sn2_country, pn2_fee = "", "", "", ""
        # 查找右侧路径
        try:
            agent_info = req_body["rtgQryDef"]["qryCrit"]["cdtrAgt"]["finInstnId"]
            if "othr" in agent_info:
                rec_info = node_infos[node_ros.index(agent_info["othr"]["id"])]
                if rec_info["nodeType"] == "PN":
                    pn2_node = agent_info["othr"]["id"]
                    sn2_node = rec_info["nodeRelSn"]
                    sn2_country = rec_info["nodeCountry"]
                    pn2_fee = self.getTransactionFeeInDB(rec_info["nodeRoxe"], out_currency, "out", "PN")
                    path_type += "-pn"
                else:
                    sn2_node = agent_info["othr"]["id"]
            else:
                if "bicFI" in agent_info:
                    sn2_country = agent_info["bicFI"][4:6]
                elif "clrSysMmbId" in agent_info:
                    sn2_country = agent_info["clrSysMmbId"]["clrSysCd"][0:2]
        except TypeError:
            sn2_country = req_body["rtgQryDef"]["qryCrit"]["cdtrAcct"]["iban"][0:2]
        # 根据SN2节点筛选路由
        if sn2_node: rts_nodes = [i for i in rts_nodes if i["outNodeCode"] == sn2_node]
        # 根据出金国家筛选路由
        if sn2_country: rts_nodes = [i for i in rts_nodes if i["outCurrency"].endswith("." + sn2_country)]

        # 路由策略参数
        strategy = ""
        if req_body["rtgQryDef"]["qryTp"] == "COST":
            strategy = "LOWEST_FEE"

        router_info, _ = rts_client.getRouterList("", in_currency, sn2_country, out_currency, in_amount, out_amount,
                                                  sn1_node, sn2_node, strategy)
        assert len(rts_nodes) >= len(router_info["data"]), f"数据库和接口查询出来的条数不一致: {rts_nodes}"
        for router in router_info["data"]:
            tmp_router = copy.deepcopy(one_router)
            if router["serviceFee"]:
                tmp_router.append(
                    new_agt("risn2roxe51", router["serviceFeeCurrency"], router["serviceFee"], "svcFeeAmt"))
            ex_node = sn2_node if sn2_node else router["receiveNodeCode"]
            tmp_router.append(new_agt(ex_node, router["deliveryFeeCurrency"], router["deliveryFee"], "dlvFeeAmt"))
            if pn2_node:
                tmp_router.append(new_agt(pn2_node, out_currency, pn2_fee, "dlvFeeAmt"))
            res_path.append(tmp_router)
        self.logger.info(f"路由路径: {json.dumps(res_path)}")
        return res_path, path_type

    def translateRouterListRequestBodyToRTS(self, req_body, isRcctParams=False):
        base_msg = req_body if isRcctParams else req_body["rtgQryDef"]["qryCrit"]
        out_node, out_country = "", ""
        if "cdtrAgt" in base_msg and base_msg["cdtrAgt"]:
            agent_info = base_msg["cdtrAgt"].get("finInstnId")
            if "othr" in agent_info:
                out_node = agent_info["othr"]["id"]
            elif "bicFI" in agent_info:
                out_country = agent_info["bicFI"][4:6]
            elif "clrSysMmbId" in agent_info:
                out_country = agent_info["clrSysMmbId"]["clrSysCd"][0:2]
        else:
            out_country = base_msg["cdtrAcct"]["iban"][0:2]
        self.logger.warning(f"根据参数得到: {out_node}, {out_country}")
        return out_node, out_country

    def findRouterPathFromDBData(self, sender, req_body, rts_client):
        in_currency = req_body["rtgQryDef"]["qryCrit"]["rmtInf"]["sndrCcy"]
        out_currency = req_body["rtgQryDef"]["qryCrit"]["rmtInf"]["rcvrCcy"]
        in_amount = req_body["rtgQryDef"]["qryCrit"]["rmtInf"]["sndrAmt"]
        out_amount = req_body["rtgQryDef"]["qryCrit"]["rmtInf"]["rcvrAmt"]
        b_type = req_body["rtgQryDef"]["pmtTpInf"]["ctgyPurp"]["cd"] if req_body["rtgQryDef"].get("pmtTpInf") else "C2C"

        node_infos = self.mysql.exec_sql_query("select * from roxe_risn_config.risn_node_info")
        rts_node_infos = self.mysql.exec_sql_query(
            f"select * from `{self.rts_db_name}`.rts_node_router where pay_currency='{in_currency}' and out_currency='{out_currency}'")
        node_ros = [i["nodeCode"] for i in node_infos]  # 节点的roxeId
        sender_info = node_infos[node_ros.index(sender)]

        if out_amount is None:
            out_amount = ""
        if in_amount is None:
            in_amount = ""
        # 查找左侧路径, 左侧发起消息的必定是一个节点
        res_path = []
        one_router = []
        path_type = "sn-sn"

        def new_agt(node, currency, fee, fee_key):
            return {"agt": {"id": node, "schmeCd": "ROXE"}, fee_key: {"ccy": currency, "amt": f"{fee:.2f}"}}

        if sender_info["nodeType"] == "PN":

            pn1_fee = self.getNodeFeeInDB(sender_info["nodeCode"], in_currency, float(in_amount), b_type)
            one_router.append(new_agt(sender_info["nodeCode"], in_currency, pn1_fee["in"], "sndFeeAmt"))
            path_type = "pn-" + path_type
        # 根据节点code，出入金币种 过滤sn1节点的法币路由
        rts_nodes = [i for i in rts_node_infos if json.loads(i["routerConfig"])["left"][0]["nodeCode"] == sender]
        node_country = rts_nodes[0]["payCountry"]

        pn2_node, sn2_node, out_country, pn2_fee = "", "", "", ""
        # 查找右侧路径
        receive_node, out_country = self.translateRouterListRequestBodyToRTS(req_body)
        if receive_node:
            rec_info = node_infos[node_ros.index(receive_node)]
            if rec_info["nodeType"] == "PN":
                pn2_node = receive_node
                out_country = rec_info["nodeCountry"]
                path_type += "-pn"
            else:
                sn2_node = receive_node
            # rts_nodes = [i for i in rts_nodes if json.loads(i["routerConfig"])["right"][-1]["nodeCode"] == receive_node]
        # 根据出金国家筛选路由
        # if out_country: rts_nodes = [i for i in rts_nodes if i["outCountry"] == out_country]
        # 路由策略参数
        strategy = ""
        if req_body["rtgQryDef"]["qryTp"] == "COST":
            strategy = "LOWEST_FEE"

        router_info, _ = rts_client.getRouterList("", in_currency, out_country, out_currency, in_amount, out_amount,
                                                  sender, receive_node, strategy, businessType=b_type)
        # assert len(rts_nodes) >= len(router_info["data"]), f"数据库和接口查询出来的条数不一致: {rts_nodes}"
        for router in router_info["data"]["roxeRouters"]:
            # 未指定PN2节点时，查询出的路由的最后1个节点为SN, 包含PN2的路由需要过滤
            tmp_router = copy.deepcopy(one_router)
            reset_sn2 = False
            sn1_node = router["roxeNodes"][1]["nodeCode"] if sender_info["nodeType"] == "PN" else sender
            sn1_amt = float(in_amount) - pn1_fee["in"] if sender_info["nodeType"] == "PN" else float(in_amount)
            node_fee = self.getNodeFeeInDB(sn1_node, in_currency, sn1_amt, b_type)
            self.logger.warning(f"SN1节点费用: {node_fee}")
            # sn1_fee = self.getTransactionFeeInDB

            sn1_fee = node_fee["in"]
            tmp_router.append(new_agt(sn1_node, in_currency, sn1_fee, "sndFeeAmt"))
            service_fee = pn1_fee["service_fee"] if sender_info["nodeType"] == "PN" else node_fee["service_fee"]
            if service_fee > 0:
                tmp_router.append(new_agt("risn2roxe51", in_currency, service_fee, "svcFeeAmt"))
            if sn2_node == "":
                reset_sn2 = True
                if router["roxeNodes"][-1]["nodeType"] == "SN":
                    sn2_node = router["roxeNodes"][-1]["nodeCode"]  # 如果最后一个节点为SN节点，即为sn2节点
                else:
                    sn2_node = router["roxeNodes"][-2]["nodeCode"]  # 最后一个节点为PN节点，即为pn2节点
            r_node = [i for i in router["roxeNodes"] if i["nodeCode"] == sn2_node]
            sn2_node_info = r_node[0] if sn1_node != sn2_node else r_node[1]
            sn2_amt = sn1_amt - sn1_fee - service_fee
            node_fee2 = self.getNodeFeeInDB(sn2_node, out_currency, sn2_amt, b_type)
            self.logger.warning(f"SN2节点费用: {node_fee2}")
            # if sn2_node_info["deliveryFee"] > 0:
            if node_fee2["out"] > 0:
                if in_currency == out_currency:
                    sn2_agt = new_agt(sn2_node, sn2_node_info["deliveryFeeCurrency"], node_fee2["out"], "dlvFeeAmt")
                else:
                    sn2_agt = new_agt(sn2_node, sn2_node_info["deliveryFeeCurrency"], sn2_node_info["deliveryFee"], "dlvFeeAmt")
                tmp_router.append(sn2_agt)
            if pn2_node:
                if in_currency == out_currency:
                    pn2_amt = sn2_amt - node_fee2["out"]
                    pn2_fee = self.getNodeFeeInDB(pn2_node, out_currency, pn2_amt, b_type)["out"]
                else:
                    pn2_node_info = [i for i in router["roxeNodes"] if i["nodeCode"] == pn2_node][-1]
                    pn2_fee = pn2_node_info["deliveryFee"]
                tmp_router.append(new_agt(pn2_node, out_currency, pn2_fee, "dlvFeeAmt"))
            res_path.append(tmp_router)
            if reset_sn2:
                sn2_node = ""
        self.logger.info(f"路由路径: {json.dumps(res_path)}")
        return res_path, path_type

    def waitNodeReceiveMessage(self, node, old_msg_id, msgStatus=None, rcct_msg_id=None, api_key=None, sec_key=None,
                               flow_state=None, rcct_msg_sender=None):
        """
        等待节点接收消息, 交易请求或者confirm消息
        """
        time_out = 800 if Global.getValue(settings.is_multiprocess) else 600
        if self.check_db:
            node_url = self.mysql.exec_sql_query("select node_callback_url from roxe_risn_config.risn_node_key where node_code='{}'".format(node))
            node_url = node_url[0]["nodeCallbackUrl"]
            if "rmn/receiveNotify" in node_url:
                # 由测试开发维护的mock系统，用于测试接收回调内容
                # sandbox环境，mock回调通知存到数据库的为密文，使用rmn发出去的消息作为筛选条件
                find_sql = f"select msg_content as confirmMsg from roxe_rmn.rmn_notify_info where msg_content like '%{old_msg_id}%' and notify_status='SUCCESS' order by create_time desc"
                if msgStatus:
                    find_sql = f"select msg_content as confirmMsg from roxe_rmn.rmn_notify_info where (msg_content like '%{old_msg_id}%{msgStatus}%' or msg_content like '%{msgStatus}%{old_msg_id}%') and notify_status='SUCCESS' order by create_time desc"
                # if "sandbox" in self.host:
                # else:
                #     find_sql = f"select response as confirmMsg from mock_notify.res_info where response like '%{old_msg_id}%' order by create_at desc"
                #     if msgStatus:
                #         find_sql = f"select response as confirmMsg from mock_notify.res_info where response like '%{old_msg_id}%{msgStatus}%' order by create_at desc"
                self.logger.debug("节点消息数据库: {}".format(find_sql))
            else:
                return
            db_info = ApiUtils.waitCondition(self.mysql.exec_sql_query, (find_sql, ), lambda x: len(x) > 0, time_out, 10)
            call_back = json.loads(db_info[0]["confirmMsg"]) if db_info else None
            parse_msg = json.dumps(call_back) if call_back else None
            self.logger.info(f"{node} 节点收到消息: {parse_msg}")
        else:
            def checkFlowState(func_res, f_state):
                flag = False
                flow_res = func_res["data"]["rptOrErr"]
                if "splmtryData" in flow_res:
                    find_flow = [f_info for f_info in flow_res["splmtryData"] if f_info["sts"] == f_state]
                    if find_flow:
                        flag = True
                return flag
            q_instgAgt = rcct_msg_sender if rcct_msg_sender else node
            tx_flow = ApiUtils.waitCondition(
                self.step_queryTransactionFlow, (node, api_key, sec_key, rcct_msg_id, q_instgAgt,),
                functools.partial(checkFlowState, f_state=flow_state), time_out, 20
            )
            flow_info = [flow_info for flow_info in tx_flow["data"]["rptOrErr"]["splmtryData"] if flow_info["sts"] == flow_state]
            call_back = flow_info[0] if flow_info else None
        return call_back

    def waitTransactionFlow(self, to_node, rcct_node=None, rcct_msg_id=None, api_key=None, sec_key=None, flow_state=None):
        flow_msg = self.waitNodeReceiveMessage(rcct_node, "", None, rcct_msg_id, api_key, sec_key, flow_state)
        q_info, q_msg = self.step_queryTransactionState(to_node, api_key, sec_key, flow_msg["msgId"], "risn2roxe51")
        tx_msg = copy.deepcopy(flow_msg)
        # 重新组装参数，后续请求RTPC、
        tx_msg["cdtTrfTxInf"] = {
            "pmtId": copy.deepcopy(q_info["data"]["rptOrErr"]["pmt"]["pmtId"]),
            "dbtrAgt": self.make_roxe_agent(rcct_node, "SN")
        }
        tx_msg["msgType"] = "RCCT"
        tx_msg["grpHdr"] = {"instgAgt": "risn2roxe51"}
        self.logger.info(f"节点收到消息: {json.dumps(tx_msg)}")
        return tx_msg

    def waitReceiveTransactionMessage(self, rmn_tx_id, to_node, pop_msg_id=None, rcct_node=None, rcct_msg_id=None, api_key=None, sec_key=None, flow_state=None, is_return=False):
        if self.check_db:
            sql = f"select * from roxe_rmn.rmn_txn_message where node_code='{to_node}' and direction='OUTBOUND' and rmn_txn_id='{rmn_tx_id}'"
            if pop_msg_id:
                sql += f" and msg_id<>'{pop_msg_id}'"
            if is_return:
                sql = sql.replace("rmn_txn_message", "rmn_return_message")
            self.logger.debug(f"查找rmn tx id: {sql}")
            time_out = 600 if Global.getValue(settings.is_multiprocess) else 200
            db_info = ApiUtils.waitCondition(self.mysql.exec_sql_query, (sql,), lambda x: len(x) > 0, time_out, 10)
            self.logger.debug(f"RMN发出去的RCCT信息: {db_info}")
            tx_msg = self.waitNodeReceiveMessage(to_node, db_info[0]["msgId"])
        else:
            flow_msg = self.waitNodeReceiveMessage(rcct_node, "", None, rcct_msg_id, api_key, sec_key, flow_state)
            q_headers = self.make_header(to_node, api_key, "RTSQ")
            q_msg_header = self.make_msg_header(to_node, q_headers["msgId"])
            q_txQryDef = self.make_RTSQ_information(flow_msg["msgId"], "risn2roxe51")
            q_info, q_msg = self.get_transaction_status(sec_key, q_headers, q_msg_header, q_txQryDef)
            tx_msg = copy.deepcopy(flow_msg)
            # 重新组装参数，后续请求RTPC、
            tx_msg["cdtTrfTxInf"] = {
                "pmtId": copy.deepcopy(q_info["data"]["rptOrErr"]["pmt"]["pmtId"]),
                "dbtrAgt": self.make_roxe_agent(rcct_node, "SN")
            }
            tx_msg["msgType"] = "RCCT"
            tx_msg["grpHdr"] = {"instgAgt": "risn2roxe51", "msgId": tx_msg["msgId"]}
            self.logger.info(f"节点收到消息: {json.dumps(tx_msg)}")
        return tx_msg

    def step_sendRCCT(self, sn1, sn2, api_key, sec_key, inCurrency, outCurrency, amount, fee, is_settled=True):
        debtor_agent = self.make_roxe_agent(sn1, "SN")
        creditor_agent = self.make_roxe_agent(sn2, "SN")
        debtor = {}
        creditor = {}
        cdtTrfTxInf = self.make_RCCT_information(inCurrency, outCurrency, debtor, debtor_agent, creditor, creditor_agent, fee, sn1, inAmount=amount)

        msg_id = self.make_msg_id()
        tx_headers = self.make_header(sn1, api_key, "RCCT", msg_id)
        tx_group_header = self.make_group_header(sn1, "risn2roxe51", msg_id)
        tx_info, tx_msg = self.submit_transaction(sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.checkCodeAndMessage(tx_info)

        rmn_tx_id = tx_info["data"]["txId"]
        time.sleep(10)

        if is_settled:
            st_headers = self.make_header(sn1, api_key, "RCSR")
            st_grpHder = self.make_group_header(sn1, "risn2roxe51", st_headers["msgId"])
            st_cdtInf = self.make_RCSR_information(tx_msg, "CRDT", sn1)
            st_info, st_msg = self.submit_settlement(sec_key, st_headers, st_grpHder, st_cdtInf)
            self.checkCodeAndMessage(st_info)

        return rmn_tx_id

    def step_sendRCSR(self, snNode, apiKey, secKey, rcctMsg, rmn_tx_id, stType, caseObj, fee=None, nodeLoc="SN1"):
        log_msg = f"{nodeLoc}: {snNode}节点提交结算请求并等待接收confirm消息"
        self.logger.warning(log_msg)
        # 发送结算请求
        st_headers = self.make_header(snNode, apiKey, "RCSR")
        st_grpHder = self.make_group_header(snNode, "risn2roxe51", st_headers["msgId"])
        st_cdtInf = self.make_RCSR_information(rcctMsg, stType, snNode)
        if st_cdtInf["cdtrAcct"].get("issr"):
            st_cdtInf["cdtrAcct"].pop("issr")
            st_cdtInf["cdtrAcct"].pop("schmeNm")
            if st_cdtInf["cdtrAcct"].get("tp"): st_cdtInf["cdtrAcct"].pop("tp")
        if fee:
            # 从PN发起的交易, SN提交结算请求时需扣除SN的费用
            tmp_amt = float(st_cdtInf["intrBkSttlmAmt"]["amt"]) - float(fee)
            st_cdtInf["intrBkSttlmAmt"]["amt"] = str(ApiUtils.parseNumberDecimal(tmp_amt, 2, True))
        self.logger.warning(f"结算金额：{st_cdtInf['intrBkSttlmAmt']}")
        st_info, st_msg = self.submit_settlement(secKey, st_headers, st_grpHder, st_cdtInf)
        self.checkCodeAndMessage(st_info)
        assert st_info["data"]["stsId"] == "RCVD"
        assert st_info["data"]["txId"] == rmn_tx_id

        # 等待结算完成
        endToEndId = st_cdtInf["pmtId"]["endToEndId"]
        flow_state = "DEBIT_STTL_CONF_SENT" if stType == "CRDT" else "CREDIT_STTL_CONF_SENT"
        st_confirm = self.waitNodeReceiveMessage(snNode, st_headers["msgId"], None, st_headers["msgId"], apiKey, secKey, flow_state)
        if hasattr(caseObj, "checkConfirmMessage"):
            caseObj.checkConfirmMessage(st_confirm, "STLD", st_headers["msgId"], "RCSR", snNode, endToEndId, endToEndId,
                                        "STTL")
        if st_cdtInf["rmtInf"]["orgnlMsgTp"] == "RCCT":
            self.checkSNSMsgOrPNSMsg(rmn_tx_id, "TO_SNS", "RCSR", st_msg)

        return st_msg

    def step_sendRTPC(self, node, apiKey, secKey, rcctMsg, **kwargs):
        pc_msg_id = self.make_msg_id()
        pc_headers = self.make_header(node, apiKey, "RTPC", pc_msg_id)
        pc_group_header = self.make_group_header(node, "risn2roxe51", pc_msg_id, hasSttlmInf=False)
        p_msg = self.make_RTPC_information(rcctMsg, "ACPT")
        if kwargs.get("stsId"):
            p_msg["txInfAndSts"]["stsId"] = kwargs.get("stsId")
        if kwargs.get("stsRsnInf"):
            p_msg["txInfAndSts"]["stsRsnInf"] = kwargs.get("stsRsnInf")
        pc_info, pc_msg = self.proc_confirm(secKey, pc_headers, pc_group_header, p_msg)
        if kwargs.get("code"):
            self.checkCodeAndMessage(pc_info, kwargs.get("code"), kwargs.get("message"))
        else:
            self.checkCodeAndMessage(pc_info)
        return pc_msg

    def step_sendRTPC_manual(self, node, apiKey, secKey, rcctMsg, **kwargs):
        pc_msg_id = self.make_msg_id()
        pc_headers = self.make_header("risn2roxe51", apiKey, "RTPC", pc_msg_id)
        pc_group_header = self.make_group_header("risn2roxe51", node, pc_msg_id, hasSttlmInf=False)
        p_msg = self.make_RTPC_information(rcctMsg, "ACPT")
        if kwargs.get("stsId"):
            p_msg["txInfAndSts"]["stsId"] = kwargs.get("stsId")
        if kwargs.get("stsRsnInf"):
            p_msg["txInfAndSts"]["stsRsnInf"] = kwargs.get("stsRsnInf")
        p_msg["txInfAndSts"]["acctSvcrRef"] = "TXNN"
        pc_info, pc_msg = self.manual_proc_confirm(secKey, pc_headers, pc_group_header, p_msg)
        if kwargs.get("code"):
            self.checkCodeAndMessage(pc_info, kwargs.get("code"), kwargs.get("message"))
        else:
            self.checkCodeAndMessage(pc_info)

    def step_queryTransactionState(self, node, apiKey, secKey, msg_id, instgPty, **kwargs):
        ts_headers = self.make_header(node, apiKey, "RTSQ")
        msg_header = self.make_msg_header(node, ts_headers["msgId"])
        txQryDef = self.make_RTSQ_information(msg_id, instgPty, **kwargs)
        q_info, q_msg = self.get_transaction_status(secKey, ts_headers, msg_header, txQryDef)
        return q_info

    def step_queryTransactionFlow(self, node, apiKey, secKey, msg_id, instgPty, returnReqMsg=False, **kwargs):
        ts_headers = self.make_header(node, apiKey, "RATQ")
        msg_header = self.make_msg_header(node, ts_headers["msgId"])
        txQryDef = self.make_RTSQ_information(msg_id, instgPty, ntryTp="ADT", **kwargs)
        q_info, q_msg = self.get_transaction_flow(secKey, ts_headers, msg_header, txQryDef)
        if returnReqMsg:
            return q_info, q_msg
        return q_info

    def step_queryRouter(self, node, sendCurrency, receiveCurrency, sn1=None, amount=None, creditor_agent=None, cdtrAcct=None, qryTp="COST", tp=None, cd="C2C", returnMsg=False):
        # 查询费用最低路由
        ts_headers = self.make_header(node, self.api_key, "RRLQ")
        msg_header = self.make_msg_header(node, ts_headers["msgId"])
        amount = amount if amount else ApiUtils.randAmount(100, 2, 30)
        sn1 = sn1 if sn1 else node
        msg = self.make_RRLQ_information(sendCurrency, receiveCurrency, amount, cdtrAgt=creditor_agent, cdtrAcct=cdtrAcct, qryTp=qryTp, cd=cd)
        if tp: msg["pmtTpInf"] = {"lclInstrm": {"cd": tp}}
        router_list, req_msg = self.get_router_list(self.sec_key, ts_headers, msg_header, msg)

        sn2 = router_list["data"]["rptOrErr"][0]["trnRtgInf"]["cdtrAgt"]["finInstnId"]["othr"]["id"]
        node_fees = router_list["data"]["rptOrErr"][0]["chrgsInf"]
        try:
            if router_list["data"]["rptOrErr"][0]["trnRtgInf"]["cdtrAgt"]["finInstnId"]["othr"]["issr"] == "PN":
                pn2_node = router_list["data"]["rptOrErr"][0]["trnRtgInf"]["cdtrAgt"]["finInstnId"]["othr"]["id"]
                sn2 = router_list["data"]["rptOrErr"][0]["trnRtgInf"]["cdtrIntrmyAgt"]["finInstnId"]["othr"]["id"]
            else:
                pn2_node = ""

            if router_list["data"]["rptOrErr"][0]["trnRtgInf"]["dbtrAgt"]["finInstnId"]["othr"]["issr"] == "PN":
                pn1_node = router_list["data"]["rptOrErr"][0]["trnRtgInf"]["dbtrAgt"]["finInstnId"]["othr"]["id"]
                sn1 = router_list["data"]["rptOrErr"][0]["trnRtgInf"]["dbtrIntrmyAgt"]["finInstnId"]["othr"]["id"]
            else:
                pn1_node = ""
        except IndexError:
            pn2_node = ""
            pn1_node = ""

        def find_sn_fee(chrgsInf, sn_node, pn_node, key="sndFeeAmt"):
            n_fee = [i[key]["amt"] for i in chrgsInf if key in i and sn_node == i["agt"]["id"] and sn_node != pn_node]
            n_fee = float(n_fee[0]) if n_fee else 0
            return n_fee

        sn1_fee = find_sn_fee(node_fees, sn1, pn1_node, "sndFeeAmt")
        sn2_fee = find_sn_fee(node_fees, sn2, pn2_node, "dlvFeeAmt")
        self.logger.warning(f"根据路由得到sn1费用: {sn1_fee}, sn2节点为: {sn2}, sn2费用: {sn2_fee}")
        if pn1_node:
            pn1_fee = find_sn_fee(node_fees, pn1_node, sn1, "sndFeeAmt")
            self.logger.warning(f"pn1费用: {pn1_fee}")
        if pn2_node:
            pn2_fee = find_sn_fee(node_fees, pn2_node, sn2, "dlvFeeAmt")
            self.logger.warning(f"pn2费用: {pn2_fee}")
        if returnMsg:
            new_msg = {}
            for field_info in router_list["data"]["rptOrErr"][0]["trnRtgInf"]["msgRqdFld"]["msgStnrdFld"]:
                if field_info["fldTp"] == "list":
                    f_value = random.choice(field_info["fldOpts"])
                    tmp_msg = ApiUtils.generateDict(field_info["fldNm"], f_value)
                    new_msg = ApiUtils.deepUpdateDict(new_msg, tmp_msg)
            if "msgNstnrdFld" in router_list["data"]["rptOrErr"][0]["trnRtgInf"]["msgRqdFld"]:
                add_msg = {}
                for f_info in router_list["data"]["rptOrErr"][0]["trnRtgInf"]["msgRqdFld"]["msgNstnrdFld"]:
                    if f_info["fldTp"] == "list":
                        f_value = random.choice(f_info["fldOpts"])
                        tmp_msg = ApiUtils.generateDict("cdtTrfTxInf.splmtryData.addenda." + f_info["fldNm"], f_value)
                        add_msg = ApiUtils.deepUpdateDict(add_msg, tmp_msg)
                new_msg = ApiUtils.deepUpdateDict(new_msg, add_msg)
            self.logger.info(f"根据路由查询出的字段生成的msg: {json.dumps(new_msg)}")
            return sn1_fee, sn2_fee, sn2, new_msg["cdtTrfTxInf"]
        else:
            return sn1_fee, sn2_fee, sn2

    def getRmnTxIdFromDB(self, q_msg):
        if self.check_db:
            msg_id = q_msg["txQryDef"]["pmtSch"]["msgId"]
            instgPty = q_msg["txQryDef"]["ptySch"]["instgPty"]
            sql_rcct = f"select * from roxe_rmn.rmn_txn_message where msg_id='{msg_id}'"
            if instgPty != "risn2roxe51":
                sql_rcct += f" and node_code='{instgPty}'"
            res_rcct = self.mysql.exec_sql_query(sql_rcct)
            if res_rcct:
                return res_rcct[0]["rmnTxnId"]
            sql_rcsr = f"select * from roxe_rmn.rmn_sttl_message where msg_id='{msg_id}' and node_code='{instgPty}'"
            res_rcsr = self.mysql.exec_sql_query(sql_rcsr)
            if res_rcsr:
                return res_rcsr[0]["rmnTxnId"]
            sql_rtpc = f"select * from roxe_rmn.rmn_confirm_message where msg_id='{msg_id}' and node_code='{instgPty}'"
            res_rtpc = self.mysql.exec_sql_query(sql_rtpc)
            if res_rtpc:
                return res_rtpc[0]["rmnTxnId"]
            sql_rprn = f"select * from roxe_rmn.rmn_return_message where msg_id='{msg_id}'"
            self.logger.debug(f"sql: {sql_rprn}")
            res_return = self.mysql.exec_sql_query(sql_rprn)
            if res_return:
                return res_return[0]["rmnTxnId"]

    def clearOrdersInDB(self):
        if self.check_db:
            rcct_sql = "select * from roxe_rmn.rmn_transaction where txn_state not in ('TRANSACTION_FINISH', 'TRANSACTION_REJECTED', 'RETURNED') and unix_timestamp(now()) - unix_timestamp(update_time) < 3600 * 10;"
            rmn_res = self.mysql.exec_sql_query(rcct_sql)
            # rts_orders = (i["rtsTxnId"] for i in rmn_res)
            # self.logger.info("准备清除rts订单: {}".format(rts_orders))
            for i in rmn_res:
                self.logger.info("准备清除rts订单: {}".format(i["rtsTxnId"]))
                self.mysql.exec_sql_query("delete from `sn-rmn-fape1meh4bsz-rmn`.sn_order where client_id like '%{}%'".format(i["rtsTxnId"]))
                self.mysql.exec_sql_query("delete from `{}`.rts_order where order_id='{}'".format(self.rts_db_name, i["rtsTxnId"]))
                self.mysql.exec_sql_query("delete from `{}`.rts_order_log where order_id='{}'".format(self.rts_db_name, i["rtsTxnId"]))
                self.mysql.exec_sql_query("delete from `{}`.rts_notify where order_id='{}'".format(self.rts_db_name, i["rtsTxnId"]))
                self.mysql.exec_sql_query("delete from roxe_rmn.rmn_transaction where rts_txn_id='{}'".format(i["rtsTxnId"]))

    def waiteNotifyRetryFail(self, rmn_tx_id, node, notify_count=None):
        sql = f"select * from roxe_rmn.rmn_notify_info where rmn_txn_id='{rmn_tx_id}' and msg_type='RCCT' and node_code='{node}' order by create_time desc"
        # 未收到正确响应, 回调通知状态为FAILED，5分钟后进入重试，重试5次，每次2分钟
        if notify_count:
            time_out = 330 if notify_count == 2 else 130
            notify_db = ApiUtils.waitCondition(
                self.mysql.exec_sql_query, (sql,),
                lambda x: len(x) > 0 and x[0]["notifyStatus"] == "FAILED" and x[0]["notifyCount"] == notify_count,
                time_out, 10
            )
        else:
            notify_db = ApiUtils.waitCondition(
                self.mysql.exec_sql_query, (sql,), lambda x: len(x) > 0 and x[0]["notifyStatus"] == "THRESHOLD_EXCEED",
                1000, 10
            )
        self.logger.info("rcct重试了{}次，重试原因: {}".format(notify_db[0]["notifyCount"], notify_db[0]["remark"]))
        return notify_db

    def getRpcFeeInDB(self, channel_name, currency, country=None):
        # risn_sql = f"select b.* from `roxe_risn_config`.risn_fee_currency a left join " \
        #            f"`roxe_risn_config`.risn_fee_rate b on a.id=b.currency_id where a.node_code='{channel_name}' and a.fee_currrency='{currency}';"
        #
        rpc_sql = f"select * from `roxe_rpc`.rpc_corridor_info where channel_name='{channel_name}' and currency='{currency}'"
        if country:
            rpc_sql += f" and country='{country}'"
        rpc_info = self.mysql.exec_sql_query(rpc_sql)
        node_fee = {"in": None, "out": None}
        for i in rpc_info:
            if i["corridorType"] == 1:
                node_fee["in"] = i
            if i["corridorType"] == 0:
                node_fee["out"] = i
        return node_fee

    def getSettlementNodeFeeInDB(self, node, currency, country):
        if self.rts_db_name == "roxe-rts":
            rts_sql = f"select * from `{self.rts_db_name}`.rts_node_router where ( pay_currency like '{currency}.%' and pay_node_code='{node}') or ( out_currency like '{currency}.%' and out_node_code='{node}')"
            rts_router = self.mysql.exec_sql_query(rts_sql)
            self.logger.debug(f"{node}, {currency}, {country}")
            if rts_router[0]["payNodeCode"] == node:
                node_key = "sn1"
                country = country if country else rts_router[0]["payCurrency"].split(".")[-1]
            else:
                node_key = "sn2"
                country = country if country else rts_router[0]["outCurrency"].split(".")[-1]
            router_config = json.loads(rts_router[0]["routerConfig"].replace("\n", ""))
            node_db_name = router_config[node_key]["nodeUrl"].split("/")[-1].rstrip("1")
            channel_name = node_db_name.split("-")[2].upper()
        else:
            rts_sql = f"select * from `{self.rts_db_name}`.rts_node_info where node_code='{node}'"
            rts_router = self.mysql.exec_sql_query(rts_sql)
            self.logger.debug(f"{node}, {currency}, {country}")
            router_config = json.loads(rts_router[0]["nodeInfo"].replace("\n", ""))
            # node_db_name = router_config["host"].split("/")[-1].rstrip("1")
            channel_name = node
        node_fee = self.getRpcFeeInDB(channel_name, currency, country)
        return node_fee

    def getNodeFeeInDB(self, node, currency, amt, b_type="C2C", is_return=False):
        fee_sql = f"select b.* from `roxe_risn_config`.risn_fee_currency a left join " \
                   f"`roxe_risn_config`.risn_fee_rate b on a.id=b.currency_id where a.node_code='{node}' " \
                   f"and a.target_currency='{currency}' and b.business_type='{b_type}'"
        node_fee_info = self.mysql.exec_sql_query(fee_sql)

        def calculate_fee(fee_type, node_fees, base_amt=0):
            fee_keys = [i["feeType"] for i in node_fees]
            if fee_type in fee_keys:
                fee_info = [i for i in node_fees if i["feeType"] == fee_type][0]
                if fee_info["feePolicy"] == "FIXED":
                    return float(fee_info["feeRate"])

                if fee_info["feePolicy"] == "PERCENTAGE":
                    per_fee = base_amt * float(fee_info["feeRate"])
                    min_fee = 0
                    if fee_info["minRate"]: min_fee = float(fee_info["minRate"])
                    self.logger.info(f"计算出的百分比方式费用为: {per_fee}, 最小费用: {min_fee}")
                    # ApiUtils.parseNumberDecimal()
                    return round(max(min_fee, per_fee), 2)
            else:
                return 0

        node_fee = {}
        if is_return:
            node_fee["in"] = calculate_fee("RTN_SEND_FEE", node_fee_info, amt)
            node_fee["out"] = calculate_fee("RTN_DELIVERY_FEE", node_fee_info, amt)
            node_fee["service_fee"] = calculate_fee("RTN_SERVICE_FEE", node_fee_info, amt)
        else:
            node_fee["in"] = calculate_fee("SEND_FEE", node_fee_info, amt)
            node_fee["out"] = calculate_fee("DELIVERY_FEE", node_fee_info, amt)
            node_fee["service_fee"] = calculate_fee("SERVICE_FEE", node_fee_info, amt)
        return node_fee

    def getTransactionFeeInDB(self, node, currency, feeType, nodeType="SN", country=None):
        if not self.check_db:
            return
        tx_fee = 0
        if nodeType == "SN":
            rts_sql = f"select * from `{self.rts_db_name}`.rts_node_info where node_code='{node}'"
            rts_router = self.mysql.exec_sql_query(rts_sql)
            self.logger.debug(f"{node}, {currency}, {country}")
            router_config = json.loads(rts_router[0]["nodeInfo"].replace("\n", ""))
            # node_db_name = router_config["host"].split("/")[-1].rstrip("1")
            channel_name = node
        # else:
        node_fee = self.getRpcFeeInDB(node, currency, country)
        if feeType == "in" and node_fee[feeType]:
            tx_fee = float(node_fee[feeType]["inFeeAmount"])
        elif feeType == "out" and node_fee[feeType]:
            tx_fee = float(node_fee[feeType][f"{feeType}BankFee"])
        self.logger.info(f"{nodeType}: {node} {currency} 交易费用: {tx_fee}")
        return tx_fee

    def getReturnFeeInDB(self, node, currency, feeType, nodeType="SN", country=None):
        if not self.check_db:
            return
        node_fee = self.getNodeFeeInDB(node, currency, country)
        return_fee = 0
        if node_fee[feeType] and node_fee[feeType][f"{feeType}ReturnFee"]:
            return_fee = float(node_fee[feeType][f"{feeType}ReturnFee"])
        # if nodeType == "SN":
        #     node_fee = self.getSettlementNodeFeeInDB(node, currency, country)
        #     if node_fee[feeType] and node_fee[feeType][f"{feeType}ReturnFee"]:
        #         return_fee = float(node_fee[feeType][f"{feeType}ReturnFee"])
        # else:
        #     node_fee = self.getPaymentNodeFeeInDB(node, currency)
        #     if node_fee[feeType] and node_fee[feeType]["rtrFeeConfig"]:
        #         return_fee = float(json.loads(node_fee[feeType]["rtrFeeConfig"])["fixFee"])
        self.logger.info(f"{nodeType}: {node} {currency} Return费用: {return_fee}")
        return return_fee

    def step_nodeSendRPRN(self, sendNode, receiveNode, return_msg, code="0", msg="Success"):
        re_headers = self.make_header(sendNode, self.api_key, "RPRN")
        msg_header = self.make_group_header(sendNode, receiveNode, re_headers["msgId"])
        tx_info, tx_msg = self.submit_return_transaction(self.sec_key, re_headers, msg_header, return_msg)
        self.checkCodeAndMessage(tx_info, code, msg)
        if code == "0":
            assert tx_info["data"]["stsId"] == "RCVD", "提交return后stsId不正确"
            self.checkOldTransactionInDB(tx_info["data"]["txId"])
        return tx_info, tx_msg

    def step_rmnSendRPRN(self, rmnNode, return_msg, code="0", msg="Success"):
        """
        手动发起return报文，sendNode和receiveNode都是rmn
        """
        re_headers = self.make_header(rmnNode, self.api_key, "RPRN")
        msg_header = self.make_group_header(rmnNode, rmnNode, re_headers["msgId"])
        tx_info, tx_msg = self.manual_return_transaction(self.sec_key, re_headers, msg_header, return_msg)
        self.checkCodeAndMessage(tx_info, code, msg)
        if code == "0":
            assert tx_info["data"]["stsId"] == "RCVD", "提交return后stsId不正确"
            self.checkOldTransactionInDB(tx_info["data"]["txId"])
        return tx_info, tx_msg

    def getNodeFeeWithApi(self, base_url, sn_node, payCurrency, side, targetCurrency, receiveMethod="BANK",
                          isReturnOrder=False):
        params = {
            "payCurrency": payCurrency,
            "side": side,
            "payQuantity": 1000,
            "targetCurrency": targetCurrency,
            "receiveMethod": receiveMethod,
            "isReturnOrder": isReturnOrder,
        }
        fee_info = requests.get(base_url + "/" + sn_node, params=params)
        self.logger.info(f"查询得到的费用为: {fee_info.json()}")

    def submitRTSOrder(self, sender, rts_client, cdtTrfTxInf, rpc_client, amt, node_fee=0):

        instructionId = originalId = f"test_{str(int(time.time() * 1000))}"
        sendCurrency = cdtTrfTxInf["splmtryData"]["envlp"]["cnts"]["sndrCcy"]
        receiveCurrency = cdtTrfTxInf["splmtryData"]["envlp"]["cnts"]["rcvrCcy"]
        sendAmount = cdtTrfTxInf["splmtryData"]["envlp"]["cnts"]["sndrAmt"]
        out_node, out_country = self.translateRouterListRequestBodyToRTS(cdtTrfTxInf, isRcctParams=True)
        sender_names = cdtTrfTxInf["dbtr"]["nm"].split(" ")
        receiver_names = cdtTrfTxInf["cdtr"]["nm"].split(" ")
        receiveInfo = {
            "senderFirstName": sender_names[0],
            "senderMiddleName": " ".join(sender_names[1:-1]),
            "senderLastName": sender_names[-1],
            "senderCountry": cdtTrfTxInf["dbtr"]["pstlAdr"].get("ctry"),
            "senderStates": cdtTrfTxInf["dbtr"]["pstlAdr"].get("ctrySubDvsn"),
            "senderCity": cdtTrfTxInf["dbtr"]["pstlAdr"].get("twnNm"),
            "senderAddress": cdtTrfTxInf["dbtr"]["pstlAdr"].get("adrLine"),
            "senderPostcode": cdtTrfTxInf["dbtr"]["pstlAdr"].get("pstCd"),
            "senderAccountNumber": cdtTrfTxInf["dbtrAcct"].get("acctId"),
            "receiverFirstName": receiver_names[0],
            "receiverLastName": receiver_names[-1],
            "receiverMiddleName": " ".join(receiver_names[1:-1]),
            "purpose": cdtTrfTxInf["purp"].get("desc"),
            "receiverBankName": cdtTrfTxInf["cdtrAgt"].get("nm"),
            "remark": cdtTrfTxInf["splmtryData"].get("rmrk"),
            "receiverStates": cdtTrfTxInf["cdtr"]["pstlAdr"].get("ctrySubDvsn"),
            "receiverCity": cdtTrfTxInf["cdtr"]["pstlAdr"].get("twnNm"),
            "receiverCountry": cdtTrfTxInf["cdtr"]["pstlAdr"].get("ctry"),
            "receiverPostcode": cdtTrfTxInf["cdtr"]["pstlAdr"].get("pstCd"),
            "receiverAddress": cdtTrfTxInf["cdtr"]["pstlAdr"].get("adrLine"),
            "receiverAccountName": cdtTrfTxInf["cdtrAcct"].get("nm"),
            "receiverAccountNumber": cdtTrfTxInf["cdtrAcct"].get("acctId"),
            "receiverAccountType": cdtTrfTxInf["cdtrAcct"].get("tp"),
            "receiverCurrency": receiveCurrency,
        }
        if "prvtId" in cdtTrfTxInf["dbtr"]:
            tmp_msg = {
                "senderBirthday": cdtTrfTxInf["dbtr"]["prvtId"]["dtAndPlcOfBirth"].get("birthDt"),
                "senderIdType": cdtTrfTxInf["dbtr"]["prvtId"]["othr"].get("prtry"),
                "senderIdNumber": cdtTrfTxInf["dbtr"]["prvtId"]["othr"].get("id"),
                "senderIdIssueCountry": cdtTrfTxInf["dbtr"]["prvtId"]["othr"].get("issr"),
                "senderNationality": cdtTrfTxInf["dbtr"]["prvtId"]["dtAndPlcOfBirth"].get("ctryOfBirth"),
            }
            receiveInfo.update(tmp_msg)
        if "prvtId" in cdtTrfTxInf["cdtr"]:
            tmp_msg = {
                "receiverIdNumber": cdtTrfTxInf["cdtr"]["prvtId"]["othr"].get("id"),
                "receiverIdType": cdtTrfTxInf["cdtr"]["prvtId"]["othr"].get("prtry"),
                "receiverNationality": cdtTrfTxInf["cdtr"]["prvtId"]["dtAndPlcOfBirth"].get("ctryOfBirth"),
                "receiverBirthday": cdtTrfTxInf["cdtr"]["prvtId"]["dtAndPlcOfBirth"].get("birthDt"),
            }
            receiveInfo.update(tmp_msg)
        if "orgId" in cdtTrfTxInf["dbtr"]:
            tmp_msg = {
                "senderOrgBIC": cdtTrfTxInf["dbtr"]["orgId"].get("anyBIC"),
                "senderOrgLei": cdtTrfTxInf["dbtr"]["orgId"].get("lei"),
                "senderOrgIdType": cdtTrfTxInf["dbtr"]["orgId"]["othr"].get("prtry"),
                "senderOrgIdNumber": cdtTrfTxInf["dbtr"]["orgId"]["othr"].get("id"),
                "senderOrgIdIssuer": cdtTrfTxInf["dbtr"]["orgId"]["othr"].get("issr"),
            }
            receiveInfo.update(tmp_msg)
        if "orgId" in cdtTrfTxInf["cdtr"]:
            tmp_msg = {
                "receiverOrgBIC": cdtTrfTxInf["cdtr"]["orgId"].get("anyBIC"),
                "receiverOrgLei": cdtTrfTxInf["cdtr"]["orgId"].get("lei"),
                "receiverOrgIdType": cdtTrfTxInf["cdtr"]["orgId"]["othr"].get("prtry"),
                "receiverOrgIdNumber": cdtTrfTxInf["cdtr"]["orgId"]["othr"].get("id"),
                "receiverOrgIdIssuer": cdtTrfTxInf["cdtr"]["orgId"]["othr"].get("issr"),
            }
            receiveInfo.update(tmp_msg)
        if "finInstnId" in cdtTrfTxInf["cdtrAgt"] and "bicFI" in cdtTrfTxInf["cdtrAgt"]["finInstnId"]:
            receiveInfo["receiverBankBIC"] = cdtTrfTxInf["cdtrAgt"]["finInstnId"]["bicFI"]
        elif "clrSysMmbId" in cdtTrfTxInf["cdtrAgt"]["finInstnId"]:
            receiveInfo["receiverBankNCCType"] = cdtTrfTxInf["cdtrAgt"]["finInstnId"]["clrSysMmbId"]["clrSysCd"]
            receiveInfo["receiverBankNCC"] = cdtTrfTxInf["cdtrAgt"]["finInstnId"]["clrSysMmbId"]["mmbId"]
        elif "othr" in cdtTrfTxInf["cdtrAgt"]["finInstnId"]:
            receiveInfo["receiverRoxeId"] = cdtTrfTxInf["cdtrAgt"]["finInstnId"]["othr"]["id"]
        if "brnchId" in cdtTrfTxInf["cdtrAgt"]:
            receiveInfo["receiverBranchName"] = cdtTrfTxInf["cdtrAgt"]["brnchId"]["nm"]
            receiveInfo["receiverBranchCode"] = cdtTrfTxInf["cdtrAgt"]["brnchId"]["id"]
        # print(receiveInfo)
        # return
        self.logger.warning(f"节点{sender}从RTS下单")
        res = rpc_client.submitPayinOrder("CHECKOUT", "src_dxles3kr3zluned5xk4thhnjbe", payMethod="debitCard",
                                          amount=ApiUtils.parseNumberDecimal(amt - node_fee, 2, isUp=True))
        rpcId = res["data"]["rpcId"]
        rpc_client.getPayinOrderTransactionStateByRpcId(rpcId)
        # paymentId = rpcId if rpcId else instructionId
        rts_order, _ = rts_client.submitOrder(
            instructionId, originalId, rpcId, sendCurrency, sendAmount, receiveCurrency, receiveInfo,
            receiveCountry=out_country, sendNodeCode=sender, receiveNodeCode=out_node
        )
        rts_order_id = rts_order["data"]["transactionId"]
        time.sleep(3)
        con_sql = f"select * from `{self.rts_db_name}`.rts_order where order_id='{rts_order_id}' and order_state in ('TRANSFER_SUBMIT', 'REDEEM_SUBMIT')"
        ApiUtils.waitCondition(self.mysql.exec_sql_query, (con_sql, ), lambda x: len(x) > 0, 120, 5)

        find_rmn_sql = f"select rmn_txn_id from rmn_transaction where rts_txn_id='{rts_order_id}'"
        rmn_tx_id = self.mysql.exec_sql_query(find_rmn_sql)[0]["rmnTxnId"]
        return rmn_tx_id

    def updateRTSOrderState(self, sn1, sn1_fee, cdtTrfTxInf, rts_order_info):
        time.sleep(3)
        rts_order_id = rts_order_info['transactionId']
        rts_payment_id = rts_order_info['paymentId']
        mint_deposit_msg = {
            "amount": ApiUtils.parseNumberDecimal(
                float(cdtTrfTxInf["splmtryData"]["envlp"]["cnts"]["sndrAmt"]) - sn1_fee, 2),
            "currency": cdtTrfTxInf["splmtryData"]["envlp"]["cnts"]["sndrCcy"],
            "id": f"{sn1},{rts_payment_id}",
            "referenceId": rts_payment_id,
            "status": "PAY_SUCCESS"
        }
        rss_sql = f"select order_id from `roxe_node_v3`.node_order where client_id='{rts_order_id}_sn1'"
        rss_order_id = self.mysql.exec_sql_query(rss_sql)[0]["orderId"]
        up_date = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")
        in_sql = f"insert into `roxe_node_v3`.node_order_log (order_id, order_state, log_info, create_time) values \
        ('{rss_order_id}', 'mint_deposit', '{json.dumps(mint_deposit_msg)}', '{up_date}')"
        self.mysql.exec_sql_query(in_sql)
        update_rss_sql = f"update `roxe_node_v3`.node_order set order_state='mint_deposit' where client_id='{rts_order_id}_sn1'"
        self.mysql.exec_sql_query(update_rss_sql)

        f_sql = f"select order_id from `roxe_node_v3`.node_order where client_id='{rts_order_id}_sn1' and order_state='finish'"
        ApiUtils.waitCondition(
            self.mysql.exec_sql_query, (f_sql,),
            lambda func_res: len(func_res) > 0, 180, 15
        )

    def matchBusinessTypeByCdtTrfTxInf(self, cdtTrfTxInf):
        if cdtTrfTxInf.get("rtrdInstdAmt"):
            b_type = "B2" if cdtTrfTxInf["rtrChain"]["dbtr"].get("orgId") else "C2"
            b_type += "B" if cdtTrfTxInf["rtrChain"]["cdtr"].get("orgId") else "C"
        else:
            b_type = "B2" if cdtTrfTxInf["dbtr"].get("orgId") else "C2"
            b_type += "B" if cdtTrfTxInf["cdtr"].get("orgId") else "C"
        self.logger.warning(f"业务类型为: {b_type}")
        return b_type

    def getServiceFee(self, cdtTrfTxInf):
        # service_fees = {"US_USD":1.5, "GB_USD":2.35, "PH_PHP":20}
        ccy = cdtTrfTxInf["splmtryData"]["envlp"]["cnts"]["sndrCcy"]
        country = "US"
        is_return = False
        if "rtrdInstdAmt" in cdtTrfTxInf:
            is_return = True
            if cdtTrfTxInf["rtrChain"]["dbtrAgt"]["finInstnId"].get("othr"):
                dbtrAgt = cdtTrfTxInf["rtrChain"]["dbtrAgt"]["finInstnId"]["othr"]["id"]
            else:
                dbtrAgt = cdtTrfTxInf["rtrChain"]["dbtrIntrmyAgt"]["finInstnId"]["othr"]["id"]
        else:
            dbtrAgt = cdtTrfTxInf["dbtrAgt"]["finInstnId"]["othr"]["id"]

        if dbtrAgt in ["huu4lssdbmbt", "pn.test.gb"]:
            country = "GB"

        if self.check_db:
            amt = float(cdtTrfTxInf["splmtryData"]["envlp"]["cnts"]["sndrAmt"])
            b_type = self.matchBusinessTypeByCdtTrfTxInf(cdtTrfTxInf)
            node_fee = self.getNodeFeeInDB(dbtrAgt, ccy, amt, b_type, is_return=is_return)
            self.logger.warning(f"节点费用信息: {node_fee}")
            return node_fee["service_fee"]

        # cfg_fee = f'{country}_{ccy}'
        # service_fee = service_fees[cfg_fee] if cfg_fee in service_fees else 0
        # self.logger.warning(f"service fee: {service_fee}")
        # return service_fee

    # 校验函数

    @staticmethod
    def checkCodeAndMessage(res, code="0", msg="Success"):
        # 校验response的code、message
        if isinstance(code, RmnCodEnum):
            assert res["code"] == code.code, f"{res['code']} not equal {code.code}"
            assert res["message"] == code.msg, f"{res['message']} not equal {code.msg}"
            return
        assert res["code"] == code, f"{res['code']} not equal {code}"
        assert res["message"] == msg, f"{res['message']} not equal {msg}"

    def checkHeaderLengthLimit(self, headers, callback, callArgs: list, headerLoc=1):
        length_headers = ["version:3", "sndrRID:12", "sndrApiKey:64", "rcvrRID:12", "msgTp:16", "msgId:25", "msgRefID:25", "sysFlg:4"]
        for i, key in enumerate(length_headers):
            h, h_len = key.split(":")
            new_headers = copy.deepcopy(headers)
            new_headers[h] = ApiUtils.generateString(int(h_len) + 1)
            self.logger.warning(f"header中{h}长度超限")
            self.logger.info(f"headers: {new_headers}")
            callArgs[headerLoc] = new_headers
            func_res, req_msg = callback(*callArgs)
            # h = "msgId" if h == "msgID" else h
            self.checkCodeAndMessage(func_res, "00100106", f"HTTP Header exception, {h} is not valid")

    def checkHeadersMissingField(self, headers, callback, callArgs: list):
        miss_headers = ["version", "sndrRID", "msgTp", "msgId", "sign"]
        for m_h in miss_headers:
            new_headers = headers.copy()
            callArgs[1] = new_headers
            tx_info, tx_msg = callback(*callArgs, popHeader=m_h)
            # m_h = "msgId" if m_h == "msgID" else m_h
            err_message = f"Missing request header '{m_h}' for method parameter of type String"
            self.checkCodeAndMessage(tx_info, "00100106", err_message)

    def checkEncryptBodyMissingField(self, callback, callArgs: list):
        for m_k in ["algorithm", "ciphertext", "nonce"]:
            tx_info, tx_msg = callback(*callArgs, popBody=m_k)
            msg = f"Encrypted message exception, {m_k} is empty"
            if m_k != "algorithm": msg += " or blank"
            self.checkCodeAndMessage(tx_info, "00100108", msg)
        tx_info, tx_msg = callback(*callArgs, popBody="associatedData")
        self.checkCodeAndMessage(tx_info, "00200002", "request data can't be decrypted")

    def checkEncryptBodyReplaceBody(self, callback, callArgs: list):
        for m_k in ["ciphertext", "nonce", "associatedData"]:
            tx_info, tx_msg = callback(*callArgs, repBody=m_k)
            self.checkCodeAndMessage(tx_info, "00200002", "request data can't be decrypted")
        tx_info, tx_msg = callback(*callArgs, repBody="algorithm")
        self.checkCodeAndMessage(tx_info, "00100108", f"Encrypted message exception, algorithm is not valid")

    def checkBodyFieldsLengthLimit(self, fieldsLimit, callback, callArgs: list, bodyLoc=3, pre="cdtTrfTxInf."):
        rep_body = copy.deepcopy(callArgs[bodyLoc])
        for f_limit in fieldsLimit:
            tmp_body = copy.deepcopy(rep_body)
            field_key, field_len = f_limit.split(":")
            g_v = ApiUtils.generateString(int(field_len) + 1)
            tmp_d = ApiUtils.generateDict(field_key, g_v)
            tmp_body = ApiUtils.deepUpdateDict(tmp_body, tmp_d)
            callArgs[bodyLoc] = tmp_body
            tx_info, tx_msg = callback(*callArgs)
            self.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, {pre}{field_key} has invalid value:{g_v}")

    def checkBodyFieldsMissing(self, fieldsLimit, callback, callArgs: list, bodyLoc=3, pre="cdtTrfTxInf."):
        rep_body = copy.deepcopy(callArgs[bodyLoc])
        for field_key in fieldsLimit:
            tmp_body = copy.deepcopy(rep_body)
            tmp_d = ApiUtils.generateDict(field_key, None)
            tmp_body = ApiUtils.deepUpdateDict(tmp_body, tmp_d)
            callArgs[bodyLoc] = tmp_body
            tx_info, tx_msg = callback(*callArgs)
            self.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, {pre}{field_key} is empty")

    def getSttlMsgInfo(self, rmnTxnId, node, cdtDbtInd):
        body = {
            "rmnTxnId": rmnTxnId,
            "nodeCode": node,
            "cdtDbtInd": cdtDbtInd,
        }
        h = {"sndrApiKey": "aoe", "sndDtTm": "aoe", "sign": "aoe"}
        res = sendPostRequest(self.host + "/pcs/get-sttlMsg-info", json.dumps(body), h)
        self.logger.info(f"结果: {res.text}")

    def checkTransactionState(self, rmn_tx_id, ex_state="RCJT"):
        if self.check_db:
            sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}'"
            db_info = self.mysql.exec_sql_query(sql)
            assert db_info[0]["txnState"] == ex_state, "数据库状态和预期不一致, {} != {}".format(db_info[0]["txnState"], ex_state)

    def checkNotNormalOrderInRTS(self, rmn_tx_id, rts_order_status, node='sn1', sn_node="sn-rmn-rmn-roxe", sn_order_state='init'):
        if self.check_db:
            # 校验RTS订单状态
            rts_order_info = self.mysql.exec_sql_query(f"select * from `{self.rts_db_name}`.rts_order where client_id='{rmn_tx_id}'")
            assert rts_order_status == rts_order_info[0]["orderState"], "rts订单状态: " + rts_order_info[0]["orderState"]
            assert rts_order_info[0]["orderStop"], "rts订单是否停止: " + rts_order_info[0]["orderStop"]
            # 校验RSS订单状态
            rts_order = rts_order_info[0]["orderId"]
            if self.rts_db_name.endswith("_v3"):
                sn_node_db = "roxe_node_v3"
                sn_node_tb = "node_order"
            else:
                node_key = "pay_node_code" if node == "sn1" else "out_node_code"
                node_info = self.mysql.exec_sql_query(f"select * from `{self.rts_db_name}`.rts_node_router where {node_key}='{sn_node}'")
                node_cfg = json.loads(node_info[0]["routerConfig"])
                sn_node_db = node_cfg[node]["nodeUrl"].lstrip("1").split("/")[-1]
                sn_node_tb = "sn_order"
            try:
                rss_order_info = self.mysql.exec_sql_query(
                    f"select * from `{sn_node_db}`.{sn_node_tb} where client_id='{rts_order}_{node}'")[0]
            except IndexError:
                rss_order_info = self.mysql.exec_sql_query(
                    f"select * from `{sn_node_db}`.{sn_node_tb} where client_id='{rts_order}_{node}'")[0]
            sn_state = [sn_order_state]
            if node == "sn2":
                sn_state.append("redeem_deposit")
                sn_state.append("redeem_submit")
            assert rss_order_info["orderState"] in sn_state, "rss订单状态: " + rss_order_info["orderState"]

    def checkExpectFlowState(self, expect_flow, flow_info, rmn_tx_id):
        expect_flows = [expect_flow] if isinstance(expect_flow, str) else expect_flow
        flow_states = [i["sts"] for i in flow_info["data"]["rptOrErr"]["splmtryData"]]
        for flow in expect_flows:
            assert flow in flow_states, f"订单flow接口数据校验有误，{flow}未存在{flow_states}中"
        if self.check_db:
            flow_sql = f"select txn_state from roxe_rmn.rmn_txn_flow where rmn_txn_id='{rmn_tx_id}'"
            flow_db = self.mysql.exec_sql_query(flow_sql)
            db_states = [i['txnState'] for i in flow_db]
            for flow in expect_flows:
                assert flow in db_states, f"订单flow在数据库记录有误，{flow}未存在{db_states}中"

    def checkRetryNotifyInfo(self, notify_db, new_url, skipCheckUrl=False):
        assert notify_db[0]["notifyCount"] == 6, "发送通知的次数总共应该为6次"
        notify_sql = f"select * from mock_notify.res_info order by create_at desc limit {notify_db[0]['notifyCount']}"
        notify_info = self.mysql.exec_sql_query(notify_sql)
        retry_time = 300 + 120 * 4
        for n_index, notify in enumerate(notify_info):
            if not skipCheckUrl:
                assert notify["url"] == new_url, "通知消息中回调地址不不正确"
            assert notify_db[0]["notifyUrl"] == new_url, "回调地址不正确"
            assert notify_db[0]["notifyStatus"] == "THRESHOLD_EXCEED", "回调状态不正确"
            assert notify_db[0]["msgContent"] == notify["response"], "回调内容不正确"
            self.logger.warning("收到回调的时间: {}".format(notify["createAt"]))
            ex_time = notify_db[0]["createTime"].timestamp() + retry_time + 3600 * 8
            time_dif = abs(notify["createAt"].timestamp() - ex_time)
            assert time_dif <= 30, "时间差距太大: {} {}".format(notify_db[0]["createTime"].timestamp(), ex_time)
            if n_index < 4:
                retry_time -= 120
            else:
                retry_time -= 300

    def checkRTSAmountWhenFinish(self, rmn_tx_id, last_order_amount, last_sn_fee, last_type="SN", last_pn_fee=0):
        """
        当交易完成后，校验RTS系统返回的金额
        :param rmn_tx_id: rmn系统的交易ID
        :param last_order_amount: 最后1个节点收到的RCCT消息中的结算金额【intrBkSttlmAmt】
        :param last_sn_fee: 最后1个结算节点SN2的费用
        :param last_type: 最后一个节点的属性
        :param last_pn_fee: pn2的费用
        :return:
        """
        if self.check_db:
            time.sleep(3)
            ApiUtils.waitCondition(
                self.mysql.exec_sql_query,
                (f"select * from rmn_rts_message where rmn_txn_id='{rmn_tx_id}' and rts_state='TRANSACTION_FINISH'",),
                lambda x: len(x) > 0, 120, 5
            )
            rmn_rts = self.mysql.exec_sql_query(
                f"select * from rmn_rts_message where rmn_txn_id='{rmn_tx_id}' order by create_time;")
            rmn_sn2_finish = json.loads([i["rtsMsgContent"] for i in rmn_rts if i["rtsState"] == "REDEEM_FINISH"][0])
            rmn_finish = json.loads([i["rtsMsgContent"] for i in rmn_rts if i["rtsState"] == "TRANSACTION_FINISH"][0])
            self.logger.debug(f"REDEEM_FINISH: {rmn_sn2_finish}")
            self.logger.debug(f"TRANSACTION_FINISH: {rmn_finish}")

            def check_diff(x, y, diff, msg=""):
                assert abs(x - y) < diff, f"{msg}: {x} != {y}"

            # redeem_amt = last_order_amount - last_sn_fee if last_type == "SN" else last_order_amount
            if last_type == "SN":
                finish_fee = last_sn_fee
                redeem_amt = last_order_amount
                finish_amt = redeem_amt
            else:
                redeem_amt = last_order_amount + last_sn_fee
                finish_amt = last_order_amount - last_pn_fee
                finish_fee = last_pn_fee
            check_diff(rmn_sn2_finish["log"]["info"]["quantity"], redeem_amt, 0.01, "REDEEM_FINISH quantity不正确")
            check_diff(rmn_sn2_finish["log"]["info"]["feeQuantity"], last_sn_fee, 0.01, "REDEEM_FINISH fee不正确")
            check_diff(rmn_finish["log"]["info"]["quantity"], finish_amt, 0.01, "TRANSACTION_FINISH quantity不正确")
            check_diff(rmn_finish["log"]["info"]["feeQuantity"], finish_fee, 0.01, "TRANSACTION_FINISH fee不正确")

    def checkOldTransactionInDB(self, return_rmn_id, old_rts_status="", isHalf=False):
        """
        提交return请求成功后，原交易的状态更新为RETURNED
        """
        if not self.check_db:
            return
        re_tx_info = self.mysql.exec_sql_query(f"select * from rmn_transaction where rmn_txn_id='{return_rmn_id}'")[0]
        old_tx_info = self.mysql.exec_sql_query(f"select * from rmn_transaction where rmn_txn_id='{re_tx_info['relTxnId']}'")[0]
        assert old_tx_info["txnState"] == "RETURNED", "原交易状态应为RETURNED"
        if old_rts_status:
            rts_order = old_tx_info["rtsTxnId"]

            old_rts_info = ApiUtils.waitCondition(
                self.mysql.exec_sql_query,
                (f"select * from `{self.rts_db_name}`.rts_order where order_id='{rts_order}'",),
                lambda x: x[0]["orderState"] == old_rts_status, 120, 5
            )[0]
            # old_rts_info = self.mysql.exec_sql_query(f"select * from `{self.rts_db_name}`.rts_order where order_id='{rts_order}'")[0]
            assert old_rts_info["orderState"] == old_rts_status, "原交易对应的RTS订单的状态为: {}".format(old_rts_info)
            if isHalf:
                # rss节点分库后，rss数据库名称的方式
                # rts_router = self.mysql.exec_sql_query(f"select * from `{self.rts_db_name}`.rts_node_router where router_id='{old_rts_info['routerId']}'")[0]
                # rss_node_db = json.loads(rts_router["routerConfig"])["sn2"]["nodeUrl"].split("/")[-1]
                rss_node_db = 'roxe_node_v3'
                time.sleep(10)
                rss_order = self.mysql.exec_sql_query(f"select * from `{rss_node_db}`.node_order where client_id like '{rts_order}_sn2'")[0]
                rss_order_log = self.mysql.exec_sql_query(f"select * from `{rss_node_db}`.node_order_log where order_id='{rss_order['orderId']}' and order_state='refund_tag'")
                assert rss_order_log[0], f"原交易对应的roxe node订单状态为: {rss_order_log}"

    def checkSNSMsgOrPNSMsg(self, rmn_tx_id, exType, msgType, origin_msg):
        if self.check_db and self.rts_db_name.endswith("_v3"):
            # RMN改造后，接收到结算报错，RMN会向SNS系统发送消息
            sns_sql = f"select * from rmn_msg_ex where rmn_txn_id='{rmn_tx_id}' and msg_id='{origin_msg['grpHdr']['msgId']}'"
            sns_msg = self.mysql.exec_sql_query(sns_sql)
            self.logger.warning(f"准备校验RMN发送给{exType}系统的消息:{sns_msg}")
            send_sns_msg = json.loads(sns_msg[0]["msgContent"])
            assert sns_msg[0]["exType"] == exType, f"{sns_msg[0]['exType']}不正确"
            assert sns_msg[0]["msgType"] == msgType, f"{sns_msg[0]['msgType']}不正确"
            assert sns_msg[0]["sent"] in (0, 1), f"sent标志为：{sns_msg[0]['sent']}"
            assert json.loads(send_sns_msg["msgContent"]) == origin_msg, f"msgContent不正确:{send_sns_msg}"
            assert sns_msg[0]["errorMsg"] is None, f"发送消息失败: {sns_msg[0]['errorMsg']}"

    def getChainAccountBalance(self):
        self.logger.warning(f"fape1meh4bsz节点的资产: {self.chain_client.get_currency_balance('fape1meh4bsz', 'roxe.ro', 'USD')}")
        self.logger.warning(f"huu4lssdbmbt节点的资产: {self.chain_client.get_currency_balance('huu4lssdbmbt', 'roxe.ro', 'USD')}")
        self.logger.warning(f"5chnthreqiow节点的资产: {self.chain_client.get_currency_balance('5chnthreqiow', 'roxe.ro', 'USD')}")

    # 流程函数
    def transactionFlow_sn_sn(self, sn1, sn2, cdtTrfTxInf, sn_fees, caseObj, isInnerNode=False, isRPP=False, rateInfo=None, chg_fees=None, isPending=False):
        rmn_id = "risn2roxe51"
        api_key, sec_key = self.api_key, self.sec_key
        service_fee = self.getServiceFee(cdtTrfTxInf)

        self.logger.warning("sn1节点提交交易请求")
        msg_id = self.make_msg_id()
        tx_headers = self.make_header(sn1, api_key, "RCCT", msg_id, sysFlg="SBCD")
        tx_group_header = self.make_group_header(sn1, rmn_id, msg_id)
        tx_info, tx_msg = self.submit_transaction(sec_key, tx_headers, tx_group_header, cdtTrfTxInf)

        self.checkCodeAndMessage(tx_info)
        caseObj.assertEqual(tx_info["data"]["stsId"], "RCVD")
        rmn_tx_id = tx_info["data"]["txId"]
        end2end_id = cdtTrfTxInf["pmtId"]["endToEndId"]
        caseObj.checkTransactionMessageInDB(rmn_tx_id, tx_msg)
        time.sleep(10)
        # self.getChainAccountBalance()
        self.logger.warning("sn1节点收到交易confirm")
        sn_tx_confirm = self.waitNodeReceiveMessage(sn1, msg_id, None, msg_id, api_key, sec_key, "ACCEPTED_CONF_SENT")
        caseObj.checkConfirmMessage(sn_tx_confirm, "ACPT", msg_id, "RCCT", sn1, end2end_id, end2end_id, "TXNS")
        caseObj.getAndcheckTransactionStatus(sn1, api_key, sec_key, msg_id, sn1, "ACPT")
        # self.getChainAccountBalance()
        sn1_st_msg = self.step_sendRCSR(sn1, api_key, sec_key, tx_msg, rmn_tx_id, "CRDT", self, nodeLoc="SN1")
        if isInnerNode:
            if isPending:
                f_sql = f"select * from rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='PENDING'"
                ApiUtils.waitCondition(
                    self.mysql.exec_sql_query, (f_sql,),
                    lambda func_res: len(func_res) > 0, 180, 15
                )
                f_sql = f"select * from rmn_notify_info where rmn_txn_id='{rmn_tx_id}' and msg_content like '%PDNG%'"
                notify_info = ApiUtils.waitCondition(
                    self.mysql.exec_sql_query, (f_sql,),
                    lambda func_res: len(func_res) > 0, 120, 15
                )
                self.logger.info(f"发送给SN1的pending RTPC: {notify_info}")
                pending_msg = caseObj.checkConfirmMessage(json.loads(notify_info[0]["msgContent"]), "PDNG", msg_id, "RCCT", sn1, end2end_id, end2end_id, "TXNN")

                order_info = self.step_queryTransactionState(sn1, api_key, sec_key, msg_id, sn1)
                assert pending_msg in order_info["data"]["rptOrErr"]["pmt"]["addtlNtryInf"], "pending原因未出现在查询交易的结果中"
                return
            if self.check_db:
                f_sql = f"select * from rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='TRANSACTION_FINISH'"
                ApiUtils.waitCondition(
                    self.mysql.exec_sql_query, (f_sql,),
                    lambda func_res: len(func_res) > 0, 180, 15
                )
            else:
                ApiUtils.waitCondition(
                    self.step_queryTransactionState, (sn1, api_key, sec_key, msg_id, sn1,),
                    lambda func_res: func_res["data"]["rptOrErr"]["pmt"]["sts"] == "CMPT", 180, 15
                )
            self.logger.warning("sn1节点接收交易完成的confirm")
            sn1_st_msg_id = sn1_st_msg["grpHdr"]["msgId"]
            sn1_endId = sn1_st_msg["cdtTrfTxInf"]["pmtId"]["endToEndId"]
            sn1_tx_confirm = self.waitNodeReceiveMessage(sn1, sn1_st_msg_id, "CMPT", msg_id, api_key, sec_key,
                                                         "DEBIT_SN_NOTICE_SENT")
            caseObj.checkConfirmMessage(sn1_tx_confirm, "CMPT", sn1_st_msg_id, "RCSR", sn1, sn1_endId, sn1_endId, "STTN")
            caseObj.getAndcheckTransactionStatus(sn1, api_key, sec_key, sn1_st_msg_id, sn1, "CMPT")
            self.logger.warning("追踪交易flow")
            ts_headers = self.make_header(sn1, api_key, "RATQ")
            msg_header = self.make_msg_header(sn1, ts_headers["msgId"])
            txQryDef = self.make_RTSQ_information(msg_id, sn1, ntryTp="ADT")
            flow_info, req_msg = self.get_transaction_flow(sec_key, ts_headers, msg_header, txQryDef)
            caseObj.checkTransactionFlowInDB(flow_info["data"], req_msg)
            return
        self.logger.warning("sn2节点收到交易请求")
        sn2_tx_info = self.waitReceiveTransactionMessage(rmn_tx_id, sn2, None, sn1, msg_id, api_key, sec_key, "CREDIT_SN_TXN_SENT")
        caseObj.checkNodeReceivedTransactionMessage(rmn_tx_id, sn2_tx_info, sn2, [sn1], [sn_fees[0]], isRPP, rateInfo, chg_fees, service_fee=service_fee)
        if isRPP:
            caseObj.checkChainInfoOfRPPInRTS(rmn_tx_id, sn1_st_msg, service_fee)
        sn2_tx_msg_id = sn2_tx_info["grpHdr"]["msgId"] if self.check_db else sn2_tx_info["msgId"]
        caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_tx_msg_id, rmn_id, "STDB")
        self.step_sendRTPC(sn2, api_key, sec_key, sn2_tx_info)
        # stsRsnInf = {"addtlInf": "Beneficiary account error", "stsRsnCd": "00600114"}
        # self.step_sendRTPC(sn2, api_key, sec_key, sn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)
        # return
        time.sleep(1)
        # self.getChainAccountBalance()
        caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_tx_msg_id, rmn_id, "STDB")

        # # sandbox环境，查询的不是数据库，而是flow状态，等待时间会变长，最终可能为完成状态
        # ex_state = ["STCD", "STLD"] if RMNData.is_check_db else ["STCD", "STLD", "CMPT"]
        if self.check_db:
            sn2_st_msg = self.step_sendRCSR(sn2, api_key, sec_key, sn2_tx_info, rmn_tx_id, "DBIT", self, nodeLoc="SN2")
        else:
            st_headers = self.make_header(sn2, api_key, "RCSR")
            st_grpHder = self.make_group_header(sn2, rmn_id, st_headers["msgId"])
            # st_cdtInf = self.client.make_RCSR_information(rcctMsg, "DBIT", sn2)
            st_cdtInf = {
                "intrBkSttlmAmt": sn1_st_msg["cdtTrfTxInf"]["intrBkSttlmAmt"].copy(),
                "intrBkSttlmDt": datetime.datetime.now().strftime(self.iso_date_format),
                "pmtId": {"endToEndId": end2end_id, "txId": end2end_id},
                "dbtr": self.make_roxe_agent(rmn_id, "VN"),
                "dbtrAcct": tx_msg["cdtTrfTxInf"]["dbtrAcct"],
                "cdtr": self.make_roxe_agent(sn2, "SN"),
                "cdtrAcct": tx_msg["cdtTrfTxInf"]["cdtrAcct"],
                "rmtInf": {"orgnlMsgID": sn2_tx_msg_id, "orgnlMsgTp": "RCCT", "instgAgt": rmn_id},
                "splmtryData": {"envlp": {"ustrd": {"cdtDbtInd": "DBIT"}}}
            }
            st_info, sn2_st_msg = self.submit_settlement(sec_key, st_headers, st_grpHder, st_cdtInf)
            self.checkCodeAndMessage(st_info)
            assert st_info["data"]["stsId"] == "RCVD"
            assert st_info["data"]["txId"] == rmn_tx_id
        # self.getChainAccountBalance()
        self.logger.warning("sn1节点接收交易完成的confirm")
        sn1_st_msg_id = sn1_st_msg["grpHdr"]["msgId"]
        sn1_endId = sn1_st_msg["cdtTrfTxInf"]["pmtId"]["endToEndId"]
        sn1_tx_confirm = self.waitNodeReceiveMessage(sn1, sn1_st_msg_id, "CMPT", msg_id, api_key, sec_key, "DEBIT_SN_NOTICE_SENT")
        caseObj.checkConfirmMessage(sn1_tx_confirm, "CMPT", sn1_st_msg_id, "RCSR", sn1, sn1_endId, sn1_endId, "STTN")
        self.logger.warning("sn2节点接收交易完成的confirm")
        sn2_st_msg_id = sn2_st_msg["grpHdr"]["msgId"]
        sn2_endId = sn2_st_msg["cdtTrfTxInf"]["pmtId"]["endToEndId"]
        sn2_tx_confirm = self.waitNodeReceiveMessage(sn2, sn2_st_msg_id, "CMPT", sn2_st_msg_id, api_key, sec_key, "CREDIT_SN_NOTICE_SENT")
        caseObj.checkConfirmMessage(sn2_tx_confirm, "CMPT", sn2_st_msg_id, "RCSR", sn2, sn2_endId, sn2_endId, "STTN")
        finish_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='TRANSACTION_FINISH'"
        ApiUtils.waitCondition(self.mysql.exec_sql_query, (finish_sql,), lambda x: len(x) > 0, 180, 5)

        time.sleep(30)
        self.logger.warning("交易完成后，查询交易状态")
        caseObj.getAndcheckTransactionStatus(sn1, api_key, sec_key, sn1_st_msg_id, sn1, "CMPT")
        caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_st_msg_id, sn2, "CMPT")

        self.logger.warning("追踪交易flow")
        flow_info, req_msg = self.step_queryTransactionFlow(sn1, self.api_key, self.sec_key, msg_id, sn1, returnReqMsg=True)
        caseObj.checkTransactionFlowInDB(flow_info["data"], req_msg)
        if self.check_db:
            order_amt = float(sn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"])
            self.checkRTSAmountWhenFinish(rmn_tx_id, order_amt, sn_fees[1])
        return sn2_tx_info

    def transactionFlow_sn_sn_pn(self, sn1, sn2, pn2, cdtTrfTxInf, sn_fees, caseObj, isInnerNode=False, isRPP=False, rateInfo=None, chg_fees=None):
        """
        SN -> SN -> PN 场景的主流程:
            sn1节点提交交易请求
            sn1节点收到交易confirm
            sn1节点提交结算表单
            sn1节点收到结算confirm
            sn2节点收到交易请求
            sn2节点发送交易confirm
            sn2节点提交结算请求
            sn2节点等待结算confirm
            pn2节点收到交易请求
            pn2节点发送交易confirm
            sn1节点和sn2节点接收交易完成的confirm
        """
        api_key, sec_key = self.api_key, self.sec_key
        service_fee = self.getServiceFee(cdtTrfTxInf)
        rmn_id = "risn2roxe51"
        self.logger.warning("sn1节点提交交易请求")
        msg_id = self.make_msg_id()
        tx_headers = self.make_header(sn1, api_key, "RCCT", msg_id)
        tx_group_header = self.make_group_header(sn1, rmn_id, msg_id)
        tx_info, tx_msg = self.submit_transaction(sec_key, tx_headers, tx_group_header, cdtTrfTxInf)

        rmn_tx_id = tx_info["data"]["txId"]
        self.checkCodeAndMessage(tx_info)
        caseObj.assertEqual(tx_info["data"]["stsId"], "RCVD")
        caseObj.checkTransactionMessageInDB(rmn_tx_id, tx_msg)
        end2end_id = cdtTrfTxInf["pmtId"]["endToEndId"]

        self.logger.warning("sn1节点收到交易confirm")
        sn_tx_confirm = self.waitNodeReceiveMessage(sn1, msg_id)
        caseObj.checkConfirmMessage(sn_tx_confirm, "ACPT", msg_id, "RCCT", sn1, end2end_id, end2end_id, "TXNS")

        sn1_st_msg = self.step_sendRCSR(sn1, api_key, sec_key, tx_msg, rmn_tx_id, "CRDT", self, nodeLoc="SN1")
        if isInnerNode:
            time.sleep(180)
            return
        self.logger.warning("sn2节点收到交易请求")
        sn2_tx_info = self.waitReceiveTransactionMessage(rmn_tx_id, sn2, None, api_key, sec_key, "CREDIT_SN_TXN_SENT")
        caseObj.checkNodeReceivedTransactionMessage(rmn_tx_id, sn2_tx_info, sn2, [sn1], [sn_fees[0]], isRPP, rateInfo, chg_fees, service_fee=service_fee)
        if isRPP: caseObj.checkChainInfoOfRPPInRTS(rmn_tx_id, sn1_st_msg, service_fee=service_fee)

        caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_tx_info["grpHdr"]["msgId"], rmn_id, "STDB")

        self.logger.warning("sn2节点发送confirm消息")
        self.step_sendRTPC(sn2, api_key, sec_key, sn2_tx_info)
        time.sleep(3)
        caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_tx_info["grpHdr"]["msgId"], rmn_id, "STDB")

        sn2_st_msg = self.step_sendRCSR(sn2, api_key, sec_key, sn2_tx_info, rmn_tx_id, "DBIT", self, nodeLoc="SN2")
        caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_tx_info["grpHdr"]["msgId"], rmn_id, ["STDB", "STCD"])

        self.logger.warning("pn2节点接收rcct消息")
        pn2_tx_info = self.waitReceiveTransactionMessage(rmn_tx_id, pn2)
        caseObj.checkNodeReceivedTransactionMessage(rmn_tx_id, pn2_tx_info, pn2, [sn1, sn2], sn_fees, isRPP, rateInfo, chg_fees, service_fee=service_fee)
        self.logger.warning("sn2节点查询交易状态")
        caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_tx_info["grpHdr"]["msgId"], rmn_id, "STCD")

        self.logger.warning("pn2节点发送confirm消息")
        pn2_msg = self.step_sendRTPC(pn2, api_key, sec_key, pn2_tx_info)
        time.sleep(0.5)

        self.logger.warning("pn2节点查询交易状态")
        caseObj.getAndcheckTransactionStatus(pn2, api_key, sec_key, pn2_tx_info["grpHdr"]["msgId"], rmn_id, ["STCD", "STLD"])

        self.logger.warning("sn1节点和sn2节点接收交易完成的confirm")
        sn1_tx_confirm = self.waitNodeReceiveMessage(sn1, sn1_st_msg["grpHdr"]["msgId"], "CMPT", rmn_tx_id, api_key, sec_key, "DEBIT_SN_NOTICE_SENT")
        sn1_endId = sn1_st_msg["cdtTrfTxInf"]["pmtId"]["endToEndId"]
        caseObj.checkConfirmMessage(sn1_tx_confirm, "CMPT", sn1_st_msg["grpHdr"]["msgId"], "RCSR", sn1, sn1_endId, sn1_endId, "STTN")
        sn2_tx_confirm = self.waitNodeReceiveMessage(sn2, sn2_st_msg["grpHdr"]["msgId"], "CMPT", rmn_tx_id, api_key, sec_key, "CREDIT_SN_NOTICE_SENT")
        sn2_endId = sn2_st_msg["cdtTrfTxInf"]["pmtId"]["endToEndId"]
        caseObj.checkConfirmMessage(sn2_tx_confirm, "CMPT", sn2_st_msg["grpHdr"]["msgId"], "RCSR", sn2, sn2_endId,
                                    sn2_endId, "STTN")
        if self.check_db:
            self.checkSNSMsgOrPNSMsg(rmn_tx_id, "TO_PNS", "RTPC", pn2_msg)
            finish_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='TRANSACTION_FINISH'"
            ApiUtils.waitCondition(self.mysql.exec_sql_query, (finish_sql,), lambda x: len(x) > 0, 60, 5)
        else:
            ApiUtils.waitCondition(
                self.step_queryTransactionState, (sn1, api_key, sec_key, msg_id, sn1,),
                lambda func_res: func_res["data"]["rptOrErr"]["pmt"]["sts"] == "CMPT", 180, 15
            )
        time.sleep(30)
        self.logger.warning("交易完成后，查询交易状态")
        caseObj.getAndcheckTransactionStatus(sn1, api_key, sec_key, sn1_st_msg["grpHdr"]["msgId"], sn1, "CMPT")
        caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_st_msg["grpHdr"]["msgId"], sn2, "CMPT")

        self.logger.warning("追踪交易flow")
        flow_info, req_msg = self.step_queryTransactionFlow(sn1, self.api_key, self.sec_key, msg_id, sn1, returnReqMsg=True)
        caseObj.checkTransactionFlowInDB(flow_info["data"], req_msg)

        if self.check_db:
            b_type = self.matchBusinessTypeByCdtTrfTxInf(cdtTrfTxInf)
            order_amt = float(pn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"])
            pn2_fee = self.getNodeFeeInDB(pn2, pn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["ccy"], order_amt, b_type)["out"]
            # pn2_fee = self.getTransactionFeeInDB(pn2, pn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["ccy"], "out", "PN")
            self.checkRTSAmountWhenFinish(rmn_tx_id, order_amt, sn_fees[1], "PN", pn2_fee)
        return pn2_tx_info

    def transactionFlow_pn_sn_sn(self, pn1, sn1, sn2, cdtTrfTxInf, sn_fees, caseObj, isInnerNode=False, isRPP=False, rateInfo=None, chg_fees=None):
        """
        PN -> SN -> SN 场景的主流程:
            pn1节点提交交易请求
            pn1节点收到交易confirm
            sn1节点收到交易请求
            sn1节点发送交易confirm
            sn1节点提交结算表单
            sn1节点收到结算confirm
            sn2节点收到交易请求
            sn2节点发送交易confirm
            sn2节点提交结算请求
            sn2节点等待结算confirm
            sn1节点和sn2节点接收交易完成的confirm
        """
        api_key, sec_key = self.api_key, self.sec_key
        service_fee = self.getServiceFee(cdtTrfTxInf)
        rmn_id = "risn2roxe51"
        self.logger.warning("pn1节点提交交易请求")
        msg_id = self.make_msg_id()
        tx_headers = self.make_header(pn1, api_key, "RCCT", msg_id)
        tx_group_header = self.make_group_header(pn1, rmn_id, msg_id)
        tx_info, tx_msg = self.submit_transaction(sec_key, tx_headers, tx_group_header, cdtTrfTxInf)

        rmn_tx_id = tx_info["data"]["txId"]
        self.checkCodeAndMessage(tx_info)
        caseObj.assertEqual(tx_info["data"]["stsId"], "RCVD")
        caseObj.checkTransactionMessageInDB(rmn_tx_id, tx_msg)
        end2end_id = cdtTrfTxInf["pmtId"]["endToEndId"]

        self.logger.warning("pn1节点收到交易confirm")
        sn_tx_confirm = self.waitNodeReceiveMessage(pn1, msg_id, None, msg_id, api_key, sec_key, "ACCEPTED_CONF_SENT")
        caseObj.checkConfirmMessage(sn_tx_confirm, "ACPT", msg_id, "RCCT", pn1, end2end_id, end2end_id, "TXNS")

        self.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.waitReceiveTransactionMessage(rmn_tx_id, sn1)
        caseObj.checkNodeReceivedTransactionMessage(rmn_tx_id, sn1_tx_info, sn1, [pn1], [])  # rpp保持原来参数即可
        caseObj.getAndcheckTransactionStatus(pn1, api_key, sec_key, msg_id, pn1, "ACPT")
        self.step_sendRTPC(sn1, api_key, sec_key, sn1_tx_info)
        time.sleep(3)

        caseObj.getAndcheckTransactionStatus(sn1, api_key, sec_key, sn1_tx_info["grpHdr"]["msgId"], rmn_id, "ACPT")

        sn1_st_msg = self.step_sendRCSR(sn1, api_key, sec_key, sn1_tx_info, rmn_tx_id, "CRDT", self, sn_fees[0], "SN1")
        if isInnerNode:
            time.sleep(180)
            return
        self.logger.warning("sn2节点收到交易请求")
        sn2_tx_info = self.waitReceiveTransactionMessage(rmn_tx_id, sn2, sn1_tx_info["grpHdr"]["msgId"])
        caseObj.checkNodeReceivedTransactionMessage(rmn_tx_id, sn2_tx_info, sn2, [pn1, sn1], [sn_fees[0]], isRPP, rateInfo, chg_fees, service_fee=service_fee)
        if isRPP: caseObj.checkChainInfoOfRPPInRTS(rmn_tx_id, sn1_st_msg, service_fee)
        caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_tx_info["grpHdr"]["msgId"], rmn_id, "STDB")
        self.step_sendRTPC(sn2, api_key, sec_key, sn2_tx_info)
        # stsRsnInf = {"addtlInf": "Beneficiary information error", "stsRsnCd": "00600120"}
        # self.step_sendRTPC(sn2, api_key, sec_key, sn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)
        # return
        time.sleep(1)

        caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_tx_info["grpHdr"]["msgId"], rmn_id, "STDB")

        sn2_st_msg = self.step_sendRCSR(sn2, api_key, sec_key, sn2_tx_info, rmn_tx_id, "DBIT", self, nodeLoc="SN2")

        caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_tx_info["grpHdr"]["msgId"], rmn_id, ["STDB", "STCD", "STLD"])
        time.sleep(1)
        self.logger.warning("sn1节点接收交易完成的confirm")
        sn1_tx_confirm = self.waitNodeReceiveMessage(sn1, sn1_st_msg["grpHdr"]["msgId"], "CMPT")
        sn1_endId = sn1_st_msg["cdtTrfTxInf"]["pmtId"]["endToEndId"]
        caseObj.checkConfirmMessage(sn1_tx_confirm, "CMPT", sn1_st_msg["grpHdr"]["msgId"], "RCSR", sn1, sn1_endId, sn1_endId, "STTN")
        self.logger.warning("sn2节点接收交易完成的confirm")
        sn2_tx_confirm = self.waitNodeReceiveMessage(sn2, sn2_st_msg["grpHdr"]["msgId"], "CMPT")
        sn2_endId = sn2_st_msg["cdtTrfTxInf"]["pmtId"]["endToEndId"]
        caseObj.checkConfirmMessage(sn2_tx_confirm, "CMPT", sn2_st_msg["grpHdr"]["msgId"], "RCSR", sn2, sn2_endId, sn2_endId, "STTN")

        finish_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='TRANSACTION_FINISH'"
        ApiUtils.waitCondition(self.mysql.exec_sql_query, (finish_sql,), lambda x: len(x) > 0, 60, 5)
        time.sleep(35)
        self.logger.warning("交易完成后，查询交易状态")
        caseObj.getAndcheckTransactionStatus(sn1, api_key, sec_key, sn1_st_msg["grpHdr"]["msgId"], sn1, "CMPT")
        if not isInnerNode:
            caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_st_msg["grpHdr"]["msgId"], sn2, "CMPT")

        self.logger.warning("追踪交易flow")
        flow_info, req_msg = self.step_queryTransactionFlow(pn1, self.api_key, self.sec_key, msg_id, pn1, returnReqMsg=True)
        caseObj.checkTransactionFlowInDB(flow_info["data"], req_msg)
        if self.check_db:
            order_amt = float(sn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"])
            self.checkRTSAmountWhenFinish(rmn_tx_id, order_amt, sn_fees[1])
            # finish_amt = float(sn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"]) - sn_fees[1]
        return sn2_tx_info

    def transactionFlow_pn_sn_sn_pn(self, pn1, sn1, sn2, pn2, cdtTrfTxInf, sn_fees, caseObj, isInnerNode=False, isRPP=False, rateInfo=None, chg_fees=None):
        """
        PN -> SN -> SN -> PN 场景的主流程:
            pn1节点提交交易请求
            pn1节点收到交易confirm
            sn1节点收到交易请求
            sn1节点发送交易confirm
            sn1节点提交结算表单
            sn1节点收到结算confirm
            sn2节点收到交易请求
            sn2节点发送交易confirm
            sn2节点提交结算请求
            sn2节点等待结算confirm
            pn2节点收到交易请求
            pn2节点发送交易confirm
            sn1节点和sn2节点接收交易完成的confirm
        """
        api_key, sec_key = self.api_key, self.sec_key
        service_fee = self.getServiceFee(cdtTrfTxInf)
        rmn_id = "risn2roxe51"
        self.logger.warning("pn1节点提交交易请求")
        msg_id = self.make_msg_id()
        tx_headers = self.make_header(pn1, api_key, "RCCT", msg_id)
        tx_group_header = self.make_group_header(pn1, rmn_id, msg_id)
        tx_info, tx_msg = self.submit_transaction(sec_key, tx_headers, tx_group_header, cdtTrfTxInf)

        rmn_tx_id = tx_info["data"]["txId"]
        self.checkCodeAndMessage(tx_info)
        caseObj.assertEqual(tx_info["data"]["stsId"], "RCVD")
        caseObj.checkTransactionMessageInDB(rmn_tx_id, tx_msg)
        end2end_id = cdtTrfTxInf["pmtId"]["endToEndId"]

        self.logger.warning("pn1节点收到交易confirm")
        sn_tx_confirm = self.waitNodeReceiveMessage(pn1, msg_id, None, msg_id, api_key, sec_key, "ACCEPTED_CONF_SENT")
        caseObj.checkConfirmMessage(sn_tx_confirm, "ACPT", msg_id, "RCCT", pn1, end2end_id, end2end_id, "TXNS")
        caseObj.getAndcheckTransactionStatus(pn1, api_key, sec_key, msg_id, pn1, "ACPT")

        self.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, pn1, msg_id, api_key, sec_key, "DEBIT_TXN_SENT")
        if not self.check_db:
            sn1_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"] = tx_msg["cdtTrfTxInf"]["intrBkSttlmAmt"]
            sn1_tx_info["cdtTrfTxInf"]["dbtrAcct"] = tx_msg["cdtTrfTxInf"]["dbtrAcct"]
            sn1_tx_info["cdtTrfTxInf"]["cdtrAcct"] = tx_msg["cdtTrfTxInf"]["cdtrAcct"]
        # else:
        #     caseObj.checkTransactionMessageWithNextNode(tx_msg, sn1_tx_info)
        caseObj.checkNodeReceivedTransactionMessage(rmn_tx_id, sn1_tx_info, sn1, [pn1], [])  # rpp保持原来参数即可

        self.logger.warning("sn1节点发送confirm消息")
        self.step_sendRTPC(sn1, api_key, sec_key, sn1_tx_info)
        time.sleep(3)

        self.logger.warning("sn1节点查询交易状态")
        caseObj.getAndcheckTransactionStatus(sn1, api_key, sec_key, sn1_tx_info["grpHdr"]["msgId"], sn1_tx_info["grpHdr"]["instgAgt"], "ACPT")

        sn1_st_msg = self.step_sendRCSR(sn1, api_key, sec_key, sn1_tx_info, rmn_tx_id, "CRDT", self, sn_fees[0])
        if isInnerNode:
            time.sleep(180)
            caseObj.getAndcheckTransactionStatus(sn1, api_key, sec_key, sn1_st_msg["grpHdr"]["msgId"], sn1, "CMPT")
            return
        self.logger.warning("sn2节点收到交易请求")
        sn2_tx_info = self.waitReceiveTransactionMessage(rmn_tx_id, sn2, sn1_tx_info["grpHdr"]["msgId"], pn1, msg_id, api_key, sec_key, "CREDIT_SN_TXN_SENT")  # sn1_st_msg, api_key, sec_key, "CREDIT_SN_TXN_SENT"
        if not self.check_db:
            sn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"] = sn1_st_msg["cdtTrfTxInf"]["intrBkSttlmAmt"]
            sn2_tx_info["cdtTrfTxInf"]["dbtrAcct"] = tx_msg["cdtTrfTxInf"]["dbtrAcct"]
            sn2_tx_info["cdtTrfTxInf"]["cdtrAcct"] = tx_msg["cdtTrfTxInf"]["cdtrAcct"]
        caseObj.checkNodeReceivedTransactionMessage(rmn_tx_id, sn2_tx_info, sn2, [pn1, sn1], [sn_fees[0]], isRPP, rateInfo, chg_fees, service_fee=service_fee)
        if isRPP:
            caseObj.checkChainInfoOfRPPInRTS(rmn_tx_id, sn1_st_msg, service_fee)

        caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_tx_info["grpHdr"]["msgId"], sn2_tx_info["grpHdr"]["instgAgt"], "STDB")

        self.logger.warning("sn2节点发送confirm消息")
        self.step_sendRTPC(sn2, api_key, sec_key, sn2_tx_info)
        # stsRsnInf = {"addtlInf": "Beneficiary information error", "stsRsnCd": "00600120"}
        # self.step_sendRTPC(sn2, api_key, sec_key, sn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)
        # return
        time.sleep(1)
        caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_tx_info["grpHdr"]["msgId"], sn2_tx_info["grpHdr"]["instgAgt"], "STDB")

        sn2_st_msg = self.step_sendRCSR(sn2, api_key, sec_key, sn2_tx_info, rmn_tx_id, "DBIT", self, nodeLoc="SN2")

        self.logger.warning("sn2节点查询交易状态")
        caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_tx_info["grpHdr"]["msgId"], sn2_tx_info["grpHdr"]["instgAgt"], ["STDB", "STCD"])

        self.logger.warning("pn2节点接收rcct消息")
        pn2_tx_info = self.waitReceiveTransactionMessage(rmn_tx_id, pn2, msg_id, pn1, msg_id, api_key, sec_key, "CREDIT_PN_TXN_SENT")
        caseObj.checkNodeReceivedTransactionMessage(rmn_tx_id, pn2_tx_info, pn2, [pn1, sn1, sn2], sn_fees, isRPP, rateInfo, chg_fees, service_fee=service_fee)
        # pn2_msg_id = pn2_tx_info["grpHdr"]["msgId"] if RMNData.is_check_db else pn2_tx_info["msgId"]

        self.logger.warning("pn2节点查询交易状态")
        caseObj.getAndcheckTransactionStatus(pn2, api_key, sec_key, pn2_tx_info["grpHdr"]["msgId"], pn2_tx_info["grpHdr"]["instgAgt"], ["STCD", "STLD"])

        self.logger.warning("pn2节点发送confirm消息")
        pn2_msg = self.step_sendRTPC(pn2, api_key, sec_key, pn2_tx_info)
        # stsRsnInf = {"addtlInf": "Beneficiary information error", "stsRsnCd": "00600120"}
        # self.step_sendRTPC(pn2, api_key, sec_key, pn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)
        # return
        time.sleep(3)

        self.logger.warning("sn1节点接收交易完成的confirm")
        sn1_tx_confirm = self.waitNodeReceiveMessage(sn1, sn1_st_msg["grpHdr"]["msgId"], "CMPT", sn1_tx_info["grpHdr"]["msgId"], api_key, sec_key, "DEBIT_SN_NOTICE_SENT", rmn_id)
        sn1_endId = sn1_st_msg["cdtTrfTxInf"]["pmtId"]["endToEndId"]
        caseObj.checkConfirmMessage(sn1_tx_confirm, "CMPT", sn1_st_msg["grpHdr"]["msgId"], "RCSR", sn1, sn1_endId, sn1_endId, "STTN")
        self.logger.warning("sn2节点接收交易完成的confirm")
        sn2_tx_confirm = self.waitNodeReceiveMessage(sn2, sn2_st_msg["grpHdr"]["msgId"], "CMPT", sn2_tx_info["grpHdr"]["msgId"], api_key, sec_key, "CREDIT_SN_NOTICE_SENT", rmn_id)
        sn2_endId = sn2_st_msg["cdtTrfTxInf"]["pmtId"]["endToEndId"]
        caseObj.checkConfirmMessage(sn2_tx_confirm, "CMPT", sn2_st_msg["grpHdr"]["msgId"], "RCSR", sn2, sn2_endId, sn2_endId, "STTN")
        if self.check_db:
            self.checkSNSMsgOrPNSMsg(rmn_tx_id, "TO_PNS", "RTPC", pn2_msg)
            finish_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='TRANSACTION_FINISH'"
            ApiUtils.waitCondition(self.mysql.exec_sql_query, (finish_sql,), lambda x: len(x) > 0, 60, 5)
        else:
            ApiUtils.waitCondition(
                self.step_queryTransactionState, (pn1, api_key, sec_key, msg_id, pn1,),
                lambda func_res: func_res["data"]["rptOrErr"]["pmt"]["sts"] == "CMPT", 180, 15
            )
        time.sleep(35)
        self.logger.warning("交易完成后，查询交易状态")
        caseObj.getAndcheckTransactionStatus(sn1, api_key, sec_key, sn1_st_msg["grpHdr"]["msgId"], sn1, "CMPT")
        caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_st_msg["grpHdr"]["msgId"], sn2, "CMPT")

        self.logger.warning("追踪交易flow")
        flow_info, req_msg = self.step_queryTransactionFlow(pn1, self.api_key, self.sec_key, msg_id, pn1, returnReqMsg=True)
        caseObj.checkTransactionFlowInDB(flow_info["data"], req_msg)
        if self.check_db:
            order_amt = float(pn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"])
            b_type = self.matchBusinessTypeByCdtTrfTxInf(cdtTrfTxInf)
            pn2_fee = self.getNodeFeeInDB(pn2, pn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["ccy"], order_amt, b_type)["out"]
            self.checkRTSAmountWhenFinish(rmn_tx_id, order_amt, sn_fees[1], "PN", pn2_fee)
        return pn2_tx_info

    def returnFlow_sn_sn(self, sn1, sn2, txInf, sn_fees, caseObj, isRPP=False, rateInfo=None, chg_fees=None):
        rmn_id = "risn2roxe51"
        self.logger.warning(f"原SN2: {sn1}节点提交return请求")
        service_fee = self.getServiceFee(txInf)
        tx_info, tx_msg = self.step_nodeSendRPRN(sn1, rmn_id, txInf)
        msg_id = tx_msg["grpHdr"]["msgId"]
        rmn_tx_id = tx_info["data"]["txId"]
        time.sleep(2)
        caseObj.checkTransactionMessageInDB(rmn_tx_id, tx_msg)

        sn_tx_confirm = self.waitNodeReceiveMessage(sn1, msg_id)
        caseObj.checkConfirmMessage(sn_tx_confirm, "ACPT", msg_id, "RPRN", sn1, "", "", "TXNS")
        caseObj.getAndcheckTransactionStatus(sn1, self.api_key, self.sec_key, msg_id, sn1, "ACPT")
        self.checkOldTransactionInDB(rmn_tx_id, "TRANSACTION_RETURN")
        # self.getChainAccountBalance()
        old_rcct_msg_id = txInf["orgnlGrpInf"]["orgnlMsgId"]
        old_rcct_instgAgt = txInf["instgAgt"]
        caseObj.getAndcheckTransactionStatus(sn1, self.api_key, self.sec_key, old_rcct_msg_id, old_rcct_instgAgt, "RTND")

        sn1_st_msg = self.step_sendRCSR(sn1, self.api_key, self.sec_key, tx_msg, rmn_tx_id, "CRDT", self, nodeLoc="原SN2")
        # self.getChainAccountBalance()
        self.logger.warning(f"原SN1: {sn2}节点收到return报文")
        sn2_tx_info = self.waitReceiveTransactionMessage(rmn_tx_id, sn2, sn_tx_confirm["grpHdr"]["msgId"], is_return=True)
        caseObj.checkNodeReceivedReturnMessage(rmn_tx_id, sn2_tx_info, sn2, [sn1], [sn_fees[0]], isRPP, rateInfo, chg_fees, node_role="DEBIT_SN", service_fee=service_fee)
        if isRPP: caseObj.checkChainInfoOfRPPInRTS(rmn_tx_id, sn1_st_msg)
        # self.getChainAccountBalance()
        sn2_rcct_msg_id = sn2_tx_info["grpHdr"]["msgId"] if self.check_db else sn2_tx_info["msgId"]
        caseObj.getAndcheckTransactionStatus(sn2, self.api_key, self.sec_key, sn2_rcct_msg_id, rmn_id, "STDB")

        self.logger.warning(f"原SN1: {sn2}节点发送confirm消息")
        self.step_sendRTPC(sn2, self.api_key, self.sec_key, sn2_tx_info)
        time.sleep(1)
        caseObj.getAndcheckTransactionStatus(sn2, self.api_key, self.sec_key, sn2_rcct_msg_id, rmn_id, "STDB")

        sn2_st_msg = self.step_sendRCSR(sn2, self.api_key, self.sec_key, sn2_tx_info, rmn_tx_id, "DBIT", self, nodeLoc="原SN1")
        # self.getChainAccountBalance()
        self.logger.warning(f"原SN2: {sn1}节点接收交易完成的confirm")
        sn1_st_msg_id = sn1_st_msg["grpHdr"]["msgId"]
        sn1_endId = sn1_st_msg["cdtTrfTxInf"]["pmtId"]["endToEndId"]
        sn1_tx_confirm = self.waitNodeReceiveMessage(sn1, sn1_st_msg_id, "CMPT")
        caseObj.checkConfirmMessage(sn1_tx_confirm, "CMPT", sn1_st_msg_id, "RCSR", sn1, sn1_endId, sn1_endId, "STTN")

        self.logger.warning(f"原SN1: {sn2}节点接收交易完成的confirm")
        sn2_st_msg_id = sn2_st_msg["grpHdr"]["msgId"]
        sn2_endId = sn2_st_msg["cdtTrfTxInf"]["pmtId"]["endToEndId"]
        sn2_tx_confirm = self.waitNodeReceiveMessage(sn2, sn2_st_msg_id, "CMPT")
        caseObj.checkConfirmMessage(sn2_tx_confirm, "CMPT", sn2_st_msg_id, "RCSR", sn2, sn2_endId, sn2_endId, "STTN")
        time.sleep(10)

        self.logger.warning("交易完成后，查询交易状态")
        caseObj.getAndcheckTransactionStatus(sn1, self.api_key, self.sec_key, sn1_st_msg_id, sn1, "CMPT")
        caseObj.getAndcheckTransactionStatus(sn2, self.api_key, self.sec_key, sn2_st_msg_id, sn2, "CMPT")

        self.logger.warning("追踪交易flow")
        flow_info, req_msg = self.step_queryTransactionFlow(sn1, self.api_key, self.sec_key, msg_id, sn1, returnReqMsg=True)
        caseObj.checkTransactionFlowInDB(flow_info["data"], req_msg)

    def returnFlow_sn_sn_pn(self, sn1, sn2, pn2, txInf, sn_fees, caseObj, isRPP=False, rateInfo=None, chg_fees=None):
        rmn_id = "risn2roxe51"
        service_fee = self.getServiceFee(txInf)
        self.logger.warning(f"原SN2: {sn1}节点提交return请求")
        tx_info, tx_msg = self.step_nodeSendRPRN(sn1, rmn_id, txInf)
        msg_id = tx_msg["grpHdr"]["msgId"]
        rmn_tx_id = tx_info["data"]["txId"]
        caseObj.checkTransactionMessageInDB(rmn_tx_id, tx_msg)

        sn_tx_confirm = self.waitNodeReceiveMessage(sn1, msg_id)
        caseObj.checkConfirmMessage(sn_tx_confirm, "ACPT", msg_id, "RPRN", sn1, "", "", "TXNS")
        caseObj.getAndcheckTransactionStatus(sn1, self.api_key, self.sec_key, msg_id, sn1, "ACPT")
        self.checkOldTransactionInDB(rmn_tx_id, "TRANSACTION_RETURN")
        old_rcct_msg_id = txInf["orgnlGrpInf"]["orgnlMsgId"]
        old_rcct_instgAgt = txInf["instgAgt"]
        caseObj.getAndcheckTransactionStatus(sn1, self.api_key, self.sec_key, old_rcct_msg_id, old_rcct_instgAgt, "RTND")

        sn1_st_msg = self.step_sendRCSR(sn1, self.api_key, self.sec_key, tx_msg, rmn_tx_id, "CRDT", self, nodeLoc="原SN2")
        self.logger.warning(f"原SN1: {sn2}节点收到return报文")
        sn2_tx_info = self.waitReceiveTransactionMessage(rmn_tx_id, sn2, is_return=True)
        caseObj.checkNodeReceivedReturnMessage(rmn_tx_id, sn2_tx_info, sn2, [sn1], [sn_fees[0]], isRPP, rateInfo, chg_fees, node_role="DEBIT_SN", service_fee=service_fee)
        if isRPP: caseObj.checkChainInfoOfRPPInRTS(rmn_tx_id, sn1_st_msg)
        sn2_rcct_msg_id = sn2_tx_info["grpHdr"]["msgId"] if self.check_db else sn2_tx_info["msgId"]
        caseObj.getAndcheckTransactionStatus(sn2, self.api_key, self.sec_key, sn2_rcct_msg_id, rmn_id, "STDB")

        self.logger.warning(f"原SN1: {sn2}节点发送confirm消息")
        self.step_sendRTPC(sn2, self.api_key, self.sec_key, sn2_tx_info)
        time.sleep(1)
        caseObj.getAndcheckTransactionStatus(sn2, self.api_key, self.sec_key, sn2_rcct_msg_id, rmn_id, "STDB")

        sn2_st_msg = self.step_sendRCSR(sn2, self.api_key, self.sec_key, sn2_tx_info, rmn_tx_id, "DBIT", self, nodeLoc="原SN1")

        self.logger.warning(f"原PN1: {pn2}节点等待收到return请求")
        pn2_tx_info = self.waitReceiveTransactionMessage(rmn_tx_id, pn2, is_return=True)
        # sn1_tx_msg_id = pn2_tx_info["grpHdr"]["msgId"]
        caseObj.checkNodeReceivedReturnMessage(rmn_tx_id, pn2_tx_info, pn2, [sn1, sn2], sn_fees, isRPP, rateInfo, chg_fees, service_fee=service_fee)
        self.step_sendRTPC(pn2, self.api_key, self.sec_key, pn2_tx_info)

        self.logger.warning(f"原SN2: {sn1}节点接收交易完成的confirm")
        sn1_st_msg_id = sn1_st_msg["grpHdr"]["msgId"]
        sn1_endId = sn1_st_msg["cdtTrfTxInf"]["pmtId"]["endToEndId"]
        sn1_tx_confirm = self.waitNodeReceiveMessage(sn1, sn1_st_msg_id, "CMPT")
        caseObj.checkConfirmMessage(sn1_tx_confirm, "CMPT", sn1_st_msg_id, "RCSR", sn1, sn1_endId, sn1_endId, "STTN")

        self.logger.warning(f"原SN1: {sn2}节点接收交易完成的confirm")
        sn2_st_msg_id = sn2_st_msg["grpHdr"]["msgId"]
        sn2_endId = sn2_st_msg["cdtTrfTxInf"]["pmtId"]["endToEndId"]
        sn2_tx_confirm = self.waitNodeReceiveMessage(sn2, sn2_st_msg_id, "CMPT")
        caseObj.checkConfirmMessage(sn2_tx_confirm, "CMPT", sn2_st_msg_id, "RCSR", sn2, sn2_endId, sn2_endId, "STTN")
        time.sleep(10)

        self.logger.warning("交易完成后，查询交易状态")
        caseObj.getAndcheckTransactionStatus(sn1, self.api_key, self.sec_key, sn1_st_msg_id, sn1, "CMPT")
        caseObj.getAndcheckTransactionStatus(sn2, self.api_key, self.sec_key, sn2_st_msg_id, sn2, "CMPT")

        self.logger.warning("追踪交易flow")
        flow_info, req_msg = self.step_queryTransactionFlow(sn1, self.api_key, self.sec_key, msg_id, sn1, returnReqMsg=True)
        caseObj.checkTransactionFlowInDB(flow_info["data"], req_msg)

    def returnFlow_pn_sn_sn(self, pn1, sn1, sn2, txInf, sn_fees, caseObj, isInnerNode=False, isRPP=False, rateInfo=None, chg_fees=None):
        rmn_id = "risn2roxe51"
        service_fee = self.getServiceFee(txInf)
        self.logger.warning(f"原PN2: {pn1}节点提交return请求")
        tx_info, tx_msg = self.step_nodeSendRPRN(pn1, rmn_id, txInf)
        msg_id = tx_msg["grpHdr"]["msgId"]
        rmn_tx_id = tx_info["data"]["txId"]
        caseObj.checkTransactionMessageInDB(rmn_tx_id, tx_msg)

        pn_tx_confirm = self.waitNodeReceiveMessage(pn1, msg_id, None)
        caseObj.checkConfirmMessage(pn_tx_confirm, "ACPT", msg_id, "RPRN", pn1, "", "", "TXNS")
        caseObj.getAndcheckTransactionStatus(pn1, self.api_key, self.sec_key, msg_id, pn1, "ACPT")
        self.checkOldTransactionInDB(rmn_tx_id, "TRANSACTION_RETURN")
        old_rcct_msg_id = txInf["orgnlGrpInf"]["orgnlMsgId"]
        old_rcct_instgAgt = txInf["instgAgt"]
        caseObj.getAndcheckTransactionStatus(pn1, self.api_key, self.sec_key, old_rcct_msg_id, old_rcct_instgAgt, "RTND")
        # sn1接收return报文并发送RTPC
        self.logger.warning(f"原SN2: {sn1}节点等待收到return请求")
        sn1_tx_info = self.waitReceiveTransactionMessage(rmn_tx_id, sn1, is_return=True)
        sn1_tx_msg_id = sn1_tx_info["grpHdr"]["msgId"]
        caseObj.checkNodeReceivedReturnMessage(rmn_tx_id, sn1_tx_info, sn1, [pn1], [], node_role="CREDIT_SN")
        self.step_sendRTPC(sn1, self.api_key, self.sec_key, sn1_tx_info)
        caseObj.getAndcheckTransactionStatus(sn1, self.api_key, self.sec_key, sn1_tx_msg_id, sn1_tx_info["grpHdr"]["instgAgt"], "ACPT")

        sn1_st_msg = self.step_sendRCSR(sn1, self.api_key, self.sec_key, sn1_tx_info, rmn_tx_id, "CRDT", self, sn_fees[0], nodeLoc="原SN2")
        if isInnerNode:
            ApiUtils.waitCondition(
                self.step_queryTransactionState, (sn1, self.api_key, self.sec_key, sn1_st_msg["grpHdr"]["msgId"], sn1,),
                lambda func_res: func_res["data"]["rptOrErr"]["pmt"]["sts"] == "CMPT", 120, 15
            )
            caseObj.getAndcheckTransactionStatus(sn1, self.api_key, self.sec_key, msg_id, sn1, "CMPT")
            self.logger.warning("追踪交易flow")
            ts_headers = self.make_header(sn1, self.api_key, "RATQ")
            msg_header = self.make_msg_header(sn1, ts_headers["msgId"])
            txQryDef = self.make_RTSQ_information(msg_id, sn1, ntryTp="ADT")
            flow_info, req_msg = self.get_transaction_flow(self.sec_key, ts_headers, msg_header, txQryDef)
            caseObj.checkTransactionFlowInDB(flow_info["data"], req_msg)
            return
        self.logger.warning(f"原SN1: {sn2}节点等待收到return请求")
        sn2_tx_info = self.waitReceiveTransactionMessage(rmn_tx_id, sn2, sn1_tx_msg_id, is_return=True)
        caseObj.checkNodeReceivedReturnMessage(rmn_tx_id, sn2_tx_info, sn2, [pn1, sn1], [sn_fees[0]], isRPP, rateInfo, chg_fees, node_role="DEBIT_SN", service_fee=service_fee)
        if isRPP: caseObj.checkChainInfoOfRPPInRTS(rmn_tx_id, sn1_st_msg)
        sn2_tx_msg_id = sn2_tx_info["grpHdr"]["msgId"] if self.check_db else sn2_tx_info["msgId"]
        self.step_sendRTPC(sn2, self.api_key, self.sec_key, sn2_tx_info)
        time.sleep(1)
        caseObj.getAndcheckTransactionStatus(sn2, self.api_key, self.sec_key, sn2_tx_msg_id, rmn_id, "STDB")

        sn2_st_msg = self.step_sendRCSR(sn2, self.api_key, self.sec_key, sn2_tx_info, rmn_tx_id, "DBIT", self, nodeLoc="原SN1")

        self.logger.warning("sn1节点接收交易完成的confirm")
        sn1_st_msg_id = sn1_st_msg["grpHdr"]["msgId"]
        sn1_endId = sn1_st_msg["cdtTrfTxInf"]["pmtId"]["endToEndId"]
        sn1_tx_confirm = self.waitNodeReceiveMessage(sn1, sn1_st_msg_id, "CMPT", msg_id, self.api_key, self.sec_key, "DEBIT_SN_NOTICE_SENT")
        caseObj.checkConfirmMessage(sn1_tx_confirm, "CMPT", sn1_st_msg_id, "RCSR", sn1, sn1_endId, sn1_endId, "STTN")
        self.logger.warning("sn2节点接收交易完成的confirm")
        sn2_st_msg_id = sn2_st_msg["grpHdr"]["msgId"]
        sn2_endId = sn2_st_msg["cdtTrfTxInf"]["pmtId"]["endToEndId"]
        sn2_tx_confirm = self.waitNodeReceiveMessage(sn2, sn2_st_msg_id, "CMPT", sn2_st_msg_id, self.api_key, self.sec_key, "CREDIT_SN_NOTICE_SENT")
        caseObj.checkConfirmMessage(sn2_tx_confirm, "CMPT", sn2_st_msg_id, "RCSR", sn2, sn2_endId, sn2_endId, "STTN")
        time.sleep(10)

        self.logger.warning("交易完成后，查询交易状态")
        caseObj.getAndcheckTransactionStatus(sn1, self.api_key, self.sec_key, sn1_st_msg_id, sn1, "CMPT")
        caseObj.getAndcheckTransactionStatus(sn2, self.api_key, self.sec_key, sn2_st_msg_id, sn2, "CMPT")

        self.logger.warning("追踪交易flow")
        flow_info, req_msg = self.step_queryTransactionFlow(pn1, self.api_key, self.sec_key, msg_id, pn1, returnReqMsg=True)
        caseObj.checkTransactionFlowInDB(flow_info["data"], req_msg)

    def returnFlow_pn_sn_sn_pn(self, pn1, sn1, sn2, pn2, txInf, sn_fees, caseObj, isInnerNode=False, isRPP=False, rateInfo=None, chg_fees=None):
        rmn_id = "risn2roxe51"
        service_fee = self.getServiceFee(txInf)
        self.logger.warning(f"原PN2: {pn1}节点提交return请求")
        tx_info, tx_msg = self.step_nodeSendRPRN(pn1, rmn_id, txInf)
        msg_id = tx_msg["grpHdr"]["msgId"]
        rmn_tx_id = tx_info["data"]["txId"]
        caseObj.checkTransactionMessageInDB(rmn_tx_id, tx_msg)

        pn_tx_confirm = self.waitNodeReceiveMessage(pn1, msg_id, None)
        caseObj.checkConfirmMessage(pn_tx_confirm, "ACPT", msg_id, "RPRN", pn1, "", "", "TXNS")
        caseObj.getAndcheckTransactionStatus(pn1, self.api_key, self.sec_key, msg_id, pn1, "ACPT")
        self.checkOldTransactionInDB(rmn_tx_id, "TRANSACTION_RETURN")
        old_rcct_msg_id = txInf["orgnlGrpInf"]["orgnlMsgId"]
        old_rcct_instgAgt = txInf["instgAgt"]
        caseObj.getAndcheckTransactionStatus(pn1, self.api_key, self.sec_key, old_rcct_msg_id, old_rcct_instgAgt, "RTND")
        # sn1接收return报文并发送RTPC
        self.logger.warning(f"原SN2: {sn1}节点等待收到return请求")
        sn1_tx_info = self.waitReceiveTransactionMessage(rmn_tx_id, sn1, is_return=True)
        sn1_tx_msg_id = sn1_tx_info["grpHdr"]["msgId"]
        b_type = self.matchBusinessTypeByCdtTrfTxInf(txInf)
        pn1_return_fee = self.getNodeFeeInDB(pn1, txInf["rtrdIntrBkSttlmAmt"]["ccy"], float(txInf["rtrdInstdAmt"]["amt"]), b_type, True)["in"]
        fee_nodes = [pn1] if pn1_return_fee > 0 else []
        caseObj.checkNodeReceivedReturnMessage(rmn_tx_id, sn1_tx_info, sn1, fee_nodes, [], node_role="CREDIT_SN")
        self.step_sendRTPC(sn1, self.api_key, self.sec_key, sn1_tx_info)
        caseObj.getAndcheckTransactionStatus(sn1, self.api_key, self.sec_key, sn1_tx_msg_id, sn1_tx_info["grpHdr"]["instgAgt"], "ACPT")

        sn1_st_msg = self.step_sendRCSR(sn1, self.api_key, self.sec_key, sn1_tx_info, rmn_tx_id, "CRDT", self, sn_fees[0], nodeLoc="原SN2")
        if isInnerNode:
            ApiUtils.waitCondition(
                self.step_queryTransactionState, (sn1, self.api_key, self.sec_key, sn1_st_msg["grpHdr"]["msgId"], sn1,),
                lambda func_res: func_res["data"]["rptOrErr"]["pmt"]["sts"] == "CMPT", 120, 15
            )
            caseObj.getAndcheckTransactionStatus(sn1, self.api_key, self.sec_key, msg_id, sn1, "CMPT")
            self.logger.warning("追踪交易flow")
            ts_headers = self.make_header(sn1, self.api_key, "RATQ")
            msg_header = self.make_msg_header(sn1, ts_headers["msgId"])
            txQryDef = self.make_RTSQ_information(msg_id, sn1, ntryTp="ADT")
            flow_info, req_msg = self.get_transaction_flow(self.sec_key, ts_headers, msg_header, txQryDef)
            caseObj.checkTransactionFlowInDB(flow_info["data"], req_msg)
            return
        self.logger.warning(f"原SN1: {sn2}节点等待收到return请求")
        sn2_tx_info = self.waitReceiveTransactionMessage(rmn_tx_id, sn2, sn1_tx_msg_id, is_return=True)
        snFees = []
        if sn_fees[0] > 0:
            fee_nodes.append(sn1)
            snFees.append(sn_fees[0])
        caseObj.checkNodeReceivedReturnMessage(rmn_tx_id, sn2_tx_info, sn2, fee_nodes, snFees, isRPP, rateInfo, chg_fees, node_role="DEBIT_SN", service_fee=service_fee)
        if isRPP: caseObj.checkChainInfoOfRPPInRTS(rmn_tx_id, sn1_st_msg)
        sn2_tx_msg_id = sn2_tx_info["grpHdr"]["msgId"] if self.check_db else sn2_tx_info["msgId"]
        self.step_sendRTPC(sn2, self.api_key, self.sec_key, sn2_tx_info)
        time.sleep(1)
        caseObj.getAndcheckTransactionStatus(sn2, self.api_key, self.sec_key, sn2_tx_msg_id, rmn_id, "STDB")

        sn2_st_msg = self.step_sendRCSR(sn2, self.api_key, self.sec_key, sn2_tx_info, rmn_tx_id, "DBIT", self, nodeLoc="原SN1")

        self.logger.warning(f"原PN1: {pn2}节点等待收到return请求")
        pn2_tx_info = self.waitReceiveTransactionMessage(rmn_tx_id, pn2, is_return=True)
        # sn1_tx_msg_id = pn2_tx_info["grpHdr"]["msgId"]
        if sn_fees[1] > 0:
            fee_nodes.append(sn2)
            snFees.append(sn_fees[1])
        caseObj.checkNodeReceivedReturnMessage(rmn_tx_id, pn2_tx_info, pn2, fee_nodes, snFees, isRPP, rateInfo, chg_fees, service_fee=service_fee)
        self.step_sendRTPC(pn2, self.api_key, self.sec_key, pn2_tx_info)

        self.logger.warning("sn1节点接收交易完成的confirm")
        sn1_st_msg_id = sn1_st_msg["grpHdr"]["msgId"]
        sn1_endId = sn1_st_msg["cdtTrfTxInf"]["pmtId"]["endToEndId"]
        sn1_tx_confirm = self.waitNodeReceiveMessage(sn1, sn1_st_msg_id, "CMPT", msg_id, self.api_key, self.sec_key, "DEBIT_SN_NOTICE_SENT")
        caseObj.checkConfirmMessage(sn1_tx_confirm, "CMPT", sn1_st_msg_id, "RCSR", sn1, sn1_endId, sn1_endId, "STTN")
        self.logger.warning("sn2节点接收交易完成的confirm")
        sn2_st_msg_id = sn2_st_msg["grpHdr"]["msgId"]
        sn2_endId = sn2_st_msg["cdtTrfTxInf"]["pmtId"]["endToEndId"]
        sn2_tx_confirm = self.waitNodeReceiveMessage(sn2, sn2_st_msg_id, "CMPT", sn2_st_msg_id, self.api_key, self.sec_key, "CREDIT_SN_NOTICE_SENT")
        caseObj.checkConfirmMessage(sn2_tx_confirm, "CMPT", sn2_st_msg_id, "RCSR", sn2, sn2_endId, sn2_endId, "STTN")
        time.sleep(10)

        self.logger.warning("交易完成后，查询交易状态")
        caseObj.getAndcheckTransactionStatus(sn1, self.api_key, self.sec_key, sn1_st_msg_id, sn1, "CMPT")
        caseObj.getAndcheckTransactionStatus(sn2, self.api_key, self.sec_key, sn2_st_msg_id, sn2, "CMPT")

        self.logger.warning("追踪交易flow")
        flow_info, req_msg = self.step_queryTransactionFlow(pn1, self.api_key, self.sec_key, msg_id, pn1, returnReqMsg=True)
        caseObj.checkTransactionFlowInDB(flow_info["data"], req_msg)

    def returnFlowForPartiallySettled(self, sn1, txInf, old_msg_id, caseObj, isRPP=False, rateInfo=None, chg_fees=None, old_pn1=None, sn1_return_fee=None):
        """
        对于未完全结算的处于pending状态的交易，RMN可以介入发起退款
        """
        rmn_id = "risn2roxe51"
        service_fee = self.getServiceFee(txInf)
        self.logger.warning(f"手动向原SN1: {sn1}节点提交return请求")
        tx_info, tx_msg = self.step_rmnSendRPRN(rmn_id, txInf)
        rmn_tx_id = tx_info["data"]["txId"]
        caseObj.checkTransactionMessageInDB(rmn_tx_id, tx_msg)

        self.logger.warning(f"原SN1: {sn1}节点收到return报文")
        sn1_tx_info = self.waitReceiveTransactionMessage(rmn_tx_id, sn1, is_return=True)
        caseObj.checkNodeReceivedReturnMessage(rmn_tx_id, sn1_tx_info, sn1, [], [], isRPP, rateInfo, chg_fees, service_fee=service_fee)
        sn1_tx_msg_id = sn1_tx_info["grpHdr"]["msgId"]
        caseObj.getAndcheckTransactionStatus(sn1, self.api_key, self.sec_key, sn1_tx_msg_id, rmn_id, "STDB")
        self.checkOldTransactionInDB(rmn_tx_id, "TRANSACTION_RETURN", isHalf=True)
        old_msg_sender = rmn_id if old_pn1 else sn1
        caseObj.getAndcheckTransactionStatus(sn1, self.api_key, self.sec_key, old_msg_id, old_msg_sender, "RTND")
        self.logger.warning(f"原SN1: {sn1}节点发送confirm消息")
        self.step_sendRTPC(sn1, self.api_key, self.sec_key, sn1_tx_info)
        time.sleep(1)
        caseObj.getAndcheckTransactionStatus(sn1, self.api_key, self.sec_key, sn1_tx_msg_id, rmn_id, "STDB")

        sn1_st_msg = self.step_sendRCSR(sn1, self.api_key, self.sec_key, sn1_tx_info, rmn_tx_id, "DBIT", self, nodeLoc="原SN1")

        # 如果原交易有pn1节点发起，则半结算的return要向原pn1节点发送消息
        if old_pn1:
            self.logger.warning(f"原PN1: {old_pn1}节点等待收到return请求")
            pn2_tx_info = self.waitReceiveTransactionMessage(rmn_tx_id, old_pn1, is_return=True)
            caseObj.checkNodeReceivedReturnMessage(rmn_tx_id, pn2_tx_info, old_pn1, [sn1], [sn1_return_fee], isHalf=True, service_fee=service_fee)
            self.step_sendRTPC(old_pn1, self.api_key, self.sec_key, pn2_tx_info)

        self.logger.warning("sn1节点接收交易完成的confirm")
        sn1_st_msg_id = sn1_st_msg["grpHdr"]["msgId"]
        sn1_endId = sn1_st_msg["cdtTrfTxInf"]["pmtId"]["endToEndId"]
        sn1_tx_confirm = self.waitNodeReceiveMessage(sn1, sn1_st_msg_id, "CMPT", sn1_tx_msg_id, self.api_key, self.sec_key, "DEBIT_SN_NOTICE_SENT")
        caseObj.checkConfirmMessage(sn1_tx_confirm, "CMPT", sn1_st_msg_id, "RCSR", sn1, sn1_endId, sn1_endId, "STTN")

        time.sleep(10)

        self.logger.warning("交易完成后，查询交易状态")
        caseObj.getAndcheckTransactionStatus(sn1, self.api_key, self.sec_key, sn1_st_msg_id, sn1, "CMPT")

        self.logger.warning("追踪交易flow")
        flow_info, req_msg = self.step_queryTransactionFlow(sn1, self.api_key, self.sec_key, sn1_st_msg_id, sn1, returnReqMsg=True)
        caseObj.checkTransactionFlowInDB(flow_info["data"], req_msg, is_rmn_send=True)

    def transactionFlow_sn_sn_Channel(self, sn1, sn2, cdtTrfTxInf, sn_fees, caseObj, isInnerNode=False, isRPP=False, rateInfo=None, chg_fees=None):
        rmn_id = "risn2roxe51"
        api_key, sec_key = self.api_key, self.sec_key
        rmn_id = "risn2roxe51"
        service_fee = self.getServiceFee(cdtTrfTxInf)
        self.logger.warning("sn1节点提交交易请求")
        msg_id = self.make_msg_id()
        tx_headers = self.make_header(sn1, api_key, "RCCT", msg_id)
        tx_group_header = self.make_group_header(sn1, rmn_id, msg_id)
        tx_info, tx_msg = self.submit_transaction(sec_key, tx_headers, tx_group_header, cdtTrfTxInf)

        self.checkCodeAndMessage(tx_info)
        caseObj.assertEqual(tx_info["data"]["stsId"], "RCVD")
        rmn_tx_id = tx_info["data"]["txId"]
        end2end_id = cdtTrfTxInf["pmtId"]["endToEndId"]
        caseObj.checkTransactionMessageInDB(rmn_tx_id, tx_msg)

        self.logger.warning("sn1节点收到交易confirm")
        sn_tx_confirm = self.waitNodeReceiveMessage(sn1, msg_id, None, msg_id, api_key, sec_key, "ACCEPTED_CONF_SENT")
        caseObj.checkConfirmMessage(sn_tx_confirm, "ACPT", msg_id, "RCCT", sn1, end2end_id, end2end_id, "TXNS")

        caseObj.getAndcheckTransactionStatus(sn1, api_key, sec_key, msg_id, sn1, "ACPT")

        self.logger.warning("sn1节点提交结算请求并等待接收confirm消息")
        self.step_sendRCSR(sn1, api_key, sec_key, tx_msg, rmn_tx_id, "CRDT", self)
        if isInnerNode:
            ApiUtils.waitCondition(
                self.mysql.exec_sql_query,
                (f"select * from `roxe_rmn`.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='CREDIT_STTL_RECEIVED'", ),
                lambda x: len(x) > 0, 180, 15
            )
        self.logger.warning("查询rpc订单状态")
        rmn_sql = self.mysql.exec_sql_query(f"select * from `roxe_rmn`.rmn_transaction where rmn_txn_id like '%{rmn_tx_id}%'")
        rts_id = rmn_sql[0]["rtsTxnId"]
        reference_id = rts_id + "_sn2"
        c_time = time.time()
        while time.time() - c_time < 300:
            rpc_sql = self.mysql.exec_sql_query(f"select * from `roxe_rpc`.rpc_pay_order where reference_id like '%{reference_id}%'")
            if len(rpc_sql) > 0:
                trs_sql = "select AES_DECRYPT(UNHEX(order_other_fields), 'ers_434_sdwer234') from `roxe_rpc`.rpc_pay_order where id='{}'".format(rpc_sql[0]["id"])
                if rpc_sql[0]["orderState"] == 0:
                    continue
                elif rpc_sql[0]["orderState"] == 1 or rpc_sql[0]["orderState"] == 2:
                    self.logger.warning(f"订单已成功提交至通道方:{rpc_sql[0]['resultData']}")
                    rpc_order = self.mysql.exec_sql_query(trs_sql)
                    self.logger.warning(f"下单信息：{rpc_order}")
                    return
                elif rpc_sql[0]["orderState"] == 3:
                    self.logger.warning(f"订单处理完成返回失败:{rpc_sql[0]['resultData']}")
                    rpc_order = self.mysql.exec_sql_query(trs_sql)
                    self.logger.warning(f"下单信息：{rpc_order}")
                    return
                elif rpc_sql[0]["orderState"] == 5:
                    result = rpc_sql[0]["resultData"]
                    if ":" in result:
                        res = result.split(":")[-1]
                    else:
                        res = result
                    self.logger.warning(f"订单提交失败: {res}")
                    rpc_order = self.mysql.exec_sql_query(trs_sql)
                    self.logger.warning(f"下单信息：{rpc_order}")
                    return res
            time.sleep(10)
        # assert rpc_sql[0]["orderState"] == 1 or rpc_sql[0]["orderState"] == 2
        try:
            assert rpc_sql[0]["orderState"] == 1 or rpc_sql[0]["orderState"] == 2
        except (AssertionError, IndexError) as x:
            self.logger.warning(x)
            self.logger.warning("订单未提交成功")
        else:
            self.logger.warning("订单已成功提交至通道方")

    def transactionFlow_sn_sn_not_check_db_1(self, sn1, sn2, cdtTrfTxInf, sn_fees, caseObj, isInnerNode=False):
        rmn_id = "risn2roxe51"
        api_key, sec_key = self.api_key, self.sec_key
        self.logger.warning("sn1节点提交交易请求")
        msg_id = self.make_msg_id()
        tx_headers = self.make_header(sn1, api_key, "RCCT", msg_id)
        tx_group_header = self.make_group_header(sn1, rmn_id, msg_id)
        tx_info, tx_msg = self.submit_transaction(sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        rmn_tx_id = tx_info["data"]["txId"]
        end2end_id = cdtTrfTxInf["pmtId"]["endToEndId"]
        self.logger.warning("等待接收消息")
        time.sleep(10)
        self.logger.warning("查询交易状态")
        ts_headers = self.make_header(sn1, api_key, "RTSQ")
        msg_header = self.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.make_RTSQ_information(msg_id, sn1, txId=None, endToEndId=None, instrId=None, instdPty=None, msgTp=None)
        time.sleep(3)
        q_info, q_msg = self.get_transaction_status(sec_key, ts_headers, msg_header, txQryDef)
        if q_info["data"]["rptOrErr"]["pmt"]["sts"] == "ACPT":
            self.logger.warning("sn1节点提交结算请求")
            tx_msg["msgId"] = tx_msg["grpHdr"]["msgId"]
            tx_msg["msgType"] = "RCCT"
            st_msg = self.step_sendRCSR(sn1, api_key, sec_key, tx_msg, rmn_tx_id, "CRDT", caseObj, nodeLoc="SN1")
            # return
            # st_headers = self.make_header(sn1, api_key, "RCSR")
            # st_grpHder = self.make_group_header(sn1, "risn2roxe51", st_headers["msgId"])
            # st_cdtInf = self.make_RCSR_information(tx_msg, "CRDT", sn1)
            # st_info, st_msg = self.submit_settlement(sec_key, st_headers, st_grpHder, st_cdtInf)
            # self.checkCodeAndMessage(st_info)
            # assert st_info["data"]["stsId"] == "RCVD"
            # assert st_info["data"]["txId"] == rmn_tx_id
            if isInnerNode:
                ApiUtils.waitCondition(
                    self.step_queryTransactionState, (sn1, api_key, sec_key, msg_id, sn1,),
                    lambda func_res: func_res["data"]["rptOrErr"]["pmt"]["sts"] == "CMPT", 180, 25
                )
                self.logger.warning("sn1节点接收交易完成的confirm")
                time.sleep(10)
                self.logger.warning("追踪交易flow")
                ts_headers = self.make_header(sn1, api_key, "RATQ")
                msg_header = self.make_msg_header(sn1, ts_headers["msgId"])
                txQryDef = self.make_RTSQ_information(msg_id, sn1, ntryTp="ADT")
                flow_info, req_msg = self.get_transaction_flow(sec_key, ts_headers, msg_header, txQryDef)

            return msg_id, tx_msg, end2end_id, rmn_tx_id, st_msg

        else:
            self.logger.warning("交易未接受，状态不正确")

    def transactionFlow_sn_sn_not_check_db_2(self, sn1, sn2, rmn_id, api_key, sec_key, msg_id, tx_msg, end2end_id, tx2_msg, rmn_tx_id, sn2_tx_msg_id):
        self.logger.warning("sn2节点收到交易请求")
        # time.sleep(5)
        self.logger.warning("查询交易状态")
        q_info = self.step_queryTransactionState(sn1, api_key, sec_key, msg_id, sn1)
        # print(q_info["data"]["rptOrErr"]["pmt"]["sts"])
        if q_info["data"]["rptOrErr"]["pmt"]["sts"] == "STDB":
            self.logger.warning("发送confirm消息")
            # self.step_sendRTPC(sn2, api_key, sec_key, sn2_tx_info)
            p_msg = {
                "orgnlGrpInfAndSts": {
                    "orgnlMsgId": sn2_tx_msg_id,
                    "orgnlMsgNmId": "RCCT"
                },
                "txInfAndSts": {
                    "stsId": "ACPT",
                    "orgnlInstrId": "",
                    "orgnlEndToEndId": end2end_id,
                    "orgnlTxId": rmn_tx_id,
                    "stsRsnInf": None,
                    "acctSvcrRef": "TXNS",
                    "instgAgt": rmn_id
                }
            }
            # p_msg["txInfAndSts"]["stsRsnInf"] = {"addtlInf": "Beneficiary information error", "stsRsnCd": "00600120"}
            pc_msg_id = self.make_msg_id()
            pc_headers = self.make_header(sn2, api_key, "RTPC", pc_msg_id)
            pc_group_header = self.make_group_header(sn2, "risn2roxe51", pc_msg_id, hasSttlmInf=False)
            # p_msg = self.make_RTPC_information(sn2_tx_info, "ACPT")
            pc_info, pc_msg = self.proc_confirm(sec_key, pc_headers, pc_group_header, p_msg)
            self.checkCodeAndMessage(pc_info)
            self.logger.warning("查询交易状态")
            # caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_tx_msg_id, rmn_id, "STDB")
            q_info = self.step_queryTransactionState(sn2, api_key, sec_key, sn2_tx_msg_id, rmn_id)
            if q_info["data"]["rptOrErr"]["pmt"]["sts"] == "STDB":
                self.logger.warning("sn2节点提交结算请求")
                st_headers = self.make_header(sn2, api_key, "RCSR")
                st_grpHder = self.make_group_header(sn2, rmn_id, st_headers["msgId"])
                # st_cdtInf = self.client.make_RCSR_information(rcctMsg, "DBIT", sn2)
                st_cdtInf = {
                    "intrBkSttlmAmt": tx2_msg["cdtTrfTxInf"]["intrBkSttlmAmt"].copy(),
                    "intrBkSttlmDt": datetime.datetime.now().strftime(self.iso_date_format),
                    "pmtId": {"endToEndId": end2end_id, "txId": end2end_id},
                    "dbtr": self.make_roxe_agent(rmn_id, "VN"),
                    "dbtrAcct": tx_msg["cdtTrfTxInf"]["dbtrAcct"],
                    "cdtr": self.make_roxe_agent(sn2, "SN"),
                    "cdtrAcct": tx_msg["cdtTrfTxInf"]["cdtrAcct"],
                    "rmtInf": {"orgnlMsgID": sn2_tx_msg_id, "orgnlMsgTp": "RCCT", "instgAgt": rmn_id},
                    "splmtryData": {"envlp": {"ustrd": {"cdtDbtInd": "DBIT"}}}
                }
                st_info, sn2_st_msg = self.submit_settlement(sec_key, st_headers, st_grpHder, st_cdtInf)
                self.checkCodeAndMessage(st_info)
                assert st_info["data"]["stsId"] == "RCVD"
                assert st_info["data"]["txId"] == rmn_tx_id
                self.logger.warning("等待节点接收消息")
                time.sleep(100)
                self.logger.warning("交易完成后，查询交易状态")
                q_info_1 = self.step_queryTransactionState(sn1, api_key, sec_key, msg_id, sn1)
                q_info_2 = self.step_queryTransactionState(sn2, api_key, sec_key, sn2_tx_msg_id, rmn_id)
                if q_info_1["data"]["rptOrErr"]["pmt"]["sts"] == "CMPT" and q_info_2["data"]["rptOrErr"]["pmt"][
                    "sts"] == "CMPT":
                    self.logger.warning("交易完成")
                    self.logger.warning("追踪交易flow")
                    self.step_queryTransactionFlow(sn1, self.api_key, self.sec_key, msg_id, sn1, returnReqMsg=True)
                else:
                    self.logger.warning("交易未完成")
            else:
                self.logger.warning("交易未完成，停留在STDB之前")
        else:
            self.logger.warning("交易未完成，停留在STDB之前")

    def returnFlow_sn_sn_not_check_db_1(self, sn1, sn2, txInf):
        rmn_id = "risn2roxe51"
        api_key, sec_key = self.api_key, self.sec_key
        self.logger.warning(f"原SN2: {sn1}节点提交return请求")
        tx_info, tx_msg = self.step_nodeSendRPRN(sn1, rmn_id, txInf)
        msg_id = tx_msg["grpHdr"]["msgId"]
        rmn_tx_id = tx_info["data"]["txId"]
        self.logger.warning("等待接收消息")
        time.sleep(30)
        self.logger.warning("查询交易状态")
        ts_headers = self.make_header(sn1, api_key, "RTSQ")
        msg_header = self.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.make_RTSQ_information(msg_id, sn1, txId=None, endToEndId=None, instrId=None, instdPty=None, msgTp=None)

        q_info, q_msg = self.get_transaction_status(sec_key, ts_headers, msg_header, txQryDef)
        if q_info["data"]["rptOrErr"]["pmt"]["sts"] == "ACPT":
            self.logger.warning("sn1节点提交结算请求")
            st_headers = self.make_header(sn1, api_key, "RCSR")
            st_grpHder = self.make_group_header(sn1, "risn2roxe51", st_headers["msgId"])
            st_cdtInf = self.make_RCSR_information(tx_msg, "CRDT", sn1)
            st_info, st_msg = self.submit_settlement(sec_key, st_headers, st_grpHder, st_cdtInf)
            self.checkCodeAndMessage(st_info)
            assert st_info["data"]["stsId"] == "RCVD"
            assert st_info["data"]["txId"] == rmn_tx_id
            sn1_st_msg_id = st_msg["grpHdr"]["msgId"]

            return msg_id, tx_msg, rmn_tx_id, sn1_st_msg_id

        else:
            self.logger.warning("交易未接受，状态不正确")

    def returnFlow_sn_sn_not_check_db_2(self, sn1, sn2, msg_id, sn2_tx_info, rmn_tx_id, sn1_st_msg_id, caseObj):
        api_key, sec_key = self.api_key, self.sec_key
        rmn_id = "risn2roxe51"
        self.logger.warning(f"原SN1: {sn2}节点收到return报文")
        self.logger.warning("查询交易状态")
        q_info = self.step_queryTransactionState(sn1, api_key, sec_key, msg_id, sn1)
        if q_info["data"]["rptOrErr"]["pmt"]["sts"] == "STDB":
            self.logger.warning(f"原SN1: {sn2}节点发送confirm消息")
            self.step_sendRTPC(sn2, self.api_key, self.sec_key, sn2_tx_info)
            time.sleep(10)
            self.logger.warning("查询交易状态")
            # pc_msg_id = sn2_tx_info["grpHdr"]["msgId"]
            # q_info = self.step_queryTransactionState(sn2, api_key, sec_key, pc_msg_id, sn2)
            sn2_rcct_msg_id = sn2_tx_info["grpHdr"]["msgId"]
            caseObj.getAndcheckTransactionStatus(sn2, self.api_key, self.sec_key, sn2_rcct_msg_id, rmn_id, "STDB")
            if q_info["data"]["rptOrErr"]["pmt"]["sts"] == "STDB":
                self.logger.warning("sn2节点提交结算请求")
                # self.logger.warning("sn2节点提交结算请求")
                # st_headers = self.make_header(sn2, api_key, "RCSR")
                # st_grpHder = self.make_group_header(sn2, rmn_id, st_headers["msgId"])
                # # st_cdtInf = self.client.make_RCSR_information(rcctMsg, "DBIT", sn2)
                # st_cdtInf = {
                #     "intrBkSttlmAmt": st_msg["cdtTrfTxInf"]["intrBkSttlmAmt"].copy(),
                #     "intrBkSttlmDt": datetime.datetime.now().strftime(self.iso_date_format),
                #     "pmtId": {"endToEndId": end2end_id, "txId": end2end_id},
                #     "dbtr": self.make_roxe_agent(rmn_id, "VN"),
                #     "dbtrAcct": tx_msg["cdtTrfTxInf"]["dbtrAcct"],
                #     "cdtr": self.make_roxe_agent(sn2, "SN"),
                #     "cdtrAcct": tx_msg["cdtTrfTxInf"]["cdtrAcct"],
                #     "rmtInf": {"orgnlMsgID": sn2_tx_msg_id, "orgnlMsgTp": "RCCT", "instgAgt": rmn_id},
                #     "splmtryData": {"envlp": {"ustrd": {"cdtDbtInd": "DBIT"}}}
                # }
                # st_info, sn2_st_msg = self.submit_settlement(sec_key, st_headers, st_grpHder, st_cdtInf)
                st_headers = self.make_header(sn2, api_key, "RCSR")
                st_grpHder = self.make_group_header(sn2, rmn_id, st_headers["msgId"])
                st_cdtInf = self.make_RCSR_information(sn2_tx_info, "DBIT", sn2)

                st_info, st_msg = self.submit_settlement(sec_key, st_headers, st_grpHder, st_cdtInf)
                self.checkCodeAndMessage(st_info)
                assert st_info["data"]["stsId"] == "RCVD"
                assert st_info["data"]["txId"] == rmn_tx_id
                self.logger.warning("等待节点接收消息")
                time.sleep(120)
                self.logger.warning("交易完成后，查询交易状态")
                sn2_st_msg_id = st_msg["grpHdr"]["msgId"]
                caseObj.getAndcheckTransactionStatus(sn1, self.api_key, self.sec_key, sn1_st_msg_id, sn1, "CMPT")
                caseObj.getAndcheckTransactionStatus(sn2, self.api_key, self.sec_key, sn2_st_msg_id, sn2, "CMPT")
                self.logger.warning("交易完成")
                self.logger.warning("追踪交易flow")
                self.step_queryTransactionFlow(sn1, self.api_key, self.sec_key, msg_id, sn1, returnReqMsg=True)
                # if q_info_1["data"]["rptOrErr"]["pmt"]["sts"] == "CMPT":  # and q_info_2["data"]["rptOrErr"]["pmt"]["sts"] == "CMPT"
                #     self.logger.warning("交易完成")
                #     self.logger.warning("追踪交易flow")
                #     self.step_queryTransactionFlow(sn1, self.api_key, self.sec_key, msg_id, sn1, returnReqMsg=True)
                # else:
                #     self.logger.warning("交易未完成")
            else:
                self.logger.warning("交易未完成，停留在STDB之前")
        else:
            self.logger.warning("交易未完成，停留在STDB之前")

    def transactionFlow_sn_sn_sn1IsRTSNode(self, rmn_tx_id, sn1, sn2, cdtTrfTxInf, sn_fees, caseObj, isRPP=False, rateInfo=None, chg_fees=None):
        rmn_id = "risn2roxe51"
        api_key, sec_key = self.api_key, self.sec_key
        service_fee = self.getServiceFee(cdtTrfTxInf)
        self.logger.warning("sn2节点收到交易请求")
        sn2_tx_info = self.waitReceiveTransactionMessage(rmn_tx_id, sn2)
        caseObj.checkNodeReceivedTransactionMessage(rmn_tx_id, sn2_tx_info, sn2, [sn1], [sn_fees[0]], isRPP, rateInfo, chg_fees, fromRTS=True, service_fee=service_fee)
        caseObj.checkRtsMsgTransferRMN(sn2_tx_info, cdtTrfTxInf)
        # if isRPP:
        #     caseObj.checkChainInfoOfRPPInRTS(rmn_tx_id, sn1_st_msg)
        sn2_tx_msg_id = sn2_tx_info["grpHdr"]["msgId"] if self.check_db else sn2_tx_info["msgId"]
        caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_tx_msg_id, rmn_id, "STDB", fromRTS=True)
        self.step_sendRTPC(sn2, api_key, sec_key, sn2_tx_info)
        time.sleep(1)
        caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_tx_msg_id, rmn_id, "STDB", fromRTS=True)

        sn2_st_msg = self.step_sendRCSR(sn2, api_key, sec_key, sn2_tx_info, rmn_tx_id, "DBIT", self, nodeLoc="SN2")

        self.logger.warning("sn2节点接收交易完成的confirm")
        sn2_st_msg_id = sn2_st_msg["grpHdr"]["msgId"]
        sn2_endId = sn2_st_msg["cdtTrfTxInf"]["pmtId"]["endToEndId"]
        sn2_tx_confirm = self.waitNodeReceiveMessage(sn2, sn2_st_msg_id, "CMPT", sn2_st_msg_id, api_key, sec_key,
                                                     "CREDIT_SN_NOTICE_SENT")
        caseObj.checkConfirmMessage(sn2_tx_confirm, "CMPT", sn2_st_msg_id, "RCSR", sn2, sn2_endId, sn2_endId, "STTN")
        finish_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='TRANSACTION_FINISH'"
        ApiUtils.waitCondition(self.mysql.exec_sql_query, (finish_sql,), lambda x: len(x) > 0, 60, 5)

        self.logger.warning("交易完成后，查询交易状态")
        caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_st_msg_id, sn2, "CMPT", fromRTS=True)

        self.logger.warning("追踪交易flow")
        flow_info, req_msg = self.step_queryTransactionFlow(sn2, self.api_key, self.sec_key, sn2_st_msg_id, sn2, returnReqMsg=True)
        caseObj.checkTransactionFlowInDB(flow_info["data"], req_msg)
        if self.check_db:
            order_amt = float(sn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"])
            self.checkRTSAmountWhenFinish(rmn_tx_id, order_amt, sn_fees[1])
        return sn2_tx_info

    def transactionFlow_sn_sn_pn_sn1IsRTSNode(self, rmn_tx_id, sn1, sn2, pn2, cdtTrfTxInf, sn_fees, caseObj, isRPP=False, rateInfo=None, chg_fees=None):
        rmn_id = "risn2roxe51"
        api_key, sec_key = self.api_key, self.sec_key
        service_fee = self.getServiceFee(cdtTrfTxInf)
        self.logger.warning("sn2节点收到交易请求")
        sn2_tx_info = self.waitReceiveTransactionMessage(rmn_tx_id, sn2)
        # todo
        caseObj.checkNodeReceivedTransactionMessage(
            rmn_tx_id, sn2_tx_info, sn2, [sn1], [sn_fees[0]], isRPP, rateInfo, chg_fees, fromRTS=True, service_fee=service_fee
        )
        caseObj.checkRtsMsgTransferRMN(sn2_tx_info, cdtTrfTxInf)
        # if isRPP:
        #     caseObj.checkChainInfoOfRPPInRTS(rmn_tx_id, sn1_st_msg)
        sn2_tx_msg_id = sn2_tx_info["grpHdr"]["msgId"] if self.check_db else sn2_tx_info["msgId"]
        caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_tx_msg_id, rmn_id, "STDB", fromRTS=True)
        self.step_sendRTPC(sn2, api_key, sec_key, sn2_tx_info)
        time.sleep(1)
        caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_tx_msg_id, rmn_id, "STDB", fromRTS=True)

        sn2_st_msg = self.step_sendRCSR(sn2, api_key, sec_key, sn2_tx_info, rmn_tx_id, "DBIT", self, nodeLoc="SN2")

        self.logger.warning("pn2节点收到交易请求")
        pn2_tx_info = self.waitReceiveTransactionMessage(rmn_tx_id, pn2)
        self.step_sendRTPC(pn2, api_key, sec_key, pn2_tx_info)

        self.logger.warning("sn2节点接收交易完成的confirm")
        sn2_st_msg_id = sn2_st_msg["grpHdr"]["msgId"]
        sn2_endId = sn2_st_msg["cdtTrfTxInf"]["pmtId"]["endToEndId"]
        sn2_tx_confirm = self.waitNodeReceiveMessage(sn2, sn2_st_msg_id, "CMPT")
        caseObj.checkConfirmMessage(sn2_tx_confirm, "CMPT", sn2_st_msg_id, "RCSR", sn2, sn2_endId, sn2_endId, "STTN")
        finish_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='TRANSACTION_FINISH'"
        ApiUtils.waitCondition(self.mysql.exec_sql_query, (finish_sql,), lambda x: len(x) > 0, 60, 5)

        self.logger.warning("交易完成后，查询交易状态")
        caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_st_msg_id, sn2, "CMPT", fromRTS=True)

        self.logger.warning("追踪交易flow")
        flow_info, req_msg = self.step_queryTransactionFlow(sn2, self.api_key, self.sec_key, sn2_st_msg_id, sn2,
                                                            returnReqMsg=True)
        caseObj.checkTransactionFlowInDB(flow_info["data"], req_msg)
        if self.check_db:
            order_amt = float(pn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"])
            pn2_fee = self.getTransactionFeeInDB(pn2, pn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["ccy"], "out", "PN")
            self.checkRTSAmountWhenFinish(rmn_tx_id, order_amt, sn_fees[1], "PN", pn2_fee)
        return sn2_tx_info

    def transactionFlow_pn_sn_sn_pn1IsRTSNode(self, rmn_tx_id, pn1, sn1, sn2, cdtTrfTxInf, sn_fees, caseObj, isRPP=False, rateInfo=None, chg_fees=None):
        rmn_id = "risn2roxe51"
        api_key, sec_key = self.api_key, self.sec_key
        service_fee = self.getServiceFee(cdtTrfTxInf)
        sn1_tx_info = self.waitReceiveTransactionMessage(rmn_tx_id, sn1)
        caseObj.checkNodeReceivedTransactionMessage(rmn_tx_id, sn1_tx_info, sn1, [pn1], [], fromRTS=True, service_fee=service_fee)
        caseObj.checkRtsMsgTransferRMN(sn1_tx_info, cdtTrfTxInf)
        self.logger.warning("sn1节点发送confirm消息")
        self.step_sendRTPC(sn1, api_key, sec_key, sn1_tx_info)
        time.sleep(3)
        self.logger.warning("sn1节点查询交易状态")
        caseObj.getAndcheckTransactionStatus(sn1, api_key, sec_key, sn1_tx_info["grpHdr"]["msgId"], rmn_id, "ACPT", fromRTS=True)

        sn1_st_msg = self.step_sendRCSR(sn1, api_key, sec_key, sn1_tx_info, rmn_tx_id, "CRDT", self, sn_fees[0])

        self.logger.warning("sn2节点收到交易请求")
        sn2_tx_info = self.waitReceiveTransactionMessage(rmn_tx_id, sn2)
        caseObj.checkNodeReceivedTransactionMessage(rmn_tx_id, sn2_tx_info, sn2, [sn1], [sn_fees[0]], isRPP, rateInfo, chg_fees, fromRTS=True, service_fee=service_fee)
        # if isRPP:
        #     caseObj.checkChainInfoOfRPPInRTS(rmn_tx_id, sn1_st_msg)
        sn2_tx_msg_id = sn2_tx_info["grpHdr"]["msgId"] if self.check_db else sn2_tx_info["msgId"]
        caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_tx_msg_id, rmn_id, "STDB", fromRTS=True)
        self.step_sendRTPC(sn2, api_key, sec_key, sn2_tx_info)
        time.sleep(1)
        caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_tx_msg_id, rmn_id, "STDB", fromRTS=True)

        sn2_st_msg = self.step_sendRCSR(sn2, api_key, sec_key, sn2_tx_info, rmn_tx_id, "DBIT", self, nodeLoc="SN2")

        self.logger.warning("sn1节点接收交易完成的confirm")
        sn1_st_msg_id = sn1_st_msg["grpHdr"]["msgId"]
        sn1_tx_confirm = self.waitNodeReceiveMessage(sn1, sn1_st_msg_id, "CMPT")
        sn1_endId = sn1_st_msg["cdtTrfTxInf"]["pmtId"]["endToEndId"]
        caseObj.checkConfirmMessage(sn1_tx_confirm, "CMPT", sn1_st_msg_id, "RCSR", sn1, sn1_endId, sn1_endId, "STTN")

        self.logger.warning("sn2节点接收交易完成的confirm")
        sn2_st_msg_id = sn2_st_msg["grpHdr"]["msgId"]
        sn2_endId = sn2_st_msg["cdtTrfTxInf"]["pmtId"]["endToEndId"]
        sn2_tx_confirm = self.waitNodeReceiveMessage(sn2, sn2_st_msg_id, "CMPT")
        caseObj.checkConfirmMessage(sn2_tx_confirm, "CMPT", sn2_st_msg_id, "RCSR", sn2, sn2_endId, sn2_endId, "STTN")
        finish_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='TRANSACTION_FINISH'"
        ApiUtils.waitCondition(self.mysql.exec_sql_query, (finish_sql,), lambda x: len(x) > 0, 60, 5)

        self.logger.warning("交易完成后，查询交易状态")
        caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_st_msg_id, sn2, "CMPT", fromRTS=True)

        self.logger.warning("追踪交易flow")
        flow_info, req_msg = self.step_queryTransactionFlow(sn2, self.api_key, self.sec_key, sn2_st_msg_id, sn2, returnReqMsg=True)
        caseObj.checkTransactionFlowInDB(flow_info["data"], req_msg)
        if self.check_db:
            order_amt = float(sn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"])
            self.checkRTSAmountWhenFinish(rmn_tx_id, order_amt, sn_fees[1])
        return sn2_tx_info

    def transactionFlow_pn_sn_sn_pn_pn1IsRTSNode(self, rmn_tx_id, pn1, sn1, sn2, pn2, cdtTrfTxInf, sn_fees, caseObj, isRPP=False, rateInfo=None, chg_fees=None):
        """
        PN -> SN -> SN -> PN 场景的主流程:
            pn1节点提交交易请求
            pn1节点收到交易confirm
            sn1节点收到交易请求
            sn1节点发送交易confirm
            sn1节点提交结算表单
            sn1节点收到结算confirm
            sn2节点收到交易请求
            sn2节点发送交易confirm
            sn2节点提交结算请求
            sn2节点等待结算confirm
            pn2节点收到交易请求
            pn2节点发送交易confirm
            sn1节点和sn2节点接收交易完成的confirm
        """
        api_key, sec_key = self.api_key, self.sec_key
        service_fee = self.getServiceFee(cdtTrfTxInf)
        self.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.waitReceiveTransactionMessage(rmn_tx_id, sn1, None)
        caseObj.checkNodeReceivedTransactionMessage(rmn_tx_id, sn1_tx_info, sn1, [pn1], [], fromRTS=True, service_fee=service_fee)  # rpp保持原来参数即可
        caseObj.checkRtsMsgTransferRMN(sn1_tx_info, cdtTrfTxInf)
        self.logger.warning("sn1节点发送confirm消息")
        self.step_sendRTPC(sn1, api_key, sec_key, sn1_tx_info)
        time.sleep(3)

        self.logger.warning("sn1节点查询交易状态")
        caseObj.getAndcheckTransactionStatus(
            sn1, api_key, sec_key, sn1_tx_info["grpHdr"]["msgId"], sn1_tx_info["grpHdr"]["instgAgt"], "ACPT",
            fromRTS=True
        )
        sn1_st_msg = self.step_sendRCSR(sn1, api_key, sec_key, sn1_tx_info, rmn_tx_id, "CRDT", self, sn_fees[0])
        self.logger.warning("sn2节点收到交易请求")
        sn2_tx_info = self.waitReceiveTransactionMessage(rmn_tx_id, sn2, sn1_tx_info["grpHdr"]["msgId"])  # sn1_st_msg, api_key, sec_key, "CREDIT_SN_TXN_SENT"
        if not self.check_db:
            sn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"] = sn1_st_msg["cdtTrfTxInf"]["intrBkSttlmAmt"]
            sn2_tx_info["cdtTrfTxInf"]["cdtrAcct"] = sn1_tx_info["cdtTrfTxInf"]["cdtrAcct"]
        caseObj.checkNodeReceivedTransactionMessage(rmn_tx_id, sn2_tx_info, sn2, [pn1, sn1], [sn_fees[0]], isRPP, rateInfo, chg_fees, service_fee=service_fee)
        if isRPP:
            caseObj.checkChainInfoOfRPPInRTS(rmn_tx_id, sn1_st_msg)

        caseObj.getAndcheckTransactionStatus(
            sn2, api_key, sec_key, sn2_tx_info["grpHdr"]["msgId"], sn2_tx_info["grpHdr"]["instgAgt"], "STDB", fromRTS=True
        )

        self.logger.warning("sn2节点发送confirm消息")
        self.step_sendRTPC(sn2, api_key, sec_key, sn2_tx_info)
        time.sleep(1)
        caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_tx_info["grpHdr"]["msgId"], sn2_tx_info["grpHdr"]["instgAgt"], "STDB")

        sn2_st_msg = self.step_sendRCSR(sn2, api_key, sec_key, sn2_tx_info, rmn_tx_id, "DBIT", self, nodeLoc="SN2")

        self.logger.warning("sn2节点查询交易状态")
        caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_tx_info["grpHdr"]["msgId"], sn2_tx_info["grpHdr"]["instgAgt"], "STCD")

        self.logger.warning("pn2节点接收rcct消息")
        pn2_tx_info = self.waitReceiveTransactionMessage(rmn_tx_id, pn2)
        caseObj.checkNodeReceivedTransactionMessage(rmn_tx_id, pn2_tx_info, pn2, [pn1, sn1, sn2], sn_fees, isRPP, rateInfo, chg_fees, service_fee=service_fee)
        # pn2_msg_id = pn2_tx_info["grpHdr"]["msgId"] if RMNData.is_check_db else pn2_tx_info["msgId"]

        self.logger.warning("pn2节点查询交易状态")
        caseObj.getAndcheckTransactionStatus(pn2, api_key, sec_key, pn2_tx_info["grpHdr"]["msgId"], pn2_tx_info["grpHdr"]["instgAgt"], ["STCD", "STLD"])

        self.logger.warning("pn2节点发送confirm消息")
        pn2_msg = self.step_sendRTPC(pn2, api_key, sec_key, pn2_tx_info)
        # stsRsnInf = {"addtlInf": "Beneficiary information error", "stsRsnCd": "00600120"}
        # self.step_sendRTPC(pn2, api_key, sec_key, pn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)
        # return
        time.sleep(1)

        self.logger.warning("sn1节点接收交易完成的confirm")
        sn1_tx_confirm = self.waitNodeReceiveMessage(sn1, sn1_st_msg["grpHdr"]["msgId"], "CMPT")
        sn1_endId = sn1_st_msg["cdtTrfTxInf"]["pmtId"]["endToEndId"]
        caseObj.checkConfirmMessage(sn1_tx_confirm, "CMPT", sn1_st_msg["grpHdr"]["msgId"], "RCSR", sn1, sn1_endId, sn1_endId, "STTN")
        self.logger.warning("sn2节点接收交易完成的confirm")
        sn2_tx_confirm = self.waitNodeReceiveMessage(sn2, sn2_st_msg["grpHdr"]["msgId"], "CMPT")
        sn2_endId = sn2_st_msg["cdtTrfTxInf"]["pmtId"]["endToEndId"]
        caseObj.checkConfirmMessage(sn2_tx_confirm, "CMPT", sn2_st_msg["grpHdr"]["msgId"], "RCSR", sn2, sn2_endId, sn2_endId, "STTN")
        if self.check_db:
            self.checkSNSMsgOrPNSMsg(rmn_tx_id, "TO_PNS", "RTPC", pn2_msg)
            finish_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='TRANSACTION_FINISH'"
            ApiUtils.waitCondition(self.mysql.exec_sql_query, (finish_sql,), lambda x: len(x) > 0, 60, 5)
        else:
            ApiUtils.waitCondition(
                self.step_queryTransactionState, (sn1, api_key, sec_key, sn1_st_msg["grpHdr"]["msgId"], sn1,),
                lambda func_res: func_res["data"]["rptOrErr"]["pmt"]["sts"] == "CMPT", 180, 15
            )

        self.logger.warning("交易完成后，查询交易状态")
        caseObj.getAndcheckTransactionStatus(sn1, api_key, sec_key, sn1_st_msg["grpHdr"]["msgId"], sn1, "CMPT")
        caseObj.getAndcheckTransactionStatus(sn2, api_key, sec_key, sn2_st_msg["grpHdr"]["msgId"], sn2, "CMPT")

        self.logger.warning("追踪交易flow")
        flow_info, req_msg = self.step_queryTransactionFlow(sn1, self.api_key, self.sec_key, sn1_st_msg["grpHdr"]["msgId"], sn1, returnReqMsg=True)
        caseObj.checkTransactionFlowInDB(flow_info["data"], req_msg)
        if self.check_db:
            order_amt = float(pn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"])
            pn2_fee = self.getTransactionFeeInDB(pn2, pn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["ccy"], "out", "PN")
            self.checkRTSAmountWhenFinish(rmn_tx_id, order_amt, sn_fees[1], "PN", pn2_fee)
        return pn2_tx_info


if __name__ == "__main__":
    logging.basicConfig()
    my_logger = logging.getLogger("rmn")
    my_logger.setLevel(logging.DEBUG)
    Global.setValue(settings.logger_name, my_logger.name)
    api = "qMJiJZG84SGYBf3SG9bUjfco0se3WJzL"
    sec = "8kqN7WwehNyltmfylxj8fJXNiNPRDXZH"
    # Global.setValue(settings.enable_trace, True)
    t_client = RMNApiClient("https://sandbox-risn.roxe.pro/api/rmn/v2", 'test', api, sec)
    # t_client = RMNApiClient("http://roxe-rmn-bj-test.roxepro.top:38888/api/rmn/v2", 'test', api, sec)
    # t_client = RMNApiClient("http://rmn-uat.roxepro.top:38888/api/rmn/v2", 'test', api, sec)

    # t_client.get_exchange_rate(sn1, api_key, sec_key, "USD", "23.45", "USD")
    sn1_agent = {"finInstnId": {"othr": {"id": "fape1meh4bsz", "schmeCd": "ROXE", "issr": "SN"}}}
    pn1_agent = {"finInstnId": {"othr": {"id": "pn.us.usd", "schmeCd": "ROXE", "issr": "PN"}}}
    pn2_agent = {"finInstnId": {"othr": {"id": "pn.gb.usd", "schmeCd": "ROXE", "issr": "PN"}}}
    us_bic_info = {"finInstnId": {"bicFI": "BOFAUS3DAU2", "nm": "rich bank"}}
    us_ncc_info = {"finInstnId": {"clrSysMmbId": {"clrSysCd": "USABA", "mmbId": "12345678901"}, "nm": "rich bank"}}
    # t_client.get_router_list(sn1, api_key, sec_key, "USD", "USD", '55', "", cdtrAgt=sn1_agent)
    # t_client.get_router_list("pn.us.usd", api_key, sec_key, "USD", "USD", '55', "", cdtrAgt=pn2_agent)

    # ts_headers = t_client.make_header("fape1meh4bsz", api_key, "RTSQ")
    # msg_header = t_client.make_msg_header("fape1meh4bsz", ts_headers["msgId"])
    # txQryDef = t_client.make_RTSQ_information("0202203284432947317744818", "risn2roxe51")
    # q_info, q_msg = t_client.get_transaction_status(sec_key, ts_headers, msg_header, txQryDef)
    # flows = t_client.step_queryTransactionFlow("fape1meh4bsz", api, sec, "0202207181658111041062113", "fape1meh4bsz")
    # for f_info in flows["data"]["rptOrErr"]["splmtryData"]:
    #     my_logger.info(f_info)
    # t_client.getSttlMsgInfo("533703344615587840", "fape1meh4bsz", "CRDT")
    # t_client.getSttlMsgInfo("499406243287269376", "huu4lssdbmbt", "DBIT")
