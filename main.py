import tkinter
from tkinter import filedialog
import os
import matplotlib.pyplot as plt
import pandas as pd
import PhotometryStruct
from PhotometryStruct import PhotometryData

root = tkinter.Tk()
root.withdraw()

#dictionary of events in Med-Pc timestamp data
pulsedEvents = {"id_sessionStart": 1,
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
    channel1 = None
    choice = None
    type = None
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

    print("Select Recording Type (default = 1):")
    print("1. Continuous")
    print("2. Pulsed")
    while True:
        val = input("> ")
        if val == "1" or val == "":
            type = "continuous"
            break
        elif val == "2":
            type = "pulsed"
            break
        else:
            print("Incorrect input")

    #instantiate data structure
    if choice == 1:
        channel1 = PhotometryStruct.PhotometryData(type= type, id_sessionStart= pulsedEvents["id_sessionStart"], id_sessionEnd= pulsedEvents["id_sessionEnd"])
        channel1.readData(fpath)
        channel1.clean()

        #normalize and bin data
        channel1.normalize()
        if type == "pulsed":
            channel1.binData()

    if channel1 is not None:
        #plot results
        fig, axes = plt.subplots(2,2)
        channel1.cleanedptDf.plot(ax= axes[0,0], x="Time", y=["_465", "_405"], kind="line", figsize=(10, 5))
        axes[0,0].set_title("Raw Data")
        axes[0,0].set_ylabel("Current")
        channel1.cleanedptDf.plot(ax = axes[0,1], x="Time", y=["norm"], kind="line", figsize=(10, 5))
        axes[0,1].set_title("Normalized")
        axes[0,1].set_ylabel("f/f")
        if type == "pulsed":
            channel1.binnedPtDf.plot(ax = axes[1,0], x="Time", y=["norm"], kind="line", figsize=(10, 5))
            axes[1,0].set_title("Binned and Normalized")
            axes[1,0].set_ylabel("f/f")
        fig.tight_layout()

        #get name of original xlsx file for plot names
        name = fpath.split("/")
        name = name[len(name) - 1].split(".")
        name = name[0]
        figName = name + "_Signal.png"
        excelName = name + "_Processed.xlsx"
        #save plots and data
        plt.savefig(figName)
        writer = pd.ExcelWriter(excelName, engine="xlsxwriter")
        channel1.cleanedptDf.to_excel(writer, sheet_name="Data", index=False)
        if type == "pulsed":
            channel1.binnedPtDf.to_excel(writer, sheet_name="Binned Data", index=False)
        if channel1.mpcDf is not None:
            channel1.mpcDf.to_excel(writer, sheet_name="Med-Pc", index=False)
        writer.close()

        #scatter plot of 465 vs 405 data
        channel1.photometryDf.plot(x="_405", y="_465", c="Time", kind="scatter", colormap="viridis")
        #save graph
        figName = name + "_Scatter.png"
        plt.savefig(figName)

        #display graphs
        plt.show()

main()