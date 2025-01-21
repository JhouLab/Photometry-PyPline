import pandas as pd
import openpyxl


class PhotometryData:
    def __init__(self, type="pulsed", autoFlProfile=0, cutoff=0.009, id_eventsDict = {}, id_sessionStart=1, id_sessionEnd=2):
        self.autoFlProfile = autoFlProfile
        #threshold value which we remove samples under (these are samples which the laser was not active for)
        self.cutoff = cutoff
        self.id_events = id_eventsDict
        self.id_sessionStart = id_sessionStart
        self.id_sessionEnd = id_sessionEnd
        #photometry data
        self.pt_raw = None
        self.pt_cleaned = None
        self.pt_binned = None
        self.pt_alignedEvents = {}
        #behavioral data
        self.mpc_data = None
        self.dlc_data = None
        #normaliztion constant, which is functionally the slope from the caluclated linear regression
        self.normConst = 0
        if type.upper() == "PULSED":
            self.isPulsed = True
        elif type.upper() == "CONTINUOUS":
            self.isPulsed = False
        else:
            raise TypeError("Passed recording type is not recognized. Passed", type,
                            "does not match either 'pulsed' or 'continuous'")

    #Helper function which takes a Med-Pc ID integer and returns a pandas dataframe with all of the timestamps for that ID
    def getTimestampTimes(self, timestampID):
        if self.mpc_data is not None:
            tmp = self.mpc_data[self.mpc_data.ID == timestampID].secs
            return tmp.values
        else:
            raise UserWarning("Cannot retrieve timestamps from empty Med-pc dataframe. Does the original data include Med-Pc Data?")

    #work in progress
    def alignEvents(self):
        if self.mpc_data is None:
            raise UserWarning("Cannot align events to non-existent Med-Pc Data")
        else:
            trials = []
            try:
                id_trialStart = self.id_events["id_trialStart"]
                trials = self.getTimestampTimes(id_trialStart)
            except:
                raise TypeError("No Med-pc events for id_trialStart")


    #uses cleaned data from pulsed recordings to create bins of each recording window
    #for each recording window, takes the mean of the signal.
    def binData(self):
        if self.isPulsed is False:
            raise TypeError("Recording type is continuous. Cannot bin data for non-pulsed recordings")
        if self.pt_cleaned is None:
            raise UserWarning("This data has not been cleaned. Please run clean() before proceeding.")
        else:
            idxs = self.pt_cleaned[self.pt_cleaned["StartIdx"] == True].index.tolist()
            if len(idxs) < 1:
                raise IndexError("Could not find any samples which would indicate the start of a new recording window")
            rowsList = []
            #find start and end times based on idxs where the time "jumps", signifying a new recording window
            #remove 1 sample at start and end to exclude points were laser was partially on/off
            for i in range(1, len(idxs)):
                end = None
                start = None
                if i == len(idxs):
                    end = self.pt_raw._465.iloc[-1]
                else:
                    end = idxs[i]
                start = idxs[i - 1]

                window = self.pt_cleaned.iloc[start:end].mean()
                rowsList.append([window.Time, window._405, window._465, window.norm])

            self.pt_binned = pd.DataFrame(rowsList)
            self.pt_binned.columns = ["Time", "_405", "_465", "norm"]
            self.pt_binned.reset_index(drop=True, inplace=True)
            print(self.pt_binned)

    #cleans raw photometry data (Doric-type only).
    def clean(self):
        if self.pt_raw is None:
            raise UserWarning("No photometry data has been added to this struct. Call readData(fpath) before proceeding")
        else:
            self.pt_cleaned = self.pt_raw
            mapping = {"Time(s)": "Time", "AIn-1 - Dem (AOut-1)": "_405", "AIn-1 - Dem (AOut-2)": "_465",
                       "DI/O-3": "TTL_6", "DI/O-4": "TTL_8"}
            self.pt_cleaned.rename(columns=mapping, inplace=True)

            if self.isPulsed is True:
                #remove samples which are outside recording windows
                self.pt_cleaned = self.pt_cleaned.drop(self.pt_cleaned[self.pt_cleaned.TTL_6 < 1].index)
                #remove samples in which signal is close to 0
                #these are samples where the TTL turned on the recording, but the laser is not fully on
                self.pt_cleaned = self.pt_cleaned.drop(self.pt_cleaned[self.pt_cleaned._465 < self.cutoff].index)

                #remove samples which are before or after session start and end times (if Med-Pc data as been loaded into data structure)
                if self.mpc_data is not None:
                    start = self.getTimestampTimes(self.id_sessionStart)
                    end = self.getTimestampTimes(self.id_sessionEnd)
                    if len(start) == 1:
                        start = start[0]
                    else:
                        raise TypeError("Found more or less than one session start timestamps in Med-Pc data. Check your Med-Pc file.")

                    if len(end) == 1:
                        end = end[0]
                    else:
                        raise TypeError("Found more or less than than one session end timestamps in Med-Pc data. Check your Med-Pc file.")
                    self.pt_cleaned = self.pt_cleaned.drop(self.pt_cleaned[self.pt_cleaned.Time < start].index)
                    self.pt_cleaned = self.pt_cleaned.drop(self.pt_cleaned[self.pt_cleaned.Time > end].index)

                #reset index to consecutive
                self.pt_cleaned.reset_index(drop=True, inplace=True)

                # find start and end times based on idxs where the time "jumps", signifying a new recording window
                # remove 2 samples at start and end to exclude points where laser was partially on/off
                self.pt_cleaned["StartIdx"] = self.pt_cleaned["Time"].diff() > 1
                idxs = self.pt_cleaned[self.pt_cleaned.StartIdx].index
                if len(idxs) < 1:
                    raise TypeError("Could not find any samples which would indicate the start of a new recording window")
                rowsList = []
                print(idxs)
                for i in range(1, len(idxs)):
                    end = None
                    start = None
                    if i == len(idxs):
                        end = self.pt_cleaned._465.iloc[-1]
                        end -= 2
                    else:
                        end = idxs[i]
                        end -= 2
                    start = idxs[i - 1]
                    start += 2
                    #need to flag this sample as new start of window
                    self.pt_cleaned["StartIdx"][start] = True

                    window = self.pt_cleaned.iloc[start:end]
                    rowsList.append(window)

                    self.pt_cleaned = pd.concat(rowsList)
                    self.pt_cleaned.reset_index(drop=True, inplace=True)

            self.cleaned = True

    #Normalizes cleaned photometry data
    def normalize(self):
        if self.pt_cleaned is None:
            raise UserWarning("This data has not been cleaned. Please run clean() before proceeding.")
        else:
            #take first and last 20 samples, calculate x-intercept of line passing between the points
            end = len(self.pt_raw._465)
            y1 = self.pt_raw._465[0:20].mean()
            y2 = self.pt_raw._465[end - 20:end].mean()
            x1 = self.pt_raw._405[0:20].mean()
            x2 = self.pt_raw._405[end - 20:end].mean()

            intercept = x2 - (y2 * (x1 - x2)) / (y1 - y2)
            print("Slope of regression: ", intercept)
            if intercept > max(y1, y2) * 0.8:
                intercept = 0
                print("Warning: y-intercept is greater than actual y values, assuming slope is 0")
            #add contribution of autofluorescence
            self.normConst = intercept
            intercept += self.autoFlProfile

            self.pt_cleaned["norm"] = self.pt_cleaned._465 / (self.pt_cleaned._405 - intercept)
            print(self.pt_cleaned)

    #given a path to a .xlsx file, loads Med-Pc, Photometry, and DeeplabCut data into data structure
    def readData(self, fpath):
        rawData = None
        timestampData = None
        #look for photometry data
        try:
            #first sheet is always our photometry data
            rawData = pd.read_excel(fpath, sheet_name=0, header=1, dtype=float)
        except:
            raise RuntimeError("Could not read photometry data")
        #look for Med-Pc Data
        try:
            timestampData = pd.read_excel(fpath, sheet_name="Med-Pc", header=0)
        except:
            print("Warning: Could not find Med-Pc data in file. Is there an excel tab labeled 'Med-Pc'?")

        #look for DLC Data
        try:
            DLCData = pd.read_excel(fpath, sheet_name="DLC", header=0)
        except:
            print("Warning: Could not find DeepLabCut")

        self.pt_raw = rawData
        self.mpc_data = timestampData
        self.dlc_data = DLCData
