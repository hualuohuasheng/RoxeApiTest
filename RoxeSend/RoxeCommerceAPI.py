# coding=utf-8
# author: Li MingLei
# date: 2021-11-09
"""
商户系统的API
"""
import logging
from roxe_libs.Global import Global
from roxe_libs.baseApi import *
from roxe_libs import settings


class CommerceApiClient:

    def __init__(self, host, token):
        self.host = host
        self.token = token
        self.logger = logging.getLogger(Global.getValue(settings.logger_name))

        traceable = Global.getValue(settings.enable_trace)
        if traceable:
            for handle in self.logger.handlers:
                handle.setLevel(logging.DEBUG)

    def getBranchQrCodeInfo(self, branchId):
        headers = {"token": self.token}
        params = {"branchId": branchId}
        self.logger.info("获取门店二维码信息")
        res = sendGetRequest(self.host + "/roxe-commerce/pc/branch/getBranchQrCodeInfo", params, headers=headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.debug(f"请求参数: {params}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()

    def getMerchantCertifyInfo(self):
        headers = {"token": self.token}
        # params = {"branchId": branchId}
        self.logger.info("获取商户创建及审核信息")
        res = sendGetRequest(self.host + "/roxe-commerce/pc/branch/getBranchQrCodeInfo", headers=headers)
        self.logger.debug(f"请求url: {res.url}")
        self.logger.debug(f"请求header: {headers}")
        self.logger.info(f"请求结果: {res.text}")
        return res.json()
