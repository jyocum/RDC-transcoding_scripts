#!/usr/bin/env python3

'''
Functions that will be in multiple scripts
Handle things like: 
input, output, checksumming, checking that software exists, etc.
'''

import os
import hashlib
import sys
import subprocess
from aja_mov2ffv1.mov2ffv1parameters import args

def guess_date(string):
    for fmt in ["%m/%d/%Y", "%d-%m-%Y", "%m/%d/%y", "%Y-%m-%d"]:
        try:
            return datetime.datetime.strptime(string, fmt).date()
        except ValueError:
            continue
    raise ValueError(string)
    
def import_csv(csvInventory):
    csvDict = {}
    try:
        with open(csvInventory, encoding='utf-8')as f:
            reader = csv.DictReader(f, delimiter=',')
            film_fieldnames_list = ['File name', 'Accession number/Call number', 'ALMA number/Finding Aid', 'Barcode', 'Title', 'Record Date/Time']
            missing_fieldnames = [i for i in video_fieldnames_list if not i in reader.fieldnames]
            if not missing_fieldnames:
                for row in reader:
                    name = row['File name']
                    id1 = row['Accession number/Call number']
                    id2 = row['ALMA number/Finding Aid']
                    id3 = row['Barcode']
                    title = row['Title']
                    record_date = row['Record Date/Time']
                    container_markings = row['Housing/Container/Cassette Markings']
                    container_markings = container_markings.split('\n')
                    description = row['Description']
                    condition_notes = row['Condition']
                    format = row['Format']
                    captureDate = row['Capture Date']
                    #try to format date as yyyy-mm-dd if not formatted correctly
                    if captureDate:
                        captureDate = str(guess_date(captureDate))
                    digitizationOperator = row['Digitization Operator']
                    vtr = row['VTR']
                    vtrOut = row['VTR Output Used']
                    tapeBrand = row['Tape Brand']
                    recordMode = row['Tape Record Mode']
                    tbc = row['TBC']
                    tbcOut = row['TBC Output Used']
                    adc = row['ADC']
                    dio = row['Capture Card']
                    sound = row['Sound']
                    sound = sound.split('\n')
                    region = row['Region']
                    capture_notes = row['Capture notes']
                    csvData = {
                    'Accession number/Call number' : id1,
                    'ALMA number/Finding Aid' : id2,
                    'Barcode' : id3,
                    'Title' : title,
                    'Record Date' : record_date,
                    'Container Markings' : container_markings,
                    'Description' : description,
                    'Condition Notes' : condition_notes,
                    'Format' : format,
                    'Digitization Operator' : digitizationOperator,
                    'Capture Date' : captureDate,
                    'Coding History' : coding_history,
                    'Sound Note' : sound,
                    'Capture Notes' : capture_notes
                    }
                    csvDict.update({name : csvData})
            elif not 'File name' in missing_fieldnames:
                print("WARNING: Unable to find all column names in csv file")
                print("File name column found. Interpreting csv file as file list")
                print("CONTINUE? (y/n)")
                yes = {'yes','y', 'ye', ''}
                no = {'no','n'}
                choice = input().lower()
                if choice in yes:
                   for row in reader:
                        name = row['File name']
                        csvData = {}
                        csvDict.update({name : csvData})
                elif choice in no:
                   quit()
                else:
                   sys.stdout.write("Please respond with 'yes' or 'no'")
                   quit()
            else:
                print("No matching column names found in csv file")
            #print(csvDict)
    except FileNotFoundError:
        print("Issue importing csv file")
    return csvDict

def convert_runtime(duration):
    runtime = time.strftime("%H:%M:%S", time.gmtime(float(duration)))
    return runtime