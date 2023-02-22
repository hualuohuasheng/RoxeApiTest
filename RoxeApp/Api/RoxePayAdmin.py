# -*- coding: utf-8 -*-
# author: liminglei
# date: 2021-06-21

import sys
import requests
import jwt
import json
import time


class AdminApi:

    def __init__(self, url, secretKey):
        self.baseUrl = url
        self.secretKey = secretKey

    def getSignature(self, methodName, methodParams):
        params_json_string = json.dumps(methodParams)
        millis = int(time.time()) + 300
        signature = jwt.encode({
            'method': methodName,
            "params": params_json_string,
            'exp': millis,
        }, self.secretKey, algorithm='HS256')
        return signature.decode("utf-8")

    def updateOrderToPaymentReceived(self, orderId):
        sig = self.getSignature("order.paymentReceived", {"orderId": orderId})
        res = requests.post(self.baseUrl + sig, data=json.dumps({"orderId": orderId}))
        print(res.json())

    def updateOrderToTransferCompleted(self, orderId):
        sig = self.getSignature("order.transferCompleted", {"orderId": orderId})
        res = requests.post(self.baseUrl + sig, data=json.dumps({"orderId": orderId}))
        print(res.json())

    def updateOrderToCancel(self, orderId):
        sig = self.getSignature("order.cancel", {"orderId": orderId})
        res = requests.post(self.baseUrl + sig, data=json.dumps({"orderId": orderId}))
        print(res.json())


def printHelp():
    print("python3 RoxePayAdmin.py <orderId> <orderStatus>")
    print("eg:")
    print("  python3 RoxePayAdmin.py 2162858274767537 1 -- 订单修改为已收款: paymentReceived")
    print("  python3 RoxePayAdmin.py 2162858274767537 2 -- 订单修改为已完成: transferCompleted")
    print("  python3 RoxePayAdmin.py 2162858274767537 3 -- 订单修改为撤销: cancel")


if __name__ == "__main__":

    order, status = None, None
    try:
        order = sys.argv[1]
        status = sys.argv[2]
    except Exception:
        printHelp()
        sys.exit()

    adminUrl = "http://xxxx/roxe-send/admin?signature="
    adminKey = "xxxx"
    adminClient = AdminApi(adminUrl, adminKey)
    order = "2163194794562899"
    status = "2"
    if status == "1":
        adminClient.updateOrderToPaymentReceived(order)
    elif status == "2":
        adminClient.updateOrderToTransferCompleted(order)
    elif status == "3":
        adminClient.updateOrderToCancel(order)
    else:
        printHelp()
