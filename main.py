import os
import tkinter
from tkinter import filedialog
import matplotlib.pyplot as plt
import pandas as pd
import BehaviorStruct
import PhotometryStruct

#dictionary of events in Med-Pc timestamp data
pulsedEvents = {"id_sessionStart": 1, "id_sessionEnd": 2, "id_recordingStart": 5, "id_recordingStop": 6}
DLCEvents = {"id_trialStart": 71, "id_cueAvers": 34, "id_cueAversHigh": 38, "id_cueNeutral": 36}

def main():
    root = tkinter.Tk()
    root.withdraw()
    print("\n==Fiber Photometry Analysis for Pulsed Recordings==")
    print("Note: Currently, this program only accepts Doric Neuroscience Studio v5 type .xlsx files\n")
    channel1 = None
    choice = None
    type = None
    currdir = os.getcwd()
    #get path to .xlsx file
    fpath = filedialog.askopenfilename(parent=root, initialdir=currdir,
                              title='Please select a data file',
                              filetypes=[("Excel file", "*.xlsx")])

    print("Select Recording Type (default = 1):")
    print("1. Continuous")
    print("2. Pulsed")
    print("3. DeepLabCut Data Only")
    while True:
        val = input("> ")
        if val == "1" or val == "":
            type = "continuous"
            break
        elif val == "2":
            type = "pulsed"
            break
        elif val == "3":
            type = "DLC-only"
            break
        else:
            print("Incorrect input")

    if type == "continuous" or type == "pulsed":
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

    #DLC data only processing
    if type == "DLC-only":
        root.deiconify()
        # get path to video
        vpath = filedialog.askopenfilename(parent=root, initialdir=currdir,
                                           title='Please select a video file',
                                           filetypes=[("Video File", "*.avi")])
        root.withdraw()
        channel1 = BehaviorStruct.BehaviorData(id_eventsDict= DLCEvents, videoPath = vpath)
        channel1.readData(fpath)
        channel1.clean()
        channel1.alignEvents(part= 'Back1', baseline= 10, outcome= 10)

        name = fpath.split("/")
        saveDir = ""
        saveDir = "/".join(name[0:len(name) - 1])
        name = name[len(name) - 1].split(".")
        name = name[0]

        #plot results
        print("Plotting total locomotion...")
        plot = channel1.dlc_cleaned.plot(x="Time", y="Back1_Vel", kind="line", figsize=(10,5))
        plot.set_title("Back1")
        plt.savefig(saveDir + "/" + "Back1_DLC.png")
        plt.savefig(saveDir + "/" + "Back1_DLC.png")
        print("Plotting aligned events...")
        for key, value in channel1.dlc_alignedEvents.items():
            plot = channel1.dlc_alignedEvents[key].plot(x="Time", y="Average", kind="line", figsize=(10, 5))
            plot.set_title(key)
            figPath = saveDir + "/" + key + "_DLC.png"
            plt.savefig(figPath)

        #save data
        print("Saving processed and aligned data in .xlsx format...")
        stats = pd.Series(channel1.dlc_stats, name="Statistics")
        #save all DLC data
        dest = saveDir + "/" + "DLC_All.xlsx"
        writer = pd.ExcelWriter(dest, engine="xlsxwriter")
        stats.to_excel(writer, sheet_name="Statistics", index=True)
        channel1.dlc_data.to_excel(writer, sheet_name="DLC_Data", index=True)
        channel1.dlc_cleaned.to_excel(writer, sheet_name="DLC_Cleaned", index=True)
        channel1.dlc_TTL.to_excel(writer, sheet_name="DLC-TTL", index=False)
        writer.close()

        #save aligned events as a separate spreadsheet
        dest = saveDir + "/" + "DLC_Aligned.xlsx"
        writer = pd.ExcelWriter(dest, engine= 'xlsxwriter')
        for key, value in channel1.dlc_alignedEvents.items():
            sheetName = key + "_velocity"
            value.to_excel(writer, sheet_name= sheetName, index= True)
        writer.close()

        #show plots
        plt.show()

    #pulsed recordings
    if choice == 1 and type != "DLC-only":
        fpath = getFile(False)
        channel1 = PhotometryStruct.PhotometryData(type= type, id_sessionStart= pulsedEvents["id_sessionStart"], id_sessionEnd= pulsedEvents["id_sessionEnd"])
        channel1.readData(fpath)
        channel1.clean()

        #normalize and bin data
        channel1.normalize()
        if type == "pulsed":
            channel1.binData()

    if channel1 != None and type != "DLC-only":
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