# coding=utf-8
# author: Li MingLei
# date: 2021-08-24

"""
一般的全局变量只在当前文件生效，此模块为了跨文件来设置和获取全局变量
用法:
    from extraUtils.globalArg import Global
    Global.setValue("ENV", "UAT")
    Global.getValue("ENV")
"""


class Global:

    _global_dict = {}

    @staticmethod
    def setValue(key, value):
        """ 定义一个全局变量 """
        Global._global_dict[key] = value

    @staticmethod
    def getValue(key):
        """ 获得一个全局变量,不存在则返回None """
        try:
            return Global._global_dict[key]
        except KeyError:
            return None
