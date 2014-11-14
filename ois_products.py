from date_conventions import *

class OvernightIndexSwap:
    ''' We define the product by its:
    - startDate
    - endDate
    - floatingLegNominal: the nominal used to compute the flows of the floating leg:
      if positive the flows are received, negative paid
    - fixedLegDates: the union of the start and end dates of all of the flows paid by the fixed leg (each flow has two
                     dates needed to computed the accrual period, the end date of the i-th flow coincides with the start
                     date of the i+1-th flow)
    - fixedRate: the coupon paid/received in the fixed leg
    - fixedLegNominal: the nominal used to compute the flows of the floating leg:
      if positive the flows are received, negative paid
    '''
    def __init__(self, startDate, endDate, floatingLegNominal, fixedLegDates, fixedRate, fixedLegNominal):
        # we want opposite signs for the two nominals: if one leg is paid, the other is received
        # if this is not the case generates an error that will stop the program
        if floatingLegNominal * fixedLegNominal > 0:
            raise "Nominal must have opposite sign"

        # store the input variables
        self.startDate = startDate
        self.endDate = endDate
        self.fixedRate = fixedRate
        self.fixedLegDates = fixedLegDates
        self.floatingLegNominal = floatingLegNominal
        self.fixedLegNominal = fixedLegNominal

    # With this method we compute the value of the floating leg at the observation date of the discount curve
    def npv_floating_leg(self, discountCurve):
        # this formula comes from the fact that for OIS the evaluation method is still the same of
        # the "old" world with just one single curve for forward rate estimation and flow discounting
        floatingleg_npv = discountCurve.df(self.startDate) - discountCurve.df(self.endDate)

        # We multiply the result for the nominal before returning it
        return floatingleg_npv * self.floatingLegNominal

    def npv_fixed_leg(self, discountCurve):
        # we now evaluate the fixed leg
        fixed_npv = 0
        for i in range(len(self.fixedLegDates) - 1):
            startPeriod = self.fixedLegDates[i]
            endPeriod = self.fixedLegDates[i+1]
            tau = dc_act360(startPeriod, endPeriod)
            df = discountCurve.df(endPeriod)
            fixed_npv = fixed_npv + df * tau * self.fixedRate

        # We multiply the result for the nominal before returning it
        return fixed_npv * self.fixedLegNominal

    def npv(self, discountCurve):
        # the npv is the sum of the floating and fixed leg values (taken with their sign)
        floatingleg_npv = self.npv_floating_leg(discountCurve)
        fixed_npv = self.npv_fixed_leg(discountCurve)
        # we sum them (the nominal have opposite sign)
        npv = fixed_npv + floatingleg_npv
        return npv

# This function just makes life easier; it allows to create a standard OIS with less
# parameters because it uses some common conventions:
# - startDate: the start date of the swap
# - maturity: the maturity of the swap express as a number of months (2 year: 24 months)
# - fixedTenor: the frequency of the fixed leg expressed in months: semi-annual payments -> fixedTenor = 6
#               Market convention is 12 months
# - nominal: the absolute value nominal of the swap (1 is 1 Eur for example)
# - swapType: a string that can be "receiver" (it means that the fixed rate is received) or  payer
def buildOIS(startDate, maturity, fixedTenor, fixedRate, nominal = 1, swapType = "receiver"):
    endDate = startDate + relativedelta(months = maturity)
    fixedLegDates = dates_generator(fixedTenor, startDate, endDate)
    if swapType == "receiver":
        fixedLegNominal = nominal
        floatingLegNominal = - nominal
    elif swapType == "payer":
        fixedLegNominal = - nominal
        floatingLegNominal = nominal
    else:
        raise "SwapType not supported"
    ois = OvernightIndexSwap(startDate, endDate, floatingLegNominal, fixedLegDates, fixedRate, fixedLegNominal)
    return ois


from ir_curves import DiscountCurve

if __name__ == '__main__':
    obsdate = date(2010,1,1)
    pillars = [date(2011,1,1), date(2012,1,1)]
    dfs = [0.9, 0.8]
    dc = DiscountCurve(obsdate, pillars, dfs)

    # we build an Overnight Index Swap with 1 year maturity and strike 8%
    startSwap = date(2010,2,1)
    maturity = 12
    ois = buildOIS(startSwap, maturity, 12, 0.08)
    print "Swap NPV:", ois.npv(dc)
