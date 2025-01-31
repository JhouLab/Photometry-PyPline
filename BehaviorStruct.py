import numpy as np
import pandas as pd
import openpyxl
import math

class BehaviorData:
    def __init__(self, id_eventsDict = {}, mpcDF = None, dlcData = None, threshold = 0.6, fps = 30):
        #dataframes
        self.mpc_data = mpcDF
        self.dlc_data = dlcData
        self.dlc_TTL = None
        self.dlc_cleaned = None
        #events
        self.id_events = id_eventsDict
        #labeling confidence threshold
        self.threshold = threshold
        #fps
        self.fps = fps


    def calcVel(self, df):
        vel = np.array([])
        vel = np.append(vel, 0)
        for x in range(1, int(df.shape[0] - 1)):
            if df.iloc[x, 0] is None or df.iloc[x, 1] is None:
                vel = np.append(vel, np.nan)
            else:
                #calculate euclidian distance
                dist = math.sqrt(math.exp((df.iloc[x, 0] - df.iloc[x-1, 0])) + (math.exp(df.iloc[x, 1] - df.iloc[x-1, 1])))
                vel = np.append(vel, dist)

        #calculate moving average for a 10 sample windwow
        test = np.convolve(vel, np.ones(10), 'valid') / 10
        test = np.concatenate([[0, 0, 0, 0, 0], test, [0,0,0,0,0]])
        return test



    def clean(self):
        #rename columns in original dataframe
        self.dlc_data.columns = (self.dlc_data.iloc[0] + '_' + self.dlc_data.iloc[1])
        self.dlc_data = self.dlc_data.iloc[2:].reset_index(drop=True)
        #change index's to reflect time in seconds instead of frame number
        self.dlc_data['Time'] = self.dlc_data.index / self.fps
        self.dlc_data.set_index('Time', inplace=True)
        #process each part independently, and remove coordinate pairs which fall below confidence threshold
        self.dlc_cleaned = self.dlc_data[["Nose_x"]]
        for x in range(0, int(self.dlc_data.shape[1]), 3):
            tmp = self.dlc_data.iloc[:, x:x+3]
            tmp = tmp[tmp.iloc[:, 2] >= self.threshold]
            pName = tmp.columns[0].split("_")
            pName = pName[0]
            pName = pName + "_Vel"
            tmp[pName] = self.calcVel(tmp)
            self.dlc_cleaned = pd.concat([self.dlc_cleaned, tmp], axis=1)

        #drop first placeholder column
        self.dlc_cleaned = self.dlc_cleaned.iloc[:, 1:]

        with pd.option_context('display.max_columns', None):
            print(self.dlc_cleaned)

    def readData(self, fpath):
        timestampData = None
        DLCData = None
        DLCFrames = None
        #look for Med-Pc Data
        try:
            timestampData = pd.read_excel(fpath, sheet_name="Med-Pc", header=0)
        except:
            print("Warning: Could not find Med-Pc data in file. Is there an excel tab labeled 'Med-Pc'?")

        #look for DLC Data
        try:
            DLCData = pd.read_excel(fpath, sheet_name="DLC", header=0, index_col=0)
        except:
            print("Warning: Could not find DeepLabCut data. Is there an excel tab labeled 'DLC'?")

        # look for DLC Data
        try:
            DLCTTL = pd.read_excel(fpath, sheet_name="DLC-TTL", header=0, index_col=0)
        except:
            print("Warning: Could not find DeepLabCut Recording TTL timestamps. Is there an excel tab labeled 'DLC-TTL'?")

        self.mpc_data = timestampData
        self.dlc_data = DLCData
        self.dlc_TTL = DLCTTL
