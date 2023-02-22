# coding=utf-8
# author: Li MingLei
# date: 2021-10-15
"""
RoxeUserCenter系统【RoxeApp的用户中心】Api的测试用例
"""
import unittest
import json
import os
import time
from .RoxeUserCenterApi import RoxeUserCenterApiClient
from roxe_libs import settings
from roxe_libs.Global import Global
from roxe_libs.DBClient import RedisClient, Mysql
from roxe_libs.pub_function import loadYmlFile

from RoxeKyc.RoxeKycApiTest import RoxeKycData, RoxeKycApiClient


class RoxeUserCenterData:

    env = Global.getValue(settings.environment)
    cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), f"./RoxeUserCenter_{env}.yml"))
    _yaml_conf = loadYmlFile(cfg_path)
    host = _yaml_conf["host"]
    # 通过km的用户
    user_id = _yaml_conf["user_id"]
    user_account = _yaml_conf["user_account"]
    user_login_token = _yaml_conf["user_login_token"]

    # 通过ka的用户
    user_id_b = _yaml_conf["user_id_b"]
    user_account_b = _yaml_conf["user_account_b"]
    user_login_token_b = _yaml_conf["user_login_token_b"]

    # 没有通过kyc的用户
    user_id_c = _yaml_conf["user_id_c"]
    user_account_c = _yaml_conf["user_account_c"]
    user_login_token_c = _yaml_conf["user_login_token_c"]

    ka_info_us = _yaml_conf["us_ka_info"]
    ka_info_eu = _yaml_conf["eu_ka_info"]
    ka_info_other = _yaml_conf["other_ka_info"]

    km_info_us = _yaml_conf["us_km_info"]
    km_info_eu = _yaml_conf["eu_km_info"]
    km_info_other = _yaml_conf["other_km_info"]

    is_check_db = _yaml_conf["is_check_db"]
    sql_cfg = _yaml_conf["sql_cfg"]
    redis_cfg = _yaml_conf["redis_cfg"]


class RoxeUserCenterApiTest(unittest.TestCase):
    mysql = None
    redis = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = RoxeUserCenterApiClient(RoxeUserCenterData.host, RoxeUserCenterData.user_id, RoxeUserCenterData.user_login_token)

        if RoxeUserCenterData.is_check_db:
            cls.mysql = Mysql(RoxeUserCenterData.sql_cfg["mysql_host"], RoxeUserCenterData.sql_cfg["port"], RoxeUserCenterData.sql_cfg["user"], RoxeUserCenterData.sql_cfg["password"], RoxeUserCenterData.sql_cfg["db"], True)
            cls.mysql.connect_database()

            cls.redis = RedisClient(RoxeUserCenterData.redis_cfg["host"], RoxeUserCenterData.redis_cfg["password"], RoxeUserCenterData.redis_cfg["db"], RoxeUserCenterData.redis_cfg["port"])

    @classmethod
    def tearDownClass(cls) -> None:
        if RoxeUserCenterData.is_check_db:
            cls.mysql.disconnect_database()
            cls.redis.closeClient()

    def setUp(self) -> None:
        # 清除kyc信息
        sql = f"select * from roxe_kyc.user_kyc where user_id='{RoxeUserCenterData.user_id_c}'"
        kyc_db = self.mysql.exec_sql_query(sql)
        if kyc_db:
            self.client.logger.info("准备清理数据库中kyc数据")
            del_sql = f"delete from roxe_kyc.user_kyc where user_id='{RoxeUserCenterData.user_id_c}'"
            self.mysql.exec_sql_query(del_sql)
        # 清除异常用户信息

    def checkCodeMessage(self, api_result, code="0", message="SUCCESS"):
        self.assertEqual(api_result["code"], code, "code检查不正确")
        self.assertEqual(api_result["message"], message, "message检查不正确")

    def checkUserInfoFromDB(self, user_info, user_id):
        self.assertEqual(user_info["userId"], int(user_id))
        if RoxeUserCenterData.is_check_db:
            sql = f"select * from user_info where user_id='{user_id}'"
            db_info = self.mysql.exec_sql_query(sql)
            self.client.logger.info(f"数据库中用户信息: {db_info}")
            self.assertEqual(user_info["roxeId"], db_info[0]["userRoxeId"])
            self.assertEqual(user_info["nickName"], db_info[0]["userName"])
            parse_expand = json.loads(db_info[0]["userExpand"])
            self.assertEqual(user_info["firstName"], parse_expand["firstName"])
            self.assertEqual(user_info["lastName"], parse_expand["lastName"])
            self.assertEqual(user_info["headImage"], parse_expand["headImage"])
            self.assertEqual(user_info["phone"], db_info[0]["userPhone"])
            self.assertEqual(user_info["itc"], db_info[0]["userItc"])
            self.assertEqual(user_info["userState"], db_info[0]["userState"])
            self.assertEqual(user_info["country"], None)
            self.assertEqual(user_info["area"], None)

    def test_001_getUserInfo(self):
        """
        获取用户信息
        """
        user_info = self.client.getUserInfo()
        self.checkCodeMessage(user_info)
        self.checkUserInfoFromDB(user_info["data"], RoxeUserCenterData.user_id)

    def test_002_getUserInfo_kmFailedThreeTime(self):
        """
        获取用户信息
        """
        user_info = self.client.getUserInfo(token=RoxeUserCenterData.user_login_token_c)
        self.checkCodeMessage(user_info)
        self.checkUserInfoFromDB(user_info["data"], RoxeUserCenterData.user_id_c)

        kyc_client = RoxeKycApiClient(RoxeKycData.host, RoxeKycData.user_id_c, RoxeKycData.user_login_token_c)
        # 提交kyc
        kyc_client.submitIdentify("KA", RoxeKycData.ka_info_us)
        for i in range(3):
            kyc_client.submitIdentify("KM", RoxeKycData.km_info_us)
            # 更新km状态
            kyc_client.updateKycState(RoxeKycData.user_id_c, "KM", "FAIL")
            user_info = self.client.getUserInfo(token=RoxeUserCenterData.user_login_token_c)
            if i < 2:
                self.checkCodeMessage(user_info)
                self.checkUserInfoFromDB(user_info["data"], RoxeUserCenterData.user_id_c)
            else:
                self.checkCodeMessage(user_info, "RMS10104", "User Suspend!")
                self.assertIsNone(user_info["data"])

        kyc_client.resetSuspendUserState(RoxeUserCenterData.user_id_c)
        user_info = self.client.getUserInfo(RoxeUserCenterData.user_login_token_c)
        self.checkCodeMessage(user_info)
        self.assertEqual(user_info["data"]["userState"], "NORMAL")
        self.checkUserInfoFromDB(user_info["data"], RoxeUserCenterData.user_id_c)
