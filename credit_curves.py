# numpy is a numerical package
# (package is the pythonic name for library, which actually is nothing else than a directory containing python files)
import numpy

# to represent dates we use the date class from the package datetime
from datetime import date

# math is mathematical package
import math

# dateutil is a library with functions to manipulate the date class;
# we need a method to shift a date and we will use the function relativedelta
# that is present in this library
from dateutil.relativedelta import relativedelta

# The CreditCurve is a class to obtain by means of an interpolation the survival probabilities
# and the hazard rated at generic dates given a list of know survival probabilities
class CreditCurve:
    # we want to create the DiscountCurve CreditCurve with that will compute ndp(t, T) where
    # t is the "today" (the so called observation date) and T a generic maturity
    # - obsdate: the date at which the curve refers to (i.e. today)
    # - pillars: a list of dates at which the survival probabilities are known
    # - ndps: the known survival probabilities, called Non Default Probabilities (ndp)
    def __init__(self, today, pillars, ndps):
        # the following generates an error that will block the program
        if pillars[0] < today:
            raise "today is greater than the first pillar date"

        # we want to make sure that the first pillar is the observation date and its discount factor is 1.0
        if pillars[0] > today:
            pillars.insert(0, today)
            ndps.insert(0, 1.0)

        # store the input variables
        self.today = today
        self.pillars = pillars
        self.ndps = ndps

        # dates must be converted to numbers, otherwise the interpolation function will not work
        self.pillars_number = map(date.toordinal, pillars)

        # we will linearly interpolate on the logarithm of the discount factors
        self.ln_ndps = map(math.log, ndps)

    # this method interpolated the survival probabilities
    def ndp(self, aDate):
        # we convert the date to a number
        date_number = aDate.toordinal()

        #we use the linear interpolator of the numpy library
        ln_ndp = numpy.interp(date_number, self.pillars_number, self.ln_ndps)

        #we  will have to the take the exponential because we interpolated the logarithms
        ndp = math.exp(ln_ndp)

        # return the resulting discount factor
        return ndp

    # we need a method to derive the hazard rate from the survival probability:
    # we now that h(t) = - d ln(NDP(t)) / dt = - 1 / NDP(t) * d NDP(t) / dt
    # we implement this derivative by an approximation using
    # finite differences:
    # h(t) = - 1 / NPP(t) * [ NDP(t + 1day) - NDP(t)] / 1day
    # we will assume 1day = 1 / 365
    def hazard(self, aDate):
        ndp_1 = self.ndp(aDate)
        ndp_2 = self.ndp(aDate + relativedelta(days=1))
        delta_t = 1.0 / 365.0
        h = - 1.0 / ndp_1 * (ndp_2 - ndp_1) / delta_t
        return h


# example
if __name__ == '__main__':
    obsdate = date(2014,1,1)
    pillars = [date(2015,1,1), date(2019,1,1)]
    ndps = [0.8, 0.4]
    cc = CreditCurve(obsdate, pillars, ndps)
    ndp = cc.ndp(date(2014,7,1))
    print ndp

    hazard = cc.hazard(date(2014,7,1))
    print hazard
