import tkinter
from tkinter import filedialog
import os
import pandas as pd
import openpyxl
import matplotlib.pyplot as plt

root = tkinter.Tk()
root.withdraw()

def normalize(df):
    #take first and last 20 samples, calculate x-intercept of line passing between the points
    end = len(df._465)
    y1 = df._465[0:20].mean()
    y2 = df._465[end-20:end].mean()
    x1 = df._405[0:20].mean()
    x2 = df._405[end-20:end].mean()

    intercept = x2 - (y2 * (x1-x2))/(y1-y2)
    print("X-intercept of regression: ", intercept)
    if intercept > max(y1, y2)*0.8:
        print("Warning: X-intercept is greater than actual x values, assuming intercept is 0")
        intercept = 0

    df["norm"] = df._465 / (df._405 - intercept)
    print(df)
    return df

def readData(fpath):
    rawData = None
    try:
        rawData = pd.read_excel(fpath, sheet_name=0, header=1, dtype=float)
    except:
        print("Error: Could not read photometry data")
    return rawData


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
    #load data into pandas dataframe
    rawData = readData(fpath)
    #rename columns
    mapping = {"AIn-1 - Dem (AOut-1)": "_405", "AIn-1 - Dem (AOut-2)": "_465", "DI/O-3": "TTL_6", "DI/O-4": "TTL_8"}
    rawData.rename(columns= mapping, inplace = True)
    #drop values which are outside recording windows
    rawData = rawData.drop(rawData[rawData.TTL_6 < 1].index)
    #remove values in which isospestic values are close to 0
    rawData = rawData.drop(rawData[rawData._465 < 0.009].index)
    print("Select a paradigm to analyze (default = 1):")
    print("1. Open Field")
    while True:
        val = input("> ")
        print(val)
        if val == "1":
            choice = 1
            break
        elif val == "":  #default option
            choice = 1
            break
        else:
            print("Incorrect input")

    #graph raw data
    rawData.plot(x="Time(s)", y=["_465", "_405"], kind="line", figsize=(10,5))
    plt.title("Raw Data")
    plt.ylabel("Current")

    #normalize data
    normData = normalize(rawData)

    #graph normalized data
    normData.plot(x="Time(s)", y=["norm"], kind="line", figsize=(10,5))
    plt.title("Normalized 465")
    plt.ylabel("f/f")
    plt.show()

main()
