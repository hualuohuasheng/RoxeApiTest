# coding=utf-8
# author: Li MingLei
# date: 2022-06-15

import os
from roxe_libs import settings
from roxe_libs.Global import Global
from roxe_libs.pub_function import loadYmlFile


class RTSData:
    env = Global.getValue(settings.environment)
    cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), f"./config/rts_{env}.yml"))
    # cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), f"./config/rts_uat.yml"))
    # cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), f"./config/rts_bjtest.yml"))
    yaml_conf = loadYmlFile(cfg_path)

    host = yaml_conf["host"]
    chain_host = yaml_conf["chain_host"]
    api_id = yaml_conf["api_id"]
    sec_key = yaml_conf["sec_key"]
    ssl_pub_key = yaml_conf["ssl_pub_key"]
    ssl_pri_key = yaml_conf["ssl_pri_key"]

    node_code_sn = yaml_conf["node_code_sn"]
    node_code_pn = yaml_conf["node_code_pn"]
    contract_info = yaml_conf.get("contract_info")

    # 生产环境节点
    sn_usd_us_a = yaml_conf.get("sn_usd_us_a")
    sn_usd_us_b = yaml_conf.get("sn_usd_us_b")

    currency_fiat_ro = yaml_conf["currency_fiat_ro"]
    currency_fiat_fiat = yaml_conf.get("currency_fiat_fiat")

    user_account = yaml_conf["user_account"]
    user_account_2 = yaml_conf["user_account_2"]

    token_1 = yaml_conf["token_1"]
    userId_1 = yaml_conf["userId_1"]

    # 拥有私钥的链上账户, ro转账时使用
    chain_account = yaml_conf["chain_account"]
    chain_pri_key = yaml_conf["chain_pri_key"]

    # 持有ach账户的用户信息, 测试涉及到法币入金的场景时使用
    ach_user_token = yaml_conf["ach_user_token"]
    ach_user_id = yaml_conf["ach_user_id"]
    ach_user_account = yaml_conf["ach_user_account"]

    # 属于rmn的sn节点, 测试法币到法币的场景
    rmn_node = yaml_conf.get("rmn_node")
    mock_node = yaml_conf.get("mock_node")
    # 渠道名称，用于在RPC中查找对应渠道或者节点的币种费用
    channel_name = yaml_conf.get("channel_name")

    # 归属于channel的节点
    channel_nodes = yaml_conf.get("channel_nodes")

    # 通道类型节点
    terrapay_node_ph = yaml_conf.get("terrapay_node_ph")
    terrapay_node_th = yaml_conf.get("terrapay_node_th")
    nium_node = yaml_conf.get("nium_node")
    cebuana_node = yaml_conf.get("cebuana_node")
    gcash_node = yaml_conf.get("gcash_node")
    checkout_node = yaml_conf.get("checkout_node")
    terrapay_node = yaml_conf.get("terrapay_node")

    targetRoxeAccount_2 = yaml_conf.get("targetRoxeAccount_2")

    out_currency_info = yaml_conf["out_currency_info"]

    is_check_db = yaml_conf["is_check_db"]
    sql_cfg = yaml_conf["sql_cfg"]

    digitalCurrency = ["rgKEYMB", "rgQVSKR", "rgTLFPH", "rgTESTA", "rgTESTB", "rgTESTC", "rgTESTD", "rgTESTE",
                       "rgTESTF", "rgTESTG", "rgTESTH", "rgTESTI", "rgTESTJ", "rgTESTK", "rgXCTNF", "rgOGGXH",
                       "rgXDQKW", "rgPHVEB", "rgOZDIU", "rgHGQJR", "rgNROBC", "rgGKWYQ", "rgAJYWZ"]  # "USDT",

    notify_url_rts = "http://172.17.3.95:8005/api/rts/receiveNotify"

    terrapay_receive_info = {
        "senderFirstName": "Jack XX",
        "senderLastName": "Bob XX",
        "senderIdType": "nationalidcard",
        "senderIdNumber": "012345",
        "senderIdExpireDate": "2100-06-01",
        "senderNationality": "US",
        "senderCountry": "US",
        "senderCity": "New York",
        "senderAddress": "Street 123",
        "senderPhone": "789123456",
        "senderBirthday": "2000-06-01",
        "senderBeneficiaryRelationship": "Friend",
        "senderSourceOfFund": "Salary",
        "purpose": "Gift",

        "receiverFirstName": "RANDY",
        "receiverLastName": "OYUGI",
        "receiverAccountName": "Asia United Bank",
        "receiverAccountNumber": "20408277204478",
        "receiverBankName": "XXX BANK",
        "receiverCountry": "PH",
        "receiverCurrency": "PHP",
        "receiveMethodCode": "BANK",
        "receiverBankBIC": "AUBKPHMM"
    }
    gcash_receive_info = {
        "receiverAccountNumber": "09056628913",
        "receiverCurrency": "PHP",
        "senderFirstName": "Test user",
        "senderMiddleName": "abc",
        "senderLastName": "handsome",
        "senderBeneficiaryRelationship": "Friend",
        "senderSourceOfFund": "Salary",
        "senderIdNumber": "123456789",
        "receiverFirstName": "BILLSPAY",
        "receiverMiddleName": "UAT",
        "receiverLastName": "TESTING",
        "receiveMethodCode": "EWALLET",
        "receiverWalletCode": "GCASH",
        "senderIdType": "PASSPORT_ID",
        "senderCountry": "US",
        "receiverBankBIC": "abc"
    }
    cebuana_receive_info = {
        "receiveMethodCode": "BANK",
        "receiverAccountNumber": "109450542671",
        "senderCountry": "US",
        "senderFirstName": "Test user",
        "senderMiddleName": "abc",
        "senderLastName": "handsome",
        "senderAddress": "1 Financial Street",
        "receiverCurrency": "PHP",
        "receiverFirstName": "Jack XX",
        "receiverMiddleName": "abc",
        "receiverLastName": "Bob XX",
        "receiverAddress": "abc",
        "receiverBankBIC": "CTCBPHMM",
        "receiverBankNCC": "",
        "receiverBankNCCType": ""
    }

    rmn_receive_info = {
        "receiverLastName": "001",
        "senderNationality": "US",
        "senderAddress": "abcd 1234 abcd XXXX",
        "receiverMiddleName": "Test",
        "purpose": "transfer my money",
        "receiverBankName": "china bank",
        "remark": "remark 1663668163.953909",
        "receiverIdNumber": "123412341234",
        "senderIdNumber": "123412341234",
        "receiverStates": "tai h",
        "receiverCity": "helel",
        "receiverAccountName": "Li XX",
        "receiverCountry": "US",
        "senderPostcode": "123456",
        "receiverAccountNumber": "987654321",
        "senderMiddleName": "Test",
        "tel": "!23123123xx",
        "senderBirthday": "1960-05-24",
        "receiverFirstName": "Jethro",
        "senderLastName": "001",
        "senderCountry": "US",
        "senderAccountNumber": "123456789012",
        "receiverIdType": "driver license",
        "senderIdType": "driver license",
        "senderFirstName": "Jethro",
        "receiverNationality": "US",
        "receiveMethodCode": "BANK",
        "receiverPostcode": "123456",
        "senderCity": "helel",
        "receiverAddress": "abcd 1234 abcd XXXX",
        "senderStates": "tai h",
        "senderIdIssueCountry": "US",
        "receiverCurrency": "USD",
        "senderBeneficiaryRelationship": "hellos"
    }
