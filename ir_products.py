from date_conventions import *
from dateutil.relativedelta import relativedelta
from numpy.random import normal
from math import exp, sqrt

def buildSwap(startDate, maturity, floatingTenor, fixedTenor, fixRate, nominal = 1, swapType = "receiver"):
    ''' With this function we build a Standard Swap using:
    - startDate
    - maturity: the number of months from start date to the end date
    - the payment frequency for the floating leg (number of months between two payments)
    - the payment frequency for the fixed leg
    - the fixRate
    - the nominal in absolute value (default value = 1)
    - the swap type (receiver or payer)
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
    ''' With this function we build a forward swap starting from an existing swap
    It will be used for the swaption
    '''
    # find first floating leg date
    floatIdx = 0
    while swap.floatingLegDates[floatIdx] <= aDate:
        floatIdx = floatIdx + 1
    if floatIdx > 0:
        floatIdx = floatIdx - 1

    # find first fixed leg date
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
    - the set of payment dates (plus the start date) of the floating leg
    - the nominal of the floating leg (+1 if the is receive)
    - the set of payment dates (plus the start date) of the fixed leg
    - the coupon of the fixed leg
    - the nominal of the fixed leg (+1 if the is receive)
    '''
    def __init__(self, floatingLegDates, floatingLegNominal, fixedLegDates, fixRate, fixedLegNominal):
        # check that the two nominals have opposite sign
        if floatingLegNominal * fixedLegNominal > 0:
            raise "Nominal must have opposite sign"

        # store the input variables
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

    # This function simulates the market value (seen as today) of a forward swap. This forward swap
    # is actually the swap itself without the flows occurring before the
    # simulation date. Only ONE simulation is done
    # The simulation is done in the Annuity measure, where the swap rate (the ratio between
    # the floating leg npv and the annuity) is a martingale
    def simulated_npv(self, discountcurve, liborcurve, vol, simuldate):
        # we build the forward swap
        fwdswap = buildForwardSwap(self, simuldate)

        # we compute today's ABSOLUTE value of the floating leg
        floating_leg = fabs(fwdswap.npv_floating_leg(discountcurve, liborcurve))

        # we compute today's ABSOLUTE value of the floating leg
        annuity = fabs(fwdswap.npv_fixed_leg(discountcurve) / fwdswap.fixRate)

        # We compute the swap rate (whose forward in the annuity measure is the same, since is a martingale)
        swaprate = floating_leg / annuity

        # we draw a random variable from a standard normal distribution
        epsilon = normal()

        # We compute the equivalent time in terms of year fraction from today to the simulation date
        # (we need numbers to make computations)
        T = dc_act365(discountcurve.today, simuldate)

        # We calculate the simulated swap rate with the lognormal evolution
        swaprate_simul = swaprate * exp(-0.5 * vol**2 * T + vol * sqrt(T) * epsilon)

        # We compute the value of the swap as if it was a payer swap
        npv_swap = (swaprate_simul - fwdswap.fixRate) * annuity

        # we change sign if it is a receiver swap
        if self.floatingLegNominal < 0:
            npv_swap = npv_swap * -1

        # ok, done, we can return the result
        return npv_swap


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

    # This function compute the value of the swaption by means of a Montecarlo method.
    # It actually invokes multiple times (nruns) the simulated_npv function of the swap class.
    # For each result of this function, it applies the payoff condition, which states that
    # the option will be exercised only in case of a positive value for the swap
    def mc_npv(self, discountCurve, libor, vol, nruns):
        # start with a zero npv
        npv = 0

        # loop nruns times
        for i in range(nruns):
            # simulate the value of the swap
            swap_npv = self.swap.simulated_npv(discountCurve, libor, vol, self.swaptionExpiry)
            # Exercise condition: if met sum the result, otherwise do nothing
            # (which is equivalent to add zero)
            if swap_npv > 0:
                npv = npv + swap_npv

        # Divide by nruns to get the average result of the simulation
        npv = npv / nruns

        # ok, done, return the result
        return npv

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

    reveiver_swaption = Swaption(swap, date(2011, 1, 1))
    print "receicer swaption:", reveiver_swaption.npv(dc, libor, 0.2)

    # we use the function build swap to create the swap
    swap = buildSwap(startSwap, maturity, 6, 12, 0.0506944444444, swapType="payer")
    payer_swaption = Swaption(swap, date(2011, 1, 1))
    print "payer swaption:", payer_swaption.npv(dc, libor, 0.2)

    print "mc receiver swaption: ", reveiver_swaption.mc_npv(dc, libor, 0.2, 1000)
    print "mc payer swaption: ", payer_swaption.mc_npv(dc, libor, 0.2, 1000)
