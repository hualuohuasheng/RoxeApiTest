# coding=utf-8
# author: Li MingLei
# date: 2022-04-22

from enum import Enum


class RmnCodEnum(Enum):

    MISS_BODY = ("00100000", "Required request body is missing")
    SN_RETURN_NOT_ALLOWED = ("00100103", "Business exception, Current state of original transaction is not feasible for return by credit SN")
    PN_RETURN_NOT_ALLOWED = ("00100103", "Business exception, Current state of original transaction is not feasible for return by credit PN")
    RMN_RETURN_NOT_ALLOWED = ("00100103", "Business exception, Current state of original transaction is not feasible for return by operation")
    OLD_MSG_NOT_FIND = ("00100103", "Business exception, original message does not exist")
    RETURN_INSTDAGT_INSTGAGT_ERR = ("00100103", "Business exception, txInf.instgAgt or txInf.instdAgt is incorrect")
    AGENT_CHANGE_WRONG = ("00100103", "Business exception, Path does not match the original RCCT")
    VERSION_ERROR = ("00100106", "HTTP Header exception, version is incorrect")
    HEADER_MSGTP_INVALID = ("00100106", "HTTP Header exception, msgTp is not valid")
    HEADER_MSGID_INVALID = ("00100106", "HTTP Header exception, msgId is not valid")

    SIGNATURE_ERROR = ("00200001", "Signature error")
    DECRYPT_ERROR = ("00200002", "request data can't be decrypted")
    APIKEY_ERROR = ("00200006", "Roxe ID and apiKey do not match")
    NO_MATCHED_SN = ("00200007", "No related SN configured for the PN")

    TX_NOT_FIND = ("00400003", "No qualified transaction found")

    ROUTER_NOT_FIND = ("00500003", "No correct routing information was found")
    AGENT_NOT_MATCH = ("00500103", "Creditor Intermediary Agent and Intermediary Agent do not match")

    MSG_NOT_FIND = ("00600105", "No matched message is found")
    NCC_WRONG = ("00600107", "NCC type is wrong")
    SETTLEMENT_AMT_INCORRECT = ("00600110", "Interbank settlement amount is incorrect")
    SETTLEMENT_CCY_INCORRECT = ("00600111", "Interbank settlement currency code is incorrect")
    ORIGNAL_MSG_ERROR = ("00600122", "Original message type error.")

    @property
    def code(self):
        return self.value[0]

    @property
    def msg(self):
        return self.value[1]
