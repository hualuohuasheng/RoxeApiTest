# -*- coding:utf-8 -*-

import unittest
import os
import roxe_libs.CoreFunction as sf
import json
from time import sleep
import logging
import subprocess
from roxe_libs import Global
import requests

logger = logging.getLogger('autolog')


class AutoTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):
        self.assertEqual(1, 1)
        pass

    @staticmethod
    def getTestFunc(case_cfg, defined_cfg):
        def func(self):
            cfg = sf.parsse_cfg_info(case_cfg, defined_cfg)
            for key, v in cfg.items():
                if 'before' in key:
                    for cmd in cfg[key]:
                        subprocess.Popen(cmd, shell=True,
                                         stdout=open(f"{os.path.pardir}/log/exec_shell_result.txt", 'w+'))
                if 'send' in key:
                    if cfg[key]['type'] == 'kafka':
                        # pass
                        sf.send_kafka_msg(cfg[key])
                if 'sleep' in key:
                    sleep(cfg[key])
                if 'check' in key:
                    if cfg[key]['type'] == 'kafka':
                        final_res = sf.check_kafka_msg(cfg[key])
            # 输出错误信息
            for key, val in final_res.items():
                if len(val) > 0:
                    self.assertTrue(False, val)
                else:
                    self.assertTrue(True)
        return func

    @staticmethod
    def getTestFunc_fix(case_cfg, defined_cfg):
        def func(self):
            final_res = {'kafka_check': '', 'fix_check': '', 'url_check': ''}
            for cfg in case_cfg:
                # 执行命令
                send_info = dict()
                check_info = dict()
                if 'exec' in cfg.keys():
                    for cmd in cfg['exec']:
                        subprocess.Popen(cmd, shell=True,
                                         stdout=open(f"{os.path.pardir}/log/exec_shell_result.txt", 'w+'))
                if 'websocket' in str(cfg.keys()):
                    send_info['s-var'] = cfg['s-var']
                    send_info = sf.parse_server_from_cfg(send_info, cfg, defined_cfg, 'websocket')
                    # 获取最好价格的行情数据
                    buy_info, sell_info = sf.get_msg_from_wsstomp(send_info['server'], send_info['topic'], 1)
                    for m in send_info['s-var']:
                        set_value = buy_info[m['tag']] if m['condition']['marketdata'] == 'asks' else sell_info[m['tag']]
                        # set_value = set_value if isinstance(set_value, float) else set_value
                        Global.set_value(m['var'], set_value)
                # 发送send消息
                if 'send' in cfg.keys():
                    send_info['send'] = cfg['send']
                    send_info['s-var'] = cfg['s-var'] if 's-var' in cfg.keys() else []
                    # 处理全局变量
                    for s_info in send_info['send']:
                        sf.get_global_deps_dict(s_info)
                    if 'kafka' in str(cfg.keys()):
                        send_info = sf.parse_server_from_cfg(send_info, cfg, defined_cfg, 'kafka')
                        sf.send_kafka_msg(send_info)

                    if 'fix' in str(cfg.keys()).lower():
                        send_info = sf.parse_server_from_cfg(send_info, cfg, defined_cfg, 'fix')
                        send_info['sendCompId'] = defined_cfg['fix']['fix_sendCompId']
                        send_info['targetCompId'] = defined_cfg['fix']['fix_targetCompId']
                        fixclient = sf.send_fix_msg(send_info, 60, send_info['sendCompId'], send_info['targetCompId'])

                    if 'url' in str(cfg.keys()).lower():
                        url_res_list = []
                        for s_info in send_info['send']:
                            header = s_info['header']
                            params = s_info['params'] if 'params' in s_info.keys() else None
                            body = json.dumps(s_info['body']) if 'body' in s_info.keys() else None
                            if cfg['s-rule']['type'] == 'GET':
                                url_res = requests.get(cfg['url'], params=params, headers=header)
                            elif cfg['s-rule']['type'] == 'POST':
                                url_res = requests.post(cfg['url'], data=body, params=params, headers=header)

                            for sv_info in send_info['s-var']:
                                Global.set_value(sv_info['var'], url_res.json()[sv_info['tag']])

                            url_res_list.append(url_res.json())

                if 'sleep' in cfg.keys():
                    sleep(cfg['sleep'])

                # 获取check消息并校验
                if 'check' in cfg.keys():
                    check_info['check'] = cfg['check']
                    check_info['c-rule'] = cfg['c-rule'] if 'c-rule' in cfg.keys() else {}
                    # print(check_info)
                    # 处理全局变量
                    for c_info in check_info['check']:
                        sf.get_global_deps_dict(c_info)

                    if 'kafka' in str(cfg.keys()):
                        check_info = sf.parse_server_from_cfg(check_info, cfg, defined_cfg, 'kafka')
                        if 'count' not in check_info['c-rule'].keys():
                            check_info['c-rule']['count'] = 10  # 默认为10
                        if 's-var' in cfg.keys():
                            check_info['s-var'] = cfg['s-var']
                        final_res['kafka_check'] += sf.get_and_check_kafka_msg(check_info, final_res['kafka_check'])

                    if 'fix' in str(cfg.keys()).lower():
                        check_info = sf.parse_server_from_cfg(check_info, cfg, defined_cfg, 'fix')
                        res = fixclient.get_msg(120)
                        if res is None:
                            final_res['fix_check'] += 'do not receive a fix response'
                        else:
                            final_res['fix_check'] += sf.check_data(res, check_info, final_res['fix_check'], 'fix')
                        fixclient.stop()

                    if 'url' in str(cfg.keys()).lower():
                        if check_info['c-rule']:
                            final_res['url_check'] += sf.check_data(url_res_list, check_info, final_res['url_check'])
                        else:
                            if url_res_list != check_info['check']:
                                final_res['url_check'] += 'url返回结果不正确：\nurl:{url}\ncheck info：\n{check}\nresponse info:\n' \
                                               '{response}'.format(url=cfg['url'],check=check_info['check'], response=url_res_list)

            # 输出错误信息
            assert (123)
            flag = False
            for key, value in final_res.items():
                if len(value) > 0:
                    flag = True
            if flag:
                print("用例出错信息")
                for key, value in final_res.items():
                    print(key+" is error：\n")
                    print(value)
                self.assertTrue(False, "用例执行出错")
            else:
                self.assertTrue(True)

        return func


def generateTestCases(files):

    for file in files:
        try:
            case_file = os.path.splitext(os.path.basename(file))[0]
            # print(case_file)
            cases_cfg = {}
            defined_cfg, cases_cfg = sf.get_cfg_info(file)
            # print(defined_cfg, cases_cfg)
        except Exception as e:
            # print(e.args)
            logger.error(f'配置文件读取失败：{file}')
            logger.error(e.args, exc_info=True)

        # 读取文件获取 defined 和case的配置

        for case, value in cases_cfg.items():
            # print(case)
            setattr(AutoTest, f'test {case_file}: {case}', AutoTest.getTestFunc_fix(value, defined_cfg))


