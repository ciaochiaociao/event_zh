import sys
import os
from opencc import OpenCC


from event_zh.main import extract_to_json
import os
import json

with open('did.json') as f:
    doc_id_dict = json.load(f)
try:
    num = int(sys.argv[1])
except:
    num = None
    while not isinstance(num, int):
        try:
            num = int(input('Please input where you want to start: '))
        except:
            pass
for fname in sorted(doc_id_dict.keys(), key=int):

    if int(fname) >= num:
        fpath = 'inputs/' + str(fname)
        if not os.path.isdir(fpath):
            extract_to_json(fpath, 'outputs')
