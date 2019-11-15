import json
import argparse
from event_zh.main import extract_to_json, extract
from opencc import OpenCC


# file = 'FGC_release_A.json'
argparser = argparse.ArgumentParser('Chinese Event Extraction')
argparser.add_argument(
        "-i", "--input",
        help="input file path"
    )
argparser.add_argument(
        "-d", "--output_dir",
        help="output file path"
    )
argparser.add_argument(
        "-o", "--output",
        help="output file path"
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

def ee(did, t, output_dir):
    
    # convert to simplified chinese
    text = cc.convert(t)
    write_file = did
    with open(write_file, 'w') as f:
        f.write(text)

    # event extraction to json
    ee_json = extract_to_json(write_file, output_dir)
    
    return ee_json

def write_to_mostai(path, ee_json):
    import json
    with open(path, 'w') as f:
        json.dump(ee_json, f)

        
num_data = 2
on_q = False


for i, dic in enumerate(data):
    
    if i >= num_data:
        break
    
    # event extraction on document
    did = dic['DID'][1:]  # strip away 'D' to avoid duplicates
    text = dic['DTEXT']
    try:
        djson = ee(did, text, output_dir)
    

        if on_q:
            # event extraction on questions
            qjsons = []
            qs = dic['QUESTIONS']
            for q in qs:
                text = q['QTEXT']
                qid = q['QID'][1:]
                qjsons.append(ee(qid, text, output_dir))

            # keep all jsons to generate most ai format
            ee_jsons.update({did: djson, 'QUESTIONS': qjsons })
        else:
            ee_jsons.update({did: djson})
    
    except FileNotFoundError:
        raise

write_to_mostai(write_file, ee_jsons)