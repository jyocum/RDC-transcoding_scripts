#!/usr/bin/env python3

def equipment_dict():

    '''
    VTRs
    '''
    panasonic_ag1980 = {
    'Coding Algorithm' : 'A=ANALOG',
    'Output is one of' : ['Composite', 'S-Video']
    }

    '''
    TBCs
    '''
    dps_295 = {
    'Coding Algorithm' : 'A=ANALOG',
    'Hardware Type' : 'TBC',
    'Output is one of' : ['Composite', 'S-Video', 'Component']
    }

    '''
    ADCs
    '''
    hd10ava = {
    'Coding Algorithm' : 'A=SDI',
    'Hardware Type' : 'A/D'
    }

    '''
    Capture Cards
    '''
    kona1 = {
    'Coding Algorithm' : 'A=v210',
    'Hardware Type' : 'DIO'
    }
        
    equipment_dict = {
    'Panasonic AG-1980P' : panasonic_ag1980, 
    'DPS-295' : dps_295,
    'HD10AVA' : hd10ava,
    'Kona-1-T-R0' : kona1
    }

    return equipment_dict