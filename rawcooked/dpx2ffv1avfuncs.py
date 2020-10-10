#!/usr/bin/env python3

import os
import sys
import hashlib
import subprocess
import platform
import json
import datetime
import glob
import shutil
import posixpath

def input_check(parameterDict):
    if parameterDict.get('input_path'):
        indir = parameterDict.get('input_path')
    else:
        print ("No input provided")
        quit()

    if not os.path.isdir(indir):
        print('input is not a directory')
        quit()
    return indir

def output_check(parameterDict):
    if parameterDict.get('output_path'):
        outdir = parameterDict.get('output_path')
    #if output directory is not specified, input directory will be used
    else:
        print('Output not specified. Using input directory as Output directory')
        outdir = parameterDict.get('input_path')
    
    if not os.path.isdir(outdir):
        print('output is not a directory')
        quit()
    return (outdir)

def assign_limit(parameterDict):
    if parameterDict.get('textlimit'):
        limit = parameterDict.get('textlimit')
    else:
        limit = None
    return limit

def get_immediate_subdirectories(folder):
    '''
    get immediate subdirectories of input
    used to create equivalent directory structure in output
    '''
    return [name for name in os.listdir(folder)
        if os.path.isdir(os.path.join(folder, name))]

'''
def define_inputfolder(indir, fname):
    inputfolder = None
    if '--subfolder_identifier' in sys.argv:
        subfolder_identifier = args.subfolder_identifier
        #assigning folder to act on as either foldername or foldername/pm
        inputfolder = os.path.join(indir, fname, subfolder_identifier)
    else:
        inputfolder = os.path.join(indir, fname)
    return inputfolder
'''
def create_transcode_output_folders(baseoutput, outputfolder):
    if not os.path.isdir(baseoutput):
        try:
            os.mkdir(baseoutput)
        except:
            print ("unable to create output folder:", outputfolder)
            quit
    else:
        print (baseoutput, "already exists")
    if not os.path.isdir(outputfolder):
        try:
            os.mkdir(outputfolder)
        except:
            print ("unable to create output folder:", outputfolder)
            quit
    else:
        print ("using existing folder", outputfolder, "as output")

def get_rawcooked_version(parameterDict):
    '''
    Returns the version of rawcooked
    '''
    rawcooked_version = 'RAWcooked'
    try:
        rawcooked_version = subprocess.check_output([
            parameterDict.get('rawcooked_path'), '--version'
        ]).decode("ascii").rstrip().split()[1]
    except:
        print ("Error getting rawcooked version")
        quit()
    return rawcooked_version
#this function is from the IFI's scripts.
#A few changes have been made to just return the version number

def get_ffmpeg_version(parameterDict):
    '''
    Returns the version of ffmpeg
    '''
    ffmpeg_version = 'ffmpeg'
    try:
        ffmpeg_version = subprocess.check_output([
            parameterDict.get('ffmpeg_path'), '-version'
        ]).decode("ascii").rstrip().splitlines()[0].split()[2]
    except:
        print ("Error getting ffmpeg version")
        quit()
    return ffmpeg_version

def get_sox_version():
    '''
    Returns the version of sox
    '''
    sox_version = 'sox'
    try:
        sox_version = subprocess.check_output([
            args.sox_path, '--version'
        ]).decode("ascii").rstrip().split()[2].replace("v", "")
    except:
        print ("Error getting SoX version")
        quit()
    return sox_version

def get_flac_version():
    '''
    Returns the version of flac encoder
    '''
    flac_version = 'flac'
    try:
        flac_version = subprocess.check_output([
            args.flac_path, '--version'
        ]).decode("ascii").rstrip().split()[1]
    except:
        print ("Error getting FLAC Encoder version")
        quit()
    return flac_version

def hashlib_md5(filename):
    '''
    Uses hashlib to return an MD5 checksum of an input filename
    '''
    read_size = 0
    last_percent_done = 0
    chksm = hashlib.md5()
    total_size = os.path.getsize(filename)
    with open(filename, 'rb') as f:
        while True:
            #2**20 is for reading the file in 1 MiB chunks
            buf = f.read(2**20)
            if not buf:
                break
            read_size += len(buf)
            chksm.update(buf)
            percent_done = 100 * read_size / total_size
            if percent_done > last_percent_done:
                sys.stdout.write('[%d%%]\r' % percent_done)
                sys.stdout.flush()
                last_percent_done = percent_done
    md5_output = chksm.hexdigest()
    return md5_output
#this function is from the IFI's scripts with a minor change
#open(str(filename)), 'rb') as f has been changed to open(filename, 'rb') as f

def get_folder_size(folder):
    '''
    Calculate the folder size
    '''
    total_size = 0
    d = os.scandir(folder)
    for entry in d:
        try:
            if entry.is_dir():
                total_size += get_folder_size(entry.path)
            else:
                total_size += entry.stat().st_size
        except FileNotFoundError:
            #file was deleted during scandir
            pass
        except PermissionError:
            return 0
    return total_size

'''
def dpx2ffv1_ffprobe_report(input_abspath):
        video_output = json.loads(subprocess.check_output([args.ffprobe_path, '-v', 'error', '-select_streams', 'v', '-show_entries', 'stream=codec_name,avg_frame_rate,codec_time_base,width,height,pix_fmt,codec_tag_string', input_file_abspath, '-of', 'json']).decode("ascii").rstrip())
        audio_output = json.loads(subprocess.check_output([args.ffprobe_path, '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=codec_name,codec_time_base,codec_tag_string', input_file_abspath, '-of', 'json']).decode("ascii").rstrip())
'''

def list_mkv_attachments(input_file_abspath, parameterDict):
    #could also identify with -select streams m:filename
    t_probe_out = json.loads(subprocess.check_output([parameterDict.get('ffprobe_path'), '-v', 'error', '-select_streams', 't', '-show_entries', 'stream_tags=filename', input_file_abspath, '-of', 'json']).decode("ascii").rstrip())
    tags = [streams.get('tags') for streams in (t_probe_out['streams'])]
    attachment_list = []
    for i in tags:
        filename = [i.get('filename')]
        attachment_list.extend(filename)
    return attachment_list

def dpx_md5_compare(dpxfolder):
    '''
    Returns two sets
    One from the original DPX sequence's md5 checksum
    The other from the calculated checksums of the decoded DPX sequence
    '''
    md5list = []
    orig_md5list = {}
    for i in os.listdir(dpxfolder):
        abspath = os.path.join(dpxfolder, i)
        if i.endswith(".md5"):
            orig_md5list = set(map(str.strip, open(abspath)))
        elif i.endswith(".xml"):
            pass
        else:
            y = hashlib_md5(abspath)
            filehash = y + ' *' + i
            md5list.append(filehash)
    compareset = set(md5list)
    return compareset, orig_md5list

def grab_actime(folder, parameterDict):
    '''
    Look for an ac folder containing an mp4 file
    If found, return the runtime
    '''
    acfolder = os.path.join(folder, 'ac')
    if os.path.isdir(acfolder):
        mp4file = glob.glob1(acfolder, "*.mp4")
        mp4counter = len(mp4file)
        if mp4counter == 1:
            for i in mp4file:
                file = os.path.join(acfolder, i)
                actime = subprocess.check_output([parameterDict.get('ffprobe_path'), '-v', 'error', file, '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1']).decode("ascii").rstrip()
                #this returns the total runtime in seconds
        elif mp4counter < 1:
            actime = "no mp4 files found in " + acfolder
        elif mp4counter > 1:
            actime = "more than 1 mp4 file found"
    else:
        actime = "no ac folder found"
    return actime
    #when comparing runtimes, you could check if this value is a float, which would allow you to know if there was an error here

def grab_pmtime(folder, subfolder_identifier, parameterDict):
    '''
    Look for a pm folder containing an mkv file
    If found, return the runtime
    '''
    pmfolder = os.path.join(folder, subfolder_identifier)
    if os.path.isdir(pmfolder):
        pmfile = glob.glob1(pmfolder, "*.mkv")
        mkvcounter = len(pmfile)
        if mkvcounter == 1:
            for i in pmfile:
                file = os.path.join(pmfolder, i)
                pmtime = subprocess.check_output([parameterDict.get('ffprobe_path'), '-v', 'error', file, '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1']).decode("ascii").rstrip()
                #this returns the total runtime in seconds
        elif mkvcounter < 1:
            pmtime = "no mkv files found in " + pmfolder
        elif mkvcounter > 1:
            pmtime = "more than 1 mkv file found"
    else:
        pmtime = "no pm folder found"
    return pmtime

def verification_check(folder):
    '''
    Parse the verification_log.txt file
    Print whether any issues were encountered
    '''
    verifile = os.path.join(folder, 'pm', "verification_log.txt")
    if not os.path.isfile(verifile):
        print('No verification_log.txt file found in', folder)
    else:
        with open(verifile) as f:
            data = f.read().split('\n')
            if 'Entries in original checksum not found in calculated checksum:' in data:
                checksums1 = data[data.index('Entries in original checksum not found in calculated checksum:') +1]
            if 'Entries in calculated checksum not found in original checksum:' in data:
                checksums2 = data[data.index('Entries in calculated checksum not found in original checksum:') +1]
            print(data[0])
            if not 'None' in checksums1:
                print('\t'"Entries found in the original checksum not found in calculated checksum", '\n''\t'"  See verification log for details")
            if not 'None' in checksums2:
                print('\t'"Entries found in the calculated checksum not found in original checksum", '\n''\t'"  See verification log for details")
            if 'Access Copy Runtime:' in data:
                try:
                    ac_runtime = float(data[data.index('Access Copy Runtime:') +1])
                except ValueError:
                    ac_runtime = None
            else:
                ac_runtime = "not logged"
            if 'Preservation Master Runtime:' in data:
                try:
                    pm_runtime = float(data[data.index('Preservation Master Runtime:') +1])
                except ValueError:
                    pm_runtime = None
                    print ("pm runtime is not a float")
            else:
                pm_runtime = "not logged"
            if ac_runtime and pm_runtime and not "not logged" in [ac_runtime] and not "not logged" in [pm_runtime]:
                runtime_total = ac_runtime - pm_runtime
                if abs(runtime_total) > 0.01 or not 'None' in checksums1 or not 'None' in checksums2:
                    if runtime_total > 0.01:
                        print('\t'"Access copy is", runtime_total, "seconds longer than FFV1 file")
                    elif runtime_total < -0.01:
                        print('\t'"Access copy is", abs(runtime_total), "seconds shorter than FFV1 file")
            elif pm_runtime and not ac_runtime:
                print('\t'"ac runtime is not a float")
            elif not pm_runtime and not ac_runtime:
                print('\t'"ac and pm runtimes are not floats")
            elif "not logged" in pm_runtime and "not logged" in ac_runtime:
                print('\t'"ac and pm runtimes were not logged")
            elif "not logged" in pm_runtime and not "not logged" in ac_runtime:
                print('\t'"pm runtime was not logged")
            elif not "not logged" in pm_runtime and "not logged" in ac_runtime:
                print('\t'"ac runtime was not logged")
