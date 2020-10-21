#!/usr/bin/env python3

import argparse
import sys
import os
import glob
import subprocess
import datetime
from mov2ffv1parameters import args
import avfuncs
import corefuncs

if sys.version_info[0] < 3:
    raise Exception("Python 3 or a more recent version is required.")

#TO DO: general cleanup

parameterDict = vars(args)

pm_identifier = 'pm'
ac_identifier = 'ac'
inventoryName = 'transcode_inventory.csv'
mov_mediaconch_policy = 'AJA_NTSC_VHS-4AS-MOV.xml'
mkv_mediaconch_policy = 'AJA_NTSC_VHS-4AS-MKV.xml'
metadata_identifier = 'meta'
ffv1_slice_count = '16'
ffmpegPath = parameterDict.get('ffmpeg_path')
ffprobePath = parameterDict.get('ffprobe_path')
qcliPath = parameterDict.get('qcli_path')
mediaconchPath = parameterDict.get('mediaconch_path')
mixdown = parameterDict.get('mixdown')
        
#assign input directory and output directory
indir = corefuncs.input_check(parameterDict)
outdir = corefuncs.output_check(parameterDict)
#check that mixdown argument is valid if provided
avfuncs.check_mixdown_arg(mixdown)
#check that required programs are present
corefuncs.qcli_check(qcliPath)
corefuncs.mediaconch_check(mediaconchPath)
corefuncs.ffprobe_check(ffprobePath)
ffvers = avfuncs.get_ffmpeg_version(ffmpegPath)

#verify that mediaconch policies are present
movPolicy = os.path.join(os.path.dirname(__file__), 'mediaconch_policies', mov_mediaconch_policy)
corefuncs.mediaconch_policy_exists(movPolicy)
mkvPolicy = os.path.join(os.path.dirname(__file__), 'mediaconch_policies', mkv_mediaconch_policy)
corefuncs.mediaconch_policy_exists(mkvPolicy)

csvInventory = os.path.join(indir, inventoryName)
#TO DO: separate out csv and json related functions that are currently in avfuncs into dedicated csv or json related py files
csvDict = avfuncs.import_csv(csvInventory)

print ("***STARTING PROCESS***")

for movFilename in glob.glob1(indir, "*.mov"):
    inputAbsPath = os.path.join(indir, movFilename)
    baseFilename = movFilename.replace('.mov','')
    baseOutput = os.path.join(outdir, baseFilename)
    pmOutputFolder = os.path.join(baseOutput, pm_identifier)
    mkvFilename = os.path.join(baseFilename + '-' + pm_identifier + '.mkv')
    outputAbsPath = os.path.join(pmOutputFolder, mkvFilename)
    tempMasterFile = os.path.join(pmOutputFolder, baseFilename + '-tmp.mkv')
    framemd5File = os.path.join(baseFilename + '-' + pm_identifier + '.framemd5')
    framemd5AbsPath = os.path.join(pmOutputFolder, framemd5File)
    acOutputFolder = os.path.join(baseOutput, ac_identifier)
    acAbsPath = os.path.join(acOutputFolder, baseFilename + '-' + ac_identifier + '.mp4')
    metaOutputFolder = os.path.join(baseOutput, metadata_identifier)
    jsonOutputFile = os.path.join(metaOutputFolder, baseFilename + '-' + metadata_identifier + '.json')
    #transcode start time
    tstime = 'Pending'
    #transcode finish time
    tftime = 'Pending'    
    
    #get information about item from csv inventory
    try:
        item_csvDict = csvDict.get(baseFilename)
    except:
        print("unable to locate", baseFilename, "in csv data.")
        item_csvDict = {}
    
    #generate ffprobe metadata from input
    input_metadata = avfuncs.ffprobe_report(ffprobePath, inputAbsPath, movFilename)  
    
    #create a list of needed output folders and make them
    outFolders = [pmOutputFolder, acOutputFolder, metaOutputFolder]
    avfuncs.create_transcode_output_folders(baseOutput, outFolders)
    
    print ("\n")
    print ("**losslessly transcoding", baseFilename + "**")
    #build ffmpeg command
    audioStreamCounter = input_metadata['techMetaA']['audio stream count']
    ffmpeg_command = [ffmpegPath]
    if not parameterDict.get('verbose'):
        ffmpeg_command.extend(('-loglevel', 'error'))
    ffmpeg_command.extend(['-i', inputAbsPath, '-map', '0', '-dn', '-c:v', 'ffv1', '-level', '3', '-g', '1', '-slices', ffv1_slice_count, '-slicecrc', '1'])
    #TO DO: consider putting color data in a list or dict to replace the following if statements with a single if statement in a for loop
    if input_metadata['techMetaV']['color primaries']:
        ffmpeg_command.extend(('-color_primaries', input_metadata['techMetaV']['color primaries']))
    if input_metadata['techMetaV']['color transfer']:
        ffmpeg_command.extend(('-color_trc', input_metadata['techMetaV']['color transfer']))
    if input_metadata['techMetaV']['color space']:
        ffmpeg_command.extend(('-colorspace', input_metadata['techMetaV']['color space']))
    if audioStreamCounter > 0:
        ffmpeg_command.extend(('-c:a', 'copy'))
    ffmpeg_command.extend((tempMasterFile, '-f', 'framemd5', '-an', framemd5AbsPath))
    
    #log transcode start time
    tstime = datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')
    #execute ffmpeg command
    subprocess.run(ffmpeg_command)
    
    #remux to attach framemd5
    add_attachment = [ffmpegPath, '-loglevel', 'error', '-i', tempMasterFile, '-c', 'copy', '-map', '0', '-attach', framemd5AbsPath, '-metadata:s:t:0', 'mimetype=application/octet-stream', '-metadata:s:t:0', 'filename=' + framemd5File, outputAbsPath]    
    if os.path.isfile(tempMasterFile):
        subprocess.call(add_attachment)
        #log transcode finish time
        tftime = datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        avfuncs.ffv1_lossless_transcode_cleanup(tempMasterFile, framemd5AbsPath)
    else:
        print ("There was an issue finding the file", tempMasterFile)
    
    #If ffv1 file was succesfully created, do remaining verification and transcoding work
    if os.path.isfile(outputAbsPath):
        #create checksum sidecar file for preservation master
        print ("*creating checksum*")
        mkvHash = corefuncs.hashlib_md5(outputAbsPath)
        with open (os.path.join(pmOutputFolder, baseFilename + '-' + pm_identifier + '.md5'), 'w',  newline='\n') as f:
            print(mkvHash, '*' + mkvFilename, file=f)
        
        #compare streamMD5s
        print ("*verifying losslessness*")
        mov_stream_sum = avfuncs.checksum_streams(ffmpegPath, inputAbsPath, audioStreamCounter)
        mkv_stream_sum = avfuncs.checksum_streams(ffmpegPath, outputAbsPath, audioStreamCounter)
        #TO DO: move into own function and return pass or fail
        if mkv_stream_sum == mov_stream_sum:
            print ('stream checksums match.  Your file is lossless')
            streamMD5status = "PASS"
        else:
            print ('stream checksums do not match.  Output file may not be lossless')
            streamMD5status = "FAIL"
        
        #create a dictionary with the mediaconch results from the MOV and MKV files
        mediaconchResults_dict = {
        'MOV Mediaconch Policy': avfuncs.run_mediaconch(mediaconchPath, inputAbsPath, movPolicy),
        'MKV Mediaconch Policy': avfuncs.run_mediaconch(mediaconchPath, outputAbsPath, mkvPolicy),
        }
        #check if any mediaconch results failed and append failed policies to results
        mediaconchResults = avfuncs.parse_mediaconchResults(mediaconchResults_dict)
        
        #run ffprobe on the output file
        output_metadata = avfuncs.ffprobe_report(ffprobePath, outputAbsPath, mkvFilename)
        #log system info
        systemInfo = avfuncs.generate_system_log(ffvers, tstime, tftime)      
        
        qcResults = avfuncs.qc_results(input_metadata, output_metadata, mediaconchResults, streamMD5status)
        
        avfuncs.write_output_csv(outdir, mkvFilename, output_metadata, qcResults)
        
        #create json metadata file
        #TO DO: combine checksums into a single dictionary to reduce variable needed here
        avfuncs.create_json(jsonOutputFile, systemInfo, input_metadata, mov_stream_sum, mkvHash, mkv_stream_sum, baseFilename, output_metadata, item_csvDict, qcResults)
        
        #create access copy
        print ('*transcoding access copy*')
        avfuncs.two_pass_h264_encoding(ffmpegPath, audioStreamCounter, mixdown, outputAbsPath, acAbsPath)
        
        #create checksum sidecar file for access copy
        acHash = corefuncs.hashlib_md5(acAbsPath)
        with open (os.path.join(acOutputFolder, baseFilename + '-' + ac_identifier + '.md5'), 'w',  newline='\n') as f:
            print(acHash, '*' + baseFilename + '-' + ac_identifier + '.mp4', file=f)
        
        #create spectrogram for pm audio channels
        if audioStreamCounter > 0:
            print ("*generating QC spectrograms*")
            channel_layout_list = input_metadata['techMetaA']['channels']
            avfuncs.generate_spectrogram(ffmpegPath, outputAbsPath, channel_layout_list, metaOutputFolder, baseFilename)
        
        #create qctools report
        print ("*creating qctools report*")
        avfuncs.generate_qctools(qcliPath, outputAbsPath)
        
    else:
        print ('No file in output folder.  Skipping file processing')

#TO DO: (low/not priority) add ability to automatically pull trim times from CSV (-ss 00:00:02 -t 02:13:52)?
#import time
#timeIn = [get csv time1]
#timeOut = [get csv time2]
#t1 = datetime.datetime.strptime(timeIn, "%H:%M:%S")
#t2 = datetime.datetime.strptime(timeOut, "%H:%M:%S")
#may have to make it a string?
#trimtime = time.strftime('%H:%M:%S', time.gmtime(((60 * ((60 * t2.hour) + t2.minute)) + t2.second) - ((60 * ((60 * t1.hour) + t1.minute)) + t1.second)))
