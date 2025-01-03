import pandas as pd
import openpyxl

class PhotometryData:
    def __init__(self, eventList = None, ptDf = None, mpcDf = None, autoFlprofile = 0, cutoff = 0.009):
        self.photometryDf = ptDf
        self.mpcDf = mpcDf
        self.binnedPtDf = None
        self.autoFlProfile = autoFlprofile
        self.cutoff = cutoff

    def clean(self):
        mapping = {"AIn-1 - Dem (AOut-1)": "_405", "AIn-1 - Dem (AOut-2)": "_465", "DI/O-3": "TTL_6", "DI/O-4": "TTL_8"}
        self.photometryDf.rename(columns=mapping, inplace=True)
        # remove values which are outside recording windows
        self.photometryDf = self.photometryDf.drop(self.photometryDf[self.photometryDf.TTL_6 < 1].index)
        # remove values in which isospestic values are close to 0
        rawData = self.photometryDf.drop(self.photometryDf[self.photometryDf._465 < self.cutoff].index)

    def normalize(self):
        #take first and last 20 samples, calculate x-intercept of line passing between the points
        end = len(self.photometryDf._465)
        y1 = self.photometryDf._465[0:20].mean()
        y2 = self.photometryDf._465[end-20:end].mean()
        x1 = self.photometryDf._405[0:20].mean()
        x2 = self.photometryDf._405[end-20:end].mean()

        intercept = x2 - (y2 * (x1-x2))/(y1-y2)
        print("X-intercept of regression: ", intercept)
        if intercept > max(y1, y2)*0.8:
            print("Warning: X-intercept is greater than actual x values, assuming intercept is 0")
            intercept = 0
        #add contribution of autofluorescence
        intercept += self.autoFlProfile

        self.photometryDf["norm"] = self.photometryDf._465 / (self.photometryDf._405 - intercept)
        print(self.photometryDf)


    def readData(self, fpath):
        rawData = None
        timestampData = None
        #look for photometry data
        try:
            #first sheet is always our photometry data
            rawData = pd.read_excel(fpath, sheet_name=0, header=1, dtype=float)
        except:
            print("Error: Could not read photometry data")
            return

        try:
            timestampData = pd.read_excel(fpath, sheet_name="Med-Pc", header = 0)
        except:
            print("Error: Could not find Med-Pc data in spreadhsheet. Is it labeled 'Med-Pc'?")
            return

        self.photometryDf = rawData
        self.mpcDf = timestampData

