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

def qcli_check(qcliPath):
    '''
    checks that qcli exists by running its -version command
    '''
    try:
        subprocess.check_output([qcliPath, '-version']).decode("ascii").rstrip().splitlines()[0]
    except:
        print('Error locating qcli')
        quit()

def mediaconch_check(mediaconchPath):
    '''
    checks that mediaconch exists by running its -v command
    ''' 
    try:
        subprocess.check_output([mediaconchPath, '-v']).decode("ascii").rstrip().splitlines()[0]
    except:
        print('Error locating mediaconch')
        quit()

def ffprobe_check(ffprobePath):
    '''
    checks that ffprobe exists by running its -version command
    '''
    try:
        subprocess.check_output([ffprobePath, '-version']).decode("ascii").rstrip().splitlines()[0].split()[2]
    except:
        print("Error locating ffprobe")
        quit()
    
def check_mixdown_arg(mixdown):
    mixdown_list = ['copy', '4to3', '4to2']
    #TO DO add swap as an option to allow switching tracks 3&4 with tracks 1&2
    if not mixdown in mixdown_list:
        print("The selected audio mixdown is not a valid value")
        print ("please use one of: copy, swap, 4to3, 4to2")
        quit()  

def mediaconch_policy_exists(policy_path):
    if not os.path.isfile(policy_path):
        print("unable to find mediaconch policy:", policy_path)
        print("Check if file exists before running")
        quit()

def hashlib_md5(filename):
    '''
    Uses hashlib to return an MD5 checksum of an input filename
    Credit: IFI scripts
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

def ffprobe_report(ffprobePath, input_file_abspath):
    '''
    returns nested dictionary with ffprobe metadata
    '''
    video_output = json.loads(subprocess.check_output([ffprobePath, '-v', 'error', '-select_streams', 'v', '-show_entries', 'stream=codec_name,avg_frame_rate,codec_time_base,width,height,pix_fmt,sample_aspect_ratio,display_aspect_ratio,color_range,color_space,color_transfer,color_primaries,chroma_location,field_order,codec_tag_string', input_file_abspath, '-of', 'json']).decode("ascii").rstrip())
    audio_output = json.loads(subprocess.check_output([ffprobePath, '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=codec_long_name,bits_per_raw_sample,sample_rate,channels', input_file_abspath, '-of', 'json']).decode("ascii").rstrip())
    format_output = json.loads(subprocess.check_output([ffprobePath, '-v', 'error', '-show_entries', 'format=duration,size,nb_streams', input_file_abspath, '-of', 'json']).decode("ascii").rstrip())
    data_output = json.loads(subprocess.check_output([ffprobePath, '-v', 'error', '-select_streams', 'd', '-show_entries', 'stream=codec_tag_string', input_file_abspath, '-of', 'json']).decode("ascii").rstrip())
    attachment_output = json.loads(subprocess.check_output([ffprobePath, '-v', 'error', '-select_streams', 't', '-show_entries', 'stream_tags=filename', input_file_abspath, '-of', 'json']).decode("ascii").rstrip())
    
    #cleaning up attachment output
    tags = [streams.get('tags') for streams in (attachment_output['streams'])]
    attachment_list = []
    for i in tags:
        filename = [i.get('filename')]
        attachment_list.extend(filename)
    
    #parse ffprobe metadata lists
    video_codec_name_list = [stream.get('codec_name') for stream in (video_output['streams'])]
    audio_codec_name_list = [stream.get('codec_long_name') for stream in (audio_output['streams'])]
    data_streams = [stream.get('codec_tag_string') for stream in (data_output['streams'])]
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
    audio_bitrate = [stream.get('bits_per_raw_sample') for stream in (audio_output['streams'])]
    audio_sample_rate = [stream.get('sample_rate') for stream in (audio_output['streams'])]
    audio_channels = [stream.get('channels') for stream in (audio_output['streams'])]
    audio_stream_count = len(audio_codec_name_list)
    
    file_metadata = {
    'file size': format_output.get('format')['size'],
    'duration': format_output.get('format')['duration'],
    'streams' : format_output.get('format')['nb_streams'],
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
    
    ffprobe_metadata = {'file metadata' : file_metadata, 'techMetaV' : techMetaV, 'techMetaA' : techMetaA}
    
    return ffprobe_metadata

def ffv1_lossless_transcode_cleanup(tmpmkv, framemd5):
    '''
    Removes temporary files created when losslessly transcoding v210 to FFV1
    '''
    try:
        os.remove(tmpmkv)
    except FileNotFoundError:
        print ("tmp mkv file seems to be missing")
    try:
        os.remove(framemd5)
    except FileNotFoundError:
        print ("framemd5 file seems to be missing")

def checksum_streams(ffmpegPath, input, audioStreamCounter):
    '''
    Gets the stream md5 of a file
    Uses both video and all audio streams if audio is present
    '''
    stream_sum_command = [ffmpegPath, '-loglevel', 'error', '-i', input, '-map', '0:v']
    if audioStreamCounter > 0:
        stream_sum_command.extend(('-map', '0:a'))
    stream_sum_command.extend(('-f', 'md5', '-'))
    stream_sum = subprocess.check_output(stream_sum_command).decode("ascii").rstrip()
    stream_sum = stream_sum.replace('MD5=', '')
    return stream_sum

def two_pass_h264_encoding(ffmpegPath, audioStreamCounter, mixdown, pmAbsPath, acAbsPath):
    #add flag to exclude attachments
    if os.name == 'nt':
        nullOut = 'NUL'
    else:
        nullOut = '/dev/null'
    pass1 = [ffmpegPath, '-loglevel', 'error', '-y', '-i', pmAbsPath, '-c:v', 'libx264', '-preset', 'medium', '-b:v', '8000k', '-pix_fmt', 'yuv420p', '-pass', '1']
    if audioStreamCounter > 0:
        if mixdown == 'copy':    
            pass1 += ['-c:a', 'aac', '-b:a', '128k']
        if mixdown == '4to3' and audioStreamCounter == 4:
            pass1 += ['-filter_complex', '[0:a:0][0:a:1]amerge=inputs=2[a]', '-map', '0:v', '-map', '[a]', '-map', '0:a:2', '-map', '0:a:3']
        if mixdown == '4to2' and audioStreamCounter == 4:
            pass1 += ['-filter_complex', '[0:a:0][0:a:1]amerge=inputs=2[a];[0:a:2][0:a:3]amerge=inputs=2[b]', '-map', '0:v', '-map', '[a]', '-map', '[b]']
    pass1 += ['-f', 'mp4', nullOut]
    pass2 = [ffmpegPath, '-loglevel', 'error', '-y', '-i', pmAbsPath, '-c:v', 'libx264', '-preset', 'medium', '-b:v', '8000k', '-pix_fmt', 'yuv420p', '-pass', '2']
    if audioStreamCounter > 0:
        if mixdown == 'copy':
            pass2 += ['-c:a', 'aac', '-b:a', '128k']
        if mixdown == '4to3' and audioStreamCounter == 4:
            pass2 += ['-filter_complex', '[0:a:0][0:a:1]amerge=inputs=2[a]', '-map', '0:v', '-map', '[a]', '-map', '0:a:2', '-map', '0:a:3']
        if mixdown == '4to2' and audioStreamCounter == 4:
            pass2 += ['-filter_complex', '[0:a:0][0:a:1]amerge=inputs=2[a];[0:a:2][0:a:3]amerge=inputs=2[b]', '-map', '0:v', '-map', '[a]', '-map', '[b]']
    pass2 += [acAbsPath]
    subprocess.run(pass1)
    subprocess.run(pass2)

def generate_spectrogram(ffmpegPath, input, channel_layout_list, outputFolder, outputName):
    '''
    Creates a spectrogram for each audio track in the input
    '''
    spectrogram_resolution = "1928x1080"
    for index, item in enumerate(channel_layout_list):
        output = os.path.join(outputFolder, outputName + '_0a' + str(index) + '.png')
        spectrogram_args = [ffmpegPath]
        spectrogram_args += ['-loglevel', 'error', '-y']
        spectrogram_args += ['-i', input, '-lavfi']
        if item > 1:
            spectrogram_args += ['[0:a:%(a)s]showspectrumpic=mode=separate:s=%(b)s' % {"a" : index, "b" : spectrogram_resolution}]
        else:
            spectrogram_args += ['[0:a:%(a)s]showspectrumpic=s=%(b)s' % {"a" : index, "b" : spectrogram_resolution}]
        spectrogram_args += [output]
        subprocess.run(spectrogram_args)

def generate_qctools(qcliPath, input):
    '''
    uses qcli to generate a QCTools report
    '''
    qctools_args = [qcliPath, '-i', input]
    subprocess.run(qctools_args)

def run_mediaconch(mediaconchPath, input, policy):
    mediaconchResults = subprocess.check_output([mediaconchPath, '--policy=' + policy, input]).decode("ascii").rstrip().split()[0]
    if mediaconchResults == "pass!":
        mediaconchResults = "PASS"
    else:
        mediaconchResults = "FAIL"
    return mediaconchResults

def generate_system_log(ffvers, tstime, tftime):
    #gather system info for json output
    osinfo = platform.platform()
    systemInfo = {
    'operating system': osinfo,
    'ffmpeg version': ffvers,
    'transcode start time': tstime,
    'transcode end time': tftime
    #TO DO: add capture software/version maybe -- would have to pull from csv
    }
    return systemInfo
    
def create_json(metaOutputFolder, metadata_identifier, systemInfo, outputAbsPath, input_metadata, mov_stream_sum, mkvHash, mkv_stream_sum, input, mkvFilename, baseFilename, streamMD5status, output_metadata, MOV_mediaconchResults):
    input_techMetaV = input_metadata.get('techMetaV')
    input_techMetaA = input_metadata.get('techMetaA')
    input_file_metadata = input_metadata.get('file metadata')
    output_techMetaV = output_metadata.get('techMetaV')
    output_techMetaA = output_metadata.get('techMetaA')
    output_file_metadata = output_metadata.get('file metadata')
     
    #create dictionary for json output
    data = {}
    data[baseFilename] = []

    #gather pre and post transcode file metadata for json output
    mov_file_meta = {}
    ffv1_file_meta = {}
    mov_file_meta[input] = []
    ffv1_file_meta[mkvFilename] = []
    #add stream checksums to metadata
    mov_md5_dict = {'a/v streamMD5': mov_stream_sum}
    ffv1_md5_dict = {'md5 checksum': mkvHash, 'a/v streamMD5': mkv_stream_sum}
    input_file_metadata = {**input_file_metadata, **mov_md5_dict}
    output_file_metadata = {**output_file_metadata, **ffv1_md5_dict}
    mov_file_meta[input].append(input_file_metadata)
    ffv1_file_meta[mkvFilename].append(output_file_metadata)
    
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
    
    QC_results = {}
    QC_results['QC'] = []
    if output_techMetaA == input_techMetaA and output_techMetaV == input_techMetaV:
        QC_techMeta = "PASS"
    else:
        print("input and output technical metadata do not match")
        QC_techMeta = "FAIL"
    QC_results['QC'] = {
    'Pre/Post Transcode Technical Metadata': QC_techMeta,
    'MOV Mediaconch Policy': MOV_mediaconchResults,
    'Stream Checksums': streamMD5status
    }

    data[baseFilename].append(systemInfo)
    data[baseFilename].append(ffv1_file_meta)
    data[baseFilename].append(mov_file_meta)        
    data[baseFilename].append(techdata)
    data[baseFilename].append(QC_results)
    with open(os.path.join(metaOutputFolder, baseFilename + '-' + metadata_identifier + '.json'), 'w', newline='\n') as outfile:
        json.dump(data, outfile, indent=4)