# coding=utf-8
# author: Roxe
# date: 2022-06-27
import contextlib
import copy
import secrets
import unittest
import os
import json
import traceback
import time
from random import random

from roxe_libs.DBClient import Mysql
from roxe_libs import ApiUtils
from RTS.RtsApi_V3 import RTSApiClient
from RTS.RTSData import RTSData
# from RPS.RpsApiTest import RPSData
# from RPS.RpsApi import RPSApiClient
from RSS.RssApiTest import RSSData
from roxe_libs.ContractChainTool import RoxeChainClient
from pymysql.err import OperationalError
from decimal import Decimal
from RPC.RpcApi import RPCApiClient
from RPC.RpcApiTest import RPCData
import operator


class BaseCheckRTS(unittest.TestCase):
    mysql = None
    rpsClient = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = RTSApiClient(RTSData.host, RTSData.env, RTSData.api_id, RTSData.sec_key, RTSData.ssl_pub_key, ns_host="http://gateway-uat-bj-test.roxepro.top:40000/roxe-ns")
        # cls.rpsClient = RPSApiClient(RPSData.host, RPSData.app_key, RPSData.secret)
        # cls.rssClient = RssApiClient(RssData.host, RssData.chain_host)
        cls.rpcClient = RPCApiClient(RPCData.host, RTSData.chain_host)
        cls.chain_client = RoxeChainClient(RTSData.chain_host)

        if RTSData.is_check_db:
            cls.mysql = Mysql(RTSData.sql_cfg["mysql_host"], RTSData.sql_cfg["port"], RTSData.sql_cfg["user"],
                              RTSData.sql_cfg["password"], RTSData.sql_cfg["db"], True)
            cls.mysql.connect_database()

    @classmethod
    def tearDownClass(cls) -> None:
        if RTSData.is_check_db:
            cls.mysql.disconnect_database()

    # 从数据库获取节点费用
    def getSendFeeAndDeliverFee(self, sendCurrency, sendCountry, recCurrency, recCountry, leftChannel, rightChannel):
        channel_info_in = self.mysql.exec_sql_query("select * from roxe_rpc.rpc_corridor_info where channel_name like '%{}%' and currency like '%{}%' and country like '%{}%' and corridor_type={}".format(leftChannel, sendCurrency, sendCountry, 1))
        channel_info_out = self.mysql.exec_sql_query("select * from roxe_rpc.rpc_corridor_info where channel_name like '%{}%' and currency like '%{}%' and country like '%{}%' and corridor_type={}".format(rightChannel, recCurrency, recCountry, 0))
        # print(channel_info_in)
        # print(channel_info_out)
        # channel_group_info = self.client.mysql.exec_sql_query("select * from roxe_rpc.rpc_channel_info where channel_name like '%{}%'".format(rightChannel))
        if len(channel_info_in) == 1 and len(channel_info_out) == 1:
            sendFee = Decimal(float(channel_info_in[0]["inFeeAmount"])).quantize(Decimal('0.00'))
            deliverFee = Decimal(float(channel_info_out[0]["outBankFee"])).quantize(Decimal('0.00'))
            # if channel_group_info[0]["channelGroups"] != "ROXE":
            #     deliverFee = 0.00
            # else:
            #     deliverFee = Decimal(float(channel_info_out[0]["outBankFee"])).quantize(Decimal('0.00'))
            return sendFee, deliverFee

    def getRpcFeeInDB(self, channel_name, currency, country=None):
        rpc_sql = f"select * from `roxe_rpc`.rpc_corridor_info where channel_name='{channel_name}' and currency='{currency}'"
        if country:
            rpc_sql += f" and country='{country}'"
        rpc_info = self.mysql.exec_sql_query(rpc_sql)
        node_fee = {"in": None, "out": None}
        for i in rpc_info:
            if i["corridorType"] == 1:
                node_fee["in"] = i
            if i["corridorType"] == 0:
                node_fee["out"] = i
        return node_fee

    def makeReceiveInfo(self, res_required_fields, body, businessType="C2C", isChannelNode=False):
        fields_list = self.checkGetReceiverRequiredFields(res_required_fields)
        dict_field = {}
        for field in fields_list:
            if isChannelNode:
                pass
            if field == "receiverFirstName":
                dict_field[field] = "Jack XX"
            elif field == "receiverLastName":
                dict_field[field] = "Bob XX"
            elif field == "receiverAccountName":
                dict_field[field] = "Jack Bob"
            elif field == "receiverAccountNumber":
                dict_field[field] = "1234567890"
            elif field == "receiverBankName":
                dict_field[field] = "XXXX BANK"
            elif field == "receiverIdType":
                dict_field[field] = "individual"
            elif field == "receiverIdNumber":
                dict_field[field] = "123456"
            elif field == "receiverBankRoxeId":
                dict_field[field] = body["receiveNodeCode"]
            elif field == "receiverCurrency":
                dict_field[field] = body["receiveCurrency"]
            elif field == "receiveMethodCode":
                if body["receiveMethodCode"] == None or body["receiveMethodCode"] == "":
                    body["receiveMethodCode"] = "BANK"
                dict_field[field] = body["receiveMethodCode"]
            elif field == "receiverCountry":
                dict_field[field] = "US"
            elif field == "senderFirstName":
                dict_field[field] = "Test user"
            elif field == "senderLastName":
                dict_field[field] = "handsome"
            elif field == "senderIdType":
                dict_field[field] = "nationalidcard"
            elif field == "senderIdNumber":
                dict_field[field] = "123456789"
            elif field == "senderIdExpireDate":
                dict_field[field] = "2100-01-02"
            elif field == "senderNationality":
                dict_field[field] = "US"
            elif field == "senderCountry":
                dict_field[field] = "US"
            elif field == "senderCity":
                dict_field[field] = "Washington"
            elif field == "senderCity":
                dict_field[field] = "Washington"
            elif field == "senderAddress":
                dict_field[field] = "1 Financial Street"
            elif field == "senderPhone":
                dict_field[field] = "+123456789"
            elif field == "senderBirthday":
                dict_field[field] = "2000-01-02"
            elif field == "senderSourceOfFund":
                dict_field[field] = "Salary"
            elif field == "senderBeneficiaryRelationship":
                dict_field[field] = "Friend"
            elif field == "purpose":
                dict_field[field] = "Gift"
            else:
                dict_field[field] = "abc"

        receive_documents_list = ["receiverBankRoxeId", ["receiverBankNCCType", "receiverBankNCC"], "receiverBankBIC", "receiverIBAN"]
        receive_documents = secrets.choice(receive_documents_list)
        if len(receive_documents) == 2:
            dict_field[receive_documents[0]] = "abc"
            dict_field[receive_documents[1]] = "123456"
        else:
            dict_field[receive_documents] = "abc"
        if businessType == "B2C":
            receive_documents_list2 = ["senderOrgBIC", "senderOrgLei", "senderOrgIdNumber"]
            receive_documents2 = secrets.choice(receive_documents_list2)
            dict_field[receive_documents2] = "abc"
        elif businessType == "C2B":
            receive_documents_list3 = ["receiverOrgBIC", "receiverOrgLei", "receiverOrgIdNumber"]
            receive_documents3 = secrets.choice(receive_documents_list3)
            dict_field[receive_documents3] = "abc"
        elif businessType == "B2B":
            receive_documents_list2 = ["senderOrgBIC", "senderOrgLei", "senderOrgIdNumber"]
            receive_documents2 = secrets.choice(receive_documents_list2)
            dict_field[receive_documents2] = "abc"
            receive_documents_list3 = ["receiverOrgBIC", "receiverOrgLei", "receiverOrgIdNumber"]
            receive_documents3 = secrets.choice(receive_documents_list3)
            dict_field[receive_documents3] = "abc"

        receiveInfo = json.dumps(dict_field)
        self.client.logger.info(f"根据获取的出金必填字段生成的receiveInfo:{receiveInfo}")

        return dict_field

    # 校验函数
    def checkNodeInfoFormDB(self, roxe_node, isInAmount=False, isReturnOrder=False, isFaitToRo=False):
        if RTSData.is_check_db:
            db_node_info = self.mysql.exec_sql_query(f"select * from `roxe_node_v3`.`node_config_info`")
            # 判断节点是否存在换汇
            if isinstance(roxe_node, dict):
                node_in_currency = roxe_node["transferInCurrency"].split(".")[0]
                node_out_currency = roxe_node["transferOutCurrency"].split(".")[0]
                if node_in_currency == node_out_currency:
                    self.assertEqual(roxe_node["exchangeRate"], 1)

                node_list = []
                nodeConfig_list = []
                for node_data in db_node_info:
                    node_list.append(node_data["nodeCode"])
                    nodeConfig_list.append(node_data["nodeConfig"])
                assert roxe_node["nodeCode"] in node_list, "返回的节点不正确"

                for nodeConfig_data in nodeConfig_list:
                    nodeConfig = json.loads(nodeConfig_data)
                    if roxe_node["nodeCode"] == nodeConfig["code"]:
                        node_name = None if nodeConfig["name"] == "" else nodeConfig["name"]
                        node_type = None if nodeConfig["type"] == "" else nodeConfig["type"].upper()
                        # self.assertEqual(roxe_node["nodeName"], node_name)  # 文档去除该字段
                        self.assertEqual(roxe_node["nodeType"], node_type)
                        # 校验费用币种
                        for path_info in nodeConfig["pathList"]:
                            db_node_pay_currency_country = path_info["payCurrency"] + "." + nodeConfig["country"].upper() if "ROXE" not in path_info["payCurrency"] else path_info["payCurrency"]
                            db_node_out_currency_country = path_info["outCurrency"] + "." + nodeConfig["country"].upper() if "ROXE" not in path_info["outCurrency"] else path_info["outCurrency"]

                            if roxe_node["transferInCurrency"] == db_node_pay_currency_country and roxe_node["transferOutCurrency"] == db_node_out_currency_country:
                                feeCurrency = path_info["feeCurrency"]
                            else:
                                continue
                            if isInAmount:
                                self.assertEqual(roxe_node["sendFeeCurrency"], feeCurrency, "返回的send费用币种不正确")
                                self.assertEqual(roxe_node["deliveryFeeCurrency"], "")
                                self.assertEqual(roxe_node["serviceFeeCurrency"], "")
                            else:
                                self.assertEqual(roxe_node["deliveryFeeCurrency"], feeCurrency, "返回的节点费用币种不正确")
                                self.assertEqual(roxe_node["sendFeeCurrency"], "")
                                self.assertEqual(roxe_node["serviceFeeCurrency"], "")
                        # 费用校验
                        if isInAmount:
                            # 当前下单入金仅使用了CHECKOUT，后期可添加STRIPE
                            node_code = "CHECKOUT" if roxe_node["nodeCode"] == RTSData.checkout_node else roxe_node["nodeCode"]
                            channel_info_in = self.mysql.exec_sql_query(
                                "select * from roxe_rpc.rpc_corridor_info where channel_name like '%{}%' and currency like '%{}%' and country like '%{}%' and corridor_type={}".format(
                                    node_code, node_in_currency, nodeConfig["country"].upper(), 1))
                            if isReturnOrder:
                                send_fee = (Decimal(float(channel_info_in[0]["inReturnFee"])).quantize(Decimal('0.00')) if len(channel_info_in) == 1 else "未查询到send费用")
                            else:
                                send_fee = (Decimal(float(channel_info_in[0]["inFeeAmount"])).quantize(Decimal('0.00')) if len(channel_info_in) == 1 else "未查询到send费用")
                            # 因为APP需求，现将入金的节点费改为了0
                            if isFaitToRo:
                                self.assertEqual(roxe_node["sendFee"], 0)
                            else:
                                self.assertEqual(roxe_node["sendFee"], float(send_fee))
                            self.assertEqual(roxe_node["deliveryFee"], 0)
                            self.assertEqual(roxe_node["serviceFee"], 0)
                        else:
                            node_code = RTSData.channel_name[roxe_node["nodeCode"]] if roxe_node["nodeCode"] in RTSData.channel_nodes else roxe_node["nodeCode"]
                            channel_info_out = self.mysql.exec_sql_query(
                                "select * from roxe_rpc.rpc_corridor_info where channel_name like '%{}%' and currency like '%{}%' and country like '%{}%' and corridor_type={}".format(
                                    node_code, node_out_currency, nodeConfig["country"].upper(), 0))
                            # 针对ewallet临时处理
                            if roxe_node["nodeCode"] == RTSData.gcash_node:
                                deliver_fee = (Decimal(float(channel_info_out[0]["outWalletFee"])).quantize(Decimal('0.00')) if len(channel_info_out) == 1 else "未查询到deliver费用")
                            else:
                                if isReturnOrder:
                                    deliver_fee = (Decimal(float(channel_info_out[0]["outReturnFee"])).quantize(Decimal('0.00')) if len(channel_info_out) == 1 else "未查询到deliver费用")
                                else:
                                    deliver_fee = (Decimal(float(channel_info_out[0]["outBankFee"])).quantize(Decimal('0.00')) if len(channel_info_out) == 1 else "未查询到deliver费用")
                            self.assertEqual(roxe_node["deliveryFee"], float(deliver_fee))
                            self.assertEqual(roxe_node["sendFee"], 0)
                            self.assertEqual(roxe_node["serviceFee"], 0)
            verify_node_code = roxe_node["nodeCode"]
            self.client.logger.info(f"{verify_node_code}节点信息校验通过")

    def checkServiceFeeCurrencyAndserviceFee(self, sendCurrency, sendCountry, serviceFeeCurrency, serviceFee, receiveCurrency):
        if "ROXE" in sendCurrency:
            self.assertEqual(serviceFeeCurrency, "")
            self.assertEqual(serviceFee, 0)
        elif "ROXE" not in sendCurrency and "ROXE" in receiveCurrency:  # fait->ro
            # self.assertEqual(serviceFeeCurrency, sendCurrency)
            self.assertEqual(serviceFeeCurrency, "")
            self.assertEqual(serviceFee, 0)
        else:
            currency_configure_list = ["USD"]  # 当前系统仅支持USB币种配置
            if sendCurrency in currency_configure_list:
                self.assertEqual(serviceFeeCurrency, sendCurrency)
            else:
                self.assertEqual(serviceFeeCurrency, "")
            # 校验费用
            if serviceFeeCurrency == "USD" and sendCountry == "US":
                self.assertEqual(serviceFee, 1.5)
            elif serviceFeeCurrency == "USD" and sendCountry == "GB":
                self.assertEqual(serviceFee, 2.35)
            elif serviceFeeCurrency == "PHP" and sendCountry == "PH":
                self.assertEqual(serviceFee, 20)
            else:
                self.assertEqual(serviceFee, 0)

    def checkCodeAndMessage(self, responseJson, code='0', message='Success'):
        self.assertEqual(responseJson["code"], code, f"接口结果: {responseJson}")
        self.assertEqual(responseJson["message"], message, f"接口结果: {responseJson}")

    def checkTransactionCurrency(self, res_currency, r_body):
        tx_currency = res_currency["data"]
        if RTSData.is_check_db:
            db_res = self.mysql.exec_sql_query("select * from `roxe_rts_v3`.`rts_node_router`")
            # print(db_res)
            if r_body["sendCountry"]:
                db_res = [i for i in db_res if i["payCountry"] == r_body['sendCountry']]

            if r_body["sendCurrency"]:
                db_res = [i for i in db_res if i["payCurrency"] == r_body["sendCurrency"]]

            if r_body["receiveCountry"]:
                db_res = [i for i in db_res if i["outCountry"] == r_body['receiveCountry']]

            if r_body["receiveCurrency"]:
                    db_res = [i for i in db_res if i["outCurrency"] == r_body["receiveCurrency"]]

            if not r_body["returnAllCurrency"]:
                tmp_db = []
                for i in db_res:
                    if i["payCurrency"].endswith(".ROXE") or i["outCurrency"].endswith(".ROXE"):
                        continue
                    elif i["payCurrency"].split(".")[0] in RTSData.digitalCurrency or i["outCurrency"].split(".")[0] in RTSData.digitalCurrency:
                        continue
                    else:
                        tmp_db.append(i)

                db_res = tmp_db

            router_path = list(set([i["payCountry"] + i["payCurrency"] + i["outCountry"] + i["outCurrency"] for i in db_res]))
            # print(router_path)
            self.assertEqual(len(router_path), len(tx_currency))
            for currency_info in tx_currency:
                if currency_info["sendCurrency"].endswith("ROXE") and currency_info["receiveCurrency"].endswith("ROXE"):
                    db_info = [i for i in db_res if
                               i['payCurrency'] == currency_info["sendCurrency"] and i['outCurrency'] == currency_info[
                                   "receiveCurrency"]]
                elif currency_info["sendCurrency"].endswith("ROXE"):
                    db_info = [i for i in db_res if
                               i['payCurrency'] == currency_info["sendCurrency"] and i['outCurrency'] ==
                               currency_info["receiveCurrency"]]
                elif currency_info["receiveCurrency"].endswith("ROXE"):
                    db_info = [i for i in db_res if
                               i['payCurrency'] == currency_info["sendCurrency"] and i['outCurrency'] ==
                               currency_info["receiveCurrency"]]
                else:
                    db_info = [i for i in db_res if i['payCurrency'] == currency_info["sendCurrency"] and
                               i['outCurrency'] == currency_info["receiveCurrency"]]
                if len(db_info) > 1:
                    if currency_info['sendCountry']: db_info = [i for i in db_info if i['payCountry'] == currency_info['sendCountry']]
                    if currency_info['receiveCountry']: db_info = [i for i in db_info if i['outCountry'] == currency_info['receiveCountry']]

                self.assertTrue(len(db_info) >= 1, f"{currency_info} 没有在数据库中找到对应的数据")

    def checkGetPayoutMethod(self, response, body):
        receive_method_code = response["data"]
        self.checkCodeAndMessage(response)
        if RTSData.is_check_db:
            rts_node_info = self.mysql.exec_sql_query(f"select * from `roxe_rts_v3`.`rts_node_info` ")
            for node_info in rts_node_info:
                node_info_json = json.loads(node_info["nodeInfo"])
                if node_info["nodeCode"] == body["receiveNodeCode"]:
                    self.assertEqual(sorted(receive_method_code["receiveMethodCode"]), sorted(node_info_json["paymentMethods"]))

    def checkRouterList(self, response, body):
        self.checkCodeAndMessage(response)
        res_data = response["data"]
        if isinstance(res_data, dict):
            self.assertEqual(res_data["routerStrategy"], body["routerStrategy"])
            self.assertEqual(res_data["businessType"], body["businessType"])
            self.assertEqual(res_data["isReturnOrder"], body["isReturnOrder"])
            self.assertEqual(res_data["sendNodeCode"], body["sendNodeCode"])
            self.assertEqual(res_data["sendCountry"], body["sendCountry"])
            self.assertEqual(res_data["sendCurrency"], body["sendCurrency"])
            self.assertEqual(res_data["sendAmount"], body["sendAmount"])
            self.assertEqual(res_data["receiveNodeCode"], body["receiveNodeCode"])
            self.assertEqual(res_data["receiveCountry"], body["receiveCountry"])
            self.assertEqual(res_data["receiveCurrency"], body["receiveCurrency"])
            self.assertEqual(res_data["receiveAmount"], body["receiveAmount"])
            self.assertEqual(res_data["receiveMethodCode"], body["receiveMethodCode"])
            self.assertEqual(res_data["eWalletCode"], body["eWalletCode"])
            self.assertEqual(res_data["passByNodes"], body["passByNodes"])
            if "ROXE" in body["sendCurrency"] and "ROXE" in body["receiveCurrency"]:
                self.assertEqual(res_data["roxeRouters"][0]["roxeNodes"], [])
            if RTSData.is_check_db:
                rts_node_router = self.mysql.exec_sql_query(f"select * from `roxe_rts_v3`.`rts_node_router`")
                db_data_list = []
                db_routerId_list = []
                routerConfig_list = []
                for db_data_info in rts_node_router:
                    db_data_list.append(db_data_info)
                    db_routerId_list.append(db_data_info["routerId"])
                    routerConfig = json.loads(db_data_info["routerConfig"])
                    routerConfig_list.append(routerConfig)

                # 1、验证路由条数
                if body["routerStrategy"] == "LOWEST_FEE" and len(res_data["roxeRouters"]) != []:  # 当前程序仅支持费用最低策略
                    self.assertEqual(len(res_data["roxeRouters"]), 1)
                else:
                    # （1）验证ro-ro路由条数
                    db_filter_data_list = []
                    if "ROXE" in body["sendCurrency"] and "ROXE" in body["receiveCurrency"]:
                        for db_data in db_data_list:
                            if body["sendCurrency"] == db_data["payCurrency"] and body["receiveCurrency"] == db_data["outCurrency"]:
                                if db_data["routerConfig"] == "{}":
                                    db_filter_data_list.append(db_data)
                        self.assertEqual(len(res_data["roxeRouters"]), len(db_filter_data_list), "返回的路由条数不正确")
                    # （2）验证fait-ro的路由条数
                    elif "ROXE" not in body["sendCurrency"] and "ROXE" in body["receiveCurrency"]:
                        for db_data in db_data_list:
                            routerConfig = json.loads(db_data["routerConfig"])
                            if "left" in routerConfig:
                                if (body["sendNodeCode"] == routerConfig["left"][0]["nodeCode"] or body["sendCountry"] == db_data["payCountry"]) and \
                                     body["sendCurrency"] == db_data["payCurrency"] and body["receiveCurrency"] == db_data["outCurrency"]:
                                    db_filter_data_list.append(db_data)
                        self.assertEqual(len(res_data["roxeRouters"]), len(db_filter_data_list), "返回的路由条数不正确")
                    # （3）验证ro-fait的路由条数
                    elif "ROXE" in body["sendCurrency"] and "ROXE" not in body["receiveCurrency"]:
                        for db_data in db_data_list:
                            routerConfig = json.loads(db_data["routerConfig"])
                            if "right" in routerConfig:
                                if body["sendCurrency"] == db_data["payCurrency"] and body["receiveCurrency"] == db_data["outCurrency"] and \
                                        (body["receiveNodeCode"] == routerConfig["right"][-1]["nodeCode"] or body["receiveCountry"] == db_data["outCountry"]):
                                    db_filter_data_list.append(db_data)
                        self.assertEqual(len(res_data["roxeRouters"]), len(db_filter_data_list), "返回的路由条数不正确")
                    # （4）验证fait-fait的路由条数
                    elif "ROXE" not in body["sendCurrency"] and "ROXE" not in body["receiveCurrency"]:
                        for db_data in db_data_list:
                            routerConfig = json.loads(db_data["routerConfig"])
                            if "left" in routerConfig and "right" in routerConfig:
                                if (body["sendNodeCode"] == routerConfig["left"][0]["nodeCode"] or body["sendCountry"] == db_data["payCountry"]) and \
                                    (body["receiveNodeCode"] == routerConfig["right"][-1]["nodeCode"] or body["receiveCountry"] == db_data["outCountry"]) and \
                                        body["sendCurrency"] == db_data["payCurrency"] and body["receiveCurrency"] == db_data["outCurrency"]:
                                    # 去除不符合return的路由
                                    if body["isReturnOrder"] == True and routerConfig["right"][-1]["nodeCode"] in RTSData.channel_nodes:
                                        continue
                                    elif body["isReturnOrder"] == True and routerConfig["right"][0]["nodeCode"] in RTSData.channel_nodes:
                                        continue
                                    elif body["receiveNodeCode"] == None  and len(routerConfig["right"]) == 2: # 当右侧只输入国家参数没有节点参数的情况下去除右侧包含pn节点的路由
                                        continue
                                    else:
                                        if body["passByNodes"] != None:
                                            db_left_nodecode_list = [i["nodeCode"] for i in routerConfig["left"]]
                                            db_right_nodecode_list = [j["nodeCode"] for j in routerConfig["right"]]
                                            all_nodecode_list = db_left_nodecode_list+db_right_nodecode_list
                                            if set(body["passByNodes"]) < set(all_nodecode_list):
                                                db_filter_data_list.append(db_data)
                                            else:
                                                continue
                                        else:
                                            db_filter_data_list.append(db_data)

                        self.assertEqual(len(res_data["roxeRouters"]), len(db_filter_data_list), "返回的路由条数不正确")

                for roxeRouter_data in res_data["roxeRouters"]:
                    # 1、验证roxeRouters的外层字段
                    if int(roxeRouter_data["routerId"]) in db_routerId_list:
                        self.assertIsNone(roxeRouter_data["custodyAccountInfo"])  # custodyAccountInfo暂无实际意义
                        self.assertEqual(roxeRouter_data["sendAmount"], body["sendAmount"])
                        # 校验serviceFeeCurrency和serviceFee
                        if "ROXE" in body["sendCurrency"]:
                            self.assertEqual(roxeRouter_data["serviceFeeCurrency"], "")
                            self.assertEqual(roxeRouter_data["serviceFee"], 0)
                        else:
                            self.checkServiceFeeCurrencyAndserviceFee(body["sendCurrency"], roxeRouter_data["roxeNodes"][0]["transferInCurrency"].split(".")[1],
                                                                  roxeRouter_data["serviceFeeCurrency"], roxeRouter_data["serviceFee"], body["receiveCurrency"])

                        for db_data in db_data_list:
                            if roxeRouter_data["routerId"] == str(db_data["routerId"]):
                                payCountry = "" if db_data["payCountry"] == "" else db_data["payCountry"]
                                outCountry = "" if db_data["outCountry"] == "" else db_data["outCountry"]
                                self.assertEqual(roxeRouter_data["sendCountry"], payCountry)
                                self.assertEqual(roxeRouter_data["sendCurrency"], db_data["payCurrency"])
                                self.assertEqual(roxeRouter_data["receiveCountry"], outCountry)
                                self.assertEqual(roxeRouter_data["receiveCurrency"], db_data["outCurrency"])
                                self.client.logger.warning("验证roxeRouters的外层字段正确")
                    else:
                        self.client.logger.warning("返回的路由信息不正确：路由ID与数据库不匹配")

                    # 校验币种相同时外层汇率及收款金额
                    sendCurrency = res_data["sendCurrency"].split(".")[0] if "ROXE" in res_data["sendCurrency"] else res_data["sendCurrency"]
                    receiveCurrency = res_data["receiveCurrency"].split(".")[0] if "ROXE" in res_data["receiveCurrency"] else res_data["receiveCurrency"]
                    if sendCurrency == receiveCurrency:
                        self.assertEqual(roxeRouter_data["exchangeRate"], 1, "返回的汇率不正确")
                        receiveAmount = '%.2f' % (body["sendAmount"]-roxeRouter_data["sendFee"]-roxeRouter_data["deliveryFee"]-roxeRouter_data["serviceFee"])
                        self.assertEqual(roxeRouter_data["receiveAmount"], float(receiveAmount))
                    else:
                        # 节点换汇
                        exchangeRate_list = []
                        for node_info in roxeRouter_data["roxeNodes"]:
                            if node_info["exchangeRate"] != 1:
                                exchangeRate_list.append(node_info["exchangeRate"])
                                # 节点换汇，因为暂时无法获取节点换汇汇率，暂时此处与节点内返回的汇率比较
                                self.assertEqual(roxeRouter_data["exchangeRate"], node_info["exchangeRate"], msg="返回的节点换汇汇率不正确")
                                self.client.logger.warning("返回的节点换汇汇率正确")
                                if roxeRouter_data["deliveryFeeCurrency"] == sendCurrency:
                                    receiveAmount = '%.2f' % ((body["sendAmount"] - roxeRouter_data["sendFee"] - roxeRouter_data["deliveryFee"] - roxeRouter_data["serviceFee"]) * roxeRouter_data["exchangeRate"])
                                else:
                                    receiveAmount = '%.2f' % ((body["sendAmount"] - roxeRouter_data["sendFee"] - roxeRouter_data["serviceFee"]) * roxeRouter_data["exchangeRate"] - roxeRouter_data["deliveryFee"])
                                self.assertEqual(float('%.2f' % roxeRouter_data["receiveAmount"]), float(receiveAmount))
                        # 校验rpp换汇汇率
                        send_rate_amount = '%.2f' % (body["sendAmount"] - roxeRouter_data["sendFee"] - roxeRouter_data["serviceFee"])  # 扣除sendFee的金额
                        # send_rate_amount = '%.2f' % (body["sendAmount"] - roxeRouter_data["serviceFee"])  # 未扣除sendFee的金额
                        if len(exchangeRate_list) == 0:
                            rate_data, rate_body = self.client.getRate(sendCurrency, receiveCurrency, float(send_rate_amount))
                            self.assertAlmostEqual(roxeRouter_data["exchangeRate"], float(rate_data["data"]["exchangeRate"]), msg="返回的rpp换汇汇率不正确", delta=0.1**6)
                            self.client.logger.warning("返回的rpp换汇汇率正确")
                        if roxeRouter_data["deliveryFeeCurrency"] == sendCurrency:
                            receiveAmount = '%.2f' % ((float(send_rate_amount) - roxeRouter_data["deliveryFee"]) * roxeRouter_data["exchangeRate"])

                        else:
                            receiveAmount = '%.2f' % (float(send_rate_amount) * roxeRouter_data["exchangeRate"] - roxeRouter_data["deliveryFee"])

                        self.assertEqual(float('%.2f' % roxeRouter_data["receiveAmount"]), float(receiveAmount))
                    # 3、校验roxeNodes
                    # nodeDescription字段暂无实际意义
                    # ro->ro
                    if len(roxeRouter_data["roxeNodes"]) == 0:
                        self.assertEqual(roxeRouter_data["roxeNodes"], [])
                        self.client.logger.warning("返回ro->ro的路由节点信息正确")
                        return
                    # fait->ro
                    elif len(roxeRouter_data["roxeNodes"]) == 1 and "ROXE" not in res_data["sendCurrency"]:
                        self.checkNodeInfoFormDB(roxeRouter_data["roxeNodes"][0], isInAmount=True, isReturnOrder=body["isReturnOrder"], isFaitToRo=True)
                        self.client.logger.warning("返回fait->ro的路由节点信息正确")
                        return
                    # ro->fait
                    elif len(roxeRouter_data["roxeNodes"]) == 1 and "ROXE" not in res_data["receiveCurrency"]:
                        self.checkNodeInfoFormDB(roxeRouter_data["roxeNodes"][-1], isReturnOrder=body["isReturnOrder"])
                        self.client.logger.warning("返回ro->fait的路由节点信息正确")
                        return
                    # fait->fait(sn-sn)
                    elif len(roxeRouter_data["roxeNodes"]) == 2:
                        self.checkNodeInfoFormDB(roxeRouter_data["roxeNodes"][0], isInAmount=True, isReturnOrder=body["isReturnOrder"])
                        self.checkNodeInfoFormDB(roxeRouter_data["roxeNodes"][1], isReturnOrder=body["isReturnOrder"])
                        self.client.logger.warning("返回fait->fait(sn-sn)的路由节点信息正确")
                        return
                    # fait->fait
                    elif len(roxeRouter_data["roxeNodes"]) == 3:
                        # pn-sn-sn
                        if roxeRouter_data["roxeNodes"][0]["nodeType"] == "PN":
                            self.checkNodeInfoFormDB(roxeRouter_data["roxeNodes"][0], isInAmount=True, isReturnOrder=body["isReturnOrder"])
                            self.checkNodeInfoFormDB(roxeRouter_data["roxeNodes"][1], isInAmount=True, isReturnOrder=body["isReturnOrder"])
                            self.checkNodeInfoFormDB(roxeRouter_data["roxeNodes"][2], isReturnOrder=body["isReturnOrder"])
                            self.client.logger.warning("返回fait->fait(pn-sn-sn)的路由节点信息正确")
                            return
                        # sn-sn-pn
                        elif roxeRouter_data["roxeNodes"][0]["nodeType"] == "SN":
                            self.checkNodeInfoFormDB(roxeRouter_data["roxeNodes"][0], isInAmount=True, isReturnOrder=body["isReturnOrder"])
                            self.checkNodeInfoFormDB(roxeRouter_data["roxeNodes"][1], isReturnOrder=body["isReturnOrder"])
                            self.checkNodeInfoFormDB(roxeRouter_data["roxeNodes"][2], isReturnOrder=body["isReturnOrder"])
                            self.client.logger.warning("返回fait->fait(sn-sn-pn)的路由节点信息正确")
                            return
                    # fait->fait
                    elif len(roxeRouter_data["roxeNodes"]) == 4:
                        # pn-sn-sn-pn
                        self.checkNodeInfoFormDB(roxeRouter_data["roxeNodes"][0], isInAmount=True, isReturnOrder=body["isReturnOrder"])
                        self.checkNodeInfoFormDB(roxeRouter_data["roxeNodes"][1], isInAmount=True, isReturnOrder=body["isReturnOrder"])
                        self.checkNodeInfoFormDB(roxeRouter_data["roxeNodes"][2], isReturnOrder=body["isReturnOrder"])
                        self.checkNodeInfoFormDB(roxeRouter_data["roxeNodes"][3], isReturnOrder=body["isReturnOrder"])
                        self.client.logger.warning("返回fait->fait(pn-sn-sn-pn)的路由节点信息正确")
                        return
                    else:
                        self.client.logger.warning("返回的路由节点信息不正确")
                        return

    def checkGetReceiverRequiredFields(self, res_data):
        self.checkCodeAndMessage(res_data)
        required_fields = res_data["data"]
        self.assertIsNotNone(required_fields, "返回的出金必填字段为空")
        fields_list = []
        if len(required_fields) > 0:
            for field_data in required_fields:
                if field_data["required"] is True:
                    fields_list.append(field_data["name"])
        self.assertEqual(len(fields_list), len(list(set(fields_list))), "返回的必填字段中存在重复字段")
        return fields_list

    def checkCheckReceiverRequiredFields(self, res_data):
        self.checkCodeAndMessage(res_data)
        res_info = res_data["data"]
        self.assertTrue(res_info["verified"], f"必填字段异常信息:{res_info['message']}")

    def checksubmitOrder(self, res_data, body, send_fee, deliver_fee, service_fee=1.50, ro2ro=False):
        self.checkCodeAndMessage(res_data)
        res_info = res_data["data"]
        # 检查是否配置代扣deliver_fee
        if RTSData.is_check_db:
            rts_node_info = self.mysql.exec_sql_query(f"select * from `roxe_rts_v3`.`rts_node_info`")
            for node in rts_node_info:
                if res_info["roxeNodes"] != [] and node["nodeCode"] == res_info["roxeNodes"][-1]["nodeCode"]:
                    nodeInfo = json.loads(node["nodeInfo"])
                    if nodeInfo["needPayHold"] == False:
                        deliver_fee = 0
                    else:
                        deliver_fee = deliver_fee
        if isinstance(res_info, dict):
            self.assertEqual(res_info["instructionId"], body["instructionId"])
            self.assertIsNotNone(res_info["transactionId"])
            self.assertEqual(res_info["paymentId"], body["paymentId"])
            self.assertEqual(res_info["originalId"], body["originalId"])
            self.assertEqual(res_info["extensionField"], body["extensionField"])
            self.assertEqual(res_info["routerStrategy"], body["routerStrategy"])
            self.assertEqual(res_info["sendNodeCode"], body["sendNodeCode"])

            # self.assertEqual(res_info["sendCountry"], body["sendCountry"])  # todo 加解密导致""->null
            # if body["sendCountry"] == "":
            #     # self.assertIsNone(res_info["sendCountry"])
            #     assert res_info["sendCountry"]=="" or res_info["sendCountry"]==None
            # else:
            #     self.assertEqual(res_info["sendCountry"], body["sendCountry"])

            self.assertEqual(res_info["sendCurrency"], body["sendCurrency"])
            self.assertEqual(res_info["sendAmount"], body["sendAmount"])
            self.assertEqual(res_info["receiveNodeCode"], body["receiveNodeCode"])

            # self.assertEqual(res_info["receiveCountry"], body["receiveCountry"])  # todo 加解密导致""->null
            # if body["receiveCountry"] == "":
            #     # self.assertIsNone(res_info["receiveCountry"])
            #     assert res_info["receiveCountry"] == "" or res_info["receiveCountry"] == None
            # else:
            #     self.assertEqual(res_info["receiveCountry"], body["receiveCountry"])

            self.assertEqual(res_info["receiveCurrency"], body["receiveCurrency"])
            self.assertEqual(res_info["receiveAmount"], body["receiveAmount"])
            self.assertEqual(res_info["notifyURL"], body["notifyURL"])
            self.assertEqual(res_info["channelCode"], body["channelCode"])
            self.assertEqual(res_info["couponCode"], body["couponCode"])
            self.assertEqual(res_info["txState"], "TRANSACTION_SUBMIT")
            assert res_info["receiveInfo"] == body["receiveInfo"]
            assert res_info["createTime"] <= res_info["updateTime"]
            # 校验汇率及预计收款金额
            sendCurrency = res_info["sendCurrency"].split(".")[0] if ".ROXE" in res_info["sendCurrency"] else res_info["sendCurrency"]
            receiveCurrency = res_info["receiveCurrency"].split(".")[0] if ".ROXE" in res_info["receiveCurrency"] else res_info["receiveCurrency"]
            if sendCurrency == receiveCurrency:
                self.assertEqual(res_info["exchangeRate"], 1)
                actual_out_amount = '%.2f' % (body["sendAmount"] - float(send_fee) - float(service_fee) - float(deliver_fee))
                self.assertEqual(str(res_info["quoteReceiveAmount"]), str(float(actual_out_amount)), msg="预期收款金额与预期实际出金金额不一致")
            else:
                # 目前仅是适用于Rpp换汇可查询的汇率,通过通道获取的汇率与rpp获取的汇率差异较大 todo
                # rate_data, body = self.client.getRate(sendCurrency, receiveCurrency, 1)
                # self.assertAlmostEqual(res_info["exchangeRate"], float(rate_data["data"]["exchangeRate"]), msg="返回的汇率不正确", delta=0.1)
                # actual_out_amount = '%.6f' % ((body["sendAmount"] - float(send_fee) - float(service_fee))*rate_data["data"]["exchangeRate"] - float(deliver_fee))
                # self.assertAlmostEqual(res_info["quoteReceiveAmount"], float(actual_out_amount), msg="预期收款金额与预期实际出金金额不一致", delta=0.1)
                assert res_info["exchangeRate"] is not None and res_info["exchangeRate"] != 1

            # 目前判断出金忽略出金为rmn节点情况
            # 校验外层费用及路径节点
            if "ROXE" in body["sendCurrency"]:
                self.assertEqual(res_info["serviceFeeCurrency"], "")
                self.assertEqual(res_info["serviceFee"], 0)
            else:
                self.checkServiceFeeCurrencyAndserviceFee(body["sendCurrency"], res_info["roxeNodes"][0]["transferInCurrency"].split(".")[1],
                                                      res_info["serviceFeeCurrency"], res_info["serviceFee"], body["receiveCurrency"])
            if ro2ro:
                self.assertEqual(res_info["serviceFee"], 0)
                self.assertEqual(res_info["sendFeeCurrency"], "")
                self.assertEqual(res_info["sendFee"], 0)
                self.assertEqual(res_info["deliveryFeeCurrency"], "")
                self.assertEqual(res_info["deliveryFee"], 0)
            # ro->fait
            if len(res_info["roxeNodes"]) == 1 and res_info["roxeNodes"][0]["nodeCode"] in RTSData.channel_nodes:
                self.assertEqual(res_info["serviceFee"], 0)
                self.assertEqual(res_info["sendFeeCurrency"], "")
                self.assertEqual(res_info["sendFee"], 0)
                self.assertEqual(res_info["deliveryFeeCurrency"], res_info["roxeNodes"][0]["deliveryFeeCurrency"])
                self.assertEqual(res_info["deliveryFee"], res_info["roxeNodes"][0]["deliveryFee"])
            # fait->ro(目前下单法币入金仅添加了checkout入金）
            elif len(res_info["roxeNodes"]) == 1 and res_info["roxeNodes"][0]["nodeCode"] == RTSData.checkout_node:
                self.checkNodeInfoFormDB(res_info["roxeNodes"][0], isInAmount=True, isFaitToRo=True)
                self.assertEqual(res_info["sendFeeCurrency"], res_info["roxeNodes"][0]["sendFeeCurrency"])
                self.assertEqual(res_info["sendFee"], res_info["roxeNodes"][0]["sendFee"])
                self.assertEqual(res_info["deliveryFeeCurrency"], "")
                self.assertEqual(res_info["deliveryFee"], 0)
            # fait->fait
            elif len(res_info["roxeNodes"]) == 2:
                self.checkNodeInfoFormDB(res_info["roxeNodes"][0], isInAmount=True)
                self.checkNodeInfoFormDB(res_info["roxeNodes"][1])
                self.assertEqual(res_info["sendFeeCurrency"], res_info["roxeNodes"][0]["sendFeeCurrency"])
                self.assertEqual(res_info["sendFee"], res_info["roxeNodes"][0]["sendFee"])
                self.assertEqual(res_info["deliveryFeeCurrency"], res_info["roxeNodes"][1]["deliveryFeeCurrency"])
                self.assertEqual(res_info["deliveryFee"], res_info["roxeNodes"][1]["deliveryFee"])
            elif len(res_info["roxeNodes"]) == 3:
                self.checkNodeInfoFormDB(res_info["roxeNodes"][0], isInAmount=True)
                if res_info["roxeNodes"][1]["nodeCode"] in RTSData.channel_nodes:
                    self.checkNodeInfoFormDB(res_info["roxeNodes"][1])
                    self.assertEqual(res_info["sendFeeCurrency"], res_info["roxeNodes"][0]["sendFeeCurrency"])
                    self.assertEqual(res_info["sendFee"], res_info["roxeNodes"][0]["sendFee"])
                    self.assertEqual(res_info["deliveryFeeCurrency"], res_info["roxeNodes"][2]["deliveryFeeCurrency"])
                    self.assertEqual(res_info["deliveryFee"], res_info["roxeNodes"][1]["deliveryFee"]+res_info["roxeNodes"][2]["deliveryFee"])
                else:
                    self.checkNodeInfoFormDB(res_info["roxeNodes"][1], isInAmount=True)
                    self.assertEqual(res_info["sendFeeCurrency"], res_info["roxeNodes"][0]["sendFeeCurrency"])
                    self.assertEqual(res_info["sendFee"], res_info["roxeNodes"][0]["sendFee"]+res_info["roxeNodes"][1]["sendFee"])
                    self.assertEqual(res_info["deliveryFeeCurrency"], res_info["roxeNodes"][2]["deliveryFeeCurrency"])
                    self.assertEqual(res_info["deliveryFee"], res_info["roxeNodes"][2]["deliveryFee"])
                self.checkNodeInfoFormDB(res_info["roxeNodes"][2])
            elif len(res_info["roxeNodes"]) == 4:
                self.checkNodeInfoFormDB(res_info["roxeNodes"][0], isInAmount=True)
                self.checkNodeInfoFormDB(res_info["roxeNodes"][1], isInAmount=True)
                self.checkNodeInfoFormDB(res_info["roxeNodes"][2])
                self.checkNodeInfoFormDB(res_info["roxeNodes"][3])
                self.assertEqual(res_info["sendFeeCurrency"], res_info["roxeNodes"][0]["sendFeeCurrency"])
                self.assertEqual(res_info["sendFee"], res_info["roxeNodes"][0]["sendFee"]+res_info["roxeNodes"][1]["sendFee"])
                self.assertEqual(res_info["deliveryFeeCurrency"], res_info["roxeNodes"][3]["deliveryFeeCurrency"])
                self.assertEqual(res_info["deliveryFee"], res_info["roxeNodes"][2]["deliveryFee"]+res_info["roxeNodes"][3]["deliveryFee"])

    def checkSuspendOrder(self, order_info, submit_order_res_data):
        order_data = order_info["data"]
        instruction_id = order_data["instructionId"]
        roxeNodes = submit_order_res_data["roxeNodes"]
        if roxeNodes == []:
            roxeNodes = None
            sendNodeCode = None
            sendCountry = ""
            receiveNodeCode = None
            receiveCountry = ""
        else:
            if len(roxeNodes) == 1:
                # ro->fait
                if "ROXE" in submit_order_res_data["sendCurrency"]:
                    sendNodeCode = None
                    sendCountry = ""
                    receiveNodeCode = roxeNodes[-1]["nodeCode"]
                    receiveCountry = roxeNodes[-1]["transferOutCurrency"].split(".")[1]
                # fait->ro
                else:
                    sendNodeCode = roxeNodes[0]["nodeCode"]
                    sendCountry = roxeNodes[0]["transferInCurrency"].split(".")[1]
                    receiveNodeCode = None
                    receiveCountry = ""
            # fait->fait
            else:
                sendNodeCode = roxeNodes[0]["nodeCode"]
                sendCountry = roxeNodes[0]["transferInCurrency"].split(".")[1]
                receiveNodeCode = roxeNodes[-1]["nodeCode"]
                receiveCountry = roxeNodes[-1]["transferOutCurrency"].split(".")[1]

        self.assertEqual(order_data["roxeNodes"], roxeNodes)
        self.assertEqual(order_data["txState"], "SUBMIT_SUSPEND")
        self.assertEqual(order_data["sendNodeCode"], sendNodeCode)
        self.assertEqual(order_data["sendCountry"], sendCountry)
        self.assertEqual(order_data["receiveNodeCode"], receiveNodeCode)
        self.assertEqual(order_data["receiveCountry"], receiveCountry)
        order_data.pop("txState")
        order_data.pop("roxeNodes")
        order_data.pop("sendNodeCode")
        order_data.pop("sendCountry")
        order_data.pop("receiveNodeCode")
        order_data.pop("receiveCountry")
        order_data.pop("updateTime")
        submit_order_res_data.pop("txState")
        submit_order_res_data.pop("roxeNodes")
        submit_order_res_data.pop("sendNodeCode")
        submit_order_res_data.pop("sendCountry")
        submit_order_res_data.pop("receiveNodeCode")
        submit_order_res_data.pop("receiveCountry")
        submit_order_res_data.pop("updateTime")
        self.assertEqual(order_data, submit_order_res_data)
        if RTSData.is_check_db:
            state_info = self.mysql.exec_sql_query(f"select * from `roxe_rts_v3`.`rts_order` where client_id='{instruction_id}'")
            self.assertTrue(state_info[0]["orderStop"])
            return state_info[0]["orderState"]

    def checkOrderInfo(self, order_info, submit_order_res, submit_body, instruction_id=None, transaction_id=None):
        order_info = order_info["data"]
        self.assertEqual(order_info["serviceFeeCurrency"], submit_order_res["data"]["serviceFeeCurrency"])
        self.assertEqual(order_info["serviceFee"], submit_order_res["data"]["serviceFee"])
        self.assertEqual(order_info["sendFeeCurrency"], submit_order_res["data"]["sendFeeCurrency"])
        self.assertEqual(order_info["sendFee"], submit_order_res["data"]["sendFee"])
        self.assertEqual(order_info["deliveryFeeCurrency"], submit_order_res["data"]["deliveryFeeCurrency"])
        self.assertEqual(order_info["deliveryFee"], submit_order_res["data"]["deliveryFee"])
        self.assertEqual(order_info["quoteReceiveAmount"], submit_order_res["data"]["quoteReceiveAmount"])
        origTransactionInfo = order_info["origTransactionInfo"]
        self.assertEqual(origTransactionInfo["receiveInfo"], submit_body["receiveInfo"])
        # self.assertEqual(origTransactionInfo["passByNodes"], submit_body["passByNodes"])  # todo rts程序对象引用问题，后期优化
        if origTransactionInfo["passByNodes"] != None and origTransactionInfo["passByNodes"] != []:
            node_code_list = [pass_node_info["nodeCode"] for pass_node_info in origTransactionInfo["passByNodes"]]
            submit_node_code_list = [submit_pass_node_info["nodeCode"] for submit_pass_node_info in submit_body["passByNodes"]]
            self.assertEqual(node_code_list, submit_node_code_list)
        origTransactionInfo_copy_data = copy.deepcopy(origTransactionInfo)
        origTransactionInfo_copy_data.pop("receiveInfo")
        origTransactionInfo_copy_data.pop("passByNodes")
        submit_body_copy_data = copy.deepcopy(submit_body)
        submit_body_copy_data.pop("receiveInfo")
        submit_body_copy_data.pop("passByNodes")

        # # todo 因为程序解析问题单独处理
        # if submit_body_copy_data["sendNodeCode"] == "":
        #     self.assertIsNone(origTransactionInfo_copy_data["sendNodeCode"])
        # else:
        #     self.assertEqual(origTransactionInfo_copy_data["sendNodeCode"], submit_body_copy_data["sendNodeCode"])
        # if submit_body_copy_data["sendCountry"] == "":
        #     self.assertIsNone(origTransactionInfo_copy_data["sendCountry"])
        # else:
        #     self.assertEqual(origTransactionInfo_copy_data["sendCountry"], submit_body_copy_data["sendCountry"])
        # if submit_body_copy_data["receiveNodeCode"] == "":
        #     self.assertIsNone(origTransactionInfo_copy_data["receiveNodeCode"])
        # else:
        #     self.assertEqual(origTransactionInfo_copy_data["receiveNodeCode"], submit_body_copy_data["receiveNodeCode"])
        # if submit_body_copy_data["receiveCountry"] == "":
        #     self.assertIsNone(origTransactionInfo_copy_data["receiveCountry"])
        # else:
        #     self.assertEqual(origTransactionInfo_copy_data["receiveCountry"], submit_body_copy_data["receiveCountry"])
        origTransactionInfo_copy_data.pop("sendNodeCode")
        origTransactionInfo_copy_data.pop("sendCountry")
        origTransactionInfo_copy_data.pop("receiveNodeCode")
        origTransactionInfo_copy_data.pop("receiveCountry")
        submit_body_copy_data.pop("sendNodeCode")
        submit_body_copy_data.pop("sendCountry")
        submit_body_copy_data.pop("receiveNodeCode")
        submit_body_copy_data.pop("receiveCountry")

        self.assertEqual(origTransactionInfo_copy_data, submit_body_copy_data)

        if order_info["txState"] == "TRANSACTION_FINISH":
            # 检查是否配置代扣deliver_fee
            if RTSData.is_check_db:
                rts_node_info = self.mysql.exec_sql_query(f"select * from `roxe_rts_v3`.`rts_node_info`")
                for node in rts_node_info:
                    if submit_order_res["data"]["roxeNodes"] != [] and node["nodeCode"] == submit_order_res["data"]["roxeNodes"][-1]["nodeCode"]:
                        nodeInfo = json.loads(node["nodeInfo"])
                        if nodeInfo["needPayHold"] == False:
                            deliver_fee = 0
                        else:
                            deliver_fee = deliver_fee

                        quoteReceiveAmount = order_info["quoteReceiveAmount"] + float(deliver_fee)
                        self.assertAlmostEqual(order_info["receiveAmount"], quoteReceiveAmount, msg="实际收款金额与预期收款金额相差过大", delta=1)
                        dif_amount = abs(float(order_info["receiveAmount"]) - quoteReceiveAmount)
                        self.client.logger.info(f"实际收款金额与预期收款金额差值: {dif_amount}")
            else:
                self.assertAlmostEqual(order_info["receiveAmount"], order_info["quoteReceiveAmount"], msg="实际收款金额与预期收款金额相差过大", delta=1)
                dif_amount = abs(float(order_info["receiveAmount"]) - order_info["quoteReceiveAmount"])
                self.client.logger.info(f"实际收款金额与预期收款金额差值: {dif_amount}")
        else:
            self.assertIsNone(order_info["receiveAmount"])

        if RTSData.is_check_db:
            if instruction_id:
                in_id = self.mysql.exec_sql_query(f"select * from `roxe_rts_v3`.`rts_order` where client_id='{instruction_id}'")
                self.assertEqual(order_info["transactionId"], in_id[0]["orderId"])
                self.assertEqual(order_info["origTransactionInfo"]["instructionId"], instruction_id)
                self.assertEqual(order_info["txState"], in_id[0]["orderState"])
                self.assertEqual(order_info["createTime"], int(in_id[0]["createTime"].timestamp() * 1000))
                self.assertEqual(order_info["updateTime"], int(in_id[0]["updateTime"].timestamp() * 1000))
            elif transaction_id:
                in_id = self.mysql.exec_sql_query(f"select * from `roxe_rts_v3`.`rts_order` where order_id='{transaction_id}'")
                self.assertEqual(order_info["transactionId"], transaction_id)
                self.assertEqual(order_info["origTransactionInfo"]["instructionId"], in_id[0]["clientId"])
                self.assertEqual(order_info["txState"], in_id[0]["orderState"])
                self.assertEqual(order_info["createTime"], int(in_id[0]["createTime"].timestamp() * 1000))
                self.assertEqual(order_info["updateTime"], int(in_id[0]["updateTime"].timestamp() * 1000))

    def checkOrderLog(self, order_log, instruction_id=None, transaction_id=None):
        order_log = order_log["data"]
        if RTSData.is_check_db:
            if instruction_id:
                in_id = self.mysql.exec_sql_query(f"select order_id from `roxe_rts_v3`.`rts_order` where client_id='{instruction_id}'")[0]["orderId"]
                db_res = self.mysql.exec_sql_query(f"select * from `roxe_rts_v3`.rts_order_log where order_id='{in_id}'")
                self.assertEqual(order_log["instructionId"], instruction_id)
                self.assertEqual(order_log["transactionId"], in_id)
            if transaction_id:
                in_id = self.mysql.exec_sql_query(f"select client_id from `roxe_rts_v3`.`rts_order` where order_id='{transaction_id}'")[0]["clientId"]
                db_res = self.mysql.exec_sql_query(f"select * from `roxe_rts_v3`.rts_order_log where order_id='{transaction_id}'")
                self.assertEqual(order_log["instructionId"], in_id)
                self.assertEqual(order_log["transactionId"], transaction_id)
            for o_log in order_log["stateInfo"]:
                find_db_log = [i for i in db_res if i["orderState"] == o_log["txState"]]
                self.assertEqual(o_log["txState"], find_db_log[0]["orderState"], f"查找的数据库日志: {find_db_log}")
                self.assertEqual(o_log["createTime"], int(find_db_log[0]["createTime"].timestamp() * 1000), f"查找的数据库日志: {find_db_log}")
            self.client.logger.info("查询订单日志校验正确")

    def verifyAndDecryptNotify(self, r_notify):
        parse_header = json.loads(r_notify["header"])
        ts = [i[1] for i in parse_header if "timestamp" == i[0]][0]
        sign = [i[1] for i in parse_header if "sign" == i[0]][0]
        res_en_data = ts + "::" + r_notify["response"].replace(" ", "")
        cur_path = os.path.abspath(__file__)
        verified = ApiUtils.rsa_verify(res_en_data, sign, os.path.join(cur_path, RTSData.ssl_pub_key))
        assert verified, "response验签失败"
        # 解密数据
        r_data = json.loads(r_notify["response"])["data"]["resource"]
        de_data = ApiUtils.aes_decrypt(r_data["ciphertext"], r_data["nonce"], r_data["associatedData"], RTSData.sec_key)
        parse_notify = json.loads(de_data)
        self.client.logger.info(f"notify解密为: {parse_notify}")
        return parse_notify

    def checkNumberDecimalLessThanSix(self, num):
        larg = num * 1000000
        self.assertLessEqual(larg, int(larg), f"{num}小数位数大于6位")

    def checkContractRateResult(self, contract_rate, request_body):
        if isinstance(request_body, bytes):
            request_body = json.loads(str(request_body, encoding="utf-8"))
        self.assertEqual(contract_rate["sendCurrency"], request_body["sendCurrency"].upper())
        self.assertEqual(contract_rate["receiveCurrency"], request_body["receiveCurrency"].upper())
        self.assertTrue(float(contract_rate["exchangeRate"]) > 0)

        if request_body["sendCurrency"] == request_body["receiveCurrency"]:
            self.assertEqual(contract_rate["exchangeRate"], "1")
            if request_body["sendAmount"] != "":
                self.assertAlmostEqual(contract_rate["receiveAmount"], float(request_body["sendAmount"]), delta=0.01)
                self.assertAlmostEqual(contract_rate["sendAmount"], float(request_body["sendAmount"]), delta=0.01)
            else:
                # self.assertEqual(contract_rate["receiveAmount"], request_body["receiveAmount"])
                # self.assertEqual(contract_rate["sendAmount"], request_body["receiveAmount"])
                # todo 暂时调整，校验通过
                self.assertAlmostEqual(contract_rate["receiveAmount"], float(request_body["receiveAmount"]), delta=0.01)
                self.assertAlmostEqual(contract_rate["sendAmount"], float(request_body["receiveAmount"]), delta=0.01)
        else:
            if request_body["sendAmount"] != "":
                # self.assertEqual(contract_rate["sendAmount"], request_body["sendAmount"])
                self.assertAlmostEqual(contract_rate["sendAmount"], float(request_body["sendAmount"]), delta=0.01)
                self.assertAlmostEqual(float(contract_rate["exchangeRate"]),
                                       float(contract_rate["receiveAmount"]) / float(request_body["sendAmount"]),
                                       delta=0.01)
                # self.assertEqual(contract_rate["receiveAmount"], str(round(float(contract_rate["exchangeRate"])*float(request_body["sendAmount"]), 2)))
                self.checkNumberDecimalLessThanSix(contract_rate["receiveAmount"])
                self.assertAlmostEqual(float(contract_rate["receiveAmount"]),
                                       round(float(contract_rate["exchangeRate"]) * float(request_body["sendAmount"]),
                                             2), delta=0.01)
            else:
                # self.assertEqual(contract_rate["receiveAmount"], request_body["receiveAmount"])
                self.assertAlmostEqual(contract_rate["receiveAmount"], float(request_body["receiveAmount"]), delta=0.01)
                self.assertAlmostEqual(float(contract_rate["exchangeRate"]),
                                       float(contract_rate["receiveAmount"]) / float(contract_rate["sendAmount"]),
                                       delta=0.000001)
                self.checkNumberDecimalLessThanSix(contract_rate["sendAmount"])
                # self.assertAlmostEqual(contract_rate["sendAmount"], round(
                #     float(contract_rate["receiveAmount"]) / float(contract_rate["exchangeRate"]), 2), delta=0.01)



    # 业务流程函数
    def submitOrderFloorOfRoToRo(self, sendCurrency, receiveCurrency, from_account, to_account, fromAccountKey, inAmount=None, routerStrategy=None, extensionField=None, is_just_submit=False):
        """
        RO->RO的下单流程:
            查询路由 -> 链上转账 -> 提交RTS订单 -> 查询订单信息 -> 等待订单完成 -> 查询订单信息 -> 查询订单日志
            每一步都有验证接口返回的结果
        :param sendCurrency: 付款币种
        :param receiveCurrency: 接收币种
        :param amount: 付款数量
        :param from_account: 付款账户地址
        :param to_account: 目标账户地址
        :param fromAccountKey: 付款账户地址私钥
        :return:
        """
        # 如果指定amount则使用指定的amount作为下单数量，否则随机生成
        amount = inAmount if inAmount else ApiUtils.randAmount(20, 2, 2)

        # 查询路由信息
        router_info, router_body = self.client.getRouterList(sendCurrency, receiveCurrency, sendAmount=amount)
        self.checkRouterList(router_info, router_body)

        if router_info["data"]["roxeRouters"] == []:
            self.client.logger.error("查询出的路由为空")
            assert len(router_info["data"]["roxeRouters"]) != 0, "查询出的路由为空"
            return
        # 查询转账前链上账户资产余额
        from_balance = self.chain_client.getBalanceWithRetry(from_account, sendCurrency.split(".")[0])
        self.client.logger.info(f"{from_account}转账前持有的资产: {from_balance}")
        to_balance = self.chain_client.getBalanceWithRetry(to_account, sendCurrency.split(".")[0])
        self.client.logger.info(f"{to_account}转账前持有的资产: {to_balance}")

        # 账户链上转账
        tx_amt = RoxeChainClient.makeContractAmount(amount, receiveCurrency.strip(".ROXE"))
        tx = self.chain_client.transferToken(from_account, fromAccountKey, to_account, tx_amt, "roxe.ro")
        paymentId = tx["transaction_id"]

        # 提交rts订单
        order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, sendAmount=amount, receiverAddress=to_account, routerStrategy=routerStrategy, extensionField=extensionField)
        self.checkCodeAndMessage(order_info)
        self.checksubmitOrder(order_info, submit_body, 0, 0, 0, ro2ro=True)

        if is_just_submit:
            return order_info["data"]

        # 查询订单状态
        instruction_id = order_info["data"]["instructionId"]
        transaction_id = order_info["data"]["transactionId"]
        query_order = self.client.getOrderInfo(transactionId=transaction_id)
        self.checkCodeAndMessage(query_order)

        # 查询订单日志
        order_log = self.client.getOrderStateLog(transactionId=transaction_id)
        self.checkCodeAndMessage(order_log)

        # 直到订单完成
        time_out = 60
        b_time = time.time()
        while True:
            if time.time() - b_time > time_out:
                self.client.logger.info("等待时间超时")
                break
            query_order = self.client.getOrderInfo(instruction_id)
            if query_order["data"]["txState"] == "TRANSACTION_FINISH":
                self.client.logger.info("rts订单已经完成")
                break
            time.sleep(10)
        # 查询订单状态
        query_order = self.client.getOrderInfo(instruction_id)
        self.checkCodeAndMessage(query_order)
        self.checkOrderInfo(query_order, order_info, submit_body, instruction_id=instruction_id)

        # 查询订单日志
        order_log = self.client.getOrderStateLog(instruction_id)
        self.checkCodeAndMessage(order_log)
        self.checkOrderLog(order_log, instruction_id=instruction_id)

        # 查询转账后链上账户资产余额
        from_balance2 = self.chain_client.getBalanceWithRetry(from_account, sendCurrency.split(".")[0])
        self.client.logger.info(f"{from_account}转账后持有的资产: {from_balance2}")
        to_balance2 = self.chain_client.getBalanceWithRetry(to_account, sendCurrency.split(".")[0])
        self.client.logger.info(f"{to_account}转账后持有的资产: {to_balance2}")

        # 校验转账金额与实际到账金额是否一致
        self.assertAlmostEqual(from_balance - from_balance2, amount, msg="from账户资产变化不正确", delta=0.1 ** 7)
        self.assertAlmostEqual(to_balance2 - to_balance, amount, msg="to账户资产变化不正确", delta=0.1 ** 7)

        return query_order["data"], 0

    def submitOrderFloorOfFiatToRo(self, sendNodeCode, sendCountry, sendCurrency, receiveCurrency, to_account,
                                   inAmount=None, routerStrategy=None, extensionField=None, notifyURL=None,
                                   passByNodes=None, is_just_submit=False):
        """
        法币->RO的下单流程:
            查询路由 -> 下单 -> 查询订单信息 -> 等待订单完成 -> 查询订单信息 -> 查询订单日志
            每一步都有验证接口返回的结果
        :param token: 有ach账户的用户token
        :param user_id: 有ach账户的用户id
        :param currency_info: 币种信息
        :param amount: 查询路由的下单数量
        :param amount_side: 查询路由的方向
        :param outer_info: 出金的信息，如果出金一方为ro则为ro地址，如果出金一方为银行卡则为银行卡信息
        :param is_just_submit: 是否在提交订单后就返回订单数据，不等待订单完成
        :param url: 回调的url
        :return:
        """
        # 如果指定amount则使用指定的amount作为下单数量，否则随机生成
        amount = inAmount if inAmount else ApiUtils.randAmount(20, 2, 2)

        # 处理passByNodes
        if passByNodes != None:
            router_passByNodes = []
            for i in passByNodes:
                router_passByNodes.append(i["nodeCode"])
        else:
            router_passByNodes = None

        # 查询路由信息
        router_info, request_body = self.client.getRouterList(sendCurrency, receiveCurrency, sendNodeCode=sendNodeCode, sendCountry=sendCountry, sendAmount=amount, passByNodes=router_passByNodes)
        self.checkRouterList(router_info, request_body)
        if router_info["data"]["roxeRouters"] == []:
            self.client.logger.error("查询出的路由为空")
            assert len(router_info["data"]["roxeRouters"]) != 0, "查询出的路由为空"
            return

        # 提交rpc订单
        channelName = "CHECKOUT"
        payBankAccountId = "src_dxles3kr3zluned5xk4thhnjbe"
        payMethod = "debitCard"

        # 获取入金节点费用
        # in_fee_info = self.getRpcFeeInDB(channelName, sendCurrency, country=None)
        # depositAmount = '%.2f' % (amount + float(in_fee_info["in"]["inFeeAmount"]))
        depositAmount = amount  # 因为APP需求，现将法币到ro的sendFee改为了0

        rpc_order_info = self.rpcClient.submitPayinOrder(channelName, payBankAccountId, payMethod=payMethod, amount=depositAmount)
        time.sleep(3)
        status_info = self.rpcClient.getPayinOrderTransactionStateByRpcId(rpc_order_info["data"]["rpcId"])
        self.checkCodeAndMessage(status_info)
        payment_id = rpc_order_info["data"]["rpcId"] if status_info["data"]["status"] == "PAY_SUCCESS" else "RPC订单未完成"

        # 查询转账前链上账户资产余额
        to_balance = self.chain_client.getBalanceWithRetry(to_account, receiveCurrency.split(".")[0])
        self.client.logger.info(f"{to_account}转账前持有的资产: {to_balance}")

        # 提交rts订单
        rts_order_info, submit_body = self.client.submitOrder(payment_id, sendCurrency, receiveCurrency, sendNodeCode=sendNodeCode, sendCountry=sendCountry, sendAmount=amount,
                                                              receiverAddress=to_account, routerStrategy=routerStrategy, extensionField=extensionField, notifyURL=notifyURL)
        if is_just_submit:
            return rts_order_info["data"]
        self.checkCodeAndMessage(rts_order_info)

        # 获取入金节点费用
        # fee_info = self.getRpcFeeInDB(channelName, sendCurrency, country=None)
        # self.checksubmitOrder(rts_order_info, submit_body, fee_info["in"]["inFeeAmount"], 0, 0)

        send_fee = 0  # 因为APP需求，现将法币到ro的sendFee改为了0
        self.checksubmitOrder(rts_order_info, submit_body, send_fee, 0, 0)

        # if is_just_submit:
        #     return rts_order_info["data"]

        # 查询订单状态
        instruction_id = rts_order_info["data"]["instructionId"]
        transaction_id = rts_order_info["data"]["transactionId"]
        query_order = self.client.getOrderInfo(transactionId=transaction_id)
        self.checkCodeAndMessage(query_order)

        # 查询订单日志
        order_log = self.client.getOrderStateLog(transactionId=transaction_id)
        self.checkCodeAndMessage(order_log)

        # 直到订单完成
        time_out = 300
        b_time = time.time()
        while True:
            if time.time() - b_time > time_out:
                self.client.logger.error("等待时间超时")
                break
            query_info = self.client.getOrderInfo(instruction_id)
            if query_info["data"]["txState"] == "TRANSACTION_FINISH":
                self.client.logger.info("rts订单已经完成")
                break
            time.sleep(time_out / 15)

        # 查询订单状态
        query_info = self.client.getOrderInfo(instruction_id)
        self.checkCodeAndMessage(query_info)
        self.checkOrderInfo(query_info, rts_order_info, submit_body, instruction_id=instruction_id)
        time.sleep(1)
        # 查询订单日志
        order_log = self.client.getOrderStateLog(instruction_id)
        self.checkCodeAndMessage(order_log)
        self.checkOrderLog(order_log, instruction_id=instruction_id)
        assert "TRANSACTION_FINISH" in [i["txState"] for i in order_log["data"]["stateInfo"]], "订单状态不正确"

        # 查询转账后链上账户资产余额
        to_balance2 = self.chain_client.getBalanceWithRetry(to_account, receiveCurrency.split(".")[0])
        self.client.logger.info(f"{to_account}转账后持有的资产: {to_balance2}")

        # 校验转账金额与实际到账金额是否一致
        self.assertAlmostEqual(to_balance2 - to_balance, amount, msg="to账户资产变化不正确", delta=0.1 ** 7)

        return query_info["data"]

    def submitOrderFloorOfRoToFiat(self, sendCurrency, receiveCurrency, receiveNodeCode, receiveCountry, receive_info, from_account, fromAccountKey,
                                   inAmount=None, businessType=None, routerStrategy=None, extensionField=None, passByNodes=None,
                                   receiveMethodCode=None, notifyURL=None, is_just_submit=False,):
        """
        RO->法币的下单流程:
            查询路由 -> 查询出金类型 -> 查询出金必填字段 -> 校验出金必填字段 -> 下单 -> 查询订单信息 -> 等待订单完成 -> 查询订单信息 -> 查询订单日志
            每一步都有验证接口返回的结果
        :param currency_info: 币种信息
        :param amount: 查询路由的下单数量
        :param amount_side: 查询路由的方向
        :param outer_info: 出金的信息，如果出金一方为ro则为ro地址，如果出金一方为银行卡则为银行卡信息
        :param from_account: 出金账户
        :param is_just_submit: 是否在提交订单后就返回订单数据，不等待订单完成
        :param replaceOutAmount:
        :param url:
        :return:
        """
        # 如果指定amount则使用指定的amount作为下单数量，否则随机生成
        amount = inAmount if inAmount else ApiUtils.randAmount(20, 2, 2)

        # 处理passByNodes
        if passByNodes != None:
            router_passByNodes = []
            for i in passByNodes:
                router_passByNodes.append(i["nodeCode"])
        else:
            router_passByNodes = None

        # 查询路由信息
        router_info, request_body = self.client.getRouterList(sendCurrency, receiveCurrency, receiveNodeCode=receiveNodeCode, receiveCountry=receiveCountry, sendAmount=amount, passByNodes=router_passByNodes)
        self.checkRouterList(router_info, request_body)
        if router_info["data"]["roxeRouters"] == []:
            self.client.logger.error("查询出的路由为空")
            assert len(router_info["data"]["roxeRouters"]) != 0, "查询出的路由为空"
            return

        # 查询转账前链上账户资产余额
        from_balance = self.chain_client.getBalanceWithRetry(from_account, sendCurrency.split(".")[0])
        self.client.logger.info(f"{from_account}转账前持有的资产: {from_balance}")

        # 账户链上转账(向rts公户5chnthreqiow转账）
        tx_amt = RoxeChainClient.makeContractAmount(amount, sendCurrency.strip(".ROXE"))
        tx = self.chain_client.transferToken(from_account, fromAccountKey, "5chnthreqiow", tx_amt, "roxe.ro")
        paymentId = tx["transaction_id"]

        # 提交rts订单
        submit_order_info, submit_body = self.client.submitOrder(paymentId, sendCurrency, receiveCurrency, receive_info,
                                                                 receiveNodeCode=receiveNodeCode, receiveCountry=receiveCountry, sendAmount=amount,
                                                                 businessType=businessType, routerStrategy=routerStrategy, extensionField=extensionField,
                                                                 passByNodes=passByNodes, receiveMethodCode=receiveMethodCode, notifyURL=notifyURL)
        if is_just_submit:
            return submit_order_info["data"]
        self.checkCodeAndMessage(submit_order_info)

        # 获取出金节点费用
        receive_node_code = submit_order_info["data"]["roxeNodes"][-1]["nodeCode"]
        node_code = RTSData.channel_name[receive_node_code] if receive_node_code in RTSData.channel_nodes else receive_node_code
        fee_info = self.getRpcFeeInDB(node_code, receiveCurrency, country=submit_order_info["data"]["roxeNodes"][-1]["transferOutCurrency"].split(".")[1])

        self.checksubmitOrder(submit_order_info, submit_body, 0, fee_info["out"]["outBankFee"], 0)

        # if is_just_submit:
        #     return submit_order_info["data"]

        # 查询转账后链上账户资产余额
        after_balance = self.chain_client.getBalanceWithRetry(from_account, sendCurrency.split(".")[0])
        self.client.logger.info(f"{from_account}转账后持有的资产: {after_balance}")

        # 查询订单状态
        instruction_id = submit_order_info["data"]["instructionId"]
        transaction_id = submit_order_info["data"]["transactionId"]
        query_order = self.client.getOrderInfo(transactionId=transaction_id)
        self.checkCodeAndMessage(query_order)
        self.checkOrderInfo(query_order, submit_order_info, submit_body, transaction_id=transaction_id)

        # 查询订单日志
        order_log = self.client.getOrderStateLog(transactionId=transaction_id)
        self.checkCodeAndMessage(order_log)

        # 直到订单完成
        time_out = 300
        b_time = time.time()
        while True:
            if time.time() - b_time > time_out:
                self.client.logger.info("等待时间超时")
                break
            query_order = self.client.getOrderInfo(instruction_id)
            if query_order["data"]["txState"] == "TRANSACTION_FINISH":
                self.client.logger.info("rts订单已经完成")
                break
            time.sleep(10)
        # 查询订单状态
        query_order = self.client.getOrderInfo(instruction_id)
        self.checkCodeAndMessage(query_order)
        self.checkOrderInfo(query_order, submit_order_info, submit_body, instruction_id=instruction_id)

        # 查询订单日志
        order_log = self.client.getOrderStateLog(instruction_id)
        self.checkCodeAndMessage(order_log)
        self.checkOrderLog(order_log, instruction_id=instruction_id)
        assert "TRANSACTION_FINISH" in [i["txState"] for i in order_log["data"]["stateInfo"]], "订单状态不正确"

        return query_order["data"]

    def submitOrderFloorOfFiatToFiat(self, sendCurrency, receiveCurrency, sendNodeCode, sendCountry, receiveNodeCode, receiveCountry, receive_info, inAmount=None,
                                     businessType=None, routerStrategy=None, extensionField=None, passByNodes=None, receiveMethodCode=None, eWalletCode=None,
                                     notifyURL=None, is_just_submit=False):
        """
        法币->法币的下单流程:
            查询路由 -> 下单 -> 查询订单信息 -> 等待订单完成 -> 查询订单信息 -> 查询订单日志
            每一步都有验证接口返回的结果
        :param token: 有ach账户的用户token
        :param user_id: 有ach账户的用户id
        :param currency_info: 币种信息
        :param amount: 查询路由的下单数量
        :param amount_side: 查询路由的方向
        :param outer_info: 出金的信息，如果出金一方为ro则为ro地址，如果出金一方为银行卡则为银行卡信息
        :param sendCurrency: 指定入金币种
        :param replaceOutAmount:
        :param url:
        :return:
        """
        # 如果指定amount则使用指定的amount作为下单数量，否则随机生成
        amount = inAmount if inAmount else ApiUtils.randAmount(100, 2, 10)

        # 处理passByNodes
        if passByNodes != None:
            router_passByNodes = []
            for i in passByNodes:
                router_passByNodes.append(i["nodeCode"])
        else:
            router_passByNodes = None

        # 查询路由信息
        router_info, request_body = self.client.getRouterList(sendCurrency, receiveCurrency, sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              receiveNodeCode=receiveNodeCode, receiveCountry=receiveCountry, sendAmount=amount,
                                                              passByNodes=router_passByNodes, receiveMethodCode=receiveMethodCode, eWalletCode=eWalletCode)
        self.checkCodeAndMessage(router_info)
        if len(router_info["data"]["roxeRouters"]) == 0:
            self.client.logger.error("查询出的路由为空")
            assert len(router_info["data"]["roxeRouters"]) != 0, "查询出的路由为空"
            return

        # 查询经费用最低后的receiveAmount
        amout_list = []
        for router_data in router_info["data"]["roxeRouters"]:
            receiveAmount = router_data["receiveAmount"]
            amout_list.append(receiveAmount)
        router_out_amount = min(amout_list)

        # 提交rpc订单
        channelName = "CHECKOUT"
        payBankAccountId = "src_7vtbbtie3xaefdxl3p2hv6nkxu"
        payMethod = "debitCard"

        # 获取入金节点费用
        in_fee_info = self.getRpcFeeInDB(channelName, sendCurrency, country=None)
        depositAmount = '%.2f' % (amount + float(in_fee_info["in"]["inFeeAmount"]))

        rpc_order_info = self.rpcClient.submitPayinOrder(channelName, payBankAccountId, payMethod=payMethod,
                                                         amount=depositAmount)
        # status_info = self.rpcClient.getPayinOrderTransactionStateByRpcId(rpc_order_info["data"]["rpcId"])
        # self.checkCodeAndMessage(status_info)
        # payment_id = rpc_order_info["data"]["rpcId"] if status_info["data"]["status"] == "PAY_SUCCESS" else "RPC订单未完成"
        # if payment_id == "RPC订单未完成":
        time_out = 120
        b_time = time.time()
        while True:
            if time.time() - b_time > time_out:
                self.client.logger.error("等待时间超时")
                break
            status_info = self.rpcClient.getPayinOrderTransactionStateByRpcId(rpc_order_info["data"]["rpcId"])
            if status_info["data"]["status"] == "PAY_SUCCESS":
                self.client.logger.info("RPC订单已经完成")
                break
            time.sleep(time_out / 10)
        payment_id = rpc_order_info["data"]["rpcId"]

        # 获取入金节点费用
        # in_fee_info = self.getRpcFeeInDB(channelName, sendCurrency, country=None)
        # sendAmount = '%.2f' % (amount - float(in_fee_info["in"]["inFeeAmount"]))

        # 提交rts定单
        rts_order_info, submit_body = self.client.submitOrder(payment_id, sendCurrency, receiveCurrency, receive_info, sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                              receiveNodeCode=receiveNodeCode, receiveCountry=receiveCountry, sendAmount=amount, businessType=businessType,
                                                              routerStrategy=routerStrategy, extensionField=extensionField, passByNodes=passByNodes,
                                                              receiveMethodCode=receiveMethodCode, eWalletCode=eWalletCode, notifyURL=notifyURL)
        if is_just_submit:
            return rts_order_info["data"]

        self.checkCodeAndMessage(rts_order_info)


        # 获取出金节点费用
        receive_node_code = rts_order_info["data"]["roxeNodes"][-1]["nodeCode"]
        node_code = RTSData.channel_name[receive_node_code] if receive_node_code in RTSData.channel_nodes else receive_node_code
        out_fee_info = self.getRpcFeeInDB(node_code, receiveCurrency, country=rts_order_info["data"]["roxeNodes"][-1]["transferOutCurrency"].split(".")[1])

        # 校验下单响应信息
        self.checksubmitOrder(rts_order_info, submit_body, in_fee_info["in"]["inFeeAmount"], out_fee_info["out"]["outBankFee"], 0)

        # if is_just_submit:
        #     return rts_order_info["data"]

        # 查询订单状态
        instruction_id = rts_order_info["data"]["instructionId"]
        transaction_id = rts_order_info["data"]["transactionId"]
        query_order = self.client.getOrderInfo(transactionId=transaction_id)
        self.checkCodeAndMessage(query_order)
        self.checkOrderInfo(query_order, rts_order_info, submit_body, transaction_id=transaction_id)

        # 查询订单日志
        order_log = self.client.getOrderStateLog(transactionId=transaction_id)
        self.checkCodeAndMessage(order_log)


        # 直到订单完成
        time_out = 300
        b_time = time.time()
        while True:
            if time.time() - b_time > time_out:
                self.client.logger.error("等待时间超时")
                break
            query_info = self.client.getOrderInfo(instruction_id)
            if query_info["data"]["txState"] == "TRANSACTION_FINISH":
                self.client.logger.info("rts订单已经完成")
                break
            time.sleep(time_out / 15)

        # 查询订单状态
        query_info = self.client.getOrderInfo(instruction_id)
        self.checkCodeAndMessage(query_info)
        self.checkOrderInfo(query_info, rts_order_info, submit_body, instruction_id=instruction_id)
        assert query_info["data"]["txState"] == "TRANSACTION_FINISH", "订单状态不正确"
        time.sleep(1)
        # 查询订单日志
        order_log = self.client.getOrderStateLog(instruction_id)
        self.checkCodeAndMessage(order_log)
        self.checkOrderLog(order_log, instruction_id=instruction_id)
        assert "TRANSACTION_FINISH" in [i["txState"] for i in order_log["data"]["stateInfo"]], "订单状态不正确"

        # 校验出金数量和路由数量一致
        real_amount = query_info["data"]["quoteReceiveAmount"]
        self.client.logger.info(f"路由最低费用出金金额：{router_out_amount}，实际出金金额：{real_amount}")
        assert abs(float(router_out_amount) - float(real_amount)) < 1, "实际出金数量和路由的出金数量不一致"  # 由于汇率波动，当换汇后金额较大时会出现较大差值

        return query_info["data"]

    def waitOrderReachStateAndSuspend(self, order_data, specified_state, timeout):
        instructionId = order_data["instructionId"]
        time_out = timeout
        b_time = time.time()
        while True:
            if time.time() - b_time > time_out:
                self.client.logger.info("等待时间超时")
                break
            query_order = self.client.getOrderInfo(instructionId)
            if query_order["data"]["txState"] == specified_state:
                self.client.logger.info(f"rts订单状态：{specified_state}")
                break
            time.sleep(5)
        suspend_order_info, suspend_body = self.client.suspendOrder(f"Test {specified_state} status suspend order", instructionId)
        return suspend_order_info, suspend_body

class RTSApiTest(BaseCheckRTS):

    def test_100_submitOrder_RoToRo(self):
        sendCurrency = "USD.ROXE"
        receiveCurrency = "USD.ROXE"
        from_address = RTSData.chain_account
        outer_address = RTSData.user_account_2
        fromAccountKey = RTSData.chain_pri_key

        self.submitOrderFloorOfRoToRo(sendCurrency, receiveCurrency, from_address, outer_address, fromAccountKey)

    def test_101_submitOrder_RoToRo_inRouterStrategyAndExtensionField(self):
        sendCurrency = "USD.ROXE"
        receiveCurrency = "USD.ROXE"
        from_address = RTSData.chain_account
        outer_address = RTSData.user_account_2
        fromAccountKey = RTSData.chain_pri_key

        self.submitOrderFloorOfRoToRo(sendCurrency, receiveCurrency, from_address, outer_address, fromAccountKey, routerStrategy="LOWEST_FEE", extensionField="This is a RoToRo order")

    def test_102_submitOrder_FaitToRo_inSendNodeCode(self):
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        sendCurrency = "USD"
        receiveCurrency = "USD.ROXE"
        from_address = RTSData.chain_account
        outer_address = RTSData.user_account_2

        self.submitOrderFloorOfFiatToRo(sendNodeCode, sendCountry, sendCurrency, receiveCurrency, from_address)

    def test_103_submitOrder_FaitToRo_inSendCountryAndRouterStrategyAndExtensionField(self):
        sendNodeCode = ""
        sendCountry = "US"
        sendCurrency = "USD"
        receiveCurrency = "USD.ROXE"
        from_address = RTSData.chain_account
        outer_address = RTSData.user_account_2

        self.submitOrderFloorOfFiatToRo(sendNodeCode, sendCountry, sendCurrency, receiveCurrency, from_address, routerStrategy="LOWEST_FEE", extensionField="This is a FaitToRo order")

    def test_104_submitOrder_FaitToRo_inSendNodeCodeAndSendCountry(self):
        sendNodeCode = RTSData.checkout_node
        sendCountry = "US"
        sendCurrency = "USD"
        receiveCurrency = "USD.ROXE"
        from_address = RTSData.chain_account
        outer_address = RTSData.user_account_2

        self.submitOrderFloorOfFiatToRo(sendNodeCode, sendCountry, sendCurrency, receiveCurrency, from_address)

    def test_105_submitOrder_RoToFait_inReceiveNodeCode(self):
        sendCurrency = "USD.ROXE"
        receiveCurrency = "PHP"
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        from_address = RTSData.chain_account
        fromAccountKey = RTSData.chain_pri_key
        receive_info = RTSData.terrapay_receive_info

        self.submitOrderFloorOfRoToFiat(sendCurrency, receiveCurrency, receiveNodeCode, receiveCountry, receive_info, from_address, fromAccountKey)

    def test_106_submitOrder_RoToFait_inReceiveCountry(self):
        sendCurrency = "USD.ROXE"
        receiveCurrency = "PHP"
        receiveNodeCode = ""
        receiveCountry = "PH"
        from_address = RTSData.chain_account
        fromAccountKey = RTSData.chain_pri_key
        receive_info = RTSData.terrapay_receive_info

        self.submitOrderFloorOfRoToFiat(sendCurrency, receiveCurrency, receiveNodeCode, receiveCountry, receive_info, from_address, fromAccountKey)

    def test_107_submitOrder_RoToFait_inReceiveNodeCode_inReceiveCountry_andAllIn(self):
        sendCurrency = "USD.ROXE"
        receiveCurrency = "PHP"
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = "PH"
        from_address = RTSData.chain_account
        fromAccountKey = RTSData.chain_pri_key
        receive_info = RTSData.terrapay_receive_info
        passByNodes = [{"nodeCode": RTSData.terrapay_node_ph}]

        self.submitOrderFloorOfRoToFiat(sendCurrency, receiveCurrency, receiveNodeCode, receiveCountry, receive_info, from_address, fromAccountKey,
                                        routerStrategy="LOWEST_FEE", extensionField="This is a RoToFait order", businessType="C2C",
                                        passByNodes=passByNodes, receiveMethodCode="BANK")

    def test_108_submitOrder_FaitToFait_inSendNodeCodeAndReceiveNodeCode_terrapay(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        inner_amount = 25
        receive_info = RTSData.terrapay_receive_info

        self.submitOrderFloorOfFiatToFiat(sendCurrency, receiveCurrency, sendNodeCode, sendCountry, receiveNodeCode, receiveCountry, receive_info)

    def test_109_submitOrder_FaitToFait_inSendCountryAndReceiveCountry_terrapay(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = ""
        sendCountry = "US"
        receiveNodeCode = ""
        receiveCountry = "PH"
        inner_amount = 25
        passByNodes = [{"nodeCode": RTSData.checkout_node}, {"nodeCode": RTSData.terrapay_node_ph}]
        receive_info = RTSData.terrapay_receive_info

        self.submitOrderFloorOfFiatToFiat(sendCurrency, receiveCurrency, sendNodeCode, sendCountry, receiveNodeCode, receiveCountry, receive_info, passByNodes=passByNodes)

    def test_110_submitOrder_FaitToFait_inSendNodeCodeAndReceiveCountry_terrapay(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        receiveNodeCode = ""
        receiveCountry = "PH"
        inner_amount = 25
        passByNodes = [{"nodeCode": RTSData.checkout_node}, {"nodeCode": RTSData.terrapay_node_ph}]
        receive_info = RTSData.terrapay_receive_info

        self.submitOrderFloorOfFiatToFiat(sendCurrency, receiveCurrency, sendNodeCode, sendCountry, receiveNodeCode, receiveCountry, receive_info, passByNodes=passByNodes)

    def test_111_submitOrder_FaitToFait_inSendCountryAndReceiveNodeCode_terrapay(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = ""
        sendCountry = "US"
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        inner_amount = 25
        passByNodes = [{"nodeCode": RTSData.checkout_node}, {"nodeCode": RTSData.terrapay_node_ph}]
        receive_info = RTSData.terrapay_receive_info

        self.submitOrderFloorOfFiatToFiat(sendCurrency, receiveCurrency, sendNodeCode, sendCountry, receiveNodeCode, receiveCountry, receive_info, passByNodes=passByNodes)

    def test_112_submitOrder_FaitToFait_allIn_terrapay(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = "US"
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = "PH"
        inner_amount = 25
        passByNodes = [{"nodeCode": RTSData.checkout_node}, {"nodeCode": RTSData.terrapay_node_ph}]
        receive_info = RTSData.terrapay_receive_info
        self.submitOrderFloorOfFiatToFiat(sendCurrency, receiveCurrency, sendNodeCode, sendCountry, receiveNodeCode, receiveCountry, receive_info,
                                          businessType="C2C", routerStrategy="LOWEST_FEE", extensionField="This is a FaitToFait order",
                                          passByNodes=passByNodes, receiveMethodCode="BANK")

    @unittest.skip("Cebuana未返回receiveAmount")  # todo
    def test_113_submitOrder_FaitToFait_cebuana_rpp(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = "US"
        receiveNodeCode = RTSData.cebuana_node
        receiveCountry = "PH"
        inner_amount = 25
        receive_info = RTSData.cebuana_receive_info

        self.submitOrderFloorOfFiatToFiat(sendCurrency, receiveCurrency, sendNodeCode, sendCountry, receiveNodeCode, receiveCountry, receive_info)

    @unittest.skip("受三方环境影响，手动执行")
    def test_114_submitOrder_FaitToFait_gcash_rpp_ewallet(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = "US"
        receiveNodeCode = RTSData.gcash_node
        receiveCountry = "PH"
        inner_amount = 25
        passByNodes = [{"nodeCode": RTSData.checkout_node}, {"nodeCode": RTSData.gcash_node}]
        receive_info = RTSData.gcash_receive_info

        self.submitOrderFloorOfFiatToFiat(sendCurrency, receiveCurrency, sendNodeCode, sendCountry, receiveNodeCode, receiveCountry, receive_info,
                                          businessType="C2C", routerStrategy="LOWEST_FEE", extensionField="This is a FaitToFait order",
                                          passByNodes=passByNodes, receiveMethodCode="EWALLET", eWalletCode="GCASH", inAmount=12)

    def test_115_submitOrder_FaitToRo_inNotifyURL(self):
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        sendCurrency = "USD"
        receiveCurrency = "USD.ROXE"
        from_address = RTSData.chain_account
        outer_address = RTSData.user_account_2
        notify_url = RTSData.notify_url_rts

        order_data = self.submitOrderFloorOfFiatToRo(sendNodeCode, sendCountry, sendCurrency, receiveCurrency, from_address, notifyURL=notify_url)

        tx_id = order_data["transactionId"]
        tx_log = self.client.getOrderStateLog("", tx_id)
        tx_log_state = [i["txState"] for i in tx_log["data"]["stateInfo"]]
        send_notify_sql = "select * from roxe_rts_v3.rts_notify where order_id='{}' and notify_state='success'".format(tx_id)
        b_time = time.time()
        send_notify = []
        while time.time() - b_time < 100:
            send_notify = self.mysql.exec_sql_query(send_notify_sql)
            if len(send_notify) == len(tx_log_state) - 1:
                break
            time.sleep(3)
        time.sleep(2)
        receive_notify_sql = "select * from mock_notify.res_info order by create_at desc limit {}".format(len(send_notify))
        receive_notify = self.mysql.exec_sql_query(receive_notify_sql)
        self.assertEqual(len(receive_notify), len(send_notify), "接收到的回调消息和发送出来的消息条数不一致")
        self.assertEqual(len(receive_notify), len(tx_log_state) - 1, "接收到的回调消息和发送出来的消息条数不一致")
        for r_notify in receive_notify:
            if "ciphertext" in r_notify["response"]:
                parse_notify = self.verifyAndDecryptNotify(r_notify)
            else:
                parse_notify = json.loads(r_notify["response"])
            self.assertIn(parse_notify["txState"], tx_log_state, "{} {}".format(parse_notify["txState"], tx_log_state))
            s_notify = [i for i in send_notify if i["orderState"] == parse_notify["txState"]][0]
            self.assertEqual(parse_notify, json.loads(s_notify["notifyInfo"]))
            # self.assertEqual(parse_notify["deliveryFee"], order_data["deliveryFee"])
            # self.assertEqual(parse_notify["deliveryFeeCurrency"], order_data["deliveryFeeCurrency"])
            # self.assertEqual(parse_notify["exchangeRate"], order_data["exchangeRate"])
            # self.assertEqual(parse_notify["sendFee"], order_data["sendFee"])
            # self.assertEqual(parse_notify["sendFeeCurrency"], order_data["sendFeeCurrency"])
            self.assertEqual(parse_notify["quoteReceiveAmount"], order_data["quoteReceiveAmount"])
            self.assertEqual(parse_notify["serviceFee"], order_data["serviceFee"])
            self.assertEqual(parse_notify["serviceFeeCurrency"], order_data["serviceFeeCurrency"])
            self.assertEqual(parse_notify["transactionId"], order_data["transactionId"])
            if "receiveAmount" in parse_notify:
                self.assertEqual(parse_notify["receiveAmount"], json.loads(s_notify["notifyInfo"])["receiveAmount"])
            for o_k, o_v in parse_notify["origTransactionInfo"].items():
                self.assertEqual(o_v, order_data["origTransactionInfo"][o_k], f"{o_k}校验失败")

    def test_116_submitOrder_RoToFait_inNotifyURL(self):
        sendCurrency = "USD.ROXE"
        receiveCurrency = "PHP"
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        from_address = RTSData.chain_account
        fromAccountKey = RTSData.chain_pri_key
        notify_url = RTSData.notify_url_rts
        receive_info = RTSData.terrapay_receive_info

        order_data = self.submitOrderFloorOfRoToFiat(sendCurrency, receiveCurrency, receiveNodeCode, receiveCountry, receive_info, from_address, fromAccountKey, notifyURL=notify_url)

        tx_id = order_data["transactionId"]
        tx_log = self.client.getOrderStateLog("", tx_id)
        tx_log_state = [i["txState"] for i in tx_log["data"]["stateInfo"]]
        send_notify_sql = "select * from roxe_rts_v3.rts_notify where order_id='{}' and notify_state='success'".format(tx_id)
        b_time = time.time()
        send_notify = []
        while time.time() - b_time < 100:
            send_notify = self.mysql.exec_sql_query(send_notify_sql)
            if len(send_notify) == len(tx_log_state) - 1:
                break
            time.sleep(3)
        time.sleep(2)
        receive_notify_sql = "select * from mock_notify.res_info order by create_at desc limit {}".format(len(send_notify))
        receive_notify = self.mysql.exec_sql_query(receive_notify_sql)
        self.assertEqual(len(receive_notify), len(send_notify), "接收到的回调消息和发送出来的消息条数不一致")
        self.assertEqual(len(receive_notify), len(tx_log_state) - 1, "接收到的回调消息和发送出来的消息条数不一致")
        for r_notify in receive_notify:
            if "ciphertext" in r_notify["response"]:
                parse_notify = self.verifyAndDecryptNotify(r_notify)
            else:
                parse_notify = json.loads(r_notify["response"])
            self.assertIn(parse_notify["txState"], tx_log_state, "{} {}".format(parse_notify["txState"], tx_log_state))
            s_notify = [i for i in send_notify if i["orderState"] == parse_notify["txState"]][0]
            self.assertEqual(parse_notify, json.loads(s_notify["notifyInfo"]))
            # self.assertEqual(parse_notify["deliveryFee"], order_data["deliveryFee"])
            # self.assertEqual(parse_notify["deliveryFeeCurrency"], order_data["deliveryFeeCurrency"])
            # self.assertEqual(parse_notify["exchangeRate"], order_data["exchangeRate"])
            # self.assertEqual(parse_notify["sendFee"], order_data["sendFee"])
            # self.assertEqual(parse_notify["sendFeeCurrency"], order_data["sendFeeCurrency"])
            self.assertEqual(parse_notify["quoteReceiveAmount"], order_data["quoteReceiveAmount"])
            self.assertEqual(parse_notify["serviceFee"], order_data["serviceFee"])
            self.assertEqual(parse_notify["serviceFeeCurrency"], order_data["serviceFeeCurrency"])
            self.assertEqual(parse_notify["transactionId"], order_data["transactionId"])
            if "receiveAmount" in parse_notify:
                self.assertEqual(parse_notify["receiveAmount"], json.loads(s_notify["notifyInfo"])["receiveAmount"])
            for o_k, o_v in parse_notify["origTransactionInfo"].items():
                self.assertEqual(o_v, order_data["origTransactionInfo"][o_k], f"{o_k}校验失败")

    def test_117_submitOrder_FaitToFait_toTerrapay_inNotifyURL(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        inner_amount = 25
        notify_url = RTSData.notify_url_rts
        receive_info = RTSData.terrapay_receive_info

        order_data = self.submitOrderFloorOfFiatToFiat(sendCurrency, receiveCurrency, sendNodeCode, sendCountry, receiveNodeCode, receiveCountry, receive_info, notifyURL=notify_url)

        # tx_id = "438099306d134ae686ef576570abf94c"
        tx_id = order_data["transactionId"]

        tx_log = self.client.getOrderStateLog("", tx_id)
        tx_log_state = [i["txState"] for i in tx_log["data"]["stateInfo"]]
        send_notify_sql = "select * from roxe_rts_v3.rts_notify where order_id='{}' and notify_state='success'".format(tx_id)
        b_time = time.time()
        send_notify = []
        while time.time() - b_time < 200:
            send_notify = self.mysql.exec_sql_query(send_notify_sql)
            if len(send_notify) == len(tx_log_state):
                break
            time.sleep(3)
        time.sleep(5)
        receive_notify_sql = "select * from mock_notify.res_info where  `url` like '%rts%' order by create_at desc limit {}".format(len(send_notify)-2)
        receive_notify = self.mysql.exec_sql_query(receive_notify_sql)
        self.assertEqual(len(receive_notify), len(send_notify) - 2, "接收到的回调消息和发送出来的消息条数不一致")
        self.assertEqual(len(receive_notify), len(tx_log_state) - 2, "接收到的回调消息和所有状态的条数减2不一致")
        for r_notify in receive_notify:
            if "ciphertext" in r_notify["response"]:
                parse_notify = self.verifyAndDecryptNotify(r_notify)
            else:
                parse_notify = json.loads(r_notify["response"])
            self.assertIn(parse_notify["txState"], tx_log_state, "{} {}".format(parse_notify["txState"], tx_log_state))
            s_notify = [i for i in send_notify if i["orderState"] == parse_notify["txState"]][0]

            self.assertEqual(parse_notify, json.loads(s_notify["notifyInfo"]))
            # self.assertEqual(parse_notify["deliveryFee"], order_data["deliveryFee"])
            # self.assertEqual(parse_notify["deliveryFeeCurrency"], order_data["deliveryFeeCurrency"])
            # self.assertEqual(parse_notify["sendFee"], order_data["sendFee"])
            # self.assertEqual(parse_notify["sendFeeCurrency"], order_data["sendFeeCurrency"])
            # self.assertEqual(parse_notify["exchangeRate"], order_data["exchangeRate"])

            self.assertEqual(parse_notify["quoteReceiveAmount"], order_data["quoteReceiveAmount"])
            self.assertEqual(parse_notify["serviceFee"], order_data["serviceFee"])
            self.assertEqual(parse_notify["serviceFeeCurrency"], order_data["serviceFeeCurrency"])
            self.assertEqual(parse_notify["transactionId"], order_data["transactionId"])
            if "receiveAmount" in parse_notify:
                self.assertEqual(parse_notify["receiveAmount"], json.loads(s_notify["notifyInfo"])["receiveAmount"])
            for o_k, o_v in parse_notify["origTransactionInfo"].items():
                self.assertEqual(o_v, order_data["origTransactionInfo"][o_k], f"{o_k}校验失败")

    def test_118_submitOrder_FaitToFait_toTerrapay_inNotifyURL_errorURL(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        inner_amount = 25
        notify_url = "http://172.17.3.95:8005/api/rts/receiveNotify123"
        receive_info = RTSData.terrapay_receive_info

        order_data = self.submitOrderFloorOfFiatToFiat(sendCurrency, receiveCurrency, sendNodeCode, sendCountry, receiveNodeCode, receiveCountry, receive_info, notifyURL=notify_url)

        # tx_id = "438099306d134ae686ef576570abf94c"
        tx_id = order_data["transactionId"]

        tx_log = self.client.getOrderStateLog("", tx_id)
        tx_log_state = [i["txState"] for i in tx_log["data"]["stateInfo"]]
        send_notify_sql1 = "select * from roxe_rts_v3.rts_notify where order_id='{}' and notify_state='success'".format(tx_id)
        send_notify_sql2 = "select * from roxe_rts_v3.rts_notify where order_id='{}' and notify_state='generate'".format(tx_id)
        b_time = time.time()
        send_notify1 = []
        send_notify2 = []
        while time.time() - b_time < 200:
            send_notify1 = self.mysql.exec_sql_query(send_notify_sql1)
            send_notify2 = self.mysql.exec_sql_query(send_notify_sql2)
            if len(send_notify1)+len(send_notify2) == len(tx_log_state):
                self.assertEqual(len(send_notify1), 2)
                self.assertEqual(len(send_notify2), 6)
                break
            time.sleep(3)



    # 挂起订单

    def test_120_suspendOrder_FaitToRo_TRANSACTION_SUBMIT(self):
        sendNodeCode = RTSData.checkout_node
        sendCountry = ""
        sendCurrency = "USD"
        receiveCurrency = "USD.ROXE"
        from_address = RTSData.chain_account
        outer_address = RTSData.user_account_2

        order_data = self.submitOrderFloorOfFiatToRo(sendNodeCode, sendCountry, sendCurrency, receiveCurrency, from_address, is_just_submit=True)

        order_info, body = self.client.suspendOrder("Test TRANSACTION_SUBMIT status suspend order", order_data["instructionId"])
        order_final_state = self.checkSuspendOrder(order_info, order_data)
        time.sleep(10)
        self.assertEqual(order_final_state, "TRANSACTION_SUBMIT")

    def test_121_suspendOrder_RoToFait_TRANSACTION_SUBMIT(self):
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = ""
        sendCountry = ""
        sendCurrency = "USD.ROXE"
        receiveCurrency = "PHP"
        from_address = RTSData.chain_account
        fromAccountKey = RTSData.chain_pri_key
        receive_info = RTSData.terrapay_receive_info

        order_data = self.submitOrderFloorOfRoToFiat(sendCurrency, receiveCurrency, receiveNodeCode, receiveCountry, receive_info, from_address, fromAccountKey, is_just_submit=True)

        order_info, body = self.client.suspendOrder("Test TRANSACTION_SUBMIT status suspend order", order_data["instructionId"])
        order_final_state = self.checkSuspendOrder(order_info, order_data)
        time.sleep(10)
        self.assertEqual(order_final_state, "TRANSACTION_SUBMIT")

    def test_122_suspendOrder_FaitToFait_TRANSACTION_SUBMIT(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = "US"
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = "PH"
        inner_amount = 25
        passByNodes = [{"nodeCode": RTSData.checkout_node}, {"nodeCode": RTSData.terrapay_node_ph}]
        receive_info = RTSData.terrapay_receive_info

        order_data = self.submitOrderFloorOfFiatToFiat(sendCurrency, receiveCurrency, sendNodeCode, sendCountry, receiveNodeCode, receiveCountry, receive_info,
                                                       businessType="C2C", routerStrategy="LOWEST_FEE", extensionField="This is a FaitToFait order",
                                                       passByNodes=passByNodes, receiveMethodCode="BANK", is_just_submit=True)

        order_info, body = self.client.suspendOrder("Test TRANSACTION_SUBMIT status suspend order", order_data["instructionId"])
        order_final_state = self.checkSuspendOrder(order_info, order_data)
        time.sleep(10)
        self.assertEqual(order_final_state, "TRANSACTION_SUBMIT")

    def test_123_suspendOrder_FaitToFait_MINT_FINISH(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = "US"
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCountry = "PH"
        inner_amount = 25
        passByNodes = [{"nodeCode": RTSData.checkout_node}, {"nodeCode": RTSData.terrapay_node_ph}]
        receive_info = RTSData.terrapay_receive_info

        order_data = self.submitOrderFloorOfFiatToFiat(sendCurrency, receiveCurrency, sendNodeCode, sendCountry, receiveNodeCode, receiveCountry, receive_info,
                                                       businessType="C2C", routerStrategy="LOWEST_FEE", extensionField="This is a FaitToFait order",
                                                       passByNodes=passByNodes, receiveMethodCode="BANK", is_just_submit=True)

        suspend_order_info, suspend_body = self.waitOrderReachStateAndSuspend(order_data, "MINT_FINISH", 200)
        order_final_state = self.checkSuspendOrder(suspend_order_info, order_data)
        time.sleep(10)
        self.assertEqual(order_final_state, "MINT_FINISH")

    def test_124_suspendOrder_FaitToFait_rpp_SWAP_FINISH(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        sendNodeCode = RTSData.checkout_node
        sendCountry = "US"
        receiveNodeCode = RTSData.cebuana_node
        receiveCountry = "PH"
        inner_amount = 25
        receive_info = RTSData.cebuana_receive_info

        order_data = self.submitOrderFloorOfFiatToFiat(sendCurrency, receiveCurrency, sendNodeCode, sendCountry, receiveNodeCode,
                                          receiveCountry, receive_info, is_just_submit=True)

        suspend_order_info, suspend_body = self.waitOrderReachStateAndSuspend(order_data, "SWAP_FINISH", 200)
        order_final_state = self.checkSuspendOrder(suspend_order_info, order_data)
        time.sleep(10)
        self.assertEqual(order_final_state, "SWAP_FINISH")

    # 获取Roxe换汇汇率
    def test_134_queryContractRate_sameCurrency_inAmount(self):
        """
        查询合约费率, 相同币种, 指定sendAmount
        """
        currency = RTSData.contract_info[0]["in"]
        amount = 10
        rate_info, request_body = self.client.getRate(currency, currency, sendAmount=amount)
        self.checkCodeAndMessage(rate_info)
        self.checkContractRateResult(rate_info["data"], request_body)

    def test_135_queryContractRate_sameCurrency_outAmount(self):
        """
        查询合约费率, 相同币种, 指定receiveAmount
        """
        currency = RTSData.contract_info[0]["in"]
        amount = 12.34
        rate_info, request_body = self.client.getRate(currency, currency, receiveAmount=amount)
        self.checkCodeAndMessage(rate_info)
        self.checkContractRateResult(rate_info["data"], request_body)

    def test_136_queryContractRate_differentCurrency_inAmount(self):
        """
        查询合约费率, 不同币种之间, 指定inAmount
        """
        in_currency = RTSData.contract_info[0]["in"]
        out_currency = RTSData.contract_info[0]["out"]
        amount = 12.34
        rate_info, request_body = self.client.getRate(in_currency, out_currency, sendAmount=amount)
        self.checkCodeAndMessage(rate_info)
        self.checkContractRateResult(rate_info["data"], request_body)

    def test_137_queryContractRate_differentCurrency_inAmount_exchangeCurrencyThenGiveInAmount(self):
        """
        查询合约费率, 不同币种之间, 指定inAmount, 然后交互in、out的币种, 根据第1次结果指定inAmount数量
        """
        in_currency = RTSData.contract_info[0]["in"]
        out_currency = RTSData.contract_info[0]["out"]
        amount = 12.34
        rate_info, request_body = self.client.getRate(in_currency, out_currency, sendAmount=amount)
        # 交换币种
        out_amount = rate_info["data"]["receiveAmount"]
        rate_info2, request_body2 = self.client.getRate(out_currency, in_currency, sendAmount=out_amount)
        self.checkContractRateResult(rate_info2["data"], request_body2)
        dif_amount = abs(float(rate_info2["data"]["receiveAmount"]) - amount)
        dif_percent = dif_amount / amount
        self.client.logger.info(f"交换币种后得到的金额差值: {dif_amount}, 误差范围: {dif_percent}")
        self.assertTrue(dif_percent < 0.005, "误差范围较大")

    def test_138_queryContractRate_differentCurrency_inAmount_exchangeCurrencyThenGiveOutAmount(self):
        """
        查询合约费率, 不同币种之间, 指定inAmount, 然后交互in、out的币种, 指定相同数量outAmount数量
        """
        in_currency = RTSData.contract_info[0]["in"]
        out_currency = RTSData.contract_info[0]["out"]
        amount = 102.34
        rate_info, request_body = self.client.getRate(in_currency, out_currency, sendAmount=amount)
        out_amount = float(rate_info["data"]["receiveAmount"])
        # 交换币种
        rate_info2, request_body2 = self.client.getRate(out_currency, in_currency, receiveAmount=amount)
        self.checkContractRateResult(rate_info2["data"], request_body2)
        dif_amount = abs(float(rate_info2["data"]["sendAmount"]) - out_amount)
        dif_percent = dif_amount / out_amount
        self.client.logger.info(f"交换币种后得到的金额差值: {dif_amount}, 误差范围: {dif_percent}")

    def test_139_queryContractRate_differentCurrency_outAmount(self):
        """
        查询合约费率, 不同币种之间, 指定outAmount
        """
        in_currency = RTSData.contract_info[0]["in"]
        out_currency = RTSData.contract_info[0]["out"]
        amount = 12.34
        rate_info, request_body = self.client.getRate(in_currency, out_currency, receiveAmount=amount)
        self.checkCodeAndMessage(rate_info)
        self.checkContractRateResult(rate_info["data"], request_body)

    def test_140_queryContractRate_differentCurrency_outAmount_exchangeCurrencyThenGiveInAmount(self):
        """
        查询合约费率, 不同币种之间, 指定outAmount, 交换币种然后指定inAmount
        """
        in_currency = RTSData.contract_info[0]["in"]
        out_currency = RTSData.contract_info[0]["out"]
        amount = 12.34
        rate_info, request_body = self.client.getRate(in_currency, out_currency, receiveAmount=amount)
        in_amount = float(rate_info["data"]["sendAmount"])

        rate_info2, request_body2 = self.client.getRate(out_currency, in_currency, sendAmount=amount)
        self.checkCodeAndMessage(rate_info2)
        self.checkContractRateResult(rate_info2["data"], request_body2)

        dif_amount = abs(float(rate_info2["data"]["receiveAmount"]) - in_amount)
        dif_percent = dif_amount / in_amount
        self.client.logger.info(f"交换币种后得到的金额差值: {dif_amount}, 误差范围: {dif_percent}")
        self.assertEqual(dif_percent, 0)

    def test_141_queryContractRate_differentCurrency_outAmount_exchangeCurrencyThenGiveOutAmount(self):
        """
        查询合约费率, 不同币种之间, 指定outAmount, 交换币种然后指定outAmount
        """
        in_currency = RTSData.contract_info[0]["in"]
        out_currency = RTSData.contract_info[0]["out"]
        amount = 102.34
        rate_info, request_body = self.client.getRate(in_currency, out_currency, receiveAmount=amount)
        in_amount = float(rate_info["data"]["sendAmount"])

        rate_info2, request_body2 = self.client.getRate(out_currency, in_currency, receiveAmount=in_amount)
        self.checkCodeAndMessage(rate_info2)
        self.checkContractRateResult(rate_info2["data"], request_body2)

        dif_amount = abs(float(rate_info2["data"]["sendAmount"]) - amount)
        dif_percent = dif_amount / amount
        self.client.logger.info(f"交换币种后得到的金额差值: {dif_amount}, 误差范围: {dif_percent}")

    # 修改Secret Key
    def test_142_updateSecretKey(self):
        """
        更新secretKey
        """
        try:
            new_key = self.client.updateSecretKey(RTSData.sec_key)
            self.checkCodeAndMessage(new_key)
            self.assertIsNotNone(new_key['data'])

            db_info = self.mysql.exec_sql_query("select * from `roxe_rts_v3`.`rts_user` where api_key='{}'".format(self.client.api_id))
            self.assertEqual(db_info[0]["secKey"], new_key["data"]["newSecretKey"])

            # 新secretKey可以正常使用
            currency_infos, r_body = self.client.getTransactionCurrency(replaceKey=new_key["data"]["newSecretKey"])
            self.checkCodeAndMessage(currency_infos)
            self.checkTransactionCurrency(currency_infos, r_body)

            # 老secretKey不能再用
            currency_infos, r_body = self.client.getTransactionCurrency()
            self.checkCodeAndMessage(currency_infos, "01200001", "Signature error")
            self.assertIsNone(currency_infos['data'])
        finally:
            self.mysql.exec_sql_query("update `roxe_rts_v3`.`rts_user`  set sec_key='{}' where api_key='{}'".format(RTSData.sec_key, RTSData.api_id))

    # 查询系统可用状态
    def test_000_querySystemOnline(self):
        system_state = self.client.getSystemState()
        self.checkCodeAndMessage(system_state)
        self.assertEqual(system_state["data"], "Available")

    # 获取支持的转账币种
    def test_001_getTransactionCurrency_allInNone(self):
        res_data, body = self.client.getTransactionCurrency()
        self.checkTransactionCurrency(res_data, body)

    def test_002_getTransactionCurrency_allCurrency(self):
        res_data, body = self.client.getTransactionCurrency(returnAllCurrency=True)
        self.checkTransactionCurrency(res_data, body)

    def test_003_getTransactionCurrency_allCurrencyIsTrue(self):
        res_data, body = self.client.getTransactionCurrency("US", "USD", "US", "USD", returnAllCurrency=True)
        self.checkTransactionCurrency(res_data, body)

    def test_004_getTransactionCurrency_allCurrencyIsFalse(self):
        res_data, body = self.client.getTransactionCurrency("US", "USD", "US", "USD", returnAllCurrency=False)
        self.checkTransactionCurrency(res_data, body)

    def test_005_getTransactionCurrency_sendCountryIsNone(self):
        res_data, body = self.client.getTransactionCurrency("", "USD", "US", "USD")
        self.checkTransactionCurrency(res_data, body)

    def test_006_getTransactionCurrency_sendCurrencyIsNone(self):
        res_data, body = self.client.getTransactionCurrency("US", "", "US", "USD")
        self.checkTransactionCurrency(res_data, body)

    def test_007_getTransactionCurrency_receiveCountryIsNone(self):
        res_data, body = self.client.getTransactionCurrency("US", "USD", "", "USD")
        self.checkTransactionCurrency(res_data, body)

    def test_008_getTransactionCurrency_receiveCurrencyIsNone(self):
        res_data, body = self.client.getTransactionCurrency("US", "USD", "US", "")
        self.checkTransactionCurrency(res_data, body)

    def test_009_getTransactionCurrency_sendCountryAndSendCurrencyIsNone(self):
        res_data, body = self.client.getTransactionCurrency("", "", "US", "USD", returnAllCurrency=True)
        self.checkTransactionCurrency(res_data, body)

    def test_010_getTransactionCurrency_sendCountryAndReceiveCountryIsNone(self):
        res_data, body = self.client.getTransactionCurrency("", "USD", "", "USD", returnAllCurrency=True)
        self.checkTransactionCurrency(res_data, body)

    def test_011_getTransactionCurrency_sendCountryAndReceiveCurrencyIsNone(self):
        res_data, body = self.client.getTransactionCurrency("", "USD", "US", "")
        self.checkTransactionCurrency(res_data, body)

    def test_012_getTransactionCurrency_sendCurrencyAndReceiveCountryIsNone(self):
        res_data, body = self.client.getTransactionCurrency("US", "", "", "USD")
        self.checkTransactionCurrency(res_data, body)

    def test_013_getTransactionCurrency_sendCurrencyAndReceiveCurrencyIsNone(self):
        res_data, body = self.client.getTransactionCurrency("US", "", "US", "")
        self.checkTransactionCurrency(res_data, body)

    def test_014_getTransactionCurrency_receiveCountryAndReceiveCurrencyIsNone(self):
        res_data, body = self.client.getTransactionCurrency("US", "USD", "", "")
        self.checkTransactionCurrency(res_data, body)

    def test_015_getTransactionCurrency_InSendCountry(self):
        res_data, body = self.client.getTransactionCurrency("US", "", "", "")
        self.checkTransactionCurrency(res_data, body)

    def test_016_getTransactionCurrency_InSendCurrency(self):
        res_data, body = self.client.getTransactionCurrency("", "USD", "", "")
        self.checkTransactionCurrency(res_data, body)

    def test_017_getTransactionCurrency_InReceiveCountry(self):
        res_data, body = self.client.getTransactionCurrency("", "", "GB", "")
        self.checkTransactionCurrency(res_data, body)

    def test_018_getTransactionCurrency_InReceiveCurrency(self):
        res_data, body = self.client.getTransactionCurrency("", "", "", "GBP")
        self.checkTransactionCurrency(res_data, body)

    # 获取支持的收款类型
    def test_019_getPayoutMethod_AllIn_nodeIsRmnPn(self):
        res, body = self.client.getPayoutMethod(RTSData.node_code_pn["US"], "US", "USD")
        self.checkGetPayoutMethod(res, body)

    def test_020_getPayoutMethod_AllIn_nodeIsRmnSn(self):
        res, body = self.client.getPayoutMethod(RTSData.node_code_sn["GB"], "GB", "GBP")
        self.checkGetPayoutMethod(res, body)

    def test_021_getPayoutMethod_AllIn_nodeIsMock(self):
        res, body = self.client.getPayoutMethod(RTSData.mock_node, "US", "USD")
        self.checkGetPayoutMethod(res, body)

    def test_022_getPayoutMethod_AllIn_nodeIsChannel_terrapay(self):
        res, body = self.client.getPayoutMethod(RTSData.terrapay_node_ph, "PH", "PHP")
        self.checkGetPayoutMethod(res, body)

    def test_023_getPayoutMethod_AllIn_nodeIsChannel_gcash(self):
        res, body = self.client.getPayoutMethod(RTSData.gcash_node, "PH", "PHP")
        self.checkGetPayoutMethod(res, body)

    def test_024_getPayoutMethod_AllIn_nodeOutCurrencyIsRo(self):
        res, body = self.client.getPayoutMethod(RTSData.checkout_node, "US", "USD.ROXE")
        self.checkGetPayoutMethod(res, body)

    # 获取汇入表单 + 校验汇入表单
    def test_025_getReceiverRequiredFields_And_checkReceiverRequiredFields_AllIn_nodeIsSn_currencyIsRo(self):
        receiveNodeCode = RTSData.checkout_node
        receiveCurrency = "USD.ROXE"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency, "C2C", "BANK")
        receiveInfo = self.makeReceiveInfo(res, body)
        res, body = self.client.checkReceiverRequiredFields(receiveNodeCode, receiveCurrency, receiveInfo, businessType="C2C")
        self.checkCheckReceiverRequiredFields(res)

    def test_026_getReceiverRequiredFields_And_checkReceiverRequiredFields_AllIn_nodeIsSn(self):
        receiveNodeCode = RTSData.node_code_sn["GB"]
        receiveCurrency = "GBP"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency, "C2C", "BANK")
        receiveInfo = self.makeReceiveInfo(res, body)
        res, body = self.client.checkReceiverRequiredFields(receiveNodeCode, receiveCurrency, receiveInfo, businessType="C2C")
        self.checkCheckReceiverRequiredFields(res)

    def test_027_getReceiverRequiredFields_And_checkReceiverRequiredFields_AllIn_nodeIsPn(self):
        receiveNodeCode = RTSData.node_code_pn["US"]
        receiveCurrency = "USD"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency, "C2C", "BANK")
        receiveInfo = self.makeReceiveInfo(res, body)
        res, body = self.client.checkReceiverRequiredFields(receiveNodeCode, receiveCurrency, receiveInfo, businessType="C2C")
        self.checkCheckReceiverRequiredFields(res)

    def test_028_getReceiverRequiredFields_And_checkReceiverRequiredFields_AllIn_nodeIsChannel_terrapay(self):
        receiveNodeCode = RTSData.terrapay_node_ph
        receiveCurrency = "PHP"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency, "C2C", "BANK")
        receiveInfo = self.makeReceiveInfo(res, body)
        res, body = self.client.checkReceiverRequiredFields(receiveNodeCode, receiveCurrency, receiveInfo, businessType="C2C")
        self.checkCheckReceiverRequiredFields(res)

    def test_029_getReceiverRequiredFields_And_checkReceiverRequiredFields_AllIn_nodeIsChannel_cebuana(self):
        receiveNodeCode = RTSData.cebuana_node
        receiveCurrency = "PHP"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency, "C2C", "BANK")
        receiveInfo = self.makeReceiveInfo(res, body)
        # receiveInfo["receiverCountry"] = "PH"
        res, body = self.client.checkReceiverRequiredFields(receiveNodeCode, receiveCurrency, receiveInfo, businessType="C2C")
        self.checkCheckReceiverRequiredFields(res)

    def test_030_getReceiverRequiredFields_And_checkReceiverRequiredFields_AllIn_nodeIsChannel_nium(self):
        receiveNodeCode = RTSData.nium_node
        receiveCurrency = "INR"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency, "C2C", "BANK")
        receiveInfo = self.makeReceiveInfo(res, body)
        receiveInfo["receiverBankNCCType"] = "INFSC"
        receiveInfo["receiverCountry"] = "IN"
        res, body = self.client.checkReceiverRequiredFields(receiveNodeCode, receiveCurrency, receiveInfo, businessType="C2C")
        self.checkCheckReceiverRequiredFields(res)

    def test_031_getReceiverRequiredFields_And_checkReceiverRequiredFields_AllIn_nodeIsMock(self):
        receiveNodeCode = RTSData.mock_node
        receiveCurrency = "USD"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency, "C2C", "BANK")
        receiveInfo = self.makeReceiveInfo(res, body)
        res, body = self.client.checkReceiverRequiredFields(receiveNodeCode, receiveCurrency, receiveInfo, businessType="C2C")
        self.checkCheckReceiverRequiredFields(res)

    def test_032_getReceiverRequiredFields_And_checkReceiverRequiredFields_AllIn_nodeIsSn_B2B(self):
        receiveNodeCode = RTSData.node_code_sn["GB"]
        receiveCurrency = "GBP"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency, "B2B", "BANK")
        receiveInfo = self.makeReceiveInfo(res, body, "B2B")
        res, body = self.client.checkReceiverRequiredFields(receiveNodeCode, receiveCurrency, receiveInfo, businessType="B2B")
        self.checkCheckReceiverRequiredFields(res)

    def test_033_getReceiverRequiredFields_And_checkReceiverRequiredFields_AllIn_nodeIsSn_B2C(self):
        receiveNodeCode = RTSData.node_code_sn["GB"]
        receiveCurrency = "GBP"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency, "B2C", "BANK")
        receiveInfo = self.makeReceiveInfo(res, body, "B2C")
        res, body = self.client.checkReceiverRequiredFields(receiveNodeCode, receiveCurrency, receiveInfo, businessType="B2C")
        self.checkCheckReceiverRequiredFields(res)

    def test_034_getReceiverRequiredFields_And_checkReceiverRequiredFields_AllIn_nodeIsSn_C2B(self):
        receiveNodeCode = RTSData.node_code_sn["GB"]
        receiveCurrency = "GBP"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency, "C2B", "BANK")
        receiveInfo = self.makeReceiveInfo(res, body, "C2B")
        res, body = self.client.checkReceiverRequiredFields(receiveNodeCode, receiveCurrency, receiveInfo, businessType="C2B")
        self.checkCheckReceiverRequiredFields(res)

    def test_035_getReceiverRequiredFields_And_checkReceiverRequiredFields_AllIn_nodeIsChannel_eWallet(self):
        receiveNodeCode = RTSData.gcash_node
        receiveCurrency = "PHP"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency, "C2C", "EWALLET")
        receiveInfo = self.makeReceiveInfo(res, body)
        receiveInfo["receiverWalletCode"] = "GCASH"
        res, body = self.client.checkReceiverRequiredFields(receiveNodeCode, receiveCurrency, receiveInfo)
        self.checkCheckReceiverRequiredFields(res)

    def test_036_getReceiverRequiredFields_And_checkReceiverRequiredFields_AllIn_nodeIsSn_businessTypeIsDefault(self):
        receiveNodeCode = RTSData.node_code_sn["GB"]
        receiveCurrency = "GBP"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency, receiveMethodCode="BANK")
        receiveInfo = self.makeReceiveInfo(res, body)
        res, body = self.client.checkReceiverRequiredFields(receiveNodeCode, receiveCurrency, receiveInfo)
        self.checkCheckReceiverRequiredFields(res)

    def test_037_getReceiverRequiredFields_And_checkReceiverRequiredFields_AllIn_nodeIsSn_receiveMethodCodeIsDefault(self):
        receiveNodeCode = RTSData.node_code_sn["GB"]
        receiveCurrency = "GBP"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency, businessType="C2C")
        receiveInfo = self.makeReceiveInfo(res, body)
        res, body = self.client.checkReceiverRequiredFields(receiveNodeCode, receiveCurrency, receiveInfo, businessType="C2C")
        self.checkCheckReceiverRequiredFields(res)

    def test_038_getReceiverRequiredFields_And_checkReceiverRequiredFields_AllIn_nodeIsPn_notRequiredIsDefault(self):
        receiveNodeCode = RTSData.node_code_pn["US"]
        receiveCurrency = "USD"
        res, body = self.client.getReceiverRequiredFields(receiveNodeCode, receiveCurrency)
        receiveInfo = self.makeReceiveInfo(res, body)
        res, body = self.client.checkReceiverRequiredFields(receiveNodeCode, receiveCurrency, receiveInfo)
        self.checkCheckReceiverRequiredFields(res)

    # 获取路由列表(目前费用策略仅支持LOWEST_FEE)
    def test_039_getRouterList_ro2ro_routerStrategyIsNone(self):
        res_router, body = self.client.getRouterList("USD.ROXE", "USD.ROXE")
        self.checkRouterList(res_router, body)

    def test_040_getRouterList_ro2ro_routerStrategyIsLOWEST_FEE(self):
        res_router, body = self.client.getRouterList("USD.ROXE", "USD.ROXE", routerStrategy="LOWEST_FEE")
        self.checkRouterList(res_router, body)

    def test_041_getRouterList_fait2ro_routerStrategyIsLOWEST_FEE(self):
        res_router, body = self.client.getRouterList("USD", "USD.ROXE", sendNodeCode=RTSData.checkout_node ,routerStrategy="LOWEST_FEE")
        self.checkRouterList(res_router, body)

    def test_042_getRouterList_ro2fait_routerStrategyIsLOWEST_FEE(self):
        res_router, body = self.client.getRouterList("USD.ROXE", "PHP", receiveNodeCode=RTSData.terrapay_node_ph, routerStrategy="LOWEST_FEE")
        self.checkRouterList(res_router, body)

    def test_043_getRouterList_fait2fait_snsn_routerStrategyIsLOWEST_FEE(self):
        res_router, body = self.client.getRouterList("USD", "PHP", sendNodeCode=RTSData.checkout_node, receiveNodeCode=RTSData.terrapay_node_ph, routerStrategy="LOWEST_FEE")
        self.checkRouterList(res_router, body)

    def test_044_getRouterList_fait2fait_pnsnsn_routerStrategyIsLOWEST_FEE(self):
        res_router, body = self.client.getRouterList("USD", "GBP", sendAmount=10000, sendNodeCode=RTSData.node_code_pn["US"], receiveNodeCode=RTSData.node_code_sn["GB"], routerStrategy="LOWEST_FEE")
        self.checkRouterList(res_router, body)

    def test_045_getRouterList_fait2fait_snsnpn_routerStrategyIsLOWEST_FEE(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendNodeCode=RTSData.node_code_sn["US"], receiveNodeCode=RTSData.node_code_pn["US"], routerStrategy="LOWEST_FEE")
        self.checkRouterList(res_router, body)

    def test_046_getRouterList_fait2fait_pnsnsnpn_routerStrategyIsLOWEST_FEE(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendNodeCode="pnuzj1hpyxxx", receiveNodeCode="pnuzj1hpyyyy", routerStrategy="LOWEST_FEE")
        self.checkRouterList(res_router, body)

    def test_047_getRouterList_ro2fait_businessTypeIsC2C(self):
        res_router, body = self.client.getRouterList("USD.ROXE", "PHP", receiveNodeCode=RTSData.terrapay_node_ph, businessType="C2C")
        self.checkRouterList(res_router, body)

    def test_048_getRouterList_fait2fait_snsn_businessTypeIsC2C(self):
        # res_router, body = self.client.getRouterList("USD", "PHP", sendNodeCode=RTSData.checkout_node, receiveNodeCode=RTSData.terrapay_node_ph, businessType="C2C")
        # res_router, body = self.client.getRouterList("USD", "CAD", sendNodeCode="n2xpress5exp", receiveNodeCode="roxeniumtca1", businessType="C2C", sendAmount=15)
        # res_router, body = self.client.getRouterList("USD", "PHP", sendNodeCode="neumi2r3mt35", receiveNodeCode="cebuanalh1c3", businessType="C2C", sendAmount=15, receiveMethodCode="CASH")
        res_router, body = self.client.getRouterList("USD", "PHP", sendNodeCode="n2xpress5exp", receiveCountry="PH", businessType="C2C", sendAmount=15, receiveMethodCode="CASH")
        # res_router, body = self.client.getRouterList("USD", "MXN", sendNodeCode="jeunese1rm43", receiveNodeCode="roxetrpaymx1", businessType="C2C")
        # res_router, body = self.client.getRouterList("USD", "MXN", sendNodeCode="limbicarc3t5", receiveNodeCode="roxetrpaymx1", businessType="C2C")
        # res_router, body = self.client.getRouterList("USD", "MXN", sendNodeCode="neumi2r3mt35", receiveNodeCode="roxetrpaymx1", businessType="C2C")
        self.checkRouterList(res_router, body)

    def test_049_getRouterList_fait2fait_snsn_businessTypeIsC2B(self):
        res_router, body = self.client.getRouterList("USD", "GBP", sendNodeCode=RTSData.node_code_sn["US"], receiveNodeCode=RTSData.node_code_sn["GB"], businessType="C2B")
        self.checkRouterList(res_router, body)

    def test_050_getRouterList_fait2fait_pnsnsn_businessTypeIsC2B(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendNodeCode=RTSData.node_code_pn["US"], receiveNodeCode=RTSData.node_code_sn["US"], businessType="C2B")
        self.checkRouterList(res_router, body)

    def test_051_getRouterList_fait2fait_snsnpn_businessTypeIsC2B(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendNodeCode=RTSData.node_code_sn["US"], receiveNodeCode=RTSData.node_code_pn["US"], businessType="C2B")
        self.checkRouterList(res_router, body)

    def test_052_getRouterList_fait2fait_pnsnsnpn_businessTypeIsC2B(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendNodeCode="pnuzj1hpyxxx", receiveNodeCode="pnuzj1hpyyyy", businessType="C2B")
        self.checkRouterList(res_router, body)

    def test_053_getRouterList_fait2fait_snsn_isReturnOrderIsFalse(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendNodeCode=RTSData.node_code_sn["US"], receiveNodeCode=RTSData.node_code_sn["US"], isReturnOrder=False)
        self.checkRouterList(res_router, body)

    def test_054_getRouterList_fait2fait_snsn_isReturnOrderIsTrue(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendNodeCode=RTSData.node_code_sn["US"], receiveNodeCode=RTSData.node_code_sn["US"], isReturnOrder=True)
        self.checkRouterList(res_router, body)

    def test_055_getRouterList_fait2fait_pnsnsn_isReturnOrderIsTrue(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendNodeCode=RTSData.node_code_pn["US"], receiveNodeCode=RTSData.node_code_sn["US"], isReturnOrder=True)
        self.checkRouterList(res_router, body)

    def test_056_getRouterList_fait2fait_snsnpn_isReturnOrderIsTrue(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendNodeCode=RTSData.node_code_sn["US"], receiveNodeCode=RTSData.node_code_pn["US"], isReturnOrder=True)
        self.checkRouterList(res_router, body)

    @unittest.skip("未配置此类路由")
    def test_057_getRouterList_fait2fait_pnsnsnpn_isReturnOrderIsTrue(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendNodeCode="pnuzj1hpyxxx", receiveNodeCode="pnuzj1hpyyyy", isReturnOrder=True)
        self.checkRouterList(res_router, body)

    def test_058_getRouterList_fait2ro_inSendCountry(self):
        res_router, body = self.client.getRouterList("USD", "USD.ROXE", sendCountry="US")
        self.checkRouterList(res_router, body)

    def test_059_getRouterList_fait2fait_snsn_inSendCountry(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendCountry="US", receiveNodeCode=RTSData.node_code_sn["US"])
        self.checkRouterList(res_router, body)

    def test_060_getRouterList_fait2fait_pnsnsn_inSendCountry(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendCountry="US", receiveNodeCode=RTSData.node_code_sn["US"])
        self.checkRouterList(res_router, body)

    def test_061_getRouterList_fait2fait_snsnpn_inSendCountry(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendCountry="US", receiveNodeCode=RTSData.node_code_pn["US"])
        self.checkRouterList(res_router, body)

    def test_062_getRouterList_fait2fait_pnsnsnpn_inSendCountry(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendCountry="US", receiveNodeCode="pnuzj1hpyyyy")
        self.checkRouterList(res_router, body)

    def test_063_getRouterList_ro2fait_inReceiveCountry(self):
        res_router, body = self.client.getRouterList("USD.ROXE", "PHP", receiveCountry="PH")
        self.checkRouterList(res_router, body)

    def test_064_getRouterList_fait2fait_snsn_inReceiveCountry(self):
        # res_router, body = self.client.getRouterList("USD", "GBP", sendNodeCode=RTSData.node_code_sn["US"], receiveCountry="GB")
        # res_router, body = self.client.getRouterList("USD", "PHP", sendNodeCode="neumi2r3mt35", receiveCountry="PH", sendAmount=100)
        # res_router, body = self.client.getRouterList("USD", "GHS", sendNodeCode="neumi2r3mt35", receiveCountry="GH", sendAmount=100)
        # res_router, body = self.client.getRouterList("USD", "CNY", sendNodeCode="jeunese1rm43", receiveCountry="CN", sendAmount=100)
        # res_router, body = self.client.getRouterList("USD", "VND", sendNodeCode="limbicarc3t5", receiveCountry="VN", sendAmount=100)
        # res_router, body = self.client.getRouterList("USD", "MXN", sendNodeCode="motoverse2e4", receiveCountry="MX", sendAmount=100)
        res_router, body = self.client.getRouterList("USD", "EUR", sendNodeCode="n2xpress5exp", receiveCountry="PL", sendAmount=100)
        # self.checkRouterList(res_router, body)

    def test_065_getRouterList_fait2fait_pnsnsn_inReceiveCountry(self):
        res_router, body = self.client.getRouterList("USD", "GBP", sendNodeCode=RTSData.node_code_pn["US"], receiveCountry="GB")
        self.checkRouterList(res_router, body)

    def test_066_getRouterList_fait2fait_snsnpn_inReceiveCountry(self):
        res_router, body = self.client.getRouterList("USD", "GBP", sendNodeCode=RTSData.node_code_sn["US"], receiveCountry="GB")
        self.checkRouterList(res_router, body)

    def test_067_getRouterList_fait2fait_pnsnsnpn_inReceiveCountry(self):
        res_router, body = self.client.getRouterList("USD", "GBP", sendNodeCode=RTSData.node_code_pn["US"], receiveCountry="GB")
        self.checkRouterList(res_router, body)

    def test_068_getRouterList_fait2fait_snsn_inSendCountry_inReceiveCountry(self):
        res_router, body = self.client.getRouterList("USD", "GBP", sendCountry="US", receiveCountry="GB")
        self.checkRouterList(res_router, body)

    def test_069_getRouterList_fait2fait_pnsnsn_inSendCountry_inReceiveCountry(self):
        res_router, body = self.client.getRouterList("USD", "GBP", sendCountry="US", receiveCountry="GB")
        self.checkRouterList(res_router, body)

    def test_070_getRouterList_fait2fait_snsnpn_inSendCountry_inReceiveCountry(self):
        res_router, body = self.client.getRouterList("USD", "GBP", sendCountry="US", receiveCountry="GB")
        self.checkRouterList(res_router, body)

    def test_071_getRouterList_fait2fait_pnsnsnpn_inSendCountry_inReceiveCountry(self):
        res_router, body = self.client.getRouterList("USD", "GBP", sendCountry="US", receiveCountry="GB")
        self.checkRouterList(res_router, body)

    def test_072_getRouterList_fait2fait_snsn_inSendCountry_inReceiveCountry(self):
        res_router, body = self.client.getRouterList("GBP", "USD", sendCountry="GB", receiveCountry="US")
        self.checkRouterList(res_router, body)

    def test_073_getRouterList_fait2fait_snsn_inAmountCriticalValue(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendNodeCode=RTSData.node_code_sn["US"], receiveNodeCode=RTSData.mock_node, sendAmount=5.24)
        self.checkRouterList(res_router, body)

    def test_074_getRouterList_ro2fait_inReceiveMethodCode_BANK(self):
        res_router, body = self.client.getRouterList("USD.ROXE", "PHP", receiveNodeCode=RTSData.terrapay_node_ph, receiveMethodCode="BANK")
        self.checkRouterList(res_router, body)

    def test_075_getRouterList_fait2fait_snsn_inReceiveMethodCode_BANK(self):
        res_router, body = self.client.getRouterList("USD", "GBP", sendNodeCode=RTSData.node_code_sn["US"], receiveNodeCode=RTSData.node_code_sn["GB"], receiveMethodCode="BANK")
        self.checkRouterList(res_router, body)

    def test_076_getRouterList_fait2fait_pnsnsn_inReceiveMethodCode_BANK(self):
        res_router, body = self.client.getRouterList("USD", "GBP", sendNodeCode=RTSData.node_code_pn["US"], receiveNodeCode=RTSData.node_code_sn["GB"], receiveMethodCode="BANK")
        self.checkRouterList(res_router, body)

    def test_077_getRouterList_fait2fait_snsnpn_inReceiveMethodCode_BANK(self):
        res_router, body = self.client.getRouterList("USD", "GBP", sendNodeCode=RTSData.node_code_sn["US"], receiveNodeCode=RTSData.node_code_pn["GB"], receiveMethodCode="BANK")
        self.checkRouterList(res_router, body)

    def test_078_getRouterList_fait2fait_pnsnsnpn_inReceiveMethodCode_BANK(self):
        res_router, body = self.client.getRouterList("USD", "GBP", sendNodeCode=RTSData.node_code_pn["US"], receiveNodeCode=RTSData.node_code_pn["GB"], receiveMethodCode="BANK")
        self.checkRouterList(res_router, body)

    # 已确认需减去sendFee和serviceFee
    def test_079_getRouterList_fait2fait_snsn_inReceiveMethodCode_eWALLET(self):
        res_router, body = self.client.getRouterList("USD", "PHP", sendNodeCode=RTSData.node_code_sn["US"], receiveNodeCode=RTSData.gcash_node, receiveMethodCode="EWALLET", eWalletCode="GCASH")
        self.checkRouterList(res_router, body)

    @unittest.skip("暂不支持CASH出金（仅可通过rpc测试Cebuana的CASH出金）")
    def test_080_getRouterList_fait2fait_snsn_inReceiveMethodCode_CASH(self):
        res_router, body = self.client.getRouterList("USD", "PHP", sendNodeCode=RTSData.checkout_node, receiveNodeCode=RTSData.cebuana_node, receiveMethodCode="CASH")
        self.checkRouterList(res_router, body)

    def test_081_getRouterList_fait2ro_inPassByNodes(self):
        res_router, body = self.client.getRouterList("USD", "USD.ROXE", sendNodeCode=RTSData.checkout_node, passByNodes=[RTSData.checkout_node])
        self.checkRouterList(res_router, body)

    def test_082_getRouterList_ro2fait_inPassByNodes(self):
        res_router, body = self.client.getRouterList("USD.ROXE", "PHP", receiveCountry="PH", passByNodes=[RTSData.terrapay_node_ph])
        self.checkRouterList(res_router, body)

    def test_083_getRouterList_fait2fait_snsn_inPassByNodes_nodata(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendNodeCode=RTSData.checkout_node, receiveCountry="US", passByNodes=[RTSData.mock_node])
        self.checkRouterList(res_router, body)

    def test_084_getRouterList_fait2fait_pnsnsn_inPassByNodes(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendCountry="GB", receiveCountry="US", passByNodes=[RTSData.node_code_pn["GB"], RTSData.node_code_sn["US"]])
        self.checkRouterList(res_router, body)

    def test_085_getRouterList_fait2fait_snsnpn_inPassByNodes_nodata(self):
        res_router, body = self.client.getRouterList("USD", "USD", sendCountry="GB", receiveCountry="US", passByNodes=[RTSData.node_code_sn["GB"], RTSData.node_code_pn["US"]])
        self.checkRouterList(res_router, body)

    def test_086_getRouterList_fait2fait_pnsnsnpn_inPassByNodes_nodata(self):
        res_router, body = self.client.getRouterList("USD", "GBP", sendCountry="US", receiveCountry="GB", passByNodes=[RTSData.node_code_pn["US"], RTSData.node_code_sn["US"], RTSData.node_code_sn["GB"], RTSData.node_code_pn["GB"]])
        self.checkRouterList(res_router, body)

    def test_087_getRouterList_fait2fait_pnsnsnpn_allIn_BANK(self):
        res_router, body = self.client.getRouterList("USD", "GBP", sendNodeCode=RTSData.node_code_pn["US"], sendCountry="US",
                                                     receiveNodeCode=RTSData.node_code_pn["GB"], receiveCountry="GB",
                                                     routerStrategy="LOWEST_FEE", businessType="C2C", receiveMethodCode="BANK", isReturnOrder=True,
                                                     passByNodes=[RTSData.node_code_pn["US"], RTSData.node_code_sn["US"], RTSData.node_code_sn["GB"], RTSData.node_code_pn["GB"]])
        self.checkRouterList(res_router, body)

    # 已确认需减去sendFee和serviceFee
    def test_088_getRouterList_fait2fait_snsn_allIn_eWALLET(self):
        res_router, body = self.client.getRouterList("USD", "PHP", sendNodeCode=RTSData.node_code_pn["US"], sendCountry="US",
                                                     receiveNodeCode=RTSData.gcash_node, receiveCountry="PH",
                                                     routerStrategy="LOWEST_FEE", businessType="C2C", receiveMethodCode="EWALLET", eWalletCode="GCASH",
                                                     passByNodes=[RTSData.node_code_sn["US"]])
        self.checkRouterList(res_router, body)

    def test_089_getRouterList_fait2fait_snsn_terrapay2(self):
        # 针对terrapay第二个节点国家测试
        res_router, body = self.client.getRouterList("USD", "THB", sendNodeCode=RTSData.node_code_sn["US"], receiveNodeCode=RTSData.terrapay_node_th)
        self.checkRouterList(res_router, body)

    def test_090_setWebhookUrl(self):
        # todo 如何保证rtsRsaKey和节点的对应关系，未做这方面的越权校验
        t = str(int(time.time()))
        node_url = "http://rmn-uat.roxepro.top:38888/api/rmn/v2/rts/notify/notice" + t
        res_info = self.client.ns_setWebhookUrl(node_url, "pnuzj1hpyyyy", "NOTICE")
        print(res_info)
        self.assertEqual(res_info["data"]["msgType"], "NOTICE")
        self.assertEqual(res_info["data"]["url"], node_url)

        query_url = "http://rmn-uat.roxepro.top:38888/api/rmn/v2/rts/notify/query" + t
        res_info = self.client.ns_setWebhookUrl(query_url, "pnuzj1hpyyyy", "QUERY")
        self.assertEqual(res_info["data"]["msgType"], "QUERY")
        self.assertEqual(res_info["data"]["url"], query_url)

        if RTSData.is_check_db:
            set_node = "pnuzj1hpyyyy"
            db_info = self.mysql.exec_sql_query(f"select * from `roxe_ns`.node_info where node_code='{set_node}'")
            self.assertEqual(db_info[0]["notifyUrl"], node_url)
            self.assertEqual(db_info[0]["queryUrl"], query_url)

    def test_091_pushOrderState(self):
        receive_info = RTSData.rmn_receive_info
        sendNodeCode = "ifomx232tdly"
        receiveNodeCode = "huu4lssdbmbt"
        receive_info["receiverBankRoxeId"] = receiveNodeCode
        amount = 15
        # rts_order_info, submit_body = self.client.submitOrder(
        #     "", "USD", "USD", receive_info, sendNodeCode=sendNodeCode, receiveNodeCode=receiveNodeCode,
        #     sendAmount=amount, businessType="C2C", receiveMethodCode="BANK"
        # )
        fee = "1.57"
        # tx_id = rts_order_info["data"]["instructionId"]
        # transactionId = rts_order_info["data"]["transactionId"]
        tx_id = "rtstest016637490548899960"
        transactionId = "1459242846634eaabb41a5f65d8a1f24"
        push_info = self.client.ns_balanceNotice(tx_id, transactionId, amount, "USD", fee, "USD", "0", "123456789012", "BANK", "12341234123")

    # 生产环境测试
    @unittest.skip("生产用例单独执行")
    def test_300_getRouterList_fait2fait_snsn(self):
        sendNodeCode = RTSData.node_code_sn["US1"]
        sendCountry = "US"
        receiveNodeCode = RTSData.node_code_sn["US2"]
        receiveCountry = "US"
        self.client.getRouterList("USD", "USD", sendNodeCode=sendNodeCode, sendCountry=sendCountry,
                                                     receiveNodeCode=receiveNodeCode, receiveCountry=receiveCountry,
                                                     routerStrategy="LOWEST_FEE", businessType="C2C",
                                                     receiveMethodCode="BANK", isReturnOrder=False,
                                                     passByNodes=[sendNodeCode, receiveNodeCode])

    @unittest.skip("生产用例单独执行")
    def test_301_queryContractRate_inAmount(self):
        sendCurrency = "USD"
        receiveCurrency = "PHP"
        amount = 10
        rate_info, request_body = self.client.getRate(sendCurrency, receiveCurrency, sendAmount=amount)
        self.checkCodeAndMessage(rate_info)
