# -*- coding: utf-8 -*-
import math


class SafeMath:

    @staticmethod
    def mul(a, b):
        if a == 0:
            return 0
        c = a * b
        assert c // a == b, "MUL_ERROR"
        return c

    @staticmethod
    def div(a, b):
        assert b > 0, "DIVIDING_ERROR"
        return a // b

    @staticmethod
    def divCeil(a, b):
        quotient = a // b
        remainder = a - quotient * b
        if remainder > 0:
            return quotient + 1
        else:
            return quotient

    @staticmethod
    def sub(a, b):
        assert b <= a, "SUB_ERROR"
        return a - b

    @staticmethod
    def add(a, b):
        c = a + b
        assert c >= a, "ADD_ERROR"
        return c

    @staticmethod
    def sqrt(x):
        z = x // 2 + 1
        y = x
        while z < y:
            y = z
            z = (x // z + z) // 2
        return y


class DecimalMath(SafeMath):

    one = int(math.pow(10, 18))

    @staticmethod
    def mul(target, d):
        return target * d // DecimalMath.one

    @staticmethod
    def mulCeil(target, d):
        return SafeMath.divCeil(target * d, DecimalMath.one)

    @staticmethod
    def divFloor(target, d):
        return SafeMath.div(target * DecimalMath.one, d)

    @staticmethod
    def divCeil(target, d):
        return SafeMath.divCeil(SafeMath.mul(target, DecimalMath.one), d)


class DODOMath:

    @staticmethod
    def generalIntegrate(V0, V1, V2, i, k):
        """
        :param V0:
        :param V1:
        :param V2:
        :param i:
        :param k:
        :return:

        ΔQ = i(B2-B1)(1-k+k* B0*B0/(B1*B2))
        fairAmount = i(B2-B1)
        V0V0V1V2 = B0*B0/(B1*B2), 进位
        """
        fairAmount = DecimalMath.mul(i, SafeMath.sub(V1, V2))
        V0V0V1V2 = DecimalMath.divCeil(V0 * V0 // V1, V2)
        penalty = DecimalMath.mul(k, V0V0V1V2)
        return DecimalMath.mul(fairAmount, SafeMath.sub(DecimalMath.one, k) + penalty)

    @staticmethod
    def solveQuadraticFunctionForTrade(Q0, Q1, ideltaB, deltaBSig, k):
        # k * Q0 *Q0 /Q1
        kQ02Q1 = DecimalMath.mul(k, Q0) * Q0 // Q1
        b = DecimalMath.mul(SafeMath.sub(DecimalMath.one, k), Q1)
        if deltaBSig:
            b += ideltaB  # (1-k)Q1+i*deltaB
        else:
            kQ02Q1 += ideltaB  # i*deltaB+kQ0^2/Q1

        if b >= kQ02Q1:
            b = SafeMath.sub(b, kQ02Q1)
            minusbSig = True
        else:
            b = kQ02Q1 - b
            minusbSig = False

        # 4(1-k)kQ0^2
        squareRoot = DecimalMath.mul(
            SafeMath.sub(DecimalMath.one, k) * 4,
            DecimalMath.mul(k, Q0) * Q0
        )
        squareRoot = SafeMath.sqrt(b * b + squareRoot)
        denominator = SafeMath.sub(DecimalMath.one, k) * 2
        if minusbSig:
            numerator = b + squareRoot
        else:
            numerator = SafeMath.sub(squareRoot, b)
        # print(f"numerator: {numerator}")
        if deltaBSig:
            return DecimalMath.divFloor(numerator, denominator)
        else:
            return DecimalMath.divCeil(numerator, denominator)

    @staticmethod
    def solveQuadraticFunctionForTarget(V1, k, fairAmount):
        """

        :param V1:
        :param k:
        :param fairAmount:
        :return:
        fairAmount = i*deltaB = (Q2-Q1)*(1-k+kQ0^2/Q1/Q2)
        Assume Q2=Q0, Given Q1 and deltaB, solve Q0
        """
        # v0 = V1+V1*(sqrt-1)/2k
        t0 = DecimalMath.divCeil(DecimalMath.mul(k, fairAmount) * 4, V1)
        t1 = SafeMath.sqrt((t0 + DecimalMath.one) * DecimalMath.one)
        # print(t1)
        premium = DecimalMath.divCeil(SafeMath.sub(t1, DecimalMath.one), k * 2)
        # print(premium)
        res = DecimalMath.mul(V1, DecimalMath.one + premium)
        # print(res)
        return res


# Pricing

# ============ R = 1 cases ============
def ROneSellBaseToken(amount, targetQuoteTokenAmount, oraclePrice, k):
    Q2 = DODOMath.solveQuadraticFunctionForTrade(
        targetQuoteTokenAmount, targetQuoteTokenAmount, DecimalMath.mul(oraclePrice, amount), False, k
    )
    return SafeMath.sub(targetQuoteTokenAmount, Q2)


def ROneBuyBaseToken(amount, targetBaseTokenAmount, oraclePrice, k):
    print(amount, targetBaseTokenAmount)
    # assert amount < targetBaseTokenAmount, "DODO_BASE_BALANCE_NOT_ENOUGH"
    B2 = targetBaseTokenAmount - amount
    payQuoteToken = _RAboveIntegrate(targetBaseTokenAmount, targetBaseTokenAmount, B2, oraclePrice, k)
    return payQuoteToken


# ============ R < 1 cases ============
def RBelowSellBaseToken(amount, quoteBalance, targetQuoteAmount, oraclePrice, k):
    Q2 = DODOMath.solveQuadraticFunctionForTrade(
        targetQuoteAmount, quoteBalance, DecimalMath.mul(oraclePrice, amount), False, k
    )
    return SafeMath.sub(quoteBalance, Q2)


def RBelowBuyBaseToken(amount, quoteBalance, targetQuoteAmount, oraclePrice, k):
    Q2 = DODOMath.solveQuadraticFunctionForTrade(
        targetQuoteAmount, quoteBalance, DecimalMath.mulCeil(oraclePrice, amount), True, k
    )
    # print(f"Q2: {Q2}")
    return SafeMath.sub(Q2, quoteBalance)


def _RBelowBackToOne(storeInfo, oraclePrice):
    spareBase = SafeMath.sub(int(storeInfo["dodos"]["_BASE_BALANCE_"]), int(storeInfo["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"]))
    price = oraclePrice
    fairAmount = DecimalMath.mul(spareBase, price)
    # print(f"fairAmount: {fairAmount}")
    newTargetQuote = DODOMath.solveQuadraticFunctionForTarget(int(storeInfo["dodos"]["_QUOTE_BALANCE_"]),
                                                              storeInfo["dodos"]["_K_"] * int(math.pow(10, 12)), fairAmount)
    # print(f"newTargetQuote: {newTargetQuote}")
    return SafeMath.sub(newTargetQuote, int(storeInfo["dodos"]["_QUOTE_BALANCE_"]))


# ============ R > 1 cases ============

def RAboveBuyBaseToken(amount, baseBalance, targetBaseAmount, oraclePrice, k):
    assert amount < baseBalance, "DODO_BASE_BALANCE_NOT_ENOUGH"
    B2 = baseBalance - amount
    return _RAboveIntegrate(targetBaseAmount, baseBalance, B2, oraclePrice, k)


def RAboveSellBaseToken(amount, baseBalance, targetBaseAmount, oraclePrice, k):
    B1 = baseBalance + amount
    return _RAboveIntegrate(targetBaseAmount, B1, baseBalance, oraclePrice, k)


def _RAboveBackToOne(storeInfo, oraclePrice):
    spareQuote = SafeMath.sub(int(storeInfo["dodos"]["_QUOTE_BALANCE_"]), int(storeInfo["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"]))
    # print("多余的quote: ", spareQuote)
    fairAmount = DecimalMath.divFloor(spareQuote, oraclePrice)
    # print("fairAmount: ", fairAmount)
    newTargetBase = DODOMath.solveQuadraticFunctionForTarget(int(storeInfo["dodos"]["_BASE_BALANCE_"]), storeInfo["dodos"]["_K_"] * int(math.pow(10, 12)), fairAmount)
    # print("newTargetBase: ", newTargetBase)
    return SafeMath.sub(newTargetBase, int(storeInfo["dodos"]["_BASE_BALANCE_"]))


# ============ Helper functions ============

def getExpectedTarget(storeInfo, oraclePrice):
    b = int(storeInfo["dodos"]["_BASE_BALANCE_"])
    q = int(storeInfo["dodos"]["_QUOTE_BALANCE_"])
    bTarget = int(storeInfo["dodos"]["_TARGET_BASE_TOKEN_AMOUNT_"])
    qTarget = int(storeInfo["dodos"]["_TARGET_QUOTE_TOKEN_AMOUNT_"])
    if storeInfo["dodos"]["_R_STATUS_"] == 0:
        return bTarget, qTarget
    elif storeInfo["dodos"]["_R_STATUS_"] == 2:
        payQuoteToken = _RBelowBackToOne(storeInfo, oraclePrice)
        return bTarget, q + payQuoteToken
    elif storeInfo["dodos"]["_R_STATUS_"] == 1:
        payBaseToken = _RAboveBackToOne(storeInfo, oraclePrice)
        return b + payBaseToken, qTarget
    else:
        return [0, 0]


def getMidPrice(storeInfo, oraclePrice):
    baseTarget, quoteTarget = getExpectedTarget(storeInfo, oraclePrice)
    if storeInfo["dodos"]["_R_STATUS_"] == 2:
        R = DecimalMath.divFloor(
            SafeMath.div(SafeMath.mul(quoteTarget, quoteTarget), int(storeInfo["dodos"]["_QUOTE_BALANCE_"])),
            int(storeInfo["dodos"]["_QUOTE_BALANCE_"])
        )
        R = SafeMath.add(
            SafeMath.sub(DecimalMath.one, storeInfo["dodos"]["_K_"]),
            DecimalMath.mul(storeInfo["dodos"]["_K_"], R)
        )
        return DecimalMath.divFloor(oraclePrice, R)
    else:
        R = DecimalMath.divFloor(
            SafeMath.div(SafeMath.mul(baseTarget, baseTarget), int(storeInfo["dodos"]["_BASE_BALANCE_"])),
            int(storeInfo["dodos"]["_BASE_BALANCE_"])
        )
        R = SafeMath.add(
            SafeMath.sub(DecimalMath.one, storeInfo["dodos"]["_K_"]),
            DecimalMath.mul(storeInfo["dodos"]["_K_"], R)
        )
        return DecimalMath.mul(oraclePrice, R)


def _RAboveIntegrate(B0, B1, B2, oraclePrice, k):
    return DODOMath.generalIntegrate(B0, B1, B2, oraclePrice, k)


