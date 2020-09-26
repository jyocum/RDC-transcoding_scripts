#!/usr/bin/env python3

import argparse
import sys
import os
import glob
import avfuncs
import subprocess
from datetime import datetime
import platform
import json

if sys.version_info[0] < 3:
    raise Exception("Python 3 or a more recent version is required.")

parser = argparse.ArgumentParser()

parser.add_argument('--input', '-i', action='store', dest='input_path', type=str, help='full path to input folder')
parser.add_argument('--output', '-o', action='store', dest='output_path', type=str, help='full path to output folder')
parser.add_argument('--ffmpeg', action='store', dest='ffmpeg_path', default='ffmpeg', type=str, help='The full path to ffmpeg.  Use on Windows if executing script from somewhere other than where ffmpeg is located')
parser.add_argument('--ffprobe', action='store', dest='ffprobe_path', default='ffprobe', type=str, help='The full path to ffprobe.  Use on Windows if executing script from somewhere other than where ffprobe is located')
parser.add_argument('--debug', required=False, action='store_true', help='view pulled ffprobe metadata and ffmpeg command without transcoding anything. Currently only works with --transcode')
parser.add_argument('--verbose', required=False, action='store_true', help='view ffmpeg output when transcoding')

args = parser.parse_args()

pm_identifier = 'pm'
am_identifier = 'ac'
ffv1_slice_count = '16'

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

#assign input directory and output directory
indir = input_check(args.input_path)
outdir = output_check(args.output_path)

for input in glob.glob1(indir, "*.mov"):
    inputAbsPath = os.path.join(indir, input)
    baseFilename = input.replace('.mov','')
    baseOutput = os.path.join(outdir, baseFilename)
    outputFolder = os.path.join(baseOutput, pm_identifier)
    mkvFilename = os.path.join(baseFilename + '_' + pm_identifier + '.mkv')
    outputAbsPath = os.path.join(outputFolder, mkvFilename)
    tempMasterFile = os.path.join(outputFolder, baseFilename + '_tmp.mkv')
    framemd5File = os.path.join(outputFolder, baseFilename + '_' + pm_identifier + '.framemd5')
    ffmpegPath = args.ffmpeg_path
    ffprobePath = args.ffprobe_path
    
    # TO DO: Create meta folder and a transcode log. Validate the file in mediaconch before transcoding.  If it does not validate, go to the next file and log in the transcode log.
    
    #get ffprobe metadata
    input_file_metadata, input_techMetaV, input_techMetaA = avfuncs.ffprobe_report(ffprobePath, inputAbsPath)
    
    if args.debug:
        '''
        Debugging tool for printing ffprobe data
        Use --debug to run
        '''
        print ('\n', '* * *', 'DEBUG MODE', '* * *', '\n')
        print("INPUT FILE PATH:", inputAbsPath)
        print ("METADATA:", '\n', input_file_metadata, '\n', input_techMetaV, '\n', input_techMetaA)
        print ("OUTPUT FILE PATH:", outputAbsPath)
    else:
        #create folder for output
        avfuncs.create_transcode_output_folders(baseOutput, outputFolder)
    
    tstime = 'Pending'
    tftime = 'Pending'
    #build ffmpeg command
    print ("**losslessly transcoding", baseFilename + "**")
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
    
    if args.debug:
        '''
        Continuation of debugging tool for printing ffmpeg command
        Use --debug to run
        '''
        print("FFMPEG COMMAND:", '\n', ffmpeg_command)
        print("* * * * * * * * * * * * * * * * * * * *")
    else:
        tstime = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        #execute ffmpeg command
        subprocess.run(ffmpeg_command)
    
    if not args.debug:
        #remux to attach framemd5
        add_attachment = [ffmpegPath, '-loglevel', 'error', '-i', tempMasterFile, '-c', 'copy', '-map', '0', '-attach', framemd5File, '-metadata:s:t:0', 'mimetype=application/octet-stream', '-metadata:s:t:0', 'filename=' + framemd5File, outputAbsPath]    
        if os.path.isfile(tempMasterFile):
            subprocess.call(add_attachment)
            tftime = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
            avfuncs.ffv1_lossless_transcode_cleanup(tempMasterFile, framemd5File)
        else:
            print ("There was an issue finding creating the file", outputAbsPath)
        
        #create md5 file for output file if it exists
        if os.path.isfile(outputAbsPath):
            mkvhash = avfuncs.hashlib_md5(outputAbsPath)
            with open (os.path.join(outputFolder, baseFilename + '_' + pm_identifier + '.md5'), 'w',  newline='\n') as f:
                print(mkvhash, '*' + mkvFilename, file=f)
            print ("**Verifying losslessness**")
            mov_stream_sum = avfuncs.checksum_streams(ffmpegPath, inputAbsPath, input_techMetaA)
            mkv_stream_sum = avfuncs.checksum_streams(ffmpegPath, outputAbsPath, input_techMetaA)
            print (mkv_stream_sum)
            print (mov_stream_sum)
            if mkv_stream_sum and mov_stream_sum:
                if mkv_stream_sum == mov_stream_sum:
                    print ('stream checksums match.  Your file is lossless')
                else:
                    print ('stream checksums do not match.  Output file may not be lossless')
        else:
            print ('No file in output folder.  Skipping file processing')
        
        #run ffprobe on the output file
        output_file_metadata, output_techMetaV, output_techMetaA = avfuncs.ffprobe_report(ffprobePath, outputAbsPath)
        
        #create dictionary for json output
        data = {}
        data[baseFilename] = []
        
        #gather system info for json output
        osinfo = platform.platform()
        ffvers = avfuncs.get_ffmpeg_version(ffmpegPath)
        systemInfo = {
        'operating system': osinfo,
        'ffmpeg version': ffvers,
        'transcode start time': tstime,
        'transcode end time': tftime
        #add capture software/version maybe -- would have to pull from csv
        }

        #gather pre and post transcode file metadata for json output
        mov_file_meta = {}
        ffv1_file_meta = {}
        mov_file_meta[input] = []
        ffv1_file_meta[mkvFilename] = []
        mov_file_meta[input].append(input_file_metadata)
        #append stream checksum
        mov_md5_dict = {
        'a/v streamMD5': mkv_stream_sum
        }
        ffv1_file_meta[mkvFilename].append(output_file_metadata)
        ffv1_md5_dict = {
        'md5 checksum': mkvhash,
        'a/v streamMD5': mkv_stream_sum
        }
        mov_file_meta[input].append(mov_md5_dict)
        ffv1_file_meta[mkvFilename].append(ffv1_md5_dict)
        
        #gather technical metadata for json output
        techdata = {}
        video_techdata = {}
        audio_techdata = {}
        techdata['technical metadata'] = []
        video_techdata['video'] = []
        audio_techdata['audio'] = []
        video_techdata['video'].append(input_techMetaV)
        audio_techdata['audio'].append(input_techMetaA)
        techdata['technical metadata'].append(video_techdata)
        techdata['technical metadata'].append(audio_techdata)

        data[baseFilename].append(systemInfo)
        data[baseFilename].append(ffv1_file_meta)
        data[baseFilename].append(mov_file_meta)        
        data[baseFilename].append(techdata)
        with open(os.path.join(baseOutput, baseFilename + 'meta.json'), 'w', newline='\n') as outfile:
            json.dump(data, outfile, indent=4)
        
        #at end, add a function to extract capture notes from csv file; possibly also VCR settings
        #generate qctools report
''' 
    
if args.access:
    print("access transcoding scripts will be here")
'''