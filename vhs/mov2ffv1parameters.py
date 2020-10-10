#!/usr/bin/env python3

import argparse
import sys

if sys.version_info[0] < 3:
    raise Exception("Python 3 or a more recent version is required.")

parser = argparse.ArgumentParser()

parser.add_argument('--input', '-i', action='store', dest='input_path', type=str, help='full path to input folder')
parser.add_argument('--output', '-o', action='store', dest='output_path', type=str, help='full path to output folder')
parser.add_argument('--ffmpeg', action='store', dest='ffmpeg_path', default='ffmpeg', type=str, help='The full path to ffmpeg.  Use on Windows if executing script from somewhere other than where ffmpeg is located')
parser.add_argument('--ffprobe', action='store', dest='ffprobe_path', default='ffprobe', type=str, help='The full path to ffprobe.  Use on Windows if executing script from somewhere other than where ffprobe is located')
parser.add_argument('--qcli', action='store', dest='qcli_path', default='qcli', type=str, help='The full path to qcli.  Use on Windows if executing script from somewhere other than where qcli is located')
parser.add_argument('--mediaconch', action='store', dest='mediaconch_path', default='mediaconch', type=str, help='The full path to qcli.  Use on Windows if executing script from somewhere other than where qcli is located')
parser.add_argument('--verbose', required=False, action='store', help='view ffmpeg output when transcoding')
parser.add_argument('--mixdown', action='store', dest='mixdown', default='copy', type=str, help='How the audio streams will be mapped for the access copy. If excluded, this will default to copying the stream configuration of the input. Inputs include: copy, 4to3, and 4to2. 4to3 takes 4 mono tracks and mixes tracks 1&2 to stereo while leaving tracks 3&4 mono. 4to2 takes 4 mono tracks and mixes tracks 1&2 and 3&4 to stereo.')

args = parser.parse_args()