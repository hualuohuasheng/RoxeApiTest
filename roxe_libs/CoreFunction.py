# -*-coding:utf-8 -*-

from kafka import KafkaConsumer, KafkaProducer
from kafka.structs import TopicPartition
import jpype as jp
import time
import requests
import json
import redis
import yaml
import sshtunnel
import pymysql
import traceback
import logging

from . import Global


logger = logging.getLogger('autolog')


class JavaCall:

    @classmethod
    def start_jvm(cls, ext_classpath):
        jvm_path = jp.getDefaultJVMPath()
        print(jvm_path)
        jvmarg = "-Djava.class.path={}".format(ext_classpath)
        if not jp.isJVMStarted():
            jp.startJVM(jvm_path, '-ea', jvmarg, convertStrings=False)

    @classmethod
    def get_java_class(cls, java_class):
        java_class = jp.JClass(java_class)
        return java_class

    @classmethod
    def close_jvm(cls):
        jp.shutdownJVM()


class Kafka:

    def __init__(self, bootstrap_servers, topics=None, auto_offset_reset='latest', group_id=None, pattern=None):
        self.topics = topics
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.auto_offset_reset = auto_offset_reset  # earliest or latest
        self.pattern = pattern

    def consumer(self):
        consumer = None
        if self.pattern:
            consumer = KafkaConsumer(group_id=self.group_id, bootstrap_servers=self.bootstrap_servers,
                                     auto_offset_reset=self.auto_offset_reset, api_version='2.1.1')
            consumer.subscribe(pattern=self.pattern)
        if self.topics:
            if type(self.topics) == list:
                consumer = KafkaConsumer(group_id=self.group_id, bootstrap_servers=self.bootstrap_servers,
                                         auto_offset_reset=self.auto_offset_reset, api_version='2.1.1')
                consumer.subscribe(self.topics)
            else:
                consumer = KafkaConsumer(self.topics, group_id=self.group_id, bootstrap_servers=self.bootstrap_servers,
                                         auto_offset_reset=self.auto_offset_reset)
        return consumer

    def get_msg_onece(self, consumer, count=10, timeout=30):
        a = TopicPartition(topic=self.topics, partition=0)
        end_offset = consumer.end_offsets([a])[a]
        # print(end_offset)
        seek_offset = end_offset - count if end_offset > count else 0
        consumer.seek(a, seek_offset)
        begin_time = time.time()
        while True:
            time.sleep(0.5)
            msg = consumer.poll(1000)
            if msg:
                res = msg[a]
                break
            if time.time() - begin_time > timeout:
                res = []
                break
        return res

    def producer(self):
        producer = KafkaProducer(bootstrap_servers=self.bootstrap_servers)
        return producer

    def send_msg(self, producer, value, key=None):
        if key is None:
            producer.send(self.topics, value=bytes(value, encoding='utf-8'))
        else:
            producer.send(self.topics, key=bytes(key, encoding='utf-8'), value=bytes(value, encoding='utf-8'))
        producer.flush()


class RedisCall(object):

    def __init__(self, sshhost, sshport, localport=10022, publick_key='/Users/admin/Documents/id_rsa'):
        """
        :param host: redis host
        :param port: redis port
        """
        self.host = sshhost
        self.port = sshport
        self.local_port = localport
        self.remote_bind_address = ('127.0.0.1', self.port)
        self.msg_list = []
        self.ssh_server = sshtunnel.SSHTunnelForwarder((self.host, 22), ssh_username='exonedev', ssh_pkey=publick_key,
                                                       remote_bind_address=self.remote_bind_address,
                                                       local_bind_address=('0.0.0.0', self.local_port))

        self.ssh_server.start()

    @staticmethod
    def connect_redis(host, port):
        pool = redis.ConnectionPool(host=host, port=port)
        connect = redis.Redis(connection_pool=pool, decode_responses=True, socket_keepalive=True, retry_on_timeout=True)
        return connect

    def subscribe_listen_msg(self, channel, server):
        connect = self.connect_redis('127.0.0.1', server.local_bind_port)
        pub = connect.pubsub()
        pub.subscribe(channel)
        res = []
        print(pub.subscribed)
        for msg in pub.listen():
            if msg["type"] == "message":
                d = json.loads(str(msg['data'], encoding='utf-8'))
                res.append(d)
                # if len(d['payload']['BTCUSDD']) == 2:
                #     break
                break  # 收到一条数据，停止订阅消息
        pub.unsubscribe(channel)
        pub.close()
        connect.shutdown()
        return res

    def get_data_by_ssh(self, channel):
        while True:
            time.sleep(1)
            res = []
            try:
                # res = self.subscribe_listen_msg(channel, self.ssh_server)
                connect = self.connect_redis('127.0.0.1', self.ssh_server.local_bind_port)
                pub = connect.pubsub()
                pub.subscribe(channel)
                print(pub.subscribed)
                for msg in pub.listen():
                    if msg["type"] == "message":
                        d = json.loads(str(msg['data'], encoding='utf-8'))
                        res.append(d)
                        break  # 收到一条数据，停止订阅消息
                pub.unsubscribe(channel)
                pub.close()
                connect.shutdown()
                break
            except Exception as e:
                # print(e.args)
                traceback.print_exc()
                pub.unsubscribe(channel)
                pub.close()
                connect.shutdown()

        return res

    def send_data_by_ssh(self, channel, msg):
        time.sleep(1)
        try:
            connect = self.connect_redis('127.0.0.1', self.ssh_server.local_bind_port)
            connect.publish(channel, msg)
            print('send over')
            connect.shutdown()
        except redis.exceptions.ConnectionError:
            traceback.print_exc()
            print('retry send message')
            self.send_data_by_ssh(channel, msg)

    def close(self):
        self.ssh_server.close()


class Mysql:

    def __init__(self, host, port, user, pwd, database, parse_col=False):
        self.host = host
        self.user = user
        self.pwd = pwd
        self.database = database
        self.port = port
        self.connect = None
        self.cursor = None
        self.parse_col = parse_col

    def connect_database(self):
        self.connect = pymysql.connect(host=self.host, port=self.port, user=self.user,
                                       password=self.pwd, db=self.database)
        self.cursor = self.connect.cursor(pymysql.cursors.DictCursor)

    def exec_sql_query(self, exe_sql):
        # cursor = self.connect.cursor(pymysql.cursors.DictCursor)
        self.cursor.execute(exe_sql)
        res = self.cursor.fetchall()
        self.connect.commit()
        # cursor.close()
        if self.parse_col:
            # 格式化列，将数据库中的inner_currency转换为innerCurrency形式
            tmp_res = []
            for info in res:
                tmp_info = {}
                for t_k, t_v in info.items():
                    if '_' in t_k and not t_k.startswith('_') and not t_k.endswith('_'):
                        s_infos = t_k.split('_')
                        parse_key = ''.join([i[0].upper() + i[1:] for i in s_infos])
                        parse_key = parse_key[0].lower() + parse_key[1:]
                        tmp_info[parse_key] = t_v
                    else:
                        tmp_info[t_k] = t_v
                tmp_res.append(tmp_info)
            return tmp_res
        return res

    def disconnect_database(self):
        self.cursor.close()
        self.connect.close()


class StoreMsg:

    def __init__(self):
        self.msgs = []

    def save_message(self, msg):
        # print(msg)
        self.msgs.append(msg)


def getBestPriceInfo(cob_market_data, exclude_e55=False):
    buy_index = len(cob_market_data['asks']) - 1
    buy_info = cob_market_data['asks'][buy_index]
    while exclude_e55 and buy_info['provider'] == 'E55':
        buy_index -= 1
        if buy_info < 0:
            buy_info = []
            break
        buy_info = cob_market_data['asks'][buy_index]

    sell_index = 0
    sell_info = cob_market_data['bids'][sell_index]
    while exclude_e55 and sell_info['provider'] == 'E55':
        sell_index += 1
        if sell_index == len(cob_market_data['bids']):
            sell_info = []
            break
        sell_info = cob_market_data['bids'][sell_index]
    # print(buy_info, sell_info)
    return buy_info, sell_info


def get_msg_from_wsstomp(server, topic, ws_time=2, exclude_e55=False):
    from roxe_libs.WSStomp import Stomp
    store_msg = StoreMsg()
    # 通过websocket订阅获取聚合后的行情数据
    stomp = Stomp(server, sockjs=True, wss=False)
    stomp.connect()
    stomp.subscribe(topic, store_msg.save_message)
    time.sleep(ws_time)
    stomp.unsubscribe(topic)
    stomp.close()
    msg = json.loads(store_msg.msgs[-1][0:-1])
    # print(msg)
    # 获取最好价格的行情数据
    buy_info, sell_info = getBestPriceInfo(msg, exclude_e55)
    return buy_info, sell_info


def get_mark_data_from_redis():
    pass


def get_cfg_info(file='mod.txt'):
    with open(file, 'r') as f:
        info = yaml.safe_load(f)
    case_cfg = {}
    for key in info.keys():
        if key != 'Defined':
            case_cfg[key] = info[key]

    defined_cfg = info['Defined']
    return defined_cfg, case_cfg


def parsse_cfg_info(case_cfg, defined_cfg):
    # print(len(case_cfg))
    res = {}
    for cfg in case_cfg:
        # print(cfg)
        if 'exec' in cfg.keys():
            res['before'] = cfg['exec']
        elif 'send' in cfg.keys():
            res['send_info'] = {}
            if 'kafka' in str(cfg.keys()):
                res['send_info']['type'] = 'kafka'
                for k, v in cfg.items():
                    if 'kafka' in k:
                        res['send_info']['server'] = defined_cfg['kafka'][k]
                        res['send_info']['topic'] = v
                res['send_info']['send'] = cfg['send']
            pass
        elif 'sleep' in cfg.keys():
            res['sleep'] = cfg['sleep']
        elif 'check' in cfg.keys():
            res['check_info'] = {}
            if 'kafka' in str(cfg.keys()):
                res['check_info']['type'] = 'kafka'
                for k, v in cfg.items():
                    if 'kafka' in k:
                        res['check_info']['server'] = defined_cfg['kafka'][k]
                        res['check_info']['topic'] = v
                res['check_info']['c-rule'] = cfg['c-rule']
                if 'count' not in res['check_info']['c-rule'].keys():
                    # 默认为10
                    res['check_info']['c-rule']['count'] = 10
                res['check_info']['check'] = cfg['check']
    # for k, v in res.items():
    #     print(k, v)
    return res


def insert_order(data, host="http://52.68.13.17:22011", params={'signature': '123'}):
    """
    :param data: {"method": "exchange.insertOrder", "params": ["A", {"orderId": "BTCUSDD:test123456",
                "symbol": "BTCUSDD", "orderType": "LIMIT","limitPrice": 9000, "orderQuantity": 0.0001,
                "orderSide": "BUY"}]}
    :param host: like "http://52.68.13.17:22011"
    :param params: like {'signature': '123'}
    :return: return

    """
    url = host + "/exchange/openAPI"
    headers = {'Content-Type': 'application/json', 'cache-control': 'no-cache'}
    res = requests.post(url, headers=headers, params=params, data=json.dumps(data))
    print(res.json())
    return res.json()


def cancel_order(data):
    """
    :param data: {"method": "exchange.cancelOrder", "params": ["A", {"orderId": "BTCUSDD:test123456"}]}
    :return: return response by json
    """

    host = "http://52.68.13.17:22011"
    url = host + "/exchange/openAPI"
    headers = {'Content-Type': 'application/json', 'cache-control': 'no-cache'}
    params = {'signature': '123'}
    res = requests.post(url, headers=headers, params=params, data=json.dumps(data))
    print(res.json())
    return res.json()


async def send_market_data(websocket):
    name = await websocket.recv()
    print("A new client input: {}".format(name))

    greeting = "hello {}!".format(name)

    await websocket.send(greeting)
    print("send {} to {}".format(greeting, name))


def compareDictData(c_info, rec_msg, check_rule, final_res):
    for c_k, c_v in c_info.items():
        if type(c_v) == dict:
            final_res += compareDictData(c_v, rec_msg[c_k], check_rule, final_res)
        else:
            if 'exclude' in check_rule.keys() and c_k in check_rule['exclude']:
                continue
            if 'have' in check_rule.keys() and c_k in check_rule['have']:
                if c_k not in rec_msg.keys():
                    final_res += "Can't find field：{}\ncheck_data:\n{}\nkafka info:\n{}\n".format(c_k, c_info, rec_msg)
                else:
                    continue

            if 'check' in check_rule.keys() and c_k in check_rule['check']:
                if c_k in check_rule['check']:
                    if c_k in rec_msg.keys():
                        if c_v != rec_msg[c_k]:
                            final_res += 'Wrong value in field：{}\ncheck_data:\n{}\nkafka info:\n{}\n'.format(c_k, c_info, rec_msg)
                    else:
                        final_res += "Can't find field：{}\ncheck_data:\n{}\nkafka info:\n{}\n".format(c_k, c_info, rec_msg)

                else:
                    continue
            else:
                if c_k in rec_msg.keys():
                    if c_v != rec_msg[c_k]:
                        final_res += 'Wrong value in field：{}\ncheck_data:\n{}\nkafka info:\n{}\n'.format(c_k, c_info, rec_msg)
                else:
                    final_res += "Can't find field：{}\ncheck_data:\n{}\nkafka info:\n{}\n".format(c_k, c_info, rec_msg)
    # print(final_res)
    return final_res


def get_check_kafka_infos(rec_msgs, check_info, check_key):
    res_msgs_values = [m.value for m in rec_msgs]
    res = []
    # print(check_info)
    for v in res_msgs_values:
        v = json.loads(str(v, encoding='utf-8'))
        if check_key:
            checked = True
            for i in check_key:
                # 如果kafka为订单数据，则check和kafka消息中都包含 result 字段
                if 'result' in check_info.keys():
                    if 'result' in v.keys():
                        checked = (checked and (check_info['result'][i] == v['result'][i]))
                    else:
                        checked = False
                else:
                    if type(v) == dict and i in v.keys():
                        checked = (checked and (check_info[i] == v[i]))
                    else:
                        checked = False
            if checked:
                if 'result' in check_info.keys():
                    res.append(v['result'])
                else:
                    res.append(v)
        else:
            res.append(v)
    # print(res)
    return res


def check_kafka_msg(rec_msgs, expected_info, check_rule):
    final_res = {}
    rec_msgs = rec_msgs[-len(expected_info)::]
    for c_info in expected_info:
        index = expected_info.index(c_info)
        final_res[index] = ''
        select_msgs = get_check_kafka_infos(rec_msgs, c_info, check_rule['key'])
        c_info = c_info['result'] if 'result' in c_info.keys() else c_info
        if select_msgs:
            for c_k, c_v in c_info.items():
                if 'exclude' in check_rule.keys() and c_k in check_rule['exclude']:
                    continue
                if 'have' in check_rule.keys() and c_k in check_rule['have']:
                    for m in select_msgs:
                        if c_k not in m.keys():
                            final_res[index] += "Can't find field：{}\ncheck_data:\n{}\nkafka info:\n{}\n".format(c_k, c_info, m)
                else:
                    if c_info in select_msgs:
                        pass
                    else:
                        for m in select_msgs:
                            if c_k in m.keys():
                                if c_v != m[c_k]:
                                    final_res[
                                        index] += 'Wrong value in field：{}\ncheck_data:\n{}\nkafka info:\n{}\n'.format(c_k, c_info, m)
                            else:
                                final_res[index] += "Can't find field：{}\ncheck_data:\n{}\nkafka info:\n{}\n".format(c_k, c_info, m)
        else:
            final_res[index] += "Can't find check_data:\n{} \nkafka info：\n{}\n".format(c_info, rec_msgs)
    return final_res


def parse_server_from_cfg(info, cfg, defined_cfg, defined_key):
    for k, v in cfg.items():
        if defined_key in k.lower():
            if isinstance(defined_cfg[defined_key], dict):
                info['server'] = defined_cfg[defined_key][k]
            else:
                info['server'] = defined_cfg[k]
            if 'kafka' in defined_key or 'websocket' in defined_key:
                info['topic'] = v
            break
    # print(info)
    return info


def send_kafka_msg(send_info):
    """
    :param send_info: {'type': 'kafka', 'server': '172.17.3.2:9092', 'topic': 'order_outbound',
    'send': [{'35': 'D', '11': 'ABC0123', '55': 'MSFT', '38': 200, '54': '1', '40': 2, '44': 100.01, '49': 'TW', '56': 'INCA', '50': 'trader'}]}

    :return:
    """
    kafka_send = Kafka(send_info['server'], send_info['topic'])
    produce = kafka_send.producer()
    send_msg = send_info['send'] if type(send_info['send']) == list else [send_info['send']]
    for msg in send_msg:
        kafka_send.send_msg(produce, json.dumps(msg))
    produce.close()


def send_fix_msg(send_info, timeout=5, SenderCompID='BANZAI', targetCompId='EXEC'):
    from fixclient.FixMessage import FixMessage
    from fixclient.FixApplication import FixClient

    fixclient = FixClient(timeout)

    for s_msg in send_info['send']:
        # print(s_msg)
        msg = FixMessage()
        msg.set_field(s_msg)
        fixclient.start(msg, send_info, SenderCompID, targetCompId)

    return fixclient


def get_and_check_kafka_msg(check_info, final_res):
    kafka_recv = Kafka(check_info['server'], check_info['topic'], 'earliest')
    counsumer = kafka_recv.consumer()
    rec_msgs = kafka_recv.get_msg_onece(counsumer, check_info['c-rule']['count'])
    counsumer.close()
    # final_res = check_kafka_msg(rec_msgs, check_info['check'], check_info['c-rule'])
    final_res = check_data(rec_msgs, check_info, final_res, 'kafka')
    if 's-var' in check_info.keys():
        for sv_info in check_info['s-var']:
            kafka_parse = json.loads(str(rec_msgs[-1].value, encoding='utf-8'))
            # print(kafka_parse)
            set_global_deps_dict(sv_info, kafka_parse)
    return final_res


def set_global_deps_dict(sv_info, info):
    if sv_info['tag'] in info.keys():
        Global.set_value(sv_info['var'], info[sv_info['tag']])
    else:
        for k, v in info.items():
            if isinstance(v, dict) and sv_info['tag'] in v.keys():
                Global.set_value(sv_info['var'], v[sv_info['tag']])


def get_global_deps_dict(send_info):
    if isinstance(send_info, list):
        for s_info in send_info:
            get_global_deps_dict(s_info)
    else:
        for k, v in send_info.items():
            if isinstance(v, dict):
                get_global_deps_dict(v)
            else:
                if type(v) is str and '$$' in v:
                    send_info[k] = Global.get_value(v)


def select_msgs(rec_msgs, c_info, check_rule, rec_msg_type):
    res = []
    for rec_msg in rec_msgs:

        if rec_msg_type == 'kafka':
            rec_msg = json.loads(str(rec_msg, encoding='utf-8'))
            if len(c_info) == 1 and type(c_info) == dict and 'result' in c_info.keys():
                c_info = c_info['result']
            if len(rec_msg) == 1 and type(rec_msg) == dict and 'result' in rec_msg.keys():
                rec_msg = rec_msg['result']

        if rec_msg_type == 'fix':
            tmp_dict = dict()
            for split_info in rec_msg.split('|'):
                if split_info:
                    tmp_dict[split_info.split('=')[0]] = split_info.split('=')[1]
            for key, value in c_info.items():
                if type(value) != str:
                    c_info[key] = str(value)
            rec_msg = tmp_dict

        res.append(rec_msg)

        if 'key' in check_rule.keys():
            flag = True
            for key in check_rule['key']:
                if key in rec_msg.keys():
                    flag = flag and (rec_msg[key] == c_info[key])
                else:
                    flag = False
            # 如果 没有符合条件的msg则跳过
            if not flag:
                res.remove(rec_msg)
    return res


def check_data(rec_msgs, check_info, final_res, rec_msg_type='url'):
    check_rule = check_info['c-rule']
    expected_info = check_info['check']
    if rec_msg_type == 'kafka':
        rec_msgs = rec_msgs[-len(expected_info)::]
        rec_msgs = [m.value for m in rec_msgs]
    for c_info in expected_info:
        msg_list = select_msgs(rec_msgs, c_info, check_rule, rec_msg_type)
        if msg_list:
            for rec_msg in msg_list:
                final_res += compareDictData(c_info, rec_msg, check_rule, final_res)
        else:
            final_res += "Can't find check_data:\n{}\nkafka info：\n{}\n".format(c_info, rec_msgs)
    # print(final_res)
    return final_res
