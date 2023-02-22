# coding=utf-8
# author: Li MingLei
# date: 2021-10-13
"""
Roxe App中KYC的相关api实现
"""
import logging
from roxe_libs.Global import Global
from roxe_libs.baseApi import *
from roxe_libs import settings
from roxe_libs.ContractChainTool import RoxeChainClient


class RoxeKycApiClient:

    def __init__(self, host, user_id, user_login_token):
        self.host = host
        self.user_id = user_id
        self.user_login_token = user_login_token
        self.logger = logging.getLogger(Global.getValue(settings.logger_name))

        traceable = Global.getValue(settings.enable_trace)
        if traceable:
            for handle in self.logger.handlers:
                handle.setLevel(logging.DEBUG)

    def getIdentifyFormConstraints(self, token=None, pop_header=None):
        """
        已废弃
        """
        token = token if token else self.user_login_token
        headers = {"token": token}
        if pop_header:
            headers.pop(pop_header)
        self.logger.info("查询认证表单约束信息")
        res = sendGetRequest(self.host + "/roxe-app/web/identify-form-constraints", headers=headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def submitIdentify(self, identifyLevel, extendInfo=None, identifySource="USER_CENTER", token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        body = {"identifyLevel": identifyLevel, "identifySource": identifySource}
        if extendInfo:
            for k, v in extendInfo.items():
                body[k] = v
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            body.pop(pop_param)
        self.logger.info("提交认证信息")
        res = sendPostRequest(self.host + "/roxe-app/web/identify-submit", body, headers=headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {body}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json(), body

    def getIdentifyResult(self, identifyLevel, identifySource="USER_CENTER", editable=0, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        params = {"identifySource": identifySource, "identifyLevel": identifyLevel, "editable": editable}
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            params.pop(pop_param)
        self.logger.info("查询认证状态")
        res = sendGetRequest(self.host + "/roxe-app/web/identify-result", params, headers=headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {params}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def cacheKMInfo(self, info, token=None, pop_header=None, pop_param=None):
        token = token if token else self.user_login_token
        headers = {"token": token, "Content-Type": "application/x-www-form-urlencoded"}
        body = {"info": info}
        if pop_header:
            headers.pop(pop_header)
        if pop_param:
            body.pop(pop_param)
        self.logger.info("缓存KM信息")
        res = sendPostRequest(self.host + "/roxe-app/web/cache-km-info", body, headers=headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {body}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def getCachedKMInfo(self, token=None, pop_header=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        if pop_header:
            headers.pop(pop_header)
        self.logger.info("获取缓存的KM信息")
        res = sendGetRequest(self.host + "/roxe-app/web/get-cached-km-info", headers=headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def addUSRestrictedStateUser(self, token=None, pop_header=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        if pop_header:
            headers.pop(pop_header)
        self.logger.info("记录当前用户到申请KYC的美国限制州用户列表中")
        res = sendPostRequest(self.host + "/roxe-app/web/add-us-restricted-state-user", None, headers=headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def getUSRestrictedState(self, token=None, pop_header=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        if pop_header:
            headers.pop(pop_header)
        self.logger.info("查询美国限制州")
        res = sendGetRequest(self.host + "/roxe-app/web/get-us-restricted-states", headers=headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def getKycLevel(self, token=None, pop_header=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        if pop_header:
            headers.pop(pop_header)
        self.logger.info("查询当前用户的 KYC 等级")
        res = sendGetRequest(self.host + "/roxe-app/web/get-kyc-level", headers=headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def updateKycState(self, user_id, kyc_level, kyc_state):
        headers = {"qaKey": "xxxx", "Content-Type": "application/x-www-form-urlencoded"}
        body = {"userId": user_id, "identifyLevel": kyc_level, "identifyState": kyc_state}
        self.logger.info("更新用的kyc状态")
        res = sendPostRequest(self.host + "/roxe-kyc/inner/qa/qa/update-identify-state", body, headers=headers, formContactSymbol="&")
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {res.request.body}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def resetSuspendUserState(self, user_id):
        headers = {"qaKey": "xxxx", "Content-Type": "application/x-www-form-urlencoded"}
        body = {"userId": user_id}
        self.logger.info("恢复用户suspend状态到normal")
        res = sendPostRequest(self.host + "/roxe-kyc/inner/api/reset-kyc-level", body, headers=headers, formContactSymbol="&")
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {res.request.body}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()
