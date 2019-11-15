import sys
import os
from opencc import OpenCC


def gen_doc_index(infolder, out_fname=None, write_to_text=False, write_to_json=False):

    from collections import OrderedDict
    import json
    import csv
    
    doc_id_dict = OrderedDict()
    
    files = (file for file in sorted(os.listdir(infolder)) 
         if os.path.isfile(os.path.join(infolder, file)))  # get only files
    
    for did, fname in enumerate(files): # ....txt
        doc_id_dict[did] = fname

    if write_to_json:
        with open(out_fname + '.json', 'w') as f:
            json.dump(doc_id_dict, f)
            
    if write_to_text:
        with open(out_fname + '.txt', 'w') as f:
            writer = csv.writer(f, delimiter='\t')
            writer.writerows(doc_id_dict.items())
            
    return doc_id_dict

        
input_folder = 'chinese_1990'
doc_id_dict = gen_doc_index(infolder=input_folder, out_fname='did', write_to_text=True, write_to_json=True)
    
    
# clean files in inputs folder and traditional 2 simplified and rename and copy to inputs folder
import glob
for f in glob.glob('inputs/*'):
    os.remove(f)

cc = OpenCC('t2s')

fnames = os.listdir(input_folder)

for fname in fnames:
    if not os.path.isdir(fname):
        with open(os.path.join(input_folder, fname), 'r') as f:
            text2conv = [line for line in f]
        with open(os.path.join('inputs', str(list(doc_id_dict.keys())[list(doc_id_dict.values()).index(fname)])), 'w') as f:
            for line in text2conv:
                f.write(cc.convert(line))
                

from event_zh.main import extract_to_json
import os

for fname in doc_id_dict.keys():
    fpath = 'inputs/' + str(fname)
    if not os.path.isdir(fpath):
        extract_to_json(fpath, 'outputs')


