import tkinter
from tkinter import filedialog
import os
import matplotlib.pyplot as plt
import PhotometryStruct
from PhotometryStruct import PhotometryData

root = tkinter.Tk()
root.withdraw()

#dictionary of events in Med-Pc timestamp data
eventDict = {"id_sessionStart": 1,
             "id_sessionEnd": 2,
             "id_recordingStart": 5,
             "id_recordingStop": 6}

def getFile():
    try:
        currdir = os.getcwd()
        tempdir = filedialog.askopenfilename(parent=root, initialdir=currdir,
                                             title='Please select photometry data file',
                                             filetypes=[('Excel', '*.xlsx')])
        if len(tempdir) > 0:
            print("You chose: %s" % tempdir)
        else:
            raise Exception("Error: No file was selected")
    except:
        tempdir = getFile()
    return tempdir


def main():
    print("\n==Fiber Photometry Analysis for Pulsed Recordings==")
    print("Note: Currently, this program only accepts Doric Neuroscience Studio v5 type .xlsx files\n")
    #get path to .xlsx file
    fpath = getFile()
    #instantiate data structure
    channel1 = PhotometryStruct.PhotometryData(id_sessionStart = 1, id_sessionEnd = 2)
    channel1.readData(fpath)
    channel1.clean()
    print("Select a paradigm to analyze (default = 1):")
    print("1. Open Field")
    while True:
        val = input("> ")
        if val == "1":
            choice = 1
            break
        elif val == "":  #default option
            choice = 1
            break
        else:
            print("Incorrect input")

    #normalize data
    channel1.normalize()
    #bin data
    channel1.binData()

    #plot results
    fig, axes = plt.subplots(2,2)
    channel1.photometryDf.plot(ax= axes[0,0], x="Time", y=["_465", "_405"], kind="line", figsize=(10, 5))
    axes[0,0].set_title("Raw 405 and 465 Data")
    axes[0,0].set_ylabel("Current")
    channel1.photometryDf.plot(ax = axes[0,1], x="Time", y=["norm"], kind="line", figsize=(10, 5))
    axes[0,1].set_title("Normalized 465 Signal")
    axes[0,1].set_ylabel("f/f")
    channel1.binnedPtDf.plot(ax = axes[1,0], x="Time", y=["norm"], kind="line", figsize=(10, 5))
    axes[1,0].set_title("Binned Normalized 465 Signal")
    axes[1,0].set_ylabel("f/f")
    plt.show()

main()