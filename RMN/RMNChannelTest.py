# coding=utf-8
# author: Li MingLei
# date: 2022-04-15
import json
import copy
import re
import time
import unittest
from .RMNApiTest import RMNData, RMNApiClient, ApiUtils, BaseCheckRMN
from RTS.RtsApiTest import RTSApiClient, RTSData
from RSS.RssApiTest import RSSApiClient, RSSData


class RMNChannelTest(BaseCheckRMN):

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = RMNApiClient(RMNData.host, RMNData.env, RMNData.api_key, RMNData.sec_key, check_db=RMNData.is_check_db,
                                  sql_cfg=RMNData.sql_cfg, node_rsa_key=RMNData.node_rsa_key)
        cls.rts_client = RTSApiClient(RTSData.host, RTSData.api_id, RTSData.sec_key, RTSData.ssl_pub_key)
        # cls.chain_client = Clroxe(RTSData.chain_host)
        cls.rss_client = RSSApiClient(RSSData.host, RSSData.chain_host)

    @classmethod
    def tearDownClass(cls) -> None:
        if RMNData.is_check_db:
            cls.client.mysql.disconnect_database()

    def submitOrderAndCheckToTerrapayAmount(self, sn1, sn2, cdtTrfTxInf, sn1_fee=None, sn2_fee=None):
        """
        提交订单并校验terrapay实际出金金额
        """
        # 获取terrapay通道费用
        to_amount = cdtTrfTxInf["intrBkSttlmAmt"]["amt"]
        recCurrency = cdtTrfTxInf["cdtrAcct"]["ccy"]
        recCountry = cdtTrfTxInf["cdtr"]["pstlAdr"]["ctry"]
        sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", recCurrency, recCountry, sn1, "TERRAPAY")
        # 向terrapay提交订单的实际金额
        to_terrapay_amount = ApiUtils.parseNumberDecimal(float(to_amount) - float(deliverFee), 2, True)
        # 查询下单前在terrapay中间账户的余额
        TP_before_balance = self.rss_client.terrapayQueryAccountBalance()
        # rmn下单
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=True)
        # 查询下单后在terrapay中间账户的余额
        TP_after_balance = self.rss_client.terrapayQueryAccountBalance()
        # 实际terrapay从中间账户转出的钱
        TP_transfer_out_amount = ApiUtils.parseNumberDecimal(TP_before_balance - TP_after_balance, 2, True)
        self.client.logger.info("实际提交到TerraPay的订单金额：{}".format(to_terrapay_amount))
        self.client.logger.info("TerraPay实际转账金额：{}".format(TP_transfer_out_amount))
        self.assertAlmostEqual(TP_transfer_out_amount, to_terrapay_amount, places=2, msg="terrapay中间账户资产变化与提交金额不符")

    def checkRouterList_sndFeeAndDlvFee(self, router_list, sendCurrency, sendCountry, recCurrency, recCountry, leftChannel, rightChannel, liftNode, rightNode):
        """
        校验返回路由列表中的sndFeeAmt、dlvFeeAmt
        """
        pay_currency = sendCurrency+"."+sendCountry
        out_currency = recCurrency+"."+recCountry
        router_db_info = self.client.mysql.exec_sql_query("select router_config from `roxe-rts`.`rts_node_router` where pay_currency like '%{}%' and out_currency like '%{}%' and pay_node_code like '%{}%' and out_node_code like '%{}%'".format(pay_currency, out_currency, liftNode, rightNode))
        channelFeeCurrency = json.loads(router_db_info[0]["routerConfig"])["sn2"]["payCurrency"].split(".")[0]
        chrgsInf = router_list["data"]["rptOrErr"][0]["chrgsInf"]
        for i in range(len(chrgsInf)):
            id = chrgsInf[i]["agt"]["id"]
            if id == liftNode:
                sendFee, channelFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, leftChannel, rightChannel)
                self.assertEqual(chrgsInf[i]["sndFeeAmt"]["amt"], str(sendFee), msg="获取的sndFeeAmt不正确")
                self.assertEqual(chrgsInf[i+1]["dlvFeeAmt"]["amt"], str(channelFee), msg="获取的dlvFeeAmt不正确")
                self.assertEqual(chrgsInf[i]["sndFeeAmt"]["ccy"], sendCurrency, msg="获取的sndFee币种不正确")
                self.assertEqual(chrgsInf[i+1]["dlvFeeAmt"]["ccy"], channelFeeCurrency, msg="获取的dlvFee币种不正确")

    def test_001_getRouterList_senderIsSN_differentCurrency_snRoxeId_TerraPay(self):
        sender = RMNData.sn_usd_us
        recCurrency = "PHP"
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(RMNData.sn_roxe_terrapay, "SN")
        msg = self.client.make_RRLQ_information("USD", recCurrency, "100", cdtrAgt=agent_info)
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "sn-sn")

    @unittest.skip
    def test_002_getRouterList_senderIsPN_differentCurrency_bicCode_TerraPay(self):
        sender = RMNData.sn_usd_us
        recCurrency = "USD"
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        msg = self.client.make_RRLQ_information("USD", recCurrency, "100", cdtrAgt=RMNData.bic_agents[recCurrency])
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sender, "sn-sn")

    def test_003_sn_sn_rightNodeUsePayChannel_TerraPay_MYR(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        # amount = float(addenda_info["amount"])
        r_currency = "MYR"
        r_name = "oyugi randy"
        r_country = "MY"
        r_bank_name = "MAY BANKA"
        r_account_number = "1976041128"
        r_bank_code = "MBBEMYKL"
        debtor = RMNData.debtor
        # debtor_agent = {"finInstnId": {"othr": {"id": sn1, "schmeCd": "ROXE"}}}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        amt = ApiUtils.randAmount(100, 2, 30)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, "USD", r_currency, creditor_agent=creditor_intermediary_agent, amount=amt
        )
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                        creditor_agent, creditor_intermediary_agent, float(sendFee), sn1, addenda_info, r_account_number, inAmount=amt)
        # self.submitOrderAndCheckToTerrapayAmount(sn1, sn2, cdtTrfTxInf, api_key, sec_key, r_currency, to_amount)
        self.submitOrderAndCheckToTerrapayAmount(sn1, sn2, cdtTrfTxInf)

    def test_004_sn_sn_rightNodeUsePayChannel_TerraPay_PHP(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay
        if "sandbox" in RMNData.host: sn2 = "huuzj2hpycrx"  # sandbox

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "PHP"
        r_country = "PH"
        r_account_number = "20408277204478"
        r_name = "RANDY OYUGI"
        r_bank_name = "Asia United Bank"
        r_bank_code = "AUBKPHMM"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        amt = ApiUtils.randAmount(100, 2, 20)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", r_currency, creditor_agent=creditor_intermediary_agent, amount=amt)
        # sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                            creditor_agent, creditor_intermediary_agent,
                                                                            float(sn1_fee), sn1, addenda_info, r_account_number, inAmount=amt)
        cdtTrfTxInf["dbtr"]["pstlAdr"]["ctry"] = "US"
        # print(json.dumps(cdtTrfTxInf))
        self.submitOrderAndCheckToTerrapayAmount(sn1, sn2, cdtTrfTxInf)

    @unittest.skip("暂不支持,提供的BIC不正确")
    def test_005_sn_sn_rightNodeUsePayChannel_TerraPay_CNY(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "CNY"
        r_country = "CN"
        r_account_number = "6217900100010200001"
        r_name = "Hui Lu"
        r_bank_name = "UNION PAY"
        r_bank_code = "CNUNIONPAY"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        ctctDtls = {"phneNb": "+8613800001111"}
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country, ctctDtls=ctctDtls)
        sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                            creditor_agent, creditor_intermediary_agent,
                                                                            float(sendFee), sn1, addenda_info, r_account_number)
        self.submitOrderAndCheckToTerrapayAmount(sn1, sn2, cdtTrfTxInf)

    def test_006_sn_sn_rightNodeUsePayChannel_TerraPay_INR(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "INR"
        r_country = "IN"
        r_account_number = "50100002965304"
        r_name = "DEEPA DEEPA"
        r_bank_name = "HDFC Bank"
        r_bank_code = "HDFC0001626"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": r_bank_name, "clrSysMmbId": {"clrSysCd": "INFSC", "mmbId": r_bank_code}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")

        # 手动组装
        # ts_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        # msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        # agent_info = self.client.make_roxe_agent(RMNData.sn_roxe_terrapay, "SN")
        # msg = self.client.make_RRLQ_information("USD", r_currency, "100", cdtrAgt=agent_info)
        # router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        # self.client.checkCodeAndMessage(router_list)
        # sn1_fee = [i["sndFeeAmt"]["amt"] for i in router_list["data"]["rptOrErr"][0]["chrgsInf"] if
        #            i["agt"]["id"] == sn1 and "sndFeeAmt" in i]
        # sendFee = float(sn1_fee[0]) if sn1_fee else 0
        # sn2 = router_list["data"]["rptOrErr"][0]["trnRtgInf"]["cdtrAgt"]["finInstnId"]["othr"]["id"]
        # sn2_fee = [i["dlvFeeAmt"]["amt"] for i in router_list["data"]["rptOrErr"][0]["chrgsInf"] if
        #            i["agt"]["id"] == sn2 and "dlvFeeAmt" in i]
        # sn2_fee = float(sn2_fee[0]) if sn2_fee else 0

        # 调用封装方法不校验费用
        # sendFee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", r_currency, creditor_agent=creditor_agent)

        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                            creditor_agent, creditor_intermediary_agent,
                                                                            float(sendFee), sn1, addenda_info, r_account_number)
        self.submitOrderAndCheckToTerrapayAmount(sn1, sn2, cdtTrfTxInf)

    def test_007_sn_sn_rightNodeUsePayChannel_TerraPay_IDR(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "IDR"
        r_country = "ID"
        r_account_number = "1976020126"
        r_name = "oyugi randy"
        r_bank_name = "Bank Mandiri"
        r_bank_code = "BMAINDMB"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        # creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_agent = {"finInstnId": {"nm": r_bank_name, "clrSysMmbId": {"clrSysCd": "INFSC", "mmbId": r_bank_code}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                            creditor_agent, creditor_intermediary_agent,
                                                                            float(sendFee), sn1, addenda_info, r_account_number)
        self.submitOrderAndCheckToTerrapayAmount(sn1, sn2, cdtTrfTxInf)

    def test_008_sn_sn_rightNodeUsePayChannel_TerraPay_THB(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "THB"
        r_country = "TH"
        r_account_number = "20408277205678"
        r_name = "RANDY OYUGI"
        r_bank_name = "BANGKOK BANK"
        r_bank_code = "BKKBTHBK"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                            creditor_agent, creditor_intermediary_agent,
                                                                            float(sendFee), sn1, addenda_info, r_account_number)
        self.submitOrderAndCheckToTerrapayAmount(sn1, sn2, cdtTrfTxInf)

    def test_009_sn_sn_rightNodeUsePayChannel_TerraPay_GHS(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "GHS"
        r_country = "GH"
        r_account_number = "00100008703552"
        r_name = "oyugi randy"
        r_bank_name = "UBA BANK"
        r_bank_code = "STBGGHAC"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent,
                                                                            creditor,
                                                                            creditor_agent, creditor_intermediary_agent,
                                                                            float(sendFee), sn1, addenda_info, r_account_number)
        self.submitOrderAndCheckToTerrapayAmount(sn1, sn2, cdtTrfTxInf)

    @unittest.skip("提供的BIC不正确")
    def test_010_sn_sn_rightNodeUsePayChannel_TerraPay_VND(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "VND"
        r_country = "VN"
        r_account_number = "1976031127"
        r_name = "oyugi randy"
        r_bank_name = "Vietin Bank"
        r_bank_code = "VBBLUKAG"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        # ctctDtls = {"phneNb": "+008413800001111"}
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                            creditor_agent, creditor_intermediary_agent,
                                                                            float(sendFee), sn1, addenda_info, r_account_number)
        self.submitOrderAndCheckToTerrapayAmount(sn1, sn2, cdtTrfTxInf)

    def test_011_sn_sn_rightNodeUsePayChannel_TerraPay_ARS(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "ARS"
        r_country = "AR"
        r_account_number = "482700048226"
        r_name = "oyugi randy"
        r_bank_name = "Banco Credicoop Coop. L"
        r_bank_code = "BACONAAR"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                            creditor_agent, creditor_intermediary_agent,
                                                                            float(sendFee), sn1, addenda_info, r_account_number)
        self.submitOrderAndCheckToTerrapayAmount(sn1, sn2, cdtTrfTxInf)

    @unittest.skip("提供的BIC不正确")
    def test_012_sn_sn_rightNodeUsePayChannel_TerraPay_CLP(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "CLP"
        r_country = "CL"
        r_account_number = "64983342"
        r_name = "oyugi randy"
        r_bank_name = "Banco Bice"
        r_bank_code = "BANBICL"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent,
                                                                            creditor,
                                                                            creditor_agent, creditor_intermediary_agent,
                                                                            float(sendFee), sn1, addenda_info, r_account_number)
        self.submitOrderAndCheckToTerrapayAmount(sn1, sn2, cdtTrfTxInf)

    def test_013_sn_sn_rightNodeUsePayChannel_TerraPay_COP(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "COP"
        r_country = "CO"
        r_account_number = "482700048226"
        r_name = "oyugi randy"
        r_bank_name = "Bancolombia"
        r_bank_code = "COLOCOBMBAQ"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                            creditor_agent, creditor_intermediary_agent,
                                                                            float(sendFee), sn1, addenda_info, r_account_number)
        self.submitOrderAndCheckToTerrapayAmount(sn1, sn2, cdtTrfTxInf)

    @unittest.skip("提供的BIC不正确")
    def test_014_sn_sn_rightNodeUsePayChannel_TerraPay_PEN(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "PEN"
        r_country = "PE"
        r_account_number = "00219313084958709612"
        r_name = "oyugi randy"
        r_bank_name = "Banco Central de Reserva"
        r_bank_code = "BANCDER"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                            creditor_agent, creditor_intermediary_agent,
                                                                            float(sendFee), sn1, addenda_info, r_account_number)
        self.submitOrderAndCheckToTerrapayAmount(sn1, sn2, cdtTrfTxInf)

    def test_015_sn_sn_rightNodeUsePayChannel_TerraPay_BRL(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "BRL"
        r_country = "BR"
        r_account_number = "718530346"
        r_name = "oyugi randy"
        r_bank_name = "unicred norte do parana"
        r_bank_code = "UNPABRPR"
        brnchId = {"id": "3450"}
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code, brnchId=brnchId)
        # creditor_agent = self.client.make_roxe_agent(sn2, "SN", name=r_bank_name, brnchId=brnchId)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = {
            "nm": r_name,
            "ctryOfRes": r_country,
            "pstlAdr": {
                "twnNm": "Manila",
                "adrLine": "No. 1 Financial Street"
            },
            "prvtId": {
                "dtAndPlcOfBirth": {
                    "ctryOfBirth": r_country,
                    "cityOfBirth": "on the earth"
                }
            }
        }
        addenda_info["receiverBankCode"] = r_bank_code
        # purp = {"desc": "Gift"}
        # rltnShp = {"desc": "Friend"}
        sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor, creditor_agent,
                                                                creditor_intermediary_agent, float(sendFee), sn1, addenda_info, r_account_number)
        cdtTrfTxInf.pop("cdtrIntrmyAgt")
        self.submitOrderAndCheckToTerrapayAmount(sn1, sn2, cdtTrfTxInf)

    def test_016_sn_sn_rightNodeUsePayChannel_TerraPay_EC_USD(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "USD"
        r_country = "EC"
        r_account_number = "02006137640"
        r_name = "oyugi randy"
        r_bank_name = "Banco Amazonas"
        r_bank_code = "BANAFMEC"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                            creditor_agent, creditor_intermediary_agent,
                                                                            float(sendFee), sn1, addenda_info, r_account_number)
        self.submitOrderAndCheckToTerrapayAmount(sn1, sn2, cdtTrfTxInf)

    @unittest.skip("提供的BIC不正确")
    def test_017_sn_sn_rightNodeUsePayChannel_TerraPay_BOB(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "BOB"
        r_country = "BO"
        r_account_number = "1071007651"
        r_name = "oyugi randy"
        r_bank_name = "Banco Mercantil"
        r_bank_code = "BANMEBO"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, r_account_number)
        self.submitOrderAndCheckToTerrapayAmount(sn1, sn2, cdtTrfTxInf)

    @unittest.skip("提供的BIC不正确")
    def test_018_sn_sn_rightNodeUsePayChannel_TerraPay_MXN(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "MXN"
        r_country = "MX"
        r_account_number = "210017272102"
        r_name = "JULIO SOLANO"
        r_bank_name = "BANAMEX"
        r_bank_code = "BANAMEX"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, r_account_number)
        self.submitOrderAndCheckToTerrapayAmount(sn1, sn2, cdtTrfTxInf)

    @unittest.skip("提供的BIC不正确")
    def test_019_sn_sn_rightNodeUsePayChannel_TerraPay_UYU(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "UYU"
        r_country = "UY"
        r_account_number = "000001156543"
        r_name = "EZEQUIEL ISRAEL"
        r_bank_name = "SANTANDER"
        r_bank_code = "SANTANDER"
        brnchId = {"id": "6393"}
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code, brnchId=brnchId)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, r_account_number)
        self.submitOrderAndCheckToTerrapayAmount(sn1, sn2, cdtTrfTxInf)

    # NIUM currency testcase
    def test_020_getRouterList_senderIsSN_differentCurrency_snRoxeId_NIUM(self):
        """
        查询路由, 消息发送方为SN节点, 指定sn2 roxe id
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "INR"
        recCountry = "IN"
        ts_headers = self.client.make_header(sn1, apiKey, "RRLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(sn2, "SN")
        msg = self.client.make_RRLQ_information(sendCurrency, recCurrency, "100", cdtrAgt=agent_info)
        router_list, req_msg = self.client.get_router_list(secKey, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sn1, "sn-sn")
        self.checkRouterList_sndFeeAndDlvFee(router_list, sendCurrency, sendCountry, recCurrency, recCountry, sn1, "NIUM", sn1, sn2)

    def test_021_sn_sn_rightNodeUsePayChannel_nium_BRL(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "BRL"
        recCountry = "BR"
        accountId = "12345678901"
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        amt = ApiUtils.randAmount(100, 2, 30)
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, creditor_agent=creditor_intermediary_agent, amount=amt
        )
        debtor = {
            "nm": "Michael Stallman",
            "prvtId": {"othr": {"prtry": "CCPT", "id": "12345678911234"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": sendCountry},
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "Edward Nelms",
                    "prvtId": {"othr": {"prtry": "CPF", "id": "12345678901"}},
                    "pstlAdr": {"ctry": recCountry},
                    "ctctDtls": {"phneNb": "3135446952"}}
        creditor_agent = {"finInstnId": {"nm": "XXXX BANK", "clrSysMmbId": {"clrSysCd": "BRBCB", "mmbId": "237"}}, "brnchId": {"id": "1234"}}

        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, accountId)
        cdtTrfTxInf["cdtrAcct"] = {"tp": "SAVINGS", "ccy": recCurrency, "acctId": accountId}
        cdtTrfTxInf["purp"] = {"desc": "Family Maintenance"}
        self.client.logger.info(cdtTrfTxInf)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    def test_022_sn_sn_rightNodeUsePayChannel_nium_CAD(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "CAD"
        recCountry = "CA"
        accountId = "4929858296666465"
        amt = ApiUtils.randAmount(100, 2, 20)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, creditor_agent=creditor_intermediary_agent, amount=amt
        )
        debtor = {
            "nm": "Michael Stallman",
            "prvtId": {"othr": {"prtry": "CCPT", "id": "12345678911234"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "twnNm": "Southfield", "ctrySubDvsn": "Washington", "pstCd": "5360", "ctry": sendCountry},
            "ctryOfRes": "US"}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "nm": "Henry G Browne",
            "pstlAdr": {"adrLine": "1123 street", "twnNm": "Mengdh", "ctrySubDvsn": "DC", "pstCd": "112", "ctry": recCountry}}
        creditor_agent = {"finInstnId": {"nm": "BRL BANK", "clrSysMmbId": {"clrSysCd": "CACPA", "mmbId": "61806071"}}}
        # creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        # addenda_info = {"receiverStates": "DC"}
        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, accountId)
        cdtTrfTxInf["purp"] = {"desc": "Family Maintenance"}
        self.client.logger.info(cdtTrfTxInf)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    def test_023_sn_sn_rightNodeUsePayChannel_nium_INR(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "INR"
        recCountry = "IN"
        accountId = "12345678901234"
        amt = ApiUtils.randAmount(100, 2, 20)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, creditor_agent=creditor_intermediary_agent, amount=amt
        )
        # sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "NIUM")
        debtor = {
            "nm": "Michael Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"}, "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": sendCountry, "twnNm": "xx", "ctrySubDvsn": "xx123"},
            "ctctDtls": {"phneNb": "911123422234"}}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "Edward Nelms", "pstlAdr": {"ctry": recCountry, "twnNm": "xxXX", "ctrySubDvsn": "1xx123", "adrLine": "123ddd"}}
        creditor_agent = {"finInstnId": {"nm": "XXXX BANK", "clrSysMmbId": {"clrSysCd": "INFSC", "mmbId": "HSBC0110002"}}}
        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                sendFee, sn1, addenda_info, accountId, amt)
        cdtTrfTxInf["purp"] = {"desc": "Family Maintenance"}

        self.client.logger.info(json.dumps(cdtTrfTxInf))
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sendFee, deliverFee], self, True)

    def test_024_sn_sn_rightNodeUsePayChannel_nium_USD(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "USD"
        recCountry = "US"
        accountId = "133563585"
        amt = ApiUtils.randAmount(100, 2, 20)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, creditor_agent=creditor_intermediary_agent, amount=amt
        )
        debtor = {
            "nm": "Oracle trust Inc.",
            "prvtId": {"othr": {"prtry": "CCPT", "id": "12345678911234"}, "dtAndPlcOfBirth": {"ctryOfBirth": "US", "cityOfBirth": "Southfield", "birthDt": "2004-07-04"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "twnNm": "Southfield", "ctrySubDvsn": "Michigan", "pstCd": "48235", "ctry": sendCountry},
            "ctryOfRes": "US"}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "nm": "Edward Nelms",
            "pstlAdr": {"adrLine": "4961 Woodbridge Lane", "twnNm": "Lincoln", "pstCd": "68501", "ctry": recCountry}}
        # creditor_agent = RMNData.bic_agents[recCurrency]
        creditor_agent = {"finInstnId": {"nm": "XXXX BANK", "clrSysMmbId": {"clrSysCd": "USABA", "mmbId": "314078469"}}}
        addenda_info = {"receiverStates": "Nebraska"}
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, accountId)
        # cdtTrfTxInf["cdtrAcct"] = {"tp": "Individual", "ccy": recCurrency, "acctId": accountId}
        cdtTrfTxInf["purp"] = {"desc": "Family Maintenance"}
        self.client.logger.info(cdtTrfTxInf)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    def test_025_sn_sn_rightNodeUsePayChannel_nium_SGD(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "SGD"
        recCountry = "SG"
        accountId = "4929858296666465"
        amt = ApiUtils.randAmount(100, 2, 20)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, creditor_agent=creditor_intermediary_agent, amount=amt
        )
        debtor = {
            "nm": "Michael Stallman",
            "prvtId": {"othr": {"prtry": "CCPT", "id": "12345678911234"}, "dtAndPlcOfBirth": {"ctryOfBirth": "US", "cityOfBirth": "abdwd", "birthDt": "1988-01-22"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "twnNm": "abdwd", "ctrySubDvsn": "ahsdfl il", "pstCd": "112233", "ctry": sendCountry},
            "ctryOfRes": "US"}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "Henry G Browne", "pstlAdr": {"adrLine": "test address 1", "twnNm": "ahver", "ctry": recCountry}}
        creditor_agent = {"finInstnId": {"bicFI": "FAEASGSG"}}
        # creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, accountId)
        cdtTrfTxInf["purp"] = {"desc": "Family Maintenance"}
        self.client.logger.info(cdtTrfTxInf)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    @unittest.skip("向NIUM提交订单失败：找不到接收方账户")
    def test_026_sn_sn_rightNodeUsePayChannel_nium_PLN(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PLN"
        recCountry = "PL"
        accountId = "GB29NWBK60161331926819"
        sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "NIUM")
        debtor = {
            "nm": "Michael Stallman",
            "prvtId": {"othr": {"prtry": "CCPT", "id": "12345678911234"}, "dtAndPlcOfBirth": {"ctryOfBirth": "US", "cityOfBirth": "Southfield", "birthDt": "1986-01-23"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "twnNm": "Southfield", "ctrySubDvsn": "Michigan", "pstCd": "5360"},
            "ctryOfRes": "US"}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "nm": "Henry G Browne",
            "ctryOfRes": recCountry,
            "pstlAdr": {"adrLine": "1123 street", "twnNm": "Mengdh"}}
        creditor_agent = {"finInstnId": {"nm": "PLA BANK", "clrSysMmbId": {"clrSysCd": "GOSKPLP0", "mmbId": "1122223333333444"}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        addenda_info = {
            "receiverBankId": "LOCAL____SWIFT____GOSKPLP0",
            "referenceId": "123456123",
            "amount": "12",
            "pledgeAccountCurrency": "USD",
            "senderAccountType": "Individual"}

        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, accountId)
        cdtTrfTxInf["cdtrAcct"] = {"tp": "Individual", "ccy": recCurrency, "acctId": accountId}
        cdtTrfTxInf["purp"] = {"desc": "Family Maintenance"}

        self.client.logger.info(cdtTrfTxInf)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    @unittest.skip("向NIUM提交订单失败：NIUM未查询到汇率")
    def test_027_sn_sn_rightNodeUsePayChannel_nium_GHS(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "GHS"
        recCountry = "GH"
        accountId = "123456789012345678"
        sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "NIUM")
        debtor = {
            "nm": "Michael Stallman",
            "prvtId": {"othr": {"prtry": "CCPT", "id": "12345678911234"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "twnNm": "Southfield", "ctrySubDvsn": "Michigan", "pstCd": "5360"},
            "ctryOfRes": "US"}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "nm": "Henry G Browne",
            "ctryOfRes": recCountry,
            "pstlAdr": {"adrLine": "1123 street", "twnNm": "Mengdh", "ctrySubDvsn": "Washington", "pstCd": "112"},
            "ctctDtls": {"phneNb": "3135446952"}}
        creditor_agent = {"finInstnId": {"nm": "XXXX BANK", "bicFI": "MBGHGHAC"}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        addenda_info = {
            "receiverBankId": "LOCAL____SWIFT____MBGHGHAC",
            "referenceId": "123456123",
            "amount": "12",
            "pledgeAccountCurrency": "USD",
            "senderAccountType": "Individual",
            "receiverState": "DC"}

        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, accountId)
        cdtTrfTxInf["cdtrAcct"] = {"tp": "Individual", "ccy": recCurrency, "acctId": accountId}
        cdtTrfTxInf["purp"] = {"desc": "Family Maintenance"}

        self.client.logger.info(cdtTrfTxInf)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    def test_028_sn_sn_rightNodeUsePayChannel_nium_EUR_DE(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "EUR"
        recCountry = "DE"
        accountId = "GB29NWBK60161331926819"
        amt = ApiUtils.randAmount(100, 2, 20)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, creditor_agent=creditor_intermediary_agent, amount=amt
        )
        debtor = {
            "nm": "Michael Stallman",
            "prvtId": {"othr": {"prtry": "CCPT", "id": "12345678911234"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": sendCountry},
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "Henry G Browne", "ctryOfRes": recCountry, "pstlAdr": {"ctry": recCountry}}
        creditor_agent = {"finInstnId": {"nm": "XXXX BANK", "bicFI": "BYLADEM1ERH"}}
        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, accountId, inAmount=amt)
        cdtTrfTxInf["purp"] = {"desc": "Family Maintenance"}
        self.client.logger.info(cdtTrfTxInf)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    def test_029_sn_sn_rightNodeUsePayChannel_nium_EUR_FR(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "EUR"
        recCountry = "FR"
        accountId = "GB29NWBK60161331926819"
        amt = ApiUtils.randAmount(100, 2, 20)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, creditor_agent=creditor_intermediary_agent, amount=amt
        )
        debtor = {
            "nm": "Michael Stallman",
            "prvtId": {"othr": {"prtry": "CCPT", "id": "12345678911234"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": sendCountry},
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "Henry G Browne", "pstlAdr": {"ctry": recCountry}}
        creditor_agent = {"finInstnId": {"nm": "XXXX BANK", "bicFI": "CHASFRP0"}}
        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, accountId)
        cdtTrfTxInf["purp"] = {"desc": "Family Maintenance"}

        self.client.logger.info(cdtTrfTxInf)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    # Cebuana currency testcase
    def test_030_getRouterList_senderIsSN_differentCurrency_snRoxeId_cebuana(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_cebuana
        apiKey = RMNData.api_key
        secKey = RMNData.sec_key
        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PHP"
        recCountry = "PH"
        ts_headers = self.client.make_header(sn1, apiKey, "RRLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(sn2, "SN")
        msg = self.client.make_RRLQ_information(sendCurrency, recCurrency, "100", cdtrAgt=agent_info)
        router_list, req_msg = self.client.get_router_list(secKey, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sn1, "sn-sn")
        self.checkRouterList_sndFeeAndDlvFee(router_list, sendCurrency, sendCountry, recCurrency, recCountry, sn1, "CEBUANA", sn1, sn2)

    # 部分账户不可用
    def test_031_sn_sn_rightNodeUsePayChannel_cebuana(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_cebuana

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PHP"
        recCountry = "PH"
        # accountId = "916100000424"  # 通过
        # accountId = "5120019630"  # 失败
        # accountId = "7010010691"  # 失败
        # accountId = "003010000426"  # 失败
        # accountId = "005120019633"  # 失败
        # accountId = "4332515"  # 失败
        # accountId = "4762018"  # 失败
        # accountId = "005120019630"  # 失败
        # accountId = "7000110622011110"  # 失败
        # accountId = "7000110622022220"  # 失败
        # accountId = "7000110622033330"  # 失败
        # accountId = "7000110622023450"  # 失败
        # accountId = "7000110622023450"  # 失败
        # accountId = "7000110622009870"  # 失败
        # accountId = "7000110622010100"  # 失败
        accountId_info = ["916100000424", "5120019630", "7010010691", "003010000426", "005120019633", "4332515", "4762018", "005120019630", "7000110622011110", "7000110622022220", "7000110622033330", "7000110622023450", "7000110622009870", "7000110622010100"]
        sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "CEBUANA")
        creditor_agent = {
            "finInstnId": {"nm": "Asia United Bank", "clrSysMmbId": {"clrSysCd": "BRSTN", "mmbId": "011020011"}}}
        amt = ApiUtils.randAmount(100, 2, 20)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, sendCurrency, recCurrency,
                                                           creditor_agent=creditor_agent, amount=amt)
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "cebuana to cebuana", "pstlAdr": {"adrLine": "001 Central Avenue"}}
        # creditor_agent = {"finInstnId": {"nm": "Asia United Bank", "bicFI": "AUBKPHMM"}}

        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="CEBUANA node")
        addenda_info = None
        # for accountId in accountId_info:
        #     cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
        #                                                             creditor_agent, creditor_intermediary_agent,
        #                                                             float(sendFee), sn1, addenda_info, accountId)
        #     self.client.logger.info(cdtTrfTxInf)
        #     inner_node = True if sn2 in RMNData.channel_nodes else False
        #     self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    # 账户不可用
    def test_032_sn_sn_rightNodeUsePayChannel_cebuana(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_cebuana

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PHP"
        recCountry = "PH"
        # accountId = "000661295397"  # 失败
        # accountId = "000668088694"  # 失败
        # accountId = "100331157"  # 失败
        # accountId = "3828014878"  # 失败
        accountId_info = ["000661295397", "000668088694", "100331157", "3828014878"]
        sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "CEBUANA")
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "cebuana to cebuana", "pstlAdr": {"adrLine": "001 Central Avenue"}}
        # creditor_agent = {"finInstnId": {"nm": "Banco de Oro", "bicFI": "BNORPHMM"}}
        creditor_agent = {"finInstnId": {"nm": "Banco de Oro", "clrSysMmbId": {"clrSysCd": "BRSTN", "mmbId": "010530667"}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="CEBUANA node")
        addenda_info = None
        for accountId in accountId_info:
            cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                    creditor_agent, creditor_intermediary_agent,
                                                                    float(sendFee), sn1, addenda_info, accountId)
            self.client.logger.info(cdtTrfTxInf)
            inner_node = True if sn2 in RMNData.channel_nodes else False
            self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    # 账户不可用
    def test_033_sn_sn_rightNodeUsePayChannel_cebuana(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_cebuana

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PHP"
        recCountry = "PH"
        # accountId = "13029636"  # 失败
        # accountId = "13033919"  # 失败
        # accountId = "5010104324"  # 失败
        # accountId = "1433000311"  # 失败
        accountId_info = ["13029636", "13033919", "5010104324", "1433000311"]
        sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "CEBUANA")
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "cebuana to cebuana", "pstlAdr": {"adrLine": "001 Central Avenue"}}
        # creditor_agent = {"finInstnId": {"nm": "Bank of the Philippine Islands", "bicFI": "BOPIPHMM"}}
        creditor_agent = {"finInstnId": {"nm": "Bank of the Philippine Islands", "clrSysMmbId": {"clrSysCd": "BRSTN", "mmbId": "010040018"}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="CEBUANA node")
        addenda_info = None
        for accountId in accountId_info:
            cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                    creditor_agent, creditor_intermediary_agent,
                                                                    float(sendFee), sn1, addenda_info, accountId)
            self.client.logger.info(cdtTrfTxInf)
            inner_node = True if sn2 in RMNData.channel_nodes else False
            self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    # 部分账户不可用
    def test_034_sn_sn_rightNodeUsePayChannel_cebuana(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_cebuana

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PHP"
        recCountry = "PH"
        # accountId = "101400001643"  # 通过
        # accountId = "100302229052"  # 失败
        # accountId = "101402017911"  # 失败
        # accountId = "101402003627"  # 失败
        accountId_info = ["101400001643", "100302229052", "101402017911", "101402003627"]
        sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "CEBUANA")
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "cebuana to cebuana", "pstlAdr": {"adrLine": "001 Central Avenue"}}
        # creditor_agent = {"finInstnId": {"nm": "Chinabanking Corp", "bicFI": "CHBKPHMM"}}
        creditor_agent = {"finInstnId": {"nm": "Chinabanking Corp", "clrSysMmbId": {"clrSysCd": "BRSTN", "mmbId": "010100013"}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="CEBUANA node")
        addenda_info = None
        for accountId in accountId_info:
            cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                    creditor_agent, creditor_intermediary_agent,
                                                                    float(sendFee), sn1, addenda_info, accountId)
            self.client.logger.info(cdtTrfTxInf)
            inner_node = True if sn2 in RMNData.channel_nodes else False
            self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    # 银行不存在
    def test_035_sn_sn_rightNodeUsePayChannel_cebuana(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_cebuana

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PHP"
        recCountry = "PH"
        accountId = "3590333624"  # 失败
        sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "CEBUANA")
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "cebuana to cebuana", "pstlAdr": {"adrLine": "001 Central Avenue"}}
        # creditor_agent = {"finInstnId": {"nm": "Chinabank Savings", "bicFI": "CHSVPHM1"}}
        creditor_agent = {"finInstnId": {"nm": "Chinabank Savings", "clrSysMmbId": {"clrSysCd": "BRSTN", "mmbId": "011129996"}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="CEBUANA node")
        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, accountId)
        self.client.logger.info(cdtTrfTxInf)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    def test_036_sn_sn_rightNodeUsePayChannel_cebuana(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_cebuana

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PHP"
        recCountry = "PH"
        # accountId = "1080073736"  # 通过
        # accountId = "1080762361"  # 通过
        # accountId = "1010061542"  # 通过
        accountId_info = ["1080073736", "1080762361", "1010061542"]
        sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "CEBUANA")
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "cebuana to cebuana", "pstlAdr": {"adrLine": "001 Central Avenue"}}
        creditor_agent = {"finInstnId": {"nm": "Cebuana Lhuillier Bank", "bicFI": "CELRPHM1"}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="CEBUANA node")
        addenda_info = None
        for accountId in accountId_info:
            cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                    creditor_agent, creditor_intermediary_agent,
                                                                    float(sendFee), sn1, addenda_info, accountId)
            self.client.logger.info(cdtTrfTxInf)
            inner_node = True if sn2 in RMNData.channel_nodes else False
            self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    # 银行不存在
    def test_037_sn_sn_rightNodeUsePayChannel_cebuana(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_cebuana

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PHP"
        recCountry = "PH"
        accountId = "636286768681"  # 失败
        sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "CEBUANA")
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "cebuana to cebuana", "pstlAdr": {"adrLine": "001 Central Avenue"}}
        # creditor_agent = {"finInstnId": {"nm": "ING Bank N.V.", "bicFI": "INGBPHMM"}}
        creditor_agent = {"finInstnId": {"nm": "ING Bank N.V.", "clrSysMmbId": {"clrSysCd": "BRSTN", "mmbId": "010660029"}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="CEBUANA node")
        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, accountId)
        self.client.logger.info(cdtTrfTxInf)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    # 银行不存在
    def test_038_sn_sn_rightNodeUsePayChannel_cebuana(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_cebuana

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PHP"
        recCountry = "PH"
        # accountId = "8245000147"
        # accountId = "8155011018"
        # accountId = "8235000882"
        accountId_info = ["8245000147", "8155011018", "8235000882"]
        sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "CEBUANA")
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "cebuana to cebuana", "pstlAdr": {"adrLine": "001 Central Avenue"}}
        # creditor_agent = {"finInstnId": {"nm": "Landbank of the Philippines", "bicFI": "TLBPPHMM"}}
        creditor_agent = {"finInstnId": {"nm": "Landbank of the Philippines", "clrSysMmbId": {"clrSysCd": "BRSTN", "mmbId": "010350025"}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="CEBUANA node")
        addenda_info = None
        for accountId in accountId_info:
            cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                    creditor_agent, creditor_intermediary_agent,
                                                                    float(sendFee), sn1, addenda_info, accountId)
            self.client.logger.info(cdtTrfTxInf)
            inner_node = True if sn2 in RMNData.channel_nodes else False
            self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    # 账户不可用
    def test_039_sn_sn_rightNodeUsePayChannel_cebuana(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_cebuana

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PHP"
        recCountry = "PH"
        # accountId = "3083220008"
        # accountId = "3083220003"
        accountId_info = ["3083220008", "3083220003"]
        sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "CEBUANA")
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "cebuana to cebuana", "pstlAdr": {"adrLine": "001 Central Avenue"}}
        # creditor_agent = {"finInstnId": {"nm": "Metropolitan Bank and Trust Co", "bicFI": "MBTCPHMM"}}
        creditor_agent = {"finInstnId": {"nm": "Metropolitan Bank and Trust Co", "clrSysMmbId": {"clrSysCd": "BRSTN", "mmbId": "010269996"}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="CEBUANA node")
        addenda_info = None
        for accountId in accountId_info:
            cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                    creditor_agent, creditor_intermediary_agent,
                                                                    float(sendFee), sn1, addenda_info, accountId)
            self.client.logger.info(cdtTrfTxInf)
            inner_node = True if sn2 in RMNData.channel_nodes else False
            self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    # 账户不可用
    def test_040_sn_sn_rightNodeUsePayChannel_cebuana(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_cebuana

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PHP"
        recCountry = "PH"
        # accountId = "188810435077"
        # accountId = "1230006673"
        accountId_info = ["188810435077", "1230006673"]
        sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "CEBUANA")
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "cebuana to cebuana", "pstlAdr": {"adrLine": "001 Central Avenue"}}
        # creditor_agent = {"finInstnId": {"nm": "Philippine National Bank", "bicFI": "PNBMPHMM"}}
        creditor_agent = {"finInstnId": {"nm": "Philippine National Bank", "clrSysMmbId": {"clrSysCd": "BRSTN", "mmbId": "010080010"}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="CEBUANA node")
        addenda_info = None
        for accountId in accountId_info:
            cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                    creditor_agent, creditor_intermediary_agent,
                                                                    float(sendFee), sn1, addenda_info, accountId)
            self.client.logger.info(cdtTrfTxInf)
            inner_node = True if sn2 in RMNData.channel_nodes else False
            self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    # bic银行不存在,ncc账户不可用
    def test_041_sn_sn_rightNodeUsePayChannel_cebuana(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_cebuana

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PHP"
        recCountry = "PH"
        accountId = "111112007726"
        sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "CEBUANA")
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "cebuana to cebuana", "pstlAdr": {"adrLine": "001 Central Avenue"}}
        # creditor_agent = {"finInstnId": {"nm": "Philippine Savings Bank", "bicFI": "PHSBPHMM"}}
        creditor_agent = {"finInstnId": {"nm": "Philippine Savings Bank", "clrSysMmbId": {"clrSysCd": "BRSTN", "mmbId": "010269996"}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="CEBUANA node")
        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, accountId)
        self.client.logger.info(cdtTrfTxInf)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    # 银行不存在
    def test_042_sn_sn_rightNodeUsePayChannel_cebuana(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_cebuana

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PHP"
        recCountry = "PH"
        # accountId = "5544143001"
        # accountId = "3292912199"
        # accountId = "0001644820100"
        # accountId = "48644813100"
        accountId_info = ["5544143001", "3292912199", "0001644820100", "48644813100"]
        sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "CEBUANA")
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "cebuana to cebuana", "pstlAdr": {"adrLine": "001 Central Avenue"}}
        # creditor_agent = {"finInstnId": {"nm": "Philippine Veterans Bank", "bicFI": "PHVBPHMM"}}
        creditor_agent = {"finInstnId": {"nm": "Philippine Veterans Bank", "clrSysMmbId": {"clrSysCd": "BRSTN", "mmbId": "010330016"}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="CEBUANA node")
        addenda_info = None
        for accountId in accountId_info:
            cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                    creditor_agent, creditor_intermediary_agent,
                                                                    float(sendFee), sn1, addenda_info, accountId)
            self.client.logger.info(cdtTrfTxInf)
            inner_node = True if sn2 in RMNData.channel_nodes else False
            self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    # 银行不存在
    def test_043_sn_sn_rightNodeUsePayChannel_cebuana(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_cebuana

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PHP"
        recCountry = "PH"
        # accountId = "9004030560"
        # accountId = "9004034191"
        accountId_info = ["9004030560", "9004034191"]
        sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "CEBUANA")
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "cebuana to cebuana", "pstlAdr": {"adrLine": "001 Central Avenue"}}
        creditor_agent = {"finInstnId": {"nm": "Rcbc Savings Bank Inc.", "bicFI": "RCSAPHM1"}}
        # creditor_agent = {"finInstnId": {"nm": "Rcbc Savings Bank Inc.", "clrSysMmbId": {"clrSysCd": "BRSTN", "mmbId": "010330016"}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="CEBUANA node")
        addenda_info = None
        for accountId in accountId_info:
            cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                    creditor_agent, creditor_intermediary_agent,
                                                                    float(sendFee), sn1, addenda_info, accountId)
            self.client.logger.info(cdtTrfTxInf)
            inner_node = True if sn2 in RMNData.channel_nodes else False
            self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    # 账户不可用
    def test_044_sn_sn_rightNodeUsePayChannel_cebuana(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_cebuana

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PHP"
        recCountry = "PH"
        accountId = "210000043"
        sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "CEBUANA")
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "cebuana to cebuana", "pstlAdr": {"adrLine": "001 Central Avenue"}}
        creditor_agent = {"finInstnId": {"nm": "ALLBANK (A Thrift Bank), Inc.", "bicFI": "ALKBPHM2"}}
        # creditor_agent = {"finInstnId": {"nm": "ALLBANK (A Thrift Bank), Inc.", "clrSysMmbId": {"clrSysCd": "BRSTN", "mmbId": "010330016"}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="CEBUANA node")
        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, accountId)
        self.client.logger.info(cdtTrfTxInf)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    # 银行不存在
    def test_045_sn_sn_rightNodeUsePayChannel_cebuana(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_cebuana

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PHP"
        recCountry = "PH"
        accountId = "180000049652"
        sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "CEBUANA")
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "cebuana to cebuana", "pstlAdr": {"adrLine": "001 Central Avenue"}}
        creditor_agent = {"finInstnId": {"nm": "BPI Direct Banko, Inc., A Savings Bank", "bicFI": "BPDIPHM1"}}
        # creditor_agent = {"finInstnId": {"nm": "ALLBANK (A Thrift Bank), Inc.", "clrSysMmbId": {"clrSysCd": "BRSTN", "mmbId": "010330016"}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="CEBUANA node")
        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, accountId)
        self.client.logger.info(cdtTrfTxInf)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    # bic通过,ncc银行不存在
    def test_046_sn_sn_rightNodeUsePayChannel_cebuana(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_cebuana

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PHP"
        recCountry = "PH"
        accountId = "109450542671"
        sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "CEBUANA")
        # debtor = RMNData.debtor
        debtor = {"nm": "RISN To Cebuana",
                  "prvtId": {"othr": {"prtry": "CCPT", "id": "12345678911234"}},
                  "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": sendCountry}}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "Cebuana C R to cebuana", "pstlAdr": {"adrLine": "001 Central Avenue"}}
        creditor_agent = {"finInstnId": {"nm": "Chinatrust Banking Corp", "bicFI": "CTCBPHMM"}}
        # creditor_agent = {"finInstnId": {"nm": "Chinatrust Banking Corp", "clrSysMmbId": {"clrSysCd": "BRSTN", "mmbId": "010690015"}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="CEBUANA node")
        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, accountId)
        self.client.logger.info(cdtTrfTxInf)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    # 账户不可用
    def test_047_sn_sn_rightNodeUsePayChannel_cebuana(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_cebuana

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PHP"
        recCountry = "PH"
        accountId = "639451841062"
        sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "CEBUANA")
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "cebuana to cebuana", "pstlAdr": {"adrLine": "001 Central Avenue"}}
        creditor_agent = {"finInstnId": {"nm": "DCPay Philippines, Inc.", "bicFI": "DCPHPHM1"}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="CEBUANA node")
        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, accountId)
        self.client.logger.info(cdtTrfTxInf)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    # 账户不可用
    def test_048_sn_sn_rightNodeUsePayChannel_cebuana(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_cebuana

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PHP"
        recCountry = "PH"
        accountId = "9177638499"
        sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "CEBUANA")
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "cebuana to cebuana", "pstlAdr": {"adrLine": "001 Central Avenue"}}
        # creditor_agent = {"finInstnId": {"nm": "Globe Gcash", "bicFI": "GLTEPHMT"}}
        creditor_agent = {"finInstnId": {"nm": "Globe Gcash", "clrSysMmbId": {"clrSysCd": "BRSTN", "mmbId": "018040010"}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="CEBUANA node")
        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, accountId)
        self.client.logger.info(cdtTrfTxInf)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    # nium toB测试

    def updateChannelCountry(self, node, country):
        if "sandbox" in self.client.host:
            return
        if self.client.check_db:
            node_sql = f"select node_config from `roxe_node_v3`.node_config_info where node_code='{node}'"
            node_info = self.client.mysql.exec_sql_query(node_sql)[0]
            ctry_info = f'"country": "{country.lower()}"'
            if f'"country": "{country.lower()}"' in node_info["nodeConfig"]:
                return
            else:
                cur_country = re.findall(r'"country": "\w\w"', node_info["nodeConfig"])[0]
                new_info = node_info["nodeConfig"].replace(cur_country, ctry_info)
                up_sql = f"update `roxe_node_v3`.node_config_info set node_config='{new_info}' where node_code='{node}'"
                self.client.mysql.exec_sql_query(up_sql)
                time.sleep(3)
            # print(node_info["nodeConfig"])

    def updateCdtTrfTxInf(self, cdtTrfTxInf, random_msg):
        if "dbtr" in random_msg and random_msg["dbtr"].get("prvtId"):
            random_msg["dbtr"].pop("prvtId")
            if len(random_msg["dbtr"]) == 0:
                random_msg.pop("dbtr")
        if "cdtr" in random_msg and random_msg["cdtr"].get("orgId"):
            random_msg["cdtr"].pop("orgId")
            if len(random_msg["cdtr"]) == 0:
                random_msg.pop("cdtr")
        cdtTrfTxInf = ApiUtils.deepUpdateDict(cdtTrfTxInf, random_msg)
        self.client.logger.info(f"下单参数: {json.dumps(cdtTrfTxInf)}")
        return cdtTrfTxInf

    def test_049_getRouterList_nium_INR_B2B(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium
        self.updateChannelCountry(sn2, "IN")

        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(1000, 2, 10)
        msg = self.client.make_RRLQ_information("USD", "INR", amt, cdtrAgt=agent_info, cd="B2B")
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sn1, "sn-sn")
        self.assertIn("cdtr.orgId", str(router_list), f"B2B中应存在cdtr,orgId")
        self.assertIn("dbtr.orgId", str(router_list), f"B2B中应存在dbtr.orgId")
        self.assertNotIn("prvtId", str(router_list), f"B2B中不应存在prvtId")

    def test_050_getRouterList_nium_INR_B2C(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium
        self.updateChannelCountry(sn2, "IN")

        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(1000, 2, 10)
        msg = self.client.make_RRLQ_information("USD", "INR", amt, cdtrAgt=agent_info, cd="B2C")
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sn1, "sn-sn")
        self.assertIn("dbtr.orgId", str(router_list))
        self.assertIn("cdtr.prvtId", str(router_list))
        self.assertNotIn("dbtr.prvtId", str(router_list))
        self.assertNotIn("cdtr.orgId", str(router_list))

    def test_051_getRouterList_nium_INR_C2B(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium
        self.updateChannelCountry(sn2, "IN")
        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(1000, 2, 10)
        msg = self.client.make_RRLQ_information("USD", "INR", amt, cdtrAgt=agent_info, cd="C2B")
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sn1, "sn-sn")
        self.assertIn("dbtr.prvtId", str(router_list), f"C2B中应存在 dbtr.prvtId")
        self.assertNotIn("dbtr.orgId", str(router_list), f"C2B中应不存在 dbtr,orgId")
        self.assertNotIn("cdtr.prvtId", str(router_list), f"C2B中应不存在 cdtr.prvtId")
        self.assertIn("cdtr.orgId", str(router_list), f"C2B中应存在 cdtr.orgId")

    def test_052_sn_sn_rightNodeUsePayChannel_nium_INR_B2B(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "INR"
        recCountry = "IN"
        accountId = "12345678901234"
        self.updateChannelCountry(sn2, recCountry)

        amt = ApiUtils.randAmount(100, 2, 10)
        nium_node_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _, f_msg = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, None, amt, nium_node_agent, cd="B2B", returnMsg=True
        )
        debtor = {
            "nm": "Michael Stallman",
            "orgId": {"othr": {"prtry": "ACRA", "id": "12345678911234"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": sendCountry},
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "nm": "Edward Nelms", "pstlAdr": {"ctry": recCountry},
            "orgId": {"othr": {"prtry": "ACRA", "id": "12345678911234"}},
            # "orgId": {"anyBIC": "123412345"},
        }
        creditor_agent = {
            "finInstnId": {"nm": "XXXX BANK", "clrSysMmbId": {"clrSysCd": "INFSC", "mmbId": "HSBC0110002"}}}
        sendFee, deliverFee, _ = self.client.step_queryRouter(sn1, sendCurrency, recCurrency, None, amt,
                                                              nium_node_agent, cd="B2B")
        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(
            sendCurrency, recCurrency, debtor, debtor_agent, creditor, creditor_agent, nium_node_agent,
            float(sendFee), sn1, addenda_info, accountId, inAmount=amt
        )
        cdtTrfTxInf = self.updateCdtTrfTxInf(cdtTrfTxInf, f_msg)
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sendFee, deliverFee], self, True)

    def test_053_sn_sn_rightNodeUsePayChannel_nium_INR_C2B(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "INR"
        recCountry = "IN"
        accountId = "12345678901234"
        self.updateChannelCountry(sn2, recCountry)

        debtor = {
            "nm": "Michael Stallman",
            "prvtId": {"othr": {"prtry": "ACRA", "id": "12345678911234"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": sendCountry},
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "nm": "Edward Nelms", "pstlAdr": {"ctry": recCountry},
            "orgId": {"othr": {"prtry": "ACRA", "id": "12345678911234"}},
        }
        creditor_agent = {
            "finInstnId": {"nm": "XXXX BANK", "clrSysMmbId": {"clrSysCd": "INFSC", "mmbId": "HSBC0110002"}}}
        amt = ApiUtils.randAmount(100, 2, 10)
        nium_node_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _, f_msg = self.client.step_queryRouter(sn1, sendCurrency, recCurrency, None, amt,
                                                                     nium_node_agent, cd="C2B", returnMsg=True)
        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(
            sendCurrency, recCurrency, debtor, debtor_agent, creditor, creditor_agent, nium_node_agent,
            float(sendFee), sn1, addenda_info, accountId, inAmount=amt
        )
        cdtTrfTxInf = self.updateCdtTrfTxInf(cdtTrfTxInf, f_msg)
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sendFee, deliverFee], self, True)

    def test_054_sn_sn_rightNodeUsePayChannel_nium_INR_B2C(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "INR"
        recCountry = "IN"
        accountId = "12345678901234"
        self.updateChannelCountry(sn2, recCountry)

        # sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "NIUM")
        debtor = {
            "nm": "Michael Stallman",
            "orgId": {"othr": {"prtry": "ACRA", "id": "12345678911234"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": sendCountry},
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "nm": "Edward Nelms", "pstlAdr": {"ctry": recCountry},
            "prvtId": {"othr": {"prtry": "ACRA", "id": "12345678911234"}},
        }
        creditor_agent = {
            "finInstnId": {"nm": "XXXX BANK", "clrSysMmbId": {"clrSysCd": "INFSC", "mmbId": "HSBC0110002"}}}
        amt = ApiUtils.randAmount(100, 2, 10)
        nium_node_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sn1Fee, sn2Fee, _, f_msg = self.client.step_queryRouter(sn1, sendCurrency, recCurrency, None, amt,
                                                                nium_node_agent, cd="B2C", returnMsg=True)
        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(
            sendCurrency, recCurrency, debtor, debtor_agent, creditor, creditor_agent, nium_node_agent,
            float(sn1Fee), sn1, addenda_info, accountId, inAmount=amt
        )
        cdtTrfTxInf = self.updateCdtTrfTxInf(cdtTrfTxInf, f_msg)
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sn1Fee, sn2Fee], self, True)

    def test_055_sn_sn_rightNodeUsePayChannel_nium_BRL_B2B(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "BRL"
        recCountry = "BR"
        accountId = "12345678901"
        self.updateChannelCountry(sn2, recCountry)

        debtor = {
            "nm": "Michael Stallman",
            "orgId": {"othr": {"prtry": "CCPT", "id": "12345678911234"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": sendCountry},
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "nm": "Edward Nelms",
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": recCountry},
            "orgId": {"othr": {"prtry": "CNPJ", "id": "12345678901234"}},
            "ctctDtls": {"phneNb": "3135446952"}
        }
        creditor_agent = {
            "finInstnId": {"nm": "XXXX BANK", "clrSysMmbId": {"clrSysCd": "BRBCB", "mmbId": "237"}},
            "brnchId": {"id": "1234"}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        nium_node_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _, f_msg = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, None, amt, nium_node_agent, cd="B2B", returnMsg=True
        )
        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(
            sendCurrency, recCurrency, debtor, debtor_agent, creditor, creditor_agent, nium_node_agent,
            float(sendFee), sn1, addenda_info, accountId, inAmount=amt,
        )
        cdtTrfTxInf = self.updateCdtTrfTxInf(cdtTrfTxInf, f_msg)
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sendFee, deliverFee], self, True)

    def test_056_sn_sn_rightNodeUsePayChannel_nium_BRL_C2B(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "BRL"
        recCountry = "BR"
        accountId = "12345678901"
        self.updateChannelCountry(sn2, recCountry)

        debtor = {
            "nm": "Michael Stallman",
            "prvtId": {"othr": {"prtry": "CCPT", "id": "12345678911234"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": sendCountry},
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "nm": "Edward Nelms",
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": recCountry},
            "orgId": {"othr": {"prtry": "CNPJ", "id": "12345678901234"}},
            "ctctDtls": {"phneNb": "3135446952"}
        }
        creditor_agent = {
            "finInstnId": {"nm": "XXXX BANK", "clrSysMmbId": {"clrSysCd": "BRBCB", "mmbId": "237"}},
            "brnchId": {"id": "1234"}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        nium_node_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _, f_msg = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, None, amt, nium_node_agent, cd="C2B", returnMsg=True
        )
        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(
            sendCurrency, recCurrency, debtor, debtor_agent, creditor, creditor_agent, nium_node_agent,
            float(sendFee), sn1, addenda_info, accountId, inAmount=amt,
        )
        cdtTrfTxInf = self.updateCdtTrfTxInf(cdtTrfTxInf, f_msg)
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sendFee, deliverFee], self, True)

    def test_057_sn_sn_rightNodeUsePayChannel_nium_BRL_B2C(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "BRL"
        recCountry = "BR"
        accountId = "12345678901"
        self.updateChannelCountry(sn2, recCountry)

        debtor = {
            "nm": "Michael Stallman",
            "orgId": {"othr": {"prtry": "CCPT", "id": "12345678911234"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": sendCountry},
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "nm": "Edward Nelms",
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": recCountry},
            "prvtId": {"othr": {"prtry": "CNPJ", "id": "12345678901234"}},
            "ctctDtls": {"phneNb": "3135446952"}
        }
        creditor_agent = {
            "finInstnId": {"nm": "XXXX BANK", "clrSysMmbId": {"clrSysCd": "BRBCB", "mmbId": "237"}},
            "brnchId": {"id": "1234"}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        nium_node_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _, f_msg = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, None, amt, nium_node_agent, cd="B2C", returnMsg=True
        )
        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(
            sendCurrency, recCurrency, debtor, debtor_agent, creditor, creditor_agent, nium_node_agent,
            float(sendFee), sn1, addenda_info, accountId, inAmount=amt,
        )
        cdtTrfTxInf = self.updateCdtTrfTxInf(cdtTrfTxInf, f_msg)
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sendFee, deliverFee], self, True)

    def test_058_sn_sn_rightNodeUsePayChannel_nium_CAD_B2B(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "CAD"
        recCountry = "CA"
        accountId = "4929858296666465"
        self.updateChannelCountry(sn2, recCountry)

        debtor = {
            "nm": "Michael Stallman",
            "orgId": {"othr": {"prtry": "CCPT", "id": "12345678911234"}},
            "pstlAdr": {
                "adrLine": "563 Mayo Street",
                "twnNm": "Southfield", "ctrySubDvsn": "Washington", "pstCd": "5360",
                "ctry": sendCountry
            },
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "nm": "Henry G Browne",
            "pstlAdr": {"adrLine": "1123 street", "twnNm": "Mengdh", "ctrySubDvsn": "DC", "pstCd": "112",
                        "ctry": recCountry},
            "orgId": {"othr": {"prtry": "CNPJ", "id": "12345678901234"}},
            "ctctDtls": {"phneNb": "3135446952"}
        }
        creditor_agent = {
            "finInstnId": {"nm": "XXXX BANK", "clrSysMmbId": {"clrSysCd": "CACPA", "mmbId": "61806071"}},
            "brnchId": {"id": "1234"}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        nium_node_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _, f_msg = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, None, amt, nium_node_agent, cd="B2B", returnMsg=True
        )
        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(
            sendCurrency, recCurrency, debtor, debtor_agent, creditor, creditor_agent, nium_node_agent,
            float(sendFee), sn1, addenda_info, accountId, inAmount=amt,
        )
        cdtTrfTxInf = self.updateCdtTrfTxInf(cdtTrfTxInf, f_msg)
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sendFee, deliverFee], self, True)

    def test_059_sn_sn_rightNodeUsePayChannel_nium_CAD_B2C(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "CAD"
        recCountry = "CA"
        accountId = "4929858296666465"
        self.updateChannelCountry(sn2, recCountry)

        debtor = {
            "nm": "Michael Stallman",
            "orgId": {"othr": {"prtry": "CCPT", "id": "12345678911234"}},
            "pstlAdr": {
                "adrLine": "563 Mayo Street",
                "twnNm": "Southfield", "ctrySubDvsn": "Washington", "pstCd": "5360",
                "ctry": sendCountry
            },
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "nm": "Henry G Browne",
            "pstlAdr": {"adrLine": "1123 street", "twnNm": "Mengdh", "ctrySubDvsn": "DC", "pstCd": "112",
                        "ctry": recCountry},
            "prvtId": {"othr": {"prtry": "CNPJ", "id": "12345678901234"}},
            "ctctDtls": {"phneNb": "3135446952"}
        }
        creditor_agent = {
            "finInstnId": {"nm": "XXXX BANK", "clrSysMmbId": {"clrSysCd": "CACPA", "mmbId": "61806071"}},
            "brnchId": {"id": "1234"}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        nium_node_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _, f_msg = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, None, amt, nium_node_agent, cd="B2C", returnMsg=True
        )
        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(
            sendCurrency, recCurrency, debtor, debtor_agent, creditor, creditor_agent, nium_node_agent,
            float(sendFee), sn1, addenda_info, accountId, inAmount=amt,
        )
        cdtTrfTxInf = self.updateCdtTrfTxInf(cdtTrfTxInf, f_msg)
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sendFee, deliverFee], self, True)

    def test_060_sn_sn_rightNodeUsePayChannel_nium_CAD_C2B(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "CAD"
        recCountry = "CA"
        accountId = "4929858296666465"
        self.updateChannelCountry(sn2, recCountry)

        debtor = {
            "nm": "Michael Stallman",
            "prvtId": {"othr": {"prtry": "CCPT", "id": "12345678911234"}},
            "pstlAdr": {
                "adrLine": "563 Mayo Street",
                "twnNm": "Southfield", "ctrySubDvsn": "Washington", "pstCd": "5360",
                "ctry": sendCountry
            },
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "nm": "Henry G Browne",
            "pstlAdr": {"adrLine": "1123 street", "twnNm": "Mengdh", "ctrySubDvsn": "DC", "pstCd": "112",
                        "ctry": recCountry},
            "orgId": {"othr": {"prtry": "CNPJ", "id": "12345678901234"}, "anyBIC": "12341234"},
            "ctctDtls": {"phneNb": "3135446952"}
        }
        creditor_agent = {
            "finInstnId": {"nm": "XXXX BANK", "clrSysMmbId": {"clrSysCd": "CACPA", "mmbId": "61806071"}},
            "brnchId": {"id": "1234"}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        nium_node_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _, f_msg = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, None, amt, nium_node_agent, cd="C2B", returnMsg=True
        )
        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(
            sendCurrency, recCurrency, debtor, debtor_agent, creditor, creditor_agent, nium_node_agent,
            float(sendFee), sn1, addenda_info, accountId, inAmount=amt,
        )
        cdtTrfTxInf = self.updateCdtTrfTxInf(cdtTrfTxInf, f_msg)
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sendFee, deliverFee], self, True)

    def test_061_sn_sn_rightNodeUsePayChannel_nium_USD_B2B(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "USD"
        recCountry = "US"
        accountId = "133563585"
        self.updateChannelCountry(sn2, recCountry)

        debtor = {
            "nm": "Michael Stallman",
            "orgId": {
                "othr": {"prtry": "CCPT", "id": "12345678911234"},
                # "dtAndPlcOfBirth": {"ctryOfBirth": sendCountry, "cityOfBirth": "Southfield", "birthDt": "2004-07-04"}
            },
            "pstlAdr": {
                "adrLine": "563 Mayo Street",
                "twnNm": "Southfield", "ctrySubDvsn": "Michigan", "pstCd": "48235",
                "ctry": sendCountry
            },
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "nm": "Edward Nelms",
            "pstlAdr": {"adrLine": "4961 Woodbridge Lane", "twnNm": "Lincoln", "pstCd": "68501",
                        "ctry": recCountry},
            "orgId": {"othr": {"prtry": "CNPJ", "id": "12345678901234"}},
            "ctctDtls": {"phneNb": "3135446952"}
        }
        creditor_agent = {
            "finInstnId": {"nm": "XXXX BANK", "clrSysMmbId": {"clrSysCd": "USABA", "mmbId": "314078469"}},
            "brnchId": {"id": "1234"}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        nium_node_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _, f_msg = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, None, amt, nium_node_agent, cd="B2B", returnMsg=True
        )
        addenda_info = {"senderOrgIdIssueDate": "2002-1-1"}
        cdtTrfTxInf = self.client.make_channel_RCCT_information(
            sendCurrency, recCurrency, debtor, debtor_agent, creditor, creditor_agent, nium_node_agent,
            float(sendFee), sn1, addenda_info, accountId, inAmount=amt,
        )
        cdtTrfTxInf = self.updateCdtTrfTxInf(cdtTrfTxInf, f_msg)
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sendFee, deliverFee], self, True)

    def test_062_sn_sn_rightNodeUsePayChannel_nium_USD_C2B(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "USD"
        recCountry = "US"
        accountId = "133563585"
        self.updateChannelCountry(sn2, recCountry)

        debtor = {
            "nm": "Michael Stallman",
            "prvtId": {
                "othr": {"prtry": "CCPT", "id": "12345678911234"},
                "dtAndPlcOfBirth": {"ctryOfBirth": sendCountry, "cityOfBirth": "Southfield",
                                    "birthDt": "2004-07-04"}
            },
            "pstlAdr": {
                "adrLine": "563 Mayo Street",
                "twnNm": "Southfield", "ctrySubDvsn": "Michigan", "pstCd": "48235",
                "ctry": sendCountry
            },
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "nm": "Edward Nelms",
            "pstlAdr": {"adrLine": "4961 Woodbridge Lane", "twnNm": "Lincoln", "pstCd": "68501",
                        "ctry": recCountry},
            "orgId": {"othr": {"prtry": "CNPJ", "id": "12345678901234"}},
            "ctctDtls": {"phneNb": "3135446952"}
        }
        creditor_agent = {
            "finInstnId": {"nm": "XXXX BANK", "clrSysMmbId": {"clrSysCd": "USABA", "mmbId": "314078469"}},
            "brnchId": {"id": "1234"}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        nium_node_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _, f_msg = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, None, amt, nium_node_agent, cd="C2B", returnMsg=True
        )
        addenda_info = {"senderOrgIdIssueDate": "2002-1-1"}
        cdtTrfTxInf = self.client.make_channel_RCCT_information(
            sendCurrency, recCurrency, debtor, debtor_agent, creditor, creditor_agent, nium_node_agent,
            float(sendFee), sn1, addenda_info, accountId, inAmount=amt,
        )
        cdtTrfTxInf = self.updateCdtTrfTxInf(cdtTrfTxInf, f_msg)
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sendFee, deliverFee], self, True)

    def test_063_sn_sn_rightNodeUsePayChannel_nium_USD_B2C(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "USD"
        recCountry = "US"
        accountId = "133563585"
        self.updateChannelCountry(sn2, recCountry)

        debtor = {
            "nm": "Michael Stallman",
            "orgId": {
                "othr": {"prtry": "CCPT", "id": "12345678911234", "issr": sendCountry},
            },
            "pstlAdr": {
                "adrLine": "563 Mayo Street",
                "twnNm": "Southfield", "ctrySubDvsn": "Michigan", "pstCd": "48235",
                "ctry": sendCountry
            },
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "nm": "Edward Nelms",
            "pstlAdr": {"adrLine": "4961 Woodbridge Lane", "twnNm": "Lincoln", "pstCd": "68501",
                        "ctry": recCountry},
            "prvtId": {"othr": {"prtry": "CNPJ", "id": "12345678901234"}},
            "ctctDtls": {"phneNb": "3135446952"}
        }
        creditor_agent = {
            "finInstnId": {"nm": "XXXX BANK", "clrSysMmbId": {"clrSysCd": "USABA", "mmbId": "314078469"}},
            "brnchId": {"id": "1234"}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        nium_node_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _, f_msg = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, None, amt, nium_node_agent, cd="B2C", returnMsg=True
        )
        addenda_info = {"senderOrgIdIssueDate": "2002-1-1"}
        cdtTrfTxInf = self.client.make_channel_RCCT_information(
            sendCurrency, recCurrency, debtor, debtor_agent, creditor, creditor_agent, nium_node_agent,
            float(sendFee), sn1, addenda_info, accountId, inAmount=amt,
        )
        cdtTrfTxInf = self.updateCdtTrfTxInf(cdtTrfTxInf, f_msg)
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sendFee, deliverFee], self, True)

    def test_064_sn_sn_rightNodeUsePayChannel_nium_SGD_B2B(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "SGD"
        recCountry = "SG"
        accountId = "4929858296666465"
        self.updateChannelCountry(sn2, recCountry)

        debtor = {
            "nm": "Michael Stallman",
            "orgId": {
                "othr": {"prtry": "CCPT", "id": "12345678911234"},
            },
            "pstlAdr": {
                "adrLine": "563 Mayo Street",
                "twnNm": "abdwd", "ctrySubDvsn": "ahsdfl il", "pstCd": "112233",
                "ctry": sendCountry
            },
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "nm": "Henry G Browne",
            "pstlAdr": {"adrLine": "test address 1", "twnNm": "ahver", "ctry": recCountry},
            "orgId": {"othr": {"prtry": "CNPJ", "id": "12345678901234"}, "anyBIC": "FAEASGSG"},
            "ctctDtls": {"phneNb": "3135446952"}
        }
        creditor_agent = {
            # "finInstnId": {"bicFI": "FAEASGSG"},
            "brnchId": {"id": "370"}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        nium_node_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _, f_msg = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, None, amt, nium_node_agent, cd="B2B", returnMsg=True
        )
        addenda_info = {"senderOrgIdIssueDate": "1891-1-1"}
        cdtTrfTxInf = self.client.make_channel_RCCT_information(
            sendCurrency, recCurrency, debtor, debtor_agent, creditor, nium_node_agent, None,
            float(sendFee), sn1, addenda_info, accountId, inAmount=amt,
        )
        cdtTrfTxInf = self.updateCdtTrfTxInf(cdtTrfTxInf, f_msg)
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sendFee, deliverFee], self, True)

    def test_065_sn_sn_rightNodeUsePayChannel_nium_SGD_B2C(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "SGD"
        recCountry = "SG"
        accountId = "4929858296666465"
        self.updateChannelCountry(sn2, recCountry)

        debtor = {
            "nm": "Michael Stallman",
            "orgId": {"othr": {"prtry": "CCPT", "id": "12345678911234"}, "lei": "12345xx"},
            "pstlAdr": {
                "adrLine": "563 Mayo Street",
                "twnNm": "abdwd", "ctrySubDvsn": "ahsdfl il", "pstCd": "112233",
                "ctry": sendCountry
            },
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "nm": "Henry G Browne",
            "pstlAdr": {"adrLine": "test address 1", "twnNm": "ahver", "ctry": recCountry},
            "prvtId": {"othr": {"prtry": "CNPJ", "id": "12345678901234"}},
            "ctctDtls": {"phneNb": "3135446952"}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        nium_node_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _, f_msg = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, None, amt, nium_node_agent, cd="B2B", returnMsg=True
        )
        addenda_info = {"senderOrgIdIssueDate": "1891-1-1"}
        cdtTrfTxInf = self.client.make_channel_RCCT_information(
            sendCurrency, recCurrency, debtor, debtor_agent, creditor, nium_node_agent, None,
            float(sendFee), sn1, addenda_info, accountId, inAmount=amt,
        )
        cdtTrfTxInf = self.updateCdtTrfTxInf(cdtTrfTxInf, f_msg)
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sendFee, deliverFee], self, True)

    def test_066_sn_sn_rightNodeUsePayChannel_nium_EUR_B2B(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "EUR"
        recCountry = "FR"
        accountId = "GB29NWBK60161331926819"
        self.updateChannelCountry(sn2, recCountry)

        debtor = {
            "nm": "Michael Stallman",
            "orgId": {
                "othr": {"prtry": "CCPT", "id": "12345678911234"},
                # "dtAndPlcOfBirth": {"birthDt": "2004-07-04"}
            },
            "pstlAdr": {
                "adrLine": "563 Mayo Street", "twnNm": "Southfield", "ctrySubDvsn": "Washington", "pstCd": "5360",
                "ctry": sendCountry
            },
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "nm": "Henry G Browne",
            "pstlAdr": {"adrLine": "1123 street", "twnNm": "Mengdh", "ctrySubDvsn": "DC", "pstCd": "112",
                        "ctry": recCountry},
            "orgId": {"othr": {"prtry": "CNPJ", "id": "12345678901234"}, "anyBIC": "CHASFRP0"},
            # "ctctDtls": {"phneNb": "3135446952"}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        nium_node_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _, f_msg = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, None, amt, nium_node_agent, cd="B2B", returnMsg=True
        )
        addenda_info = None

        cdtTrfTxInf = self.client.make_channel_RCCT_information(
            sendCurrency, recCurrency, debtor, debtor_agent, creditor, nium_node_agent, None,
            float(sendFee), sn1, addenda_info, accountId, inAmount=amt,
        )
        cdtTrfTxInf = self.updateCdtTrfTxInf(cdtTrfTxInf, f_msg)
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sendFee, deliverFee], self, True)

    def test_067_sn_sn_rightNodeUsePayChannel_nium_EUR_C2B(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "EUR"
        recCountry = "FR"
        accountId = "GB29NWBK60161331926819"
        self.updateChannelCountry(sn2, recCountry)

        debtor = {
            "nm": "Michael Stallman",
            "prvtId": {
                "othr": {"prtry": "CCPT", "id": "12345678911234"},
                # "dtAndPlcOfBirth": {"birthDt": "2004-07-04"}
            },
            "pstlAdr": {
                "adrLine": "563 Mayo Street", "twnNm": "Southfield", "ctrySubDvsn": "Washington", "pstCd": "5360",
                "ctry": sendCountry
            },
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "nm": "Henry G Browne",
            "pstlAdr": {"adrLine": "1123 street", "twnNm": "Mengdh", "ctrySubDvsn": "DC", "pstCd": "112",
                        "ctry": recCountry},
            "orgId": {"othr": {"prtry": "CNPJ", "id": "12345678901234"}, "anyBIC": "CHASFRP0"},
            # "ctctDtls": {"phneNb": "3135446952"}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        nium_node_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _, f_msg = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, None, amt, nium_node_agent, cd="C2B", returnMsg=True
        )
        addenda_info = None

        cdtTrfTxInf = self.client.make_channel_RCCT_information(
            sendCurrency, recCurrency, debtor, debtor_agent, creditor, nium_node_agent, None,
            float(sendFee), sn1, addenda_info, accountId, inAmount=amt,
        )
        cdtTrfTxInf = self.updateCdtTrfTxInf(cdtTrfTxInf, f_msg)
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sendFee, deliverFee], self, True)

    def test_068_sn_sn_rightNodeUsePayChannel_nium_EUR_B2C(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "EUR"
        recCountry = "FR"
        accountId = "GB29NWBK60161331926819"
        self.updateChannelCountry(sn2, recCountry)

        debtor = {
            "nm": "Michael Stallman",
            "orgId": {
                "othr": {"prtry": "CCPT", "id": "12345678911234"},
                # "dtAndPlcOfBirth": {"birthDt": "2004-07-04"}
            },
            "pstlAdr": {
                "adrLine": "563 Mayo Street", "twnNm": "Southfield", "ctrySubDvsn": "Washington", "pstCd": "5360",
                "ctry": sendCountry
            },
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "nm": "Henry G Browne",
            "pstlAdr": {"adrLine": "1123 street", "twnNm": "Mengdh", "ctrySubDvsn": "DC", "pstCd": "112",
                        "ctry": recCountry},
            "prvtId": {"othr": {"prtry": "CNPJ", "id": "12345678901234"}},
            # "ctctDtls": {"phneNb": "3135446952"}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        nium_node_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _, f_msg = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, None, amt, nium_node_agent, cd="C2B", returnMsg=True
        )
        addenda_info = None

        cdtTrfTxInf = self.client.make_channel_RCCT_information(
            sendCurrency, recCurrency, debtor, debtor_agent, creditor, nium_node_agent, None,
            float(sendFee), sn1, addenda_info, accountId, inAmount=amt,
        )

        cdtTrfTxInf = self.updateCdtTrfTxInf(cdtTrfTxInf, f_msg)
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sendFee, deliverFee], self, True)

    def test_069_getRouterList_GME_C2C(self):
        sn1 = RMNData.sn_usd_us
        sn2 = "gmeremit2d5a"

        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(1000, 2, 10)
        msg = self.client.make_RRLQ_information("USD", "KRW", amt, cdtrAgt=agent_info, cd="C2C")
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sn1, "sn-sn")
        self.assertIn("prvtId", str(router_list))
        self.assertNotIn("orgId", str(router_list))

    def test_070_getRouterList_Rana_C2C(self):
        sn1 = RMNData.sn_usd_us
        sn2 = "ranaexp5a1sd"

        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(sn2, "SN")
        amt = ApiUtils.randAmount(100, 2, 10)
        msg = self.client.make_RRLQ_information("USD", "BRL", amt, cdtrAgt=agent_info, cd="C2C")
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.checkRouterList(router_list, req_msg, sn1, "sn-sn")
        self.assertIn("prvtId", str(router_list))
        self.assertNotIn("orgId", str(router_list))

    def test_071_sn_sn_rightNodeUsePayChannel_TerraPay_PHP_pendingMsgSendSN1(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay
        if "sandbox" in RMNData.host: sn2 = "huuzj2hpycrx"

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "PHP"
        r_country = "PH"
        r_account_number = "20408277204478"
        r_name = "RANDY OYUGI"
        r_bank_name = "Asia United Bank"
        r_bank_code = "AUBKPHMM"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        sendFee, deliverFee, _ = self.client.step_queryRouter(sn1, "USD", r_currency, creditor_agent=creditor_intermediary_agent)
        cdtTrfTxInf = self.client.make_channel_RCCT_information(
            "USD", r_currency, debtor, debtor_agent, creditor, creditor_agent, creditor_intermediary_agent,
            float(sendFee), sn1, addenda_info, r_account_number
        )
        cdtTrfTxInf["dbtr"]["pstlAdr"]["ctry"] = None
        # cdtTrfTxInf["dbtr"]["pstlAdr"].pop("ctry")
        # cdtTrfTxInf["addenda"] = None
        # print(json.dumps(cdtTrfTxInf))
        self.client.transactionFlow_sn_sn(
            sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
            isInnerNode=True, isPending=True
        )

    def test_072_sn_sn_rightNodeUsePayChannel_nium_INR_pendingMsgSendSN1(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "INR"
        recCountry = "IN"
        accountId = "12345678901234"
        self.updateChannelCountry(sn2, recCountry)

        debtor = {
            "nm": "Michael Stallman",
            "prvtId": {"othr": {"prtry": "ACRA", "id": "12345678911234"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": sendCountry},
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "nm": "Edward Nelms", "pstlAdr": {"ctry": recCountry},
            "prvtId": {"othr": {"prtry": "ACRA", "id": "12345678911234"}},
        }
        creditor_agent = {
            "finInstnId": {"nm": "XXXX BANK", "clrSysMmbId": {"clrSysCd": "INFSC", "mmbId": "HSBC0110002"}}}
        amt = ApiUtils.randAmount(100, 2, 10)
        nium_node_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _, f_msg = self.client.step_queryRouter(sn1, sendCurrency, recCurrency, None, amt,
                                                                     nium_node_agent, cd="C2C", returnMsg=True)
        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(
            sendCurrency, recCurrency, debtor, debtor_agent, creditor, creditor_agent, nium_node_agent,
            float(sendFee), sn1, addenda_info, accountId, inAmount=amt
        )
        cdtTrfTxInf = self.updateCdtTrfTxInf(cdtTrfTxInf, f_msg)
        cdtTrfTxInf["cdtrAgt"]["finInstnId"]["clrSysMmbId"]["mmbId"] = "HSBC1234"
        # cdtTrfTxInf["cdtr"]["pstlAdr"]["ctry"] = None
        self.client.transactionFlow_sn_sn(
            sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self,
            isInnerNode=True, isPending=True
        )

    def test_073_sn_sn_rightNodeUsePayChannel_gcash_PHP_pendingMsgSendSN1(self):
        sn1 = RMNData.sn_usd_us
        # sn2 = RMNData.sn_php_ph
        # sn2 = "idlzjsbeza4m"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": "rich bank"}}
        cdtrAcct = {"schmeNm": {"prtry": "PH"}, "issr": "GCASH", "acctId": "09686470321", "ccy": "PHP"}
        amt = ApiUtils.randAmount(10, 2, 3)
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "USD", "PHP", cdtrAcct=cdtrAcct, tp='EWALLET', amount=amt)

        cdtTrfTxInf = self.client.make_RCCT_information(
            "USD", "PHP", RMNData.prvtId, debtor_agent, RMNData.prvtId_b, creditor_agent, sn1_fee, sn1,
            cdtrAcct=cdtrAcct, inAmount=amt
        )
        cdtTrfTxInf["pmtTpInf"] = {"lclInstrm": {"cd": "EWALLET"}}
        cdtTrfTxInf["cdtr"]["nm"] = "OPERATIONS ROLLOUTS SUSPENDED"
        cdtTrfTxInf["cdtr"]["pstlAdr"]["ctry"] = "PH"
        cdtTrfTxInf["dbtr"]["prvtId"]["othr"]["prtry"] = "DRIVER_LICENSE"
        # cdtTrfTxInf["splmtryData"]["addenda"]["senderSourceOfFund"] = "bank account"
        cdtTrfTxInf["splmtryData"]["addenda"]["receiverWalletCode"] = "GCASH"

        ts_headers = self.client.make_header(sn1, RMNData.api_key, "RERQ")
        msg_header = self.client.make_msg_header(sn1, ts_headers["msgId"])
        rate_info, req_msg = self.client.get_exchange_rate(RMNData.sec_key, ts_headers, msg_header, "USD", cdtTrfTxInf["intrBkSttlmAmt"]["amt"], "PHP")
        self.client.checkCodeAndMessage(rate_info)

        self.client.transactionFlow_sn_sn(
            sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=True,
            isRPP=True, rateInfo=rate_info, chg_fees=["USD"], isPending=True
        )

    def test_074_sn_sn_rightNodeUsePayChannel_cebuana_pendingMsgSendSN1(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_cebuana

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PHP"
        recCountry = "PH"
        # accountId = "916100000424"  # 通过
        # accountId = "5120019630"  # 失败
        # accountId = "7010010691"  # 失败
        # accountId = "003010000426"  # 失败
        # accountId = "005120019633"  # 失败
        # accountId = "4332515"  # 失败
        # accountId = "4762018"  # 失败
        # accountId = "005120019630"  # 失败
        # accountId = "7000110622011110"  # 失败
        # accountId = "7000110622022220"  # 失败
        # accountId = "7000110622033330"  # 失败
        # accountId = "7000110622023450"  # 失败
        # accountId = "7000110622023450"  # 失败
        # accountId = "7000110622009870"  # 失败
        accountId = "7000110622010100"  # 失败
        # accountId_info = ["916100000424", "5120019630", "7010010691", "003010000426", "005120019633", "4332515", "4762018", "005120019630", "7000110622011110", "7000110622022220", "7000110622033330", "7000110622023450", "7000110622009870", "7000110622010100"]
        sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "CEBUANA")
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "cebuana to cebuana", "pstlAdr": {"adrLine": "001 Central Avenue"}}
        # creditor_agent = {"finInstnId": {"nm": "Asia United Bank", "bicFI": "AUBKPHMM"}}
        creditor_agent = {"finInstnId": {"nm": "Asia United Bank", "clrSysMmbId": {"clrSysCd": "BRSTN", "mmbId": "011020011"}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="CEBUANA node")
        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent,
                                                                creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, accountId)
        self.client.logger.info(cdtTrfTxInf)
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, True,
                                          isPending=True)

    def test_075_sn_sn_rightNodeUsePayChannel_gcash_PHP_pendingMsgSendSN1(self):
        sn1 = RMNData.sn_usd_us
        # sn2 = RMNData.sn_php_ph
        # sn2 = "idlzjsbeza4m"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": "rich bank"}}
        cdtrAcct = {"schmeNm": {"prtry": "PH"}, "issr": "GCASH", "acctId": "09064554429", "ccy": "PHP"}
        amt = ApiUtils.randAmount(10, 2, 3)
        amt = 1.9
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "USD", "PHP", cdtrAcct=cdtrAcct, tp='EWALLET', amount=amt)

        cdtTrfTxInf = self.client.make_RCCT_information(
            "USD", "PHP", RMNData.prvtId, debtor_agent, RMNData.prvtId_b, creditor_agent, sn1_fee, sn1,
            cdtrAcct=cdtrAcct, inAmount=amt
        )
        cdtTrfTxInf["pmtTpInf"] = {"lclInstrm": {"cd": "EWALLET"}}
        cdtTrfTxInf["cdtr"]["nm"] = "CARLOS ALFRED TABILLA"
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
            isRPP=True, rateInfo=rate_info, chg_fees=["USD"], isPending=True
        )

    def test_076_sn_sn_rightNodeUsePayChannel_TerraPay_PHP_preCheck(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay
        if "sandbox" in RMNData.host: sn2 = "huuzj2hpycrx"  # sandbox

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "PHP"
        r_country = "PH"
        r_account_number = "20408277204478"
        r_name = "RANDY OYUGI"
        r_bank_name = "Asia United Bank"
        r_bank_code = "AUBKPHMM"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        amt = ApiUtils.randAmount(100, 2, 20)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", r_currency, creditor_agent=creditor_intermediary_agent, amount=amt)
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent, sn1_fee,
                                                                sn1, addenda_info, r_account_number, inAmount=amt)
        cdtTrfTxInf["dbtr"]["pstlAdr"]["ctry"] = "US"
        popKey = {
            "dbtr.pstlAdr.twnNm": "[\\\"senderCity can't be blank\\\"]",
            "dbtr.ctctDtls.phneNb": "[\\\"senderPhone can't be blank\\\"]",
            "cdtrAcct.ccy": "\"outInfo receiveCurrency is empty",
            # "dbtr.nm": "[\\\"senderLastName can't be blank\\\",\\\"senderFirstName can't be blank\\\"]",
            "dbtr.pstlAdr.adrLine": "[\\\"senderAddress can't be blank\\\"]",
            "dbtr.pstlAdr.ctry": "[\\\"senderCountry can't be null\\\"]",
            "purp.desc": "[\\\"purpose can't be blank\\\"]",
            "dbtr.prvtId.dtAndPlcOfBirth.birthDt": "[\\\"senderBirthday can't be blank\\\"]",
            "cdtr.pstlAdr.ctry": "receiverCountry can't be blank",
            "rltnShp.desc": "[\\\"senderBeneficiaryRelationship can't be blank\\\"]",
            "senderSourceOfFund": "[\\\"senderSourceOfFund can't be blank\\\"]",
            "senderIdExpireDate": "[\\\"senderIdExpireDate can't be blank\\\"]",
        }
        for k, v in popKey.items():
            tmp_info = copy.deepcopy(cdtTrfTxInf)
            if "." in k:
                new_dict = ApiUtils.generateDict(k, None)
                tmp_info = ApiUtils.deepUpdateDict(tmp_info, new_dict)
            else:
                tmp_info["splmtryData"]["addenda"][k] = None
            msg_id = self.client.make_msg_id()
            tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id)
            tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
            tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, tmp_info)
            self.assertEqual(tx_info["code"], "00100111")
            self.assertEqual(tx_info["message"], v)

    def test_077_sn_sn_rightNodeUsePayChannel_TerraPay_PHP_preCheck(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay
        if "sandbox" in RMNData.host: sn2 = "huuzj2hpycrx"  # sandbox

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "PHP"
        r_country = "PH"
        r_account_number = "20408277204478"
        r_name = "RANDY OYUGI"
        r_bank_name = "Asia United Bank"
        r_bank_code = "AUBKPHMM"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        amt = ApiUtils.randAmount(100, 2, 20)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", r_currency, creditor_agent=creditor_intermediary_agent, amount=amt)
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_intermediary_agent, None, sn1_fee,
                                                                sn1, addenda_info, r_account_number, inAmount=amt)
        cdtTrfTxInf["dbtr"]["pstlAdr"]["ctry"] = "US"
        # print(json.dumps(cdtTrfTxInf))
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.assertEqual(tx_info["code"], "00100111")
        self.assertEqual(tx_info["message"], "[\\\"receiverBankBIC can't be blank\\\"]")

    def test_078_sn_sn_rightNodeUsePayChannel_nium_INR_preCheck(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "INR"
        recCountry = "IN"
        accountId = "12345678901234"
        amt = ApiUtils.randAmount(100, 2, 20)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, creditor_agent=creditor_intermediary_agent, amount=amt
        )
        # sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "NIUM")
        debtor = {
            "nm": "Michael Stallman",
            "prvtId": {"othr": {"prtry": "CCPT", "id": "12345678911234"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": sendCountry},
            "ctryOfRes": "US"}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "Edward Nelms", "ctryOfRes": recCountry, "pstlAdr": {"ctry": recCountry}}
        creditor_agent = {"finInstnId": {"nm": "XXXX BANK", "clrSysMmbId": {"clrSysCd": "INFSC", "mmbId": "HSBC0110002"}}}

        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                sendFee, sn1, addenda_info, accountId, amt)
        cdtTrfTxInf["purp"] = {"desc": "Family Maintenance"}

        self.client.logger.info(json.dumps(cdtTrfTxInf))
        popKey = {
            "cdtrAcct.ccy": "\"outInfo receiveCurrency is empty",
            "dbtr.nm": "senderFirstName can not be empty",
            "dbtr.pstlAdr.adrLine": "senderAddress can not be empty",
            "purp.desc": "purpose can not be empty",
            "cdtr.nm": "receiverFirstName can not be empty",
            "cdtrAcct.acctId": "receiverAccountNumber can not be empty",
            "dbtr.pstlAdr.ctry": "senderCountry can not be empty",
            "cdtr.pstlAdr.ctry": "ReceiverCountry is blank or invalid",
        }
        for k, v in popKey.items():
            tmp_info = copy.deepcopy(cdtTrfTxInf)
            if "." in k:
                new_dict = ApiUtils.generateDict(k, None)
                tmp_info = ApiUtils.deepUpdateDict(tmp_info, new_dict)
            else:
                tmp_info["splmtryData"]["addenda"][k] = None
            msg_id = self.client.make_msg_id()
            tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id)
            tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
            tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, tmp_info)
            self.assertEqual(tx_info["code"], "00100111")
            self.assertEqual(tx_info["message"], v)

    def test_079_sn_sn_rightNodeUsePayChannel_nium_INR_preCheck(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "INR"
        recCountry = "IN"
        accountId = "12345678901234"
        amt = ApiUtils.randAmount(100, 2, 20)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, creditor_agent=creditor_intermediary_agent, amount=amt
        )
        # sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "NIUM")
        debtor = {
            "nm": "Michael Stallman",
            "prvtId": {"othr": {"prtry": "CCPT", "id": "12345678911234"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": sendCountry},
            "ctryOfRes": "US"}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "Edward Nelms", "ctryOfRes": recCountry, "pstlAdr": {"ctry": recCountry}}
        creditor_agent = {"finInstnId": {"nm": "XXXX BANK", "clrSysMmbId": {"clrSysCd": "INFSC", "mmbId": "HSBC0110002"}}}

        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_intermediary_agent, None,
                                                                sendFee, sn1, addenda_info, accountId, amt)
        cdtTrfTxInf["purp"] = {"desc": "Family Maintenance"}

        self.client.logger.info(json.dumps(cdtTrfTxInf))
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.assertEqual(tx_info["code"], "00100111")
        self.assertEqual(tx_info["message"], "receiverBankNCC can not be empty")

    def test_080_sn_sn_rightNodeUsePayChannel_gcash_PHP_preCheck(self):
        sn1 = RMNData.sn_usd_us
        # sn2 = RMNData.sn_php_ph
        # sn2 = "idlzjsbeza4m"
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": "rich bank"}}
        cdtrAcct = {"schmeNm": {"prtry": "PH"}, "issr": "GCASH", "acctId": "09686470321", "ccy": "PHP"}
        amt = ApiUtils.randAmount(10, 2, 3)
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "USD", "PHP", cdtrAcct=cdtrAcct, tp='EWALLET', amount=amt)

        cdtTrfTxInf = self.client.make_RCCT_information(
            "USD", "PHP", RMNData.prvtId, debtor_agent, RMNData.prvtId_b, creditor_agent, sn1_fee, sn1,
            cdtrAcct=cdtrAcct, inAmount=amt
        )
        cdtTrfTxInf["pmtTpInf"] = {"lclInstrm": {"cd": "EWALLET"}}
        cdtTrfTxInf["cdtr"]["nm"] = "OPERATIONS ROLLOUTS SUSPENDED"
        cdtTrfTxInf["cdtr"]["pstlAdr"]["ctry"] = "PH"
        cdtTrfTxInf["dbtr"]["prvtId"]["othr"]["prtry"] = "DRIVER_LICENSE"
        cdtTrfTxInf["splmtryData"]["addenda"]["senderSourceOfFund"] = "bank account"
        cdtTrfTxInf["splmtryData"]["addenda"]["receiverWalletCode"] = "GCASH"

        popKeys = {
            "cdtrAcct.ccy": "\"outInfo receiveCurrency is empty",
            "dbtr.nm": "parameter error --> senderFirstName is empty",
            "cdtr.nm": "parameter error --> receiverFirstName is empty",
            "cdtrAcct.acctId": "parameter error --> receiverAccountNumber is empty",
            "rltnShp.desc": "parameter error --> senderBeneficiaryRelationship is empty",
            "dbtr.pstlAdr.ctry": "parameter error --> SenderCountry is empty",
            "senderSourceOfFund": "parameter error --> senderSourceOfFund is empty",
            "receiverWalletCode": "parameter error --> receiverWalletCode is empty",
        }
        for k, v in popKeys.items():
            tmp_info = copy.deepcopy(cdtTrfTxInf)
            if "." in k:
                new_dict = ApiUtils.generateDict(k, None)
                tmp_info = ApiUtils.deepUpdateDict(tmp_info, new_dict)
            else:
                tmp_info["splmtryData"]["addenda"][k] = None
            msg_id = self.client.make_msg_id()
            tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id)
            tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
            tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, tmp_info)
            self.assertEqual(tx_info["code"], "00100111")
            self.assertEqual(tx_info["message"], v)

    def test_081_sn_sn_rightNodeUsePayChannel_cebuana_preCheck(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_cebuana

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PHP"
        recCountry = "PH"
        accountId = "7000110622010100"  # 失败
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="CEBUANA node")
        amount = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "PHP", creditor_agent=creditor_intermediary_agent, amount=amount)
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "cebuana to cebuana", "pstlAdr": {"adrLine": "001 Central Avenue"}}
        creditor_agent = {"finInstnId": {"nm": "Asia United Bank", "bicFI": "AUBKPHMM"}}
        # creditor_agent = {"finInstnId": {"nm": "Asia United Bank", "clrSysMmbId": {"clrSysCd": "BRSTN", "mmbId": "011020011"}}}

        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent,
                                                                creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                sn1_fee, sn1, addenda_info, accountId, inAmount=amount)
        self.client.logger.info(cdtTrfTxInf)
        popKeys = {
            # "cdtrAgt.finInstnId.bicFI": "",
            "cdtrAcct.ccy": "\"outInfo receiveCurrency is empty",
            "dbtr.nm": "senderFirstName cannot be empty",
            "dbtr.pstlAdr.adrLine": "senderAddress cannot be empty",
            "cdtr.nm": "receiverFirstName cannot be empty",
            "cdtrAcct.acctId": "receiverAccountNumber cannot be empty",
            # "cdtrAgt.finInstnId.clrSysMmbId.clrSysCd": "",
            # "cdtrAgt.finInstnId.clrSysMmbId.mmbId": "",
            "dbtr.pstlAdr.ctry": "senderCountry cannot be empty",
            "cdtr.pstlAdr.adrLine": "receiverAddress cannot be empty",
        }
        for k, v in popKeys.items():
            tmp_info = copy.deepcopy(cdtTrfTxInf)
            if "." in k:
                new_dict = ApiUtils.generateDict(k, None)
                tmp_info = ApiUtils.deepUpdateDict(tmp_info, new_dict)
            else:
                tmp_info["splmtryData"]["addenda"][k] = None
            msg_id = self.client.make_msg_id()
            tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id)
            tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
            tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, tmp_info)
            self.assertEqual(tx_info["code"], "00100111")
            self.assertEqual(tx_info["message"], v)

    def test_082_sn_sn_rightNodeUsePayChannel_cebuana_preCheck(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_cebuana

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PHP"
        recCountry = "PH"
        accountId = "7000110622010100"  # 失败
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="CEBUANA node")
        amount = ApiUtils.randAmount(100, 2, 30)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", "PHP", creditor_agent=creditor_intermediary_agent, amount=amount)
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "cebuana to cebuana", "pstlAdr": {"adrLine": "001 Central Avenue"}}
        creditor_agent = {"finInstnId": {"nm": "Asia United Bank", "bicFI": "AUBKPHMM"}}
        # creditor_agent = {"finInstnId": {"nm": "Asia United Bank", "clrSysMmbId": {"clrSysCd": "BRSTN", "mmbId": "011020011"}}}

        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent,
                                                                creditor,
                                                                creditor_intermediary_agent, None,
                                                                sn1_fee, sn1, addenda_info, accountId, inAmount=amount)
        self.client.logger.info(cdtTrfTxInf)
        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.assertEqual(tx_info["code"], "00100111")
        # self.assertEqual(tx_info["message"], v)

    def test_083_sn_sn_cdtrAgtGiveSNRoxeId_sameCurrency(self):
        """
        主流程: sn_sn, cdtrAgt有roxeId, 且为SN, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amount)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId_b, creditor_agent, sn1_fee, sn1, inAmount=amount)
        popKeys = {
            "cdtrAcct.ccy": "\"outInfo receiveCurrency is empty",
            "cdtrAcct.nm": "receiverAccountName can not be null",
            "cdtr.nm": "receiverFirstName can not be null",
            "cdtrAcct.acctId": "receiverAccountNumber can not be null",
        }
        for k, v in popKeys.items():
            tmp_info = copy.deepcopy(cdtTrfTxInf)
            if "." in k:
                new_dict = ApiUtils.generateDict(k, None)
                tmp_info = ApiUtils.deepUpdateDict(tmp_info, new_dict)
            else:
                tmp_info["splmtryData"]["addenda"][k] = None
            msg_id = self.client.make_msg_id()
            tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id)
            tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
            tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, tmp_info)
            self.assertEqual(tx_info["code"], "00100111")
            self.assertEqual(tx_info["message"], v)

    def test_084_sn_sn_cdtrAgtGiveSNRoxeId_sameCurrency(self):
        """
        主流程: sn_sn, cdtrAgt有roxeId, 且为SN, cdtrIntrmyAgt及intrmyAgt为空
        """
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent, amount=amount)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", RMNData.prvtId, debtor_agent, RMNData.prvtId_b, creditor_agent, sn1_fee, sn1, inAmount=amount)
        cdtTrfTxInf["cdtr"]["prvtId"]["othr"] = None

        msg_id = self.client.make_msg_id()
        tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id)
        tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
        tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, cdtTrfTxInf)
        self.assertEqual(tx_info["code"], "00100111")
        self.assertEqual(tx_info["message"], "receiverIdType can not be null")

    def test_085_sn_sn_rightNodeUsePayChannel_ipay_AUD_NCC(self):
        sn1 = RMNData.sn_usd_us
        sn2 = "ifomx232tdly"
        if "sandbox" in RMNData.host or "prod" in RMNData.host: sn2 = "ipayrmta1au1"

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")

        creditor_agent = {"finInstnId": {"nm": "AU BANK", "clrSysMmbId": {"clrSysCd": "AUBSB"}}}
        # creditor_agent["finInstnId"]["clrSysMmbId"]["mmbId"] = "123456789"  # ncc编码不在列表中，应报错
        creditor_agent["finInstnId"]["clrSysMmbId"]["mmbId"] = "082-99123456789"  # ncc编码在列表中,下单成功
        # creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, _, r_msg = self.client.step_queryRouter(sn1, "USD", "AUD", creditor_agent=creditor_agent, amount=amount, returnMsg=True)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "AUD", RMNData.prvtId, debtor_agent, RMNData.prvtId_b, creditor_agent, sn1_fee, sn1, inAmount=amount)
        cdtTrfTxInf = ApiUtils.deepUpdateDict(cdtTrfTxInf, r_msg)
        cdtTrfTxInf["dbtr"]["ctctDtls"] = {"phneNb": "1234123412"}
        cdtTrfTxInf["cdtr"]["ctctDtls"] = {"phneNb": "1234123412"}
        cdtTrfTxInf["cdtr"]["pstlAdr"]["ctry"] = "AU"
        cdtTrfTxInf["cdtrAcct"]["ccy"] = "AUD"
        cdtTrfTxInf["splmtryData"]["addenda"]["senderIdIssueDate"] = "2018-07-03"
        cdtTrfTxInf["splmtryData"]["addenda"]["senderIdExpireDate"] = "2038-07-03"
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, True)

    def test_086_sn_sn_rightNodeUsePayChannel_ipay_INR_NCC(self):
        sn1 = RMNData.sn_usd_us
        sn2 = "ifomx232tdly"

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")

        creditor_agent = {"finInstnId": {"nm": "UTKARSH SMALL FINANCE BANK", "clrSysMmbId": {"clrSysCd": "INFSC"}}}
        # creditor_agent["finInstnId"]["clrSysMmbId"]["mmbId"] = "123456789"  # ncc编码不在列表中，应报错
        # creditor_agent["finInstnId"]["clrSysMmbId"]["mmbId"] = "UTKS"  # ncc编码在列表中,下单成功
        creditor_agent["finInstnId"]["clrSysMmbId"]["mmbId"] = "BOTM0ND3611"  # ncc编码在列表中,下单成功
        # creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amount = ApiUtils.randAmount(85, 2, 80)
        sn1_fee, sn2_fee, _, r_msg = self.client.step_queryRouter(sn1, "USD", "INR", creditor_agent=creditor_agent, amount=amount, returnMsg=True)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "INR", RMNData.prvtId, debtor_agent, RMNData.prvtId_b, creditor_agent, sn1_fee, sn1, inAmount=amount)
        cdtTrfTxInf["dbtr"]["ctctDtls"] = {"phneNb": "1234123412"}
        cdtTrfTxInf["cdtr"]["pstlAdr"]["ctry"] = "IN"
        cdtTrfTxInf = ApiUtils.deepUpdateDict(cdtTrfTxInf, r_msg)
        cdtTrfTxInf["splmtryData"]["addenda"]["senderIdIssueDate"] = "2018-07-03"
        cdtTrfTxInf["splmtryData"]["addenda"]["senderIdExpireDate"] = "2038-07-03"
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, True)

    def test_085E_sn_sn_rightNodeUsePayChannel_ipay_AUD_BIC(self):
        sn1 = RMNData.sn_usd_us
        sn2 = "ifomx232tdly"

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": "AU BANK", "bicFI": "CTBAAU2S"}}
        # creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, _, r_msg = self.client.step_queryRouter(sn1, "USD", "AUD", creditor_agent=creditor_agent, amount=amount, returnMsg=True)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "AUD", RMNData.prvtId, debtor_agent, RMNData.prvtId_b, creditor_agent, sn1_fee, sn1, inAmount=amount)
        cdtTrfTxInf["dbtr"]["ctctDtls"] = {"phneNb": "1234123412"}
        cdtTrfTxInf["cdtr"]["pstlAdr"]["ctry"] = "AU"
        cdtTrfTxInf = ApiUtils.deepUpdateDict(cdtTrfTxInf, r_msg)
        cdtTrfTxInf["splmtryData"]["addenda"]["senderIdIssueDate"] = "2018-07-03"
        cdtTrfTxInf["splmtryData"]["addenda"]["senderIdExpireDate"] = "2038-07-03"

        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

    def test_087_sn_sn_rightNodeUsePayChannel_ipay_EGP_BIC(self):
        sn1 = RMNData.sn_usd_us
        sn2 = "ifomx232tdly"
        if "sandbox" in RMNData.host or "prod" in RMNData.host:
            sn2 = "ipayrmta1eg1"

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        # creditor_agent = {"finInstnId": {"nm": "NATIONAL BANK OF EGYPT", "bicFI": "BCAIEGCX"}}
        creditor_agent = {"finInstnId": {"nm": "Bank of Egypt", "bicFI": "CBEGEGCX"}}
        # creditor_agent = {"finInstnId": {"nm": "Bank of Egypt", "bicFI": "NBEGEGCXXXX"}}
        # creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        # amount = ApiUtils.randAmount(50, 2, 40)
        amount = 48
        sn1_fee, sn2_fee, _, r_msg = self.client.step_queryRouter(sn1, "USD", "EGP", creditor_agent=creditor_agent, amount=amount, returnMsg=True)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "EGP", RMNData.prvtId, debtor_agent, RMNData.prvtId_b, creditor_agent, sn1_fee, sn1, inAmount=amount)
        cdtTrfTxInf = ApiUtils.deepUpdateDict(cdtTrfTxInf, r_msg)
        cdtTrfTxInf["cdtr"] = {
            "nm": "Jethro Test 002",
            "pstlAdr": {"ctry": "EG", "adrLine": "abcd 1234"},
            # "pstlAdr": {"pstCd": "asd123", "twnNm": "xasd", "twnLctnNm": "asda", "dstrctNm": "1 street", "ctrySubDvsn": "xx h", "ctry": "AU", "adrLine": "abcd 1234"},
            # "prvtId": {
            #     "dtAndPlcOfBirth": {"ctryOfBirth": "EG", "prvcOfBirth": "London", "cityOfBirth": "London City", "birthDt": "1983-05-24"},
            #     "othr": {"id": "xs1233das", "prtry": "ID Card", "issr": "GB"}
            # }
        }
        cdtTrfTxInf["dbtr"]["ctctDtls"] = {"phneNb": "1234123412"}

        cdtTrfTxInf["splmtryData"]["addenda"]["senderIdIssueDate"] = "2018-07-03"
        cdtTrfTxInf["splmtryData"]["addenda"]["senderIdExpireDate"] = "2038-07-03"
        # print(json.dumps(cdtTrfTxInf))
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, True)

    def test_087A_sn_sn_rightNodeUsePayChannel_ipay_CNY_BIC(self):
        sn1 = RMNData.sn_usd_us
        sn2 = "ifomx232tdly"

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": "Agricultural Bank Of China", "bicFI": "ABOCCNBJ"}}
        # creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amount = ApiUtils.randAmount(20, 2, 10)
        sn1_fee, sn2_fee, _, r_msg = self.client.step_queryRouter(sn1, "USD", "CNY", creditor_agent=creditor_agent, amount=amount, returnMsg=True)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "CNY", RMNData.prvtId, debtor_agent, RMNData.prvtId_b, creditor_agent, sn1_fee, sn1, inAmount=amount)
        cdtTrfTxInf["dbtr"]["ctctDtls"] = {"phneNb": "1234123412"}
        cdtTrfTxInf["cdtr"]["pstlAdr"]["ctry"] = "CN"
        cdtTrfTxInf = ApiUtils.deepUpdateDict(cdtTrfTxInf, r_msg)

        cdtTrfTxInf["splmtryData"]["addenda"]["senderIdIssueDate"] = "2018-07-03"
        cdtTrfTxInf["splmtryData"]["addenda"]["senderIdExpireDate"] = "2038-07-03"
        # print(json.dumps(cdtTrfTxInf))
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, True)

    def checkChannelReturnOrder(self, rts_return_order, rts_old_order, sn_node, return_amt):
        if RMNData.is_check_db:
            time.sleep(10)
            rts_info = self.client.mysql.exec_sql_query(f"select * from `{self.client.rts_db_name}`.rts_order where order_id='{rts_old_order}'")
            self.assertEqual(rts_info[0]["orderState"], "TRANSACTION_RETURN")
            time.sleep(30)
            rmn_tx_id = self.client.mysql.exec_sql_query(f"select * from rmn_transaction where rts_txn_id='{rts_return_order}'")[0]["rmnTxnId"]
            rcct_info = self.client.waitReceiveTransactionMessage(rmn_tx_id, sn_node, is_return=True)
            # 校验return交易的金额
            self.assertAlmostEqual(float(rcct_info["txInf"]["rtrdInstdAmt"]["amt"]), return_amt, delta=0.01)
            self.assertAlmostEqual(float(rcct_info["txInf"]["rtrdIntrBkSttlmAmt"]["amt"]), return_amt, delta=0.01)

            self.client.step_sendRTPC(sn_node, RMNData.api_key, RMNData.sec_key, rcct_info)
            sn2_st_msg = self.client.step_sendRCSR(sn_node, RMNData.api_key, RMNData.sec_key, rcct_info, rmn_tx_id, "DBIT", self, nodeLoc="原SN1")

            self.client.logger.warning("sn2节点接收交易完成的confirm")
            sn2_st_msg_id = sn2_st_msg["grpHdr"]["msgId"]
            sn2_endId = sn2_st_msg["cdtTrfTxInf"]["pmtId"]["endToEndId"]
            sn2_tx_confirm = self.client.waitNodeReceiveMessage(sn_node, sn2_st_msg_id, "CMPT", sn2_st_msg_id, RMNData.api_key, RMNData.sec_key,
                                                         "CREDIT_SN_NOTICE_SENT")
            self.checkConfirmMessage(sn2_tx_confirm, "CMPT", sn2_st_msg_id, "RCSR", sn_node, sn2_endId, sn2_endId,
                                        "STTN")
            finish_sql = f"select * from roxe_rmn.rmn_transaction where rmn_txn_id='{rmn_tx_id}' and txn_state='TRANSACTION_FINISH'"
            ApiUtils.waitCondition(self.client.mysql.exec_sql_query, (finish_sql,), lambda x: len(x) > 0, 180, 5)

    def test_088_sn_sn_channelReturn_terrapay(self):
        # rts_old_order = "c07fad1879a843128ef3472f3ab8290f"
        self.test_071_sn_sn_rightNodeUsePayChannel_TerraPay_PHP_pendingMsgSendSN1()
        rts_sql = f"select * from `{self.client.rts_db_name}`.rts_order order by create_time desc limit 1"
        rts_old_order = self.client.mysql.exec_sql_query(rts_sql)[0]["orderId"]
        rts_log_info = self.client.mysql.exec_sql_query(f"select * from `{self.client.rts_db_name}`.rts_order_log where order_id='{rts_old_order}'")
        rts_old_info = [json.loads(i["logInfo"]) for i in rts_log_info if i["orderState"] == 'TRANSACTION_SUBMIT'][0]
        i_id = f"return_{int(time.time())}"
        rtn_amt = [json.loads(i["logInfo"]) for i in rts_log_info if i["orderState"] == 'MINT_FINISH'][0]["payQuantity"]
        # rtn_amt -= 0.53
        # rtn_amt = ApiUtils.parseNumberDecimal(rtn_amt, 2, True)
        self.client.logger.warning(f"退款金额为: {rtn_amt}")
        new_out_info = copy.deepcopy(rts_old_info["receiveInfo"])
        new_out_info["receiverCurrency"] = "USD"
        new_out_info["receiverCountry"] = "US"
        for k, v in rts_old_info["receiveInfo"].items():
            if k.startswith("sender") and "Name" in k:
                new_out_info[k.replace("sender", "receiver")] = v
            elif k.startswith("receiver") and "Name" in k:
                new_out_info[k.replace("receiver", "sender")] = v
        rts_return_order, _ = self.rts_client.submitOrder(
            i_id, rts_old_order, i_id, "PHP", rtn_amt, "USD", sendNodeCode=rts_old_info["receiveNodeCode"],
            receiveNodeCode=rts_old_info["sendNodeCode"], isReturnOrder=True, receiveInfo=new_out_info, refundServiceFee=True
        )

        rts_order_id = rts_return_order["data"]["transactionId"]
        self.checkChannelReturnOrder(rts_order_id, rts_old_order, rts_return_order["data"]["receiveNodeCode"], rtn_amt)

    def test_089_sn_sn_channelReturn_terrapay(self):
        self.test_071_sn_sn_rightNodeUsePayChannel_TerraPay_PHP_pendingMsgSendSN1()
        rts_sql = f"select * from `{self.client.rts_db_name}`.rts_order order by create_time desc limit 1"
        rts_old_order = self.client.mysql.exec_sql_query(rts_sql)[0]["orderId"]
        rts_log_info = self.client.mysql.exec_sql_query(f"select * from `{self.client.rts_db_name}`.rts_order_log where order_id='{rts_old_order}'")
        rts_old_info = [json.loads(i["logInfo"]) for i in rts_log_info if i["orderState"] == 'TRANSACTION_SUBMIT'][0]
        i_id = f"return_{int(time.time())}"
        rtn_amt = [json.loads(i["logInfo"]) for i in rts_log_info if i["orderState"] == 'MINT_FINISH'][0]["payQuantity"]
        rtn_amt -= 0.53
        rtn_amt = ApiUtils.parseNumberDecimal(rtn_amt, 2, True)
        self.client.logger.warning(f"退款金额为: {rtn_amt}")
        new_out_info = copy.deepcopy(rts_old_info["receiveInfo"])
        new_out_info["receiverCurrency"] = "USD"
        new_out_info["receiverCountry"] = "US"
        for k, v in rts_old_info["receiveInfo"].items():
            if k.startswith("sender") and "Name" in k:
                new_out_info[k.replace("sender", "receiver")] = v
            elif k.startswith("receiver") and "Name" in k:
                new_out_info[k.replace("receiver", "sender")] = v
        rts_return_order, _ = self.rts_client.submitOrder(
            i_id, rts_old_order, i_id, "PHP", rtn_amt, "USD", sendNodeCode=rts_old_info["receiveNodeCode"],
            receiveNodeCode=rts_old_info["sendNodeCode"], isReturnOrder=True, receiveInfo=new_out_info
        )

        rts_order_id = rts_return_order["data"]["transactionId"]
        self.checkChannelReturnOrder(rts_order_id, rts_old_order, rts_return_order["data"]["receiveNodeCode"], rtn_amt)

    def test_090_sn_sn_channelReturn_terrapay_repeatRefund(self):
        rts_old_order = "c07fad1879a843128ef3472f3ab8290f"
        rts_log_info = self.client.mysql.exec_sql_query(f"select * from `{self.client.rts_db_name}`.rts_order_log where order_id='{rts_old_order}'")
        rts_old_info = [json.loads(i["logInfo"]) for i in rts_log_info if i["orderState"] == 'TRANSACTION_SUBMIT'][0]
        i_id = f"return_{int(time.time())}"
        rtn_amt = [json.loads(i["logInfo"]) for i in rts_log_info if i["orderState"] == 'MINT_FINISH'][0]["payQuantity"]
        # rtn_amt -= 0.53
        # rtn_amt = ApiUtils.parseNumberDecimal(rtn_amt, 2, True)
        self.client.logger.warning(f"退款金额为: {rtn_amt}")
        new_out_info = copy.deepcopy(rts_old_info["receiveInfo"])
        new_out_info["receiverCurrency"] = "USD"
        new_out_info["receiverCountry"] = "US"
        for k, v in rts_old_info["receiveInfo"].items():
            if k.startswith("sender") and "Name" in k:
                new_out_info[k.replace("sender", "receiver")] = v
            elif k.startswith("receiver") and "Name" in k:
                new_out_info[k.replace("receiver", "sender")] = v
        rts_return_order, _ = self.rts_client.submitOrder(
            i_id, rts_old_order, i_id, "PHP", rtn_amt, "USD", sendNodeCode=rts_old_info["receiveNodeCode"],
            receiveNodeCode=rts_old_info["sendNodeCode"], isReturnOrder=True, receiveInfo=new_out_info, refundServiceFee=True
        )
        self.assertEqual(rts_return_order["message"], f"{rts_old_order} refund order already exists")

    def test_091_sn_sn_channelReturn_nium(self):
        self.test_072_sn_sn_rightNodeUsePayChannel_nium_INR_pendingMsgSendSN1()
        rts_sql = f"select * from `{self.client.rts_db_name}`.rts_order order by create_time desc limit 1"
        rts_old_order = self.client.mysql.exec_sql_query(rts_sql)[0]["orderId"]
        rts_log_info = self.client.mysql.exec_sql_query(f"select * from `{self.client.rts_db_name}`.rts_order_log where order_id='{rts_old_order}'")
        rts_old_info = [json.loads(i["logInfo"]) for i in rts_log_info if i["orderState"] == 'TRANSACTION_SUBMIT'][0]
        i_id = f"return_{int(time.time())}"
        rtn_amt = [json.loads(i["logInfo"]) for i in rts_log_info if i["orderState"] == 'MINT_FINISH'][0]["payQuantity"]
        # rtn_amt -= 0.53
        # rtn_amt = ApiUtils.parseNumberDecimal(rtn_amt, 2, True)
        self.client.logger.warning(f"退款金额为: {rtn_amt}")
        new_out_info = copy.deepcopy(rts_old_info["receiveInfo"])
        new_out_info["receiverCurrency"] = "USD"
        new_out_info["receiverCountry"] = "US"
        for k, v in rts_old_info["receiveInfo"].items():
            if k.startswith("sender") and "Name" in k:
                new_out_info[k.replace("sender", "receiver")] = v
            elif k.startswith("receiver") and "Name" in k:
                new_out_info[k.replace("receiver", "sender")] = v
        rts_return_order, _ = self.rts_client.submitOrder(
            i_id, rts_old_order, i_id, "INR", rtn_amt, "USD", sendNodeCode=rts_old_info["receiveNodeCode"],
            receiveNodeCode=rts_old_info["sendNodeCode"], isReturnOrder=True, receiveInfo=new_out_info, refundServiceFee=True
        )

        rts_order_id = rts_return_order["data"]["transactionId"]
        self.checkChannelReturnOrder(rts_order_id, rts_old_order, rts_return_order["data"]["receiveNodeCode"], rtn_amt)

    def test_092_sn_sn_channelReturn_nium(self):
        self.test_072_sn_sn_rightNodeUsePayChannel_nium_INR_pendingMsgSendSN1()
        rts_sql = f"select * from `{self.client.rts_db_name}`.rts_order order by create_time desc limit 1"
        rts_old_order = self.client.mysql.exec_sql_query(rts_sql)[0]["orderId"]
        rts_log_info = self.client.mysql.exec_sql_query(f"select * from `{self.client.rts_db_name}`.rts_order_log where order_id='{rts_old_order}'")
        rts_old_info = [json.loads(i["logInfo"]) for i in rts_log_info if i["orderState"] == 'TRANSACTION_SUBMIT'][0]
        i_id = f"return_{int(time.time())}"
        rtn_amt = [json.loads(i["logInfo"]) for i in rts_log_info if i["orderState"] == 'MINT_FINISH'][0]["payQuantity"]
        rtn_amt -= 0.53
        rtn_amt = ApiUtils.parseNumberDecimal(rtn_amt, 2, True)
        self.client.logger.warning(f"退款金额为: {rtn_amt}")
        new_out_info = copy.deepcopy(rts_old_info["receiveInfo"])
        new_out_info["receiverCurrency"] = "USD"
        new_out_info["receiverCountry"] = "US"
        for k, v in rts_old_info["receiveInfo"].items():
            if k.startswith("sender") and "Name" in k:
                new_out_info[k.replace("sender", "receiver")] = v
            elif k.startswith("receiver") and "Name" in k:
                new_out_info[k.replace("receiver", "sender")] = v
        rts_return_order, _ = self.rts_client.submitOrder(
            i_id, rts_old_order, i_id, "INR", rtn_amt, "USD", sendNodeCode=rts_old_info["receiveNodeCode"],
            receiveNodeCode=rts_old_info["sendNodeCode"], isReturnOrder=True, receiveInfo=new_out_info, refundServiceFee=False
        )

        rts_order_id = rts_return_order["data"]["transactionId"]
        self.checkChannelReturnOrder(rts_order_id, rts_old_order, rts_return_order["data"]["receiveNodeCode"], rtn_amt)

    def test_093_sn_sn_rightNodeUsePayChannel_nium_INR_ruleBook_ncc(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium
        if "sandbox" in RMNData.host: sn2 = "iovqxmagbin1"

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "INR"
        recCountry = "IN"
        accountId = "12345678901234"
        amt = ApiUtils.randAmount(100, 2, 20)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        creditor_agent = {"finInstnId": {"nm": "XXXX BANK", "clrSysMmbId": {"clrSysCd": "INFSC", "mmbId": "HSBC0110002"}}}
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, creditor_agent=creditor_agent, amount=amt
        )
        # sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "NIUM")
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"}, "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": sendCountry, "twnNm": "xx", "ctrySubDvsn": "xx123"},
            "ctctDtls": {"phneNb": "98 11234222342214"}}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"frstNm": "Edward", "lstNm": "Nelms", "pstlAdr": {"ctry": recCountry, "twnNm": "xxXX", "ctrySubDvsn": "1xx123", "adrLine": "123ddd"}}


        addenda_info = {"senderSourceOfFundCode": "SF001"}
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                sendFee, sn1, addenda_info, accountId, amt)
        cdtTrfTxInf["purp"] = {"cd": "RP002"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}

        self.client.logger.info(json.dumps(cdtTrfTxInf))
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sendFee, deliverFee], self, True)

    def test_094_sn_sn_rightNodeUsePayChannel_nium_BRL_ruleBook_ncc(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "BRL"
        recCountry = "BR"
        accountId = "12345678901234"
        amt = ApiUtils.randAmount(100, 2, 20)
        creditor_agent = {"finInstnId": {"nm": "XXXX BANK", "clrSysMmbId": {"clrSysCd": "BRBCB", "mmbId": "237"}},
                          "brnchId": {"id": "12344"}}

        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, creditor_agent=creditor_agent, amount=amt
        )
        # sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "NIUM")
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"}, "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": sendCountry, "twnNm": "xx", "ctrySubDvsn": "xx123", "pstCd": "12341234"},
            "ctctDtls": {"phneNb": "1 11234222342214"}}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "frstNm": "Edward", "lstNm": "Nelms",
            "pstlAdr": {"ctry": recCountry, "twnNm": "xxXX", "ctrySubDvsn": "1xx123", "adrLine": "123ddd"},
            "prvtId": {"othr": {"prtry": "CPF", "id": "12345678911234", "issr": "BR"}},
            "ctctDtls": {"phneNb": "55 11234222342214"}
        }

        addenda_info = {"senderSourceOfFundCode": "SF001"}
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                sendFee, sn1, addenda_info, accountId, amt)
        cdtTrfTxInf["cdtrAcct"]["tp"] = "Savings"
        cdtTrfTxInf["cdtrAcct"]["acctId"] = "123456789012"
        cdtTrfTxInf["purp"] = {"cd": "RP002"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}

        self.client.logger.info(json.dumps(cdtTrfTxInf))
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sendFee, deliverFee], self, True)

    def test_095_sn_sn_rightNodeUsePayChannel_nium_CAD_ruleBook_ncc(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "CAD"
        recCountry = "CA"
        accountId = "4929858296666465"
        amt = ApiUtils.randAmount(100, 2, 20)
        creditor_agent = {"finInstnId": {"nm": "XXXX BANK", "clrSysMmbId": {"clrSysCd": "CACPA", "mmbId": "061806071"}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, creditor_agent=creditor_agent, amount=amt
        )
        # sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "NIUM")
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"}, "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": sendCountry, "twnNm": "xx", "ctrySubDvsn": "xx123", "pstCd": "12341234"},
            "ctctDtls": {"phneNb": "1 11234222342214"}}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "frstNm": "Edward", "lstNm": "Nelms",
            "pstlAdr": {"ctry": recCountry, "twnNm": "xxXX", "ctrySubDvsn": "1xx123", "adrLine": "123ddd", "pstCd": "12341234"},
            "prvtId": {"othr": {"prtry": "CPF", "id": "12345678911234", "issr": "CA"}},
            "ctctDtls": {"phneNb": "55 11234222342214"}
        }
        addenda_info = {"senderSourceOfFundCode": "SF001"}
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                sendFee, sn1, addenda_info, accountId, amt)
        cdtTrfTxInf["cdtrAcct"]["tp"] = "Savings"
        cdtTrfTxInf["cdtrAcct"]["acctId"] = "123456789012"
        cdtTrfTxInf["purp"] = {"cd": "RP002"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}

        self.client.logger.info(json.dumps(cdtTrfTxInf))
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sendFee, deliverFee], self, True)

    def test_096_sn_sn_rightNodeUsePayChannel_nium_USD_ruleBook_ncc(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "USD"
        recCountry = "US"
        accountId = "133563585"
        amt = ApiUtils.randAmount(100, 2, 20)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, creditor_agent=creditor_intermediary_agent, amount=amt
        )
        # sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "NIUM")
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"}, "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": sendCountry, "twnNm": "xx", "ctrySubDvsn": "xx123", "pstCd": "12341234"},
            "ctctDtls": {"phneNb": "1 11234222342214"}}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "frstNm": "Edward", "lstNm": "Nelms",
            "pstlAdr": {"ctry": recCountry, "twnNm": "xxXX", "ctrySubDvsn": "1xx123", "adrLine": "123ddd", "pstCd": "12341234"},
            "prvtId": {"othr": {"prtry": "CPF", "id": "12345678911234", "issr": "US"}},
            "ctctDtls": {"phneNb": "1 9012345678"}
        }
        creditor_agent = {"finInstnId": {"nm": "XXXX BANK", "clrSysMmbId": {"clrSysCd": "USABA", "mmbId": "314078469"}}}

        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                sendFee, sn1, addenda_info, accountId, amt)
        # cdtTrfTxInf["cdtrAcct"]["tp"] = "Savings"
        # cdtTrfTxInf["cdtrAcct"]["acctId"] = "123456789012"
        cdtTrfTxInf["purp"] = {"cd": "RP002"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}

        self.client.logger.info(json.dumps(cdtTrfTxInf))
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sendFee, deliverFee], self, True)

    def test_097_sn_sn_rightNodeUsePayChannel_nium_USD_ruleBook_roxeId(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "USD"
        recCountry = "US"
        accountId = "133563585"
        amt = ApiUtils.randAmount(100, 2, 20)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, creditor_agent=creditor_intermediary_agent, amount=amt
        )
        # sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "NIUM")
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"}, "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": sendCountry, "twnNm": "xx", "ctrySubDvsn": "xx123", "pstCd": "12341234"},
            "ctctDtls": {"phneNb": "1 11234222342214"}}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "frstNm": "Edward", "lstNm": "Nelms",
            "pstlAdr": {"ctry": recCountry, "twnNm": "xxXX", "ctrySubDvsn": "1xx123", "adrLine": "123ddd", "pstCd": "12341234"},
            "prvtId": {"othr": {"prtry": "CPF", "id": "12345678911234", "issr": "US"}},
            "ctctDtls": {"phneNb": "1 9012345678"}
        }
        creditor_agent = {"finInstnId": {"nm": "XXXX BANK", "clrSysMmbId": {"clrSysCd": "USABA", "mmbId": "314078469"}}}

        addenda_info = {"roxeFlag": "ROXE"}
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_intermediary_agent, None,
                                                                sendFee, sn1, addenda_info, accountId, amt)
        # cdtTrfTxInf["cdtrAcct"]["tp"] = "Savings"
        # cdtTrfTxInf["cdtrAcct"]["acctId"] = "123456789012"
        cdtTrfTxInf["purp"] = {"cd": "RP002"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}

        self.client.logger.info(json.dumps(cdtTrfTxInf))
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sendFee, deliverFee], self, True)

    def test_098_sn_sn_rightNodeUsePayChannel_nium_USD_ruleBook_roxeId(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "USD"
        recCountry = "US"
        accountId = "133563585"
        amt = ApiUtils.randAmount(100, 2, 20)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, creditor_agent=creditor_intermediary_agent, amount=amt
        )
        # sendFee, deliverFee = self.getSendFeeAndDeliverFee(sendCurrency, sendCountry, recCurrency, recCountry, sn1, "NIUM")
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"}, "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": sendCountry, "twnNm": "xx", "ctrySubDvsn": "xx123", "pstCd": "12341234"},
            "ctctDtls": {"phneNb": "1 11234222342214"}}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "frstNm": "Edward", "lstNm": "Nelms",
            "pstlAdr": {"ctry": recCountry, "twnNm": "xxXX", "ctrySubDvsn": "1xx123", "adrLine": "123ddd", "pstCd": "12341234"},
            "prvtId": {"othr": {"prtry": "CPF", "id": "12345678911234", "issr": "US"}},
            "ctctDtls": {"phneNb": "1 9012345678"}
        }
        creditor_agent = {"finInstnId": {"nm": "XXXX BANK", "clrSysMmbId": {"clrSysCd": "USABA", "mmbId": "314078469"}}}

        addenda_info = {"roxeFlag": "ROXE"}
        addenda_info = None
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                sendFee, sn1, addenda_info, accountId, amt)
        # cdtTrfTxInf["cdtrAcct"]["tp"] = "Savings"
        # cdtTrfTxInf["cdtrAcct"]["acctId"] = "123456789012"
        cdtTrfTxInf["purp"] = {"cd": "RP002"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}

        self.client.logger.info(json.dumps(cdtTrfTxInf))
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sendFee, deliverFee], self, True)

    def test_099_sn_sn_rightNodeUsePayChannel_nium_EUR_DE_ruleBook(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "EUR"
        recCountry = "DE"
        accountId = "GB29NWBK60161331926819"
        amt = ApiUtils.randAmount(100, 2, 20)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        creditor_agent = {"finInstnId": {"nm": "XXXX BANK", "bicFI": "BYLADEM1ERH"}}
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, creditor_agent=creditor_intermediary_agent, amount=amt
        )
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"},
                       "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": sendCountry, "twnNm": "xx", "ctrySubDvsn": "xx123",
                        "pstCd": "12341234"},
            "ctctDtls": {"phneNb": "1 11234222342214"}}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "frstNm": "Edward", "lstNm": "Nelms",
            "pstlAdr": {"ctry": recCountry, "twnNm": "xxXX", "ctrySubDvsn": "1xx123", "adrLine": "123ddd"},
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "DE"}},
            "ctctDtls": {"phneNb": "49 1712345678"}
        }

        addenda_info = {"senderSourceOfFundCode": "SF004"}
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, accountId, inAmount=amt)
        cdtTrfTxInf["purp"] = {"cd": "RP003"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}
        cdtTrfTxInf["cdtrAcct"] = {"ccy": recCurrency, "iban": accountId}
        self.client.logger.info(cdtTrfTxInf)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    def test_100_sn_sn_rightNodeUsePayChannel_nium_EUR_FR_ruleBook(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "EUR"
        recCountry = "FR"
        accountId = "FR7630006000011234567890189"
        amt = ApiUtils.randAmount(100, 2, 20)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        creditor_agent = {"finInstnId": {"nm": "XXXX BANK", "bicFI": "CHASFRP0"}}
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, creditor_agent=creditor_agent, amount=amt
        )
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"},
                       "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": sendCountry, "twnNm": "xx", "ctrySubDvsn": "xx123",
                        "pstCd": "12341234"},
            "ctctDtls": {"phneNb": "1 11234222342214"}}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "frstNm": "Edward", "lstNm": "Nelms",
            "pstlAdr": {"ctry": recCountry, "twnNm": "xxXX", "ctrySubDvsn": "1xx123", "adrLine": "123ddd"},
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "FR"}},
            "ctctDtls": {"phneNb": "49 1712345678"}
        }

        addenda_info = {"senderSourceOfFundCode": "SF004"}
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, accountId)
        cdtTrfTxInf["purp"] = {"cd": "RP003"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}
        cdtTrfTxInf["cdtrAcct"] = {"ccy": recCurrency, "iban": accountId}

        self.client.logger.info(cdtTrfTxInf)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    # todo bug
    def test_101_sn_sn_rightNodeUsePayChannel_nium_EUR_FR_ruleBook_enrichRouter(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "EUR"
        recCountry = "FR"
        # accountId = "GB29NWBK60161331926819"
        accountId = "FR7630006000011234567890189"
        amt = ApiUtils.randAmount(100, 2, 20)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        cdtrAcct = {"iban": accountId}
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, cdtrAcct=cdtrAcct, amount=amt
        )
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"},
                       "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": sendCountry, "twnNm": "xx", "ctrySubDvsn": "xx123",
                        "pstCd": "12341234"},
            "ctctDtls": {"phneNb": "1 11234222342214"}}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "frstNm": "Edward", "lstNm": "Nelms",
            "pstlAdr": {"ctry": recCountry, "twnNm": "xxXX", "ctrySubDvsn": "1xx123", "adrLine": "123ddd"},
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "FR"}},
            "ctctDtls": {"phneNb": "49 1712345678"}
        }
        # creditor_agent = {"finInstnId": {"nm": "XXXX BANK", "bicFI": "CHASFRP0"}}
        # creditor_agent = {"finInstnId": {"nm": "BANQUE CHALUS", "bicFI": "AGRIFRPP"}}
        creditor_agent = {"finInstnId": {"nm": "CREDIT AGRICOLE S.A."}}
        addenda_info = {"senderSourceOfFundCode": "SF004"}
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, None,
                                                                float(sendFee), sn1, addenda_info, accountId)
        cdtTrfTxInf["purp"] = {"cd": "RP003"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}
        cdtTrfTxInf["cdtrAcct"] = {"ccy": recCurrency, "iban": accountId}

        self.client.logger.info(cdtTrfTxInf)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    def test_102_sn_sn_rightNodeUsePayChannel_nium_EUR_FR_ruleBook_enrichRouterFailed(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "EUR"
        recCountry = "FR"
        # accountId = "GB29NWBK60161331926819"
        accountId = "FR7630008000011234567890189"
        amt = ApiUtils.randAmount(100, 2, 20)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        cdtrAcct = {"iban": accountId}
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, cdtrAcct=cdtrAcct, amount=amt
        )
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"},
                       "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": sendCountry, "twnNm": "xx", "ctrySubDvsn": "xx123",
                        "pstCd": "12341234"},
            "ctctDtls": {"phneNb": "1 11234222342214"}}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "frstNm": "Edward", "lstNm": "Nelms",
            "pstlAdr": {"ctry": recCountry, "twnNm": "xxXX", "ctrySubDvsn": "1xx123", "adrLine": "123ddd"},
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "FR"}},
            "ctctDtls": {"phneNb": "49 1712345678"}
        }
        # creditor_agent = {"finInstnId": {"nm": "XXXX BANK", "bicFI": "CHASFRP0"}}
        # creditor_agent = {"finInstnId": {"nm": "BANQUE CHALUS", "bicFI": "AGRIFRPP"}}
        creditor_agent = {"finInstnId": {"nm": "CREDIT AGRICOLE S.A."}}
        addenda_info = {"senderSourceOfFundCode": "SF004"}
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, None,
                                                                float(sendFee), sn1, addenda_info, accountId)
        cdtTrfTxInf["purp"] = {"cd": "RP003"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}
        cdtTrfTxInf["cdtrAcct"] = {"ccy": recCurrency, "iban": accountId}

        self.client.logger.info(cdtTrfTxInf)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        rpc_res = self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)
        self.assertEqual(rpc_res, " receiverBankNCC can not be empty")  # iban账号未找到对应的bic码时，nium下单会报错

    def test_103_sn_sn_rightNodeUsePayChannel_cebuana(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_cebuana
        if "sandbox" in RMNData.host: sn2 = "cebuanalh1c3"

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PHP"
        recCountry = "PH"
        accountId = "916100000424"  # 通过
        # creditor_agent = {"finInstnId": {"nm": "Asia United Bank", "clrSysMmbId": {"clrSysCd": "BRSTN", "mmbId": "011020011"}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="CEBUANA node")
        amt = ApiUtils.randAmount(100, 2, 20)
        sendFee, deliverFee, _ = self.client.step_queryRouter(sn1, sendCurrency, recCurrency, creditor_agent=creditor_intermediary_agent, amount=amt)
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"},
                       "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": sendCountry, "twnNm": "xx", "ctrySubDvsn": "xx123",
                        "pstCd": "12341234"},
            "ctctDtls": {"phneNb": "1 11234222342214"}}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "frstNm": "cebuana", "mdlNm": "to", "lstNm": "cebuana",
            "pstlAdr": {"adrLine": "001 Central Avenue", "ctry": recCountry, "twnNm": "xx", "ctrySubDvsn": "xx123", "adrLine": "563 Mayo Street"}
        }
        creditor_agent = {"finInstnId": {"nm": "Asia United Bank", "bicFI": "AUBKPHMM"}}
        addenda_info = {"senderSourceOfFundCode": "SF002"}
        cdtTrfTxInf = self.client.make_channel_RCCT_information(
            sendCurrency, recCurrency, debtor, debtor_agent, creditor, creditor_agent, creditor_intermediary_agent,
            float(sendFee), sn1, addenda_info, accountId
        )
        cdtTrfTxInf["purp"] = {"cd": "RP002"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}
        self.client.logger.info(cdtTrfTxInf)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    def test_104_sn_sn_rightNodeUsePayChannel_cebuana_missField(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_cebuana

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PHP"
        recCountry = "PH"
        accountId = "916100000424"  # 通过
        # creditor_agent = {"finInstnId": {"nm": "Asia United Bank", "clrSysMmbId": {"clrSysCd": "BRSTN", "mmbId": "011020011"}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="CEBUANA node")
        amt = ApiUtils.randAmount(100, 2, 20)
        sendFee, deliverFee, _ = self.client.step_queryRouter(sn1, sendCurrency, recCurrency, creditor_agent=creditor_intermediary_agent, amount=amt)
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"},
                       "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": sendCountry, "twnNm": "xx", "ctrySubDvsn": "xx123",
                        "pstCd": "12341234"},
            "ctctDtls": {"phneNb": "1 11234222342214"}}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "frstNm": "cebuana", "mdlNm": "to", "lstNm": "cebuana",
            "pstlAdr": {"adrLine": "001 Central Avenue", "ctry": recCountry, "twnNm": "xx", "ctrySubDvsn": "xx123"}
        }
        creditor_agent = {"finInstnId": {"nm": "Asia United Bank", "bicFI": "AUBKPHMM"}}
        addenda_info = {"senderSourceOfFundCode": "SF002", "senderIdExpireDate": "2022-2-2"}
        cdtTrfTxInf = self.client.make_channel_RCCT_information(
            sendCurrency, recCurrency, debtor, debtor_agent, creditor, creditor_agent, creditor_intermediary_agent,
            float(sendFee), sn1, addenda_info, accountId
        )
        cdtTrfTxInf["purp"] = {"cd": "RP002"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}
        self.client.logger.info(cdtTrfTxInf)
        miss_fields = {
            "cdtr.frstNm": "receiverFirstName",
            "cdtr.lstNm": "receiverLastName",
            "cdtr.pstlAdr.adrLine": "receiverAddress",
            "cdtr.pstlAdr.ctry": "receiverCountry",
            "cdtr.pstlAdr.twnNm": "receiverCity",
            "cdtr.pstlAdr.ctrySubDvsn": "receiverStates",
            "purp.cd": "purposeCode",
            "rltnShp.cd": "senderBeneficiaryRelationshipCode",
        }
        for m_f, rpc_field in miss_fields.items():
            new_f = ApiUtils.generateDict(m_f, None)
            tmp_info = copy.deepcopy(cdtTrfTxInf)
            tmp_info = ApiUtils.deepUpdateDict(tmp_info, new_f)
            msg_id = self.client.make_msg_id()
            tx_headers = self.client.make_header(sn1, RMNData.api_key, "RCCT", msg_id)
            tx_group_header = self.client.make_group_header(sn1, RMNData.rmn_id, msg_id)
            tx_info, tx_msg = self.client.submit_transaction(RMNData.sec_key, tx_headers, tx_group_header, tmp_info)
            self.assertEqual(tx_info["code"], "00100111")
            self.assertEqual(tx_info["message"], f"{rpc_field} can not be null")

    def test_105_sn_sn_rightNodeUsePayChannel_TerraPay_INR_ruleBook(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay
        if "sandbox" in RMNData.host: sn2 = "huuzj1hpycrx"  # sandbox

        addenda_info = {"senderSourceOfFundCode": "SF001", "senderIdExpireDate": "2023-09-26"}
        r_currency = "INR"
        r_country = "IN"
        r_account_number = "50100002965304"
        r_name = "RANDY OYUGI"
        r_bank_name = "HDFC Bank"
        r_bank_code = "HDFC0001626"
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"}, "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": "US", "twnNm": "xx", "ctrySubDvsn": "xx123"},
            "ctctDtls": {"phneNb": "1 6023305692"}
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": r_bank_name, "clrSysMmbId": {"clrSysCd": "INFSC", "mmbId": r_bank_code}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = {
            "frstNm": "RANDY", "lstNm": "OYUGI",
            "pstlAdr": {"ctry": r_country, "twnNm": "A city", "ctrySubDvsn": "s ad", "adrLine": "13 god street"},
            "prvtId": {"dtAndPlcOfBirth": {"ctryOfBirth": "IN", "cityOfBirth": "on the earth"}}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", r_currency, creditor_agent=creditor_agent, amount=amt)
        # sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                            creditor_agent, creditor_intermediary_agent,
                                                                            float(sn1_fee), sn1, addenda_info, r_account_number, inAmount=amt)
        cdtTrfTxInf["purp"] = {"cd": "RP101"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, True)

    @unittest.skip("pass")
    def test_106_sn_sn_rightNodeUsePayChannel_TerraPay_USD_ruleBook(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay
        if "sandbox" in RMNData.host: sn2 = "huuzj2hpycrx"  # sandbox

        addenda_info = {"senderSourceOfFundCode": "SF001", "senderIdExpireDate": "2023-09-26"}
        r_currency = "USD"
        r_country = "EC"
        r_account_number = "02006137640"
        r_name = "RANDY OYUGI"
        r_bank_name = "Banco Amazonas"
        r_bank_code = "BANAFMEC"
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"}, "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": "US", "twnNm": "xx", "ctrySubDvsn": "xx123"},
            "ctctDtls": {"phneNb": "1 6023305692"}
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": r_bank_name, "clrSysMmbId": {"clrSysCd": "INFSC", "mmbId": r_bank_code}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = {
            "frstNm": "RANDY", "lstNm": "OYUGI",
            "pstlAdr": {"ctry": r_country, "twnNm": "A city", "ctrySubDvsn": "s ad", "adrLine": "13 god street"},
            "prvtId": {"dtAndPlcOfBirth": {"ctryOfBirth": "IN", "cityOfBirth": "on the earth"}}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", r_currency, creditor_agent=creditor_intermediary_agent, amount=amt)
        # sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                            creditor_agent, creditor_intermediary_agent,
                                                                            float(sn1_fee), sn1, addenda_info, r_account_number, inAmount=amt)
        cdtTrfTxInf["purp"] = {"cd": "RP101"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, True)

    def test_107_sn_sn_rightNodeUsePayChannel_TerraPay_EUR_ruleBook(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay
        if "sandbox" in RMNData.host: sn2 = "huuzjhpycfr1"  # sandbox

        addenda_info = {"senderSourceOfFundCode": "SF001", "senderIdExpireDate": "2023-09-26"}
        r_currency = "EUR"
        r_country = "FR"
        r_account_number = "FR7720041000016702233S02022"
        r_bank_name = "LA BANQUE POSTALE"
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"}, "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": "US", "twnNm": "xx", "ctrySubDvsn": "xx123"},
            "ctctDtls": {"phneNb": "1 6023305692"}
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": r_bank_name}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = {
            "frstNm": "RANDY", "lstNm": "OYUGI",
            "pstlAdr": {"ctry": r_country, "twnNm": "A city", "ctrySubDvsn": "s ad", "adrLine": "13 god street"},
            "prvtId": {"dtAndPlcOfBirth": {"ctryOfBirth": "IN", "cityOfBirth": "on the earth"}}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", r_currency, creditor_agent=creditor_intermediary_agent, amount=amt)
        # sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                            creditor_agent, creditor_intermediary_agent,
                                                                            float(sn1_fee), sn1, addenda_info, r_account_number, inAmount=amt)
        cdtTrfTxInf["cdtrAcct"].pop("acctId")
        cdtTrfTxInf["cdtrAcct"]["iban"] = r_account_number

        cdtTrfTxInf["purp"] = {"cd": "RP101"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, True)

    def test_107T_sn_sn_rightNodeUsePayChannel_terrapay_EUR_FR_ruleBook_enrichRouter(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay
        if "sandbox" in RMNData.host: sn2 = "huuzjhpycfr1"  # sandbox

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "EUR"
        recCountry = "FR"
        # accountId = "GB29NWBK60161331926819"
        accountId = "FR7610071000011234567890189"
        amt = ApiUtils.randAmount(100, 2, 20)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        cdtrAcct = {"iban": accountId}
        sendFee, deliverFee, _ = self.client.step_queryRouter(
            sn1, sendCurrency, recCurrency, cdtrAcct=cdtrAcct, amount=amt
        )
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"},
                       "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": sendCountry, "twnNm": "xx", "ctrySubDvsn": "xx123",
                        "pstCd": "12341234"},
            "ctctDtls": {"phneNb": "1 11234222342214"}}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "frstNm": "Edward", "lstNm": "Nelms",
            "pstlAdr": {"ctry": recCountry, "twnNm": "xxXX", "ctrySubDvsn": "1xx123", "adrLine": "123ddd"},
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "FR"}},
            "ctctDtls": {"phneNb": "49 1712345678"}
        }
        # creditor_agent = {"finInstnId": {"nm": "XXXX BANK", "bicFI": "CHASFRP0"}}
        # creditor_agent = {"finInstnId": {"nm": "BANQUE CHALUS", "bicFI": "AGRIFRPP"}}
        creditor_agent = {"finInstnId": {"nm": "CREDIT AGRICOLE S.A."}}
        addenda_info = {"senderSourceOfFundCode": "SF004"}
        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, None,
                                                                float(sendFee), sn1, addenda_info, accountId)
        cdtTrfTxInf["purp"] = {"cd": "RP003"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}
        cdtTrfTxInf["cdtrAcct"] = {"ccy": recCurrency, "iban": accountId}

        self.client.logger.info(cdtTrfTxInf)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [float(sendFee), float(deliverFee)], self, isInnerNode=inner_node)

    def test_108_sn_sn_rightNodeUsePayChannel_TerraPay_GBP_ruleBook(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay
        if "sandbox" in RMNData.host: sn2 = "huuzj2hpycrx"  # sandbox

        addenda_info = {"senderSourceOfFundCode": "SF001", "senderIdExpireDate": "2023-09-26"}
        r_currency = "GBP"
        r_country = "GB"
        r_account_number = "GB29NWBK60161331926819"
        r_bank_name = "HDFC Bank"
        r_bank_code = "HDFCINBB"
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"}, "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": "US", "twnNm": "xx", "ctrySubDvsn": "xx123"},
            "ctctDtls": {"phneNb": "1 6023305692"}
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = {
            "frstNm": "RANDY", "lstNm": "OYUGI",
            "pstlAdr": {"ctry": r_country, "twnNm": "A city", "ctrySubDvsn": "s ad", "adrLine": "13 god street"},
            "prvtId": {"dtAndPlcOfBirth": {"ctryOfBirth": "IN", "cityOfBirth": "on the earth"}}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", r_currency, creditor_agent=creditor_intermediary_agent, amount=amt)
        # sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                            creditor_agent, creditor_intermediary_agent,
                                                                            float(sn1_fee), sn1, addenda_info, r_account_number, inAmount=amt)

        cdtTrfTxInf["purp"] = {"cd": "RP101"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, True)

    # todo
    def test_109_sn_sn_rightNodeUsePayChannel_TerraPay_BRL_ruleBook(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay
        if "sandbox" in RMNData.host: sn2 = "huuzj2hpycrx"  # sandbox

        addenda_info = {"senderSourceOfFundCode": "SF001", "senderIdExpireDate": "2023-09-26"}
        r_currency = "BRL"
        r_country = "BR"
        r_account_number = "718530346"
        r_name = "RANDY OYUGI"
        r_bank_name = "unicred norte do parana"
        r_bank_code = "UNPABRPR"
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"}, "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": "US", "twnNm": "xx", "ctrySubDvsn": "xx123", "pstCd": "12033"},
            "ctctDtls": {"phneNb": "1 6023305692"}
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code, brnchId={"id": "235"})
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = {
            "frstNm": "RANDY", "lstNm": "OYUGI",
            "pstlAdr": {"ctry": r_country, "twnNm": "A city", "ctrySubDvsn": "s ad", "adrLine": "13 god street"},
            "prvtId": {
                "dtAndPlcOfBirth": {"ctryOfBirth": r_country, "cityOfBirth": "on the earth"},
                "othr": {"id": "1234123", "prtry": "CPF"}
            },
            "ctctDtls": {"phneNb": "0055 6023305692"}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", r_currency, creditor_agent=creditor_agent, amount=amt)
        return
        # sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                            creditor_agent, creditor_intermediary_agent,
                                                                            float(sn1_fee), sn1, addenda_info, r_account_number, inAmount=amt)
        cdtTrfTxInf["cdtrAcct"]["tp"] = "Checking"
        cdtTrfTxInf["purp"] = {"cd": "RP101"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, True)

    def test_110_sn_sn_rightNodeUsePayChannel_TerraPay_CAD_ruleBook(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay
        if "sandbox" in RMNData.host: sn2 = "huuzj2hpycrx"  # sandbox

        addenda_info = {"senderSourceOfFundCode": "SF001", "senderIdExpireDate": "2023-09-26"}
        r_currency = "CAD"
        r_country = "CA"
        r_account_number = "6146198"
        r_name = "RANDY OYUGI"
        r_bank_name = "HDFC Bank"
        r_bank_code = "961806071"
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"}, "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": "US", "twnNm": "xx", "ctrySubDvsn": "xx123", "pstCd": "12033"},
            "ctctDtls": {"phneNb": "1 6023305692"}
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": r_bank_name, "clrSysMmbId": {"clrSysCd": "CACPA", "mmbId": r_bank_code}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = {
            "frstNm": "RANDY", "lstNm": "OYUGI",
            "pstlAdr": {"ctry": r_country, "twnNm": "A city", "ctrySubDvsn": "s ad", "adrLine": "13 god street", "pstCd": "10023"},
            "prvtId": {
                "dtAndPlcOfBirth": {"ctryOfBirth": r_country, "cityOfBirth": "on the earth"}
            }
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", r_currency, creditor_agent=creditor_intermediary_agent, amount=amt)
        # sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                            creditor_agent, creditor_intermediary_agent,
                                                                            float(sn1_fee), sn1, addenda_info, r_account_number, inAmount=amt)
        # cdtTrfTxInf["cdtrAcct"]["tp"] = "Checking"
        cdtTrfTxInf["purp"] = {"cd": "RP101"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, True)

    def test_111_sn_sn_rightNodeUsePayChannel_TerraPay_ZAR_ruleBook(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay
        if "sandbox" in RMNData.host: sn2 = "huuzj2hpycrx"  # sandbox

        addenda_info = {"senderSourceOfFundCode": "SF001", "senderIdExpireDate": "2023-09-26"}
        r_currency = "ZAR"
        r_country = "ZA"
        r_account_number = "38038390535"
        r_name = "RANDY OYUGI"
        r_bank_name = "ABSA Bank"
        r_bank_code = "ABSAZAJJ"
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"}, "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": "US", "twnNm": "xx", "ctrySubDvsn": "xx123", "pstCd": "12033"},
            "ctctDtls": {"phneNb": "1 6023305692"}
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code, brnchId={"id": "103"})
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = {
            "frstNm": "RANDY", "lstNm": "OYUGI",
            "pstlAdr": {"ctry": r_country, "twnNm": "A city", "ctrySubDvsn": "s ad", "adrLine": "13 god street"},
            "prvtId": {
                "dtAndPlcOfBirth": {"ctryOfBirth": r_country, "cityOfBirth": "on the earth"}
            },
            "ctctDtls": {"phneNb": "27 837738087"}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", r_currency, creditor_agent=creditor_intermediary_agent, amount=amt)
        # sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                            creditor_agent, creditor_intermediary_agent,
                                                                            float(sn1_fee), sn1, addenda_info, r_account_number, inAmount=amt)
        # cdtTrfTxInf["cdtrAcct"]["tp"] = "Checking"
        cdtTrfTxInf["purp"] = {"cd": "RP101"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, True)

    # todo
    def test_112_sn_sn_rightNodeUsePayChannel_TerraPay_CNY_ruleBook(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay
        if "sandbox" in RMNData.host: sn2 = "huuzj2hpycrx"  # sandbox

        addenda_info = {"senderSourceOfFundCode": "SF001", "senderIdExpireDate": "2023-09-26"}
        r_currency = "CNY"
        r_country = "CN"
        r_account_number = "6217900100010200001"
        r_name = "RANDY OYUGI"
        r_bank_name = "Agricultural Bank Of China"#"UNION PAY"
        r_bank_code = "ABOCCNBJ"
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"}, "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": "US", "twnNm": "xx", "ctrySubDvsn": "xx123"},
            "ctctDtls": {"phneNb": "1 6023305692"}
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code, brnchId={"id": '123'})
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = {
            "frstNm": "RANDY", "lstNm": "OYUGI",
            "pstlAdr": {"ctry": r_country, "twnNm": "A city", "ctrySubDvsn": "s ad", "adrLine": "13 god street"},
            "prvtId": {
                "dtAndPlcOfBirth": {"ctryOfBirth": "CN", "cityOfBirth": "on the earth"},
                "othr": {"prtry": "NID", "id": "13013319990210234E"},
                # "othr": {"prtry": "Passport", "id": "13013319990210234E"},
            },
            "ctctDtls": {"phneNb": "86 13800001111"}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", r_currency, creditor_agent=creditor_intermediary_agent, amount=amt)
        # sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                            creditor_agent, creditor_intermediary_agent,
                                                                            float(sn1_fee), sn1, addenda_info, r_account_number, inAmount=amt)
        cdtTrfTxInf["purp"] = {"cd": "RP101"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, True)

    def test_113_sn_sn_rightNodeUsePayChannel_TerraPay_PHP_ruleBook(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay
        if "sandbox" in RMNData.host: sn2 = "huuzj2hpycrx"  # sandbox

        addenda_info = {"senderSourceOfFundCode": "SF001", "senderIdExpireDate": "2023-09-26"}
        r_currency = "PHP"
        r_country = "PH"
        r_account_number = "20408277204478"
        r_name = "RANDY OYUGI"
        r_bank_name = "Asia United Bank"
        r_bank_code = "AUBKPHMM"
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"}, "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": "US", "twnNm": "xx", "ctrySubDvsn": "xx123"},
            "ctctDtls": {"phneNb": "1 6023305692"}
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = {
            "frstNm": "RANDY", "lstNm": "OYUGI",
            "pstlAdr": {"ctry": r_country, "twnNm": "A city", "ctrySubDvsn": "s ad", "adrLine": "13 god street"},
            "prvtId": {"dtAndPlcOfBirth": {"ctryOfBirth": "PH", "cityOfBirth": "on the earth"}}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", r_currency, creditor_agent=creditor_agent, amount=amt)
        # sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                            creditor_agent, creditor_intermediary_agent,
                                                                            float(sn1_fee), sn1, addenda_info, r_account_number, inAmount=amt)
        cdtTrfTxInf["purp"] = {"cd": "RP101"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}
        # print(json.dumps(cdtTrfTxInf))
        self.submitOrderAndCheckToTerrapayAmount(sn1, sn2, cdtTrfTxInf)

    def test_114_sn_sn_rightNodeUsePayChannel_TerraPay_GHS_ruleBook(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay
        if "sandbox" in RMNData.host: sn2 = "huuzjhpycgh1"  # sandbox

        addenda_info = {"senderSourceOfFundCode": "SF001", "senderIdExpireDate": "2023-09-26"}
        r_currency = "GHS"
        r_country = "GH"
        r_account_number = "00100008703552"
        r_name = "RANDY OYUGI"
        r_bank_name = "UBA Bank"
        r_bank_code = "STBGGHAC"
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"}, "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": "US", "twnNm": "xx", "ctrySubDvsn": "xx123", "pstCd": "123"},
            "ctctDtls": {"phneNb": "1 6023305692"}
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code, brnchId={"id": "305"})
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = {
            "frstNm": "RANDY", "lstNm": "OYUGI",
            "pstlAdr": {"ctry": r_country, "twnNm": "A city", "ctrySubDvsn": "s ad", "adrLine": "13 god street"},
            "prvtId": {"dtAndPlcOfBirth": {"ctryOfBirth": r_country, "cityOfBirth": "on the earth"}}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", r_currency, creditor_agent=creditor_intermediary_agent, amount=amt)
        # sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                            creditor_agent, creditor_intermediary_agent,
                                                                            float(sn1_fee), sn1, addenda_info, r_account_number, inAmount=amt)
        cdtTrfTxInf["purp"] = {"cd": "RP101"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, True)

    # todo bug 查询不到路由
    def test_115_sn_sn_rightNodeUsePayChannel_TerraPay_VND_ruleBook(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay
        if "sandbox" in RMNData.host: sn2 = "huuzj2hpycrx"  # sandbox

        addenda_info = {"senderSourceOfFundCode": "SF001", "senderIdExpireDate": "2023-09-26"}
        r_currency = "VND"
        r_country = "VN"
        r_account_number = "1976031127"
        r_name = "RANDY OYUGI"
        r_bank_name = "Vietin Bank"
        r_bank_code = "VBBLVNAG"
        debtor = {
            "frstNm": "AnaThree", "lstNm": "AmariThree",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"}, "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": "US", "twnNm": "xx", "ctrySubDvsn": "xx123"},
            "ctctDtls": {"phneNb": "1 6023305692"}
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = {
            "frstNm": "RANDY", "lstNm": "OYUGI", "nm": "OYUGI RANDY",
            "pstlAdr": {"ctry": r_country, "twnNm": "A city", "ctrySubDvsn": "s ad", "adrLine": "13 god street"},
            "prvtId": {"dtAndPlcOfBirth": {"ctryOfBirth": r_country, "cityOfBirth": "on the earth"}}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", r_currency, creditor_agent=creditor_intermediary_agent, amount=amt)
        # sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sn1_fee), sn1, addenda_info, r_account_number, inAmount=amt)
        cdtTrfTxInf["purp"] = {"cd": "RP101"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, True)

    # todo
    def test_116_sn_sn_rightNodeUsePayChannel_TerraPay_ARS_ruleBook(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay
        if "sandbox" in RMNData.host: sn2 = "huuzj2hpycrx"  # sandbox

        addenda_info = {"senderSourceOfFundCode": "SF001", "senderIdExpireDate": "2023-09-26"}
        r_currency = "ARS"
        r_country = "AR"
        r_account_number = "482700048226"
        r_name = "RANDY OYUGI"
        r_bank_name = "Banco Credicoop Coop. L"
        r_bank_code = "BACONAAR"
        debtor = {
            "frstNm": "AnaThree", "lstNm": "AmariThree",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"}, "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": "US", "twnNm": "xx", "ctrySubDvsn": "xx123"},
            "ctctDtls": {"phneNb": "1 6023305692"}
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = {
            "frstNm": "RANDY", "lstNm": "OYUGI", "mtrnlNm": "asd",
            "pstlAdr": {"ctry": r_country, "twnNm": "A city", "ctrySubDvsn": "s ad", "adrLine": "13 god street"},
            "prvtId": {
                "dtAndPlcOfBirth": {"ctryOfBirth": r_country, "cityOfBirth": "on the earth"},
                "othr": {"prtry": "CUIL", "id": "12341234"}
            },
            "ctctDtls": {"phneNb": "54 6023305692"}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", r_currency, creditor_agent=creditor_intermediary_agent, amount=amt)
        # sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sn1_fee), sn1, addenda_info, r_account_number, inAmount=amt)
        cdtTrfTxInf["cdtrAcct"]["tp"] = "Savings"
        cdtTrfTxInf["purp"] = {"cd": "RP101"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, True)

    # todo
    def test_117_sn_sn_rightNodeUsePayChannel_TerraPay_PEN_ruleBook(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay
        if "sandbox" in RMNData.host: sn2 = "huuzj2hpycrx"  # sandbox

        addenda_info = {"senderSourceOfFundCode": "SF001", "senderIdExpireDate": "2023-09-26"}
        r_currency = "PEN"
        r_country = "PE"
        r_account_number = "00219313084958709612"
        r_name = "RANDY OYUGI"
        r_bank_name = "BANCO CENTRAL DE RESERVA"
        r_bank_code = "CRPEPEPL"
        debtor = {
            "frstNm": "AnaThree", "lstNm": "AmariThree",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"}, "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": "US", "twnNm": "xx", "ctrySubDvsn": "xx123"},
            "ctctDtls": {"phneNb": "1 6023305692"}
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = {
            "frstNm": "RANDY", "lstNm": "OYUGI", "sndLstNm": "asd",
            "pstlAdr": {"ctry": r_country, "twnNm": "A city", "ctrySubDvsn": "s ad", "adrLine": "13 god street"},
            "prvtId": {
                "dtAndPlcOfBirth": {"ctryOfBirth": r_country, "cityOfBirth": "on the earth"},
                "othr": {"prtry": "DNI", "id": "12341234"}
            },
            "ctctDtls": {"phneNb": "0051 6023305692"}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", r_currency, creditor_agent=creditor_intermediary_agent, amount=amt)
        # sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sn1_fee), sn1, addenda_info, r_account_number, inAmount=amt)
        # cdtTrfTxInf["cdtrAcct"]["tp"] = "Savings"
        cdtTrfTxInf["purp"] = {"cd": "RP101"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, True)

    def test_118_sn_sn_rightNodeUsePayChannel_TerraPay_MXN_ruleBook(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay
        if "sandbox" in RMNData.host: sn2 = "huuzj2hpycrx"  # sandbox

        addenda_info = {"senderSourceOfFundCode": "SF001", "senderIdExpireDate": "2023-09-26"}
        r_currency = "MXN"
        r_country = "MX"
        r_account_number = "210017272102"
        r_name = "RANDY OYUGI"
        r_bank_name = "BNMXMXMM"
        r_bank_code = "BNMXMXMM"
        debtor = {
            "frstNm": "AnaThree", "lstNm": "AmariThree",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"}, "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": "US", "twnNm": "xx", "ctrySubDvsn": "xx123", "pstCd": "12342"},
            "ctctDtls": {"phneNb": "1 6023305692"}
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = {
            "frstNm": "JULIO", "lstNm": "SOLANO",
            "pstlAdr": {"ctry": r_country, "twnNm": "A city", "ctrySubDvsn": "s ad", "adrLine": "13 god street"},
            "prvtId": {
                "dtAndPlcOfBirth": {"ctryOfBirth": r_country, "cityOfBirth": "on the earth"},
                "othr": {"prtry": "RFC", "id": "12341234"}
            },
            "ctctDtls": {"phneNb": "0052 6023305692"}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", r_currency, creditor_agent=creditor_intermediary_agent, amount=amt)
        # sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sn1_fee), sn1, addenda_info, r_account_number, inAmount=amt)
        cdtTrfTxInf["purp"] = {"cd": "RP101"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, True)

    def test_119_sn_sn_rightNodeUsePayChannel_TerraPay_THB_ruleBook(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay
        if "sandbox" in RMNData.host: sn2 = "huuzj2hpycrx"  # sandbox

        addenda_info = {"senderSourceOfFundCode": "SF001", "senderIdExpireDate": "2023-09-26"}
        r_currency = "THB"
        r_country = "TH"
        r_account_number = "20408277205678"
        r_name = "RANDY OYUGI"
        r_bank_name = "BANGKOK Bank"
        r_bank_code = "BKKBTHBK"
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"}, "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": "US", "twnNm": "xx", "ctrySubDvsn": "xx123"},
            "ctctDtls": {"phneNb": "1 6023305692"}
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = {
            "frstNm": "RANDY", "lstNm": "OYUGI",
            "pstlAdr": {"ctry": r_country, "twnNm": "A city", "ctrySubDvsn": "s ad", "adrLine": "13 god street"},
            "prvtId": {"dtAndPlcOfBirth": {"ctryOfBirth": "IN", "cityOfBirth": "on the earth"}}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", r_currency, creditor_agent=creditor_intermediary_agent, amount=amt)
        # sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                            creditor_agent, creditor_intermediary_agent,
                                                                            float(sn1_fee), sn1, addenda_info, r_account_number, inAmount=amt)
        cdtTrfTxInf["purp"] = {"cd": "RP101"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, True)

    # todo
    def test_120_sn_sn_rightNodeUsePayChannel_TerraPay_MYR_ruleBook(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay
        if "sandbox" in RMNData.host: sn2 = "huuzj2hpycrx"  # sandbox

        addenda_info = {"senderSourceOfFundCode": "SF001", "senderIdExpireDate": "2023-09-26"}
        r_currency = "MYR"
        r_country = "MY"
        r_account_number = "1976041128"
        r_name = "RANDY OYUGI"
        r_bank_name = "MAY BANKA"
        r_bank_code = "MBBEMYKL"
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"}, "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": "US", "twnNm": "xx", "ctrySubDvsn": "xx123"},
            "ctctDtls": {"phneNb": "1 6023305692"}
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = {
            "frstNm": "RANDY", "lstNm": "OYUGI",
            "pstlAdr": {"ctry": r_country, "twnNm": "A city", "ctrySubDvsn": "s ad", "adrLine": "13 god street"},
            "prvtId": {"dtAndPlcOfBirth": {"ctryOfBirth": "MY", "cityOfBirth": "on the earth"}}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", r_currency, creditor_agent=creditor_intermediary_agent, amount=amt)
        # sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                            creditor_agent, creditor_intermediary_agent,
                                                                            float(sn1_fee), sn1, addenda_info, r_account_number, inAmount=amt)
        cdtTrfTxInf["purp"] = {"cd": "RP101"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, True)

    def test_121_sn_sn_rightNodeUsePayChannel_rmn_USD_ruleBook(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_us
        if "sandbox" in RMNData.host: sn2 = sn2  # sandbox

        addenda_info = {"senderSourceOfFundCode": "SF001", "senderIdExpireDate": "2023-09-26", "roxeFlag": "ROXE"}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_roxe_agent(sn2, "SN")
        amount = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent,
                                                             amount=amount)
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"},
                       "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": "US", "twnNm": "xx", "ctrySubDvsn": "xx123", "pstCd": "456"},
            "ctctDtls": {"phneNb": "1 6023305692"}
        }
        creditor = {
            "frstNm": "RANDY", "lstNm": "OYUGI",
            "pstlAdr": {"ctry": "US", "twnNm": "A city", "ctrySubDvsn": "s ad", "adrLine": "13 god street", "pstCd": "1234"},
            "prvtId": {"dtAndPlcOfBirth": {"ctryOfBirth": "IN", "cityOfBirth": "on the earth"}}
        }
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", debtor, debtor_agent, creditor,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amount)
        cdtTrfTxInf["purp"] = {"cd": "RP101"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}
        cdtTrfTxInf["splmtryData"]["addenda"] = addenda_info
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

    def test_122_sn_sn_rightNodeUsePayChannel_rmn_USD_bic_ruleBook(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        if "sandbox" in RMNData.host: sn2 = "huuzj2hpycrx"  # sandbox

        addenda_info = {"senderSourceOfFundCode": "SF001", "senderIdExpireDate": "2023-09-26"}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": "rich bank", "bicFI": "BOFAUS3DAU2"}}
        amount = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent,
                                                             amount=amount)
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"},
                       "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": "US", "twnNm": "xx", "ctrySubDvsn": "xx123", "pstCd": "12345"},
            "ctctDtls": {"phneNb": "1 6023305692"}
        }
        creditor = {
            "frstNm": "RANDY", "lstNm": "OYUGI",
            "pstlAdr": {"ctry": "US", "twnNm": "A city", "ctrySubDvsn": "s ad", "adrLine": "13 god street", "pstCd": "12345"},
            "prvtId": {"dtAndPlcOfBirth": {"ctryOfBirth": "IN", "cityOfBirth": "on the earth"}}
        }
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", debtor, debtor_agent, creditor,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amount)
        cdtTrfTxInf["purp"] = {"cd": "RP101"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}
        cdtTrfTxInf["splmtryData"]["addenda"] = addenda_info
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, inner_node)

    def test_123_sn_sn_rightNodeUsePayChannel_rmn_USD_ncc_ruleBook(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        if "sandbox" in RMNData.host: sn2 = "huuzj2hpycrx"  # sandbox

        addenda_info = {"senderSourceOfFundCode": "SF001", "senderIdExpireDate": "2023-09-26"}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": "rich bank", "clrSysMmbId": {"clrSysCd": "USABA", "mmbId": "111000025"}}}
        amount = ApiUtils.randAmount(15, 2, 10)
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "USD", "USD", creditor_agent=creditor_agent,
                                                             amount=amount)
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"},
                       "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": "US", "twnNm": "xx", "ctrySubDvsn": "xx123", "pstCd": "12345"},
            "ctctDtls": {"phneNb": "1 6023305692"}
        }
        creditor = {
            "frstNm": "RANDY", "lstNm": "OYUGI",
            "pstlAdr": {"ctry": "US", "twnNm": "A city", "ctrySubDvsn": "s ad", "adrLine": "13 god street", "pstCd": "12345"},
            "prvtId": {"dtAndPlcOfBirth": {"ctryOfBirth": "IN", "cityOfBirth": "on the earth"}}
        }
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "USD", debtor, debtor_agent, creditor,
                                                        creditor_agent, sn1_fee, sn1, inAmount=amount)
        cdtTrfTxInf["purp"] = {"cd": "RP101"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}
        cdtTrfTxInf["splmtryData"]["addenda"] = addenda_info
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, inner_node)

    def test_124_sn_sn_rightNodeUsePayChannel_rmn_EUR_ruleBook(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_usd_gb
        if "sandbox" in RMNData.host: sn2 = "fape1meh3bsz"  # sandbox

        addenda_info = {"senderSourceOfFundCode": "SF001", "senderIdExpireDate": "2023-09-26"}
        r_currency = "EUR"
        r_country = "FR"
        r_account_number = "FR7720041000016702233S02022"
        r_bank_name = "LA BANQUE POSTALE"
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"},
                       "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": "US", "twnNm": "xx", "ctrySubDvsn": "xx123"},
            "ctctDtls": {"phneNb": "1 6023305692"}
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": r_bank_name}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = {
            "frstNm": "RANDY", "lstNm": "OYUGI",
            "pstlAdr": {"ctry": r_country, "twnNm": "A city", "ctrySubDvsn": "s ad", "adrLine": "13 god street"},
            "prvtId": {"dtAndPlcOfBirth": {"ctryOfBirth": "IN", "cityOfBirth": "on the earth"}}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", r_currency,
                                                           creditor_agent=creditor_intermediary_agent, amount=amt)
        # sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sn1_fee), sn1, addenda_info, r_account_number,
                                                                inAmount=amt)
        cdtTrfTxInf["cdtrAcct"].pop("acctId")
        cdtTrfTxInf["cdtrAcct"]["iban"] = r_account_number

        cdtTrfTxInf["purp"] = {"cd": "RP101"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}
        self.client.transactionFlow_sn_sn(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self)

    def test_125_sn_sn_rightNodeUsePayChannel_TerraPay_PHP_ruleBook(self):
        sn1 = RMNData.sn_usd_us
        sn2 = RMNData.sn_roxe_terrapay
        if "sandbox" in RMNData.host: sn2 = "huuzj2hpycrx"  # sandbox

        addenda_info = {"senderSourceOfFundCode": "SF001", "senderIdExpireDate": "2023-09-26"}
        r_currency = "PHP"
        r_country = "PH"
        r_account_number = "20408277204478"
        r_name = "RANDY OYUGI"
        r_bank_name = "Asia United Bank"
        r_bank_code = "AUBKPHMM"
        debtor = {
            "frstNm": "Michael", "lstNm": "Stallman",
            "prvtId": {"othr": {"prtry": "Passport", "id": "12345678911234", "issr": "US"}, "dtAndPlcOfBirth": {"birthDt": "1972-06-30", "ctryOfBirth": "US", "cityOfBirth": "sd"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "ctry": "US", "twnNm": "xx", "ctrySubDvsn": "xx123"},
            "ctctDtls": {"phneNb": "1 6023305692"}
        }
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = {
            "frstNm": "RANDY", "lstNm": "OYUGI",
            "pstlAdr": {"ctry": r_country, "twnNm": "A city", "ctrySubDvsn": "s ad", "adrLine": "13 god street"},
            "prvtId": {"dtAndPlcOfBirth": {"ctryOfBirth": "PH", "cityOfBirth": "on the earth"}}
        }
        amt = ApiUtils.randAmount(100, 2, 20)
        sn1_fee, sn2_fee, _ = self.client.step_queryRouter(sn1, "USD", r_currency, creditor_agent=creditor_intermediary_agent, amount=amt)
        # sendFee, deliverFee = self.getSendFeeAndDeliverFee("USD", "US", r_currency, r_country, sn1, "TERRAPAY")
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                            creditor_agent, creditor_intermediary_agent,
                                                                            float(sn1_fee), sn1, addenda_info, r_account_number, inAmount=amt)
        cdtTrfTxInf["purp"] = {"cd": "RP101"}
        cdtTrfTxInf["rltnShp"] = {"cd": "RS004"}
        # print(json.dumps(cdtTrfTxInf))
        self.submitOrderAndCheckToTerrapayAmount(sn1, sn2, cdtTrfTxInf)

    def test_183_sn_sn_rightNodeUsePayChannel_fifan_VND_BIC(self):
        sn1 = RMNData.sn_usd_us
        sn2 = "finfan2ls31e"

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": "XXXX BANK", "clrSysMmbId": {"clrSysCd": "VNNPS", "mmbId": "970412"}}}
        # cdtrIntrmyAgt = self.client.make_roxe_agent(sn2, "SN")
        # creditor_agent = self.client.make_roxe_agent(sn2, "SN") # VNBIN
        # amount = ApiUtils.randAmount(50, 2, 40)
        amount = 22
        sn1_fee, sn2_fee, _, r_msg = self.client.step_queryRouter(sn1, "USD", "VND", creditor_agent=creditor_agent,
                                                                  amount=amount, returnMsg=True)
        cdtTrfTxInf = self.client.make_RCCT_information("USD", "VND", RMNData.prvtId, debtor_agent,
                                                        RMNData.prvtId_b, creditor_agent, sn1_fee, sn1,
                                                        inAmount=amount)
        cdtTrfTxInf = ApiUtils.deepUpdateDict(cdtTrfTxInf, r_msg)
        cdtTrfTxInf["cdtr"] = {
            "nm": "BUI MINH TIEN",
            "pstlAdr": {"ctry": "EG", "adrLine": "Heliopolis, Cairo, Egypt"},
            # "pstlAdr": {"pstCd": "asd123", "twnNm": "xasd", "twnLctnNm": "asda", "dstrctNm": "1 street", "ctrySubDvsn": "xx h", "ctry": "AU", "adrLine": "abcd 1234"},
            "prvtId": {
                "dtAndPlcOfBirth": {"ctryOfBirth": "VN", "prvcOfBirth": "London", "cityOfBirth": "London City", "birthDt": "1983-05-24"},
                "othr": {"id": "xs1233das", "prtry": "ID Card", "issr": "VN"}
            }
        }
        # cdtTrfTxInf["cdtrIntrmyAgt"] = self.client.make_roxe_agent(sn2, "SN")
        cdtTrfTxInf["cdtrAcct"] = {"ccy": "VND", "acctId": "109000636588"}
        cdtTrfTxInf["dbtr"]["ctctDtls"] = {"phneNb": "1234123412"}

        cdtTrfTxInf["splmtryData"]["addenda"]["senderIdIssueDate"] = "2018-07-03"
        cdtTrfTxInf["splmtryData"]["addenda"]["senderIdExpireDate"] = "2038-07-03"
        print(json.dumps(cdtTrfTxInf))
        # return
        self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=True)
        # msg_id, tx_msg, end2end_id, rmn_tx_id, st_msg = self.client.transactionFlow_sn_sn_not_check_db_1(
        #     sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, isInnerNode=True
        # )
        # self.client.logger.warning("msg_id={}".format(msg_id))
        # self.client.logger.warning("tx_msg={}".format(tx_msg))
        # self.client.logger.warning("end2end_id={}".format(end2end_id))
        # self.client.logger.warning("rmn_tx_id={}".format(rmn_tx_id))
        # self.client.logger.warning("st_msg={}".format(st_msg))
        # time.sleep(90)
        # tx2_msg = self.waitSN2ReceiveRCCTInProd(5)[0]
        # self.client.transactionFlow_sn_sn_Channel(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, True)

    # pro testcase
    @unittest.skip("生产测试用例，手动执行")
    def test_200_getRouterList_senderIsSN_differentCurrency_snRoxeId_To_Channel(self):
        sender = RMNData.sn_usd_us_a
        sn2 = RMNData.sn_roxe_terrapay["ZA"]
        # sn2 = RMNData.sn_roxe_nium
        # sn2 = RMNData.sn_roxe_cebuana

        recCurrency = "ZAR"
        ts_headers = self.client.make_header(sender, RMNData.api_key, "RRLQ")
        msg_header = self.client.make_msg_header(sender, ts_headers["msgId"])
        agent_info = self.client.make_roxe_agent(sn2, "SN")
        msg = self.client.make_RRLQ_information("USD", recCurrency, "100", cdtrAgt=agent_info, cd="C2C")
        router_list, req_msg = self.client.get_router_list(RMNData.sec_key, ts_headers, msg_header, msg)
        self.client.checkCodeAndMessage(router_list)

    @unittest.skip("生产测试用例，手动执行")
    def test_201_sn_sn_rightNodeUsePayChannel_TerraPay_INR(self):
        sn1 = RMNData.sn_usd_us_a
        sn2 = RMNData.sn_roxe_terrapay["IN"]

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "INR"
        r_country = "IN"
        r_account_number = "020401525694"
        r_name = "Rajiv Kumar"
        r_bank_name = "ICICI Bank Ltd"
        r_bank_code = "ICIC0000204"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        # creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_agent = {"finInstnId": {"nm": r_bank_name, "clrSysMmbId": {"clrSysCd": "INFSC", "mmbId": r_bank_code}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        sendFee = 0.10

        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, r_account_number, inAmount=3.6)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_not_check_db_1(sn1, sn2, cdtTrfTxInf, [0.10, 1.25], self, isInnerNode=inner_node)

    @unittest.skip("生产测试用例，手动执行")
    def test_202_sn_sn_rightNodeUsePayChannel_TerraPay_RUB(self):
        sn1 = RMNData.sn_usd_us_a
        sn2 = RMNData.sn_roxe_terrapay["RU"]

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "RUB"
        r_country = "RU"
        r_account_number = "40817810401002050444"
        r_name = "KSENIYA SERGEEVNA ZHESTOVSKAYA"
        r_bank_name = "UNICREDIT BANK"
        r_bank_code = "044525700"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        # creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_agent = {"finInstnId": {"nm": r_bank_name, "clrSysMmbId": {"clrSysCd": "RUCBC", "mmbId": r_bank_code}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")

        sendFee = 0.10

        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, r_account_number,
                                                                inAmount=4)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_not_check_db_1(sn1, sn2, cdtTrfTxInf, [0.10, 1.75], self, isInnerNode=inner_node)

    @unittest.skip("生产测试用例，手动执行")
    def test_203_sn_sn_rightNodeUsePayChannel_TerraPay_VND(self):
        sn1 = RMNData.sn_usd_us_a
        sn2 = RMNData.sn_roxe_terrapay["VN"]

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "VND"
        r_country = "VN"
        r_account_number = "060190228218"
        r_name = "NGUYEN HUYNH THANH TRUC"
        r_bank_name = "Saigon Thuong Tin Commercial Joint Stock Bank"
        r_bank_code = "SGTTVNVX"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        # ctctDtls = {"phneNb": "+84977967162"}
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        # creditor_agent = {"finInstnId": {"nm": r_bank_name, "clrSysMmbId": {"clrSysCd": "INFSC", "mmbId": r_bank_code}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")

        sendFee = 0.10

        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, r_account_number,
                                                                inAmount=4)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_not_check_db_1(sn1, sn2, cdtTrfTxInf, [0.10, 1.75], self, isInnerNode=inner_node)

    @unittest.skip("生产测试用例，手动执行")
    def test_204_sn_sn_rightNodeUsePayChannel_TerraPay_CNY(self):
        sn1 = RMNData.sn_usd_us_a
        sn2 = RMNData.sn_roxe_terrapay["CN"]

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "CNY"
        r_country = "CN"
        r_account_number = "6214830110455572"
        r_name = "YANPING CHAI"
        r_bank_name = "UNION PAY"
        r_bank_code = "CHUYCNS1"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        ctctDtls = {"phneNb": "+8613911224525"}
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country, ctctDtls=ctctDtls)
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        # creditor_agent = {"finInstnId": {"nm": r_bank_name, "clrSysMmbId": {"clrSysCd": "INFSC", "mmbId": r_bank_code}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")

        sendFee = 0.10
        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, r_account_number,
                                                                inAmount=5.5)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_not_check_db_1(sn1, sn2, cdtTrfTxInf, [0.10, 3.50], self, isInnerNode=inner_node)

    @unittest.skip("生产测试用例，手动执行")
    def test_205_sn_sn_rightNodeUsePayChannel_TerraPay_EUR_FR(self):
        sn1 = RMNData.sn_usd_us_a
        sn2 = RMNData.sn_roxe_terrapay["FR"]

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "EUR"
        r_country = "FR"
        r_account_number = "FR7720041000016702233S02022"
        r_name = "OBEL OKELI MAYEUL GILDAS"
        r_bank_name = "LA BANQUE POSTALE"

        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": r_bank_name}}
        # creditor_agent = {"finInstnId": {"nm": r_bank_name, "clrSysMmbId": {"clrSysCd": "INFSC", "mmbId": r_bank_code}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        sendFee = 0.10

        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, r_account_number,
                                                                inAmount=5)
        cdtTrfTxInf["cdtrAcct"].pop("acctId")
        cdtTrfTxInf["cdtrAcct"]["iban"] = r_account_number
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_not_check_db_1(sn1, sn2, cdtTrfTxInf, [0.10, 1.20], self, isInnerNode=inner_node)

    @unittest.skip("生产测试用例，手动执行")
    def test_206_sn_sn_rightNodeUsePayChannel_TerraPay_GBP(self):
        sn1 = RMNData.sn_usd_us_a
        sn2 = RMNData.sn_roxe_terrapay["GB"]

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "GBP"
        r_country = "GB"
        r_account_number = "79541250"
        r_name = "Miller Andres Rodriguez Lopez"
        r_bank_name = "Starling Bank"
        r_bank_code = "608371"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        # creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_agent = {"finInstnId": {"nm": r_bank_name, "clrSysMmbId": {"clrSysCd": "GBDSC", "mmbId": r_bank_code}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        sendFee = 0.10

        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, r_account_number,
                                                                inAmount=3)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_not_check_db_1(sn1, sn2, cdtTrfTxInf, [0.10, 1.10], self, isInnerNode=inner_node)

    @unittest.skip("生产测试用例，手动执行")
    def test_207_sn_sn_rightNodeUsePayChannel_TerraPay_GHS(self):
        sn1 = RMNData.sn_usd_us_a
        sn2 = RMNData.sn_roxe_terrapay["GH"]

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "GHS"
        r_country = "GH"
        r_account_number = "0091552604091"
        r_name = "MICHAEL CHARWAY"
        r_bank_name = "ACCESS BANK"
        r_bank_code = "ABNGGHAC"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        # creditor_agent = {"finInstnId": {"nm": r_bank_name, "clrSysMmbId": {"clrSysCd": "INFSC", "mmbId": r_bank_code}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")

        sendFee = 0.10

        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, r_account_number,
                                                                inAmount=3.6)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_not_check_db_1(sn1, sn2, cdtTrfTxInf, [0.10, 1.75], self, isInnerNode=inner_node)

    @unittest.skip("生产测试用例，手动执行")
    def test_208_sn_sn_rightNodeUsePayChannel_TerraPay_BRL(self):
        sn1 = RMNData.sn_usd_us_a
        sn2 = RMNData.sn_roxe_terrapay["BR"]

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "BRL"
        r_country = "BR"
        # r_account_number = "115873-2"
        # r_name = "LUCIANA CARLA BORAGINA"
        # r_bank_name = "Banco Bradesco S.A."
        # r_bank_code = "BANBRBR"
        # brnchId = {"id": "0111"}

        r_account_number = "01005782-6"
        r_name = "Carlos A M Cadavid"
        r_bank_name = "Santander Brasil"
        r_bank_code = "BSSCCOBB"
        brnchId = {"id": "1503"}
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code, brnchId=brnchId)
        # creditor_agent = {"finInstnId": {"nm": r_bank_name, "clrSysMmbId": {"clrSysCd": "INFSC", "mmbId": r_bank_code}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")

        sendFee = 0.10

        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, r_account_number,
                                                                inAmount=4)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_not_check_db_1(sn1, sn2, cdtTrfTxInf, [0.10, 1.20], self, isInnerNode=inner_node)

    @unittest.skip("生产测试用例，手动执行")
    def test_209_sn_sn_rightNodeUsePayChannel_TerraPay_THB(self):
        sn1 = RMNData.sn_usd_us_a
        sn2 = RMNData.sn_roxe_terrapay["TH"]

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "THB"
        r_country = "TH"
        # 数据问题：Invalid Beneficiary Account
        # r_account_number = "5792752939"
        # r_name = "Siriporn Krasaeat"
        # r_bank_name = "Siam Commercial Bank"
        # r_bank_code = "SICOTHBK"

        r_account_number = "9250150530"
        r_name = "EUSTACE LOBO"
        r_bank_name = "Bangkok Bank"
        r_bank_code = "BKKBTHBK"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        # creditor_agent = {"finInstnId": {"nm": r_bank_name, "clrSysMmbId": {"clrSysCd": "INFSC", "mmbId": r_bank_code}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")

        sendFee = 0.10

        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, r_account_number,
                                                                inAmount=4.5)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_not_check_db_1(sn1, sn2, cdtTrfTxInf, [0.10, 2.25], self,
                                                         isInnerNode=inner_node)

    @unittest.skip("生产测试用例，手动执行")
    def test_210_sn_sn_rightNodeUsePayChannel_TerraPay_ZAR(self):
        sn1 = RMNData.sn_usd_us_a
        sn2 = RMNData.sn_roxe_terrapay["ZA"]

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "ZAR"
        r_country = "ZA"
        # r_account_number = "78600000002"
        # r_name = "ANAND NAIDOO"
        # r_bank_name = "Sasfin"
        # r_bank_code = "SASFZAJJ"
        # ctctDtls = {"phneNb": "+27823375512"}

        # r_account_number = "62362224992"
        # r_name = "ANDRONICA MPHAHLELE"
        # r_bank_name = "First National Bank of South Africa"
        # r_bank_code = "FIRNZAJJ"
        # ctctDtls = {"phneNb": "+27835360301"}

        # r_account_number = "9346617558"
        # r_name = "TSHILILO LIGEGE"
        # r_bank_name = "ABSA Bank"
        # r_bank_code = "ABSAZAJJ"
        # ctctDtls = {"phneNb": "+27823976562"}

        r_account_number = "38038390535"
        r_name = "LEE HENDERSON"
        r_bank_name = "ABSA Bank"
        r_bank_code = "ABSAZAJJ"
        ctctDtls = {"phneNb": "+27837738087"}

        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")

        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country, ctctDtls=ctctDtls)
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        # creditor_agent = {"finInstnId": {"nm": r_bank_name, "clrSysMmbId": {"clrSysCd": "INFSC", "mmbId": r_bank_code}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")

        sendFee = 0.10

        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, r_account_number,
                                                                inAmount=4.5)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_not_check_db_1(sn1, sn2, cdtTrfTxInf, [0.10, 1.75], self,
                                                         isInnerNode=inner_node)

    @unittest.skip("生产测试用例，手动执行，测试账户无效暂不处理")
    def test_211_sn_sn_rightNodeUsePayChannel_TerraPay_USD_ZW(self):
        sn1 = RMNData.sn_usd_us_a
        sn2 = RMNData.sn_roxe_terrapay["ZW"]

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "USD"
        r_country = "ZW"
        r_account_number = "4112086072405"
        r_name = "Andrew Mugari"
        r_bank_name = "ZB Bank First Street"
        r_bank_code = "ZBCOZWHX"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        # creditor_agent = {"finInstnId": {"nm": r_bank_name, "clrSysMmbId": {"clrSysCd": "INFSC", "mmbId": r_bank_code}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")

        sendFee = 0.10

        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, r_account_number,
                                                                inAmount=3.6)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_not_check_db_1(sn1, sn2, cdtTrfTxInf, [0.10, 1.75], self,
                                                         isInnerNode=inner_node)

    @unittest.skip("生产测试用例，手动执行")
    def test_212_sn_sn_rightNodeUsePayChannel_TerraPay_MYR(self):
        sn1 = RMNData.sn_usd_us_a
        sn2 = RMNData.sn_roxe_terrapay["MY"]

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "MYR"
        r_country = "MY"
        r_account_number = "364101162108"
        r_name = "Vinay Muzumdar"
        r_bank_name = "HSBC Bank"
        r_bank_code = "HBMBMYKL"
        debtor = RMNData.debtor
        ctctDtls = {"phneNb": "+60122077304"}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country, ctctDtls=ctctDtls)
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        # creditor_agent = {"finInstnId": {"nm": r_bank_name, "clrSysMmbId": {"clrSysCd": "INFSC", "mmbId": r_bank_code}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")

        sendFee = 0.10

        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, r_account_number,
                                                                inAmount=3.6)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_not_check_db_1(sn1, sn2, cdtTrfTxInf, [0.10, 1.75], self,
                                                         isInnerNode=inner_node)

    @unittest.skip("生产测试用例，手动执行")
    def test_213_sn_sn_rightNodeUsePayChannel_TerraPay_PEN(self):
        sn1 = RMNData.sn_usd_us_a
        sn2 = RMNData.sn_roxe_terrapay["PE"]

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "PEN"
        r_country = "PE"
        r_account_number = "00219313084958709612"
        r_name = "SANTIAGO JOSE DE AUBEYZON PEIRANO"
        r_bank_name = "Scotiabank"
        r_bank_code = "SCOTIOBAN"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        # creditor_agent = {"finInstnId": {"nm": r_bank_name, "clrSysMmbId": {"clrSysCd": "INFSC", "mmbId": r_bank_code}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")

        sendFee = 0.10

        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, r_account_number,
                                                                inAmount=3.7)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_not_check_db_1(sn1, sn2, cdtTrfTxInf, [0.10, 1.60], self, isInnerNode=inner_node)

    @unittest.skip("生产测试用例，手动执行")
    def test_214_sn_sn_rightNodeUsePayChannel_TerraPay_MXN(self):
        sn1 = RMNData.sn_usd_us_a
        sn2 = RMNData.sn_roxe_terrapay["MX"]

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "MXN"
        r_country = "MX"
        # r_account_number = "002028904190987517"
        # r_name = "MAURICIO JACUINDE MIRAMONTES"
        # r_bank_name = "BANAMEX"
        # r_bank_code = "BNMXMXMM"

        # r_account_number = "4152313794893862"
        # r_name = "FRANCISCO IBARRA MORENO"
        # r_bank_name = "BBVA BANCOMER"
        # r_bank_code = "BCMRMXMM"

        # r_account_number = "4815163018598279"
        # r_name = "ABRIL ALEJANDRA MARTINEZ MARTINEZ"
        # r_bank_name = "BBVA BANCOMER"
        # r_bank_code = "BCMRMXMM"

        r_account_number = "012180001116984192"
        r_name = "DEMERGE MEXICO"
        r_bank_name = "HSBC"
        r_bank_code = "HSBCMXMM"

        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        # creditor_agent = {"finInstnId": {"nm": r_bank_name, "clrSysMmbId": {"clrSysCd": "INFSC", "mmbId": r_bank_code}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")

        sendFee = 0.10

        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, r_account_number,
                                                                inAmount=4)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_not_check_db_1(sn1, sn2, cdtTrfTxInf, [0.10, 1.35], self,
                                                         isInnerNode=inner_node)

    @unittest.skip("生产测试用例，手动执行")
    def test_215_sn_sn_rightNodeUsePayChannel_TerraPay_ARS(self):
        sn1 = RMNData.sn_usd_us_a
        sn2 = RMNData.sn_roxe_terrapay["AR"]

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "ARS"
        r_country = "AR"
        r_account_number = "0170116240000008367534"
        r_name = "MERCEDES BAYLAC"
        r_bank_name = "Banco Comafi"
        r_bank_code = "BANCOMAR"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        # creditor_agent = {"finInstnId": {"nm": r_bank_name, "clrSysMmbId": {"clrSysCd": "INFSC", "mmbId": r_bank_code}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")

        sendFee = 0.10

        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, r_account_number,
                                                                inAmount=3.6)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_not_check_db_1(sn1, sn2, cdtTrfTxInf, [0.10, 1.75], self,
                                                         isInnerNode=inner_node)

    @unittest.skip("生产测试用例，手动执行，没有提供BIC暂不处理")
    def test_216_sn_sn_rightNodeUsePayChannel_TerraPay_PLN(self):
        sn1 = RMNData.sn_usd_us_a
        sn2 = RMNData.sn_roxe_terrapay["PL"]

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "PLN"
        r_country = "PL"
        r_account_number = "97116022020000000099275745"
        r_name = "ROBERT LEWANDOWSKI"
        r_bank_name = "Bank Millennium Spolka Akcyjna"
        r_bank_code = ""
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        # creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_agent = {"finInstnId": {"nm": r_bank_name, "clrSysMmbId": {"clrSysCd": "PLKNR", "mmbId": r_bank_code}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")

        sendFee = 0.10

        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, r_account_number,
                                                                inAmount=3.6)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_not_check_db_1(sn1, sn2, cdtTrfTxInf, [0.10, 1.75], self,
                                                         isInnerNode=inner_node)

    @unittest.skip("生产测试用例，手动执行，费用暂不支持百分比配置，暂不处理")
    def test_217_sn_sn_rightNodeUsePayChannel_TerraPay_CAD(self):
        sn1 = RMNData.sn_usd_us_a
        sn2 = RMNData.sn_roxe_terrapay["CA"]

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "CAD"
        r_country = "CA"
        r_account_number = "6146198"
        r_name = "DANIEL PHILIP CHACKAPARAMBI"
        r_bank_name = "CIBC"
        r_bank_code = "01003869"
        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        # creditor_agent = self.client.make_terrapay_roxe_agent(r_bank_name, r_bank_code)
        creditor_agent = {"finInstnId": {"nm": r_bank_name, "clrSysMmbId": {"clrSysCd": "CACPA", "mmbId": r_bank_code}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")

        sendFee = 0.10

        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, r_account_number,
                                                                inAmount=3.6)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_not_check_db_1(sn1, sn2, cdtTrfTxInf, [0.10, 1.75], self,
                                                         isInnerNode=inner_node)

    @unittest.skip("生产测试用例，手动执行")
    def test_218_sn_sn_rightNodeUsePayChannel_TerraPay_EUR_BE(self):
        sn1 = RMNData.sn_usd_us_a
        sn2 = RMNData.sn_roxe_terrapay["BE"]

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "EUR"
        r_country = "BE"
        r_account_number = "BE09967104778857"
        r_name = "Veera Muthusamy"
        r_bank_name = "TransferWise"

        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": r_bank_name}}
        # creditor_agent = {"finInstnId": {"nm": r_bank_name, "clrSysMmbId": {"clrSysCd": "INFSC", "mmbId": r_bank_code}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        sendFee = 0.10

        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, r_account_number,
                                                                inAmount=5)
        cdtTrfTxInf["cdtrAcct"].pop("acctId")
        cdtTrfTxInf["cdtrAcct"]["iban"] = r_account_number
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_not_check_db_1(sn1, sn2, cdtTrfTxInf, [0.10, 1.20], self,
                                                         isInnerNode=inner_node)

    @unittest.skip("生产测试用例，手动执行")
    def test_219_sn_sn_rightNodeUsePayChannel_TerraPay_EUR_EE(self):
        sn1 = RMNData.sn_usd_us_a
        sn2 = RMNData.sn_roxe_terrapay["EE"]

        addenda_info = copy.deepcopy(RMNData.out_bank_info["TerraPay"])
        r_currency = "EUR"
        r_country = "EE"
        r_account_number = "EE641010011644993222"
        r_name = "Bharath Chari"
        r_bank_name = "AS SEB PANK"

        debtor = RMNData.debtor
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": r_bank_name}}
        # creditor_agent = {"finInstnId": {"nm": r_bank_name, "clrSysMmbId": {"clrSysCd": "INFSC", "mmbId": r_bank_code}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="terrapay node")
        creditor = self.client.make_terrapay_roxe_cdtr(r_name, r_country)
        sendFee = 0.10

        cdtTrfTxInf = self.client.make_channel_RCCT_information("USD", r_currency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, r_account_number,
                                                                inAmount=5.2)
        cdtTrfTxInf["cdtrAcct"].pop("acctId")
        cdtTrfTxInf["cdtrAcct"]["iban"] = r_account_number
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_not_check_db_1(sn1, sn2, cdtTrfTxInf, [0.10, 1.20], self,
                                                         isInnerNode=inner_node)

    @unittest.skip("生产测试用例，手动执行")
    def test_220_sn_sn_rightNodeUsePayChannel_nium_CAD(self):
        sn1 = RMNData.sn_usd_us_a
        sn2 = RMNData.sn_roxe_nium

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "CAD"
        recCountry = "CA"
        accountId = "5215504"
        debtor = {
            "nm": "Michael Stallman",
            "prvtId": {"othr": {"prtry": "CCPT", "id": "12345678911234"}},
            "pstlAdr": {"adrLine": "563 Mayo Street", "twnNm": "Southfield", "ctrySubDvsn": "Washington", "pstCd": "5360"},
            "ctryOfRes": sendCountry}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {
            "nm": "Wei Tang",
            "ctryOfRes": recCountry,
            "pstlAdr": {"adrLine": "23-127 BanYan Cres", "twnNm": "SASKATOON", "ctrySubDvsn": "SK", "pstCd": "S7V1G5"}}
        # creditor_agent = {"finInstnId": {"nm": "Royal Bank", "bicFI": "ROYCCAT2"}}
        creditor_agent = {"finInstnId": {"nm": "Royal Bank", "clrSysMmbId": {"clrSysCd": "CACPA", "mmbId": "00307758"}}}  # mmbid:前三位bank code，后五位transit number
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="NIUM node")
        addenda_info = None
        sendFee = 0.10

        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, accountId, inAmount=5)
        cdtTrfTxInf["purp"] = {"desc": "Representative office expenses"}
        self.client.logger.info(cdtTrfTxInf)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        msg_id, tx_msg, end2end_id, rmn_tx_id, st_msg = self.client.transactionFlow_sn_sn_not_check_db_1(sn1, sn2, cdtTrfTxInf, [0.10, 3.00], self, isInnerNode=inner_node)
        self.client.logger.warning("msg_id={}, tx_msg={}, end2end_id={}, rmn_tx_id={}, st_msg={}".format(msg_id, tx_msg, end2end_id, rmn_tx_id, st_msg))

    @unittest.skip("生产测试用例，手动执行")
    def test_221_sn_sn_rightNodeUsePayChannel_cebuana(self):
        sn1 = RMNData.sn_usd_us_a
        sn2 = RMNData.sn_roxe_cebuana

        sendCurrency = "USD"
        sendCountry = "US"
        recCurrency = "PHP"
        recCountry = "PH"
        accountId = "005400234780"

        # debtor = RMNData.debtor
        debtor = {"nm": "RISN To Cebuana",
                  # "prvtId": {"othr": {"prtry": "CCPT", "id": "12345678911234"}},
                  "pstlAdr": {"ctry": sendCountry, "adrLine": "563 Mayo Street"}}
        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor = {"nm": "Anna Mae Quizon", "pstlAdr": {"adrLine": "001 Central Avenue"}}
        creditor_agent = {"finInstnId": {"nm": "Banco De Oro", "bicFI": "BNORPHMM"}}
        # creditor_agent = {"finInstnId": {"nm": "Banco De Oro", "clrSysMmbId": {"clrSysCd": "BRSTN", "mmbId": "010690015"}}}
        creditor_intermediary_agent = self.client.make_roxe_agent(sn2, "SN", name="CEBUANA node")
        addenda_info = None
        sendFee = 0.10

        cdtTrfTxInf = self.client.make_channel_RCCT_information(sendCurrency, recCurrency, debtor, debtor_agent, creditor,
                                                                creditor_agent, creditor_intermediary_agent,
                                                                float(sendFee), sn1, addenda_info, accountId, inAmount=3.2)
        self.client.logger.info(cdtTrfTxInf)
        inner_node = True if sn2 in RMNData.channel_nodes else False
        self.client.transactionFlow_sn_sn_not_check_db_1(sn1, sn2, cdtTrfTxInf, [0.10, 75.00], self, isInnerNode=inner_node)

    @unittest.skip("生产测试用例，手动执行")
    def test_222_sn_sn_rightNodeUsePayChannel_gcash_PHP(self):
        sn1 = RMNData.sn_usd_us
        # sn2 = RMNData.sn_roxe_terrapay["IN"]

        debtor_agent = self.client.make_roxe_agent(sn1, "SN")
        creditor_agent = {"finInstnId": {"nm": "test bank"}}
        cdtrAcct = {"schmeNm": {"prtry": "PH"}, "issr": "GCASH", "acctId": "09612803885", "ccy": "PHP"}
        amt = ApiUtils.randAmount(10, 2, 3)
        amt = 2.5
        sn1_fee, sn2_fee, sn2 = self.client.step_queryRouter(sn1, "USD", "PHP", cdtrAcct=cdtrAcct, tp='EWALLET',
                                                             amount=amt)

        cdtTrfTxInf = self.client.make_RCCT_information(
            "USD", "PHP", RMNData.prvtId, debtor_agent, RMNData.prvtId_b, creditor_agent, sn1_fee, sn1,
            cdtrAcct=cdtrAcct, inAmount=amt
        )
        cdtTrfTxInf["pmtTpInf"] = {"lclInstrm": {"cd": "EWALLET"}}
        cdtTrfTxInf["cdtr"]["nm"] = "Test Test"
        cdtTrfTxInf["cdtr"]["pstlAdr"]["ctry"] = "PH"
        cdtTrfTxInf["dbtr"]["prvtId"]["othr"]["prtry"] = "DRIVER_LICENSE"
        cdtTrfTxInf["splmtryData"]["addenda"]["senderSourceOfFund"] = "bank account"
        cdtTrfTxInf["splmtryData"]["addenda"]["receiverWalletCode"] = "GCASH"
        self.client.logger.info(json.dumps(cdtTrfTxInf))

        self.client.transactionFlow_sn_sn_not_check_db_1(sn1, sn2, cdtTrfTxInf, [sn1_fee, sn2_fee], self, True)
