# coding=utf-8
# author: Li MingLei
# date: 2021-08-27
import concurrent.futures
import functools
import logging
import pickle
import queue
import random
import time
from multiprocessing import Pool, Manager, cpu_count, Process, current_process
from roxe_libs.pub_function import setCustomLogger, sendTestResultMail, split_log
from roxe_libs.Global import Global
from roxe_libs.BeautifulReport import BeautifulReport, testResultFields, MirrorStringIO
from roxe_libs import settings
import unittest
import datetime
import argparse
import sys
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed


# 当前脚本所在目录
cur_path = os.path.abspath(os.path.dirname(__file__))

origin_stdout = sys.stdout
origin_stderr = sys.stderr

# 测试用例类的导入配置信息
test_class_config = {
    "RSSApiTest": "RSS.RssApiTest.RSSApiTest",
    "RTSApiTest": "RTS.RtsApiTest_V3.RTSApiTest",
    "RMNApiTest": "RMN.RMNApiTest.RMNApiTest",
    "RMNChannelTest": "RMN.RMNChannelTest.RMNChannelTest",
    "RmnMsgFieldValidationTest": "RMN.RMNValidationTest.RmnMsgFieldValidationTest",
    "RmnBusinessValidationTest": "RMN.RMNValidationTest.RmnBusinessValidationTest",
    "RmnRejectReturnTest": "RMN.RMNValidationTest.RmnRejectReturnTest",
    "RPCApiTest": "RPC.RpcApiTest.RPCApiTest",
    "RTSExceptionTest": "RTS.RTSExceptionTest.RTSExceptionTest",
}

logger = setCustomLogger("test", "./log/apiTest.log", isprintsreen=True, logRedirectHandler=True, logfilemod="a")
Global.setValue(settings.logger_name, logger.name)
Global.setValue(settings.enable_trace, True)
_class_dict = {}


class ProcessJob(Process):

    def __init__(self, job_queue, res_queue, worker_size, env, log_name):
        super(ProcessJob, self).__init__()
        self.job_queue = job_queue
        self.res_queue = res_queue
        self.worker_size = worker_size
        self.env = env
        self.log_name = log_name

        self.free_worker_size = worker_size

    def run(self):
        Global.setValue(settings.environment, self.env)
        Global.setValue(settings.is_multiprocess, True)
        cur_pid = current_process().pid
        logger.warning(f"子进程启动: {cur_pid}")
        sub_queue = queue.Queue()
        log_name = self.log_name
        workers = []
        res_num = 0
        add_new_worker = True
        stop_flag = False
        while 1:
            if add_new_worker:
                case_job = self.job_queue.get()

                if case_job != "end":
                    # f_case = unittest.TestLoader().loadTestsFromName(case_loader_name)
                    f_case = pickle.loads(case_job)
                    logger.info(f"准备执行用例: {f_case}, {add_new_worker}")
                    case = CaseThread(f_case, sub_queue, log_name)
                    t = threading.Thread(target=case.run)
                    t.start()
                    workers.append(t)
                    sleep_time = 0.5 * random.randint(1, 3)
                    time.sleep(sleep_time)
                    # 增加延迟时间，防止瞬时tps太大，影响用例运行的结果
                    if isinstance(sys.stderr, MirrorStringIO):
                        if threading.main_thread().ident not in sys.stderr.mirror_log:
                            sys.stderr.mirror_log[threading.main_thread().ident] = ""
                    sys.stderr.write(f"线程{t.ident}已启动\n")
                    res_num += 1
                else:
                    stop_flag = True
                if len(workers) >= self.worker_size:
                    add_new_worker = False
            # 不添加新的job，等待有job完成，再添加新的job
            if not add_new_worker:
                wait_free = True
                while wait_free:
                    for t in workers:
                        if not t.is_alive():
                            wait_free = False
                            break
                add_new_worker = True

            if stop_flag:
                sys.stderr.write(f"任务队列接收到结束标志，等待任务执行完成: {cur_pid}\n")
                for t in workers:
                    t.join()
                    f_res = sub_queue.get()
                    self.res_queue.put(f_res)
                break

        sys.stderr.write(f"子进程结束: {cur_pid}\n")

    def run_old(self):
        Global.setValue(settings.environment, self.env)
        Global.setValue(settings.is_multiprocess, True)
        cur_pid = current_process().pid
        logger.info(f"子进程启动: {cur_pid}")
        sub_queue = queue.Queue()
        log_name = self.log_name
        workers = []
        add_new_worker = True
        stop_flag = False
        work_pool = concurrent.futures.ThreadPoolExecutor(max_workers=self.worker_size)
        while 1:
            if add_new_worker:
                case_job = self.job_queue.get()
                if case_job == "end":
                    stop_flag = True
                else:
                    f_case = pickle.loads(case_job)
                    logger.info(f"准备执行用例: {f_case}, {add_new_worker}")
                    case = CaseThread(f_case, sub_queue, log_name)
                    task = work_pool.submit(case.run)
                    task.add_done_callback(case.error_callback)
                    workers.append(task)
                    # 增加延迟时间，防止瞬时tps太大，影响用例运行的结果
                    if isinstance(sys.stderr, MirrorStringIO):
                        if threading.main_thread().ident not in sys.stderr.mirror_log:
                            sys.stderr.mirror_log[threading.main_thread().ident] = ""

            if len(workers) >= self.worker_size:
                add_new_worker = False

            if not add_new_worker:
                wait_free = True
                while wait_free:
                    for t in workers:
                        if t.done():
                            wait_free = False
                            break
                add_new_worker = True

            if stop_flag:
                sys.stderr.write(f"任务队列接收到结束标志，等待任务执行完成: {cur_pid}\n")
                for f in concurrent.futures.as_completed(workers):
                    f_r = f.result()
                    self.res_queue.put(f_r)
                    # f_res = sub_queue.get()
                    # self.res_queue.put(f_res)
                break
        work_pool.shutdown()


class CaseThread:

    def __init__(self, case_suite: unittest.TestSuite, res_queue, logger_name):
        # super().__init__()
        self.case_suite = case_suite
        self.queue = res_queue
        self.logger_name = logger_name
        self.logger = logging.getLogger(self.logger_name)
        self.e = None
        self.thread_state = 0
        self.thread_exception = ""

    def run(self):
        try:
            new_report = BeautifulReport(self.case_suite, log_name=self.logger_name, verbosity=2)
            new_report.title = "自动化测试报告"
            new_report.startTestRun()
            new_report.suites.run(result=new_report)
            new_report.stopTestRun(new_report.title)
            split_log(new_report.fields)
            self.queue.put(new_report.fields)
            return new_report.fields
        except Exception as e:
            err_msg = testResultFields()
            err_msg["testFail"] = 1
            err_msg["testAll"] = 1
            err_msg["testResult"] = [{
                "methodName": f"error case: {self.case_suite}",
                "log": e.args[1]
            }]
            self.queue.put(err_msg)
            # self.e = e
            # self.thread_state = 1
            # self.thread_exception = e.args[1]

    def error_callback(self, future):
        exp = future.exception()
        if exp:
            self.logger.error(str(exp), exc_info=True)


class RunCase:
    load_strategy = "keyword_load"  # 默认查找用例的策略名称
    class_config = {}
    find_case_strategy = {}
    # 保存测试结果的数据结构，在生成html报告发送邮件时有用到
    testResultDict = testResultFields()

    def __init__(self, case_classes: dict, env="bjtest", debug=True, argv=None):
        self.env = env
        self.debug = debug
        Global.setValue(settings.environment, env)
        self.report_dir = os.path.abspath(os.path.join(cur_path, "TestReports"))
        self.reportPath = None
        self.start_time = None
        self.task_queue = None
        self.multi_run = False
        self.run_suite = unittest.TestSuite()
        self.use_cpu_num = None
        self.thread_workers = 1
        self.parser = None
        self.argv = argv if argv else sys.argv[1::]
        self.mail_receiver = dict()
        self._initArgs()
        # 默认的用例加载策略
        self.registerStrategy(self.load_strategy, self.singleLoadCase)
        for case_class, class_loader_name in case_classes.items():
            self.registerTestClass(case_class, class_loader_name)
        # 初始化邮件接收方
        self.initMailConfig()

    def initMailConfig(self):
        self.mail_receiver = {"mail_recievers": ["mingleili@jiujiutech.cn"], "env": self.env}
        if not self.debug:
            self.mail_receiver["mail_recievers"] = [
                "qcroxe@jiujiutech.cn",
                "shuqiangwang@jiujiutech.cn",
                "weitang@jiujiutech.cn",
                "jianxinlu@jiujiutech.cn",
                "yangzhou@jiujiutech.cn",
                "yanqingli@jiujiutech.cn",
                "gaoxianghe@jiujiutech.cn",
            ]

    def _initArgs(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("-t", "--testClass", help="测试类, 多个类以','分隔", type=str, dest="testClass", action="store")
        parser.add_argument("-c", "--case", help="测试用例查找的关键字, 执行多个用例以','分隔", type=str, dest="caseKey", default="", action="store")
        parser.add_argument("-r", help="执行用例的策略, 现支持: multi_run、debug_class、debug、multi_thread_pool、pool_pool", type=str, dest="runWay", default="debug", action="store")
        self.parser = parser.parse_args(self.argv)
        logger.debug(f"参数为: testClass: {self.parser.testClass} caseKey:{self.parser.caseKey} runWay:{self.parser.runWay}")

    def registerTestClass(self, test_class, name):
        """
        注册用例类的方法
        :param test_class:
        :param name:
        """
        self.class_config[test_class] = name

    def registerStrategy(self, strategy_name, strategy_func):
        """
        注册加载测试用例类策略的方法
        :param strategy_name: 加载用例的策略名称
        :param strategy_func: 加载用例的策略方法
        :return:
        """
        self.find_case_strategy[strategy_name] = strategy_func

    @staticmethod
    def singleLoadCase(all_cases, key_val, class_val=""):
        """
        根据关键字中找出想要的case放入要执行的测试suite中
        :param all_cases: 必须为TestCase组成的suite类，不能是嵌套的suite类
        :param key_val: 搜索用例的关键字
        :param class_val: 搜索测试类的关键字
        """
        return [c for c in all_cases for key in key_val.split(",") if key in str(c) and class_val in str(c)]

    def loadCase(self, test_class, case_key="", load_strategy=None):
        find_cases = []
        loader = unittest.TestLoader()
        for each_class in test_class.split(","):
            each_find = loader.loadTestsFromName(self.class_config[each_class])
            if loader.errors:
                sys.stderr.write("".join([str(i) for i in loader.errors]))
                sys.exit(f"load case error: {each_class}")
            for i in iter(each_find):
                find_cases.append(i)

        if load_strategy is None:
            # 默认使用注册的用例查找策略
            load_strategy = self.load_strategy
        # 查找加载用例的策略
        try:
            stra_func = self.find_case_strategy[load_strategy]
        except KeyError:
            raise ValueError("找不到对应的查找用例策略")

        if case_key:
            find_cases = stra_func(find_cases, case_key)
        self.run_suite.addTests(find_cases)

    def runCaseWithTextRunner(self):
        runner = unittest.TextTestRunner(verbosity=2)
        self.start_time = datetime.datetime.now()
        runner.run(self.run_suite)

    def runCaseWithHtmlReport(self, test_class):
        self.start_time = datetime.datetime.now()
        logger.info(f"{test_class}开始运行")
        module_name = test_class[0].rstrip("Test") if isinstance(test_class, list) else test_class.rstrip("Test")
        reportName = "{}DailyTestReport{}.html".format(module_name, self.start_time.strftime('%Y-%m-%d_%H-%M-%S'))
        report = BeautifulReport(self.run_suite, log_name=logger.name, verbosity=2)
        report.startTestRun()
        report.report("自动化测试报告", reportName, self.report_dir, callback=split_log)
        self.testResultDict = report.fields
        self.reportPath = os.path.join(self.report_dir, reportName)
        self.sendEmail(test_class)

    def init_run_cpu_num(self, cpu_num=1):
        self.use_cpu_num = min(os.cpu_count(), cpu_num)

    def init_run_thread_workers(self, run_case_num):
        self.thread_workers = min(os.cpu_count() * 4, run_case_num)

    def runCaseWithThreadPool(self, test_class):
        Global.setValue(settings.is_multiprocess, True)
        from queue import Queue
        run_case_num = self.run_suite.countTestCases()
        self.init_run_cpu_num()
        self.init_run_thread_workers(run_case_num)
        future_tasks = []
        pool_queue = Queue()
        self.start_time = datetime.datetime.now()
        logger.info(f"{test_class}开始运行{run_case_num}个用例")
        logger.warning(f"准备开启{self.thread_workers}个线程的线程池")
        nm = self.thread_workers
        with ThreadPoolExecutor(max_workers=self.thread_workers) as t_pool:
            for i, c in enumerate(self.run_suite):
                # if isinstance(sys.stderr, io.StringIO):
                #     sys.stderr.mirror_log[threading.current_thread().ident] = ""
                new_suite = unittest.TestSuite([c])
                case = CaseThread(new_suite, pool_queue, logger.name)
                future = t_pool.submit(case.run)
                future.add_done_callback(case.error_callback)
                future_tasks.append(future)
                time.sleep(0.5)
            # 等待所有任务执行完成
            for future in as_completed(future_tasks):
                future.result()
                nm -= 1

        end_time = datetime.datetime.now().timestamp()
        total_time = str(round(end_time - self.start_time.timestamp(), 6)) + 's'
        parse_start_time = self.start_time.strftime('%Y-%m-%d_%H-%M-%S')
        # 生成html报告
        module_name = test_class.split(",")[0].rstrip("Test") if "," in test_class else test_class.rstrip("Test")
        self.testResultDict["testName"] = module_name
        self.testResultDict["beginTime"] = parse_start_time
        self.testResultDict["totalTime"] = total_time
        # 恢复标准io流
        sys.stdout = origin_stdout
        sys.stderr = origin_stderr
        print("准备获取数据..\n")
        print(f"final left: {nm}")
        while run_case_num > 0:
            # 从队列中获取数据
            case_result = pool_queue.get()
            # print(case_result)
            self.testResultDict["testPass"] += case_result["testPass"]
            self.testResultDict["testAll"] += case_result["testAll"]
            self.testResultDict["testFail"] += case_result["testFail"]
            self.testResultDict["testSkip"] += case_result["testSkip"]
            self.testResultDict["testResult"] += case_result["testResult"]
            run_case_num -= 1
        self.testResultDict["testResult"] = sorted(self.testResultDict["testResult"],
                                                   key=lambda testResult: testResult["methodName"])
        reportName = "{}DailyTestReport{}.html".format(module_name, parse_start_time)
        # 多进程下生成html报告
        report = BeautifulReport(unittest.TestSuite())
        report.report_path = os.path.abspath(self.report_dir)
        report.filename = reportName
        report.output_report(out_res=self.testResultDict)
        self.reportPath = os.path.join(self.report_dir, reportName)

        self.sendEmail(test_class)

    def runCaseWithThread(self, test_class):
        Global.setValue(settings.is_multiprocess, True)
        from queue import Queue
        run_case_num = self.run_suite.countTestCases()
        self.init_run_cpu_num()
        self.init_run_thread_workers(run_case_num)
        tasks = []
        pool_queue = Queue()
        self.start_time = datetime.datetime.now()
        logger.info(f"{test_class}开始运行{run_case_num}个用例")
        logger.warning(f"准备开启{self.thread_workers}个线程的")
        for i, c in enumerate(self.run_suite):
            new_suite = unittest.TestSuite([c])
            case = CaseThread(new_suite, pool_queue, logger.name)
            t = threading.Thread(target=case.run)
            tasks.append(t)
            t.start()
        for t in tasks:
            t.join()

        end_time = datetime.datetime.now().timestamp()
        total_time = str(round(end_time - self.start_time.timestamp(), 6)) + 's'
        parse_start_time = self.start_time.strftime('%Y-%m-%d_%H-%M-%S')
        # 生成html报告
        module_name = test_class.split(",")[0].rstrip("Test") if "," in test_class else test_class.rstrip("Test")
        self.testResultDict["testName"] = module_name
        self.testResultDict["beginTime"] = parse_start_time
        self.testResultDict["totalTime"] = total_time

        while run_case_num > 0:
            # 从队列中获取数据
            case_result = pool_queue.get()
            self.testResultDict["testPass"] += case_result["testPass"]
            self.testResultDict["testAll"] += case_result["testAll"]
            self.testResultDict["testFail"] += case_result["testFail"]
            self.testResultDict["testSkip"] += case_result["testSkip"]
            self.testResultDict["testResult"] += case_result["testResult"]
            run_case_num -= 1
        self.testResultDict["testResult"] = sorted(self.testResultDict["testResult"],
                                                   key=lambda testResult: testResult["methodName"])
        reportName = "{}DailyTestReport{}.html".format(module_name, parse_start_time)
        # 多进程下生成html报告
        report = BeautifulReport(unittest.TestSuite())
        report.report_path = os.path.abspath(self.report_dir)
        report.filename = reportName
        report.output_report(out_res=self.testResultDict)
        self.reportPath = os.path.join(self.report_dir, reportName)
        # 恢复标准io流
        sys.stdout = origin_stdout
        sys.stderr = origin_stderr
        # self.sendEmail(test_class)

    @staticmethod
    def process_case(case_loader_name, env, res_queue):
        # 在进程中初始化环境变量，加载测试类文件
        Global.setValue(settings.environment, env)
        Global.setValue(settings.is_multiprocess, True)
        # 当前进程查找对应的用例
        f_case = unittest.TestLoader().loadTestsFromName(case_loader_name)
        report = BeautifulReport(f_case, log_name=logger.name, verbosity=2)
        report.title = "自动化测试报告"
        report.startTestRun()
        report.suites.run(result=report)
        report.stopTestRun(report.title)
        split_log(report.fields)
        c_res = report.fields
        res_queue.put(c_res)

    def runCaseWithProcessPool(self, test_class, pool_num=None):
        """
        并发运行用例是使用
        :param test_class: 执行测试的用例类
        :param pool_num: 指定开启的进程池中processes数量
        """
        self.start_time = datetime.datetime.now()
        parse_start_time = self.start_time.strftime('%Y-%m-%d_%H-%M-%S')
        logger.info(f"{test_class}于{parse_start_time}开始运行")

        pools = []
        if pool_num is None:
            # 默认使用当前cpu的内核数-1
            pool_num = cpu_count()
        pool = Pool(processes=pool_num)
        pool_queue = Manager().Queue()
        for c_i, c in enumerate(self.run_suite):
            case_name, case_class = str(c).split()
            case_class = case_class.split(".")[-1].strip(")")
            case_loader_name = self.class_config[case_class] + "." + case_name
            p = pool.apply_async(self.process_case, args=(case_loader_name, self.env, pool_queue,))
            pools.append(p)
        pool.close()
        # 进程执行报错时，抛出到前台
        for p in pools:
            p.get()
        pool.join()
        print("run finish..")
        end_time = datetime.datetime.now().timestamp()
        total_time = str(round(end_time - self.start_time.timestamp(), 6)) + 's'

        # 生成html报告
        module_name = test_class.split(",")[0].rstrip("Test") if "," in test_class else test_class.rstrip("Test")
        self.testResultDict["testName"] = module_name
        self.testResultDict["beginTime"] = parse_start_time
        self.testResultDict["totalTime"] = total_time
        while not pool_queue.empty():
            # 从队列中获取数据
            case_result = pool_queue.get()
            # print("从子进程中获取执行结果: ", case_result)
            self.testResultDict["testPass"] += case_result["testPass"]
            self.testResultDict["testAll"] += case_result["testAll"]
            self.testResultDict["testFail"] += case_result["testFail"]
            self.testResultDict["testSkip"] += case_result["testSkip"]
            self.testResultDict["testResult"] += case_result["testResult"]
        self.testResultDict["testResult"] = sorted(self.testResultDict["testResult"],
                                                   key=lambda testResult: testResult["methodName"])
        reportName = "{}DailyTestReport{}.html".format(module_name, parse_start_time)
        # 多进程下生成html报告
        report = BeautifulReport(unittest.TestSuite())
        report.report_path = os.path.abspath(self.report_dir)
        report.filename = reportName
        report.output_report(out_res=self.testResultDict)
        self.reportPath = os.path.join(self.report_dir, reportName)
        # 恢复标准io流
        sys.stdout = origin_stdout
        sys.stderr = origin_stderr
        self.sendEmail(test_class)

    def runCaseWithProcessPoolPThreadPool(self, test_class):
        """
        并发运行用例是使用
        :param test_class: 执行测试的用例类
        """
        self.start_time = datetime.datetime.now()
        parse_start_time = self.start_time.strftime('%Y-%m-%d_%H-%M-%S')
        logger.info(f"{test_class}于{parse_start_time}开始运行")

        run_case_num = self.run_suite.countTestCases()
        cpu_num = min(run_case_num, 4)
        self.init_run_cpu_num(cpu_num)
        m = Manager()
        job_queue = m.Queue()
        res_queue = m.Queue()
        pools = []
        # 开启各个进程的处理程序，等待任务队列
        for i in range(self.use_cpu_num):
            process_scheduler = ProcessJob(job_queue, res_queue, 8, self.env, logger.name)
            process_scheduler.start()
            pools.append(process_scheduler)
        # 将用例放入任务队列
        for c_i, c in enumerate(self.run_suite):
            new_suite = unittest.TestSuite([c])
            pickle_case = pickle.dumps(new_suite)
            job_queue.put(pickle_case)
        # 将结束标志放入任务队列
        for i in range(run_case_num):
            job_queue.put("end")
        # 进程执行报错时，抛出到前台
        for p in pools:
            print(p.is_alive())
            p.join()

        # 恢复标准io流
        sys.stdout = origin_stdout
        sys.stderr = origin_stderr
        print("run finish..")
        end_time = datetime.datetime.now().timestamp()
        total_time = str(round(end_time - self.start_time.timestamp(), 6)) + 's'

        # 生成html报告
        module_name = test_class.split(",")[0].rstrip("Test") if "," in test_class else test_class.rstrip("Test")
        self.testResultDict["testName"] = module_name
        self.testResultDict["beginTime"] = parse_start_time
        self.testResultDict["totalTime"] = total_time

        while run_case_num > 0:
            # 从队列中获取数据
            case_result = res_queue.get()
            # print(case_result)
            self.testResultDict["testPass"] += case_result["testPass"]
            self.testResultDict["testAll"] += case_result["testAll"]
            self.testResultDict["testFail"] += case_result["testFail"]
            self.testResultDict["testSkip"] += case_result["testSkip"]
            self.testResultDict["testResult"] += case_result["testResult"]
            run_case_num -= 1
        # print(self.testResultDict)
        self.testResultDict["testResult"] = sorted(self.testResultDict["testResult"], key=lambda x: x["methodName"])
        reportName = "{}DailyTestReport{}.html".format(module_name, parse_start_time)
        # 多进程下生成html报告
        report = BeautifulReport(unittest.TestSuite())
        report.report_path = os.path.abspath(self.report_dir)
        report.filename = reportName
        report.output_report(out_res=self.testResultDict)
        self.reportPath = os.path.join(self.report_dir, reportName)

        self.sendEmail(test_class)

    def sendEmail(self, test_class):
        mailTitle = "{} {} Daily Test Report {}".format(self.env, self.testResultDict["testName"], self.start_time.strftime("%y-%m-%d"))

        testClassRelationship = {}
        if isinstance(test_class, list):
            for t_c in test_class:
                testClassRelationship[t_c] = t_c.rstrip("Test")
        else:
            testClassRelationship[test_class] = self.testResultDict["testName"]
        sendTestResultMail(
            self.mail_receiver, mailTitle, self.reportPath, self.testResultDict, testClassRelationship, logger.name,
            mail_user="mingleili@jiujiutech.cn", mail_pass="xxxxxx"
        )

    def run(self, test_class, case_key="", strategy="debug", load_case_strategy=None):
        """
        执行用例的主方法
        :param test_class: 运行的测试类
        :param case_key: 需要进行筛选加载的case关键字
        :param strategy: 运行策略：multi_run[并发执行, 结果发送邮件]、debug_class[非并发运行, 结果发送邮件]、默认为调试用
        :param load_case_strategy: 用例加载策略：默认为关键字查找
        :return:
        """
        # 加载用例
        self.loadCase(test_class, case_key, load_case_strategy)
        logger.debug(f"准备运行的用例: {self.run_suite}")

        run_strategy = {
            "pool_pool": functools.partial(self.runCaseWithProcessPoolPThreadPool, test_class=test_class),
            "multi_thread_pool": functools.partial(self.runCaseWithThreadPool, test_class=test_class),
            "debug_class": functools.partial(self.runCaseWithHtmlReport, test_class=test_class),
            "debug": self.runCaseWithTextRunner,
        }
        if strategy not in run_strategy.keys():
            raise ValueError(f"当前仅支持的运行策略: {[i for i in run_strategy.keys()]}")
        run_strategy[strategy]()


if __name__ == "__main__":

    # run_client = RunCase(test_class_config, "prod")
    # run_client = RunCase(test_class_config, "sandbox")
    # run_client = RunCase(test_class_config, "bjtest")
    run_client = RunCase(test_class_config, "uat")
    if sys.argv[1:]:
        # 从命令行启动执行用例
        run_client.run(run_client.parser.testClass, run_client.parser.caseKey, run_client.parser.runWay)
        sys.exit(0)

    # 并发执行测试类，一般用于回归
    # run_client.run("RmnMsgFieldValidationTest,RmnBusinessValidationTest,RmnRejectReturnTest", "", strategy="multi_run")

    # 调试测试脚本, 单跑
    # run_client.run("RMNApiTest", "", "multi_thread_pool")
    # run_client.run("RmnRejectReturnTest",  "test_04,test_05", "multi_thread_pool")
    # run_client.run("RMNApiTest", "test_03,test_02,test_04", "pool_pool")
    # run_client.run("RMNApiTest", "test_00,test_01", "pool_pool")
    # run_client.run("RMNApiTest", "test_001,test_002,test_003,test_004,test_007")
    # run_client.run("RMNApiTest", "test_003,test_008,test_009,test_024,test_035,test_075,test_095,test_184,test_185,test_186,test_187,test_152", "multi_thread_pool")
    # run_client.run("RMNApiTest", "test_28,test_29", "multi_thread_pool")
    # run_client.run("RMNApiTest", "test_023,test_030,test_075,test_095")
    run_client.run("RMNApiTest", "test_023")
    # run_client.run("RMNChannelTest", "test_099_")
    # run_client.run("RMNChannelTest", "test_121_")
    # run_client.run("RMNChannelTest", "test_093_")
    # run_client.run("RmnRejectReturnTest", "test_031")
    # run_client.run("RmnRejectReturnTest", "test_065")
    # run_client.run("RTSApiTest", "test_048")
    # run_client.run("RmnRejectReturnTest", "", "multi_thread_pool")
    # run_client.run("RmnMsgFieldValidationTest", "test_178")
    # run_client.run("RMNApiTest", "test_001,test_002,test_003",  "pool_pool")
    # run_client.run("RMNApiTest", "test_00", "multi_thread_pool")
    # run_client.run("RmnBusinessValidationTest", "test_060")

