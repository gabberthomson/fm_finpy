# numpy is a numerical package
# (package is the pythonic name for library, which actually is nothing else than a directory containing python files)
import numpy

# to represent dates we use the date class from the package datetime
from datetime import date

# math is mathematical package
import math

class DiscountCurve:
    # we want to create the DiscountCurve class with that will compute df(t, T) where
    # t is the "today" (the so called observation date) and T a generic maturity
    # - obsdate: the date at which the curve refers to (i.e. today)
    # - pillars: a list of dates at which the discount factor is known
    # - dfs: the known discount factors
    def __init__(self, obsdate, pillars, dfs):
        # the following generates an error that will block the program
        if pillars[0] < obsdate:
            raise "today is greater than the first pillar date"
        
        # we want to make sure that the first pillar is the observation date and its discount factor is 1.0
        # therefore we add it if not present in the original lists
        if pillars[0] > obsdate:
            pillars.insert(0, obsdate)
            dfs.insert(0, 1.0)

        # store the input variables
        self.today = obsdate
        self.pillars = pillars
        self.dfs = dfs

        # dates must be converted to numbers, otherwise the interpolation function will not work
        self.pillars_number = [aDate.toordinal() for aDate in pillars]

        # we will linearly interpolate on the logarithm of the discount factors
        self.logdfs = [math.log(df) for df in dfs]

    def df(self, aDate):
        # we convert the date to a number
        date_number = aDate.toordinal()

        # we use the linear interpolator of the numpy library
        log_df = numpy.interp(date_number, self.pillars_number, self.logdfs)

        #we  will have to the take the exponential beacuse we interpolated the logarithms
        df = math.exp(log_df)

        # return the resulting discount factor
        return df

class ForwardLiborCurve:
    # we want to create the ForwardLiborCurve class with that will compute Lt, T), i.e.
    # the forward libor rate computed at t (today) that resets (fixes) at T (this means that
    # if the "tenor" of this rate is 3 months, the rate will be know at T and paid
    # at T + 3m
    # - obsdate: the date at which the curve refers to (i.e. today)
    # - fixingDates: the list of fixing dates of the kwnown forward libor rates
    # - forwardLibors: the kwnown forward libor rates
    def __init__(self, obsdate, fixingDates, forwardLibors):
        # store the input variables
        self.obsdate = obsdate
        self.fixingDates = fixingDates
        self.forwardLibors = forwardLibors

        # dates must be converted to numbers, otherwise the interpolation function will not work
        self.fixingDates_number = [aDate.toordinal() for aDate in pillars]


    def value(self, fixingDate):
        # we convert the date to a number
        date_number = fixingDate.toordinal()

        #we use the linear interpolator of the numpy library
        forwardRate = numpy.interp(date_number, self.fixingDates_number, self.forwardLibors)

        # return the resulting interpolated forward rate
        return forwardRate

# example
if __name__ == '__main__':
    # today is the 1st January 2010
    obsdate = date(2010,1,1)
    pillars = [date(2010,1,1), date(2011,1,1), date(2012,1,1)]
    dfs = [1., 0.95, 0.88]
    dc = DiscountCurve(obsdate, pillars, dfs)
    df = dc.df(date(2010,6,1))    

    print "Interpolated Discount Factor:", df
    
    forwardLibors = [0.03, 0.035, 0.042]
    libor = ForwardLiborCurve(obsdate, pillars, forwardLibors)
    fwdLibor = libor.value(date(2010,11,1))
    print "Interpolated Forward Libor:", fwdLibor
