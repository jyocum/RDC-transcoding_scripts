#!/usr/bin/env python3

import argparse
import sys
import os
import glob
import avfuncs
import subprocess
import datetime
import json
import equipment_dict
from mov2ffv1parameters import args

if sys.version_info[0] < 3:
    raise Exception("Python 3 or a more recent version is required.")

parameterDict = vars(args)

pm_identifier = 'pm'
ac_identifier = 'ac'
inventoryName = 'transcode_inventory.csv'
metadata_identifier = 'meta'
ffv1_slice_count = '16'
ffmpegPath = parameterDict.get('ffmpeg_path')
ffprobePath = parameterDict.get('ffprobe_path')
qcliPath = parameterDict.get('qcli_path')
mediaconchPath = parameterDict.get('mediaconch_path')
mixdown = parameterDict.get('mixdown')
        
#assign input directory and output directory
indir = avfuncs.input_check(parameterDict)
outdir = avfuncs.output_check(parameterDict)
#check that mixdown argument is valid if provided
avfuncs.check_mixdown_arg(mixdown)
#check that required programs are present
avfuncs.qcli_check(qcliPath)
avfuncs.mediaconch_check(mediaconchPath)
avfuncs.ffprobe_check(ffprobePath)
ffvers = avfuncs.get_ffmpeg_version(ffmpegPath)

#verify that mediaconch policies are present
movPolicy = os.path.join(os.path.dirname(__file__), 'mediaconch_policies', 'AJA_NTSC_VHS-4AS-MOV.xml')
avfuncs.mediaconch_policy_exists(movPolicy)
#mkvPolicy = os.path.join(os.path.dirname(__file__), 'mediaconch_policies', 'AJA_NTSC_VHS-4AS-FFV1.xml')
#avfuncs.mediaconch_policy_exists(mkvPolicy)

csvInventory = os.path.join(indir, inventoryName)
#TO DO: separate out csv and json related vunctions that are currently in avfuncs into dedicated csv or json related py files
csvDict = avfuncs.import_csv(csvInventory, equipment_dict)

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
    
    #get information about item from csv inventory
    try:
        csvDict = csvDict.get(baseFilename)
    except:
        print("unable to locate", baseFilename, "in csv data.")
        csvDict = {}
    
    #generate ffprobe metadata from input
    input_metadata = avfuncs.ffprobe_report(ffprobePath, inputAbsPath)
    
    #check input file in Mediaconch    
    MOV_mediaconchResults = avfuncs.run_mediaconch(mediaconchPath, inputAbsPath, movPolicy)    
    
    #create a list of needed output folders and make them
    outFolders = [pmOutputFolder, acOutputFolder, metaOutputFolder]
    avfuncs.create_transcode_output_folders(baseOutput, outFolders)
    '''
    #****CURRENTLY FOR TESTING - REMOVE FOR ACTUAL USE****
    with open(os.path.join(metaOutputFolder, baseFilename + '-' + metadata_identifier + '.json'), 'w', newline='\n') as outfile:
        json.dump(csvDict, outfile, indent=4)
    quit()
    ''''
    #build ffmpeg command
    print ("**losslessly transcoding", baseFilename + "**")
    audioStreamCounter = input_metadata['techMetaA']['audio stream count']
    ffmpeg_command = [ffmpegPath]
    if not parameterDict.get('verbose'):
        ffmpeg_command.extend(('-loglevel', 'error'))
    ffmpeg_command.extend(['-i', inputAbsPath, '-map', '0', '-dn', '-c:v', 'ffv1', '-level', '3', '-g', '1', '-slices', ffv1_slice_count, '-slicecrc', '1'])
    if input_metadata['techMetaV']['color primaries']:
        ffmpeg_command.extend(('-color_primaries', input_metadata['techMetaV']['color primaries']))
    if input_metadata['techMetaV']['color transfer']:
        ffmpeg_command.extend(('-color_trc', input_metadata['techMetaV']['color transfer']))
    if input_metadata['techMetaV']['color space']:
        ffmpeg_command.extend(('-colorspace', input_metadata['techMetaV']['color space']))
    if audioStreamCounter > 0:
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
        mov_stream_sum = avfuncs.checksum_streams(ffmpegPath, inputAbsPath, audioStreamCounter)
        mkv_stream_sum = avfuncs.checksum_streams(ffmpegPath, outputAbsPath, audioStreamCounter)
        if mkv_stream_sum == mov_stream_sum:
            print ('stream checksums match.  Your file is lossless')
            streamMD5status = "PASS"
        else:
            print ('stream checksums do not match.  Output file may not be lossless')
            streamMD5status = "FAIL"
        
        #run ffprobe on the output file
        output_metadata = avfuncs.ffprobe_report(ffprobePath, outputAbsPath)
        #log system info
        systemInfo = avfuncs.generate_system_log(ffvers, tstime, tftime)      
        
        qcResults = avfuncs.qc_results(input_metadata, output_metadata, MOV_mediaconchResults, streamMD5status)
        
        avfuncs.write_output_csv(outdir, mkvFilename, output_metadata, qcResults)
        
        #create json metadata file
        #TO DO: clean up how some of this information is passed around. Use dictionaries and nested dictionaries to reduce clutter with variables
        avfuncs.create_json(metaOutputFolder, metadata_identifier, systemInfo, outputAbsPath, input_metadata, mov_stream_sum, mkvHash, mkv_stream_sum, input, mkvFilename, baseFilename, output_metadata, csvDict, qcResults)
        
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
