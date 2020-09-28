#!/usr/bin/env python3

import os
import sys
import hashlib
import subprocess
import platform
import json

def define_inputfolder(indir, fname):
    inputfolder = None
    if '--subfolder_identifier' in sys.argv:
        subfolder_identifier = args.subfolder_identifier
        #assigning folder to act on as either foldername or foldername/pm
        inputfolder = os.path.join(indir, fname, subfolder_identifier)
    else:
        inputfolder = os.path.join(indir, fname)
    return inputfolder

def create_transcode_output_folders(baseOutput, outputFolderList):
    if not os.path.isdir(baseOutput):
        try:
            os.mkdir(baseOutput)
        except:
            print ("unable to create output folder:", baseOutput)
            quit()
    else:
        print (baseOutput, "already exists")
        print ('Proceeding')
        
    for folder in outputFolderList:
        if not os.path.isdir(folder):
            try:
                os.mkdir(folder)
            except:
                print ("unable to create output folder:", folder)
                quit()
        else:
            print ("using existing folder", folder, "as output")

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

def ffprobe_report(ffprobePath, input_file_abspath):
    '''
    returns dictionaries with ffprobe metadata
    '''
    video_output = json.loads(subprocess.check_output([ffprobePath, '-v', 'error', '-select_streams', 'v', '-show_entries', 'stream=codec_name,avg_frame_rate,codec_time_base,width,height,pix_fmt,sample_aspect_ratio,display_aspect_ratio,color_range,color_space,color_transfer,color_primaries,chroma_location,field_order,codec_tag_string', input_file_abspath, '-of', 'json']).decode("ascii").rstrip())
    audio_output = json.loads(subprocess.check_output([ffprobePath, '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=codec_long_name,bits_per_sample,sample_rate,channels', input_file_abspath, '-of', 'json']).decode("ascii").rstrip())
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
    audio_channels = [stream.get('channels') for stream in (audio_output['streams'])]
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
    'audio sample rate' : audio_sample_rate,
    'channels' : audio_channels
    }
    
    return file_metadata, techMetaV, techMetaA

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

def two_pass_h264_encoding(ffmpegPath, audioStreamCounter, pmAbsPath, acAbsPath):
    #add flag to exclude attachments
    if os.name == 'nt':
        nullOut = 'NUL'
    else:
        nullOut = '/dev/null'
    pass1 = [ffmpegPath, '-loglevel', 'error', '-y', '-i', pmAbsPath, '-c:v', 'libx264', '-preset', 'medium', '-b:v', '8000k', '-pix_fmt', 'yuv420p', '-pass', '1']
    if audioStreamCounter > 0:
        #TO DO: map audio to stereo pairs if first two are mono? if tracks >= 2, combine the first 2 to stereo
        pass1 += ['-c:a', 'aac', '-b:a', '128k']
    pass1 += ['-f', 'mp4', nullOut]
    pass2 = [ffmpegPath, '-loglevel', 'error', '-i', pmAbsPath, '-c:v', 'libx264', '-preset', 'medium', '-b:v', '8000k', '-pix_fmt', 'yuv420p', '-pass', '2']
    if audioStreamCounter > 0:
        #TO DO: map audio to stereo pairs if first two are mono? if tracks >= 2, combine the first 2 to stereo
        pass2 += ['-c:a', 'aac', '-b:a', '128k']
    pass2 += [acAbsPath]
    subprocess.run(pass1)
    subprocess.run(pass2)

def generate_spectrogram(ffmpegPath, input, channel_layout_list, outputFolder, outputName):
    spectrogram_resolution = "1928x1080"
    for index, item in enumerate(channel_layout_list):
        output = os.path.join(outputFolder, outputName + '_0a' + str(index) + '.png')
        spectrogram_args = [ffmpegPath]
        spectrogram_args += ['-loglevel', 'error']
        spectrogram_args += ['-i', input, '-lavfi']
        if item > 1:
            spectrogram_args += ['[0:a:%(a)s]showspectrumpic=mode=separate:s=%(b)s' % {"a" : index, "b" : spectrogram_resolution}]
        else:
            spectrogram_args += ['[0:a:%(a)s]showspectrumpic=s=%(b)s' % {"a" : index, "b" : spectrogram_resolution}]
        spectrogram_args += [output]
        subprocess.run(spectrogram_args)

def make_qctools(input):
    '''
    Source: IFI Scripts
    Runs an ffprobe process that stores QCTools XML info as a variable.
    A file is not actually created here.
    '''
    qctools_args = [args.ffprobe_path, '-f', 'lavfi', '-i',]
    qctools_args += ["movie=%s:s=v+a[in0][in1],[in0]signalstats=stat=tout+vrep+brng,cropdetect=reset=1:round=1,split[a][b];[a]field=top[a1];[b]field=bottom[b1],[a1][b1]psnr[out0];[in1]ebur128=metadata=1,astats=metadata=1:reset=1:length=0.4[out1]" % input]
    qctools_args += ['-show_frames', '-show_versions', '-of', 'xml=x=1:q=1', '-noprivate']
    print(qctools_args)
    qctoolsreport = subprocess.check_output(qctools_args).decode("ascii").rstrip()
    return str(qctoolsreport)

def write_qctools_gz(qctoolsxml, sourcefile):
    '''
    Source: IFI Scripts
    This accepts a variable containing XML that is written to a file.
    '''
    with open(qctoolsxml, "w+") as f:
        f.write(make_qctools(sourcefile))
    #TO DO check if gzip exists before running qctools
    #on Windows install cygwin, then in Windows go to Edit the System Environment Variables
    #In Advanced tab, click Environment Variables button
    #In new window, select Path under User Variables for your username and then Edit
    #Add C:\cygwin64\bin
    #gzip should now be accessible from the Windows command line
    subprocess.call(['gzip', qctoolsxml])
    #use subprocess.run