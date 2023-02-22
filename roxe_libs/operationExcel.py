# -*- coding: utf-8 -*-
# 读取Excel表数据
import xlrd
import os
from enum import Enum


# 获取路径下的文件，调用需要传递两个参数替换，否则使用默认的参数
def filePath(fileDir="../test_case_scripts", fileName="data.xlsx"):
    """
    :param fileDir:目录
    :param fileName: 文件名称
    :return: 返回
    """
    return os.path.abspath(os.path.join(os.path.dirname(__file__), fileDir, fileName))


class OperationExcel:

    # 获取shell表
    def getSheet(self, excelFile, index=0):
        book = xlrd.open_workbook(excelFile)  # 前面已经默认将文件参数传递进去了，所以直接调用不用再传参了

        return book.sheet_by_index(index)  # 根据索引获取到sheet表

    # 以列表形式读取出所有数据
    def getExcelData(self, excelFile):
        data = []
        sheet = self.getSheet(excelFile)
        title = sheet.row_values(0)  # 0获取第一行也就是表头
        for row in range(1, sheet.nrows):  # 从第二行开始获取
            row_value = sheet.row_values(row)
            data.append(dict(zip(title, row_value)))  # 将读取出每一条用例作为一个字典存放进列表
        return data


class ExcelValues(Enum):
    CASE_ID = "用例ID"
    CASE_MODULE = "用例模块"
    CASE_NAME = "用例名称"
    CASE_URL = "用例地址"
    CASE_METHOD = "请求方式"
    CASE_TYPE = "请求类型"
    CASE_PARAMS = "请求参数"
    CASE_HEADER = "请求头"
    CASE_PREPOSITION = "前置条件"
    CASE_IS_RUN = "是否执行"
    CASE_CODE = "状态码"
    CASE_RESULT = "期望结果"
    CASE_RESULT_RULE = "结果对比规则"
    CASE_PARAMETERIZED_RULE = "参数化规则"
    CASE_WEBSOCKET_TIMEOUT = "WS超时时间"
    CASE_WEBSOCKET_PARSE = "WS消息格式化规则"
    CASE_RESULT_COMPARE_WITH_DB = "结果和数据库对比"


if __name__ == "__main__":
    print(OperationExcel().getExcelData(filePath()))
