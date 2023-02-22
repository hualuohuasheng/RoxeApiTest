# coding=utf-8
# author: Li MingLei
# date: 2021-08-16

import os
import sys
import json

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from typing import Optional, Union
from fastapi import FastAPI, Request
# from fastapi.encoders import jsonable_encoder
from fastapi.responses import RedirectResponse
# from pydantic import BaseModel, Field
#from TestPayChannel import tools
#import logging
# import datetime
import uvicorn
import time
import pymysql
from roxe_libs.DBClient import Mysql
#from logging.handlers import RotatingFileHandler



# logger = logging.getLogger("notify")
#
# fileHandler = RotatingFileHandler(filename="notify.log", maxBytes=1024 * 1024 * 200, backupCount=5)
# formatter = logging.Formatter('[%(levelname)s] %(asctime)s: [%(name)s:%(lineno)d]: %(message)s')
# fileHandler.setFormatter(formatter)
# logger.addHandler(fileHandler)
# logger.setLevel(logging.WARNING)
# for h in logger.handlers:
#     h.setLevel(logging.WARNING)
# print(logger.handlers)
# logger = tools.setClientLogger("uvicorn.access", "notify.log", level=logging.INFO)

app = FastAPI()

db_client = Mysql("xxxx", 3306, "xxxx", "xxxx", "mock_notify")


def utilResponse(code=0, message="success", data: Union[str, list, dict, tuple] = ""):
    return {"code": code, "message": message, "data": data}


def insertDB(res_url, res_info, res_header=""):
    in_sql = "insert into mock_notify.res_info (url, response, header) values ('{}', '{}', '{}')".format(res_url, res_info, res_header)
    db_client.connect_database()
    db_client.exec_sql_query(in_sql)
    db_client.disconnect_database()


@app.get('/', include_in_schema=False)
async def index():
    return RedirectResponse("/docs")


@app.get("/api/getNotify", description="查询通知")
async def getNotify(limit_num: str):
    db_client.connect_database()
    db_info = db_client.exec_sql_query("select * from res_info order by create_at desc limit {}".format(limit_num))
    db_client.disconnect_database()
    print("响应数据: {}".format(db_info))
    return utilResponse(data=db_info)


@app.post("/api/rts/receiveNotify",  description="接收通知")
async def rtsNotify(request: Request):
    res_info = await request.json()
    res_url = str(request.url)
    res_headers = json.dumps(request.headers.items())
    # logger.info("接收到url: {}".format(res_url))
    # logger.info("接收到header: {}".format(res_headers))
    # logger.info("接收到的数据: {}".format(res_info))
    insertDB(res_url, json.dumps(res_info), res_headers)
    respData = {"code": "SUCCESS", "message": ""}
    # logger.info("响应数据: {}".format(respData))
    return respData


def decryptResponse(request, req_body):
    from roxe_libs import ApiUtils
    header_sign = [i[1] for i in request.headers.items() if i[0] == "sign"][0]
    header_timestamp = [i[1] for i in request.headers.items() if i[0] == "snddttm"][0]
    msg = header_timestamp + "::" + req_body
    verify_res = ApiUtils.rsa_verify(msg, header_sign, "keys/rmn_rsa_public_key.pem")
    # logger.info(verify_res)
    r_data = json.loads(req_body)["resource"]
    node_secret_key = "xxxx"
    de_data = ApiUtils.aes_decrypt(r_data["ciphertext"], r_data["nonce"], r_data["associatedData"], node_secret_key)
    # logger.info(de_data)
    return de_data

@app.post("/api/rmn/receiveNotify", description="接收RMN消息")
async def rmnNotify(request: Request):
    req_header = request.headers
    req_body = await request.body()
    req_body = req_body.decode("utf-8")
    res_url = str(request.url)
    res_headers = json.dumps(request.headers.items())
    # logger.info("接收到url: {}".format(res_url))
    # logger.info("接收到header: {}".format(req_header))
    # logger.info("接收到的数据: {}".format(req_body))
    if "resource" in req_body and "AES_256_GCM" in req_body:
        de_data = decryptResponse(request, req_body)
    else:
        de_data = req_body
    insertDB(res_url, de_data, res_headers)
    respData = utilResponse(data="update success")
    # logger.info("响应数据: {}".format(respData))
    return respData


@app.post("/api/rmn/receiveNotify/signaturError", description="接收RMN消息, 返回异常信息")
async def signaturError(request: Request):
    req_header = request.headers
    req_body = await request.body()
    req_body = req_body.decode("utf-8")
    res_url = str(request.url)
    res_headers = json.dumps(request.headers.items())
    # logger.info("接收到url: {}".format(res_url))
    # logger.info("接收到header: {}".format(req_header))
    # logger.info("接收到的数据: {}".format(req_body))
    if "resource" in req_body and "AES_256_GCM" in req_body:
        de_data = decryptResponse(request, req_body)
    else:
        de_data = req_body
    insertDB(res_url, de_data, res_headers)
    respData = utilResponse("00200001", "signature error", data=None)
    # logger.info("响应数据: {}".format(respData))
    return respData


@app.post("/api/rmn/receiveNotify/encryptionErrorA", description="接收RMN消息, 返回异常信息")
async def encryptionErrorA(request: Request):
    req_header = request.headers
    req_body = await request.body()
    req_body = req_body.decode("utf-8")
    res_url = str(request.url)
    res_headers = json.dumps(request.headers.items())
    # logger.info("接收到url: {}".format(res_url))
    # logger.info("接收到header: {}".format(req_header))
    # logger.info("接收到的数据: {}".format(req_body))
    if "resource" in req_body and "AES_256_GCM" in req_body:
        de_data = decryptResponse(request, req_body)
    else:
        de_data = req_body
    insertDB(res_url, de_data, res_headers)
    respData = utilResponse("00200002", "encryption error A", data=None)
    # logger.info("响应数据: {}".format(respData))
    return respData


@app.post("/api/rmn/receiveNotify/encryptionErrorB", description="接收RMN消息, 返回异常信息")
async def encryptionErrorB(request: Request):
    req_header = request.headers
    req_body = await request.body()
    req_body = req_body.decode("utf-8")
    res_url = str(request.url)
    res_headers = json.dumps(request.headers.items())
    # logger.info("接收到url: {}".format(res_url))
    # logger.info("接收到header: {}".format(req_header))
    # logger.info("接收到的数据: {}".format(req_body))
    if "resource" in req_body and "AES_256_GCM" in req_body:
        de_data = decryptResponse(request, req_body)
    else:
        de_data = req_body
    insertDB(res_url, de_data, res_headers)
    respData = utilResponse("00100108", "encryption error B", data=None)
    # logger.info("响应数据: {}".format(respData))
    return respData


@app.post("/api/rmn/receiveNotify/businessError", description="接收RMN消息, 返回异常信息")
async def businessError(request: Request):
    req_header = request.headers
    req_body = await request.body()
    req_body = req_body.decode("utf-8")
    res_url = str(request.url)
    res_headers = json.dumps(request.headers.items())
    # logger.info("接收到url: {}".format(res_url))
    # logger.info("接收到header: {}".format(req_header))
    # logger.info("接收到的数据: {}".format(req_body))
    if "resource" in req_body and "AES_256_GCM" in req_body:
        de_data = decryptResponse(request, req_body)
    else:
        de_data = req_body
    insertDB(res_url, de_data, res_headers)
    respData = utilResponse("00100103", "business error", data=None)
    # logger.info("响应数据: {}".format(respData))
    return respData


@app.post("/api/rmn/receiveNotify/validationError", description="接收RMN消息, 返回异常信息")
async def validationError(request: Request):
    req_header = request.headers
    req_body = await request.body()
    req_body = req_body.decode("utf-8")
    res_url = str(request.url)
    res_headers = json.dumps(request.headers.items())
    # logger.info("接收到url: {}".format(res_url))
    # logger.info("接收到header: {}".format(req_header))
    # logger.info("接收到的数据: {}".format(req_body))
    if "resource" in req_body and "AES_256_GCM" in req_body:
        de_data = decryptResponse(request, req_body)
    else:
        de_data = req_body
    insertDB(res_url, de_data, res_headers)
    respData = utilResponse("00100000", "validation error", data=None)
    # logger.info("响应数据: {}".format(respData))
    return respData


if __name__ == "__main__":
    uvicorn.run("mockNotify_uat:app", host="0.0.0.0", port=8006)
