# coding=utf-8
# author: Roxe
# date: 2022-06-23

from enum import Enum


class RtsCodEnum(Enum):

    Parameter_Error = ("01100000", "Parameter error")
    Server_Error = ("01100100", "Server error")
    Unknown_Error = ("01100101", "Unknown error")
    Request_Frequency_Too_High = ("01100202", "Request frequency too high")
    Signature_Error = ("01200001", "Signature error")
    Balance_Not_Enough = ("01300001", "Not enough balance to pay the handling fee")
    Order_Status_Information_Error = ("01400001", "Unable to complete the current order status information")
    Not_Found_Routing_Node = ("01500001", "No suitable routing node was found")
    Not_Found_Settlement_Node = ("01500002", "No available settlement node was found")
    Not_Found_Routing = ("01500003", "No correct routing information was found")
    Not_Supported_Currency = ("01600001", "This currency is not supported")
    Amount_Negative_Number = ("01600002", "Amount cannot be a negative number")
    Order_Exists = ("01600101", "Transaction order already exists")
    Order_Not_Exists = ("01600102", "Transaction order does not exist")

    @property
    def code(self):
        return self.value[0]

    @property
    def msg(self):
        return self.value[1]
