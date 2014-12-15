from date_conventions import *
from dateutil.relativedelta import relativedelta

def buildSwap(startDate, maturity, floatingTenor, fixedTenor, fixRate, nominal = 1, swapType = "receiver"):
    ''' With this function we build a Standard Swap using:
    - startDate
    - maturity: the number of months from start date to the end date
    - the payment frequency for the floating leg (number of months between two payments)
    - the payment frequency for the fixed leg
    - the fixRate
    '''
    endDate = startDate + relativedelta(months = maturity)
    floatingDates = dates_generator(floatingTenor, startDate, endDate)
    fixedDates = dates_generator(fixedTenor, startDate, endDate)
    if swapType == "receiver":
        fixedLegNominal = nominal
        floatingLegNominal = - nominal
    elif swapType == "payer":
        fixedLegNominal = - nominal
        floatingLegNominal = nominal
    else:
        raise "SwapType not supported"
    swap = Swap(floatingDates, floatingLegNominal, fixedDates, fixRate, fixedLegNominal)
    return swap

def buildForwardSwap(swap, aDate):
    # find first floating leg date
    floatIdx = 0
    while swap.floatingLegDates[floatIdx] <= aDate:
        floatIdx = floatIdx + 1
    if floatIdx > 0:
        floatIdx = floatIdx - 1

    fixedIdx = 0
    while swap.fixedLegDates[fixedIdx] <= aDate:
        fixedIdx = fixedIdx + 1
    if fixedIdx > 0:
        fixedIdx = fixedIdx - 1

    floatingLegDates = swap.floatingLegDates[floatIdx:]
    fixedLegDates = swap.fixedLegDates[fixedIdx:]

    swap = Swap(floatingLegDates, swap.floatingLegNominal, fixedLegDates, swap.fixRate, swap.fixedLegNominal)
    return swap

class Swap:
    ''' We define the product by its:
    - the tenoe of the underlying libor
    - the relevant dates of the floating leg
    - the relecant dares of the fixed leg
    - the fixRate
    - the floating leg nomimal (scalar)
    - the fixed leg nomimal (scalar)
    '''
    def __init__(self, floatingLegDates, floatingLegNominal, fixedLegDates, fixRate, fixedLegNominal):
        if floatingLegNominal * fixedLegNominal > 0:
            raise "Nominal must have opposite sign"
        self.floatingLegDates = floatingLegDates
        self.fixedLegDates = fixedLegDates
        self.fixRate = fixRate
        self.floatingLegNominal = floatingLegNominal
        self.fixedLegNominal = fixedLegNominal

        # we now compute the accrual periods for the floating leg
        self.floating_tau = []
        for i in range(len(self.floatingLegDates) - 1):
            startPeriod = self.floatingLegDates[i]
            endPeriod = self.floatingLegDates[i+1]
            self.floating_tau.append(dc_act360(startPeriod, endPeriod))

        # we now compute the accrual periods for the fixed leg
        self.fixed_tau = []
        for i in range(len(self.fixedLegDates) - 1):
            startPeriod = self.fixedLegDates[i]
            endPeriod = self.fixedLegDates[i+1]
            self.fixed_tau.append(dc_30e360(startPeriod, endPeriod))

    def npv_floating_leg(self, discountCurve, liborCurve):
        #we now evaluate the floating leg
        floatingleg_npv = 0
        for i in range(len(self.floatingLegDates) - 1):
            startPeriod = self.floatingLegDates[i]
            endPeriod = self.floatingLegDates[i+1]
            # we just consider "future" flows.
            # N.B. Past flows doesn't contribute to the market value
            if endPeriod > discountCurve.today:
                fwd_libor = liborCurve.value(startPeriod)
                df = discountCurve.df(endPeriod)
                floatingleg_npv = floatingleg_npv + df * self.floating_tau[i] * fwd_libor

        # multiply for the nominal and return the value
        return floatingleg_npv * self.floatingLegNominal

    def npv_fixed_leg(self, discountCurve):
        #we now evaluate the fixed leg (no libor curve needed)
        fixed_npv = 0
        for i in range(len(self.fixedLegDates) - 1):
            startPeriod = self.fixedLegDates[i]
            endPeriod = self.fixedLegDates[i+1]
            # we just consider "future" flows.
            # N.B. Past flows doesn't contribute to the market value
            if endPeriod > discountCurve.today:
                df = discountCurve.df(endPeriod)
                fixed_npv = fixed_npv + df * self.fixed_tau[i] * self.fixRate

        # multiply for the nominal and return the value
        return fixed_npv * self.fixedLegNominal

    def npv(self, discountCurve, liborRate):
        floatingleg_npv = self.npv_floating_leg(discountCurve, liborRate)
        fixed_npv = self.npv_fixed_leg(discountCurve)
        npv = fixed_npv + floatingleg_npv
        return npv


from scipy.stats import norm
from math import log, fabs


class Swaption:
    # It's an option that gives the right to enter into a swap:
    # it will be excercised if the market value of the swap will
    # be greater than zero a the swaption expity
    # we need:
    # - a swap
    # - an expiry for the swaption
    def __init__(self, swap, swaptionExpiry):
        self.swaptionExpiry = swaptionExpiry
        # since we will enter into a swap at swaption expiry, this swap
        # will be composed only by flows whose maturity is greater than the
        # expiry of the swap.
        # This is the reason for which we create new swap, which wil be
        # equal to the one passed as an argument to the __init__, but without
        # all of the flows occurring before the swaption expiry.
        # This is done by means of the function buildForwardSwap
        self.swap = buildForwardSwap(swap, swaptionExpiry)

        # The parity of the swap is like the one in an option (1 for the call, -1 for the put).
        # In case of a swaption we have:
        # 1 for the payer
        # -1 for the receiver
        self.parity = 1
        if self.swap.floatingLegNominal < 0:
            self.parity = -1

    # the analogue of the d1 in the B&S formula (or better in the Merton one)
    def d1(self, swapRate, strike, time, vol):
        return (log(swapRate/strike) + 0.5*vol**2*time)/(vol*(time**0.5))

    # the analogue of the d2 in the B&S formula (or better in the Merton one)
    def d2(self, swapRate, strike, time, vol):
        return (log(swapRate/strike) - 0.5*vol**2*time)/(vol*(time**0.5))

    # the price function of the swpation, which by market standards is
    # the Merton formula where:
    # - instead of the discount we have the annuity
    # - instead of the forward of an asset, we have the forward swap rate, which is given by
    #   the ratio of the npv of the floating leg and the npv of the fixed leg
    def npv(self, discountCurve, libor, vol):
        floatNpv = fabs(self.swap.npv_floating_leg(discountCurve, libor))
        annuity = fabs(self.swap.npv_fixed_leg(discountCurve) / self.swap.fixRate)
        swapRate = floatNpv / annuity
        time = dc_act365(discountCurve.today, self.swaptionExpiry)
        d1 = self.d1(swapRate, self.swap.fixRate, time, vol)
        d2 = self.d2(swapRate, self.swap.fixRate, time, vol)
        price = annuity * self.parity * (swapRate * norm.cdf(self.parity * d1) - self.swap.fixRate * norm.cdf(self.parity * d2))
        return price

# example
from ir_curves import DiscountCurve, ForwardLiborCurve

if __name__ == '__main__':
    obsdate = date(2010,1,1)
    pillars = [date(2010,1,1), date(2011,1,1), date(2012,1,1)]
    dfs = [1., 0.95, 0.95]
    dc = DiscountCurve(obsdate, pillars, dfs)

    fwd_pillars = [date(2010,1,1), date(2011,1,1), date(2012,1,1)]
    forwardLibors = [0.05, 0.05, 0.05]
    libor = ForwardLiborCurve(obsdate, fwd_pillars, forwardLibors)

    startSwap = date(2010,1,1)
    maturity = 24
    # we use the function build swap to create the swap
    swap = buildSwap(startSwap, maturity, 6, 12, 0.05069444444445)
    print "swap:", swap.npv(dc, libor)

    swaption = Swaption(swap, date(2011, 1, 1))
    print "receicer swaption:", swaption.npv(dc, libor, 0.2)

    # we use the function build swap to create the swap
    swap = buildSwap(startSwap, maturity, 6, 12, 0.0506944444444, swapType="payer")
    swaption = Swaption(swap, date(2011, 1, 1))
    print "payer swaption:", swaption.npv(dc, libor, 0.2)

