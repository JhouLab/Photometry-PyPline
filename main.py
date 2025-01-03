import tkinter
from tkinter import filedialog
import os
import pandas as pd
import openpyxl

root = tkinter.Tk()
root.withdraw()

def readData(fpath):
    rawData = None
    try:
        rawData = pd.read_excel(fpath, sheet_name=0, header=1, dtype=float)
    except:
        print("Error: Could not read photometry data")
    print(rawData)
    return rawData
def getFile():
    try:
        currdir = os.getcwd()
        tempdir = filedialog.askopenfilename(parent=root, initialdir=currdir,
                                             title='Please select the DeepLabCut model config', filetypes=[('Excel','*.xlsx')])
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


main()