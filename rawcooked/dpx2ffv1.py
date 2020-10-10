#!/usr/bin/env python3

import os
import sys
import subprocess
import platform
import json
import datetime
import shutil
import glob
from dpx2ffv1parameters import args
import dpx2ffv1avfuncs

#TO DO: general clean up (improve readability by separating out some functions); merge avfuncs scripts between different transcode scripts where overlapping functions exist and separate format specific functions better

if sys.version_info[0] < 3:
    raise Exception("Python 3 or a more recent version is required.")

parameterDict = vars(args)

if args.dpx2ffv1:
    #set up the input, output, and other folder/file sctructure elements
    #expected folder/file structure is input/item_name/subfolder_identifier/item_name_0000001.dpx
    indir = dpx2ffv1avfuncs.input_check(parameterDict)
    outdir = dpx2ffv1avfuncs.output_check(parameterDict)
    #TO DO: allow running without subfolder identifier to support having the dpx files directly in the item_name folder?
    #set the subfolder_identifier. Defaults to 'pm' if not specified
    if parameterDict.get('subfolder_identifier'):
        subfolder_identifier = parameterDict.get('subfolder_identifier')
    else:
        subfolder_identifier = 'pm'
    #set a limit so that the command only runs on item_name folders containing the string specified
    limit = dpx2ffv1avfuncs.assign_limit(parameterDict)
    #if specifying a list of folders to run on from a text file, get inputs from there
    if parameterDict.get('textlist_path'):
        with open(parameterDict.get('textlist_path')) as f:
            lines = [line.rstrip() for line in f]
    #else the list of folders to run on are the item_name folders in the input
    else:
        lines = dpx2ffv1avfuncs.get_immediate_subdirectories(indir)
    
    checklist = []
    for item_name in lines:
        if not limit or (limit) in item_name:
            #currently the input folder name is fixed as input/item_name/pm for consistency in the structure of the RAWcooked data
            if os.path.isdir(os.path.join(indir, item_name, subfolder_identifier)):
                #TO DO: differentiate subfolder_identifier and dpx_subfolder_identifier
                indirbase = os.path.join(indir, item_name, subfolder_identifier)
                outpathbase = os.path.join(outdir, item_name)
                outpathfull = os.path.join(outpathbase, subfolder_identifier)
                ffv1_name = os.path.join(item_name + '_' + subfolder_identifier + '.mkv')
                mkv_abspath = os.path.join(outpathfull, ffv1_name)
                #TO DO: it may be better to make the default behavior be to just run rawcooked on item_name
                #then you could add a flag where you specify pm folders if they exist

                #TO DO check for md5 file in dpx folders
                #if not found, generate and output to input folder

                print('\n'"***Processing", item_name + "***" + '\n')

                #gather system metadata
                osinfo = platform.platform()
                ffvers = dpx2ffv1avfuncs.get_ffmpeg_version(parameterDict)
                rawcvers = dpx2ffv1avfuncs.get_rawcooked_version(parameterDict)
                tstime = datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')

                #build output directory
                try:
                    os.mkdir(outpathbase)
                except FileExistsError:
                    print("Output directory already exists in", outdir)
                    quit()
                if subfolder_identifier:
                    try:
                        os.mkdir(outpathfull)
                    except FileExistsError:
                        print("pm folder already exists in output")
                        quit()

                #build and execute rawcooked command
                rawcooked_command = [parameterDict.get('rawcooked_path'), '--check', '1', '-s', '10000000']
                if parameterDict.get('framerate'):
                    rawcooked_command.extend(('-framerate', parameterDict.get('framerate')))
                rawcooked_command.extend((indirbase, '-o', mkv_abspath))
                subprocess.call(rawcooked_command)
                
                #log transcode finish time
                tftime = datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')
                
                #if output exists, create an md5checksum
                if os.path.isfile(mkv_abspath):
                    mkvhash = dpx2ffv1avfuncs.hashlib_md5(mkv_abspath)
                else:
                    mkvhash = None
                #write md5 checksum to md5 file
                with open (os.path.join(outpathfull, item_name + '_' + subfolder_identifier + '.md5'), 'w',  newline='\n') as f:
                    print(mkvhash, '*' + ffv1_name, file=f)

                data = {}
                data[item_name] = []
                metadict = {
                'operating system': osinfo,
                'ffmpeg version': ffvers,
                'rawcooked version': rawcvers,
                'transcode start time': tstime,
                'transcode end time': tftime
                }
                #note that the size is output in bytes.  This can be converted to MiB by dividing by 1024**2 or GiB by dividing by 1024**3
                dpxsize = dpx2ffv1avfuncs.get_folder_size(os.path.join(indir, item_name, subfolder_identifier))
                #log ffv1 file size
                #This uses outpathfull so that it will not fail if there is no mkv file
                mkvsize = dpx2ffv1avfuncs.get_folder_size(outpathfull)
                attachments = dpx2ffv1avfuncs.list_mkv_attachments(mkv_abspath, parameterDict)
                #TO DO: Log other information
                #framerate =
                #width
                #height
                #stream count (video/audio)
                post_transcode_dict = {
                'file name': ffv1_name,
                'md5 checksum': mkvhash,
                'compressed size': mkvsize,
                'uncompressed size': dpxsize,
                'attachments': attachments
                }
                metadict.update(post_transcode_dict)
                data[item_name].append(metadict)
                with open(os.path.join(outpathfull, item_name + '_pm.json'), 'w', newline='\n') as outfile:
                    json.dump(data, outfile, indent=4)

                #Confirm the losslessness of the ffv1 file
                #decodes and verifies checksum, then compares runtimes between the ac and pm files
                #can be skipped by using the --notparanoid flag
                if parameterDict.get('notparanoid') == False:
                    dpxoutpath = args.dpxcheck_path

                    print('\n''\n'"Decoding", ffv1_name, "back to DPX for reversibility check" + '\n')

                    #if statement to determine where to decode DPX sequence to
                    if '--dpxcheck' in sys.argv:
                        #maybe make this try/except instead of if/else
                        if not os.path.isdir(dpxoutpath):
                            print('provided dpx verification folder is not a valid output.  Using ', item_name, ' pm folder instead')
                            dpxverifolder = os.path.join(outpathfull, item_name + '_dpx')
                        else:
                            dpxverifolder = os.path.join(dpxoutpath, item_name + '_dpx')
                    else:
                        dpxverifolder = os.path.join(outpathfull, item_name + '_dpx')

                    #run rawcooked, outputting to directory determined previously
                    subprocess.call([args.rawcooked_path, mkv_abspath, '-o', dpxverifolder])

                    print('\n'"Verifying DPX checksums in", dpxverifolder + '\n')

                    compareset, orig_md5list = dpx2ffv1avfuncs.dpx_md5_compare(os.path.join(dpxverifolder, 'pm'))

                    with open(os.path.join(indir, os.path.join(outpathfull, 'verification_log.txt')), 'a',  newline='\n') as f:
                        print(ffv1_name, file=f)
                        result1 = [x for x in orig_md5list if not x in compareset]
                        print('\n'"Entries in original checksum not found in calculated checksum:", file=f)
                        if not result1:
                            print("None", file=f)
                        else:
                            print(result1, file=f)
                        result2 = [x for x in compareset if not x in orig_md5list]
                        print('\n'"Entries in calculated checksum not found in original checksum:", file=f)
                        if not result2:
                            print("None", file=f)
                        else:
                            print(result2, file=f)

                    #compare runtimes between the ac and pm files
                    #can be skipped using the --lessparanoid flag
                    if parameterDict.get('lessparanoid') == False:
                        #It may be a good idea to format the runtime outputs as sets or lists
                        ac_runtime = dpx2ffv1avfuncs.grab_actime(os.path.join(indir, item_name), parameterDict)
                        pm_runtime = dpx2ffv1avfuncs.grab_pmtime(outpathbase, subfolder_identifier, parameterDict)

                        with open(os.path.join(indir, os.path.join(outpathfull, 'verification_log.txt')), 'a',  newline='\n') as f:
                            print('\n'"Access Copy Runtime:", file=f)
                            print(ac_runtime, file=f)
                            print('\n'"Preservation Master Runtime:", file=f)
                            print(pm_runtime, file=f)

                    #delete dpx verification folder
                    shutil.rmtree(dpxverifolder)

                    checklist.append(outpathbase)

            elif not os.path.isdir(os.path.join(indir, item_name, 'pm')):
                print('no pm folder in input directory')
        elif limit and not (limit) in item_name:
            print(item_name, 'does not contain ', limit)

    if parameterDict.get('notparanoid') == False and checklist:
        print("* * * * * * * * * * * * * * * * *" + '\n' + "Checking verification log results" + '\n' + "* * * * * * * * * * * * * * * * *")
        for i in checklist:
            dpx2ffv1avfuncs.verification_check(i)

if args.checklogs:
    indir = args.input_path
    limit = dpx2ffv1avfuncs.assign_limit()
    dpx2ffv1avfuncs.input_check(indir)

    if '--textlist' in sys.argv:
        with open(args.textlist_path) as f:
            lines = [line.rstrip() for line in f]
    else:
        lines = dpx2ffv1avfuncs.get_immediate_subdirectories(indir)

    for object_folder in lines:
        if not limit or (limit) in object_folder:
            if os.path.isdir(os.path.join(indir, object_folder)):
                print (os.path.join(indir, object_folder))
                dpx2ffv1avfuncs.verification_check(os.path.join(indir, object_folder))
            elif os.path.isfile(os.path.join(indir, object_folder)):
                print("skipped", os.path.join(indir, object_folder))
        elif limit and not (limit) in object_folder:
            print("Skipped", object_folder)

#if args.verifylossless:
    #for *.mkv run ffprobe to check if file contains a rawcooked reversibility file
    #if so, funnel into rawcooked decode pathway

if args.decodeffv1:
    indir = args.input_path
    limit = dpx2ffv1avfuncs.assign_limit()
    dpx2ffv1avfuncs.input_check(indir)

    #use --output instead
    if '--dpxcheck' in sys.argv:
        verifolder_base = args.dpxcheck_path
        if not os.path.isdir(dpxverifolder):
            print ("Specified DPX check folder does not exist.  Uisng input folder instead")
            verifolder_base = args.input_path
    else:
        verifolder_base = args.input_path

    #TO DO: make sure terminology is consistent across script (i.e. item_name vs object_folder)
    for object_folder in os.listdir(indir):
        dpxverifolder = os.path.join(verifolder_base, object_folder, object_folder + '_dpx')
        #TO DO: add check for more than one mkv file
        if not limit or (limit) in object_folder:
            if os.path.isdir(os.path.join(indir, object_folder)):
                print ('\n', "FOLDER: ", os.path.join(object_folder))
                mkv_file = glob.glob1(os.path.join(indir, object_folder, 'pm'), "*.mkv")
                mkvcounter = len(mkv_file)
                if mkvcounter == 1:
                    for i in mkv_file:
                        ffv1_file_abspath = os.path.join(indir, object_folder, 'pm', i)
                        mkvsize = dpx2ffv1avfuncs.get_folder_size(os.path.join(indir, object_folder, 'pm'))
                        subprocess.call([args.rawcooked_path, ffv1_file_abspath, '-o', dpxverifolder])
                        #may want to allow passing an md5 file or md5 data into dpx_md5_compare so that the md5 doesn't have to be embedded
                        dpxsize = dpx2ffv1avfuncs.get_folder_size(os.path.join(dpxverifolder, 'pm'))
                        #compareset, orig_md5list = dpx2ffv1avfuncs.dpx_md5_compare(os.path.join(dpxverifolder, 'pm'))
                        print ("mkv folder size:", mkvsize)
                        print ("DPX folder size:", dpxsize)
                elif mkvcounter < 1:
                    print ("No mkv files found in", os.path.join(indir, object_folder))
                elif mkvcounter > 1:
                    print ("More than 1 mkv file found in", os.path.join(indir, object_folder))
        elif limit and not (limit) in object_folder:
            print("Skipped", object_folder)