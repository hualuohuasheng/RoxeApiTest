# coding=utf-8
# author: Li MingLei
# date: 2021-08-27

"""
本模块定义了适用于整个项目的全局变量名称
"""
# 区分项目的环境配置
environment = "env"

# 通过此变量获取日志生成器的对象名称
logger_name = "log"

# 控制是否将日志级别调整为debug, 打印debug信息
enable_trace = False
# 通过此变量获取连接mysql后的对象
mysql_client = "mysql"

# 通过此变量获取连接mysql的配置信息
mysql_config = "mysql_config"

# 通过此变量获取连接redis后的对象
redis_client = "redis"

# 通过此变量获取连接redis的配置信息
redis_config = "redis_config"

# 多进程并发下执行用例
is_multiprocess = "is_multiprocess"
