# coding=utf-8
# author: Li MingLei
# date: 2021-09-26
"""
RoxeSend系统【RoxeApp的后台服务】Api的测试用例
"""
import unittest
import json
import os
import time
from .RoxeKycApi import RoxeKycApiClient
from roxe_libs import settings, ApiUtils
from roxe_libs.Global import Global
from roxe_libs.DBClient import RedisClient, Mysql
from roxe_libs.pub_function import loadYmlFile


class RoxeKycData:

    env = Global.getValue(settings.environment)
    cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), f"./RoxeKyc_{env}.yml"))
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


class RoxeKycApiTest(unittest.TestCase):
    mysql = None
    redis = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = RoxeKycApiClient(RoxeKycData.host, RoxeKycData.user_id, RoxeKycData.user_login_token)

        if RoxeKycData.is_check_db:
            cls.mysql = Mysql(RoxeKycData.sql_cfg["mysql_host"], RoxeKycData.sql_cfg["port"], RoxeKycData.sql_cfg["user"], RoxeKycData.sql_cfg["password"], RoxeKycData.sql_cfg["db"], True)
            cls.mysql.connect_database()

            cls.redis = RedisClient(RoxeKycData.redis_cfg["host"], RoxeKycData.redis_cfg["password"], RoxeKycData.redis_cfg["db"], RoxeKycData.redis_cfg["port"])

    @classmethod
    def tearDownClass(cls) -> None:
        if RoxeKycData.is_check_db:
            cls.mysql.disconnect_database()
            cls.redis.closeClient()

    def setUp(self) -> None:
        sql = f"select * from user_kyc where user_id='{RoxeKycData.user_id_c}'"
        kyc_db = self.mysql.exec_sql_query(sql)
        if kyc_db:
            self.client.logger.info("准备清理数据库中kyc数据")
            del_sql = f"delete from user_kyc where user_id='{RoxeKycData.user_id_c}'"
            self.mysql.exec_sql_query(del_sql)

    def tearDown(self) -> None:
        sql = f"select * from user_kyc where user_id='{RoxeKycData.user_id_c}'"
        kyc_db = self.mysql.exec_sql_query(sql)
        if kyc_db:
            self.client.logger.info("准备清理数据库中kyc数据")
            del_sql = f"delete from user_kyc where user_id='{RoxeKycData.user_id_c}'"
            self.mysql.exec_sql_query(del_sql)

    def checkCodeMessage(self, api_result, code="0", message="Success"):
        self.assertEqual(api_result["code"], code, "code检查不正确")
        self.assertEqual(api_result["message"], message, "message检查不正确")

    def checkIdentifyResult(self, kyc_result, user_id, kyc_level, r_body=None, showSSN=False):
        self.assertEqual(kyc_result["userId"], user_id)
        self.assertEqual(kyc_result["identifyLevel"], kyc_level)
        if r_body:
            for kyc_k, kyc_v in kyc_result["identify"].items():
                if kyc_k in ["ip", "phone"]:
                    continue
                elif kyc_k not in r_body:
                    self.assertIsNone(kyc_v, f"{kyc_k}校验失败")
                else:
                    if kyc_k == "ssn" and not showSSN:
                        self.assertEqual(kyc_v, f"xxx-xx-{r_body[kyc_k][-4:]}", f"kyc信息中{kyc_k}校验失败")
                    else:
                        self.assertEqual(kyc_v, r_body[kyc_k], f"kyc信息中{kyc_k}校验失败")
        if RoxeKycData.is_check_db:
            kyc_sql = f"select * from user_kyc where user_id='{user_id}' and kyc_level='{kyc_level}'"
            kyc_db = self.mysql.exec_sql_query(kyc_sql)
            if kyc_db:
                kyc_data = json.loads(kyc_db[0]["kycData"])
                for k, v in kyc_result["identify"].items():
                    if k not in kyc_data:
                        self.assertIsNone(v, f"未在数据库中找到{k}: {v}")
                        continue
                    if k == "ssn" and not showSSN:
                        self.assertEqual(v, f"xxx-xx-{kyc_data[k][-4:]}", f"kyc信息中{k}和数据库不一致")
                    else:
                        self.assertEqual(v, kyc_data[k], f"kyc信息中{k}和数据库不一致")
            else:
                self.assertEqual(kyc_result["result"], "NONE")
                self.assertIsNone(kyc_result["reviewerMemo"])
                self.assertIsNone(kyc_result["identify"])

    def test_001_submitIdentify_US_KA(self):
        """
        提交认证信息, 未经过kyc的用户，美国，提交kA认证
        """
        ka_info_us = RoxeKycData.ka_info_us
        identify_submit, r_body = self.client.submitIdentify("KA", ka_info_us, token=RoxeKycData.user_login_token_c)
        self.checkCodeMessage(identify_submit)
        self.assertTrue(identify_submit["data"])

        kyc_result = self.client.getIdentifyResult("KA", token=RoxeKycData.user_login_token_c)
        self.checkCodeMessage(kyc_result)
        self.checkIdentifyResult(kyc_result["data"], RoxeKycData.user_id_c, "KA", r_body)

    def test_002_submitIdentify_EU_KA(self):
        """
        提交认证信息, 未经过kyc的用户，欧盟，提交kA认证
        """
        ka_info_eu = RoxeKycData.ka_info_eu
        identify_submit, r_body = self.client.submitIdentify("KA", ka_info_eu, token=RoxeKycData.user_login_token_c)
        self.checkCodeMessage(identify_submit)
        self.assertTrue(identify_submit["data"])

        kyc_result = self.client.getIdentifyResult("KA", token=RoxeKycData.user_login_token_c)
        self.checkCodeMessage(kyc_result)
        self.checkIdentifyResult(kyc_result["data"], RoxeKycData.user_id_c, "KA", r_body)

    def test_003_submitIdentify_OTHER_KA(self):
        """
        提交认证信息, 未经过kyc的用户，非美国、欧盟国家，提交kA认证
        """
        ka_info_other = RoxeKycData.ka_info_other
        identify_submit, r_body = self.client.submitIdentify("KA", ka_info_other, token=RoxeKycData.user_login_token_c)
        self.checkCodeMessage(identify_submit)
        self.assertTrue(identify_submit["data"])

        kyc_result = self.client.getIdentifyResult("KA", token=RoxeKycData.user_login_token_c)
        self.checkCodeMessage(kyc_result)
        self.checkIdentifyResult(kyc_result["data"], RoxeKycData.user_id_c, "KA", r_body)

    def test_004_submitIdentify_US_KM(self):
        """
        提交认证信息, 未经过kyc的用户，美国，提交ka后, 提交kM认证
        """
        ka_info_us = RoxeKycData.ka_info_us
        identify_submit, r_body = self.client.submitIdentify("KA", ka_info_us, token=RoxeKycData.user_login_token_c)
        self.checkCodeMessage(identify_submit)
        self.assertTrue(identify_submit["data"])

        kyc_result = self.client.getIdentifyResult("KA", token=RoxeKycData.user_login_token_c)
        self.checkCodeMessage(kyc_result)
        self.checkIdentifyResult(kyc_result["data"], RoxeKycData.user_id_c, "KA", r_body)

        time.sleep(1)

        km_info_us = RoxeKycData.km_info_us
        identify_submit, r_body = self.client.submitIdentify("KM", km_info_us, token=RoxeKycData.user_login_token_c)
        self.checkCodeMessage(identify_submit)
        self.assertTrue(identify_submit["data"])

        kyc_result = self.client.getIdentifyResult("KM", token=RoxeKycData.user_login_token_c)
        self.checkCodeMessage(kyc_result)
        self.checkIdentifyResult(kyc_result["data"], RoxeKycData.user_id_c, "KM", r_body)
        self.assertEqual(kyc_result["data"]["result"], "SUBMIT")

    def test_005_submitIdentify_EU_KM(self):
        """
        提交认证信息, 未经过kyc的用户，欧盟，提交ka后，提交kM认证
        """
        ka_info_eu = RoxeKycData.ka_info_eu
        identify_submit, r_body = self.client.submitIdentify("KA", ka_info_eu, token=RoxeKycData.user_login_token_c)
        self.checkCodeMessage(identify_submit)
        self.assertTrue(identify_submit["data"])

        kyc_result = self.client.getIdentifyResult("KA", token=RoxeKycData.user_login_token_c)
        self.checkCodeMessage(kyc_result)
        self.checkIdentifyResult(kyc_result["data"], RoxeKycData.user_id_c, "KA", r_body)

        time.sleep(1)

        km_info_eu = RoxeKycData.km_info_eu
        identify_submit, r_body = self.client.submitIdentify("KM", km_info_eu, token=RoxeKycData.user_login_token_c)
        self.checkCodeMessage(identify_submit)
        self.assertTrue(identify_submit["data"])

        kyc_result = self.client.getIdentifyResult("KM", token=RoxeKycData.user_login_token_c)
        self.checkCodeMessage(kyc_result)
        self.checkIdentifyResult(kyc_result["data"], RoxeKycData.user_id_c, "KM", r_body)
        self.assertEqual(kyc_result["data"]["result"], "SUBMIT")

    def test_006_submitIdentify_OTHER_KM(self):
        """
        提交认证信息, 未经过kyc的用户，非美国和欧盟的国家，提交ka后，提交kM认证
        """
        ka_info_other = RoxeKycData.ka_info_other
        identify_submit, r_body = self.client.submitIdentify("KA", ka_info_other, token=RoxeKycData.user_login_token_c)
        self.checkCodeMessage(identify_submit)
        self.assertTrue(identify_submit["data"])

        kyc_result = self.client.getIdentifyResult("KA", token=RoxeKycData.user_login_token_c)
        self.checkCodeMessage(kyc_result)
        self.checkIdentifyResult(kyc_result["data"], RoxeKycData.user_id_c, "KA", r_body)

        time.sleep(1)

        km_info_other = RoxeKycData.km_info_other
        identify_submit, r_body = self.client.submitIdentify("KM", km_info_other, token=RoxeKycData.user_login_token_c)
        self.checkCodeMessage(identify_submit)
        self.assertTrue(identify_submit["data"])

        kyc_result = self.client.getIdentifyResult("KM", token=RoxeKycData.user_login_token_c)
        self.checkCodeMessage(kyc_result)
        self.checkIdentifyResult(kyc_result["data"], RoxeKycData.user_id_c, "KM", r_body)
        self.assertEqual(kyc_result["data"]["result"], "SUBMIT")

    def test_007_cacheKMInfo_notKyc_US_KM(self):
        """
        缓存KM信息, 未经过kyc的用户，美国
        """
        km_info_us = RoxeKycData.km_info_us
        cache_result = self.client.cacheKMInfo(km_info_us, token=RoxeKycData.user_login_token_c)
        self.checkCodeMessage(cache_result)
        self.assertTrue(cache_result["data"])

        km_cache = self.client.getCachedKMInfo(RoxeKycData.user_login_token_c)
        self.checkCodeMessage(km_cache)
        self.assertEqual(km_cache["data"], json.dumps(km_info_us))

        # 提交kyc
        self.client.submitIdentify("KA", RoxeKycData.ka_info_us, token=RoxeKycData.user_login_token_c)
        self.client.submitIdentify("KM", km_info_us, token=RoxeKycData.user_login_token_c)
        # 提交后km的缓存应该消失
        km_cache = self.client.getCachedKMInfo(RoxeKycData.user_login_token_c)
        self.checkCodeMessage(km_cache)
        self.assertIsNone(km_cache["data"], "提交认证后km的缓存应该消失")

    def test_008_getKycLevel_notKyc(self):
        """
        查询用户的kyc等级, 未经过kyc的用户
        """
        kyc_level = self.client.getKycLevel(RoxeKycData.user_login_token_c)
        self.checkCodeMessage(kyc_level)
        self.assertEqual(kyc_level["data"], "L1")

    def test_009_getKycLevel_passKaKyc(self):
        """
        查询用户的kyc等级, 经过ka kyc的用户
        """
        kyc_level = self.client.getKycLevel(RoxeKycData.user_login_token_b)
        self.checkCodeMessage(kyc_level)
        self.assertEqual(kyc_level["data"], "L2")

    def test_010_getKycLevel_submitKmKyc(self):
        """
        查询用户的kyc等级, 进行km认证的用户，但是km未通过时
        """
        # 提交kyc
        self.client.submitIdentify("KA", RoxeKycData.ka_info_us, token=RoxeKycData.user_login_token_c)
        self.client.submitIdentify("KM", RoxeKycData.km_info_us, token=RoxeKycData.user_login_token_c)
        kyc_level = self.client.getKycLevel(token=RoxeKycData.user_login_token_c)
        self.checkCodeMessage(kyc_level)
        self.assertEqual(kyc_level["data"], "L2")

    def test_011_getKycLevel_kmKycFailed(self):
        """
        查询用户的kyc等级, km失败的用户
        """
        # 提交kyc
        self.client.submitIdentify("KA", RoxeKycData.ka_info_us, token=RoxeKycData.user_login_token_c)
        self.client.submitIdentify("KM", RoxeKycData.km_info_us, token=RoxeKycData.user_login_token_c)
        # 更新km状态
        self.client.updateKycState(RoxeKycData.user_id_c, "KM", "FAIL")
        # sql = f"# update user_kyc set check_state='FAIL' where user_id='{RoxeKycData.user_id_c}' and kyc_level='KM'"
        # self.mysql.exec_sql_query(sql)
        # 查询kyc level
        kyc_level = self.client.getKycLevel(token=RoxeKycData.user_login_token_c)
        self.checkCodeMessage(kyc_level)
        self.assertEqual(kyc_level["data"], "L2")

    def test_012_getKycLevel_passKmKyc(self):
        """
        查询用户的kyc等级, 经过km kyc的用户
        """
        kyc_level = self.client.getKycLevel()
        self.checkCodeMessage(kyc_level)
        self.assertEqual(kyc_level["data"], "L3")

    def test_013_getUSRestrictedStates(self):
        """
        查询美国的限制州
        """
        states = self.client.getUSRestrictedState()
        self.checkCodeMessage(states)
        expect_states = [
            {"abbr": "AL", "name": "Alabama", "restricted": True}, {"abbr": "AZ", "name": "Arizona", "restricted": True}, {"abbr": "AR", "name": "Arkansas", "restricted": True},
            {"abbr": "CA", "name": "California", "restricted": True}, {"abbr": "DE", "name": "Delaware", "restricted": True}, {"abbr": "FL", "name": "Florida", "restricted": True},
            {"abbr": "GA", "name": "Georgia", "restricted": True}, {"abbr": "ID", "name": "Idaho", "restricted": True}, {"abbr": "IL", "name": "Illinois", "restricted": True},
            {"abbr": "IN", "name": "Indiana", "restricted": True}, {"abbr": "KS", "name": "Kansas", "restricted": True}, {"abbr": "LA", "name": "Louisiana", "restricted": True},
            {"abbr": "MA", "name": "Massachusetts", "restricted": True}, {"abbr": "ME", "name": "Maine", "restricted": True}, {"abbr": "MD", "name": "Maryland", "restricted": True},
            {"abbr": "MN", "name": "Minnesota", "restricted": True}, {"abbr": "MO", "name": "Missouri", "restricted": True}, {"abbr": "MS", "name": "Mississippi", "restricted": True},
            {"abbr": "MT", "name": "Montana", "restricted": False},
            {"abbr": "NE", "name": "Nebraska", "restricted": True}, {"abbr": "NC", "name": "North Carolina", "restricted": True}, {"abbr": "ND", "name": "North Dakota", "restricted": True},
            {"abbr": "NH", "name": "New Hampshire", "restricted": True}, {"abbr": "NJ", "name": "New Jersey", "restricted": True}, {"abbr": "NV", "name": "Nevada", "restricted": True},
            {"abbr": "OK", "name": "Oklahoma", "restricted": True}, {"abbr": "OR", "name": "Oregon", "restricted": True}, {"abbr": "RI", "name": "Rhode Island", "restricted": True},
            {"abbr": "SC", "name": "South Carolina", "restricted": True}, {"abbr": "SD", "name": "South Dakota", "restricted": True}, {"abbr": "TN", "name": "Tennessee", "restricted": True},
            {"abbr": "TX", "name": "Texas", "restricted": True}, {"abbr": "UT", "name": "Utah", "restricted": True}, {"abbr": "VA", "name": "Virginia", "restricted": True},
            {"abbr": "VT", "name": "Vermont", "restricted": True}, {"abbr": "WA", "name": "Washington", "restricted": True}, {"abbr": "WI", "name": "Wisconsin", "restricted": True},
            {"abbr": "WV", "name": "West Virginia", "restricted": True}, {"abbr": "WY", "name": "Wyoming", "restricted": True}, {"abbr": "AK", "name": "Alaska", "restricted": True},
            {"abbr": "CO", "name": "Colorado", "restricted": True}, {"abbr": "CT", "name": "Connecticut", "restricted": True}, {"abbr": "HI", "name": "Hawaii", "restricted": True},
            {"abbr": "IA", "name": "Iowa", "restricted": True}, {"abbr": "KY", "name": "Kentucky", "restricted": True}, {"abbr": "MI", "name": "Michigan", "restricted": True},
            {"abbr": "NM", "name": "New Mexico", "restricted": True}, {"abbr": "NY", "name": "New York", "restricted": True}, {"abbr": "OH", "name": "Ohio", "restricted": True},
            {"abbr": "PA", "name": "Pennsylvania", "restricted": True}
        ]
        self.assertEqual(states["data"], expect_states)

    def test_014_getIdentifyResult_notKyc(self):
        """
        查询用户的kyc认证状态, 未经过kyc的用户
        """
        kyc_result = self.client.getIdentifyResult("KA", token=RoxeKycData.user_login_token_c)
        self.checkCodeMessage(kyc_result)
        self.checkIdentifyResult(kyc_result["data"], RoxeKycData.user_id_c, "KA")

        kyc_result = self.client.getIdentifyResult("KM", token=RoxeKycData.user_login_token_c)
        self.checkCodeMessage(kyc_result)
        self.checkIdentifyResult(kyc_result["data"], RoxeKycData.user_id_c, "KM")

    def test_015_getIdentifyResult_passKaKyc(self):
        """
        查询用户的kyc认证状态, 经过ka kyc的用户
        """
        kyc_result = self.client.getIdentifyResult("KA", token=RoxeKycData.user_login_token_b)
        self.checkCodeMessage(kyc_result)
        self.checkIdentifyResult(kyc_result["data"], RoxeKycData.user_id_b, "KA")

        kyc_result = self.client.getIdentifyResult("KM", token=RoxeKycData.user_login_token_b)
        self.checkCodeMessage(kyc_result)
        self.checkIdentifyResult(kyc_result["data"], RoxeKycData.user_id_b, "KM")

    def test_016_getIdentifyResult_passKmKyc(self):
        """
        查询用户的kyc认证状态, 经过km kyc的用户
        """
        kyc_result = self.client.getIdentifyResult("KA")
        self.checkCodeMessage(kyc_result)
        self.checkIdentifyResult(kyc_result["data"], RoxeKycData.user_id, "KA")

        kyc_result = self.client.getIdentifyResult("KM")
        self.checkCodeMessage(kyc_result)
        self.checkIdentifyResult(kyc_result["data"], RoxeKycData.user_id, "KM")

    def test_017_getKycLevel_kmKycFailedThreeTime(self):
        """
        查询用户的kyc等级, km失败达到3次的用户, 用户状态为suspend且kyc level变为L1
        """
        # 提交kyc
        self.client.submitIdentify("KA", RoxeKycData.ka_info_us, token=RoxeKycData.user_login_token_c)
        try:
            for i in range(3):
                self.client.submitIdentify("KM", RoxeKycData.km_info_us, token=RoxeKycData.user_login_token_c)
                # 更新km状态
                self.client.updateKycState(RoxeKycData.user_id_c, "KM", "FAIL")
                kyc_level = self.client.getKycLevel(token=RoxeKycData.user_login_token_c)
                if i < 2:
                    self.checkCodeMessage(kyc_level)
                    self.assertEqual(kyc_level["data"], "L2")
                else:
                    self.checkCodeMessage(kyc_level, "RMS10104", "User Suspend!")
        except Exception:
            assert False, "用例执行失败"
        finally:
            self.client.resetSuspendUserState(RoxeKycData.user_id_c)
        # 查询kyc level
        kyc_level = self.client.getKycLevel(token=RoxeKycData.user_login_token_c)
        self.checkCodeMessage(kyc_level)
        self.assertEqual(kyc_level["data"], "L1")
