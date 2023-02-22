# coding=utf-8
# author: Li MingLei
# date: 2021-10-15
"""
Roxe App中用户系统的相关api实现
"""
import logging
from roxe_libs.Global import Global
from roxe_libs.baseApi import *
from roxe_libs import settings, ApiUtils
import json


class RoxeUserCenterApiClient:

    def __init__(self, host, user_id, user_login_token):
        self.host = host
        self.user_id = user_id
        self.user_login_token = user_login_token
        self.logger = logging.getLogger(Global.getValue(settings.logger_name))

        traceable = Global.getValue(settings.enable_trace)
        if traceable:
            for handle in self.logger.handlers:
                handle.setLevel(logging.DEBUG)

    def getUserInfo(self, token=None, pop_header=None):
        token = token if token else self.user_login_token
        headers = {"token": token}
        if pop_header:
            headers.pop(pop_header)
        self.logger.info("查询用户信息")
        res = sendGetRequest(self.host + "/roxe-app/api/user/get-user-info", headers=headers)
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
