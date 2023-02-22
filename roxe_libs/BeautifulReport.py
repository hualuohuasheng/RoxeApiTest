# -*- coding:utf-8 -*-
"""
@Version: 1.0
@Project: BeautyReport
@Author: Raymond
@Data: 2017/11/15 下午5:28
@File: __init__.py.py
@License: MIT
"""
import concurrent.futures
import logging
import os
import sys
from threading import current_thread, Lock
from queue import Queue
from io import StringIO as StringIO
import time
import datetime
import json
import unittest
import platform
import base64
# from distutils.sysconfig import get_python_lib
import traceback
from functools import wraps

__all__ = ['BeautifulReport', "testResultFields", "MirrorStringIO"]

HTML_IMG_TEMPLATE = """
    <a href="data:image/png;base64, {}">
    <img src="data:image/png;base64, {}" width="800px" height="500px"/>
    </a>
    <br></br>
"""
origin_stdout = sys.stdout


class OutputRedirector(object):
    """ Wrapper to redirect stdout or stderr """
    
    def __init__(self, fp):
        self.fp = fp
    
    def write(self, s):
        self.fp.write(s)
        # # 打印到控制台
        # tmp_stdout = sys.stdout
        # sys.stdout = origin_stdout
        # sys.stdout.write(s)
        # sys.stdout = tmp_stdout

    def writelines(self, lines):
        self.fp.writelines(lines)
    
    def flush(self):
        self.fp.flush()


class MirrorStringIO(StringIO):
    mirror_log = {}
    lock = Lock()

    def _save_log(self, s):
        self.mirror_log[current_thread().ident] += s

    def write(self, __s: str):
        self._save_log(__s)
        super().write(__s)

    def getMirrorValue(self) -> str:
        """
        返回当前线程的日志结果
        :return:
        """
        return self.mirror_log[current_thread().ident]


# output_buffer = MirrorStringIO()

SYSSTR = platform.system()
# SITE_PAKAGE_PATH = get_python_lib()


class PATH:
    """ all file PATH meta """
    curpath = os.path.abspath(os.path.dirname(__file__))
    # config_tmp_path = os.path.join(curpath, '../statics/template')
    config_tmp_path = os.path.join(curpath, './template/template.html')


class MakeResultJson:
    """ make html table tags """
    
    def __init__(self, datas: tuple):
        """
        init self object
        :param datas: 拿到所有返回数据结构
        """
        self.datas = datas
        self.result_schema = {}
    
    def __setitem__(self, key, value):
        """
        
        :param key: self[key]
        :param value: value
        :return:
        """
        self[key] = value
    
    def __repr__(self) -> str:
        """
            返回对象的html结构体
        :rtype: dict
        :return: self的repr对象, 返回一个构造完成的tr表单
        """
        keys = (
            'className',
            'methodName',
            'description',
            'spendTime',
            'status',
            'log',
        )
        for key, data in zip(keys, self.datas):
            self.result_schema.setdefault(key, data)
        return json.dumps(self.result_schema)


def testResultFields():
    fields = {
        "testPass": 0,
        "testResult": [],
        "testName": "",
        "testAll": 0,
        "testFail": 0,
        "beginTime": "",
        "totalTime": "",
        "testSkip": 0
    }
    return fields


class ReportTestResult(unittest.TestResult):
    """ override"""
    
    def __init__(self, log_name=None, stream=sys.stdout, descriptions=None, verbosity=None):
        """ pass """
        super().__init__(stream, descriptions, verbosity=1)
        self.begin_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        self.start_time = 0
        self.end_time = 0
        self.failure_count = 0
        self.error_count = 0
        self.success_count = 0
        self.skip_count = 0
        self.verbosity = verbosity
        self.success_case_info = []
        self.skipped_case_info = []
        self.failures_case_info = []
        self.errors_case_info = []
        self.all_case_counter = 0
        # self.suite = suite
        self.status = ''
        self.result_list = []
        self.case_log = ''
        self.default_report_name = '自动化测试报告'
        self.sys_stdout = None
        self.sys_stderr = None
        self.outputBuffer = None
        self.logger = None
        if log_name:
            self.logger = logging.getLogger(log_name)
        self.fields = testResultFields()

    @property
    def success_counter(self) -> int:
        """ set success counter """
        return self.success_count
    
    @success_counter.setter
    def success_counter(self, value) -> None:
        """
            success_counter函数的setter方法, 用于改变成功的case数量
        :param value: 当前传递进来的成功次数的int数值
        :return:
        """
        self.success_count = value

    def startTestRun(self):
        """
        在用例执行前运行，初始化记录日志的buffer
        :return:
        """
        self.outputBuffer = MirrorStringIO()
        self.outputBuffer.mirror_log[current_thread().ident] = ""
    
    def startTest(self, test) -> None:
        """
            当测试用例测试即将运行时调用
        :return:
        """
        if self.logger:
            self.logger.debug(f"start run {test}")
        super().startTest(test)
        self.sys_stdout = sys.stdout
        self.sys_stderr = sys.stderr
        sys.stdout = self.outputBuffer
        sys.stderr = self.outputBuffer
        self.start_time = time.time()
    
    def stopTest(self, test) -> None:
        """
            当测试用力执行完成后进行调用
        :return:
        """
        self.end_time = '{0:.6f} s'.format((time.time() - self.start_time))
        # print(self.get_all_result_info_tuple(test))
        self.result_list.append(self.get_all_result_info_tuple(test))
        self.complete_output()

    def complete_output(self):
        """
        Disconnect output redirection and return buffer.
        Safe to call multiple times.
        """
        if self.sys_stdout:
            sys.stdout = self.sys_stdout
            self.sys_stdout = None
        if self.sys_stderr:
            sys.stderr = self.sys_stderr
            self.sys_stderr = None
        return self.outputBuffer.getMirrorValue()
    
    def stopTestRun(self, title=None) -> dict:
        """
            所有测试执行完成后, 执行该方法
        :param title:
        :return:
        """
        self.fields['testPass'] = self.success_counter
        for item in self.result_list:
            item = json.loads(str(MakeResultJson(item)))
            self.fields.get('testResult').append(item)
        self.fields['testAll'] = len(self.result_list)
        self.fields['testName'] = title if title else self.default_report_name
        self.fields['testFail'] = self.failure_count
        self.fields['beginTime'] = self.begin_time
        end_time = time.time()
        start_time = datetime.datetime.strptime(self.begin_time, "%Y-%m-%d %H:%M:%S.%f").timestamp()
        self.fields['totalTime'] = str(round(end_time - start_time, 6)) + 's'
        self.fields['testError'] = self.error_count
        self.fields['testSkip'] = self.skip_count
        return self.fields
    
    def get_all_result_info_tuple(self, test) -> tuple:
        """
            接受test 相关信息, 并拼接成一个完成的tuple结构返回
        :param test:
        :return:
        """
        return tuple([*self.get_testcase_property(test), self.end_time, self.status, self.case_log])
    
    @staticmethod
    def error_or_failure_text(err) -> list:
        """
            获取sys.exc_info()的参数并返回字符串类型的数据, 去掉t6 error
        :param err:
        :return:
        """
        return traceback.format_exception(*err)
    
    def addSuccess(self, test) -> None:
        """
            pass
        :param test:
        :return:
        """
        logs = []
        output = self.complete_output()
        logs.append(output)
        if self.verbosity > 1:
            if self.logger:
                self.logger.info(f"ok {test}")
            else:
                sys.stderr.write('ok ')
                sys.stderr.write(str(test))
                sys.stderr.write('\n')
        else:
            sys.stderr.write('.')
        self.success_counter += 1
        self.status = '成功'
        self.case_log = output.split('\n')
        self._mirrorOutput = True  # print(class_name, method_name, method_doc)
    
    def addError(self, test, err):
        """
            add Some Error Result and infos
        :param test:
        :param err:
        :return:
        """
        logs = []
        output = self.complete_output()
        logs.append(output)
        logs.extend(self.error_or_failure_text(err))
        self.failure_count += 1
        self.add_test_type('失败', logs)
        if self.verbosity > 1:
            if self.logger:
                self.logger.info(f"E {test}")
            else:
                sys.stderr.write('E ')
                sys.stderr.write(str(test))
                sys.stderr.write('\n')
        else:
            sys.stderr.write('E')

        self._mirrorOutput = True
    
    def addFailure(self, test, err):
        """
            add Some Failures Result and infos
        :param test:
        :param err:
        :return:
        """
        logs = []
        output = self.complete_output()
        logs.append(output)
        logs.extend(self.error_or_failure_text(err))
        self.failure_count += 1
        self.add_test_type('失败', logs)
        if self.verbosity > 1:
            if self.logger:
                self.logger.info(f"F {test}")
            else:
                sys.stderr.write('F ')
                sys.stderr.write(str(test))
                sys.stderr.write('\n')
        else:
            sys.stderr.write('F')
        
        self._mirrorOutput = True
    
    def addSkip(self, test, reason) -> None:
        """
            获取全部的跳过的case信息
        :param test:
        :param reason:
        :return: None
        """
        logs = [reason]
        self.complete_output()
        self.skip_count += 1
        self.add_test_type('跳过', logs)
        
        if self.verbosity > 1:
            sys.stderr.write('S  ')
            sys.stderr.write(str(test))
            sys.stderr.write('\n')
        else:
            sys.stderr.write('S')
        self._mirrorOutput = True
    
    def add_test_type(self, status: str, case_log: list) -> None:
        """
            abstruct add test type and return tuple
        :param status:
        :param case_log:
        :return:
        """
        self.status = status
        self.case_log = case_log
    
    @staticmethod
    def get_testcase_property(test) -> tuple:
        """
            接受一个test, 并返回一个test的class_name, method_name, method_doc属性
        :param test:
        :return: (class_name, method_name, method_doc) -> tuple
        """
        class_name = test.__class__.__qualname__
        method_name = test.__dict__['_testMethodName']
        method_doc = test.__dict__['_testMethodDoc']
        return class_name, method_name, method_doc


class BeautifulReport(ReportTestResult, PATH):
    img_path = 'img/' if platform.system() != 'Windows' else 'img\\'
    
    def __init__(self, suites: unittest.TestSuite, log_name=None, *args, **kwargs):
        super(BeautifulReport, self).__init__(log_name, *args, **kwargs)
        self.suites = suites
        self.report_path = None
        self.title = '自动化测试报告'
        self.filename = 'report.html'

    def report(self, description, filename: str = None, report_path='.', fields_path=None, callback=None):
        """
            生成测试报告,并放在当前运行路径下
        :param description: 描述
        :param filename: 生成文件的filename
        :param report_path: 生成report的文件存储路径
        :param fields_path: 序列化测试结果的文件路径
        :param callback: 回调函数，用于处理fields
        :return:
        """
        if filename:
            self.filename = filename if filename.endswith('.html') else filename + '.html'
        
        if description:
            self.title = description
        
        self.report_path = os.path.abspath(report_path)
        self.suites.run(result=self)
        self.stopTestRun(self.title)
        # print(self.fields)
        if callback:
            callback(self.fields)
        if fields_path:
            # print(self.fields)
            import pickle
            pickle.dump(self.fields, open(fields_path, 'wb'))
        else:
            self.output_report()
            print('测试用例已全部完成.')

    def report_threads(self, description, callback=None):
        """
            生成测试报告,并放在当前运行路径下
        :param description: 描述
        :param callback: 回调函数，用于处理fields
        :return:
        """
        if description:
            self.title = description
        self.suites.run(result=self)
        self.stopTestRun(self.title)
        # print(self.fields)
        if callback:
            callback(self.fields)
        return self.fields

    def output_report(self, theme="theme_default", out_res=None):
        """
            生成测试报告到指定路径下
        :return:
        """
        out_res = out_res if out_res else self.fields
        template_path = self.config_tmp_path
        with open(os.path.join(os.path.dirname(template_path), theme + '.json'), 'r') as theme:
            render_params = {
                **json.load(theme),
                'resultData': json.dumps(out_res, ensure_ascii=False, indent=4)
            }

        override_path = os.path.abspath(self.report_path) if \
            os.path.abspath(self.report_path).endswith('/') else \
            os.path.abspath(self.report_path) + '/'

        with open(template_path, 'rb') as file:
            # body = file.readlines()
            body = file.read().decode("utf-8")

        def render_template(params: dict, template: str):
            for name, value in params.items():
                name = '${' + name + '}'
                template = template.replace(name, value)
            return template

        # with open(override_path + self.filename, 'wb') as write_file:
        #     for item in body:
        #         # print(item)
        #         if item.strip().startswith(b'var resultData'):
        #             head = '    var resultData = '
        #             item = item.decode().split(head)
        #             item[1] = head + json.dumps(self.FIELDS, ensure_ascii=False, indent=4)
        #             item = ''.join(item).encode()
        #             item = bytes(item) + b';\n'
        #         write_file.write(item)
        with open(override_path + self.filename, 'w', encoding="utf-8", newline="\n") as write_file:
            html = render_template(render_params, body)
            write_file.write(html)
        print("测试报告生成到: {}".format(override_path + self.filename))
    
    @staticmethod
    def img2base(img_path: str, file_name: str) -> str:
        """
            接受传递进函数的filename 并找到文件转换为base64格式
        :param img_path: 通过文件名及默认路径找到的img绝对路径
        :param file_name: 用户在装饰器中传递进来的问价匿名
        :return:
        """
        pattern = '/' if platform != 'Windows' else '\\'

        with open(img_path + pattern + file_name, 'rb') as file:
            data = file.read()
        return base64.b64encode(data).decode()

    def add_test_img(*pargs):
        """
            接受若干个图片元素, 并展示在测试报告中
        :param pargs:
        :return:
        """

        def _wrap(func):
            @wraps(func)
            def __wrap(*args, **kwargs):
                img_path = os.path.abspath('{}'.format(BeautifulReport.img_path))
                try:
                    result = func(*args, **kwargs)
                except Exception:
                    if 'save_img' in dir(args[0]):
                        save_img = getattr(args[0], 'save_img')
                        save_img(func.__name__)
                        data = BeautifulReport.img2base(img_path, pargs[0] + '.png')
                        print(HTML_IMG_TEMPLATE.format(data, data))
                    sys.exit(0)
                print('<br></br>')

                if len(pargs) > 1:
                    for parg in pargs:
                        print(parg + ':')
                        data = BeautifulReport.img2base(img_path, parg + '.png')
                        print(HTML_IMG_TEMPLATE.format(data, data))
                    return result
                if not os.path.exists(img_path + pargs[0] + '.png'):
                    return result
                data = BeautifulReport.img2base(img_path, pargs[0] + '.png')
                print(HTML_IMG_TEMPLATE.format(data, data))
                return result
            return __wrap
        return _wrap
