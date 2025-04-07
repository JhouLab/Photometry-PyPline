import numpy as np
import pandas as pd
import openpyxl
import math
import cv2

class BehaviorData:
    def __init__(self, type = "deeplabcut", id_eventsDict = {}, mpcDF = None, behaviorData = None, threshold = 0.6, videoPath = None):
        #dataframes
        #event timestamps, either from MedPc or BrainMata control software
        self.timestamp_data = mpcDF
        self.beh_data = behaviorData
        #timstamps of TTLs from video recording software, to align with
        self.beh_TTL = None
        self.beh_cleaned = None
        self.beh_stats = {}

        #events
        self.id_events = id_eventsDict
        self.beh_alignedEvents = {}

        #labeling confidence threshold for DLC data types
        self.threshold = threshold

        #fps and path to .avi file
        self.videoPath = videoPath
        self.fps = None
        self.trueFrames = None
        self.videoLength = None

        #type
        self.type = type
        self.control_type = None


    #Given an eventID int, part name string, baseline interval int, and outcome int.
    #Align trace of data to closest trialstart TTL timestamp and apply the pre-calculated offset compared to MED-Pc timestamp.
    #This function should be theorhetically recording FPS agnostic, as it locates closest rows in dataframe based on the time, not by frame index.
    def processEvent(self, eventID, part, baseline, outcome):
        # get the timestamps for each event with passed ID
        events = self.getEventTimes(eventID)
        df = pd.DataFrame()

        for y in range(len(events)):
            # find closest DLC-TTL event to behavioral event
            # these are the trail start TTls - they should be approximate to each event
            closest = self.beh_TTL['onset'].sub(events[y]).abs().idxmin()
            closestON = self.beh_TTL.at[closest, 'onset']
            offset = self.beh_TTL.at[closest, 'offset_MPC']
            tMin = (closestON + offset) - baseline
            tMax = (closestON + offset) + outcome

            #find closest timepoints in DLC data to start and stop times
            min = self.beh_cleaned['Time'].sub(tMin).abs().idxmin()
            max = self.beh_cleaned['Time'].sub(tMax).abs().idxmin()

            #write exact time interval to behavioral TTL dataframe
            self.beh_TTL.at[closest, 'interval_min_sec'] = self.beh_cleaned.at[min, 'Time']
            self.beh_TTL.at[closest, 'interval_max_sec'] = self.beh_cleaned.at[max, 'Time']

            trace = self.beh_cleaned.iloc[min:max][part]
            trace.reset_index(drop=True, inplace=True)
            df[y] = trace

        #take SD
        df['SD'] = df.std(axis=1, skipna=True)
        #take row average
        df['Average'] = df.mean(axis=1, skipna=True)
        #mov = np.convolve(df['Average'], np.ones(10), 'valid') / 10
        # first 5 and last 5 samples cannot be calculated, so pad array so that dimensions fit with existing data
        #mov = np.concatenate([[np.nan, np.nan, np.nan, np.nan, np.nan], mov, [np.nan, np.nan, np.nan, np.nan]])
        #df['Average'] = mov
        #reindex dataframe so times are event centric
        time = np.linspace(0 - baseline, 0 + outcome, df.shape[0])
        df['Time'] = time
        df.set_index('Time')
        return df


    def getEventTimes(self, timestampID):
        if self.timestamp_data is not None:
            if self.control_type == 'medpc':
                tmp = self.timestamp_data[self.timestamp_data.ID == timestampID].secs
                return tmp.values
            if self.control_type == 'brainmata':
                print(timestampID)
                tmp = self.timestamp_data[timestampID].dropna()
                return tmp.values
        else:
            raise UserWarning("Cannot retrieve timestamps from empty events dataframe. Does the original data include events Data?")
        return None


    #aligns segment of data to each type of event using the id_eventsDict
    def alignEvents(self, part, baseline = 10, outcome = 10):
        if self.beh_cleaned is None:
            print("Error: Cannot align events if data has not been cleaned")
        else:
            print("Aligning behavioral data to timestamps...")
            if len(self.id_events) < 1:
                print("Error: No dictionary of events provided. Cannot align events.")
            else:
                #Calculate offsets of each TLL pulse detected by camera compared to each TrialStart
                MPC = self.getEventTimes(self.id_events.get("id_trialStart"))
                for x in range(len(MPC)):
                    closest = self.beh_TTL.sub(MPC[x]).abs().idxmin()
                    closest = closest['onset']
                    offset = self.beh_TTL.at[closest, 'onset'] - MPC[x]
                    self.beh_TTL.at[closest, 'offset_MPC'] = offset

                #loop though event dictionary to process each event, using TTL offsets to align animal velocity
                for key, value in self.id_events.items():
                    eventName = key.split("_")
                    eventName = eventName[1]
                    print("Processing event", eventName, "...")
                    self.beh_alignedEvents[eventName] = self.processEvent(value, part, baseline, outcome)

    #annote a behavior event (i.e as 0 or 1 for each time point) given a deeplabcut part name and a minimum number of samples
    def booleanEvent(self, part):
        if self.type == "deeplabcut":
            newName = part + "_bool"
            self.beh_cleaned[newName] = [0 if np.isnan(x) else 1 if not np.isnan(x) else np.isnan() for x in self.beh_cleaned[part]]

    #annotate a behavior event in a range around an event window. Uses aligned events to label number of behavior events in a given range (0 is TTL)
    #expects boolean event annotations (weather a behavior happened at a time point) to have been previously calculated
    #window: array [x, y] of min and max times in seconds to look
    #isCorrect: #if the event is a correct or incorrect behavioral response
    #eventName: Name of event to search for in dictionary
    #part: Name of the data segment which we are analyzing
    def annotatePerieventBehavior(self, window, isCorrect, eventName, part):
        tmin = window[0]
        tmax = window[1]
        annotations = []
        counts = []
        eventData = None
        if self.beh_alignedEvents is not None:
            eventData = self.beh_alignedEvents[eventName]
            if eventData is not None:
                wMin = eventData['Time'].sub(tmin).abs().idxmin()
                wMax = eventData['Time'].sub(tmax).abs().idxmin()
                numTrials = eventData.shape[1] - 3
                numCorrect = 0
                for x in range(numTrials): #ignore SD, Average, and Time so subtract 3
                    slice = eventData.iloc[wMin:wMax][x]
                    tmp = slice[slice >= 1].shape[0]
                    counts.append(tmp)
                    if isCorrect == True:
                        if tmp > 0:
                            annotations.append("Correct")
                            numCorrect += 1
                        elif tmp <= 0:
                            annotations.append("Incorrect")
                        else:
                            annotations.append("Indeterminate")

                    if isCorrect == False:
                        if tmp <= 0:
                            annotations.append("Correct")
                            numCorrect += 1
                        elif tmp > 0:
                            annotations.append("Incorrect")
                        else:
                            annotations.append("Indeterminate")

                print("Annotations for event: ", part + "_" + eventName)
                colName = "num_" + part + "_" + eventName
                colName2 = "annotation_" + part + "_" + eventName
                d = {colName: counts, colName2: annotations}
                df = pd.DataFrame(data = d)
                print(df)
                dictName = part + "_" + eventName + "_annotations"
                self.beh_stats[dictName] = df
                percentCorrect = numCorrect / numTrials
                dictName = part + "_" + eventName + "_correct"
                self.beh_stats[dictName] = percentCorrect
                print("Number of correct events:", percentCorrect)




    def calcVel(self, df, movingAverage = False, threshold = 100):
        vel = np.array([])
        vel = np.append(vel, 0)
        locomotion = float(0)
        for x in range(1, int(df.shape[0])):
            #calculate euclidian distance
            dist = math.dist((df.iloc[x-1, 0] , df.iloc[x-1, 1]), (df.iloc[x,0] , df.iloc[x, 1]))
            #if velocity is greater than a threshold value, make NA as it is a putative outlier
            if dist >= threshold:
                vel = np.append(vel, np.nan)
            else:
                if np.isnan(dist) is False or math.isnan(dist) is False:
                    locomotion = locomotion + dist
                vel = np.append(vel, dist)

        #calculate moving average for a 10 sample windwow
        if movingAverage == True:
            print("Warning: calculating the moving average causes unexpected results with Nan values. Use with caution")
            test = np.convolve(vel, np.ones(10), 'valid') / 10
            #first 5 and last 5 samples cannot be calculated, so pad array so that dimensions fit with existing data
            test = np.concatenate([[0, 0, 0, 0, 0], test, [0,0,0,0,0]])
            return test, locomotion
        else:
            return vel, locomotion


    def clean(self):
        if self.videoPath is None or self.trueFrames is None or self.fps is None:
            print("Error: no video file was passed. Cannot process behavioral data without accurate fps")
        else:
            #check what type of behavioral data has been passed
            #current types checked for: DeepLabCut, ezTrack Location Analysis, ezTrack Freezing Analysis
            test = self.beh_data.columns[0]
            if test == "File":
                if "Freezing" in self.beh_data.columns:
                    self.type = "ezt_freezing"
                    print("Detected ezTrack freezing data")
                    #remove redundent columns
                    self.beh_cleaned = self.beh_data.iloc[:,5:]
                    self.beh_cleaned["Freezing"] = self.beh_cleaned["Freezing"] / 100
                    self.beh_cleaned["Freezing"] = self.beh_cleaned["Freezing"].astype(int)

                elif "X" in self.beh_data.columns:
                    self.type = "ezt_location"
                    print("Detected ezTrack location data")
                    # remove redundent columns
                    self.beh_cleaned = self.beh_data.iloc[:,7:]
                else:
                    print("Error: Detected ezTrack style data but could not identify the type...")

            elif test == "scorer":
                self.type = "deeplabcut"
                print("Detected Deeplabcut data...")
                #remove existing headers
                newHeaders = self.beh_data.iloc[0]
                self.beh_data = self.beh_data[1:]
                self.beh_data.columns = newHeaders
                #rename columns in original dataframe
                tmp = self.beh_data.iloc[1:].set_axis(self.beh_data.columns + '_' + self.beh_data.iloc[0], axis=1)
                self.beh_data = tmp
                self.beh_data = self.beh_data.reset_index(drop=True)
                self.beh_data.drop(self.beh_data.columns[0], axis=1, inplace=True)
                #process each part independently, and remove coordinate pairs which fall below confidence threshold
                self.beh_cleaned = self.beh_data[["Nose_x"]]
                for x in range(0, int(self.beh_data.shape[1]) - 1, 3):
                    tmp = self.beh_data.iloc[:, x:x+3]
                    #set points where labeling is not above threshold to nan
                    tmp = tmp.where(tmp.iloc[:, 2] >= self.threshold)
                    pName = tmp.columns[0].split("_")
                    pName = pName[0]
                    dictName = pName + "_Total_Locomotion"
                    pName = pName + "_Vel"
                    #calculate velocity and total locomotion
                    tmp[pName], total = self.calcVel(tmp)
                    self.beh_cleaned = pd.concat([self.beh_cleaned, tmp], axis=1)
                    self.beh_stats[dictName] = total

                #drop first placeholder column
                self.beh_cleaned = self.beh_cleaned.iloc[:, 1:]


            #caluclate fps from video file to produce accurate timestamps
            self.beh_cleaned['Time'] = self.beh_data.index / self.fps

            if int(self.beh_cleaned.shape[0]) != self.trueFrames:
                print("Error: cleaned behavioral data contains", int(self.beh_cleaned.shape[0]), "frames while cv2 reports", self.trueFrames, ". Is this the correct video and behavioral data?")
            else:
                print("Confirmed detected number of frames matches amount in behavioral data...")

            #rename DLC-TTL data columns
            self.beh_TTL.columns = ['onset', 'offset']

            print(self.beh_stats)


    def determineControlType(self):
        if self.timestamp_data is None:
            raise UserWarning("Cannot determine control recording type since no timestamp data was provided")
        else:
            test = self.timestamp_data.columns[0]
            if test == "SOLENOID_WATER":
                print("Found BrainMata event data...")
                self.control_type = "brainmata"
            elif test == "Index":
                print("Found Med-Pc event data...")
                self.control_type = "medpc"
            else:
                print("Warning: event data is not a recognized format")

    def readData(self, fpath):
        print("Reading data...")
        timestampData = None
        DLCData = None
        DLCTTL = None
        #look for Med-Pc Data
        try:
            timestampData = pd.read_excel(fpath, sheet_name="Events")
        except:
            print("Warning: Could not find events data in file. Is there an excel tab labeled 'Events'?")

        #look for behavior data
        #ALWAYS ASSUME IT IS THE FIRST SHEET
        try:
            DLCData = pd.read_excel(fpath, sheet_name=0, header=0)
        except:
            print("Warning: Could not find behavioral data. Is there an excel tab labeled 'Behavior'?")

        #look for behavioral data TTL timestamps
        try:
            DLCTTL = pd.read_excel(fpath, sheet_name="Behavior-TTL", header=0, index_col=0)
        except:
            print("Warning: Could not find behavioral recording TTL timestamps. Is there an excel tab labeled 'Behavior-TTL'?")

        self.beh_data = DLCData
        self.beh_TTL = DLCTTL
        self.timestamp_data = timestampData

        if self.videoPath is not None:
            video = cv2.VideoCapture(self.videoPath)
            self.trueFrames = video.get(cv2.CAP_PROP_FRAME_COUNT)
            self.fps = video.get(cv2.CAP_PROP_FPS)
            self.videoLength = self.trueFrames / self.fps
            self.beh_stats['True_FPS'] = self.fps
            self.beh_stats['cv2_Video_Length'] = self.videoLength
            print("Detected video with", self.trueFrames, "frames recorded at", self.fps, "fps")

        self.determineControlType()
        #reformat event datafram
        if self.control_type == "brainmata":
            tmp = self.timestamp_data.iloc[1:].set_axis(self.timestamp_data.columns + '_' + self.timestamp_data.iloc[0], axis = 1)
            self.timestamp_data = tmp
            self.timestamp_data = self.timestamp_data.reset_index(drop=True)
        else:
            self.timestamp_data = timestampData

