#!/usr/bin/env python3

import argparse
import sys
import os
import glob
import avfuncs
import subprocess
import datetime
import json
import csv
import time

if sys.version_info[0] < 3:
    raise Exception("Python 3 or a more recent version is required.")

parser = argparse.ArgumentParser()

parser.add_argument('--input', '-i', action='store', dest='input_path', type=str, help='full path to input folder')
parser.add_argument('--output', '-o', action='store', dest='output_path', type=str, help='full path to output folder')
parser.add_argument('--ffmpeg', action='store', dest='ffmpeg_path', default='ffmpeg', type=str, help='The full path to ffmpeg.  Use on Windows if executing script from somewhere other than where ffmpeg is located')
parser.add_argument('--ffprobe', action='store', dest='ffprobe_path', default='ffprobe', type=str, help='The full path to ffprobe.  Use on Windows if executing script from somewhere other than where ffprobe is located')
parser.add_argument('--qcli', action='store', dest='qcli_path', default='qcli', type=str, help='The full path to qcli.  Use on Windows if executing script from somewhere other than where qcli is located')
parser.add_argument('--mediaconch', action='store', dest='mediaconch_path', default='mediaconch', type=str, help='The full path to qcli.  Use on Windows if executing script from somewhere other than where qcli is located')
parser.add_argument('--debug', required=False, action='store_true', help='view pulled ffprobe metadata and ffmpeg command without transcoding anything. Currently only works with --transcode')
parser.add_argument('--verbose', required=False, action='store', help='view ffmpeg output when transcoding')
parser.add_argument('--mixdown', action='store', dest='mixdown', default='copy', type=str, help='How the audio streams will be mapped for the access copy. If excluded, this will default to copying the stream configuration of the input. Inputs include: copy, 4to3, and 4to2. 4to3 takes 4 mono tracks and mixes tracks 1&2 to stereo while leaving tracks 3&4 mono. 4to2 takes 4 mono tracks and mixes tracks 1&2 and 3&4 to stereo.')

args = parser.parse_args()

#TO DO (low priority): collect all args into a single list or dictionary so that you can easily pass them between functions?
#in particular, should concatenate paths to tools into a list or dictionary so that tools for logging and json creation functions are more portable (for example, also being usable for film transcoding despite using some different tools)

pm_identifier = 'pm'
ac_identifier = 'ac'
inventoryName = 'transcode_inventory.csv'
metadata_identifier = 'meta'
ffv1_slice_count = '16'
ffmpegPath = args.ffmpeg_path
ffprobePath = args.ffprobe_path
qcliPath = args.qcli_path
mediaconchPath = args.mediaconch_path
mixdown = args.mixdown

def check_mixdown_arg(mixdown):
    mixdown_list = ['copy', '4to3', '4to2']
    #TO DO add swap as an option to allow switching tracks 3&4 with tracks 1&2
    if not mixdown in mixdown_list:
        print("The selected audio mixdown is not a valid value")
        print ("please use one of: copy, swap, 4to3, 4to2")
        quit()
    
def input_check(indir):
    if '-i' in sys.argv or '--input' in sys.argv:
        indir = args.input_path
    else:
        print ("No input provided")
        quit()

    if not os.path.isdir(indir):
        print('input is not a directory')
        quit()
    return indir

def output_check(outdir):
    #if output directory is not specified, input directory will be used
    if '-o' in sys.argv or '--output' in sys.argv:
        outdir = args.output_path
    else:
        print('Output not specified. Using input directory as Output directory')
        outdir = args.input_path
    
    if not os.path.isdir(outdir):
        print('output is not a directory')
        quit()
    return (outdir)
        

check_mixdown_arg(mixdown)

#assign input directory and output directory
indir = input_check(args.input_path)
outdir = output_check(args.output_path)

#verify that mediaconch policies are present
movPolicy = os.path.join(os.path.dirname(__file__), 'mediaconch_policies', 'AJA_NTSC_VHS-4AS-MOV.xml')
avfuncs.mediaconch_policy_exists(movPolicy)
#mkvPolicy = os.path.join(os.path.dirname(__file__), 'mediaconch_policies', 'AJA_NTSC_VHS-4AS-FFV1.xml')
#avfuncs.mediaconch_policy_exists(mkvPolicy)

'''
csvInventory = os.path.join(indir, inventoryName)
if os.path.isfile(csvInventory):
    csvDict = {}
    panasonic_ag1980 = 'panasonic ag-1980'
    with open(csvInventory)as f:
        reader = csv.DictReader(f, delimiter=',')
        for row in reader:
            name = row['File name']
            csvDict[name] = []
            #date needs to be formatted as yyyy-mm-dd
            captureDate = row['Capture Date']
            digitizationOperator = row['Digitization Operator']
            vtr = row['VTR']
            if panasonic_ag1980.lower() in vtr.lower():
                print('Your VCR exists!')
            vtrOut = row['VTR Output Used']
            #tbc = row['TBC']
            #tbcOut = row['TBC Output Used']
            #adc = row['Capture Device']
            #format coding history as:
            #A=ANALOG,T=Panasonic AG-1980P; J5TC00083; S-Video
            #A=ANALOG,T=DPS 295; 9211295054; Component (Beta Levels)
            #A=SDI,T=HD10AVA; K0190697; ADC
            #A=v210,T=Kona-1-T-R0; U11963
            csvData = {
            'Capture Date' : captureDate,
            'Digitization Operator' : digitizationOperator,
            'VTR' : vtr,
            'VTR Output Used' : vtrOut,
            'TBC' : row['TBC'],
            'TBC Output Used' : row['TBC Output Used'],
            'Capture Device' : row['Capture Device']
            }
            csvDict[name].append(csvData)
        print (csvDict)
        printMe = csvDict.get('P0358-GRNG-N879-t00001')
        print(printMe)
    quit()
else:
    print('unable to find csv file')
    quit()
'''

for input in glob.glob1(indir, "*.mov"):
    inputAbsPath = os.path.join(indir, input)
    baseFilename = input.replace('.mov','')
    baseOutput = os.path.join(outdir, baseFilename)
    pmOutputFolder = os.path.join(baseOutput, pm_identifier)
    acOutputFolder = os.path.join(baseOutput, ac_identifier)
    metaOutputFolder = os.path.join(baseOutput, metadata_identifier)
    mkvFilename = os.path.join(baseFilename + '-' + pm_identifier + '.mkv')
    outputAbsPath = os.path.join(pmOutputFolder, mkvFilename)
    acAbsPath = os.path.join(acOutputFolder, baseFilename + '-' + ac_identifier + '.mp4')
    tempMasterFile = os.path.join(pmOutputFolder, baseFilename + '-tmp.mkv')
    framemd5File = os.path.join(pmOutputFolder, baseFilename + '-' + pm_identifier + '.framemd5')
    #transcode start time
    tstime = 'Pending'
    #transcode finish time
    tftime = 'Pending'    
        
    #get ffprobe metadata
    #input_file_metadata, input_techMetaV, input_techMetaA = avfuncs.ffprobe_report(ffprobePath, inputAbsPath)
    
    input_metadata = avfuncs.ffprobe_report(ffprobePath, inputAbsPath)
    print(input_metadata)
    print(input_metadata['techMetaV']['color primaries'])
    quit()
    
    #check input file in Mediaconch    
    MOV_mediaconchResults = avfuncs.run_mediaconch(mediaconchPath, inputAbsPath, movPolicy)    
    
    #create a list of needed output folders and make them
    outFolders = [pmOutputFolder, acOutputFolder, metaOutputFolder]
    avfuncs.create_transcode_output_folders(baseOutput, outFolders)

    #build ffmpeg command
    print ("**losslessly transcoding", baseFilename + "**")
    audioStreamCounter = input_techMetaA.get('audio stream count')
    ffmpeg_command = [ffmpegPath]
    if not args.verbose:
        ffmpeg_command.extend(('-loglevel', 'error'))
    ffmpeg_command.extend(['-i', inputAbsPath, '-map', '0', '-dn', '-c:v', 'ffv1', '-level', '3', '-g', '1', '-slices', ffv1_slice_count, '-slicecrc', '1'])
    if input_techMetaV.get('color primaries'):
        ffmpeg_command.extend(('-color_primaries', input_techMetaV.get('color primaries')))
    if input_techMetaV.get('color transfer'):
        ffmpeg_command.extend(('-color_trc', input_techMetaV.get('color transfer')))
    if input_techMetaV.get('color space'):
        ffmpeg_command.extend(('-colorspace', input_techMetaV.get('color space')))
    if input_techMetaA.get('audio stream count') > 0:
        ffmpeg_command.extend(('-c:a', 'copy'))
    ffmpeg_command.extend((tempMasterFile, '-f', 'framemd5', '-an', framemd5File))
    
    #log transcode start time
    tstime = datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')
    #execute ffmpeg command
    subprocess.run(ffmpeg_command)
    
    #remux to attach framemd5
    add_attachment = [ffmpegPath, '-loglevel', 'error', '-i', tempMasterFile, '-c', 'copy', '-map', '0', '-attach', framemd5File, '-metadata:s:t:0', 'mimetype=application/octet-stream', '-metadata:s:t:0', 'filename=' + framemd5File, outputAbsPath]    
    if os.path.isfile(tempMasterFile):
        subprocess.call(add_attachment)
        #log transcode finish time
        tftime = datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        avfuncs.ffv1_lossless_transcode_cleanup(tempMasterFile, framemd5File)
    else:
        print ("There was an issue finding the file", tempMasterFile)
    
    #If ffv1 file was succesfully created, do remaining verification and transcoding work
    if os.path.isfile(outputAbsPath):
        #create checksum sidecar file for preservation master
        print ("*creating checksum*")
        mkvHash = avfuncs.hashlib_md5(outputAbsPath)
        with open (os.path.join(pmOutputFolder, baseFilename + '-' + pm_identifier + '.md5'), 'w',  newline='\n') as f:
            print(mkvHash, '*' + mkvFilename, file=f)
        
        #compare streamMD5s
        print ("*verifying losslessness*")
        mov_stream_sum = avfuncs.checksum_streams(ffmpegPath, inputAbsPath, input_techMetaA)
        mkv_stream_sum = avfuncs.checksum_streams(ffmpegPath, outputAbsPath, input_techMetaA)
        if mkv_stream_sum and mov_stream_sum:
            if mkv_stream_sum == mov_stream_sum:
                print ('stream checksums match.  Your file is lossless')
                streamMD5status = "PASS"
            else:
                print ('stream checksums do not match.  Output file may not be lossless')
                streamMD5status = "FAIL"
        
        #run ffprobe on the output file
        output_file_metadata, output_techMetaV, output_techMetaA = avfuncs.ffprobe_report(ffprobePath, outputAbsPath)
        #log system info
        systemInfo = avfuncs.generate_system_log(ffmpegPath, tstime, tftime)      
         
        #create json metadata file
        #TO DO: clean up how some of this information is imported here. Use nested dictionaries to combine a lot of these
        avfuncs.create_json(metaOutputFolder, metadata_identifier, systemInfo, outputAbsPath, input_file_metadata, input_techMetaV, input_techMetaA, mov_stream_sum, mkvHash, mkv_stream_sum, input, mkvFilename, baseFilename, streamMD5status, output_file_metadata, output_techMetaV, output_techMetaA, MOV_mediaconchResults)
        
        #create access copy
        print ('*transcoding access copy*')
        avfuncs.two_pass_h264_encoding(ffmpegPath, audioStreamCounter, mixdown, outputAbsPath, acAbsPath)
        
        #create checksum sidecar file for access copy
        acHash = avfuncs.hashlib_md5(acAbsPath)
        with open (os.path.join(acOutputFolder, baseFilename + '-' + ac_identifier + '.md5'), 'w',  newline='\n') as f:
            print(acHash, '*' + baseFilename + '-' + ac_identifier + '.mp4', file=f)
        
        #create spectrogram for pm audio channels
        if audioStreamCounter > 0:
            print ("*generating QC spectrograms*")
            channel_layout_list = input_techMetaA.get('channels')
            avfuncs.generate_spectrogram(ffmpegPath, outputAbsPath, channel_layout_list, metaOutputFolder, baseFilename)
        
        #create qctools report
        print ("*creating qctools report*")
        avfuncs.generate_qctools(qcliPath, outputAbsPath)
        
        #placeholder - start building csv output here
        csvRuntime = time.strftime("%H:%M:%S", time.gmtime(float(input_file_metadata.get('duration'))))
        print ("runtime to print =", csvRuntime)
        
    else:
        print ('No file in output folder.  Skipping file processing')

#at end, add a function to extract capture notes from csv file; possibly also VCR settings

#add ability to automatically pull trim times from CSV (-ss 00:00:02 -t 02:13:52)?
#import time
#timeIn = [get csv time1]
#timeOut = [get csv time2]
#t1 = datetime.datetime.strptime(timeIn, "%H:%M:%S")
#t2 = datetime.datetime.strptime(timeOut, "%H:%M:%S")
#may have to make it a string?
#trimtime = time.strftime('%H:%M:%S', time.gmtime(((60 * ((60 * t2.hour) + t2.minute)) + t2.second) - ((60 * ((60 * t1.hour) + t1.minute)) + t1.second)))
