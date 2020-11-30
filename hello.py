# -*- coding: utf-8 -*-
"""
Created on Mon Nov 30 01:08:44 2020

@author: stavos
"""

import time as _time
import os

from bs4 import BeautifulSoup
from bs4 import Tag

path = r"D:\Games\Return to Castle Wolfenstein\Main"
download_path = "s3something"

exceptions = [
         'mp_pak0.pk3',
         'mp_pak01.pk3',
         'mp_pak1.pk3',
         'mp_pak2.pk3',
         'mp_pak3.pk3',
         'mp_pak4.pk3',
         'mp_pak5.pk3',
         'sp_pak1.pk3',
         'sp_pak2.pk3',
         'sp_pak3.pk3'
 ]

def list_pk3_files(path):
    print("[ ] Scanning files in " + path)
    
    pk3_files = [] # will contain elements like [filepath,date]
    for subdir, dirs, files in os.walk(path):
            for file in files:
                #print os.path.join(subdir, file)
                filepath = subdir + os.sep + file

                if filepath.endswith(".pk3"):
                    file_date_str = filepath.replace(path,"").replace("\\","")
                    pk3_files.append(file_date_str)
    #print(osp_files)
    sorted_pk3_files = sorted(pk3_files)
    return sorted_pk3_files

pk3_list = list_pk3_files(path)

main_list = list(set(pk3_list) - set(exceptions))
main_list

