# codinng=utf-8
# author: Li MingLei
# date: 2022-04-21
import os
from roxe_libs.Global import Global
from roxe_libs import settings
from roxe_libs.pub_function import loadYmlFile


class RMNData:
    env = Global.getValue(settings.environment)
    cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), f"./config/rmn_{env}.yml"))
    _yaml_conf = loadYmlFile(cfg_path)

    # env_sign = _yaml_conf["env"]
    host = _yaml_conf["host"]
    chain_host = _yaml_conf.get("chain_host")
    rmn_id = _yaml_conf.get("rmn_id")
    api_key = _yaml_conf.get("api_key")
    sec_key = _yaml_conf.get("sec_key")
    node_rsa_key = _yaml_conf.get("node_rsa_private_key")

    rts_node_host = _yaml_conf.get("rts_node_host")

    iban = _yaml_conf.get("iban")

    mock_node = _yaml_conf.get("mock_node")
    nium_node = _yaml_conf.get("nium_node")

    pn_usd_us = _yaml_conf.get("pn_usd_us")
    sn_usd_us = _yaml_conf.get("sn_usd_us")
    pn_usd_gb = _yaml_conf.get("pn_usd_gb")
    sn_usd_gb = _yaml_conf.get("sn_usd_gb")

    pn_gbp_gb = _yaml_conf.get("pn_gbp_gb")
    sn_gbp_gb = _yaml_conf.get("sn_gbp_gb")
    pn_gbp_us = _yaml_conf.get("pn_gbp_us")
    sn_gbp_us = _yaml_conf.get("sn_gbp_us")

    sn_eur_fr = _yaml_conf.get("sn_eur_fr")
    rpp_node_usd2php = _yaml_conf.get("rpp_node_php")
    sn_php_ph = _yaml_conf.get("sn_php_ph")

    pn_php_ph = _yaml_conf.get("pn_php_ph")
    pn_eur_fr = _yaml_conf.get("pn_eur_fr")
    pn_usd_us_b = _yaml_conf.get("pn_usd_us_b")
    # 线上环境节点
    sn_usd_us_a = _yaml_conf.get("sn_usd_us_a")
    sn_usd_us_b = _yaml_conf.get("sn_usd_us_b")
    sn_krw_kr = _yaml_conf.get("sn_krw_kr")  # 生产测试GME下单使用

    # 通道节点通过get方法取得
    sn_roxe_terrapay = _yaml_conf.get("sn_roxe_terrapay")
    sn_roxe_nium = _yaml_conf.get("sn_roxe_nium")
    sn_roxe_cebuana = _yaml_conf.get("sn_roxe_cebuana")

    # 归属于channel的节点，
    channel_nodes = _yaml_conf.get("channel_nodes")

    iban_agent = _yaml_conf.get("iban_agent_info")
    bic_agents = _yaml_conf.get("bic_agent_info")
    ncc_agents = _yaml_conf.get("ncc_agent_info")

    query_tx_info = _yaml_conf["query_tx_info"] if "rmn-uat" not in host else _yaml_conf["query_tx_info_uat"]

    # prvtId = _yaml_conf["prvtId"]
    # prvtId_b = _yaml_conf.get("prvtId_b")
    # orgId = _yaml_conf["orgId"]
    # orgId_b = _yaml_conf.get("orgId_b")
    # debtor = _yaml_conf["debtor"]  # 借款人信息（左侧）

    prvtId = {
        "nm": "Jethro Test 001",
        # "frstNm": "Jethro Test 001", "mdlNm": "test", "lstNm": "001",
        "pstlAdr": {
            "pstCd": "123456", "twnNm": "helel", "twnLctnNm": "Olmpic", "dstrctNm": "god street",
            "ctrySubDvsn": "tai h",
            "ctry": "US",
            "adrLine": "abcd 1234 abcd XXXX"
        },
        "prvtId": {
            "dtAndPlcOfBirth": {"ctryOfBirth": "US", "prvcOfBirth": "New York", "cityOfBirth": "New York City", "birthDt": "1960-05-24"},
            "othr": {"id": "123412341234", "prtry": "Driving License", "issr": "US"}
        },
        "ctctDtls": {"phneNb": "1 983384893"}
    }
    prvtId_b = {
        "nm": "Jethro Test 002",
        "pstlAdr": {"pstCd": "asd123", "twnNm": "xasd", "twnLctnNm": "asda", "dstrctNm": "1 street", "ctrySubDvsn": "xx h", "ctry": "GB", "adrLine": "abcd 1234"},
        "prvtId": {
            "dtAndPlcOfBirth": {"ctryOfBirth": "GB", "prvcOfBirth": "London", "cityOfBirth": "London City", "birthDt": "1983-05-24"},
            "othr": {"id": "xs1233das", "prtry": "ID Card", "issr": "GB"}}
    }
    orgId = {
        "nm": "org Test 001",
        "pstlAdr": {"pstCd": "1623123", "twnNm": "abdas1", "twnLctnNm": "xxsad1", "dstrctNm": "ss street", "ctrySubDvsn": "absdr", "ctry": "GB", "adrLine": "abcd 1234 abcd xas123"},
        "orgId": {"lei": "XX12341234", "anyBIC": "BOFAUS3DAU211", "othr": {"prtry": "abcd1234", "id": "abcd1133", "issr": "GB"}},
        "ctctDtls": {"emailAdr": "asd@test1.com", "phneNb": "1234123412"}
    }
    orgId_b = {
        "nm": "org Test 002",
        "pstlAdr": {"pstCd": "12341234", "twnNm": "abdas1", "twnLctnNm": "xxsad1", "dstrctNm": "ss street", "ctrySubDvsn": "absdr", "ctry": "GB", "adrLine": "abcd 1234 abcd xas123"},
        "orgId": {
            "lei": "abc1234",
            "anyBIC": "MOLUGB22123444",
            "othr": {"prtry": "abc1234", "id": "abc1234", "issr": "US"}
        },
        "ctctDtls": {"emailAdr": "asd@test1.com", "phneNb": "1234123412"}
    }
    debtor = {
        "nm": "Jethro Test boy", "ctctDtls": {"phneNb": "+19718084756"},
        "pstlAdr": {"ctry": "US", "twnNm": "helel", "adrLine": "No. 1 chang an Avenue"},
        "prvtId": {
            "dtAndPlcOfBirth": {"ctryOfBirth": "US", "cityOfBirth": "New York", "birthDt": "1990-06-01"},
            "othr": {"prtry": "passport", "id": "6918625", "issr": "GB"}
        }
    }
    # Sender Id Type ["nationalidcard", "drivinglicense", "passport"]

    out_bank_info = _yaml_conf["out_bank_info"]  # 收款人信息

    is_check_db = _yaml_conf["is_check_db"]
    sql_cfg = _yaml_conf["sql_cfg"]
