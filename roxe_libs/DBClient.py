# coding=utf-8
# author: liminglei
# date: 2021-10-13
"""
操作redis的工具类
"""
import sys
import time

import pymysql
import redis
import json
from dbutils.pooled_db import PooledDB


class RedisClient:

    def __init__(self, redisHost, redisPWD, db=0, redisPort=6379):
        self.redisHost = redisHost
        self.redisConn = redis.Redis(self.redisHost, redisPort, password=redisPWD, db=db)

    def getInfoFromKey(self, key, hashKey=None):
        try:
            res = self.redisConn.get(key)
        except redis.exceptions.ResponseError:
            res = self.redisConn.hget(key, hashKey)
        redis_value = None
        if res:
            try:
                redis_value = json.loads(res.decode("utf-8"))
            except json.decoder.JSONDecodeError:
                redis_value = res.decode("utf-8")

        return redis_value

    def updateKey(self, key, value):
        res = self.redisConn.set(key, value)
        assert res is True

    def deleteKey(self, key):
        res = self.redisConn.delete(key)
        assert res is True

    def closeClient(self):
        self.redisConn.close()


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
        self.pool = None

    # def connect_database(self):
    #     self.connect = pymysql.connect(host=self.host, port=self.port, user=self.user,
    #                                    password=self.pwd, db=self.database)
    #     self.cursor = self.connect.cursor(pymysql.cursors.DictCursor)
    #
    # def exec_sql_query(self, exe_sql):
    #     self.cursor.execute(exe_sql)
    #     res = self.cursor.fetchall()
    #     self.connect.commit()
    #     if self.parse_col:
    #         # 格式化列，将数据库中的inner_currency转换为innerCurrency形式
    #         tmp_res = []
    #         for info in res:
    #             tmp_info = {}
    #             for t_k, t_v in info.items():
    #                 if '_' in t_k and not t_k.startswith('_') and not t_k.endswith('_'):
    #                     s_infos = t_k.split('_')
    #                     parse_key = ''.join([i[0].upper() + i[1:] for i in s_infos])
    #                     parse_key = parse_key[0].lower() + parse_key[1:]
    #                     tmp_info[parse_key] = t_v
    #                 else:
    #                     tmp_info[t_k] = t_v
    #             tmp_res.append(tmp_info)
    #         return tmp_res
    #     return res

    def connect_database(self):
        # 多线程下，只创建一个数据库连接池
        if self.pool:
            return
        self.pool = PooledDB(pymysql, maxcached=10, maxconnections=30, blocking=True,
                             host=self.host, port=self.port, user=self.user, password=self.pwd, db=self.database)
    @staticmethod
    def parse_col_key(db_res):
        # 格式化列，将数据库中的inner_currency转换为innerCurrency形式
        tmp_res = []
        for info in db_res:
            tmp_info = {}
            for t_k, t_v in info.items():
                if '_' in t_k and not t_k.startswith('_') and not t_k.endswith('_'):
                    s_infos = t_k.split('_')
                    parse_key = "".join([i[0].upper() + i[1:] for i in s_infos])
                    parse_key = parse_key[0].lower() + parse_key[1:]
                    tmp_info[parse_key] = t_v
                else:
                    tmp_info[t_k] = t_v
            tmp_res.append(tmp_info)
        return tmp_res

    def exec_sql_query(self, exe_sql):
        conn = self.pool.connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        cur.execute(exe_sql)
        res = cur.fetchall()
        time.sleep(0.1)
        if self.parse_col: res = self.parse_col_key(res)
        conn.commit()
        cur.close()
        conn.close()
        return res

    def disconnect_database(self):
        if self.pool:
            # 如果是通过连接池连接数据库，返回
            return
        self.cursor.close()
        self.connect.close()
