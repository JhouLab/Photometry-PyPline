import pandas as pd
import openpyxl

class PhotometryData:
    def __init__(self, ptDf = None, mpcDf = None, autoFlprofile = 0, cutoff = 0.009, id_sessionStart = 1, id_sessionEnd = 2):
        self.photometryDf = ptDf
        self.mpcDf = mpcDf
        self.binnedPtDf = None
        self.autoFlProfile = autoFlprofile
        #threshold value which we remove 465 values under (these are samples which the laser was not active for)
        self.cutoff = cutoff
        self.id_sessionStart = id_sessionStart
        self.id_sessionEnd = id_sessionEnd
        self.cleaned = False

    def getTimestampTimes(self, timestampID):
        tmp = self.mpcDf[self.mpcDf.ID == timestampID].secs
        return tmp.values


    #assumes clean() has already been ran on data
    def binData(self):
        if self.cleaned == False:
            print("Error: This data has not been cleaned. Please run clean() before proceeding.")
        else:
            self.photometryDf["StartIdx"] = self.photometryDf["Time"].diff() > 1
            idxs = self.photometryDf[self.photometryDf.StartIdx].index
            rowsList = []
            for i in range(1, len(idxs)):
                end = None
                start = None
                if i == len(idxs):
                    end = self.photometryDf._465.iloc[-1]
                else:
                    end = idxs[i]
                start = idxs[i-1]

                window = self.photometryDf.iloc[start:end].mean()
                rowsList.append([window.Time, window._405, window._465, window.norm])

            self.binnedPtDf = pd.DataFrame(rowsList)
            self.binnedPtDf.columns = ["Time", "_405", "_465", "norm"]
            self.binnedPtDf = self.binnedPtDf[self.binnedPtDf["Time"].notna()]
            print(self.binnedPtDf)

    def clean(self):
        mapping = {"Time(s)": "Time", "AIn-1 - Dem (AOut-1)": "_405", "AIn-1 - Dem (AOut-2)": "_465", "DI/O-3": "TTL_6", "DI/O-4": "TTL_8"}
        self.photometryDf.rename(columns = mapping, inplace = True)
        #remove samples which are outside recording windows
        self.photometryDf = self.photometryDf.drop(self.photometryDf[self.photometryDf.TTL_6 < 1].index)
        #remove samples in which isosbestic values are close to 0
        self.photometryDf = self.photometryDf.drop(self.photometryDf[self.photometryDf._465 < self.cutoff].index)

        #remove samples which are before or after session start and end times
        start = self.getTimestampTimes(self.id_sessionStart)
        end = self.getTimestampTimes(self.id_sessionEnd)
        if len(start) == 1:
            start = start[0]
        else:
            print("Error: Found more than one session start timestamps in Med-Pc data. Check your Med-Pc file.")

        if len(end) == 1:
            end = end[0]
        else:
            print("Error: Found more than one session end timestamps in Med-Pc data. Check your Med-Pc file.")
        self.photometryDf = self.photometryDf.drop(self.photometryDf[self.photometryDf.Time < start].index)
        self.photometryDf = self.photometryDf.drop(self.photometryDf[self.photometryDf.Time > end].index)

        self.cleaned = True


    def normalize(self):
        if self.cleaned == False:
            print("Error: This data has not been cleaned. Please run clean() before proceeding.")
        else:
            #take first and last 20 samples, calculate x-intercept of line passing between the points
            end = len(self.photometryDf._465)
            y1 = self.photometryDf._465[0:20].mean()
            y2 = self.photometryDf._465[end-20:end].mean()
            x1 = self.photometryDf._405[0:20].mean()
            x2 = self.photometryDf._405[end-20:end].mean()

            intercept = x2 - (y2 * (x1-x2))/(y1-y2)
            print("X-intercept of regression: ", intercept)
            if intercept > max(y1, y2) * 0.8:
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
        #look for Med-Pc Data
        try:
            timestampData = pd.read_excel(fpath, sheet_name="Med-Pc", header = 0)
        except:
            print("Error: Could not find Med-Pc data in file. Is there an excel tab labeled 'Med-Pc'?")
            return

        self.photometryDf = rawData
        self.mpcDf = timestampData