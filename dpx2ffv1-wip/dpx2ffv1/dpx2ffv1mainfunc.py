#!/usr/bin/env python3

import argparse
import sys
import os
import glob
import subprocess
import datetime
from dpx2ffv1.dpx2ffv1parameters import args
#from dpx2ffv1 import dpx2ffv1supportfuncs
from dpx2ffv1 import corefuncs
from dpx2ffv1 import classes
#from dpx2ffv1 import dpx2ffv1passfail_checks


def dpx2ffv1_main():
    inventoryName = 'transcode_inventory.csv'

    #assign input directory and output directory
    indir = corefuncs.input_check()
    outdir = corefuncs.output_check()
    #check that required programs are present
    corefuncs.mediaconch_check()
    corefuncs.ffprobe_check()
    corefuncs.mediainfo_check()
    ffvers = corefuncs.get_ffmpeg_version()
    rcvers = corefuncs.get_rawcooked_version()

    def get_immediate_subdirectories(folder):
        """get immediate subdirectories of input"""
        return [name for name in os.listdir(folder)
            if os.path.isdir(os.path.join(folder, name))]

    def filterFilenames(title_list):
        """identify titles to process based on a provided list"""
        with open(args.filter_list) as f:
            filter_list = [line.rstrip() for line in f]

        if (title_list in filter_list):
            return True
        else:
            return False

    #create the list of folders to run the script on
    title_list = get_immediate_subdirectories(indir)
    #if a list of titles was provided, select only those titles to process
    if args.filter_list:
        with open(args.filter_list) as f:
            filter_list = set(line.rstrip() for line in f)

        title_list = [item for item in title_list if item in filter_list]

    '''


    csvInventory = os.path.join(indir, inventoryName)
    csvDict = dpx2ffv1metawrangler.import_csv(csvInventory)
    '''
    #create the list of csv headers that will go in the qc log csv file
    csvHeaderList = [
    "Shot Sheet Check",
    "Date",
    "PM Lossless Transcoding",
    "Date",
    "File Format & Metadata Verification",
    "Date",
    "File Inspection",
    "Date",
    "QC Notes",
    "AC Filename",
    "PM Filename",
    "Runtime"
    ]

    print ("***STARTING PROCESS***")

    #get list of subdirectories from input
    #iterate through list
    #if directory exists in inventory (inventory check pass/fail)
    films = [classes.FilmObject(name, indir, outdir) for name in title_list]

    for filmObject in films:
        print('entered main loop')
        #TO DO check if filmObject exists in inventory. If so, import data
        #TO DO grab metadata - mediainfo grabs more useful info, so probably want to use that instead of ffprobe
        #print ("The status for", filmObject.get_name(), "is", filmObject.get_status())
        variableDict = filmObject.get_variable_dict()

        #TO DO check that folder structure is correct

        filmObject.run_rawcooked(variableDict)
        #generate ffprobe metadata from input
        print ("perform transcoding and QC")
        filmObject.set_status("Complete")
        #print ("The status for", filmObject.get_name(), "is", filmObject.get_status())

    #for filmObject in films:
    #    filmObject.print_status()
