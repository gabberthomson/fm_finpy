from ois_products import *
from ir_curves import *
from scipy.optimize import brentq

class DiscountCurveBootstrapHelper:
    '''
    This class will be used within the root finding algorithm which will recursively
    invoke the method updateDf
    '''
    def __init__(self, today, product, pillars, dfs):
        self.today = today
        self.product = product
        self.pillars = pillars
        self.dfs = dfs

    def pricer(self, df):
        self.dfs[-1] = df
        dc = DiscountCurve(self.today, self.pillars, self.dfs)
        npv = self.product.npv(dc)
        return npv

class DiscountCurveBootstrap:
    '''
    This class will find the discount factors given a collection of ir products
    '''

    # In the init we build an empty list products
    # The only parameter we need is the date at which this procedure refers
    def __init__(self, today):
        self.products = []
        self.tenors = []
        self.today = today

    def addProduct(self, product):
        # we add products and check that they are ordered
        if len(self.products) > 0:
            # check that the product to be added has a longer maturity than the onm
            # inserted before: if not generates an error that will stop the program
            if product.endDate > self.products[-1].endDate:
                raise "Products not ordered"
        self.products.append(product)

    def bootstrap(self):
        # we run the iterative procedure
        pillars = [self.today]
        dfs = [1.0]
        for i, product in enumerate(self.products):
            # we enlarge the lists containing our desired output
            pillars.append(product.endDate)
            dfs.append(0.5) # N.B. this is an arbitrary value: it will be overrided during the bootstrap

            # We need to use an auxiliary class to wrap the target function, i.e. the function
            # that will be passed to the root finder (brent algorithm)
            helper = DiscountCurveBootstrapHelper(self.today, product, pillars, dfs)

            # run the root finding searching the result in the interval [0.0001, 2.]
            df = brentq(helper.pricer, 0.0001, 2.)

            # the following is actually not necessary because the
            # root finding algorithm already updated the list of discount factor
            dfs[-1] = df

        # return the output as a tuple consisting of 2 lists
        return DiscountCurve(self.today, pillars, dfs)


from dateutil.relativedelta import relativedelta

if __name__ == '__main__':
    today = date(2010,1,1)

    dc_bootstrapper = DiscountCurveBootstrap(today)
    dc_bootstrapper.addProduct(buildOIS(today, 1, 12, 0.02))
    dc_bootstrapper.addProduct(buildOIS(today, 2, 12, 0.022))
    dc_bootstrapper.addProduct(buildOIS(today, 3, 12, 0.025))
    dc_bootstrapper.addProduct(buildOIS(today, 6, 12, 0.03))
    dc_bootstrapper.addProduct(buildOIS(today, 12, 12, 0.04))
    dc_bootstrapper.addProduct(buildOIS(today, 18, 12, 0.045))
    dc_bootstrapper.addProduct(buildOIS(today, 24, 12, 0.05))

    dc_curve = dc_bootstrapper.bootstrap()
    for i, pillar in enumerate(dc_curve.pillars):
        print pillar, ": ", dc_curve.dfs[i]

