# -*- coding: UTF-8 -*-
import unittest
import requests
import json
import datetime
from threading import Thread
import websocket
import time
import ssl
from .pub_function import setCustomLogger
from .Global import Global
from .operationExcel import *
from .CoreFunction import Mysql
from . import ApiUtils as Utils


class WSClient:

    def __init__(self, url, msg=None, headers=None, init_send_msg=None, pingMsg="ping"):
        # websocket.enableTrace(True)
        self.url = url.replace("http", 'ws')
        print("请求的ws url: {}".format(self.url))
        self.pingMsg = pingMsg
        self.ws = websocket.WebSocketApp(self.url, header=headers)

        # register websocket callbacks
        self.ws.on_open = self._on_open
        self.ws.on_message = self._on_message
        self.ws.on_error = self._on_error
        self.ws.on_close = self._on_close
        self.ws.on_ping = self._on_ping
        if msg is None:
            msg = []
        self.msg = msg
        self.errMsg = []
        self.init_send_msg = init_send_msg

        # run event loop on separate thread
        if self.url.startswith('wss'):
            sslopt = {'cert_reqs': ssl.CERT_NONE}
        else:
            sslopt = None
        self.t = Thread(target=self.ws.run_forever, args=(None, sslopt, 30, 20))

        self.t.setDaemon(True)
        self.t.start()

        self.opened = False

        while self.opened is False:
            time.sleep(.50)

    def _on_ping(self):
        self.ws.send(self.pingMsg)

    def _on_message(self, message):
        """
        Executed when WS received message
        """
        if isinstance(self.msg, list):
            self.msg.append(message)
        else:
            self.msg = message

    def _on_error(self, error):
        """
        Executed when WS connection errors out
        """
        print(error)
        self.errMsg.append(error)

    def _on_close(self):
        """
        Executed when WS connection is closed
        """
        print("### closed ###")
        self.errMsg.append("连接被关闭")

    def _on_open(self):
        """
        Executed when WS connection is opened
        """
        self.opened = True
        if self.init_send_msg:
            self.ws.send(self.init_send_msg)


class MakeTestData:
    isCheckDb = True
    dbInfo = {}
    redisInfo = {}
    if Global.get_value("ENV") == "uat":
        dbInfo = {
            "mysqlHost": "192.168.43.208",
            "mysqlPort": 3306,
            "mysqlUser": "exone",
            "mysqlPwd": "da0llarG!",
            "mysqlDB": "roxe_user_center_cloud",
        }

        redisInfo = {
            "redisHost": "192.168.43.195",
            "redisPort": 6379,
            "redisPwd": "0RmlMywU5omPJjDOSsN4",
        }


def makeHttpTestFunc(clsObject, case):
    def func(*args):
        # 组装http请求参数
        requestUrl = case[ExcelValues.CASE_URL.value]
        requestMethod = case[ExcelValues.CASE_METHOD.value].lower()
        params = BaseTestClass.getParamFromExcelData(case, ExcelValues.CASE_PARAMS.value, "body")
        headers = BaseTestClass.getParamFromExcelData(case, ExcelValues.CASE_HEADER.value, "header", params)
        # 发送http请求获取响应
        logger.info("准备发送请求")
        if requestMethod == "get":
            res = requests.get(requestUrl, params=params, headers=headers)
        elif requestMethod == "post":
            res = BaseTestClass.sendPostRequest(requestUrl, params, headers)
        elif requestMethod == "delete":
            res = requests.delete(requestUrl, headers=headers)
        else:
            res = None
        logger.info("得到请求结果。。")
        # 打印请求的参数和结果
        logger.info("请求url: {}".format(requestUrl))
        if headers is not None:
            logger.info("请求header: {}".format(headers))
        if requestMethod == "get" and params is not None:
            logger.info("请求params: {}".format(params))
        if requestMethod == "post" and params is not None:
            logger.info("请求body: {}".format(params))
        logger.info("请求结果: {}".format(res.text))
        # 校验返回的响应
        clsObject.checkDictResult(res.json(), case)
    return func


class BaseTestClass(unittest.TestCase):
    mysql = None
    redisClient0 = None
    redisClient2 = None

    @classmethod
    def setUpClass(cls):
        if MakeTestData.isCheckDb:
            cls.mysql = Mysql(MakeTestData.dbInfo["mysqlHost"], MakeTestData.dbInfo["mysqlPort"], MakeTestData.dbInfo["mysqlUser"], MakeTestData.dbInfo["mysqlPwd"], MakeTestData.dbInfo["mysqlDB"])
            cls.mysql.connect_database()
        if MakeTestData.redisInfo:
            r = Utils.RedisClient(MakeTestData.redisInfo["redisHost"], MakeTestData.redisInfo["redisPort"], MakeTestData.redisInfo["redisPwd"])
            cls.redisClient0 = r.getClient(0)
            cls.redisClient2 = r.getClient(2)

    @classmethod
    def tearDownClass(cls):
        if MakeTestData.isCheckDb:
            cls.mysql.disconnect_database()
        if MakeTestData.redisInfo:
            cls.redisClient0.close()
            cls.redisClient2.close()

    @classmethod
    def getExpectResult(cls, case):
        dataResult = {}
        dataResultStr = case[ExcelValues.CASE_RESULT.value].strip()
        if dataResultStr != "":
            dataResult = json.loads(dataResultStr)
            if "$" in dataResultStr:
                # 结果数据参数化
                resultDBInfo = case[ExcelValues.CASE_RESULT_COMPARE_WITH_DB.value].strip()
                expectValue = None
                savedDbRes = {}
                for dbKey, dbValue in json.loads(resultDBInfo).items():
                    if "mysql" in dbValue:
                        # 从数据库中得到结果
                        dbRes = cls.mysql.exec_sql_query(dbValue["mysql"])
                        logger.info("执行的查询sql:{}".format(dbValue["mysql"]))
                        logger.info("查询数据库的结果: {}".format(dbRes))
                        if dbValue["dbResType"] == "list":
                            expectValue = dbRes
                        elif dbValue["dbResType"] == "float":
                            expectValue = float(dbRes[0][dbKey]) if len(dbRes) > 0 else 0
                        savedDbRes[dbKey] = dbRes
                    if "generateByDBRes" in dbValue:
                        # 根据之前的数据库结果二次加工得到
                        m = dbValue["generateByDBRes"]["method"]
                        p = dbValue["generateByDBRes"]["params"]
                        executeStr = m.replace(p, 'savedDbRes["{}"]'.format(p))
                        expectValue = eval(executeStr)
                    updateDict = Utils.generateDict(dbKey, expectValue)
                    dataResult = Utils.deepUpdateDict(dataResult, updateDict)
        return dataResult

    @classmethod
    def checkDictResult(cls, result, case):
        if case[ExcelValues.CASE_RESULT_RULE.value].strip() != "":
            resultRule = json.loads(case[ExcelValues.CASE_RESULT_RULE.value].strip())
        else:
            resultRule = None
        dataResult = cls.getExpectResult(case)
        if resultRule:
            for ruleKey, ruleValue in resultRule.items():
                rules = ruleValue if isinstance(ruleValue, list) else [ruleValue]
                if ruleKey == "判断不为None":
                    extendResult = Utils.expandData(result)
                    extendDataResult = Utils.expandData(dataResult)
                    for index, info in enumerate(extendResult):
                        if info[0] in rules:
                            assert info[1] is not None, "{}检查应不为None".format(info[0])
                        else:
                            assert info[0] == extendDataResult[index][0], "key的实际结果和预期不符: {}、{}".format(info[0], extendDataResult[index][0])
                            assert info[1] == extendDataResult[index][1], "{}的实际结果和预期不符: {}、{}".format(info[0], info[1], extendDataResult[index][1])
                elif ruleKey == "数据类型为list":
                    for rk, rv in result.items():
                        if rk in rules:
                            assert len(rv) == len(dataResult[rk]), "接口返回的数据和数据库查询的数据条数不一致: {}、{}".format(len(rv), len(dataResult[rk]))
                            for item in rv:
                                assert item in dataResult[rk], "{} 不在数据库结果中".format(item)
                        else:
                            assert rv == dataResult[rk]
                else:
                    assert result == dataResult, "实际结果和预期不符: {}、{}".format(result, dataResult)
        else:
            assert result == dataResult, "实际结果和预期不符: {}、{}".format(result, dataResult)

    @staticmethod
    def generateParams(paramName, rule: dict, **kwargs):
        try:
            r = rule[paramName]
            if r["method"] == "hmac256(body, secKey)":
                return Utils.getSignByHmacSha256(**kwargs)
            elif r["method"] == "readFromExcel":
                return r["params"]
            elif r["method"] == "sha256":
                return Utils.getSignBySha256(r["params"])
            elif r["method"] == "readImageFile":
                fileName = os.path.basename(r["params"])
                if r["params"].endswith(".jpg"):
                    fileType = "image/jpeg"
                else:
                    fileType = "image/png"
                f = (fileName, open(r["params"], 'rb'), fileType)
                return f
            elif r["method"] == "readFromRedis":
                pass
        except Exception:
            raise Exception("加密参数错误，检查数据:{}".format(rule))

    @staticmethod
    def getParamFromExcelData(case, excelColumn, location, body=None, **kwargs):
        res = None
        if case[excelColumn] != "":
            res = json.loads(case[excelColumn])
        if case[ExcelValues.CASE_PARAMETERIZED_RULE.value] != "":
            rule = json.loads(case[ExcelValues.CASE_PARAMETERIZED_RULE.value])
            for k, v in rule.items():
                if v["location"].lower() == location and res is not None:
                    if location == "header":
                        if "hmac256" in v["method"]:
                            res[k] = BaseTestClass.generateParams(k, rule, body=json.dumps(body), secKey=v["params"])
                        else:
                            res[k] = BaseTestClass.generateParams(k, rule, **kwargs)
                    else:
                        res[k] = BaseTestClass.generateParams(k, rule)
        return res

    @classmethod
    def sendPostRequest(cls, requestUrl, body, headers):
        # 获取Content-Type类型，默认为<application/json>
        dataType = headers.get("Content-Type") if "Content-Type" in headers else "application/json"
        if dataType == "application/json":
            res = requests.post(requestUrl, json=body, headers=headers)
        elif dataType == "multipart/form-data":
            files = []
            for k, v in body.items():
                files.append((k, v))
            res = requests.post(requestUrl, files=files, headers=headers)
        elif dataType == "application/x-www-form-urlencoded":
            bodyData = ""
            for bk, bv in body.items():
                bodyData += bk + "=" + bv
            res = requests.post(requestUrl, bodyData, headers=headers)
        else:
            res = requests.post(requestUrl, json.dumps(body), headers=headers)
        return res


class MakeTestCase:
    testCases = None

    def __init__(self, excelData):
        self.caseData = excelData

    @staticmethod
    def makeWebsocketTestFunc(case):
        def func(*args):
            headers, sendMsg = None, None
            requestUrl = case[ExcelValues.CASE_URL.value]
            if case[ExcelValues.CASE_HEADER.value] != "":
                headers = json.loads(case[ExcelValues.CASE_HEADER.value])
            wsTimeOut = 20
            if case[ExcelValues.CASE_WEBSOCKET_TIMEOUT.value] != "":
                wsTimeOut = float(case[ExcelValues.CASE_WEBSOCKET_TIMEOUT.value])
            logger.info(case[ExcelValues.CASE_PARAMETERIZED_RULE.value])
            rule = None
            if case[ExcelValues.CASE_PARAMETERIZED_RULE.value] != "":
                rule = json.loads(case[ExcelValues.CASE_PARAMETERIZED_RULE.value])
            if case[ExcelValues.CASE_PARAMS.value] != "":
                params = json.loads(case[ExcelValues.CASE_PARAMS.value])
                if "body" in params:
                    if isinstance(params["body"], str):
                        sendMsg = params["body"]
                    else:
                        sendMsg = json.dumps(params["body"])
                if rule:
                    for k, v in rule.items():
                        if v["location"].lower() == "url" and params["url"] is not None:
                            params["url"][k] = BaseTestClass.generateParams(k, rule, body=v["body"], secKey=v["params"])
                requestUrl += "?"
                for pk, pv in params["url"].items():
                    requestUrl += pk + "=" + pv + "&"
                requestUrl = requestUrl.rstrip("&")
            logger.info("sendMsg: {}".format(sendMsg))
            ws = WSClient(requestUrl, headers=headers, init_send_msg=sendMsg)
            beginWsTime = time.time()
            while True:
                if time.time() - beginWsTime > wsTimeOut:
                    break
            if len(ws.msg) == 0:
                assert False, "websocket在{}秒内没有接收到消息".format(wsTimeOut)
            logger.info(ws.msg)
            # ws.msg = ['{"result":"true"}']
            # ws.msg = ['"{"method":"transaction","clientId":"G000000111","foreignExchange":{"destroyAmount":7448.99,"exchangeRate":74.4899,"inAmount":100.00,"inCurrency":"USD","mintageAmount":100.00,"outAmount":7438.99,"outCurrency":"INR"},"fee":{"deliveryFee":10,"deliveryFeeCurrency":"INR","serviceFee":0,"serviceFeeCurrency":"USD"},"payerUser":{"account":{"currency":"USD","id":"9893847433","method":"Saving Account","type":"OTHER"},"info":{"cityOfBirth":"New York","ctryOfBirth":"US","id":"23022919890815xxxx","name":"G1","postalAddress":"95 Xizhimen East Street, Xicheng District, Beijing, China","proprietary":"ID","provinceOfBirth":"New York"},"paymentOrg":{"name":"China Commercial Bank"}},"dbtrAgt":{"name":"JPMorgan Chase Bank","roxe":"a000000002","serviceFee":0,"serviceFeeCurrency":"USD","type":"SN"},"cdtrAgt":{"name":"ECS Fin","roxe":"a000000007","serviceFee":10,"serviceFeeCurrency":"INR","type":"SN"},"beneficiaryUser":{"account":{"currency":"INR","id":"3498474533","method":"Saving Account","type":"OTHER"},"info":{"cityOfBirth":"New York","ctryOfBirth":"US","id":"23022919890815xxxx","name":"g1","postalAddress":"95 Xizhimen East Street, Xicheng District, Beijing, China","proprietary":"ID","provinceOfBirth":"New York"},"paymentOrg":{"clrsys":{"code":"","id":""},"name":"Bank of Communications Hong Kong","roxe":"a000000007","swift":""}}}"']
            msgRule = None
            if case[ExcelValues.CASE_WEBSOCKET_PARSE.value] != "":
                msgRule = json.loads(case[ExcelValues.CASE_WEBSOCKET_PARSE.value].strip())
            if msgRule is None:
                # 默认为json最后1条数据
                result = json.loads(ws.msg[-1])
            else:
                checkMsg = ws.msg[-1]
                if "msgSearch" in msgRule:
                    searchRule = msgRule["msgSearch"]
                    checkMsg = []
                    for i in ws.msg:
                        conn = eval('{} in i'.format(searchRule))
                        if conn:
                            checkMsg.append(i)
                    checkMsg = checkMsg[0]  # 默认只取第一条
                if "msgParse" in msgRule:
                    s_info = msgRule["msgParse"].split(" ")
                    start_index = int(s_info[1]) - 1
                    end_index = -1 if s_info[-1] == "end" else int(s_info[-1])
                    result = json.loads(checkMsg[start_index:end_index])
                else:
                    result = checkMsg

            BaseTestClass().checkDictResult(result, case)
        return func

    def make(self):
        tSuite = unittest.TestSuite()
        testClasses = {}
        tests = []
        for case in self.caseData:
            className = case[ExcelValues.CASE_MODULE.value].strip() + "Test"
            if className not in testClasses:
                test_class = type(className, (BaseTestClass, ), {})
                testClasses[className] = test_class
            if case[ExcelValues.CASE_IS_RUN.value].lower() == "y":
                if case[ExcelValues.CASE_TYPE.value].lower() == "http":
                    test_func = makeHttpTestFunc(testClasses[className], case)
                else:
                    test_func = self.makeWebsocketTestFunc(case)
                test_name = "test_" + case[ExcelValues.CASE_ID.value] + "_" + case[ExcelValues.CASE_NAME.value]
                setattr(testClasses[className], test_name, test_func)
                tests.append(testClasses[className](test_name))
        tSuite.addTests(tests)
        return tSuite, testClasses


curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
logPath = os.path.join(rootPath, "./log/apiTestLog.log")
logger = setCustomLogger("MakeTestLog", logPath, isprintsreen=True, isrotaing=True)
if __name__ == "__main__":
    start_time = datetime.datetime.now()
    Global.setValue("ENV", "uat")

    client = MakeTestCase(OperationExcel().getExcelData(filePath(fileName="RoxeUserCenterAPI.xlsx")))
    suite, classNames = client.make()
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)

    # # 生成html报告并发送邮件
    # from roxe_libs.pub_function import produce_html_report, sendTestResultMail
    # reportName = "RTSDailyTestReport{}.html".format(start_time.strftime('%Y-%m-%d_%H-%M-%S'))
    # reportPath = os.path.abspath(os.path.join(curpath, "../TestReports"))
    # testResultDict = produce_html_report(suite, reportName, reportName, reportPath)
    # reportPath = os.path.abspath(os.path.join(reportPath, reportName))
    # mailTitle = "{} RTS Daily Test Report {}".format(Global.get_value("ENV"), start_time.strftime("%y-%m-%d"))
    # a = dict(mail_recievers=["mingleili@jiujiutech.cn"], env="uat")
    # testClassRelationship = {}
    # for name in classNames.keys():
    #     testClassRelationship[name] = name.rstrip("Test")
    # sendTestResultMail(a, mailTitle, reportPath, testResultDict, testClassRelationship, mail_user="mingleili@jiujiutech.cn", mail_pass="Xinyuanlml0617")
