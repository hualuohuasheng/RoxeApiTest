# coding=utf-8
# author: Li MingLei
# date: 2021-08-26
"""
本模块是发送HTTP请求的基础模块，所有调用Http请求的函数最终统一该模块提供的方法
"""
import requests
import json


def sendGetRequest(request_url, params=None, headers=None, verify=True):
    """
    发送Get请求
    :param request_url: 请求的url
    :param params: 请求的参数
    :param headers: 请求的header
    :return:
    """
    return requests.get(request_url, params=params, headers=headers, verify=verify)


def sendPostRequest(request_url, body, headers=None, formContactSymbol=None, verify=True):
    """
    发送Post请求
    :param request_url: 请求的url
    :param body: 请求的body数据, 根据Content-Type的不同，需要对body进行重新组装
    :param headers: 请求的header
    :param formContactSymbol: 请求的header
    :param verify
    :return: 返回响应
    """
    # 获取Content-Type类型，默认为<application/json>
    if headers is None:
        headers = {}
    data_type = headers.get("Content-Type") if "Content-Type" in headers else "application/json"
    if data_type == "application/json":
        if isinstance(body, str):
            res = requests.post(request_url, body, headers=headers, verify=verify)
        else:
            res = requests.post(request_url, json=body, headers=headers, verify=verify)
    elif data_type == "multipart/form-data":
        files = []
        for k, v in body.items():
            files.append((k, v))
        res = requests.post(request_url, files=files, headers=headers, verify=verify)
    elif data_type == "application/x-www-form-urlencoded":
        body_data = ""
        formContactSymbol = formContactSymbol if formContactSymbol else ""
        for bk, bv in body.items():
            if isinstance(bv, dict):
                body_data += bk + "=" + json.dumps(bv) + formContactSymbol
            else:
                body_data += bk + "=" + bv + formContactSymbol
        body_data.rstrip(formContactSymbol)
        res = requests.post(request_url, body_data, headers=headers, verify=verify)
    else:
        res = requests.post(request_url, json.dumps(body), headers=headers, verify=verify)
    return res


def sendDeleteRequest(request_url, headers):
    return requests.delete(request_url, headers=headers)
