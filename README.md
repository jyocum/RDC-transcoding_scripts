# transcoding-scripts
Scripts for batch transcoding files<br/>

## VHS
### Flags
**--input**, **-i** INPUT_PATH      full path to input folder<br/>
**--output**, **-o** OUTPUT_PATH     full path to output folder. If left blank, this will default to the same folder as the input.<br/>
**--mixdown** MIXDOWN     Sets how audio streams will be mapped when transcoding the access copy. Inputs include: `copy`, `4to3`, and `4to2`. Defaults to copy. 4to3 mixes streams 1&2 to a single stereo stream and copies streams 3 and 4. 4to2 mixes streams 1&2 and 3&4 to two stereo streams.<br/>
**--verbose** VERBOSE     view ffmpeg output when transcoding<br/>

### Flags for custom tool paths
#### Only include if trying to use a version of the tool other than the system version or if the tool is not installed in the current path.
**--ffmpeg** FFMPEG_PATH<br/>
**--ffprobe** FFPROBE_PATH<br/>
**--qcli** QCLI_PATH<br/>
**--mediaconch** MEDIACONCH_PATH<br/>

### Usage
-The input should be a folder containing v210/MOV files that you want to losslessly transcode to FFV1/MKV.<br/>
-Place the transcode_inventory.csv file in the input folder with the video files and add any associated inventory information. Doing so allows the script to pull the inventory metadata and use it for some of the QC steps. The csv file also supplies additional metadata for the sidecar json file that will be produced.<br/>
-It is recommended to use a program like Data Curator (github.com/qcif/data-curator) to edit the CSV file to avoid any autoformatting.<br/>
-In order for the script to match a v210/MOV file with its associated inventory row the v210/MOV file minus the ".mov" extension **MUST** be identical to the name entered in the "File name" column in the inventory.<br/>

**Example command:**
	`aja_mov_2_ffv1.py -i input_folder -o output_folder --mixdown 4to3`