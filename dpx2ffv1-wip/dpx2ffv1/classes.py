#!/usr/bin/env python3

import os
import subprocess
from dpx2ffv1.dpx2ffv1parameters import args

class FilmObject:
    """example film class"""
    def __init__(self, name):
        self.name = name
        #initialize status as pending
        self.set_status("Pending")
        self.set_mediaconch_policies()
        
    def set_status(self, status):
        self.status = status
        return(self.status)
    
    def set_variables(self, name, indir, outdir):
        #TO DO come up with a better way of organizing variables
        #set identifiers for output folder and file names
        preservation_folder = 'pm'
        access_folder = 'ac'
        metadata = 'meta'
        transcode_input = os.path.join(indir, name, preservation_folder)
        outputBaseFilename = (name + '-pm' ) if args.keep_filename else (name)
        pmAbsPath = os.path.join(outdir, outputBaseFilename, preservation_folder)
        mkv_file = os.path.join(pmAbsPath, name + '.mkv')
        framemd5 = os.path.join(pmAbsPath, name + '.framemd5')
        
        
        object_variables = {
        'preservation folder' : preservation_folder,
        'access folder' : access_folder,
        'metadata' : metadata,
        'transcode input' : transcode_input,
        'outputBaseFilename' : outputBaseFilename,
        'pmAbsPath' : pmAbsPath,
        'mkv_file' : mkv_file,
        'framemd5' : framemd5
        }
        
        '''
        inputAbsPath = os.path.join(indir, name)
        baseOutput = os.path.join(outdir, baseFilename)
        acOutputFolder = os.path.join(baseOutput, ac_identifier)
        acAbsPath = os.path.join(acOutputFolder, baseFilename + '-' + ac_identifier + '.mp4')
        metaOutputFolder = os.path.join(baseOutput, metadata_identifier)
        jsonAbsPath = os.path.join(metaOutputFolder, baseFilename + '-' + metadata_identifier + '.json')
        pmMD5AbsPath = os.path.join(pmOutputFolder, mkvBaseFilename + '.md5')
        '''
        print (object_variables.get('transcode input'))
        return object_variables
    
    def set_mediaconch_policies (self):
        pass
        #pass this a dictionary to which it can append information about what policies were used
        '''
        #assign mediaconch policies to use
        if not args.input_policy:
            movPolicy = os.path.join(os.path.dirname(__file__), 'data/mediaconch_policies/AJA_NTSC_VHS-4AS-MOV.xml')
        else:
            movPolicy = args.input_policy
        if not args.output_policy:
            mkvPolicy = os.path.join(os.path.dirname(__file__), 'data/mediaconch_policies/AJA_NTSC_VHS-4AS-MKV-PCM.xml')
        else:
            mkvPolicy = args.output_policy
        
        #verify that mediaconch policies are present
        corefuncs.mediaconch_policy_exists(movPolicy)
        corefuncs.mediaconch_policy_exists(mkvPolicy)
        '''
    
    def run_rawcooked(self, object_variables):
        #TO DO log rawcooked version and check that rawcooked exists
        rawcooked_command = [args.rawcooked_path, '--all', '--framemd5', '--framemd5-name', object_variables.get('framemd5')] 
        if args.framerate:
            rawcooked_command += ['-framerate', args.framerate]
        rawcooked_command += [object_variables.get('transcode input'), '-o', object_variables.get('mkv_file')]
        print(rawcooked_command)
        subprocess.call(rawcooked_command)
    
    def get_name(self):
        return self.name
    
    def get_status(self):
        return self.status

    def exifdata(self):
        #run exiftool on object and save to dictionary
        pass

    def get_associated_files():
        pass	

    def test_function(self):
        print ('hello world')

#films = [FilmObject(name) for name in input]