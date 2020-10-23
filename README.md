# transcoding-scripts
Scripts for batch transcoding files<br/>

## VHS
### Flags
**--input**, **-i** INPUT_PATH      full path to input folder<br/>
**--output**, **-o** OUTPUT_PATH     full path to output folder<br/>
**--mixdown** MIXDOWN     Sets how audio streams will be mapped when transcoding the access copy. Inputs include: copy, 4to3, and 4to2. Defaults to copy. 4to3 mixes streams 1&2 to a single stereo stream and copies streams 3 and 4. 4to2 mixes streams 1&2 and 3&4 to two stereo streams.<br/>
**--verbose** VERBOSE     view ffmpeg output when transcoding<br/>

## Flags for custom tool paths
#### Only include if trying to use a version of the tool other than the system version or if the tool is not installed in the current path.
**--ffmpeg** FFMPEG_PATH<br/>
**--ffprobe** FFPROBE_PATH<br/>
**--qcli** QCLI_PATH<br/>
**--mediaconch** MEDIACONCH_PATH<br/>
