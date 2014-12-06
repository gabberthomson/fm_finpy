from date_conventions import *
from ir_curves import DiscountCurve
from credit_curves import CreditCurve
from dateutil.relativedelta import relativedelta
from scipy.integrate import quad
from datetime import date

class CDS:
    ''' We define the product by its:
    - startDate
    - maturity: the number of months from start date to the end date
    - spread: the running premium received until the default of the underlying issuer
    - recovery: the fraction of the bond expected to be recovered in case of default;
                the protection leg pays 1 - recovery in such a case
    '''
    def __init__(self, startDate, maturity, spread, recovery):
        self.startDate = startDate
        tmpEndDate = startDate + relativedelta(months = maturity)
        # The end date of a CDS must be one of the following dates:
        # 20/03 - 20/06 - 20/09 - 20/12
        # we have to take the one that immediately follows tmpEndDate
        march = date(tmpEndDate.year, 3, 20)
        june = date(tmpEndDate.year, 6, 20)
        sept = date(tmpEndDate.year, 9, 20)
        dec = date(tmpEndDate.year, 12, 20)
        if tmpEndDate <= march:
            self.endDate = march
        elif tmpEndDate <= june:
            self.endDate = june
        elif tmpEndDate <= sept:
            self.endDate = sept
        elif tmpEndDate <= dec:
            self.endDate = dec
        else:
            self.endDate = date(tmpEndDate.year+1, 3, 20)

        # store input parameters
        self.spread = spread
        self.recovery = recovery

        #compute the dates at which the spread is paid, plus the start date of the cds
        self.premiumDates = dates_generator(3, self.startDate, self.endDate)

        # we compute the accruals
        self.tau = []
        for i in range(len(self.premiumDates) - 1):
            startPeriod = self.premiumDates[i]
            endPeriod = self.premiumDates[i+1]
            self.tau.append(dc_act360(startPeriod, endPeriod))

    def premiumleg_npv(self, discountCurve, creditCurve):
        premiumleg_npv = 0
        for i in range(len(self.premiumDates) - 1):
            paydate = self.premiumDates[i+1]
            df = discountCurve.df(paydate)
            ndp = creditCurve.ndp(paydate)
            premiumleg_npv = premiumleg_npv + df * ndp * self.tau[i] * self.spread
        return premiumleg_npv

    def defaultleg_npv(self, discountCurve, creditCurve):
        #we now evaluate the default leg
        # the extremes of the integral are expressed as a number of days
        t0 = self.startDate.toordinal();
        t1 = self.endDate.toordinal();

        integrand = DefaultLegIntegrand(discountCurve, creditCurve, self.recovery)
        integral = quad(integrand.integrand, t0, t1)
        defaultleg_npv = integral[0]
        return defaultleg_npv

    def npv(self, discountCurve, creditCurve):
        npv = self.premiumleg_npv(discountCurve, creditCurve) - self.defaultleg_npv(discountCurve, creditCurve)
        return npv

class DefaultLegIntegrand:
    def __init__(self, discountCurve, creditCurve, recovery):
        self.discountCurve = discountCurve
        self.creditCurve = creditCurve
        self.recovery = recovery

    def integrand(self,  t):
        aDate = date.fromordinal(int(t))
        df = self.discountCurve.df(aDate)
        ndp = self.creditCurve.ndp(aDate)
        # since the extremes are expressed as number of days, the hazard must be expressed in the same unit:
        # therefore it as to be divided by 365 (this is because the one returned by the credit curve is
        # expressed as 1 / years).
        h = self.creditCurve.hazard(aDate) / 365.0
        value = df * ndp * h * (1 - self.recovery)
        return value


# example
if __name__ == '__main__':
    obsdate = date(2010,1,1)
    pillars = [date(2011,1,1), date(2012,1,1)]
    ndps = [0.95, 0.9]
    cc = CreditCurve(obsdate, pillars, ndps)
    # remember to use DIFFERENT lists for different classes (even in this case, where the to dates lists
    # have the same dates!
    irpillars = [date(2011,1,1), date(2012,1,1)]
    dfs = [0.9, 0.8]
    dc = DiscountCurve(obsdate, irpillars, dfs)

    cds = CDS(obsdate, 12, 0.03, 0.4)
    print cds.npv(dc, cc)

