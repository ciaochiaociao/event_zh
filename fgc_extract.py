import json
import argparse
import os
from event_zh.main import extract_and_coref
from opencc import OpenCC


# file = 'FGC_release_A.json'
argparser = argparse.ArgumentParser('Chinese Event Extraction')
argparser.add_argument(
        "-i", "--input",
        help="input file path",
        default="FGC_data/FGC_release_A_all(cn).json"
    )
argparser.add_argument(
        "-d", "--output_dir",
        help="output file path",
        default="data_dir"
    )
argparser.add_argument(
        "-o", "--output",
        help="output file path",
        default="FGC_train.ee.json"
    )
argparser.add_argument(
        "--t2s",
        action="store_true",
        help="translating to simplified chinese"
    )


args = argparser.parse_args()

file = args.input
# output_dir = 'formosa_ai_outputs'
output_dir = args.output_dir

# write_file = 'FGC_train3.ee.json'
write_file = args.output

with open(file) as f:
    data = json.load(f)
    
cc = OpenCC('t2s')

ee_jsons = {}

def ee(did, text, output_dir, write_out=True):
    
    if args.t2s:
        # convert to simplified chinese
        text = cc.convert(text)

    # output to file
    if write_out:
        write_file = os.path.join(output_dir, did)
        with open(write_file, 'w') as f:
            f.write(text)

    # event extraction to json
    ee_json = extract_and_coref(write_file, output_dir, fmt='fgc', to_json=False)
    
    return ee_json

def write_to_mostai(path, ee_jsons):
    import json
    with open(path, 'w') as f:
        json.dump(ee_jsons, f, ensure_ascii=False)


num_data = float('Inf') # set small number for testing
on_q = True  # False for testing


try:
    for i, dic in enumerate(data):

        if i >= num_data:
            break

        
        try:
            # event extraction on document
            did = dic['DID'][1:]  # strip away 'D' to avoid duplicates
            text = dic['DTEXT']
            djson = {'PASSAGE': ee(did, text, output_dir)}

            
            if on_q:            
                # event extraction on questions
                qjsons = []
                qs = dic['QUESTIONS']

                for q in qs:
                    text = q['QTEXT']
                    qid = q['QID'][1:]
                    qjson = ee(qid, text, output_dir)
                    print('qjson', qjson)
                    if len(qjson['events']) > 0 or len(qjson['corefs']) > 0:
                        qjson['QID'] = q['QID']
                        qjsons.append(qjson)

                djson.update({'QUESTIONS': qjsons})
                
            # keep all jsons to generate most ai format
            ee_jsons.update({dic['DID']: djson})

        except FileNotFoundError:
            raise
        
finally:
    print(ee_jsons)
    write_to_mostai(write_file, ee_jsons)