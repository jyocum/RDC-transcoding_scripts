#!/usr/bin/env python3

#from funcs import parameters
#from funcs import toolbox_parser
import os
import sys
import hashlib
import subprocess
import platform
import json
from datetime import datetime
import glob
import shutil
import posixpath

def construct_output(command_identifier):
    #allow output path to be left unassigned, in which case it defaults to input path
    #specified output should also override toolbox: include "or (args.output_path and args.toolbox_profile)"
    if args.output_path:
        outdir = args.output_path
        if outdir.startswith( '{' ):
            json_acceptable_string = outdir.replace("'", "\"")
            outdir = json.loads(json_acceptable_string)
            #output base folder can use keywords like =input
            parse_output_construction(outdir, command_identifier)

    elif args.toolbox_profile:
        print("using toolbox profile")
        opened_toolbox = toolbox_parser.load_toolbox_profile()
        outdir = toolbox_parser.return_value(opened_toolbox, 'io manager', 'output')
        parse_output_construction(outdir, command_identifier)
        #print(outdir)
        #make the output parsing for the normal output flag a function and just have this reference the same function
        #may actually be able to combine this with the above, although transcoding multiple derivatives in one command will be difficult
        #one solution might be to have another key containing a list of sub-keys
    elif args.input_path and not args.output_path:
        #TO DO should probably develop this a little further to match the input folder for each item
        #this could probably be done using a keyword to have it match the final input folder when assigning
        outdir = args.input_path
    return outdir

def define_inputfolder(indir, fname):
    inputfolder = None
    if '--subfolder_identifier' in sys.argv:
        subfolder_identifier = args.subfolder_identifier
        #assigning folder to act on as either foldername or foldername/pm
        inputfolder = os.path.join(indir, fname, subfolder_identifier)
    else:
        inputfolder = os.path.join(indir, fname)
    return inputfolder

def create_transcode_output_folders(baseOutput, outputFolder):
    if not os.path.isdir(baseOutput):
        try:
            os.mkdir(baseOutput)
        except:
            print ("unable to create output folder:", baseOutput)
            quit
    else:
        print (baseOutput, "already exists")
        print ('Proceeding')
        
    if not os.path.isdir(outputFolder):
        try:
            os.mkdir(outputFolder)
        except:
            print ("unable to create output folder:", outputFolder)
            quit
    else:
        print ("using existing folder", outputFolder, "as output")

def get_ffmpeg_version(ffmpegPath):
    '''
    Returns the version of ffmpeg
    '''
    ffmpeg_version = 'ffmpeg'
    try:
        ffmpeg_version = subprocess.check_output([
            ffmpegPath, '-version'
        ]).decode("ascii").rstrip().splitlines()[0].split()[2]
    except:
        print ("Error getting ffmpeg version")
        quit()
    return ffmpeg_version

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

#get immediate subdirectories of input
#used to create equivalent directory structure in output
def get_immediate_subdirectories(folder):
        return [name for name in os.listdir(folder)
            if os.path.isdir(os.path.join(folder, name))]

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

def get_size_format(b, factor=1024, suffix="B"):
    '''
    Scale bytes to its proper byte format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    '''
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if b < factor:
            return f"{b:.2f}{unit}{suffix}"
        b /= factor
    return f"{b:.2f}Y{suffix}"
#credit: How to Get the Size of Directories in Python, Abdou Rockikz
#this is currently not being used
#may use this for a later part of the script to total file sizes -- sum sizes in bytes from json files, then run that through this

def ffprobe_report(ffprobePath, input_file_abspath):
    '''
    returns dictionaries with ffprobe metadata
    '''
    video_output = json.loads(subprocess.check_output([ffprobePath, '-v', 'error', '-select_streams', 'v', '-show_entries', 'stream=codec_name,avg_frame_rate,codec_time_base,width,height,pix_fmt,sample_aspect_ratio,display_aspect_ratio,color_range,color_space,color_transfer,color_primaries,chroma_location,field_order,codec_tag_string', input_file_abspath, '-of', 'json']).decode("ascii").rstrip())
    audio_output = json.loads(subprocess.check_output([ffprobePath, '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=codec_long_name,bits_per_sample,sample_rate', input_file_abspath, '-of', 'json']).decode("ascii").rstrip())
    format_output = json.loads(subprocess.check_output([ffprobePath, '-v', 'error', '-show_entries', 'format=duration,size,nb_streams', input_file_abspath, '-of', 'json']).decode("ascii").rstrip())
    data_output = json.loads(subprocess.check_output([ffprobePath, '-v', 'error', '-select_streams', 'd', '-show_entries', 'stream=codec_tag_string', input_file_abspath, '-of', 'json']).decode("ascii").rstrip())
    attachment_output = json.loads(subprocess.check_output([ffprobePath, '-v', 'error', '-select_streams', 't', '-show_entries', 'stream_tags=filename', input_file_abspath, '-of', 'json']).decode("ascii").rstrip())
    
    #cleaning up data_output
    if data_output.get('streams'):
        for i in data_output.get('streams'):
            i['data type'] = i.pop('codec_tag_string')
    #cleaning up attachment output
    tags = [streams.get('tags') for streams in (attachment_output['streams'])]
    attachment_list = []
    for i in tags:
        filename = [i.get('filename')]
        attachment_list.extend(filename)
    
    #parse ffprobe metadata    
    file_size = format_output.get('format')['size']
    duration = format_output.get('format')['duration']
    video_codec_name_list = [stream.get('codec_name') for stream in (video_output['streams'])]
    audio_codec_name_list = [stream.get('codec_long_name') for stream in (audio_output['streams'])]
    total_stream_count = format_output.get('format')['nb_streams']
    data_streams = data_output.get('streams')
    width = [stream.get('width') for stream in (video_output['streams'])][0]
    height = [stream.get('height') for stream in (video_output['streams'])][0]
    pixel_format = [stream.get('pix_fmt') for stream in (video_output['streams'])][0]
    sar = [stream.get('sample_aspect_ratio') for stream in (video_output['streams'])][0]
    dar = [stream.get('display_aspect_ratio') for stream in (video_output['streams'])][0]
    framerate = [stream.get('avg_frame_rate') for stream in (video_output['streams'])][0]
    color_space = [stream.get('color_space') for stream in (video_output['streams'])][0]
    color_range = [stream.get('color_range') for stream in (video_output['streams'])][0]
    color_transfer = [stream.get('color_transfer') for stream in (video_output['streams'])][0]
    color_primaries = [stream.get('color_primaries') for stream in (video_output['streams'])][0]
    audio_bitrate = [stream.get('bits_per_sample') for stream in (audio_output['streams'])]
    audio_sample_rate = [stream.get('sample_rate') for stream in (audio_output['streams'])]
    audio_stream_count = len(audio_codec_name_list)
    
    file_metadata = {
    'file size': file_size,
    'duration': duration,
    'streams' : total_stream_count,
    'video streams': video_codec_name_list,
    'audio streams' : audio_codec_name_list,
    'data streams' : data_streams,
    'attachments' : attachment_list
    }
    
    techMetaV = {
    'width' : width,
    'height' : height,
    'sample aspect ratio': sar,
    'display aspect ratio' : dar,
    'pixel format' : pixel_format,
    'framerate' : framerate,
    'color space' : color_space,
    'color range' : color_range,
    'color primaries' : color_primaries,
    'color transfer' : color_transfer
    }
    
    techMetaA = {
    'audio stream count' : audio_stream_count,
    'audio bitrate' : audio_bitrate,
    'audio sample rate' : audio_sample_rate
    }
    
    return file_metadata, techMetaV, techMetaA

def list_mkv_attachments(input_file_abspath):
    #could also identify with -select streams m:filename
    t_probe_out = json.loads(subprocess.check_output([args.ffprobe_path, '-v', 'error', '-select_streams', 't', '-show_entries', 'stream_tags=filename', input_file_abspath, '-of', 'json']).decode("ascii").rstrip())
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

def grab_actime(folder):
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
                actime = subprocess.check_output([args.ffprobe_path, '-v', 'error', file, '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1']).decode("ascii").rstrip()
                #this returns the total runtime in seconds
        elif mp4counter < 1:
            actime = "no mp4 files found in " + acfolder
        elif mp4counter > 1:
            actime = "more than 1 mp4 file found"
    else:
        actime = "no ac folder found"
    return actime
    #when comparing runtimes, you could check if this value is a float, which would allow you to know if there was an error here

def grab_pmtime(folder):
    '''
    Look for a pm folder containing an mkv file
    If found, return the runtime
    '''
    pmfolder = os.path.join(folder, 'pm')
    if os.path.isdir(pmfolder):
        pmfile = glob.glob1(pmfolder, "*.mkv")
        mkvcounter = len(pmfile)
        if mkvcounter == 1:
            for i in pmfile:
                file = os.path.join(pmfolder, i)
                pmtime = subprocess.check_output([args.ffprobe_path, '-v', 'error', file, '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1']).decode("ascii").rstrip()
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

def create_checksum_manifest(folder):
    file_set = set()
    for dir_, _, files in os.walk(folder):
        for file_name in files:
            rel_dir = os.path.relpath(dir_, folder)
            rel_file = os.path.join(rel_dir, file_name).replace(os.sep, posixpath.sep)
            #probably not the most efficient way to bypass the base folder
            #but it works
            if not "./" in rel_file:
                md5chksum = hashlib_md5(os.path.join(folder, rel_dir, file_name))
                md5out = md5chksum + " *" + rel_file
                file_set.add(md5out)
    return file_set

def ffv1_lossless_transcode_cleanup(tmpmkv, framemd5):
    try:
        os.remove(tmpmkv)
    except FileNotFoundError:
        print ("tmp mkv file seems to be missing")
    try:
        os.remove(framemd5)
    except FileNotFoundError:
        print ("framemd5 file seems to be missing")

def checksum_streams(ffmpegPath, input, input_techMetaA):
    stream_sum_command = [ffmpegPath, '-loglevel', 'error', '-i', input, '-map', '0:v']
    if input_techMetaA.get('audio stream count') > 0:
        stream_sum_command.extend(('-map', '0:a'))
    stream_sum_command.extend(('-f', 'md5', '-'))
    stream_sum = subprocess.check_output(stream_sum_command).decode("ascii").rstrip()
    return stream_sum