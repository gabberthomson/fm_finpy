from datetime import date
from dateutil.relativedelta import relativedelta

# this function converts the excel date representation to the pythonic one
def date_from_xl(xl_value):
    return date.fromordinal(xl_value + 693594)

# this function computes the difference between two dates with the act/360 day count convention
def dc_act360(startDate, endDate):
    return (endDate.toordinal() - startDate.toordinal())/360.0

# this function computes the difference between two dates with the act/365 day count convention
def dc_act365(startDate, endDate):
    return (endDate.toordinal() - startDate.toordinal())/365.0

# this function computes the difference between two dates with the 30E360 day count convention
def dc_30e360(startDate, endDate):
    base_day = 360.0
    d1, d2   = startDate.day,   endDate.day
    m1, m2   = startDate.month, endDate.month
    y1, y2   = startDate.year,  endDate.year
    if d1 == 31: d1 = 30
    if d2 == 31: d2 = 30
    return (360.0*(y2-y1) + 30.0*(m2-m1) + (d2-d1)) / base_day

# this function is used to generate a list of dates, between startdate and enddate,
# each of which is "tenor"-months distant from the other (except the first: "short coupon stub")
def dates_generator(tenor, startdate, enddate):
    # we start with an empty list and populate it
    relevantdates = []

    # N.B. We start from the end date and proceed backward in time
    runningdate = enddate
    i = 1
    while (runningdate > startdate):
        relevantdates.append(runningdate)
        runningdate = enddate - relativedelta(months = i * tenor)
        i = i + 1
    relevantdates.append(startdate)

    # we sort these dates from the oldest to the newest
    relevantdates = sorted(relevantdates)

    # return the result
    return relevantdates

if __name__ == '__main__':
    startDate = date(2010,1,1)
    endDate = date(2012,1,1)
    dates = dates_generator(6, startDate, endDate)
    print dates
