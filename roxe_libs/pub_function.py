# -*- coding:utf-8 -*-
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
import yaml
import datetime
import smtplib
from email.mime.text import MIMEText
# from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from roxe_libs.BeautifulReport import BeautifulReport

import ctypes
import inspect


def _async_raise(tid, exctype):
    """raises the exception, performs cleanup if needed"""
    tid = ctypes.c_long(tid)
    if not inspect.isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        # """if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


def stop_thread(thread):
    _async_raise(thread.ident, SystemExit)


def loadYmlFile(yml_file):
    with open(yml_file, 'r', encoding='utf-8') as f:
        fr = f.read()
    return yaml.load(fr, Loader=yaml.FullLoader)


class LogRedirectHandler(logging.Handler):

    def __init__(self):
        logging.Handler.__init__(self)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            sys.stderr.write(msg + "\n")
        except Exception:
            self.handleError(record)


def setCustomLogger(name, logfilename="autolog.txt", isprintsreen=False, isrotaing=False, logfilemod='a',
                    level=logging.INFO, logRedirectHandler=False):
    fmt = '[%(levelname)s] %(asctime)s [%(threadName)s: %(thread)d]: [%(name)s:%(lineno)d]: %(message)s'
    # 定义logger对象，设置日志级别
    # logging.basicConfig(format=fmt, level=logging.DEBUG)
    logger_first = logging.getLogger(name)
    logger_first.setLevel(logging.DEBUG)
    # fmt = '[%(levelname)s] %(asctime)s: [%(threadName)s:%(thread)d] [%(name)s:%(lineno)d]: %(message)s'
    formatter = logging.Formatter(fmt)
    # 把日志输出到控制台
    if isprintsreen:
        if logRedirectHandler:
            handler = LogRedirectHandler()
        else:
            handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        handler.setLevel(level)
        logger_first.addHandler(handler)

    # 把日志输出到文件
    if isrotaing:
        fileHandler = RotatingFileHandler(filename=logfilename, maxBytes=1024 * 1024 * 200, backupCount=5, mode=logfilemod)
        # fileHandler = TimedRotatingFileHandler(filename=logfilename, when="W1", interval=1, backupCount=8)
    else:
        fileHandler = logging.FileHandler(filename=logfilename, mode=logfilemod)
    fileHandler.setFormatter(formatter)
    fileHandler.setLevel(logging.DEBUG)
    logger_first.addHandler(fileHandler)

    return logger_first


def split_log(fields):
    for info in fields['testResult']:
        tmp_log = []
        for i in info['log']:
            if isinstance(i, str):
                if i.count('\n') > 2:
                    for j in i.split('\n'):
                        tmp_log.append(j)
                else:
                    tmp_log.append(i)
        info['log'] = tmp_log
        if info["description"] and "        " in info["description"]:
            info["description"] = info["description"].replace("        ", "")


def produce_html_report(suite, report_file_name='report.html', report_file_path='../TestReports', log_name=None):
    report = BeautifulReport(suite, log_name=log_name)
    report.verbosity = 2
    report.report("自动化测试报告", report_file_name, report_file_path, callback=split_log)
    return report.fields


def multi_run_case(suite, case_res, log_name=None):
    report = BeautifulReport(suite, log_name=log_name)
    report.verbosity = 2
    c_res = report.report_threads("自动化测试报告", callback=split_log)
    case_res["testPass"] += c_res["testPass"]
    case_res["testAll"] += c_res["testAll"]
    case_res["testFail"] += c_res["testFail"]
    case_res["testSkip"] += c_res["testSkip"]
    case_res["testResult"] += c_res["testResult"]
    return case_res


def multi_html_report(case_res, report_file_name, report_file_path='../TestReports'):
    report = BeautifulReport([])
    report.report_path = os.path.abspath(report_file_path)
    report.filename = report_file_name
    report.output_report(out_res=case_res)


def findFailedCaseNameFromHtmlReport(result_file):
    import json
    with open(result_file, "rb") as f:
        body = f.read().decode("utf-8")
    begin_index = body.index("var resultData")
    end_index = body.index("function details(obj)")
    val = body[begin_index+17: end_index-1].strip().rstrip(";")
    tes_res = json.loads(val)
    failed_case = {}
    for i in tes_res["testResult"]:
        if i["status"] == "失败":
            if i["className"] not in failed_case:
                failed_case[i["className"]] = []
            failed_case[i["className"]].append(i["methodName"])
    return failed_case


def send_mail(receivers, title, contents, attachments, logger_name='', mail_user='qa_apifiny@jiujiutech.cn', mail_pass='Qa11111111!'):
    mail_host = "smtp.exmail.qq.com"

    # mail_user = 'mingleili@jiujiutech.cn'
    # mail_pass = 'Xinyuanlml0617'
    # sender = 'mingleili@jiujiutech.cn'

    mail_user = mail_user
    mail_pass = mail_pass
    sender = mail_user

    # parsreceivers = ['{}@jiujiutech.cn'.format(name) for name in receivers]

    # 1> 创建用于发送带有附件文件的邮件对象
    # related: 邮件内容的格式，采用内嵌的形式进行展示。
    message = MIMEMultipart('related')

    receivers = [receivers] if isinstance(receivers, str) else receivers

    message['From'] = sender
    message['Subject'] = title
    message['To'] = ';'.join(receivers)
    message_body = MIMEText(contents, 'plain', 'utf8')

    # 2> 需要将message_body对象，添加至message中，等待被发送。
    message.attach(message_body)

    # 3> 文档附件、图片附件等。
    # 一般如果数据是二进制的数据格式，在指定第二个参数的时候，都使用base64，一种数据传输格式。
    attachments = [attachments] if isinstance(attachments, str) else attachments
    for attachment in attachments:
        print(attachment)
        if not os.path.exists(attachment):
            print("{} doesn't exist".format(attachment))
            continue
        message_docx = MIMEText(open(attachment, 'rb').read().decode(), 'base64', 'utf8')
        message_docx.add_header('content-disposition', 'attachment', filename=os.path.basename(attachment))
        message.attach(message_docx)
    logger = logging.getLogger(logger_name)
    try:
        # smtpObj = smtplib.SMTP()
        # smtpObj.connect(mail_host,25)
        smtpobj = smtplib.SMTP_SSL(mail_host, 465)
        smtpobj.login(mail_user, mail_pass)
        smtpobj.sendmail(sender, receivers, message.as_string())
        smtpobj.quit()
        print('mail send success')
        logger.info('mail send success')
        logging.shutdown()
    except smtplib.SMTPException as e:
        print('mail send error:', e.args)
        print(e.with_traceback(e.__traceback__))
        logger.error("mail send error: " + e.args[0], exc_info=True)


def sendTestResultMail(testCaseData, mailTitle, report_path, result_dict, testClassRelationship, logger_name="",
                       mailReceiver=None, mail_user='qa_apifiny@jiujiutech.cn', mail_pass='Qa11111111!'):
    """

    :param testCaseData: 测试用例配置文件的数据，为一个字典，其中case_infos为用例相关信息
    :param mailTitle: 邮件的标题
    :param report_path: 测试用例报告的路径
    :param result_dict: 测试用例的执行数据
    :param testClassRelationship: 测试模块的关系，用来分类统计各模块的运行结果，例如:
                {
                    "ConnectTest": "Broker",
                    "SORTest": "SOR",
                }， key为改模块对应的test class name, value为模块名称
    :param logger_name: 日志的名称
    :param mailReceiver: 邮件接收人，默认为None，使用用例配置文件中的收件人, 可使用此参数进行调试
    :param mail_user: 邮件发件人
    :param mail_pass: 邮件发件人密码
    :return:
    """
    logger = logging.getLogger(logger_name)
    # 邮件收件人

    mail_recievers = testCaseData["mail_recievers"] if isinstance(testCaseData, dict) else testCaseData.mail_recievers
    if mailReceiver:
        mail_recievers = mailReceiver if "@" in mailReceiver else mailReceiver + "@jiujiutech.cn"
        print("测试报告邮件收件人: {}".format(mail_recievers))
    logger.info("测试报告邮件收件人: {}".format(mail_recievers))
    countFormat = {"成功": 0, "失败": 0, "跳过": 0}
    class_count = dict()
    for mode in testClassRelationship.keys():
        class_count[testClassRelationship[mode]] = countFormat.copy()
    for i in result_dict['testResult']:
        # print(i)
        if i['className'] in testClassRelationship:
            cur_count_key = testClassRelationship[i['className']]
        else:
            cur_count_key = None
        try:
            if i['status'] == "成功":
                class_count[cur_count_key]['成功'] += 1
            elif i["status"] == "失败":
                class_count[cur_count_key]['失败'] += 1
            else:
                class_count[cur_count_key]['跳过'] += 1
        except KeyError as e:
            logger.error(e.args[0], exc_info=True)
    env = testCaseData["env"] if isinstance(testCaseData, dict) else testCaseData.env
    contents = 'ENV: {}\ntestAll: {}\ntestPass: {}\ntestFail: {}\ntestSkip: {}\n\n' \
        .format(env, result_dict['testAll'], result_dict['testPass'], result_dict['testFail'],
                result_dict['testSkip'], )
    for k, v in class_count.items():
        if v['成功'] + v['失败'] > 0:
            tmp = 'Components {}: total: {} pass: {} fail: {} skip: {}\n'.format(
                k, v['成功'] + v['失败'] + v['跳过'], v['成功'], v['失败'], v["跳过"]
            )
            # print(tmp)
            contents += tmp
    contents += '\nPlease check the test results in the attached document\n'
    print("邮件正文: {}".format(contents))
    logger.info("邮件正文: {}".format(contents))
    send_mail(mail_recievers, mailTitle, contents, report_path, logger_name=logger_name, mail_user=mail_user, mail_pass=mail_pass)


def get_local_time(fmt='%Y-%m-%d %H:%M:%S.%f'):
    return datetime.datetime.now().strftime(fmt)



