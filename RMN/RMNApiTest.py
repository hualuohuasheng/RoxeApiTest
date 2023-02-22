# coding=utf-8
# author: Li MingLei
# date: 2021-11-27
import copy
import unittest
import time
import json
from .RMNData import RMNData
from .RMNApi import RMNApiClient
from RTS.RtsApiTest import RTSApiClient, RTSData
from roxe_libs import ApiUtils
# from roxepy.clroxe import Clroxe
from decimal import Decimal
if "prod" not in RMNData.env:
    from RPC.RpcApiTest import RPCData, RPCApiClient


class BaseCheckRMN(unittest.TestCase):
    client = None
    rts_client = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = RMNApiClient(
            RMNData.host, RMNData.env, RMNData.api_key, RMNData.sec_key,
            check_db=RMNData.is_check_db, sql_cfg=RMNData.sql_cfg, node_rsa_key=RMNData.node_rsa_key,
            chain_host=RMNData.chain_host
        )

    @classmethod
    def tearDownClass(cls) -> None:
        if RMNData.is_check_db:
            cls.client.mysql.disconnect_database()

    # 封装处理流程函数

    def getAndcheckTransactionStatus(self, from_node, api_key, sec_key, msgId, instgAgt, expect_key, txId=None,
                                     endToEndId=None, instrId=None, instdPty=None, msgTp=None, fromRTS=False):
        ts_headers = self.client.make_header(from_node, api_key, "RTSQ")
        msg_header = self.client.make_msg_header(from_node, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(msgId, instgAgt, txId, endToEndId, instrId, instdPty, msgTp=msgTp)
        time.sleep(3)
        q_info, q_msg = self.client.get_transaction_status(sec_key, ts_headers, msg_header, txQryDef)

        self.checkCodeAndMessage(q_info)
        self.checkTransactionStateInDB(q_info["data"], q_msg, fromRTS=True)
        if isinstance(expect_key, list):
            self.assertIn(q_info["data"]["rptOrErr"]["pmt"]["sts"], expect_key)
        else:
            self.assertEqual(q_info["data"]["rptOrErr"]["pmt"]["sts"], expect_key)

    def checkChainInfoOfRPPInRTS(self, rmn_tx_id, sn1_st_msg, service_fee=0):
        if RMNData.is_check_db:
            # 验证rts记录的换汇信息和链上信息一致
            rts_sql = f"SELECT a.* FROM `{self.client.rts_db_name}`.rts_order_log a left join `{self.client.rts_db_name}`.rts_order b on a.order_id=b.order_id where b.client_id='{rmn_tx_id}';"
            rts_log = self.client.mysql.exec_sql_query(rts_sql)
            swap_info = [i for i in rts_log if i["orderState"] == "SWAP_FINISH"]
            log_info = json.loads(swap_info[0]["logInfo"])
            try:
                hash_info = self.client.chain_client.get_transaction(log_info["hash"])
            except Exception as e:
                self.client.logger.error(f"测试链域名访问不通，跳过验证: {e.args[0]}", exc_info=True)
                return
            self.client.logger.info(f"rts日志: {json.dumps(log_info)}")
            self.client.logger.info(f"获取的链上信息: {json.dumps(hash_info)}")

            hash_from_info = [i for i in hash_info["traces"] if
                              i["act"]["account"] == "roxe.ro" and i["act"]["data"]["from"] == "5chnthreqiow"]
            hash_to_info = [i for i in hash_info["traces"] if
                            i["act"]["account"] == "roxe.ro" and i["act"]["data"]["to"] == "5chnthreqiow"]
            log_from_info = [i for i in log_info["traces"] if
                             i["account"] == "roxe.ro" and i["data"]["from"] == "5chnthreqiow"]
            log_to_info = [i for i in log_info["traces"] if
                           i["account"] == "roxe.ro" and i["data"]["to"] == "5chnthreqiow"]

            hash_amount = float(hash_to_info[0]["act"]["data"]["quantity"].split(" ")[0])
            # 验证换汇的换出金额
            self.assertAlmostEqual(float(log_info["outQuantity"]), hash_amount, delta=0.000001)
            self.assertAlmostEqual(float(log_to_info[0]["data"]["quantity"].split(" ")[0]), hash_amount, delta=0.000001)
            # 验证换汇的下单金额
            self.assertAlmostEqual(float(log_from_info[0]["data"]["quantity"].split(" ")[0]),
                                   float(sn1_st_msg["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"]) - service_fee, delta=0.000001)
            # 验证rts记录的日志和链上的交易信息一致
            self.assertTrue(hash_from_info[0]["act"]["data"] == log_from_info[0]["data"])
            self.assertTrue(hash_to_info[0]["act"]["data"] == log_to_info[0]["data"])

    # 校验函数

    def checkCodeAndMessage(self, res, code="0", msg="Success"):
        self.assertEqual(res["code"], code)
        self.assertEqual(res["message"], msg)

    def checkExchangeRate(self, rate_res, req_body):
        self.checkCodeAndMessage(rate_res)
        rate_info = rate_res["data"]
        self.assertIsNotNone(rate_info["msgHdr"]["msgId"])
        # self.assertIsNotNone(rate_info["msgHdr"]["creDtTm"])
        self.assertEqual(rate_info["msgHdr"]["orgnlInstgPty"], req_body["msgHdr"]["instgPty"])
        self.assertEqual(rate_info["rptOrErr"]["ccyXchg"]["sndrCcy"], req_body["ccyQryDef"]["ccyCrit"]["sndrCcy"])
        self.assertEqual(rate_info["rptOrErr"]["ccyXchg"]["rcvrCcy"], req_body["ccyQryDef"]["ccyCrit"]["rcvrCcy"])
        if req_body["ccyQryDef"]["ccyCrit"]["sndrAmt"]:
            self.assertEqual('%.6f' % float(rate_info["rptOrErr"]["ccyXchg"]["sndrAmt"]),
                             '%.6f' % float(req_body["ccyQryDef"]["ccyCrit"]["sndrAmt"]))
            self.assertIsNotNone(rate_info["rptOrErr"]["ccyXchg"]["xchgRate"])
            exp_amt = float(rate_info["rptOrErr"]["ccyXchg"]["rcvrAmt"]) / float(
                rate_info["rptOrErr"]["ccyXchg"]["sndrAmt"])
            self.assertAlmostEqual(float(rate_info["rptOrErr"]["ccyXchg"]["xchgRate"]), exp_amt, delta=0.01)
        else:
            self.assertEqual('%.6f' % float(rate_info["rptOrErr"]["ccyXchg"]["rcvrAmt"]),
                             '%.6f' % float(req_body["ccyQryDef"]["ccyCrit"]["rcvrAmt"]))
            self.assertIsNotNone(rate_info["rptOrErr"]["ccyXchg"]["xchgRate"])
            exp_amt = float(rate_info["rptOrErr"]["ccyXchg"]["rcvrAmt"]) / float(
                rate_info["rptOrErr"]["ccyXchg"]["sndrAmt"])
            self.assertAlmostEqual(float(rate_info["rptOrErr"]["ccyXchg"]["xchgRate"]), exp_amt, delta=0.01)

    def checkTransactionMessageInDB(self, tx_id, req_body):
        if RMNData.is_check_db:
            if req_body["msgType"] == "RCCT":
                search_sql = f"select * from roxe_rmn.rmn_txn_message where rmn_txn_id='{tx_id}'"
            elif req_body["msgType"] == "RPRN":
                search_sql = f"select * from roxe_rmn.rmn_return_message where rmn_txn_id='{tx_id}'"
            else:
                search_sql = f"select * from roxe_rmn.rmn_sttl_message where rmn_txn_id='{tx_id}'"
            db_info = self.client.mysql.exec_sql_query(search_sql)
            self.assertEqual(len(db_info), 1, f"数据库数据不正确: {db_info}")
            self.assertEqual(db_info[0]["msgType"], req_body["msgType"])
            self.assertEqual(db_info[0]["version"], req_body["version"])
            self.assertEqual(db_info[0]["msgId"], req_body["grpHdr"]["msgId"])
            self.assertEqual(db_info[0]["nodeCode"], req_body["grpHdr"]["instgAgt"])
            if req_body["msgType"] == "RCCT":
                self.assertEqual(db_info[0]["e2eId"], req_body["cdtTrfTxInf"]["pmtId"]["endToEndId"])
                self.assertEqual(db_info[0]["txId"], req_body["cdtTrfTxInf"]["pmtId"]["txId"])
            self.assertEqual(db_info[0]["direction"], "INBOUND")
            self.assertIsNotNone(db_info[0]["createTime"])
            self.assertEqual(json.loads(db_info[0]["msgContent"]), req_body)

            if req_body["msgType"] == "RCCT":
                rts_sql = f"select rts_txn_id from rmn_transaction where rmn_txn_id='{tx_id}'"
                rts_id = self.client.mysql.exec_sql_query(rts_sql)[0]["rtsTxnId"]
                b_type = self.client.matchBusinessTypeByCdtTrfTxInf(req_body["cdtTrfTxInf"])
                rts_type = f"select * from `{self.client.rts_db_name}`.rts_order_log where order_id='{rts_id}' and order_state='TRANSACTION_SUBMIT'"
                rts_submit = self.client.mysql.exec_sql_query(rts_type)
                p_rts_submit = json.loads(rts_submit[0]["logInfo"])
                self.client.logger.info(f"RMN向RTS下单的信息: {p_rts_submit}")
                self.assertEqual(p_rts_submit["businessType"], b_type, "RMN向RTS下单时的businessType不正确")

                if b_type.startswith("B"):
                    self.assertIn("senderOrgName", p_rts_submit["receiveInfo"].keys(), "senderOrgName不正确")
                    self.assertIn("senderOrgIdNumber", p_rts_submit["receiveInfo"].keys(), "senderOrgIdNumber不正确")
                    self.assertIn("senderOrgIdType", p_rts_submit["receiveInfo"].keys(), "senderOrgIdType不正确")
                    if req_body["cdtTrfTxInf"]["dbtr"]["orgId"].get("anyBIC"):
                        self.assertIn("senderOrgBIC", p_rts_submit["receiveInfo"].keys(), "senderOrgBIC字段对应不正确")
                    if req_body["cdtTrfTxInf"]["dbtr"]["orgId"].get("lei"):
                        self.assertIn("senderOrgLei", p_rts_submit["receiveInfo"].keys(), "senderOrgLei字段对应不正确")
                if b_type.endswith("B"):
                    self.assertIn("receiverOrgName", p_rts_submit["receiveInfo"].keys(), "receiverOrgName不正确")
                    self.assertIn("receiverOrgIdNumber", p_rts_submit["receiveInfo"].keys(), "receiverOrgIdNumber不正确")
                    self.assertIn("receiverOrgIdType", p_rts_submit["receiveInfo"].keys(), "receiverOrgIdType不正确")
                    if req_body["cdtTrfTxInf"]["cdtr"]["orgId"].get("anyBIC"):
                        self.assertIn("receiverOrgBIC", p_rts_submit["receiveInfo"].keys(), "receiverOrgBIC字段对应不正确")
                    if req_body["cdtTrfTxInf"]["cdtr"]["orgId"].get("lei"):
                        self.assertIn("receiverOrgLei", p_rts_submit["receiveInfo"].keys(), "receiverOrgLei字段对应不正确")

    def checkTransactionStateInDB(self, tx_info, req_body, fromRTS=False):
        if RMNData.is_check_db:
            rmn_txn_id = self.client.getRmnTxIdFromDB(req_body)
            rmn_sql = "select * from rmn_transaction where rmn_txn_id='{}'".format(rmn_txn_id)
            rmn_tx = self.client.mysql.exec_sql_query(rmn_sql)
            self.assertTrue(len(rmn_tx) == 1, f"数据库未找到: {rmn_txn_id}: {rmn_tx}")
            # 验证msgHdr
            self.assertIsNotNone(tx_info["msgHdr"]["msgId"])
            self.assertIsNotNone(tx_info["msgHdr"]["creDtTm"])
            self.assertEqual(tx_info["msgHdr"]["orgnlInstgPty"], req_body["msgHdr"]["instgPty"])
            # 验证交易
            if not fromRTS:
                self.assertEqual(tx_info["rptOrErr"]["pmt"]["msgId"], rmn_tx[0]["msgId"])
            self.assertEqual(tx_info["rptOrErr"]["pmt"]["instgPty"], "risn2roxe51")
            self.assertEqual(tx_info["rptOrErr"]["pmt"]["instdPty"], rmn_tx[0]["nodeCode"])  # req_body["msgHdr"]["instgPty"]
            if rmn_tx[0]["txnType"] == "RPRN":
                self.assertNotIn("endToEndId", tx_info["rptOrErr"]["pmt"]["pmtId"])
            else:
                self.assertEqual(tx_info["rptOrErr"]["pmt"]["pmtId"]["endToEndId"], rmn_tx[0]["e2eId"])
            tx_statement = json.loads(rmn_tx[0]["txnStatement"])
            ex_key = "rmnTxnId" if rmn_tx[0]["txnType"] == "RPRN" else "txId"
            self.assertEqual(tx_info["rptOrErr"]["pmt"]["pmtId"]["txId"], tx_statement[ex_key])
            self.assertIsNotNone(tx_info["rptOrErr"]["pmt"]["sts"])
            # self.assertEqual(tx_info["rptOrErr"]["pmt"]["dtTm"], rmn_tx[0]["updateTime"].strftime("%Y-%m-%dT%H:%M:%S.%f"))
        else:
            return

    def checkTransactionFlowInDB(self, tx_flow_info, req_body, is_rmn_send=False):
        if RMNData.is_check_db:
            rmn_txn_id = self.client.getRmnTxIdFromDB(req_body)
            rmn_sql = "select * from rmn_txn_flow where rmn_txn_id='{}' order by create_time".format(rmn_txn_id)
            rmn_tx = self.client.mysql.exec_sql_query(rmn_sql)
            old_msg_sql = "select * from rmn_transaction where rmn_txn_id='{}'".format(rmn_txn_id)
            old_tx_info = self.client.mysql.exec_sql_query(old_msg_sql)[0]
            old_msg_id = old_tx_info["msgId"]
            self.assertTrue(len(rmn_tx) >= 1, f"数据库未找到: {rmn_txn_id}")
            # 验证msgHdr
            self.assertIsNotNone(tx_flow_info["msgHdr"]["msgId"])
            self.assertIsNotNone(tx_flow_info["msgHdr"]["creDtTm"])
            self.assertEqual(tx_flow_info["msgHdr"]["orgnlInstgPty"], req_body["msgHdr"]["instgPty"])
            # 验证交易
            if "txnSrcSys" in old_tx_info and old_tx_info["txnSrcSys"] == "RMN":
                self.assertEqual(tx_flow_info["rptOrErr"]["pmt"]["msgId"], old_msg_id)
            self.assertEqual(tx_flow_info["rptOrErr"]["pmt"]["msgTp"], rmn_tx[0]["txnType"])
            if is_rmn_send:
                self.assertEqual(tx_flow_info["rptOrErr"]["pmt"]["instgPty"], RMNData.rmn_id)
            else:
                self.assertEqual(tx_flow_info["rptOrErr"]["pmt"]["instgPty"], rmn_tx[0]["nodeCode"])
                if tx_flow_info["rptOrErr"]["pmt"]["msgTp"] != "RPRN":
                    self.assertEqual(tx_flow_info["rptOrErr"]["pmt"]["pmtId"]["endToEndId"], rmn_tx[0]["e2eId"])
            # tx_statement = json.loads(rmn_tx[0]["txnStatement"])
            self.assertEqual(tx_flow_info["rptOrErr"]["pmt"]["pmtId"]["txId"], rmn_txn_id)

            for flow_data in tx_flow_info["rptOrErr"]["splmtryData"]:
                db_flow = [i for i in rmn_tx if i["txnState"] == flow_data["sts"]]
                self.assertEqual(flow_data["txId"], db_flow[0]["rmnTxnId"])
                if db_flow[0]["msgId"] is None:
                    self.assertNotIn("msgId", flow_data)
                else:
                    self.assertEqual(flow_data["msgId"], db_flow[0]["msgId"])
                if flow_data["sts"] != "TRANSACTION_FINISH":
                    if tx_flow_info["rptOrErr"]["pmt"]["msgTp"] == "RPRN" and db_flow[0]["remark"]:
                        self.assertNotIn("nodeCode", flow_data.keys())
                    else:
                        self.assertEqual(flow_data["nodeCode"], db_flow[0]["nodeCode"])
                self.assertEqual(flow_data["sts"], db_flow[0]["txnState"])
                # self.assertEqual(flow_data["createTime"], rmn_tx[0]["createTime"].strftime("%Y-%m-%dT%H:%M:%S") + ".000Z")

    def checkDictMessage(self, dict_data, ex_data):
        self.assertEqual(len([i for i in dict_data.keys()]), len([i for i in ex_data.keys()]), f"{dict_data}\n {ex_data}")
        for k_k, k_v in dict_data.items():
            if isinstance(k_v, dict):
                self.checkDictMessage(k_v, ex_data[k_k])
            else:
                self.assertEqual(k_v, ex_data[k_k], f"{k_k} 校验失败")

    def checkNodeReceivedReturnMessage(self, tx_id, return_info, to_node, fee_nodes, node_fees, isRPP=False, rateInfo=None, fees=None, isHalf=False, node_role=None, service_fee=0):
        if RMNData.is_check_db:
            node_info = self.client.mysql.exec_sql_query("select * from roxe_risn_config.risn_node")
            db_info = self.client.mysql.exec_sql_query(f"select * from `roxe_rmn`.rmn_return_message where rmn_txn_id='{tx_id}' and node_code='{to_node}' and direction='OUTBOUND'")
            if len(db_info) > 1:
                db_info = [i for i in db_info if i["msgId"] == return_info["grpHdr"]["msgId"]]
            self.assertEqual(len(db_info), 1, f"数据库数据不正确: {db_info}")
            out_msg_db = json.loads(db_info[0]["msgContent"])  # RMN发出去的消息
            self.assertEqual(return_info["version"], db_info[0]["version"])
            self.assertEqual(return_info["msgType"], "RPRN")
            # 校验grpHdr
            self.assertEqual(return_info["grpHdr"]["msgId"], db_info[0]["msgId"])
            self.assertEqual(return_info["grpHdr"]["instgAgt"], RMNData.rmn_id)
            self.assertEqual(return_info["grpHdr"]["instdAgt"], to_node)
            self.assertIsNotNone(return_info["grpHdr"]["creDtTm"])
            # 校验sttlmInf
            self.assertEqual(return_info["grpHdr"]["sttlmInf"]["clrSysCd"], "ROXE")
            self.assertEqual(return_info["grpHdr"]["sttlmInf"]["sttlmMtd"], "CLRG")
            # 校验txInf
            in_info = self.client.mysql.exec_sql_query("select * from roxe_rmn.rmn_return_message where rmn_txn_id='{}' and direction='INBOUND'".format(tx_id))
            parse_in_msg = json.loads(in_info[0]["msgContent"])
            self.client.logger.debug(f"下单的原始请求: {parse_in_msg}")

            self.assertEqual(return_info["txInf"]["rtrId"], tx_id, "rtrId不正确")
            # 找到return对应的原交易的rcct报文
            re_tx_info = self.client.mysql.exec_sql_query(f"select * from rmn_transaction where rmn_txn_id='{tx_id}'")[0]
            old_tx_id = re_tx_info["relTxnId"]
            old_rcct_sql = f"select * from rmn_txn_message where rmn_txn_id='{old_tx_id}' and node_code='{to_node}'"
            old_rcct = self.client.mysql.exec_sql_query(old_rcct_sql)
            if node_role: old_rcct = [i for i in old_rcct if i["nodeRole"] == node_role]
            old_rcct_msg = json.loads(old_rcct[0]["msgContent"])
            self.assertEqual(return_info["txInf"]["orgnlGrpInf"]["orgnlMsgId"], old_rcct_msg["grpHdr"]["msgId"])
            self.assertEqual(return_info["txInf"]["orgnlGrpInf"]["orgnlMsgNmId"], old_rcct_msg["msgType"])
            self.assertEqual(return_info["txInf"]["orgnlIntrBkSttlmAmt"], old_rcct_msg["cdtTrfTxInf"]["intrBkSttlmAmt"])
            self.assertEqual(return_info["txInf"]["rtrdInstdAmt"], parse_in_msg["txInf"]["rtrdInstdAmt"])

            if isRPP:
                self.assertEqual(return_info["txInf"]["rtrdIntrBkSttlmAmt"]["ccy"], parse_in_msg["txInf"]["splmtryData"]["envlp"]["cnts"]["rcvrCcy"])
            else:
                self.assertEqual(return_info["txInf"]["rtrdIntrBkSttlmAmt"]["ccy"], parse_in_msg["txInf"]["rtrdIntrBkSttlmAmt"]["ccy"])
            self.assertEqual(return_info["txInf"]["instgAgt"], old_rcct_msg["grpHdr"]["instgAgt"])
            self.assertEqual(return_info["txInf"]["instdAgt"], old_rcct_msg["grpHdr"]["instdAgt"])
            self.assertEqual(return_info["txInf"]["rtrRsnInf"], parse_in_msg["txInf"]["rtrRsnInf"])

            self.assertEqual(return_info["txInf"]["orgnlEndToEndId"], old_rcct_msg["cdtTrfTxInf"]["pmtId"]["endToEndId"])
            self.assertEqual(return_info["txInf"]["orgnlTxId"], old_rcct_msg["cdtTrfTxInf"]["pmtId"]["txId"])
            fee = 0
            if fee_nodes:
                ex_len = len(fee_nodes) + 1 if service_fee > 0 else len(fee_nodes)
                self.assertEqual(len(return_info["txInf"]["chrgsInf"]), ex_len)
                first_sn = True
                fee_currency = return_info["txInf"]["rtrdIntrBkSttlmAmt"]["ccy"]
                send_sn_index = 0
                for c_index, c_info in enumerate(return_info["txInf"]["chrgsInf"]):
                    # 预期的节点nodeCode
                    if c_info["agt"]["id"] == RMNData.rmn_id:
                        self.assertEqual(c_info["svcFeeAmt"]["ccy"], fee_currency)
                        self.assertAlmostEqual(float(c_info["svcFeeAmt"]["amt"]), service_fee, delta=0.01)
                        self.assertEqual(c_info["agt"]["schmeCd"], "ROXE")
                    else:
                        ex_node = fee_nodes[c_index]
                        self.assertEqual(c_info["agt"]["id"], ex_node)
                        self.assertEqual(c_info["agt"]["schmeCd"], "ROXE")
                        # 预期节点的类型：PN、SN
                        ex_node_type = [i["nodeType"] for i in node_info if i["nodeRoxe"] == ex_node][0]
                        if ex_node_type == "SN":
                            # 第一个SN节点
                            if first_sn:
                                first_sn = False
                                send_sn_index = c_index
                            ex_key = "sndFeeAmt" if c_index == send_sn_index else "dlvFeeAmt"
                            if isHalf: ex_key = "dlvFeeAmt"
                            sn_fee = node_fees[0] if c_index == send_sn_index else node_fees[1]
                            if fees:
                                ex_fee = fees[0] if c_index == send_sn_index else fees[1]
                            else:
                                ex_fee = copy.deepcopy(fee_currency)
                            self.assertEqual(c_info[ex_key]["amt"], f"{sn_fee:.2f}")  # 费用保留2位小数
                            self.assertEqual(c_info[ex_key]["ccy"], ex_fee)
                            fee += float(c_info[ex_key]["amt"])
                        else:
                            ex_side = "in" if c_index == 0 else "out"
                            if isRPP:
                                ex_fee_key = "rtrdInstdAmt" if c_index == 0 else "rtrdIntrBkSttlmAmt"
                                ex_fee_currency = old_rcct_msg["cdtTrfTxInf"][ex_fee_key]["ccy"]
                            else:
                                ex_fee_currency = fee_currency
                            b_type = self.client.matchBusinessTypeByCdtTrfTxInf(return_info["txInf"])
                            pn_fee = self.client.getNodeFeeInDB(ex_node, ex_fee_currency, float(return_info["txInf"]["rtrdInstdAmt"]["amt"]), b_type, True)[ex_side]
                            ex_key = "sndFeeAmt" if c_index <= send_sn_index else "dlvFeeAmt"
                            self.assertEqual(c_info[ex_key]["amt"], f"{pn_fee:.2f}", f"{ex_node} {ex_key}不正确")  # 费用保留2位小数
                            self.assertEqual(c_info[ex_key]["ccy"], ex_fee_currency)
                            fee += float(c_info[ex_key]["amt"])
            if service_fee > 0:
                fee += service_fee
            if isRPP:
                rate_amount = rateInfo["data"]["rptOrErr"]["ccyXchg"]["rcvrAmt"]
                ex_amount = ApiUtils.parseNumberDecimal(float(rate_amount), 2)
                is_right = [c for c in return_info["txInf"]["chrgsInf"] if "dlvFeeAmt" in c]
                if is_right:
                    ex_amount = float(rate_amount) - float(is_right[0]["dlvFeeAmt"]["amt"])
                per_diff = (float(return_info["txInf"]["rtrdIntrBkSttlmAmt"]["amt"]) - ex_amount) / ex_amount
                # 最终换汇的金额需要人工确认下，这个差值会随入金金额以及资金池的深度变化而变化
                self.client.logger.warning(f"下单前查询汇率得到: {ex_amount}")
                self.client.logger.warning("下单后实际可以换得: {}".format(float(return_info["txInf"]["rtrdIntrBkSttlmAmt"]["amt"])))
                self.client.logger.warning(f"和预期误差范围: {per_diff} %")
            else:
                ex_amount = float(parse_in_msg["txInf"]["rtrdInstdAmt"]["amt"]) - fee
                self.assertAlmostEqual(float(return_info["txInf"]["rtrdIntrBkSttlmAmt"]["amt"]), ex_amount, delta=0.001)

            self.checkDictMessage(return_info["txInf"]["rtrChain"], parse_in_msg["txInf"]["rtrChain"])
            self.assertDictEqual(out_msg_db, return_info)

    def checkTransactionMessageWithNextNode(self, tx_msg, next_node_msg):
        for k in ["dbtr", "dbtrAcct", "cdtr", "cdtrAcct"]:
            self.client.logger.debug(f"准备校验: {k}")
            self.checkDictMessage(tx_msg["cdtTrfTxInf"][k], next_node_msg["cdtTrfTxInf"][k])
        for k in ["dbtrAgt", "dbtrIntrmyAgt", "cdtrAgt", "cdtrIntrmyAgt", "intrmyAgt"]:
            if k in tx_msg["cdtTrfTxInf"]:
                self.assertTrue(k in next_node_msg["cdtTrfTxInf"], f"{k}应存在rcct消息中")
                self.checkDictMessage(tx_msg["cdtTrfTxInf"][k], next_node_msg["cdtTrfTxInf"][k])

    def checkNodeReceivedTransactionMessage(self, tx_id, tx_info, to_node, fee_nodes, node_fees, isRPP=False, rateInfo=None, fees=None, fromRTS=False, service_fee=0):
        if RMNData.is_check_db:
            node_info = self.client.mysql.exec_sql_query("select * from roxe_risn_config.risn_node")
            # channel_info = self.client.mysql.exec_sql_query("select * from roxe_risn_config.risn_node_channel")
            db_info = self.client.mysql.exec_sql_query(f"select * from rmn_txn_message where rmn_txn_id='{tx_id}' and node_code='{to_node}' and direction='OUTBOUND'")
            if len(db_info) > 1:
                db_info = [i for i in db_info if i["msgId"] == tx_info["grpHdr"]["msgId"]]
            self.assertEqual(len(db_info), 1, f"数据库数据不正确: {db_info}")
            parse_msg = json.loads(db_info[0]["msgContent"])
            self.assertEqual(tx_info["version"], db_info[0]["version"])
            self.assertEqual(tx_info["msgType"], "RCCT")
            # 校验grpHdr
            self.assertEqual(tx_info["grpHdr"]["msgId"], db_info[0]["msgId"])
            self.assertEqual(tx_info["grpHdr"]["instgAgt"], RMNData.rmn_id)
            self.assertEqual(tx_info["grpHdr"]["instdAgt"], to_node)
            self.assertIsNotNone(tx_info["grpHdr"]["creDtTm"])
            # 校验sttlmInf
            self.assertEqual(tx_info["grpHdr"]["sttlmInf"]["clrSysCd"], "ROXE")
            self.assertEqual(tx_info["grpHdr"]["sttlmInf"]["sttlmMtd"], "CLRG")
            # 校验cdtTrfTxInf
            in_info = self.client.mysql.exec_sql_query("select * from roxe_rmn.rmn_txn_message where rmn_txn_id='{}' and direction='INBOUND'".format(tx_id))
            parse_in_msg = json.loads(in_info[0]["msgContent"])
            self.client.logger.debug(f"下单的原始请求: {parse_in_msg}")
            self.assertAlmostEqual(float(tx_info["cdtTrfTxInf"]["instdAmt"]["amt"]), float(parse_in_msg["cdtTrfTxInf"]["instdAmt"]["amt"]), delta=0.01)
            self.assertEqual(tx_info["cdtTrfTxInf"]["instdAmt"]["ccy"], parse_in_msg["cdtTrfTxInf"]["instdAmt"]["ccy"])
            if isRPP:
                self.assertEqual(tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["ccy"], parse_in_msg["cdtTrfTxInf"]["splmtryData"]["envlp"]["cnts"]["rcvrCcy"])
            else:
                self.assertEqual(tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["ccy"], parse_in_msg["cdtTrfTxInf"]["instdAmt"]["ccy"])
            self.assertIsNotNone(tx_info["cdtTrfTxInf"]["intrBkSttlmDt"])
            self.assertEqual(tx_info["cdtTrfTxInf"]["pmtId"]["endToEndId"], parse_in_msg["cdtTrfTxInf"]["pmtId"]["endToEndId"])
            self.assertEqual(tx_info["cdtTrfTxInf"]["pmtId"]["txId"], tx_id)

            self.assertIsNotNone(tx_info["cdtTrfTxInf"]["chrgsInf"])
            ex_fee_len = len(fee_nodes)
            # 存在service_fee时，只有向右侧节点发送的交易消息中才会存在
            if RMNData.rmn_id in [i["agt"]["id"] for i in tx_info["cdtTrfTxInf"]["chrgsInf"]] or service_fee > 0:
                ex_fee_len += 1
            self.assertEqual(len(tx_info["cdtTrfTxInf"]["chrgsInf"]), ex_fee_len)
            first_sn = True
            fee_currency = tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["ccy"]
            send_sn_index = 0
            fee = 0
            for c_index, c_info in enumerate(tx_info["cdtTrfTxInf"]["chrgsInf"]):
                if c_info["agt"]["id"] == RMNData.rmn_id:
                    service_fee_ccy = tx_info["cdtTrfTxInf"]["splmtryData"]["envlp"]["cnts"]["sndrCcy"]
                    self.assertAlmostEqual(float(c_info["svcFeeAmt"]["amt"]), service_fee, delta=0.01)
                    self.assertEqual(c_info["svcFeeAmt"]["ccy"], service_fee_ccy)
                    self.assertEqual(c_info["agt"]["schmeCd"], "ROXE")
                    fee += float(c_info["svcFeeAmt"]["amt"])
                else:
                    ex_node = fee_nodes[c_index]
                    self.assertEqual(c_info["agt"]["id"], ex_node)
                    self.assertEqual(c_info["agt"]["schmeCd"], "ROXE")
                    ex_node_type = [i["nodeType"] for i in node_info if i["nodeRoxe"] == ex_node][0]
                    if ex_node_type == "SN":
                        # 第一个SN节点
                        if first_sn:
                            first_sn = False
                            send_sn_index = c_index
                        ex_key = "sndFeeAmt" if c_index == send_sn_index else "dlvFeeAmt"
                        sn_fee = node_fees[0] if c_index == send_sn_index else node_fees[1]
                        if fees:
                            ex_fee = fees[0] if c_index == send_sn_index else fees[1]
                        else:
                            ex_fee = copy.deepcopy(fee_currency)
                        self.assertEqual(c_info[ex_key]["amt"], f"{sn_fee:.2f}")  # 费用保留2位小数
                        self.assertEqual(c_info[ex_key]["ccy"], ex_fee)
                        fee += float(c_info[ex_key]["amt"])
                    else:
                        ex_side = "in" if c_index == 0 else "out"
                        if isRPP:
                            ex_fee_key = "instdAmt" if c_index == 0 else "intrBkSttlmAmt"
                            ex_fee_currency = parse_in_msg["cdtTrfTxInf"][ex_fee_key]["ccy"]
                        else:
                            ex_fee_currency = fee_currency
                        pn_fee = self.client.getTransactionFeeInDB(c_info["agt"]["id"], ex_fee_currency, ex_side, "PN")
                        ex_key = "sndFeeAmt" if c_index <= send_sn_index else "dlvFeeAmt"
                        self.assertEqual(c_info[ex_key]["amt"], f"{pn_fee:.2f}")  # 费用保留2位小数，不足2位应补0
                        self.assertEqual(c_info[ex_key]["ccy"], ex_fee_currency)
                        fee += float(c_info[ex_key]["amt"])

            if isRPP:
                rate_amount = rateInfo["data"]["rptOrErr"]["ccyXchg"]["rcvrAmt"]
                ex_amount = ApiUtils.parseNumberDecimal(float(rate_amount), 2)
                is_right = [c for c in tx_info["cdtTrfTxInf"]["chrgsInf"] if "dlvFeeAmt" in c]
                if is_right:
                    ex_amount = float(rate_amount) - float(is_right[0]["dlvFeeAmt"]["amt"])

                per_diff = (float(tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"]) - ex_amount) / ex_amount
                # 最终换汇的金额需要人工确认下，这个差值会随入金金额以及资金池的深度变化而变化
                self.client.logger.warning(f"下单前查询汇率得到: {ex_amount}")
                self.client.logger.warning(
                    "下单后实际可以换得: {}".format(float(tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"])))
                self.client.logger.warning(f"和预期误差范围: {per_diff} %")
                # self.assertAlmostEqual(abs(per_diff), 0.005, delta=0.001)
                # self.assertAlmostEqual(float(tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"]), ex_amount, delta=0.001)
            else:
                ex_amount = float(parse_in_msg["cdtTrfTxInf"]["instdAmt"]["amt"]) - fee
                self.assertAlmostEqual(float(tx_info["cdtTrfTxInf"]["intrBkSttlmAmt"]["amt"]), ex_amount, delta=0.001)

            for k in ["dbtr", "dbtrAcct", "cdtr", "cdtrAcct"]:
                if fromRTS and k == "dbtrAcct":
                    continue
                self.client.logger.debug(f"准备校验: {k}")
                self.checkDictMessage(tx_info["cdtTrfTxInf"][k], parse_in_msg["cdtTrfTxInf"][k])
            for k in ["dbtrAgt", "dbtrIntrmyAgt", "cdtrAgt", "cdtrIntrmyAgt", "intrmyAgt"]:
                if k in parse_in_msg["cdtTrfTxInf"]:
                    self.assertTrue(k in tx_info["cdtTrfTxInf"], f"{k}应存在rcct消息中")
                    self.assertIsNotNone(tx_info["cdtTrfTxInf"][k], f"{k}校验失败")
            cdtrAgt = parse_in_msg["cdtTrfTxInf"]["cdtrAgt"]
            cdtrAcct = parse_in_msg["cdtTrfTxInf"]["cdtrAcct"]
            if "othr" in cdtrAgt["finInstnId"]:
                self.assertEqual(cdtrAgt["finInstnId"]["othr"], tx_info["cdtTrfTxInf"]["cdtrAgt"]["finInstnId"]["othr"])
            else:
                if "bicFI" in cdtrAgt["finInstnId"] or "clrSysMmbId" in cdtrAgt["finInstnId"]:
                    self.assertEqual(cdtrAgt, tx_info["cdtTrfTxInf"]["cdtrAgt"])
                    self.assertIsNotNone(tx_info["cdtTrfTxInf"]["cdtrIntrmyAgt"], "cdtrIntrmyAgt应为查询出的节点")
                elif "iban" in cdtrAcct:
                    self.assertEqual(cdtrAgt, tx_info["cdtTrfTxInf"]["cdtrAgt"])
                    self.assertIsNotNone(tx_info["cdtTrfTxInf"]["cdtrIntrmyAgt"], "cdtrIntrmyAgt应为查询出的节点")
            self.assertDictEqual(parse_msg, tx_info)

    def checkRouterList(self, router_list, req_body, sender, path_type="pn-sn-sn-pn"):
        self.client.checkCodeAndMessage(router_list)
        router_info = router_list["data"]
        in_currency = req_body["rtgQryDef"]["qryCrit"]["rmtInf"]["sndrCcy"]
        out_currency = req_body["rtgQryDef"]["qryCrit"]["rmtInf"]["rcvrCcy"]
        # 验证msgHdr
        self.assertIsNotNone(router_info["msgHdr"]["msgId"])
        # self.assertIsNotNone(router_info["msgHdr"]["creDtTm"])
        self.assertEqual(router_info["msgHdr"]["orgnlInstgPty"], req_body["msgHdr"]["instgPty"])
        paths = None
        if RMNData.is_check_db:
            # 从数据库中查找正确的路由以及相关费用
            if self.client.rts_db_name.endswith("_v3"):
                paths, find_type = self.client.findRouterPathFromDBData(sender, req_body, self.rts_client)
            else:
                paths, find_type = self.client.findRouterPathFromDBData_old(sender, req_body, self.rts_client)
            self.assertEqual(find_type, path_type)  # 验证数据库中找到的路由类型和期望一致
            self.assertTrue(len(router_info["rptOrErr"]) <= len(paths), "由于第3方环境问题，可用路由要少")
        # 开始验证msg
        for router in router_info["rptOrErr"]:
            if req_body["rtgQryDef"]["qryCrit"]["rmtInf"]["rcvrAmt"]:
                in_quantity = float(req_body["rtgQryDef"]["qryCrit"]["rmtInf"]["rcvrAmt"])
                self.assertEqual(float(router["rmtInf"]["rcvrAmt"]), in_quantity)
            else:
                in_quantity = float(req_body["rtgQryDef"]["qryCrit"]["rmtInf"]["sndrAmt"])
                self.assertEqual(float(router["rmtInf"]["sndrAmt"]), in_quantity)
            rmt_info = router["rmtInf"]
            self.assertEqual(rmt_info["sndrCcy"], in_currency)
            self.assertEqual(rmt_info["rcvrCcy"], out_currency)

            fee = 0
            for charge_info in router["chrgsInf"]:
                # 当前节点收取的sendFee还是deliverFee
                cur_fee_key = "sndFeeAmt" if "sndFeeAmt" in charge_info else "dlvFeeAmt"
                if charge_info["agt"]["id"] == RMNData.rmn_id: cur_fee_key = "svcFeeAmt"
                fee += float(charge_info[cur_fee_key]["amt"])
            self.client.logger.info(f"准备校验rmtInf: {rmt_info}")
            if req_body["rtgQryDef"]["qryCrit"]["rmtInf"]["sndrAmt"]:
                self.assertAlmostEqual(float(rmt_info["sndrAmt"]),
                                       float(req_body["rtgQryDef"]["qryCrit"]["rmtInf"]["sndrAmt"]), delta=0.001)
                if in_currency == out_currency:
                    self.assertAlmostEqual(float(rmt_info["rcvrAmt"]), in_quantity - fee, delta=0.001)
                else:
                    sndFeeInf = [i for i in router["chrgsInf"] if "sndFeeAmt" in i.keys()]
                    dlfFeeInf = [i for i in router["chrgsInf"] if "dlvFeeAmt" in i.keys()]
                    in_fee, out_fee = 0, 0
                    if sndFeeInf:
                        in_fee = float(sndFeeInf[0]["sndFeeAmt"]["amt"])
                    if dlfFeeInf:
                        if dlfFeeInf[0]["dlvFeeAmt"]["ccy"] == out_currency:
                            out_fee = float(dlfFeeInf[0]["dlvFeeAmt"]["amt"])
                        else:
                            in_fee += float(dlfFeeInf[0]["dlvFeeAmt"]["amt"])
                    self.client.logger.warning(
                        f"{out_currency}->{in_currency}汇率: {(float(rmt_info['rcvrAmt']) + out_fee) / float(in_quantity - in_fee)}:1")
            if paths:
                path = [p for p in paths if p == router["chrgsInf"]]
                self.assertEqual(len(path), 1, f"{json.dumps(router['chrgsInf'])}找不到对应的路由")
                path = path[0]
                self.assertEqual(router["chrgsInf"], path)
            else:
                path = None
            self.assertEqual(router["trnRtgInf"]["dbtrAgt"]["finInstnId"]["othr"]["id"], req_body["msgHdr"]["instgPty"])
            self.assertEqual(router["trnRtgInf"]["dbtrAgt"]["finInstnId"]["othr"]["schmeCd"], "ROXE")
            self.assertEqual(router["trnRtgInf"]["dbtrAgt"]["finInstnId"]["othr"]["issr"], path_type.split("-")[0].upper())
            if "pn-sn" in path_type:
                if path: self.assertEqual(router["trnRtgInf"]["dbtrIntrmyAgt"]["finInstnId"]["othr"]["id"], path[1]["agt"]["id"])
                self.assertEqual(router["trnRtgInf"]["dbtrIntrmyAgt"]["finInstnId"]["othr"]["schmeCd"], "ROXE")
                self.assertEqual(router["trnRtgInf"]["dbtrIntrmyAgt"]["finInstnId"]["othr"]["issr"], path_type.split("-")[1].upper())
            if "sn-pn" in path_type:
                if path: self.assertEqual(router["trnRtgInf"]["cdtrIntrmyAgt"]["finInstnId"]["othr"]["id"], path[-2]["agt"]["id"])
                self.assertEqual(router["trnRtgInf"]["cdtrIntrmyAgt"]["finInstnId"]["othr"]["schmeCd"], "ROXE")
                self.assertEqual(router["trnRtgInf"]["cdtrIntrmyAgt"]["finInstnId"]["othr"]["issr"], path_type.split("-")[-2].upper())
            if path: self.assertEqual(router["trnRtgInf"]["cdtrAgt"]["finInstnId"]["othr"]["id"], path[-1]["agt"]["id"])
            self.assertEqual(router["trnRtgInf"]["cdtrAgt"]["finInstnId"]["othr"]["schmeCd"], "ROXE")
            self.assertEqual(router["trnRtgInf"]["cdtrAgt"]["finInstnId"]["othr"]["issr"], path_type.split("-")[-1].upper())
            if router["trnRtgInf"]["cdtrAgt"]["finInstnId"]["othr"]["id"] != RMNData.mock_node:
                self.assertIsNotNone(router["trnRtgInf"]["msgRqdFld"], "通道节点是有模拟节点的")
                self.checkRouterFields(router["trnRtgInf"]["msgRqdFld"])

    def checkRouterFields(self, routerFields):
        field_map_info = None
        if RMNData.is_check_db:
            # field_map_info = self.client.mysql.exec_sql_query("select * from `roxe_risn_config`.risn_field_mapping")
            field_map_info = self.client.mysql.exec_sql_query("select * from risn_field_mapping")

        for std_field in routerFields["msgStnrdFld"]:
            with self.subTest(msg=f"校验失败: {std_field}", filed=std_field):
                self.assertIsNotNone(std_field["fldNm"])
                self.assertIsNotNone(std_field["fldTp"])
                self.assertIsNotNone(std_field["fldDesc"])
                self.assertIsInstance(std_field["fldRequired"], bool)
                if std_field["fldTp"] == "list":
                    self.assertIsInstance(std_field["fldOpts"], list)
                else:
                    self.assertNotIn("fldOpts", std_field)
                if field_map_info:
                    cur_field_db = [i for i in field_map_info if i["rmnField"] == std_field["fldNm"]]
                    self.assertTrue(len(cur_field_db) >= 1, f"数据库中{std_field['fldNm']}字段映射不正确: {cur_field_db}")
                    self.assertEqual(std_field["fldNm"], cur_field_db[0]["rmnField"])
        if "msgNstnrdFld" in routerFields:
            for nstd_field in routerFields["msgNstnrdFld"]:
                with self.subTest(msg=f"校验失败: {nstd_field}", filed=nstd_field):
                    self.assertIsNotNone(nstd_field["fldNm"])
                    self.assertIsNotNone(nstd_field["fldTp"])
                    self.assertIsNotNone(nstd_field["fldDesc"])
                    self.assertIsInstance(nstd_field["fldRequired"], bool)
                    if field_map_info:
                        self.assertNotIn(nstd_field["fldNm"], field_map_info[0]["rmnField"])

    def checkConfirmMessage(self, confirm_msg, status_code, olg_msg_id, old_msg_type, old_sender, end_to_end_id, tx_id, acctSvcrRef, pendingMsg=None):
        if not RMNData.is_check_db:
            return
        confirm_msg_id = confirm_msg["grpHdr"]["msgId"]
        send_msg = self.client.mysql.exec_sql_query(f"select * from roxe_rmn.rmn_notify_info where msg_id='{confirm_msg_id}'")
        self.assertEqual(json.loads(send_msg[0]["msgContent"]), confirm_msg)

        self.assertEqual(confirm_msg["msgType"], "RTPC")
        self.assertEqual(confirm_msg["grpHdr"]["instgAgt"], RMNData.rmn_id)
        self.assertEqual(confirm_msg["grpHdr"]["instdAgt"], old_sender)
        self.assertEqual(confirm_msg["orgnlGrpInfAndSts"]["orgnlMsgId"], olg_msg_id)
        self.assertEqual(confirm_msg["orgnlGrpInfAndSts"]["orgnlMsgNmId"], old_msg_type)

        self.assertEqual(confirm_msg["txInfAndSts"]["stsId"], status_code)
        if confirm_msg["orgnlGrpInfAndSts"]["orgnlMsgNmId"] != "RPRN":
            self.assertEqual(confirm_msg["txInfAndSts"]["orgnlEndToEndId"], end_to_end_id)
            self.assertEqual(confirm_msg["txInfAndSts"]["orgnlTxId"], tx_id)
        self.assertEqual(confirm_msg["txInfAndSts"]["acctSvcrRef"], acctSvcrRef)
        # self.assertEqual(confirm_msg["txInfAndSts"]["instgAgt"], old_sender) todo
        if status_code == "PDNG":
            if pendingMsg:
                ex_msg = pendingMsg
                self.assertEqual(confirm_msg["txInfAndSts"]["stsRsnInf"]["stsRsnCd"], "00100110")
            else:
                notify_sql = f"select * from rmn_rts_message where rmn_txn_id='{send_msg[0]['rmnTxnId']}' and rts_state='PENDING'"
                rts_notify = self.client.mysql.exec_sql_query(notify_sql)[0]["rtsMsgContent"]
                rts_log = json.loads(rts_notify)["log"]["info"]
                ex_msg = '%s,%s' % (rts_log["errorCode"], rts_log["message"])
                self.assertEqual(confirm_msg["txInfAndSts"]["stsRsnInf"]["stsRsnCd"], "00100109")
            self.assertEqual(ex_msg, confirm_msg["txInfAndSts"]["stsRsnInf"]["addtlInf"])
            return ex_msg

    def getSendFeeAndDeliverFee(self, sendCurrency, sendCountry, recCurrency, recCountry, leftChannel, rightChannel):
        channel_info_in = self.client.mysql.exec_sql_query("select * from roxe_rpc.rpc_corridor_info where channel_name like '%{}%' and currency like '%{}%' and country like '%{}%' and corridor_type={}".format(leftChannel, sendCurrency, sendCountry, 1))
        channel_info_out = self.client.mysql.exec_sql_query("select * from roxe_rpc.rpc_corridor_info where channel_name like '%{}%' and currency like '%{}%' and country like '%{}%' and corridor_type={}".format(rightChannel, recCurrency, recCountry, 0))
        # print(channel_info_in)
        # print(channel_info_out)
        # channel_group_info = self.client.mysql.exec_sql_query("select * from roxe_rpc.rpc_channel_info where channel_name like '%{}%'".format(rightChannel))
        if len(channel_info_in) == 1 and len(channel_info_out) == 1:
            sendFee = Decimal(float(channel_info_in[0]["inFeeAmount"])).quantize(Decimal('0.00'))
            deliverFee = Decimal(float(channel_info_out[0]["outBankFee"])).quantize(Decimal('0.00'))
            # if channel_group_info[0]["channelGroups"] != "ROXE":
            #     deliverFee = 0.00
            # else:
            #     deliverFee = Decimal(float(channel_info_out[0]["outBankFee"])).quantize(Decimal('0.00'))
            return sendFee, deliverFee

    def checkRtsMsgTransferRMN(self, rcct_msg, cdtTrfTxInf):
        rcct_info = rcct_msg["cdtTrfTxInf"]
        self.assertEqual(rcct_info["dbtr"]["nm"], cdtTrfTxInf["dbtr"]["nm"])
        self.assertEqual(rcct_info["cdtr"]["nm"], cdtTrfTxInf["cdtr"]["nm"])
        self.assertEqual(rcct_info["splmtryData"]["envlp"], cdtTrfTxInf["splmtryData"]["envlp"])
        self.assertEqual(rcct_info["splmtryData"]["rmrk"], cdtTrfTxInf["splmtryData"]["rmrk"])
        self.assertEqual(rcct_info["purp"]["desc"], cdtTrfTxInf["purp"]["desc"])
        self.assertEqual(rcct_info["cdtrAcct"], cdtTrfTxInf["cdtrAcct"])

        self.assertEqual(rcct_info["dbtr"]["pstlAdr"]["adrLine"], cdtTrfTxInf["dbtr"]["pstlAdr"]["adrLine"])
        self.assertEqual(rcct_info["dbtr"]["pstlAdr"]["ctrySubDvsn"], cdtTrfTxInf["dbtr"]["pstlAdr"]["ctrySubDvsn"])
        self.assertEqual(rcct_info["dbtr"]["pstlAdr"]["pstCd"], cdtTrfTxInf["dbtr"]["pstlAdr"]["pstCd"])
        self.assertEqual(rcct_info["dbtr"]["pstlAdr"]["twnNm"], cdtTrfTxInf["dbtr"]["pstlAdr"]["twnNm"])
        self.assertEqual(rcct_info["dbtr"]["pstlAdr"]["ctry"], cdtTrfTxInf["dbtr"]["pstlAdr"]["ctry"])

        self.assertEqual(rcct_info["cdtr"]["pstlAdr"]["adrLine"], cdtTrfTxInf["cdtr"]["pstlAdr"]["adrLine"])
        self.assertEqual(rcct_info["cdtr"]["pstlAdr"]["ctrySubDvsn"], cdtTrfTxInf["cdtr"]["pstlAdr"]["ctrySubDvsn"])
        self.assertEqual(rcct_info["cdtr"]["pstlAdr"]["pstCd"], cdtTrfTxInf["cdtr"]["pstlAdr"]["pstCd"])
        self.assertEqual(rcct_info["cdtr"]["pstlAdr"]["twnNm"], cdtTrfTxInf["cdtr"]["pstlAdr"]["twnNm"])
        self.assertEqual(rcct_info["cdtr"]["pstlAdr"]["ctry"], cdtTrfTxInf["cdtr"]["pstlAdr"]["ctry"])

        if "prvtId" in cdtTrfTxInf["dbtr"]:
            self.assertEqual(rcct_info["dbtr"]["prvtId"]["othr"], cdtTrfTxInf["dbtr"]["prvtId"]["othr"])
            self.assertEqual(rcct_info["dbtr"]["prvtId"]["dtAndPlcOfBirth"]["ctryOfBirth"], cdtTrfTxInf["dbtr"]["prvtId"]["dtAndPlcOfBirth"]["ctryOfBirth"])
            self.assertEqual(rcct_info["dbtr"]["prvtId"]["dtAndPlcOfBirth"]["birthDt"], cdtTrfTxInf["dbtr"]["prvtId"]["dtAndPlcOfBirth"]["birthDt"])

        if "prvtId" in cdtTrfTxInf["cdtr"]:
            self.assertEqual(rcct_info["cdtr"]["prvtId"]["othr"]["id"], cdtTrfTxInf["cdtr"]["prvtId"]["othr"]["id"])
            self.assertEqual(rcct_info["cdtr"]["prvtId"]["othr"]["prtry"], cdtTrfTxInf["cdtr"]["prvtId"]["othr"]["prtry"])
            self.assertEqual(rcct_info["cdtr"]["prvtId"]["dtAndPlcOfBirth"]["ctryOfBirth"], cdtTrfTxInf["cdtr"]["prvtId"]["dtAndPlcOfBirth"]["ctryOfBirth"])
            self.assertEqual(rcct_info["cdtr"]["prvtId"]["dtAndPlcOfBirth"]["birthDt"], cdtTrfTxInf["cdtr"]["prvtId"]["dtAndPlcOfBirth"]["birthDt"])

        if "orgId" in cdtTrfTxInf["dbtr"]:
            self.assertEqual(rcct_info["dbtr"]["orgId"], cdtTrfTxInf["dbtr"]["orgId"])

        if "orgId" in cdtTrfTxInf["cdtr"]:
            self.assertEqual(rcct_info["cdtr"]["orgId"], cdtTrfTxInf["cdtr"]["orgId"])

        self.assertEqual(rcct_info["dbtrAgt"]["finInstnId"]["othr"], cdtTrfTxInf["dbtrAgt"]["finInstnId"]["othr"])
        if "othr" in cdtTrfTxInf["cdtrAgt"]["finInstnId"]:
            self.assertEqual(rcct_info["cdtrAgt"]["finInstnId"]["othr"], cdtTrfTxInf["cdtrAgt"]["finInstnId"]["othr"])

        if "finInstnId" in cdtTrfTxInf["cdtrAgt"] and "bicFI" in cdtTrfTxInf["cdtrAgt"]["finInstnId"]:
            self.assertEqual(rcct_info["cdtrAgt"]["finInstnId"]["bicFI"], cdtTrfTxInf["cdtrAgt"]["finInstnId"]["bicFI"])
        elif "clrSysMmbId" in cdtTrfTxInf["cdtrAgt"]["finInstnId"]:
            self.assertEqual(rcct_info["cdtrAgt"]["finInstnId"]["clrSysMmbId"], cdtTrfTxInf["cdtrAgt"]["finInstnId"]["clrSysMmbId"])

        if "brnchId" in cdtTrfTxInf["cdtrAgt"]:
            self.assertEqual(rcct_info["cdtrAgt"]["brnchId"]["nm"], rcct_info["cdtrAgt"]["brnchId"]["nm"])
            self.assertEqual(rcct_info["cdtrAgt"]["brnchId"]["id"], rcct_info["cdtrAgt"]["brnchId"]["id"])

    def checkPendingTransactionReason(self, rmn_tx_id, msg_id, node, end2end_id, pendingMsg=None):
        f_sql = f"select * from rmn_notify_info where rmn_txn_id='{rmn_tx_id}' and msg_content like '%PDNG%'"
        notify_info = ApiUtils.waitCondition(
            self.client.mysql.exec_sql_query, (f_sql,),
            lambda func_res: len(func_res) > 0, 120, 15
        )
        self.client.logger.info(f"发送给SN1的pending RTPC: {notify_info}")
        pending_msg = self.checkConfirmMessage(json.loads(notify_info[0]["msgContent"]), "PDNG", msg_id, "RCCT", node,
                                               end2end_id, end2end_id, "TXNN", pendingMsg=pendingMsg)

        order_info = self.client.step_queryTransactionState(node, RMNData.api_key, RMNData.sec_key, msg_id, node)
        assert pending_msg in order_info["data"]["rptOrErr"]["pmt"]["addtlNtryInf"], "pending原因未出现在查询交易的结果中"


class RMNApiTest(BaseCheckRMN):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        # cls.client = RMNApiClient(RMNData.host, "test", RMNData.api_key, RMNData.sec_key, check_db=RMNData.is_check_db, sql_cfg=RMNData.sql_cfg)
        cls.rts_client = RTSApiClient(RTSData.host, RTSData.api_id, RTSData.sec_key, RTSData.ssl_pub_key)
        if "prod" not in RMNData.env:
            cls.rpc_client = RPCApiClient(RPCData.host, RPCData.chain_host)
        # cls.chain_client = Clroxe(RMNData.chain_host)

    def test_001_getExchangeRate_sameCurrency(self):
        """
        查询汇率，同币种
        """
        sender = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        rate_res, req_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", "23.45", "USD")
        self.checkExchangeRate(rate_res, req_msg)

        ts_headers = self.client.make_header(sender, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        rate_res, req_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", None, "USD", "23.5")
        self.checkExchangeRate(rate_res, req_msg)

    def test_002_getExchangeRate_diffCurrency(self):
        """
        查询汇率，不同币种
        """
        sender = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        rate_res, req_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", "203.45", "PHP")
        self.checkExchangeRate(rate_res, req_msg)

        ts_headers = self.client.make_header(sender, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        rate_res, req_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "PHP", None, "USD", "1223.5")
        self.checkExchangeRate(rate_res, req_msg)

    def test_003_getRouterList_senderIsSN_sameCurrency_snRoxeId(self):
        """
        查询路由, 消息发送方为SN节点, 指定sn2 roxe id
        """
        sender = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        # agent_info = self.client.make_roxe_agent(RMNData.sn_usd_gb, "SN")
        agent_info = self.client.make_roxe_agent(sender, "SN")
        msg = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAgt=agent_info)
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "sn-sn")

    def test_004_getRouterList_senderIsSN_sameCurrency_pnRoxeId(self):
        """
        查询路由, 消息发送方为SN节点, 指定sn2 roxe id
        """
        sender = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(RMNData.pn_usd_gb, "PN")
        msg = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAgt=agent_info)
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "sn-sn-pn")

    def test_005_getRouterList_senderIsSN_sameCurrency_iban(self):
        """
        查询路由, 消息发送方为SN节点, 指定creditorAccount
        """
        sender = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAcct={"iban": RMNData.iban["GBP"]})
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "sn-sn")

    def test_006_getRouterList_senderIsSN_sameCurrency_bicCode(self):
        """
        查询路由, 消息发送方为SN节点, 指定Swift/bic code
        """
        sender = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAgt=RMNData.bic_agents["GBP"])
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "sn-sn")

    def test_007_getRouterList_senderIsSN_sameCurrency_nccCode(self):
        """
        查询路由, 消息发送方为SN节点, 指定NCC code
        """
        sender = RMNData.sn_usd_us
        ncc_ccy = "GBP" if RMNData.env in ["uat", "bjtest"] else "USD"
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAgt=RMNData.ncc_agents[ncc_ccy])
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "sn-sn")

    def test_008_getRouterList_senderIsPN_sameCurrency_snRoxeId(self):
        sender = RMNData.pn_usd_us
        sn = RMNData.sn_usd_gb
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAgt=self.client.make_roxe_agent(sn, "SN"))
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "pn-sn-sn")

    def test_009_getRouterList_senderIsPN_sameCurrency_pnRoxeId(self):
        sender = RMNData.pn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAgt=self.client.make_roxe_agent(RMNData.pn_usd_gb, "PN"))
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "pn-sn-sn-pn")

    def test_010_getRouterList_senderIsPN_sameCurrency_iban(self):
        """
        查询路由, 消息发送方为SN节点, 指定creditorAccount
        """
        sender = RMNData.pn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAcct={"iban": RMNData.iban["GBP"]})
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "pn-sn-sn")

    def test_011_getRouterList_senderIsPN_sameCurrency_bicCode(self):
        """
        查询路由, 消息发送方为SN节点, 指定Swift/bic code
        """
        sender = RMNData.pn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAgt=RMNData.bic_agents["GBP"])
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "pn-sn-sn")

    def test_012_getRouterList_senderIsPN_sameCurrency_nccCode(self):
        """
        查询路由, 消息发送方为SN节点, 指定NCC code
        """
        sender = RMNData.pn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAgt=RMNData.ncc_agents["GBP"])
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "pn-sn-sn")

    def test_013_getRouterList_senderIsSN_differentCurrency_snRoxeId(self):
        """
        查询路由, 消息发送方为SN节点, 指定sn2 roxe id
        """
        sender = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(RMNData.sn_usd_us, "SN")

        amt = str(ApiUtils.parseNumberDecimal(ApiUtils.randAmount(10000, 2)))
        msg = self.client.make_RRLQ_information("USD", "PHP", amt, cdtrAgt=agent_info)
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "sn-sn")

    def test_014_getRouterList_senderIsSN_differentCurrency_pnRoxeId(self):
        """
        查询路由, 消息发送方为SN节点, 指定sn2 roxe id
        """
        sender = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(RMNData.pn_php_ph, "PN")
        amt = str(ApiUtils.parseNumberDecimal(ApiUtils.randAmount(10000, 2)))
        msg = self.client.make_RRLQ_information("USD", "PHP", amt, cdtrAgt=agent_info)
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "sn-sn-pn")

    def test_015_getRouterList_senderIsSN_differentCurrency_iban(self):
        """
        查询路由, 消息发送方为SN节点, 指定creditorAccount
        """
        sender = RMNData.sn_gbp_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        amt = str(ApiUtils.parseNumberDecimal(ApiUtils.randAmount(10000, 2)))
        msg = self.client.make_RRLQ_information("USD", "GBP", amt, cdtrAcct={"iban": RMNData.iban["GBP"]})
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "sn-sn")

    def test_016_getRouterList_senderIsSN_differentCurrency_bicCode(self):
        """
        查询路由, 消息发送方为SN节点, 指定Swift/bic code
        """
        sender = RMNData.sn_gbp_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        amt = str(ApiUtils.parseNumberDecimal(ApiUtils.randAmount(10000, 2)))
        msg = self.client.make_RRLQ_information("USD", "GBP", amt, cdtrAgt=RMNData.bic_agents["GBP"])
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "sn-sn")

    def test_017_getRouterList_senderIsSN_differentCurrency_nccCode(self):
        """
        查询路由, 消息发送方为SN节点, 指定NCC code
        """
        sender = RMNData.sn_gbp_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        amt = str(ApiUtils.parseNumberDecimal(ApiUtils.randAmount(10000, 2)))
        msg = self.client.make_RRLQ_information("USD", "GBP", amt, cdtrAgt=RMNData.ncc_agents["GBP"])
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "sn-sn")

    def test_018_getRouterList_senderIsPN_differentCurrency_snRoxeId(self):
        sender = RMNData.pn_usd_us
        sn = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        amt = str(ApiUtils.parseNumberDecimal(ApiUtils.randAmount(1000, 2)))
        msg = self.client.make_RRLQ_information("USD", "PHP", amt, cdtrAgt=self.client.make_roxe_agent(sn, "SN"))
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "pn-sn-sn")

    def test_019_getRouterList_senderIsPN_differentCurrency_pnRoxeId(self):
        sender = RMNData.pn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        amt = str(ApiUtils.parseNumberDecimal(ApiUtils.randAmount(1000, 2)))
        msg = self.client.make_RRLQ_information("USD", "PHP", amt, cdtrAgt=self.client.make_roxe_agent(RMNData.pn_php_ph, "PN"))
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "pn-sn-sn-pn")

    def test_020_getRouterList_senderIsPN_differentCurrency_iban(self):
        """
        查询路由, 消息发送方为SN节点, 指定creditorAccount
        """
        sender = RMNData.pn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("GBP", "USD", "23.45", cdtrAcct={"iban": RMNData.iban["GBP"]})
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "pn-sn-sn")

    def test_021_getRouterList_senderIsPN_differentCurrency_bicCode(self):
        """
        查询路由, 消息发送方为SN节点, 指定Swift/bic code
        """
        sender = RMNData.pn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("USD", "GBP", "123.67", cdtrAgt=RMNData.bic_agents["GBP"])
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "pn-sn-sn")

    def test_022_getRouterList_senderIsPN_differentCurrency_nccCode(self):
        """
        查询路由, 消息发送方为SN节点, 指定NCC code
        """
        sender = RMNData.pn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("USD", "GBP", "32.79", cdtrAgt=RMNData.ncc_agents["GBP"])
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "pn-sn-sn")

    # SN -> SN 主流程

    def test_023_sn_sn_cdtrAgtGiveSNRoxeId_sameCurrency(self):
        """
        主流程: sn_sn, cdtrAgt有roxeId, 且为SN, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        sn2 = sn1

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amount)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId_b, creditor_agent, sn1_fee, sn1, inAmount=amount)
        cdtTrfTxInf['cdtr']["pstlAdr"]["ctry"] = "US"
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_024_sn_sn_cdtrAgtGiveBIC_sameCurrency(self):
        sn1 = RMNData.sn_usd_us

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amount = ApiUtils.randAmount(15, 2, 10)
        amount = 11.4
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amount)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_025_sn_sn_cdtrAgtGiveNCC_sameCurrency(self):
        sn1 = RMNData.sn_usd_us
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.ncc_agents["USD"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amount)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_026_sn_sn_cdtrGiveIBAN_sameCurrency(self):
        sn1 = RMNData.sn_gbp_us
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.iban_agent
        amount = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amount)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1, inAmount=amount)
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_027_sn_sn_cdtrAgtGiveBIC_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        sn1 = RMNData.sn_usd_us
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amount)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1, inAmount=amount)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_028_sn_sn_cdtrAgtGiveNCC_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amount)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1, inAmount=amount)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_029_sn_sn_cdtrGiveIBAN_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        sn1 = RMNData.sn_gbp_us
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.iban_agent
        amount = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amount)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1, inAmount=amount)
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    # SN -> SN -> PN 主流程

    def test_030_sn_sn_pn_cdtrAgtGivePNRoxeId_sameCurrency(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amount)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_pn(sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_031_sn_sn_pn_cdtrAgtGivePNRoxeId_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amount)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1, inAmount=amount)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_pn(sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_032_sn_sn_pn_cdtrIntrmyAgtGivePNRoxeID_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amount)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1, inAmount=amount)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_pn(sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_033_sn_sn_pn_cdtrAgtGiveBIC_cdtrIntrmyAgtGivePNRoxeId_sameCurrency(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amount)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1, inAmount=amount)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_pn(sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_034_sn_sn_pn_cdtrAgtGiveNCC_cdtrIntrmyAgtGivePNRoxeId_sameCurrency(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amount)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1, inAmount=amount)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_pn(sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_035_sn_sn_pn_cdtrGiveIBAN_cdtrIntrmyAgtGivePNRoxeId_sameCurrency(self):
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        cdtrIntrmyAgt = self.client.make_roxe_agent(pn2, "PN")
        creditor_agent = RMNData.iban_agent
        amount = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "GBP", "GBP", creditor_agent=cdtrIntrmyAgt, amount=amount)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1, inAmount=amount)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_pn(sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_036_sn_sn_pn_cdtrAgtGiveBIC_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amount)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1, inAmount=amount)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_pn(sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_037_sn_sn_pn_cdtrAgtGiveNCC_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amount)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1, inAmount=amount)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_pn(sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_038_sn_sn_pn_cdtrAgtGiveIBAN_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.iban_agent
        amount = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "GBP", "GBP", cdtrAcct=dict(iban=RMNData.iban["GBP"]), amount=amount)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1, inAmount=amount)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_pn(sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    # PN -> SN -> SN 主流程
    def test_039_pn_sn_sn_dbtrAgtGivePNRoxeId_cdtrAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_040_pn_sn_sn_dbtrAgtGiveBIC_cdtrAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent["finInstnId"]["bicFI"] = RMNData.bic_agents["USD"]["finInstnId"]["bicFI"]
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_041_pn_sn_sn_dbtrAgtGiveNCC_cdtrAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_042_pn_sn_sn_dbtrGiveIBAN_cdtrAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(pn1, "GBP", "GBP", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_043_pn_sn_sn_dbtrAgtGivePNRoxeId_cdtrAgtGiveBIC_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_044_pn_sn_sn_dbtrAgtGivePNRoxeId_cdtrAgtGiveNCC_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_045_pn_sn_sn_dbtrAgtGivePNRoxeId_cdtrGiveIBAN_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_046_pn_sn_sn_dbtrAgtGiveBIC_cdtrAgtGiveBIC_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_047_pn_sn_sn_dbtrAgtGiveBIC_cdtrAgtGiveNCC_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_048_pn_sn_sn_dbtrAgtGiveBIC_cdtrGiveIBAN_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct=dict(iban=RMNData.iban["GBP"]), amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_049_pn_sn_sn_dbtrAgtGiveNCC_cdtrAgtGiveBIC_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_050_pn_sn_sn_dbtrAgtGiveNCC_cdtrAgtGiveNCC_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_051_pn_sn_sn_dbtrAgtGiveNCC_cdtrGiveIBAN_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_052_pn_sn_sn_dbtrGiveIBAN_cdtrAgtGiveBIC_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_053_pn_sn_sn_dbtrGiveIBAN_cdtrAgtGiveNCC_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_054_pn_sn_sn_dbtrGiveIBAN_cdtrGiveIBAN_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_055_pn_sn_sn_dbtrAgtGivePNRoxeId_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_056_pn_sn_sn_dbtrAgtGiveBIC_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_057_pn_sn_sn_dbtrAgtGiveNCC_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_058_pn_sn_sn_dbtrAgtGiveIBAN_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_059_pn_sn_sn_dbtrAgtGivePNRoxeId_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveBIC_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_060_pn_sn_sn_dbtrAgtGivePNRoxeId_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveNCC_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_061_pn_sn_sn_dbtrAgtGivePNRoxeId_dbtrIntrmyAgtGiveSNRoxeId_cdtrGiveIBAN_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_062_pn_sn_sn_dbtrAgtGiveBIC_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveBIC_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_063_pn_sn_sn_dbtrAgtGiveBIC_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveNCC_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_064_pn_sn_sn_dbtrAgtGiveBIC_dbtrIntrmyAgtGiveSNRoxeId_cdtrGiveIBAN_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_065_pn_sn_sn_dbtrAgtGiveNCC_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveBIC_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_066_pn_sn_sn_dbtrAgtGiveNCC_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveNCC_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_067_pn_sn_sn_dbtrAgtGiveNCC_dbtrIntrmyAgtGiveSNRoxeId_cdtrGiveIBAN_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_068_pn_sn_sn_dbtrGiveIBAN_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveBIC_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_069_pn_sn_sn_dbtrGiveIBAN_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveNCC_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_070_pn_sn_sn_dbtrGiveIBAN_dbtrIntrmyAgtGiveSNRoxeId_cdtrGiveIBAN_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_071_pn_sn_sn_dbtrAgtGivePNRoxeId_cdtrAgtGiveBIC_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        # sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(100, 2, )
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent,
                                                             amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, pn1_fee, pn1, inAmount=amt)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_072_pn_sn_sn_dbtrAgtGivePNRoxeId_cdtrAgtGiveNCC_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        # sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, pn1_fee, pn1, inAmount=amt)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_073_pn_sn_sn_dbtrAgtGivePNRoxeId_cdtrAgtGiveIBAN_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        # sn2 = RMNData.sn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct=dict(iban=RMNData.iban["GBP"]), amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_074_pn_sn_sn_dbtrAgtGiveBIC_cdtrAgtGiveBIC_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        # sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent,
                                                             amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, pn1_fee, pn1, inAmount=amt)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_075_pn_sn_sn_dbtrAgtGiveBIC_cdtrAgtGiveNCC_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        # sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent,
                                                             amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, pn1_fee, pn1, inAmount=amt)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_076_pn_sn_sn_dbtrAgtGiveBIC_cdtrAgtGiveIBAN_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        # sn2 = RMNData.sn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct=dict(iban=RMNData.iban["GBP"]), amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_077_pn_sn_sn_dbtrAgtGiveNCC_cdtrAgtGiveBIC_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        # sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent,
                                                             amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, pn1_fee, pn1, inAmount=amt)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_078_pn_sn_sn_dbtrAgtGiveNCC_cdtrAgtGiveNCC_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        # sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent,
                                                             amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, pn1_fee, pn1, inAmount=amt)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_079_pn_sn_sn_dbtrAgtGiveNCC_cdtrAgtGiveIBAN_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        # sn2 = RMNData.sn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct=dict(iban=RMNData.iban["GBP"]), amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_080_pn_sn_sn_dbtrGiveIBAN_cdtrAgtGiveBIC_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        # sn2 = RMNData.sn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct=dict(iban=RMNData.iban["GBP"]), amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_081_pn_sn_sn_dbtrGiveIBAN_cdtrAgtGiveNCC_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        # sn2 = RMNData.sn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct=dict(iban=RMNData.iban["GBP"]), amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_082_pn_sn_sn_dbtrGiveIBAN_cdtrAgtGiveIBAN_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        # sn2 = RMNData.sn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct=dict(iban=RMNData.iban["GBP"]), amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_083_pn_sn_sn_dbtrAgtGivePNRoxeId_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveBIC_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        # sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent,
                                                             amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_084_pn_sn_sn_dbtrAgtGivePNRoxeId_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveNCC_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        # sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent,
                                                             amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_085_pn_sn_sn_dbtrAgtGivePNRoxeId_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveIBAN_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        # sn2 = RMNData.sn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct=dict(iban=RMNData.iban["GBP"]), amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_086_pn_sn_sn_dbtrAgtGiveBIC_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveBIC_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        # sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent,
                                                             amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_087_pn_sn_sn_dbtrAgtGiveBIC_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveNCC_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        # sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent,
                                                             amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_088_pn_sn_sn_dbtrAgtGiveBIC_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveIBAN_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        # sn2 = RMNData.sn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct=dict(iban=RMNData.iban["GBP"]), amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_089_pn_sn_sn_dbtrAgtGiveNCC_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveBIC_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        # sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent,
                                                             amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_090_pn_sn_sn_dbtrAgtGiveNCC_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveNCC_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        # sn2 = RMNData.sn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent,
                                                             amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_091_pn_sn_sn_dbtrAgtGiveNCC_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveIBAN_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        # sn2 = RMNData.sn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct=dict(iban=RMNData.iban["GBP"]), amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_092_pn_sn_sn_dbtrGiveIBAN_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveBIC_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        # sn2 = RMNData.sn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct=dict(iban=RMNData.iban["GBP"]), amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_093_pn_sn_sn_dbtrGiveIBAN_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveNCC_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        # sn2 = RMNData.sn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct=dict(iban=RMNData.iban["GBP"]), amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_094_pn_sn_sn_dbtrGiveIBAN_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveIBAN_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        # sn2 = RMNData.sn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct=dict(iban=RMNData.iban["GBP"]), amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    # PN -> SN -> SN -> PN

    def test_095_pn_sn_sn_pn_dbtrAgtGivePNRoxeId_cdtrAgtGivePNRoxeId_sameCurrency(self):
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
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_096_pn_sn_sn_pn_dbtrAgtGivePNRoxeId_cdtrAgtGivePNRoxeId_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_097_pn_sn_sn_pn_dbtrAgtGivePNRoxeId_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_098_pn_sn_sn_pn_dbtrAgtGivePNRoxeId_cdtrAgtGiveBIC_cdtrIntrmyAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_099_pn_sn_sn_pn_dbtrAgtGivePNRoxeId_cdtrAgtGiveNCC_cdtrIntrmyAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_100_pn_sn_sn_pn_dbtrAgtGivePNRoxeId_cdtrGiveIBAN_cdtrIntrmyAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_101_pn_sn_sn_pn_dbtrAgtGivePNRoxeId_cdtrAgtGiveBIC_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_102_pn_sn_sn_pn_dbtrAgtGivePNRoxeId_cdtrAgtGiveNCC_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_103_pn_sn_sn_pn_dbtrAgtGivePNRoxeId_cdtrAgtGiveIBAN_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(100, 2, 30)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct=dict(iban=RMNData.iban["GBP"]), amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_104_pn_sn_sn_pn_dbtrAgtGiveBIC_cdtrAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_105_pn_sn_sn_pn_dbtrAgtGiveBIC_cdtrAgtGivePNRoxeId_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_106_pn_sn_sn_pn_dbtrAgtGiveBIC_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_107_pn_sn_sn_pn_dbtrAgtGiveBIC_cdtrAgtGiveBIC_cdtrIntrmyAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_108_pn_sn_sn_pn_dbtrAgtGiveBIC_cdtrAgtGiveNCC_cdtrIntrmyAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_109_pn_sn_sn_pn_dbtrAgtGiveBIC_cdtrGiveIBAN_cdtrIntrmyAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_110_pn_sn_sn_pn_dbtrAgtGiveBIC_cdtrAgtGiveBIC_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_111_pn_sn_sn_pn_dbtrAgtGiveBIC_cdtrAgtGiveNCC_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_112_pn_sn_sn_pn_dbtrAgtGiveBIC_cdtrAgtGiveIBAN_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(100, 2, 20)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct=dict(iban=RMNData.iban["GBP"]), amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_113_pn_sn_sn_pn_dbtrAgtGiveNCC_cdtrAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_114_pn_sn_sn_pn_dbtrAgtGiveNCC_cdtrAgtGivePNRoxeId_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_115_pn_sn_sn_pn_dbtrAgtGiveNCC_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_116_pn_sn_sn_pn_dbtrAgtGiveNCC_cdtrAgtGiveBIC_cdtrIntrmyAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_117_pn_sn_sn_pn_dbtrAgtGiveNCC_cdtrAgtGiveNCC_cdtrIntrmyAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_118_pn_sn_sn_pn_dbtrAgtGiveNCC_cdtrGiveIBAN_cdtrIntrmyAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_119_pn_sn_sn_pn_dbtrAgtGiveNCC_cdtrAgtGiveBIC_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_120_pn_sn_sn_pn_dbtrAgtGiveNCC_cdtrAgtGiveNCC_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_121_pn_sn_sn_pn_dbtrAgtGiveNCC_cdtrAgtGiveIBAN_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_122_pn_sn_sn_pn_dbtrAgtGiveIBAN_cdtrAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_123_pn_sn_sn_pn_dbtrAgtGiveIBAN_cdtrAgtGivePNRoxeId_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_124_pn_sn_sn_pn_dbtrAgtGiveIBAN_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_125_pn_sn_sn_pn_dbtrAgtGiveIBAN_cdtrAgtGiveBIC_cdtrIntrmyAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_126_pn_sn_sn_pn_dbtrAgtGiveIBAN_cdtrAgtGiveNCC_cdtrIntrmyAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_127_pn_sn_sn_pn_dbtrAgtGiveIBAN_cdtrGiveIBAN_cdtrIntrmyAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_128_pn_sn_sn_pn_dbtrAgtGiveIBAN_cdtrAgtGiveBIC_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_129_pn_sn_sn_pn_dbtrAgtGiveIBAN_cdtrAgtGiveNCC_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_130_pn_sn_sn_pn_dbtrAgtGiveIBAN_cdtrAgtGiveIBAN_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_131_pn_sn_sn_pn_dbtrAgtGivePNRoxeId_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_132_pn_sn_sn_pn_dbtrAgtGivePNRoxeId_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGivePNRoxeId_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_133_pn_sn_sn_pn_dbtrAgtGivePNRoxeId_dbtrIntrmyAgtGiveSNRoxeId_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_134_pn_sn_sn_pn_dbtrAgtGivePNRoxeId_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveBIC_cdtrIntrmyAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_135_pn_sn_sn_pn_dbtrAgtGivePNRoxeId_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveNCC_cdtrIntrmyAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_136_pn_sn_sn_pn_dbtrAgtGivePNRoxeId_dbtrIntrmyAgtGiveSNRoxeId_cdtrGiveIBAN_cdtrIntrmyAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_137_pn_sn_sn_pn_dbtrAgtGivePNRoxeId_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveBIC_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_138_pn_sn_sn_pn_dbtrAgtGivePNRoxeId_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveNCC_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_139_pn_sn_sn_pn_dbtrAgtGivePNRoxeId_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveIBAN_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_140_pn_sn_sn_pn_dbtrAgtGiveBIC_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_141_pn_sn_sn_pn_dbtrAgtGiveBIC_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGivePNRoxeId_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_142_pn_sn_sn_pn_dbtrAgtGiveBIC_dbtrIntrmyAgtGiveSNRoxeId_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_143_pn_sn_sn_pn_dbtrAgtGiveBIC_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveBIC_cdtrIntrmyAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_144_pn_sn_sn_pn_dbtrAgtGiveBIC_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveNCC_cdtrIntrmyAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_145_pn_sn_sn_pn_dbtrAgtGiveBIC_dbtrIntrmyAgtGiveSNRoxeId_cdtrGiveIBAN_cdtrIntrmyAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_146_pn_sn_sn_pn_dbtrAgtGiveBIC_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveBIC_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_147_pn_sn_sn_pn_dbtrAgtGiveBIC_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveNCC_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_148_pn_sn_sn_pn_dbtrAgtGiveBIC_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveIBAN_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.bic_agents["USD"])
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_149_pn_sn_sn_pn_dbtrAgtGiveNCC_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_150_pn_sn_sn_pn_dbtrAgtGiveNCC_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGivePNRoxeId_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_151_pn_sn_sn_pn_dbtrAgtGiveNCC_dbtrIntrmyAgtGiveSNRoxeId_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_152_pn_sn_sn_pn_dbtrAgtGiveNCC_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveBIC_cdtrIntrmyAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(100, 2, 20)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt, "B2B")["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=self.client.make_roxe_agent(pn2, "PN"), amount=amt, cd="B2B")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.orgId, debtor_agent, RMNData.orgId_b, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["cdtrAgt"]["brnchId"] = {"nm": "test 1", "id": "a123d", "lei": "lei1234"}
        cdtTrfTxInf["dbtrAgt"]["brnchId"] = {"nm": "test debitor agent", "id": "debitor12341sa", "lei": "debitor lei12345"}
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_153_pn_sn_sn_pn_dbtrAgtGiveNCC_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveNCC_cdtrIntrmyAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_154_pn_sn_sn_pn_dbtrAgtGiveNCC_dbtrIntrmyAgtGiveSNRoxeId_cdtrGiveIBAN_cdtrIntrmyAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_155_pn_sn_sn_pn_dbtrAgtGiveNCC_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveBIC_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_156_pn_sn_sn_pn_dbtrAgtGiveNCC_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveNCC_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_157_pn_sn_sn_pn_dbtrAgtGiveNCC_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveIBAN_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        debtor_agent = ApiUtils.deepUpdateDict(debtor_agent, RMNData.ncc_agents["USD"])
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_158_pn_sn_sn_pn_dbtrAgtGiveIBAN_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_159_pn_sn_sn_pn_dbtrAgtGiveIBAN_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGivePNRoxeId_cdtrIntrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_160_pn_sn_sn_pn_dbtrAgtGiveIBAN_dbtrIntrmyAgtGiveSNRoxeId_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_161_pn_sn_sn_pn_dbtrAgtGiveIBAN_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveBIC_cdtrIntrmyAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_162_pn_sn_sn_pn_dbtrAgtGiveIBAN_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveNCC_cdtrIntrmyAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_163_pn_sn_sn_pn_dbtrAgtGiveIBAN_dbtrIntrmyAgtGiveSNRoxeId_cdtrGiveIBAN_cdtrIntrmyAgtGivePNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_164_pn_sn_sn_pn_dbtrAgtGiveIBAN_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveBIC_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_165_pn_sn_sn_pn_dbtrAgtGiveIBAN_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveNCC_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_166_pn_sn_sn_pn_dbtrAgtGiveIBAN_dbtrIntrmyAgtGiveSNRoxeId_cdtrAgtGiveIBAN_cdtrIntrmyAgtGivePNRoxeId_intrmyAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = RMNData.pn_gbp_us
        sn1 = RMNData.sn_gbp_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_gbp_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.iban_agent
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "GBP", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(pn1, "GBP", "GBP", cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)
        cdtTrfTxInf["dbtrIntrmyAgt"] = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(pn2, "PN")
        cdtTrfTxInf["intrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf["dbtrAcct"]["iban"] = RMNData.iban["GBP"]
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_167_getRouterList_senderIsPN_sameCurrency_qryTpIsAll(self):
        sender = RMNData.pn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAgt=RMNData.ncc_agents["GBP"], qryTp="ALL")
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "pn-sn-sn")

    @unittest.skip("暂未实现此路由策略")
    def test_168_getRouterList_senderIsPN_sameCurrency_qryTpIsTIME(self):
        sender = RMNData.pn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAgt=RMNData.bic_agents["GBP"], qryTp="TIME")
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "pn-sn-sn")

    def test_169_getRouterList_senderIsPN_sameCurrency_qryTpIsCOST(self):
        sender = RMNData.pn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAgt=RMNData.bic_agents["GBP"], qryTp="COST")
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "pn-sn-sn")

    def test_170_getRouterList_senderIsPN_sameCurrency_outAmount(self):
        sender = RMNData.pn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("USD", "USD", None, "100", cdtrAgt=RMNData.bic_agents["GBP"])
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "pn-sn-sn")

    def test_171_getTransactionStatus(self):
        self.getAndcheckTransactionStatus(RMNData.sn_usd_us, RMNData.api_key, RMNData.sec_key, RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"], "CMPT")

    def test_172_getTransactionStatus_givePmtId(self):
        sn1 = RMNData.sn_usd_us
        api_key = RMNData.api_key
        sec_key = RMNData.sec_key

        self.getAndcheckTransactionStatus(
            sn1, api_key, sec_key, RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"], "CMPT",
            txId=RMNData.query_tx_info["endToEndId"], endToEndId=RMNData.query_tx_info["endToEndId"]
        )

    def test_173_getTransactionStatus_giveMsgTp(self):
        sn1 = RMNData.sn_usd_us
        api_key = RMNData.api_key
        sec_key = RMNData.sec_key

        self.getAndcheckTransactionStatus(
            sn1, api_key, sec_key, RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"], "CMPT",
            msgTp=RMNData.query_tx_info["msgTp"]
        )

    def test_174_getTransactionStatus_giveInstdPty(self):
        sn1 = RMNData.sn_usd_us
        api_key = RMNData.api_key
        sec_key = RMNData.sec_key

        self.getAndcheckTransactionStatus(
            sn1, api_key, sec_key, RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"], "CMPT",
            instdPty=RMNData.rmn_id
        )

    def test_175_getTransactionFlow(self):
        sn1 = RMNData.sn_usd_us
        api_key = RMNData.api_key
        sec_key = RMNData.sec_key

        ts_headers = self.client.make_header(sn1, api_key, "RATQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(
            RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"], ntryTp="ADT"
        )
        q_info, q_msg = self.client.get_transaction_flow(sec_key, ts_headers, msg_header, txQryDef)

        self.checkCodeAndMessage(q_info)
        self.checkTransactionFlowInDB(q_info["data"], q_msg)

    def test_176_getTransactionFlow_givePmtId(self):
        sn1 = RMNData.sn_usd_us
        api_key = RMNData.api_key
        sec_key = RMNData.sec_key

        ts_headers = self.client.make_header(sn1, api_key, "RATQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(
            RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"],
            txId=RMNData.query_tx_info["endToEndId"], endToEndId=RMNData.query_tx_info["endToEndId"], ntryTp="ADT"
        )
        q_info, q_msg = self.client.get_transaction_flow(sec_key, ts_headers, msg_header, txQryDef)

        self.checkCodeAndMessage(q_info)
        self.checkTransactionFlowInDB(q_info["data"], q_msg)

    def test_177_getTransactionFlow_giveMsgTp(self):
        sn1 = RMNData.sn_usd_us
        api_key = RMNData.api_key
        sec_key = RMNData.sec_key

        ts_headers = self.client.make_header(sn1, api_key, "RATQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(
            RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"],
            msgTp=RMNData.query_tx_info["msgTp"], ntryTp="ADT"
        )
        q_info, q_msg = self.client.get_transaction_flow(sec_key, ts_headers, msg_header, txQryDef)

        self.checkCodeAndMessage(q_info)
        self.checkTransactionFlowInDB(q_info["data"], q_msg)

    def test_178_getTransactionFlow_giveInstdPty(self):
        sn1 = RMNData.sn_usd_us
        api_key = RMNData.api_key
        sec_key = RMNData.sec_key

        ts_headers = self.client.make_header(sn1, api_key, "RATQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(
            RMNData.query_tx_info["msgId"], RMNData.query_tx_info["nodeCode"],
            instdPty=RMNData.rmn_id, ntryTp="ADT"
        )
        q_info, q_msg = self.client.get_transaction_flow(sec_key, ts_headers, msg_header, txQryDef)

        self.checkCodeAndMessage(q_info)
        self.checkTransactionFlowInDB(q_info["data"], q_msg)

    def test_179_getTransactionStatus(self):
        sn1 = RMNData.sn_usd_us
        api_key = RMNData.api_key
        sec_key = RMNData.sec_key

        ts_headers = self.client.make_header(sn1, api_key, "RTSQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        txQryDef = self.client.make_RTSQ_information(
            RMNData.query_tx_info["msgId"],
            RMNData.query_tx_info["nodeCode"],
            RMNData.query_tx_info["endToEndId"],
            RMNData.query_tx_info["endToEndId"],
            # ntryTp="ADT", msgTp="RCCT"
        )
        q_info, q_msg = self.client.get_transaction_status(sec_key, ts_headers, msg_header, txQryDef)
        # q_info, q_msg = self.client.get_transaction_flow(sec_key, ts_headers, msg_header, txQryDef)
        self.client.checkCodeAndMessage(q_info)

    def test_180_sn_sn_rightNodeUsePayChannel_mock(self):
        """
        右侧节点选择支付通道
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.mock_node

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1)
        cdtTrfTxInf["cdtrAgt"]["finInstnId"]["clrSysMmbId"] = RMNData.ncc_agents["USD"]["finInstnId"]["clrSysMmbId"]
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=True)

    def test_181_getExchangeRate_rpp(self):
        """
        查询汇率，不同币种
        """
        sender = RMNData.sn_usd_us
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        ts_headers = self.client.make_header(sender, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        amt_list = ["0.01", "0.1", "1.34"]
        for i in range(10):
            amt_list.append(str(ApiUtils.parseNumberDecimal(ApiUtils.randAmount(10 ** (i + 2), 2, 10 ** (i + 1)))))

        for amt in amt_list:
            self.client.logger.info(f"准备换汇的金额: {amt} USD")
            rate_res, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, "USD", amt, "PHP")
            self.checkExchangeRate(rate_res, req_msg)
            self.client.logger.info(f"准备换汇的金额: {amt} PHP")
            ts_headers2 = self.client.make_header(sender, apiKey, "RERQ")
            msg_header2 = self.client.make_msg_header(sender, ts_headers2["msgId"])
            rate_res, req_msg = self.client.get_exchange_rate(secKey, ts_headers2, msg_header2, "USD", None, "PHP", amt)
            self.checkExchangeRate(rate_res, req_msg)

    def test_182_getRouterList_rpp_baseCurrency(self):
        """
        查询路由，不同币种
        """
        sender = RMNData.sn_usd_us
        api_key = RMNData.api_key
        sec_key = RMNData.sec_key
        ts_headers = self.client.make_header(sender, api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(RMNData.sn_usd_us, "SN")

        amt_list = ["0.3", "1.34"]
        # amt_list = ["0.03", "101.34"]  # A测试环境调试数据
        for i in range(10):
            amt_list.append(str(ApiUtils.parseNumberDecimal(ApiUtils.randAmount(10 ** (i + 2), 2, 10 ** (i + 1)))))
        # print(amt_list)
        for amt in amt_list:
            self.client.logger.info(f"in amount: {amt}")
            msg = self.client.make_RRLQ_information("USD", "PHP", amt, cdtrAgt=agent_info)
            router_list, req_msg = self.client.get_router_list(sec_key, ts_headers, msg_header, msg)
            if float(amt) < 1:
                self.client.checkCodeAndMessage(router_list, "00500003", "No correct routing information was found")
            else:
                self.checkRouterList(router_list, req_msg, sender, "sn-sn")

    def test_183_getRouterList_rpp_quoteCurrency(self):
        """
        查询路由，不同币种
        """
        sender = RMNData.sn_usd_us
        api_key = RMNData.api_key
        sec_key = RMNData.sec_key
        ts_headers = self.client.make_header(sender, api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(sender, "SN")

        amt_list = ["0.38", "1.34"]
        # amt_list = ["1.08", "100.34"]  # A测试环境调试数据
        for i in range(10):
            amt_list.append(str(ApiUtils.parseNumberDecimal(ApiUtils.randAmount(10 ** (i + 2), 2, 10 ** (i + 1)))))
        for amt in amt_list:
            self.client.logger.info(f"in amount: {amt}")
            msg = self.client.make_RRLQ_information("PHP", "USD", amt, cdtrAgt=agent_info)
            self.client.logger.info(f"msg: {msg}")
            router_list, req_msg = self.client.get_router_list(sec_key, ts_headers, msg_header, msg)
            if float(amt) < 500:
                self.client.checkCodeAndMessage(router_list, "00500003", "No correct routing information was found")
            else:
                self.checkRouterList(router_list, req_msg, sender, "sn-sn")

    def test_184_sn_sn_cdtrAgtGiveSNRoxeId_rpp_inAmount_baseCurrency(self):
        """
        主流程: sn_sn, cdtrAgt有roxeId, 且为SN, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.rpp_node_usd2php   # "f3viuzqrqq4d"
        sn2 = RMNData.sn_php_ph   # "rss_roxe_ph"

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "PHP", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "PHP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1, inAmount=amt)
        cdtTrfTxInf["cdtr"]["pstlAdr"]["ctry"] = "PH"
        cdtTrfTxInf["cdtr"]["frstNm"] = "Jethro"
        cdtTrfTxInf["cdtr"]["mdlNm"] = "Test"
        cdtTrfTxInf["cdtr"]["lstNm"] = "Gss"
        cdtTrfTxInf["cdtr"].pop("nm")

        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", cdtTrfTxInf["intrBkSttlmAmt"]["amt"], "PHP")
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(
            sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=in_node,
            isRPP=True, rateInfo=rate_info, chg_fees=["USD"]
        )

    def test_185_sn_sn_pn_cdtrAgtGiveSNRoxeId_rpp_inAmount_baseCurrency(self):
        """
        主流程: sn_sn, cdtrAgt有roxeId, 且为SN, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.rpp_node_usd2php   # "f3viuzqrqq4d"
        sn2 = RMNData.sn_php_ph   # "rss_roxe_ph"
        pn2 = RMNData.pn_php_ph

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "PHP", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "PHP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1, inAmount=amt)
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, "USD", cdtTrfTxInf["intrBkSttlmAmt"]["amt"], "PHP")
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_pn(
            sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=in_node,
            isRPP=True, rateInfo=rate_info, chg_fees=["USD", "PHP"])

    def test_186_pn_sn_sn_cdtrAgtGiveSNRoxeId_rpp_inAmount_baseCurrency(self):
        """
        主流程: sn_sn, cdtrAgt有roxeId, 且为SN, cdtrIntrmyAgt及intrmyAgt为空
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.rpp_node_usd2php
        sn2 = RMNData.sn_php_ph

        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "PHP", creditor_agent=creditor_agent, amount=amt)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "PHP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amt)

        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        sn_amt = ApiUtils.parseNumberDecimal(float(cdtTrfTxInf["intrBkSttlmAmt"]["amt"]) - sn1_fee, 2, True)
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, "USD", sn_amt, "PHP")
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(
            pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=in_node,
            isRPP=True, rateInfo=rate_info, chg_fees=["USD", "PHP"])

    def test_187_pn_sn_sn_pn_cdtrAgtGiveSNRoxeId_rpp_inAmount_baseCurrency(self):
        """
        主流程: sn_sn, cdtrAgt有roxeId, 且为SN, cdtrIntrmyAgt及intrmyAgt为空
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.rpp_node_usd2php
        sn2 = RMNData.sn_php_ph
        pn2 = RMNData.pn_php_ph

        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(15, 2, 10)
        pn1_fee = self.client.getNodeFeeInDB(pn1, "USD", amt)["in"]
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "PHP", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "PHP", RMNData.prvtId, debtor_agent, RMNData.prvtId_b, creditor_agent, pn1_fee, pn1, inAmount=amt)

        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        sn_amt = ApiUtils.parseNumberDecimal(float(cdtTrfTxInf["intrBkSttlmAmt"]["amt"]) - sn1_fee, 2, True)
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, "USD", sn_amt, "PHP")
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(
            pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=in_node,
            isRPP=True, rateInfo=rate_info, chg_fees=["USD", "PHP"]
        )

    def test_188_sn_sn_cdtrAgtGiveSNRoxeId_rpp_inAmount_quoteCurrency(self):
        """
        主流程: sn_sn, cdtrAgt有roxeId, 且为SN, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.rpp_node_usd2php
        # sn1 = RMNData.sn_usd_gb
        sn2 = RMNData.sn_usd_us

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        php_amount = ApiUtils.randAmount(1000, 2, 300)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "PHP", "USD", creditor_agent=creditor_agent, amount=php_amount)
        cdtTrfTxInf = self.client.make_RCCT_information("PHP", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1, inAmount=php_amount)

        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, "PHP", float(cdtTrfTxInf["intrBkSttlmAmt"]["amt"]), "USD")
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(
            sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=in_node,
            isRPP=True, rateInfo=rate_info, chg_fees=["PHP", "USD"]
        )

    def test_189_sn_sn_pn_cdtrAgtGiveSNRoxeId_rpp_inAmount_quoteCurrency(self):
        """
        主流程: sn_sn, cdtrAgt有roxeId, 且为SN, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.rpp_node_usd2php
        sn2 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_us

        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "PHP", "USD", creditor_agent=creditor_agent, amount=5000)
        cdtTrfTxInf = self.client.make_RCCT_information("PHP", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1, inAmount=5000)

        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, "PHP", cdtTrfTxInf["intrBkSttlmAmt"]["amt"], "USD")
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_pn(
            sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=in_node,
            isRPP=True, rateInfo=rate_info, chg_fees=["PHP", "USD"]
        )

    def test_190_pn_sn_sn_cdtrAgtGiveSNRoxeId_rpp_inAmount_quoteCurrency(self):
        """
        主流程: sn_sn, cdtrAgt有roxeId, 且为SN, cdtrIntrmyAgt及intrmyAgt为空
        """
        pn1 = RMNData.pn_php_ph
        sn1 = RMNData.rpp_node_usd2php
        sn2 = RMNData.sn_usd_us

        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "PHP", "USD", creditor_agent=creditor_agent, amount=50000)
        cdtTrfTxInf = self.client.make_RCCT_information("PHP", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, 1, pn1, inAmount=50000)

        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        sn_amt = ApiUtils.parseNumberDecimal(float(cdtTrfTxInf["intrBkSttlmAmt"]["amt"]) - sn1_fee, 2, True)
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, "PHP", sn_amt, "USD")
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(
            pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=in_node,
            isRPP=True, rateInfo=rate_info, chg_fees=["PHP", "USD"]
        )

    # todo
    def test_191_pn_sn_sn_pn_cdtrAgtGiveSNRoxeId_rpp_inAmount_quoteCurrency(self):
        """
        主流程: sn_sn, cdtrAgt有roxeId, 且为SN, cdtrIntrmyAgt及intrmyAgt为空
        """
        pn1 = RMNData.pn_php_ph
        sn1 = RMNData.rpp_node_usd2php
        sn2 = RMNData.sn_usd_us
        pn2 = RMNData.pn_usd_us

        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(5000, 2, 100)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "PHP", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("PHP", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, 1, pn1, inAmount=amt)

        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        sn_amt = ApiUtils.parseNumberDecimal(float(cdtTrfTxInf["intrBkSttlmAmt"]["amt"]) - sn1_fee, 2, True)
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, "PHP", sn_amt, "USD")
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(
            pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=in_node,
            isRPP=True, rateInfo=rate_info, chg_fees=["PHP", "USD"]
        )

    # 路由增加费用最低策略后
    def test_192_getRouterList_senderIsSN_sameCurrency_iban(self):
        """
        查询路由, 消息发送方为SN节点, 指定creditorAccount
        """
        sender = RMNData.sn_gbp_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAcct={"iban": RMNData.iban["GBP"]}, qryTp="COST")
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "sn-sn")

    def test_193_getRouterList_senderIsSN_sameCurrency_bicCode(self):
        """
        查询路由, 消息发送方为SN节点, 指定Swift/bic code
        """
        sender = RMNData.sn_gbp_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAgt=RMNData.bic_agents["GBP"], qryTp="COST")
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "sn-sn")

    def test_194_getRouterList_senderIsSN_sameCurrency_nccCode(self):
        """
        查询路由, 消息发送方为SN节点, 指定NCC code
        """
        sender = RMNData.sn_gbp_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAgt=RMNData.ncc_agents["USD"], qryTp="COST")
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "sn-sn")

    def test_195_getRouterList_senderIsSN_sameCurrency_node(self):
        """
        查询路由, 消息发送方为SN节点, 指定Swift/bic code
        """
        sender = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agt = self.client.make_roxe_agent(RMNData.sn_usd_us, "SN")
        msg = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAgt=agt, qryTp="COST")
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "sn-sn")

    def test_196_getRouterList_senderIsSN_differentCurrency_ncc(self):
        """
        查询路由, 消息发送方为SN节点, 指定Swift/bic code
        """
        sender = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agt = RMNData.ncc_agents["GBP"]
        msg = self.client.make_RRLQ_information("USD", "GBP", "100", cdtrAgt=agt, qryTp="COST")
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "sn-sn")

    def test_197_getRouterList_senderIsSN_differentCurrency_bic(self):
        """
        查询路由, 消息发送方为SN节点, 指定Swift/bic code
        """
        sender = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agt = RMNData.bic_agents["USD"]
        msg = self.client.make_RRLQ_information("USD", "PHP", "100", cdtrAgt=agt, qryTp="COST")
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "sn-sn")

    def test_198_getRouterList_senderIsSN_differentCurrency_node(self):
        """
        查询路由, 消息发送方为SN节点, 指定Swift/bic code
        """
        sender = RMNData.sn_usd_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agt = self.client.make_roxe_agent(RMNData.sn_usd_us, "SN")
        msg = self.client.make_RRLQ_information("USD", "PHP", "100", cdtrAgt=agt, qryTp="COST")
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "sn-sn")

    def test_199_getRouterList_senderIsSN_changeAmount_nccCode(self):
        """
        查询路由, 消息发送方为SN节点, 指定NCC code
        """
        sender = RMNData.sn_gbp_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("USD", "USD", "100", cdtrAgt=RMNData.ncc_agents["GBP"])
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "sn-sn")

        # 计算一条路由的费用总和
        router_fees = [ApiUtils.parseNumberDecimal(float(i["rmtInf"]["sndrAmt"]) - float(i["rmtInf"]["rcvrAmt"]), 2, True) for i in router_list["data"]["rptOrErr"]]
        self.client.logger.warning(f"全部路由的费用: {router_fees}")
        new_amounts = [max(router_fees) + 0.01, max(router_fees), min(router_fees) + 0.01, min(router_fees),
                       min(router_fees) - 0.01]
        new_amounts = [ApiUtils.parseNumberDecimal(i, 2, True) for i in new_amounts]
        ex_router_lengths = [len(router_fees), len(router_fees) - 1, 1, 0, 0]
        for new_amount, ex_length in zip(new_amounts, ex_router_lengths):
            self.client.logger.warning(f"查询路由金额: {new_amount}")
            msg = self.client.make_RRLQ_information("USD", "USD", str(new_amount), cdtrAgt=RMNData.ncc_agents["GBP"])
            router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
            if ex_length > 0:
                self.checkRouterList(router_list, req_msg, sender, "sn-sn")
                self.assertEqual(len(router_list["data"]["rptOrErr"]), ex_length)
            else:
                self.client.checkCodeAndMessage(router_list, "00500003", "No correct routing information was found")

    @unittest.skip("涉及换汇费用校验，可能出现不准确情况")
    def test_200_getRouterList_senderIsSN_changeAmount_bicCode(self):
        """
        查询路由, 消息发送方为SN节点, 指定NCC code
        """
        sender = RMNData.sn_gbp_us
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("USD", "PHP", "100", cdtrAgt=RMNData.bic_agents["PHP"])
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "sn-sn")

        # 计算一条路由的费用总和
        router_fees = []
        for i in router_list["data"]["rptOrErr"]:
            in_fee_info = [j["sndFeeAmt"] for j in i["chrgsInf"] if "sndFeeAmt" in j.keys()]
            out_fee_info = [j["dlvFeeAmt"] for j in i["chrgsInf"] if "dlvFeeAmt" in j.keys()]
            r_fee = 0
            if in_fee_info and out_fee_info:
                if in_fee_info[0]["ccy"] == out_fee_info[0]["ccy"]:
                    r_fee = ApiUtils.parseNumberDecimal(float(in_fee_info[0]["amt"]) + float(out_fee_info[0]["amt"]), 2, True)
                else:
                    rate = (float(i["rmtInf"]["sndrAmt"]) - float(in_fee_info[0]["amt"])) / (float(i["rmtInf"]["rcvrAmt"]) + float(out_fee_info[0]["amt"]))
                    r_fee = float(in_fee_info[0]["amt"]) + rate * float(out_fee_info[0]["amt"])
                    r_fee = ApiUtils.parseNumberDecimal(r_fee, 2, True)
            router_fees.append(r_fee)
        # router_fees = [ApiUtils.parseNumberDecimal(float(i["chrgsInf"]["sndrAmt"]) - float(i["rmtInf"]["rcvrAmt"]), 2, True) for i in router_list["data"]["rptOrErr"]]
        self.client.logger.warning(f"全部路由的费用: {router_fees}")
        new_amounts = [max(router_fees) + 0.01, max(router_fees), min(router_fees) + 0.01, min(router_fees),
                       min(router_fees) - 0.01]
        new_amounts = [ApiUtils.parseNumberDecimal(i, 2, True) for i in new_amounts]
        ex_router_lengths = [len(router_fees), len(router_fees) - 1, 1, 0, 0]
        for new_amount, ex_length in zip(new_amounts, ex_router_lengths):
            self.client.logger.warning(f"查询路由金额: {new_amount}")
            msg = self.client.make_RRLQ_information("USD", "PHP", str(new_amount), cdtrAgt=RMNData.bic_agents["PHP"])
            router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
            try:
                self.checkRouterList(router_list, req_msg, sender, "sn-sn")
                self.assertEqual(len(router_list["data"]["rptOrErr"]), ex_length)
            except AssertionError:
                self.client.checkCodeAndMessage(router_list, "00500003", "No correct routing information was found")

    def test_201_sn_sn_cdtrAgtGiveNCC_sameCurrency(self):
        """
        指定ncc，自动查找费用最低的路由节点
        """
        sn1 = RMNData.sn_usd_us
        creditor_agent = RMNData.ncc_agents["USD"]
        # 查询费用最低路由
        amount = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(
            sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amount, qryTp="COST"
        )
        inner_node = True if sn2 in RMNData.channel_nodes else False
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1, inAmount=amount)
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, inner_node)

    def test_202_sn_sn_cdtrAgtGiveBIC_differentCurrency(self):
        """
        指定ncc，自动查找费用最低的路由节点
        """
        sn1 = RMNData.sn_usd_us
        # 查询费用最低路由
        creditor_agent = RMNData.bic_agents["USD"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(
            sn1, "USD", "PHP", creditor_agent=creditor_agent, amount=amount, qryTp="COST"
        )
        channel_nodes = [RMNData.mock_node, RMNData.sn_roxe_terrapay, RMNData.sn_roxe_nium]
        inner_node = True if sn2 in channel_nodes else False
        is_rpp = True if sn2 in [RMNData.sn_usd_us, RMNData.mock_node] else False
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "PHP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1, inAmount=amount)

        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", cdtTrfTxInf["intrBkSttlmAmt"]["amt"], "PHP")
        self.client.checkCodeAndMessage(rate_info)
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, inner_node, isRPP=is_rpp, rateInfo=rate_info, chg_fees=["USD"])

    def test_203_sn_sn_cdtrAgtGiveSNRoxeId_sameCurrency(self):
        """
        主流程: sn_sn, cdtrAgt有roxeId, 且为SN, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "GBP", "GBP", creditor_agent=creditor_agent, amount=amount)
        cdtTrfTxInf = self.client.make_RCCT_information("GBP", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)

    def test_204_sn_sn_cdtrAgtGiveSNRoxeId_rpp_inAmount_diCurrency(self):
        """
        主流程: sn_sn, cdtrAgt有roxeId, 且为SN, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "GBP", creditor_agent=creditor_agent, amount=amount)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "GBP", RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sn1_fee, sn1, inAmount=amount)

        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", cdtTrfTxInf["intrBkSttlmAmt"]["amt"], "GBP")
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(
            sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=in_node,
            isRPP=True, rateInfo=rate_info, chg_fees=["USD"]
        )

    def submitOrderAndCheckToRmnChannelAmount(self, sn1, sn2, cdtTrfTxInf, api_key, sec_key, to_amount, deliverFee):
        sendCurrency = cdtTrfTxInf["instdAmt"]["ccy"]
        recCurrency = cdtTrfTxInf["cdtrAcct"]["ccy"]
        e2e_id = cdtTrfTxInf["pmtId"]["endToEndId"]
        # 向右侧节点提交订单的实际金额
        # to_right_node_amount = ApiUtils.parseNumberDecimal(float(to_amount) - float(deliverFee), 2, True)
        # rmn下单 (to_right_node_amount:向右侧节点提交订单的实际金额)
        if sendCurrency == recCurrency:
            to_right_node_amount = ApiUtils.parseNumberDecimal(float(to_amount) - float(deliverFee), 2, True)
            self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [], self)
        else:
            ts_headers = self.client.make_header(sn1, api_key, "RERQ")
            msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
            rate_info, req_msg = self.client.get_exchange_rate(sec_key, ts_headers, msg_header, "USD", cdtTrfTxInf["intrBkSttlmAmt"]["amt"], recCurrency)
            print(rate_info)
            exchange_rate_after = rate_info["data"]["rptOrErr"]["ccyXchg"]["rcvrAmt"]
            to_right_node_amount = ApiUtils.parseNumberDecimal(float(exchange_rate_after) - float(deliverFee), 2, True)
            self.client.checkCodeAndMessage(rate_info)
            self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [], self, isRPP=True, rateInfo=rate_info, chg_fees=["USD"])
        # 查询订单赎回完成后实际提交至通道的金额
        sql_rmn = "select rts_txn_id from roxe_rmn.rmn_transaction where e2e_id like '%{}%' and txn_state='TRANSACTION_FINISH'".format(e2e_id)
        rts_txn_id = self.client.mysql.exec_sql_query(sql_rmn)[0]["rtsTxnId"]
        sql_rts = "select log_info from `{}`.rts_order_log where order_id like '%{}%' and order_state='REDEEM_FINISH'".format(self.client.rts_db_name, rts_txn_id)
        to_channel_amount = json.loads(self.client.mysql.exec_sql_query(sql_rts)[0]["logInfo"])["outAmount"]
        self.client.logger.info("向右侧节点提交订单的实际金额：{}".format(to_right_node_amount))
        self.client.logger.info("订单赎回完成后实际提交至通道的金额：{}".format(to_channel_amount))
        self.assertAlmostEqual(to_channel_amount, to_right_node_amount, places=2, msg="订单赎回完成后实际提交至通道的金额与提交金额不符")

    # @unittest.skip("偶发报错")
    def test_220_getRouterList_senderIsSN_sameCurrency_snRoxeId(self):
        """
        查询路由, 消息发送方为SN节点, 指定sn2 roxe id,两个SN均为RMN节点
        """
        sender = RMNData.sn_usd_us
        recCurrency = "USD"
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(RMNData.sn_gbp_gb, "SN")
        # agent_info = self.client.make_roxe_agent(sender, "SN")  # sandbox环境
        cd_list = ["B2B", "C2C", "B2C", "C2B"]
        for cd in cd_list:
            msg = self.client.make_RRLQ_information("USD", recCurrency, "100", cdtrAgt=agent_info, cd=cd)
            router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
            self.checkRouterList(router_list, req_msg, sender, "sn-sn")
            if cd == "B2B":
                assert ("prvtId" not in str(router_list)) and ("dbtr.orgId", "cdtr.orgId" in str(router_list))
            elif cd == "C2C":
                assert ("orgId" not in str(router_list)) and ("dbtr.prvtId", "cdtr.prvtId" in str(router_list))
            elif cd == "B2C":
                assert ("dbtr.prvtId", "cdtr.orgId" not in str(router_list)) and ("dbtr.orgId", "cdtr.prvtId" in str(router_list))
            elif cd == "C2B":
                assert ("dbtr.orgId", "cdtr.prvtId" not in str(router_list)) and ("dbtr.prvtId", "cdtr.orgId" in str(router_list))

    def test_221_getRouterList_senderIsSN_sameCurrency_snRoxeId(self):
        """
        查询路由, 消息发送方为SN节点, 指定sn2 roxe id,左侧SN为RMN节点，右侧SN为MOCK节点,目前仅支持C2C
        """
        sender = RMNData.sn_usd_us
        recCurrency = "USD"
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(RMNData.mock_node, "SN")
        msg = self.client.make_RRLQ_information("USD", recCurrency, "100", cdtrAgt=agent_info, cd="C2C")
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "sn-sn")

    def test_222_getRouterList_senderIsSN_differentCurrency_snRoxeId(self):
        """
        查询路由, 消息发送方为SN节点, 指定sn2 roxe id，左侧SN为RMN节点，右侧SN为TerraPay节点,目前仅支持C2C
        """
        sender = RMNData.sn_usd_us
        recCurrency = "PHP"
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(RMNData.sn_php_ph, "SN")
        msg = self.client.make_RRLQ_information("USD", recCurrency, "100", cdtrAgt=agent_info, cd="C2C")
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "sn-sn")
        assert ("orgId" not in str(router_list)) and ("prvtId" in str(router_list))

    def test_223_getRouterList_senderIsPN_differentCurrency_snRoxeId(self):
        """
        查询路由, 消息发送方为PN节点, 指定sn2 roxe id,两个SN均为RMN节点
        """
        sender = RMNData.pn_usd_us  # PN1 节点
        recCurrency = "PHP"
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(RMNData.sn_php_ph, "SN")
        cd_list = ["B2B", "C2C", "B2C", "C2B"]
        for cd in cd_list:
            msg = self.client.make_RRLQ_information("USD", recCurrency, "100", cdtrAgt=agent_info, cd=cd)
            router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
            self.checkRouterList(router_list, req_msg, sender, "pn-sn-sn")

    def test_224_getRouterList_senderIsSN_differentCurrency_pnRoxeId(self):
        """
        查询路由, 消息发送方为SN节点, 指定pn2 roxe id，两个SN均为RMN节点
        """
        sender = RMNData.sn_usd_us
        recCurrency = "PHP"
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(RMNData.pn_php_ph, "PN")
        cd_list = ["B2B", "C2C", "B2C", "C2B"]
        for cd in cd_list:
            msg = self.client.make_RRLQ_information("USD", recCurrency, "100", cdtrAgt=agent_info, cd=cd)
            router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
            self.checkRouterList(router_list, req_msg, sender, "sn-sn-pn")

    def test_225_getRouterList_senderIsPN_differentCurrency_pnRoxeId(self):
        """
        USD-EUR，查询路由, 消息发送方为PN节点, 指定pn2 roxe id，两个SN均为RMN节点
        """
        sender = RMNData.pn_usd_us  # PN1 节点
        recCurrency = "PHP"
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(RMNData.pn_php_ph, "PN")
        cd_list = ["B2B", "C2C", "B2C", "C2B"]
        for cd in cd_list:
            msg = self.client.make_RRLQ_information("USD", recCurrency, "100", cdtrAgt=agent_info, cd=cd)
            router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
            self.checkRouterList(router_list, req_msg, sender, "pn-sn-sn-pn")
            if cd == "B2B":
                assert ("prvtId" not in str(router_list)) and ("dbtr.orgId", "cdtr.orgId" in str(router_list))
            elif cd == "C2C":
                assert ("orgId" not in str(router_list)) and ("dbtr.prvtId", "cdtr.prvtId" in str(router_list))
            elif cd == "B2C":
                assert ("dbtr.prvtId", "cdtr.orgId" not in str(router_list)) and ("dbtr.orgId", "cdtr.prvtId" in str(router_list))
            elif cd == "C2B":
                assert ("dbtr.orgId", "cdtr.prvtId" not in str(router_list)) and ("dbtr.prvtId", "cdtr.orgId" in str(router_list))

    def test_226_getRouterList_senderIsPN_differentCurrency_pnRoxeId(self):
        """PHP-USD,查询路由, 消息发送方为PN节点, 指定pn2 roxe id，两个SN均为RMN节点"""
        sender = RMNData.pn_php_ph                    # PN1 节点
        pn2 = RMNData.pn_usd_us
        sendCurrency = "PHP"
        recCurrency = "USD"
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(pn2, "PN")
        cd_list = ["B2B", "C2C", "B2C", "C2B"]
        for cd in cd_list:
            msg = self.client.make_RRLQ_information(sendCurrency, recCurrency, "10000", cdtrAgt=agent_info, cd=cd)
            router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
            self.checkRouterList(router_list, req_msg, sender, "pn-sn-sn-pn")

    def test_227_getRouterList_senderIsSN_differentCurrency_IBAN(self):
        """
        查询路由, 消息发送方为SN节点, 指定IBAN,两个SN均为RMN节点
        """
        sender = RMNData.sn_usd_us
        recCurrency = "GBP"
        cdtrAcct = {"iban": RMNData.iban[recCurrency]}
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        cd_list = ["B2B", "C2C", "B2C", "C2B"]
        for cd in cd_list:
            msg = self.client.make_RRLQ_information("USD", recCurrency, "100", cdtrAcct=cdtrAcct, cd=cd)
            router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
            self.checkRouterList(router_list, req_msg, sender, "sn-sn")

    def test_228_getRouterList_senderIsSN_differentCurrency_bicCode(self):
        """
        查询路由, 消息发送方为SN节点, 指定Swift/bic code（TerraPay提供的数据）,左侧为RMN节点，右侧为RMN/Terrapay节点(两条路由）
        当cd为C2C时返回两条路由RMN-RNM,RMN-TERRAPAY
        当cd为2B时返回一条路由RMN-RMN
        """
        sender = RMNData.sn_usd_us
        recCurrency = "GBP"
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        cd_list = ["B2B", "C2C", "B2C", "C2B"]
        for cd in cd_list:
            msg = self.client.make_RRLQ_information("USD", recCurrency, "100", cdtrAgt=RMNData.bic_agents[recCurrency], cd=cd)  # 目前terrapay通道暂不支持2B业务
            router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
            self.checkRouterList(router_list, req_msg, sender, "sn-sn")
            # if cd == "C2C":
            #     self.assertEqual(len(router_list["data"]["rptOrErr"]), 3, msg="返回的路由条数不正确")
            # else:
            self.assertEqual(len(router_list["data"]["rptOrErr"]), 1, msg="返回的路由条数不正确")

    def test_229_getRouterList_senderIsSN_sameCurrency_NCC(self):
        """
        查询路由, 消息发送方为SN节点, 指定NCC
        当cd为C2C时返回两条路由：1、RMN-MOCK,2、RMN-RMN
        当cd为2B时返回一条路由：RMN-RMN
        """
        sender = RMNData.sn_usd_us
        recCurrency = "USD"
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        cd_list = ["B2B", "C2C", "B2C", "C2B"]
        for cd in cd_list:
            msg = self.client.make_RRLQ_information(recCurrency, recCurrency, "100", cdtrAgt=RMNData.ncc_agents[recCurrency], cd=cd)
            router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
            self.checkRouterList(router_list, req_msg, sender, "sn-sn")
            if cd == "C2C":
                self.assertEqual(len(router_list["data"]["rptOrErr"]), 2, msg="返回的路由条数不正确")
            else:
                self.assertEqual(len(router_list["data"]["rptOrErr"]), 1, msg="返回的路由条数不正确")

    def test_230_getRouterList_senderIsPN_differentCurrency_IBAN(self):
        """
        查询路由, 发起方PN,右侧指定IBAN
        """
        sender = RMNData.pn_usd_us  # PN1 节点
        recCurrency = "GBP"
        cdtrAcct = {"iban": RMNData.iban[recCurrency]}
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        cd_list = ["B2B", "C2C", "B2C", "C2B"]
        for cd in cd_list:
            msg = self.client.make_RRLQ_information("USD", recCurrency, "100", cdtrAcct=cdtrAcct, cd=cd)
            router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
            self.checkRouterList(router_list, req_msg, sender, "pn-sn-sn")

    def test_231_getRouterList_senderIsPN_differentCurrency_bicCode(self):
        """
        查询路由,发起方PN,右侧指定Swift/bic code（TerraPay提供的数据）
        当cd为C2C时返回两条路由RMN-RNM,RMN-TERRAPAY
        当cd为2B时返回一条路由RMN-RMN
        """
        sender = RMNData.pn_usd_us  # PN1 节点
        recCurrency = "GBP"
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        cd_list = ["B2B", "C2C", "B2C", "C2B"]
        for cd in cd_list:
            msg = self.client.make_RRLQ_information("USD", recCurrency, "100", cdtrAgt=RMNData.bic_agents[recCurrency], cd=cd)
            router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
            self.checkRouterList(router_list, req_msg, sender, "pn-sn-sn")
            # if cd == "C2C":
            #     self.assertEqual(len(router_list["data"]["rptOrErr"]), 3, msg="返回的路由条数不正确")
            # else:
            self.assertEqual(len(router_list["data"]["rptOrErr"]), 1, msg="返回的路由条数不正确")

    def test_232_getRouterList_senderIsPN_sameCurrency_NCC(self):
        """
        查询路由, 发起方PN，右侧指定NCC, SN均为RMN节点
        """
        sender = RMNData.pn_usd_us  # PN1 节点
        recCurrency = "GBP"
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        cd_list = ["B2B", "C2C", "B2C", "C2B"]
        for cd in cd_list:
            msg = self.client.make_RRLQ_information("USD", recCurrency, "100", cdtrAgt=RMNData.ncc_agents[recCurrency], cd=cd)
            router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
            self.checkRouterList(router_list, req_msg, sender, "pn-sn-sn")

    def test_233_getRouterList_senderIsSN_sameCurrency_snRoxeId(self):
        """
        查询路由, 消息发送方为SN节点, 指定sn2 roxe id,两个SN均为RMN节点,cd字段缺省，默认为C2C
        """
        sender = RMNData.sn_usd_us
        recCurrency = "USD"
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(RMNData.sn_gbp_gb, "SN")
        msg = self.client.make_RRLQ_information("USD", recCurrency, "100", cdtrAgt=agent_info)
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "sn-sn")
        assert ("orgId" not in str(router_list)) and ("dbtr.prvtId", "cdtr.prvtId" in str(router_list))

    def test_234_getRouterList_senderIsPN_differentCurrency_pnRoxeId(self):
        """
        USD-EUR，查询路由, 消息发送方为PN节点, 指定sn2 roxe id，两个SN均为RMN节点，cd字段缺省，默认为C2C
        """
        sender = RMNData.pn_usd_us  # PN1 节点
        recCurrency = "PHP"
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(RMNData.pn_php_ph, "PN")
        msg = self.client.make_RRLQ_information("USD", recCurrency, "100", cdtrAgt=agent_info)
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "pn-sn-sn-pn")
        assert ("orgId" not in str(router_list)) and ("dbtr.prvtId", "cdtr.prvtId" in str(router_list))

    # SN-SN,同币种
    def test_235_sn_sn_cdtrAgtGiveSNRoxeId_sameCurrency_C2C(self):
        """
        USD-USD,C2C业务
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        sendCurrency = "USD"
        # sendCountry = "US"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, float(sendFee), sn1, inAmount=amount)
        cdtTrfTxInf["purp"] = {"cd": "001", "desc": "Family Maintenance"}
        cdtTrfTxInf["rltnShp"] = {"cd": "002", "desc": "Friend"}
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    def test_236_sn_sn_cdtrAgtGiveSNRoxeId_sameCurrency_B2B(self):
        """
        USD-USD,B2B业务
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        sendCurrency = "USD"
        # sendCountry = "US"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount, cd="B2B"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.orgId, debtor_agent, RMNData.orgId,
                                                        creditor_agent, float(sendFee), sn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    def test_237_sn_sn_cdtrAgtGiveSNRoxeId_sameCurrency_B2C(self):
        """
        USD-USD,B2C业务
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        sendCurrency = "USD"
        # sendCountry = "US"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount, cd="B2C"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.orgId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, float(sendFee), sn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    def test_238_sn_sn_cdtrAgtGiveSNRoxeId_sameCurrency_C2B(self):
        """
        USD-USD,C2B业务
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        sendCurrency = "USD"
        # sendCountry = "US"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount, cd="C2B"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.prvtId, debtor_agent, RMNData.orgId,
                                                        creditor_agent, sendFee, sn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sendFee, deliverFee], self, isInnerNode=inner_node)

    def test_239_sn_sn_cdtrGiveIBAN_sameCurrency_C2C(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId, BIC和NCC, cdtr给出IBAN账户
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        sendCurrency = "USD"
        # sendCountry = "US"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.iban_agent
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, sendCurrency, cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amount
        )
        print(sendFee, deliverFee)
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, sendFee, sn1, inAmount=amount)
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sendFee, deliverFee], self, isInnerNode=inner_node)

    def test_240_sn_sn_cdtrGiveIBAN_sameCurrency_B2B(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId, BIC和NCC, cdtr给出IBAN账户
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        sendCurrency = "USD"
        # sendCountry = "US"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.iban_agent
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, sendCurrency, cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amount, cd="B2B"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.orgId, debtor_agent, RMNData.orgId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    def test_241_sn_sn_cdtrGiveIBAN_sameCurrency_B2C(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId, BIC和NCC, cdtr给出IBAN账户
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        sendCurrency = "USD"
        # sendCountry = "US"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.iban_agent
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, sendCurrency, cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amount, cd="B2C"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.orgId, debtor_agent, RMNData.prvtId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    def test_242_sn_sn_cdtrGiveIBAN_sameCurrency_C2B(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId, BIC和NCC, cdtr给出IBAN账户
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        sendCurrency = "USD"
        # sendCountry = "US"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.iban_agent
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, sendCurrency, cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amount, cd="C2B"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.prvtId, debtor_agent, RMNData.orgId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    def test_243_sn_sn_cdtrAgtGiveBIC_sameCurrency_C2C(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId, 有BIC, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        sendCurrency = "USD"
        # sendCountry = "US"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        # cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    def test_244_sn_sn_cdtrAgtGiveBIC_sameCurrency_B2B(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId, 有BIC, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        sendCurrency = "USD"
        # sendCountry = "US"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount, cd="B2B"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.orgId, debtor_agent, RMNData.orgId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    def test_245_sn_sn_cdtrAgtGiveBIC_sameCurrency_B2C(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId, 有BIC, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_gbp_gb
        sendCurrency = "USD"
        # sendCountry = "US"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount, cd="B2C"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.orgId, debtor_agent, RMNData.prvtId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    def test_246_sn_sn_cdtrAgtGiveBIC_sameCurrency_C2B(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId, 有BIC, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_gbp_gb
        sendCurrency = "USD"
        # sendCountry = "US"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount, cd="C2B"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.prvtId, debtor_agent, RMNData.orgId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    def test_247_sn_sn_cdtrAgtGiveNCC_sameCurrency_C2C(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId, 有NCC, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_gbp_gb
        sendCurrency = "USD"
        # sendCountry = "US"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    def test_248_sn_sn_cdtrAgtGiveNCC_sameCurrency_B2B(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId, 有NCC, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_gbp_gb
        sendCurrency = "USD"
        # sendCountry = "US"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount, cd="B2B"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.orgId, debtor_agent, RMNData.orgId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    def test_249_sn_sn_cdtrAgtGiveNCC_sameCurrency_B2C(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId, 有NCC, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_gbp_gb
        sendCurrency = "USD"
        # sendCountry = "US"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount, cd="B2C"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.orgId, debtor_agent, RMNData.prvtId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    def test_250_sn_sn_cdtrAgtGiveNCC_sameCurrency_C2B(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId, 有NCC, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_gbp_gb
        sendCurrency = "USD"
        # sendCountry = "US"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount, cd="C2B"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.prvtId, debtor_agent, RMNData.orgId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    # SN-SN，不同币种
    def test_251_sn_sn_cdtrAgtGiveSNRoxeId_inAmount_differentCurrency_C2C(self):
        """
        主流程: sn_sn, cdtrAgt有roxeId, 且为SN, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_php_ph
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        # sendCountry = "US"
        rccCurrency = "PHP"
        # rccCountry = "US"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amount = ApiUtils.randAmount(10, 2, 5)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, rccCurrency, creditor_agent=creditor_agent, amount=amount
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, rccCurrency, RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        cdtTrfTxInf["purp"] = {"cd": "001", "desc": "Family Maintenance"}
        cdtTrfTxInf["rltnShp"] = {"cd": "002", "desc": "Friend"}
        self.client.logger.info(cdtTrfTxInf)

        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, cdtTrfTxInf["intrBkSttlmAmt"]["amt"], rccCurrency)
        self.client.checkCodeAndMessage(rate_info)
        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=in_node, isRPP=True, rateInfo=rate_info, chg_fees=["USD", "EUR"])

    def test_252_sn_sn_cdtrAgtGiveSNRoxeId_inAmount_differentCurrency_B2B(self):
        """
        主流程: sn_sn, cdtrAgt有roxeId, 且为SN, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_php_ph
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        # sendCountry = "US"
        rccCurrency = "PHP"
        # rccCountry = "US"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, rccCurrency, creditor_agent=creditor_agent, amount=amount, cd="B2B"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, rccCurrency, RMNData.orgId, debtor_agent, RMNData.orgId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        cdtTrfTxInf["cdtr"]["ctctDtls"] = {"emailAdr": "asd@test1.com", "phneNb": "1234123412"}
        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, cdtTrfTxInf["intrBkSttlmAmt"]["amt"], rccCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                          isInnerNode=in_node, isRPP=True, rateInfo=rate_info, chg_fees=["USD", "PHP"])

    def test_253_sn_sn_cdtrAgtGiveSNRoxeId_inAmount_differentCurrency_B2C(self):
        """
        主流程: sn_sn, cdtrAgt有roxeId, 且为SN, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_php_ph
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        # sendCountry = "US"
        rccCurrency = "PHP"
        # rccCountry = "US"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, rccCurrency, creditor_agent=creditor_agent, amount=amount, cd="B2C"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, rccCurrency, RMNData.orgId, debtor_agent, RMNData.prvtId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        cdtTrfTxInf["purp"] = {"cd": "001", "desc": "Family Maintenance"}
        cdtTrfTxInf["rltnShp"] = {"cd": "002", "desc": "Friend"}

        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, cdtTrfTxInf["intrBkSttlmAmt"]["amt"], rccCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                          isInnerNode=in_node, isRPP=True, rateInfo=rate_info, chg_fees=["USD", "EUR"])

    def test_254_sn_sn_cdtrAgtGiveSNRoxeId_inAmount_differentCurrency_C2B(self):
        """
        主流程: sn_sn, cdtrAgt有roxeId, 且为SN, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_php_ph
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        # sendCountry = "US"
        rccCurrency = "PHP"
        # rccCountry = "US"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, rccCurrency, creditor_agent=creditor_agent, amount=amount, cd="C2B"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, rccCurrency, RMNData.prvtId, debtor_agent, RMNData.orgId, creditor_agent, float(sendFee), sn1, inAmount=amount)

        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, cdtTrfTxInf["intrBkSttlmAmt"]["amt"], rccCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                          isInnerNode=in_node, isRPP=True, rateInfo=rate_info, chg_fees=["USD", "EUR"])

    def test_255_sn_sn_cdtrGiveIBAN_inAmount_differentCurrency_C2C(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId,有IBAN, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_gbp_gb
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        # sendCountry = "US"
        rccCurrency = "GBP"
        # rccCountry = "GB"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.iban_agent
        amount = ApiUtils.randAmount(10, 2, 5)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, rccCurrency, cdtrAcct={"iban": RMNData.iban[rccCurrency]}, amount=amount
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, rccCurrency, RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban[rccCurrency]
        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, cdtTrfTxInf["intrBkSttlmAmt"]["amt"], rccCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                          isInnerNode=in_node, isRPP=True, rateInfo=rate_info, chg_fees=["USD", "EUR"])

    def test_256_sn_sn_cdtrGiveIBAN_inAmount_differentCurrency_B2B(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId,有IBAN, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_gbp_gb
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        # sendCountry = "US"
        rccCurrency = "GBP"
        # rccCountry = "GB"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.iban_agent
        amount = ApiUtils.randAmount(10, 2, 5)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, rccCurrency, cdtrAcct={"iban": RMNData.iban[rccCurrency]}, amount=amount, cd="B2B"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, rccCurrency, RMNData.orgId, debtor_agent, RMNData.orgId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban[rccCurrency]
        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, cdtTrfTxInf["intrBkSttlmAmt"]["amt"], rccCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                          isInnerNode=in_node, isRPP=True, rateInfo=rate_info, chg_fees=["USD", "EUR"])

    def test_257_sn_sn_cdtrGiveIBAN_inAmount_differentCurrency_B2C(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId,有IBAN, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_gbp_gb
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        # sendCountry = "US"
        rccCurrency = "GBP"
        # rccCountry = "GB"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.iban_agent
        amount = ApiUtils.randAmount(10, 2, 5)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, rccCurrency, cdtrAcct={"iban": RMNData.iban[rccCurrency]}, amount=amount, cd="C2B"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, rccCurrency, RMNData.orgId, debtor_agent, RMNData.prvtId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban[rccCurrency]
        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, cdtTrfTxInf["intrBkSttlmAmt"]["amt"], rccCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                          isInnerNode=in_node, isRPP=True, rateInfo=rate_info, chg_fees=["USD", "EUR"])

    def test_258_sn_sn_cdtrGiveIBAN_inAmount_differentCurrency_C2B(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId,有IBAN, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_gbp_gb
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        # sendCountry = "US"
        rccCurrency = "GBP"
        # rccCountry = "GB"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.iban_agent
        amount = ApiUtils.randAmount(10, 2, 5)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, rccCurrency, cdtrAcct={"iban": RMNData.iban[rccCurrency]}, amount=amount, cd="C2B"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, rccCurrency, RMNData.prvtId, debtor_agent, RMNData.orgId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban[rccCurrency]
        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, cdtTrfTxInf["intrBkSttlmAmt"]["amt"], rccCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                          isInnerNode=in_node, isRPP=True, rateInfo=rate_info, chg_fees=["USD", "EUR"])

    def test_259_sn_sn_cdtrAgtGiveBIC_inAmount_differentCurrency_C2C(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId, 有BIC, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_gbp_gb
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        # sendCountry = "US"
        rccCurrency = "GBP"
        # rccCountry = "GB"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.bic_agents[rccCurrency]
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, rccCurrency, creditor_agent=creditor_agent, amount=amount
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, rccCurrency, RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, float(sendFee), sn1, inAmount=60)
        # cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, cdtTrfTxInf["intrBkSttlmAmt"]["amt"], rccCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                          isInnerNode=in_node, isRPP=True, rateInfo=rate_info, chg_fees=["USD", "GBP"])

    def test_260_sn_sn_cdtrAgtGiveBIC_inAmount_differentCurrency_B2B(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId, 有BIC, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        # sendCountry = "US"
        rccCurrency = "GBP"
        # rccCountry = "GB"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.bic_agents[rccCurrency]
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, rccCurrency, creditor_agent=creditor_agent, amount=amount, cd="B2B"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, rccCurrency, RMNData.orgId, debtor_agent, RMNData.orgId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        # cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, cdtTrfTxInf["intrBkSttlmAmt"]["amt"], rccCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                          isInnerNode=in_node, isRPP=True, rateInfo=rate_info, chg_fees=["USD", "GBP"])

    def test_261_sn_sn_cdtrAgtGiveBIC_inAmount_differentCurrency_B2C(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId, 有BIC, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        # sendCountry = "US"
        rccCurrency = "GBP"
        # rccCountry = "GB"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.bic_agents[rccCurrency]
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, rccCurrency, creditor_agent=creditor_agent, amount=amount, cd="B2C"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, rccCurrency, RMNData.orgId, debtor_agent, RMNData.prvtId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        # cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, cdtTrfTxInf["intrBkSttlmAmt"]["amt"], rccCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                          isInnerNode=in_node, isRPP=True, rateInfo=rate_info, chg_fees=["USD", "GBP"])

    def test_262_sn_sn_cdtrAgtGiveBIC_inAmount_differentCurrency_C2B(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId, 有BIC, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        # sendCountry = "US"
        rccCurrency = "GBP"
        # rccCountry = "GB"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.bic_agents[rccCurrency]
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, rccCurrency, creditor_agent=creditor_agent, amount=amount, cd="C2B"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, rccCurrency, RMNData.prvtId, debtor_agent, RMNData.orgId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        # cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, cdtTrfTxInf["intrBkSttlmAmt"]["amt"], rccCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                          isInnerNode=in_node, isRPP=True, rateInfo=rate_info, chg_fees=["USD", "GBP"])

    def test_263_sn_sn_cdtrAgtGiveNCC_inAmount_differentCurrency_C2C(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId, 有NCC, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        # sendCountry = "US"
        rccCurrency = "GBP"
        # rccCountry = "GB"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.ncc_agents[rccCurrency]
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, rccCurrency, creditor_agent=creditor_agent, amount=amount
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, rccCurrency, RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        # cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, cdtTrfTxInf["intrBkSttlmAmt"]["amt"], rccCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                          isInnerNode=in_node, isRPP=True, rateInfo=rate_info, chg_fees=["USD", "GBP"])

    def test_264_sn_sn_cdtrAgtGiveNCC_inAmount_differentCurrency_B2B(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId, 有NCC, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        # sendCountry = "US"
        rccCurrency = "GBP"
        # rccCountry = "GB"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.ncc_agents[rccCurrency]
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, rccCurrency, creditor_agent=creditor_agent, amount=amount, cd="B2B"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, rccCurrency, RMNData.orgId, debtor_agent, RMNData.orgId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        # cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, cdtTrfTxInf["intrBkSttlmAmt"]["amt"], rccCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                          isInnerNode=in_node, isRPP=True, rateInfo=rate_info, chg_fees=["USD", "GBP"])

    def test_265_sn_sn_cdtrAgtGiveNCC_inAmount_differentCurrency_B2C(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId, 有NCC, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        # sendCountry = "US"
        rccCurrency = "GBP"
        # rccCountry = "GB"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.ncc_agents[rccCurrency]
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, rccCurrency, creditor_agent=creditor_agent, amount=amount
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, rccCurrency, RMNData.orgId, debtor_agent, RMNData.prvtId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        # cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, cdtTrfTxInf["intrBkSttlmAmt"]["amt"], rccCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                          isInnerNode=in_node, isRPP=True, rateInfo=rate_info, chg_fees=["USD", "GBP"])

    def test_266_sn_sn_cdtrAgtGiveNCC_inAmount_differentCurrency_C2B(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId, 有NCC, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        # sendCountry = "US"
        rccCurrency = "GBP"
        # rccCountry = "GB"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.ncc_agents[rccCurrency]
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, rccCurrency, creditor_agent=creditor_agent, amount=amount, cd="C2B"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, rccCurrency, RMNData.prvtId, debtor_agent, RMNData.orgId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        # cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, cdtTrfTxInf["intrBkSttlmAmt"]["amt"], rccCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                          isInnerNode=in_node, isRPP=True, rateInfo=rate_info, chg_fees=["USD", "GBP"])

    # PN-SN-SN,同币种
    def test_267_pn_sn_sn_cdtrAgtGiveSNRoxeId_sameCurrency_C2C(self):
        """
        主流程: pn_sn_sn, cdtrAgt有roxeId, 且为SN, cdtrIntrmyAgt及intrmyAgt为空
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_gbp_gb

        sendCurrency = "USD"
        # sendCountry = "US"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            pn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount
        )
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, amount, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    def test_268_pn_sn_sn_cdtrAgtGiveSNRoxeId_sameCurrency_B2B(self):
        """
        主流程: pn_sn_sn, cdtrAgt有roxeId, 且为SN, cdtrIntrmyAgt及intrmyAgt为空
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_gbp_gb

        sendCurrency = "USD"
        # sendCountry = "US"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            pn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount, cd="B2B"
        )
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, amount, "B2B")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.orgId, debtor_agent, RMNData.orgId, creditor_agent, pn1_fee, pn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                             isInnerNode=inner_node)

    def test_269_pn_sn_sn_cdtrAgtGiveSNRoxeId_sameCurrency_B2C(self):
        """
        主流程: pn_sn_sn, cdtrAgt有roxeId, 且为SN, cdtrIntrmyAgt及intrmyAgt为空
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_gbp_gb

        sendCurrency = "USD"
        # sendCountry = "US"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            pn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount, cd="B2C"
        )
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, amount, "B2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.orgId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                             isInnerNode=inner_node)

    def test_270_pn_sn_sn_cdtrAgtGiveSNRoxeId_sameCurrency_C2B(self):
        """
        主流程: pn_sn_sn, cdtrAgt有roxeId, 且为SN, cdtrIntrmyAgt及intrmyAgt为空
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sendCurrency = "USD"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            pn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount, cd="C2B"
        )
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, amount, "C2B")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.prvtId, debtor_agent, RMNData.orgId, creditor_agent, pn1_fee, pn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                             isInnerNode=inner_node)

    def test_271_pn_sn_sn_cdtrGiveIBAN_sameCurrency_C2C(self):
        """
        主流程: pn_sn_sn, cdtrAgt无roxeId, BIC和NCC, cdtr给出IBAN账户
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        sendCurrency = "USD"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.iban_agent
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            pn1, sendCurrency, sendCurrency, cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amount
        )
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, amount, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amount)
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                             isInnerNode=inner_node)

    def test_272_pn_sn_sn_cdtrGiveIBAN_sameCurrency_B2B(self):
        """
        主流程: pn_sn_sn, cdtrAgt无roxeId, BIC和NCC, cdtr给出IBAN账户
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_gbp_gb

        sendCurrency = "USD"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.iban_agent
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            pn1, sendCurrency, sendCurrency, cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amount, cd="B2B"
        )
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, amount, "B2B")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.orgId, debtor_agent, RMNData.orgId, creditor_agent, pn1_fee, pn1, inAmount=amount)
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                             isInnerNode=inner_node)

    def test_272_pn_sn_sn_cdtrGiveIBAN_sameCurrency_B2C(self):
        """
        主流程: pn_sn_sn, cdtrAgt无roxeId, BIC和NCC, cdtr给出IBAN账户
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_gbp_gb

        sendCurrency = "USD"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.iban_agent
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            pn1, sendCurrency, sendCurrency, cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amount, cd="B2C"
        )
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, amount, "B2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.orgId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amount)
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                             isInnerNode=inner_node)

    def test_273_pn_sn_sn_cdtrGiveIBAN_sameCurrency_C2B(self):
        """
        主流程: pn_sn_sn, cdtrAgt无roxeId, BIC和NCC, cdtr给出IBAN账户
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_gbp_gb

        sendCurrency = "USD"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.iban_agent
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            pn1, sendCurrency, sendCurrency, cdtrAcct={"iban": RMNData.iban["GBP"]}, amount=amount, cd="C2B"
        )
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, amount, "C2B")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.prvtId, debtor_agent, RMNData.orgId, creditor_agent, pn1_fee, pn1, inAmount=amount)
        cdtTrfTxInf["cdtrAcct"]["iban"] = RMNData.iban["GBP"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                             isInnerNode=inner_node)

    def test_274_pn_sn_sn_cdtrAgtGiveBIC_sameCurrency_C2C(self):
        """
        主流程: pn_sn_sn, cdtrAgt无roxeId, 有BIC, cdtrIntrmyAgt及intrmyAgt为空
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_gbp_gb

        sendCurrency = "USD"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            pn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount
        )
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, amount, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                             isInnerNode=inner_node)

    def test_275_pn_sn_sn_cdtrAgtGiveBIC_sameCurrency_B2B(self):
        """
        主流程: pn_sn_sn, cdtrAgt无roxeId, 有BIC, cdtrIntrmyAgt及intrmyAgt为空
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_gbp_gb

        sendCurrency = "USD"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            pn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount, cd="B2B"
        )
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, amount, "B2B")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.orgId, debtor_agent, RMNData.orgId, creditor_agent, pn1_fee, pn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                             isInnerNode=inner_node)

    def test_276_pn_sn_sn_cdtrAgtGiveBIC_sameCurrency_B2C(self):
        """
        主流程: pn_sn_sn, cdtrAgt无roxeId, 有BIC, cdtrIntrmyAgt及intrmyAgt为空
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_gbp_gb

        sendCurrency = "USD"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            pn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount, cd="B2C"
        )
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, amount, "B2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.orgId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                             isInnerNode=inner_node)

    def test_277_pn_sn_sn_cdtrAgtGiveBIC_sameCurrency_C2B(self):
        """
        主流程: pn_sn_sn, cdtrAgt无roxeId, 有BIC, cdtrIntrmyAgt及intrmyAgt为空
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_gbp_gb

        sendCurrency = "USD"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.bic_agents["GBP"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            pn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount, cd="C2B"
        )
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, amount, "C2B")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.prvtId, debtor_agent, RMNData.orgId, creditor_agent, pn1_fee, pn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                             isInnerNode=inner_node)

    def test_278_pn_sn_sn_cdtrAgtGiveNCC_sameCurrency_C2C(self):
        """
        主流程: pn_sn_sn, cdtrAgt无roxeId, 有NCC, cdtrIntrmyAgt及intrmyAgt为空
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_gbp_gb

        sendCurrency = "USD"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            pn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount
        )
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, amount, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                             isInnerNode=inner_node)

    def test_279_pn_sn_sn_cdtrAgtGiveNCC_sameCurrency_B2B(self):
        """
        主流程: pn_sn_sn, cdtrAgt无roxeId, 有NCC, cdtrIntrmyAgt及intrmyAgt为空
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_gbp_gb

        sendCurrency = "USD"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            pn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount, cd="B2B"
        )
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, amount, "B2B")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.orgId, debtor_agent, RMNData.orgId, creditor_agent, pn1_fee, pn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                             isInnerNode=inner_node)

    def test_280_pn_sn_sn_cdtrAgtGiveNCC_sameCurrency_B2C(self):
        """
        主流程: pn_sn_sn, cdtrAgt无roxeId, 有NCC, cdtrIntrmyAgt及intrmyAgt为空
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_gbp_gb

        sendCurrency = "USD"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            pn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount, cd="B2C"
        )
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, amount, "B2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.orgId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                             isInnerNode=inner_node)

    def test_281_pn_sn_sn_cdtrAgtGiveNCC_sameCurrency_C2B(self):
        """
        主流程: pn_sn_sn, cdtrAgt无roxeId, 有NCC, cdtrIntrmyAgt及intrmyAgt为空
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_gbp_gb

        sendCurrency = "USD"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            pn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount, cd="C2B"
        )
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, amount, "C2B")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.prvtId, debtor_agent, RMNData.orgId, creditor_agent, pn1_fee, pn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                             isInnerNode=inner_node)

    # PN-SN-SN，不同币种
    def test_282_pn_sn_sn_cdtrAgtGiveSNRoxeId_inAmount_differentCurrency_C2C(self):
        """
        主流程: pn_sn_sn, cdtrAgt有roxeId, 且为SN, cdtrIntrmyAgt及intrmyAgt为空
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_php_ph
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        rccCurrency = "PHP"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            pn1, sendCurrency, rccCurrency, creditor_agent=creditor_agent, amount=amount
        )
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, amount, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, rccCurrency, RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=60)

        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        sn_amt = ApiUtils.parseNumberDecimal(float(cdtTrfTxInf["intrBkSttlmAmt"]["amt"]) - float(sendFee), 2, True)
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, sn_amt, rccCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=in_node,
                                             isRPP=True, rateInfo=rate_info, chg_fees=["USD", "EUR"])

    def test_283_pn_sn_sn_cdtrAgtGiveSNRoxeId_inAmount_differentCurrency_B2B(self):
        """
        主流程: pn_sn_sn, cdtrAgt有roxeId, 且为SN, cdtrIntrmyAgt及intrmyAgt为空
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_php_ph
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        rccCurrency = "PHP"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            pn1, sendCurrency, rccCurrency, creditor_agent=creditor_agent, amount=amount, cd="B2B"
        )
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, amount, "B2B")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, rccCurrency, RMNData.orgId, debtor_agent, RMNData.orgId, creditor_agent, pn1_fee, pn1, inAmount=amount)

        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        sn_amt = ApiUtils.parseNumberDecimal(float(cdtTrfTxInf["intrBkSttlmAmt"]["amt"]) - float(sendFee), 2, True)
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, sn_amt, rccCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                             isInnerNode=in_node,
                                             isRPP=True, rateInfo=rate_info, chg_fees=["USD", "PHP"])

    def test_284_pn_sn_sn_cdtrAgtGiveSNRoxeId_inAmount_differentCurrency_B2C(self):
        """
        主流程: pn_sn_sn, cdtrAgt有roxeId, 且为SN, cdtrIntrmyAgt及intrmyAgt为空
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_php_ph
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        rccCurrency = "PHP"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            pn1, sendCurrency, rccCurrency, creditor_agent=creditor_agent, amount=amount, cd="B2C"
        )
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, amount, "B2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, rccCurrency, RMNData.orgId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amount)

        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        sn_amt = ApiUtils.parseNumberDecimal(float(cdtTrfTxInf["intrBkSttlmAmt"]["amt"]) - float(sendFee), 2, True)
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, sn_amt, rccCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                             isInnerNode=in_node,
                                             isRPP=True, rateInfo=rate_info, chg_fees=["USD", "PHP"])

    def test_285_pn_sn_sn_cdtrAgtGiveSNRoxeId_inAmount_differentCurrency_C2B(self):
        """
        主流程: pn_sn_sn, cdtrAgt有roxeId, 且为SN, cdtrIntrmyAgt及intrmyAgt为空
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_php_ph
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        rccCurrency = "PHP"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            pn1, sendCurrency, rccCurrency, creditor_agent=creditor_agent, amount=amount, cd="C2B"
        )
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, amount, "C2B")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, rccCurrency, RMNData.prvtId, debtor_agent, RMNData.orgId, creditor_agent, pn1_fee, pn1, inAmount=amount)

        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        sn_amt = ApiUtils.parseNumberDecimal(float(cdtTrfTxInf["intrBkSttlmAmt"]["amt"]) - float(sendFee), 2, True)
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, sn_amt, rccCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                             isInnerNode=in_node,
                                             isRPP=True, rateInfo=rate_info, chg_fees=["USD", "EUR"])

    def test_286_pn_sn_sn_cdtrAgtGiveNCC_inAmount_differentCurrency_C2C(self):
        """
        主流程: pn_sn_sn, cdtrAgt无roxeId,有NCC , cdtrIntrmyAgt及intrmyAgt为空
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_php_ph
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        rccCurrency = "PHP"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.ncc_agents["USD"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            pn1, sendCurrency, rccCurrency, creditor_agent=creditor_agent, amount=amount, cd="C2C"
        )
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, amount, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, rccCurrency, RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amount)

        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        sn_amt = ApiUtils.parseNumberDecimal(float(cdtTrfTxInf["intrBkSttlmAmt"]["amt"]) - float(sendFee), 2, True)
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, sn_amt, rccCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                             isInnerNode=in_node,
                                             isRPP=True, rateInfo=rate_info, chg_fees=["USD", rccCurrency])

    def test_287_pn_sn_sn_cdtrAgtGiveNCC_inAmount_differentCurrency_B2B(self):
        """
        主流程: pn_sn_sn,cdtrAgt无roxeId,有NCC, cdtrIntrmyAgt及intrmyAgt为空
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_php_ph
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        rccCurrency = "PHP"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.ncc_agents["USD"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            pn1, sendCurrency, rccCurrency, creditor_agent=creditor_agent, amount=amount, cd="B2B"
        )
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, amount, "B2B")["in"]
        print(sendFee)
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, rccCurrency, RMNData.orgId, debtor_agent, RMNData.orgId, creditor_agent, pn1_fee, pn1, inAmount=amount)

        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        sn_amt = ApiUtils.parseNumberDecimal(float(cdtTrfTxInf["intrBkSttlmAmt"]["amt"]) - float(sendFee), 2, True)
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, sn_amt, rccCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                             isInnerNode=in_node,
                                             isRPP=True, rateInfo=rate_info, chg_fees=["USD", rccCurrency])

    def test_288_pn_sn_sn_cdtrAgtGiveNCC_inAmount_differentCurrency_B2C(self):
        """
        主流程: pn_sn_sn,cdtrAgt无roxeId,有NCC, cdtrIntrmyAgt及intrmyAgt为空
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_php_ph
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        rccCurrency = "PHP"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.ncc_agents["USD"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            pn1, sendCurrency, rccCurrency, creditor_agent=creditor_agent, amount=amount, cd="B2C"
        )
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, amount, "B2C")["in"]
        print(sendFee)
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, rccCurrency, RMNData.orgId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amount)

        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        sn_amt = ApiUtils.parseNumberDecimal(float(cdtTrfTxInf["intrBkSttlmAmt"]["amt"]) - float(sendFee), 2, True)
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, sn_amt, rccCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                             isInnerNode=in_node,
                                             isRPP=True, rateInfo=rate_info, chg_fees=["USD", rccCurrency])

    def test_289_pn_sn_sn_cdtrAgtGiveNCC_inAmount_differentCurrency_C2B(self):
        """
        主流程: pn_sn_sn,cdtrAgt无roxeId,有NCC, cdtrIntrmyAgt及intrmyAgt为空
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_php_ph
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        rccCurrency = "PHP"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = RMNData.ncc_agents["USD"]
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            pn1, sendCurrency, rccCurrency, creditor_agent=creditor_agent, amount=amount, cd="C2B"
        )
        print(sendFee)
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, amount, "C2B")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, rccCurrency, RMNData.prvtId, debtor_agent, RMNData.orgId, creditor_agent, pn1_fee, pn1, inAmount=amount)

        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        sn_amt = ApiUtils.parseNumberDecimal(float(cdtTrfTxInf["intrBkSttlmAmt"]["amt"]) - float(sendFee), 2, True)
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, sn_amt, rccCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn(pn1, sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                             isInnerNode=in_node,
                                             isRPP=True, rateInfo=rate_info, chg_fees=["USD", rccCurrency])

    # SN-SN-PN,同币种
    def test_290_sn_sn_pn_cdtrAgtGivePNRoxeId_sameCurrency_C2C(self):
        """
        主流程: sn_sn_pn, cdtrAgt有roxeId, 且为PN, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        sendCurrency = "USD"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_pn(sn1, sn2, pn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    def test_291_sn_sn_pn_cdtrAgtGivePNRoxeId_sameCurrency_B2B(self):
        """
        主流程: sn_sn_pn, cdtrAgt有roxeId, 且为PN, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        sendCurrency = "USD"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount, cd="B2B"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.orgId, debtor_agent, RMNData.orgId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_pn(sn1, sn2, pn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                             isInnerNode=inner_node)

    def test_292_sn_sn_pn_cdtrAgtGivePNRoxeId_sameCurrency_B2C(self):
        """
        主流程: sn_sn_pn, cdtrAgt有roxeId, 且为PN, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        sendCurrency = "USD"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount, cd="B2C"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.orgId, debtor_agent, RMNData.prvtId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_pn(sn1, sn2, pn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                             isInnerNode=inner_node)

    def test_293_sn_sn_pn_cdtrAgtGivePNRoxeId_sameCurrency_C2B(self):
        """
        主流程: sn_sn_pn, cdtrAgt有roxeId, 且为PN, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        sendCurrency = "USD"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount, cd="C2B"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.prvtId, debtor_agent, RMNData.orgId, creditor_agent, float(sendFee), sn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_pn(sn1, sn2, pn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                             isInnerNode=inner_node)

    # SN-SN-PN,不同币种
    def test_294_sn_sn_pn_cdtrAgtGivePNRoxeId_differentCurrency_C2C(self):
        """
        主流程: sn_sn_pn, cdtrAgt有roxeId, 且为PN, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_php_ph
        pn2 = RMNData.pn_php_ph
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        rccCurrency = "PHP"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, rccCurrency, creditor_agent=creditor_agent, amount=amount
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, rccCurrency, RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, float(sendFee), sn1, inAmount=amount)

        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, cdtTrfTxInf["intrBkSttlmAmt"]["amt"], rccCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_pn(
            sn1, sn2, pn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=in_node,
            isRPP=True, rateInfo=rate_info, chg_fees=[sendCurrency, rccCurrency])

    def test_295_sn_sn_pn_cdtrAgtGivePNRoxeId_differentCurrency_B2B(self):
        """
        主流程: sn_sn_pn, cdtrAgt有roxeId, 且为PN, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_php_ph
        pn2 = RMNData.pn_php_ph
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        rccCurrency = "PHP"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, rccCurrency, creditor_agent=creditor_agent, amount=amount, cd="B2B"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, rccCurrency, RMNData.orgId, debtor_agent, RMNData.orgId, creditor_agent, float(sendFee), sn1, inAmount=amount)

        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, cdtTrfTxInf["intrBkSttlmAmt"]["amt"], rccCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_pn(
            sn1, sn2, pn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=in_node,
            isRPP=True, rateInfo=rate_info, chg_fees=[sendCurrency, rccCurrency])

    def test_296_sn_sn_pn_cdtrAgtGivePNRoxeId_differentCurrency_B2C(self):
        """
        主流程: sn_sn_pn, cdtrAgt有roxeId, 且为PN, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_php_ph
        pn2 = RMNData.pn_php_ph
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        rccCurrency = "PHP"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, rccCurrency, creditor_agent=creditor_agent, amount=amount, cd="B2C"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, rccCurrency, RMNData.orgId, debtor_agent, RMNData.prvtId, creditor_agent, float(sendFee), sn1, inAmount=amount)

        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, cdtTrfTxInf["intrBkSttlmAmt"]["amt"], rccCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_pn(
            sn1, sn2, pn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=in_node,
            isRPP=True, rateInfo=rate_info, chg_fees=[sendCurrency, rccCurrency])

    def test_297_sn_sn_pn_cdtrAgtGivePNRoxeId_differentCurrency_C2B(self):
        """
        主流程: sn_sn_pn, cdtrAgt有roxeId, 且为PN, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_php_ph
        pn2 = RMNData.pn_php_ph
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        rccCurrency = "PHP"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, rccCurrency, creditor_agent=creditor_agent, amount=amount, cd="C2B"
        )
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, rccCurrency, RMNData.prvtId, debtor_agent, RMNData.orgId, creditor_agent, float(sendFee), sn1, inAmount=amount)

        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, cdtTrfTxInf["intrBkSttlmAmt"]["amt"], rccCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_pn(
            sn1, sn2, pn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=in_node,
            isRPP=True, rateInfo=rate_info, chg_fees=[sendCurrency, rccCurrency])

    # PN-SN-SN-PN,同币种
    def test_298_pn_sn_sn_pn_dbtrAgtGivePNRoxeId_cdtrAgtGivePNRoxeId_sameCurrency_C2C(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        sendCurrency = "USD"
        rccCurrency = "USD"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            pn1, sendCurrency, rccCurrency, creditor_agent=creditor_agent, amount=amount
        )
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, amount, "C2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    def test_299_pn_sn_sn_pn_dbtrAgtGivePNRoxeId_cdtrAgtGivePNRoxeId_sameCurrency_B2B(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_usd_gb
        sendCurrency = "USD"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            pn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount, cd="B2B"
        )
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, amount, "B2B")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.orgId, debtor_agent, RMNData.orgId, creditor_agent, pn1_fee, pn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)],
                                                self, isInnerNode=inner_node)

    def test_300_pn_sn_sn_pn_dbtrAgtGivePNRoxeId_cdtrAgtGivePNRoxeId_sameCurrency_B2C(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_gbp_gb
        pn2 = RMNData.pn_usd_gb

        sendCurrency = "USD"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            pn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount, cd="B2C"
        )
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, amount, "B2C")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.orgId, debtor_agent, RMNData.prvtId, creditor_agent, pn1_fee, pn1, inAmount=amount)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)],
                                                self, isInnerNode=inner_node)

    def test_301_pn_sn_sn_pn_dbtrAgtGivePNRoxeId_cdtrAgtGivePNRoxeId_sameCurrency_C2B(self):
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb

        sendCurrency = "USD"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            pn1, sendCurrency, sendCurrency, creditor_agent=creditor_agent, amount=amount, cd="C2B"
        )
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, amount, "C2B")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.prvtId, debtor_agent, RMNData.orgId, creditor_agent, pn1_fee, pn1, inAmount=amount)
        cdtTrfTxInf["purp"] = {"cd": "001", "desc": "Family Maintenance"}
        cdtTrfTxInf["rltnShp"] = {"cd": "002", "desc": "Friend"}
        self.client.logger.info(cdtTrfTxInf)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(pn1, sn1, sn2, pn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)],
                                                self, isInnerNode=inner_node)

    # PN-SN-SN-PN,不同币种
    def test_302_pn_sn_sn_pn_cdtrAgtGiveSNRoxeId_inAmount_differentCurrency_C2C(self):
        """
        主流程: pn_sn_sn_pn, cdtrAgt有roxeId, cdtrIntrmyAgt及intrmyAgt为空
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_php_ph
        pn2 = RMNData.pn_php_ph

        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PHP"
        recCountry = "US"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, sn2)
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, recCurrency, RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, 1, pn1, inAmount=50)

        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        sn_amt = ApiUtils.parseNumberDecimal(float(cdtTrfTxInf["intrBkSttlmAmt"]["amt"]) - float(sendFee), 2, True)
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, sn_amt, recCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(
            pn1, sn1, sn2, pn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=in_node,
            isRPP=True, rateInfo=rate_info, chg_fees=[sendCurrency, recCurrency])

    def test_303_pn_sn_sn_pn_cdtrAgtGiveSNRoxeId_inAmount_differentCurrency_B2B(self):
        """
        主流程: pn_sn_sn_pn, cdtrAgt有roxeId, cdtrIntrmyAgt及intrmyAgt为空
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_php_ph
        pn2 = RMNData.pn_php_ph

        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PHP"
        recCountry = "US"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, sn2)
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, recCurrency, RMNData.orgId, debtor_agent, RMNData.orgId, creditor_agent, 1, pn1, inAmount=50)

        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        sn_amt = ApiUtils.parseNumberDecimal(float(cdtTrfTxInf["intrBkSttlmAmt"]["amt"]) - float(sendFee), 2, True)
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, sn_amt, recCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(
            pn1, sn1, sn2, pn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=in_node,
            isRPP=True, rateInfo=rate_info, chg_fees=[sendCurrency, recCurrency])

    def test_304_pn_sn_sn_pn_cdtrAgtGiveSNRoxeId_inAmount_differentCurrency_B2C(self):
        """
        主流程: pn_sn_sn_pn, cdtrAgt有roxeId, cdtrIntrmyAgt及intrmyAgt为空
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_php_ph
        pn2 = RMNData.pn_php_ph

        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PHP"
        recCountry = "US"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, sn2)
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, recCurrency, RMNData.orgId, debtor_agent, RMNData.prvtId, creditor_agent, 1, pn1, inAmount=50)

        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        sn_amt = ApiUtils.parseNumberDecimal(float(cdtTrfTxInf["intrBkSttlmAmt"]["amt"]) - float(sendFee), 2, True)
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, sn_amt, recCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(
            pn1, sn1, sn2, pn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=in_node,
            isRPP=True, rateInfo=rate_info, chg_fees=[sendCurrency, recCurrency])

    def test_305_pn_sn_sn_pn_cdtrAgtGiveSNRoxeId_inAmount_differentCurrency_C2B(self):
        """
        主流程: pn_sn_sn_pn, cdtrAgt有roxeId, cdtrIntrmyAgt及intrmyAgt为空
        """
        pn1 = RMNData.pn_usd_us
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_php_ph
        pn2 = RMNData.pn_php_ph

        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        recCurrency = "PHP"
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        sendFee, deliverFee, _ = self.client.step_queryRouter(pn1, sendCurrency, recCurrency, creditor_agent=creditor_agent, amount=50, cd="C2B")
        pn1_fee = self.client.getNodeFeeInDB(pn1, sendCurrency, 50, "C2B")["in"]
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, recCurrency, RMNData.prvtId, debtor_agent, RMNData.orgId, creditor_agent, pn1_fee, pn1, inAmount=50)

        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        sn_amt = ApiUtils.parseNumberDecimal(float(cdtTrfTxInf["intrBkSttlmAmt"]["amt"]) - float(sendFee), 2, True)
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency, sn_amt, recCurrency)
        self.client.checkCodeAndMessage(rate_info)

        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_pn_sn_sn_pn(
            pn1, sn1, sn2, pn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=in_node,
            isRPP=True, rateInfo=rate_info, chg_fees=[sendCurrency, recCurrency])

    # To B异常用例
    def test_306_getRouterList_senderIsSN_snRoxeId_sameCurrency(self):
        """
        查询路由, 消息发送方为SN节点, 指定sn2 roxe id, cd 字段大小写混合校验
        """
        sender = RMNData.sn_usd_us
        recCurrency = "USD"
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(RMNData.sn_gbp_gb, "SN")
        cd_list = ["c2c", "b2B", "b2c", "C2b"]
        for cd in cd_list:
            msg = self.client.make_RRLQ_information("USD", recCurrency, "100", cdtrAgt=agent_info, cd=cd)
            router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
            self.assertEqual(router_list["code"], "00100000", msg="返回的code码不正确")
            self.assertEqual(router_list["message"], "Parameter exception, rtgQryDef.pmtTpInf.ctgyPurp.cd has invalid value:{}".format(cd))

    def test_307_getRouterList_senderIsSN_snRoxeId_sameCurrency(self):
        """
        查询路由, 消息发送方为SN节点, 指定sn2 roxe id, cd 字段填写不正确或为空
        """
        sender = RMNData.sn_usd_us
        recCurrency = "USD"
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(RMNData.sn_gbp_gb, "SN")
        cd_list = ["123", "abc", "A2C", ""]
        for cd in cd_list:
            msg = self.client.make_RRLQ_information("USD", recCurrency, "100", cdtrAgt=agent_info, cd=cd)
            router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
            self.assertEqual(router_list["code"], "00100000", msg="返回的code码不正确")
            self.assertEqual(router_list["message"], "Parameter exception, rtgQryDef.pmtTpInf.ctgyPurp.cd has invalid value:{}".format(cd))

    def test_308_getRouterList_senderIsPN_pnRoxeId_differentCurrency(self):
        """cd 字段大小写混合校验"""
        sender = RMNData.pn_usd_us  # PN1 节点
        recCurrency = "EUR"
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent("pn.fr.eur", "PN")
        cd_list = ["c2c", "b2B", "b2c", "C2b"]
        for cd in cd_list:
            msg = self.client.make_RRLQ_information("USD", recCurrency, "100", cdtrAgt=agent_info, cd=cd)
            router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
            self.assertEqual(router_list["code"], "00100000", msg="返回的code码不正确")
            self.assertEqual(router_list["message"], "Parameter exception, rtgQryDef.pmtTpInf.ctgyPurp.cd has invalid value:{}".format(cd))

    def test_309_getRouterList_senderIsPN_pnRoxeId_differentCurrency(self):
        """cd 字段填写不正确或为空"""
        sender = RMNData.pn_usd_us  # PN1 节点
        recCurrency = "EUR"
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent("pn.fr.eur", "PN")
        cd_list = ["123", "abc", "A2C", ""]
        for cd in cd_list:
            msg = self.client.make_RRLQ_information("USD", recCurrency, "100", cdtrAgt=agent_info, cd=cd)
            router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
            self.assertEqual(router_list["code"], "00100000", msg="返回的code码不正确")
            self.assertEqual(router_list["message"], "Parameter exception, rtgQryDef.pmtTpInf.ctgyPurp.cd has invalid value:{}".format(cd))

    def test_310_getRouterList_senderIsSN_snRoxeId_differentCurrency(self):
        """
        查询路由, 消息发送方为SN节点, 指定sn2 roxe id，左侧SN为RMN节点，右侧SN为MOCK节点,目前仅支持C2C(cd字段为当前节点不支持的业务方式）
        """
        sender = RMNData.sn_usd_us
        recCurrency = "USD"
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(RMNData.mock_node, "SN")
        cd_list = ["B2B", "B2C", "C2B"]
        for cd in cd_list:
            msg = self.client.make_RRLQ_information("USD", recCurrency, "100", cdtrAgt=agent_info, cd=cd)
            router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
            self.assertEqual(router_list["code"], "00500003", msg="返回的code码不正确")
            self.assertEqual(router_list["message"], "No correct routing information was found")

    def test_311_getRouterList_senderIsSN_snRoxeId_differentCurrency(self):
        """
        查询路由, 消息发送方为SN节点, 指定sn2 roxe id，左侧SN为RMN节点，右侧SN为TerraPay节点,目前仅支持C2C(cd字段为当前节点不支持的业务方式）
        """
        sender = RMNData.sn_usd_us
        recCurrency = "PHP"
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(RMNData.sn_roxe_terrapay, "SN")
        cd_list = ["B2B", "B2C", "C2B"]
        for cd in cd_list:
            msg = self.client.make_RRLQ_information("USD", recCurrency, "100", cdtrAgt=agent_info, cd=cd)
            router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
            self.assertEqual(router_list["code"], "00500003", msg="返回的code码不正确")
            self.assertEqual(router_list["message"], "No correct routing information was found")

    def test_312_getRouterList_senderIsPN_snRoxeId_differentCurrency(self):
        """
        查询路由, 消息发送方为PN节点, 指定sn2 roxe id,左侧SN为RMN节点，右侧SN为TerraPay节点,目前仅支持C2C(cd字段为当前节点不支持的业务方式）
        """
        sender = RMNData.pn_usd_us  # PN1 节点
        recCurrency = "PHP"
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(RMNData.sn_roxe_terrapay, "SN")
        cd_list = ["B2B", "B2C", "C2B"]
        for cd in cd_list:
            msg = self.client.make_RRLQ_information("USD", recCurrency, "100", cdtrAgt=agent_info, cd=cd)
            router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
            self.assertEqual(router_list["code"], "00500003", msg="返回的code码不正确")
            self.assertEqual(router_list["message"], "No correct routing information was found")

    def test_313_getRouterList_senderIsPN_cdtrAgtGiveBicCode_differentCurrency(self):
        """
        查询路由, 消息发送方为PN节点,左侧SN为RMN节点，右侧SN为TerraPay节点,目前仅支持C2C(cd字段为当前节点不支持的业务方式）
        """
        sender = RMNData.sn_usd_us
        recCurrency = "MYR"
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        cd_list = ["B2B", "B2C", "C2B"]
        for cd in cd_list:
            msg = self.client.make_RRLQ_information("USD", recCurrency, "100", cdtrAgt=RMNData.bic_agents[recCurrency], cd=cd)
            router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
            self.assertEqual(router_list["code"], "00500003", msg="返回的code码不正确")
            self.assertEqual(router_list["message"], "No correct routing information was found")

    @unittest.skip("异常处理手动执行")
    def test_314_sn_sn_cdtrAgtGiveSNRoxeId_sameCurrency_C2B(self):
        """
        USD-USD,B2C业务,MOCK节点目前仅支持出金C2C业务
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.mock_node

        sendCurrency = "USD"
        sendCountry = "US"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, sendCurrency, sendCountry, sn1, "MOCK")
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.prvtId, debtor_agent, RMNData.orgId,
                                                        creditor_agent, float(sendFee), sn1)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                          isInnerNode=inner_node)
        # 接口应返回{"code": "00200012", "message": "Company remittance is not permitted by your party, please contace your admin."}

    @unittest.skip("异常处理手动执行")
    def test_315_sn_sn_rightNodeUsePayChannel_TerraPay_MYR_B2C(self):
        """
        右侧节点选择支付通道（terrapay），B2C传参
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay

        addenda_info = RMNData.out_bank_info["TerraPay"].copy()
        # amount = float(addenda_info["amount"])
        r_currency = "MYR"
        r_name = "oyugi randy"
        r_country = "MY"
        r_bank_name = "MAY BANKA"
        r_account_number = "1976041128"
        r_bank_code = "MBBEMYKL"
        debtor = RMNData.orgId
        # debtor_agent = {"finInstnId": {"othr": {"id": sn1, "schmeCd": "ROXE"}}}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        # creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        creditor = {
            "nm": r_name,
            "ctryOfRes": r_country,
            "prvtId": {
                "dtAndPlcOfBirth": {"ctryOfBirth": r_country, "cityOfBirth": "on the earth"}
            }
        }
        sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, "RMN", "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information(
            "USD", r_currency, debtor, debtor_agent, creditor, creditor_agent, creditor_intermediary_agent,
            float(sendFee), sn1, addenda_info, r_account_number
        )
        # self.submitOrderAndCheckToTerrapayAmount(sn1, sn2, cdtTrfTxInf, api_key, sec_key, r_currency, to_amount)
        # self.submitOrderAndCheckToRmnChannelAmount(sn1, sn2, cdtTrfTxInf, api_key, sec_key, to_amount, deliverFee)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                          isInnerNode=inner_node)

        # rmn_id = "risn2roxe51"
        # msg_id = self.client.make_msg_id()
        # tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id)
        # tx_group_header = self.client.make_group_header(sn1, rmn_id, msg_id)
        # tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        # print(tx_info,tx_msg)
        # 接口应返回{"code": "00200012", "message": "Company remittance is not permitted by your party, please contace your admin."}

    # mock节点支持RPP换汇出金
    def test_316_getRouterList_senderIsSN_sameCurrency_snRoxeId(self):
        """
        查询路由, 消息发送方为SN节点, 指定sn2 roxe id,左侧SN为RMN节点，右侧SN为MOCK节点,目前仅支持C2C
        """
        sender = RMNData.sn_usd_us
        recCurrency = "USD"
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(RMNData.mock_node, "SN")
        msg = self.client.make_RRLQ_information("USD", recCurrency, "100", cdtrAgt=agent_info, cd="C2C")
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "sn-sn")

    def test_317_getRouterList_senderIsSN_differentCurrency_snRoxeId(self):
        """
        查询路由, 消息发送方为SN节点,cdtrAgt提供BIC ,左侧SN为RMN节点，右侧SN为MOCK节点,目前仅支持C2C
        """
        sender = RMNData.sn_usd_us
        recCurrency = "PHP"
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(RMNData.mock_node, "SN")
        # sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sender, "USD", recCurrency, cdtrAgt=RMNData.bic_agents[recCurrency])
        msg = self.client.make_RRLQ_information("USD", recCurrency, "100", cdtrAgt=agent_info, cd="C2C")
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "sn-sn")

    def test_318_sn_sn_cdtrAgtGiveSNRoxeId_inAmount_differentCurrency(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId, 有BIC, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.mock_node
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        recCurrency = "EUR"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sendFee, deliverFee, _ = self.client.step_queryRouter(sn1, sendCurrency, recCurrency,
                                                              creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.prvtId, debtor_agent,
                                                        RMNData.prvtId,
                                                        creditor_agent, float(sendFee), sn1, inAmount=amt)
        cdtTrfTxInf["cdtrAgt"]["finInstnId"]["bicFI"] = RMNData.bic_agents["USD"]["finInstnId"]["bicFI"]
        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency,
                                                           cdtTrfTxInf["intrBkSttlmAmt"]["amt"], recCurrency)
        self.client.checkCodeAndMessage(rate_info)
        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                          isInnerNode=in_node, isRPP=True, rateInfo=rate_info, chg_fees=["USD", "EUR"])

    def test_319_sn_sn_cdtrAgtGiveSNRoxeId_inAmount_differentCurrency(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId, 有BIC, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.mock_node
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        recCurrency = "PHP"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sendFee, deliverFee, _ = self.client.step_queryRouter(sn1, sendCurrency, recCurrency,
                                                              creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.prvtId, debtor_agent,
                                                        RMNData.prvtId,
                                                        creditor_agent, float(sendFee), sn1, inAmount=amt)
        cdtTrfTxInf["cdtrAgt"]["finInstnId"]["bicFI"] = RMNData.bic_agents[recCurrency]["finInstnId"]["bicFI"]

        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency,
                                                           cdtTrfTxInf["intrBkSttlmAmt"]["amt"], recCurrency)
        self.client.checkCodeAndMessage(rate_info)
        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                          isInnerNode=in_node, isRPP=True, rateInfo=rate_info, chg_fees=["USD", "PHP"])

    def test_320_sn_sn_cdtrAgtGiveSNRoxeId_inAmount_differentCurrency(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId, 有NCC, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.mock_node
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        recCurrency = "INR"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sendFee, deliverFee, _ = self.client.step_queryRouter(sn1, sendCurrency, recCurrency,
                                                              creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.prvtId, debtor_agent,
                                                        RMNData.prvtId,
                                                        creditor_agent, float(sendFee), sn1, inAmount=amt)
        cdtTrfTxInf["cdtrAgt"]["finInstnId"]["clrSysMmbId"] = RMNData.ncc_agents["USD"]["finInstnId"]["clrSysMmbId"]

        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency,
                                                           cdtTrfTxInf["intrBkSttlmAmt"]["amt"], recCurrency)
        self.client.checkCodeAndMessage(rate_info)
        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                          isInnerNode=in_node, isRPP=True, rateInfo=rate_info, chg_fees=["USD", "INR"])

    def test_321_sn_sn_cdtrAgtGiveSNRoxeId_inAmount_differentCurrency(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId, 有NCC, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_eur_fr
        # sn1 = RMNData.sn_usd_us  # sandbox环境数据
        sn2 = RMNData.mock_node
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "EUR"
        recCurrency = "USD"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sendFee, deliverFee, _ = self.client.step_queryRouter(sn1, sendCurrency, recCurrency,
                                                              creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.prvtId, debtor_agent,
                                                        RMNData.prvtId,
                                                        creditor_agent, float(sendFee), sn1, inAmount=amt)
        cdtTrfTxInf["cdtrAgt"]["finInstnId"]["clrSysMmbId"] = RMNData.ncc_agents[recCurrency]["finInstnId"]["clrSysMmbId"]

        ts_headers = self.client.make_header(sn1, apiKey, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(secKey, ts_headers, msg_header, sendCurrency,
                                                           cdtTrfTxInf["intrBkSttlmAmt"]["amt"], recCurrency)
        self.client.checkCodeAndMessage(rate_info)
        in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
                                          isInnerNode=in_node, isRPP=True, rateInfo=rate_info, chg_fees=["EUR", "USD"])

    def test_322_sn_sn_cdtrAgtGiveSNRoxeId_inAmount_differentCurrency(self):
        """
        主流程: sn_sn, cdtrAgt无roxeId, 有NCC, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.mock_node
        sendCurrency = "USD"
        # recCurrency = "EUR"
        # recCountry = "FR"
        recCurrency = "INR"  # sandbox环境数据
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sendFee, deliverFee, _ = self.client.step_queryRouter(sn1, sendCurrency, recCurrency, creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information(
            sendCurrency, sendCurrency, RMNData.prvtId, debtor_agent, RMNData.prvtId, creditor_agent, float(sendFee), 
            sn1, inAmount=amt
        )
        cdtTrfTxInf["cdtrAgt"]["finInstnId"]["bicFI"] = RMNData.bic_agents[recCurrency]["finInstnId"]["bicFI"]

        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    def test_323_sn_sn_cdtrAgtGiveSNRoxeId_sameCurrency(self):
        """
        USD-USD
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.mock_node
        sendCurrency = "USD"
        recCurrency = "USD"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 30)
        sendFee, deliverFee, _ = self.client.step_queryRouter(sn1, sendCurrency, recCurrency, creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information(sendCurrency, sendCurrency, RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, float(sendFee), sn1, inAmount=amt)
        cdtTrfTxInf["cdtrAgt"]["finInstnId"]["clrSysMmbId"] = RMNData.ncc_agents[recCurrency]["finInstnId"]["clrSysMmbId"]
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    # pro testcase

    def waitSN2ReceiveRCCTInProd(self, limit_num=5):
        if RMNData.env != "prod":
            return
        from roxe_libs.DBClient import Mysql
        db_inf = RMNData._yaml_conf["notify_cfg"]
        prod_mock_db = Mysql(db_inf["mysql_host"], 3306, db_inf["user"], db_inf["password"], db_inf["db"], True)
        res_notify = []
        try:
            prod_mock_db.connect_database()
            sql = f"select * from res_info where header like '%msgId\", \"1%' order by create_at desc limit {limit_num};"
            infos = prod_mock_db.exec_sql_query(sql)
            for i, notify in enumerate(infos):
                # print(notify)
                notify_info = json.loads(notify["response"])
                de_info = ApiUtils.aes_decrypt(
                    notify_info["resource"]["ciphertext"], notify_info["resource"]["nonce"],
                    notify_info["resource"]["associatedData"], RMNData.sec_key
                )
                res_notify.append(json.loads(de_info))
                self.client.logger.info(json.dumps(de_info))
        except Exception:
            pass
        finally:
            prod_mock_db.disconnect_database()
            return res_notify

    @unittest.skipIf(RMNData.env != "prod", "生产测试用例，手动执行")
    def test_324_getExchangeRate_sameCurrency(self):
        """
        查询汇率，同币种
        """
        sender = RMNData.sn_usd_us_a
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        rate_res, req_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", "12.34", "PHP")
        self.checkExchangeRate(rate_res, req_msg)

        ts_headers = self.client.make_header(sender, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        rate_res, req_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", None, "USD", "12.6")
        self.checkExchangeRate(rate_res, req_msg)

    @unittest.skipIf(RMNData.env != "prod", "生产测试用例，手动执行")
    def test_325_getRouterList_senderIsSN_sameCurrency_snRoxeId(self):
        # sender = RMNData.sn_usd_us_a  # pro 节点数据
        # sn2 = RMNData.sn_usd_us_b  # pro 节点数据
        sender = RMNData.sn_usd_us_a  # pro 节点数据
        sn2 = RMNData.sn_usd_us_b  # pro 节点数据
        # sn2 = RMNData.sn_krw_kr  # pro test GME

        recCurrency = "USD"

        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(sn2, "SN")
        msg = self.client.make_RRLQ_information("USD", recCurrency, "100", cdtrAgt=agent_info, cd="C2C")
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.client.checkCodeAndMessage(router_list)

    @unittest.skipIf(RMNData.env != "prod", "生产测试用例，手动执行")
    def test_326_sn_sn_cdtrAgtGiveSNRoxeId_sameCurrency_step1(self):
        sn1 = RMNData.sn_usd_us_a  # pro 节点数据
        sn2 = RMNData.sn_usd_us_b  # pro 节点数据
        # rmn_id = "risn2roxe51"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = 3.4
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amt)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)
        cdtTrfTxInf["splmtryData"]["addenda"] = {"testKey": None, "testKey2": "223"}
        inner_node = True if sn2 in RMNData.channel_nodes else False
        msg_id, tx_msg, end2end_id, rmn_tx_id, st_msg = self.client.transactionFlow_sn_sn_not_check_db_1(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=inner_node)
        self.client.logger.warning("msg_id={}".format(msg_id))
        self.client.logger.warning("tx_msg={}".format(tx_msg))
        self.client.logger.warning("end2end_id={}".format(end2end_id))
        self.client.logger.warning("rmn_tx_id={}".format(rmn_tx_id))
        self.client.logger.warning("st_msg={}".format(st_msg))
        time.sleep(90)
        tx2_msg = self.waitSN2ReceiveRCCTInProd(5)[0]
        sn2_tx_msg_id = tx2_msg["grpHdr"]["msgId"]
        self.client.transactionFlow_sn_sn_not_check_db_2(
            sn1, sn2, RMNData.rmn_id, RMNData.api_key, RMNData.sec_key, msg_id, tx_msg, end2end_id,
            tx2_msg, rmn_tx_id, sn2_tx_msg_id
        )

    @unittest.skipIf(RMNData.env != "prod", "生产测试用例，手动执行")
    def test_327_sn_sn_cdtrAgtGiveSNRoxeId_sameCurrency_step2(self):
        sn1 = RMNData.sn_usd_us_a  # pro 节点数据
        sn2 = RMNData.sn_usd_us_b  # pro 节点数据
        rmn_id = "risn2roxe51"
        api_key = RMNData.api_key
        sec_key = RMNData.sec_key
        msg_id = "1202211221669088749611298"
        tx_msg = {'version': '001', 'msgType': 'RCCT', 'grpHdr': {'msgId': '1202211221669088749611298', 'instgAgt': 'risnsmkg2t31', 'instdAgt': 'risn2roxe51', 'creDtTm': '2022-11-22T11:45:49', 'sttlmInf': {'sttlmMtd': 'CLRG', 'clrSysCd': 'ROXE'}}, 'cdtTrfTxInf': {'instdAmt': {'ccy': 'USD', 'amt': '3.4'}, 'intrBkSttlmAmt': {'ccy': 'USD', 'amt': '3.3'}, 'intrBkSttlmDt': '2022-11-22', 'pmtId': {'endToEndId': 'test_rmn_1669088749611', 'txId': 'test_rmn_1669088749611'}, 'dbtr': {'nm': 'Jethro Test 001', 'pstlAdr': {'pstCd': '123456', 'twnNm': 'helel', 'twnLctnNm': 'Olmpic', 'dstrctNm': 'god street', 'ctrySubDvsn': 'tai h', 'ctry': 'US', 'adrLine': 'abcd 1234 abcd XXXX'}, 'prvtId': {'dtAndPlcOfBirth': {'ctryOfBirth': 'US', 'prvcOfBirth': 'New York', 'cityOfBirth': 'New York City', 'birthDt': '1960-05-24'}, 'othr': {'id': '123412341234', 'prtry': 'Driving License', 'issr': 'US'}}, 'ctctDtls': {'phneNb': '1 983384893'}}, 'dbtrAcct': {'acctId': '123456789012', 'nm': 'Jethro Lee', 'ccy': 'USD'}, 'dbtrAgt': {'finInstnId': {'othr': {'id': 'risnsmkg2t31', 'schmeCd': 'ROXE', 'issr': 'SN'}, 'nm': 'china bank'}}, 'cdtr': {'nm': 'Jethro Test 001', 'pstlAdr': {'pstCd': '123456', 'twnNm': 'helel', 'twnLctnNm': 'Olmpic', 'dstrctNm': 'god street', 'ctrySubDvsn': 'tai h', 'ctry': 'US', 'adrLine': 'abcd 1234 abcd XXXX'}, 'prvtId': {'dtAndPlcOfBirth': {'ctryOfBirth': 'US', 'prvcOfBirth': 'New York', 'cityOfBirth': 'New York City', 'birthDt': '1960-05-24'}, 'othr': {'id': '123412341234', 'prtry': 'Driving License', 'issr': 'US'}}, 'ctctDtls': {'phneNb': '1 983384893'}}, 'cdtrAcct': {'nm': 'Li XX', 'ccy': 'USD', 'acctId': '987654321'}, 'cdtrAgt': {'finInstnId': {'othr': {'id': 'risnsmkg2t32', 'schmeCd': 'ROXE', 'issr': 'SN'}, 'nm': 'china bank'}}, 'purp': {'cd': 'cod1', 'desc': 'transfer my money'}, 'rltnShp': {'cd': '457', 'desc': 'hellos'}, 'chrgsInf': [{'agt': {'id': 'risnsmkg2t31', 'schmeCd': 'ROXE'}, 'sndFeeAmt': {'amt': '0.1', 'ccy': 'USD'}}], 'splmtryData': {'envlp': {'cnts': {'sndrAmt': '3.4', 'sndrCcy': 'USD', 'rcvrCcy': 'USD'}}, 'rmrk': 'remark 1669088749.611298', 'addenda': {'testKey': None, 'testKey2': '223'}}}, 'msgId': '1202211221669088749611298'}
        end2end_id = "test_rmn_1669088749611"
        rmn_tx_id = "580831393261551616"
        # st_msg = {'version': '001', 'msgType': 'RCSR', 'grpHdr': {'msgId': '1202208181660794783222880', 'instgAgt': 'risnsmkg2t31', 'instdAgt': 'risn2roxe51', 'creDtTm': '2022-08-18T11:53:03', 'sttlmInf': {'sttlmMtd': 'CLRG', 'clrSysCd': 'ROXE'}}, 'cdtTrfTxInf': {'intrBkSttlmAmt': {'ccy': 'USD', 'amt': '5.5'}, 'intrBkSttlmDt': '2022-08-18', 'pmtId': {'endToEndId': 'test_rmn_1660794783223', 'txId': 'test_rmn_1660794783223'}, 'dbtr': {'finInstnId': {'othr': {'id': 'risnsmkg2t31', 'schmeCd': 'ROXE', 'issr': 'SN'}, 'nm': 'china bank'}}, 'cdtr': {'finInstnId': {'othr': {'id': 'risn2roxe51', 'schmeCd': 'ROXE', 'issr': 'VN'}, 'nm': 'china bank'}}, 'cdtrAcct': {'nm': 'Li XX', 'ccy': 'USD', 'acctId': '987654321'}, 'rmtInf': {'orgnlMsgID': '1202208181660794758033450', 'orgnlMsgTp': 'RCCT', 'instgAgt': 'risnsmkg2t31'}, 'splmtryData': {'envlp': {'ustrd': {'cdtDbtInd': 'CRDT'}}}, 'dbtrAcct': {'acctId': '123456789012', 'nm': 'Jethro Lee', 'ccy': 'USD'}}}
        sn2_tx_msg_id = "1202211229200099235405618"
        tx2_msg = "{\"version\":\"001\",\"msgType\":\"RCCT\",\"grpHdr\":{\"msgId\":\"1202210313679027261817640\",\"instgAgt\":\"risn2roxe51\",\"instdAgt\":\"risnsmkg2t32\",\"creDtTm\":\"2022-10-31T10:26:42\",\"sttlmInf\":{\"clrSysCd\":\"ROXE\",\"sttlmMtd\":\"CLRG\"}},\"cdtTrfTxInf\":{\"instdAmt\":{\"amt\":\"3.4\",\"ccy\":\"USD\"},\"intrBkSttlmAmt\":{\"amt\":\"1.80\",\"ccy\":\"USD\"},\"intrBkSttlmDt\":\"2022-10-31\",\"pmtId\":{\"endToEndId\":\"test_rmn_1667211826198\",\"txId\":\"572958994012831744\"},\"chrgsInf\":[{\"agt\":{\"id\":\"risnsmkg2t31\",\"schmeCd\":\"ROXE\"},\"sndFeeAmt\":{\"amt\":\"0.10\",\"ccy\":\"USD\"}},{\"agt\":{\"id\":\"risn2roxe51\",\"schmeCd\":\"ROXE\"},\"svcFeeAmt\":{\"amt\":\"1.50\",\"ccy\":\"USD\"}}],\"dbtr\":{\"nm\":\"Jethro Test 001\",\"prvtId\":{\"dtAndPlcOfBirth\":{\"birthDt\":\"1960-05-24\",\"cityOfBirth\":\"New York City\",\"ctryOfBirth\":\"US\",\"prvcOfBirth\":\"New York\"},\"othr\":{\"id\":\"123412341234\",\"issr\":\"US\",\"prtry\":\"driver license\"}},\"pstlAdr\":{\"adrLine\":\"abcd 1234 abcd XXXX\",\"ctry\":\"US\",\"ctrySubDvsn\":\"tai h\",\"dstrctNm\":\"god street\",\"pstCd\":\"123456\",\"twnLctnNm\":\"Olmpic\",\"twnNm\":\"helel\"}},\"dbtrAcct\":{\"acctId\":\"123456789012\",\"ccy\":\"USD\",\"nm\":\"Jethro Lee\"},\"dbtrAgt\":{\"finInstnId\":{\"nm\":\"RISN Production Test 01\",\"othr\":{\"id\":\"risnsmkg2t31\",\"issr\":\"SN\",\"schmeCd\":\"ROXE\"}}},\"cdtrAgt\":{\"finInstnId\":{\"nm\":\"RISN Production Test 02\",\"othr\":{\"id\":\"risnsmkg2t32\",\"issr\":\"SN\",\"schmeCd\":\"ROXE\"}}},\"cdtr\":{\"nm\":\"Jethro Test 001\",\"prvtId\":{\"dtAndPlcOfBirth\":{\"birthDt\":\"1960-05-24\",\"cityOfBirth\":\"New York City\",\"ctryOfBirth\":\"US\",\"prvcOfBirth\":\"New York\"},\"othr\":{\"id\":\"123412341234\",\"issr\":\"US\",\"prtry\":\"driver license\"}},\"pstlAdr\":{\"adrLine\":\"abcd 1234 abcd XXXX\",\"ctry\":\"US\",\"ctrySubDvsn\":\"tai h\",\"dstrctNm\":\"god street\",\"pstCd\":\"123456\",\"twnLctnNm\":\"Olmpic\",\"twnNm\":\"helel\"}},\"cdtrAcct\":{\"acctId\":\"987654321\",\"ccy\":\"USD\",\"nm\":\"Li XX\"},\"purp\":{\"cd\":\"cod1\",\"desc\":\"transfer my money\"},\"rltnShp\":{\"cd\":\"457\",\"desc\":\"hellos\"},\"splmtryData\":{\"rmrk\":\"remark 1667211826.198612\",\"envlp\":{\"cnts\":{\"sndrCcy\":\"USD\",\"sndrAmt\":\"3.4\",\"rcvrCcy\":\"USD\"}},\"addenda\":{\"testKey2\":\"223\"}}}}"
        tx2_msg = json.loads(tx2_msg)
        self.client.transactionFlow_sn_sn_not_check_db_2(sn1, sn2, rmn_id, api_key, sec_key, msg_id, tx_msg, end2end_id,
                                                         tx2_msg, rmn_tx_id, sn2_tx_msg_id)

    @unittest.skip("生产测试用例，手动执行")
    def test_328_return_FullySettled_sn_sn_step1(self):
        sn1 = RMNData.sn_usd_us_a  # pro 节点数据
        sn2 = RMNData.sn_usd_us_b  # pro 节点数据
        # sn1 = RMNData.sn_usd_us
        # sn2 = RMNData.sn_usd_gb
        sn2_tx_info = {
            "version": "001",
            "msgType": "RCCT",
            "grpHdr": {
                "msgId": "1202206065498195022661790",
                "instgAgt": "risn2roxe51",
                "instdAgt": "risnsmkg2t32",
                "creDtTm": "2022-06-06T09:27:20",
                "sttlmInf": {
                    "clrSysCd": "ROXE",
                    "sttlmMtd": "CLRG"
                }
            },
            "cdtTrfTxInf": {
                "instdAmt": {
                    "amt": "5.5",
                    "ccy": "USD"
                },
                "intrBkSttlmAmt": {
                    "amt": "5.4",
                    "ccy": "USD"
                },
                "intrBkSttlmDt": "2022-06-06",
                "pmtId": {
                    "endToEndId": "test_rmn_1654506433049",
                    "txId": "519668703558631424"
                },
                "chrgsInf": [{
                    "agt": {
                        "id": "risnsmkg2t31",
                        "schmeCd": "ROXE"
                    },
                    "sndFeeAmt": {
                        "amt": "0.10",
                        "ccy": "USD"
                    }
                }],
                "dbtr": {
                    "nm": "Jethro Test 001",
                    "prvtId": {
                        "dtAndPlcOfBirth": {
                            "cityOfBirth": "New York",
                            "ctryOfBirth": "US"
                        },
                        "othr": {
                            "id": "123412341234",
                            "issr": "us.aba",
                            "prtry": "driver license"
                        }
                    },
                    "pstlAdr": {
                        "adrLine": "abcd 1234 abcd XXXX",
                        "ctry": "US",
                        "ctrySubDvsn": "tai h",
                        "dstrctNm": "god street",
                        "pstCd": "123456",
                        "twnLctnNm": "Olmpic",
                        "twnNm": "helel"
                    }
                },
                "dbtrAcct": {
                    "acctId": "123456789012",
                    "ccy": "USD",
                    "nm": "Jethro Lee",
                    "tp": "bank"
                },
                "dbtrAgt": {
                    "finInstnId": {
                        "nm": "RISN Production Test 01",
                        "othr": {
                            "id": "risnsmkg2t31",
                            "issr": "SN",
                            "schmeCd": "ROXE"
                        }
                    }
                },
                "cdtrAgt": {
                    "finInstnId": {
                        "nm": "RISN Production Test 02",
                        "othr": {
                            "id": "risnsmkg2t32",
                            "issr": "SN",
                            "schmeCd": "ROXE"
                        }
                    }
                },
                "cdtr": {
                    "nm": "Jethro Test 001",
                    "prvtId": {
                        "dtAndPlcOfBirth": {
                            "birthDt": "1960-05-24",
                            "cityOfBirth": "New York City",
                            "ctryOfBirth": "US",
                            "prvcOfBirth": "New York"
                        },
                        "othr": {
                            "id": "123412341234",
                            "issr": "us.aba",
                            "prtry": "driver license"
                        }
                    },
                    "pstlAdr": {
                        "adrLine": "abcd 1234 abcd XXXX",
                        "ctry": "US",
                        "ctrySubDvsn": "tai h",
                        "dstrctNm": "god street",
                        "pstCd": "123456",
                        "twnLctnNm": "Olmpic",
                        "twnNm": "helel"
                    }
                },
                "cdtrAcct": {
                    "acctId": "987654321",
                    "ccy": "USD",
                    "nm": "Li XX",
                    "tp": "eWallet"
                },
                "purp": {
                    "cd": "cod1",
                    "desc": "transfer my money"
                },
                "rltnShp": {
                    "cd": "457",
                    "desc": "hellos"
                },
                "splmtryData": {
                    "rmrk": "remark 1655891050.7513237",
                    "envlp": {
                        "cnts": {
                            "sndrCcy": "USD",
                            "sndrAmt": "6.5",
                            "rcvrCcy": "USD"
                        }
                    },
                    "addenda": {
                        "tel": "!23123123xx"
                    }
                }
            }
        }
        # sn2_fee = 0.50
        # sn2_return_fee = 2.00
        # sn1_return_fee = 1.00
        sn2_fee = 0.22
        sn2_return_fee = 0.10
        # sn1_return_fee = 0.15
        return_msg = self.client.make_RPRN_information(sn2, "USD", "USD", sn2_tx_info, sn2_fee, sn2_return_fee)
        msg_id, tx_msg, rmn_tx_id, sn1_st_msg_id = self.client.returnFlow_sn_sn_not_check_db_1(sn2, sn1, return_msg)
        self.client.logger.warning("msg_id={}, rmn_tx_id={}, sn1_st_msg_id={}".format(msg_id, rmn_tx_id, sn1_st_msg_id))

    @unittest.skip("生产测试用例，手动执行")
    def test_329_return_FullySettled_sn_sn_step2(self):
        sn1 = RMNData.sn_usd_us_a  # pro 节点数据
        sn2 = RMNData.sn_usd_us_b  # pro 节点数据
        # sn1 = RMNData.sn_usd_us
        # sn2 = RMNData.sn_usd_gb
        # rmn_id = "risn2roxe51"
        # api_key = RMNData.api_key
        # sec_key = RMNData.sec_key
        msg_id = "1202206221655893475995981"
        rmn_tx_id = "525486383939190784"
        r_sn2_tx_info = {
            "version": "001",
            "msgType": "RPRN",
            "grpHdr": {
                "msgId": "1202206225169670314535460",
                "instgAgt": "risn2roxe51",
                "instdAgt": "risnsmkg2t31",
                "creDtTm": "2022-06-22T10:26:52",
                "sttlmInf": {
                    "clrSysCd": "ROXE",
                    "sttlmMtd": "CLRG"
                }
            },
            "txInf": {
                "rtrId": "525486383939190784",
                "orgnlGrpInf": {
                    "orgnlMsgId": "1202206221655891050752322",
                    "orgnlMsgNmId": "RCCT"
                },
                "orgnlTxId": "test_rmn_1655891050751",
                "orgnlEndToEndId": "test_rmn_1655891050751",
                "orgnlIntrBkSttlmAmt": {
                    "amt": "6.4",
                    "ccy": "USD"
                },
                "rtrdIntrBkSttlmAmt": {
                    "amt": "6.08",
                    "ccy": "USD"
                },
                "rtrdInstdAmt": {
                    "amt": "6.18",
                    "ccy": "USD"
                },
                "chrgsInf": [{
                    "agt": {
                        "id": "risnsmkg2t32",
                        "schmeCd": "ROXE"
                    },
                    "sndFeeAmt": {
                        "amt": "0.10",
                        "ccy": "USD"
                    }
                }],
                "instgAgt": "risnsmkg2t31",
                "instdAgt": "risn2roxe51",
                "rtrRsnInf": {
                    "rsn": {
                        "cd": "1234",
                        "prtry": "return money"
                    }
                },
                "rtrChain": {
                    "dbtr": {
                        "nm": "Jethro Test 001",
                        "prvtId": {
                            "dtAndPlcOfBirth": {
                                "birthDt": "1960-05-24",
                                "cityOfBirth": "New York City",
                                "ctryOfBirth": "US",
                                "prvcOfBirth": "New York"
                            },
                            "othr": {
                                "id": "123412341234",
                                "issr": "us.aba",
                                "prtry": "driver license"
                            }
                        },
                        "pstlAdr": {
                            "adrLine": "abcd 1234 abcd XXXX",
                            "ctry": "US",
                            "ctrySubDvsn": "tai h",
                            "dstrctNm": "god street",
                            "pstCd": "123456",
                            "twnLctnNm": "Olmpic",
                            "twnNm": "helel"
                        }
                    },
                    "dbtrAcct": {
                        "acctId": "987654321",
                        "ccy": "USD",
                        "nm": "Li XX",
                        "tp": "eWallet"
                    },
                    "dbtrAgt": {
                        "finInstnId": {
                            "nm": "RISN Production Test 02",
                            "othr": {
                                "id": "risnsmkg2t32",
                                "issr": "SN",
                                "schmeCd": "ROXE"
                            }
                        }
                    },
                    "cdtrAgt": {
                        "finInstnId": {
                            "nm": "RISN Production Test 01",
                            "othr": {
                                "id": "risnsmkg2t31",
                                "issr": "SN",
                                "schmeCd": "ROXE"
                            }
                        }
                    },
                    "cdtr": {
                        "nm": "Jethro Test 001",
                        "prvtId": {
                            "dtAndPlcOfBirth": {
                                "birthDt": "1960-05-24",
                                "cityOfBirth": "New York City",
                                "ctryOfBirth": "US",
                                "prvcOfBirth": "New York"
                            },
                            "othr": {
                                "id": "123412341234",
                                "issr": "us.aba",
                                "prtry": "driver license"
                            }
                        },
                        "pstlAdr": {
                            "adrLine": "abcd 1234 abcd XXXX",
                            "ctry": "US",
                            "ctrySubDvsn": "tai h",
                            "dstrctNm": "god street",
                            "pstCd": "123456",
                            "twnLctnNm": "Olmpic",
                            "twnNm": "helel"
                        }
                    },
                    "cdtrAcct": {
                        "acctId": "123456789012",
                        "ccy": "USD",
                        "nm": "Jethro Lee",
                        "tp": "bank"
                    }
                },
                "splmtryData": {
                    "envlp": {
                        "cnts": {
                            "sndrCcy": "USD",
                            "sndrAmt": "6.18",
                            "rcvrCcy": "USD"
                        }
                    }
                }
            }
        }
        sn1_st_msg_id = "1202206221655893507943138"
        self.client.returnFlow_sn_sn_not_check_db_2(sn2, sn1, msg_id, r_sn2_tx_info, rmn_tx_id, sn1_st_msg_id, self)

    @unittest.skipUnless(RMNData.is_check_db, "从rts下单需修改数据库使模拟的sn1订单完成")
    def test_330_sn_sn_dbtrAgtGiveSNRoxeId_cdtrAgtGiveSNRoxeId_sameCurrency(self):
        sn1 = "hpuuz5siv3tr"
        sn2 = RMNData.sn_usd_gb
        # amt = ApiUtils.randAmount(50, 2, 10)
        amt = 29.36
        rts_router, _ = self.rts_client.getRouterList("", "USD", "", "USD", amt, "", sn1, sn2, )
        sn1_fee = rts_router["data"]["roxeRouters"][0]["roxeNodes"][0]["sendFee"]
        sn2_fee = rts_router["data"]["roxeRouters"][0]["roxeNodes"][1]["deliveryFee"]

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf = self.client.make_RCCT_information(
            "USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId_b, creditor_agent, sn1_fee, sn1, inAmount=amt
        )
        self.client.logger.info(json.dumps(cdtTrfTxInf))

        rmn_tx_id = self.client.submitRTSOrder(sn1, self.rts_client, cdtTrfTxInf, self.rpc_client, amt, sn1_fee)
        self.client.transactionFlow_sn_sn_sn1IsRTSNode(rmn_tx_id, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

    @unittest.skipUnless(RMNData.is_check_db, "从rts下单需修改数据库使模拟的sn1订单完成")
    def test_331_sn_sn_pn_dbtrAgtGiveSNRoxeId_cdtrAgtGivePNRoxeId_sameCurrency(self):
        # pn1 = RMNData.pn_usd_us
        sn1 = "hpuuz5siv3tr"
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = ApiUtils.randAmount(30, 2, 10)
        rts_router, _ = self.rts_client.getRouterList("", "USD", "", "USD", amt, "", sn1, pn2, )
        sn1_fee = rts_router["data"]["roxeRouters"][0]["roxeNodes"][0]["sendFee"]
        sn2_fee = rts_router["data"]["roxeRouters"][0]["roxeNodes"][1]["deliveryFee"]

        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId_b,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)
        self.client.logger.info(json.dumps(cdtTrfTxInf))
        rmn_tx_id = self.client.submitRTSOrder(sn1, self.rts_client, cdtTrfTxInf, self.rpc_client, amt, sn1_fee)
        self.client.transactionFlow_sn_sn_pn_sn1IsRTSNode(
            rmn_tx_id, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self
        )

    @unittest.skip("PNS未独立出来暂时跳过")
    def test_332_pn_sn_sn_dbtrAgtGivePNRoxeId_cdtrAgtGiveSNRoxeId_sameCurrency(self):
        pn1 = "pnuzj1hpyxxx"
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        # pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 10)
        rts_router, _ = self.rts_client.getRouterList("", "USD", "", "USD", amt, "", pn1, sn2, )
        pn1_fee = rts_router["data"]["roxeRouters"][0]["roxeNodes"][0]["sendFee"]
        sn1_fee = rts_router["data"]["roxeRouters"][0]["roxeNodes"][1]["sendFee"]
        sn2_fee = rts_router["data"]["roxeRouters"][0]["roxeNodes"][2]["deliveryFee"]

        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId_b,
                                                        creditor_agent, pn1_fee, pn1, inAmount=amt)
        self.client.logger.info(json.dumps(cdtTrfTxInf))
        rmn_tx_id = self.client.submitRTSOrder(pn1, self.rts_client, cdtTrfTxInf, self.rpc_client, amt, pn1_fee)
        self.client.transactionFlow_pn_sn_sn_pn1IsRTSNode(
            rmn_tx_id, pn1, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self
        )

    @unittest.skip("PNS未独立出来暂时跳过")
    def test_333_pn_sn_sn_pn_dbtrAgtGivePNRoxeId_cdtrAgtGivePNRoxeId_sameCurrency(self):
        pn1 = "pnuzj1hpyxxx"
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        pn2 = RMNData.pn_usd_gb
        debtor_agent = self.client.make_roxe_agent(pn1, "PN")
        creditor_agent = self.client.make_roxe_agent(pn2, "PN")
        amt = f"{ApiUtils.randAmount(15, 2, 10):.2f}"
        rts_router, _ = self.rts_client.getRouterList("", "USD", "", "USD", amt, "", pn1, pn2, )
        pn1_fee = rts_router["data"]["roxeRouters"][0]["roxeNodes"][0]["sendFee"]
        sn1_fee = rts_router["data"]["roxeRouters"][0]["roxeNodes"][1]["sendFee"]
        sn2_fee = rts_router["data"]["roxeRouters"][0]["roxeNodes"][2]["deliveryFee"]
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId_b,
                                                        creditor_agent, pn1_fee, pn1)
        rmn_tx_id = self.client.submitRTSOrder(pn1, self.rts_client, cdtTrfTxInf, self.rpc_client, amt, pn1_fee)
        self.client.transactionFlow_pn_sn_sn_pn_pn1IsRTSNode(
            rmn_tx_id, pn1, sn1, sn2, pn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self
        )

    @unittest.skipUnless(RMNData.is_check_db, "从rts下单需修改数据库使模拟的sn1订单完成")
    def test_334_sn_sn_dbtrAgtGiveSNRoxeId_cdtrAgtGiveSNRoxeId_orgId(self):
        # pn1 = RMNData.pn_usd_us
        sn1 = "hpuuz5siv3tr"
        sn2 = RMNData.sn_usd_gb
        # pn2 = RMNData.pn_usd_gb
        amt = ApiUtils.randAmount(10, 2, 5)
        rts_router, _ = self.rts_client.getRouterList("", "USD", "", "USD", amt, "", sn1, sn2, )
        sn1_fee = rts_router["data"]["roxeRouters"][0]["roxeNodes"][0]["sendFee"]
        sn2_fee = rts_router["data"]["roxeRouters"][0]["roxeNodes"][1]["deliveryFee"]

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf = self.client.make_RCCT_information(
            "USD", "USD", RMNData.orgId, debtor_agent, RMNData.orgId_b, creditor_agent, sn1_fee, sn1, inAmount=amt
        )
        self.client.logger.info(json.dumps(cdtTrfTxInf))

        rmn_tx_id = self.client.submitRTSOrder(sn1, self.rts_client, cdtTrfTxInf, self.rpc_client, amt-sn1_fee)
        self.client.transactionFlow_sn_sn_sn1IsRTSNode(rmn_tx_id, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

    @unittest.skipUnless(RMNData.is_check_db, "从rts下单需修改数据库使模拟的sn1订单完成")
    def test_335_sn_sn_dbtrAgtGiveSNRoxeId_cdtrAgtGiveSNRoxeId_bic(self):
        # pn1 = RMNData.pn_usd_us
        sn1 = "hpuuz5siv3tr"
        sn2 = RMNData.sn_usd_gb
        # pn2 = RMNData.pn_usd_gb
        amt = ApiUtils.randAmount(10, 2, 5)
        rts_router, _ = self.rts_client.getRouterList("", "USD", "", "USD", amt, "", sn1, sn2, )
        sn1_fee = rts_router["data"]["roxeRouters"][0]["roxeNodes"][0]["sendFee"]
        sn2_fee = rts_router["data"]["roxeRouters"][0]["roxeNodes"][1]["deliveryFee"]

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.bic_agents["GBP"]
        cdtTrfTxInf = self.client.make_RCCT_information(
            "USD", "USD", RMNData.orgId, debtor_agent, RMNData.orgId_b, creditor_agent, sn1_fee, sn1, inAmount=amt
        )
        self.client.logger.info(json.dumps(cdtTrfTxInf))

        rmn_tx_id = self.client.submitRTSOrder(sn1, self.rts_client, cdtTrfTxInf, self.rpc_client, amt - sn1_fee)
        self.client.transactionFlow_sn_sn_sn1IsRTSNode(rmn_tx_id, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

    @unittest.skipUnless(RMNData.is_check_db, "从rts下单需修改数据库使模拟的sn1订单完成")
    def test_336_sn_sn_dbtrAgtGiveSNRoxeId_cdtrAgtGiveSNRoxeId_ncc(self):
        # pn1 = RMNData.pn_usd_us
        sn1 = "hpuuz5siv3tr"
        sn2 = RMNData.sn_usd_gb
        # pn2 = RMNData.pn_usd_gb
        amt = ApiUtils.randAmount(10, 2, 5)
        rts_router, _ = self.rts_client.getRouterList("", "USD", "", "USD", amt, "", sn1, sn2, )
        sn1_fee = rts_router["data"]["roxeRouters"][0]["roxeNodes"][0]["sendFee"]
        sn2_fee = rts_router["data"]["roxeRouters"][0]["roxeNodes"][1]["deliveryFee"]

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        cdtTrfTxInf = self.client.make_RCCT_information(
            "USD", "USD", RMNData.prvtId, debtor_agent, RMNData.orgId_b, creditor_agent, sn1_fee, sn1, inAmount=amt
        )
        self.client.logger.info(json.dumps(cdtTrfTxInf))

        rmn_tx_id = self.client.submitRTSOrder(sn1, self.rts_client, cdtTrfTxInf, self.rpc_client, amt - sn1_fee)
        self.client.transactionFlow_sn_sn_sn1IsRTSNode(rmn_tx_id, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

    @unittest.skipUnless(RMNData.is_check_db, "从rts下单需修改数据库使模拟的sn1订单完成")
    def test_337_sn_sn_dbtrAgtGiveSNRoxeId_cdtrAgtGiveSNRoxeId_branch(self):
        # pn1 = RMNData.pn_usd_us
        sn1 = "hpuuz5siv3tr"
        sn2 = RMNData.sn_usd_gb
        # pn2 = RMNData.pn_usd_gb
        amt = ApiUtils.randAmount(10, 2, 5)
        rts_router, _ = self.rts_client.getRouterList("", "USD", "", "USD", amt, "", sn1, sn2, )
        sn1_fee = rts_router["data"]["roxeRouters"][0]["roxeNodes"][0]["sendFee"]
        sn2_fee = rts_router["data"]["roxeRouters"][0]["roxeNodes"][1]["deliveryFee"]

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = RMNData.ncc_agents["GBP"]
        creditor_agent["brnchId"] = {"nm": "test123", "id": "he123d"}
        cdtTrfTxInf = self.client.make_RCCT_information(
            "USD", "USD", RMNData.prvtId, debtor_agent, RMNData.orgId_b, creditor_agent, sn1_fee, sn1, inAmount=amt
        )
        self.client.logger.info(json.dumps(cdtTrfTxInf))

        rmn_tx_id = self.client.submitRTSOrder(sn1, self.rts_client, cdtTrfTxInf, self.rpc_client, amt - sn1_fee)
        self.client.transactionFlow_sn_sn_sn1IsRTSNode(rmn_tx_id, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

    # ewallet

    def test_340_sn_sn_cdtrAgtGiveSNRoxeId_rpp_inAmount_baseCurrency_bankToEWallet(self):
        sn1 = RMNData.sn_usd_us
        # sn2 = RMNData.sn_php_ph
        # sn2 = "idlzjsbeza4m"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": "rich bank"}}
        cdtrAcct = {"schmeNm": {"prtry": "PH"}, "issr": "GCASH", "acctId": "09612803885", "ccy": "PHP"}
        # amt = ApiUtils.randAmount(10, 2, 3)
        amt = 2.9
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "USD", "PHP", cdtrAcct=cdtrAcct, tp='EWALLET', amount=amt)

        cdtTrfTxInf = self.client.make_RCCT_information(
            "USD", "PHP", RMNData.prvtId, debtor_agent, RMNData.prvtId_b, creditor_agent, sn1_fee, sn1,
            cdtrAcct=cdtrAcct, inAmount=amt
        )
        cdtTrfTxInf["pmtTpInf"] = {"lclInstrm": {"cd": "EWALLET"}}
        cdtTrfTxInf["cdtr"]["nm"] = "Sean Warwick Dela Cruz"
        cdtTrfTxInf["cdtr"]["pstlAdr"]["ctry"] = "PH"
        cdtTrfTxInf["dbtr"]["prvtId"]["othr"]["prtry"] = "DRIVER_LICENSE"
        cdtTrfTxInf["splmtryData"]["addenda"]["senderSourceOfFund"] = "bank account"
        cdtTrfTxInf["splmtryData"]["addenda"]["receiverWalletCode"] = "GCASH"

        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", cdtTrfTxInf["intrBkSttlmAmt"]["amt"], "PHP")
        self.client.checkCodeAndMessage(rate_info)

        self.client.transactionFlow_sn_sn(
            sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=True,
            isRPP=True, rateInfo=rate_info, chg_fees=["USD"]
        )

    def test_341_sn_sn_cdtrAgtGiveSNRoxeId_rpp_inAmount_baseCurrency_bank(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        # sn2 = "idlzjsbeza4m"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, tp='BANK')
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId_b, creditor_agent, sn1_fee, sn1)
        cdtTrfTxInf["pmtTpInf"] = {"lclInstrm": {"cd": "BANK"}}
        # cdtTrfTxInf["cdtrAcct"]["schmeNm"] = {"prtry": "GB"}
        # cdtTrfTxInf["cdtrAcct"]["issr"] = "ALIPAY"

        cdtTrfTxInf["dbtr"]["prvtId"]["othr"]["prtry"] = "DRIVER_LICENSE"
        cdtTrfTxInf["splmtryData"]["addenda"]["senderSourceOfFund"] = "bank account"
        # cdtTrfTxInf["splmtryData"]["addenda"]["receiverWalletCode"] = "ALIPAY"

        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", cdtTrfTxInf["intrBkSttlmAmt"]["amt"], "PHP")
        self.client.checkCodeAndMessage(rate_info)

        # in_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(
            sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=False,
            isRPP=False, rateInfo=rate_info, chg_fees=["USD"]
        )

    def test_342_sn_sn_cdtrAgtGiveSNRoxeId_rpp_inAmount_baseCurrency_cdtrIntrmyAgtGiveSN(self):
        sn1 = RMNData.rpp_node_usd2php
        # sn2 = RMNData.sn_php_ph
        # sn2 = "idlzjsbeza4m"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": "rich bank"}}
        cdtrAcct = {"schmeNm": {"prtry": "PH"}, "issr": "GCASH", "acctId": "09612803885", "ccy": "PHP"}
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "USD", "PHP", cdtrAcct=cdtrAcct, tp='EWALLET')
        amt = ApiUtils.randAmount(5, 2, 2)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "PHP", RMNData.prvtId, debtor_agent, RMNData.prvtId_b, creditor_agent, sn1_fee, sn1, cdtrAcct=cdtrAcct, inAmount=amt)
        cdtTrfTxInf["pmtTpInf"] = {"lclInstrm": {"cd": "EWALLET"}}
        cdtTrfTxInf["cdtr"]["nm"] = "Sean Warwick Dela Cruz"
        cdtTrfTxInf["cdtr"]["pstlAdr"]["ctry"] = "PH"
        cdtTrfTxInf["dbtr"]["prvtId"]["othr"]["prtry"] = "DRIVER_LICENSE"
        cdtTrfTxInf["splmtryData"]["addenda"]["senderSourceOfFund"] = "bank account"
        cdtTrfTxInf["splmtryData"]["addenda"]["receiverWalletCode"] = "GCASH"
        cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")

        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", cdtTrfTxInf["intrBkSttlmAmt"]["amt"], "PHP")
        self.client.checkCodeAndMessage(rate_info)
        # return
        self.client.transactionFlow_sn_sn(
            sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=True,
            isRPP=True, rateInfo=rate_info, chg_fees=["USD"]
        )

    def test_343_sn_sn_cdtrAgtGiveSNRoxeId_rpp_inAmount_baseCurrency_eWalletToEWallet(self):
        sn1 = RMNData.rpp_node_usd2php
        # sn2 = RMNData.sn_php_ph
        # sn2 = "idlzjsbeza4m"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": "rich bank"}}
        cdtrAcct = {"schmeNm": {"prtry": "PH"}, "issr": "GCASH", "acctId": "09612803885", "ccy": "PHP"}
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "USD", "PHP", cdtrAcct=cdtrAcct, tp='EWALLET')
        amt = ApiUtils.randAmount(5, 2, 2)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "PHP", RMNData.prvtId, debtor_agent, RMNData.prvtId_b, creditor_agent, sn1_fee, sn1, cdtrAcct=cdtrAcct, inAmount=amt)
        cdtTrfTxInf["pmtTpInf"] = {"lclInstrm": {"cd": "EWALLET"}}
        cdtTrfTxInf["cdtr"]["nm"] = "Sean Warwick Dela Cruz"
        cdtTrfTxInf["cdtr"]["pstlAdr"]["ctry"] = "PH"
        cdtTrfTxInf["dbtr"]["prvtId"]["othr"]["prtry"] = "DRIVER_LICENSE"
        cdtTrfTxInf["splmtryData"]["addenda"]["senderSourceOfFund"] = "bank account"
        cdtTrfTxInf["splmtryData"]["addenda"]["receiverWalletCode"] = "GCASH"

        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", cdtTrfTxInf["intrBkSttlmAmt"]["amt"], "PHP")
        self.client.checkCodeAndMessage(rate_info)
        # return
        self.client.transactionFlow_sn_sn(
            sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=True,
            isRPP=True, rateInfo=rate_info, chg_fees=["USD"]
        )

    @unittest.skipUnless(RMNData.is_check_db, "从rts下单需修改数据库使模拟的sn1订单完成")
    def test_371_sn_sn_dbtrAgtGiveSNRoxeId_cdtrAgtGivePNRoxeId_sameCurrency(self):
        # pn1 = RMNData.pn_usd_us
        sn1 = "huuzj1hpycrx"
        sn2 = RMNData.sn_usd_us
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(30, 2, 10)
        rts_router, _ = self.rts_client.getRouterList("", "PHP", "", "USD", amt, "", sn1, sn2, )
        sn1_fee = rts_router["data"]["roxeRouters"][0]["roxeNodes"][0]["sendFee"]
        sn2_fee = rts_router["data"]["roxeRouters"][0]["roxeNodes"][1]["deliveryFee"]

        cdtTrfTxInf = self.client.make_RCCT_information("PHP", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId_b,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amt)
        self.client.logger.info(json.dumps(cdtTrfTxInf))
        rmn_tx_id = self.client.submitRTSOrder(sn1, self.rts_client, cdtTrfTxInf, self.rpc_client, amt, sn1_fee)
        # self.client.transactionFlow_sn_sn_sn1IsRTSNode(
        #     rmn_tx_id, sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self
        # )

    @unittest.skipIf(RMNData.is_check_db, "生产测试用例，手动执行")
    def test_383_sn_sn_rightNodeUsePayChannel_ipay_EGP_BIC(self):
        sn1 = RMNData.sn_usd_us_a
        sn2 = "ifomx232tdly"
        if "sandbox" in RMNData.host or "prod" in RMNData.host:
            sn2 = "ipayrmta1eg1"

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": "Credit Agricole Egypt", "bicFI": "AGRIEGCX"},
                          "brnchId": {"nm": "GEZIRA BRANCH"}}
        # cdtrIntrmyAgt = self.client.make_roxe_agent(sn2, "SN")
        # creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        # amount = ApiUtils.randAmount(50, 2, 40)
        amount = 10
        sn1_fee, sn2_fee, _, r_msg = self.client.step_queryRouter(sn1, "USD", "EGP", creditor_agent=creditor_agent,
                                                                  amount=amount, returnMsg=True)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "EGP", RMNData.prvtId, debtor_agent,
                                                        RMNData.prvtId_b, creditor_agent, sn1_fee, sn1,
                                                        inAmount=amount)
        cdtTrfTxInf = ApiUtils.deepUpdateDict(cdtTrfTxInf, r_msg)
        cdtTrfTxInf["dbtr"] = {
            "nm": "Wade Tang",
            "pstlAdr": {"pstCd": "70070", "twnNm": "LULING", "twnLctnNm": "Olmpic", "dstrctNm": "2008 Jadewood Drive",
                        "ctrySubDvsn": "Louisiana", "ctry": "US", "adrLine": "2008 Jadewood Drive"},
            "prvtId": {
                "dtAndPlcOfBirth": {"ctryOfBirth": "US", "prvcOfBirth": "New York", "cityOfBirth": "New York City",
                                    "birthDt": "1960-05-24"},
                "othr": {"id": "EC8661523", "prtry": "Foreign Passport", "issr": "CA"}
            },
            "ctctDtls": {"phneNb": "224-420-2671"}
        }
        cdtTrfTxInf["cdtr"] = {
            "nm": "AMR ADEL HELMY ALY HASSAN",
            "pstlAdr": {"ctry": "EG", "adrLine": "Heliopolis, Cairo, Egypt"},
        }
        cdtTrfTxInf["cdtrAcct"] = {"ccy": "EGP", "acctId": "11118180194503"}

        cdtTrfTxInf["splmtryData"]["addenda"]["senderIdIssueDate"] = "2018-07-03"
        cdtTrfTxInf["splmtryData"]["addenda"]["senderIdExpireDate"] = "2038-07-03"
        print(json.dumps(cdtTrfTxInf))
        return
        msg_id, tx_msg, end2end_id, rmn_tx_id, st_msg = self.client.transactionFlow_sn_sn_not_check_db_1(
            sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=True
        )
        self.client.logger.warning("msg_id={}".format(msg_id))
        self.client.logger.warning("tx_msg={}".format(tx_msg))
        self.client.logger.warning("end2end_id={}".format(end2end_id))
        self.client.logger.warning("rmn_tx_id={}".format(rmn_tx_id))
        self.client.logger.warning("st_msg={}".format(st_msg))
        time.sleep(90)
        # tx2_msg = self.waitSN2ReceiveRCCTInProd(5)[0]
        # self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, True)

    @unittest.skipIf(RMNData.is_check_db, "生产测试用例，手动执行")
    def test_384_sn_sn_rightNodeUsePayChannel_ipay_CNY_BIC(self):
        sn1 = RMNData.sn_usd_us_a
        sn2 = "ipayrmt11cn1"

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": "China Merchants Bank", "bicFI": "CMBCCNBS"}}
        cdtrIntrmyAgt = self.client.make_roxe_agent(sn2, "SN")
        amount = 8
        sn1_fee, sn2_fee, _, r_msg = self.client.step_queryRouter(sn1, "USD", "CNY", creditor_agent=cdtrIntrmyAgt,
                                                                  amount=amount, returnMsg=True)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "CNY", RMNData.prvtId, debtor_agent,
                                                        RMNData.prvtId_b, creditor_agent, sn1_fee, sn1,
                                                        inAmount=amount)
        cdtTrfTxInf = ApiUtils.deepUpdateDict(cdtTrfTxInf, r_msg)
        cdtTrfTxInf["dbtr"] = {
            "nm": "Wade Tang",
            "pstlAdr": {"pstCd": "70070", "twnNm": "LULING", "twnLctnNm": "Olmpic", "dstrctNm": "2008 Jadewood Drive",
                        "ctrySubDvsn": "Louisiana", "ctry": "US", "adrLine": "2008 Jadewood Drive"},
            "prvtId": {
                "dtAndPlcOfBirth": {"ctryOfBirth": "US", "prvcOfBirth": "New York", "cityOfBirth": "New York City",
                                    "birthDt": "1960-05-24"},
                "othr": {"id": "EC8661523", "prtry": "Foreign Passport", "issr": "CA"}
            },
            "ctctDtls": {"phneNb": "224-420-2671"}
        }
        cdtTrfTxInf["cdtr"] = {
            "nm": "MingLei Li",
            "pstlAdr": {"ctry": "CN", "adrLine": "Baimiao Village, Changping District, Beijing"},
            "ctctDtls": {"phneNb": "15811055254"}
        }
        cdtTrfTxInf["cdtrAcct"] = {"ccy": "CNY", "acctId": "6225880172276413"}

        cdtTrfTxInf["splmtryData"]["addenda"]["senderIdIssueDate"] = "2018-07-03"
        cdtTrfTxInf["splmtryData"]["addenda"]["senderIdExpireDate"] = "2038-07-03"
        # cdtTrfTxInf["purp"] = {"desc": "Other Personal Services"}
        # cdtTrfTxInf["rltnShp"] = {"desc": "Friend"}
        # cdtTrfTxInf["splmtryData"]["addenda"]["senderSourceOfFund"] = "Others"
        cdtTrfTxInf["splmtryData"]["addenda"].pop("tel")
        cdtTrfTxInf["cdtrIntrmyAgt"] = cdtrIntrmyAgt
        print(json.dumps(cdtTrfTxInf))
        # return
        msg_id, tx_msg, end2end_id, rmn_tx_id, st_msg = self.client.transactionFlow_sn_sn_not_check_db_1(
            sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=True
        )
        self.client.logger.warning("msg_id={}".format(msg_id))
        self.client.logger.warning("tx_msg={}".format(tx_msg))
        self.client.logger.warning("end2end_id={}".format(end2end_id))
        self.client.logger.warning("rmn_tx_id={}".format(rmn_tx_id))
        self.client.logger.warning("st_msg={}".format(st_msg))
        time.sleep(90)
        # tx2_msg = self.waitSN2ReceiveRCCTInProd(5)[0]
        # self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, True)