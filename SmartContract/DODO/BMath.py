# -*- coding: utf-8 -*-
import math


class BConst:

    BONE = int(math.pow(10, 18))

    MIN_BOUND_TOKENS = 2
    MAX_BOUND_TOKENS = 8

    MIN_FEE = BONE // 10 ** 6
    MAX_FEE = BONE // 10

    EXIT_FEE = 0
    MIN_WEIGHT = BONE
    MAX_WEIGHT = BONE * 50

    MAX_TOTAL_WEIGHT = BONE * 50
    MIN_BALANCE = BONE // 10 ** 12

    INIT_POOL_SUPPLY = BONE * 100

    MIN_BPOW_BASE = 1
    MAX_BPOW_BASE = (2 * BONE) - 1
    BPOW_PRECISION = BONE // 10 ** 10

    MAX_IN_RATIO = BONE // 2
    MAX_OUT_RATIO = (BONE // 3) + 1


class BNum(BConst):

    def btoi(self, a):
        return a // self.BONE

    def bfloor(self, a):
        return self.btoi(a) * self.BONE

    def badd(self, a, b):
        c = a + b
        assert c >= a, "ERR_ADD_OVERFLOW"
        return c

    def bsub(self, a, b):
        c, flag = self.bsubSign(a, b)
        assert flag is False, "ERR_SUB_UNDERFLOW"
        return c

    def bsubSign(self, a, b):
        if a >= b:
            return a - b, False
        else:
            return b - a, True

    def bmul(self, a, b):
        c0 = a * b
        # assert a == 0 or c0 // a == b, "ERR_MUL_OVERFLOW"
        c1 = c0 + self.BONE // 2
        # assert c1 >= c0, "ERR_MUL_OVERFLOW"
        c2 = c1 // self.BONE
        return c2

    def bdiv(self, a, b):
        assert b != 0, "ERR_DIV_ZERO"
        c0 = a * self.BONE
        assert a == 0 or c0 // a == self.BONE, "ERR_DIV_INTERNAL"
        c1 = c0 + b // 2
        assert c1 >= c0, "ERR_DIV_INTERNAL"
        c2 = c1 // b
        return c2

    def bpowi(self, a, n):
        z = a if n % 2 != 0 else self.BONE
        n = n // 2
        # print(z, n)
        while n != 0:
            a = self.bmul(a, a)
            if n % 2 != 0:
                z = self.bmul(z, a)
            n = n // 2
        return z

    def bpow(self, base, exp):
        assert base >= self.MIN_BPOW_BASE, "ERR_BPOW_BASE_TOO_LOW"
        assert base <= self.MAX_BPOW_BASE, "ERR_BPOW_BASE_TOO_HIGH"

        whole = self.bfloor(exp)
        remain = self.bsub(exp, whole)

        # print(base, self.btoi(whole))
        wholePow = self.bpowi(base, self.btoi(whole))
        # print(wholePow)
        # print(remain)

        if remain == 0:
            return wholePow

        partialResult = self.bpowApprox(base, remain, self.BPOW_PRECISION)
        # print(partialResult)
        return self.bmul(wholePow, partialResult)

    def bpowApprox(self, base, exp, precision):
        a = exp
        x, xneg = self.bsubSign(base, self.BONE)
        term = self.BONE
        sum = term
        negative = False

        i = 1
        while term >= precision:
            bigK = i * self.BONE
            c, cneg = self.bsubSign(a, self.bsub(bigK, self.BONE))
            term = self.bmul(term, self.bmul(c, x))
            term = self.bdiv(term, bigK)
            if term == 0:
                break

            if xneg:
                negative = not negative
            if cneg:
                negative = not negative

            if negative:
                sum = self.bsub(sum, term)
            else:
                sum = self.badd(sum, term)

            i += 1
        return sum


class BMath(BNum):

    """
    //**********************************************************************************************
    // calcSpotPrice                                                                             //
    // sP = spotPrice                                                                            //
    // bI = tokenBalanceIn                ( bI // wI )         1                                  //
    // bO = tokenBalanceOut         sP =  -----------  *  ----------                             //
    // wI = tokenWeightIn                 ( bO // wO )     ( 1 - sF )                             //
    // wO = tokenWeightOut                                                                       //
    // sF = swapFee                                                                              //
    **********************************************************************************************//
    """
    def calcSpotPrice(self, tokenBalanceIn, tokenWeightIn, tokenBalanceOut, tokenWeightOut, swapFee):
        numer = self.bdiv(tokenBalanceIn, tokenWeightIn)
        denom = self.bdiv(tokenBalanceOut, tokenWeightOut)
        ratio = self.bdiv(numer, denom)
        scale = self.bdiv(self.BONE, self.bsub(self.BONE, swapFee))
        spotPrice = self.bmul(ratio, scale)
        return spotPrice

    """
    //**********************************************************************************************
    // calcOutGivenIn                                                                            //
    // aO = tokenAmountOut                                                                       //
    // bO = tokenBalanceOut                                                                      //
    // bI = tokenBalanceIn              //      //            bI             \    (wI // wO) \      //
    // aI = tokenAmountIn    aO = bO * |  1 - | --------------------------  | ^            |     //
    // wI = tokenWeightIn               \      \ ( bI + ( aI * ( 1 - sF )) //              //      //
    // wO = tokenWeightOut                                                                       //
    // sF = swapFee                                                                              //
    **********************************************************************************************//
    """
    def calcOutGivenIn(self, tokenBalanceIn, tokenWeightIn, tokenBalanceOut, tokenWeightOut, tokenAmountIn, swapFee):
        weightRatio = self.bdiv(tokenWeightIn, tokenWeightOut)
        # print(weightRatio)
        adjustedIn = self.bsub(self.BONE, swapFee)
        adjustedIn = self.bmul(tokenAmountIn, adjustedIn)
        y = self.bdiv(tokenBalanceIn, self.badd(tokenBalanceIn, adjustedIn))
        # print(y, weightRatio)
        foo = self.bpow(y, weightRatio)
        bar = self.bsub(self.BONE, foo)
        tokenAmountOut = self.bmul(tokenBalanceOut, bar)
        return tokenAmountOut

    """
    //**********************************************************************************************
    // calcInGivenOut                                                                            //
    // aI = tokenAmountIn                                                                        //
    // bO = tokenBalanceOut               //  //     bO      \    (wO // wI)      \                 //
    // bI = tokenBalanceIn          bI * |  | ------------  | ^            - 1  |                //
    // aO = tokenAmountOut    aI =        \  \ ( bO - aO ) //                   //                 //
    // wI = tokenWeightIn           --------------------------------------------                 //
    // wO = tokenWeightOut                          ( 1 - sF )                                   //
    // sF = swapFee                                                                              //
    **********************************************************************************************//
    """
    def calcInGivenOut(self, tokenBalanceIn, tokenWeightIn, tokenBalanceOut, tokenWeightOut, tokenAmountOut, swapFee):
        weightRatio = self.bdiv(tokenWeightOut, tokenWeightIn)
        diff = self.bsub(tokenBalanceOut, tokenAmountOut)
        y = self.bdiv(tokenBalanceOut, diff)
        print(y, diff, tokenBalanceOut, weightRatio)
        foo = self.bpow(y, weightRatio)
        print(foo)
        foo = self.bsub(foo, self.BONE)
        print(foo)
        tokenAmountIn = self.bsub(self.BONE, swapFee)
        tokenAmountIn = self.bdiv(self.bmul(tokenBalanceIn, foo), tokenAmountIn)
        return tokenAmountIn


if __name__ == "__main__":

    # print(BConst.MIN_FEE)
    # print(BMath().calcSpotPrice(10000100000, 1000000000, 329003290000000, 1000000000, 1000000))
    # print(BMath().calcOutGivenIn(10000100000, 1000000000, 329003290000000, 1000000000, 10000, 1000000))
    print(BMath().calcOutGivenIn(10000150000, 1000000000, 329001647397000, 1000000000, 10000, 1000000))
    # print(BMath().calcInGivenOut(10000100000, 1000000000, 329003290000000, 1000000000, 100000, 1000000))
    # print(BMath().calcInGivenOut(329003290000000, 1000000000, 10000100000, 1000000000, 100000, 1000000))
    print("%.8f" % 3.634e-05)