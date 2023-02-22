# coding=utf-8
# author: MingLei Li
# date: 2022-2-10
import json
import traceback
from contextlib import contextmanager
import requests
import unittest
import copy
import time
from .RMNApiTest import RMNData, ApiUtils, BaseCheckRMN

from roxe_libs.Global import Global
from roxe_libs import settings
from .RMNStatusCode import RmnCodEnum


class RmnMsgFieldValidationTest(BaseCheckRMN):

    def test_001_error_submitTransaction_headers_missingFields(self):
        """
        提交交易请求，header中缺少必填参数时报错
        """
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        sec_key = RMNData.sec_key
        self.client.checkHeadersMissingField(tx_headers, self.client.submit_transaction, [sec_key, tx_headers, tx_group_header, cdtTrfTxInf])

    def test_002_error_submitTransaction_headers_fieldsLengthLimit(self):
        """
        提交交易请求，header中字段超过长度限制
        """
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        sec_key = RMNData.sec_key
        self.client.checkHeaderLengthLimit(tx_headers, self.client.submit_transaction, [sec_key, tx_headers, tx_group_header, cdtTrfTxInf])

    def test_003_error_submitTransaction_headers_versionNotCorrect(self):
        """
        提交交易请求，使用错误的secret key进行加密
        """
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        tx_headers["version"] = "100"
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.VERSION_ERROR)

    def test_004_error_submitTransaction_headers_sndrRIDNotCorrect(self):
        """
        提交交易请求，使用错误的rsa private key进行签名
        """
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(ApiUtils.generateString(12), RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00200004", "Roxe ID does not exist, sndrRID:" + tx_headers["sndrRID"])

    def test_005_error_submitTransaction_headers_senderApiKeyNotCorrect(self):
        """
        提交交易请求，header中apikey不正确
        """
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key + "1", "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.APIKEY_ERROR)

    def test_006_error_submitTransaction_headers_msgTpNotCorrect(self):
        """
        提交交易请求，header中msgIp不正确
        """
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCXT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.HEADER_MSGTP_INVALID)

    def test_007_error_submitTransaction_headers_msgIDNotCorrect(self):
        """
        提交交易请求，header中msgId不正确
        """
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = "0202202341644824030711331"
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.HEADER_MSGID_INVALID)

    def test_008_error_submitTransaction_headers_signWithOtherRSAPrivateKey(self):
        """
        提交交易请求，使用错误的rsa private key进行签名
        """
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf, replaceKeyFile=True)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.SIGNATURE_ERROR)

    def test_009_error_submitTransaction_encryptBody_enbodyIsEmpty(self):
        """
        提交交易请求，发送请求数据为空
        """
        pn1 = RMNData.pn_usd_us
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        self.client.logger.info("加密body为空")
        tx_info = requests.post(self.client.host + "/submit-transaction", "", headers=tx_headers).json()
        self.client.logger.info(tx_info)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.MISS_BODY)

    def test_010_error_submitTransaction_encryptBody_missingItems(self):
        """
        提交交易请求，加密请求数据中缺少字段
        """
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        self.client.checkEncryptBodyMissingField(self.client.submit_transaction, [RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf])

    def test_011_error_submitTransaction_encryptBody_enbodyNotCorrect(self):
        """
        提交交易请求，加密请求数据不正确
        """
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        self.client.checkEncryptBodyReplaceBody(self.client.submit_transaction, [RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf])

    def test_012_error_submitTransaction_encryptBody_ciphertextEncryptWithErrorSecretKey(self):
        """
        提交交易请求，使用错误的secretKey进行加密
        """
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.api_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.DECRYPT_ERROR)

    def test_013_error_submitTransaction_decryptBody_grpHdr_msgIdNotSameWithMsgIDInHeaders(self):
        """
        提交交易请求，grpHdr中msgId和请求header中不一致
        """
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id.replace("1", "2"))
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, grpHdr.msgId in message does not match the one in HTTP header")

    def test_014_error_submitTransaction_decryptBody_grpHdr_instgAgtNotSameWithSndrRIDInHeaders(self):
        """
        提交交易请求，grpHdr中instgAgt和请求header中不一致
        """
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn2, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn2, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, 1, pn2)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, grpHdr.instgAgt in message does not match the one in HTTP header")

    def test_015_error_submitTransaction_decryptBody_grpHdr_missingItems(self):
        """
        提交交易请求，grpHdr中缺少必填字段
        """
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        for m_g_k in ["msgId", "instgAgt", "instdAgt", "creDtTm"]:
            with self.subTest(f"grpHdr缺少: {m_g_k}"):
                tmp_gp_header = copy.deepcopy(tx_group_header)
                tmp_gp_header.pop(m_g_k)
                tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tmp_gp_header, cdtTrfTxInf)
                self.client.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, grpHdr.{m_g_k} is empty")

    def test_016_error_submitTransaction_decryptBody_grpHdr_fieldsLengthLimit(self):
        """
        提交交易请求，grpHdr中字段长度限制
        """
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        for key in ["instgAgt:12", "instdAgt:12", "msgId:25"]:
            with self.subTest(f"grpHdr长度限制: {key}"):
                m_g_k = key.split(":")[0]
                tmp_gp_header = copy.deepcopy(tx_group_header)
                tmp_gp_header[m_g_k] = ApiUtils.generateString(int(key.split(":")[1]) + 1)
                tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tmp_gp_header, cdtTrfTxInf)
                self.client.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, grpHdr.{m_g_k} has invalid value:{tmp_gp_header[m_g_k]}")

    def test_017_error_submitTransaction_decryptBody_grpHdr_creDtTmIsIllegal(self):
        """
        提交交易请求，grpHdr中creDtTm不合法
        """
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        tx_group_header["creDtTm"] = "20221122"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, grpHdr.creDtTm has invalid value:" + tx_group_header["creDtTm"])

    def test_018_error_submitTransaction_decryptBody_grpHdr_sttlmInfIsIllegal(self):
        """
        提交交易请求，grpHdr中sttlmInf不合法
        """
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id, "CLRG", "xxx")
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, grpHdr.sttlmInf.clrSysCd has invalid value:xxx")
        tx_group_header["sttlmInf"] = {"sttlmMtd": "abcd", "clrSysCd": "ROXE"}
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, grpHdr.sttlmInf.sttlmMtd has invalid value:abcd")

    def test_019_error_submitTransaction_decryptBody_intrBkSttlmDtNotCorrect(self):
        """
        提交交易请求，结算时间不符合要求
        """
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["intrBkSttlmDt"] = "2020-12-12T17:21:28"
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, cdtTrfTxInf.intrBkSttlmDt has invalid value:{cdtTrfTxInf['intrBkSttlmDt']}")

    def test_020_error_submitTransaction_decryptBody_pmtIdFieldsLengthLimit(self):
        """
        提交交易请求，pmtId中字段限制
        """
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        for k in ["instrId", "endToEndId", "txId"]:
            with self.subTest(f"{k}超过长度限制"):
                tmp_body = copy.deepcopy(cdtTrfTxInf)
                tmp_body["pmtId"][k] = ApiUtils.generateString(36)
                tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, tmp_body)
                self.client.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, cdtTrfTxInf.pmtId.{k} has invalid value:{tmp_body['pmtId'][k]}")

    def test_021_error_submitTransaction_decryptBody_chrgsInf_agtSchmeCdNotCorrect(self):
        """
        提交交易请求，费用信息中schmeCd不合法
        """
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["chrgsInf"][0]["agt"]["schmeCd"] = "1234"
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, cdtTrfTxInf.chrgsInf.0.agt.schmeCd is not valid")

    def test_022_error_submitTransaction_decryptBody_xchgRateLengthLimit(self):
        """
        提交交易请求，汇率超过长度限制
        """
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["xchgRate"] = "1.12345"
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, cdtTrfTxInf.xchgRate has invalid value:1.12345")

    def test_023_error_submitTransaction_decryptBody_dbtrAndCdtr_prvtId_fieldsLengthLimit(self):
        """
        提交交易请求，个人信息时的字段长度校验
        """
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", copy.deepcopy(RMNData.prvtId), debtor_agent, copy.deepcopy(RMNData.prvtId), creditor_agent, 1, pn1)
        dbtr_keys = [
            "nm:140",
            "pstlAdr.pstCd:35", "pstlAdr.twnNm:35", "pstlAdr.twnLctnNm:35", "pstlAdr.dstrctNm:35",
            "pstlAdr.ctrySubDvsn:35", "pstlAdr.adrLine:490",
            "prvtId.dtAndPlcOfBirth.prvcOfBirth:35",
            "prvtId.dtAndPlcOfBirth.cityOfBirth:35",
            "prvtId.othr.prtry:35", "prvtId.othr.id:35", "prvtId.othr.issr:35",
        ]
        for k in dbtr_keys:
            for user in ["dbtr", "cdtr"]:
                with self.subTest(f"{user}长度限制: {k}"):
                    tmp_body = copy.deepcopy(cdtTrfTxInf)
                    field, k_len = k.split(":")
                    g_v = ApiUtils.generateString(int(k_len) + 1)
                    tmp_d = ApiUtils.generateDict(field, g_v)
                    tmp_body[user] = ApiUtils.deepUpdateDict(tmp_body[user], tmp_d)
                    tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, tmp_body)
                    self.client.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, cdtTrfTxInf.{user}.{field} has invalid value:{g_v}")

    def test_024_error_submitTransaction_decryptBody_dbtrAndCdtr_prvtId_missingField(self):
        """
        提交交易请求，个人信息时缺少必填字段
        """
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", copy.deepcopy(RMNData.prvtId), debtor_agent, copy.deepcopy(RMNData.prvtId), creditor_agent, 1, pn1)
        dbtr_keys = [
            "prvtId.dtAndPlcOfBirth.ctryOfBirth",
            "prvtId.dtAndPlcOfBirth.cityOfBirth",
            "prvtId.othr.prtry", "prvtId.othr.id",
        ]
        for k in dbtr_keys:
            for user in ["dbtr", "cdtr"]:
                with self.subTest(f"{user}缺少必填字段: {k}"):
                    tmp_body = copy.deepcopy(cdtTrfTxInf)
                    field = k
                    tmp_d = ApiUtils.generateDict(field, None)
                    tmp_body[user] = ApiUtils.deepUpdateDict(tmp_body[user], tmp_d)
                    tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, tmp_body)
                    self.client.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, cdtTrfTxInf.{user}.{field} is empty")

    def test_025_error_submitTransaction_decryptBody_dbtrAndCdtr_orgId_fieldsLengthLimit(self):
        """
        提交交易请求，组织信息时的字段长度校验
        """
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", copy.deepcopy(RMNData.orgId), debtor_agent, copy.deepcopy(RMNData.orgId), creditor_agent, 1, pn1)
        dbtr_keys = [
            "orgId.lei:35",
            "orgId.othr.prtry:35", "orgId.othr.id:35", "orgId.othr.issr:35",
            "ctctDtls.phneNb:35", "ctctDtls.mobNb:35", "ctctDtls.emailAdr:128",
        ]
        for k in dbtr_keys:
            for user in ["dbtr", "cdtr"]:
                with self.subTest(f"{user}长度限制: {k}"):
                    tmp_body = copy.deepcopy(cdtTrfTxInf)
                    field, k_len = k.split(":")
                    g_v = ApiUtils.generateString(int(k_len) + 1)
                    tmp_d = ApiUtils.generateDict(field, g_v)
                    tmp_body[user] = ApiUtils.deepUpdateDict(tmp_body[user], tmp_d)
                    tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, tmp_body)
                    self.client.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, cdtTrfTxInf.{user}.{field} has invalid value:{g_v}")

    def test_026_error_submitTransaction_decryptBody_dbtrAndCdtr_orgId_missingField(self):
        """
        提交交易请求，组织信息时缺少必填字段
        """
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", copy.deepcopy(RMNData.orgId), debtor_agent, copy.deepcopy(RMNData.orgId), creditor_agent, 1, pn1)
        dbtr_keys = ["orgId.othr.prtry", "orgId.othr.id"]
        for k in dbtr_keys:
            for user in ["dbtr", "cdtr"]:
                with self.subTest(f"{user}缺少必填字段: {k}"):
                    tmp_body = copy.deepcopy(cdtTrfTxInf)
                    tmp_d = ApiUtils.generateDict(k, None)
                    tmp_body[user] = ApiUtils.deepUpdateDict(tmp_body[user], tmp_d)
                    tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, tmp_body)
                    self.client.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, cdtTrfTxInf.{user}.{k} is empty")

    def test_027_error_submitTransaction_decryptBody_account_fieldsLengthLimit(self):
        """
        提交交易请求，账户信息中字段长度限制
        """
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", copy.deepcopy(RMNData.prvtId), debtor_agent, copy.deepcopy(RMNData.prvtId), creditor_agent, 1, pn1)
        dbtr_keys = ["acctId:35", "tp:35", "iban:34", "nm:140"]
        for k in dbtr_keys:
            for act in ["dbtrAcct", "cdtrAcct"]:
                with self.subTest(f"{act}长度限制: {k}"):
                    tmp_body = copy.deepcopy(cdtTrfTxInf)
                    field, k_len = k.split(":")
                    g_v = ApiUtils.generateString(int(k_len) + 1)
                    tmp_body[act][field] = g_v
                    tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, tmp_body)
                    if field == "iban":
                        self.client.checkCodeAndMessage(tx_info, "00600108", f"IBAN is wrong, cdtTrfTxInf.{act}.iban has invalid value:{g_v}")
                    else:
                        self.client.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, cdtTrfTxInf.{act}.{field} has invalid value:{g_v}")

    def test_028_error_submitTransaction_decryptBody_dbtrAgt_issrNotCorrect(self):
        """
        提交交易请求，dbtrAgt issr不正确
        """
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "XX")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, cdtTrfTxInf.dbtrAgt.finInstnId.othr.issr has invalid value:XX")

    def test_029_error_submitTransaction_decryptBody_dbtrAgt_missingField(self):
        """
        提交交易请求，dbtrAgt缺少必填字段
        """
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        for k in ["id", "schmeCd"]:
            cdtTrfTxInf["dbtrAgt"]["finInstnId"]["othr"][k] = None
            tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
            self.client.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, cdtTrfTxInf.dbtrAgt.finInstnId.othr.{k} is empty")

    def test_030_error_submitTransaction_decryptBody_agent_fieldsLengthLimit(self):
        """
        提交交易请求，agent字段长度限制
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        dbtr_keys = [
            "finInstnId.nm:140", "finInstnId.bicFI:11", "finInstnId.othr.id:12",
            "brnchId.nm:140", "brnchId.id:35", "brnchId.lei:35"
        ]
        for k in dbtr_keys:
            for agt in ["dbtrAgt", "dbtrIntrmyAgt", "cdtrAgt", "cdtrIntrmyAgt"]:
                with self.subTest(f"{agt}长度限制: {k}"):
                    tmp_body = copy.deepcopy(cdtTrfTxInf)
                    if agt not in tmp_body:
                        tmp_body[agt] = {}
                    field, k_len = k.split(":")
                    g_v = ApiUtils.generateString(int(k_len) + 1)
                    tmp_d = ApiUtils.generateDict(field, g_v)
                    tmp_body[agt] = ApiUtils.deepUpdateDict(tmp_body[agt], tmp_d)
                    tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, tmp_body)
                    if field.endswith("bicFI"):
                        self.client.checkCodeAndMessage(tx_info, "00600106", f"SWIFT BIC is wrong, cdtTrfTxInf.{agt}.{field} has invalid value:{g_v}")
                    else:
                        self.client.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, cdtTrfTxInf.{agt}.{field} has invalid value:{g_v}")

    def test_031_error_submitTransaction_decryptBody_dbtrIntrmyAgt_issrNotCorrect(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(RMNData.sn_usd_us, "XX")
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, cdtTrfTxInf.dbtrIntrmyAgt.finInstnId.othr.issr has invalid value:XX")

    def test_032_error_submitTransaction_decryptBody_cdtrAgt_nccNotCorrect(self):
        """
        提交交易请求，NCC不正确
        """
        pn1 = RMNData.pn_usd_us
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = {"finInstnId": {"clrSysMmbId": {"clrSysCd": "USDDD", "mmbId": "111000025"}}}
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00600107", "NCC type is wrong, cdtTrfTxInf.cdtrAgt.finInstnId.clrSysMmbId.clrSysCd has invalid value:USDDD")

    def test_033_error_submitTransaction_decryptBody_cdtrAgt_bicNotCorrect(self):
        """
        提交交易请求，BIC不正确
        """
        pn1 = RMNData.pn_usd_us
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = {"finInstnId": {"bicFI": "BOFAUU3DAU2"}}
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00600106", "SWIFT BIC is wrong, cdtTrfTxInf.cdtrAgt.finInstnId.bicFI has invalid value:BOFAUU3DAU2")

    def test_034_error_submitTransaction_decryptBody_cdtrAgt_ibanNotCorrect(self):
        """
        提交交易请求，iban不正确
        """
        pn1 = RMNData.pn_usd_us
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrAcct"]["iban"] = "XX2700000000123121231412231C1"
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00600108", "IBAN is wrong, cdtTrfTxInf.cdtrAcct.iban has invalid value:XX2700000000123121231412231C1")

    def test_035_error_submitTransaction_decryptBody_cdtrAgt_issrNotCorrect(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "XX")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, cdtTrfTxInf.cdtrAgt.finInstnId.othr.issr has invalid value:XX")

    def test_036_error_submitTransaction_decryptBody_cdtrIntrmyAgt_issrNotCorrect(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(RMNData.sn_usd_gb, "XX")
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, cdtTrfTxInf.cdtrIntrmyAgt.finInstnId.othr.issr has invalid value:XX")

    def test_037_error_submitTransaction_decryptBody_splmtryData_sndrCcyNotSupport(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["splmtryData"]["envlp"]["cnts"]["sndrCcy"] = "ABC"
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, cdtTrfTxInf.splmtryData.envlp.cnts.sndrCcy has invalid value:ABC")

    def test_038_error_submitTransaction_decryptBody_splmtryData_rcvrCcyNotSupport(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["splmtryData"]["envlp"]["cnts"]["rcvrCcy"] = "ABC"
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, cdtTrfTxInf.splmtryData.envlp.cnts.rcvrCcy has invalid value:ABC")

    def test_039_error_submitTransaction_decryptBody_cdtTrfTxInf_missingItems(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        for m_k in ["dbtr", "instdAmt", "intrBkSttlmAmt", "intrBkSttlmDt", "pmtId", "dbtrAgt"]:
            with self.subTest(f"缺少字段: {m_k}"):
                tmp_body = copy.deepcopy(cdtTrfTxInf)
                tmp_body.pop(m_k)
                tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, tmp_body)
                self.client.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, cdtTrfTxInf.{m_k} is empty")

    def test_040_error_submitTransaction_decryptBody_other_fieldsLengthLimit(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        other_limit = [
            "purp.cd:35", "purp.desc:140",
            "rltnShp.cd:35", "rltnShp.desc:35",
            "splmtryData.rmrk:140"
        ]
        self.client.checkBodyFieldsLengthLimit(other_limit, self.client.submit_transaction, [RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf])

    def prepare_transaction(self, sender, receiver, senderType, receiverType):
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sender, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sender, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sender, senderType)
        creditor_agent = self.client.make_roxe_agent(receiver, receiverType)
        if senderType == "SN":
            sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sender, "USD", "USD", creditor_agent=creditor_agent)
            sender_fee = sn1_fee
        else:
            sender_fee = self.client.getTransactionFeeInDB(sender, "USD", "in", "PN")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sender_fee, sender)

        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)
        self.client.logger.warning(f"{sender}节点收到交易confirm")
        self.client.waitNodeReceiveMessage(sender, msg_id)
        if senderType == "SN":
            return tx_msg
        else:
            return tx_info["data"]["txId"]

    def test_041_error_submitSettlement_headers_missingFields(self):
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb

        tx_msg = self.prepare_transaction(sn1, pn2, "SN", "PN")

        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_group_headers = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"])
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        self.client.checkHeadersMissingField(st_headers, self.client.submit_settlement, [RMNData.sec_key, st_headers, st_group_headers, st_cdtInf])

    def test_042_error_submitSettlement_headers_fieldsLengthLimit(self):
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        tx_msg = self.prepare_transaction(sn1, pn2, "SN", "PN")

        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"])
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        self.client.checkHeaderLengthLimit(st_headers, self.client.submit_settlement, [RMNData.sec_key, st_headers, st_grpHder, st_cdtInf])

    def test_043_error_submitSettlement_headers_versionNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        tx_msg = self.prepare_transaction(sn1, pn2, "SN", "PN")

        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"])
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        st_headers["version"] = "100"
        st_info, st_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, st_grpHder, st_cdtInf)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.VERSION_ERROR)

    def test_044_error_submitSettlement_headers_sndrRIDNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        tx_msg = self.prepare_transaction(sn1, pn2, "SN", "PN")

        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"])
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        st_headers["sndrRID"] = ApiUtils.generateString(12)
        st_info, st_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, st_grpHder, st_cdtInf)
        self.client.checkCodeAndMessage(st_info, "00200004", "Roxe ID does not exist, sndrRID:" + st_headers["sndrRID"])

    def test_045_error_submitSettlement_headers_senderApiKeyNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        tx_msg = self.prepare_transaction(sn1, pn2, "SN", "PN")

        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, ApiUtils.generateString(12), "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"])
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        st_info, st_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, st_grpHder, st_cdtInf)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.APIKEY_ERROR)

    def test_046_error_submitSettlement_headers_msgTpNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        tx_msg = self.prepare_transaction(sn1, pn2, "SN", "PN")

        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RSRX")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"])
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        st_info, st_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, st_grpHder, st_cdtInf)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.HEADER_MSGTP_INVALID)

    def test_047_error_submitSettlement_headers_msgIdNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        tx_msg = self.prepare_transaction(sn1, pn2, "SN", "PN")

        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"])
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        st_headers["msgId"] = ApiUtils.generateString(25)
        st_info, st_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, st_grpHder, st_cdtInf)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.HEADER_MSGID_INVALID)

    def test_048_error_submitSettlement_headers_signWithOtherRSAPrivateKey(self):
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        tx_msg = self.prepare_transaction(sn1, pn2, "SN", "PN")

        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"])
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        st_info, st_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, st_grpHder, st_cdtInf, replaceKeyFile=True)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.SIGNATURE_ERROR)

    def test_049_error_submitSettlement_encryptBody_enbodyIsEmpty(self):
        sn1 = RMNData.sn_usd_us
        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_info = requests.post(self.client.host + "/submit-settlement", "", headers=st_headers).json()
        self.client.logger.info(st_info)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.MISS_BODY)

    def test_050_error_submitSettlement_encryptBody_missingItems(self):
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        tx_msg = self.prepare_transaction(sn1, pn2, "SN", "PN")

        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"])
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        self.client.checkEncryptBodyMissingField(self.client.submit_settlement, [RMNData.sec_key, st_headers, st_grpHder, st_cdtInf])

    def test_051_error_submitSettlement_encryptBody_enBodyNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        tx_msg = self.prepare_transaction(sn1, pn2, "SN", "PN")

        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"])
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        self.client.checkEncryptBodyReplaceBody(self.client.submit_settlement, [RMNData.sec_key, st_headers, st_grpHder, st_cdtInf])

    def test_052_error_submitSettlement_encryptBody_ciphertextEncryptWithErrorSecretKey(self):
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        tx_msg = self.prepare_transaction(sn1, pn2, "SN", "PN")

        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"])
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        st_info, st_msg = self.client.submit_settlement(RMNData.api_key, st_headers, st_grpHder, st_cdtInf)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.DECRYPT_ERROR)

    def test_053_error_submitSettlement_decryptBody_msgIsEmpty(self):
        sn1 = RMNData.sn_usd_us

        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        headers, en_body = self.client.makeEncryptHeaders(st_headers, "", RMNData.sec_key)
        self.client.logger.info("加密body为空")
        st_info = requests.post(self.client.host + "/submit-settlement", en_body, headers=headers).json()
        self.client.logger.info(st_info)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.DECRYPT_ERROR)

    def test_054_error_submitSettlement_decryptBody_grpHdr_fieldsLengthLimit(self):
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        tx_msg = self.prepare_transaction(sn1, pn2, "SN", "PN")

        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"])
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        for key in ["msgId:25", "instgAgt:12", "instdAgt:12"]:
            with self.subTest(f"长度限制: {key}"):
                field_key, field_len = key.split(":")
                self.client.logger.warning(f"grpHdr缺少: {field_key}")
                tmp_gp_header = copy.deepcopy(st_grpHder)
                tmp_gp_header[field_key] = ApiUtils.generateString(int(field_len) + 1)
                st_info, st_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, tmp_gp_header, st_cdtInf)
                self.client.checkCodeAndMessage(st_info, "00100000", f"Parameter exception, grpHdr.{field_key} has invalid value:" + tmp_gp_header[field_key])

    def test_055_error_submitSettlement_decryptBody_grpHdr_missingFields(self):
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        tx_msg = self.prepare_transaction(sn1, pn2, "SN", "PN")

        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"])
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        for m_g_k in ["msgId", "msgId", "instgAgt", "instdAgt", "creDtTm"]:
            with self.subTest(f"grpHdr缺少: {m_g_k}"):
                tmp_gp_header = copy.deepcopy(st_grpHder)
                tmp_gp_header.pop(m_g_k)
                tx_info, tx_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, tmp_gp_header, st_cdtInf)
                self.client.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, grpHdr.{m_g_k} is empty")

    def test_056_error_submitSettlement_decryptBody_grpHdr_creDtTmIsIllegal(self):
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        tx_msg = self.prepare_transaction(sn1, pn2, "SN", "PN")

        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"])
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        st_grpHder["creDtTm"] = "29292929292"
        tx_info, tx_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, st_grpHder, st_cdtInf)
        self.client.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, grpHdr.creDtTm has invalid value:29292929292")

    def test_057_error_submitSettlement_decryptBody_grpHdr_sttlmInfIsIllegal(self):
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        tx_msg = self.prepare_transaction(sn1, pn2, "SN", "PN")

        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"], "XXX")
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        tx_info, tx_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, st_grpHder, st_cdtInf)
        self.client.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, grpHdr.sttlmInf.sttlmMtd has invalid value:XXX")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"], clearingSystemCode="XXX")
        tx_info, tx_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, st_grpHder, st_cdtInf)
        self.client.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, grpHdr.sttlmInf.clrSysCd has invalid value:XXX")

    def test_058_error_submitSettlement_decryptBody_grpHdr_msgIdNotSameWithMsgIDInHeaders(self):
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        tx_msg = self.prepare_transaction(sn1, pn2, "SN", "PN")
        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"].replace("1", "2"))
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        tx_info, tx_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, st_grpHder, st_cdtInf)
        self.client.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, grpHdr.msgId in message does not match the one in HTTP header")

    def test_059_error_submitSettlement_decryptBody_grpHdr_instgAgtNotSameWithMsgIDInHeaders(self):
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        tx_msg = self.prepare_transaction(sn1, pn2, "SN", "PN")
        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(pn2, RMNData.rmn_id, st_headers["msgId"])
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        tx_info, tx_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, st_grpHder, st_cdtInf)
        self.client.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, grpHdr.instgAgt in message does not match the one in HTTP header")

    def test_060_error_submitSettlement_decryptBody_cdtTrfTxnInf_fieldsLength(self):
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        tx_msg = self.prepare_transaction(sn1, pn2, "SN", "PN")
        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"].replace("1", "2"))
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        f_length = [
            "pmtId.instrId:35", "pmtId.endToEndId:35", "pmtId.txId:35",
            "dbtr.finInstnId.nm:140", "dbtr.finInstnId.othr.id:12",
            "dbtrAcct.acctId:35", "dbtrAcct.tp:35", "dbtrAcct.nm:140",
            "cdtr.finInstnId.nm:140", "cdtr.finInstnId.othr.id:12",
            "cdtrAcct.acctId:35", "cdtrAcct.tp:35", "cdtrAcct.nm:140",
            "rmtInf.orgnlMsgID:35", "rmtInf.orgnlMsgTp:4", "rmtInf.instgAgt:12",
        ]
        self.client.checkBodyFieldsLengthLimit(f_length, self.client.submit_settlement, [RMNData.sec_key, st_headers, st_grpHder, st_cdtInf], 3)
        st_cdtInf["cdtrAcct"]["iban"] = ApiUtils.generateString(35)
        st_info, st_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, st_grpHder, st_cdtInf)
        self.client.checkCodeAndMessage(st_info, "00600108", "IBAN is wrong, cdtTrfTxInf.cdtrAcct.iban has invalid value:" + st_cdtInf["cdtrAcct"]["iban"])

    def test_061_error_submitSettlement_decryptBody_cdtTrfTxnInf_missingField(self):
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        tx_msg = self.prepare_transaction(sn1, pn2, "SN", "PN")
        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"].replace("1", "2"))
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        f_length = [
            "intrBkSttlmAmt", "intrBkSttlmDt", "pmtId.endToEndId", "pmtId.txId",
            "dbtr.finInstnId", "dbtr.finInstnId.othr.id",
            "rmtInf.orgnlMsgID", "rmtInf.orgnlMsgTp", "rmtInf.instgAgt", "splmtryData.envlp.ustrd.cdtDbtInd"
        ]
        self.client.checkBodyFieldsMissing(f_length, self.client.submit_settlement, [RMNData.sec_key, st_headers, st_grpHder, st_cdtInf], 3)

    def test_062_error_procConfirm_headers_missingFields(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        rmn_tx_id = self.prepare_transaction(pn1, pn2, "PN", "PN")

        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, RMNData.api_key, RMNData.sec_key,  "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", pc_msg_id)
        pc_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, pc_msg_id, hasSttlmInf=False)
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        self.client.checkHeadersMissingField(pc_headers, self.client.proc_confirm, [RMNData.sec_key, pc_headers, pc_group_header, p_msg])

    def test_063_error_procConfirm_headers_fieldsLengthLimit(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        rmn_tx_id = self.prepare_transaction(pn1, pn2, "PN", "PN")

        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, RMNData.api_key, RMNData.sec_key,  "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC", pc_msg_id)
        pc_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, pc_msg_id, hasSttlmInf=False)
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        self.client.checkHeaderLengthLimit(pc_headers, self.client.proc_confirm, [RMNData.sec_key, pc_headers, pc_group_header, p_msg])

    def test_064_error_procConfirm_headers_versionNotCorrect(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        rmn_tx_id = self.prepare_transaction(pn1, pn2, "PN", "PN")

        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, RMNData.api_key, RMNData.sec_key,  "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC", pc_msg_id)
        pc_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, pc_msg_id, hasSttlmInf=False)
        pc_headers["version"] = "123"
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        pc_info, pc_msg = self.client.proc_confirm(RMNData.sec_key, pc_headers, pc_group_header, p_msg)
        self.client.checkCodeAndMessage(pc_info, RmnCodEnum.VERSION_ERROR)

    def test_065_error_procConfirm_headers_sndrRIDNotCorrect(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        rmn_tx_id = self.prepare_transaction(pn1, pn2, "PN", "PN")

        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, RMNData.api_key, RMNData.sec_key,  "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC", pc_msg_id)
        pc_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, pc_msg_id, hasSttlmInf=False)
        pc_headers["sndrRID"] = ApiUtils.generateString(12)
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        pc_info, pc_msg = self.client.proc_confirm(RMNData.sec_key, pc_headers, pc_group_header, p_msg)
        self.client.checkCodeAndMessage(pc_info, "00200004", "Roxe ID does not exist, sndrRID:" + pc_headers["sndrRID"])

    def test_066_error_procConfirm_headers_senderApiKeyNotCorrect(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        rmn_tx_id = self.prepare_transaction(pn1, pn2, "PN", "PN")

        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, RMNData.api_key, RMNData.sec_key,  "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC", pc_msg_id)
        pc_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, pc_msg_id, hasSttlmInf=False)
        pc_headers["sndrApiKey"] = ApiUtils.generateString(12)
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        pc_info, pc_msg = self.client.proc_confirm(RMNData.sec_key, pc_headers, pc_group_header, p_msg)
        self.client.checkCodeAndMessage(pc_info, RmnCodEnum.APIKEY_ERROR)

    def test_067_error_procConfirm_headers_msgTpNotCorrect(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        rmn_tx_id = self.prepare_transaction(pn1, pn2, "PN", "PN")

        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, RMNData.api_key, RMNData.sec_key,  "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC", pc_msg_id)
        pc_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, pc_msg_id, hasSttlmInf=False)
        pc_headers["msgTp"] = "RXXT"
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        pc_info, pc_msg = self.client.proc_confirm(RMNData.sec_key, pc_headers, pc_group_header, p_msg)
        self.client.checkCodeAndMessage(pc_info, RmnCodEnum.HEADER_MSGTP_INVALID)

    def test_068_error_procConfirm_headers_msgIdNotCorrect(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        rmn_tx_id = self.prepare_transaction(pn1, pn2, "PN", "PN")

        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, RMNData.api_key, RMNData.sec_key,  "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC", pc_msg_id)
        pc_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, pc_msg_id, hasSttlmInf=False)
        pc_headers["msgId"] = "0202202341644807879378361"
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        pc_info, pc_msg = self.client.proc_confirm(RMNData.sec_key, pc_headers, pc_group_header, p_msg)
        self.client.checkCodeAndMessage(pc_info, RmnCodEnum.HEADER_MSGID_INVALID)

    def test_069_error_procConfirm_headers_signWithOtherRSAPrivateKey(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        
        rmn_tx_id = self.prepare_transaction(pn1, pn2, "PN", "PN")

        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, RMNData.api_key, RMNData.sec_key,  "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC", pc_msg_id)
        pc_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, pc_msg_id, hasSttlmInf=False)
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        pc_info, pc_msg = self.client.proc_confirm(RMNData.sec_key, pc_headers, pc_group_header, p_msg, replaceKeyFile=True)
        self.client.checkCodeAndMessage(pc_info, RmnCodEnum.SIGNATURE_ERROR)

    def test_070_error_procConfirm_encryptBody_enbodyIsEmpty(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        rmn_tx_id = self.prepare_transaction(pn1, pn2, "PN", "PN")

        self.client.logger.warning("sn1节点接收rcct消息")
        self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, RMNData.api_key, RMNData.sec_key,  "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC", pc_msg_id)
        pc_info = requests.post(self.client.host + "/proc-confirm", "", headers=pc_headers).json()
        self.client.logger.info(pc_info)
        self.client.checkCodeAndMessage(pc_info, RmnCodEnum.MISS_BODY)

    def test_071_error_procConfirm_encryptBody_missingItems(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        rmn_tx_id = self.prepare_transaction(pn1, pn2, "PN", "PN")

        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, RMNData.api_key, RMNData.sec_key,  "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC", pc_msg_id)
        pc_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, pc_msg_id, hasSttlmInf=False)
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        self.client.checkEncryptBodyMissingField(self.client.proc_confirm, [RMNData.sec_key, pc_headers, pc_group_header, p_msg])

    def test_072_error_procConfirm_encryptBody_enBodyNotCorrect(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        rmn_tx_id = self.prepare_transaction(pn1, pn2, "PN", "PN")

        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, RMNData.api_key, RMNData.sec_key,  "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC", pc_msg_id)
        pc_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, pc_msg_id, hasSttlmInf=False)
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        self.client.checkEncryptBodyReplaceBody(self.client.proc_confirm, [RMNData.sec_key, pc_headers, pc_group_header, p_msg])

    def test_073_error_procConfirm_encryptBody_ciphertextEncryptWithErrorSecretKey(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        rmn_tx_id = self.prepare_transaction(pn1, pn2, "PN", "PN")

        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, RMNData.api_key, RMNData.sec_key,  "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC", pc_msg_id)
        pc_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, pc_msg_id, hasSttlmInf=False)
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        pc_info, pc_msg = self.client.proc_confirm(RMNData.api_key, pc_headers, pc_group_header, p_msg)
        self.client.checkCodeAndMessage(pc_info, RmnCodEnum.DECRYPT_ERROR)

    def test_074_error_procConfirm_decryptBody_msgIsEmpty(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        rmn_tx_id = self.prepare_transaction(pn1, pn2, "PN", "PN")

        self.client.logger.warning("sn1节点接收rcct消息")
        self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, RMNData.api_key, RMNData.sec_key,  "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC", pc_msg_id)
        headers, en_body = self.client.makeEncryptHeaders(pc_headers, "", RMNData.sec_key)
        self.client.logger.info("加密body为空")
        pc_info = requests.post(self.client.host + "/proc-confirm", en_body, headers=headers).json()
        self.client.logger.info(pc_info)
        self.client.checkCodeAndMessage(pc_info, RmnCodEnum.DECRYPT_ERROR)

    def test_075_error_procConfirm_decryptBody_grpHdr_fieldsLengthLimit(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        rmn_tx_id = self.prepare_transaction(pn1, pn2, "PN", "PN")

        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, RMNData.api_key, RMNData.sec_key,  "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC", pc_msg_id)
        pc_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, pc_msg_id, hasSttlmInf=False)
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        for key in ["msgId:25", "instgAgt:12", "instdAgt:12"]:
            with self.subTest(f"grpHdr长度限制: {key}"):
                field_key, field_len = key.split(":")
                tmp_gp_header = copy.deepcopy(pc_group_header)
                tmp_gp_header[field_key] = ApiUtils.generateString(int(field_len) + 1)
                pc_info, pc_msg = self.client.proc_confirm(RMNData.sec_key, pc_headers, tmp_gp_header, p_msg)
                self.client.checkCodeAndMessage(pc_info, "00100000", f"Parameter exception, grpHdr.{field_key} has invalid value:" + tmp_gp_header[field_key])

    def test_076_error_procConfirm_decryptBody_grpHdr_missingFields(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        rmn_tx_id = self.prepare_transaction(pn1, pn2, "PN", "PN")

        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, RMNData.api_key, RMNData.sec_key,  "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC", pc_msg_id)
        pc_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, pc_msg_id, hasSttlmInf=False)
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        for key in ["msgId", "instgAgt", "creDtTm"]:
            with self.subTest(f"grpHdr缺少: {key}"):
                tmp_gp_header = copy.deepcopy(pc_group_header)
                tmp_gp_header.pop(key)
                pc_info, pc_msg = self.client.proc_confirm(RMNData.sec_key, pc_headers, tmp_gp_header, p_msg)
                self.client.checkCodeAndMessage(pc_info, "00100000", f"Parameter exception, grpHdr.{key} is empty")

    def test_077_error_procConfirm_decryptBody_grpHdr_creDtTmIsIllegal(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        rmn_tx_id = self.prepare_transaction(pn1, pn2, "PN", "PN")

        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, RMNData.api_key, RMNData.sec_key,  "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC", pc_msg_id)
        pc_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, pc_msg_id, hasSttlmInf=False)
        pc_group_header["creDtTm"] = "2022-02-30T10:12:35"
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        pc_info, pc_msg = self.client.proc_confirm(RMNData.sec_key, pc_headers, pc_group_header, p_msg)
        self.client.checkCodeAndMessage(pc_info, "00100000", f"Parameter exception, grpHdr.creDtTm has invalid value:" + pc_group_header["creDtTm"])

    def test_078_error_procConfirm_decryptBody_grpHdr_msgIdNotSameWithMsgIDInHeaders(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        rmn_tx_id = self.prepare_transaction(pn1, pn2, "PN", "PN")

        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, RMNData.api_key, RMNData.sec_key,  "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC", pc_msg_id)
        pc_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, pc_msg_id, hasSttlmInf=False)
        pc_group_header["msgId"] = self.client.make_msg_id()
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        pc_info, pc_msg = self.client.proc_confirm(RMNData.sec_key, pc_headers, pc_group_header, p_msg)
        self.client.checkCodeAndMessage(pc_info, "00100000", f"Parameter exception, grpHdr.msgId in message does not match the one in HTTP header")

    def test_079_error_procConfirm_decryptBody_grpHdr_instgAgtNotSameWithMsgIDInHeaders(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        rmn_tx_id = self.prepare_transaction(pn1, pn2, "PN", "PN")

        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, RMNData.api_key, RMNData.sec_key,  "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC", pc_msg_id)
        pc_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, pc_msg_id, hasSttlmInf=False)
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        pc_info, pc_msg = self.client.proc_confirm(RMNData.sec_key, pc_headers, pc_group_header, p_msg)
        self.client.checkCodeAndMessage(pc_info, "00100000", f"Parameter exception, grpHdr.instgAgt in message does not match the one in HTTP header")

    def test_080_error_procConfirm_decryptBody_fieldsLengthLimit(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        rmn_tx_id = self.prepare_transaction(pn1, pn2, "PN", "PN")

        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, RMNData.api_key, RMNData.sec_key,  "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC", pc_msg_id)
        pc_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, pc_msg_id, hasSttlmInf=False)
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        p_msg["txInfAndSts"]["stsRsnInf"] = {"addtlInf": "reject", "stsRsnCd": "error"}
        f_length = [
            "orgnlGrpInfAndSts.orgnlMsgId:25", "orgnlGrpInfAndSts.orgnlMsgNmId:4",
            "txInfAndSts.orgnlInstrId:35", "txInfAndSts.orgnlEndToEndId:35", "txInfAndSts.orgnlTxId:35",
            "txInfAndSts.stsRsnInf.addtlInf:105",
            "txInfAndSts.stsRsnInf.stsRsnCd:35",
            "txInfAndSts.instgAgt:12",
        ]
        self.client.checkBodyFieldsLengthLimit(f_length, self.client.proc_confirm, [RMNData.sec_key, pc_headers, pc_group_header, p_msg], 3, "")

    def test_081_error_procConfirm_decryptBody_stsIdIsIllegal(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        rmn_tx_id = self.prepare_transaction(pn1, pn2, "PN", "PN")

        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, RMNData.api_key, RMNData.sec_key,  "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC", pc_msg_id)
        pc_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, pc_msg_id, hasSttlmInf=False)
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        p_msg["txInfAndSts"]["stsId"] = "ABCD"
        pc_info, pc_msg = self.client.proc_confirm(RMNData.sec_key, pc_headers, pc_group_header, p_msg)
        self.client.checkCodeAndMessage(pc_info, "00100000", "Parameter exception, txInfAndSts.stsId has invalid value:ABCD")

    def test_082_error_procConfirm_decryptBody_acctSvcrRefIsIllegal(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        rmn_tx_id = self.prepare_transaction(pn1, pn2, "PN", "PN")

        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, RMNData.api_key, RMNData.sec_key,  "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC", pc_msg_id)
        pc_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, pc_msg_id, hasSttlmInf=False)
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        p_msg["txInfAndSts"]["stsId"] = "ABCD"
        pc_info, pc_msg = self.client.proc_confirm(RMNData.sec_key, pc_headers, pc_group_header, p_msg)
        self.client.checkCodeAndMessage(pc_info, "00100000", "Parameter exception, txInfAndSts.stsId has invalid value:ABCD")

    def test_083_error_procConfirm_decryptBody_missingFields(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        rmn_tx_id = self.prepare_transaction(pn1, pn2, "PN", "PN")

        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, RMNData.api_key, RMNData.sec_key,  "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC", pc_msg_id)
        pc_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, pc_msg_id, hasSttlmInf=False)
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        p_msg["txInfAndSts"]["stsId"] = "ABCD"
        # return功能添加后，"txInfAndSts.orgnlEndToEndId"不再作为报文的必填项
        f_length = [
            "orgnlGrpInfAndSts.orgnlMsgId", "orgnlGrpInfAndSts.orgnlMsgNmId", "txInfAndSts.orgnlTxId",
            "txInfAndSts.stsId", "txInfAndSts.acctSvcrRef", "txInfAndSts.instgAgt",
        ]
        self.client.checkBodyFieldsMissing(f_length, self.client.proc_confirm, [RMNData.sec_key, pc_headers, pc_group_header, p_msg], 3, "")

    def test_084_error_getExchangeRate_headers_missingFields(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        self.client.checkHeadersMissingField(ts_headers, self.client.get_exchange_rate, [RMNData.sec_key, ts_headers, msg_header, "USD", "100", "USD"])

    def test_085_error_getExchangeRate_headers_fieldsLengthLimit(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        self.client.checkHeaderLengthLimit(ts_headers, self.client.get_exchange_rate, [RMNData.sec_key, ts_headers, msg_header, "USD", "100", "USD"])

    def test_086_error_getExchangeRate_headers_versionNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        ts_headers["version"] = "100"
        st_info, st_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", "100", "USD")
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.VERSION_ERROR)

    def test_087_error_getExchangeRate_headers_sndrRIDNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        ts_headers["sndrRID"] = ApiUtils.generateString(12)
        st_info, st_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", "100", "USD")
        self.client.checkCodeAndMessage(st_info, "00200004", "Roxe ID does not exist, sndrRID:" + ts_headers["sndrRID"])

    def test_088_error_getExchangeRate_headers_senderApiKeyNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key + "1", "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        st_info, st_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", "100", "USD")
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.APIKEY_ERROR)

    def test_089_error_getExchangeRate_headers_msgTpNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RTXQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        st_info, st_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", "100", "USD")
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.HEADER_MSGTP_INVALID)

    def test_090_error_getExchangeRate_headers_msgIdNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        ts_headers["msgId"] = ApiUtils.generateString(12)
        st_info, st_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", "100", "USD")
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.HEADER_MSGID_INVALID)

    def test_091_error_getExchangeRate_headers_signWithOtherRSAPrivateKey(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        st_info, st_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", "100", "USD", replaceKeyFile=True)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.SIGNATURE_ERROR)

    def test_092_error_getExchangeRate_encryptBody_enbodyIsEmpty(self):
        sn1 = RMNData.sn_usd_us
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RERQ")
        st_info = requests.post(self.client.host + "/get-exchange-rate", "", headers=st_headers).json()
        self.client.logger.info(st_info)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.MISS_BODY)

    def test_093_error_getExchangeRate_encryptBody_missingItems(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        self.client.checkEncryptBodyMissingField(self.client.get_exchange_rate, [RMNData.sec_key, ts_headers, msg_header, "USD", "100", "USD"])

    def test_094_error_getExchangeRate_encryptBody_enBodyNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        self.client.checkEncryptBodyReplaceBody(self.client.get_exchange_rate, [RMNData.sec_key, ts_headers, msg_header, "USD", "100", "USD"])

    def test_095_error_getExchangeRate_encryptBody_ciphertextEncryptWithErrorSecretKey(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        st_info, st_msg = self.client.get_exchange_rate(RMNData.api_key, ts_headers, msg_header, "USD", "100", "USD")
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.DECRYPT_ERROR)

    def test_096_error_getExchangeRate_decryptBody_msgIsEmpty(self):
        sn1 = RMNData.sn_usd_us
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RERQ")
        headers, en_body = self.client.makeEncryptHeaders(st_headers, "", RMNData.sec_key)
        self.client.logger.info("加密body为空")
        st_info = requests.post(self.client.host + "/get-exchange-rate", en_body, headers=headers).json()
        self.client.logger.info(st_info)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.DECRYPT_ERROR)

    def test_097_error_getExchangeRate_decryptBody_msgHdr_msgIdNotSameWithMsgIDInHeaders(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        msg_header["msgId"] = "0202202341644822356579402"
        st_info, st_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", "100", "USD")
        self.client.checkCodeAndMessage(st_info, "00100000", "Parameter exception, msgHdr.msgId has invalid value:0202202341644822356579402")

    def test_098_error_getExchangeRate_decryptBody_msgHdr_creDtTmIsIllegal(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        msg_header["creDtTm"] = "20220234"
        st_info, st_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", "100", "USD")
        self.client.checkCodeAndMessage(st_info, "00100000", "Parameter exception, msgHdr.creDtTm has invalid value:20220234")

    def test_099_error_getExchangeRate_decryptBody_msgHdr_missingField(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        for k in ["msgId", "instgPty"]:
            with self.subTest(f"msgHdr缺少{k}"):
                tmp_header = copy.deepcopy(msg_header)
                tmp_header.pop(k)
                st_info, st_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, tmp_header, "USD", "100", "USD")
                self.client.checkCodeAndMessage(st_info, "00100000", f"Parameter exception, msgHdr.{k} is empty")

    def test_100_error_getExchangeRate_decryptBody_msgHdr_fieldsLengthLimit(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        for i in ["msgId:25", "instgPty:12"]:
            with self.subTest(f"msgHdr长度限制：{i}"):
                k, k_len = i.split(":")
                tmp_header = copy.deepcopy(msg_header)
                tmp_header[k] = ApiUtils.generateString(int(k_len) + 1)
                st_info, st_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, tmp_header, "USD", "100", "USD")
                self.client.checkCodeAndMessage(st_info, "00100000", f"Parameter exception, msgHdr.{k} has invalid value:{tmp_header[k]}")

    def test_101_error_getExchangeRate_sndrCcyNotCorrect(self):
        sender = RMNData.pn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        tx_info, req_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "XX", "23", "USD")
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, ccyQryDef.ccyCrit.sndrCcy has invalid value:XX")

    def test_102_error_getExchangeRate_rcvrCcyNotCorrect(self):
        sender = RMNData.pn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        tx_info, req_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", "10", "XX")
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, ccyQryDef.ccyCrit.rcvrCcy has invalid value:XX")

    def test_103_error_getExchangeRate_sndrAmtNotCorrect(self):
        sender = RMNData.pn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        tx_info, req_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", "1.12341234", "USD")
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, ccyQryDef.ccyCrit.sndrAmt has invalid value:1.12341234")

    def test_104_error_getExchangeRate_rcvrAmtNotCorrect(self):
        sender = RMNData.pn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        tx_info, req_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", "", "USD", "1.12344123")
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, ccyQryDef.ccyCrit.rcvrAmt has invalid value:1.12344123")

    def test_105_error_getExchangeRate_sndrCcyAndRcvrCcyNotFill(self):
        sender = RMNData.pn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        tx_info, req_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "", "", "")
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, ccyQryDef.ccyCrit.rcvrCcy is empty")

    def test_106_error_getRouterList_headers_missingFields(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rtgQryDef = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAcct={"iban": RMNData.iban["GBP"]})
        self.client.checkHeadersMissingField(ts_headers, self.client.get_router_list, [RMNData.sec_key, ts_headers, msg_header, rtgQryDef])

    def test_107_error_getRouterList_headers_fieldsLengthLimit(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rtgQryDef = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAcct={"iban": RMNData.iban["GBP"]})
        self.client.checkHeaderLengthLimit(ts_headers, self.client.get_router_list, [RMNData.sec_key, ts_headers, msg_header, rtgQryDef])

    def test_108_error_getRouterList_headers_versionNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        ts_headers["version"] = "100"
        rtgQryDef = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAcct={"iban": RMNData.iban["GBP"]})
        st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, rtgQryDef)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.VERSION_ERROR)

    def test_109_error_getRouterList_headers_sndrRIDNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        ts_headers["sndrRID"] = ApiUtils.generateString(12)
        rtgQryDef = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAcct={"iban": RMNData.iban["GBP"]})
        st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, rtgQryDef)
        self.client.checkCodeAndMessage(st_info, "00200004", "Roxe ID does not exist, sndrRID:" + ts_headers["sndrRID"])

    def test_110_error_getRouterList_headers_senderApiKeyNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key + "1", "RRLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rtgQryDef = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAcct={"iban": RMNData.iban["GBP"]})
        st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, rtgQryDef)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.APIKEY_ERROR)

    def test_111_error_getRouterList_headers_msgTpNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RXLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rtgQryDef = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAcct={"iban": RMNData.iban["GBP"]})
        st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, rtgQryDef)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.HEADER_MSGTP_INVALID)

    def test_112_error_getRouterList_headers_msgIdNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sn1, "0202202341644832278952964")
        rtgQryDef = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAcct={"iban": RMNData.iban["GBP"]})
        st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, rtgQryDef)
        self.client.checkCodeAndMessage(st_info, "00100000", "Parameter exception, msgHdr.msgId has invalid value:0202202341644832278952964")

    def test_113_error_getRouterList_headers_signWithOtherRSAPrivateKey(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rtgQryDef = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAcct={"iban": RMNData.iban["GBP"]})
        st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, rtgQryDef, replaceKeyFile=True)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.SIGNATURE_ERROR)

    def test_114_error_getRouterList_encryptBody_enbodyIsEmpty(self):
        sn1 = RMNData.sn_usd_us
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        st_info = requests.post(self.client.host + "/get-route-list", "", headers=st_headers).json()
        self.client.logger.info(st_info)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.MISS_BODY)

    def test_115_error_getRouterList_encryptBody_missingItems(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rtgQryDef = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAcct={"iban": RMNData.iban["GBP"]})
        self.client.checkEncryptBodyMissingField(self.client.get_router_list, [RMNData.sec_key, ts_headers, msg_header, rtgQryDef])

    def test_116_error_getRouterList_encryptBody_enBodyNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rtgQryDef = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAcct={"iban": RMNData.iban["GBP"]})
        self.client.checkEncryptBodyReplaceBody(self.client.get_router_list, [RMNData.sec_key, ts_headers, msg_header, rtgQryDef])

    def test_117_error_getRouterList_encryptBody_ciphertextEncryptWithErrorSecretKey(self):
        sn1 = RMNData.sn_usd_us
        api_key = RMNData.api_key
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rtgQryDef = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAcct={"iban": RMNData.iban["GBP"]})
        st_info, st_msg = self.client.get_router_list(api_key, ts_headers, msg_header, rtgQryDef)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.DECRYPT_ERROR)

    def test_118_error_getRouterList_decryptBody_msgIsEmpty(self):
        sn1 = RMNData.sn_usd_us
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        headers, en_body = self.client.makeEncryptHeaders(st_headers, "", RMNData.sec_key)
        self.client.logger.info("加密body为空")
        st_info = requests.post(self.client.host + "/get-route-list", en_body, headers=headers).json()
        self.client.logger.info(st_info)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.DECRYPT_ERROR)

    def test_119_error_getRouterList_decryptBody_msgHdr_msgIdNotSameWithMsgIDInHeaders(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        msg_header["msgId"] = self.client.make_msg_id()
        rtgQryDef = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAcct={"iban": RMNData.iban["GBP"]})
        st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, rtgQryDef)
        self.client.checkCodeAndMessage(st_info, "00100000", "Parameter exception, msgHdr.msgId in message does not match the one in HTTP header")

    def test_120_error_getRouterList_decryptBody_msgHdr_instgAgtNotSameWithSndrRIDInHeaders(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(RMNData.pn_usd_us, ts_headers["msgId"])
        rtgQryDef = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAcct={"iban": RMNData.iban["GBP"]})
        st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, rtgQryDef)
        self.client.checkCodeAndMessage(st_info, "00100000", "Parameter exception, msgHdr.instgPty in message does not match the one in HTTP header")

    def test_121_error_getRouterList_decryptBody_msgHdr_creDtTmIsIllegal(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        msg_header["creDtTm"] = "20220234"
        rtgQryDef = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAcct={"iban": RMNData.iban["GBP"]})
        st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, rtgQryDef)
        self.client.checkCodeAndMessage(st_info, "00100000", "Parameter exception, msgHdr.creDtTm has invalid value:20220234")

    def test_122_error_getRouterList_decryptBody_msgHdr_missingField(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rtgQryDef = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAcct={"iban": RMNData.iban["GBP"]})
        for k in ["msgId", "instgPty"]:
            with self.subTest(f"msgHdr缺少{k}"):
                tmp_header = copy.deepcopy(msg_header)
                tmp_header.pop(k)
                st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, tmp_header, rtgQryDef)
                self.client.checkCodeAndMessage(st_info, "00100000", f"Parameter exception, msgHdr.{k} is empty")

    def test_123_error_getRouterList_decryptBody_msgHdr_fieldsLengthLimit(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rtgQryDef = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAcct={"iban": RMNData.iban["GBP"]})
        for i in ["msgId:25", "instgPty:12"]:
            with self.subTest(f"msgHdr缺少{i}"):
                k, k_len = i.split(":")
                tmp_header = copy.deepcopy(msg_header)
                tmp_header[k] = ApiUtils.generateString(int(k_len) + 1)
                st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, tmp_header, rtgQryDef)
                self.client.checkCodeAndMessage(st_info, "00100000", f"Parameter exception, msgHdr.{k} has invalid value:{tmp_header[k]}")

    def test_124_error_getRouterList_decryptBody_rtgQryDef_missingField(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rtgQryDef = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAcct={"iban": RMNData.iban["GBP"]})
        for k in ["qryCrit.rmtInf", "qryCrit.rmtInf.sndrCcy", "qryCrit.rmtInf.rcvrCcy"]:
            with self.subTest(f"缺少{k}"):
                tmp_msg = copy.deepcopy(rtgQryDef)
                new_dict = ApiUtils.generateDict(k, None)
                tmp_msg = ApiUtils.deepUpdateDict(tmp_msg, new_dict)
                st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, tmp_msg)
                self.client.checkCodeAndMessage(st_info, "00100000", f"Parameter exception, rtgQryDef.{k} is empty")

    def test_125_error_getRouterList_decryptBody_rtgQryDef_cdtrAcctAndCdtrAgtBothMissing(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rtgQryDef = self.client.make_RRLQ_information("USD", "USD", "100")
        st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, rtgQryDef)
        self.client.checkCodeAndMessage(st_info, "00100103", "Business exception, IBAN or cdtrAgt is mandatory")

    def test_126_error_getRouterList_decryptBody_qryTpNotCorrect(self):
        sender = RMNData.pn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("USD", "USD", "100", qryTp="NEE", cdtrAgt=RMNData.bic_agents["USD"])

        st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.client.checkCodeAndMessage(st_info, "00100000", "Parameter exception, rtgQryDef.qryTp has invalid value:NEE")

    def test_127_error_getRouterList_decryptBody_NCCNotCorrect(self):
        sender = RMNData.pn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agt = {"finInstnId": {"clrSysMmbId": {"clrSysCd": "USAC", "mmbId": "123412345"}}}
        msg = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAgt=agt)

        st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.client.checkCodeAndMessage(st_info, "00600107", "NCC type is wrong, rtgQryDef.qryCrit.cdtrAgt.finInstnId.clrSysMmbId.clrSysCd has invalid value:USAC")

    def test_128_error_getRouterList_decryptBody_BICNotCorrect(self):
        sender = RMNData.pn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agt = {"finInstnId": {"bicFI": "BOFAU3DAU2"}}
        msg = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAgt=agt)

        st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.client.checkCodeAndMessage(st_info, "00600106", "SWIFT BIC is wrong, rtgQryDef.qryCrit.cdtrAgt.finInstnId.bicFI has invalid value:BOFAU3DAU2")

    def test_129_error_getRouterList_decryptBody_IBANNotCorrect(self):
        sender = RMNData.pn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        account = {"iban": "UU33BUKB20201555555555"}
        msg = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAcct=account)

        st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.client.checkCodeAndMessage(st_info, "00600108", "IBAN is wrong, rtgQryDef.qryCrit.cdtrAcct.iban has invalid value:UU33BUKB20201555555555")

    def test_130_error_getRouterList_decryptBody_agentIdNotCorrect(self):
        sender = RMNData.pn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        g = ApiUtils.generateString(12)
        agt = self.client.make_roxe_agent(g, "SN")
        msg = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAgt=agt)

        st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.client.checkCodeAndMessage(st_info, "00200004", f"Roxe ID does not exist, {g}")

    def test_131_error_getRouterList_decryptBody_sndrAmtNotCorrect(self):
        sender = RMNData.pn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("USD", "USD", "100.123", cdtrAgt=RMNData.bic_agents["USD"])

        st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.client.checkCodeAndMessage(st_info, "00100000", "Parameter exception, rtgQryDef.qryCrit.rmtInf.sndrAmt has invalid value:100.123")

    def test_132_error_getRouterList_decryptBody_rcvrAmtNotCorrect(self):
        sender = RMNData.pn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("USD", "USD", "", "100.123", cdtrAgt=RMNData.bic_agents["USD"])

        st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.client.checkCodeAndMessage(st_info, "00100000", "Parameter exception, rtgQryDef.qryCrit.rmtInf.rcvrAmt has invalid value:100.123")

    def test_133_error_getRouterList_decryptBody_ibanLengthLimit(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rtgQryDef = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAcct={"iban": "GB" + ApiUtils.generateString(33)})
        st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, rtgQryDef)
        self.client.checkCodeAndMessage(st_info, "00600108", f"IBAN is wrong, rtgQryDef.qryCrit.cdtrAcct.iban has invalid value:{rtgQryDef['qryCrit']['cdtrAcct']['iban']}")

    def test_134_error_getRouterList_decryptBody_bicLengthLimit(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        agt = {"finInstnId": {"bicFI": "BOFAU3DAU212"}}
        rtgQryDef = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAgt=agt)
        st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, rtgQryDef)
        self.client.checkCodeAndMessage(st_info, "00600106", f"SWIFT BIC is wrong, rtgQryDef.qryCrit.cdtrAgt.finInstnId.bicFI has invalid value:{agt['finInstnId']['bicFI']}")

    def test_135_error_getRouterList_decryptBody_nccLengthLimit(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        agt = copy.deepcopy(RMNData.ncc_agents["USD"])
        agt["finInstnId"]["clrSysMmbId"]["mmbId"] = ApiUtils.generateString(36)
        rtgQryDef = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAgt=agt)
        st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, rtgQryDef)
        self.client.checkCodeAndMessage(st_info, "00100000", f"Parameter exception, rtgQryDef.qryCrit.cdtrAgt.finInstnId.clrSysMmbId.mmbId has invalid value:{agt['finInstnId']['clrSysMmbId']['mmbId']}")

    def test_136_error_getTransactionStatus_headers_missingFields(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RTSQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"])
        self.client.checkHeadersMissingField(ts_headers, self.client.get_transaction_status, [RMNData.sec_key, ts_headers, msg_header, txQryDef])

    def test_137_error_getTransactionStatus_headers_fieldsLengthLimit(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RTSQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"])
        self.client.checkHeaderLengthLimit(ts_headers, self.client.submit_settlement, [RMNData.sec_key, ts_headers, msg_header, txQryDef])

    def test_138_error_getTransactionStatus_headers_versionNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RTSQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"])
        ts_headers["version"] = "100"
        st_info, st_msg = self.client.get_transaction_status(RMNData.sec_key, ts_headers, msg_header, txQryDef)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.VERSION_ERROR)

    def test_139_error_getTransactionStatus_headers_sndrRIDNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RTSQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        ts_headers["sndrRID"] = ApiUtils.generateString(12)
        txQryDef = self.client.make_RTSQ_information(RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"])
        st_info, st_msg = self.client.get_transaction_status(RMNData.sec_key, ts_headers, msg_header, txQryDef)
        self.client.checkCodeAndMessage(st_info, "00200004", "Roxe ID does not exist, sndrRID:" + ts_headers["sndrRID"])

    def test_140_error_getTransactionStatus_headers_senderApiKeyNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key + "1", "RTSQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"])
        st_info, st_msg = self.client.get_transaction_status(RMNData.sec_key, ts_headers, msg_header, txQryDef)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.APIKEY_ERROR)

    def test_141_error_getTransactionStatus_headers_msgTpNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RTXQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"])
        st_info, st_msg = self.client.get_transaction_status(RMNData.sec_key, ts_headers, msg_header, txQryDef)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.HEADER_MSGTP_INVALID)

    def test_142_error_getTransactionStatus_headers_msgIdNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RTSQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"])
        ts_headers["msgId"] = "0202202341644832278952964"
        st_info, st_msg = self.client.get_transaction_status(RMNData.sec_key, ts_headers, msg_header, txQryDef)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.HEADER_MSGID_INVALID)

    def test_143_error_getTransactionStatus_headers_signWithOtherRSAPrivateKey(self):
        sn1 = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RTSQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"])
        st_info, st_msg = self.client.get_transaction_status(RMNData.sec_key, ts_headers, msg_header, txQryDef, replaceKeyFile=True)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.SIGNATURE_ERROR)

    def test_144_error_getTransactionStatus_encryptBody_enbodyIsEmpty(self):
        sn1 = RMNData.sn_usd_us
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RTSQ")
        st_info = requests.post(self.client.host + "/get-transaction-status", "", headers=st_headers).json()
        self.client.logger.info(st_info)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.MISS_BODY)

    def test_145_error_getTransactionStatus_encryptBody_missingItems(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RTSQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"])
        self.client.checkEncryptBodyMissingField(self.client.get_transaction_status, [RMNData.sec_key, ts_headers, msg_header, txQryDef])

    def test_146_error_getTransactionStatus_encryptBody_enBodyNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RTSQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"])
        self.client.checkEncryptBodyReplaceBody(self.client.get_transaction_status, [RMNData.sec_key, ts_headers, msg_header, txQryDef])

    def test_147_error_getTransactionStatus_encryptBody_ciphertextEncryptWithErrorSecretKey(self):
        sn1 = RMNData.sn_usd_us
        api_key = RMNData.api_key

        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RTSQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"])
        st_info, st_msg = self.client.get_transaction_status(api_key, ts_headers, msg_header, txQryDef)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.DECRYPT_ERROR)

    def test_148_error_getTransactionStatus_decryptBody_msgIsEmpty(self):
        sn1 = RMNData.sn_usd_us
        
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RTSQ")
        headers, en_body = self.client.makeEncryptHeaders(st_headers, "", RMNData.sec_key)
        self.client.logger.info("加密body为空")
        st_info = requests.post(self.client.host + "/get-transaction-status", en_body, headers=headers).json()
        self.client.logger.info(st_info)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.DECRYPT_ERROR)

    def test_149_error_getTransactionStatus_decryptBody_msgHdr_msgIdNotSameWithMsgIDInHeaders(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RTSQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        msg_header["msgId"] = self.client.make_msg_id()
        txQryDef = self.client.make_RTSQ_information(RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"])
        st_info, st_msg = self.client.get_transaction_status(RMNData.sec_key, ts_headers, msg_header, txQryDef)
        self.client.checkCodeAndMessage(st_info, "00100000", "Parameter exception, msgHdr.msgId in message does not match the one in HTTP header")

    def test_150_error_getTransactionStatus_decryptBody_msgHdr_instgAgtNotSameWithSndrRIDInHeaders(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RTSQ")
        msg_header = self.client.make_msg_header(RMNData.pn_usd_us, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"])
        st_info, st_msg = self.client.get_transaction_status(RMNData.sec_key, ts_headers, msg_header, txQryDef)
        self.client.checkCodeAndMessage(st_info, "00100000", "Parameter exception, msgHdr.instgPty in message does not match the one in HTTP header")

    def test_151_error_getTransactionStatus_decryptBody_msgHdr_creDtTmIsIllegal(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RTSQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        msg_header["creDtTm"] = "20220234"
        txQryDef = self.client.make_RTSQ_information(RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"])
        st_info, st_msg = self.client.get_transaction_status(RMNData.sec_key, ts_headers, msg_header, txQryDef)
        self.client.checkCodeAndMessage(st_info, "00100000", "Parameter exception, msgHdr.creDtTm has invalid value:20220234")

    def test_152_error_getTransactionStatus_decryptBody_msgHdr_missingField(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RTSQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"])
        for k in ["msgId", "instgPty"]:
            with self.subTest(f"msgHdr缺少{k}"):
                tmp_header = copy.deepcopy(msg_header)
                tmp_header.pop(k)
                st_info, st_msg = self.client.get_transaction_status(RMNData.sec_key, ts_headers, tmp_header, txQryDef)
                self.client.checkCodeAndMessage(st_info, "00100000", f"Parameter exception, msgHdr.{k} is empty")

    def test_153_error_getTransactionStatus_decryptBody_msgHdr_fieldsLengthLimit(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RTSQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"])
        for i in ["msgId:25", "instgPty:12"]:
            with self.subTest(f"msgHdr长度限制{i}"):
                k, k_len = i.split(":")
                tmp_header = copy.deepcopy(msg_header)
                tmp_header[k] = ApiUtils.generateString(int(k_len) + 1)
                st_info, st_msg = self.client.get_transaction_status(RMNData.sec_key, ts_headers, tmp_header, txQryDef)
                self.client.checkCodeAndMessage(st_info, "00100000", f"Parameter exception, msgHdr.{k} has invalid value:{tmp_header[k]}")

    def test_154_error_getTransactionStatus_decryptBody_rtgQryDef_missingField(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RTSQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(
            RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"],
            RMNData.query_tx_info["endToEndId"], RMNData.query_tx_info["endToEndId"]
        )
        f = ["pmtSch.msgId", "pmtSch.pmtId.endToEndId", "pmtSch.pmtId.txId", "ptySch.instgPty", "ntryTp"]
        self.client.checkBodyFieldsMissing(f, self.client.get_transaction_status, [RMNData.sec_key, ts_headers, msg_header, txQryDef], 3, "txQryDef.")

    def test_155_error_getTransactionStatus_decryptBody_rtgQryDef_fieldLengthLimit(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RTSQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(
            RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"],
            RMNData.query_tx_info["endToEndId"], RMNData.query_tx_info["endToEndId"]
        )
        f_limit = [
            "pmtSch.msgId:25", "pmtSch.msgTp:4", "ntryTp:3",
            "pmtSch.pmtId.instrId:35", "pmtSch.pmtId.endToEndId:35", "pmtSch.pmtId.txId:35",
            "ptySch.instgPty:12", "ptySch.instdPty:12",
        ]
        self.client.checkBodyFieldsLengthLimit(f_limit, self.client.get_transaction_status, [RMNData.sec_key, ts_headers, msg_header, txQryDef], 3, "txQryDef.")

    def test_156_error_getAuditTrail_headers_missingFields(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RATQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(ts_headers["msgId"], sn1, ntryTp="ADT")
        self.client.checkHeadersMissingField(ts_headers, self.client.get_transaction_flow, [RMNData.sec_key, ts_headers, msg_header, txQryDef])

    def test_157_error_getAuditTrail_headers_fieldsLengthLimit(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RATQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(ts_headers["msgId"], sn1, ntryTp="ADT")
        self.client.checkHeaderLengthLimit(ts_headers, self.client.get_transaction_flow, [RMNData.sec_key, ts_headers, msg_header, txQryDef])

    def test_158_error_getAuditTrail_headers_versionNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RATQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(ts_headers["msgId"], sn1, ntryTp="ADT")
        ts_headers["version"] = "100"
        st_info, st_msg = self.client.get_transaction_flow(RMNData.sec_key, ts_headers, msg_header, txQryDef)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.VERSION_ERROR)

    def test_159_error_getAuditTrail_headers_sndrRIDNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RATQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        ts_headers["sndrRID"] = ApiUtils.generateString(12)
        txQryDef = self.client.make_RTSQ_information(ts_headers["msgId"], sn1, ntryTp="ADT")
        st_info, st_msg = self.client.get_transaction_flow(RMNData.sec_key, ts_headers, msg_header, txQryDef)
        self.client.checkCodeAndMessage(st_info, "00200004", "Roxe ID does not exist, sndrRID:" + ts_headers["sndrRID"])

    def test_160_error_getAuditTrail_headers_senderApiKeyNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key + "1", "RATQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(ts_headers["msgId"], sn1, ntryTp="ADT")
        st_info, st_msg = self.client.get_transaction_flow(RMNData.sec_key, ts_headers, msg_header, txQryDef)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.APIKEY_ERROR)

    def test_161_error_getAuditTrail_headers_msgTpNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RTXQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(ts_headers["msgId"], sn1, ntryTp="ADT")
        st_info, st_msg = self.client.get_transaction_flow(RMNData.sec_key, ts_headers, msg_header, txQryDef)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.HEADER_MSGTP_INVALID)

    def test_162_error_getAuditTrail_headers_msgIdNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RATQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(ts_headers["msgId"], sn1, ntryTp="ADT")
        ts_headers["msgId"] = "0202202341644832278952964"
        st_info, st_msg = self.client.get_transaction_flow(RMNData.sec_key, ts_headers, msg_header, txQryDef)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.HEADER_MSGID_INVALID)

    def test_163_error_getAuditTrail_headers_signWithOtherRSAPrivateKey(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RATQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(ts_headers["msgId"], sn1, ntryTp="ADT")
        st_info, st_msg = self.client.get_transaction_flow(RMNData.sec_key, ts_headers, msg_header, txQryDef, replaceKeyFile=True)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.SIGNATURE_ERROR)

    def test_164_error_getAuditTrail_encryptBody_enbodyIsEmpty(self):
        sn1 = RMNData.sn_usd_us
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RATQ")
        st_info = requests.post(self.client.host + "/get-transaction-flow", "", headers=st_headers).json()
        self.client.logger.info(st_info)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.MISS_BODY)

    def test_165_error_getAuditTrail_encryptBody_missingItems(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RATQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(ts_headers["msgId"], sn1, ntryTp="ADT")
        self.client.checkEncryptBodyMissingField(self.client.get_transaction_flow, [RMNData.sec_key, ts_headers, msg_header, txQryDef])

    def test_166_error_getAuditTrail_encryptBody_enBodyNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RATQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(ts_headers["msgId"], sn1, ntryTp="ADT")
        self.client.checkEncryptBodyReplaceBody(self.client.get_transaction_flow, [RMNData.sec_key, ts_headers, msg_header, txQryDef])

    def test_167_error_getAuditTrail_encryptBody_ciphertextEncryptWithErrorSecretKey(self):
        sn1 = RMNData.sn_usd_us
        api_key = RMNData.api_key

        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RATQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(ts_headers["msgId"], sn1, ntryTp="ADT")
        st_info, st_msg = self.client.get_transaction_flow(api_key, ts_headers, msg_header, txQryDef)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.DECRYPT_ERROR)

    def test_168_error_getAuditTrail_decryptBody_msgIsEmpty(self):
        sn1 = RMNData.sn_usd_us
        
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RATQ")
        headers, en_body = self.client.makeEncryptHeaders(st_headers, "", RMNData.sec_key)
        self.client.logger.info("加密body为空")
        st_info = requests.post(self.client.host + "/get-transaction-flow", en_body, headers=headers).json()
        self.client.logger.info(st_info)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.DECRYPT_ERROR)

    def test_169_error_getAuditTrail_decryptBody_msgHdr_msgIdNotSameWithMsgIDInHeaders(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RATQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        msg_header["msgId"] = self.client.make_msg_id()
        txQryDef = self.client.make_RTSQ_information(ts_headers["msgId"], sn1, ntryTp="ADT")
        st_info, st_msg = self.client.get_transaction_flow(RMNData.sec_key, ts_headers, msg_header, txQryDef)
        self.client.checkCodeAndMessage(st_info, "00100000", "Parameter exception, msgHdr.msgId in message does not match the one in HTTP header")

    def test_170_error_getAuditTrail_decryptBody_msgHdr_instgAgtNotSameWithSndrRIDInHeaders(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RATQ")
        msg_header = self.client.make_msg_header(RMNData.pn_usd_us, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(ts_headers["msgId"], sn1, ntryTp="ADT")
        st_info, st_msg = self.client.get_transaction_flow(RMNData.sec_key, ts_headers, msg_header, txQryDef)
        self.client.checkCodeAndMessage(st_info, "00100000", "Parameter exception, msgHdr.instgPty in message does not match the one in HTTP header")

    def test_171_error_getAuditTrail_decryptBody_msgHdr_creDtTmIsIllegal(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RATQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        msg_header["creDtTm"] = "20220234"
        txQryDef = self.client.make_RTSQ_information(ts_headers["msgId"], sn1, ntryTp="ADT")
        st_info, st_msg = self.client.get_transaction_flow(RMNData.sec_key, ts_headers, msg_header, txQryDef)
        self.client.checkCodeAndMessage(st_info, "00100000", "Parameter exception, msgHdr.creDtTm has invalid value:20220234")

    def test_172_error_getAuditTrail_decryptBody_msgHdr_missingField(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RATQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(ts_headers["msgId"], sn1, ntryTp="ADT")
        for k in ["msgId", "instgPty"]:
            with self.subTest(f"msgHdr缺少{k}"):
                tmp_header = copy.deepcopy(msg_header)
                tmp_header.pop(k)
                st_info, st_msg = self.client.get_transaction_flow(RMNData.sec_key, ts_headers, tmp_header, txQryDef)
                self.client.checkCodeAndMessage(st_info, "00100000", f"Parameter exception, msgHdr.{k} is empty")

    def test_173_error_getAuditTrail_decryptBody_msgHdr_fieldsLengthLimit(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RATQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(ts_headers["msgId"], sn1, ntryTp="ADT")
        for i in ["msgId:25", "instgPty:12"]:
            with self.subTest(f"msgHdr长度限制:{i}"):
                k, k_len = i.split(":")
                tmp_header = copy.deepcopy(msg_header)
                tmp_header[k] = ApiUtils.generateString(int(k_len) + 1)
                st_info, st_msg = self.client.get_transaction_flow(RMNData.sec_key, ts_headers, tmp_header, txQryDef)
                self.client.checkCodeAndMessage(st_info, "00100000", f"Parameter exception, msgHdr.{k} has invalid value:{tmp_header[k]}")

    def test_174_error_getAuditTrail_decryptBody_rtgQryDef_missingField(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RATQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(
            RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"],
            RMNData.query_tx_info["endToEndId"], RMNData.query_tx_info["endToEndId"], ntryTp="ADT"
        )
        f = ["pmtSch.msgId", "pmtSch.pmtId.endToEndId", "pmtSch.pmtId.txId", "ptySch.instgPty", "ntryTp"]
        self.client.checkBodyFieldsMissing(f, self.client.get_transaction_flow, [RMNData.sec_key, ts_headers, msg_header, txQryDef], 3, "txQryDef.")

    def test_175_error_getAuditTrail_decryptBody_rtgQryDef_fieldLengthLimit(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RATQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(
            RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"],
            RMNData.query_tx_info["endToEndId"], RMNData.query_tx_info["endToEndId"], ntryTp="ADT"
        )
        f_limit = [
            "pmtSch.msgId:25", "pmtSch.msgTp:4", "ntryTp:3",
            "pmtSch.pmtId.instrId:35", "pmtSch.pmtId.endToEndId:35", "pmtSch.pmtId.txId:35",
            "ptySch.instgPty:12", "ptySch.instdPty:12",
        ]
        self.client.checkBodyFieldsLengthLimit(f_limit, self.client.get_transaction_flow, [RMNData.sec_key, ts_headers, msg_header, txQryDef], 3, "txQryDef.")

    def test_176_error_submitTransaction_decryptBody_dbtrIntrmyAgt_noRoxeId(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent("", "SN")
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, cdtTrfTxInf.dbtrIntrmyAgt.finInstnId.othr.id is empty")

    def test_177_error_submitTransaction_decryptBody_cdtrIntrmyAgt_noRoxeId(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent("", "SN")
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, cdtTrfTxInf.cdtrIntrmyAgt.finInstnId.othr.id is empty")

    def prepareFullySettledTransaction(self, sn1, sn2, sendCurrency="USD", receiveCurrency="USD", is_private=True):
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 20)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, sendCurrency, receiveCurrency, creditor_agent=creditor_agent, amount=amt)
        if is_private:
            cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, receiveCurrency, RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1, inAmount=amt)
        else:
            cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, receiveCurrency, RMNData.orgId, debtor_agent, RMNData.orgId, creditor_agent, sn1_fee, sn1, inAmount=amt)
        in_node = True if sn2 in RMNData.channel_nodes else False
        sn2_tx_info = self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=in_node)
        return sn2_tx_info, sn2_fee

    def test_178_error_submitReturn_headers_missingFields(self):
        """
        提交交易请求，header中缺少必填参数时报错
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee = self.prepareFullySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn2, RMNData.api_key, "RPRN", msg_id)
        tx_group_header = self.client.make_group_header(sn2, RMNData.rmn_id, msg_id)
        self.client.checkHeadersMissingField(tx_headers, self.client.submit_return_transaction, [RMNData.sec_key, tx_headers, tx_group_header, return_msg])

    def test_179_error_submitReturn_headers_fieldsLengthLimit(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee = self.prepareFullySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn2, RMNData.api_key, "RPRN", msg_id)
        tx_group_header = self.client.make_group_header(sn2, RMNData.rmn_id, msg_id)
        self.client.checkHeaderLengthLimit(tx_headers, self.client.submit_return_transaction, [RMNData.sec_key, tx_headers, tx_group_header, return_msg])

    def test_180_error_submitReturn_headers_versionNotCorrect(self):
        """
        提交交易请求，使用错误的secret key进行加密
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee = self.prepareFullySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn2, RMNData.api_key, "RPRN", msg_id)
        tx_group_header = self.client.make_group_header(sn2, RMNData.rmn_id, msg_id)
        tx_headers["version"] = "100"
        tx_info, _ = self.client.submit_return_transaction(RMNData.sec_key, tx_headers, tx_group_header, return_msg)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.VERSION_ERROR)

    def test_181_error_submitReturn_headers_sndrRIDNotCorrect(self):
        """
        提交交易请求，使用错误的rsa private key进行签名
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee = self.prepareFullySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(ApiUtils.generateString(12), RMNData.api_key, "RPRN", msg_id)
        tx_group_header = self.client.make_group_header(sn2, RMNData.rmn_id, msg_id)
        tx_info, _ = self.client.submit_return_transaction(RMNData.sec_key, tx_headers, tx_group_header, return_msg)
        self.client.checkCodeAndMessage(tx_info, "00200004", "Roxe ID does not exist, sndrRID:" + tx_headers["sndrRID"])

    def test_182_error_submitReturn_headers_senderApiKeyNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee = self.prepareFullySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn2, RMNData.api_key + "1", "RPRN", msg_id)
        tx_group_header = self.client.make_group_header(sn2, RMNData.rmn_id, msg_id)
        tx_info, _ = self.client.submit_return_transaction(RMNData.sec_key, tx_headers, tx_group_header, return_msg)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.APIKEY_ERROR)

    def test_183_error_submitReturn_headers_msgTpNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee = self.prepareFullySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn2, RMNData.api_key, "RPXT", msg_id)
        tx_group_header = self.client.make_group_header(sn2, RMNData.rmn_id, msg_id)
        tx_info, _ = self.client.submit_return_transaction(RMNData.sec_key, tx_headers, tx_group_header, return_msg)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.HEADER_MSGTP_INVALID)

    def test_184_error_submitReturn_headers_msgIDNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee = self.prepareFullySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)

        msg_id = "0202202341644824030711331"
        tx_headers = self.client.make_header(sn2, RMNData.api_key, "RPRN", msg_id)
        tx_group_header = self.client.make_group_header(sn2, RMNData.rmn_id, msg_id)
        tx_info, _ = self.client.submit_return_transaction(RMNData.sec_key, tx_headers, tx_group_header, return_msg)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.HEADER_MSGID_INVALID)

    def test_185_error_submitReturn_headers_signWithOtherRSAPrivateKey(self):
        """
        提交交易请求，使用错误的rsa private key进行签名
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee = self.prepareFullySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn2, RMNData.api_key, "RPRN", msg_id)
        tx_group_header = self.client.make_group_header(sn2, RMNData.rmn_id, msg_id)
        tx_info, _ = self.client.submit_return_transaction(RMNData.sec_key, tx_headers, tx_group_header, return_msg, replaceKeyFile=True)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.SIGNATURE_ERROR)

    def test_186_error_submitReturn_encryptBody_enbodyIsEmpty(self):
        pn1 = RMNData.pn_usd_us
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RPRN", msg_id)
        self.client.logger.info("加密body为空")
        tx_info = requests.post(self.client.host + "/submit-return-txn", "", headers=tx_headers).json()
        self.client.logger.info(tx_info)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.MISS_BODY)

    def test_187_error_submitReturn_encryptBody_missingItems(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee = self.prepareFullySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn2, RMNData.api_key, "RPRN", msg_id)
        tx_group_header = self.client.make_group_header(sn2, RMNData.rmn_id, msg_id)
        self.client.checkEncryptBodyMissingField(self.client.submit_return_transaction, [RMNData.sec_key, tx_headers, tx_group_header, return_msg])

    def test_188_error_submitReturn_encryptBody_enbodyNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee = self.prepareFullySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn2, RMNData.api_key, "RPRN", msg_id)
        tx_group_header = self.client.make_group_header(sn2, RMNData.rmn_id, msg_id)
        self.client.checkEncryptBodyReplaceBody(self.client.submit_return_transaction, [RMNData.sec_key, tx_headers, tx_group_header, return_msg])

    def test_189_error_submitReturn_encryptBody_ciphertextEncryptWithErrorSecretKey(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee = self.prepareFullySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn2, RMNData.api_key, "RPRN", msg_id)
        tx_group_header = self.client.make_group_header(sn2, RMNData.rmn_id, msg_id)
        tx_info, _ = self.client.submit_return_transaction(RMNData.api_key, tx_headers, tx_group_header, return_msg)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.DECRYPT_ERROR)

    def test_190_error_submitReturn_decryptBody_grpHdr_msgIdNotSameWithMsgIDInHeaders(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee = self.prepareFullySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn2, RMNData.api_key, "RPRN", msg_id)
        tx_group_header = self.client.make_group_header(sn2, RMNData.rmn_id, msg_id.replace("1", "2"))
        tx_info, _ = self.client.submit_return_transaction(RMNData.sec_key, tx_headers, tx_group_header, return_msg)
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, grpHdr.msgId in message does not match the one in HTTP header")

    def test_191_error_submitReturn_decryptBody_grpHdr_instgAgtNotSameWithSndrRIDInHeaders(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee = self.prepareFullySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn2, RMNData.api_key, "RPRN", msg_id)
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        tx_info, _ = self.client.submit_return_transaction(RMNData.sec_key, tx_headers, tx_group_header, return_msg)
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, grpHdr.instgAgt in message does not match the one in HTTP header")

    def test_192_error_submitReturn_decryptBody_grpHdr_missingItems(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee = self.prepareFullySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn2, RMNData.api_key, "RPRN", msg_id)
        tx_group_header = self.client.make_group_header(sn2, RMNData.rmn_id, msg_id)
        for m_g_k in ["msgId", "instgAgt", "instdAgt", "creDtTm"]:
            self.client.logger.warning(f"grpHdr缺少: {m_g_k}")
            tmp_gp_header = copy.deepcopy(tx_group_header)
            tmp_gp_header.pop(m_g_k)
            tx_info, _ = self.client.submit_return_transaction(RMNData.sec_key, tx_headers, tmp_gp_header, return_msg)
            self.client.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, grpHdr.{m_g_k} is empty")

    def test_193_error_submitReturn_decryptBody_grpHdr_fieldsLengthLimit(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee = self.prepareFullySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn2, RMNData.api_key, "RPRN", msg_id)
        tx_group_header = self.client.make_group_header(sn2, RMNData.rmn_id, msg_id)
        tx_info, _ = self.client.submit_return_transaction(RMNData.sec_key, tx_headers, tx_group_header, return_msg)
        f_limit = ["instgAgt:12", "instdAgt:12", "msgId:25"]
        self.client.checkBodyFieldsLengthLimit(f_limit, self.client.submit_return_transaction, [RMNData.sec_key, tx_headers, tx_group_header, return_msg], 2, "grpHdr.")

    def test_194_error_submitReturn_decryptBody_grpHdr_creDtTmIsIllegal(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee = self.prepareFullySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn2, RMNData.api_key, "RPRN", msg_id)
        tx_group_header = self.client.make_group_header(sn2, RMNData.rmn_id, msg_id)
        tx_group_header["creDtTm"] = "20221122"
        tx_info, _ = self.client.submit_return_transaction(RMNData.sec_key, tx_headers, tx_group_header, return_msg)
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, grpHdr.creDtTm has invalid value:" + tx_group_header["creDtTm"])

    def test_195_error_submitReturn_decryptBody_grpHdr_sttlmInfIsIllegal(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee = self.prepareFullySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn2, RMNData.api_key, "RPRN", msg_id)
        tx_group_header = self.client.make_group_header(sn2, RMNData.rmn_id, msg_id, "CLRG", "xxx")
        tx_info, _ = self.client.submit_return_transaction(RMNData.sec_key, tx_headers, tx_group_header, return_msg)
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, grpHdr.sttlmInf.clrSysCd has invalid value:xxx")
        tx_group_header["sttlmInf"] = {"sttlmMtd": "abcd", "clrSysCd": "ROXE"}
        tx_info, tx_msg = self.client.submit_return_transaction(RMNData.sec_key, tx_headers, tx_group_header, return_msg)
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, grpHdr.sttlmInf.sttlmMtd has invalid value:abcd")

    def test_196_error_submitReturn_decryptBody_chrgsInf_agtSchmeCdNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee = self.prepareFullySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn2, RMNData.api_key, "RPRN", msg_id)
        tx_group_header = self.client.make_group_header(sn2, RMNData.rmn_id, msg_id)
        return_msg["chrgsInf"][0]["agt"]["schmeCd"] = "1234"
        tx_info, _ = self.client.submit_return_transaction(RMNData.sec_key, tx_headers, tx_group_header, return_msg)
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, txInf.chrgsInf.0.agt.schmeCd is not valid")

    def test_197_error_submitReturn_decryptBody_xchgRateLengthLimit(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["xchgRate"] = "1.12345"
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, cdtTrfTxInf.xchgRate has invalid value:1.12345")

    def test_198_error_submitReturn_decryptBody_dbtrAndCdtr_prvtId_fieldsLengthLimit(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee = self.prepareFullySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn2, RMNData.api_key, "RPRN", msg_id)
        tx_group_header = self.client.make_group_header(sn2, RMNData.rmn_id, msg_id)
        dbtr_keys = [
            "nm:140",
            "pstlAdr.pstCd:35", "pstlAdr.twnNm:35", "pstlAdr.twnLctnNm:35", "pstlAdr.dstrctNm:35",
            "pstlAdr.ctrySubDvsn:35", "pstlAdr.adrLine:490",
            "prvtId.dtAndPlcOfBirth.prvcOfBirth:35",
            "prvtId.dtAndPlcOfBirth.cityOfBirth:35",
            "prvtId.othr.prtry:35", "prvtId.othr.id:35", "prvtId.othr.issr:35",
        ]
        for k in dbtr_keys:
            for user in ["dbtr", "cdtr"]:
                with self.subTest(f"{user}字段限制: {k}"):
                    tmp_body = copy.deepcopy(return_msg)
                    field, k_len = k.split(":")
                    g_v = ApiUtils.generateString(int(k_len) + 1)
                    tmp_d = ApiUtils.generateDict(field, g_v)
                    tmp_body["rtrChain"][user] = ApiUtils.deepUpdateDict(tmp_body["rtrChain"][user], tmp_d)
                    tx_info, tx_msg = self.client.submit_return_transaction(RMNData.sec_key, tx_headers, tx_group_header, tmp_body)
                    self.client.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, txInf.rtrChain.{user}.{field} has invalid value:{g_v}")

    def test_199_error_submitReturn_decryptBody_dbtrAndCdtr_prvtId_missingField(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee = self.prepareFullySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn2, RMNData.api_key, "RPRN", msg_id)
        tx_group_header = self.client.make_group_header(sn2, RMNData.rmn_id, msg_id)
        dbtr_keys = [
            "prvtId.dtAndPlcOfBirth.ctryOfBirth",
            "prvtId.dtAndPlcOfBirth.cityOfBirth",
            "prvtId.othr.prtry", "prvtId.othr.id",
        ]
        for k in dbtr_keys:
            for user in ["dbtr", "cdtr"]:
                with self.subTest(f"{user}缺少{k}"):
                    tmp_body = copy.deepcopy(return_msg)
                    field = k
                    tmp_d = ApiUtils.generateDict(field, None)
                    tmp_body["rtrChain"][user] = ApiUtils.deepUpdateDict(tmp_body["rtrChain"][user], tmp_d)
                    tx_info, tx_msg = self.client.submit_return_transaction(RMNData.sec_key, tx_headers, tx_group_header, tmp_body)
                    self.client.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, txInf.rtrChain.{user}.{field} is empty")

    def test_200_error_submitReturn_decryptBody_dbtrAndCdtr_orgId_fieldsLengthLimit(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee = self.prepareFullySettledTransaction(sn1, sn2, is_private=False)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn2, RMNData.api_key, "RPRN", msg_id)
        tx_group_header = self.client.make_group_header(sn2, RMNData.rmn_id, msg_id)
        dbtr_keys = [
            "orgId.lei:35",
            "orgId.othr.prtry:35", "orgId.othr.id:35", "orgId.othr.issr:35",
            "ctctDtls.phneNb:35", "ctctDtls.mobNb:35", "ctctDtls.emailAdr:128",
        ]
        for k in dbtr_keys:
            for user in ["dbtr", "cdtr"]:
                with self.subTest(f"{user}字段限制: {k}"):
                    tmp_body = copy.deepcopy(return_msg)
                    field, k_len = k.split(":")
                    g_v = ApiUtils.generateString(int(k_len) + 1)
                    tmp_d = ApiUtils.generateDict(field, g_v)
                    tmp_body["rtrChain"][user] = ApiUtils.deepUpdateDict(tmp_body["rtrChain"][user], tmp_d)
                    tx_info, tx_msg = self.client.submit_return_transaction(RMNData.sec_key, tx_headers, tx_group_header, tmp_body)
                    self.client.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, txInf.rtrChain.{user}.{field} has invalid value:{g_v}")

    def test_201_error_submitReturn_decryptBody_dbtrAndCdtr_orgId_missingField(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee = self.prepareFullySettledTransaction(sn1, sn2, is_private=False)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn2, RMNData.api_key, "RPRN", msg_id)
        tx_group_header = self.client.make_group_header(sn2, RMNData.rmn_id, msg_id)
        dbtr_keys = ["orgId.othr.prtry", "orgId.othr.id"]
        for k in dbtr_keys:
            for user in ["dbtr", "cdtr"]:
                with self.subTest(f"{user}缺少字段: {k}"):
                    tmp_body = copy.deepcopy(return_msg)
                    field = k
                    tmp_d = ApiUtils.generateDict(field, None)
                    tmp_body["rtrChain"][user] = ApiUtils.deepUpdateDict(tmp_body["rtrChain"][user], tmp_d)
                    tx_info, tx_msg = self.client.submit_return_transaction(RMNData.sec_key, tx_headers, tx_group_header, tmp_body)
                    self.client.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, txInf.rtrChain.{user}.{field} is empty")

    def test_202_error_submitReturn_decryptBody_account_fieldsLengthLimit(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee = self.prepareFullySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn2, RMNData.api_key, "RPRN", msg_id)
        tx_group_header = self.client.make_group_header(sn2, RMNData.rmn_id, msg_id)
        dbtr_keys = ["acctId:35", "tp:35", "iban:34", "nm:140"]
        for k in dbtr_keys:
            for act in ["dbtrAcct", "cdtrAcct"]:
                with self.subTest(f"{act}字段限制: {k}"):
                    tmp_body = copy.deepcopy(return_msg)
                    field, k_len = k.split(":")
                    g_v = ApiUtils.generateString(int(k_len) + 1)
                    tmp_body["rtrChain"][act][field] = g_v
                    tx_info, tx_msg = self.client.submit_return_transaction(RMNData.sec_key, tx_headers, tx_group_header, tmp_body)
                    if field == "iban":
                        self.client.checkCodeAndMessage(tx_info, "00600108", f"IBAN is wrong, txInf.rtrChain.{act}.iban has invalid value:{g_v}")
                    else:
                        self.client.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, txInf.rtrChain.{act}.{field} has invalid value:{g_v}")

    def test_203_error_submitReturn_decryptBody_dbtrAgt_issrNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee = self.prepareFullySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)
        return_msg["rtrChain"]["dbtrAgt"]["finInstnId"]["othr"]["issr"] = "XX"
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn2, RMNData.api_key, "RPRN", msg_id)
        tx_group_header = self.client.make_group_header(sn2, RMNData.rmn_id, msg_id)
        tx_info, tx_msg = self.client.submit_return_transaction(RMNData.sec_key, tx_headers, tx_group_header, return_msg)
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, txInf.rtrChain.dbtrAgt.finInstnId.othr.issr has invalid value:XX")

    def test_204_error_submitReturn_decryptBody_dbtrAgt_missingField(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee = self.prepareFullySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn2, RMNData.api_key, "RPRN", msg_id)
        tx_group_header = self.client.make_group_header(sn2, RMNData.rmn_id, msg_id)
        for k in ["id", "schmeCd"]:
            return_msg["rtrChain"]["dbtrAgt"]["finInstnId"]["othr"][k] = None
            tx_info, tx_msg = self.client.submit_return_transaction(RMNData.sec_key, tx_headers, tx_group_header, return_msg)
            self.client.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, txInf.rtrChain.dbtrAgt.finInstnId.othr.{k} is empty")

    def test_205_error_submitReturn_decryptBody_agent_fieldsLengthLimit(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent)
        pn1_fee = self.client.getTransactionFeeInDB(pn1, "USD", "in", "PN")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1)
        in_node = True if sn2 in RMNData.channel_nodes else False
        pn2_tx_info = self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=in_node)

        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", pn2_tx_info, sn2_fee)
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn2, RMNData.api_key, "RPRN", msg_id)
        tx_group_header = self.client.make_group_header(sn2, RMNData.rmn_id, msg_id)
        dbtr_keys = [
            "finInstnId.nm:140", "finInstnId.bicFI:11", "finInstnId.othr.id:12",
            "brnchId.nm:140", "brnchId.id:35", "brnchId.lei:35"
        ]
        for k in dbtr_keys:
            for agt in ["dbtrAgt", "dbtrIntrmyAgt", "cdtrAgt", "cdtrIntrmyAgt"]:
                with self.subTest(f"{agt}字段限制: {k}"):
                    tmp_body = copy.deepcopy(return_msg)
                    field, k_len = k.split(":")
                    g_v = ApiUtils.generateString(int(k_len) + 1)
                    tmp_d = ApiUtils.generateDict(field, g_v)
                    tmp_body["rtrChain"][agt] = ApiUtils.deepUpdateDict(tmp_body["rtrChain"][agt], tmp_d)
                    tx_info, tx_msg = self.client.submit_return_transaction(RMNData.sec_key, tx_headers, tx_group_header, tmp_body)
                    if field.endswith("bicFI"):
                        self.client.checkCodeAndMessage(tx_info, "00600106", f"SWIFT BIC is wrong, txInf.rtrChain.{agt}.{field} has invalid value:{g_v}")
                    else:
                        self.client.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, txInf.rtrChain.{agt}.{field} has invalid value:{g_v}")

    def test_206_error_submitReturn_decryptBody_dbtrIntrmyAgt_issrNotCorrect(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent)
        pn1_fee = self.client.getTransactionFeeInDB(pn1, "USD", "in", "PN")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1)
        in_node = True if sn2 in RMNData.channel_nodes else False
        pn2_tx_info = self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=in_node)

        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", pn2_tx_info, sn2_fee)
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn2, RMNData.api_key, "RPRN", msg_id)
        tx_group_header = self.client.make_group_header(sn2, RMNData.rmn_id, msg_id)
        return_msg["rtrChain"]["dbtrIntrmyAgt"]["finInstnId"]["othr"]["issr"] = "XX"
        tx_info, tx_msg = self.client.submit_return_transaction(RMNData.sec_key, tx_headers, tx_group_header, return_msg)
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, txInf.rtrChain.dbtrIntrmyAgt.finInstnId.othr.issr has invalid value:XX")

    def test_207_error_submitReturn_decryptBody_txInf_missingItems(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee = self.prepareFullySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)

        tx_headers = self.client.make_header(sn2, RMNData.api_key, "RPRN")
        tx_group_header = self.client.make_group_header(sn2, RMNData.rmn_id, tx_headers["msgId"])
        miss_fields = [
            "orgnlGrpInf.orgnlMsgId", "orgnlGrpInf.orgnlMsgNmId", "orgnlTxId", "orgnlGrpInf", "instgAgt", "instdAgt",
            "rtrdIntrBkSttlmAmt.ccy", "rtrdIntrBkSttlmAmt.amt", "rtrdIntrBkSttlmAmt",
            "rtrdInstdAmt.ccy", "rtrdInstdAmt.amt", "rtrdInstdAmt", "rtrRsnInf", "rtrChain", "rtrRsnInf.rsn",
            "rtrRsnInf.rsn.prtry", "rtrChain.dbtr", "rtrChain.cdtr", "rtrChain.dbtrAgt", "rtrChain.cdtrAgt"
        ]
        self.client.checkBodyFieldsMissing(miss_fields, self.client.submit_return_transaction, [RMNData.sec_key, tx_headers, tx_group_header, return_msg], 3, pre="txInf.")

    def test_208_error_submitReturn_decryptBody_other_fieldsLengthLimit(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee = self.prepareFullySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)

        tx_headers = self.client.make_header(sn2, RMNData.api_key, "RPRN")
        tx_group_header = self.client.make_group_header(sn2, RMNData.rmn_id, tx_headers["msgId"])
        fields_limit = [
            "orgnlGrpInf.orgnlMsgId:35", "orgnlGrpInf.orgnlMsgNmId:35", "orgnlTxId:35", "instgAgt:12", "instdAgt:12",
            "rtrRsnInf.rsn.prtry:140", "splmtryData.rmrk:140"
        ]
        self.client.checkBodyFieldsLengthLimit(fields_limit, self.client.submit_return_transaction, [RMNData.sec_key, tx_headers, tx_group_header, return_msg], 3, "txInf.")

    def test_209_error_getExchangeRate_headers_msgIdNotMatchVersion(self):
        sn1 = RMNData.sn_usd_us
        msg_id = self.client.make_msg_id()
        pre_env = "0" if self.client.env == "prod" else "1"
        msg_id = pre_env + msg_id[1:]
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RERQ", msg_id)
        msg_header = self.client.make_msg_header(sn1, msg_id)
        st_info, st_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", "100", "USD")
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.HEADER_MSGID_INVALID)


class RmnBusinessValidationTest(BaseCheckRMN):

    @classmethod
    def tearDownClass(cls) -> None:
        if RMNData.is_check_db:
            if not Global.getValue(settings.is_multiprocess):
                pass
                # cls.client.clearOrdersInDB()
            cls.client.mysql.disconnect_database()

    def test_001_error_submitTransaction_decryptBody_instdAmtCcyNotSameWithIntrBksttlmAmtCcy(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["intrBkSttlmAmt"]["ccy"] = "HKD"
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.SETTLEMENT_CCY_INCORRECT)

    def test_002_error_submitTransaction_decryptBody_instdAmtCcyNotSameWithSndrCcy(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["instdAmt"]["ccy"] = "HKD"
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, instd currency does not match sndrCcy")

    def test_003_error_submitTransaction_decryptBody_intrBkSttlmAmtAmtNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, 1, sn1)
        tmp_inf = copy.deepcopy(cdtTrfTxInf)
        tmp_inf["intrBkSttlmAmt"]["amt"] = "1"
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, tmp_inf)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.SETTLEMENT_AMT_INCORRECT)
        tmp_inf["chrgsInf"][0]["sndFeeAmt"]["amt"] = "1"
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, tmp_inf)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.SETTLEMENT_AMT_INCORRECT)

    def test_004_error_submitTransaction_decryptBody_endToEndIdIsRepeat(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        msg_id_2 = self.client.make_msg_id()
        tx_headers_2 = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id_2, "sign123")
        tx_group_header_2 = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id_2)
        cdtTrfTxInf2 = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, 1, pn1)
        cdtTrfTxInf2["pmtId"] = cdtTrfTxInf["pmtId"]
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers_2, tx_group_header_2, cdtTrfTxInf2)
        self.client.checkCodeAndMessage(tx_info)

    def test_005_error_submitTransaction_decryptBody_chrgsInf_ccyNotSameWithSndrCcy(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["chrgsInf"][0]["sndFeeAmt"]["ccy"] = "HKD"
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, sndFee currency does not match instd currency")

    def test_006_error_submitTransaction_decryptBody_chrgsInf_agtIdNotSameWithSender(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["chrgsInf"][0]["agt"]["id"] = pn2
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, agt.id:pn.test.gb in charge list is not correct")

    def test_007_error_submitTransaction_decryptBody_chrgsInf_chargeFeeNameIsNotSndFeeAmt(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["chrgsInf"] = [{"agt": {"id": pn1, "schmeCd": "ROXE"}, "dlvFeeAmt": {"amt": str(1), "ccy": "USD"}}]
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100000", f"Parameter exception, charge is supposed to be send fee charge")

    def test_008_error_submitTransaction_decryptBody_xchgRateNotCorrect(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["xchgRate"] = "120"
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

    def test_009_error_submitTransaction_decryptBody_dbtrAgtNotGiveRoxeId(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrAgt"] = RMNData.ncc_agents["USD"]
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, cdtTrfTxInf.dbtrAgt.finInstnId.othr.id is empty")

    def test_010_error_submitTransaction_decryptBody_dbtrAgt_issrNotCorrect(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100103", f"Business exception, cdtTrfTxInf.dbtrAgt.finInstnId.othr.issr is incorrect for id:{pn1}")

    def test_011_error_submitTransaction_decryptBody_dbtrIntrmyAgt_issrNotCorrect(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(RMNData.sn_usd_us, "PN")
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100103", f"Business exception, cdtTrfTxInf.dbtrIntrmyAgt.finInstnId.othr.issr is incorrect for id:{RMNData.sn_usd_us}")

    def test_012_error_submitTransaction_decryptBody_cdtrAgt_issrNotCorrect(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100103", f"Business exception, cdtTrfTxInf.cdtrAgt.finInstnId.othr.issr is incorrect for id:{pn2}")

    def test_013_error_submitTransaction_decryptBody_cdtrIntrmyAgt_issrNotCorrect(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(RMNData.sn_usd_gb, "PN")
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100103", f"Business exception, cdtTrfTxInf.cdtrIntrmyAgt.finInstnId.othr.issr is incorrect for id:{RMNData.sn_usd_gb}")

    def test_014_error_submitTransaction_decryptBody_noRouterPath(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "HKD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, 1, sn1)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.ROUTER_NOT_FIND)

    def test_015_error_submitSettlement_decryptBody_grpHdr_instdAgtNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1)
        
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("sn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(sn1, msg_id)

        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"])
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        st_grpHder["instdAgt"] = "29292929292x"
        tx_info, tx_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, st_grpHder, st_cdtInf)
        self.client.checkCodeAndMessage(tx_info)

    def test_016_error_submitSettlement_decryptBody_intrBksttlmAmt_ccyNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1)
        
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("sn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(sn1, msg_id)

        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"])
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        st_cdtInf["intrBkSttlmAmt"]["ccy"] = "CNY"
        tx_info, tx_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, st_grpHder, st_cdtInf)
        self.client.checkCodeAndMessage(tx_info,  RmnCodEnum.SETTLEMENT_CCY_INCORRECT)

    def test_017_error_submitSettlement_decryptBody_intrBksttlmAmt_amtNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1)
        
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("sn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(sn1, msg_id)

        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"])
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        st_cdtInf["intrBkSttlmAmt"]["amt"] = "1"
        tx_info, tx_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, st_grpHder, st_cdtInf)
        self.client.checkCodeAndMessage(tx_info, "00600110", f"Interbank settlement amount is incorrect")

    def test_018_error_submitSettlement_decryptBody_rmtInf_orgnlMsgIDNotMatchTransaction(self):
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1)
        
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("sn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(sn1, msg_id)

        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"])
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        st_cdtInf["rmtInf"]["orgnlMsgID"] = self.client.make_msg_id()
        tx_info, tx_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, st_grpHder, st_cdtInf)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.MSG_NOT_FIND)

    def test_019_error_submitSettlement_decryptBody_rmtInf_orgnlMsgTpNotMatchTransaction(self):
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1)
        
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("sn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(sn1, msg_id)

        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"])
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        st_cdtInf["rmtInf"]["orgnlMsgTp"] = "RCSR"
        tx_info, tx_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, st_grpHder, st_cdtInf)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.MSG_NOT_FIND)

    def test_020_error_submitSettlement_decryptBody_rmtInf_instgAgtNotMatchTransaction(self):
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1)
        
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("sn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(sn1, msg_id)

        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"])
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        st_cdtInf["rmtInf"]["instgAgt"] = pn2
        tx_info, tx_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, st_grpHder, st_cdtInf)
        self.client.checkCodeAndMessage(tx_info, "00600105", f"No matched message is found")

    def test_021_error_submitSettlement_decryptBody_submitTwice(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1)

        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        rmn_tx_id = tx_info["data"]["txId"]
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("sn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(sn1, msg_id)

        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"])
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        tx_info, tx_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, st_grpHder, st_cdtInf)
        self.client.checkCodeAndMessage(tx_info)
        self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, None, RMNData.api_key, RMNData.sec_key)
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"])
        tx_info2, tx_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, st_grpHder, st_cdtInf)
        self.client.checkCodeAndMessage(tx_info2, "00600112", "Original message has been settled and can not be settled again")

    def test_022_error_submitSettlement_decryptBody_submitWhenTransactionFinish(self):
        sn1 = RMNData.query_tx_info["nodeCode"]
        
        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"])
        st_cdtInf = {
            "intrBkSttlmAmt": {"amt": "10", "ccy": "USD"},
            "intrBkSttlmDt": "2022-02-18",
            "pmtId": {"endToEndId": self.client.make_end_to_end_id(), "txId": self.client.make_end_to_end_id()},
            "dbtr": self.client.make_roxe_agent(sn1, "SN"),
            "dbtrAcct": {"acctId": "123456789012", "nm": "Jethro Lee"},
            "cdtr": self.client.make_roxe_agent(RMNData.rmn_id, "SN"),
            "cdtrAcct": {"nm": "Li XX", "ccy": "USD", "acctId": "987654321"},
            "rmtInf": {"orgnlMsgID": RMNData.query_tx_info["msgId"], "orgnlMsgTp": "RCCT", "instgAgt": sn1},
            "splmtryData": {"envlp": {"ustrd": {"cdtDbtInd": "CRDT"}}}
        }
        tx_info, tx_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, st_grpHder, st_cdtInf)
        self.client.checkCodeAndMessage(tx_info, "00600112", "Original message has been settled and can not be settled again")

    def test_023_error_procConfirm_decryptBody_orgnlMsgIdNotMatchTransaction(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)

        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)
        rmn_tx_id = tx_info["data"]["txId"]

        self.client.logger.warning("pn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(pn1, msg_id, None, rmn_tx_id, RMNData.api_key, RMNData.sec_key,  "ACCEPTED_CONF_SENT")

        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, RMNData.api_key, RMNData.sec_key,  "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC")
        pc_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, pc_headers["msgId"], hasSttlmInf=False)
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        p_msg["orgnlGrpInfAndSts"]["orgnlMsgId"] = self.client.make_msg_id()
        pc_info, pc_msg = self.client.proc_confirm(RMNData.sec_key, pc_headers, pc_group_header, p_msg)
        self.client.checkCodeAndMessage(pc_info, RmnCodEnum.MSG_NOT_FIND)

    def test_024_error_procConfirm_decryptBody_orgnlMsgNmIdNotMatchTransaction(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)

        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)
        rmn_tx_id = tx_info["data"]["txId"]

        self.client.logger.warning("pn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(pn1, msg_id, None, rmn_tx_id, RMNData.api_key, RMNData.sec_key,  "ACCEPTED_CONF_SENT")

        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, RMNData.api_key, RMNData.sec_key,  "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC")
        pc_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, pc_headers["msgId"], hasSttlmInf=False)
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        p_msg["orgnlGrpInfAndSts"]["orgnlMsgNmId"] = "RCSR"
        pc_info, pc_msg = self.client.proc_confirm(RMNData.sec_key, pc_headers, pc_group_header, p_msg)
        self.client.checkCodeAndMessage(pc_info, RmnCodEnum.ORIGNAL_MSG_ERROR)

    def test_025_error_procConfirm_decryptBody_orgnlEndToEndIdNotMatchTransaction(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)

        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)
        rmn_tx_id = tx_info["data"]["txId"]

        self.client.logger.warning("pn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(pn1, msg_id, None, rmn_tx_id, RMNData.api_key, RMNData.sec_key,  "ACCEPTED_CONF_SENT")

        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, RMNData.api_key, RMNData.sec_key,  "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC")
        pc_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, pc_headers["msgId"], hasSttlmInf=False)
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        p_msg["txInfAndSts"]["orgnlEndToEndId"] = self.client.make_end_to_end_id()
        pc_info, pc_msg = self.client.proc_confirm(RMNData.sec_key, pc_headers, pc_group_header, p_msg)
        self.client.checkCodeAndMessage(pc_info, RmnCodEnum.MSG_NOT_FIND)

    def test_026_error_procConfirm_decryptBody_orgnlTxIdNotMatchTransaction(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)

        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)
        rmn_tx_id = tx_info["data"]["txId"]

        self.client.logger.warning("pn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(pn1, msg_id, None, rmn_tx_id, RMNData.api_key, RMNData.sec_key,  "ACCEPTED_CONF_SENT")

        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, RMNData.api_key, RMNData.sec_key,  "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC")
        pc_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, pc_headers["msgId"], hasSttlmInf=False)
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        p_msg["txInfAndSts"]["orgnlTxId"] = self.client.make_end_to_end_id()
        pc_info, pc_msg = self.client.proc_confirm(RMNData.sec_key, pc_headers, pc_group_header, p_msg)
        self.client.checkCodeAndMessage(pc_info, RmnCodEnum.MSG_NOT_FIND)

    def test_027_error_procConfirm_decryptBody_instgAgtNotMatchTransaction(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)

        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)
        rmn_tx_id = tx_info["data"]["txId"]

        self.client.logger.warning("pn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(pn1, msg_id, None, rmn_tx_id, RMNData.api_key, RMNData.sec_key,  "ACCEPTED_CONF_SENT")

        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, RMNData.api_key, RMNData.sec_key,  "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC")
        pc_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, pc_headers["msgId"], hasSttlmInf=False)
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        p_msg["txInfAndSts"]["instgAgt"] = pn2
        pc_info, pc_msg = self.client.proc_confirm(RMNData.sec_key, pc_headers, pc_group_header, p_msg)
        self.client.checkCodeAndMessage(pc_info, RmnCodEnum.MSG_NOT_FIND)

    def test_028_error_getExchangeRate_sndrCcyNotSupport(self):
        """
        查询交易状态，txId不存在
        """
        sender = RMNData.pn_usd_us
        
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        tx_info, req_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "CNY", "23", "USD")
        self.client.checkCodeAndMessage(tx_info, "00600109", "Currency pair is not supported")

    def test_029_error_getExchangeRate_rcvrCcyNotCorrect(self):
        """
        查询交易状态，txId不存在
        """
        sender = RMNData.pn_usd_us
        
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        tx_info, req_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", "10", "CNY")
        self.client.checkCodeAndMessage(tx_info, "00600109", "Currency pair is not supported")

    def test_030_error_getRouterList_decryptBody_issrNotMatchNodeId(self):
        """
        查询交易状态，txId不存在
        """
        sender = RMNData.pn_usd_us
        
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agt = self.client.make_roxe_agent(RMNData.pn_usd_gb, "SN")
        msg = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAgt=agt)

        st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.client.checkCodeAndMessage(st_info, "00100103", f"Business exception, rtgQryDef.qryCrit.cdtrAgt.finInstnId.othr.issr is incorrect for id:{RMNData.pn_usd_gb}")

    def test_031_error_getRouterList_decryptBody_sndrCcyNotSupport(self):
        """
        查询交易状态，txId不存在
        """
        sender = RMNData.pn_usd_us
        
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("CNY", "USD", "100", cdtrAgt=RMNData.bic_agents["USD"])

        st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.ROUTER_NOT_FIND)

    def test_032_error_getRouterList_decryptBody_rcvrCcyNotSupport(self):
        """
        查询交易状态，txId不存在
        """
        sender = RMNData.pn_usd_us
        
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("USD", "CNY", "100", cdtrAgt=RMNData.bic_agents["USD"])

        st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.ROUTER_NOT_FIND)

    def test_033_error_submitTransaction_dbtrAgtNotFindSNNode(self):
        pn1 = "pn_de_dm"
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, 0, pn1)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.ROUTER_NOT_FIND)

    def test_034_error_submitTransaction_cdtrAgtGivePNRoxeId_cdtrIntrmyAgtGivePNRoxeId(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100103", "Business exception, cdtTrfTxInf.cdtrIntrmyAgt is supposed to be a SN")

    def test_035_error_submitTransaction_cdtrAgtGivePNRoxeId_cdtrIntrmyAgtGiveNotMatchedSNRoxeId(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(RMNData.mock_node, "SN")
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.ROUTER_NOT_FIND)

    def test_036_error_submitTransaction_cdtrAgtGiveSNRoxeId_cdtrIntrmyAgtGivePNRoxeId(self):
        pn1 = RMNData.pn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00200011", "Existing multiple settlement nodes in credit chain of payment is not allowed.")

    def test_037_error_submitTransaction_cdtrAgtGiveSNRoxeId_cdtrIntrmyAgtGiveSNRoxeId(self):
        """
        提交交易请求
        """
        pn1 = RMNData.pn_usd_us
        sn2 = RMNData.sn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00200011", "Existing multiple settlement nodes in credit chain of payment is not allowed.")

    def test_038_error_submitTransaction_cdtrAgtGivePNRoxeId_cdtrIntrmyAgtNoRoxeId(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = RMNData.bic_agents["GBP"]
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100103", "Business exception, cdtTrfTxInf.cdtrIntrmyAgt is supposed to be a SN or null")

    def test_039_error_submitTransaction_cdtrAgtGivePNRoxeId_intrmyAgtGiveRoxeId(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(RMNData.sn_usd_gb, "SN")
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100103", "Business exception, intrmyAgt is not supposed to present")

    def test_040_error_submitTransaction_cdtrAgtGivePNRoxeId_cdtrIntrmyAgtNoRoxeId_intrmyAgtNoRoxeId(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = RMNData.ncc_agents["GBP"]
        cdtTrfTxInf["intrmyAgt"] = RMNData.bic_agents["GBP"]
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100103", "Business exception, intrmyAgt is not supposed to present")

    def test_041_error_submitTransaction_cdtrAgtGiveSNRoxeId_cdtrIntrmyAgtNoRoxeId_intrmyAgtNoRoxeId(self):
        pn1 = RMNData.pn_usd_us
        sn2 = RMNData.sn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = RMNData.ncc_agents["GBP"]
        cdtTrfTxInf["intrmyAgt"] = RMNData.bic_agents["GBP"]
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00200011", "Existing multiple settlement nodes in credit chain of payment is not allowed.")

    def test_042_error_submitTransaction_cdtrAcctGiveIban(self):
        pn1 = RMNData.pn_gbp_us
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.iban_agent
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, 0.5, pn1)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100103", "Business exception, one of bicFI or clrSysCd is supposed to present")

    def test_043_error_submitTransaction_cdtrIntrmyAgtGiveNotMatchedSNRoxeId(self):
        pn1 = RMNData.pn_usd_us
        # sn1 = RMNData.sn_usd_us
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["PHP"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "PHP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, 1, pn1)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(RMNData.mock_node, "SN")
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.ROUTER_NOT_FIND)

    def test_044_error_submitTransaction_cdtrIntrmyAgtGiveNotMatchedPNRoxeId(self):
        pn1 = RMNData.pn_usd_us
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent("pn_ru_usd", "PN")
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.ROUTER_NOT_FIND)

    def test_045_error_submitTransaction_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGivePNRoxeId(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(pn1, "PN")
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100103", "Business exception, cdtTrfTxInf.intrmyAgt is supposed to be a SN")

    def test_046_error_submitTransaction_cdtrIntrmyAgtGiveSNRoxeId_intrmyAgtGivePNRoxeId(self):
        pn1 = RMNData.pn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100103", "Business exception, intrmyAgt is not supposed to present")

    def test_047_error_submitTransaction_cdtrIntrmyAgtGiveSNRoxeId_intrmyAgtGiveSNRoxeId(self):
        pn1 = RMNData.pn_usd_us
        sn2 = RMNData.sn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100103", "Business exception, intrmyAgt is not supposed to present")

    def test_048_error_submitTransaction_cdtrIntrmyAgtGiveSNRoxeId_intrmyAgtGiveNotMatchedSNRoxeId(self):
        pn1 = RMNData.pn_usd_us
        # sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(RMNData.mock_node, "SN")
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.ROUTER_NOT_FIND)

    def test_049_error_submitTransaction_cdtrAgtNotFindSNNode(self):
        pn1 = RMNData.pn_usd_us
        pn2 = "pn_de_dm"
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.ROUTER_NOT_FIND)

    def test_050_error_getTransactionFlow_msgIdNotMatchMsgTp(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RATQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(
            RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"], ntryTp="ADT", msgTp="RTPC"
        )
        q_info, q_msg = self.client.get_transaction_flow(RMNData.sec_key, ts_headers, msg_header, txQryDef)

        self.client.checkCodeAndMessage(q_info, RmnCodEnum.TX_NOT_FIND)

    def test_051_error_getTransactionFlow_msgIdNotMatchEndToEndId(self):
        sn1 = RMNData.sn_usd_us
        
        e_id = self.client.make_end_to_end_id()
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RATQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(
            RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"], e_id, e_id, ntryTp="ADT"
        )
        q_info, q_msg = self.client.get_transaction_flow(RMNData.sec_key, ts_headers, msg_header, txQryDef)

        self.client.checkCodeAndMessage(q_info, RmnCodEnum.TX_NOT_FIND)

    def test_052_error_getTransactionFlow_msgIdNotMatchInstgPty(self):
        sn1 = RMNData.sn_usd_us
        
        instgPty = sn1 if RMNData.query_tx_info["nodeCode"] != sn1 else RMNData.mock_node
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RATQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(
            RMNData.query_tx_info["msgId"], instgPty, ntryTp="ADT"
        )
        q_info, q_msg = self.client.get_transaction_flow(RMNData.sec_key, ts_headers, msg_header, txQryDef)

        self.client.checkCodeAndMessage(q_info, RmnCodEnum.TX_NOT_FIND)

    def test_053_error_getTransactionFlow_msgIdNotMatchInstdPty(self):
        sn1 = RMNData.sn_usd_us
        
        instgPty = RMNData.query_tx_info["nodeCode"]
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RATQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(
            RMNData.query_tx_info["msgId"], instgPty, ntryTp="ADT", instdPty=instgPty
        )
        q_info, q_msg = self.client.get_transaction_flow(RMNData.sec_key, ts_headers, msg_header, txQryDef)

        self.client.checkCodeAndMessage(q_info, "00100103", "Business exception, instdPty should be RISN node code")

    def test_054_error_getTransactionFlow_msgIdNotExist(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RATQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(
            self.client.make_msg_id(), sn1, ntryTp="ADT"
        )
        q_info, q_msg = self.client.get_transaction_flow(RMNData.sec_key, ts_headers, msg_header, txQryDef)

        self.client.checkCodeAndMessage(q_info, RmnCodEnum.TX_NOT_FIND)

    def test_055_error_getTransactionStatus_msgIdNotMatchMsgTp(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RTSQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(
            RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"], msgTp="RTPC"
        )
        q_info, q_msg = self.client.get_transaction_status(RMNData.sec_key, ts_headers, msg_header, txQryDef)

        self.client.checkCodeAndMessage(q_info, RmnCodEnum.TX_NOT_FIND)

    def test_056_error_getTransactionStatus_msgIdNotMatchEndToEndId(self):
        sn1 = RMNData.sn_usd_us
        
        e_id = self.client.make_end_to_end_id()
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RTSQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(
            RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"], e_id, e_id
        )
        q_info, q_msg = self.client.get_transaction_status(RMNData.sec_key, ts_headers, msg_header, txQryDef)

        self.client.checkCodeAndMessage(q_info, RmnCodEnum.TX_NOT_FIND)

    def test_057_error_getTransactionStatus_msgIdNotMatchInstgPty(self):
        sn1 = RMNData.sn_usd_us
        
        instgPty = sn1 if RMNData.query_tx_info["nodeCode"] != sn1 else RMNData.mock_node
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RTSQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(RMNData.query_tx_info["msgId"], instgPty)
        q_info, q_msg = self.client.get_transaction_status(RMNData.sec_key, ts_headers, msg_header, txQryDef)

        self.client.checkCodeAndMessage(q_info, RmnCodEnum.TX_NOT_FIND)

    def test_058_error_getTransactionStatus_msgIdNotMatchInstdPty(self):
        sn1 = RMNData.sn_usd_us
        
        instgPty = RMNData.query_tx_info["nodeCode"]
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RTSQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(
            RMNData.query_tx_info["msgId"], instgPty, instdPty=instgPty
        )
        q_info, q_msg = self.client.get_transaction_status(RMNData.sec_key, ts_headers, msg_header, txQryDef)

        self.client.checkCodeAndMessage(q_info, "00100103", "Business exception, instdPty should be RISN node code")

    def test_059_error_getTransactionStatus_msgIdNotExist(self):
        sn1 = RMNData.sn_usd_us
        
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RTSQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(self.client.make_msg_id(), sn1)
        q_info, q_msg = self.client.get_transaction_status(RMNData.sec_key, ts_headers, msg_header, txQryDef)

        self.client.checkCodeAndMessage(q_info, RmnCodEnum.TX_NOT_FIND)

    def test_060_error_submitTransaction_decryptBody_chrgsInf_AmtNotCorrect(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, 2, pn1)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100103", f"Business exception, incorrect send fee for node:{pn1}")

    def test_061_error_submitTransaction_msgIdRepeat(self):
        pn1 = RMNData.pn_usd_us
        pn2 = RMNData.pn_usd_gb
        
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, 1, pn1)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100103", f"Business exception, Duplicate message ID:{msg_id}")

    def test_062_error_submitSettlement_msgIdRepeat(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1)

        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("sn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(sn1, msg_id)

        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"])
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        tx_info, tx_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, st_grpHder, st_cdtInf)
        self.client.checkCodeAndMessage(tx_info)
        tx_info, tx_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, st_grpHder, st_cdtInf)
        self.client.checkCodeAndMessage(tx_info, "00600112", "Original message has been settled and can not be settled again")

    def test_063_error_getTransactionStatus_msgIdNotMatchTxId(self):
        sn1 = RMNData.sn_usd_us
        
        e_id = self.client.make_end_to_end_id()
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RTSQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(
            RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"], e_id, RMNData.query_tx_info["endToEndId"]
        )
        q_info, q_msg = self.client.get_transaction_status(RMNData.sec_key, ts_headers, msg_header, txQryDef)

        self.client.checkCodeAndMessage(q_info, RmnCodEnum.TX_NOT_FIND)

    def test_064_error_getTransactionStatus_msgIdNotMatchInstrId(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1)
        cdtTrfTxInf["pmtId"]["instrId"] = self.client.make_end_to_end_id()
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RTSQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(
            msg_id, sn1, cdtTrfTxInf["pmtId"]["txId"], cdtTrfTxInf["pmtId"]["endToEndId"], self.client.make_end_to_end_id()
        )
        q_info, q_msg = self.client.get_transaction_status(RMNData.sec_key, ts_headers, msg_header, txQryDef)

        self.client.checkCodeAndMessage(q_info, RmnCodEnum.TX_NOT_FIND)

    def test_065_error_getTransactionStatus_msgIdNotMatchTxId(self):
        sn1 = RMNData.sn_usd_us
        
        e_id = self.client.make_end_to_end_id()
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RATQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(
            RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"], e_id, RMNData.query_tx_info["endToEndId"], ntryTp="ADT"
        )
        q_info, q_msg = self.client.get_transaction_flow(RMNData.sec_key, ts_headers, msg_header, txQryDef)

        self.client.checkCodeAndMessage(q_info, RmnCodEnum.TX_NOT_FIND)

    def test_066_error_getTransactionStatus_msgIdNotMatchInstrId(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1)
        cdtTrfTxInf["pmtId"]["instrId"] = self.client.make_end_to_end_id()
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RATQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(
            msg_id, sn1, cdtTrfTxInf["pmtId"]["txId"], cdtTrfTxInf["pmtId"]["endToEndId"], self.client.make_end_to_end_id(), ntryTp="ADT"
        )
        q_info, q_msg = self.client.get_transaction_flow(RMNData.sec_key, ts_headers, msg_header, txQryDef)

        self.client.checkCodeAndMessage(q_info, RmnCodEnum.TX_NOT_FIND)

    def test_067_error_submitSettlement_msgIdNotMatchRCCT(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1)

        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("sn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(sn1, msg_id)

        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"])
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        st_cdtInf["rmtInf"]["orgnlMsgID"] = RMNData.query_tx_info["msgId"].replace("2", "1")
        tx_info, tx_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, st_grpHder, st_cdtInf)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.MSG_NOT_FIND)

    def test_068_error_submitSettlement_msgTpNotMatchRCCT(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1)

        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("sn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(sn1, msg_id)

        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"])
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        st_cdtInf["rmtInf"]["orgnlMsgTp"] = "RFCT"
        tx_info, tx_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, st_grpHder, st_cdtInf)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.MSG_NOT_FIND)

    def test_069_error_submitSettlement_instgAgtNotMatchSender(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1)

        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("sn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(sn1, msg_id)

        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"])
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        st_cdtInf["rmtInf"]["instgAgt"] = RMNData.mock_node
        tx_info, tx_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, st_grpHder, st_cdtInf)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.MSG_NOT_FIND)

    def test_070_error_procConfirm_msgIdNotMatchRCCT(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)

        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("pn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(pn1, msg_id)

        rmn_tx_id = tx_info["data"]["txId"]
        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1)

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC", pc_msg_id)
        pc_group_header = self.client.make_group_header(sn1, "risn2roxe51", pc_msg_id, hasSttlmInf=False)
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        p_msg["orgnlGrpInfAndSts"]["orgnlMsgId"] = RMNData.query_tx_info["msgId"]
        pc_info, pc_msg = self.client.proc_confirm(RMNData.sec_key, pc_headers, pc_group_header, p_msg)
        self.client.checkCodeAndMessage(pc_info,  RmnCodEnum.MSG_NOT_FIND)

    def test_071_error_procConfirm_msgTpNotMatchRCCT(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)

        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("pn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(pn1, msg_id)

        rmn_tx_id = tx_info["data"]["txId"]
        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1)

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC", pc_msg_id)
        pc_group_header = self.client.make_group_header(sn1, "risn2roxe51", pc_msg_id, hasSttlmInf=False)
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        p_msg["orgnlGrpInfAndSts"]["orgnlMsgNmId"] = "RFCT"
        pc_info, pc_msg = self.client.proc_confirm(RMNData.sec_key, pc_headers, pc_group_header, p_msg)
        self.client.checkCodeAndMessage(pc_info, RmnCodEnum.ORIGNAL_MSG_ERROR)

    def test_072_error_procConfirm_orgnlEndToEndIdNotMatchRCCT(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)

        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("pn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(pn1, msg_id)

        rmn_tx_id = tx_info["data"]["txId"]
        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1)

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC", pc_msg_id)
        pc_group_header = self.client.make_group_header(sn1, "risn2roxe51", pc_msg_id, hasSttlmInf=False)
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        p_msg["txInfAndSts"]["orgnlEndToEndId"] = self.client.make_end_to_end_id()
        pc_info, pc_msg = self.client.proc_confirm(RMNData.sec_key, pc_headers, pc_group_header, p_msg)
        self.client.checkCodeAndMessage(pc_info, RmnCodEnum.MSG_NOT_FIND)

    def test_073_error_procConfirm_orgnlTxIdNotMatchRCCT(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)

        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("pn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(pn1, msg_id)

        rmn_tx_id = tx_info["data"]["txId"]
        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1)

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC", pc_msg_id)
        pc_group_header = self.client.make_group_header(sn1, "risn2roxe51", pc_msg_id, hasSttlmInf=False)
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        p_msg["txInfAndSts"]["orgnlTxId"] = self.client.make_end_to_end_id()
        pc_info, pc_msg = self.client.proc_confirm(RMNData.sec_key, pc_headers, pc_group_header, p_msg)
        self.client.checkCodeAndMessage(pc_info, RmnCodEnum.MSG_NOT_FIND)

    def test_074_error_procConfirm_instgAgtNotMatchRCCT(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)

        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("pn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(pn1, msg_id)

        rmn_tx_id = tx_info["data"]["txId"]
        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1)

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC", pc_msg_id)
        pc_group_header = self.client.make_group_header(sn1, "risn2roxe51", pc_msg_id, hasSttlmInf=False)
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        p_msg["txInfAndSts"]["instgAgt"] = sn1
        pc_info, pc_msg = self.client.proc_confirm(RMNData.sec_key, pc_headers, pc_group_header, p_msg)
        self.client.checkCodeAndMessage(pc_info, RmnCodEnum.MSG_NOT_FIND)

    def test_075_error_procConfirm_orgnlInstrIdNotMatchRCCT(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["pmtId"]["instrId"] = self.client.make_end_to_end_id()
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("pn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(pn1, msg_id)

        rmn_tx_id = tx_info["data"]["txId"]
        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1)

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC", pc_msg_id)
        pc_group_header = self.client.make_group_header(sn1, "risn2roxe51", pc_msg_id, hasSttlmInf=False)
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        p_msg["txInfAndSts"]["orgnlInstrId"] = self.client.make_end_to_end_id()
        pc_info, pc_msg = self.client.proc_confirm(RMNData.sec_key, pc_headers, pc_group_header, p_msg)
        self.client.checkCodeAndMessage(pc_info, RmnCodEnum.MSG_NOT_FIND)

    def test_076_error_procConfirm_instdAgtNotMatchRCCT(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 40)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["pmtId"]["instrId"] = self.client.make_end_to_end_id()
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("pn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(pn1, msg_id)

        rmn_tx_id = tx_info["data"]["txId"]
        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1)

        self.client.logger.warning("sn1节点发送confirm消息")
        pc_msg_id = self.client.make_msg_id()
        pc_headers = self.client.make_header(sn1, RMNData.api_key, "RTPC", pc_msg_id)
        pc_group_header = self.client.make_group_header(sn1, "risn2roxe512", pc_msg_id, hasSttlmInf=False)
        p_msg = self.client.make_RTPC_information(sn1_tx_info, "ACPT")
        pc_info, pc_msg = self.client.proc_confirm(RMNData.sec_key, pc_headers, pc_group_header, p_msg)
        self.client.checkCodeAndMessage(pc_info)  # 对于group header中的instdAgt不做强制校验，因为接收方就是RISN

    def test_077_error_submitSettlement_decryptBody_intrBksttlmAmt_amtCorrectButNotMatchRcct(self):
        sn1 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee + 1, sn1)

        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100103", f"Business exception, incorrect send fee for node:{sn1}")
        return
        self.client.logger.warning("sn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(sn1, msg_id)

        self.client.logger.warning("sn1节点提交结算请求")
        st_headers = self.client.make_header(sn1, RMNData.api_key, "RCSR")
        st_grpHder = self.client.make_group_header(sn1, RMNData.rmn_id, st_headers["msgId"])
        st_cdtInf = self.client.make_RCSR_information(tx_msg, "CRDT", sn1)
        st_cdtInf["intrBkSttlmAmt"]["amt"] = str(ApiUtils.parseNumberDecimal(float(st_cdtInf["intrBkSttlmAmt"]["amt"]) + 1, 2, True))
        tx_info, tx_msg = self.client.submit_settlement(RMNData.sec_key, st_headers, st_grpHder, st_cdtInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.waitNodeReceiveMessage(sn2, tx_info["data"]["txId"])

    def test_078_error_submitTransaction_decryptBody_chrgsInf_chargeFeeIsNotCorrect_sn_sn(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, 1, sn1)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100103", f"Business exception, incorrect send fee for node:{sn1}")

    def test_079_error_submitTransaction_decryptBody_chrgsInf_chargeFeeIsNotCorrect_pn_sn_sn(self):
        pn1 = RMNData.pn_usd_us
        sn2 = RMNData.sn_usd_gb
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, 2.1, pn1)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100103", f"Business exception, incorrect send fee for node:{pn1}")

    def test_080_error_submitTransaction_ewallet_cdtrIntrmyAgtGivePN_NORouter(self):
        sn1 = RMNData.rpp_node_usd2php
        # sn2 = RMNData.sn_php_ph
        # sn2 = "idlzjsbeza4m"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": "rich bank"}}
        cdtrAcct = {"schmeNm": {"prtry": "PH"}, "issr": "GCASH", "acctId": "09612803885", "ccy": "PHP"}
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "USD", "PHP", cdtrAcct=cdtrAcct, tp='EWALLET')
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "PHP", RMNData.prvtId, debtor_agent, RMNData.prvtId_b, creditor_agent, sn1_fee, sn1, cdtrAcct=cdtrAcct)
        cdtTrfTxInf["pmtTpInf"] = {"lclInstrm": {"cd": "EWALLET"}}
        cdtTrfTxInf["cdtr"]["nm"] = "Sean Warwick Dela Cruz"
        cdtTrfTxInf["cdtr"]["pstlAdr"]["ctry"] = "PH"
        cdtTrfTxInf["dbtr"]["prvtId"]["othr"]["prtry"] = "DRIVER_LICENSE"
        cdtTrfTxInf["splmtryData"]["addenda"]["senderSourceOfFund"] = "bank account"
        cdtTrfTxInf["splmtryData"]["addenda"]["receiverWalletCode"] = "GCASH"
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent("pn.ph.php", "PN")

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.ROUTER_NOT_FIND)

    def test_081_error_submitTransaction_ewallet_cdtrIntrmyAgtGiveBIC(self):
        sn1 = RMNData.rpp_node_usd2php
        # sn2 = RMNData.sn_php_ph
        # sn2 = "idlzjsbeza4m"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": "rich bank"}}
        cdtrAcct = {"schmeNm": {"prtry": "PH"}, "issr": "GCASH", "acctId": "09612803885", "ccy": "PHP"}
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "USD", "PHP", cdtrAcct=cdtrAcct, tp='EWALLET')
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "PHP", RMNData.prvtId, debtor_agent, RMNData.prvtId_b, creditor_agent, sn1_fee, sn1, cdtrAcct=cdtrAcct)
        cdtTrfTxInf["pmtTpInf"] = {"lclInstrm": {"cd": "EWALLET"}}
        cdtTrfTxInf["cdtr"]["nm"] = "Sean Warwick Dela Cruz"
        cdtTrfTxInf["cdtr"]["pstlAdr"]["ctry"] = "PH"
        cdtTrfTxInf["dbtr"]["prvtId"]["othr"]["prtry"] = "DRIVER_LICENSE"
        cdtTrfTxInf["splmtryData"]["addenda"]["senderSourceOfFund"] = "bank account"
        cdtTrfTxInf["splmtryData"]["addenda"]["receiverWalletCode"] = "GCASH"
        cdtTrfTxInf["cdtrIntrmyAgt"] = RMNData.bic_agents["PHP"]

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100103", f"Business exception, cdtrIntrmyAgt is supposed to be a Roxe node or null")

    def test_082_error_submitTransaction_ewallet_intrmyAgtGiveRoxeId(self):
        sn1 = RMNData.rpp_node_usd2php
        # sn2 = RMNData.sn_php_ph
        # sn2 = "idlzjsbeza4m"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": "rich bank"}}
        cdtrAcct = {"schmeNm": {"prtry": "PH"}, "issr": "GCASH", "acctId": "09612803885", "ccy": "PHP"}
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "USD", "PHP", cdtrAcct=cdtrAcct, tp='EWALLET')
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "PHP", RMNData.prvtId, debtor_agent, RMNData.prvtId_b, creditor_agent, sn1_fee, sn1, cdtrAcct=cdtrAcct)
        cdtTrfTxInf["pmtTpInf"] = {"lclInstrm": {"cd": "EWALLET"}}
        cdtTrfTxInf["cdtr"]["nm"] = "Sean Warwick Dela Cruz"
        cdtTrfTxInf["cdtr"]["pstlAdr"]["ctry"] = "PH"
        cdtTrfTxInf["dbtr"]["prvtId"]["othr"]["prtry"] = "DRIVER_LICENSE"
        cdtTrfTxInf["splmtryData"]["addenda"]["senderSourceOfFund"] = "bank account"
        cdtTrfTxInf["splmtryData"]["addenda"]["receiverWalletCode"] = "GCASH"
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100103", f"Business exception, intrmyAgt is supposed to be a Roxe node or null")

    def test_083_error_submitTransaction_ewallet_cdtrIntrmyAgtGivePN_intrmyAgtGivePN(self):
        sn1 = RMNData.rpp_node_usd2php
        # sn2 = RMNData.sn_php_ph
        # sn2 = "idlzjsbeza4m"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": "rich bank"}}
        cdtrAcct = {"schmeNm": {"prtry": "PH"}, "issr": "GCASH", "acctId": "09612803885", "ccy": "PHP"}
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "USD", "PHP", cdtrAcct=cdtrAcct, tp='EWALLET')
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "PHP", RMNData.prvtId, debtor_agent, RMNData.prvtId_b, creditor_agent, sn1_fee, sn1, cdtrAcct=cdtrAcct)
        cdtTrfTxInf["pmtTpInf"] = {"lclInstrm": {"cd": "EWALLET"}}
        cdtTrfTxInf["cdtr"]["nm"] = "Sean Warwick Dela Cruz"
        cdtTrfTxInf["cdtr"]["pstlAdr"]["ctry"] = "PH"
        cdtTrfTxInf["dbtr"]["prvtId"]["othr"]["prtry"] = "DRIVER_LICENSE"
        cdtTrfTxInf["splmtryData"]["addenda"]["senderSourceOfFund"] = "bank account"
        cdtTrfTxInf["splmtryData"]["addenda"]["receiverWalletCode"] = "GCASH"
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent("pn.test.ph", "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(RMNData.pn_usd_gb, "PN")

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100103", "Business exception, cdtTrfTxInf.intrmyAgt is supposed to be a SN")

    def test_084_error_submitTransaction_ewallet_cdtrIntrmyAgtGiveSN_intrmyAgtGiveSN(self):
        sn1 = RMNData.rpp_node_usd2php
        # sn2 = RMNData.sn_php_ph
        # sn2 = "idlzjsbeza4m"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": "rich bank"}}
        cdtrAcct = {"schmeNm": {"prtry": "PH"}, "issr": "GCASH", "acctId": "09612803885", "ccy": "PHP"}
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "USD", "PHP", cdtrAcct=cdtrAcct, tp='EWALLET')
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "PHP", RMNData.prvtId, debtor_agent, RMNData.prvtId_b, creditor_agent, sn1_fee, sn1, cdtrAcct=cdtrAcct)
        cdtTrfTxInf["pmtTpInf"] = {"lclInstrm": {"cd": "EWALLET"}}
        cdtTrfTxInf["cdtr"]["nm"] = "Sean Warwick Dela Cruz"
        cdtTrfTxInf["cdtr"]["pstlAdr"]["ctry"] = "PH"
        cdtTrfTxInf["dbtr"]["prvtId"]["othr"]["prtry"] = "DRIVER_LICENSE"
        cdtTrfTxInf["splmtryData"]["addenda"]["senderSourceOfFund"] = "bank account"
        cdtTrfTxInf["splmtryData"]["addenda"]["receiverWalletCode"] = "GCASH"
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100103", "Business exception, intrmyAgt is not supposed to present")

    def test_085_error_submitTransaction_ewallet_cdtrAcct_prtry_noRouter(self):
        sn1 = RMNData.rpp_node_usd2php
        # sn2 = RMNData.sn_php_ph
        # sn2 = "idlzjsbeza4m"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": "rich bank"}}
        cdtrAcct = {"schmeNm": {"prtry": "PH"}, "issr": "GCASH", "acctId": "09612803885", "ccy": "PHP"}
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "USD", "PHP", cdtrAcct=cdtrAcct, tp='EWALLET')
        cdtrAcct["schmeNm"]["prtry"] = "US"
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "PHP", RMNData.prvtId, debtor_agent, RMNData.prvtId_b, creditor_agent, sn1_fee, sn1, cdtrAcct=cdtrAcct)
        cdtTrfTxInf["pmtTpInf"] = {"lclInstrm": {"cd": "EWALLET"}}
        cdtTrfTxInf["cdtr"]["nm"] = "Sean Warwick Dela Cruz"
        cdtTrfTxInf["cdtr"]["pstlAdr"]["ctry"] = "PH"
        cdtTrfTxInf["dbtr"]["prvtId"]["othr"]["prtry"] = "DRIVER_LICENSE"
        cdtTrfTxInf["splmtryData"]["addenda"]["senderSourceOfFund"] = "bank account"
        cdtTrfTxInf["splmtryData"]["addenda"]["receiverWalletCode"] = "GCASH"

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.ROUTER_NOT_FIND)

    def test_086_error_submitTransaction_ewallet_cdtrAcct_issr_noRouter(self):
        sn1 = RMNData.rpp_node_usd2php
        # sn2 = RMNData.sn_php_ph
        # sn2 = "idlzjsbeza4m"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": "rich bank"}}
        cdtrAcct = {"schmeNm": {"prtry": "PH"}, "issr": "GCASH", "acctId": "09612803885", "ccy": "PHP"}
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "USD", "PHP", cdtrAcct=cdtrAcct, tp='EWALLET')
        cdtrAcct["issr"] = "PAYPAL"
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "PHP", RMNData.prvtId, debtor_agent, RMNData.prvtId_b, creditor_agent, sn1_fee, sn1, cdtrAcct=cdtrAcct)
        cdtTrfTxInf["pmtTpInf"] = {"lclInstrm": {"cd": "EWALLET"}}
        cdtTrfTxInf["cdtr"]["nm"] = "Sean Warwick Dela Cruz"
        cdtTrfTxInf["cdtr"]["pstlAdr"]["ctry"] = "PH"
        cdtTrfTxInf["dbtr"]["prvtId"]["othr"]["prtry"] = "DRIVER_LICENSE"
        cdtTrfTxInf["splmtryData"]["addenda"]["senderSourceOfFund"] = "bank account"
        cdtTrfTxInf["splmtryData"]["addenda"]["receiverWalletCode"] = "GCASH"

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, RmnCodEnum.ROUTER_NOT_FIND)

    def test_087_error_submitTransaction_ewallet_cdtrAcct_issr_notCorrect(self):
        sn1 = RMNData.rpp_node_usd2php
        # sn2 = RMNData.sn_php_ph
        # sn2 = "idlzjsbeza4m"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": "rich bank"}}
        cdtrAcct = {"schmeNm": {"prtry": "PH"}, "issr": "GCASH", "acctId": "09612803885", "ccy": "PHP"}
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "USD", "PHP", cdtrAcct=cdtrAcct, tp='EWALLET')
        cdtrAcct["issr"] = "APPLEPAYXX"
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "PHP", RMNData.prvtId, debtor_agent, RMNData.prvtId_b, creditor_agent, sn1_fee, sn1, cdtrAcct=cdtrAcct)
        cdtTrfTxInf["pmtTpInf"] = {"lclInstrm": {"cd": "EWALLET"}}
        cdtTrfTxInf["cdtr"]["nm"] = "Sean Warwick Dela Cruz"
        cdtTrfTxInf["cdtr"]["pstlAdr"]["ctry"] = "PH"
        cdtTrfTxInf["dbtr"]["prvtId"]["othr"]["prtry"] = "DRIVER_LICENSE"
        cdtTrfTxInf["splmtryData"]["addenda"]["senderSourceOfFund"] = "bank account"
        cdtTrfTxInf["splmtryData"]["addenda"]["receiverWalletCode"] = "GCASH"

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, cdtTrfTxInf.cdtrAcct.issr has invalid e-wallet code")

    def test_088_error_submitTransaction_ewallet_cdtrAcct_prtry_noRouter(self):
        sn1 = RMNData.sn_usd_us
        # sn2 = RMNData.sn_php_ph
        # sn2 = "idlzjsbeza4m"
        cdtrAcct = {"schmeNm": {"prtry": "US"}, "issr": "GCASH", "acctId": "09612803885", "ccy": "PHP"}
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("USD", "PHP", "100", cdtrAcct=cdtrAcct)
        msg["pmtTpInf"] = {"lclInstrm": {"cd": "EWALLET"}}

        st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.ROUTER_NOT_FIND)

    def test_089_error_submitTransaction_ewallet_cdtrAcct_issr_noRouter(self):
        sn1 = RMNData.sn_usd_us
        # sn2 = RMNData.sn_php_ph
        # sn2 = "idlzjsbeza4m"
        cdtrAcct = {"schmeNm": {"prtry": "PH"}, "issr": "PAYPAL", "acctId": "09612803885", "ccy": "PHP"}
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("USD", "PHP", "100", cdtrAcct=cdtrAcct)
        msg["pmtTpInf"] = {"lclInstrm": {"cd": "EWALLET"}}

        st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.client.checkCodeAndMessage(st_info, RmnCodEnum.ROUTER_NOT_FIND)

    def test_090_error_submitTransaction_ewallet_cdtrAcct_issr_notCorrect(self):
        sn1 = RMNData.sn_usd_us
        # sn2 = RMNData.sn_php_ph
        # sn2 = "idlzjsbeza4m"
        cdtrAcct = {"schmeNm": {"prtry": "PH"}, "issr": "APPLEPAYXX", "acctId": "09612803885", "ccy": "PHP"}
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("USD", "PHP", "100", cdtrAcct=cdtrAcct)
        msg["pmtTpInf"] = {"lclInstrm": {"cd": "EWALLET"}}

        st_info, st_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.client.checkCodeAndMessage(st_info, "00100000", "Parameter exception, rtgQryDef.qryCrit.cdtrAcct.issr has invalid e-wallet code")


class RmnRejectReturnTest(BaseCheckRMN):

    is_concurrency = Global.getValue(settings.is_multiprocess)

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        # cls.chain_client = Clroxe(RMNData.chain_host)

    def tearDown(self):
        print(self.is_concurrency)
        if RMNData.env == "uat":
            uat_url = "http://172.17.3.95:8006/api/rmn/receiveNotify"
            u_sql = f"update roxe_risn_config.risn_node set node_callback_url='{uat_url}' where node_callback_url<>'{uat_url}'"
            self.client.mysql.exec_sql_query(u_sql)

    def test_001_error_sn1SendRejectRTPC_hitAML(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, 1, pn1)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("pn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(pn1, msg_id, None, msg_id, RMNData.api_key, RMNData.sec_key,
                                           "ACCEPTED_CONF_SENT")

        rmn_tx_id = tx_info["data"]["txId"]
        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, pn1, msg_id, RMNData.api_key,
                                                                RMNData.sec_key, "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        stsRsnInf = {"addtlInf": "hit AML", "stsRsnCd": "00600104"}
        self.client.step_sendRTPC(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)

        pn_notify_info = self.client.waitNodeReceiveMessage(pn1, msg_id, "RJCT", msg_id, RMNData.api_key,
                                                            RMNData.sec_key, "DEBIT_TXN_REJECTED")
        time.sleep(10)
        self.client.checkTransactionState(rmn_tx_id, "TRANSACTION_REJECTED")
        sn_msg_id = sn1_tx_info["grpHdr"]["msgId"] if RMNData.is_check_db else sn1_tx_info["msgId"]
        state_info = self.client.step_queryTransactionState(sn1, RMNData.api_key, RMNData.sec_key, sn_msg_id,
                                                            RMNData.rmn_id)
        flow_info = self.client.step_queryTransactionFlow(sn1, RMNData.api_key, RMNData.sec_key, sn_msg_id,
                                                          RMNData.rmn_id)

        self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "RJCT")
        # 校验flow中reject状态
        self.client.checkExpectFlowState(["DEBIT_TXN_REJECTED", "TRANSACTION_REJECTED"], flow_info, rmn_tx_id)
        # 校验PN收到reject的RTPC消息
        self.assertEqual(pn_notify_info["txInfAndSts"]["stsId"], "RJCT")
        # 校验rts系统中订单状态
        self.client.checkNotNormalOrderInRTS(rmn_tx_id, "TRANSACTION_REJECT", "sn1", sn1, "fail")

    def test_002_error_sn1SendRejectRTPC_positionNotEnough(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, 1, pn1)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("pn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(pn1, msg_id)

        rmn_tx_id = tx_info["data"]["txId"]
        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1)

        self.client.logger.warning("sn1节点发送confirm消息")
        stsRsnInf = {"addtlInf": "PN position not enough in SN", "stsRsnCd": "00400103"}
        self.client.step_sendRTPC(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)

        pn_notify_info = self.client.waitNodeReceiveMessage(pn1, msg_id, "RJCT")
        time.sleep(5)
        self.client.checkTransactionState(rmn_tx_id, "TRANSACTION_REJECTED")

        state_info = self.client.step_queryTransactionState(sn1, RMNData.api_key, RMNData.sec_key,
                                                            sn1_tx_info["grpHdr"]["msgId"], RMNData.rmn_id)
        flow_info = self.client.step_queryTransactionFlow(sn1, RMNData.api_key, RMNData.sec_key,
                                                          sn1_tx_info["grpHdr"]["msgId"], RMNData.rmn_id)

        self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "RJCT")
        # 校验flow中reject状态
        self.client.checkExpectFlowState(["DEBIT_TXN_REJECTED", "TRANSACTION_REJECTED"], flow_info, rmn_tx_id)
        # 校验PN收到reject的RTPC消息
        self.assertEqual(pn_notify_info["txInfAndSts"]["stsId"], "RJCT")
        # 校验rts系统中订单状态
        self.client.checkNotNormalOrderInRTS(rmn_tx_id, "TRANSACTION_REJECT", "sn1", sn1, "fail")

    def test_003_error_sn2SendRejectRTPC_accountError_pn_sn_sn(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(20, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "B2B")["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt, cd="B2B")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.orgId, debtor_agent, RMNData.orgId_b,
                                                        creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrAcct"]["nm"] = "张三"
        cdtTrfTxInf["cdtrAcct"]["nm"] = "李四"
        cdtTrfTxInf["pmtId"]["instrId"] = str(int(time.time()))
        cdtTrfTxInf["dbtr"]["pstlAdr"]["dstrctNm"] = "god street 12"
        cdtTrfTxInf["dbtr"]["pstlAdr"]["ctrySubDvsn"] = "axb"
        cdtTrfTxInf["dbtr"]["pstlAdr"]["ctry"] = "US"
        cdtTrfTxInf["dbtr"]["pstlAdr"]["adrLine"] = "abcd 1234 abcd XXXX"
        # cdtTrfTxInf["dbtr"]["prvtId"]["dtAndPlcOfBirth"]["birthDt"] = "1960-05-24"
        cdtTrfTxInf["dbtr"]["ctctDtls"] = {"phneNb": "123423112", "mobNb": "1234567890123",
                                           "emailAdr": "abc@sample.mail.com"}
        cdtTrfTxInf["cdtr"]["ctctDtls"] = {"phneNb": "123-123-123", "mobNb": "1143-134-256",
                                           "emailAdr": "asd232@sample.mail.com"}
        cdtTrfTxInf["purp"] = {"cd": "123", "desc": "transfer money"}
        cdtTrfTxInf["rltnShp"] = {"cd": "457", "desc": "transfer money"}
        cdtTrfTxInf["splmtryData"]["rmrk"] = "iron man"
        cdtTrfTxInf["splmtryData"]["addenda"] = {"hello": "world", "tel": "123412341234"}
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("pn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(pn1, msg_id, None, msg_id, RMNData.api_key, RMNData.sec_key,
                                           "ACCEPTED_CONF_SENT")

        rmn_tx_id = tx_info["data"]["txId"]
        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None, pn1, msg_id, RMNData.api_key,
                                                                RMNData.sec_key, "DEBIT_TXN_SENT")

        self.client.logger.warning("sn1节点发送confirm消息")
        self.client.step_sendRTPC(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info)
        time.sleep(3)
        self.client.logger.warning("sn1节点提交结算请求并等待接收confirm消息")
        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info, rmn_tx_id, "CRDT", self, sn1_fee)

        self.client.logger.warning("sn2节点收到交易请求")
        sn1_tx_msg_id = sn1_tx_info["grpHdr"]["msgId"] if RMNData.is_check_db else sn1_tx_info["msgId"]
        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, sn1_tx_msg_id, pn1, msg_id,
                                                                RMNData.api_key, RMNData.sec_key, "CREDIT_SN_TXN_SENT")

        self.client.logger.warning("sn2节点发送confirm消息")
        stsRsnInf = {"addtlInf": "Beneficiary account error", "stsRsnCd": "00600114"}
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)

        finish_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='PENDING'"
        ApiUtils.waitCondition(self.client.mysql.exec_sql_query, (finish_sql,), lambda x: len(x) > 0, 120, 5)

        sn_msg_id = sn1_tx_info["grpHdr"]["msgId"] if RMNData.is_check_db else sn1_tx_info["msgId"]
        state_info = self.client.step_queryTransactionState(sn1, RMNData.api_key, RMNData.sec_key, sn_msg_id,
                                                            RMNData.rmn_id)
        flow_info = self.client.step_queryTransactionFlow(sn1, RMNData.api_key, RMNData.sec_key, sn_msg_id,
                                                          RMNData.rmn_id)
        self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "PDNG")
        # 校验flow中reject状态
        self.client.checkExpectFlowState("PENDING", flow_info, rmn_tx_id)
        # 校验rts系统中订单状态
        self.client.checkNotNormalOrderInRTS(rmn_tx_id, "REDEEM_SUBMIT", "sn2", sn2, "init")

        pendingMsg = "{},{}".format(stsRsnInf["stsRsnCd"], stsRsnInf["addtlInf"])
        self.checkPendingTransactionReason(rmn_tx_id, msg_id, pn1, cdtTrfTxInf["pmtId"]["endToEndId"], pendingMsg)

    def test_004_error_sn2SendRejectRTPC_informationError_pn_sn_sn(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, 1, pn1)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("pn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(pn1, msg_id)

        rmn_tx_id = tx_info["data"]["txId"]
        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1)

        self.client.logger.warning("sn1节点发送confirm消息")
        self.client.step_sendRTPC(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info)
        time.sleep(3)
        self.client.logger.warning("sn1节点提交结算请求并等待接收confirm消息")
        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info, rmn_tx_id, "CRDT", self, sn1_fee)

        self.client.logger.warning("sn2节点收到交易请求")
        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, sn1_tx_info["grpHdr"]["msgId"])

        self.client.logger.warning("sn2节点发送confirm消息")
        stsRsnInf = {"addtlInf": "Beneficiary information error", "stsRsnCd": "00600120"}
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)

        finish_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='PENDING'"
        ApiUtils.waitCondition(self.client.mysql.exec_sql_query, (finish_sql,), lambda x: len(x) > 0, 120, 5)

        state_info = self.client.step_queryTransactionState(sn1, RMNData.api_key, RMNData.sec_key,
                                                            sn1_tx_info["grpHdr"]["msgId"], RMNData.rmn_id)
        flow_info = self.client.step_queryTransactionFlow(sn1, RMNData.api_key, RMNData.sec_key,
                                                          sn1_tx_info["grpHdr"]["msgId"], RMNData.rmn_id)

        self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "PDNG")
        # 校验flow中reject状态
        self.client.checkExpectFlowState("PENDING", flow_info, rmn_tx_id)
        # 校验rts系统中订单状态
        self.client.checkNotNormalOrderInRTS(rmn_tx_id, "REDEEM_SUBMIT", "sn2", sn2, "init")

        pendingMsg = "{},{}".format(stsRsnInf["stsRsnCd"], stsRsnInf["addtlInf"])
        self.checkPendingTransactionReason(rmn_tx_id, msg_id, pn1, cdtTrfTxInf["pmtId"]["endToEndId"], pendingMsg)

    def test_005_error_sn2SendRejectRTPC_hitAML_pn_sn_sn(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, 1, pn1)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("pn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(pn1, msg_id)

        rmn_tx_id = tx_info["data"]["txId"]
        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1)

        self.client.logger.warning("sn1节点发送confirm消息")
        self.client.step_sendRTPC(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info)
        time.sleep(3)
        self.client.logger.warning("sn1节点提交结算请求并等待接收confirm消息")
        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info, rmn_tx_id, "CRDT", self, sn1_fee)

        self.client.logger.warning("sn2节点收到交易请求")
        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, sn1_tx_info["grpHdr"]["msgId"])

        self.client.logger.warning("sn2节点发送confirm消息")
        stsRsnInf = {"addtlInf": "report hit AML", "stsRsnCd": "00600104"}
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)

        finish_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='PENDING'"
        ApiUtils.waitCondition(self.client.mysql.exec_sql_query, (finish_sql,), lambda x: len(x) > 0, 120, 5)

        state_info = self.client.step_queryTransactionState(sn1, RMNData.api_key, RMNData.sec_key,
                                                            sn1_tx_info["grpHdr"]["msgId"], RMNData.rmn_id)
        flow_info = self.client.step_queryTransactionFlow(sn1, RMNData.api_key, RMNData.sec_key,
                                                          sn1_tx_info["grpHdr"]["msgId"], RMNData.rmn_id)
        self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "PDNG")
        # 校验flow中reject状态
        self.client.checkExpectFlowState("PENDING", flow_info, rmn_tx_id)
        # 校验rts系统中订单状态
        self.client.checkNotNormalOrderInRTS(rmn_tx_id, "REDEEM_SUBMIT", "sn2", sn2, "init")

        pendingMsg = "{},{}".format(stsRsnInf["stsRsnCd"], stsRsnInf["addtlInf"])
        self.checkPendingTransactionReason(rmn_tx_id, msg_id, pn1, cdtTrfTxInf["pmtId"]["endToEndId"], pendingMsg)

    def test_006_error_sn2SendRejectRTPC_accountError_sn_sn(self):
        # pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("sn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(sn1, msg_id)

        rmn_tx_id = tx_info["data"]["txId"]
        time.sleep(3)
        self.client.logger.warning("sn1节点提交结算请求并等待接收confirm消息")
        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, tx_msg, rmn_tx_id, "CRDT", self)

        self.client.logger.warning("sn2节点收到交易请求")
        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, msg_id)

        self.client.logger.warning("sn2节点发送confirm消息")
        stsRsnInf = {"addtlInf": "Beneficiary account error", "stsRsnCd": "00600114"}
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)

        finish_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='PENDING'"
        ApiUtils.waitCondition(self.client.mysql.exec_sql_query, (finish_sql,), lambda x: len(x) > 0, 120, 5)

        state_info = self.client.step_queryTransactionState(sn1, RMNData.api_key, RMNData.sec_key, msg_id, sn1)
        flow_info = self.client.step_queryTransactionFlow(sn1, RMNData.api_key, RMNData.sec_key, msg_id, sn1)

        self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "PDNG")
        # 校验flow中reject状态
        self.client.checkExpectFlowState("PENDING", flow_info, rmn_tx_id)
        # 校验rts系统中订单状态
        self.client.checkNotNormalOrderInRTS(rmn_tx_id, "REDEEM_SUBMIT", "sn2", sn2, "init")

        pendingMsg = "{},{}".format(stsRsnInf["stsRsnCd"], stsRsnInf["addtlInf"])
        self.checkPendingTransactionReason(rmn_tx_id, msg_id, sn1, cdtTrfTxInf["pmtId"]["endToEndId"], pendingMsg)

    def test_007_error_sn2SendRejectRTPC_informationError_sn_sn(self):
        # pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        # creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("sn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(sn1, msg_id)

        rmn_tx_id = tx_info["data"]["txId"]

        time.sleep(3)
        self.client.logger.warning("sn1节点提交结算请求并等待接收confirm消息")
        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, tx_msg, rmn_tx_id, "CRDT", self)

        self.client.logger.warning("sn2节点收到交易请求")
        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, msg_id)

        self.client.logger.warning("sn2节点发送confirm消息")
        stsRsnInf = {"addtlInf": "Beneficiary information error", "stsRsnCd": "00600120"}
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)

        finish_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='PENDING'"
        ApiUtils.waitCondition(self.client.mysql.exec_sql_query, (finish_sql,), lambda x: len(x) > 0, 120, 5)

        state_info = self.client.step_queryTransactionState(sn1, RMNData.api_key, RMNData.sec_key, msg_id, sn1)
        flow_info = self.client.step_queryTransactionFlow(sn1, RMNData.api_key, RMNData.sec_key, msg_id, sn1)

        self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "PDNG")
        # 校验flow中reject状态
        self.client.checkExpectFlowState("PENDING", flow_info, rmn_tx_id)
        # 校验rts系统中订单状态
        self.client.checkNotNormalOrderInRTS(rmn_tx_id, "REDEEM_SUBMIT", "sn2", sn2, "init")

    def test_008_error_sn2SendRejectRTPC_hitAML_sn_sn(self):
        # pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId_b,
                                                        creditor_agent, sn1_fee, sn1)
        cdtTrfTxInf["dbtrAcct"]["nm"] = "张三"
        cdtTrfTxInf["cdtrAcct"]["nm"] = "李四"
        cdtTrfTxInf["pmtId"]["instrId"] = str(int(time.time()))
        cdtTrfTxInf["dbtr"]["ctctDtls"] = {"phneNb": "123423112", "mobNb": "1234567890123", "emailAdr": "abc@sample.mail.com"}
        cdtTrfTxInf["cdtr"]["ctctDtls"] = {"phneNb": "123-123-123", "mobNb": "1143-134-256", "emailAdr": "asd232@sample.mail.com"}
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("sn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(sn1, msg_id)

        rmn_tx_id = tx_info["data"]["txId"]
        time.sleep(3)
        self.client.logger.warning("sn1节点提交结算请求并等待接收confirm消息")
        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, tx_msg, rmn_tx_id, "CRDT", self)

        self.client.logger.warning("sn2节点收到交易请求")
        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, msg_id)

        self.client.logger.warning("sn2节点发送confirm消息")
        stsRsnInf = {"addtlInf": "report hit AML", "stsRsnCd": "00600104"}
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)

        finish_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='PENDING'"
        ApiUtils.waitCondition(self.client.mysql.exec_sql_query, (finish_sql,), lambda x: len(x) > 0, 120, 5)

        state_info = self.client.step_queryTransactionState(sn1, RMNData.api_key, RMNData.sec_key, msg_id, sn1)
        flow_info = self.client.step_queryTransactionFlow(sn1, RMNData.api_key, RMNData.sec_key, msg_id, sn1)

        self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "PDNG")
        # 校验flow中reject状态
        self.client.checkExpectFlowState("PENDING", flow_info, rmn_tx_id)
        # 校验rts系统中订单状态
        self.client.checkNotNormalOrderInRTS(rmn_tx_id, "REDEEM_SUBMIT", "sn2", sn2, "init")

    def test_009_error_sn2SendRejectRTPC_accountError_sn_sn_pn(self):
        # pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(20, 2, 10)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt, cd="B2B")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.orgId, debtor_agent, RMNData.orgId_b,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)
        cdtTrfTxInf["dbtrAcct"]["nm"] = "张三"
        cdtTrfTxInf["cdtrAcct"]["nm"] = "李四"
        cdtTrfTxInf["cdtrAgt"]["brnchId"] = {"nm": "test 1", "id": "a123d", "lei": "lei1234"}
        cdtTrfTxInf["dbtrAgt"]["brnchId"] = {"nm": "test debitor agent", "id": "12341sa", "lei": "lei12345"}
        cdtTrfTxInf["pmtId"]["instrId"] = str(int(time.time()))
        cdtTrfTxInf["dbtr"]["ctctDtls"] = {"phneNb": "123423112", "mobNb": "1234567890123",
                                           "emailAdr": "abc@sample.mail.com"}
        cdtTrfTxInf["cdtr"]["ctctDtls"] = {"phneNb": "123-123-123", "mobNb": "1143-134-256",
                                           "emailAdr": "asd232@sample.mail.com"}
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("sn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(sn1, msg_id)

        rmn_tx_id = tx_info["data"]["txId"]
        time.sleep(3)
        self.client.logger.warning("sn1节点提交结算请求并等待接收confirm消息")
        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, tx_msg, rmn_tx_id, "CRDT", self)

        self.client.logger.warning("sn2节点收到交易请求")
        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, msg_id)

        self.client.logger.warning("sn2节点发送confirm消息")
        stsRsnInf = {"addtlInf": "Beneficiary account error", "stsRsnCd": "00600114"}
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)

        finish_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='PENDING'"
        ApiUtils.waitCondition(self.client.mysql.exec_sql_query, (finish_sql,), lambda x: len(x) > 0, 120, 5)

        state_info = self.client.step_queryTransactionState(sn1, RMNData.api_key, RMNData.sec_key, msg_id, sn1)
        flow_info = self.client.step_queryTransactionFlow(sn1, RMNData.api_key, RMNData.sec_key, msg_id, sn1)

        self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "PDNG")
        # 校验flow中reject状态
        self.client.checkExpectFlowState("PENDING", flow_info, rmn_tx_id)
        # 校验rts系统中订单状态
        self.client.checkNotNormalOrderInRTS(rmn_tx_id, "REDEEM_SUBMIT", "sn2", sn2, "init")

    def test_010_error_sn2SendRejectRTPC_informationError_sn_sn_pn(self):
        # pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(20, 2, 10)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("sn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(sn1, msg_id)

        rmn_tx_id = tx_info["data"]["txId"]

        time.sleep(3)
        self.client.logger.warning("sn1节点提交结算请求并等待接收confirm消息")
        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, tx_msg, rmn_tx_id, "CRDT", self)

        self.client.logger.warning("sn2节点收到交易请求")
        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, msg_id)

        self.client.logger.warning("sn2节点发送confirm消息")
        stsRsnInf = {"addtlInf": "Beneficiary information error", "stsRsnCd": "00600120"}
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)

        finish_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='PENDING'"
        ApiUtils.waitCondition(self.client.mysql.exec_sql_query, (finish_sql,), lambda x: len(x) > 0, 120, 5)

        state_info = self.client.step_queryTransactionState(sn1, RMNData.api_key, RMNData.sec_key, msg_id, sn1)
        flow_info = self.client.step_queryTransactionFlow(sn1, RMNData.api_key, RMNData.sec_key, msg_id, sn1)

        self.client.checkCodeAndMessage(state_info)
        self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "PDNG")
        # 校验flow中reject状态
        self.client.checkExpectFlowState("PENDING", flow_info, rmn_tx_id)
        # 校验rts系统中订单状态
        self.client.checkNotNormalOrderInRTS(rmn_tx_id, "REDEEM_SUBMIT", "sn2", sn2, "init")

    def test_011_error_sn2SendRejectRTPC_hitAML_sn_sn_pn(self):
        # pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(20, 2, 10)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("sn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(sn1, msg_id)

        rmn_tx_id = tx_info["data"]["txId"]
        time.sleep(3)
        self.client.logger.warning("sn1节点提交结算请求并等待接收confirm消息")
        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, tx_msg, rmn_tx_id, "CRDT", self)

        self.client.logger.warning("sn2节点收到交易请求")
        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, msg_id)

        self.client.logger.warning("sn2节点发送confirm消息")
        stsRsnInf = {"addtlInf": "report hit AML", "stsRsnCd": "00600104"}
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)

        finish_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='PENDING'"
        ApiUtils.waitCondition(self.client.mysql.exec_sql_query, (finish_sql,), lambda x: len(x) > 0, 120, 5)

        state_info = self.client.step_queryTransactionState(sn1, RMNData.api_key, RMNData.sec_key, msg_id, sn1)
        flow_info = self.client.step_queryTransactionFlow(sn1, RMNData.api_key, RMNData.sec_key, msg_id, sn1)

        self.client.checkCodeAndMessage(state_info)
        self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "PDNG")
        # 校验flow中reject状态
        self.client.checkExpectFlowState("PENDING", flow_info, rmn_tx_id)
        # 校验rts系统中订单状态
        self.client.checkNotNormalOrderInRTS(rmn_tx_id, "REDEEM_SUBMIT", "sn2", sn2, "init")

    def test_012_error_sn2SendRejectRTPC_accountError_pn_sn_sn_pn(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(20, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, pn1_fee, pn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("pn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(pn1, msg_id)

        rmn_tx_id = tx_info["data"]["txId"]
        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1)

        self.client.logger.warning("sn1节点发送confirm消息")
        self.client.step_sendRTPC(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info)
        time.sleep(3)
        self.client.logger.warning("sn1节点提交结算请求并等待接收confirm消息")
        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info, rmn_tx_id, "CRDT", self, sn1_fee)

        self.client.logger.warning("sn2节点收到交易请求")
        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, sn1_tx_info["grpHdr"]["msgId"])

        self.client.logger.warning("sn2节点发送confirm消息")
        stsRsnInf = {"addtlInf": "Beneficiary account error", "stsRsnCd": "00600114"}
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)

        finish_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='PENDING'"
        ApiUtils.waitCondition(self.client.mysql.exec_sql_query, (finish_sql,), lambda x: len(x) > 0, 120, 5)

        state_info = self.client.step_queryTransactionState(sn1, RMNData.api_key, RMNData.sec_key,
                                                            sn1_tx_info["grpHdr"]["msgId"], RMNData.rmn_id)
        flow_info = self.client.step_queryTransactionFlow(sn1, RMNData.api_key, RMNData.sec_key,
                                                          sn1_tx_info["grpHdr"]["msgId"], RMNData.rmn_id)

        self.client.checkCodeAndMessage(state_info)
        self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "PDNG")
        # 校验flow中reject状态
        self.client.checkExpectFlowState("PENDING", flow_info, rmn_tx_id)
        # 校验rts系统中订单状态
        self.client.checkNotNormalOrderInRTS(rmn_tx_id, "REDEEM_SUBMIT", "sn2", sn2, "init")

    def test_013_error_sn2SendRejectRTPC_informationError_pn_sn_sn_pn(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(20, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, pn1_fee, pn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("pn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(pn1, msg_id)

        rmn_tx_id = tx_info["data"]["txId"]
        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1)

        self.client.logger.warning("sn1节点发送confirm消息")
        self.client.step_sendRTPC(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info)
        time.sleep(3)
        self.client.logger.warning("sn1节点提交结算请求并等待接收confirm消息")
        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info, rmn_tx_id, "CRDT", self, sn1_fee)

        self.client.logger.warning("sn2节点收到交易请求")
        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, sn1_tx_info["grpHdr"]["msgId"])

        self.client.logger.warning("sn2节点发送confirm消息")
        stsRsnInf = {"addtlInf": "Beneficiary information error", "stsRsnCd": "00600120"}
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)

        finish_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='PENDING'"
        ApiUtils.waitCondition(self.client.mysql.exec_sql_query, (finish_sql,), lambda x: len(x) > 0, 120, 5)

        state_info = self.client.step_queryTransactionState(sn1, RMNData.api_key, RMNData.sec_key,
                                                            sn1_tx_info["grpHdr"]["msgId"], RMNData.rmn_id)
        flow_info = self.client.step_queryTransactionFlow(sn1, RMNData.api_key, RMNData.sec_key,
                                                          sn1_tx_info["grpHdr"]["msgId"], RMNData.rmn_id)

        self.client.checkCodeAndMessage(state_info)
        self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "PDNG")
        # 校验flow中reject状态
        self.client.checkExpectFlowState("PENDING", flow_info, rmn_tx_id)
        # 校验rts系统中订单状态
        self.client.checkNotNormalOrderInRTS(rmn_tx_id, "REDEEM_SUBMIT", "sn2", sn2, "init")

    def test_014_error_sn2SendRejectRTPC_hitAML_pn_sn_sn_pn(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(20, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, pn1_fee, pn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("pn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(pn1, msg_id)

        rmn_tx_id = tx_info["data"]["txId"]
        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1)

        self.client.logger.warning("sn1节点发送confirm消息")
        self.client.step_sendRTPC(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info)
        time.sleep(3)
        self.client.logger.warning("sn1节点提交结算请求并等待接收confirm消息")
        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info, rmn_tx_id, "CRDT", self, sn1_fee)

        self.client.logger.warning("sn2节点收到交易请求")
        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, sn1_tx_info["grpHdr"]["msgId"])

        self.client.logger.warning("sn2节点发送confirm消息")
        stsRsnInf = {"addtlInf": "report hit AML", "stsRsnCd": "00600104"}
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)

        finish_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='PENDING'"
        ApiUtils.waitCondition(self.client.mysql.exec_sql_query, (finish_sql,), lambda x: len(x) > 0, 120, 5)

        state_info = self.client.step_queryTransactionState(sn1, RMNData.api_key, RMNData.sec_key,
                                                            sn1_tx_info["grpHdr"]["msgId"], RMNData.rmn_id)
        flow_info = self.client.step_queryTransactionFlow(sn1, RMNData.api_key, RMNData.sec_key,
                                                          sn1_tx_info["grpHdr"]["msgId"], RMNData.rmn_id)

        self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "PDNG")
        # 校验flow中reject状态
        self.client.checkExpectFlowState("PENDING", flow_info, rmn_tx_id)
        # 校验rts系统中订单状态
        self.client.checkNotNormalOrderInRTS(rmn_tx_id, "REDEEM_SUBMIT", "sn2", sn2, "init")

    def test_015_error_pn2SendRejectRTPC_accountError_pn_sn_sn_pn(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(20, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        creditor_agent["finInstnId"]["clrSysMmbId"] = RMNData.ncc_agents["GBP"]["finInstnId"]["clrSysMmbId"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, pn1_fee, pn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("pn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(pn1, msg_id)

        rmn_tx_id = tx_info["data"]["txId"]
        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1)

        self.client.logger.warning("sn1节点发送confirm消息")
        self.client.step_sendRTPC(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info)
        time.sleep(3)
        self.client.logger.warning("sn1节点提交结算请求并等待接收confirm消息")
        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info, rmn_tx_id, "CRDT", self, sn1_fee)

        self.client.logger.warning("sn2节点收到交易请求")
        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, sn1_tx_info["grpHdr"]["msgId"])

        self.client.logger.warning("sn2节点发送confirm消息")
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info)
        time.sleep(1)

        self.client.logger.warning("sn2节点提交结算请求并等待接收confirm消息")
        self.client.step_sendRCSR(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, rmn_tx_id, "DBIT", self)

        self.client.logger.warning("pn2节点发送confirm消息")
        pn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, pn2, None, RMNData.api_key, RMNData.sec_key,
                                                                "CREDIT_PN_TXN_SENT")
        stsRsnInf = {"addtlInf": "Beneficiary account error", "stsRsnCd": "00600114"}
        self.client.step_sendRTPC(pn2, RMNData.api_key, RMNData.sec_key, pn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)

        finish_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='PENDING'"
        ApiUtils.waitCondition(self.client.mysql.exec_sql_query, (finish_sql,), lambda x: len(x) > 0, 180, 5)

        state_info = self.client.step_queryTransactionState(sn1, RMNData.api_key, RMNData.sec_key,
                                                            sn1_tx_info["grpHdr"]["msgId"], RMNData.rmn_id)
        flow_info = self.client.step_queryTransactionFlow(sn1, RMNData.api_key, RMNData.sec_key,
                                                          sn1_tx_info["grpHdr"]["msgId"], RMNData.rmn_id)

        self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "PDNG")
        # 校验flow中reject状态
        self.client.checkExpectFlowState("PENDING", flow_info, rmn_tx_id)
        # 校验rts系统中订单状态
        self.client.checkNotNormalOrderInRTS(rmn_tx_id, "PAYOUT_SUBMIT", "sn2", sn2, "finish")

        pendingMsg = "{},{}".format(stsRsnInf["stsRsnCd"], stsRsnInf["addtlInf"])
        self.checkPendingTransactionReason(rmn_tx_id, msg_id, pn1, cdtTrfTxInf["pmtId"]["endToEndId"], pendingMsg)

    def test_016_error_pn2SendRejectRTPC_informationError_pn_sn_sn_pn(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(20, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, pn1_fee, pn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("pn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(pn1, msg_id)

        rmn_tx_id = tx_info["data"]["txId"]
        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1)

        self.client.logger.warning("sn1节点发送confirm消息")
        self.client.step_sendRTPC(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info)
        time.sleep(3)
        self.client.logger.warning("sn1节点提交结算请求并等待接收confirm消息")
        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info, rmn_tx_id, "CRDT", self, sn1_fee)

        self.client.logger.warning("sn2节点收到交易请求")
        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, sn1_tx_info["grpHdr"]["msgId"])

        self.client.logger.warning("sn2节点发送confirm消息")
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info)
        time.sleep(1)

        self.client.logger.warning("sn2节点提交结算请求并等待接收confirm消息")
        self.client.step_sendRCSR(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, rmn_tx_id, "DBIT", self)

        self.client.logger.warning("pn2节点发送confirm消息")
        pn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, pn2, None, RMNData.api_key, RMNData.sec_key,
                                                                "CREDIT_PN_TXN_SENT")
        stsRsnInf = {"addtlInf": "Beneficiary information error", "stsRsnCd": "00600120"}
        self.client.step_sendRTPC(pn2, RMNData.api_key, RMNData.sec_key, pn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)

        finish_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='PENDING'"
        ApiUtils.waitCondition(self.client.mysql.exec_sql_query, (finish_sql,), lambda x: len(x) > 0, 120, 5)

        state_info = self.client.step_queryTransactionState(sn1, RMNData.api_key, RMNData.sec_key,
                                                            sn1_tx_info["grpHdr"]["msgId"], RMNData.rmn_id)
        flow_info = self.client.step_queryTransactionFlow(sn1, RMNData.api_key, RMNData.sec_key,
                                                          sn1_tx_info["grpHdr"]["msgId"], RMNData.rmn_id)

        self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "PDNG")
        # 校验flow中reject状态
        self.client.checkExpectFlowState("PENDING", flow_info, rmn_tx_id)
        # 校验rts系统中订单状态
        self.client.checkNotNormalOrderInRTS(rmn_tx_id, "PAYOUT_SUBMIT", "sn2", sn2, "finish")

        pendingMsg = "{},{}".format(stsRsnInf["stsRsnCd"], stsRsnInf["addtlInf"])
        self.checkPendingTransactionReason(rmn_tx_id, msg_id, pn1, cdtTrfTxInf["pmtId"]["endToEndId"], pendingMsg)

    def test_017_error_pn2SendRejectRTPC_hitAML_pn_sn_sn_pn(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(20, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, pn1_fee, pn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("pn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(pn1, msg_id)

        rmn_tx_id = tx_info["data"]["txId"]
        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1)

        self.client.logger.warning("sn1节点发送confirm消息")
        self.client.step_sendRTPC(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info)
        time.sleep(3)
        self.client.logger.warning("sn1节点提交结算请求并等待接收confirm消息")
        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info, rmn_tx_id, "CRDT", self, sn1_fee)

        self.client.logger.warning("sn2节点收到交易请求")
        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, sn1_tx_info["grpHdr"]["msgId"])

        self.client.logger.warning("sn2节点发送confirm消息")
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info)
        time.sleep(1)

        self.client.logger.warning("sn2节点提交结算请求并等待接收confirm消息")
        self.client.step_sendRCSR(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, rmn_tx_id, "DBIT", self)

        self.client.logger.warning("pn2节点发送confirm消息")
        pn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, pn2, None, RMNData.api_key, RMNData.sec_key,
                                                                "CREDIT_PN_TXN_SENT")
        stsRsnInf = {"addtlInf": "report hit AML", "stsRsnCd": "00600104"}
        self.client.step_sendRTPC(pn2, RMNData.api_key, RMNData.sec_key, pn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)

        finish_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='PENDING'"
        ApiUtils.waitCondition(self.client.mysql.exec_sql_query, (finish_sql,), lambda x: len(x) > 0, 120, 5)

        state_info = self.client.step_queryTransactionState(sn1, RMNData.api_key, RMNData.sec_key,
                                                            sn1_tx_info["grpHdr"]["msgId"], RMNData.rmn_id)
        flow_info = self.client.step_queryTransactionFlow(sn1, RMNData.api_key, RMNData.sec_key,
                                                          sn1_tx_info["grpHdr"]["msgId"], RMNData.rmn_id)

        self.client.checkCodeAndMessage(state_info)
        self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "PDNG")
        # 校验flow中reject状态
        self.client.checkExpectFlowState("PENDING", flow_info, rmn_tx_id)
        # 校验rts系统中订单状态
        self.client.checkNotNormalOrderInRTS(rmn_tx_id, "PAYOUT_SUBMIT", "sn2", sn2, "finish")

        pendingMsg = "{},{}".format(stsRsnInf["stsRsnCd"], stsRsnInf["addtlInf"])
        self.checkPendingTransactionReason(rmn_tx_id, msg_id, pn1, cdtTrfTxInf["pmtId"]["endToEndId"], pendingMsg)

    def test_018_error_pn2SendRejectRTPC_accountError_sn_sn_pn(self):
        # pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(20, 2, 10)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("sn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(sn1, msg_id)

        rmn_tx_id = tx_info["data"]["txId"]
        time.sleep(3)
        self.client.logger.warning("sn1节点提交结算请求并等待接收confirm消息")
        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, tx_msg, rmn_tx_id, "CRDT", self)

        self.client.logger.warning("sn2节点收到交易请求")
        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, tx_msg["grpHdr"]["msgId"])

        self.client.logger.warning("sn2节点发送confirm消息")
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info)
        time.sleep(1)

        self.client.logger.warning("sn2节点提交结算请求并等待接收confirm消息")
        self.client.step_sendRCSR(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, rmn_tx_id, "DBIT", self)

        self.client.logger.warning("pn2节点发送confirm消息")
        pn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, pn2, None, RMNData.api_key, RMNData.sec_key,
                                                                "CREDIT_PN_TXN_SENT")
        stsRsnInf = {"addtlInf": "Beneficiary account error", "stsRsnCd": "00600114"}
        self.client.step_sendRTPC(pn2, RMNData.api_key, RMNData.sec_key, pn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)

        finish_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='PENDING'"
        ApiUtils.waitCondition(self.client.mysql.exec_sql_query, (finish_sql,), lambda x: len(x) > 0, 120, 5)

        state_info = self.client.step_queryTransactionState(sn1, RMNData.api_key, RMNData.sec_key, msg_id, sn1)
        flow_info = self.client.step_queryTransactionFlow(sn1, RMNData.api_key, RMNData.sec_key, msg_id, sn1)

        self.client.checkCodeAndMessage(state_info)
        self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "PDNG")
        # 校验flow中reject状态
        self.client.checkExpectFlowState("PENDING", flow_info, rmn_tx_id)
        # 校验rts系统中订单状态
        self.client.checkNotNormalOrderInRTS(rmn_tx_id, "PAYOUT_SUBMIT", "sn2", sn2, "finish")

    def test_019_error_pn2SendRejectRTPC_informationError_sn_sn_pn(self):
        # pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(20, 2, 10)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("sn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(sn1, msg_id)

        rmn_tx_id = tx_info["data"]["txId"]
        time.sleep(3)
        self.client.logger.warning("sn1节点提交结算请求并等待接收confirm消息")
        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, tx_msg, rmn_tx_id, "CRDT", self)

        self.client.logger.warning("sn2节点收到交易请求")
        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, tx_msg["grpHdr"]["msgId"])

        self.client.logger.warning("sn2节点发送confirm消息")
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info)
        time.sleep(1)

        self.client.logger.warning("sn2节点提交结算请求并等待接收confirm消息")
        self.client.step_sendRCSR(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, rmn_tx_id, "DBIT", self)

        self.client.logger.warning("pn2节点发送confirm消息")
        pn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, pn2, None, RMNData.api_key, RMNData.sec_key,
                                                                "CREDIT_PN_TXN_SENT")
        stsRsnInf = {"addtlInf": "Beneficiary information error", "stsRsnCd": "00600120"}
        self.client.step_sendRTPC(pn2, RMNData.api_key, RMNData.sec_key, pn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)

        finish_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='PENDING'"
        ApiUtils.waitCondition(self.client.mysql.exec_sql_query, (finish_sql,), lambda x: len(x) > 0, 120, 5)

        state_info = self.client.step_queryTransactionState(sn1, RMNData.api_key, RMNData.sec_key, msg_id, sn1)
        flow_info = self.client.step_queryTransactionFlow(sn1, RMNData.api_key, RMNData.sec_key, msg_id, sn1)

        self.client.checkCodeAndMessage(state_info)
        self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "PDNG")
        # 校验flow中reject状态
        self.client.checkExpectFlowState("PENDING", flow_info, rmn_tx_id)
        # 校验rts系统中订单状态
        self.client.checkNotNormalOrderInRTS(rmn_tx_id, "PAYOUT_SUBMIT", "sn2", sn2, "finish")

    def test_020_error_pn2SendRejectRTPC_hitAML_sn_sn_pn(self):
        # pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(20, 2, 10)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("sn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(sn1, msg_id)

        rmn_tx_id = tx_info["data"]["txId"]
        time.sleep(3)
        self.client.logger.warning("sn1节点提交结算请求并等待接收confirm消息")
        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, tx_msg, rmn_tx_id, "CRDT", self)

        self.client.logger.warning("sn2节点收到交易请求")
        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, tx_msg["grpHdr"]["msgId"])

        self.client.logger.warning("sn2节点发送confirm消息")
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info)
        time.sleep(1)

        self.client.logger.warning("sn2节点提交结算请求并等待接收confirm消息")
        self.client.step_sendRCSR(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, rmn_tx_id, "DBIT", self)

        self.client.logger.warning("pn2节点发送confirm消息")
        pn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, pn2, None, RMNData.api_key, RMNData.sec_key,
                                                                "CREDIT_PN_TXN_SENT")
        stsRsnInf = {"addtlInf": "report hit AML", "stsRsnCd": "00600104"}
        self.client.step_sendRTPC(pn2, RMNData.api_key, RMNData.sec_key, pn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)

        finish_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='PENDING'"
        ApiUtils.waitCondition(self.client.mysql.exec_sql_query, (finish_sql,), lambda x: len(x) > 0, 120, 5)

        state_info = self.client.step_queryTransactionState(sn1, RMNData.api_key, RMNData.sec_key, msg_id, sn1)
        flow_info = self.client.step_queryTransactionFlow(sn1, RMNData.api_key, RMNData.sec_key, msg_id, sn1)

        self.client.checkCodeAndMessage(state_info)
        self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "PDNG")
        # 校验flow中reject状态
        self.client.checkExpectFlowState("PENDING", flow_info, rmn_tx_id)
        # 校验rts系统中订单状态
        self.client.checkNotNormalOrderInRTS(rmn_tx_id, "PAYOUT_SUBMIT", "sn2", sn2, "finish")

    def test_021_error_snSendRejectRTPCForRejectedTransaction(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(20, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, pn1_fee, pn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("pn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(pn1, msg_id)

        rmn_tx_id = tx_info["data"]["txId"]
        self.client.logger.warning("sn1节点接收rcct消息")
        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1)

        self.client.logger.warning("sn1节点发送confirm消息")
        stsRsnInf = {"addtlInf": "hit AML", "stsRsnCd": "00600104"}
        self.client.step_sendRTPC(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)

        pn_notify_info = self.client.waitNodeReceiveMessage(pn1, msg_id, "RJCT")
        time.sleep(10)
        self.client.checkTransactionState(rmn_tx_id, "TRANSACTION_REJECTED")

        state_info = self.client.step_queryTransactionState(sn1, RMNData.api_key, RMNData.sec_key,
                                                            sn1_tx_info["grpHdr"]["msgId"], RMNData.rmn_id)
        flow_info = self.client.step_queryTransactionFlow(sn1, RMNData.api_key, RMNData.sec_key,
                                                          sn1_tx_info["grpHdr"]["msgId"], RMNData.rmn_id)

        self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "RJCT")
        # 校验flow中reject状态
        self.client.checkExpectFlowState(["DEBIT_TXN_REJECTED", "TRANSACTION_REJECTED"], flow_info, rmn_tx_id)
        # 校验PN收到reject的RTPC消息
        self.assertEqual(pn_notify_info["txInfAndSts"]["stsId"], "RJCT")
        # 校验rts系统中订单状态
        self.client.checkNotNormalOrderInRTS(rmn_tx_id, "TRANSACTION_REJECT", "sn1", sn1, "fail")

        self.client.logger.warning("sn1节点再次发送confirm消息")
        stsRsnInf = {"addtlInf": "hit AML", "stsRsnCd": "00600104"}
        self.client.step_sendRTPC(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf,
                                  code="00600121",
                                  message="The suspended message has received multiple RTPC messages, please stop resending it.")
        sql = f"select * from `roxe_rmn`.rmn_confirm_message where node_code='{sn1}' and direction='INBOUND' and rmn_txn_id='{rmn_tx_id}'"
        db_conf = self.client.mysql.exec_sql_query(sql)
        self.assertEqual(len(db_conf), 1, "数据库只保留1条reject的记录")

    def test_022_error_sn2SendRejectRTPCForPendingTransaction(self):
        # pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(20, 2, 10)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("sn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(sn1, msg_id)

        rmn_tx_id = tx_info["data"]["txId"]
        time.sleep(3)
        self.client.logger.warning("sn1节点提交结算请求并等待接收confirm消息")
        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, tx_msg, rmn_tx_id, "CRDT", self)

        self.client.logger.warning("sn2节点收到交易请求")
        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, msg_id)

        self.client.logger.warning("sn2节点发送confirm消息")
        stsRsnInf = {"addtlInf": "report hit AML", "stsRsnCd": "00600104"}
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)

        finish_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='PENDING'"
        ApiUtils.waitCondition(self.client.mysql.exec_sql_query, (finish_sql,), lambda x: len(x) > 0, 120, 5)

        state_info = self.client.step_queryTransactionState(sn1, RMNData.api_key, RMNData.sec_key, msg_id, sn1)
        flow_info = self.client.step_queryTransactionFlow(sn1, RMNData.api_key, RMNData.sec_key, msg_id, sn1)

        self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "PDNG")
        # 校验flow中reject状态
        self.client.checkExpectFlowState("PENDING", flow_info, rmn_tx_id)
        # 校验rts系统中订单状态
        self.client.checkNotNormalOrderInRTS(rmn_tx_id, "REDEEM_SUBMIT", "sn2", sn2, "init")

        self.client.logger.warning("sn1节点再次发送confirm消息")
        stsRsnInf = {"addtlInf": "hit AML", "stsRsnCd": "00600104"}
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf,
                                  code="00600121",
                                  message="The suspended message has received multiple RTPC messages, please stop resending it.")
        sql = f"select * from `roxe_rmn`.rmn_confirm_message where node_code='{sn2}' and direction='INBOUND' and rmn_txn_id='{rmn_tx_id}'"
        db_conf = self.client.mysql.exec_sql_query(sql)
        self.assertEqual(len(db_conf), 1, "数据库保留1条reject的记录")

    @unittest.skip("需修改数据库，单独运行")
    def test_023_error_sn1SendRejectRTPC_pendingTransaction_manuallyRtpc(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        with self.updateNotifyUrl("signaturError", sn1) as new_url:
            msg_id = self.client.make_msg_id()
            tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
            tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
            debtor_agent = self.client.make_roxe_agent(pn1, "PN")
            creditor_agent = self.client.make_roxe_agent(sn2, "SN")
            cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                            creditor_agent, 1, pn1)
            tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
            self.client.checkCodeAndMessage(tx_info)

            self.client.logger.warning("pn1节点收到交易confirm")
            self.client.waitNodeReceiveMessage(pn1, msg_id)

            rmn_tx_id = tx_info["data"]["txId"]

            notify_db = self.client.waiteNotifyRetryFail(rmn_tx_id, sn1)
            self.client.checkRetryNotifyInfo(notify_db, new_url)
            time.sleep(3)
            self.client.checkTransactionState(rmn_tx_id, "PENDING")
            state_info = self.client.step_queryTransactionState(pn1, RMNData.api_key, RMNData.sec_key, msg_id, pn1)
            flow_info = self.client.step_queryTransactionFlow(pn1, RMNData.api_key, RMNData.sec_key, msg_id, pn1)
            self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "PDNG")
            self.client.checkExpectFlowState("PENDING", flow_info, rmn_tx_id)
            self.client.checkNotNormalOrderInRTS(rmn_tx_id, "MINT_SUBMIT", "sn1", sn1, "init")

            sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1)
            self.client.logger.warning("手动触发RTPC")
            stsRsnInf = {"addtlInf": "Debit side report signature error", "stsRsnCd": "00600104"}
            self.client.step_sendRTPC_manual(pn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)
            time.sleep(10)
            msg = self.client.waitNodeReceiveMessage(sn1, rmn_tx_id, "RJCT")
            self.assertIsNone(msg)
            self.client.checkNotNormalOrderInRTS(rmn_tx_id, "TRANSACTION_REJECT", "sn1", sn1, "fail")

    def test_024_error_sn2SendRejectRTPC_pendingTransaction_manuallyRtpc(self):
        # pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id, "sign123")
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(20, 2, 10)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.client.checkCodeAndMessage(tx_info)

        self.client.logger.warning("sn1节点收到交易confirm")
        self.client.waitNodeReceiveMessage(sn1, msg_id)

        rmn_tx_id = tx_info["data"]["txId"]
        time.sleep(3)
        self.client.logger.warning("sn1节点提交结算请求并等待接收confirm消息")
        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, tx_msg, rmn_tx_id, "CRDT", self)

        self.client.logger.warning("sn2节点收到交易请求")
        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, msg_id)

        self.client.logger.warning("sn2节点发送confirm消息")
        stsRsnInf = {"addtlInf": "report hit AML", "stsRsnCd": "00600104"}
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)

        time.sleep(30)
        self.client.checkTransactionState(rmn_tx_id, "PENDING")

        state_info = self.client.step_queryTransactionState(sn1, RMNData.api_key, RMNData.sec_key, msg_id, sn1)
        flow_info = self.client.step_queryTransactionFlow(sn1, RMNData.api_key, RMNData.sec_key, msg_id, sn1)

        self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "PDNG")
        # 校验flow中reject状态
        self.client.checkExpectFlowState("PENDING", flow_info, rmn_tx_id)
        # 校验rts系统中订单状态
        self.client.checkNotNormalOrderInRTS(rmn_tx_id, "REDEEM_SUBMIT", "sn2", sn2, "init")

        self.client.logger.warning("手动向sn1节点发送reject rtpc消息")
        stsRsnInf = {"addtlInf": "Debit side report signature error", "stsRsnCd": "00600104"}
        self.client.step_sendRTPC_manual(sn1, RMNData.api_key, RMNData.sec_key, sn2_tx_info, stsId="RJCT",
                                         stsRsnInf=stsRsnInf, code="00100103",
                                         message="the transaction is not start with PN")

        state_info = self.client.step_queryTransactionState(sn1, RMNData.api_key, RMNData.sec_key, msg_id, sn1)
        flow_info = self.client.step_queryTransactionFlow(sn1, RMNData.api_key, RMNData.sec_key, msg_id, sn1)

        self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "PDNG")
        self.client.checkExpectFlowState("PENDING", flow_info, rmn_tx_id)
        sql = f"select * from `roxe_rmn`.rmn_confirm_message where node_code='{sn1}' and direction='OUTBOUND' and rmn_txn_id='{rmn_tx_id}'"
        db_conf = self.client.mysql.exec_sql_query(sql)
        self.assertEqual(len(db_conf), 3, "rmn应向sn1节点发出去3条消息")

        msg = self.client.waitNodeReceiveMessage(sn1, db_conf[0]["msgId"], "RJCT")
        self.assertIsNone(msg)

    @unittest.skip("需修改数据库，单独运行")
    def test_025_error_sn1CallbackUrlResponseErrorCode_thenResponseCorrect(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sql = f"select node_callback_url from roxe_risn_config.risn_node where node_roxe='{sn1}';"
        callback_url = self.client.mysql.exec_sql_query(sql)[0]["nodeCallbackUrl"]
        self.client.logger.info(f"节点的回调地址: {callback_url}")
        try:
            new_url = callback_url + "/signaturError"
            update_sql = f"update roxe_risn_config.risn_node set node_callback_url='{new_url}' where node_roxe='{sn1}'"
            self.client.mysql.exec_sql_query(update_sql)
            self.client.logger.info(f"节点的新回调地址: {new_url}")
            msg_id = self.client.make_msg_id()
            tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
            tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
            debtor_agent = self.client.make_roxe_agent(pn1, "PN")
            creditor_agent = self.client.make_roxe_agent(sn2, "SN")
            cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                            creditor_agent, 1, pn1)
            tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
            self.client.checkCodeAndMessage(tx_info)

            self.client.logger.warning("pn1节点收到交易confirm")
            self.client.waitNodeReceiveMessage(pn1, msg_id)

            rmn_tx_id = tx_info["data"]["txId"]
            self.client.logger.warning("sn1节点接收rcct消息")
            sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1)

            sql = f"select * from roxe_rmn.rmn_notify_info where rmn_txn_id='{rmn_tx_id}' and msg_type='RCCT'"
            a_time = time.time()
            # 未收到正确响应5分钟后进入重试，重试5次，每次2分钟
            notify_db = None
            while time.time() - a_time < 500:
                notify_db = self.client.mysql.exec_sql_query(sql)
                if notify_db and notify_db[0]["notifyCount"] > 1:
                    break
                time.sleep(10)
            self.client.logger.info("rcct重试了{}次，重试原因: {}".format(notify_db[0]["notifyCount"], notify_db[0]["remark"]))
            # 还原回调地址
            self.client.mysql.exec_sql_query(
                f"update roxe_risn_config.risn_node set node_callback_url='{callback_url}' where node_roxe='{sn1}'")
            notify_db2 = None
            while time.time() - a_time < 500:
                notify_db2 = self.client.mysql.exec_sql_query(sql)
                if notify_db2 and notify_db2[0]["notifyStatus"] == "SUCCESS":
                    break

            self.assertEqual(notify_db2[0]["notifyUrl"], callback_url)
            self.assertEqual(notify_db2[0]["notifyStatus"], "SUCCESS")
            self.assertEqual(notify_db2[0]["notifyCount"], notify_db[0]["notifyCount"] + 1)

            self.client.checkTransactionState(rmn_tx_id, "DEBIT_TXN_SENT")
            state_info = self.client.step_queryTransactionState(sn1, RMNData.api_key, RMNData.sec_key,
                                                                sn1_tx_info["grpHdr"]["msgId"],
                                                                RMNData.rmn_id)
            flow_info = self.client.step_queryTransactionFlow(sn1, RMNData.api_key, RMNData.sec_key,
                                                              sn1_tx_info["grpHdr"]["msgId"],
                                                              RMNData.rmn_id)

            self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "ACPT")
            self.client.checkTransactionState(rmn_tx_id, "ACPT")
            self.client.checkExpectFlowState("DEBIT_TXN_SENT", flow_info, rmn_tx_id)
        except Exception as e:
            self.client.logger.error(e.args[0], exc_info=True)
            traceback.print_exc()
        finally:
            self.client.mysql.exec_sql_query(
                f"update roxe_risn_config.risn_node set node_callback_url='{callback_url}' where node_roxe='{sn1}'")

    def updateNodeUrl(self, new_url, node):
        update_sql = f"update roxe_risn_config.risn_node_key set node_callback_url='{new_url}' where node_code='{node}'"
        print(update_sql)
        self.client.mysql.exec_sql_query(update_sql)
        self.client.logger.info(f"节点的新回调地址: {new_url}")

    @contextmanager
    def updateNotifyUrl(self, callbackUrl, node):
        sql = f"select node_callback_url from roxe_risn_config.risn_node_key where node_code='{node}';"
        print(sql)
        callback_url = self.client.mysql.exec_sql_query(sql)[0]["nodeCallbackUrl"]
        self.client.logger.info(f"节点的回调地址: {callback_url}")
        try:
            new_url = callback_url + "/" + callbackUrl
            self.updateNodeUrl(new_url, node)
            yield new_url
        except Exception as e:
            self.client.logger.error(e.args[0], exc_info=True)
        finally:
            self.updateNodeUrl(callback_url, node)

    # @unittest.skip("需修改数据库，单独运行")
    def test_026_error_sn1CallbackUrlResponseErrorCode_00200001(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        with self.updateNotifyUrl("signaturError", pn1) as new_url:
            msg_id = self.client.make_msg_id()
            tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
            tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
            debtor_agent = self.client.make_roxe_agent(pn1, "PN")
            creditor_agent = self.client.make_roxe_agent(sn2, "SN")
            cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                            creditor_agent, 1, pn1)
            tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
            self.client.checkCodeAndMessage(tx_info)

            self.client.logger.warning("pn1节点收到交易confirm")
            self.client.waitNodeReceiveMessage(pn1, msg_id)

            rmn_tx_id = tx_info["data"]["txId"]
            self.client.logger.warning("sn1节点接收rcct消息")
            sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1)

            notify_db = self.client.waiteNotifyRetryFail(rmn_tx_id, sn1)
            # self.client.checkRetryNotifyInfo(notify_db, new_url, skipCheckUrl=True)
            time.sleep(5)
            self.client.checkTransactionState(rmn_tx_id, "PENDING")
            state_info = self.client.step_queryTransactionState(pn1, RMNData.api_key, RMNData.sec_key, msg_id, pn1)
            flow_info = self.client.step_queryTransactionFlow(pn1, RMNData.api_key, RMNData.sec_key, msg_id, pn1)

            self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "PDNG")
            self.client.checkExpectFlowState("PENDING", flow_info, rmn_tx_id)
            # 校验rts系统中订单状态
            self.client.checkNotNormalOrderInRTS(rmn_tx_id, "MINT_SUBMIT", "sn1", sn1, "init")

    @unittest.skip("需修改数据库，单独运行")
    def test_027_error_sn1CallbackUrlResponseErrorCode_sn_sn(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        with self.updateNotifyUrl("signaturError", sn1) as new_url:
            msg_id = self.client.make_msg_id()
            tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
            tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
            debtor_agent = self.client.make_roxe_agent(pn1, "PN")
            creditor_agent = self.client.make_roxe_agent(sn2, "SN")
            cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                            creditor_agent, 1, pn1)
            tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
            self.client.checkCodeAndMessage(tx_info)

            self.client.logger.warning("pn1节点收到交易confirm")
            self.client.waitNodeReceiveMessage(pn1, msg_id)

            rmn_tx_id = tx_info["data"]["txId"]
            # 未收到正确响应5分钟后进入重试，重试5次，每次2分钟
            self.client.waiteNotifyRetryFail(rmn_tx_id, sn1, 1)
            self.updateNodeUrl(new_url.replace("signaturError", "encryptionErrorA"), sn1)
            self.client.waiteNotifyRetryFail(rmn_tx_id, sn1, 2)
            self.updateNodeUrl(new_url.replace("signaturError", "encryptionErrorB"), sn1)
            self.client.waiteNotifyRetryFail(rmn_tx_id, sn1, 3)
            self.updateNodeUrl(new_url.replace("signaturError", "businessError"), sn1)
            self.client.waiteNotifyRetryFail(rmn_tx_id, sn1, 4)
            self.updateNodeUrl(new_url.replace("signaturError", "validationError"), sn1)
            self.client.waiteNotifyRetryFail(rmn_tx_id, sn1, 5)
            self.updateNodeUrl(new_url, sn1)
            notify_db = self.client.waiteNotifyRetryFail(rmn_tx_id, sn1)
            self.client.checkRetryNotifyInfo(notify_db, new_url, True)
            time.sleep(3)
            self.client.checkTransactionState(rmn_tx_id, "PENDING")
            state_info = self.client.step_queryTransactionState(pn1, RMNData.api_key, RMNData.sec_key, msg_id, pn1)
            flow_info = self.client.step_queryTransactionFlow(pn1, RMNData.api_key, RMNData.sec_key, msg_id, pn1)

            self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "PDNG")
            self.client.checkExpectFlowState("PENDING", flow_info, rmn_tx_id)
            # 校验rts系统中订单状态
            self.client.checkNotNormalOrderInRTS(rmn_tx_id, "MINT_SUBMIT", "sn1", sn1, "init")

    @unittest.skip("需修改数据库，单独运行")
    def test_028_error_sn2CallbackUrlResponseErrorCode_pn_sn_sn(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        with self.updateNotifyUrl("signaturError", sn2) as new_url:
            msg_id = self.client.make_msg_id()
            tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
            tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
            debtor_agent = self.client.make_roxe_agent(pn1, "PN")
            creditor_agent = self.client.make_roxe_agent(sn2, "SN")
            sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent)
            cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                            creditor_agent, 1, pn1)
            tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
            self.client.checkCodeAndMessage(tx_info)

            self.client.logger.warning("pn1节点收到交易confirm")
            self.client.waitNodeReceiveMessage(pn1, msg_id)

            rmn_tx_id = tx_info["data"]["txId"]
            self.client.logger.warning("sn1节点接收rcct消息")
            sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1)

            self.client.logger.warning("sn1节点发送confirm消息")
            self.client.step_sendRTPC(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info)
            time.sleep(3)
            self.client.logger.warning("sn1节点提交结算请求并等待接收confirm消息")
            self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info, rmn_tx_id, "CRDT", self, sn1_fee)

            # 未收到正确响应5分钟后进入重试，重试5次，每次2分钟
            self.client.waiteNotifyRetryFail(rmn_tx_id, sn2, 1)
            self.updateNodeUrl(new_url.replace("signaturError", "encryptionErrorA"), sn2)
            self.client.waiteNotifyRetryFail(rmn_tx_id, sn2, 2)
            self.updateNodeUrl(new_url.replace("signaturError", "encryptionErrorB"), sn2)
            self.client.waiteNotifyRetryFail(rmn_tx_id, sn2, 3)
            self.updateNodeUrl(new_url.replace("signaturError", "businessError"), sn2)
            self.client.waiteNotifyRetryFail(rmn_tx_id, sn2, 4)
            self.updateNodeUrl(new_url.replace("signaturError", "validationError"), sn2)
            self.client.waiteNotifyRetryFail(rmn_tx_id, sn2, 5)
            self.updateNodeUrl(new_url, sn2)
            notify_db = self.client.waiteNotifyRetryFail(rmn_tx_id, sn2)
            self.client.checkRetryNotifyInfo(notify_db, new_url, True)
            time.sleep(5)
            self.client.checkTransactionState(rmn_tx_id, "PENDING")
            state_info = self.client.step_queryTransactionState(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info["grpHdr"]["msgId"], RMNData.rmn_id)
            flow_info = self.client.step_queryTransactionFlow(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info["grpHdr"]["msgId"], RMNData.rmn_id)

            self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "PDNG")
            self.client.checkExpectFlowState("PENDING", flow_info, rmn_tx_id)
            # 校验rts系统中订单状态
            self.client.checkNotNormalOrderInRTS(rmn_tx_id, "REDEEM_SUBMIT", "sn2", sn2, "init")

    @unittest.skip("需修改数据库，单独运行")
    def test_029_error_sn2CallbackUrlResponseErrorCode_pn_sn_sn_pn(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        with self.updateNotifyUrl("signaturError", sn2) as new_url:
            msg_id = self.client.make_msg_id()
            tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
            tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
            debtor_agent = self.client.make_roxe_agent(pn1, "PN")
            creditor_agent = self.client.make_roxe_agent(pn2, "PN")
            sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent)
            cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                            creditor_agent, 1, pn1)
            tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
            self.client.checkCodeAndMessage(tx_info)

            self.client.logger.warning("pn1节点收到交易confirm")
            self.client.waitNodeReceiveMessage(pn1, msg_id)

            rmn_tx_id = tx_info["data"]["txId"]
            self.client.logger.warning("sn1节点接收rcct消息")
            sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1)

            self.client.logger.warning("sn1节点发送confirm消息")
            self.client.step_sendRTPC(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info)
            time.sleep(3)
            self.client.logger.warning("sn1节点提交结算请求并等待接收confirm消息")
            self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info, rmn_tx_id, "CRDT", self, sn1_fee)

            self.client.logger.warning("sn2节点收到交易请求")
            self.client.waiteNotifyRetryFail(rmn_tx_id, sn2, 1)
            self.updateNodeUrl(new_url.replace("signaturError", "encryptionErrorA"), sn2)
            self.client.waiteNotifyRetryFail(rmn_tx_id, sn2, 2)
            self.updateNodeUrl(new_url.replace("signaturError", "encryptionErrorB"), sn2)
            self.client.waiteNotifyRetryFail(rmn_tx_id, sn2, 3)
            self.updateNodeUrl(new_url.replace("signaturError", "businessError"), sn2)
            self.client.waiteNotifyRetryFail(rmn_tx_id, sn2, 4)
            self.updateNodeUrl(new_url.replace("signaturError", "validationError"), sn2)
            self.client.waiteNotifyRetryFail(rmn_tx_id, sn2, 5)
            self.updateNodeUrl(new_url, sn2)
            notify_db = self.client.waiteNotifyRetryFail(rmn_tx_id, sn2)
            self.client.checkRetryNotifyInfo(notify_db, new_url, True)
            time.sleep(3)
            self.client.checkTransactionState(rmn_tx_id, "PENDING")
            state_info = self.client.step_queryTransactionState(pn1, RMNData.api_key, RMNData.sec_key, msg_id, pn1)
            flow_info = self.client.step_queryTransactionFlow(pn1, RMNData.api_key, RMNData.sec_key, msg_id, pn1)

            self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "PDNG")
            self.client.checkExpectFlowState("PENDING", flow_info, rmn_tx_id)
            # 校验rts系统中订单状态
            self.client.checkNotNormalOrderInRTS(rmn_tx_id, "REDEEM_SUBMIT", "sn2", sn2, "init")

    @unittest.skip("需修改数据库，单独运行")
    def test_030_error_pn2CallbackUrlResponseErrorCode_pn_sn_sn_pn(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        with self.updateNotifyUrl("signaturError", pn2) as new_url:
            msg_id = self.client.make_msg_id()
            tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id, "sign123")
            tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
            debtor_agent = self.client.make_roxe_agent(pn1, "PN")
            creditor_agent = self.client.make_roxe_agent(pn2, "PN")
            sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent)
            cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                            creditor_agent, 1, pn1)
            tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
            self.client.checkCodeAndMessage(tx_info)

            self.client.logger.warning("pn1节点收到交易confirm")
            self.client.waitNodeReceiveMessage(pn1, msg_id)

            rmn_tx_id = tx_info["data"]["txId"]
            self.client.logger.warning("sn1节点接收rcct消息")
            sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1)
            self.client.logger.warning("sn1节点发送confirm消息")
            self.client.step_sendRTPC(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info)
            time.sleep(3)
            self.client.logger.warning("sn1节点提交结算请求并等待接收confirm消息")
            self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info, rmn_tx_id, "CRDT", self, sn1_fee)

            self.client.logger.warning("sn2节点收到交易请求")
            sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, sn1_tx_info["grpHdr"]["msgId"])
            self.client.logger.warning("sn2节点发送confirm消息")
            self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info)
            self.client.logger.warning("sn2节点提交结算请求并等待接收confirm消息")
            self.client.step_sendRCSR(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, rmn_tx_id, "DBIT", self)

            self.client.logger.warning("pn2节点接收rcct消息")
            self.client.waiteNotifyRetryFail(rmn_tx_id, pn2, 1)
            self.updateNodeUrl(new_url.replace("signaturError", "encryptionErrorA"), pn2)
            self.client.waiteNotifyRetryFail(rmn_tx_id, pn2, 2)
            self.updateNodeUrl(new_url.replace("signaturError", "encryptionErrorB"), pn2)
            self.client.waiteNotifyRetryFail(rmn_tx_id, pn2, 3)
            self.updateNodeUrl(new_url.replace("signaturError", "businessError"), pn2)
            self.client.waiteNotifyRetryFail(rmn_tx_id, pn2, 4)
            self.updateNodeUrl(new_url.replace("signaturError", "validationError"), pn2)
            self.client.waiteNotifyRetryFail(rmn_tx_id, pn2, 5)
            self.updateNodeUrl(new_url, pn2)
            notify_db = self.client.waiteNotifyRetryFail(rmn_tx_id, pn2)
            self.client.checkRetryNotifyInfo(notify_db, new_url, True)
            time.sleep(3)
            self.client.checkTransactionState(rmn_tx_id, "PENDING")
            state_info = self.client.step_queryTransactionState(sn1, RMNData.api_key, RMNData.sec_key,
                                                                sn1_tx_info["grpHdr"]["msgId"],
                                                                RMNData.rmn_id)
            flow_info = self.client.step_queryTransactionFlow(sn1, RMNData.api_key, RMNData.sec_key,
                                                              sn1_tx_info["grpHdr"]["msgId"],
                                                              RMNData.rmn_id)

            self.assertEqual(state_info["data"]["rptOrErr"]["pmt"]["sts"], "PDNG")
            self.client.checkExpectFlowState("PENDING", flow_info, rmn_tx_id)
            # 校验rts系统中订单状态
            self.client.checkNotNormalOrderInRTS(rmn_tx_id, "TRANSACTION_FINISH", "sn2", sn2, "finish")

    def test_031_return_FullySettled_sn_sn(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)

        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        sn2_tx_info = self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)
        re_amt = ApiUtils.parseNumberDecimal(float(sn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"]) - sn2_fee, 2, True)
        sn2_return_fee = self.client.getNodeFeeInDB(sn2, "USD", re_amt, "C2C", True)
        sn1_re_amt = re_amt - sn2_return_fee["in"] - sn2_return_fee["service_fee"]
        sn1_return_fee = self.client.getNodeFeeInDB(sn1, "USD", sn1_re_amt, "C2C", True)
        self.client.logger.warning(f"sn2 return费用: {sn2_return_fee}")
        self.client.logger.warning(f"sn1 return费用: {sn1_return_fee}")
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)
        self.client.returnFlow_sn_sn(sn2, sn1, return_msg, [sn2_return_fee["in"], sn1_return_fee["out"]], self)

    def test_032_return_FullySettled_sn_sn_pn(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)
        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        pn2_tx_info = self.client.transactionFlow_sn_sn_pn(sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

        re_amt = float(pn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"])
        pn2_fee = self.client.getNodeFeeInDB(pn2, "USD", re_amt)["out"]
        re_amt -= pn2_fee
        pn2_return_fee = self.client.getNodeFeeInDB(pn2, "USD", re_amt, "C2C", True)
        sn2_return_fee = self.client.getNodeFeeInDB(sn2, "USD", re_amt - pn2_return_fee["in"], "C2C", True)
        sn1_re_amt = re_amt - sn2_return_fee["in"] - pn2_return_fee["service_fee"] - pn2_return_fee["in"]
        sn1_return_fee = self.client.getNodeFeeInDB(sn1, "USD", sn1_re_amt, "C2C", True)
        self.client.logger.warning(f"pn2 return费用: {pn2_return_fee}")
        self.client.logger.warning(f"sn2 return费用: {sn2_return_fee}")
        self.client.logger.warning(f"sn1 return费用: {sn1_return_fee}")
        return_msg = self.client.make_RPRN_information(pn2, "USD", "USD", pn2_tx_info, pn2_fee)
        self.client.returnFlow_pn_sn_sn(pn2, sn2, sn1, return_msg, [sn2_return_fee["in"], sn1_return_fee["out"]], self)

    def test_033_return_FullySettled_pn_sn_sn(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", sn1=sn1, creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, pn1_fee, pn1, inAmount=amt)

        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        sn2_tx_info = self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

        re_amt = ApiUtils.parseNumberDecimal(float(sn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"]) - sn2_fee, 2,
                                             True)
        sn2_return_fee = self.client.getNodeFeeInDB(sn2, "USD", re_amt, "C2C", True)
        sn1_re_amt = re_amt - sn2_return_fee["in"] - sn2_return_fee["service_fee"]
        sn1_return_fee = self.client.getNodeFeeInDB(sn1, "USD", sn1_re_amt, "C2C", True)
        self.client.logger.warning(f"sn2 return费用: {sn2_return_fee}")
        self.client.logger.warning(f"sn1 return费用: {sn1_return_fee}")
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)
        self.client.returnFlow_sn_sn_pn(sn2, sn1, pn1, return_msg, [sn2_return_fee["in"], sn1_return_fee["out"]], self)

    def test_034_return_FullySettled_pn_sn_sn_pn(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 30)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)

        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        pn2_tx_info = self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)
        re_amt = float(pn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"])
        pn2_fee = self.client.getNodeFeeInDB(pn2, "USD", re_amt)["out"]
        re_amt -= pn2_fee
        pn2_return_fee = self.client.getNodeFeeInDB(pn2, "USD", re_amt, "C2C", True)
        sn2_return_fee = self.client.getNodeFeeInDB(sn2, "USD", re_amt - pn2_return_fee["in"], "C2C", True)
        sn1_re_amt = re_amt - sn2_return_fee["in"] - pn2_return_fee["service_fee"] - pn2_return_fee["in"]
        sn1_return_fee = self.client.getNodeFeeInDB(sn1, "USD", sn1_re_amt, "C2C", True)
        self.client.logger.warning(f"pn2 return费用: {pn2_return_fee}")
        self.client.logger.warning(f"sn2 return费用: {sn2_return_fee}")
        self.client.logger.warning(f"sn1 return费用: {sn1_return_fee}")
        return_msg = self.client.make_RPRN_information(pn2, "USD", "USD", pn2_tx_info, pn2_fee)
        self.client.returnFlow_pn_sn_sn_pn(pn2, sn2, sn1, pn1, return_msg, [sn2_return_fee["in"], sn1_return_fee["out"]], self, isInnerNode=in_node)

    def test_035_return_FullySettled_rpp_USD_PHP(self):
        sn1 = RMNData.rpp_node_usd2php
        sn2 = RMNData.sn_php_ph

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "PHP", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "PHP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1, inAmount=amt)

        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", cdtTrfTxInf["intrBkSttlmAmt"]["amt"], "PHP")
        self.client.checkCodeAndMessage(rate_info)
        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        sn2_tx_info = self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isRPP=True, rateInfo=rate_info, chg_fees=["USD"])

        re_amt = ApiUtils.parseNumberDecimal(float(sn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"]) - sn2_fee, 2,
                                             True)
        sn2_return_fee = self.client.getNodeFeeInDB(sn2, "PHP", re_amt, "C2C", True)
        sn1_re_amt = re_amt - sn2_return_fee["in"] - sn2_return_fee["service_fee"]
        sn1_return_fee = self.client.getNodeFeeInDB(sn1, "USD", sn1_re_amt, "C2C", True)
        self.client.logger.warning(f"sn2 return费用: {sn2_return_fee}")
        self.client.logger.warning(f"sn1 return费用: {sn1_return_fee}")

        return_msg = self.client.make_RPRN_information(sn2, "PHP", "USD", sn2_tx_info, sn2_fee, sn2_return_fee)
        ts_headers = self.client.make_header(sn2, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sn2, ts_headers["msgId"])
        new_rate_info, req_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "PHP", return_msg["rtrdIntrBkSttlmAmt"]["amt"], "USD")
        self.client.checkCodeAndMessage(new_rate_info)
        self.client.returnFlow_sn_sn(sn2, sn1, return_msg, [sn2_return_fee["in"], sn1_return_fee["out"]], self, isRPP=True, rateInfo=new_rate_info, chg_fees=["PHP"])

    def test_036_return_FullySettled_rpp_PHP_USD(self):
        sn1 = RMNData.rpp_node_usd2php
        sn2 = RMNData.sn_usd_us

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(10000, 2, 1000)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "PHP", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("PHP", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1, inAmount=amt)

        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "PHP", cdtTrfTxInf["intrBkSttlmAmt"]["amt"], "USD")
        self.client.checkCodeAndMessage(rate_info)
        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        sn2_tx_info = self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isRPP=True, rateInfo=rate_info, chg_fees=["PHP"])

        sn2_return_fee = self.client.getReturnFeeInDB(sn2, "USD", "in", country="US")
        sn1_return_fee = self.client.getReturnFeeInDB(sn1, "PHP", "out", country="US")

        return_msg = self.client.make_RPRN_information(sn2, "USD", "PHP", sn2_tx_info, sn2_fee, sn2_return_fee)
        ts_headers = self.client.make_header(sn2, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sn2, ts_headers["msgId"])
        new_rate_info, req_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", return_msg["rtrdIntrBkSttlmAmt"]["amt"], "PHP")
        self.client.checkCodeAndMessage(new_rate_info)
        self.client.returnFlow_sn_sn(sn2, sn1, return_msg, [sn2_return_fee, sn1_return_fee], self, isRPP=True, rateInfo=new_rate_info, chg_fees=["USD"])

    def test_037_return_FullySettled_pn_sn_sn_pn_cdtrAgtGiveBIC_cdtrIntrmyAgtGivePN(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(100, 2, 30)
        pn1_fee = self.client.getTransactionFeeInDB(pn1, "USD", "in", "PN")
        pn2_fee = self.client.getTransactionFeeInDB(pn2, "USD", "out", "PN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")

        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        pn2_tx_info = self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)
        pn2_return_fee = self.client.getReturnFeeInDB(pn2, "USD", "in", "PN")
        sn2_return_fee = self.client.getReturnFeeInDB(sn2, "USD", "in")
        sn1_return_fee = self.client.getReturnFeeInDB(sn1, "USD", "out")
        return_msg = self.client.make_RPRN_information(pn2, "USD", "USD", pn2_tx_info, pn2_fee, pn2_return_fee)
        print(json.dumps(return_msg))
        self.client.returnFlow_pn_sn_sn_pn(pn2, sn2, sn1, pn1, return_msg, [sn2_return_fee, sn1_return_fee], self, isInnerNode=in_node)

    def test_038_return_FullySettled_pn_sn_sn_pn_cdtrAgtGiveNCC_cdtrIntrmyAgtGivePN(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(100, 2, 30)
        pn1_fee = self.client.getTransactionFeeInDB(pn1, "USD", "in", "PN")
        pn2_fee = self.client.getTransactionFeeInDB(pn2, "USD", "out", "PN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")

        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        pn2_tx_info = self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)
        pn2_return_fee = self.client.getReturnFeeInDB(pn2, "USD", "in", "PN")
        sn2_return_fee = self.client.getReturnFeeInDB(sn2, "USD", "in")
        sn1_return_fee = self.client.getReturnFeeInDB(sn1, "USD", "out")
        return_msg = self.client.make_RPRN_information(pn2, "USD", "USD", pn2_tx_info, pn2_fee, pn2_return_fee)
        self.client.returnFlow_pn_sn_sn_pn(pn2, sn2, sn1, pn1, return_msg, [sn2_return_fee, sn1_return_fee], self, isInnerNode=in_node)

    def test_039_return_FullySettled_pn_sn_sn_cdtrAgtGiveIBAN_cdtrIntrmyAgtGivePN(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb

        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        cdtrAcct = {"nm": "Li XX", "ccy": "GBP", "iban": RMNData.iban["GBP"]}
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(100, 2, 30)
        pn1_fee = self.client.getTransactionFeeInDB(pn1, "GBP", "in", "PN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "GBP", "GBP", cdtrAcct=cdtrAcct, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrAcct"] = cdtrAcct
        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        sn2_tx_info = self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)
        sn2_return_fee = self.client.getReturnFeeInDB(sn2, "GBP", "in")
        sn1_return_fee = self.client.getReturnFeeInDB(sn1, "GBP", "out")
        return_msg = self.client.make_RPRN_information(sn2, "GBP", "GBP", sn2_tx_info, sn2_fee, sn2_return_fee)
        # return_msg["rtrChain"]["intrmyAgt"] = pn2_tx_info["cdtTrfTxInf"]["intrmyAgt"]
        self.client.returnFlow_sn_sn_pn(sn2, sn1, pn1, return_msg, [sn2_return_fee, sn1_return_fee], self)

    def test_040_return_FullySettled_pn_sn_sn_pn_cdtrAgtGiveNCC_cdtrIntrmyAgtGivePN_intrmyAgtGiveSNRoxeId(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(100, 2, 30)
        pn1_fee = self.client.getTransactionFeeInDB(pn1, "USD", "in", "PN")
        pn2_fee = self.client.getTransactionFeeInDB(pn2, "USD", "out", "PN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")

        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        pn2_tx_info = self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)
        pn2_return_fee = self.client.getReturnFeeInDB(pn2, "USD", "in", "PN")
        sn2_return_fee = self.client.getReturnFeeInDB(sn2, "USD", "in")
        sn1_return_fee = self.client.getReturnFeeInDB(sn1, "USD", "out")
        return_msg = self.client.make_RPRN_information(pn2, "USD", "USD", pn2_tx_info, pn2_fee, pn2_return_fee)
        self.client.returnFlow_pn_sn_sn_pn(pn2, sn2, sn1, pn1, return_msg, [sn2_return_fee, sn1_return_fee], self, isInnerNode=in_node)

    def test_041_return_FullySettled_pn_sn_sn_pn_cdtrAgtGiveBIC_cdtrIntrmyAgtGivePN_rpp(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.rpp_node_usd2php
        sn2 = RMNData.sn_php_ph
        pn2 = RMNData.pn_php_ph

        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["PHP"]
        amt = ApiUtils.randAmount(100, 2, 30)
        pn1_fee = self.client.getTransactionFeeInDB(pn1, "USD", "in", "PN")
        pn2_fee = self.client.getTransactionFeeInDB(pn2, "PHP", "out", "PN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "PHP", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "PHP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")

        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", cdtTrfTxInf["intrBkSttlmAmt"]["amt"], "PHP")
        self.client.checkCodeAndMessage(rate_info)

        pn2_tx_info = self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isRPP=True, rateInfo=rate_info, chg_fees=["USD", "PHP"])
        pn2_return_fee = self.client.getReturnFeeInDB(pn2, "PHP", "in", "PN")
        sn2_return_fee = self.client.getReturnFeeInDB(sn2, "PHP", "in", country="PH")
        sn1_return_fee = self.client.getReturnFeeInDB(sn1, "USD", "out")
        return_msg = self.client.make_RPRN_information(pn2, "PHP", "USD", pn2_tx_info, pn2_fee, pn2_return_fee)
        self.client.returnFlow_pn_sn_sn_pn(pn2, sn2, sn1, pn1, return_msg, [sn2_return_fee, sn1_return_fee], self, isRPP=True, rateInfo=rate_info, chg_fees=["PHP", "USD"])

    def test_042_error_return_FullySettled_oldTransactionWasReturned(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)

        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        sn2_tx_info = self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)
        self.client.step_nodeSendRPRN(sn2, RMNData.rmn_id, return_msg)
        # 再次发起return报错
        self.client.step_nodeSendRPRN(sn2, RMNData.rmn_id, return_msg, RmnCodEnum.SN_RETURN_NOT_ALLOWED)

    def test_043_error_return_FullySettled_rtrdInstdAmtNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)

        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        sn2_tx_info = self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

        re_amt = float(sn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"]) - sn2_fee
        sn2_return_fee = self.client.getNodeFeeInDB(sn2, "USD", re_amt, "C2C", True)["in"]
        # 修改原交易的结算金额，使提交的return报文中退款金额不正确
        new_amount = float(sn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"]) - 1
        new_amount = str(ApiUtils.parseNumberDecimal(new_amount, 2, True))
        sn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"] = new_amount
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee, sn2_return_fee)
        self.client.step_nodeSendRPRN(sn2, RMNData.rmn_id, return_msg, "00100103", "Business exception, orgnlIntrBkSttlmAmt.amt does not match the one in original message")

    def test_044_error_return_FullySettled_chrgFeeAmtNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)

        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        sn2_tx_info = self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)
        return_msg["chrgsInf"][0]["sndFeeAmt"]["amt"] = str(ApiUtils.parseNumberDecimal(return_msg["chrgsInf"][0]["sndFeeAmt"]["amt"] + 1, 2, True))
        self.client.step_nodeSendRPRN(sn2, RMNData.rmn_id, return_msg, "00100103", f"Business exception, incorrect send fee for node:{sn2}")

    def test_045_error_return_FullySettled_rtrdIntrBkSttlmAmtNotMatchFee(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)

        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        sn2_tx_info = self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)
        new_amount = float(return_msg["rtrdIntrBkSttlmAmt"]["amt"]) + 0.01
        return_msg["rtrdIntrBkSttlmAmt"]["amt"] = str(ApiUtils.parseNumberDecimal(new_amount, 2, True))
        self.client.step_nodeSendRPRN(sn2, RMNData.rmn_id, return_msg)

    def test_046_error_return_FullySettled_canNotFindTransaction_orgnlMsgIdNotExist(self):
        """
        完全结算的return，找不到原交易: orgnlMsgId和原交易不匹配
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)

        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        sn2_tx_info = self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

        re_amt = float(sn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"]) - sn2_fee
        sn2_return_fee = self.client.getNodeFeeInDB(sn2, "USD", re_amt, "C2C", True)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee, sn2_return_fee)
        return_msg["orgnlGrpInf"]["orgnlMsgId"] = self.client.make_msg_id()
        self.client.step_nodeSendRPRN(sn2, RMNData.rmn_id, return_msg, "00100103", "Business exception, original message does not exist")

    def test_047_error_return_FullySettled_canNotFindTransaction_orgnlMsgNmIdNotMatch(self):
        """
        完全结算的return，找不到原交易: orgnlMsgNmId和原交易不匹配
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)

        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        sn2_tx_info = self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)
        return_msg["orgnlGrpInf"]["orgnlMsgNmId"] = "RCSR"
        self.client.step_nodeSendRPRN(sn2, RMNData.rmn_id, return_msg, "00100103", "Business exception, orgnlMsgNmId is not valid")

    def test_048_error_return_FullySettled_canNotFindTransaction_orgnlTxIdNotMatch(self):
        """
        完全结算的return，找不到原交易: orgnlTxId和原交易不匹配
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)

        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        sn2_tx_info = self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)
        return_msg["orgnlTxId"] = RMNData.query_tx_info["txId"]
        self.client.step_nodeSendRPRN(sn2, RMNData.rmn_id, return_msg, "00100103", "Business exception, txInf.orgnlTxId does not match the original message")

    def test_049_error_return_FullySettled_canNotFindTransaction_orgnlInstrIdNotMatch(self):
        """
        完全结算的return，找不到原交易: orgnlInstrId和原交易不匹配
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)
        cdtTrfTxInf["pmtId"]["instrId"] = "testinstrId"
        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        sn2_tx_info = self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)
        return_msg["orgnlInstrId"] = "1234"
        self.client.step_nodeSendRPRN(sn2, RMNData.rmn_id, return_msg, "00100103", "Business exception, txInf.orgnlInstrId does not match the original message")

    def test_050_error_return_FullySettled_canNotFindTransaction_orgnlEndToEndIdNotMatch(self):
        """
        完全结算的return，找不到原交易: orgnlEndToEndId和原交易不匹配
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)

        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        sn2_tx_info = self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)
        return_msg["orgnlEndToEndId"] = self.client.make_end_to_end_id()
        self.client.step_nodeSendRPRN(sn2, RMNData.rmn_id, return_msg, "00100103", "Business exception, txInf.orgnlEndToEndId does not match the original message")

    def test_051_error_return_FullySettled_canNotFindTransaction_orgnlIntrBkSttlmAmtNotMatch(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)

        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        sn2_tx_info = self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)
        return_msg["orgnlIntrBkSttlmAmt"] = {"amt": "1.11", "ccy": "USD"}
        self.client.step_nodeSendRPRN(sn2, RMNData.rmn_id, return_msg, "00100103", "Business exception, orgnlIntrBkSttlmAmt.amt does not match the one in original message")

        return_msg["orgnlIntrBkSttlmAmt"] = {"amt": sn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"], "ccy": "PHP"}
        self.client.step_nodeSendRPRN(sn2, RMNData.rmn_id, return_msg, "00100103", "Business exception, orgnlIntrBkSttlmAmt.ccy does not match rtrdIntrBkSttlmAmt.ccy")
        return_msg["rtrdIntrBkSttlmAmt"]["ccy"] = "PHP"
        return_msg["rtrdInstdAmt"]["ccy"] = "PHP"
        self.client.step_nodeSendRPRN(sn2, RMNData.rmn_id, return_msg, "00100103", "Business exception, orgnlIntrBkSttlmAmt.ccy does not match the one in original message")

    def test_052_error_return_FullySettled_canNotFindTransaction_orgnlMsgIdNotMatch(self):
        """
        完全结算的return，找不到原交易: orgnlMsgId和原交易不匹配
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)

        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        sn2_tx_info = self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

        other_tx_sql = f"select msg_id from roxe_rmn.rmn_txn_message where node_code<>'{sn2}' and msg_id is not null "
        other_tx = self.client.mysql.exec_sql_query(other_tx_sql)[0]

        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)
        return_msg["orgnlGrpInf"]["orgnlMsgId"] = other_tx["msgId"]
        self.client.step_nodeSendRPRN(sn2, RMNData.rmn_id, return_msg, "00100103", "Business exception, original message does not exist")

    def test_053_error_return_FullySettled_canNotFindTransaction_instgAgtNotMatch(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)

        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        sn2_tx_info = self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)
        return_msg["instgAgt"] = sn1
        self.client.step_nodeSendRPRN(sn2, RMNData.rmn_id, return_msg, RmnCodEnum.RETURN_INSTDAGT_INSTGAGT_ERR)

    def test_054_error_return_FullySettled_canNotFindTransaction_instdAgtNotMatch(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)

        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        sn2_tx_info = self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)
        return_msg["instdAgt"] = sn1
        self.client.step_nodeSendRPRN(sn2, RMNData.rmn_id, return_msg, RmnCodEnum.OLD_MSG_NOT_FIND)
        return_msg["instdAgt"] = RMNData.rmn_id
        self.client.step_nodeSendRPRN(sn2, RMNData.rmn_id, return_msg, RmnCodEnum.RETURN_INSTDAGT_INSTGAGT_ERR)

    def test_055_error_return_FullySettled_canNotFindTransaction_agtNotChangeCorrect(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        pn1_fee = self.client.getTransactionFeeInDB(pn1, "USD", "in", "PN")
        pn2_fee = self.client.getTransactionFeeInDB(pn2, "USD", "out", "PN")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, pn1_fee, pn1, inAmount=amt)

        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        pn2_tx_info = self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

        # 因为要交换agent顺序，所以取pn1节点发起时的return费用
        return_msg = self.client.make_RPRN_information(pn2, "USD", "USD", pn2_tx_info, pn2_fee)
        return_msg["rtrChain"]["dbtrAgt"] = pn2_tx_info["cdtTrfTxInf"]["dbtrAgt"]
        return_msg["rtrChain"]["cdtrAgt"] = pn2_tx_info["cdtTrfTxInf"]["cdtrAgt"]
        self.client.step_nodeSendRPRN(pn2, RMNData.rmn_id, return_msg, "00100103", "Business exception, txInf.rtrChain.dbtrAgt.finInstnId.othr.id is incorrect")

    def test_056_error_return_FullySettled_canNotFindTransaction_agtMissing(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        pn1_fee = self.client.getTransactionFeeInDB(pn1, "USD", "in", "PN")
        pn2_fee = self.client.getTransactionFeeInDB(pn2, "USD", "out", "PN")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        pn2_tx_info = self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

        return_msg = self.client.make_RPRN_information(pn2, "USD", "USD", pn2_tx_info, pn2_fee)
        for m_k in ["cdtrIntrmyAgt", "dbtrIntrmyAgt", "intrmyAgt"]:
            with self.subTest(f"missing {m_k}"):
                new_return_msg = copy.deepcopy(return_msg)
                new_return_msg["rtrChain"][m_k] = None
                self.client.step_nodeSendRPRN(pn2, RMNData.rmn_id, new_return_msg, "00100103", f"Business exception, txInf.rtrChain.{m_k} is empty")

    def test_057_error_return_FullySettled_sn_sn_notSentBySN2(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)

        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        sn2_tx_info = self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)
        for sender in [sn1, RMNData.rmn_id]:
            with self.subTest(f"sender is {sender}"):
                self.client.step_nodeSendRPRN(sender, RMNData.rmn_id, return_msg, "00100103", f"Business exception, instgAgt:{sender} is not allowed to initiate this return flow")

    def test_058_error_return_FullySettled_pn_sn_sn_notSentBySN2(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        pn1_fee = self.client.getTransactionFeeInDB(pn1, "USD", "in", "PN")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, pn1_fee, pn1, inAmount=amt)

        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        sn2_tx_info = self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)
        for sender in [sn1, pn1, RMNData.rmn_id]:
            with self.subTest(f"sender is {sender}"):
                self.client.step_nodeSendRPRN(sender, RMNData.rmn_id, return_msg, "00100103", f"Business exception, instgAgt:{sender} is not allowed to initiate this return flow")
        # self.client.step_nodeSendRPRN(sn1, RMNData.rmn_id, return_msg, RmnCodEnum.SN_RETURN_NOT_ALLOWED)
        # self.client.step_nodeSendRPRN(pn1, RMNData.rmn_id, return_msg, RmnCodEnum.PN_RETURN_NOT_ALLOWED)
        # self.client.step_nodeSendRPRN(RMNData.rmn_id, RMNData.rmn_id, return_msg, "00100103", "Business exception, instgAgt:risn2roxe51 is not allowed to initiate this return flow")

    def test_059_error_return_FullySettled_pn_sn_sn_pn_notSentByPN2(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        pn1_fee = self.client.getTransactionFeeInDB(pn1, "USD", "in", "PN")
        pn2_fee = self.client.getTransactionFeeInDB(pn2, "USD", "out", "PN")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, pn1_fee, pn1, inAmount=amt)

        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        pn2_tx_info = self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

        return_msg = self.client.make_RPRN_information(pn2, "USD", "USD", pn2_tx_info, pn2_fee)
        for sender in [RMNData.rmn_id, sn1, sn2, pn1]:
            with self.subTest(f"sender is {sender}"):
                self.client.step_nodeSendRPRN(sender, RMNData.rmn_id, return_msg, "00100103", f"Business exception, instgAgt:{sender} is not allowed to initiate this return flow")
            # self.client.step_nodeSendRPRN(sender, RMNData.rmn_id, return_msg, RmnCodEnum.PN_RETURN_NOT_ALLOWED)

    def test_060_error_return_NotAllowedWhenTransactionNotFinish(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        pn1_fee = self.client.getTransactionFeeInDB(pn1, "USD", "in", "PN")
        pn2_fee = self.client.getTransactionFeeInDB(pn2, "USD", "out", "PN")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, pn1_fee, pn1, inAmount=amt)

        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        sn1_return_fee = self.client.getReturnFeeInDB(sn1, "USD", "out")
        sn2_return_fee = self.client.getReturnFeeInDB(sn2, "USD", "in")
        pn2_return_fee = self.client.getReturnFeeInDB(pn2, "USD", "in", "PN")

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        rmn_tx_id = tx_info["data"]["txId"]
        end2end_id = cdtTrfTxInf["pmtId"]["endToEndId"]
        self.client.checkCodeAndMessage(tx_info)
        sn_tx_confirm = self.client.waitNodeReceiveMessage(pn1, msg_id)
        self.checkConfirmMessage(sn_tx_confirm, "ACPT", msg_id, "RCCT", pn1, end2end_id, end2end_id, "TXNS")
        time.sleep(1)
        return_msg = self.client.make_RPRN_information(pn1, "USD", "USD", tx_msg, 0, 0, orgnlTxId=rmn_tx_id, instgAgt=pn1, instdAgt=RMNData.rmn_id)
        self.client.step_nodeSendRPRN(pn1, RMNData.rmn_id, return_msg, RmnCodEnum.PN_RETURN_NOT_ALLOWED)

        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1)
        self.client.step_sendRTPC(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info)
        return_msg = self.client.make_RPRN_information(sn1, "USD", "USD", sn1_tx_info, 0)
        self.client.step_nodeSendRPRN(sn1, RMNData.rmn_id, return_msg, RmnCodEnum.SN_RETURN_NOT_ALLOWED)

        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info, rmn_tx_id, "CRDT", self, sn1_fee)
        return_msg = self.client.make_RPRN_information(sn1, "USD", "USD", sn1_tx_info, sn1_fee)
        self.client.step_nodeSendRPRN(sn1, RMNData.rmn_id, return_msg, RmnCodEnum.SN_RETURN_NOT_ALLOWED)

        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, sn1_tx_info["grpHdr"]["msgId"])
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, 0, sn2_return_fee)
        self.client.step_nodeSendRPRN(sn2, RMNData.rmn_id, return_msg, RmnCodEnum.SN_RETURN_NOT_ALLOWED)

        self.client.step_sendRCSR(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, rmn_tx_id, "DBIT", self, nodeLoc="SN2")
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee,)
        self.client.step_nodeSendRPRN(sn2, RMNData.rmn_id, return_msg, RmnCodEnum.SN_RETURN_NOT_ALLOWED)

        pn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, pn2, None, RMNData.api_key, RMNData.sec_key, "CREDIT_PN_TXN_SENT")
        return_msg = self.client.make_RPRN_information(pn2, "USD", "USD", pn2_tx_info, pn2_fee)
        self.client.step_nodeSendRPRN(pn2, RMNData.rmn_id, return_msg, RmnCodEnum.PN_RETURN_NOT_ALLOWED)

    def test_061_error_return_FullySettled_NotSendOrgnlIntrBkSttlmAmt(self):
        """
        完全结算的交易, 提交return请求时不填orgnlIntrBkSttlmAmt, 报错：{"code":"00100101"}
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)

        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        sn2_tx_info = self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

        sn2_return_fee = self.client.getReturnFeeInDB(sn2, "USD", "in")
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee, sn2_return_fee)
        return_msg["orgnlIntrBkSttlmAmt"] = None
        tx_info, tx_msg = self.client.step_nodeSendRPRN(sn2, RMNData.rmn_id, return_msg)
        self.client.checkOldTransactionInDB(tx_info["data"]["txId"])

    def test_062_return_partiallySettled_sn_sn(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(sn1, "risn2roxe51", msg_id)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.checkCodeAndMessage(tx_info)
        rmn_tx_id = tx_info["data"]["txId"]
        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, tx_msg, rmn_tx_id, "CRDT", self, nodeLoc="SN1")
        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, msg_id)

        self.client.logger.warning("sn2节点发送confirm消息")
        stsRsnInf = {"addtlInf": "Beneficiary account error", "stsRsnCd": "00600114"}
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)
        time.sleep(120)
        self.client.checkTransactionState(rmn_tx_id, "PENDING")

        # sn2节点因未发生结算，费用为0
        return_msg = self.client.make_RPRN_information(sn1, "USD", "USD", sn2_tx_info, 0, True)
        print(json.dumps(return_msg))
        self.assertEqual(return_msg["rtrdInstdAmt"], sn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"])
        self.client.returnFlowForPartiallySettled(sn1, return_msg, msg_id, self)

    def test_063_return_partiallySettled_sn_sn_pn(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(sn1, "risn2roxe51", msg_id)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.checkCodeAndMessage(tx_info)
        rmn_tx_id = tx_info["data"]["txId"]
        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, tx_msg, rmn_tx_id, "CRDT", self, nodeLoc="SN1")
        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, msg_id)

        self.client.logger.warning("sn2节点发送confirm消息")
        stsRsnInf = {"addtlInf": "Beneficiary account error", "stsRsnCd": "00600114"}
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)
        time.sleep(30)
        self.client.checkTransactionState(rmn_tx_id, "PENDING")

        # sn2节点因未发生结算，费用为0
        return_msg = self.client.make_RPRN_information(sn1, "USD", "USD", sn2_tx_info, 0, True)
        self.assertEqual(return_msg["rtrdInstdAmt"], sn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"])
        self.client.returnFlowForPartiallySettled(sn1, return_msg, msg_id, self)

    def test_064_return_partiallySettled_pn_sn_sn(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        pn1_fee = self.client.getTransactionFeeInDB(pn1, "USD", "in", "PN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, "risn2roxe51", msg_id)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.checkCodeAndMessage(tx_info)

        rmn_tx_id = tx_info["data"]["txId"]

        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None)
        self.client.step_sendRTPC(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info)

        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info, rmn_tx_id, "CRDT", self, sn1_fee, nodeLoc="SN1")
        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, sn1_tx_info["grpHdr"]["msgId"])

        self.client.logger.warning("sn2节点发送confirm消息")
        stsRsnInf = {"addtlInf": "Beneficiary account error", "stsRsnCd": "00600114"}
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)
        time.sleep(100)
        self.client.checkTransactionState(rmn_tx_id, "PENDING")

        # sn2节点因未发生结算，费用为0
        sn1_return_fee = self.client.getNodeFeeInDB(sn1, "USD", float(sn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"]), "C2C", True)["out"]
        return_msg = self.client.make_RPRN_information(sn1, "USD", "USD", sn2_tx_info, 0, True)
        self.assertEqual(return_msg["rtrdInstdAmt"], sn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"])
        self.client.returnFlowForPartiallySettled(sn1, return_msg, sn1_tx_info["grpHdr"]["msgId"], self, old_pn1=pn1, sn1_return_fee=sn1_return_fee)

    def test_065_return_partiallySettled_pn_sn_sn_pn(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 30)
        pn1_fee = self.client.getTransactionFeeInDB(pn1, "USD", "in", "PN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.checkCodeAndMessage(tx_info)

        rmn_tx_id = tx_info["data"]["txId"]

        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None)
        self.client.step_sendRTPC(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info)

        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info, rmn_tx_id, "CRDT", self, sn1_fee, nodeLoc="SN1")
        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, sn1_tx_info["grpHdr"]["msgId"])

        self.client.logger.warning("sn2节点发送confirm消息")
        stsRsnInf = {"addtlInf": "Beneficiary account error", "stsRsnCd": "00600114"}
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)
        time.sleep(30)
        self.client.checkTransactionState(rmn_tx_id, "PENDING")

        sn1_return_fee = self.client.getNodeFeeInDB(sn1, "USD", float(sn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"]), "C2C", True)["out"]
        # sn2节点因未发生结算，费用为0
        return_msg = self.client.make_RPRN_information(sn1, "USD", "USD", sn2_tx_info, 0, True)
        self.assertAlmostEqual(float(return_msg["rtrdInstdAmt"]["amt"]), float(sn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"]), delta=0.01)
        self.client.returnFlowForPartiallySettled(sn1, return_msg, sn1_tx_info["grpHdr"]["msgId"], self, old_pn1=pn1, sn1_return_fee=sn1_return_fee)

    def preparePartiallySettledTransaction(self, sn1, sn2):
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(sn1, "risn2roxe51", msg_id)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.checkCodeAndMessage(tx_info)
        rmn_tx_id = tx_info["data"]["txId"]
        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, tx_msg, rmn_tx_id, "CRDT", self, nodeLoc="SN1")
        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, msg_id)

        self.client.logger.warning("sn2节点发送confirm消息")
        stsRsnInf = {"addtlInf": "Beneficiary account error", "stsRsnCd": "00600114"}
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)
        wait_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='PENDING'"
        ApiUtils.waitCondition(self.client.mysql.exec_sql_query, (wait_sql, ), lambda x: len(x) > 0, 60, 5)
        self.client.checkTransactionState(rmn_tx_id, "PENDING")
        sn1_return_fee = self.client.getNodeFeeInDB(sn1, "USD", float(sn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"]), "C2C", True)["out"]
        return sn2_tx_info, sn2_fee, sn1_return_fee

    def test_066_error_return_partiallySettled_rtrdInstdAmtNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee, sn1_return_fee = self.preparePartiallySettledTransaction(sn1, sn2)
        # sn2节点因未发生结算，费用为0
        dif_amounts = [-1, -0.01, 0.01, 1]
        for dif_amt in dif_amounts:
            self.client.logger.warning(f"准备调整的return金额差: {dif_amt}")
            tmp_msg = copy.deepcopy(sn2_tx_info)
            # 修改原交易的结算金额，使提交的return报文中退款金额不正确
            new_amount = float(tmp_msg["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"]) + dif_amt
            new_amount = str(ApiUtils.parseNumberDecimal(new_amount, 2, True))
            tmp_msg["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"] = new_amount
            return_msg = self.client.make_RPRN_information(sn1, "USD", "USD", tmp_msg, 0, True)
            self.client.step_rmnSendRPRN(RMNData.rmn_id, return_msg, "00100103", "Business exception, orgnlIntrBkSttlmAmt.amt does not match the one in original message")

    def test_067_error_return_partiallySettled_chrgsInfAmtNotCorrect(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee, sn1_return_fee = self.preparePartiallySettledTransaction(sn1, sn2)
        # sn2节点因未发生结算，费用为0
        return_msg = self.client.make_RPRN_information(sn1, "USD", "USD", sn2_tx_info, 0, True)
        return_msg["chrgsInf"] = [{"agt": {"id": sn1, "schmeCd": "ROXE"}, "sndFeeAmt": {"ccy": "USD", "amt": f"{sn1_return_fee+1:.2f}"}}]
        self.client.step_rmnSendRPRN(RMNData.rmn_id, return_msg, "00100103", "Business exception, txInf.chrgsInf is not supposed to present")

    def test_068_error_return_partiallySettled_rtrdIntrBkSttlmAmtNotMatchFee(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee, sn1_return_fee = self.preparePartiallySettledTransaction(sn1, sn2)
        # sn2节点因未发生结算，费用为0
        return_msg = self.client.make_RPRN_information(sn1, "USD", "USD", sn2_tx_info, 0, True)
        new_amount = float(return_msg["rtrdIntrBkSttlmAmt"]["amt"]) + 0.01
        return_msg["rtrdIntrBkSttlmAmt"]["amt"] = str(ApiUtils.parseNumberDecimal(new_amount, 2, True))
        self.client.step_rmnSendRPRN(RMNData.rmn_id, return_msg, "00100103", "Business exception, orgnlIntrBkSttlmAmt.amt does not match rtrdIntrBkSttlmAmt.amt")

    def test_069_error_return_partiallySettled_canNotFindTransaction_orgnlMsgIdNotExist(self):
        """
        完全结算的return，找不到原交易: orgnlMsgId和原交易不匹配
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee, sn1_return_fee = self.preparePartiallySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn1, "USD", "USD", sn2_tx_info, 0, True)
        return_msg["orgnlGrpInf"]["orgnlMsgId"] = self.client.make_msg_id()
        self.client.step_rmnSendRPRN(RMNData.rmn_id, return_msg, RmnCodEnum.OLD_MSG_NOT_FIND)

    def test_070_error_return_partiallySettled_canNotFindTransaction_orgnlMsgNmIdNotMatch(self):
        """
        完全结算的return，找不到原交易: orgnlMsgNmId和原交易不匹配
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee, sn1_return_fee = self.preparePartiallySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn1, "USD", "USD", sn2_tx_info, 0, True)
        return_msg["orgnlGrpInf"]["orgnlMsgNmId"] = "RCSR"
        self.client.step_rmnSendRPRN(RMNData.rmn_id, return_msg, "00100103", "Business exception, orgnlMsgNmId is not valid")

    def test_071_error_return_partiallySettled_canNotFindTransaction_orgnlTxIdNotMatch(self):
        """
        完全结算的return，找不到原交易: orgnlTxId和原交易不匹配
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee, sn1_return_fee = self.preparePartiallySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn1, "USD", "USD", sn2_tx_info, 0, True)
        return_msg["orgnlTxId"] = RMNData.query_tx_info["txId"]
        self.client.step_rmnSendRPRN(RMNData.rmn_id, return_msg, "00100103", "Business exception, txInf.orgnlTxId does not match the original message")

    def test_072_error_return_partiallySettled_canNotFindTransaction_orgnlInstrIdNotMatch(self):
        """
        完全结算的return，找不到原交易: orgnlInstrId和原交易不匹配
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee, sn1_return_fee = self.preparePartiallySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn1, "USD", "USD", sn2_tx_info, 0, True)
        return_msg["orgnlInstrId"] = "1234"
        self.client.step_rmnSendRPRN(RMNData.rmn_id, return_msg, "00100103", "Business exception, txInf.orgnlInstrId does not match the original message")

    def test_073_error_return_partiallySettled_canNotFindTransaction_orgnlEndToEndIdNotMatch(self):
        """
        完全结算的return，找不到原交易: orgnlEndToEndId和原交易不匹配
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee, sn1_return_fee = self.preparePartiallySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn1, "USD", "USD", sn2_tx_info, 0, True)
        return_msg["orgnlEndToEndId"] = self.client.make_end_to_end_id()
        self.client.step_rmnSendRPRN(RMNData.rmn_id, return_msg, "00100103", "Business exception, txInf.orgnlEndToEndId does not match the original message")

    def test_074_error_return_partiallySettled_canNotFindTransaction_orgnlIntrBkSttlmAmtNotMatch(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee, sn1_return_fee = self.preparePartiallySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn1, "USD", "USD", sn2_tx_info, 0, True)
        return_msg["orgnlIntrBkSttlmAmt"] = {"amt": "1.11", "ccy": "USD"}
        self.client.step_rmnSendRPRN(RMNData.rmn_id, return_msg, "00100103", "Business exception, orgnlIntrBkSttlmAmt.amt does not match the one in original message")

        return_msg["orgnlIntrBkSttlmAmt"] = {"amt": sn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"], "ccy": "PHP"}
        self.client.step_nodeSendRPRN(sn2, RMNData.rmn_id, return_msg, "00100103", "Business exception, orgnlIntrBkSttlmAmt.ccy does not match rtrdIntrBkSttlmAmt.ccy")
        return_msg["rtrdIntrBkSttlmAmt"]["ccy"] = "PHP"
        return_msg["rtrdInstdAmt"]["ccy"] = "PHP"
        self.client.step_nodeSendRPRN(sn2, RMNData.rmn_id, return_msg, "00100103", "Business exception, orgnlIntrBkSttlmAmt.ccy does not match the one in original message")

    def test_075_error_return_partiallySettled_canNotFindTransaction_orgnlMsgIdNotMatch(self):
        """
        完全结算的return，找不到原交易: orgnlMsgId和原交易不匹配
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee, sn1_return_fee = self.preparePartiallySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn1, "USD", "USD", sn2_tx_info, 0, True)

        other_tx_sql = f"select msg_id from roxe_rmn.rmn_txn_message where node_code<>'{sn2}' and msg_id is not null"
        other_tx = self.client.mysql.exec_sql_query(other_tx_sql)[0]
        return_msg["orgnlGrpInf"]["orgnlMsgId"] = other_tx["msgId"]
        self.client.step_rmnSendRPRN(RMNData.rmn_id, return_msg, RmnCodEnum.OLD_MSG_NOT_FIND)

    def test_076_error_return_partiallySettled_canNotFindTransaction_instgAgtNotMatch(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee, sn1_return_fee = self.preparePartiallySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn1, "USD", "USD", sn2_tx_info, 0, True)
        return_msg["instgAgt"] = sn2
        self.client.step_rmnSendRPRN(RMNData.rmn_id, return_msg, RmnCodEnum.RETURN_INSTDAGT_INSTGAGT_ERR)

    def test_077_error_return_partiallySettled_canNotFindTransaction_instdAgtNotMatch(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee, sn1_return_fee = self.preparePartiallySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn1, "USD", "USD", sn2_tx_info, 0, True)
        return_msg["instdAgt"] = RMNData.mock_node
        self.client.step_rmnSendRPRN(RMNData.rmn_id, return_msg, RmnCodEnum.OLD_MSG_NOT_FIND)
        return_msg["instdAgt"] = RMNData.rmn_id
        self.client.step_rmnSendRPRN(RMNData.rmn_id, return_msg, RmnCodEnum.RETURN_INSTDAGT_INSTGAGT_ERR)

    def test_078_error_return_partiallySettled_canNotFindTransaction_agtNotChangeCorrect(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee, sn1_return_fee = self.preparePartiallySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn1, "USD", "USD", sn2_tx_info, 0, True)
        return_msg["rtrChain"]["dbtrAgt"] = sn2_tx_info["cdtTrfTxInf"]["dbtrAgt"]
        return_msg["rtrChain"]["cdtrAgt"] = sn2_tx_info["cdtTrfTxInf"]["cdtrAgt"]
        self.client.step_rmnSendRPRN(RMNData.rmn_id, return_msg, RmnCodEnum.AGENT_CHANGE_WRONG)

    def test_079_error_return_partiallySettled_canNotFindTransaction_agtMissing(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(100, 2, 30)
        pn1_fee = self.client.getTransactionFeeInDB(pn1, "USD", "in", "PN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, "risn2roxe51", msg_id)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)

        self.checkCodeAndMessage(tx_info)
        rmn_tx_id = tx_info["data"]["txId"]

        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1, None)
        self.client.step_sendRTPC(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info)

        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info, rmn_tx_id, "CRDT", self, sn1_fee, nodeLoc="SN1")
        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, msg_id)

        self.client.logger.warning("sn2节点发送confirm消息")
        stsRsnInf = {"addtlInf": "Beneficiary account error", "stsRsnCd": "00600114"}
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, stsId="RJCT", stsRsnInf=stsRsnInf)
        ApiUtils.waitCondition(
            self.client.mysql.exec_sql_query, (f"select * from rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='PENDING'", ),
            lambda x: len(x) > 0, 120, 10
        )
        self.client.checkTransactionState(rmn_tx_id, "PENDING")

        return_msg = self.client.make_RPRN_information(sn1, "USD", "USD", sn2_tx_info, 0, True)
        for m_k in ["cdtrIntrmyAgt", "dbtrIntrmyAgt", "intrmyAgt"]:
            with self.subTest(f"miss {m_k}"):
                new_return_msg = copy.deepcopy(return_msg)
                new_return_msg["rtrChain"][m_k] = None
                self.client.step_rmnSendRPRN(RMNData.rmn_id, new_return_msg, "00100103", f"Business exception, txInf.rtrChain.{m_k} is empty")

    def test_080_error_return_partiallySettled_sn_sn_notSentByOperation(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee, sn1_return_fee = self.preparePartiallySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn1, "USD", "USD", sn2_tx_info, 0, True)
        for sender in [sn2, sn1]:
            re_headers = self.client.make_header(sender, RMNData.api_key, "RPRN")
            msg_header = self.client.make_group_header(sender, RMNData.rmn_id, re_headers["msgId"])
            tx_info, tx_msg = self.client.manual_return_transaction(RMNData.sec_key, re_headers, msg_header, return_msg)
            self.client.checkCodeAndMessage(tx_info, "00100103", f"Business exception, The node:{sender} is not supposed to initiate the return flow")

    def test_081_error_return_partiallySettled_sn_sn_notSentToOperation(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee, sn1_return_fee = self.preparePartiallySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn1, "USD", "USD", sn2_tx_info, 0, True)
        for receiver in [sn2, sn1]:
            re_headers = self.client.make_header(RMNData.rmn_id, RMNData.api_key, "RPRN")
            msg_header = self.client.make_group_header(RMNData.rmn_id, receiver, re_headers["msgId"])
            tx_info, tx_msg = self.client.manual_return_transaction(RMNData.sec_key, re_headers, msg_header, return_msg)
            self.client.checkCodeAndMessage(tx_info, "00100000", "Parameter exception, grpHdr.instdAgt is supposed to be RISN node code")

    def test_082_error_return_partiallySettled_NotAllowedWhenTransactionNotPending(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        pn1_fee = self.client.getTransactionFeeInDB(pn1, "USD", "in", "PN")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(pn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(pn1, RMNData.rmn_id, msg_id)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        rmn_tx_id = tx_info["data"]["txId"]
        end2end_id = cdtTrfTxInf["pmtId"]["endToEndId"]
        self.client.checkCodeAndMessage(tx_info)
        sn_tx_confirm = self.client.waitNodeReceiveMessage(pn1, msg_id)
        self.checkConfirmMessage(sn_tx_confirm, "ACPT", msg_id, "RCCT", pn1, end2end_id, end2end_id, "TXNS")
        time.sleep(5)
        return_msg = self.client.make_RPRN_information(pn1, "USD", "USD", tx_msg, 0)
        return_msg["orgnlTxId"] = rmn_tx_id
        return_msg["instgAgt"] = pn1
        return_msg["instdAgt"] = RMNData.rmn_id
        self.client.step_rmnSendRPRN(RMNData.rmn_id, return_msg, RmnCodEnum.RMN_RETURN_NOT_ALLOWED)

        sn1_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn1)
        self.client.step_sendRTPC(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info)
        return_msg = self.client.make_RPRN_information(sn1, "USD", "USD", sn1_tx_info, 0)
        self.client.step_rmnSendRPRN(RMNData.rmn_id, return_msg, RmnCodEnum.RMN_RETURN_NOT_ALLOWED)

        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, sn1_tx_info, rmn_tx_id, "CRDT", self, sn1_fee)
        return_msg = self.client.make_RPRN_information(sn1, "USD", "USD", sn1_tx_info, 0)
        self.client.step_rmnSendRPRN(RMNData.rmn_id, return_msg, RmnCodEnum.RMN_RETURN_NOT_ALLOWED)

        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, sn1_tx_info["grpHdr"]["msgId"])
        self.client.step_sendRTPC(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info)
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, 0)
        self.client.step_rmnSendRPRN(RMNData.rmn_id, return_msg, RmnCodEnum.RMN_RETURN_NOT_ALLOWED)

        self.client.step_sendRCSR(sn2, RMNData.api_key, RMNData.sec_key, sn2_tx_info, rmn_tx_id, "DBIT", self, nodeLoc="SN2")
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, 0)
        self.client.step_rmnSendRPRN(RMNData.rmn_id, return_msg, RmnCodEnum.RMN_RETURN_NOT_ALLOWED)

        pn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, pn2, None)
        return_msg = self.client.make_RPRN_information(pn2, "USD", "USD", pn2_tx_info, 0)
        self.client.step_rmnSendRPRN(RMNData.rmn_id, return_msg, RmnCodEnum.RMN_RETURN_NOT_ALLOWED)

    def test_083_error_return_partiallySettled_NotSendOrgnlIntrBkSttlmAmt(self):
        """
        完全结算的交易, 提交return请求时不填orgnlIntrBkSttlmAmt, 报错：{"code":"00100101"}
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee, sn1_return_fee = self.preparePartiallySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn1, "USD", "USD", sn2_tx_info, 0, True)
        return_msg["orgnlIntrBkSttlmAmt"] = None
        self.client.step_rmnSendRPRN(RMNData.rmn_id, return_msg)

    def test_084_error_return_partiallySettled_canNotFindTransaction_cdtrNotMatch(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee, sn1_return_fee = self.preparePartiallySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn1, "USD", "USD", sn2_tx_info, 0, True)
        return_msg["rtrChain"]["cdtr"]["nm"] = "test123"
        self.client.step_rmnSendRPRN(RMNData.rmn_id, return_msg, "00100103", "Business exception, cdtr does not match the dbtr in original RCCT")

    def test_085_error_return_partiallySettled_canNotFindTransaction_cdtrAcctNotMatch(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sn2_tx_info, sn2_fee, sn1_return_fee = self.preparePartiallySettledTransaction(sn1, sn2)
        return_msg = self.client.make_RPRN_information(sn1, "USD", "USD", sn2_tx_info, 0, True)
        return_msg["rtrChain"]["cdtrAcct"]["acctId"] = "12345"
        self.client.step_rmnSendRPRN(RMNData.rmn_id, return_msg)

    def test_086_error_return_FullySettled_canNotFindTransaction_cdtrNotMatch(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)

        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        sn2_tx_info = self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)
        return_msg["rtrChain"]["cdtr"]["nm"] = "test123"
        self.client.step_nodeSendRPRN(sn2, RMNData.rmn_id, return_msg, "00100103", "Business exception, cdtr does not match the dbtr in original RCCT")

    def test_087_error_return_FullySettled_canNotFindTransaction_cdtrAcctNotMatch(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)

        in_node = True if sn2 in RMNData.channel_nodes else False
        if in_node:
            self.skipTest("通道节点暂不支持return")
        sn2_tx_info = self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee)
        return_msg["rtrChain"]["cdtrAcct"]["acctId"] = "12345"
        self.client.step_nodeSendRPRN(sn2, RMNData.rmn_id, return_msg)

    def test_092_return_partiallySettled_sn_sn_terrapay(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_account_number = "20408277204478"
        r_name = "RANDY OYUGI"
        r_bank_name = "Asia United Bank"
        r_bank_code = "AUBKPHMM"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, "PH")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "PHP",
                                                           creditor_agent=creditor_intermediary_agent)
        sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", "PHP", "PH", sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", "PHP", debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, r_account_number)
        # cdtTrfTxInf["dbtr"]["pstlAdr"]["ctry"] = "US"
        cdtTrfTxInf["dbtr"]["pstlAdr"].pop("ctry")
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(sn1, "risn2roxe51", msg_id)
        # cdtTrfTxInf = self.client.make_RCCT_information("USD", "PHP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1, inAmount=amt)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.checkCodeAndMessage(tx_info)
        rmn_tx_id = tx_info["data"]["txId"]
        self.client.step_sendRCSR(sn1, RMNData.api_key, RMNData.sec_key, tx_msg, rmn_tx_id, "CRDT", self, nodeLoc="SN1")
        sn2_tx_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn2, msg_id)

        time.sleep(60)
        self.client.checkTransactionState(rmn_tx_id, "PENDING")

        # sn2节点因未发生结算，费用为0
        return_msg = self.client.make_RPRN_information(sn1, "PHP", "USD", tx_msg, 0, True)
        self.assertEqual(return_msg["rtrdInstdAmt"], sn2_tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"])
        # self.client.returnFlowForPartiallySettled(sn1, return_msg, msg_id, self)